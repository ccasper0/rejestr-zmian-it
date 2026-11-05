"""``GET /api/v1/audit`` — browsing one audit chain (CLAUDE.md 8, ADR 0009).

Company chain: members with ``audit.read`` (auditor; app admin only with a membership);
global chain (``company_id`` omitted): app admins only. Entries are returned exactly as
stored (they re-hash to ``hash``), newest first, with filters and ``total``.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine

from app.domain.audit import Actor, AuditAction, EntityType, build_payload, compute_hash
from app.permissions import Role
from app.services import audit
from tests.factories import World, auth, grant, scoped
from tests.test_api_auth import assert_problem

pytestmark = pytest.mark.db

ACTOR = Actor(id=UUID(int=42), display="Zażółć Gęślą", roles=("editor",))


async def add_entries(engine: AsyncEngine, company_id: UUID, entity_id: UUID, count: int) -> None:
    async with scoped(engine, [company_id]) as session:
        for i in range(count):
            await audit.record(
                session,
                company_id=company_id,
                actor=ACTOR,
                entity_type=EntityType.CHANGE,
                entity_id=entity_id,
                action=AuditAction.UPDATE if i % 2 else AuditAction.CREATE,
                diff={"title": {"before": f"v{i}", "after": f"v{i + 1}"}},
                context={"i": i},
                ip="2001:db8::7",
                user_agent="pytest",
            )


async def get(api: AsyncClient, user: Any, **params: Any) -> Any:
    return await api.get("/api/v1/audit", params=params, headers=auth(user))


async def test_auditor_browses_own_company_chain_newest_first(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    change = uuid4()
    await add_entries(rw_engine, world.a.id, change, 5)
    response = await get(api, world.auditor, company_id=str(world.a.id), limit=3)
    assert response.status_code == 200, response.text
    body = response.json()
    items = body["items"]
    assert (body["limit"], body["offset"], len(items)) == (3, 0, 3)
    assert body["total"] >= 5
    seqs = [i["seq"] for i in items]
    assert seqs == sorted(seqs, reverse=True)
    assert {i["company_id"] for i in items} == {str(world.a.id)}
    newest = items[0]
    assert newest["entity_id"] == str(change)
    assert newest["actor_display"] == "Zażółć Gęślą"
    assert newest["ip_address"] == "2001:db8::7"
    assert newest["occurred_at"].endswith("Z")
    # Exactly what was hashed: the client can recompute the hash.
    payload = build_payload(
        company_id=UUID(newest["company_id"]),
        seq=newest["seq"],
        occurred_at=datetime.fromisoformat(newest["occurred_at"]),
        actor_id=UUID(newest["actor_id"]),
        actor_display=newest["actor_display"],
        actor_roles=newest["actor_roles"],
        ip_address=newest["ip_address"],
        user_agent=newest["user_agent"],
        request_id=UUID(newest["request_id"]),
        entity_type=newest["entity_type"],
        entity_id=UUID(newest["entity_id"]),
        action=newest["action"],
        diff=newest["diff"],
        context=newest["context"],
        prev_hash=newest["prev_hash"],
    )
    assert compute_hash(newest["prev_hash"], payload) == newest["hash"]
    assert items[1]["hash"] == newest["prev_hash"]

    second = (await get(api, world.auditor, company_id=str(world.a.id), limit=3, offset=3)).json()
    assert second["items"][0]["seq"] == items[-1]["seq"] - 1


async def test_filters(api: AsyncClient, world: World, rw_engine: AsyncEngine) -> None:
    change = uuid4()
    await add_entries(rw_engine, world.a.id, change, 4)
    base = {"company_id": str(world.a.id)}

    by_entity = (await get(api, world.auditor, **base, entity_id=str(change))).json()
    assert by_entity["total"] == 4
    by_action = (
        await get(api, world.auditor, **base, entity_id=str(change), action="create")
    ).json()
    assert by_action["total"] == 2
    assert {i["action"] for i in by_action["items"]} == {"create"}
    by_type = (await get(api, world.auditor, **base, entity_type="membership")).json()
    assert by_type["total"] >= 1
    assert {i["entity_type"] for i in by_type["items"]} == {"membership"}
    by_actor = (await get(api, world.auditor, **base, actor_id=str(ACTOR.id))).json()
    assert by_actor["total"] >= 4
    assert {i["actor_id"] for i in by_actor["items"]} == {str(ACTOR.id)}

    now = datetime.now(UTC)
    future = (
        await get(
            api,
            world.auditor,
            **base,
            occurred_from=(now + timedelta(hours=1)).isoformat(),
        )
    ).json()
    assert future["total"] == 0
    window = (
        await get(
            api,
            world.auditor,
            **base,
            entity_id=str(change),
            occurred_from=(now - timedelta(hours=1)).isoformat(),
            occurred_to=(now + timedelta(hours=1)).isoformat(),
        )
    ).json()
    assert window["total"] == 4


@pytest.mark.parametrize(
    "params",
    [
        {"entity_type": "nonsense"},
        {"action": "nonsense"},
        {"occurred_from": "2026-01-01T00:00:00"},  # no time zone
        {"limit": 0},
        {"limit": 501},
        {"offset": -1},
        {"company_id": "not-a-uuid"},
    ],
)
async def test_invalid_query_is_422(api: AsyncClient, world: World, params: dict[str, Any]) -> None:
    response = await get(api, world.auditor, **{"company_id": str(world.a.id), **params})
    assert_problem(response, 422, "request.validation_error")


async def test_empty_period_is_422(api: AsyncClient, world: World) -> None:
    response = await get(
        api,
        world.auditor,
        company_id=str(world.a.id),
        occurred_from="2026-02-01T00:00:00Z",
        occurred_to="2026-01-01T00:00:00Z",
    )
    assert_problem(response, 422, "audit.invalid_period")


async def test_global_chain_only_for_app_admin(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    response = await get(api, world.admin, entity_type="company")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] >= 2  # companies A and B were created
    assert {i["company_id"] for i in body["items"]} == {None}
    assert {i["entity_type"] for i in body["items"]} == {"company"}
    for persona in ("auditor", "approver", "editor", "viewer", "outsider", "nobody"):
        denied = await get(api, world.persona(persona))
        assert_problem(denied, 403, "auth.forbidden")


async def test_company_chain_requires_audit_read_role(api: AsyncClient, world: World) -> None:
    for persona in ("approver", "editor", "viewer"):
        response = await get(api, world.persona(persona), company_id=str(world.a.id))
        assert_problem(response, 403, "auth.forbidden")


async def test_admin_reads_any_company_chain(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    """Owner decision 2026-11-02 (ADR 0009 §3, ADR 0015 §7): the app admin reads the log of
    every company, also without membership (narrow read-only path), and only that chain."""
    without = await get(api, world.admin, company_id=str(world.b.id))
    assert without.status_code == 200, without.text
    assert {i["company_id"] for i in without.json()["items"]} == {str(world.b.id)}
    await grant(rw_engine, world.b, world.admin, Role.VIEWER)
    member = await get(api, world.admin, company_id=str(world.b.id))
    assert member.status_code == 200, member.text
    assert_problem(await get(api, world.admin, company_id=str(uuid4())), 404, "company.not_found")


async def test_auditor_never_sees_other_company_entries(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    secret = uuid4()
    await add_entries(rw_engine, world.b.id, secret, 2)
    foreign = await get(api, world.auditor, company_id=str(world.b.id), entity_id=str(secret))
    missing = await get(api, world.auditor, company_id=str(uuid4()))
    assert_problem(foreign, 404, "company.not_found")
    assert_problem(missing, 404, "company.not_found")
    own = (await get(api, world.auditor, company_id=str(world.a.id), entity_id=str(secret))).json()
    assert own["total"] == 0


async def test_list_entries_refuses_chain_outside_scope(rw_engine: AsyncEngine) -> None:
    async with scoped(rw_engine, [uuid4()]) as session:
        with pytest.raises(audit.AuditScopeError):
            await audit.list_entries(session, uuid4(), audit.EntryFilters(), limit=10, offset=0)
        with pytest.raises(audit.AuditScopeError):
            await audit.list_entries(session, None, audit.EntryFilters(), limit=10, offset=0)
