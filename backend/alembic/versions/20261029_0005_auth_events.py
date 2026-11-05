"""Authentication event state: auth_logins, auth_failure_windows.

CLAUDE.md 6.5; decisions in docs/decisions/0010-auth-events.md.

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-29

- ``auth_logins``: one row per distinct bearer token (SHA-256 of its public claims, never
  the token). The INSERT that creates the row is what makes a request a ``login``: with
  ``ON CONFLICT DO NOTHING`` exactly one request (of any API process) writes the entry.
- ``auth_failure_windows``: failed authentications counted per (time window, bucket), so
  a flood of anonymous failures produces a bounded number of audit entries while every
  failure is still counted and summarized in the audit log.

No ``company_id`` (no company data), hence no RLS (as ``users``, ADR 0008 §3).
``app_rw``: SELECT, INSERT, DELETE on ``auth_logins`` (rows are immutable, purged after
the token expired); SELECT, INSERT, UPDATE, DELETE on ``auth_failure_windows``.

Runs as ``app_owner``; ``downgrade`` refuses to run as any other role.
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

HEX64 = "^[0-9a-f]{64}$"

GRANTS = [
    # Default privileges (roles.psql) gave app_rw SELECT/INSERT/UPDATE/DELETE.
    "REVOKE ALL ON auth_logins FROM app_rw",
    "GRANT SELECT, INSERT, DELETE ON auth_logins TO app_rw",
    "REVOKE ALL ON auth_failure_windows FROM app_rw",
    "GRANT SELECT, INSERT, UPDATE, DELETE ON auth_failure_windows TO app_rw",
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
        "auth_logins",
        _uuid_pk(),
        sa.Column("token_fingerprint", sa.CHAR(64), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("issuer", sa.Text(), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auth_logins")),
        sa.UniqueConstraint("token_fingerprint", name=op.f("uq_auth_logins_token_fingerprint")),
        sa.CheckConstraint(
            f"token_fingerprint ~ '{HEX64}'", name=op.f("ck_auth_logins_token_fingerprint_hex")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_auth_logins_user_id_users")
        ),
    )
    op.create_index("ix_auth_logins_expires_at", "auth_logins", ["expires_at"])

    op.create_table(
        "auth_failure_windows",
        _uuid_pk(),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_seconds", sa.Integer(), nullable=False),
        sa.Column("bucket", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("client_network", sa.Text(), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("count", sa.BigInteger(), nullable=False),
        sa.Column("logged_count", sa.BigInteger(), nullable=False),
        sa.Column("first_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_at", sa.DateTime(timezone=True), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auth_failure_windows")),
        # A window is (start, length): instances configured with different
        # AUTH_FAILURE_WINDOW_SECONDS never mix their counters.
        sa.UniqueConstraint(
            "window_start",
            "window_seconds",
            "bucket",
            name=op.f("uq_auth_failure_windows_window_start_window_seconds_bucket"),
        ),
        sa.CheckConstraint(
            "window_seconds > 0", name=op.f("ck_auth_failure_windows_window_seconds_positive")
        ),
        sa.CheckConstraint("count >= 1", name=op.f("ck_auth_failure_windows_count_positive")),
        sa.CheckConstraint(
            "logged_count >= 0 AND logged_count <= count",
            name=op.f("ck_auth_failure_windows_logged_count_range"),
        ),
    )
    op.create_index(
        "ix_auth_failure_windows_pending",
        "auth_failure_windows",
        ["window_start"],
        postgresql_where=sa.text("logged_count < count"),
    )

    for statement in GRANTS:
        op.execute(statement)


def downgrade() -> None:
    conn = op.get_bind()
    owner = conn.execute(
        sa.text(
            "SELECT tableowner FROM pg_tables "
            "WHERE schemaname = 'public' AND tablename = 'auth_logins'"
        )
    ).scalar_one_or_none()
    current = conn.execute(sa.text("SELECT current_user")).scalar_one()
    if owner is not None and owner != current:
        raise RuntimeError(
            f"downgrade of the auth event tables must run as the table owner ({owner}), "
            f"not {current}"
        )
    # Operational state only (the evidence is in audit_log): dropping it loses no audit data.
    op.drop_index("ix_auth_failure_windows_pending", table_name="auth_failure_windows")
    op.drop_table("auth_failure_windows")
    op.drop_index("ix_auth_logins_expires_at", table_name="auth_logins")
    op.drop_table("auth_logins")
