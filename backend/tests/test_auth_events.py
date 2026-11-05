"""Authentication events in the audit log (CLAUDE.md 6.5, ADR 0010).

- ``login``: the first request with a given token, exactly once across API processes;
- ``login_failed``: every failure counted; entries at the 1st, 2nd, 4th, ... failure per
  window and bucket, plus an exact summary of every closed window (no failure is lost,
  a flood does not flood the log); overflow bucket for many sources;
- ``access_denied``: 403 and the 404 for a foreign company, with ``target_company_id``;
- nothing derived from an unverified token, and no token, is stored.
"""

from __future__ import annotations

import asyncio
import math
import secrets
from collections.abc import AsyncIterator
from datetime import timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.auth.dev import issue_dev_token
from app.auth.tokens import TokenClaims
from app.db import Database, run_in_separate_transaction
from app.domain.audit import Actor
from app.main import create_app
from app.request_context import ClientInfo, _client_info
from app.services import auth_events
from app.services.auth_events import FailureReason
from app.worker import auth_maintenance
from tests.conftest import DEV_SECRET, DbUrls, make_settings
from tests.factories import World, auth, make_user, scoped, verify
from tests.test_api_auth import assert_problem

pytestmark = pytest.mark.db


def random_ip() -> str:
    """A TEST-NET-3 address unique enough to give every test its own failure bucket."""
    return f"203.0.{secrets.randbelow(256)}.{secrets.randbelow(254) + 1}"


def client_from(app: FastAPI, ip: str) -> AsyncClient:
    return AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False, client=(ip, 40000)),
        base_url="http://test",
    )


async def global_entries(engine: AsyncEngine, where: str, **params: Any) -> list[Any]:
    async with scoped(engine, global_read=True) as session:
        result = await session.execute(
            text(f"SELECT * FROM audit_log WHERE company_id IS NULL AND {where} ORDER BY seq"),  # noqa: S608
            params,
        )
        return list(result.all())


async def windows_of(engine: AsyncEngine, network: str) -> list[Any]:
    async with AsyncSession(engine) as session:
        result = await session.execute(
            text(
                "SELECT * FROM auth_failure_windows WHERE client_network = :n "
                "ORDER BY window_start, bucket"
            ),
            {"n": network},
        )
        return list(result.all())


@pytest.fixture
async def database(db_urls: DbUrls) -> AsyncIterator[Database]:
    db = Database(db_urls.rw)
    yield db
    await db.dispose()


# --------------------------------------------------------------------------- login


