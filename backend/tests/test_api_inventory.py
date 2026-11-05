"""Company configuration API: available categories (PUT, admin) and the CI inventory.

Audit: both write to the chain OF THE COMPANY (ADR 0011). Isolation (404 for another
company's resources) and the permission matrix are in ``tests/test_isolation_api.py`` and
``tests/test_rbac_matrix.py``.
"""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine

from app.db import SessionDep
from app.main import create_app
from app.permissions import Action, Role, require_company
from app.services import configuration_items
from tests.conftest import DbUrls, make_settings
from tests.factories import (
    SYSTEM,
    World,
    audit_entries,
    auth,
    client_for,
    grant,
    make_category,
    make_ci,
    make_ci_type,
    make_company,
    make_user,
    scoped,
    verify,
)
from tests.test_api_auth import assert_problem

pytestmark = pytest.mark.db


def categories_url(company_id: UUID) -> str:
    return f"/api/v1/companies/{company_id}/categories"


def ci_url(company_id: UUID, ci_id: UUID | None = None) -> str:
    base = f"/api/v1/companies/{company_id}/ci"
    return base if ci_id is None else f"{base}/{ci_id}"


# --------------------------------------------------------------------------- company categories


async def test_admin_sets_company_categories_with_audit(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    net = await make_category(rw_engine, name="Sieć")
    fw = await make_category(rw_engine, name="Firewall")
    url = categories_url(world.a.id)
    body = {
        "categories": [
            {"category_id": str(net.id)},
            {"category_id": str(fw.id), "approver_override_id": str(world.approver.id)},
        ]
    }
    first = await api.put(url, json=body, headers=auth(world.admin))
    assert first.status_code == 200, first.text
    items = {i["code"]: i for i in first.json()["items"]}
    assert set(items) == {net.code, fw.code}
    assert items[fw.code]["approver_override_id"] == str(world.approver.id)
    assert items[net.code]["approver_override_id"] is None
    assert items[net.code]["requires_approval"] is True

    # Same list again: nothing changes, no audit entry.
    again = await api.put(url, json=body, headers=auth(world.admin))
    assert again.json() == first.json()

    # Withdraw NET, clear the FW override, add the world category.
    changed = await api.put(
        url,
        json={
            "categories": [
                {"category_id": str(fw.id)},
                {"category_id": str(world.category.id)},
            ]
        },
        headers=auth(world.admin),
    )
    assert {i["code"] for i in changed.json()["items"]} == {fw.code, world.category.code}

    # Members read it (every role).
    listed = await api.get(url, headers=auth(world.viewer))
    assert listed.json() == changed.json()

    entries = await audit_entries(rw_engine, world.a.id)
    entries = [e for e in entries if e.entity_type == "company_category"]
    assert len(entries) == 2
    assert {e.company_id for e in entries} == {world.a.id}  # the company chain
    assert {e.actor_roles == ["app_admin"] for e in entries} == {True}
    assert entries[0].diff == {
        net.code: {"before": None, "after": {"approver_override_id": None}},
        fw.code: {"before": None, "after": {"approver_override_id": str(world.approver.id)}},
    }
    assert entries[0].context == {
        "added": sorted([net.code, fw.code]),
        "removed": [],
        "override_changed": [],
    }
    assert entries[1].diff == {
        net.code: {"before": {"approver_override_id": None}, "after": None},
        fw.code: {
            "before": {"approver_override_id": str(world.approver.id)},
            "after": {"approver_override_id": None},
        },
        world.category.code: {"before": None, "after": {"approver_override_id": None}},
    }
    assert entries[1].context == {
        "added": [world.category.code],
        "removed": [net.code],
        "override_changed": [fw.code],
    }
    assert (await verify(rw_engine, world.a.id)).ok


@pytest.mark.parametrize("who", ["editor", "auditor", "outsider", "nobody", "inactive", "random"])
async def test_approver_override_must_be_an_approver_of_the_company(
    api: AsyncClient, world: World, rw_engine: AsyncEngine, who: str
) -> None:
    if who == "inactive":
        user = await make_user(rw_engine, active=False)
        user_id = user.id
    elif who == "random":
        user_id = uuid4()
    else:
        user_id = world.persona(who).id
    response = await api.put(
        categories_url(world.a.id),
        json={
            "categories": [
                {"category_id": str(world.category.id), "approver_override_id": str(user_id)}
            ]
        },
        headers=auth(world.admin),
    )
    assert_problem(response, 422, "company_category.approver_not_eligible")


async def test_company_category_rejections(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    sub = await make_category(rw_engine, parent=world.category)
    inactive = await make_category(rw_engine)
    await api.patch(
        f"/api/v1/categories/{inactive.id}", json={"is_active": False}, headers=auth(world.admin)
    )
    url = categories_url(world.a.id)

    async def put(*ids: Any) -> Any:
        return await api.put(
            url,
            json={"categories": [{"category_id": str(i)} for i in ids]},
            headers=auth(world.admin),
        )

    assert_problem(await put(sub.id), 422, "company_category.not_top_level")
    assert_problem(await put(inactive.id), 422, "company_category.category_inactive")
    assert_problem(await put(uuid4()), 422, "company_category.category_not_found")
    assert_problem(
        await put(world.category.id, world.category.id), 422, "company_category.duplicate"
    )

    # A category deactivated AFTER it was made available stays (not removed by a PUT that
    # keeps it); only adding an inactive category is refused.
    available = await make_category(rw_engine)
    assert (await put(available.id)).status_code == 200
    await api.patch(
        f"/api/v1/categories/{available.id}", json={"is_active": False}, headers=auth(world.admin)
    )
    kept = await put(available.id, world.category.id)
    assert kept.status_code == 200, kept.text
    assert {i["code"]: i["is_active"] for i in kept.json()["items"]} == {
        available.code: False,
        world.category.code: True,
    }


async def test_admin_reads_company_categories_without_membership(
    api: AsyncClient, world: World
) -> None:
    response = await api.get(categories_url(world.b.id), headers=auth(world.admin))
    assert response.status_code == 200, response.text
    assert response.json() == {"items": []}


# --------------------------------------------------------------------------- CI: create


async def test_editor_creates_ci_with_audit(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    body = {
        "ci_type_id": str(world.ci_type.id),
        "identifier": "  FW-01 ",
        "name": "Zapora główna",
        "description": "Klaster HA, zażółć gęślą jaźń\nsala 2",
        "owner_user_id": str(world.approver.id),
    }
    response = await api.post(ci_url(world.a.id), json=body, headers=auth(world.editor))
    assert response.status_code == 201, response.text
    created = response.json()
    assert created["identifier"] == "FW-01"
    assert created["company_id"] == str(world.a.id)
    assert (created["ci_type_code"], created["ci_type_name"]) == (
        world.ci_type.code,
        world.ci_type.name,
    )
    assert created["owner_user_id"] == str(world.approver.id)
    assert created["is_active"] is True
    assert response.headers["location"].endswith(f"/ci/{created['id']}")

    (entry,) = await audit_entries(rw_engine, UUID(created["id"]))
    assert entry.company_id == world.a.id
    assert (entry.entity_type, entry.action) == ("ci", "create")
    assert entry.actor_id == world.editor.id
    assert entry.actor_roles == ["editor"]
    assert entry.diff["identifier"] == {"before": None, "after": "FW-01"}
    assert entry.diff["description"]["after"] == "Klaster HA, zażółć gęślą jaźń\nsala 2"
    assert entry.context == {"identifier": "FW-01", "ci_type_code": world.ci_type.code}
    assert (await verify(rw_engine, world.a.id)).ok


async def test_ci_identifier_unique_in_company_ignoring_case(
    api: AsyncClient, world: World
) -> None:
    def body(identifier: str) -> dict[str, Any]:
        return {"ci_type_id": str(world.ci_type.id), "identifier": identifier, "name": "X"}

    taken = await api.post(
        ci_url(world.a.id), json=body(world.ci_a.identifier.lower()), headers=auth(world.editor)
    )
    assert_problem(taken, 409, "ci.identifier_taken")
    # The same identifier in another company is fine.
    other = await api.post(
        ci_url(world.b.id), json=body(world.ci_a.identifier), headers=auth(world.outsider)
    )
    assert other.status_code == 201, other.text
    # Concurrent creation: exactly one wins.
    identifier = f"RACE-{uuid4().hex[:6]}"
    responses = await asyncio.gather(
        *(
            api.post(ci_url(world.a.id), json=body(identifier), headers=auth(world.editor))
            for _ in range(5)
        )
    )
    assert sorted(r.status_code for r in responses) == [201, 409, 409, 409, 409]


async def test_ci_type_and_owner_rules(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    inactive_type = await make_ci_type(rw_engine)
    await api.patch(
        f"/api/v1/ci-types/{inactive_type.id}", json={"is_active": False}, headers=auth(world.admin)
    )

    async def create(**overrides: Any) -> Any:
        body = {
            "ci_type_id": str(world.ci_type.id),
            "identifier": f"CI-{uuid4().hex[:8]}",
            "name": "Obiekt",
        }
        body.update(overrides)
        return await api.post(ci_url(world.a.id), json=body, headers=auth(world.approver))

    assert_problem(await create(ci_type_id=str(inactive_type.id)), 422, "ci.type_inactive")
    assert_problem(await create(ci_type_id=str(uuid4())), 422, "ci.type_not_found")
    for owner in (world.outsider.id, world.nobody.id, world.admin.id, uuid4()):
        assert_problem(await create(owner_user_id=str(owner)), 422, "ci.owner_not_member")
    # Any role in the company makes a valid owner (here: viewer).
    assert (await create(owner_user_id=str(world.viewer.id))).status_code == 201
    assert_problem(await create(identifier="   "), 422, "ci.invalid_data")
    assert_problem(await create(name="x\u0007"), 422, "request.validation_error")


async def test_admin_manages_ci_without_membership(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    """§5: the CI inventory is managed by the app admin too (explicit admin path)."""
    response = await api.post(
        ci_url(world.b.id),
        json={"ci_type_id": str(world.ci_type.id), "identifier": "SRV-ADM", "name": "Serwer"},
        headers=auth(world.admin),
    )
    assert response.status_code == 201, response.text
    (entry,) = await audit_entries(rw_engine, UUID(response.json()["id"]))
    assert entry.company_id == world.b.id
    assert entry.actor_roles == ["app_admin"]
    assert (await verify(rw_engine, world.b.id)).ok


async def test_archived_company_inventory_is_frozen(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    company = await make_company(rw_engine)
    await grant(rw_engine, company, world.editor, Role.EDITOR)
    ci = await make_ci(rw_engine, company, world.ci_type)
    archived = await api.post(f"/api/v1/companies/{company.id}/archive", headers=auth(world.admin))
    assert archived.status_code == 200
    created = await api.post(
        ci_url(company.id),
        json={"ci_type_id": str(world.ci_type.id), "identifier": "NEW-1", "name": "X"},
        headers=auth(world.editor),
    )
    assert_problem(created, 409, "company.archived")
    updated = await api.patch(
        ci_url(company.id, ci.id), json={"name": "Y"}, headers=auth(world.editor)
    )
    assert_problem(updated, 409, "company.archived")
    # Still readable (history).
    assert (await api.get(ci_url(company.id, ci.id), headers=auth(world.editor))).status_code == 200


# --------------------------------------------------------------------------- CI: update


async def test_update_and_deactivate_ci_with_audit(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    other_type = await make_ci_type(rw_engine, name="Maszyna wirtualna")
    url = ci_url(world.a.id, world.ci_a.id)
    updated = await api.patch(
        url,
        json={
            "name": "Zapora brzegowa (HA)",
            "ci_type_id": str(other_type.id),
            "owner_user_id": str(world.editor.id),
            "description": "  ",
        },
        headers=auth(world.approver),
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["ci_type_code"] == other_type.code
    assert updated.json()["description"] is None
    # Case-only change of the own identifier is allowed.
    recased = await api.patch(
        url, json={"identifier": world.ci_a.identifier.lower()}, headers=auth(world.editor)
    )
    assert recased.json()["identifier"] == world.ci_a.identifier.lower()
    renamed = await api.patch(
        url, json={"identifier": f" {world.ci_a.identifier.upper()}X "}, headers=auth(world.editor)
    )
    assert renamed.json()["identifier"] == f"{world.ci_a.identifier.upper()}X"
    noop = await api.patch(url, json={"name": "Zapora brzegowa (HA)"}, headers=auth(world.editor))
    assert noop.status_code == 200
    off = await api.patch(url, json={"is_active": False}, headers=auth(world.editor))
    assert off.json()["is_active"] is False
    on = await api.patch(
        url, json={"is_active": True, "owner_user_id": None}, headers=auth(world.editor)
    )
    assert (on.json()["is_active"], on.json()["owner_user_id"]) == (True, None)

    entries = await audit_entries(rw_engine, world.ci_a.id)
    assert [e.action for e in entries] == [
        "create",
        "update",
        "update",
        "update",
        "deactivate",
        "update",
    ]
    assert entries[1].diff == {
        "ci_type_id": {"before": str(world.ci_type.id), "after": str(other_type.id)},
        "name": {"before": "Zapora brzegowa A", "after": "Zapora brzegowa (HA)"},
        "owner_user_id": {"before": None, "after": str(world.editor.id)},
    }
    assert entries[1].actor_roles == ["approver"]
    assert entries[4].diff == {"is_active": {"before": True, "after": False}}
    assert (await verify(rw_engine, world.a.id)).ok


async def test_update_rejections(api: AsyncClient, world: World, rw_engine: AsyncEngine) -> None:
    second = await make_ci(rw_engine, world.a, world.ci_type)
    url = ci_url(world.a.id, world.ci_a.id)
    for body, status, code in (
        ({"identifier": second.identifier.lower()}, 409, "ci.identifier_taken"),
        ({"name": None}, 422, "ci.invalid_data"),
        ({"is_active": None}, 422, "ci.invalid_data"),
        ({"ci_type_id": None}, 422, "ci.invalid_data"),
        ({"owner_user_id": str(world.outsider.id)}, 422, "ci.owner_not_member"),
        ({"company_id": str(world.b.id)}, 422, "request.validation_error"),
    ):
        response = await api.patch(url, json=body, headers=auth(world.editor))
        assert_problem(response, status, code)
    missing = await api.patch(
        ci_url(world.a.id, uuid4()), json={"name": "X"}, headers=auth(world.editor)
    )
    assert_problem(missing, 404, "ci.not_found")
    assert_problem(
        await api.get(ci_url(world.a.id, uuid4()), headers=auth(world.viewer)), 404, "ci.not_found"
    )


# --------------------------------------------------------------------------- CI: list


async def test_list_ci_filters_and_pagination(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    vm = await make_ci_type(rw_engine, name="VM")
    company = await make_company(rw_engine)
    await grant(rw_engine, company, world.viewer, Role.VIEWER)
    await make_ci(rw_engine, company, world.ci_type, identifier="FW-02", name="Zapora zapasowa")
    await make_ci(rw_engine, company, world.ci_type, identifier="fw-01", name="Zapora główna")
    await make_ci(rw_engine, company, vm, identifier="VM-100", name="Serwer 100%_procent")
    old = await make_ci(rw_engine, company, vm, identifier="VM-OLD", name="Wycofana")
    async with scoped(rw_engine, [company.id]) as session:
        await configuration_items.update_item(
            session, actor=SYSTEM, company=company, ci_id=old.id, changes={"is_active": False}
        )
    await make_ci(rw_engine, world.a, vm, identifier="VM-A", name="Inna spółka")

    async def ids(**params: Any) -> tuple[list[str], int]:
        response = await api.get(ci_url(company.id), params=params, headers=auth(world.viewer))
        assert response.status_code == 200, response.text
        data = response.json()
        return [i["identifier"] for i in data["items"]], data["total"]

    assert await ids() == (["fw-01", "FW-02", "VM-100", "VM-OLD"], 4)  # case-insensitive order
    assert await ids(limit=2, offset=1) == (["FW-02", "VM-100"], 4)
    assert await ids(active="true") == (["fw-01", "FW-02", "VM-100"], 3)
    assert await ids(active="false") == (["VM-OLD"], 1)
    assert await ids(type=vm.code) == (["VM-100", "VM-OLD"], 2)
    assert await ids(type=[vm.code, world.ci_type.code]) == (
        ["fw-01", "FW-02", "VM-100", "VM-OLD"],
        4,
    )
    assert await ids(q="zapora") == (["fw-01", "FW-02"], 2)
    assert await ids(q="fw-0") == (["fw-01", "FW-02"], 2)
    assert await ids(q="100%") == (["VM-100"], 1)  # LIKE wildcards are literal
    assert await ids(q="_") == (["VM-100"], 1)
    assert await ids(q="nic takiego") == ([], 0)


async def test_admin_write_path_opens_only_the_company_scope(db_urls: DbUrls, world: World) -> None:
    """``ci.manage`` on the admin path widens the scope by the target company WITHOUT
    ``app.admin_scope``: in that transaction RLS rejects writes to companies, memberships,
    company categories and the dictionaries, while the company's CI stay writable."""

    app = create_app(make_settings(database_url=db_urls.rw))
    statements = {
        "companies": "UPDATE companies SET is_ksc_entity = is_ksc_entity WHERE id = :c",
        "memberships": (
            "INSERT INTO company_memberships (user_id, company_id, role) VALUES (:u, :c, 'viewer')"
        ),
        "company_categories": (
            "INSERT INTO company_categories (company_id, category_id) VALUES (:c, :k)"
        ),
        "change_categories": "UPDATE change_categories SET name = name WHERE id = :k",
        "ci_types": "UPDATE ci_types SET name = name WHERE id = :t",
        "ci": "UPDATE configuration_items SET name = name WHERE id = :ci",
    }

    @app.post("/api/v1/_test/companies/{company_id}/ci-write-scope")
    async def _probe(
        session: SessionDep,
        ctx: Any = require_company(Action.CI_MANAGE, admin_action=Action.CI_MANAGE),
    ) -> dict[str, Any]:
        params = {
            "c": ctx.company_id,
            "u": world.nobody.id,
            "k": world.category.id,
            "t": world.ci_type.id,
            "ci": world.ci_b.id,
        }
        results: dict[str, Any] = {}
        for name, sql in statements.items():
            try:
                async with session.begin_nested():
                    result = await session.execute(text(sql), params)
                    results[name] = result.rowcount  # type: ignore[attr-defined]
            except DBAPIError as exc:
                results[name] = getattr(exc.orig, "sqlstate", None)
        admin_scope = (await session.execute(text("SELECT app_admin_scope()"))).scalar_one()
        return {"admin_path": ctx.admin_path, "admin_scope": admin_scope, "results": results}

    try:
        async with client_for(app) as client:
            response = await client.post(
                f"/api/v1/_test/companies/{world.b.id}/ci-write-scope", headers=auth(world.admin)
            )
    finally:
        await app.state.db.dispose()
    assert response.status_code == 200, response.text
    assert response.json() == {
        "admin_path": True,
        "admin_scope": False,
        "results": {
            "companies": 0,  # invisible to UPDATE without the admin scope
            "memberships": "42501",
            "company_categories": "42501",
            "change_categories": 0,
            "ci_types": 0,
            "ci": 1,  # the company's own table: writable
        },
    }
