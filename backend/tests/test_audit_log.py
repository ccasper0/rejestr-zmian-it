"""Audit log on a real PostgreSQL, as app_rw (CLAUDE.md 6, ADR 0006).

Every company chain is isolated by using a fresh random company id per test. The global
chain is shared, so tests touching it reset the audit tables first (as app_owner, with
triggers disabled — exactly what the protection is designed to make visible).
"""

from __future__ import annotations

import asyncio
import itertools
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.db import apply_company_scope
from app.domain.audit import normalize_ip
from app.request_context import _request_id
from app.services import audit
from app.services.audit import (
    GENESIS_HASH,
    Actor,
    AuditAction,
    AuditError,
    AuditScopeError,
    EntityType,
)
from tests.conftest import DbUrls

pytestmark = pytest.mark.db

INSUFFICIENT_PRIVILEGE = "42501"
RESTRICT_VIOLATION = "23001"
CHECK_VIOLATION = "23514"

USER = Actor(id=UUID(int=7), display="Anna Kowalska", roles=("editor",))


def sqlstate(exc: DBAPIError) -> str | None:
    orig = exc.orig
    return getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)


@asynccontextmanager
async def scoped(
    engine: AsyncEngine, company_ids: Sequence[UUID] = (), *, global_read: bool = False
) -> AsyncIterator[AsyncSession]:
    """One transaction as the engine's role, scoped like a request (RLS)."""
    async with AsyncSession(engine) as session, session.begin():
        await apply_company_scope(session, company_ids, global_audit_read=global_read)
        yield session


async def write(
    engine: AsyncEngine, company_id: UUID | None, count: int = 1, **kwargs: Any
) -> list[audit.AuditRecord]:
    scope = [company_id] if company_id else []
    records = []
    async with scoped(engine, scope) as session:
        for i in range(count):
            records.append(
                await audit.record(
                    session,
                    company_id=company_id,
                    actor=kwargs.get("actor", USER),
                    entity_type=kwargs.get("entity_type", EntityType.CHANGE),
                    entity_id=kwargs.get("entity_id", uuid4()),
                    action=kwargs.get("action", AuditAction.UPDATE),
                    diff=kwargs.get("diff", {"title": {"before": f"v{i}", "after": f"v{i + 1}"}}),
                    context=kwargs.get("context"),
                    ip=kwargs.get("ip", "10.0.0.5"),
                    user_agent=kwargs.get("user_agent", "pytest"),
                    request_id=kwargs.get("request_id"),
                )
            )
    return records


async def verify(engine: AsyncEngine, company_id: UUID | None, **kwargs: Any) -> audit.VerifyResult:
    scope = [company_id] if company_id else []
    async with scoped(engine, scope, global_read=company_id is None) as session:
        return await audit.verify_chain(session, company_id, **kwargs)


async def rows(engine: AsyncEngine, company_id: UUID) -> list[Any]:
    async with scoped(engine, [company_id]) as session:
        result = await session.execute(
            text("SELECT * FROM audit_log WHERE company_id = :c ORDER BY seq"), {"c": company_id}
        )
        return list(result.all())


async def owner_exec(engine: AsyncEngine, *statements: str, **params: Any) -> None:
    """Tamper as the table owner (triggers must be disabled explicitly to succeed)."""
    async with engine.begin() as conn:
        for statement in statements:
            await conn.execute(text(statement), params)


@pytest.fixture
async def clean_audit(owner_engine: AsyncEngine) -> None:
    await owner_exec(
        owner_engine,
        "ALTER TABLE audit_log DISABLE TRIGGER USER",
        "ALTER TABLE audit_chain_heads DISABLE TRIGGER USER",
        "TRUNCATE audit_log, audit_chain_heads",
        "ALTER TABLE audit_log ENABLE TRIGGER USER",
        "ALTER TABLE audit_chain_heads ENABLE TRIGGER USER",
    )


