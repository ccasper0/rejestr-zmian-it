"""Report exports: report_exports and report_number_sequences.

CLAUDE.md 4.1 (report_exports), 7, 9; decisions in docs/decisions/0017-reports-export.md.

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-02

``report_exports`` holds one row per export (PDF register report, PDF change card, CSV
register export). ``company_id`` is NULL for the multi-company report of an auditor
("Wszystkie spółki (audytor)"); ``scope_company_ids`` lists the companies whose data the
report contains (``{company_id}`` for a company report).

Row-Level Security (ADR 0017 §3):

- a company row: the standard policy ``company_id = ANY (app_company_ids())``;
- a multi-company row (``company_id IS NULL``): visible only to its author
  (``generated_by_id = app_user_id()``) and on the explicit admin path
  (``app_admin_scope()``); written only by its author with EVERY company of the report in
  the transaction scope (``scope_company_ids <@ app_company_ids()``);
- the admin path (``app_admin_scope()``) may READ every row (the admin's report list,
  §5: export ✓ for app_admin) - never write.

Protection in the database (defence in depth):

- the row is immutable except the outcome of the generation; the status moves only
  ``pending -> done | failed`` and a finished row is frozen (``report_exports_guard``);
- consistency CHECKs (done => hashes, file, size; failed => error; card => change);
- ``app_rw``: SELECT, INSERT, UPDATE (no DELETE); TRUNCATE rejected for every role.

``report_number_sequences``: one counter per (company, year) - ``RAP-{PREFIX}-{YYYY}-{NNNN}``
- and one per year for the multi-company reports (``company_id IS NULL`` -
``RAP-{YYYY}-{NNNN}``), ``UNIQUE NULLS NOT DISTINCT``; starts at 0 and advances by exactly
one (trigger).

Runs as ``app_owner``; ``downgrade`` refuses to run as any other role, and refuses to drop
a non-empty ``report_exports`` unless explicitly told so (``-x allow_audit_data_loss=yes``;
the exports stay recorded in ``audit_log``; files in the storage remain).
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import context, op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

HEX64 = "^[0-9a-f]{64}$"
KINDS = ("register", "change_card")
FORMATS = ("pdf", "csv")
STATUSES = ("pending", "done", "failed")
# Columns the generation fills in once (pending -> done | failed); all others immutable.
OUTCOME_COLUMNS = (
    "status",
    "data_sha256",
    "file_sha256",
    "size",
    "storage_key",
    "error",
    "change_count",
    "completed_at",
    "updated_at",
)
IMMUTABLE_COLUMNS = (
    "id",
    "company_id",
    "number",
    "kind",
    "format",
    "change_id",
    "scope_company_ids",
    "period_from",
    "period_to",
    "filters",
    "include_audit_trail",
    "generated_by_id",
    "created_at",
)


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


def _row(prefix: str, columns: tuple[str, ...]) -> str:
    return "ROW(" + ", ".join(f"{prefix}.{c}" for c in columns) + ")"


FUNCTIONS = [
    f"""-- A report row is written once and completed once: pending -> done | failed.
CREATE FUNCTION report_exports_guard() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF {_row("NEW", IMMUTABLE_COLUMNS)} IS DISTINCT FROM {_row("OLD", IMMUTABLE_COLUMNS)} THEN
        RAISE EXCEPTION 'report_exports: only the outcome of the generation can be updated'
            USING ERRCODE = 'restrict_violation';
    END IF;
    IF OLD.status <> 'pending' THEN
        RAISE EXCEPTION 'report_exports: report % is finished (status %)', OLD.number, OLD.status
            USING ERRCODE = 'restrict_violation', CONSTRAINT = 'report_exports_finished';
    END IF;
    RETURN NEW;
END
$$
    """,
    "REVOKE ALL ON FUNCTION report_exports_guard() FROM PUBLIC, app_rw",
    r"""-- Report numbering: a year counter starts at 0 and advances by exactly one.
