"""Local accounts with passwords: user_credentials, auth_sessions, auth_refresh_tokens.

CLAUDE.md 4.1 (users), 6.5; decisions in docs/decisions/0018-local-password-accounts.md.

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-03

- ``users``: the e-mail is the login of a local account, unique regardless of case
  (``uq_users_email_lower``). The upgrade refuses to run when existing users share an
  e-mail (case-insensitively) and lists them - the duplicates must be resolved by hand.
- ``user_credentials``: the argon2id hash of the password (never the password), when it
  was set, ``must_change_password``, the counter of consecutive failed passwords and
  ``locked_until`` (lockout). One row per user; no row = the user cannot log in with a
  password.
- ``auth_sessions``: one row per login (the ``sid`` of the access tokens), with the
  absolute expiry and the revocation (logout, password change/reset, deactivation,
  refresh-token reuse). A revoked session cannot be revived (trigger).
- ``auth_refresh_tokens``: SHA-256 of every refresh token (never the token), single use:
  ``rotated_at`` is set when it is exchanged and cannot be cleared (trigger); presenting a
  rotated token again revokes the whole session (reuse detection).

No ``company_id`` (no company data), hence no RLS (as ``users``, ADR 0008 §3).

``app_rw`` (minimal):
- ``user_credentials``: SELECT, INSERT, UPDATE of the password/lockout columns only - no
  DELETE (accounts are deactivated), no UPDATE of ``user_id``;
- ``auth_sessions``: SELECT, INSERT, UPDATE of ``refreshed_at``, ``revoked_at``,
  ``revoke_reason``, ``updated_at``; DELETE (purge of long-expired sessions);
- ``auth_refresh_tokens``: SELECT, INSERT, UPDATE of ``rotated_at``, ``updated_at``; DELETE
  (purge, also by cascade).

Runs as ``app_owner``; ``downgrade`` refuses to run as any other role, and refuses to drop
existing passwords unless explicitly told so (``-x allow_credential_loss=yes``).
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import context, op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

HEX64 = "^[0-9a-f]{64}$"

GUARDS = [
    """
    CREATE FUNCTION auth_sessions_guard() RETURNS trigger
    LANGUAGE plpgsql AS $$
    BEGIN
        IF NEW.id <> OLD.id OR NEW.user_id <> OLD.user_id
           OR NEW.expires_at <> OLD.expires_at OR NEW.created_at <> OLD.created_at THEN
            RAISE EXCEPTION 'auth_sessions: identity and expiry of a session are immutable'
                USING ERRCODE = '23001';
        END IF;
        IF OLD.revoked_at IS NOT NULL AND (
            NEW.revoked_at IS DISTINCT FROM OLD.revoked_at
            OR NEW.revoke_reason IS DISTINCT FROM OLD.revoke_reason
            OR NEW.refreshed_at IS DISTINCT FROM OLD.refreshed_at
        ) THEN
            RAISE EXCEPTION 'auth_sessions: a revoked session cannot be changed'
                USING ERRCODE = '23001';
        END IF;
        RETURN NEW;
    END
    $$
    """,
    "REVOKE ALL ON FUNCTION auth_sessions_guard() FROM PUBLIC, app_rw",
    """
    CREATE TRIGGER auth_sessions_guard BEFORE UPDATE ON auth_sessions
    FOR EACH ROW EXECUTE FUNCTION auth_sessions_guard()
    """,
    """
    CREATE FUNCTION auth_refresh_tokens_guard() RETURNS trigger
    LANGUAGE plpgsql AS $$
    BEGIN
        IF NEW.id <> OLD.id OR NEW.session_id <> OLD.session_id
           OR NEW.token_hash <> OLD.token_hash OR NEW.expires_at <> OLD.expires_at
           OR NEW.created_at <> OLD.created_at THEN
            RAISE EXCEPTION 'auth_refresh_tokens: a refresh token is immutable'
                USING ERRCODE = '23001';
        END IF;
        IF OLD.rotated_at IS NOT NULL AND NEW.rotated_at IS DISTINCT FROM OLD.rotated_at THEN
            RAISE EXCEPTION 'auth_refresh_tokens: a rotated refresh token stays rotated'
                USING ERRCODE = '23001';
        END IF;
        RETURN NEW;
    END
    $$
    """,
    "REVOKE ALL ON FUNCTION auth_refresh_tokens_guard() FROM PUBLIC, app_rw",
    """
    CREATE TRIGGER auth_refresh_tokens_guard BEFORE UPDATE ON auth_refresh_tokens
    FOR EACH ROW EXECUTE FUNCTION auth_refresh_tokens_guard()
    """,
]

GRANTS = [
    # Default privileges (roles.psql) gave app_rw SELECT/INSERT/UPDATE/DELETE.
    "REVOKE ALL ON user_credentials FROM app_rw",
    "GRANT SELECT, INSERT ON user_credentials TO app_rw",
    "GRANT UPDATE (password_hash, password_changed_at, must_change_password, "
    "failed_attempts, locked_until, updated_at) ON user_credentials TO app_rw",
    "REVOKE ALL ON auth_sessions FROM app_rw",
    "GRANT SELECT, INSERT, DELETE ON auth_sessions TO app_rw",
    "GRANT UPDATE (refreshed_at, revoked_at, revoke_reason, updated_at) "
    "ON auth_sessions TO app_rw",
    "REVOKE ALL ON auth_refresh_tokens FROM app_rw",
    "GRANT SELECT, INSERT, DELETE ON auth_refresh_tokens TO app_rw",
    "GRANT UPDATE (rotated_at, updated_at) ON auth_refresh_tokens TO app_rw",
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
    conn = op.get_bind()
    duplicates = conn.execute(
        sa.text(
            "SELECT lower(email) AS email, count(*) AS n FROM users "
            "GROUP BY lower(email) HAVING count(*) > 1 ORDER BY 1"
        )
    ).all()
    if duplicates:
        listed = ", ".join(f"{row.email!r} ({row.n}x)" for row in duplicates)
        raise RuntimeError(
            "users share an e-mail address (case-insensitively), which is the login of a "
            f"local account: {listed}. Give each user a distinct e-mail, then re-run."
        )
    op.create_index(
        "uq_users_email_lower", "users", [sa.text("lower(email)")], unique=True
    )

    op.create_table(
        "user_credentials",
        _uuid_pk(),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("must_change_password", sa.Boolean(), nullable=False),
        sa.Column("failed_attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_credentials")),
        sa.UniqueConstraint("user_id", name=op.f("uq_user_credentials_user_id")),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_user_credentials_user_id_users")
        ),
        sa.CheckConstraint(
            "password_hash LIKE '$argon2id$%'",
            name=op.f("ck_user_credentials_password_hash_argon2id"),
        ),
        sa.CheckConstraint(
            "failed_attempts >= 0", name=op.f("ck_user_credentials_failed_attempts_non_negative")
        ),
    )

    op.create_table(
        "auth_sessions",
        _uuid_pk(),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("refreshed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoke_reason", sa.Text(), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auth_sessions")),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_auth_sessions_user_id_users")
        ),
    )
    op.create_index("ix_auth_sessions_user_id", "auth_sessions", ["user_id"])
    op.create_index("ix_auth_sessions_expires_at", "auth_sessions", ["expires_at"])

    op.create_table(
        "auth_refresh_tokens",
        _uuid_pk(),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.CHAR(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auth_refresh_tokens")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_auth_refresh_tokens_token_hash")),
        sa.CheckConstraint(
            f"token_hash ~ '{HEX64}'", name=op.f("ck_auth_refresh_tokens_token_hash_hex")
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["auth_sessions.id"],
            name=op.f("fk_auth_refresh_tokens_session_id_auth_sessions"),
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        "ix_auth_refresh_tokens_session_id", "auth_refresh_tokens", ["session_id"]
    )

    for statement in [*GUARDS, *GRANTS]:
        op.execute(statement)


def downgrade() -> None:
    conn = op.get_bind()
    owner = conn.execute(
        sa.text(
            "SELECT tableowner FROM pg_tables "
            "WHERE schemaname = 'public' AND tablename = 'user_credentials'"
        )
    ).scalar_one_or_none()
    current = conn.execute(sa.text("SELECT current_user")).scalar_one()
    if owner is not None and owner != current:
        raise RuntimeError(
            f"downgrade of the local accounts must run as the table owner ({owner}), "
            f"not {current}"
        )
    # Dropping the table removes every password: nobody could log in afterwards.
    allow_loss = context.get_x_argument(as_dictionary=True).get("allow_credential_loss") == "yes"
    has_rows = conn.execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM user_credentials)")
    ).scalar_one()
    if has_rows and not allow_loss:
        raise RuntimeError(
            "user_credentials is not empty: dropping it removes every password of the local "
            "accounts. Re-run with `-x allow_credential_loss=yes` if this is intended."
        )
    op.drop_table("auth_refresh_tokens")
    op.drop_table("auth_sessions")
    op.drop_table("user_credentials")
    op.execute("DROP FUNCTION auth_refresh_tokens_guard()")
    op.execute("DROP FUNCTION auth_sessions_guard()")
    op.drop_index("uq_users_email_lower", table_name="users")