# --------------------------------------------------------------------------- protection


async def test_app_rw_cannot_update_delete_or_truncate(rw_engine: AsyncEngine) -> None:
    company = uuid4()
    await write(rw_engine, company)
    for statement in (
        "UPDATE audit_log SET action = 'forged' WHERE company_id = :c",
        "DELETE FROM audit_log WHERE company_id = :c",
        "TRUNCATE audit_log",
    ):
        with pytest.raises(DBAPIError) as info:
            async with scoped(rw_engine, [company]) as session:
                await session.execute(text(statement), {"c": company})
        assert sqlstate(info.value) == INSUFFICIENT_PRIVILEGE, statement
    assert len(await rows(rw_engine, company)) == 1


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE audit_log SET action = 'forged' WHERE company_id = :c",
        "DELETE FROM audit_log WHERE company_id = :c",
        "TRUNCATE audit_log",
    ],
)
async def test_trigger_blocks_owner_too(
    rw_engine: AsyncEngine, owner_engine: AsyncEngine, statement: str
) -> None:
    company = uuid4()
    await write(rw_engine, company)
    with pytest.raises(DBAPIError) as info:
        await owner_exec(owner_engine, statement, c=company)
    assert sqlstate(info.value) == RESTRICT_VIOLATION
    assert "append-only" in str(info.value)
    assert len(await rows(rw_engine, company)) == 1


async def test_chain_heads_cannot_be_deleted_or_rewound(
    rw_engine: AsyncEngine, owner_engine: AsyncEngine
) -> None:
    company = uuid4()
    await write(rw_engine, company, count=2)
    with pytest.raises(DBAPIError) as info:
        async with scoped(rw_engine, [company]) as session:
            await session.execute(
                text("DELETE FROM audit_chain_heads WHERE company_id = :c"), {"c": company}
            )
    assert sqlstate(info.value) == INSUFFICIENT_PRIVILEGE

    for statement in (
        "UPDATE audit_chain_heads SET last_seq = 1 WHERE company_id = :c",
        "UPDATE audit_chain_heads SET last_seq = 3, last_hash = repeat('a', 64) "
        "WHERE company_id = :c",
        "UPDATE audit_chain_heads SET company_id = gen_random_uuid() WHERE company_id = :c",
    ):
        with pytest.raises(DBAPIError) as info:
            async with scoped(rw_engine, [company]) as session:
                await session.execute(text(statement), {"c": company})
        assert sqlstate(info.value) == CHECK_VIOLATION, statement

    with pytest.raises(DBAPIError) as info:
        await owner_exec(
            owner_engine, "DELETE FROM audit_chain_heads WHERE company_id = :c", c=company
        )
    assert sqlstate(info.value) == RESTRICT_VIOLATION
    assert (await verify(rw_engine, company)).ok


async def test_chain_head_must_start_empty(rw_engine: AsyncEngine) -> None:
    company = uuid4()
    with pytest.raises(DBAPIError) as info:
        async with scoped(rw_engine, [company]) as session:
            await session.execute(
                text(
                    "INSERT INTO audit_chain_heads (company_id, last_seq, last_hash) "
                    "VALUES (:c, 5, :h)"
                ),
                {"c": company, "h": "b" * 64},
            )
    assert sqlstate(info.value) == CHECK_VIOLATION


RAW_INSERT = (
    "INSERT INTO audit_log (company_id, seq, occurred_at, actor_display, actor_roles, "
    "request_id, entity_type, action, diff, context, prev_hash, hash) VALUES "
    "(:c, :seq, clock_timestamp() + CAST(:shift AS interval), 'x', '{}', gen_random_uuid(), "
    "'change', 'create', '{}', '{}', :prev, :hash)"
)


