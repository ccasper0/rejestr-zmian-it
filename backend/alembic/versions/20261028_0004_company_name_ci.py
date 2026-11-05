"""Company names unique regardless of letter case.

The application already rejects "ALFA" when "Alfa" exists, but only with a pre-check that
two concurrent requests can both pass. A unique index on ``lower(name)`` closes the race
(the service maps its violation to 409 ``company.name_taken``). It replaces the
case-sensitive ``uq_companies_name`` constraint, which it makes redundant.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-28

Runs as ``app_owner``; ``downgrade`` refuses to run as any other role.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    duplicates = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT lower(name) FROM companies GROUP BY lower(name) HAVING count(*) > 1 "
                "ORDER BY 1"
            )
        )
        .scalars()
        .all()
    )
    if duplicates:
        raise RuntimeError(
            "companies with names differing only in letter case must be renamed first: "
            + ", ".join(duplicates)
        )
    op.create_index(
        "uq_companies_name_lower", "companies", [sa.text("lower(name)")], unique=True
    )
    op.drop_constraint("uq_companies_name", "companies", type_="unique")


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
            f"downgrade of company name index must run as the table owner ({owner}), "
            f"not {current}"
        )
    op.create_unique_constraint("uq_companies_name", "companies", ["name"])
    op.drop_index("uq_companies_name_lower", table_name="companies")