async def test_login_is_recorded_once_per_token(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    user = await make_user(rw_engine)
    headers = auth(user)
    for _ in range(3):
        assert (await api.get("/api/v1/me", headers=headers)).status_code == 200
    logins = await global_entries(rw_engine, "action = 'login' AND entity_id = :u", u=user.id)
    assert len(logins) == 1
    (entry,) = logins
    assert (entry.entity_type, entry.actor_id, entry.actor_display) == (
        "auth",
        user.id,
        user.display_name,
    )
    assert entry.context["issuer"] == "urn:rejestr:dev-auth"
    assert len(entry.context["token_fingerprint"]) == 64
    assert entry.context["token_expires_at"].endswith("Z")
    token = headers["Authorization"].removeprefix("Bearer ")
    assert token not in repr(tuple(entry))

    # A new token (later iat/exp) is a new login.
    later = issue_dev_token(DEV_SECRET, user.external_id)[0]
    await asyncio.sleep(1.05)
    newer = issue_dev_token(DEV_SECRET, user.external_id)[0]
    assert later != newer
    assert (await api.get("/api/v1/me", headers={"Authorization": f"Bearer {newer}"})).is_success
    assert (
        len(await global_entries(rw_engine, "action = 'login' AND entity_id = :u", u=user.id)) == 2
    )


async def test_admin_login_carries_the_global_role(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    await api.get("/api/v1/me", headers=auth(world.admin))
    (entry,) = await global_entries(
        rw_engine, "action = 'login' AND entity_id = :u", u=world.admin.id
    )
    assert entry.actor_roles == ["app_admin"]


async def test_concurrent_first_requests_in_several_processes_log_in_once(
    db_urls: DbUrls, rw_engine: AsyncEngine
) -> None:
    """Two application instances (= two API processes, own pools) and 20 parallel requests."""
    user = await make_user(rw_engine)
    headers = auth(user)
    apps = [create_app(make_settings(database_url=db_urls.rw)) for _ in range(2)]
    try:
        clients = [client_from(app, "198.51.100.10") for app in apps]
        responses = await asyncio.gather(
            *(clients[i % 2].get("/api/v1/me", headers=headers) for i in range(20))
        )
        for client in clients:
            await client.aclose()
    finally:
        for app in apps:
            await app.state.db.dispose()
    assert [r.status_code for r in responses] == [200] * 20
    logins = await global_entries(rw_engine, "action = 'login' AND entity_id = :u", u=user.id)
    assert len(logins) == 1
    async with AsyncSession(rw_engine) as session:
        rows = (
            await session.execute(
                text("SELECT count(*) FROM auth_logins WHERE user_id = :u"), {"u": user.id}
            )
        ).scalar_one()
    assert rows == 1
    assert (await verify(rw_engine, None)).ok


def test_token_fingerprint_uses_public_claims_only() -> None:
    base = {"iss": "i", "sub": "s", "aud": ["a", "b"], "iat": 1, "exp": 2.5, "nonce": "x"}
    claims = TokenClaims(subject="s", issuer="i", email="", display_name="s", raw=base)
    other_nonce = TokenClaims(
        subject="s", issuer="i", email="", display_name="s", raw={**base, "nonce": "y"}
    )
    other_iat = TokenClaims(
        subject="s", issuer="i", email="", display_name="s", raw={**base, "iat": 3}
    )
    fingerprint = auth_events.token_fingerprint(claims)
    assert len(fingerprint) == 64
    assert auth_events.token_fingerprint(other_nonce) == fingerprint
    assert auth_events.token_fingerprint(other_iat) != fingerprint


async def test_register_login_requires_its_own_transaction(
    rw_engine: AsyncEngine, world: World
) -> None:
    claims = TokenClaims(subject="s", issuer="i", email="", display_name="s", raw={"sub": "s"})
    async with scoped(rw_engine) as session:
        with pytest.raises(RuntimeError, match="own transaction"):
            await auth_events.register_login(session, user=world.viewer, claims=claims)


async def test_login_without_exp_is_kept_for_the_retention_period(
    database: Database, rw_engine: AsyncEngine
) -> None:
    user = await make_user(rw_engine)
    claims = TokenClaims(
        subject=user.external_id,
        issuer="i",
        email="",
        display_name="x",
        raw={"sub": user.external_id, "jti": str(uuid4()), "iat": "not-a-number"},
    )
    recorded = await run_in_separate_transaction(
        database, lambda s: auth_events.register_login(s, user=user, claims=claims)
    )
    again = await run_in_separate_transaction(
        database, lambda s: auth_events.register_login(s, user=user, claims=claims)
    )
    assert (recorded, again) == (True, False)
    (entry,) = await global_entries(rw_engine, "action = 'login' AND entity_id = :u", u=user.id)
    assert entry.context["token_issued_at"] is None


# --------------------------------------------------------------------------- login_failed


async def test_failed_logins_are_counted_and_sampled(
    db_app: FastAPI, rw_engine: AsyncEngine
) -> None:
    ip = random_ip()
    async with client_from(db_app, ip) as client:
        for _ in range(9):
            response = await client.get(
                "/api/v1/me", headers={"Authorization": "Bearer not.a.token-SECRET"}
            )
            assert_problem(response, 401, "auth.invalid_token")

    windows = await windows_of(rw_engine, f"{ip}/32")
    assert sum(w.count for w in windows) == 9
    entries = await global_entries(
        rw_engine,
        "action = 'login_failed' AND context->>'client_network' = :n",
        n=f"{ip}/32",
    )
    for window in windows:
        in_window = [
            e
            for e in entries
            if e.context["window_start"]
            == window.window_start.isoformat().replace("+00:00", ".000000Z")
        ]
        expected = [2**k for k in range(int(math.log2(window.count)) + 1)]
        assert [e.context["count_in_window"] for e in in_window] == expected
        assert window.logged_count == expected[-1]
    first = entries[0]
    assert (first.actor_id, first.actor_display, first.entity_id) == (None, "system", None)
    assert first.ip_address is not None
    assert first.context["reason"] == "invalid_token"
    assert first.context["authenticated"] is False
    assert first.context["path"] == "/api/v1/me"
    assert first.context["method"] == "GET"
    assert "detail" in first.context
    assert all("SECRET" not in repr(tuple(e)) for e in entries)
    assert (await verify(rw_engine, None)).ok


async def test_missing_token_and_unknown_user_are_recorded(
    db_app: FastAPI, rw_engine: AsyncEngine
) -> None:
    ip = random_ip()
    unknown = f"ghost-{uuid4()}"
    async with client_from(db_app, ip) as client:
        assert_problem(await client.get("/api/v1/me"), 401, "auth.invalid_token")
        token = issue_dev_token(DEV_SECRET, unknown)[0]
        assert_problem(
            await client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"}),
            401,
            "auth.invalid_token",
        )
    entries = await global_entries(
        rw_engine,
        "action = 'login_failed' AND context->>'client_network' = :n",
        n=f"{ip}/32",
    )
    assert {e.context["reason"] for e in entries} == {"missing_token", "unknown_user"}
    ghost = next(e for e in entries if e.context["reason"] == "unknown_user")
    assert ghost.context["subject"] == unknown  # from a VERIFIED token only


async def test_inactive_user_is_a_failed_login_of_that_user(
    db_app: FastAPI, rw_engine: AsyncEngine
) -> None:
    user = await make_user(rw_engine, active=False)
    async with client_from(db_app, random_ip()) as client:
        response = await client.get("/api/v1/me", headers=auth(user))
    assert_problem(response, 403, "auth.user_inactive")
    (entry,) = await global_entries(
        rw_engine, "action = 'login_failed' AND entity_id = :u", u=user.id
    )
    assert (entry.actor_id, entry.context["reason"]) == (user.id, "user_inactive")
    assert entry.context["authenticated"] is True
    assert not await global_entries(rw_engine, "action = 'login' AND entity_id = :u", u=user.id)


async def test_ipv6_clients_are_bucketed_per_64() -> None:
    assert auth_events.client_network("2001:db8:1:2:aaaa::1") == "2001:db8:1:2::/64"
    assert auth_events.client_network("192.0.2.1") == "192.0.2.1/32"
    assert auth_events.client_network(None) is None
    assert auth_events.client_network("garbage") is None


async def _fail(
    database: Database, ip: str, *, window: int, max_buckets: int
) -> auth_events.FailureCount:
    token = _client_info.set(ClientInfo(ip=ip, user_agent="pytest"))
    try:
        return await run_in_separate_transaction(
            database,
            lambda s: auth_events.record_login_failure(
                s,
                reason=FailureReason.INVALID_TOKEN,
                window_seconds=window,
                max_buckets=max_buckets,
                detail="x" * 500,
            ),
        )
    finally:
        _client_info.reset(token)


async def test_many_sources_are_folded_into_an_overflow_bucket(
    database: Database, rw_engine: AsyncEngine
) -> None:
    # A window length used by no other test: its buckets are this test's only.
    window = 7919
    for _attempt in range(2):  # retried once if the window rolled over meanwhile
        results = [
            await _fail(database, random_ip(), window=window, max_buckets=3) for _ in range(6)
        ]
        if len({r.window_start for r in results}) == 1:
            break
    assert [r.overflow for r in results][-3:] == [True, True, True]
    overflow = [r for r in results if r.overflow]
    assert {r.bucket for r in overflow} == {"invalid_token|overflow"}
    assert [r.count for r in overflow][-2:] == [overflow[-2].count, overflow[-2].count + 1]
    entries = await global_entries(
        rw_engine, "action = 'login_failed' AND (context->>'window_seconds')::int = 7919"
    )
    assert any(e.context["overflow"] for e in entries)
    assert all(len(e.context["detail"]) == 200 for e in entries)


async def test_closed_windows_are_summarized_exactly_then_purged(
    database: Database, rw_engine: AsyncEngine, owner_engine: AsyncEngine
) -> None:
    ip = random_ip()
    for _ in range(5):
        await _fail(database, ip, window=300, max_buckets=1000)
    network = f"{ip}/32"
    # Close the window: move it into the past (as the application role may).
    async with AsyncSession(rw_engine) as session, session.begin():
        await session.execute(
            text(
                "UPDATE auth_failure_windows SET window_start = window_start - interval '1 hour' "
                "WHERE client_network = :n"
            ),
            {"n": network},
        )
    (window,) = await windows_of(rw_engine, network)
    assert (window.count, window.logged_count) == (5, 4)  # entries at 1, 2, 4

    report = await auth_maintenance({"db": database})
    assert report["summaries"] >= 1
    summaries = await global_entries(
        rw_engine,
        "action = 'login_failed' AND context->>'client_network' = :n "
        "AND (context->>'summary')::boolean",
        n=network,
    )
    (summary,) = summaries
    assert summary.context["count_in_window"] == 5
    assert summary.context["not_recorded_individually"] == 1
    assert (summary.actor_display, summary.ip_address) == ("system", None)
    (window,) = await windows_of(rw_engine, network)
    assert window.logged_count == 5

    # Nothing pending: a second run writes nothing for it.
    await auth_maintenance({"db": database})
    assert (
        len(
            await global_entries(
                rw_engine,
                "action = 'login_failed' AND context->>'client_network' = :n "
                "AND (context->>'summary')::boolean",
                n=network,
            )
        )
        == 1
    )

    # Older than the retention: purged (the audit log keeps the evidence).
    async with AsyncSession(rw_engine) as session, session.begin():
        await session.execute(
            text(
                "UPDATE auth_failure_windows SET window_start = window_start - interval '2 days' "
                "WHERE client_network = :n"
            ),
            {"n": network},
        )
    user = await make_user(rw_engine)
    claims = TokenClaims(
        subject=user.external_id,
        issuer="i",
        email="",
        display_name="x",
        raw={"sub": user.external_id, "exp": 1_000_000_000, "jti": str(uuid4())},
    )
    await run_in_separate_transaction(
        database, lambda s: auth_events.register_login(s, user=user, claims=claims)
    )
    report = await auth_maintenance({"db": database})
    assert report["windows_purged"] >= 1
    assert report["logins_purged"] >= 1
    assert await windows_of(rw_engine, network) == []
    assert (await verify(rw_engine, None)).ok


async def test_flood_is_bounded_but_counted(database: Database, rw_engine: AsyncEngine) -> None:
    ip = random_ip()
    results = [await _fail(database, ip, window=86400, max_buckets=1000) for _ in range(40)]
    recorded = [r.count for r in results if r.recorded]
    windows = {r.window_start for r in results}
    if len(windows) == 1:
        assert recorded == [1, 2, 4, 8, 16, 32]
    assert sum(w.count for w in await windows_of(rw_engine, f"{ip}/32")) == 40


async def test_maintenance_report_shape() -> None:
    report = auth_events.MaintenanceReport(1, 2, 3)
    assert report.as_dict() == {"summaries": 1, "logins_purged": 2, "windows_purged": 3}
    assert timedelta(days=1) == auth_events.RETENTION


# --------------------------------------------------------------------------- access_denied


async def test_foreign_company_404_is_recorded_with_target(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    response = await api.get(f"/api/v1/companies/{world.b.id}/members", headers=auth(world.viewer))
    assert_problem(response, 404, "company.not_found")
    (entry,) = await global_entries(
        rw_engine, "action = 'access_denied' AND actor_id = :u", u=world.viewer.id
    )
    assert entry.entity_type == "auth"
    assert entry.entity_id == world.viewer.id
    assert entry.context == {
        "status": 404,
        "reason": "no_membership",
        "target_company_id": str(world.b.id),
        "method": "GET",
        "path": f"/api/v1/companies/{world.b.id}/members",
    }
    assert entry.request_id == UUID(response.headers["X-Request-ID"])
    # The foreign company's chain is untouched (the entry is global, ADR 0006 §7).
    async with scoped(rw_engine, [world.b.id]) as session:
        actions = (
            (
                await session.execute(
                    text("SELECT DISTINCT action FROM audit_log WHERE company_id = :b"),
                    {"b": world.b.id},
                )
            )
            .scalars()
            .all()
        )
    assert "access_denied" not in actions


async def test_forbidden_action_is_recorded(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    response = await api.post(
        "/api/v1/companies", json={"name": "X", "prefix": "XQXQ"}, headers=auth(world.editor)
    )
    assert_problem(response, 403, "auth.forbidden")
    response = await api.post(
        "/api/v1/audit/verify", params={"company_id": str(world.a.id)}, headers=auth(world.viewer)
    )
    assert_problem(response, 403, "auth.forbidden")
    editor = await global_entries(
        rw_engine, "action = 'access_denied' AND actor_id = :u", u=world.editor.id
    )
    viewer = await global_entries(
        rw_engine, "action = 'access_denied' AND actor_id = :u", u=world.viewer.id
    )
    assert [(e.context["status"], e.context["reason"]) for e in editor] == [(403, "company.manage")]
    assert editor[0].context["target_company_id"] is None
    assert [(e.context["status"], e.context["reason"]) for e in viewer] == [(403, "audit.verify")]
    assert viewer[0].context["target_company_id"] == str(world.a.id)
    assert viewer[0].actor_roles == ["viewer"]


async def test_admin_company_endpoint_denial_is_recorded(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    response = await api.post(
        f"/api/v1/companies/{world.a.id}/archive", headers=auth(world.approver)
    )
    assert_problem(response, 403, "auth.forbidden")
    (entry,) = await global_entries(
        rw_engine, "action = 'access_denied' AND actor_id = :u", u=world.approver.id
    )
    assert entry.context["target_company_id"] == str(world.a.id)


async def test_access_denied_requires_its_own_transaction(rw_engine: AsyncEngine) -> None:
    async with scoped(rw_engine) as session:
        with pytest.raises(RuntimeError, match="own transaction"):
            await auth_events.record_access_denied(
                session,
                actor=Actor.system(),
                status=403,
                reason="x",
                company_id=None,
            )


# --------------------------------------------------------------------------- pool exhaustion


async def test_denials_do_not_deadlock_a_single_connection_pool(
    db_urls: DbUrls, world: World, rw_engine: AsyncEngine
) -> None:
    """Regression (Etap 2 review): recording a denial while the request holds a connection.

    With ONE main connection and no overflow, the request transaction holds the only
    main-pool connection when the denial is recorded; taken from the same pool, the
    separate transaction would wait for it forever (pool self-deadlock, ADR 0010 §5).
    The auxiliary pool (also a single connection here) breaks the cycle: every request
    gets its 404/403 and every denial is in the log.
    """
    app = create_app(
        make_settings(
            database_url=db_urls.rw,
            db_pool_size=1,
            db_max_overflow=0,
            db_aux_pool_size=1,
            db_aux_max_overflow=0,
            db_pool_timeout_seconds=5,
        )
    )
    foreign = f"/api/v1/companies/{world.b.id}/members"
    try:
        async with client_from(app, random_ip()) as client:
            requests = [
                *(client.get(foreign, headers=auth(world.viewer)) for _ in range(4)),
                *(
                    client.post(
                        "/api/v1/audit/verify",
                        params={"company_id": str(world.a.id)},
                        headers=auth(world.editor),
                    )
                    for _ in range(4)
                ),
            ]
            responses = await asyncio.wait_for(asyncio.gather(*requests), 30)
    finally:
        await app.state.db.dispose()
    assert [r.status_code for r in responses] == [404] * 4 + [403] * 4, [r.text for r in responses]
    viewer = await global_entries(
        rw_engine, "action = 'access_denied' AND actor_id = :u", u=world.viewer.id
    )
    editor = await global_entries(
        rw_engine, "action = 'access_denied' AND actor_id = :u", u=world.editor.id
    )
    assert [e.context["status"] for e in viewer] == [404] * 4
    assert [e.context["status"] for e in editor] == [403] * 4
    assert (await verify(rw_engine, None)).ok


async def test_separate_transactions_use_the_auxiliary_pool(database: Database) -> None:
    async def which_pool(session: AsyncSession) -> object:
        return session.bind

    assert await run_in_separate_transaction(database, which_pool) is database.aux_engine


# --------------------------------------------------------------------------- maintenance batches


async def _backlog(engine: AsyncEngine, windows: int) -> str:
    """``windows`` closed windows with unrecorded failures, all in one fresh network."""
    network = f"198.18.{secrets.randbelow(256)}.{secrets.randbelow(254) + 1}/32"
    async with AsyncSession(engine) as session, session.begin():
        for i in range(windows):
            await session.execute(
                text(
                    "INSERT INTO auth_failure_windows (window_start, window_seconds, bucket, "
                    "reason, client_network, count, logged_count, first_at, last_at) VALUES "
                    "(date_trunc('hour', now()) - make_interval(hours => :h), 300, :b, "
                    "'invalid_token', :n, 3, 1, now(), now())"
                ),
                {"h": 2 + i, "b": f"invalid_token|{network}|-", "n": network},
            )
    return network


async def test_maintenance_commits_each_batch(database: Database, rw_engine: AsyncEngine) -> None:
    network = await _backlog(rw_engine, 5)
    report = await auth_events.maintenance(database.sessionmaker, batch=2)
    assert report.summaries >= 5
    async with scoped(rw_engine, global_read=True) as session:
        xmins = (
            (
                await session.execute(
                    text(
                        "SELECT DISTINCT xmin::text FROM audit_log WHERE company_id IS NULL "
                        "AND context->>'client_network' = :n"
                    ),
                    {"n": network},
                )
            )
            .scalars()
            .all()
        )
    assert len(xmins) >= 3  # 5 summaries in batches of 2: at least 3 transactions
    assert all(w.logged_count == w.count for w in await windows_of(rw_engine, network))
    with pytest.raises(ValueError, match="positive"):
        await auth_events.maintenance(database.sessionmaker, batch=0)


async def test_other_global_writers_proceed_during_maintenance(
    database: Database, rw_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A large backlog must not hold the global chain head for the whole flush."""
    from app.services import audit as audit_service

    network = await _backlog(rw_engine, 12)
    original = audit_service.record

    async def slow_record(*args: Any, **kwargs: Any) -> Any:
        result = await original(*args, **kwargs)
        await asyncio.sleep(0.05)  # ~0.6 s for the backlog, ~0.1 s per batch of 2
        return result

    monkeypatch.setattr(auth_events.audit, "record", slow_record)
    flushing = asyncio.create_task(auth_events.maintenance(database.sessionmaker, batch=2))
    await asyncio.sleep(0.1)  # the flush is under way
    written = 0
    try:
        while not flushing.done():
            async with AsyncSession(rw_engine) as session, session.begin():
                await session.execute(text("SET LOCAL lock_timeout = '400ms'"))
                await scoped_global(session)
                await original(
                    session,
                    company_id=None,
                    actor=Actor.system(),
                    entity_type=auth_events.EntityType.AUTH,
                    entity_id=None,
                    action=auth_events.AuditAction.LOGIN_FAILED,
                    context={"probe": True},
                )
            written += 1
            await asyncio.sleep(0.02)
    finally:
        await flushing
    assert written >= 1
    assert all(w.logged_count == w.count for w in await windows_of(rw_engine, network))
    assert (await verify(rw_engine, None)).ok


async def scoped_global(session: AsyncSession) -> None:
    from app.db import apply_company_scope

    await apply_company_scope(session, [])


async def test_admin_path_404_is_recorded(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    """The admin path answers 404 for a missing company - and records it like any denial."""
    missing = uuid4()
    calls = [
        ("PATCH", f"/api/v1/companies/{missing}", {"is_ksc_entity": True}, None),
        ("POST", f"/api/v1/companies/{missing}/archive", None, None),
        ("GET", f"/api/v1/companies/{missing}/members", None, None),
        ("POST", "/api/v1/audit/verify", None, {"company_id": str(missing)}),
    ]
    for method, url, body, params in calls:
        response = await api.request(
            method, url, json=body, params=params, headers=auth(world.admin)
        )
        assert_problem(response, 404, "company.not_found")
    entries = await global_entries(
        rw_engine,
        "action = 'access_denied' AND actor_id = :u AND context->>'target_company_id' = :c",
        u=world.admin.id,
        c=str(missing),
    )
    assert [(e.context["status"], e.context["reason"]) for e in entries] == [(404, "not_found")] * 4
    assert [e.context["method"] for e in entries] == ["PATCH", "POST", "GET", "POST"]


async def test_windows_of_different_length_never_share_a_counter(
    database: Database, rw_engine: AsyncEngine
) -> None:
    """Instances configured with different AUTH_FAILURE_WINDOW_SECONDS (Etap 2 review)."""
    from datetime import UTC, datetime

    start = datetime(2000, 1, 1, tzinfo=UTC)  # aligned to both 300 s and 600 s
    bucket = f"invalid_token|{random_ip()}/32|-"

    async def bump(session: AsyncSession, seconds: int) -> int:
        _, count, _ = await auth_events._increment(
            session,
            window_start=start,
            window_seconds=seconds,
            bucket=bucket,
            reason="invalid_token",
            network=None,
            user_id=None,
        )
        return count

    async with AsyncSession(rw_engine) as session, session.begin():
        counts = [await bump(session, 300), await bump(session, 600), await bump(session, 300)]
        rows = (
            await session.execute(
                text(
                    "SELECT window_seconds, count FROM auth_failure_windows "
                    "WHERE bucket = :b ORDER BY window_seconds"
                ),
                {"b": bucket},
            )
        ).all()
        await session.execute(
            text("DELETE FROM auth_failure_windows WHERE bucket = :b"), {"b": bucket}
        )
    assert counts == [1, 1, 2]
    assert [tuple(r) for r in rows] == [(300, 2), (600, 1)]


async def test_immediate_entries_are_capped_per_window_but_summarized(
    database: Database, rw_engine: AsyncEngine
) -> None:
    """Many sources: at most N immediate entries per window; the rest only in summaries."""
    window = 7907  # a window length used by no other test

    async def fail(ip: str) -> auth_events.FailureCount:
        token = _client_info.set(ClientInfo(ip=ip, user_agent="pytest"))
        try:
            return await run_in_separate_transaction(
                database,
                lambda s: auth_events.record_login_failure(
                    s,
                    reason=FailureReason.MISSING_TOKEN,
                    window_seconds=window,
                    max_buckets=1000,
                    max_immediate_entries=4,
                ),
            )
        finally:
            _client_info.reset(token)

    for _attempt in range(2):  # retried once if the window rolled over meanwhile
        repeated = random_ip()
        # One source failing twice (entries at 1 and 2 = 2 entries), then new sources.
        results = [await fail(repeated), await fail(repeated)]
        results += [await fail(random_ip()) for _ in range(5)]
        if len({r.window_start for r in results}) == 1:
            break
    assert [r.recorded for r in results] == [True, True, True, True, False, False, False]
    assert [r.capped for r in results] == [False] * 4 + [True] * 3

    # Close the window: every capped failure gets its summary entry.
    async with AsyncSession(rw_engine) as session, session.begin():
        await session.execute(
            text(
                "UPDATE auth_failure_windows SET window_start = window_start - interval '3 hours' "
                "WHERE window_seconds = :w AND window_start = :s"
            ),
            {"w": window, "s": results[0].window_start},
        )
    await auth_maintenance({"db": database})
    async with AsyncSession(rw_engine) as session:
        pending = (
            await session.execute(
                text(
                    "SELECT count(*) FROM auth_failure_windows "
                    "WHERE window_seconds = :w AND logged_count < count"
                ),
                {"w": window},
            )
        ).scalar_one()
    assert pending == 0
    summaries = await global_entries(
        rw_engine,
        "action = 'login_failed' AND (context->>'window_seconds')::int = :w "
        "AND (context->>'summary')::boolean",
        w=window,
    )
    assert sum(e.context["not_recorded_individually"] for e in summaries) >= 3