def _raw_insert(**overrides: Any) -> tuple[str, dict[str, Any]]:
    """Bypass the service: a hand-made entry that app_rw might try to insert."""
    params: dict[str, Any] = {
        "seq": 1,
        "shift": timedelta(0),
        "prev": GENESIS_HASH,
        "hash": "c" * 64,
    }
    params.update(overrides)
    return RAW_INSERT, params


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"prev": "d" * 64}, "does not continue"),
        ({"seq": 3, "prev": "e" * 64}, "does not continue"),
        ({"shift": timedelta(hours=-1)}, "database clock"),
        ({"shift": timedelta(hours=1)}, "database clock"),
    ],
)
async def test_direct_inserts_that_break_the_chain_are_rejected(
    rw_engine: AsyncEngine, overrides: dict[str, Any], message: str
) -> None:
    company = uuid4()
    if overrides.get("seq") == 3:
        await write(rw_engine, company)  # seq 1 exists; seq 2 is skipped
    sql, params = _raw_insert(**overrides)
    with pytest.raises(DBAPIError) as info:
        async with scoped(rw_engine, [company]) as session:
            await session.execute(text(sql), {"c": company, **params})
    assert sqlstate(info.value) == CHECK_VIOLATION
    assert message in str(info.value)


async def test_duplicate_seq_in_global_chain_rejected(
    rw_engine: AsyncEngine, clean_audit: None
) -> None:
    # UNIQUE NULLS NOT DISTINCT: NULL company ids do not escape the uniqueness of seq.
    first = (await write(rw_engine, None))[0]
    sql, params = _raw_insert()
    with pytest.raises(DBAPIError) as info:
        async with scoped(rw_engine) as session:
            await session.execute(text(sql), {"c": None, **params})
    assert sqlstate(info.value) == "23505"
    assert first.seq == 1


# --------------------------------------------------------------------------- chain


async def test_first_entry_and_linking(rw_engine: AsyncEngine) -> None:
    company = uuid4()
    records = await write(rw_engine, company, count=3)
    stored = await rows(rw_engine, company)

    assert [r.seq for r in stored] == [1, 2, 3]
    assert stored[0].prev_hash == GENESIS_HASH
    assert stored[1].prev_hash == stored[0].hash
    assert stored[2].prev_hash == stored[1].hash
    assert [r.hash for r in stored] == [r.hash for r in records]
    assert len({r.hash for r in stored}) == 3
    assert await verify(rw_engine, company) == audit.VerifyResult(True, 3, None)


async def test_chains_are_separate_per_company_and_global(
    rw_engine: AsyncEngine, clean_audit: None
) -> None:
    alfa, beta = uuid4(), uuid4()
    await write(rw_engine, alfa, count=2)
    await write(rw_engine, beta, count=1)
    glob = await write(rw_engine, None, count=2, entity_type=EntityType.COMPANY)
    await write(rw_engine, alfa, count=1)

    assert [r.seq for r in await rows(rw_engine, alfa)] == [1, 2, 3]
    assert [r.seq for r in await rows(rw_engine, beta)] == [1]
    assert [r.seq for r in glob] == [1, 2]
    assert glob[0].prev_hash == GENESIS_HASH
    assert (await rows(rw_engine, beta))[0].prev_hash == GENESIS_HASH

    assert await verify(rw_engine, alfa) == audit.VerifyResult(True, 3, None)
    assert await verify(rw_engine, beta) == audit.VerifyResult(True, 1, None)
    assert await verify(rw_engine, None) == audit.VerifyResult(True, 2, None)


async def test_empty_chain_verifies(rw_engine: AsyncEngine) -> None:
    assert await verify(rw_engine, uuid4()) == audit.VerifyResult(True, 0, None)


