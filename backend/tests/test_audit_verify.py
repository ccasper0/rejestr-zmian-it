"""Audit chain verification: service, ``POST /api/v1/audit/verify`` and the CLI (CLAUDE.md 6.4).

Acceptance criteria of Etap 2 (§12): an entry modified by the table owner (triggers
disabled) is detected by ``verify`` — through the API and the CLI — with the correct
``first_broken_seq``; the verification itself is recorded in the audit log; concurrent
verifications (50 parallel API writers) keep the chain linear.
"""

from __future__ import annotations

import asyncio
import itertools
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app import cli
from app.domain.audit import GENESIS_HASH, Actor, AuditAction, EntityType
from app.main import create_app
from app.models import Company
from app.services import audit
from tests.conftest import DbUrls, make_settings
from tests.factories import World, auth, client_for, make_company, scoped, verify
from tests.test_api_auth import assert_problem
from tests.test_audit_log import _tamper, owner_exec

pytestmark = pytest.mark.db

SYSTEM = Actor.system()


async def chain_rows(engine: AsyncEngine, company_id: UUID | None) -> list[Any]:
    scope = [company_id] if company_id else []
    async with scoped(engine, scope, global_read=company_id is None) as session:
        where = "company_id IS NULL" if company_id is None else "company_id = :c"
        result = await session.execute(
            text(f"SELECT * FROM audit_log WHERE {where} ORDER BY seq"),  # noqa: S608
            {"c": company_id},
        )
        return list(result.all())


async def tamper_entry(owner_engine: AsyncEngine, company_id: UUID, seq: int) -> None:
    """The owner modifies an entry (triggers disabled) without recomputing its hash."""
    await _tamper(
        owner_engine,
        """UPDATE audit_log SET context = '{"forged": true}'
           WHERE company_id = :c AND seq = :s""",
        c=company_id,
        s=seq,
    )


async def tamper_last_hash(owner_engine: AsyncEngine, company_id: UUID | None) -> None:
    """Forge the hash of the last entry: the chain then REFUSES further appends."""
    where = "company_id IS NULL" if company_id is None else "company_id = :c"
    await _tamper(
        owner_engine,
        f"""UPDATE audit_log SET hash = repeat('f', 64)
            WHERE {where} AND seq = (SELECT max(seq) FROM audit_log WHERE {where})""",  # noqa: S608
        c=company_id,
    )


async def write_entries(engine: AsyncEngine, company_id: UUID, count: int) -> None:
    async with scoped(engine, [company_id]) as session:
        for i in range(count):
            await audit.record(
                session,
                company_id=company_id,
                actor=SYSTEM,
                entity_type=EntityType.CHANGE,
                entity_id=uuid4(),
                action=AuditAction.UPDATE,
                diff={"n": {"before": i, "after": i + 1}},
            )


@pytest.fixture
async def fresh_global_chain(owner_engine: AsyncEngine) -> AsyncIterator[None]:
    """Empty audit tables before and after: the global chain is shared by all tests."""
    statements = (
        "ALTER TABLE audit_log DISABLE TRIGGER USER",
        "ALTER TABLE audit_chain_heads DISABLE TRIGGER USER",
        "TRUNCATE audit_log, audit_chain_heads",
        "ALTER TABLE audit_log ENABLE TRIGGER USER",
        "ALTER TABLE audit_chain_heads ENABLE TRIGGER USER",
    )
    await owner_exec(owner_engine, *statements)
    yield
    await owner_exec(owner_engine, *statements)


# --------------------------------------------------------------------------- service


async def test_verify_and_record_appends_the_result_to_the_verified_chain(
    rw_engine: AsyncEngine,
) -> None:
    company = uuid4()
    await write_entries(rw_engine, company, 3)
    async with scoped(rw_engine, [company]) as session:
        outcome = await audit.verify_and_record(
            session, company, actor=SYSTEM, context={"source": "test"}
        )
    assert outcome.recorded_in == "chain"
    assert outcome.verification.result == audit.VerifyResult(True, 3, None)
    assert outcome.verification.head_seq == 3
    rows = await chain_rows(rw_engine, company)
    assert outcome.verification.head_hash == rows[2].hash
    entry = rows[-1]
    assert outcome.entry is not None
    assert (entry.seq, entry.hash) == (4, outcome.entry.hash)
    assert (entry.entity_type, entry.action, entry.entity_id) == ("audit", "verify", company)
    assert entry.context == {
        "source": "test",
        "chain": "company",
        "ok": True,
        "checked": 3,
        "first_broken_seq": None,
        "head_seq": 3,
        "head_hash": rows[2].hash,
    }
    assert entry.actor_id is None
    assert entry.actor_display == "system"
    # The verification entry is itself a valid link.
    assert await verify(rw_engine, company) == audit.VerifyResult(True, 4, None)


