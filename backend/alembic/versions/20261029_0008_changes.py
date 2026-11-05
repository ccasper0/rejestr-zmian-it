"""Changes: changes, change_items, change_ci_consents, change_comments, attachments,
number_sequences; the CI owner consent flag of change categories.

CLAUDE.md 4.1, 4.2, 6.3, 7; decisions in docs/decisions/0013-change-persistence.md
(state machine rules: docs/decisions/0012-change-state-machine.md).

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-29

Every table has ``company_id`` (also the child tables), so Row-Level Security uses the
same direct policy everywhere (``company_id = ANY (app_company_ids())``) - no policy
depends on a join. Composite foreign keys ``(change_id, company_id)`` and
``(ci_id, company_id)`` make a child row of another company impossible.

Protection in the database (defence in depth, the services are the first line):

- ``change_comments``, ``attachments``, ``change_ci_consents``: append-only (``app_rw``
  has only SELECT, INSERT; a trigger rejects UPDATE / DELETE / TRUNCATE for every role,
  CLAUDE.md 6.3);
- ``changes``: identity columns are immutable; ``version`` grows by exactly one on every
  UPDATE (optimistic locking cannot be skipped); ``status``, the lifecycle timestamps and
  ``approved_by_id`` and ``consent_round`` change only on the action path
  (``app.change_action`` = the change id, set by the action service) and that path never
  changes the business fields; from ``approved`` on the business fields are frozen (except
  the narrow re-pointing of the verifier / emergency approver decided by the domain);
  ``rejected`` / ``cancelled`` rows are closed entirely; consistency and four-eyes CHECKs
  (on the approver of record, ``approved_by_id``); no DELETE;
- ``change_items``: no INSERT / DELETE once the change is frozen; the CI snapshot
  (identifier, name) is written once, on the action path;
- ``number_sequences``: starts at 0 and advances by exactly one;
- ``company_must_be_active()`` (migration 0007) on every write of the change tables.

Runs as ``app_owner``; ``downgrade`` refuses to run as any other role. It drops the
business data of these tables (their history stays in ``audit_log``).
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

HEX64 = "^[0-9a-f]{64}$"
STATUSES = (
    "draft",
    "pending_approval",
    "approved",
    "implemented",
    "verified",
    "rejected",
    "rolled_back",
    "cancelled",
)
# Business fields frozen from approval on (CLAUDE.md 4.2: from implemented; approved by the
# state machine, which allows no edit there either); terminal statuses: the whole row.
FROZEN = ("approved", "implemented", "verified", "rolled_back")
TERMINAL = ("rejected", "cancelled")
CHANGE_TYPES = ("standard", "normal", "emergency")
RISKS = ("low", "medium", "high")
ACTIONS = (
    "submit",
    "return",
    "approve",
    "reject",
    "implement",
    "verify",
    "rollback",
    "cancel",
    "consent",
)
MERIT_COLUMNS = (
    "title",
    "category_id",
    "subcategory_id",
    "change_type",
    "risk",
    "description",
    "implementation_plan",
    "rollback_plan",
    "impact",
    "requirement_ref",
    "ticket_ref",
    "assignee_id",
    "approver_id",
    "verifier_id",
    "window_start",
    "window_end",
)
# ``verifier_id`` and ``approver_id`` are re-pointable in narrow cases of an implemented
# change decided by the state machine (owner decisions 2026-10-29, ADR 0012 §6); the guard
# only bounds them to those statuses (ADR 0013 §3).
FROZEN_COLUMNS = tuple(c for c in MERIT_COLUMNS if c not in {"verifier_id", "approver_id"})
LIFECYCLE_COLUMNS = (
    "status",
    "approved_at",
    "implemented_at",
    "verified_at",
    "rejected_at",
    "approved_by_id",
    "consent_round",
)
TABLES = (
    "attachments",
    "change_comments",
    "change_ci_consents",
    "change_items",
    "changes",
    "number_sequences",
)
APPEND_ONLY = ("change_comments", "attachments", "change_ci_consents")


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


def _row(prefix: str, columns: tuple[str, ...]) -> str:
    return "ROW(" + ", ".join(f"{prefix}.{c}" for c in columns) + ")"


FUNCTIONS = [
    r"""-- Append-only tables other than audit_log (CLAUDE.md 6.3): comments, attachments, CI
