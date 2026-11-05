"""Authentication event state (ADR 0010): login de-duplication and failure aggregation.

Mirrors migration ``0005``; grants exist only in the migration. Neither table holds
company data (no ``company_id``, no RLS — like ``users``, ADR 0008 §3) and neither holds
tokens or secrets: a login is identified by the SHA-256 of the token's public claims.

These are OPERATIONAL tables, not evidence: the evidence is the audit log. Rows are
purged once they are no longer needed (``app.services.auth_events.purge_expired``).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CHAR,
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.audit import HEX64
from app.models.base import Base
from app.models.mixins import TimestampMixin, UuidPkMixin


class AuthLogin(UuidPkMixin, TimestampMixin, Base):
    """One row per distinct bearer token seen: its first use is the ``login`` event."""

    __tablename__ = "auth_logins"
    __table_args__ = (
        UniqueConstraint("token_fingerprint"),
        CheckConstraint(f"token_fingerprint ~ '{HEX64}'", name="token_fingerprint_hex"),
        Index("ix_auth_logins_expires_at", "expires_at"),
    )

    token_fingerprint: Mapped[str] = mapped_column(CHAR(64))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    issuer: Mapped[str] = mapped_column(Text)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AuthFailureWindow(UuidPkMixin, TimestampMixin, Base):
    """Failed authentications of one bucket (reason, client network, user) in one window."""

    __tablename__ = "auth_failure_windows"
    __table_args__ = (
        # A window is (start, length): instances with different window lengths never mix.
        UniqueConstraint("window_start", "window_seconds", "bucket"),
        CheckConstraint("window_seconds > 0", name="window_seconds_positive"),
        CheckConstraint("count >= 1", name="count_positive"),
        CheckConstraint("logged_count >= 0 AND logged_count <= count", name="logged_count_range"),
        # Closed windows with failures not yet in the audit log (flush).
        Index(
            "ix_auth_failure_windows_pending",
            "window_start",
            postgresql_where=text("logged_count < count"),
        ),
    )

    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    window_seconds: Mapped[int] = mapped_column(Integer)
    bucket: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    client_network: Mapped[str | None] = mapped_column(Text)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    count: Mapped[int] = mapped_column(BigInteger)
    # ``count`` at the moment of the last audit entry of this bucket/window.
    logged_count: Mapped[int] = mapped_column(BigInteger)
    first_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


# --------------------------------------------------------------------------- local accounts
# Migration 0010, ADR 0018. Secrets are stored only as hashes: the argon2id password hash
# and the SHA-256 of each refresh token. None of these columns ever leaves the API or
# enters the audit log (``app.services.audit`` rejects secret-like keys).


class UserCredential(UuidPkMixin, TimestampMixin, Base):
    """The password of a local account (one row per user; no row = no password login)."""

    __tablename__ = "user_credentials"
    __table_args__ = (
        UniqueConstraint("user_id"),
        CheckConstraint("password_hash LIKE '$argon2id$%'", name="password_hash_argon2id"),
        CheckConstraint("failed_attempts >= 0", name="failed_attempts_non_negative"),
        CheckConstraint(
            "must_change_password = (temp_password_expires_at IS NOT NULL)",
            name="temp_password_expiry",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    password_hash: Mapped[str] = mapped_column(Text)
    password_changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    must_change_password: Mapped[bool] = mapped_column(Boolean)
    # Consecutive failed passwords since the last success / lockout / reset.
    failed_attempts: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Deadline of a temporary password (set exactly when must_change_password; migration
    # 0011, ADR 0018 §12 p. 4).
    temp_password_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuthSession(UuidPkMixin, TimestampMixin, Base):
    """A login session (``sid`` of the access tokens); revoked, never deleted while valid."""

    __tablename__ = "auth_sessions"
    __table_args__ = (
        Index("ix_auth_sessions_user_id", "user_id"),
        Index("ix_auth_sessions_expires_at", "expires_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))  # absolute limit
    refreshed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoke_reason: Mapped[str | None] = mapped_column(Text)


class AuthRefreshToken(UuidPkMixin, TimestampMixin, Base):
    """One refresh token of a session (SHA-256 only); single use - rotated on refresh."""

    __tablename__ = "auth_refresh_tokens"
    __table_args__ = (
        UniqueConstraint("token_hash"),
        CheckConstraint(f"token_hash ~ '{HEX64}'", name="token_hash_hex"),
        Index("ix_auth_refresh_tokens_session_id", "session_id"),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("auth_sessions.id", ondelete="CASCADE")
    )
    token_hash: Mapped[str] = mapped_column(CHAR(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))  # idle limit
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
