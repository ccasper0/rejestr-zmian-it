"""Local accounts with passwords: login, sessions, refresh, logout, password change
(``AUTH_MODE=local``, ADR 0018).

Every event goes to the GLOBAL audit chain, never with a password, a token or a hash of
one (``app.services.audit.record`` rejects such keys):

- ``auth/login`` (actor: the user) - successful login, with the new ``session_id``;
- ``auth/login_failed`` - aggregated per window and source exactly like the bearer-token
  failures (ADR 0010 §3), reasons ``unknown_email``, ``invalid_password``,
  ``no_password``, ``account_locked``, ``user_inactive``, ``rate_limited``,
  ``invalid_refresh_token``, ``invalid_current_password``, ``temporary_password_expired``
  (the right temporary password after its deadline - not a guess, not counted towards the
  lockout);
- ``user/lockout`` (actor ``system``) - the account was locked after
  ``AUTH_LOCKOUT_THRESHOLD`` consecutive failed passwords;
- ``auth/token_refresh`` (actor: the user) - the tokens of a session were renewed;
- ``auth/session_revoke`` (actor ``system``) - a rotated refresh token was presented again
  (reuse detection), or the refresh token of a session opened with a temporary password
  was presented after the password's deadline: the whole session is revoked;
- ``auth/logout`` (actor: the user);
- ``user/password_change`` (actor: the user) - every session of the user is revoked and a
  new one is issued.

Failed attempts must survive the failing request, so login and refresh run in their own
transactions (``run_in_separate_transaction``, main pool - the endpoints hold no other
connection). Lock order inside them: the credential / session rows, then the failure
bucket (``record_login_failure``), then the global chain head - never the reverse.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.passwords import (
    hash_password_async,
    needs_rehash,
    verify_password_async,
)
from app.config import Settings
from app.db import Database, run_in_separate_transaction
from app.domain.audit import Actor, AuditAction, EntityType, make_diff
from app.models import AuthRefreshToken, AuthSession, User, UserCredential
from app.services import audit, auth_events
from app.services.auth_events import PASSWORD_GUESS_REASONS, FailureReason

REFRESH_TOKEN_BYTES = 32


class RevokeReason(StrEnum):
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"  # noqa: S105 - a reason code, not a secret
    PASSWORD_RESET = "password_reset"  # noqa: S105
    LOCKOUT = "lockout"
    DEACTIVATED = "deactivated"
    REFRESH_TOKEN_REUSE = "refresh_token_reuse"  # noqa: S105
    TEMPORARY_PASSWORD_EXPIRED = "temporary_password_expired"  # noqa: S105


@dataclass(frozen=True, slots=True)
class AuthPolicy:
    """Session and lockout limits (``Settings``, ADR 0018 §4-6)."""

    access_token_seconds: int
    refresh_idle: timedelta
    session_max: timedelta
    lockout_threshold: int
    lockout_duration: timedelta
    max_failures_per_network: int
    failure_window_seconds: int
    failure_max_buckets: int
    failure_max_immediate_entries: int
    # Validity of a temporary password (TEMP_PASSWORD_TTL_HOURS, ADR 0018 §12 p. 4).
    temp_password_ttl: timedelta = timedelta(hours=168)

    @classmethod
    def from_settings(cls, settings: Settings) -> AuthPolicy:
        return cls(
            access_token_seconds=settings.auth_access_token_minutes * 60,
            refresh_idle=timedelta(minutes=settings.auth_refresh_idle_minutes),
            session_max=timedelta(hours=settings.auth_session_max_hours),
            lockout_threshold=settings.auth_lockout_threshold,
            lockout_duration=timedelta(minutes=settings.auth_lockout_minutes),
            max_failures_per_network=settings.auth_login_max_failures_per_network,
            failure_window_seconds=settings.auth_failure_window_seconds,
            failure_max_buckets=settings.auth_failure_max_buckets,
            failure_max_immediate_entries=settings.auth_failure_max_immediate_entries,
            temp_password_ttl=timedelta(hours=settings.temp_password_ttl_hours),
        )


@dataclass(frozen=True, slots=True)
class IssuedSession:
    """A session with a fresh refresh token (the access token is signed by the caller)."""

    user: User
    session_id: UUID
    refresh_token: str
    refresh_expires_at: datetime
    session_expires_at: datetime
    must_change_password: bool


class AuthFailure(StrEnum):
    INVALID_CREDENTIALS = "invalid_credentials"
    RATE_LIMITED = "rate_limited"
    INVALID_REFRESH_TOKEN = "invalid_refresh_token"  # noqa: S105
    # The password (or the session's refresh token) was right, but the temporary password
    # is past its deadline (ADR 0018 §12 p. 4) - only the admin's reset helps.
    TEMPORARY_PASSWORD_EXPIRED = "temporary_password_expired"  # noqa: S105


@dataclass(frozen=True, slots=True)
class AuthResult:
    issued: IssuedSession | None = None
    failure: AuthFailure | None = None
    retry_after: int | None = None


@dataclass(frozen=True, slots=True)
class RequestInfo:
    """What the failure entries record about the request (never a body)."""

    method: str | None = None
    path: str | None = None


@dataclass(frozen=True, slots=True)
class SessionState:
    must_change_password: bool


# --------------------------------------------------------------------------- helpers


def normalize_email(email: str) -> str:
    return email.strip()


def refresh_token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def system_actor() -> Actor:
    return Actor.system()


def user_actor(user: User) -> Actor:
    return auth_events.actor_for_user(user)


async def db_now(session: AsyncSession) -> datetime:
    value: datetime = (await session.execute(select(func.clock_timestamp()))).scalar_one()
    return value


def temporary_password_expired(credential: UserCredential | None, now: datetime) -> bool:
    """A temporary password past its deadline (``temp_password_expires_at``)."""
    return (
        credential is not None
        and credential.must_change_password
        and credential.temp_password_expires_at is not None
        and credential.temp_password_expires_at <= now
    )


async def get_user_by_email(session: AsyncSession, email: str) -> User | None:
    result = await session.execute(
        select(User).where(func.lower(User.email) == normalize_email(email).lower())
    )
    return result.scalar_one_or_none()


async def get_credential(
    session: AsyncSession, user_id: UUID, *, for_update: bool = False
) -> UserCredential | None:
    stmt = select(UserCredential).where(UserCredential.user_id == user_id)
    if for_update:
        stmt = stmt.with_for_update().execution_options(populate_existing=True)
    return (await session.execute(stmt)).scalar_one_or_none()


async def _record_failure(
    session: AsyncSession,
    policy: AuthPolicy,
    request: RequestInfo,
    reason: FailureReason,
    *,
    actor: Actor | None = None,
    user_id: UUID | None = None,
) -> None:
    await auth_events.record_login_failure(
        session,
        reason=reason,
        window_seconds=policy.failure_window_seconds,
        max_buckets=policy.failure_max_buckets,
        max_immediate_entries=policy.failure_max_immediate_entries,
        actor=actor,
        user_id=user_id,
        method=request.method,
        path=request.path,
    )


async def revoke_user_sessions(
    session: AsyncSession, user_id: UUID, reason: RevokeReason
) -> list[UUID]:
    """Revoke every live session of the user; returns their ids (for the audit entry)."""
    now = await db_now(session)
    rows = await session.execute(
        update(AuthSession)
        .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=now, revoke_reason=reason.value, updated_at=now)
        .returning(AuthSession.id)
    )
    return sorted(rows.scalars().all())


async def _new_refresh_token(
    session: AsyncSession, auth_session: AuthSession, policy: AuthPolicy, now: datetime
) -> tuple[str, datetime]:
    token = secrets.token_urlsafe(REFRESH_TOKEN_BYTES)
    expires_at = min(now + policy.refresh_idle, auth_session.expires_at)
    session.add(
        AuthRefreshToken(
            session_id=auth_session.id,
            token_hash=refresh_token_hash(token),
            expires_at=expires_at,
        )
    )
    await session.flush()
    return token, expires_at


async def create_session(
    session: AsyncSession, user: User, credential: UserCredential, policy: AuthPolicy
) -> IssuedSession:
    now = await db_now(session)
    expires_at = now + policy.session_max
    if credential.must_change_password and credential.temp_password_expires_at is not None:
        # A session opened with a temporary password cannot outlive it (ADR 0018 §12).
        expires_at = min(expires_at, credential.temp_password_expires_at)
    auth_session = AuthSession(user_id=user.id, expires_at=expires_at)
    session.add(auth_session)
    await session.flush()
    token, refresh_expires_at = await _new_refresh_token(session, auth_session, policy, now)
    return IssuedSession(
        user=user,
        session_id=auth_session.id,
        refresh_token=token,
        refresh_expires_at=refresh_expires_at,
        session_expires_at=auth_session.expires_at,
        must_change_password=credential.must_change_password,
    )


async def _lock_out(
    session: AsyncSession,
    user: User,
    credential: UserCredential,
    policy: AuthPolicy,
    now: datetime,
    *,
    trigger: str,
    revoke_sessions: bool,
) -> None:
    """Lock the account (the failure entry was already written: bucket before head)."""
    before = {"locked_until": credential.locked_until}
    credential.locked_until = now + policy.lockout_duration
    credential.failed_attempts = 0
    revoked: list[UUID] = []
    if revoke_sessions:
        revoked = await revoke_user_sessions(session, user.id, RevokeReason.LOCKOUT)
    await session.flush()
    await audit.record(
        session,
        company_id=None,
        actor=system_actor(),
        entity_type=EntityType.USER,
        entity_id=user.id,
        action=AuditAction.LOCKOUT,
        diff=make_diff(before, {"locked_until": credential.locked_until}),
        context={
            "trigger": trigger,
            "threshold": policy.lockout_threshold,
            "lockout_minutes": int(policy.lockout_duration.total_seconds() // 60),
            "sessions_revoked": [str(s) for s in revoked],
        },
    )


def _is_locked(credential: UserCredential, now: datetime) -> bool:
    return credential.locked_until is not None and credential.locked_until > now


# --------------------------------------------------------------------------- login


async def login(
    db: Database,
    *,
    email: str,
    password: str,
    policy: AuthPolicy,
    request: RequestInfo,
) -> AuthResult:
    """Check the e-mail and password; on success open a session (``login`` entry).

    Every failure looks the same to the client (``INVALID_CREDENTIALS``) and takes the same
    time: an unknown e-mail is verified against a dummy argon2id hash, a locked account
    is verified too (and the result ignored). Only the per-network limit answers
    differently (``RATE_LIMITED``), which says nothing about any account.
    """

    async def precheck(session: AsyncSession) -> tuple[bool, int, str | None]:
        if policy.max_failures_per_network > 0:
            failures = await auth_events.failures_from_network(
                session,
                window_seconds=policy.failure_window_seconds,
                reasons=PASSWORD_GUESS_REASONS,
            )
            if failures >= policy.max_failures_per_network:
                await _record_failure(session, policy, request, FailureReason.RATE_LIMITED)
                retry = await auth_events.seconds_to_window_end(
                    session, policy.failure_window_seconds
                )
                return True, retry, None
        user = await get_user_by_email(session, email)
        credential = None if user is None else await get_credential(session, user.id)
        return False, 0, None if credential is None else credential.password_hash

    limited, retry_after, encoded = await run_in_separate_transaction(db, precheck, main_pool=True)
    if limited:
        return AuthResult(failure=AuthFailure.RATE_LIMITED, retry_after=retry_after)

    # The expensive part runs without a connection or a lock.
    password_ok = await verify_password_async(encoded, password)
    rehash = (
        await hash_password_async(password)
        if password_ok and encoded is not None and needs_rehash(encoded)
        else None
    )

    async def apply(session: AsyncSession) -> AuthResult:
        user = await get_user_by_email(session, email)
        if user is None:
            # No e-mail in the entry: users type passwords into the e-mail field.
            await _record_failure(session, policy, request, FailureReason.UNKNOWN_EMAIL)
            return AuthResult(failure=AuthFailure.INVALID_CREDENTIALS)
        credential = await get_credential(session, user.id, for_update=True)
        if credential is None:
            await _record_failure(
                session, policy, request, FailureReason.NO_PASSWORD, user_id=user.id
            )
            return AuthResult(failure=AuthFailure.INVALID_CREDENTIALS)
        now = await db_now(session)
        if not user.is_active:
            await _record_failure(
                session, policy, request, FailureReason.USER_INACTIVE, user_id=user.id
            )
            return AuthResult(failure=AuthFailure.INVALID_CREDENTIALS)
        if _is_locked(credential, now):
            # Not counted again: the lock is not extended by further attempts.
            await _record_failure(
                session, policy, request, FailureReason.ACCOUNT_LOCKED, user_id=user.id
            )
            return AuthResult(failure=AuthFailure.INVALID_CREDENTIALS)
        if not password_ok or credential.password_hash != encoded:
            # (A hash changed since the check above, i.e. a concurrent password change,
            # is a failure too, but not the user's fault: not counted.)
            if credential.password_hash == encoded:
                credential.failed_attempts += 1
            await session.flush()
            await _record_failure(
                session, policy, request, FailureReason.INVALID_PASSWORD, user_id=user.id
            )
            if credential.failed_attempts >= policy.lockout_threshold:
                await _lock_out(
                    session,
                    user,
                    credential,
                    policy,
                    now,
                    trigger="login",
                    revoke_sessions=False,
                )
            return AuthResult(failure=AuthFailure.INVALID_CREDENTIALS)
        if temporary_password_expired(credential, now):
            # Checked only AFTER the password: without it the answer is the generic one,
            # so this reveals nothing to someone who does not know the password. Not a
            # guess: neither the lockout counter nor the per-network limit counts it.
            await _record_failure(
                session,
                policy,
                request,
                FailureReason.TEMPORARY_PASSWORD_EXPIRED,
                user_id=user.id,
            )
            return AuthResult(failure=AuthFailure.TEMPORARY_PASSWORD_EXPIRED)

        credential.failed_attempts = 0
        credential.locked_until = None
        if rehash is not None:
            credential.password_hash = rehash
        issued = await create_session(session, user, credential, policy)
        await audit.record(
            session,
            company_id=None,
            actor=user_actor(user),
            entity_type=EntityType.AUTH,
            entity_id=user.id,
            action=AuditAction.LOGIN,
            context={
                "method": "password",
                "session_id": issued.session_id,
                "session_expires_at": issued.session_expires_at,
                "must_change_password": issued.must_change_password,
                "password_rehashed": rehash is not None,
            },
        )
        return AuthResult(issued=issued)

    return await run_in_separate_transaction(db, apply, main_pool=True)


# --------------------------------------------------------------------------- refresh


async def refresh(
    db: Database, *, refresh_token: str, policy: AuthPolicy, request: RequestInfo
) -> AuthResult:
    """Exchange a refresh token for a new one (rotation) - ``token_refresh`` entry.

    A token that was already exchanged and is presented again means two parties hold it
    (theft, or a client that did not serialize its refreshes): the whole session is
    revoked (``session_revoke``, ``refresh_token_reuse``) and both must log in again.
    """
    token_hash = refresh_token_hash(refresh_token)

    async def apply(session: AsyncSession) -> AuthResult:
        row = (
            await session.execute(
                select(AuthRefreshToken, AuthSession)
                .join(AuthSession, AuthSession.id == AuthRefreshToken.session_id)
                .where(AuthRefreshToken.token_hash == token_hash)
                .with_for_update()
            )
        ).one_or_none()
        if row is None:
            await _record_failure(session, policy, request, FailureReason.INVALID_REFRESH_TOKEN)
            return AuthResult(failure=AuthFailure.INVALID_REFRESH_TOKEN)
        token, auth_session = row
        now = await db_now(session)
        user = await session.get(User, auth_session.user_id)
        if user is None:  # pragma: no cover - foreign key
            raise RuntimeError("session without user")

        if token.rotated_at is not None:
            await _record_failure(
                session, policy, request, FailureReason.INVALID_REFRESH_TOKEN, user_id=user.id
            )
            if auth_session.revoked_at is None:
                auth_session.revoked_at = now
                auth_session.revoke_reason = RevokeReason.REFRESH_TOKEN_REUSE.value
                await session.flush()
                await audit.record(
                    session,
                    company_id=None,
                    actor=system_actor(),
                    entity_type=EntityType.AUTH,
                    entity_id=user.id,
                    action=AuditAction.SESSION_REVOKE,
                    context={
                        "session_id": auth_session.id,
                        "reason": RevokeReason.REFRESH_TOKEN_REUSE.value,
                        "token_rotated_at": token.rotated_at,
                    },
                )
            return AuthResult(failure=AuthFailure.INVALID_REFRESH_TOKEN)

        if (
            auth_session.revoked_at is not None
            or auth_session.expires_at <= now
            or token.expires_at <= now
        ):
            await _record_failure(
                session, policy, request, FailureReason.INVALID_REFRESH_TOKEN, user_id=user.id
            )
            return AuthResult(failure=AuthFailure.INVALID_REFRESH_TOKEN)
        if not user.is_active:
            await _record_failure(
                session, policy, request, FailureReason.USER_INACTIVE, user_id=user.id
            )
            return AuthResult(failure=AuthFailure.INVALID_REFRESH_TOKEN)

        credential = await get_credential(session, user.id)
        if credential is not None and temporary_password_expired(credential, now):
            # The temporary password was not changed in time: the session ends with it
            # (sessions opened with it are capped at the deadline anyway; this covers
            # sessions opened before the deadline was introduced or shortened).
            await _record_failure(
                session,
                policy,
                request,
                FailureReason.TEMPORARY_PASSWORD_EXPIRED,
                user_id=user.id,
            )
            auth_session.revoked_at = now
            auth_session.revoke_reason = RevokeReason.TEMPORARY_PASSWORD_EXPIRED.value
            await session.flush()
            await audit.record(
                session,
                company_id=None,
                actor=system_actor(),
                entity_type=EntityType.AUTH,
                entity_id=user.id,
                action=AuditAction.SESSION_REVOKE,
                context={
                    "session_id": auth_session.id,
                    "reason": RevokeReason.TEMPORARY_PASSWORD_EXPIRED.value,
                    "temp_password_expires_at": credential.temp_password_expires_at,
                },
            )
            return AuthResult(failure=AuthFailure.TEMPORARY_PASSWORD_EXPIRED)
        token.rotated_at = now
        auth_session.refreshed_at = now
        new_token, refresh_expires_at = await _new_refresh_token(session, auth_session, policy, now)
        await audit.record(
            session,
            company_id=None,
            actor=user_actor(user),
            entity_type=EntityType.AUTH,
            entity_id=user.id,
            action=AuditAction.TOKEN_REFRESH,
            context={"session_id": auth_session.id},
        )
        return AuthResult(
            issued=IssuedSession(
                user=user,
                session_id=auth_session.id,
                refresh_token=new_token,
                refresh_expires_at=refresh_expires_at,
                session_expires_at=auth_session.expires_at,
                must_change_password=bool(credential and credential.must_change_password),
            )
        )

    return await run_in_separate_transaction(db, apply, main_pool=True)


# --------------------------------------------------------------------------- per request


async def check_session(
    session: AsyncSession, *, user_id: UUID, session_id: UUID
) -> SessionState | None:
    """The live session of an access token (``None``: revoked, expired or foreign).

    Runs on every authenticated request of a local account (identity transaction).
    """
    row = (
        await session.execute(
            select(AuthSession.user_id, UserCredential.must_change_password)
            .outerjoin(UserCredential, UserCredential.user_id == AuthSession.user_id)
            .where(
                AuthSession.id == session_id,
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > func.clock_timestamp(),
                # A temporary password past its deadline ends the session at once.
                or_(
                    UserCredential.temp_password_expires_at.is_(None),
                    UserCredential.temp_password_expires_at > func.clock_timestamp(),
                ),
            )
        )
    ).one_or_none()
    if row is None or row.user_id != user_id:
        return None
    return SessionState(must_change_password=bool(row.must_change_password))


# --------------------------------------------------------------------------- logout


async def logout(session: AsyncSession, *, actor: Actor, user_id: UUID, session_id: UUID) -> bool:
    """Revoke the caller's session (``logout`` entry); False if it was already gone."""
    now = await db_now(session)
    revoked = (
        await session.execute(
            update(AuthSession)
            .where(
                AuthSession.id == session_id,
                AuthSession.user_id == user_id,
                AuthSession.revoked_at.is_(None),
            )
            .values(revoked_at=now, revoke_reason=RevokeReason.LOGOUT.value, updated_at=now)
            .returning(AuthSession.id)
        )
    ).scalar_one_or_none()
    await audit.record(
        session,
        company_id=None,
        actor=actor,
        entity_type=EntityType.AUTH,
        entity_id=user_id,
        action=AuditAction.LOGOUT,
        context={"session_id": session_id, "already_revoked": revoked is None},
    )
    return revoked is not None


