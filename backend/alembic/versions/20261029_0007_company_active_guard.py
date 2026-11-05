"""Writes to the CI inventory of an archived company are rejected by the database.

CLAUDE.md 4.1 (companies are archived); decisions in
docs/decisions/0011-dictionaries-and-ci-inventory.md §5.

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-29

The service checks ``companies.status`` first, but without a lock: an archive committed
concurrently (``archive_company`` locks the company row ``FOR UPDATE``) could slip
between the check and the INSERT. The trigger function ``company_must_be_active()``
locks the company row ``FOR SHARE`` and reads its status:

- archive first: the trigger waits for the archive to commit and (READ COMMITTED) then
  sees the NEW row version - ``archived`` - and raises 23001;
- CI write first: the archive waits until the CI transaction ends, so the CI is created
  while the company is still active.

It is ``SECURITY DEFINER`` (owner ``app_owner``) because ``SELECT ... FOR SHARE`` on
``companies`` is subject to its UPDATE policy, which only the admin path passes (ADR
0008); ``app_rw`` has no EXECUTE on it (the RLS guard forbids definer functions callable
by ``app_rw``; triggers fire regardless). Reusable: stage 4 attaches it to ``changes``.

Runs as ``app_owner``; ``downgrade`` refuses to run as any other role.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

FUNCTION = r"""
CREATE FUNCTION company_must_be_active() RETURNS trigger
    LANGUAGE plpgsql
    SECURITY DEFINER
    SET search_path = pg_catalog, public
    AS $$
DECLARE
    current_status text;
BEGIN
    SELECT status INTO current_status FROM companies WHERE id = NEW.company_id FOR SHARE;
    IF current_status = 'archived' THEN
        RAISE EXCEPTION 'company_archived: company % is archived, % cannot be modified',
            NEW.company_id, TG_TABLE_NAME
            USING ERRCODE = 'restrict_violation', CONSTRAINT = 'company_archived';
    END IF;
    RETURN NEW;
END
$$
"""


def upgrade() -> None:
    op.execute(FUNCTION)
    op.execute("REVOKE ALL ON FUNCTION company_must_be_active() FROM PUBLIC, app_rw")
    op.execute(
        """
        CREATE TRIGGER configuration_items_company_active
            BEFORE INSERT OR UPDATE ON configuration_items
            FOR EACH ROW EXECUTE FUNCTION company_must_be_active()
        """
    )


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
            f"downgrade of the company guard must run as the table owner ({owner}), "
            f"not {current}"
        )
    op.execute("DROP TRIGGER configuration_items_company_active ON configuration_items")
    op.execute("DROP FUNCTION company_must_be_active()")