async def test_stored_entry_round_trips_exactly(rw_engine: AsyncEngine) -> None:
    company, entity, request = uuid4(), uuid4(), uuid4()
    at = datetime(2026, 10, 28, 9, 30, 0, 1, tzinfo=timezone(timedelta(hours=1)))
    record = (
        await write(
            rw_engine,
            company,
            entity_id=entity,
            request_id=request,
            action=AuditAction.TRANSITION,
            diff={"window_start": {"before": None, "after": at}},
            context={
                "comment": "Zażółć gęślą jaźń — wdrożenie „FW-01”",
                "amount": Decimal("12.50"),
                "from_status": "draft",
                "nested": {"z": [1, 2], "a": None},
            },
            ip="2001:DB8::0001",
            user_agent="Mozilla/5.0 (ąę)",
        )
    )[0]
    row = (await rows(rw_engine, company))[0]

    assert row.request_id == request
    assert record.request_id == request
    assert row.entity_id == entity
    assert row.entity_type == "change"
    assert row.action == "transition"
    assert row.actor_id == USER.id
    assert row.actor_display == "Anna Kowalska"
    assert row.actor_roles == ["editor"]
    assert str(row.ip_address) == "2001:db8::1"
    assert row.user_agent == "Mozilla/5.0 (ąę)"
    assert row.diff == {"window_start": {"before": None, "after": "2026-10-28T08:30:00.000001Z"}}
    assert row.context["amount"] == "12.50"
    assert row.context["comment"] == "Zażółć gęślą jaźń — wdrożenie „FW-01”"
    assert row.occurred_at == record.occurred_at
    assert row.occurred_at.tzinfo is not None
    assert await verify(rw_engine, company) == audit.VerifyResult(True, 1, None)


IP_ROUNDTRIP = [
    ("10.0.0.5", "10.0.0.5", 4),
    ("::ffff:192.0.2.1", "192.0.2.1", 4),  # IPv4-mapped is stored as IPv4
    ("::ffff:c000:201", "192.0.2.1", 4),
    ("::192.0.2.1", "::c000:201", 6),  # IPv4-compatible: PostgreSQL prints "::192.0.2.1"
    ("64:ff9b::192.0.2.1", "64:ff9b::c000:201", 6),  # PostgreSQL prints a dotted quad
    ("2001:DB8:0:0:1:0:0:1", "2001:db8::1:0:0:1", 6),
    ("2001:db8:0:1:1:1:1:1", "2001:db8:0:1:1:1:1:1", 6),
    ("::", "::", 6),
    ("::1", "::1", 6),
]


@pytest.mark.parametrize(("ip", "canonical", "family"), IP_ROUNDTRIP)
async def test_ip_address_round_trips_through_inet(
    rw_engine: AsyncEngine, ip: str, canonical: str, family: int
) -> None:
    """The value read back from the ``inet`` column normalizes to the hashed text, both
    as returned by the driver and as PostgreSQL's own text output (ADR 0006 §3)."""
    company = uuid4()
    await write(rw_engine, company, ip=ip)
    async with scoped(rw_engine, [company]) as session:
        row = (
            await session.execute(
                text(
                    "SELECT ip_address, ip_address::text AS pg_text, host(ip_address) AS host, "
                    "family(ip_address) AS family FROM audit_log WHERE company_id = :c"
                ),
                {"c": company},
            )
        ).one()
    assert row.family == family
    assert normalize_ip(row.ip_address) == canonical
    assert normalize_ip(row.pg_text) == canonical
    assert normalize_ip(row.host) == canonical
    assert await verify(rw_engine, company) == audit.VerifyResult(True, 1, None)


async def test_occurred_at_comes_from_database_clock_in_seq_order(rw_engine: AsyncEngine) -> None:
    company = uuid4()
    before = datetime.now(UTC) - timedelta(minutes=5)
    records = await write(rw_engine, company, count=3)
    times = [r.occurred_at for r in records]
    assert times == sorted(times)
    assert all(t > before for t in times)


