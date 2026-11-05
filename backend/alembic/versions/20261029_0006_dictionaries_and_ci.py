"""Dictionaries and CI inventory: change_categories, ci_types, company_categories,
configuration_items.

CLAUDE.md 4.1, 5, 7; decisions in docs/decisions/0011-dictionaries-and-ci-inventory.md.

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-29

- ``change_categories``: global, two levels. A trigger rejects a subcategory of a
  subcategory; ``code`` and ``parent_id`` are immutable (trigger, 23001), so the depth
  check cannot be bypassed by moving rows.
- ``ci_types``: global; ``code`` immutable.
- ``company_categories``: categories available in a company + approver override.
- ``configuration_items``: per company; identifier unique in the company regardless of
  letter case; ``company_id`` immutable.

Grants (``app_rw``): nothing is deleted (deactivation) except ``company_categories`` rows -
a PUT that withdraws a category deletes its row and the removal is in the audit log
(like role revocation, ADR 0007 §7). No TRUNCATE.

Row-Level Security (``app_rw`` only, no FORCE - ADR 0008):

- dictionaries (no ``company_id``): SELECT for everybody; INSERT/UPDATE only on the
  explicit admin path (``app_admin_scope()``) - defence in depth for "writes: app admin";
- ``company_categories``: SELECT within the scope; writes only on the admin path AND
  within the scope (as ``company_memberships``);
- ``configuration_items``: SELECT/INSERT/UPDATE within the scope (editors and approvers
  write their companies' inventory; the admin path widens the scope with one company).

Runs as ``app_owner``; ``downgrade`` refuses to run as any other role.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

CATEGORY_CODE_CHECK = "code ~ '^[A-Z][A-Z0-9]*(-[A-Z0-9]+)*$' AND length(code) BETWEEN 2 AND 32"
CI_TYPE_CODE_CHECK = "code ~ '^[a-z][a-z0-9_]{1,31}$'"
RISK_CHECK = "default_risk IN ('low', 'medium', 'high')"

TABLES = ("configuration_items", "company_categories", "ci_types", "change_categories")

GUARDS = [
    r"""-- Two levels only, and the shape of the tree never changes: code and parent_id are
-- immutable for every role (the service rejects it first with 422).
CREATE FUNCTION change_categories_guard() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        IF NEW.code IS DISTINCT FROM OLD.code THEN
            RAISE EXCEPTION 'change_categories.code is immutable (% -> %)', OLD.code, NEW.code
                USING ERRCODE = 'restrict_violation';
        END IF;
        IF NEW.parent_id IS DISTINCT FROM OLD.parent_id THEN
            RAISE EXCEPTION 'change_categories.parent_id is immutable'
                USING ERRCODE = 'restrict_violation';
        END IF;
        RETURN NEW;
    END IF;
    IF NEW.parent_id IS NOT NULL AND EXISTS (
        SELECT 1 FROM change_categories WHERE id = NEW.parent_id AND parent_id IS NOT NULL
    ) THEN
        RAISE EXCEPTION 'change categories have two levels: % is a subcategory', NEW.parent_id
            USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END
$$
    """,
    "REVOKE ALL ON FUNCTION change_categories_guard() FROM PUBLIC, app_rw",
    """
    CREATE TRIGGER change_categories_guard
        BEFORE INSERT OR UPDATE ON change_categories
        FOR EACH ROW EXECUTE FUNCTION change_categories_guard()
    """,
    r"""CREATE FUNCTION ci_types_code_immutable() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NEW.code IS DISTINCT FROM OLD.code THEN
        RAISE EXCEPTION 'ci_types.code is immutable (% -> %)', OLD.code, NEW.code
            USING ERRCODE = 'restrict_violation';
    END IF;
    RETURN NEW;
END
$$
    """,
    "REVOKE ALL ON FUNCTION ci_types_code_immutable() FROM PUBLIC, app_rw",
    """
    CREATE TRIGGER ci_types_code_immutable
        BEFORE UPDATE OF code ON ci_types
        FOR EACH ROW EXECUTE FUNCTION ci_types_code_immutable()
    """,
    r"""-- A tenant row never moves to another company (RLS WITH CHECK alone would allow a
-- move between two companies of the same transaction scope).
CREATE FUNCTION company_id_immutable() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NEW.company_id IS DISTINCT FROM OLD.company_id THEN
        RAISE EXCEPTION '%.company_id is immutable', TG_TABLE_NAME
            USING ERRCODE = 'restrict_violation';
    END IF;
    RETURN NEW;
