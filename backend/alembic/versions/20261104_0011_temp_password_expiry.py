"""Expiry of temporary passwords: user_credentials.temp_password_expires_at.

ADR 0018 §12 p. 4 (decision of the owner 2026-11-04).

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-04

A temporary password (issued by ``POST /users``, ``POST /users/{id}/reset-password`` or
``create-admin --generate-password``) is valid until ``temp_password_expires_at`` =
issue time + ``TEMP_PASSWORD_TTL_HOURS`` (default 168 h). The deadline is stored when the
password is issued (not derived from the current setting), so a later change of the
variable does not move the deadlines of passwords already handed out, and the admin views
and the audit diff show the exact date.

- set exactly when ``must_change_password`` is true (CHECK
  ``ck_user_credentials_temp_password_expiry``); cleared by the password change;
- existing temporary passwords get ``password_changed_at + 168 hours`` (the default);
- ``app_rw`` may UPDATE the column (like ``locked_until``).

Runs as ``app_owner``. ``downgrade`` drops the column (the deadlines are lost; the
temporary passwords stay valid without a limit, as before this revision).
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

DEFAULT_TTL_HOURS = 168
CHECK = "ck_user_credentials_temp_password_expiry"


def upgrade() -> None:
    op.add_column(
        "user_credentials",
        sa.Column("temp_password_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        "UPDATE user_credentials "
        f"SET temp_password_expires_at = password_changed_at + interval '{DEFAULT_TTL_HOURS} hours' "
        "WHERE must_change_password"
    )
    op.create_check_constraint(
        op.f(CHECK),
        "user_credentials",
        "must_change_password = (temp_password_expires_at IS NOT NULL)",
    )
    op.execute("GRANT UPDATE (temp_password_expires_at) ON user_credentials TO app_rw")


def downgrade() -> None:
    conn = op.get_bind()
    owner = conn.execute(
        sa.text(
            "SELECT tableowner FROM pg_tables "
            "WHERE schemaname = 'public' AND tablename = 'user_credentials'"
        )
    ).scalar_one()
    current = conn.execute(sa.text("SELECT current_user")).scalar_one()
    if owner != current:
        raise RuntimeError(
            f"downgrade of the temporary password expiry must run as the table owner "
            f"({owner}), not {current}"
        )
    op.execute("REVOKE UPDATE (temp_password_expires_at) ON user_credentials FROM app_rw")
    op.drop_constraint(op.f(CHECK), "user_credentials", type_="check")
    op.drop_column("user_credentials", "temp_password_expires_at")