-- owner consents. Rejects UPDATE, DELETE and TRUNCATE for every role.
CREATE FUNCTION reject_modification() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    RAISE EXCEPTION '% is append-only: % is not allowed', TG_TABLE_NAME, TG_OP
        USING ERRCODE = 'restrict_violation',
              HINT = 'Rows of this table can only be added (CLAUDE.md 6.3).';
END
$$
    """,
    "REVOKE ALL ON FUNCTION reject_modification() FROM PUBLIC, app_rw",
    r"""-- True when the current transaction is on the action path of the change (the action
-- service sets app.change_action to the change id for the duration of one action).
CREATE FUNCTION app_change_action(change_id uuid) RETURNS boolean
    LANGUAGE sql STABLE PARALLEL SAFE
    AS $$ SELECT COALESCE(current_setting('app.change_action', true), '') = change_id::text $$
    """,
    f"""-- Status changes only through the state machine (action path), the business fields
-- only through editing (never on the action path), and never once frozen.
CREATE FUNCTION changes_guard() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NEW.id <> OLD.id OR NEW.company_id <> OLD.company_id OR NEW.number <> OLD.number
       OR NEW.requested_by_id <> OLD.requested_by_id
       OR NEW.supersedes_change_id IS DISTINCT FROM OLD.supersedes_change_id
       OR NEW.created_at <> OLD.created_at THEN
        RAISE EXCEPTION 'changes: id, company_id, number, requested_by_id, '
                        'supersedes_change_id and created_at are immutable'
            USING ERRCODE = 'restrict_violation';
    END IF;
    IF OLD.status IN ({", ".join(repr(s) for s in TERMINAL)}) THEN
        RAISE EXCEPTION 'change_frozen: change % is closed (status %)', OLD.id, OLD.status
            USING ERRCODE = 'restrict_violation', CONSTRAINT = 'changes_frozen';
    END IF;
    IF NEW.version <> OLD.version + 1 THEN
        RAISE EXCEPTION 'changes.version must grow by exactly one on every update (% -> %)',
                        OLD.version, NEW.version
            USING ERRCODE = 'check_violation', CONSTRAINT = 'changes_version_step';
    END IF;
    IF {_row("NEW", LIFECYCLE_COLUMNS)} IS DISTINCT FROM {_row("OLD", LIFECYCLE_COLUMNS)}
       AND NOT app_change_action(OLD.id) THEN
        RAISE EXCEPTION 'change_status_path: the status of change % changes only through '
                        'the action endpoint', OLD.id
            USING ERRCODE = 'restrict_violation', CONSTRAINT = 'changes_status_path';
    END IF;
    IF {_row("NEW", MERIT_COLUMNS)} IS DISTINCT FROM {_row("OLD", MERIT_COLUMNS)} THEN
        IF app_change_action(OLD.id) THEN
            RAISE EXCEPTION 'changes: an action does not edit the fields of change %', OLD.id
                USING ERRCODE = 'restrict_violation';
        END IF;
        IF OLD.status IN ({", ".join(repr(s) for s in FROZEN)})
           AND ({_row("NEW", FROZEN_COLUMNS)} IS DISTINCT FROM {_row("OLD", FROZEN_COLUMNS)}
                -- the verifier: only of an implemented change (re-pointing a verifier who
                -- can no longer verify)
                OR (NEW.verifier_id IS DISTINCT FROM OLD.verifier_id
                    AND OLD.status <> 'implemented')
                -- the approver: only of an emergency change implemented without approval
                OR (NEW.approver_id IS DISTINCT FROM OLD.approver_id
                    AND NOT (OLD.status = 'implemented' AND OLD.change_type = 'emergency'
                             AND OLD.approved_at IS NULL))) THEN
            RAISE EXCEPTION 'change_frozen: change % is frozen (status %)', OLD.id, OLD.status
                USING ERRCODE = 'restrict_violation', CONSTRAINT = 'changes_frozen';
        END IF;
    END IF;
    RETURN NEW;
