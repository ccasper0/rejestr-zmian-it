"""Companies API: create, list, update (immutable prefix), archive — always audited."""

from __future__ import annotations

import asyncio
from typing import Any
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine

from app.services import companies as companies_service
from tests.factories import (
    World,
    all_companies,
    audit_entries,
    auth,
    make_company,
    make_user,
    random_prefix,
    scoped,
    verify,
)
from tests.test_api_auth import assert_problem

pytestmark = pytest.mark.db

RESTRICT_VIOLATION = "23001"


def new_company_body(**overrides: Any) -> dict[str, Any]:
    prefix = random_prefix()
    body: dict[str, Any] = {"name": f"Nowa {prefix} sp. z o.o.", "prefix": prefix}
    body.update(overrides)
    return body


# --------------------------------------------------------------------------- create


async def test_admin_creates_company_with_audit(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    body = new_company_body(
        tax_id="526-025-09-95", is_ksc_entity=True, default_approver_id=str(world.approver.id)
    )
    response = await api.post("/api/v1/companies", json=body, headers=auth(world.admin))
    assert response.status_code == 201, response.text
    created = response.json()
    assert created["prefix"] == body["prefix"]
    assert created["tax_id"] == "5260250995"  # normalized
    assert created["status"] == "active"
    assert created["is_ksc_entity"] is True
    assert created["default_approver_id"] == str(world.approver.id)
    assert created["created_at"].endswith("Z")
    assert response.headers["location"].endswith(f"/companies/{created['id']}")

    entries = await audit_entries(rw_engine, created["id"])
    assert len(entries) == 1
    entry = entries[0]
    assert entry.company_id is None  # company events live in the global chain
    assert (entry.entity_type, entry.action) == ("company", "create")
    assert entry.actor_id == world.admin.id
    assert entry.actor_roles == ["app_admin"]
    assert entry.diff == {
        "default_approver_id": {"before": None, "after": str(world.approver.id)},
        "is_ksc_entity": {"before": None, "after": True},
        "name": {"before": None, "after": body["name"]},
        "prefix": {"before": None, "after": body["prefix"]},
        "status": {"before": None, "after": "active"},
        "tax_id": {"before": None, "after": "5260250995"},
    }
    assert entry.ip_address is not None
    assert (await verify(rw_engine, None)).ok


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"prefix": "al"}, "prefix"),
        ({"prefix": "ABCDEFGHI"}, "prefix"),
        ({"prefix": "AŁFA"}, "prefix"),
        ({"tax_id": "1234567890"}, "tax_id"),
        ({"name": "   "}, "name"),
    ],
)
async def test_create_validation(
    api: AsyncClient, world: World, overrides: dict[str, Any], field: str
) -> None:
    response = await api.post(
        "/api/v1/companies", json=new_company_body(**overrides), headers=auth(world.admin)
    )
    body = assert_problem(response, 422, "company.invalid_data")
    assert body["field"] == field


@pytest.mark.parametrize("name", ["Zla\x00Spolka", "Zla\x1fSpolka", "Dwie\nlinie"])
async def test_create_rejects_control_characters(api: AsyncClient, world: World, name: str) -> None:
    response = await api.post(
        "/api/v1/companies", json=new_company_body(name=name), headers=auth(world.admin)
    )
    body = assert_problem(response, 422, "request.validation_error")
    assert body["errors"][0]["loc"] == ["body", "name"]
    assert body["errors"][0]["msg"] == "Tekst zawiera niedozwolone znaki sterujące."


async def test_update_rejects_nul(api: AsyncClient, world: World) -> None:
    response = await api.patch(
        f"/api/v1/companies/{world.a.id}", json={"name": "A\x00"}, headers=auth(world.admin)
    )
    assert_problem(response, 422, "request.validation_error")


async def test_users_query_rejects_nul(api: AsyncClient, world: World) -> None:
    response = await api.get("/api/v1/users", params={"q": "a\x00"}, headers=auth(world.admin))
    assert_problem(response, 422, "request.validation_error")


async def test_create_rejects_unknown_fields(api: AsyncClient, world: World) -> None:
    response = await api.post(
        "/api/v1/companies", json=new_company_body(status="archived"), headers=auth(world.admin)
    )
    assert_problem(response, 422, "request.validation_error")