CREATE FUNCTION report_number_sequences_guard() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF NEW.last_value <> 0 THEN
            RAISE EXCEPTION 'report_number_sequences: a counter starts at 0'
                USING ERRCODE = 'check_violation';
        END IF;
        RETURN NEW;
    END IF;
    IF NEW.company_id IS DISTINCT FROM OLD.company_id OR NEW.year <> OLD.year
       OR NEW.id <> OLD.id THEN
        RAISE EXCEPTION 'report_number_sequences: company_id and year are immutable'
            USING ERRCODE = 'restrict_violation';
    END IF;
    IF NEW.last_value <> OLD.last_value + 1 THEN
        RAISE EXCEPTION 'report_number_sequences: a counter advances by exactly one'
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END
$$
    """,
    "REVOKE ALL ON FUNCTION report_number_sequences_guard() FROM PUBLIC, app_rw",
]

TRIGGERS = [
    """
    CREATE TRIGGER report_exports_guard
        BEFORE UPDATE ON report_exports
        FOR EACH ROW EXECUTE FUNCTION report_exports_guard()
    """,
    # reject_modification() (migration 0008) also rejects TRUNCATE.
    """
    CREATE TRIGGER report_exports_no_truncate
        BEFORE TRUNCATE ON report_exports
        FOR EACH STATEMENT EXECUTE FUNCTION reject_modification()
    """,
    """
    CREATE TRIGGER report_number_sequences_guard
        BEFORE INSERT OR UPDATE ON report_number_sequences
        FOR EACH ROW EXECUTE FUNCTION report_number_sequences_guard()
    """,
]

GRANTS = [
    "REVOKE ALL ON report_exports FROM app_rw",
    "GRANT SELECT, INSERT, UPDATE ON report_exports TO app_rw",
    "REVOKE ALL ON report_number_sequences FROM app_rw",
    "GRANT SELECT, INSERT, UPDATE ON report_number_sequences TO app_rw",
]

_COMPANY = "company_id = ANY (app_company_ids())"
# A multi-company report: its author, with every company of the report in scope.
_OWN_AGGREGATE = (
    "company_id IS NULL AND generated_by_id = app_user_id() "
    "AND scope_company_ids <@ app_company_ids()"
)
_READ = (
    f"app_admin_scope() OR {_COMPANY} "
    "OR (company_id IS NULL AND generated_by_id = app_user_id())"
)
_WRITE = f"{_COMPANY} OR ({_OWN_AGGREGATE})"
# The yearly counter of the multi-company reports is shared by every authenticated user.
_SEQUENCE = f"{_COMPANY} OR (company_id IS NULL AND app_user_id() IS NOT NULL)"

POLICIES = [
    "ALTER TABLE report_exports ENABLE ROW LEVEL SECURITY",
    f"CREATE POLICY report_exports_select ON report_exports FOR SELECT TO app_rw USING ({_READ})",
    f"CREATE POLICY report_exports_insert ON report_exports FOR INSERT TO app_rw "
    f"WITH CHECK ({_WRITE})",
    f"CREATE POLICY report_exports_update ON report_exports FOR UPDATE TO app_rw "
    f"USING ({_WRITE}) WITH CHECK ({_WRITE})",
    "ALTER TABLE report_number_sequences ENABLE ROW LEVEL SECURITY",
    *(
        f"CREATE POLICY report_number_sequences_{command.lower()} ON report_number_sequences "
        f"FOR {command} TO app_rw {clause}"
        for command, clause in (
            ("SELECT", f"USING ({_SEQUENCE})"),
            ("INSERT", f"WITH CHECK ({_SEQUENCE})"),
            ("UPDATE", f"USING ({_SEQUENCE}) WITH CHECK ({_SEQUENCE})"),
        )
    ),
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


def upgrade() -> None:
    op.create_table(
        "report_number_sequences",
        _uuid_pk(),
        _uuid("company_id", nullable=True),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("last_value", sa.Integer(), server_default=sa.text("0"), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_report_number_sequences")),
        sa.CheckConstraint(
            "last_value >= 0", name=op.f("ck_report_number_sequences_last_value_non_negative")
        ),
        sa.CheckConstraint(
            "year BETWEEN 2000 AND 9999", name=op.f("ck_report_number_sequences_year_range")
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name=op.f("fk_report_number_sequences_company_id_companies"),
        ),
    )
    # NULLS NOT DISTINCT: exactly one counter per year for the multi-company reports.
    op.execute(
        "ALTER TABLE report_number_sequences ADD CONSTRAINT "
        "uq_report_number_sequences_company_id_year UNIQUE NULLS NOT DISTINCT (company_id, year)"
    )

    op.create_table(
        "report_exports",
        _uuid_pk(),
        _uuid("company_id", nullable=True),
        sa.Column("number", sa.Text(), nullable=False),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("format", sa.Text(), nullable=False),
        _uuid("change_id", nullable=True),
        sa.Column("scope_company_ids", postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
                  nullable=False),
        sa.Column("period_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "filters",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "include_audit_trail", sa.Boolean(), server_default=sa.false(), nullable=False
        ),
        _uuid("generated_by_id"),
        sa.Column("status", sa.Text(), server_default="pending", nullable=False),
        sa.Column("data_sha256", sa.CHAR(64), nullable=True),
        sa.Column("file_sha256", sa.CHAR(64), nullable=True),
        sa.Column("size", sa.BigInteger(), nullable=True),
        sa.Column("storage_key", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("change_count", sa.Integer(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_report_exports")),
        sa.UniqueConstraint("number", name=op.f("uq_report_exports_number")),
        sa.UniqueConstraint("storage_key", name=op.f("uq_report_exports_storage_key")),
        sa.ForeignKeyConstraint(
            ["company_id"], ["companies.id"], name=op.f("fk_report_exports_company_id_companies")
        ),
        sa.ForeignKeyConstraint(
            ["generated_by_id"],
            ["users.id"],
            name=op.f("fk_report_exports_generated_by_id_users"),
        ),
        # A change card belongs to a change of the same company.
        sa.ForeignKeyConstraint(
            ["change_id", "company_id"],
            ["changes.id", "changes.company_id"],
            name=op.f("fk_report_exports_change_id_changes"),
        ),
        sa.CheckConstraint(_in("kind", KINDS), name=op.f("ck_report_exports_kind_values")),
        sa.CheckConstraint(_in("format", FORMATS), name=op.f("ck_report_exports_format_values")),
        sa.CheckConstraint(_in("status", STATUSES), name=op.f("ck_report_exports_status_values")),
        sa.CheckConstraint(
            "number ~ '^RAP-([A-Z]{2,8}-)?[0-9]{4}-[0-9]{4,}$'",
            name=op.f("ck_report_exports_number_format"),
        ),
        sa.CheckConstraint(
            "(kind = 'change_card' AND change_id IS NOT NULL AND company_id IS NOT NULL "
            "AND format = 'pdf') OR (kind = 'register' AND change_id IS NULL)",
            name=op.f("ck_report_exports_kind_shape"),
        ),
        sa.CheckConstraint(
            "cardinality(scope_company_ids) >= 1 AND array_position(scope_company_ids, NULL) "
            "IS NULL AND (company_id IS NULL OR scope_company_ids = ARRAY[company_id])",
            name=op.f("ck_report_exports_scope"),
        ),
        sa.CheckConstraint(
            "period_from IS NULL OR period_to IS NULL OR period_from < period_to",
            name=op.f("ck_report_exports_period_order"),
        ),
        sa.CheckConstraint(
            f"data_sha256 IS NULL OR data_sha256 ~ '{HEX64}'",
            name=op.f("ck_report_exports_data_sha256_hex"),
        ),
        sa.CheckConstraint(
            f"file_sha256 IS NULL OR file_sha256 ~ '{HEX64}'",
            name=op.f("ck_report_exports_file_sha256_hex"),
        ),
        sa.CheckConstraint(
            "(status = 'pending' AND data_sha256 IS NULL AND file_sha256 IS NULL "
            " AND storage_key IS NULL AND size IS NULL AND error IS NULL "
            " AND completed_at IS NULL) "
            "OR (status = 'done' AND data_sha256 IS NOT NULL AND file_sha256 IS NOT NULL "
            " AND storage_key IS NOT NULL AND size IS NOT NULL AND size >= 0 "
            " AND change_count IS NOT NULL AND error IS NULL AND completed_at IS NOT NULL) "
            "OR (status = 'failed' AND error IS NOT NULL AND storage_key IS NULL "
            " AND completed_at IS NOT NULL)",
            name=op.f("ck_report_exports_status_shape"),
        ),
    )
    op.create_index(
        "ix_report_exports_company_id_created_at", "report_exports", ["company_id", "created_at"]
    )
    op.create_index(
        "ix_report_exports_generated_by_id_created_at",
        "report_exports",
        ["generated_by_id", "created_at"],
    )

    for statement in [*FUNCTIONS, *TRIGGERS, *GRANTS, *POLICIES]:
        op.execute(statement)


def downgrade() -> None:
    conn = op.get_bind()
    owner = conn.execute(
        sa.text(
            "SELECT tableowner FROM pg_tables "
            "WHERE schemaname = 'public' AND tablename = 'report_exports'"
        )
    ).scalar_one_or_none()
    current = conn.execute(sa.text("SELECT current_user")).scalar_one()
    if owner is not None and owner != current:
        raise RuntimeError(
            f"downgrade of the report exports must run as the table owner ({owner}), "
            f"not {current}"
        )
    # The rows are the register of every export (numbers, data_sha256 of the files the
    # audit entries point at): never dropped silently (like audit_log, migration 0001).
    allow_loss = context.get_x_argument(as_dictionary=True).get("allow_audit_data_loss") == "yes"
    has_rows = conn.execute(sa.text("SELECT EXISTS (SELECT 1 FROM report_exports)")).scalar_one()
    if has_rows and not allow_loss:
        raise RuntimeError(
            "report_exports is not empty: dropping it destroys the register of exports. "
            "Back it up first and re-run with `-x allow_audit_data_loss=yes` if this is "
            "intended."
        )
    op.drop_table("report_exports")
    op.drop_table("report_number_sequences")
    op.execute("DROP FUNCTION report_number_sequences_guard()")
    op.execute("DROP FUNCTION report_exports_guard()")
