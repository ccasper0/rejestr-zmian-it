"""Audit log service: append (``record``) and verify (``verify_chain``) — CLAUDE.md 6.

``record`` MUST be called by the service that modifies data, inside the same business
transaction (never from middleware). The chain head row is locked with
``SELECT ... FOR UPDATE`` until the transaction ends, so concurrent writers of the same
chain are serialized and the chain cannot fork. If the business transaction rolls back,
the entry and the head advance roll back with it.

Rules for callers (ADR 0006):

- the transaction must be scoped to the company (``app.db.apply_company_scope``) — RLS
  rejects company entries outside the scope; global entries (``company_id=None``) are
  always allowed;
- lock order: when one transaction writes to several chains, write company chains first
  and the global chain last, to avoid deadlocks between transactions;
- the head lock is held until COMMIT, keep audited transactions short.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta
from ipaddress import IPv4Address, IPv6Address
from typing import Any, Literal
from uuid import UUID, uuid4

from sqlalchemy import ColumnElement, func, select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.audit import (
    GENESIS_HASH,
    Actor,
    AuditAction,
    EntityType,
    VerifyResult,
    build_payload,
    compute_hash,
    find_secret_keys,
    normalize_context,
    normalize_diff,
    normalize_ip,
    normalize_user_agent,
)
from app.domain.canonical import canonical_json
from app.models.audit import AuditChainHead, AuditLog
from app.request_context import ClientInfo, get_client_info, get_request_id

__all__ = [
    "GENESIS_HASH",
    "Actor",
    "AuditAction",
    "AuditError",
    "AuditRecord",
    "AuditScopeError",
    "ChainStatus",
    "ChainVerification",
    "EntityType",
    "EntryFilters",
    "RecordedVerification",
    "VerifyResult",
    "canonical_json",
    "chain_status",
    "compute_hash",
    "entry_hash_valid",
    "held_chain_locks",
    "list_entries",
    "record",
    "verify_and_record",
    "verify_chain",
    "verify_chain_with_head",
]

logger = logging.getLogger(__name__)

_HEAD_UNIQUE = "uq_audit_chain_heads_company_id"
_CHAIN_LOCKS_INFO_KEY = "audit_chain_locks"
DEFAULT_VERIFY_BATCH = 1000
_NO_CLIENT = ClientInfo()


class AuditError(RuntimeError):
    """Programming error in the use of the audit log (never a user error)."""


class AuditScopeError(AuditError):
    """The chain is not visible in the current transaction scope (RLS)."""


@dataclass(frozen=True, slots=True)
class AuditRecord:
    """What was appended (``id`` is not returned: RETURNING would require read access)."""

    company_id: UUID | None
    seq: int
    occurred_at: datetime
    request_id: UUID
    prev_hash: str
    hash: str


def _chain_filter(column: Any, company_id: UUID | None) -> ColumnElement[bool]:
    # Two explicit forms instead of IS NOT DISTINCT FROM, which cannot use the index.
    if company_id is None:
        result: ColumnElement[bool] = column.is_(None)
    else:
        result = column == company_id
    return result


async def _lock_head(session: AsyncSession, company_id: UUID | None) -> tuple[UUID, int, str]:
    stmt = (
        select(AuditChainHead.id, AuditChainHead.last_seq, AuditChainHead.last_hash)
        .where(_chain_filter(AuditChainHead.company_id, company_id))
        .with_for_update()
    )
    row = (await session.execute(stmt)).one_or_none()
    if row is None:
        # First entry of the chain. A concurrent creator makes our INSERT wait for its
        # commit and then do nothing; the second SELECT ... FOR UPDATE then sees and
        # locks the committed row (READ COMMITTED takes a new snapshot per statement).
        await session.execute(
            pg_insert(AuditChainHead)
            .values(company_id=company_id, last_seq=0, last_hash=GENESIS_HASH)
            .on_conflict_do_nothing(constraint=_HEAD_UNIQUE)
        )
        row = (await session.execute(stmt)).one()
    return row.id, int(row.last_seq), str(row.last_hash)


def _note_chain_lock(session: AsyncSession, company_id: UUID | None) -> None:
    transaction = session.sync_session.get_transaction()
    entry: tuple[object, set[UUID | None]] | None = session.info.get(_CHAIN_LOCKS_INFO_KEY)
    if entry is None or entry[0] is not transaction:
        # Keyed by the (root) transaction object: a new transaction starts with no locks.
        entry = (transaction, set())
        session.info[_CHAIN_LOCKS_INFO_KEY] = entry
    entry[1].add(company_id)


def held_chain_locks(session: AsyncSession) -> frozenset[UUID | None]:
    """Chains (``None`` = global) whose head the session's CURRENT transaction has locked.

    Used by ``app.db.run_in_separate_transaction`` to refuse starting a second
    transaction that could wait for these locks (undetectable deadlock).
    """
    transaction = session.sync_session.get_transaction()
    entry = session.info.get(_CHAIN_LOCKS_INFO_KEY)
    if transaction is None or entry is None or entry[0] is not transaction:
        return frozenset()
    return frozenset(entry[1])


async def record(
    session: AsyncSession,
    *,
    company_id: UUID | None,
    actor: Actor,
    entity_type: EntityType,
    entity_id: UUID | None,
    action: AuditAction,
    diff: Mapping[str, object] | None = None,
    context: Mapping[str, object] | None = None,
    ip: str | IPv4Address | IPv6Address | None = None,
    user_agent: str | None = None,
    request_id: UUID | None = None,
    inherit_client: bool = True,
) -> AuditRecord:
    """Append one entry to the chain of ``company_id`` (``None`` = global chain).

    ``diff``: ``{"field": {"before": ..., "after": ...}}`` (see ``app.domain.audit.make_diff``).
    ``request_id`` defaults to the current request's id; outside a request (CLI, worker)
    a fresh one is generated — pass one explicitly to group several entries.
    ``ip`` / ``user_agent`` default to the current request's client (``None`` outside a
    request). ``inherit_client=False``: the entry is not about the current request (e.g. a
    summary of earlier events written while handling it) — no client defaults are taken.
    """
    if not session.in_transaction():
        raise AuditError("audit.record() must run inside the business transaction")

    # Normalize everything BEFORE hashing: the stored values must be exactly the ones
    # that were hashed (they are re-read and re-hashed by verify_chain).
    diff_json = normalize_diff(diff or {})
    context_json = normalize_context(context or {})
    # Never a password, token or hash of one in the (immutable) log (ADR 0018 §7).
    secrets_found = find_secret_keys(diff_json) + find_secret_keys(context_json)
    if secrets_found:
        raise AuditError(f"audit entry must not contain secrets: {', '.join(secrets_found)}")
    client = get_client_info() if inherit_client else _NO_CLIENT
    ip_text = normalize_ip(ip if ip is not None else client.ip)
    agent = normalize_user_agent(user_agent if user_agent is not None else client.user_agent)
    req_id = request_id or get_request_id() or uuid4()

    head_id, last_seq, last_hash = await _lock_head(session, company_id)
    _note_chain_lock(session, company_id)
    # Database clock, read AFTER the head lock: entries of one chain get timestamps in
    # seq order regardless of how many API instances write (ADR 0006). asyncpg returns
    # the exact microsecond value that is stored back below.
    occurred_at: datetime = (await session.execute(select(func.clock_timestamp()))).scalar_one()
    seq = last_seq + 1

    payload = build_payload(
        company_id=company_id,
        seq=seq,
        occurred_at=occurred_at,
        actor_id=actor.id,
        actor_display=actor.display,
        actor_roles=actor.roles,
        ip_address=ip_text,
        user_agent=agent,
        request_id=req_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        diff=diff_json,
        context=context_json,
        prev_hash=last_hash,
    )
    entry_hash = compute_hash(last_hash, payload)

    # No RETURNING: it would require SELECT visibility of the new row, which RLS does
    # not grant for global entries to ordinary users.
    await session.execute(
        pg_insert(AuditLog).values(
            company_id=company_id,
            seq=seq,
            occurred_at=occurred_at,
            actor_id=actor.id,
            actor_display=actor.display,
            actor_roles=list(actor.roles),
            ip_address=ip_text,
            user_agent=agent,
            request_id=req_id,
            entity_type=str(entity_type),
            entity_id=entity_id,
            action=str(action),
            diff=diff_json,
            context=context_json,
            prev_hash=last_hash,
            hash=entry_hash,
        )
    )
    await session.execute(
        update(AuditChainHead)
        .where(AuditChainHead.id == head_id)
        .values(last_seq=seq, last_hash=entry_hash, updated_at=func.clock_timestamp())
    )
    return AuditRecord(
        company_id=company_id,
        seq=seq,
        occurred_at=occurred_at,
        request_id=req_id,
        prev_hash=last_hash,
        hash=entry_hash,
    )


# --------------------------------------------------------------------------- verification


async def _ensure_chain_visible(session: AsyncSession, company_id: UUID | None) -> None:
    """Refuse to verify a chain hidden by RLS — an invisible chain would look empty (ok)."""
    if company_id is None:
        visible = (await session.execute(text("SELECT app_global_audit_read()"))).scalar_one()
    else:
        visible = (
            await session.execute(
                text("SELECT CAST(:cid AS uuid) = ANY (app_company_ids())"), {"cid": company_id}
            )
        ).scalar_one()
    if not visible:
        chain = "global" if company_id is None else str(company_id)
        raise AuditScopeError(f"audit chain {chain} is not in the transaction scope")


async def _read_head(session: AsyncSession, company_id: UUID | None) -> tuple[int, str] | None:
    row = (
        await session.execute(
            select(AuditChainHead.last_seq, AuditChainHead.last_hash).where(
                _chain_filter(AuditChainHead.company_id, company_id)
            )
        )
    ).one_or_none()
    return None if row is None else (int(row.last_seq), str(row.last_hash))


async def _max_seq(session: AsyncSession, company_id: UUID | None) -> int:
    value = (
        await session.execute(
            select(func.max(AuditLog.seq)).where(_chain_filter(AuditLog.company_id, company_id))
        )
    ).scalar_one()
    return 0 if value is None else int(value)


def _broken(checked: int, seq: int) -> VerifyResult:
    return VerifyResult(ok=False, checked=checked, first_broken_seq=seq)


def entry_hash_valid(entry: Any) -> bool:
    """The stored ``hash`` of one entry (a Core row of ``audit_log``) matches its content.

    Proves the entry itself was not changed; the link to its neighbours (``prev_hash``,
    ``seq``) is checked only by :func:`verify_chain`.
    """
    payload = build_payload(
        company_id=entry.company_id,
        seq=entry.seq,
        occurred_at=entry.occurred_at,
        actor_id=entry.actor_id,
        actor_display=entry.actor_display,
        actor_roles=entry.actor_roles,
        ip_address=entry.ip_address,
        user_agent=entry.user_agent,
        request_id=entry.request_id,
        entity_type=entry.entity_type,
        entity_id=entry.entity_id,
        action=entry.action,
        diff=entry.diff,
        context=entry.context,
        prev_hash=entry.prev_hash,
    )
    return bool(compute_hash(entry.prev_hash, payload) == entry.hash)


async def _verify(
    session: AsyncSession, company_id: UUID | None, batch_size: int
) -> tuple[VerifyResult, int, str]:
    """The verification; returns the verdict and the head (seq, hash) it was checked to."""
    head = await _read_head(session, company_id)
    if head is None:
        if await _max_seq(session, company_id) == 0:
            return VerifyResult(ok=True, checked=0, first_broken_seq=None), 0, GENESIS_HASH
        # Entries exist: either the head was created concurrently (visible now) or it is
        # missing, which never happens without tampering.
        head = await _read_head(session, company_id)
        if head is None:
            return _broken(0, 1), 0, GENESIS_HASH
    head_seq, head_hash = head

    def at_head(result: VerifyResult) -> tuple[VerifyResult, int, str]:
        return result, head_seq, head_hash

    checked = 0
    prev_hash = GENESIS_HASH
    expected_seq = 1
    chain = _chain_filter(AuditLog.company_id, company_id)
    while expected_seq <= head_seq:
        rows = (
            await session.execute(
                # Core rows (no ORM identity map): exactly what the database returns.
                select(*AuditLog.__table__.columns)
                .where(chain, AuditLog.seq >= expected_seq, AuditLog.seq <= head_seq)
                .order_by(AuditLog.seq)
                .limit(batch_size)
            )
        ).all()
        batch_count = 0
        for entry in rows:
            batch_count += 1
            if entry.seq != expected_seq or entry.prev_hash != prev_hash:
                return at_head(_broken(checked, expected_seq))
            if not entry_hash_valid(entry):
                return at_head(_broken(checked, entry.seq))
            prev_hash = entry.hash
            checked += 1
            expected_seq += 1
        if batch_count == 0:
            # Entries up to the head are missing (removed tail).
            return at_head(_broken(checked, expected_seq))

    if checked and prev_hash != head_hash:
        return at_head(_broken(checked - 1, head_seq))

    # Entries beyond the head: legitimate only if the head has advanced meanwhile.
    max_seq = await _max_seq(session, company_id)
    if max_seq > head_seq:
        current = await _read_head(session, company_id)
        if current is None or current[0] < max_seq:
            return at_head(_broken(checked, head_seq + 1))

    return at_head(VerifyResult(ok=True, checked=checked, first_broken_seq=None))


@dataclass(frozen=True, slots=True)
class ChainVerification:
    """Result of :func:`verify_chain_with_head`: the verdict and the head it was checked to.

    ``head_seq`` / ``head_hash`` are the values of ``audit_chain_heads`` read at the start
    of the verification (``0`` / genesis for a chain that does not exist yet). For a broken
    chain they are what the head row CLAIMS, not a verified value.
    """

    company_id: UUID | None
    result: VerifyResult
    head_seq: int
    head_hash: str


async def verify_chain_with_head(
    session: AsyncSession,
    company_id: UUID | None,
    *,
    batch_size: int = DEFAULT_VERIFY_BATCH,
) -> ChainVerification:
    """Recompute the chain of ``company_id`` (``None`` = global) up to its head.

    Detects: modified entries (hash mismatch), broken links (``prev_hash``), gaps and
    removed entries (``seq`` continuity), removed tail / forged head (head mismatch).
    ``first_broken_seq`` is the first ``seq`` at which the chain stops being valid;
    ``checked`` counts the entries verified as valid before it.

    Takes no locks: entries committed after the head was read are outside the verified
    range (entries and head advances commit atomically).

    Refuses (:class:`AuditScopeError`) a chain that is not in the transaction scope: an
    invisible chain would look empty and verify as "ok".
    """
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    await _ensure_chain_visible(session, company_id)
    result, head_seq, head_hash = await _verify(session, company_id, batch_size)
    if result.ok:
        logger.debug("audit chain %s verified: %d entries", company_id or "global", result.checked)
    return ChainVerification(company_id, result, head_seq, head_hash)


async def verify_chain(
    session: AsyncSession,
    company_id: UUID | None,
    *,
    batch_size: int = DEFAULT_VERIFY_BATCH,
) -> VerifyResult:
    """:func:`verify_chain_with_head` without the head (``{ok, checked, first_broken_seq}``)."""
    return (await verify_chain_with_head(session, company_id, batch_size=batch_size)).result


# --------------------------------------------------------------------------- verify + record

RecordedIn = Literal["chain", "global"]


@dataclass(frozen=True, slots=True)
class RecordedVerification:
    """:func:`verify_and_record`: the verification and where its own audit entry went.

    ``recorded_in``: ``"chain"`` - the verified chain itself (normal case); ``"global"`` -
    the global chain, because the broken company chain refused the append; ``None`` -
    nowhere (every chain that could take it refused it).
    """

    verification: ChainVerification
    entry: AuditRecord | None
    recorded_in: RecordedIn | None


def verification_context(verification: ChainVerification) -> dict[str, object]:
    """``context`` of the ``audit/verify`` entry: the verdict and the verified head."""
    result = verification.result
    return {
        "chain": "global" if verification.company_id is None else "company",
        "ok": result.ok,
        "checked": result.checked,
        "first_broken_seq": result.first_broken_seq,
        "head_seq": verification.head_seq,
        "head_hash": verification.head_hash,
    }


def _error_name(exc: DBAPIError) -> str:
    return type(exc.orig).__name__ if exc.orig is not None else type(exc).__name__


async def verify_and_record(
    session: AsyncSession,
    company_id: UUID | None,
    *,
    actor: Actor,
    context: Mapping[str, object] | None = None,
    batch_size: int = DEFAULT_VERIFY_BATCH,
) -> RecordedVerification:
    """Verify the chain, then append the verification and its result (CLAUDE.md 6.4).

    The entry (``entity_type = audit``, ``action = verify``, ``entity_id`` = the company or
    ``None`` for the global chain, ``context`` = ``context`` + the verdict and the verified
    head) is appended to the VERIFIED chain after the verification, in the caller's
    transaction, so it is outside the verified range (``head_seq``).

    A tampered chain may refuse the append: the database requires ``prev_hash`` of a new
    entry to equal the stored hash of the previous one and ``seq`` to be unique (ADR 0006
    §5). The detection must not be lost, so for a BROKEN chain the append runs in a
    SAVEPOINT and, if refused, a company chain's verification is written to the GLOBAL
    chain instead (``target_company_id``, ``chain_append_failed``). If that is refused too
    (or the refusing chain is the global one), the result is returned with
    ``recorded_in = None`` and logged as an error; callers must tell the user. A failing
    append to a chain that verified OK is unexpected and propagates.

    Lock order (ADR 0006 §7): company chain first, global chain last.
    """
    verification = await verify_chain_with_head(session, company_id, batch_size=batch_size)
    entry_context = {**(context or {}), **verification_context(verification)}

    async def append(chain: UUID | None, extra: Mapping[str, object]) -> AuditRecord:
        return await record(
            session,
            company_id=chain,
            actor=actor,
            entity_type=EntityType.AUDIT,
            entity_id=company_id,
            action=AuditAction.VERIFY,
            context={**entry_context, **extra},
        )

    if verification.result.ok:
        return RecordedVerification(verification, await append(company_id, {}), "chain")

    chain_name = "global" if company_id is None else str(company_id)
    try:
        async with session.begin_nested():
            entry = await append(company_id, {})
        return RecordedVerification(verification, entry, "chain")
    except DBAPIError as exc:
        logger.error(
            "broken audit chain %s refused the verification entry (%s)",
            chain_name,
            _error_name(exc),
        )
    if company_id is not None:
        try:
            async with session.begin_nested():
                entry = await append(
                    None, {"target_company_id": company_id, "chain_append_failed": True}
                )
            return RecordedVerification(verification, entry, "global")
        except DBAPIError as exc:
            logger.error(
                "global audit chain refused the verification entry of chain %s (%s)",
                chain_name,
                _error_name(exc),
            )
    logger.error(
        "verification of audit chain %s (broken at seq %s) could NOT be recorded",
        chain_name,
        verification.result.first_broken_seq,
    )
    return RecordedVerification(verification, None, None)


# --------------------------------------------------------------------------- browsing


@dataclass(frozen=True, slots=True)
class EntryFilters:
    """Filters of ``GET /audit`` (all optional, combined with AND)."""

    entity_type: str | None = None
    entity_id: UUID | None = None
    action: str | None = None
    actor_id: UUID | None = None
    occurred_from: datetime | None = None  # inclusive
    occurred_to: datetime | None = None  # exclusive


async def list_entries(
    session: AsyncSession,
    company_id: UUID | None,
    filters: EntryFilters,
    *,
    limit: int,
    offset: int,
) -> tuple[list[Any], int]:
    """Entries of ONE chain (``None`` = global), newest first (``seq`` descending).

    Returns Core rows (exact stored values) and the total matching the filters. Refuses
    (:class:`AuditScopeError`) a chain outside the transaction scope, so a hidden chain is
    never reported as empty. RLS filters the rows in any case.
    """
    await _ensure_chain_visible(session, company_id)
    conditions: list[ColumnElement[bool]] = [_chain_filter(AuditLog.company_id, company_id)]
    if filters.entity_type is not None:
        conditions.append(AuditLog.entity_type == filters.entity_type)
    if filters.entity_id is not None:
        conditions.append(AuditLog.entity_id == filters.entity_id)
    if filters.action is not None:
        conditions.append(AuditLog.action == filters.action)
    if filters.actor_id is not None:
        conditions.append(AuditLog.actor_id == filters.actor_id)
    if filters.occurred_from is not None:
        conditions.append(AuditLog.occurred_at >= filters.occurred_from)
    if filters.occurred_to is not None:
        conditions.append(AuditLog.occurred_at < filters.occurred_to)
    total = (
        await session.execute(select(func.count()).select_from(AuditLog).where(*conditions))
    ).scalar_one()
    rows = (
        await session.execute(
            select(*AuditLog.__table__.columns)
            .where(*conditions)
            .order_by(AuditLog.seq.desc())
            .limit(limit)
            .offset(offset)
        )
    ).all()
    return list(rows), int(total)


# --------------------------------------------------------------------------- chain status

ChainStatusValue = Literal["ok", "stale", "broken", "unknown"]
# At most this many entries since the last verification are checked per request; more
# -> ``stale`` (no claim). The daily worker verification keeps the tail short. No cache:
# a cached "ok" would hide an entry forged after it at an unchanged head (ADR 0013 §11).
STATUS_TAIL_LIMIT = 2_000


@dataclass(frozen=True, slots=True)
class ChainStatus:
    """Verdict for the "Łańcuch spójny" badge (CLAUDE.md §10.2, ADR 0013 §11).

    - ``ok``: the last recorded verification of the chain passed, is not older than the
      allowed age, and every entry appended after it is consistent (contiguous ``seq``,
      ``prev_hash`` links, own hash, matching chain head);
    - ``broken``: the last verification failed, or the entries after it are inconsistent;
    - ``stale``: the last verification is too old (or too many entries since) - no claim;
    - ``unknown``: the chain was never verified.

    Never ``ok`` without an actual verification. Details of a violation are not exposed
    (members see only the verdict; auditors use ``POST /audit/verify``).
    """

    status: ChainStatusValue
    checked_at: datetime | None
    verified_head_seq: int | None
    head_seq: int


async def chain_status(
    session: AsyncSession, company_id: UUID, *, max_age: timedelta, now: datetime
) -> ChainStatus:
    """Read-only: no audit entry (the verifications themselves are recorded)."""
    await _ensure_chain_visible(session, company_id)
    # Everything below is judged AS OF this head: entries appended concurrently (READ
    # COMMITTED - later statements see them) are outside the checked range.
    head = await _read_head(session, company_id)
    head_seq = head[0] if head is not None else 0
    last = (
        await session.execute(
            select(*AuditLog.__table__.columns)
            .where(
                AuditLog.company_id == company_id,
                AuditLog.seq <= head_seq,
                AuditLog.entity_type == EntityType.AUDIT.value,
                AuditLog.action == AuditAction.VERIFY.value,
            )
            .order_by(AuditLog.seq.desc())
            .limit(1)
        )
    ).one_or_none()
    if last is None:
        return ChainStatus("unknown", None, None, head_seq)
    context = last.context
    verified_seq = int(context.get("head_seq", 0))
    if not context.get("ok"):
        return ChainStatus("broken", last.occurred_at, verified_seq, head_seq)
    if now - last.occurred_at > max_age or head_seq - verified_seq > STATUS_TAIL_LIMIT:
        return ChainStatus("stale", last.occurred_at, verified_seq, head_seq)
    consistent = await _tail_consistent(
        session, company_id, verified_seq, str(context.get("head_hash", "")), head
    )
    return ChainStatus("ok" if consistent else "broken", last.occurred_at, verified_seq, head_seq)


async def _tail_consistent(
    session: AsyncSession,
    company_id: UUID,
    verified_seq: int,
    verified_hash: str,
    head: tuple[int, str] | None,
) -> bool:
    """Entries ``verified_seq .. head`` still continue the verified chain."""
    if head is None:
        return False
    rows = (
        await session.execute(
            select(*AuditLog.__table__.columns)
            .where(
                AuditLog.company_id == company_id,
                AuditLog.seq >= max(verified_seq, 1),
                AuditLog.seq <= head[0],  # the head read first; later entries are not judged
            )
            .order_by(AuditLog.seq)
        )
    ).all()
    prev_hash = verified_hash if verified_seq > 0 else GENESIS_HASH
    expected = verified_seq + 1
    for row in rows:
        if row.seq == verified_seq:
            if row.hash != verified_hash:
                return False
            continue
        if row.seq != expected or row.prev_hash != prev_hash or not entry_hash_valid(row):
            return False
        prev_hash, expected = row.hash, expected + 1
    return expected - 1 == head[0] and prev_hash == head[1]