END
$$
    """,
    "REVOKE ALL ON FUNCTION company_id_immutable() FROM PUBLIC, app_rw",
    """
    CREATE TRIGGER configuration_items_company_id_immutable
        BEFORE UPDATE OF company_id ON configuration_items
        FOR EACH ROW EXECUTE FUNCTION company_id_immutable()
    """,
    """
    CREATE TRIGGER company_categories_company_id_immutable
        BEFORE UPDATE OF company_id ON company_categories
        FOR EACH ROW EXECUTE FUNCTION company_id_immutable()
    """,
]

GRANTS = [
    # Default privileges (roles.psql) gave app_rw SELECT/INSERT/UPDATE/DELETE.
    "REVOKE ALL ON change_categories FROM app_rw",
    "GRANT SELECT, INSERT, UPDATE ON change_categories TO app_rw",
    "REVOKE ALL ON ci_types FROM app_rw",
    "GRANT SELECT, INSERT, UPDATE ON ci_types TO app_rw",
    "REVOKE ALL ON company_categories FROM app_rw",
    "GRANT SELECT, INSERT, UPDATE, DELETE ON company_categories TO app_rw",
    "REVOKE ALL ON configuration_items FROM app_rw",
    "GRANT SELECT, INSERT, UPDATE ON configuration_items TO app_rw",
]

POLICIES = [
    # ---- global dictionaries: read by all, written only on the admin path
    "ALTER TABLE change_categories ENABLE ROW LEVEL SECURITY",
    """
    CREATE POLICY change_categories_select ON change_categories FOR SELECT TO app_rw
        USING (true)
    """,
    """
    CREATE POLICY change_categories_insert ON change_categories FOR INSERT TO app_rw
        WITH CHECK (app_admin_scope())
    """,
    """
    CREATE POLICY change_categories_update ON change_categories FOR UPDATE TO app_rw
        USING (app_admin_scope()) WITH CHECK (app_admin_scope())
    """,
    "ALTER TABLE ci_types ENABLE ROW LEVEL SECURITY",
    "CREATE POLICY ci_types_select ON ci_types FOR SELECT TO app_rw USING (true)",
    """
    CREATE POLICY ci_types_insert ON ci_types FOR INSERT TO app_rw
        WITH CHECK (app_admin_scope())
    """,
    """
    CREATE POLICY ci_types_update ON ci_types FOR UPDATE TO app_rw
        USING (app_admin_scope()) WITH CHECK (app_admin_scope())
    """,
    # ---- company_categories: like company_memberships (written by the app admin only)
    "ALTER TABLE company_categories ENABLE ROW LEVEL SECURITY",
    """
    CREATE POLICY company_categories_select ON company_categories FOR SELECT TO app_rw
        USING (company_id = ANY (app_company_ids()))
    """,
    """
    CREATE POLICY company_categories_insert ON company_categories FOR INSERT TO app_rw
        WITH CHECK (app_admin_scope() AND company_id = ANY (app_company_ids()))
    """,
    """
    CREATE POLICY company_categories_update ON company_categories FOR UPDATE TO app_rw
        USING (app_admin_scope() AND company_id = ANY (app_company_ids()))
        WITH CHECK (app_admin_scope() AND company_id = ANY (app_company_ids()))
    """,
    """
    CREATE POLICY company_categories_delete ON company_categories FOR DELETE TO app_rw
        USING (app_admin_scope() AND company_id = ANY (app_company_ids()))
    """,
    # ---- configuration_items: the company scope (members; admin path widens it)
    "ALTER TABLE configuration_items ENABLE ROW LEVEL SECURITY",
    """
    CREATE POLICY configuration_items_select ON configuration_items FOR SELECT TO app_rw
        USING (company_id = ANY (app_company_ids()))
    """,
    """
    CREATE POLICY configuration_items_insert ON configuration_items FOR INSERT TO app_rw
        WITH CHECK (company_id = ANY (app_company_ids()))
    """,
    """
    CREATE POLICY configuration_items_update ON configuration_items FOR UPDATE TO app_rw
        USING (company_id = ANY (app_company_ids()))
        WITH CHECK (company_id = ANY (app_company_ids()))
    """,
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


def _is_active() -> sa.Column[object]:
    return sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False)


def upgrade() -> None:
    op.create_table(
        "change_categories",
        _uuid_pk(),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        _uuid("parent_id", nullable=True),
        sa.Column("requires_approval", sa.Boolean(), nullable=False),
        sa.Column("default_risk", sa.Text(), nullable=False),
        _is_active(),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_change_categories")),
        sa.UniqueConstraint("code", name=op.f("uq_change_categories_code")),
        sa.CheckConstraint(CATEGORY_CODE_CHECK, name=op.f("ck_change_categories_code_format")),
        sa.CheckConstraint(RISK_CHECK, name=op.f("ck_change_categories_default_risk_values")),
        sa.CheckConstraint(
            "parent_id IS NULL OR parent_id <> id",
            name=op.f("ck_change_categories_parent_not_self"),
        ),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["change_categories.id"],
            name=op.f("fk_change_categories_parent_id_change_categories"),
        ),
    )
    op.create_index("ix_change_categories_parent_id", "change_categories", ["parent_id"])

    op.create_table(
        "ci_types",
        _uuid_pk(),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        _is_active(),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ci_types")),
        sa.UniqueConstraint("code", name=op.f("uq_ci_types_code")),
        sa.CheckConstraint(CI_TYPE_CODE_CHECK, name=op.f("ck_ci_types_code_format")),
    )

    op.create_table(
        "company_categories",
        _uuid_pk(),
        _uuid("company_id"),
        _uuid("category_id"),
        _uuid("approver_override_id", nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_company_categories")),
        sa.UniqueConstraint(
            "company_id", "category_id", name=op.f("uq_company_categories_company_id_category_id")
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name=op.f("fk_company_categories_company_id_companies"),
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["change_categories.id"],
            name=op.f("fk_company_categories_category_id_change_categories"),
        ),
        sa.ForeignKeyConstraint(
            ["approver_override_id"],
            ["users.id"],
            name=op.f("fk_company_categories_approver_override_id_users"),
        ),
    )

    op.create_table(
        "configuration_items",
        _uuid_pk(),
        _uuid("company_id"),
        _uuid("ci_type_id"),
        sa.Column("identifier", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        _uuid("owner_user_id", nullable=True),
        _is_active(),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_configuration_items")),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name=op.f("fk_configuration_items_company_id_companies"),
        ),
        sa.ForeignKeyConstraint(
            ["ci_type_id"],
            ["ci_types.id"],
            name=op.f("fk_configuration_items_ci_type_id_ci_types"),
        ),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            name=op.f("fk_configuration_items_owner_user_id_users"),
        ),
    )
    op.create_index(
        "uq_configuration_items_company_id_identifier_lower",
        "configuration_items",
        ["company_id", sa.text("lower(identifier)")],
        unique=True,
    )
    op.create_index("ix_configuration_items_ci_type_id", "configuration_items", ["ci_type_id"])

    for statement in [*GUARDS, *GRANTS, *POLICIES]:
        op.execute(statement)


def downgrade() -> None:
    conn = op.get_bind()
    owner = conn.execute(
        sa.text(
            "SELECT tableowner FROM pg_tables "
            "WHERE schemaname = 'public' AND tablename = 'configuration_items'"
        )
    ).scalar_one_or_none()
    current = conn.execute(sa.text("SELECT current_user")).scalar_one()
    if owner is not None and owner != current:
        raise RuntimeError(
            f"downgrade of the dictionaries and CI inventory must run as the table owner "
            f"({owner}), not {current}"
        )
    # Business data only; its history stays in audit_log (dropping the tables drops their
    # policies and triggers too).
    for table in TABLES:
        op.drop_table(table)
    op.execute("DROP FUNCTION company_id_immutable()")
    op.execute("DROP FUNCTION ci_types_code_immutable()")
    op.execute("DROP FUNCTION change_categories_guard()")