async def test_duplicate_prefix_and_name_are_409(api: AsyncClient, world: World) -> None:
    taken_prefix = await api.post(
        "/api/v1/companies",
        json=new_company_body(prefix=world.a.prefix),
        headers=auth(world.admin),
    )
    assert_problem(taken_prefix, 409, "company.prefix_taken")
    taken_name = await api.post(
        "/api/v1/companies",
        json=new_company_body(name=world.a.name.upper()),  # case-insensitive
        headers=auth(world.admin),
    )
    assert_problem(taken_name, 409, "company.name_taken")


async def test_concurrent_names_differing_in_case_one_wins(api: AsyncClient, world: World) -> None:
    base = f"Wyścig {random_prefix()}"
    responses = await asyncio.gather(
        *(
            api.post(
                "/api/v1/companies",
                json=new_company_body(name=name),
                headers=auth(world.admin),
            )
            for name in (base.title(), base.upper())
        )
    )
    assert sorted(r.status_code for r in responses) == [201, 409], [r.text for r in responses]
    assert_problem(next(r for r in responses if r.status_code == 409), 409, "company.name_taken")


async def test_case_insensitive_name_enforced_by_database(
    api: AsyncClient, world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Without the application pre-check (as in a race) the unique index on lower(name)
    # still rejects the duplicate, mapped to 409 instead of a 500.
    async def no_precheck(*_args: Any, **_kwargs: Any) -> None:
        return None

    monkeypatch.setattr(companies_service, "_ensure_name_free", no_precheck)
    name = f"Indeks {random_prefix()}"
    first = await api.post(
        "/api/v1/companies", json=new_company_body(name=name), headers=auth(world.admin)
    )
    assert first.status_code == 201, first.text
    second = await api.post(
        "/api/v1/companies", json=new_company_body(name=name.lower()), headers=auth(world.admin)
    )
    assert_problem(second, 409, "company.name_taken")
    renamed = await api.patch(
        f"/api/v1/companies/{world.a.id}", json={"name": name.upper()}, headers=auth(world.admin)
    )
    assert_problem(renamed, 409, "company.name_taken")


async def test_name_unique_index_in_database(
    rw_engine: AsyncEngine, owner_engine: AsyncEngine
) -> None:
    company = await make_company(rw_engine)
    async with owner_engine.begin() as conn:
        with pytest.raises(DBAPIError) as info:
            await conn.execute(
                text(
                    "INSERT INTO companies (id, name, prefix) "
                    "VALUES (gen_random_uuid(), :name, :prefix)"
                ),
                {"name": company.name.swapcase(), "prefix": random_prefix()},
            )
    assert "uq_companies_name_lower" in str(info.value)


async def test_default_approver_must_be_active_user(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    inactive = await make_user(rw_engine, active=False)
    for approver in (uuid4(), inactive.id):
        response = await api.post(
            "/api/v1/companies",
            json=new_company_body(default_approver_id=str(approver)),
            headers=auth(world.admin),
        )
        body = assert_problem(response, 422, "company.invalid_data")
        assert body["field"] == "default_approver_id"


# --------------------------------------------------------------------------- list


async def test_list_companies_per_user(api: AsyncClient, world: World) -> None:
    editor = (await api.get("/api/v1/companies", headers=auth(world.editor))).json()
    assert [c["id"] for c in editor["items"]] == [str(world.a.id)]
    assert editor["total"] == 1
    assert editor["items"][0]["my_roles"] == ["editor"]

    nobody = (await api.get("/api/v1/companies", headers=auth(world.nobody))).json()
    assert nobody == {"items": [], "total": 0, "limit": 100, "offset": 0}

    admin = await all_companies(api, world.admin)
    ids = {c["id"] for c in admin}
    assert {str(world.a.id), str(world.b.id)} <= ids


# --------------------------------------------------------------------------- update


async def test_admin_updates_company_with_diff(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    response = await api.patch(
        f"/api/v1/companies/{world.a.id}",
        json={"name": f"{world.a.name} (nowa)", "is_ksc_entity": True, "tax_id": None},
        headers=auth(world.admin),
    )
    assert response.status_code == 200, response.text
    assert response.json()["name"] == f"{world.a.name} (nowa)"
    entries = await audit_entries(rw_engine, world.a.id)
    update = entries[-1]
    assert (update.entity_type, update.action, update.company_id) == ("company", "update", None)
    # tax_id was already NULL: not part of the diff.
    assert update.diff == {
        "is_ksc_entity": {"before": False, "after": True},
        "name": {"before": world.a.name, "after": f"{world.a.name} (nowa)"},
    }
    assert (await verify(rw_engine, None)).ok


async def test_noop_update_writes_no_audit(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    before = len(await audit_entries(rw_engine, world.a.id))
    response = await api.patch(
        f"/api/v1/companies/{world.a.id}",
        json={"name": world.a.name, "prefix": world.a.prefix},
        headers=auth(world.admin),
    )
    assert response.status_code == 200, response.text
    assert len(await audit_entries(rw_engine, world.a.id)) == before


async def test_prefix_is_immutable_in_service(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    before = len(await audit_entries(rw_engine, world.a.id))
    response = await api.patch(
        f"/api/v1/companies/{world.a.id}",
        json={"prefix": random_prefix(), "name": "Inna"},
        headers=auth(world.admin),
    )
    assert_problem(response, 422, "company.prefix_immutable")
    company = (await api.get("/api/v1/companies", headers=auth(world.editor))).json()["items"][0]
    assert (company["prefix"], company["name"]) == (world.a.prefix, world.a.name)
    assert len(await audit_entries(rw_engine, world.a.id)) == before


async def test_prefix_is_immutable_in_database(rw_engine: AsyncEngine) -> None:
    """With RLS on (migration 0003): outside the admin path the row is not even visible
    for UPDATE; on the admin path the immutability trigger rejects the change."""
    company = await make_company(rw_engine)
    update = text("UPDATE companies SET prefix = 'ZZZZ' WHERE id = :id")
    async with scoped(rw_engine, [company.id]) as session:
        hidden = await session.execute(update, {"id": company.id})
        assert hidden.rowcount == 0  # type: ignore[attr-defined]
    with pytest.raises(DBAPIError) as info:
        async with scoped(rw_engine, [company.id], admin_scope=True) as session:
            await session.execute(update, {"id": company.id})
    assert getattr(info.value.orig, "sqlstate", None) == RESTRICT_VIOLATION
    async with scoped(rw_engine, admin_scope=True) as session:
        prefix = (
            await session.execute(
                text("SELECT prefix FROM companies WHERE id = :id"), {"id": company.id}
            )
        ).scalar_one()
    assert prefix == company.prefix


async def test_update_unknown_company_is_404(api: AsyncClient, world: World) -> None:
    response = await api.patch(
        f"/api/v1/companies/{uuid4()}", json={"name": "X"}, headers=auth(world.admin)
    )
    assert_problem(response, 404, "company.not_found")


async def test_update_to_taken_name_is_409(api: AsyncClient, world: World) -> None:
    response = await api.patch(
        f"/api/v1/companies/{world.a.id}", json={"name": world.b.name}, headers=auth(world.admin)
    )
    assert_problem(response, 409, "company.name_taken")


# --------------------------------------------------------------------------- archive


async def test_archive_company(api: AsyncClient, world: World, rw_engine: AsyncEngine) -> None:
    response = await api.post(f"/api/v1/companies/{world.b.id}/archive", headers=auth(world.admin))
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "archived"

    entry = (await audit_entries(rw_engine, world.b.id))[-1]
    assert (entry.entity_type, entry.action, entry.company_id) == ("company", "archive", None)
    assert entry.diff == {"status": {"before": "active", "after": "archived"}}

    again = await api.post(f"/api/v1/companies/{world.b.id}/archive", headers=auth(world.admin))
    assert_problem(again, 409, "company.already_archived")

    # Archived, never deleted: members still see it (read-only history).
    listed = (await api.get("/api/v1/companies", headers=auth(world.outsider))).json()
    assert [(c["id"], c["status"]) for c in listed["items"]] == [(str(world.b.id), "archived")]
    assert (await verify(rw_engine, None)).ok


async def test_archive_unknown_company_is_404(api: AsyncClient, world: World) -> None:
    response = await api.post(f"/api/v1/companies/{uuid4()}/archive", headers=auth(world.admin))
    assert_problem(response, 404, "company.not_found")