END
$$
    """,
    "REVOKE ALL ON FUNCTION changes_guard() FROM PUBLIC, app_rw",
    f"""-- The CI list of a frozen change never changes; the CI snapshot is written once, by
-- the action that implements the change.
CREATE FUNCTION change_items_guard() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    current_status text;
    target uuid := COALESCE(NEW.change_id, OLD.change_id);
BEGIN
    IF TG_OP = 'UPDATE' THEN
        IF NEW.id <> OLD.id OR NEW.company_id <> OLD.company_id
           OR NEW.change_id <> OLD.change_id OR NEW.ci_id <> OLD.ci_id
           OR NEW.created_at <> OLD.created_at THEN
            RAISE EXCEPTION 'change_items: only the CI snapshot can be updated'
                USING ERRCODE = 'restrict_violation';
        END IF;
        IF ROW(NEW.ci_identifier, NEW.ci_name) IS DISTINCT FROM
           ROW(OLD.ci_identifier, OLD.ci_name)
           AND (OLD.ci_identifier IS NOT NULL OR NOT app_change_action(OLD.change_id)) THEN
            RAISE EXCEPTION 'change_items: the CI snapshot is written once, by an action'
                USING ERRCODE = 'restrict_violation';
        END IF;
        RETURN NEW;
    END IF;
    SELECT status INTO current_status FROM changes WHERE id = target;
    IF current_status IS NULL THEN
        RAISE EXCEPTION 'change_items: change % is not visible', target
            USING ERRCODE = 'insufficient_privilege';
    END IF;
    IF current_status IN ({", ".join(repr(s) for s in (*FROZEN, *TERMINAL))}) THEN
        RAISE EXCEPTION 'change_frozen: the CI list of change % is frozen', target
            USING ERRCODE = 'restrict_violation', CONSTRAINT = 'changes_frozen';
    END IF;
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END
$$
    """,
    "REVOKE ALL ON FUNCTION change_items_guard() FROM PUBLIC, app_rw",
    r"""-- Numbering (CHG-{PREFIX}-{YYYY}-{NNNN}): a year counter starts at 0 and advances by
-- exactly one, so a number can never be skipped or reused through the counter.
CREATE FUNCTION number_sequences_guard() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF NEW.last_value <> 0 THEN
            RAISE EXCEPTION 'number_sequences: a counter starts at 0'
                USING ERRCODE = 'check_violation';
        END IF;
        RETURN NEW;
    END IF;
    IF NEW.company_id <> OLD.company_id OR NEW.year <> OLD.year OR NEW.id <> OLD.id THEN
        RAISE EXCEPTION 'number_sequences: company_id and year are immutable'
            USING ERRCODE = 'restrict_violation';
    END IF;
    IF NEW.last_value <> OLD.last_value + 1 THEN
        RAISE EXCEPTION 'number_sequences: a counter advances by exactly one'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END