# --------------------------------------------------------------------------- password change


class PasswordChangeOutcome(StrEnum):
    CHANGED = "changed"
    WRONG_CURRENT = "wrong_current"
    LOCKED = "locked"
    NO_PASSWORD = "no_password"  # noqa: S105


async def record_wrong_current_password(
    db: Database,
    outer: AsyncSession,
    *,
    user: User,
    actor: Actor,
    policy: AuthPolicy,
    request: RequestInfo,
) -> None:
    """A wrong current password in ``POST /auth/password``: counted like a failed login,
    in its own transaction (the request fails). Reaching the threshold locks the account
    AND revokes every session - whoever holds this session is guessing the password."""

    async def apply(session: AsyncSession) -> None:
        credential = await get_credential(session, user.id, for_update=True)
        if credential is None:  # pragma: no cover - checked by the caller
            return
        now = await db_now(session)
        credential.failed_attempts += 1
        await session.flush()
        await _record_failure(
            session, policy, request, FailureReason.INVALID_CURRENT_PASSWORD, actor=actor
        )
        if credential.failed_attempts >= policy.lockout_threshold:
            await _lock_out(
                session,
                user,
                credential,
                policy,
                now,
                trigger="password_change",
                revoke_sessions=True,
            )

    await run_in_separate_transaction(db, apply, outer=outer)