async def test_system_actor_and_request_id_sources(rw_engine: AsyncEngine) -> None:
    company = uuid4()
    request = uuid4()
    token = _request_id.set(request)
    try:
        from_context = (await write(rw_engine, company, actor=Actor.system()))[0]
    finally:
        _request_id.reset(token)
    generated = (await write(rw_engine, company, actor=Actor.system()))[0]

    assert from_context.request_id == request
    assert generated.request_id not in (None, request)
    stored = await rows(rw_engine, company)
    assert [(r.actor_id, r.actor_display, r.actor_roles) for r in stored] == [
        (None, "system", []),
        (None, "system", []),
    ]


async def test_rolled_back_entry_does_not_remain_nor_advance_head(
    rw_engine: AsyncEngine,
) -> None:
    company = uuid4()
    await write(rw_engine, company)

    class BusinessError(Exception):
        pass

    async def failing_business_transaction() -> None:
        async with scoped(rw_engine, [company]) as session:
            await audit.record(
                session,
                company_id=company,
                actor=USER,
                entity_type=EntityType.CHANGE,
                entity_id=uuid4(),
                action=AuditAction.CREATE,
            )
            raise BusinessError

    with pytest.raises(BusinessError):
        await failing_business_transaction()

    async with scoped(rw_engine, [company]) as session:
        head = (
            await session.execute(
                text("SELECT last_seq FROM audit_chain_heads WHERE company_id = :c"),
                {"c": company},
            )
        ).scalar_one()
    assert head == 1
    assert len(await rows(rw_engine, company)) == 1

    nxt = (await write(rw_engine, company))[0]
    assert nxt.seq == 2
    assert await verify(rw_engine, company) == audit.VerifyResult(True, 2, None)


async def test_record_requires_a_transaction(rw_engine: AsyncEngine) -> None:
    async with AsyncSession(rw_engine) as session:
        with pytest.raises(AuditError, match="business transaction"):
            await audit.record(
                session,
                company_id=None,
                actor=USER,
                entity_type=EntityType.AUTH,
                entity_id=None,
                action=AuditAction.LOGIN,
            )


async def test_apply_company_scope_requires_a_transaction(rw_engine: AsyncEngine) -> None:
    async with AsyncSession(rw_engine) as session:
        with pytest.raises(RuntimeError, match="inside a transaction"):
            await apply_company_scope(session, [uuid4()])


# --------------------------------------------------------------------------- concurrency


async def test_fifty_parallel_writers_do_not_fork_the_chain(db_urls: DbUrls) -> None:
    company = uuid4()
    # Every writer has its own connection (NullPool) and transaction.
    engine = create_async_engine(db_urls.rw, poolclass=NullPool)
    start = asyncio.Event()

    async def writer(i: int) -> audit.AuditRecord:
        async with AsyncSession(engine) as session, session.begin():
            await apply_company_scope(session, [company])
            await start.wait()
            return await audit.record(
                session,
                company_id=company,
                actor=USER,
                entity_type=EntityType.CHANGE,
                entity_id=uuid4(),
                action=AuditAction.UPDATE,
                diff={"n": {"before": i, "after": i + 1}},
            )

    try:
        tasks = [asyncio.create_task(writer(i)) for i in range(50)]
        await asyncio.sleep(0.5)  # let every writer open its transaction first
        start.set()
        results = await asyncio.gather(*tasks)
    finally:
        await engine.dispose()

    assert sorted(r.seq for r in results) == list(range(1, 51))
    stored = await rows(engine_rw := create_async_engine(db_urls.rw, poolclass=NullPool), company)
    await engine_rw.dispose()
    assert [r.seq for r in stored] == list(range(1, 51))
    assert stored[0].prev_hash == GENESIS_HASH
    for previous, current in itertools.pairwise(stored):
        assert current.prev_hash == previous.hash
    assert len({r.prev_hash for r in stored}) == 50  # no two entries share a parent

    check = create_async_engine(db_urls.rw, poolclass=NullPool)
    try:
        assert await verify(check, company, batch_size=7) == audit.VerifyResult(True, 50, None)
    finally:
        await check.dispose()