async def test_verify_with_head_of_an_empty_chain(rw_engine: AsyncEngine) -> None:
    company = uuid4()
    async with scoped(rw_engine, [company]) as session:
        verification = await audit.verify_chain_with_head(session, company)
    assert verification == audit.ChainVerification(
        company, audit.VerifyResult(True, 0, None), 0, GENESIS_HASH
    )


async def test_broken_chain_still_records_the_detection(
    rw_engine: AsyncEngine, owner_engine: AsyncEngine
) -> None:
    company = uuid4()
    await write_entries(rw_engine, company, 5)
    await tamper_entry(owner_engine, company, 2)
    async with scoped(rw_engine, [company]) as session:
        outcome = await audit.verify_and_record(session, company, actor=SYSTEM)
    assert outcome.verification.result == audit.VerifyResult(False, 1, 2)
    # The tail was not touched, so the chain accepts the append.
    assert outcome.recorded_in == "chain"
    entry = (await chain_rows(rw_engine, company))[-1]
    assert (entry.seq, entry.action) == (6, "verify")
    assert (entry.context["ok"], entry.context["first_broken_seq"]) == (False, 2)


async def test_chain_refusing_the_append_falls_back_to_the_global_chain(
    rw_engine: AsyncEngine, owner_engine: AsyncEngine, fresh_global_chain: None
) -> None:
    company = uuid4()
    await write_entries(rw_engine, company, 3)
    await tamper_last_hash(owner_engine, company)
    async with scoped(rw_engine, [company]) as session:
        outcome = await audit.verify_and_record(session, company, actor=SYSTEM)
    assert outcome.verification.result == audit.VerifyResult(False, 2, 3)
    assert outcome.recorded_in == "global"
    assert outcome.entry is not None
    assert outcome.entry.company_id is None
    assert len(await chain_rows(rw_engine, company)) == 3  # nothing appended there
    (entry,) = await chain_rows(rw_engine, None)
    assert entry.entity_id == company
    assert entry.context["target_company_id"] == str(company)
    assert entry.context["chain_append_failed"] is True
    assert entry.context["first_broken_seq"] == 3
    assert (await verify(rw_engine, None)).ok


async def test_unrecordable_result_is_returned_not_lost(
    rw_engine: AsyncEngine, owner_engine: AsyncEngine, fresh_global_chain: None
) -> None:
    async with scoped(rw_engine) as session:
        for _ in range(2):
            await audit.record(
                session,
                company_id=None,
                actor=SYSTEM,
                entity_type=EntityType.COMPANY,
                entity_id=uuid4(),
                action=AuditAction.CREATE,
            )
    await tamper_last_hash(owner_engine, None)
    async with scoped(rw_engine, global_read=True) as session:
        outcome = await audit.verify_and_record(session, None, actor=SYSTEM)
    assert outcome.verification.result == audit.VerifyResult(False, 1, 2)
    assert (outcome.recorded_in, outcome.entry) == (None, None)


async def test_verify_and_record_refuses_a_chain_outside_the_scope(rw_engine: AsyncEngine) -> None:
    async with scoped(rw_engine, [uuid4()]) as session:
        with pytest.raises(audit.AuditScopeError):
            await audit.verify_and_record(session, uuid4(), actor=SYSTEM)


# --------------------------------------------------------------------------- API