$$
    """,
    "REVOKE ALL ON FUNCTION number_sequences_guard() FROM PUBLIC, app_rw",
]

TRIGGERS = [
    *(
        statement
        for table in APPEND_ONLY
        for statement in (
            f"""
            CREATE TRIGGER {table}_append_only
                BEFORE UPDATE OR DELETE ON {table}
                FOR EACH ROW EXECUTE FUNCTION reject_modification()
            """,
            f"""
            CREATE TRIGGER {table}_no_truncate
                BEFORE TRUNCATE ON {table}
                FOR EACH STATEMENT EXECUTE FUNCTION reject_modification()
            """,
            f"""
            CREATE TRIGGER {table}_company_active
                BEFORE INSERT ON {table}
                FOR EACH ROW EXECUTE FUNCTION company_must_be_active()
            """,
        )
    ),
    """
    CREATE TRIGGER changes_guard
        BEFORE UPDATE ON changes
        FOR EACH ROW EXECUTE FUNCTION changes_guard()
    """,
    """
    CREATE TRIGGER changes_company_active
        BEFORE INSERT OR UPDATE ON changes
        FOR EACH ROW EXECUTE FUNCTION company_must_be_active()
    """,
    """
    CREATE TRIGGER changes_no_truncate
        BEFORE TRUNCATE ON changes
        FOR EACH STATEMENT EXECUTE FUNCTION reject_modification()
    """,
    """
    CREATE TRIGGER change_items_guard
        BEFORE INSERT OR UPDATE OR DELETE ON change_items
        FOR EACH ROW EXECUTE FUNCTION change_items_guard()
    """,
    """
    CREATE TRIGGER change_items_company_active
        BEFORE INSERT OR UPDATE ON change_items
        FOR EACH ROW EXECUTE FUNCTION company_must_be_active()
    """,
    """
    CREATE TRIGGER number_sequences_guard
        BEFORE INSERT OR UPDATE ON number_sequences
        FOR EACH ROW EXECUTE FUNCTION number_sequences_guard()
    """,
]

GRANTS = [
    # Default privileges (roles.psql) gave app_rw SELECT/INSERT/UPDATE/DELETE.
    "REVOKE ALL ON changes FROM app_rw",
    "GRANT SELECT, INSERT, UPDATE ON changes TO app_rw",
    "REVOKE ALL ON change_items FROM app_rw",
    # DELETE: a CI removed from a draft (frozen changes: trigger).
    "GRANT SELECT, INSERT, UPDATE, DELETE ON change_items TO app_rw",
    "REVOKE ALL ON number_sequences FROM app_rw",
    "GRANT SELECT, INSERT, UPDATE ON number_sequences TO app_rw",
    *(
        statement
        for table in APPEND_ONLY
        for statement in (
            f"REVOKE ALL ON {table} FROM app_rw",
            f"GRANT SELECT, INSERT ON {table} TO app_rw",
        )
    ),
]


def _policies(table: str, commands: tuple[str, ...]) -> list[str]:
    scope = "company_id = ANY (app_company_ids())"
    statements = [f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"]
    for command in commands:
        name = f"{table}_{command.lower()}"
        if command == "SELECT" or command == "DELETE":
            clause = f"USING ({scope})"
        elif command == "INSERT":
            clause = f"WITH CHECK ({scope})"
        else:
            clause = f"USING ({scope}) WITH CHECK ({scope})"
        statements.append(f"CREATE POLICY {name} ON {table} FOR {command} TO app_rw {clause}")
    return statements


POLICIES = [
    *_policies("changes", ("SELECT", "INSERT", "UPDATE")),
    *_policies("change_items", ("SELECT", "INSERT", "UPDATE", "DELETE")),
    *_policies("number_sequences", ("SELECT", "INSERT", "UPDATE")),
    *(p for table in APPEND_ONLY for p in _policies(table, ("SELECT", "INSERT"))),
]


def _timestamps() -> list[sa.Column[object]]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def _uuid(name: str, *, nullable: bool = False) -> sa.Column[object]:
    return sa.Column(name, postgresql.UUID(as_uuid=True), nullable=nullable)


def _uuid_pk() -> sa.Column[object]:
    return sa.Column(
        "id",
        postgresql.UUID(as_uuid=True),
        server_default=sa.text("gen_random_uuid()"),
        nullable=False,
    )


def _text(name: str, *, nullable: bool = True) -> sa.Column[object]:
    return sa.Column(name, sa.Text(), nullable=nullable)


def _ts(name: str) -> sa.Column[object]:
    return sa.Column(name, sa.DateTime(timezone=True), nullable=True)


def _change_fk(table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["change_id", "company_id"],
        ["changes.id", "changes.company_id"],
        name=op.f(f"fk_{table}_change_id_changes"),
    )


def _company_fk(table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["company_id"], ["companies.id"], name=op.f(f"fk_{table}_company_id_companies")
    )


def _user_fk(table: str, column: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [column], ["users.id"], name=op.f(f"fk_{table}_{column}_users")
    )


def _ci_fk(table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["ci_id", "company_id"],
        ["configuration_items.id", "configuration_items.company_id"],
        name=op.f(f"fk_{table}_ci_id_configuration_items"),
    )


def upgrade() -> None:
    op.add_column(
        "change_categories",
        sa.Column(
            "requires_ci_owner_consent", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
    )
    # Target of the composite foreign keys (ci_id, company_id) of the change tables.
    op.create_unique_constraint(
        op.f("uq_configuration_items_id_company_id"), "configuration_items", ["id", "company_id"]
    )

    op.create_table(
        "number_sequences",
        _uuid_pk(),
        _uuid("company_id"),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("last_value", sa.Integer(), server_default=sa.text("0"), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_number_sequences")),
        sa.UniqueConstraint(
            "company_id", "year", name=op.f("uq_number_sequences_company_id_year")
        ),
        sa.CheckConstraint(
            "last_value >= 0", name=op.f("ck_number_sequences_last_value_non_negative")
        ),
        sa.CheckConstraint(
            "year BETWEEN 2000 AND 9999", name=op.f("ck_number_sequences_year_range")
        ),
        _company_fk("number_sequences"),
    )

    op.create_table(
        "changes",
        _uuid_pk(),
        _uuid("company_id"),
        _text("number", nullable=False),
        _text("title"),
        _uuid("category_id", nullable=True),
        _uuid("subcategory_id", nullable=True),
        _text("change_type"),
        _text("risk"),
        sa.Column("status", sa.Text(), server_default="draft", nullable=False),
        _text("description"),
        _text("implementation_plan"),
        _text("rollback_plan"),
        _text("impact"),
        _text("requirement_ref"),
        _text("ticket_ref"),
        _uuid("requested_by_id"),
        _uuid("assignee_id", nullable=True),
        _uuid("approver_id", nullable=True),
        _uuid("verifier_id", nullable=True),
        _ts("window_start"),
        _ts("window_end"),
        _ts("implemented_at"),
        _ts("verified_at"),
        _ts("approved_at"),
        _ts("rejected_at"),
        # Who approved (the ``approve`` action); NULL with approved_at = ``system``.
        _uuid("approved_by_id", nullable=True),
        _uuid("supersedes_change_id", nullable=True),
        sa.Column("consent_round", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_changes")),
        sa.UniqueConstraint("number", name=op.f("uq_changes_number")),
        sa.UniqueConstraint("id", "company_id", name=op.f("uq_changes_id_company_id")),
        _company_fk("changes"),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["change_categories.id"],
            name=op.f("fk_changes_category_id_change_categories"),
        ),
        sa.ForeignKeyConstraint(
            ["subcategory_id"],
            ["change_categories.id"],
            name=op.f("fk_changes_subcategory_id_change_categories"),
        ),
        _user_fk("changes", "requested_by_id"),
        _user_fk("changes", "assignee_id"),
        _user_fk("changes", "approver_id"),
        _user_fk("changes", "verifier_id"),
        _user_fk("changes", "approved_by_id"),
        # A correction points to a change OF THE SAME company.
        sa.ForeignKeyConstraint(
            ["supersedes_change_id", "company_id"],
            ["changes.id", "changes.company_id"],
            name=op.f("fk_changes_supersedes_change_id_changes"),
        ),
        sa.CheckConstraint(
            "number ~ '^CHG-[A-Z]{2,8}-[0-9]{4}-[0-9]{4,}$'",
            name=op.f("ck_changes_number_format"),
        ),
        sa.CheckConstraint(_in("status", STATUSES), name=op.f("ck_changes_status_values")),
        sa.CheckConstraint(
            "change_type IS NULL OR " + _in("change_type", CHANGE_TYPES),
            name=op.f("ck_changes_change_type_values"),
        ),
        sa.CheckConstraint(
            "risk IS NULL OR " + _in("risk", RISKS), name=op.f("ck_changes_risk_values")
        ),
        sa.CheckConstraint(
            "window_start IS NULL OR window_end IS NULL OR window_start < window_end",
            name=op.f("ck_changes_window_order"),
        ),
        sa.CheckConstraint("version >= 1", name=op.f("ck_changes_version_positive")),
        sa.CheckConstraint(
            "consent_round >= 1", name=op.f("ck_changes_consent_round_positive")
        ),
        sa.CheckConstraint(
            "supersedes_change_id IS NULL OR supersedes_change_id <> id",
            name=op.f("ck_changes_not_superseding_itself"),
        ),
        # Lifecycle timestamps agree with the status (CLAUDE.md 4.2).
        sa.CheckConstraint(
            "status <> 'approved' OR approved_at IS NOT NULL",
            name=op.f("ck_changes_approved_has_timestamp"),
        ),
        sa.CheckConstraint(
            "status NOT IN ('implemented', 'verified', 'rolled_back') "
            "OR implemented_at IS NOT NULL",
            name=op.f("ck_changes_implemented_has_timestamp"),
        ),
        sa.CheckConstraint(
            "status <> 'verified' OR (verified_at IS NOT NULL AND approved_at IS NOT NULL)",
            name=op.f("ck_changes_verified_has_timestamps"),
        ),
        sa.CheckConstraint(
            "status <> 'rejected' OR rejected_at IS NOT NULL",
            name=op.f("ck_changes_rejected_has_timestamp"),
        ),
        # Past the draft, the core of §4.3 is always filled (cancelled drafts may be
        # incomplete). The approver is deliberately not here (ADR 0012 §10 pt 3).
        sa.CheckConstraint(
            "status IN ('draft', 'cancelled') OR (title IS NOT NULL "
            "AND category_id IS NOT NULL AND change_type IS NOT NULL AND risk IS NOT NULL "
            "AND description IS NOT NULL AND implementation_plan IS NOT NULL "
            "AND assignee_id IS NOT NULL)",
            name=op.f("ck_changes_complete_after_draft"),
        ),
        # Four eyes (CLAUDE.md 4.2): a change is never approved by its requester or
        # assignee - the critical deviation of the report cannot be stored. Judged by who
        # actually approved (approved_by_id; NULL = system, ADR 0012 §4).
        sa.CheckConstraint(
            "approved_by_id IS NULL OR (approved_by_id <> requested_by_id "
            "AND approved_by_id IS DISTINCT FROM assignee_id)",
            name=op.f("ck_changes_four_eyes"),
        ),
        # The approver of record is the designated approver at the time of approval, and
        # only an approved change has one.
        sa.CheckConstraint(
            "approved_by_id IS NULL OR (approved_at IS NOT NULL AND approved_by_id = approver_id)",
            name=op.f("ck_changes_approved_by_designated"),
        ),
    )
    op.create_index("ix_changes_company_id_status", "changes", ["company_id", "status"])
    op.create_index("ix_changes_company_id_created_at", "changes", ["company_id", "created_at"])
    op.create_index(
        "ix_changes_company_id_implemented_at", "changes", ["company_id", "implemented_at"]
    )
    op.create_index(
        "ix_changes_company_id_change_type", "changes", ["company_id", "change_type"]
    )
    op.create_index("ix_changes_category_id", "changes", ["category_id"])
    op.create_index("ix_changes_subcategory_id", "changes", ["subcategory_id"])
    op.create_index("ix_changes_assignee_id", "changes", ["assignee_id"])
    op.create_index("ix_changes_approver_id", "changes", ["approver_id"])
    op.create_index("ix_changes_supersedes_change_id", "changes", ["supersedes_change_id"])

    op.create_table(
        "change_items",
        _uuid_pk(),
        _uuid("company_id"),
        _uuid("change_id"),
        _uuid("ci_id"),
        # Snapshot of the CI at implementation (ADR 0011 §9 pt 5); NULL before.
        _text("ci_identifier"),
        _text("ci_name"),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_change_items")),
        sa.UniqueConstraint("change_id", "ci_id", name=op.f("uq_change_items_change_id_ci_id")),
        _change_fk("change_items"),
        _ci_fk("change_items"),
        sa.CheckConstraint(
            "(ci_identifier IS NULL) = (ci_name IS NULL)",
            name=op.f("ck_change_items_snapshot_complete"),
        ),
    )
    op.create_index("ix_change_items_ci_id", "change_items", ["ci_id"])

    op.create_table(
        "change_ci_consents",
        _uuid_pk(),
        _uuid("company_id"),
        _uuid("change_id"),
        _uuid("ci_id"),
        _uuid("owner_user_id"),
        sa.Column("consent_round", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_change_ci_consents")),
        # One consent per owner per round; a new owner of the CI consents again.
        sa.UniqueConstraint(
            "change_id",
            "ci_id",
            "consent_round",
            "owner_user_id",
            name=op.f("uq_change_ci_consents_round_owner"),
        ),
        _change_fk("change_ci_consents"),
        _ci_fk("change_ci_consents"),
        _user_fk("change_ci_consents", "owner_user_id"),
        sa.CheckConstraint(
            "consent_round >= 1", name=op.f("ck_change_ci_consents_consent_round_positive")
        ),
    )

    op.create_table(
        "change_comments",
        _uuid_pk(),
        _uuid("company_id"),
        _uuid("change_id"),
        _uuid("author_id"),
        _text("body", nullable=False),
        # The action the comment was given with (return / reject / ...); NULL = a plain
        # comment (POST .../comments).
        _text("action"),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_change_comments")),
        _change_fk("change_comments"),
        _user_fk("change_comments", "author_id"),
        sa.CheckConstraint(
            "char_length(body) BETWEEN 1 AND 4000", name=op.f("ck_change_comments_body_length")
        ),
        sa.CheckConstraint(
            "action IS NULL OR " + _in("action", ACTIONS),
            name=op.f("ck_change_comments_action_values"),
        ),
    )
    op.create_index(
        "ix_change_comments_change_id_created_at", "change_comments", ["change_id", "created_at"]
    )

    op.create_table(
        "attachments",
        _uuid_pk(),
        _uuid("company_id"),
        _uuid("change_id"),
        _text("filename", nullable=False),
        _text("content_type", nullable=False),
        sa.Column("size", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.CHAR(64), nullable=False),
        _text("storage_key", nullable=False),
        _uuid("uploaded_by_id"),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_attachments")),
        sa.UniqueConstraint("storage_key", name=op.f("uq_attachments_storage_key")),
        _change_fk("attachments"),
        _user_fk("attachments", "uploaded_by_id"),
        sa.CheckConstraint(f"sha256 ~ '{HEX64}'", name=op.f("ck_attachments_sha256_hex")),
        sa.CheckConstraint("size >= 0", name=op.f("ck_attachments_size_non_negative")),
        sa.CheckConstraint(
            "char_length(filename) BETWEEN 1 AND 255",
            name=op.f("ck_attachments_filename_length"),
        ),
    )
    op.create_index("ix_attachments_change_id", "attachments", ["change_id"])

    for statement in [*FUNCTIONS, *TRIGGERS, *GRANTS, *POLICIES]:
        op.execute(statement)


def downgrade() -> None:
    conn = op.get_bind()
    owner = conn.execute(
        sa.text(
            "SELECT tableowner FROM pg_tables "
            "WHERE schemaname = 'public' AND tablename = 'changes'"
        )
    ).scalar_one_or_none()
    current = conn.execute(sa.text("SELECT current_user")).scalar_one()
    if owner is not None and owner != current:
        raise RuntimeError(
            f"downgrade of the changes must run as the table owner ({owner}), not {current}"
        )
    # Business data only; its history stays in audit_log (DROP TABLE drops the triggers,
    # including the append-only ones, and the policies).
    for table in TABLES:
        op.drop_table(table)
    op.execute("DROP FUNCTION number_sequences_guard()")
    op.execute("DROP FUNCTION change_items_guard()")
    op.execute("DROP FUNCTION changes_guard()")
    op.execute("DROP FUNCTION app_change_action(uuid)")
    op.execute("DROP FUNCTION reject_modification()")
    op.drop_constraint(
        op.f("uq_configuration_items_id_company_id"), "configuration_items", type_="unique"
    )
    op.drop_column("change_categories", "requires_ci_owner_consent")
