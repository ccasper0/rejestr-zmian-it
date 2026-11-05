"""Users: lookup, local accounts managed by the app admin, admin listing (ADR 0018).

Every modification writes an audit entry to the GLOBAL chain in the same transaction
(entity ``user``). Users are never deleted (``app_rw`` has no DELETE), only deactivated.
Passwords and their hashes never enter an entry: the diff carries only the audited
profile fields and the password STATE (``must_change_password``, ``password_changed_at``,
``locked_until``, ``temp_password_expires_at``).

Accounts are created by the app admin (``POST /users``) or by the CLI
(``python -m app.cli create-admin``); there is no self-registration and no just-in-time
provisioning (OIDC was dropped, ADR 0018 §1). The identity of a bearer token
(:func:`resolve_identity`) is looked up in its own short transaction
(``app.db.run_in_separate_transaction``, ADR 0007 §2).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.passwords import generate_temporary_password, hash_password_async
from app.auth.tokens import TokenClaims
from app.db import SEPARATE_TRANSACTION_INFO_KEY
from app.domain.audit import Actor, AuditAction, EntityType, make_diff
from app.domain.passwords import check_password
from app.errors import ProblemError
from app.models import User, UserCredential
from app.services import audit
from app.services.local_auth import (
    RevokeReason,
    db_now,
    get_credential,
    get_user_by_email,
    normalize_email,
    revoke_user_sessions,
)

AUDITED_FIELDS = ("external_id", "email", "display_name", "is_app_admin", "is_active")
CREDENTIAL_STATE_FIELDS = (
    "must_change_password",
    "password_changed_at",
    "failed_attempts",
    "locked_until",
    "temp_password_expires_at",
)
LOCAL_EXTERNAL_ID_PREFIX = "local:"
TEMPORARY_PASSWORD_ATTEMPTS = 5
# TEMP_PASSWORD_TTL_HOURS default (ADR 0018 §12 p. 4); callers pass the configured value.
DEFAULT_TEMP_PASSWORD_TTL = timedelta(hours=168)


def snapshot(user: User) -> dict[str, object]:
    return {name: getattr(user, name) for name in AUDITED_FIELDS}


def credential_state(credential: UserCredential | None) -> dict[str, object]:
    """The password STATE (never the hash) for diffs."""
    if credential is None:
        return {"has_password": False}
    return {
        "has_password": True,
        **{name: getattr(credential, name) for name in CREDENTIAL_STATE_FIELDS},
    }


def user_not_found() -> ProblemError:
    return ProblemError(status=404, code="user.not_found", detail="Nie znaleziono użytkownika.")


async def get_user(session: AsyncSession, user_id: UUID) -> User | None:
    return await session.get(User, user_id)


async def get_user_by_external_id(session: AsyncSession, external_id: str) -> User | None:
    result = await session.execute(select(User).where(User.external_id == external_id))
    return result.scalar_one_or_none()


def _email_taken() -> ProblemError:
    return ProblemError(
        status=409,
        code="user.email_taken",
        detail="Użytkownik o tym adresie e-mail już istnieje.",
    )


async def _ensure_email_free(session: AsyncSession, email: str) -> None:
    if await get_user_by_email(session, email) is not None:
        raise _email_taken()


async def _flush_new_user(session: AsyncSession) -> None:
    """Flush in a savepoint: a concurrent account with the same e-mail (inserted between
    :func:`_ensure_email_free` and this flush) becomes 409, not a 500."""
    try:
        async with session.begin_nested():
            await session.flush()
    except IntegrityError as exc:
        if "uq_users_email_lower" in str(exc.orig):
            raise _email_taken() from exc
        raise


async def create_user(
    session: AsyncSession,
    *,
    actor: Actor,
    external_id: str,
    email: str,
    display_name: str,
    is_app_admin: bool = False,
    is_active: bool = True,
    context: Mapping[str, object] | None = None,
) -> User:
    """A user without a password (seed users of the dev mode, tests)."""
    user = User(
        id=uuid4(),
        external_id=external_id,
        email=normalize_email(email),
        display_name=display_name,
        is_app_admin=is_app_admin,
        is_active=is_active,
    )
    session.add(user)
    await session.flush()
    await audit.record(
        session,
        company_id=None,
        actor=actor,
        entity_type=EntityType.USER,
        entity_id=user.id,
        action=AuditAction.CREATE,
        diff=make_diff({}, snapshot(user)),
        context=context,
    )
    return user


async def _temporary_password(email: str, display_name: str) -> tuple[str, str]:
    """A random temporary password accepted by the policy, and its hash."""
    for _ in range(TEMPORARY_PASSWORD_ATTEMPTS):
        password = generate_temporary_password()
        if check_password(password, email=email, display_name=display_name).ok:
            return password, await hash_password_async(password)
    raise RuntimeError("could not generate a temporary password")  # pragma: no cover


@dataclass(frozen=True, slots=True)
class AccountWithPassword:
    user: User
    credential: UserCredential
    temporary_password: str | None  # returned ONCE to the admin, never stored


async def create_local_account(
    session: AsyncSession,
    *,
    actor: Actor,
    email: str,
    display_name: str,
    is_app_admin: bool = False,
    password_hash: str | None = None,
    context: Mapping[str, object] | None = None,
    temp_password_ttl: timedelta = DEFAULT_TEMP_PASSWORD_TTL,
) -> AccountWithPassword:
    """A local account (``POST /users``, CLI ``create-admin``).

    Without ``password_hash`` a temporary password is generated and returned once; the
    user must change it at the first login (``must_change_password``). With
    ``password_hash`` (the CLI, the operator typed the password) the account is ready.
    A temporary password is valid for ``temp_password_ttl`` (``TEMP_PASSWORD_TTL_HOURS``).
    """
    email = normalize_email(email)
    await _ensure_email_free(session, email)
    temporary: str | None = None
    if password_hash is None:
        temporary, password_hash = await _temporary_password(email, display_name)
    user = User(
        id=uuid4(),
        external_id=f"{LOCAL_EXTERNAL_ID_PREFIX}{uuid4()}",
        email=email,
        display_name=display_name,
        is_app_admin=is_app_admin,
        is_active=True,
    )
    session.add(user)
    await _flush_new_user(session)
    now = await db_now(session)
    credential = UserCredential(
        user_id=user.id,
        password_hash=password_hash,
        password_changed_at=now,
        must_change_password=temporary is not None,
        temp_password_expires_at=None if temporary is None else now + temp_password_ttl,
        failed_attempts=0,
    )
    session.add(credential)
    await session.flush()
    await audit.record(
        session,
        company_id=None,
        actor=actor,
        entity_type=EntityType.USER,
        entity_id=user.id,
        action=AuditAction.CREATE,
        diff=make_diff({}, {**snapshot(user), **credential_state(credential)}),
        context={
            **(context or {}),
            "temporary_password_issued": temporary is not None,
        },
    )
    return AccountWithPassword(user, credential, temporary)


async def _lock_user(session: AsyncSession, user_id: UUID) -> User:
    user = (
        await session.execute(
            select(User)
            .where(User.id == user_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if user is None:
        raise user_not_found()
    return user


async def reset_password(
    session: AsyncSession,
    *,
    actor: Actor,
    user_id: UUID,
    temp_password_ttl: timedelta = DEFAULT_TEMP_PASSWORD_TTL,
) -> AccountWithPassword:
    """A new temporary password (returned once) valid for ``temp_password_ttl`` from now,
    ``must_change_password``, the lockout cleared and every session of the user revoked
    (``password_reset``)."""
    if actor.id == user_id:
        raise ProblemError(
            status=409,
            code="user.self_password_reset",
            detail="Własne hasło zmień w ustawieniach konta (podając obecne hasło).",
        )
    user = await _lock_user(session, user_id)
    temporary, password_hash = await _temporary_password(user.email, user.display_name)
    credential = await get_credential(session, user.id, for_update=True)
    before = credential_state(credential)
    now = await db_now(session)
    if credential is None:
        credential = UserCredential(
            user_id=user.id,
            password_hash=password_hash,
            password_changed_at=now,
            must_change_password=True,
            temp_password_expires_at=now + temp_password_ttl,
            failed_attempts=0,
        )
        session.add(credential)
    else:
        credential.password_hash = password_hash
        credential.password_changed_at = now
        credential.must_change_password = True
        credential.temp_password_expires_at = now + temp_password_ttl
        credential.failed_attempts = 0
        credential.locked_until = None
    revoked = await revoke_user_sessions(session, user.id, RevokeReason.PASSWORD_RESET)
    await session.flush()
    await audit.record(
        session,
        company_id=None,
        actor=actor,
        entity_type=EntityType.USER,
        entity_id=user.id,
        action=AuditAction.PASSWORD_RESET,
        diff=make_diff(before, credential_state(credential)),
        context={
            "sessions_revoked": [str(s) for s in revoked],
            "temporary_password_issued": True,
        },
    )
    return AccountWithPassword(user, credential, temporary)


async def _lock_admins_and(
    session: AsyncSession, user_id: UUID, *, admins_need_password: bool
) -> tuple[User, int]:
    """Lock every active app admin AND the target in ONE statement ordered by id (a
    single lock order for every caller: two admins demoting each other concurrently
    serialize instead of deadlocking). Returns the target and the number of OTHER
    active app admins; with ``admins_need_password`` (``AUTH_MODE=local``) only those
    who can sign in, i.e. have a ``user_credentials`` row (ADR 0018)."""
    rows = (
        (
            await session.execute(
                select(User)
                .where(
                    or_(
                        (User.is_app_admin.is_(True)) & (User.is_active.is_(True)),
                        User.id == user_id,
                    )
                )
                .order_by(User.id)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        )
        .scalars()
        .all()
    )
    target = next((u for u in rows if u.id == user_id), None)
    if target is None:
        raise user_not_found()
    others = [u.id for u in rows if u.id != user_id and u.is_app_admin and u.is_active]
    if admins_need_password and others:
        with_password = await credentials_by_user(session, others)
        others = [uid for uid in others if uid in with_password]
    return target, len(others)


async def update_user(
    session: AsyncSession,
    *,
    actor: Actor,
    user_id: UUID,
    display_name: str | None = None,
    is_active: bool | None = None,
    is_app_admin: bool | None = None,
    admins_need_password: bool = False,
) -> User:
    """``PATCH /users/{id}``: profile, (de)activation, the app admin flag.

    Deactivation revokes every session (``deactivate``). An admin cannot deactivate or
    demote themself, and the last active app admin cannot be deactivated or demoted.
    With ``admins_need_password`` (``AUTH_MODE=local``) an active admin without a
    password (cannot sign in) does not count as another admin.
    """
    removes_admin = is_active is False or is_app_admin is False
    if actor.id == user_id and removes_admin:
        raise ProblemError(
            status=409,
            code="user.cannot_modify_self",
            detail="Nie możesz dezaktywować swojego konta ani odebrać sobie roli administratora.",
        )
    if removes_admin:
        user, others = await _lock_admins_and(
            session, user_id, admins_need_password=admins_need_password
        )
    else:
        user, others = await _lock_user(session, user_id), 0
    if removes_admin and user.is_app_admin and user.is_active and others == 0:
        raise ProblemError(
            status=409,
            code="user.last_admin",
            detail="To ostatni aktywny administrator aplikacji - nie można go dezaktywować "
            "ani odebrać mu roli.",
        )
    before = snapshot(user)
    if display_name is not None:
        user.display_name = display_name
    if is_active is not None:
        user.is_active = is_active
    if is_app_admin is not None:
        user.is_app_admin = is_app_admin
    diff = make_diff(before, snapshot(user))
    if not diff:
        return user
    deactivated = before["is_active"] is True and user.is_active is False
    revoked: list[UUID] = []
    if deactivated:
        revoked = await revoke_user_sessions(session, user.id, RevokeReason.DEACTIVATED)
    await session.flush()
    context: dict[str, object] = {"source": "admin"}
    if deactivated:
        context["sessions_revoked"] = [str(s) for s in revoked]
    await audit.record(
        session,
        company_id=None,
        actor=actor,
        entity_type=EntityType.USER,
        entity_id=user.id,
        action=AuditAction.DEACTIVATE if deactivated else AuditAction.UPDATE,
        diff=diff,
        context=context,
    )
    await session.refresh(user)  # updated_at (set by the database)
    return user


async def resolve_identity(session: AsyncSession, claims: TokenClaims) -> User | None:
    """The user of a verified token (``None``: unknown subject).

    Must run in a session opened by ``app.db.run_in_separate_transaction`` (never inside
    a business transaction, ADR 0007 §2).
    """
    if not session.info.get(SEPARATE_TRANSACTION_INFO_KEY):
        raise RuntimeError(
            "resolve_identity() must run in its own transaction (run_in_separate_transaction)"
        )
    return await get_user_by_external_id(session, claims.subject)


async def list_users(
    session: AsyncSession, *, q: str | None, limit: int, offset: int
) -> tuple[list[User], int]:
    stmt = select(User)
    if q and q.strip():
        pattern = f"%{q.strip().replace('%', r'\%').replace('_', r'\_')}%"
        stmt = stmt.where(
            or_(
                User.display_name.ilike(pattern),
                User.email.ilike(pattern),
                User.external_id.ilike(pattern),
            )
        )
    total = (await session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = await session.execute(
        stmt.order_by(User.display_name, User.id).limit(limit).offset(offset)
    )
    return list(rows.scalars().all()), int(total)


async def credentials_by_user(
    session: AsyncSession, user_ids: list[UUID]
) -> dict[UUID, UserCredential]:
    """Password STATE of the users (for the admin views; the hash is never serialized)."""
    if not user_ids:
        return {}
    rows = await session.execute(select(UserCredential).where(UserCredential.user_id.in_(user_ids)))
    return {c.user_id: c for c in rows.scalars().all()}