async def test_auditor_verifies_own_company_and_the_verification_is_audited(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    before = await chain_rows(rw_engine, world.a.id)
    response = await api.post(
        "/api/v1/audit/verify", params={"company_id": str(world.a.id)}, headers=auth(world.auditor)
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body == {
        "company_id": str(world.a.id),
        "chain": "company",
        "ok": True,
        "checked": len(before),
        "first_broken_seq": None,
        "head_seq": len(before),
        "head_hash": before[-1].hash,
        "verified_at": body["verified_at"],
        "recorded_in": "chain",
        "audit_entry": {
            "company_id": str(world.a.id),
            "seq": len(before) + 1,
            "hash": body["audit_entry"]["hash"],
        },
    }
    assert body["verified_at"].endswith("Z")
    entry = (await chain_rows(rw_engine, world.a.id))[-1]
    assert (entry.seq, entry.hash) == (len(before) + 1, body["audit_entry"]["hash"])
    assert (entry.entity_type, entry.action) == ("audit", "verify")
    assert entry.actor_id == world.auditor.id
    assert entry.actor_roles == ["auditor"]
    assert entry.context["source"] == "api"
    assert entry.context["admin_path"] is False
    assert entry.request_id == UUID(response.headers["X-Request-ID"])


async def test_api_detects_entry_modified_by_the_owner(
    api: AsyncClient, world: World, rw_engine: AsyncEngine, owner_engine: AsyncEngine
) -> None:
    company = world.a.id
    await write_entries(rw_engine, company, 4)
    rows = await chain_rows(rw_engine, company)
    target = rows[-2].seq
    await tamper_entry(owner_engine, company, target)

    response = await api.post(
        "/api/v1/audit/verify", params={"company_id": str(company)}, headers=auth(world.auditor)
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["ok"], body["first_broken_seq"], body["checked"]) == (False, target, target - 1)
    assert body["recorded_in"] == "chain"
    entry = (await chain_rows(rw_engine, company))[-1]
    assert (entry.context["ok"], entry.context["first_broken_seq"]) == (False, target)


async def test_api_reports_and_records_a_chain_that_refuses_appends(
    api: AsyncClient,
    world: World,
    rw_engine: AsyncEngine,
    owner_engine: AsyncEngine,
    fresh_global_chain: None,
) -> None:
    company = await make_company(rw_engine)
    await write_entries(rw_engine, company.id, 2)
    await tamper_last_hash(owner_engine, company.id)
    response = await api.post(
        "/api/v1/audit/verify", params={"company_id": str(company.id)}, headers=auth(world.admin)
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["ok"], body["first_broken_seq"], body["recorded_in"]) == (False, 2, "global")
    assert body["audit_entry"]["company_id"] is None
    entries = [e for e in await chain_rows(rw_engine, None) if e.action == "verify"]
    assert entries[-1].context["target_company_id"] == str(company.id)


async def test_admin_verifies_global_chain(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    response = await api.post("/api/v1/audit/verify", headers=auth(world.admin))
    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["chain"], body["company_id"], body["ok"]) == ("global", None, True)
    assert body["audit_entry"]["company_id"] is None
    entry = next(
        e for e in await chain_rows(rw_engine, None) if e.seq == body["audit_entry"]["seq"]
    )
    assert (entry.action, entry.entity_id, entry.actor_id) == ("verify", None, world.admin.id)
    assert entry.context["chain"] == "global"


async def test_admin_verifies_any_company_on_the_admin_path(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    response = await api.post(
        "/api/v1/audit/verify", params={"company_id": str(world.b.id)}, headers=auth(world.admin)
    )
    assert response.status_code == 200, response.text
    entry = (await chain_rows(rw_engine, world.b.id))[-1]
    assert (entry.action, entry.actor_id) == ("verify", world.admin.id)
    assert entry.actor_roles == ["app_admin"]
    assert entry.context["admin_path"] is True
    missing = await api.post(
        "/api/v1/audit/verify", params={"company_id": str(uuid4())}, headers=auth(world.admin)
    )
    assert_problem(missing, 404, "company.not_found")


@pytest.mark.parametrize("persona", ["auditor", "approver", "editor", "viewer", "outsider"])
async def test_only_app_admin_verifies_the_global_chain(
    api: AsyncClient, world: World, persona: str
) -> None:
    response = await api.post("/api/v1/audit/verify", headers=auth(world.persona(persona)))
    assert_problem(response, 403, "auth.forbidden")


async def test_fifty_parallel_api_verifications_keep_the_chain_linear(
    db_urls: DbUrls, world: World, rw_engine: AsyncEngine
) -> None:
    """50 concurrent requests, each appending to the same chain: no fork, seq continuous."""
    app: FastAPI = create_app(make_settings(database_url=db_urls.rw))
    before = len(await chain_rows(rw_engine, world.a.id))
    try:
        async with client_for(app) as client:
            responses = await asyncio.gather(
                *(
                    client.post(
                        "/api/v1/audit/verify",
                        params={"company_id": str(world.a.id)},
                        headers=auth(world.auditor),
                    )
                    for _ in range(50)
                )
            )
    finally:
        await app.state.db.dispose()
    assert [r.status_code for r in responses] == [200] * 50, [r.text for r in responses]
    assert all(r.json()["ok"] for r in responses)
    seqs = sorted(r.json()["audit_entry"]["seq"] for r in responses)
    assert seqs == list(range(before + 1, before + 51))

    rows = await chain_rows(rw_engine, world.a.id)
    assert [r.seq for r in rows] == list(range(1, before + 51))
    assert rows[0].prev_hash == GENESIS_HASH
    for previous, current in itertools.pairwise(rows):
        assert current.prev_hash == previous.hash
    assert len({r.prev_hash for r in rows}) == len(rows)  # no two entries share a parent
    assert await verify(rw_engine, world.a.id) == audit.VerifyResult(True, before + 50, None)


# --------------------------------------------------------------------------- CLI


@pytest.fixture
def cli_settings(db_urls: DbUrls, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "get_settings", lambda: make_settings(database_url=db_urls.rw))


async def run_cli(*argv: str) -> int:
    """``python -m app.cli`` in-process, in a thread (``asyncio.run`` needs one without a loop)."""
    return await asyncio.to_thread(cli.main, list(argv))


async def test_cli_verifies_company_chain_and_records_it(
    cli_settings: None, rw_engine: AsyncEngine, capsys: pytest.CaptureFixture[str]
) -> None:
    company: Company = await make_company(rw_engine, name="Spółka Żółta Gęś")
    await write_entries(rw_engine, company.id, 2)
    before = await chain_rows(rw_engine, company.id)

    code = await run_cli("verify-audit", "--company", company.prefix.lower())
    out = capsys.readouterr().out
    assert code == 0, out
    assert "jest spójny" in out
    assert f"zweryfikowano {len(before)} wpisów" in out
    assert "Spółka Żółta Gęś" in out

    entry = (await chain_rows(rw_engine, company.id))[-1]
    assert (entry.seq, entry.action, entry.entity_type) == (len(before) + 1, "verify", "audit")
    assert (entry.actor_id, entry.actor_display, entry.ip_address) == (None, "system", None)
    assert entry.context["source"] == "cli"
    assert entry.context["command"] == "verify-audit"
    assert entry.context["ok"] is True


async def test_cli_detects_entry_modified_by_the_owner(
    cli_settings: None,
    rw_engine: AsyncEngine,
    owner_engine: AsyncEngine,
    capsys: pytest.CaptureFixture[str],
) -> None:
    company = await make_company(rw_engine)
    await write_entries(rw_engine, company.id, 5)
    rows = await chain_rows(rw_engine, company.id)
    target = rows[3].seq
    await tamper_entry(owner_engine, company.id, target)

    code = await run_cli("verify-audit", "--company", company.prefix)
    out = capsys.readouterr().out
    assert code == 1
    assert "NARUSZENIE" in out
    assert f"seq {target}" in out
    entry = (await chain_rows(rw_engine, company.id))[-1]
    assert (entry.action, entry.context["first_broken_seq"]) == ("verify", target)


async def test_cli_verifies_global_chain(
    cli_settings: None, rw_engine: AsyncEngine, capsys: pytest.CaptureFixture[str]
) -> None:
    code = await run_cli("verify-audit", "--global")
    out = capsys.readouterr().out
    assert code == 0, out
    assert "Łańcuch audytu globalny jest spójny" in out
    entry = (await chain_rows(rw_engine, None))[-1]
    assert (entry.action, entry.context["chain"], entry.entity_id) == ("verify", "global", None)


async def test_cli_global_chain_refusing_append_is_reported(
    cli_settings: None,
    rw_engine: AsyncEngine,
    owner_engine: AsyncEngine,
    fresh_global_chain: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    await make_company(rw_engine)  # one global entry
    await tamper_last_hash(owner_engine, None)
    code = await run_cli("verify-audit", "--global")
    captured = capsys.readouterr()
    assert code == 1
    assert "seq 1" in captured.out
    assert "nie udało się zapisać" in captured.err


async def test_cli_company_chain_refusing_append_falls_back_to_global(
    cli_settings: None,
    rw_engine: AsyncEngine,
    owner_engine: AsyncEngine,
    fresh_global_chain: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    company = await make_company(rw_engine)
    await write_entries(rw_engine, company.id, 2)
    await tamper_last_hash(owner_engine, company.id)
    code = await run_cli("verify-audit", "--company", company.prefix)
    out = capsys.readouterr().out
    assert code == 1
    assert "łańcuchu globalnym" in out


@pytest.mark.parametrize(
    ("prefix", "message"),
    [("ZZZZZZZZ", "nie znaleziono spółki"), ("A1", "nieprawidłowy prefiks")],
)
async def test_cli_unknown_or_invalid_prefix(
    cli_settings: None, capsys: pytest.CaptureFixture[str], prefix: str, message: str
) -> None:
    code = await run_cli("verify-audit", "--company", prefix)
    assert code == 1
    assert message in capsys.readouterr().err.lower()


async def test_cli_database_error_is_exit_code_1(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    unreachable = "postgresql+asyncpg://app_rw:x@127.0.0.1:1/none"
    monkeypatch.setattr(cli, "get_settings", lambda: make_settings(database_url=unreachable))
    code = await run_cli("verify-audit", "--global")
    assert code == 1
    assert "nie powiodła się" in capsys.readouterr().err
