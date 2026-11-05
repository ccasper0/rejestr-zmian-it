"""Identity: users, companies, company_memberships; prefix immutability; grants.

CLAUDE.md 4.1, 5, 7; decisions in docs/decisions/0007-auth-and-admin-scope.md.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-28

Runs as ``app_owner``; ``downgrade`` refuses to run as any other role.

Row-Level Security policies for ``companies`` and ``company_memberships`` are added by
migration 0003 (ADR 0008); ``users`` deliberately has none.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

PREFIX_PATTERN = "^[A-Z]{2,8}$"

PREFIX_GUARD = [
    r"""-- companies.prefix is part of every change number (CHG-{PREFIX}-...): immutable
-- after creation, for every role (CLAUDE.md 4.1). The service rejects it first with
-- company.prefix_immutable; this is the defence in depth.
CREATE FUNCTION companies_prefix_immutable() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NEW.prefix IS DISTINCT FROM OLD.prefix THEN
        RAISE EXCEPTION 'companies.prefix is immutable (% -> %)', OLD.prefix, NEW.prefix
            USING ERRCODE = 'restrict_violation';
    END IF;
    RETURN NEW;
END
$$
    """,
    "REVOKE ALL ON FUNCTION companies_prefix_immutable() FROM PUBLIC, app_rw",
    """
    CREATE TRIGGER companies_prefix_immutable
        BEFORE UPDATE OF prefix ON companies
        FOR EACH ROW EXECUTE FUNCTION companies_prefix_immutable()
    """,
]

GRANTS = [
    # Default privileges (roles.psql) gave app_rw SELECT/INSERT/UPDATE/DELETE.
    # Companies are archived, never deleted; users are deactivated, never deleted
    # (audit entries reference them by id). Memberships keep DELETE: revoking a role
    # removes the row and is recorded in the audit log (role_revoke).
    "REVOKE ALL ON companies FROM app_rw",
    "GRANT SELECT, INSERT, UPDATE ON companies TO app_rw",
    "REVOKE ALL ON users FROM app_rw",
    "GRANT SELECT, INSERT, UPDATE ON users TO app_rw",
    "REVOKE ALL ON company_memberships FROM app_rw",
    "GRANT SELECT, INSERT, UPDATE, DELETE ON company_memberships TO app_rw",
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


def _uuid_pk() -> sa.Column[object]:
    return sa.Column(
        "id",
        postgresql.UUID(as_uuid=True),
        server_default=sa.text("gen_random_uuid()"),
        nullable=False,
    )


def upgrade() -> None:
    op.create_table(
        "users",
        _uuid_pk(),
        sa.Column("external_id", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("is_app_admin", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("external_id", name=op.f("uq_users_external_id")),
    )

    op.create_table(
        "companies",
        _uuid_pk(),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("tax_id", sa.Text(), nullable=True),
        sa.Column("prefix", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default="active", nullable=False),
        sa.Column("is_ksc_entity", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("default_approver_id", postgresql.UUID(as_uuid=True), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_companies")),
        sa.UniqueConstraint("name", name=op.f("uq_companies_name")),
        sa.UniqueConstraint("prefix", name=op.f("uq_companies_prefix")),
        sa.CheckConstraint(f"prefix ~ '{PREFIX_PATTERN}'", name=op.f("ck_companies_prefix_format")),
        sa.CheckConstraint(
            "status IN ('active', 'archived')", name=op.f("ck_companies_status_values")
        ),
        sa.ForeignKeyConstraint(
            ["default_approver_id"],
            ["users.id"],
            name=op.f("fk_companies_default_approver_id_users"),
        ),
    )

    op.create_table(
        "company_memberships",
        _uuid_pk(),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("company_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_company_memberships")),
        sa.UniqueConstraint(
            "user_id",
            "company_id",
            "role",
            name=op.f("uq_company_memberships_user_id_company_id_role"),
        ),
        sa.CheckConstraint(
            "role IN ('editor', 'approver', 'auditor', 'viewer')",
            name=op.f("ck_company_memberships_role_values"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_company_memberships_user_id_users")
        ),
        sa.ForeignKeyConstraint(
            ["company_id"],
            ["companies.id"],
            name=op.f("fk_company_memberships_company_id_companies"),
        ),
    )
    # (user_id, ...) lookups use the unique constraint; per-company member lists use this.
    op.create_index("ix_company_memberships_company_id", "company_memberships", ["company_id"])

    for statement in [*PREFIX_GUARD, *GRANTS]:
        op.execute(statement)


def downgrade() -> None:
    conn = op.get_bind()
    owner = conn.execute(
        sa.text(
            "SELECT tableowner FROM pg_tables "
            "WHERE schemaname = 'public' AND tablename = 'companies'"
        )
    ).scalar_one_or_none()
    current = conn.execute(sa.text("SELECT current_user")).scalar_one()
    if owner is not None and owner != current:
        raise RuntimeError(
            f"downgrade of the identity tables must run as the table owner ({owner}), not {current}"
        )
    op.drop_index("ix_company_memberships_company_id", table_name="company_memberships")
    op.drop_table("company_memberships")
    op.drop_table("companies")  # drops the trigger with it
    op.drop_table("users")
    op.execute("DROP FUNCTION companies_prefix_immutable()")
