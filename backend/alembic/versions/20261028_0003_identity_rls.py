"""Row-Level Security for companies and company_memberships.

CLAUDE.md 5, 7; decisions in docs/decisions/0008-row-level-security.md (proposal in
ADR 0007 §4).

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-28

Session variables (set transaction-locally by ``app.db``; names are a contract):
``app.user_id``, ``app.company_ids``, ``app.admin_scope``, ``app.audit_global_read``.

Rules (``app_rw`` only; the owner ``app_owner`` is deliberately not FORCEd, ADR 0008):

- ``companies``: SELECT own companies (``app.company_ids``) or the explicit admin path;
  INSERT only on the admin path; UPDATE only on the admin path AND for a company that is
  in the transaction scope (the admin path widens the scope with the target company).
- ``company_memberships``: SELECT rows of the scoped companies, the caller's own rows
  (``app.user_id`` - memberships are read BEFORE the company scope exists) or the admin
  path; INSERT/UPDATE/DELETE only on the admin path AND within the scoped companies.
- ``users``: no ``company_id``, no RLS (ADR 0008 §3).

Runs as ``app_owner``; ``downgrade`` refuses to run as any other role.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

HELPERS = [
    # The authenticated user of the transaction. Missing / empty (a pooled connection after
    # a transaction-local set_config reverts to '') = NULL, so comparisons are never true.
    """
    CREATE FUNCTION app_user_id() RETURNS uuid
        LANGUAGE sql STABLE PARALLEL SAFE
        AS $$ SELECT NULLIF(current_setting('app.user_id', true), '')::uuid $$
    """,
    # Explicit administrative path (app admin: companies, dictionaries, role assignment).
    # Anything but exactly 'on' (missing, '', 'off') = off.
    """
    CREATE FUNCTION app_admin_scope() RETURNS boolean
        LANGUAGE sql STABLE PARALLEL SAFE
        AS $$ SELECT COALESCE(current_setting('app.admin_scope', true), '') = 'on' $$
    """,
]

POLICIES = [
    "ALTER TABLE companies ENABLE ROW LEVEL SECURITY",
    """
    CREATE POLICY companies_select ON companies FOR SELECT TO app_rw
        USING (id = ANY (app_company_ids()) OR app_admin_scope())
    """,
    # A new company cannot be in the scope yet: the admin path alone is required.
    """
    CREATE POLICY companies_insert ON companies FOR INSERT TO app_rw
        WITH CHECK (app_admin_scope())
    """,
    # Note: SELECT ... FOR UPDATE/SHARE on companies is subject to this USING clause too,
    # so only the admin path may lock company rows (FK checks are not affected).
    """
    CREATE POLICY companies_update ON companies FOR UPDATE TO app_rw
        USING (app_admin_scope() AND id = ANY (app_company_ids()))
        WITH CHECK (app_admin_scope() AND id = ANY (app_company_ids()))
    """,
    # No DELETE policy: app_rw has no DELETE privilege on companies (archive only).
    "ALTER TABLE company_memberships ENABLE ROW LEVEL SECURITY",
    """
    CREATE POLICY company_memberships_select ON company_memberships FOR SELECT TO app_rw
        USING (company_id = ANY (app_company_ids())
               OR user_id = app_user_id()
               OR app_admin_scope())
    """,
    """
    CREATE POLICY company_memberships_insert ON company_memberships FOR INSERT TO app_rw
        WITH CHECK (app_admin_scope() AND company_id = ANY (app_company_ids()))
    """,
    """
    CREATE POLICY company_memberships_update ON company_memberships FOR UPDATE TO app_rw
        USING (app_admin_scope() AND company_id = ANY (app_company_ids()))
        WITH CHECK (app_admin_scope() AND company_id = ANY (app_company_ids()))
    """,
    """
    CREATE POLICY company_memberships_delete ON company_memberships FOR DELETE TO app_rw
        USING (app_admin_scope() AND company_id = ANY (app_company_ids()))
    """,
]


def upgrade() -> None:
    for statement in [*HELPERS, *POLICIES]:
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
            f"downgrade of identity RLS must run as the table owner ({owner}), not {current}"
        )
    for table, commands in (
        ("company_memberships", ("select", "insert", "update", "delete")),
        ("companies", ("select", "insert", "update")),
    ):
        for command in commands:
            op.execute(f"DROP POLICY {table}_{command} ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    op.execute("DROP FUNCTION app_admin_scope()")
    op.execute("DROP FUNCTION app_user_id()")