# --------------------------------------------------------------------------- tampering


async def _tamper(owner_engine: AsyncEngine, *statements: str, **params: Any) -> None:
    await owner_exec(
        owner_engine,
        "ALTER TABLE audit_log DISABLE TRIGGER USER",
        "ALTER TABLE audit_chain_heads DISABLE TRIGGER USER",
        *statements,
        "ALTER TABLE audit_log ENABLE TRIGGER USER",
        "ALTER TABLE audit_chain_heads ENABLE TRIGGER USER",
        **params,
    )


async def test_modified_entry_is_detected(
    rw_engine: AsyncEngine, owner_engine: AsyncEngine
) -> None:
    company = uuid4()
    await write(rw_engine, company, count=5)
    assert (await verify(rw_engine, company)).ok
    await _tamper(
        owner_engine,
        """UPDATE audit_log SET diff = '{"title": {"before": "a", "after": "forged"}}'
           WHERE company_id = :c AND seq = 3""",
        c=company,
    )
    assert await verify(rw_engine, company) == audit.VerifyResult(False, 2, 3)


async def test_modified_entry_with_recomputed_hash_breaks_the_next_link(
    rw_engine: AsyncEngine, owner_engine: AsyncEngine
) -> None:
    company = uuid4()
    await write(rw_engine, company, count=5)
    entry = (await rows(rw_engine, company))[2]
    payload = audit.build_payload(
        company_id=entry.company_id,
        seq=entry.seq,
        occurred_at=entry.occurred_at,
        actor_id=entry.actor_id,
        actor_display="Ktoś inny",
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
    forged_hash = audit.compute_hash(entry.prev_hash, payload)
    await _tamper(
        owner_engine,
        "UPDATE audit_log SET actor_display = 'Ktoś inny', hash = :h "
        "WHERE company_id = :c AND seq = 3",
        c=company,
        h=forged_hash,
    )
    assert await verify(rw_engine, company) == audit.VerifyResult(False, 3, 4)


@pytest.mark.parametrize(
    ("statement", "expected"),
    [
        # removed entry in the middle -> gap
        (
            "DELETE FROM audit_log WHERE company_id = :c AND seq = 3",
            audit.VerifyResult(False, 2, 3),
        ),
        # removed tail -> head points beyond the last entry
        (
            "DELETE FROM audit_log WHERE company_id = :c AND seq = 5",
            audit.VerifyResult(False, 4, 5),
        ),
        # head rewound to hide the tail
        (
            "UPDATE audit_chain_heads SET last_seq = 4, last_hash = "
            "(SELECT hash FROM audit_log WHERE company_id = :c AND seq = 4) WHERE company_id = :c",
            audit.VerifyResult(False, 4, 5),
        ),
        # head with a forged hash
        (
            "UPDATE audit_chain_heads SET last_hash = repeat('f', 64) WHERE company_id = :c",
            audit.VerifyResult(False, 4, 5),
        ),
        # head removed
        ("DELETE FROM audit_chain_heads WHERE company_id = :c", audit.VerifyResult(False, 0, 1)),
        # entry re-linked to a forged parent
        (
            "UPDATE audit_log SET prev_hash = repeat('a', 64) WHERE company_id = :c AND seq = 2",
            audit.VerifyResult(False, 1, 2),
        ),
    ],
)
async def test_structural_tampering_is_detected(
    rw_engine: AsyncEngine,
    owner_engine: AsyncEngine,
    statement: str,
    expected: audit.VerifyResult,
) -> None:
    company = uuid4()
    await write(rw_engine, company, count=5)
    await _tamper(owner_engine, statement, c=company)
    assert await verify(rw_engine, company) == expected


async def test_verify_ignores_entries_committed_after_the_head_was_read(
    rw_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Simulates a writer committing between verify's head read and its row reads."""
    company = uuid4()
    records = await write(rw_engine, company, count=3)
    real_read_head = audit._read_head
    calls = 0

    async def stale_first_read(session: AsyncSession, cid: UUID | None) -> Any:
        nonlocal calls
        calls += 1
        if calls == 1:
            return (2, records[1].hash)  # head as it was before entry 3 committed
        return await real_read_head(session, cid)

    monkeypatch.setattr(audit, "_read_head", stale_first_read)
    assert await verify(rw_engine, company) == audit.VerifyResult(True, 2, None)


async def test_verify_tolerates_chain_created_after_the_head_was_read(
    rw_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    company = uuid4()
    await write(rw_engine, company, count=2)
    real_read_head = audit._read_head
    calls = 0

    async def missing_first_read(session: AsyncSession, cid: UUID | None) -> Any:
        nonlocal calls
        calls += 1
        return None if calls == 1 else await real_read_head(session, cid)

    monkeypatch.setattr(audit, "_read_head", missing_first_read)
    assert await verify(rw_engine, company) == audit.VerifyResult(True, 2, None)


async def test_verify_batch_size_must_be_positive(rw_engine: AsyncEngine) -> None:
    with pytest.raises(ValueError, match="batch_size"):
        await verify(rw_engine, uuid4(), batch_size=0)


# --------------------------------------------------------------------------- RLS


async def test_company_entry_outside_scope_is_rejected(rw_engine: AsyncEngine) -> None:
    alfa, beta = uuid4(), uuid4()
    with pytest.raises(DBAPIError) as info:
        async with scoped(rw_engine, [alfa]) as session:
            await audit.record(
                session,
                company_id=beta,
                actor=USER,
                entity_type=EntityType.CHANGE,
                entity_id=uuid4(),
                action=AuditAction.CREATE,
            )
    assert sqlstate(info.value) == INSUFFICIENT_PRIVILEGE
    assert "row-level security" in str(info.value)


async def test_other_company_chain_is_invisible(rw_engine: AsyncEngine) -> None:
    alfa, beta = uuid4(), uuid4()
    await write(rw_engine, beta, count=2)
    async with scoped(rw_engine, [alfa]) as session:
        visible = (
            await session.execute(
                text("SELECT count(*) FROM audit_log WHERE company_id = :c"), {"c": beta}
            )
        ).scalar_one()
        heads = (
            await session.execute(
                text("SELECT count(*) FROM audit_chain_heads WHERE company_id = :c"), {"c": beta}
            )
        ).scalar_one()
        with pytest.raises(AuditScopeError):
            await audit.verify_chain(session, beta)
    assert (visible, heads) == (0, 0)


async def test_unscoped_connection_sees_nothing(rw_engine: AsyncEngine) -> None:
    company = uuid4()
    await write(rw_engine, company)
    async with rw_engine.connect() as conn:
        count = (
            await conn.execute(
                text("SELECT count(*) FROM audit_log WHERE company_id = :c"), {"c": company}
            )
        ).scalar_one()
    assert count == 0


async def test_global_chain_writable_by_anyone_readable_only_explicitly(
    rw_engine: AsyncEngine, clean_audit: None
) -> None:
    await write(rw_engine, None, entity_type=EntityType.AUTH, action=AuditAction.LOGIN_FAILED)
    async with scoped(rw_engine, [uuid4()]) as session:
        hidden = (
            await session.execute(text("SELECT count(*) FROM audit_log WHERE company_id IS NULL"))
        ).scalar_one()
        with pytest.raises(AuditScopeError):
            await audit.verify_chain(session, None)
    async with scoped(rw_engine, global_read=True) as session:
        shown = (
            await session.execute(text("SELECT count(*) FROM audit_log WHERE company_id IS NULL"))
        ).scalar_one()
    assert (hidden, shown) == (0, 1)
    assert await verify(rw_engine, None) == audit.VerifyResult(True, 1, None)
