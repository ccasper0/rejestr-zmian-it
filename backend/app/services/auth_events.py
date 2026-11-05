"""Authentication / authorization events in the audit log (CLAUDE.md 6.5, ADR 0010).

All entries go to the GLOBAL chain (``entity_type = auth``). Every function here must run
in a session of its own (``app.db.run_in_separate_transaction``), committed independently
of the request: the request transaction is rolled back when it fails with 401/403/404,
and the event must survive that.

- ``login`` (:func:`register_login`): the FIRST request with a given bearer token. A token
  is identified by the SHA-256 of its public claims (:func:`token_fingerprint` — never the
  token itself); the unique row in ``auth_logins`` decides, across any number of API
  processes, which single request writes the entry.
- ``login_failed`` (:func:`record_login_failure`): counted per window and bucket
  (reason + client network [+ user]) in ``auth_failure_windows``; the 1st, 2nd, 4th, 8th,
  ... failure of a bucket in a window is written at once (``count_in_window``), and
  :func:`flush_closed_windows` writes the exact total of every closed window that has
  failures not covered by an entry yet. No failure is left out of the log; a flood
  produces O(log n) entries per bucket and window instead of n.
- ``access_denied`` (:func:`record_access_denied`): every 403, and every 404 for a company
  the user has no membership in, with ``context.target_company_id``. The actor is an
  authenticated user (accountable), so these are not aggregated.

Lock order inside these transactions: own failure bucket row, then (flush) other bucket
rows with ``SKIP LOCKED``, then the global chain head — never the reverse.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from ipaddress import IPv4Address, ip_address, ip_network
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.tokens import TokenClaims
from app.db import SEPARATE_TRANSACTION_INFO_KEY, apply_company_scope
from app.domain.audit import Actor, AuditAction, EntityType
from app.domain.canonical import canonical_json, sha256_hex
from app.models import AuthFailureWindow, AuthLogin, AuthSession, User
from app.request_context import get_client_info
from app.services import audit

logger = logging.getLogger(__name__)

# Public claims that identify one issued token (no signature, nothing secret).
FINGERPRINT_CLAIMS = ("iss", "sub", "aud", "iat", "nbf", "exp", "jti", "uti", "sid")
DETAIL_MAX_LENGTH = 200
PATH_MAX_LENGTH = 512
# Operational rows are kept this long after they stop being needed.
RETENTION = timedelta(days=1)
FLUSH_BATCH = 50
OPPORTUNISTIC_FLUSH = 5
IPV6_BUCKET_PREFIX = 64  # one customer / host usually gets a whole /64


class FailureReason(StrEnum):
    MISSING_TOKEN = "missing_token"  # noqa: S105 - a reason code, not a secret
    INVALID_TOKEN = "invalid_token"  # noqa: S105
    UNKNOWN_USER = "unknown_user"
    USER_INACTIVE = "user_inactive"
    # Local accounts (ADR 0018). The client always gets the same answer for the first
    # five (no account enumeration); the log tells them apart.
    UNKNOWN_EMAIL = "unknown_email"
    INVALID_PASSWORD = "invalid_password"  # noqa: S105
    NO_PASSWORD = "no_password"  # noqa: S105 - the account has no password set
    ACCOUNT_LOCKED = "account_locked"
    INVALID_CURRENT_PASSWORD = "invalid_current_password"  # noqa: S105 - POST /auth/password
    RATE_LIMITED = "rate_limited"  # too many failures from the client network (429)
    INVALID_REFRESH_TOKEN = "invalid_refresh_token"  # noqa: S105
    SESSION_INVALID = "session_invalid"  # access token of a revoked / expired session
    # The right temporary password (or refresh token) after the password's deadline
    # (ADR 0018 §12 p. 4): not a guess, not in PASSWORD_GUESS_REASONS.
    TEMPORARY_PASSWORD_EXPIRED = "temporary_password_expired"  # noqa: S105


# Failed logins of these reasons count towards the per-network limit of POST /auth/login
# (ADR 0018 §6): guessing passwords, whichever account the e-mail names.
PASSWORD_GUESS_REASONS = frozenset(
    {
        FailureReason.UNKNOWN_EMAIL,
        FailureReason.INVALID_PASSWORD,
        FailureReason.NO_PASSWORD,
        FailureReason.ACCOUNT_LOCKED,
    }
)


def _require_own_transaction(session: AsyncSession) -> None:
    if not session.info.get(SEPARATE_TRANSACTION_INFO_KEY):
        raise RuntimeError(
            "authentication events must be written in their own transaction "
            "(app.db.run_in_separate_transaction)"
        )


def actor_for_user(user: User) -> Actor:
    """Actor of an identified user before memberships are known: global roles only."""
    return Actor(
        id=user.id, display=user.display_name, roles=("app_admin",) if user.is_app_admin else ()
    )


def _clip(value: str | None, limit: int) -> str | None:
    return None if value is None else value[:limit]


# --------------------------------------------------------------------------- login


def _claim_value(value: Any) -> str | int:
    if isinstance(value, str | int) and not isinstance(value, bool):
        return value
    # Lists (aud), floats (NumericDate may be fractional) and anything else: a stable text.
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def token_fingerprint(claims: TokenClaims) -> str:
    """SHA-256 of the token's identifying public claims (never of the token itself).

    Two requests carry "the same token" when these claims are equal; a new token from the
    identity provider (refresh, re-login) has a new ``iat``/``exp``/``jti`` and is a new
    login. Nothing that could be presented as a credential is stored.
    """
    selected = {k: _claim_value(claims.raw[k]) for k in FINGERPRINT_CLAIMS if k in claims.raw}
    return sha256_hex(canonical_json(selected).encode("utf-8"))


def _numeric_date(value: Any) -> datetime | None:
    if isinstance(value, int | float) and not isinstance(value, bool):
        try:
            return datetime.fromtimestamp(int(value), tz=UTC)
        except (OverflowError, OSError, ValueError):
            return None
    return None


async def register_login(session: AsyncSession, *, user: User, claims: TokenClaims) -> bool:
    """Record ``login`` if this is the first request with this token; True if recorded.

    Cheap for every later request (one indexed SELECT). Concurrent first requests (any
    process): ``INSERT ... ON CONFLICT DO NOTHING`` lets exactly one of them insert the
    row and write the entry; the others wait for its commit and do nothing.
    """
    _require_own_transaction(session)
    fingerprint = token_fingerprint(claims)
    seen = await session.execute(
        select(AuthLogin.id).where(AuthLogin.token_fingerprint == fingerprint)
    )
    if seen.first() is not None:
        return False
    issued_at = _numeric_date(claims.raw.get("iat"))
    expires_at = _numeric_date(claims.raw.get("exp"))
    if expires_at is None:  # both verifiers require exp; keep the row a day in any case
        expires_at = datetime.now(UTC) + RETENTION
    inserted = await session.execute(
        pg_insert(AuthLogin)
        .values(
            token_fingerprint=fingerprint,
            user_id=user.id,
            issuer=claims.issuer,
            issued_at=issued_at,
            expires_at=expires_at,
        )
        .on_conflict_do_nothing(index_elements=[AuthLogin.token_fingerprint])
        .returning(AuthLogin.id)
    )
    if inserted.scalar_one_or_none() is None:
        return False
    await audit.record(
        session,
        company_id=None,
        actor=actor_for_user(user),
        entity_type=EntityType.AUTH,
        entity_id=user.id,
        action=AuditAction.LOGIN,
        context={
            "issuer": claims.issuer,
            "token_fingerprint": fingerprint,
            "token_issued_at": issued_at,
            "token_expires_at": expires_at,
        },
    )
    return True


# --------------------------------------------------------------------------- login_failed


def client_network(ip: str | None) -> str | None:
    """Bucket of a client address: the host for IPv4, its /64 for IPv6."""
    if ip is None:
        return None
    try:
        address = ip_address(ip)
    except ValueError:
        return None
    if isinstance(address, IPv4Address):
        return f"{address}/32"
    return str(ip_network(f"{address}/{IPV6_BUCKET_PREFIX}", strict=False))


def _is_power_of_two(value: int) -> bool:
    return value > 0 and value & (value - 1) == 0


@dataclass(frozen=True, slots=True)
class FailureCount:
    window_start: datetime
    window_seconds: int
    bucket: str
    count: int
    overflow: bool
    recorded: bool
    capped: bool = False  # an immediate entry was due but the per-window limit was reached


async def _immediate_entries(session: AsyncSession, window_start: datetime, seconds: int) -> int:
    """Immediate entries already written in an OPEN window, over all its buckets.

    In an open window ``logged_count`` only ever takes the values 1, 2, 4, ... (summaries
    are written for closed windows only), so a bucket with ``logged_count = 2^k`` has
    produced ``k + 1`` entries: the bit length of ``logged_count``. Exact integer
    arithmetic, no logarithms. Approximate only under concurrency (a few extra entries).
    """
    value = (
        await session.execute(
            text(
                "SELECT COALESCE(sum(length(ltrim(logged_count::bit(64)::text, '0'))), 0) "
                "FROM auth_failure_windows "
                "WHERE window_start = :start AND window_seconds = :seconds AND logged_count > 0"
            ),
            {"start": window_start, "seconds": seconds},
        )
    ).scalar_one()
    return int(value)


async def _current_window(session: AsyncSession, window_seconds: int) -> datetime:
    value: datetime = (
        await session.execute(
            text(
                "SELECT to_timestamp(floor(extract(epoch FROM clock_timestamp()) "
                "/ CAST(:w AS integer)) * CAST(:w AS integer))"
            ),
            {"w": window_seconds},
        )
    ).scalar_one()
    return value


async def _increment(
    session: AsyncSession,
    *,
    window_start: datetime,
    window_seconds: int,
    bucket: str,
    reason: str,
    network: str | None,
    user_id: UUID | None,
) -> tuple[UUID, int, int]:
    now = func.clock_timestamp()
    stmt = (
        pg_insert(AuthFailureWindow)
        .values(
            window_start=window_start,
            window_seconds=window_seconds,
            bucket=bucket,
            reason=reason,
            client_network=network,
            user_id=user_id,
            count=1,
            logged_count=0,
            first_at=now,
            last_at=now,
        )
        .on_conflict_do_update(
            index_elements=[
                AuthFailureWindow.window_start,
                AuthFailureWindow.window_seconds,
                AuthFailureWindow.bucket,
            ],
            set_={
                "count": AuthFailureWindow.count + 1,
                "last_at": now,
                "updated_at": now,
            },
        )
        .returning(AuthFailureWindow.id, AuthFailureWindow.count, AuthFailureWindow.logged_count)
    )
    # Positional: ``Row.count`` is the tuple method, not the column.
    row_id, count, logged_count = (await session.execute(stmt)).one()
    return row_id, int(count), int(logged_count)


async def record_login_failure(
    session: AsyncSession,
    *,
    reason: FailureReason,
    window_seconds: int,
    max_buckets: int,
    max_immediate_entries: int | None = None,
    actor: Actor | None = None,
    user_id: UUID | None = None,
    subject: str | None = None,
    detail: str | None = None,
    method: str | None = None,
    path: str | None = None,
) -> FailureCount:
    """Count one failed authentication; write ``login_failed`` when the count is 1, 2, 4, ...

    ``actor``: the identified user (inactive account); ``None`` = unauthenticated client,
    recorded as the ``system`` actor (``context.authenticated = false``) because §6.1
    reserves ``actor_id = NULL`` for ``system``. ``subject`` only from a VERIFIED token.
    ``detail`` is the verifier's message (clipped), never token content.

    ``user_id``: the account the attempt was about when the client is NOT authenticated
    (a wrong password of an existing local account, ADR 0018): the bucket and
    ``entity_id`` are per account, the actor stays ``system``. Ignored with ``actor``.

    ``max_immediate_entries``: at most this many immediate (1, 2, 4, ...) entries per
    window over ALL buckets (``None`` = no limit). Beyond it failures are only counted;
    the window summary still records every one of them (ADR 0010 §3).
    """
    _require_own_transaction(session)
    window_start = await _current_window(session, window_seconds)
    network = client_network(get_client_info().ip)
    if actor is not None:
        user_id = actor.id
    bucket = "|".join((reason.value, network or "-", str(user_id) if user_id else "-"))
    overflow = False

    existing = await session.execute(
        select(AuthFailureWindow.id).where(
            AuthFailureWindow.window_start == window_start,
            AuthFailureWindow.window_seconds == window_seconds,
            AuthFailureWindow.bucket == bucket,
        )
    )
    if existing.first() is None:
        buckets = (
            await session.execute(
                select(func.count()).select_from(
                    select(AuthFailureWindow.id)
                    .where(
                        AuthFailureWindow.window_start == window_start,
                        AuthFailureWindow.window_seconds == window_seconds,
                    )
                    .limit(max_buckets)
                    .subquery()
                )
            )
        ).scalar_one()
        if buckets >= max_buckets:
            # Too many distinct sources in this window (e.g. rotating addresses): count
            # them together. Approximate under concurrency (a few extra buckets possible).
            overflow = True
            bucket, network, user_id = f"{reason.value}|overflow", None, None

    row_id, count, _ = await _increment(
        session,
        window_start=window_start,
        window_seconds=window_seconds,
        bucket=bucket,
        reason=reason.value,
        network=network,
        user_id=user_id,
    )
    recorded = _is_power_of_two(count)
    capped = False
    if recorded and max_immediate_entries is not None:
        written = await _immediate_entries(session, window_start, window_seconds)
        if written >= max_immediate_entries:
            recorded, capped = False, True
    if recorded:
        context: dict[str, object] = {
            "reason": reason.value,
            "authenticated": actor is not None,
            "window_start": window_start,
            "window_seconds": window_seconds,
            "count_in_window": count,
            "client_network": network,
            "overflow": overflow,
        }
        if subject is not None:
            context["subject"] = _clip(subject, DETAIL_MAX_LENGTH)
        if detail:
            context["detail"] = _clip(detail, DETAIL_MAX_LENGTH)
        if method is not None:
            context["method"] = method
        if path is not None:
            context["path"] = _clip(path, PATH_MAX_LENGTH)
        await audit.record(
            session,
            company_id=None,
            actor=actor or Actor.system(),
            entity_type=EntityType.AUTH,
            entity_id=user_id,
            action=AuditAction.LOGIN_FAILED,
            context=context,
        )
        # Our upsert holds the row lock: nobody changed the row since.
        await session.execute(
            update(AuthFailureWindow)
            .where(AuthFailureWindow.id == row_id)
            .values(logged_count=count)
        )
    await flush_closed_windows(session, limit=OPPORTUNISTIC_FLUSH)
    return FailureCount(window_start, window_seconds, bucket, count, overflow, recorded, capped)


async def failures_from_network(
    session: AsyncSession,
    *,
    window_seconds: int,
    reasons: frozenset[FailureReason],
) -> int:
    """Failures of ``reasons`` from the current client's network in the current window.

    Read from the aggregation counters (``auth_failure_windows``), so the limit holds
    across every API process. Failures folded into an ``overflow`` bucket have no network
    and are not counted here (the window then already has very many sources).
    """
    network = client_network(get_client_info().ip)
    if network is None:
        return 0
    window_start = await _current_window(session, window_seconds)
    value = (
        await session.execute(
            select(func.coalesce(func.sum(AuthFailureWindow.count), 0)).where(
                AuthFailureWindow.window_start == window_start,
                AuthFailureWindow.window_seconds == window_seconds,
                AuthFailureWindow.client_network == network,
                AuthFailureWindow.reason.in_([r.value for r in reasons]),
            )
        )
    ).scalar_one()
    return int(value)


async def seconds_to_window_end(session: AsyncSession, window_seconds: int) -> int:
    """Whole seconds until the current failure window closes (``Retry-After``)."""
    value = (
        await session.execute(
            text(
                "SELECT CAST(:w AS integer) - CAST(floor(extract(epoch FROM clock_timestamp())) "
                "AS bigint) % CAST(:w AS integer)"
            ),
            {"w": window_seconds},
        )
    ).scalar_one()
    return max(1, int(value))


async def flush_closed_windows(session: AsyncSession, *, limit: int = FLUSH_BATCH) -> int:
    """Write the exact totals of closed windows with failures not covered by an entry yet.

    One ``login_failed`` summary per window and bucket (``context.summary = true``,
    ``count_in_window`` = the final count, ``not_recorded_individually`` = failures after
    the last entry). Rows locked by others are skipped (``SKIP LOCKED``), so concurrent
    flushers never wait for each other or for a failure being counted.
    Returns the number of summaries written.
    """
    rows = (
        (
            await session.execute(
                select(AuthFailureWindow)
                .where(
                    AuthFailureWindow.logged_count < AuthFailureWindow.count,
                    AuthFailureWindow.window_start
                    + func.make_interval(0, 0, 0, 0, 0, 0, AuthFailureWindow.window_seconds)
                    <= func.clock_timestamp(),
                )
                .order_by(AuthFailureWindow.window_start, AuthFailureWindow.bucket)
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
        )
        .scalars()
        .all()
    )
    for row in rows:
        await audit.record(
            session,
            company_id=None,
            actor=Actor.system(),
            entity_type=EntityType.AUTH,
            entity_id=row.user_id,
            action=AuditAction.LOGIN_FAILED,
            context={
                "reason": row.reason,
                "summary": True,
                "window_start": row.window_start,
                "window_seconds": row.window_seconds,
                "count_in_window": row.count,
                "not_recorded_individually": row.count - row.logged_count,
                "first_at": row.first_at,
                "last_at": row.last_at,
                "client_network": row.client_network,
                "overflow": row.bucket.endswith("|overflow"),
            },
            request_id=uuid4(),
            inherit_client=False,
        )
        row.logged_count = row.count
    await session.flush()
    return len(rows)


# --------------------------------------------------------------------------- access_denied


async def record_access_denied(
    session: AsyncSession,
    *,
    actor: Actor,
    status: int,
    reason: str,
    company_id: UUID | None,
    method: str | None = None,
    path: str | None = None,
) -> audit.AuditRecord:
    """``access_denied`` in the GLOBAL chain (``context.target_company_id``, ADR 0006 §7).

    Like every ``auth`` entry, ``entity_id`` is the user the event is about (the actor).
    """
    _require_own_transaction(session)
    context: dict[str, object] = {
        "status": status,
        "reason": _clip(reason, DETAIL_MAX_LENGTH),
        "target_company_id": company_id,
    }
    if method is not None:
        context["method"] = method
    if path is not None:
        context["path"] = _clip(path, PATH_MAX_LENGTH)
    return await audit.record(
        session,
        company_id=None,
        actor=actor,
        entity_type=EntityType.AUTH,
        entity_id=actor.id,
        action=AuditAction.ACCESS_DENIED,
        context=context,
    )


# --------------------------------------------------------------------------- maintenance


@dataclass(frozen=True, slots=True)
class MaintenanceReport:
    summaries: int
    logins_purged: int
    windows_purged: int

    def as_dict(self) -> Mapping[str, int]:
        return {
            "summaries": self.summaries,
            "logins_purged": self.logins_purged,
            "windows_purged": self.windows_purged,
        }


async def purge_expired(session: AsyncSession) -> tuple[int, int]:
    """Delete operational rows no longer needed (never audit data).

    - ``auth_logins`` of tokens expired for longer than :data:`RETENTION` (the verifier
      rejects them anyway, so they can never log in again);
    - ``auth_failure_windows`` closed for longer than :data:`RETENTION` whose every failure
      is covered by an audit entry (``logged_count = count``).
    """
    cutoff = func.clock_timestamp() - RETENTION
    # Sessions of local accounts (ADR 0018): expired (absolute limit) for longer than the
    # retention; their refresh tokens go with them (ON DELETE CASCADE). Refresh tokens of
    # live sessions that are expired or rotated are kept until the session goes: a
    # rotated token presented again must still be recognized (reuse detection).
    await session.execute(delete(AuthSession).where(AuthSession.expires_at < cutoff))
    logins = await session.execute(
        delete(AuthLogin).where(AuthLogin.expires_at < cutoff).returning(AuthLogin.id)
    )
    windows = await session.execute(
        delete(AuthFailureWindow)
        .where(
            AuthFailureWindow.logged_count == AuthFailureWindow.count,
            AuthFailureWindow.window_start
            + func.make_interval(0, 0, 0, 0, 0, 0, AuthFailureWindow.window_seconds)
            < cutoff,
        )
        .returning(AuthFailureWindow.id)
    )
    return len(logins.all()), len(windows.all())


async def maintenance(
    sessionmaker: async_sessionmaker[AsyncSession], *, batch: int = FLUSH_BATCH
) -> MaintenanceReport:
    """Flush every pending closed window, then purge (worker cron, ADR 0010 §4).

    Each batch of at most ``batch`` summaries is its OWN short transaction: a summary
    locks the global chain head until COMMIT, so one transaction over a large backlog
    would block every other global write (login, JIT, access_denied — those run with
    ``lock_timeout``) for the whole flush. The purge is a separate transaction as well.
    Every transaction has an EMPTY company scope (only global audit entries can be written).
    """
    if batch < 1:
        raise ValueError("batch must be positive")
    summaries = 0
    while True:
        async with sessionmaker() as session, session.begin():
            await apply_company_scope(session, [])
            written = await flush_closed_windows(session, limit=batch)
        summaries += written
        if written < batch:
            break
    async with sessionmaker() as session, session.begin():
        await apply_company_scope(session, [])
        logins, windows = await purge_expired(session)
    return MaintenanceReport(summaries, logins, windows)