async def change_password(
    session: AsyncSession,
    *,
    user: User,
    actor: Actor,
    new_password_hash: str,
    policy: AuthPolicy,
) -> IssuedSession:
    """Store the new hash, end every session and open a new one (``password_change``)."""
    credential = await get_credential(session, user.id, for_update=True)
    if credential is None:  # pragma: no cover - checked by the caller
        raise RuntimeError("user has no password")
    now = await db_now(session)
    before = {
        "password_changed_at": credential.password_changed_at,
        "must_change_password": credential.must_change_password,
        "temp_password_expires_at": credential.temp_password_expires_at,
    }
    credential.password_hash = new_password_hash
    credential.password_changed_at = now
    credential.must_change_password = False
    credential.temp_password_expires_at = None
    credential.failed_attempts = 0
    credential.locked_until = None
    revoked = await revoke_user_sessions(session, user.id, RevokeReason.PASSWORD_CHANGE)
    issued = await create_session(session, user, credential, policy)
    await audit.record(
        session,
        company_id=None,
        actor=actor,
        entity_type=EntityType.USER,
        entity_id=user.id,
        action=AuditAction.PASSWORD_CHANGE,
        diff=make_diff(
            before,
            {
                "password_changed_at": credential.password_changed_at,
                "must_change_password": credential.must_change_password,
                "temp_password_expires_at": credential.temp_password_expires_at,
            },
        ),
        context={
            "sessions_revoked": [str(s) for s in revoked],
            "new_session_id": issued.session_id,
        },
    )
    return issued
