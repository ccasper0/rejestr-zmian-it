"""Global dictionaries API: change categories (2 levels) and CI types - always audited.

Writes: app admin only (``dictionary.manage``); reads: anybody with a role in any company
or the app admin (``require_in_any_company``, ADR 0011). The full permission matrix is in
``tests/test_rbac_matrix.py``.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine

from tests.factories import (
    World,
    audit_entries,
    auth,
    make_category,
    random_category_code,
    random_ci_type_code,
    verify,
)
from tests.test_api_auth import assert_problem

pytestmark = pytest.mark.db

CATEGORIES = "/api/v1/categories"
CI_TYPES = "/api/v1/ci-types"


# --------------------------------------------------------------------------- categories


async def test_admin_creates_category_and_subcategory_with_audit(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    code = random_category_code()
    root = await api.post(
        CATEGORIES,
        json={"code": code, "name": "  Konta i uprawnienia ", "requires_approval": False},
        headers=auth(world.admin),
    )
    assert root.status_code == 201, root.text
    body = root.json()
    assert body["code"] == code
    assert body["name"] == "Konta i uprawnienia"
    assert body["parent_id"] is None
    assert (body["requires_approval"], body["default_risk"], body["is_active"]) == (
        False,
        "medium",
        True,
    )
    assert body["created_at"].endswith("Z")
    assert root.headers["location"].endswith(f"/categories/{body['id']}")

    child = await api.post(
        CATEGORIES,
        json={
            "code": f"{code}-PRIV",
            "name": "Konto uprzywilejowane",
            "parent_id": body["id"],
            "requires_approval": True,
        },
        headers=auth(world.admin),
    )
    assert child.status_code == 201, child.text
    assert child.json()["parent_id"] == body["id"]
    # Not given: inherited from the category.
    inherited = await api.post(
        CATEGORIES,
        json={"code": f"{code}-GRANT", "name": "Nadanie", "parent_id": body["id"]},
        headers=auth(world.admin),
    )
    assert (inherited.json()["requires_approval"], inherited.json()["default_risk"]) == (
        False,
        "medium",
    )

    (entry,) = await audit_entries(rw_engine, body["id"])
    assert entry.company_id is None  # global chain
    assert (entry.entity_type, entry.action) == ("category", "create")
    assert entry.actor_roles == ["app_admin"]
    assert entry.diff["code"] == {"before": None, "after": code}
    (child_entry,) = await audit_entries(rw_engine, child.json()["id"])
    assert child_entry.context == {"parent_code": code}
    assert (await verify(rw_engine, None)).ok


async def test_categories_have_two_levels(api: AsyncClient, world: World) -> None:
    parent = await api.post(
        CATEGORIES,
        json={"code": random_category_code(), "name": "Główna"},
        headers=auth(world.admin),
    )
    child = await api.post(
        CATEGORIES,
        json={"code": random_category_code(), "name": "Pod", "parent_id": parent.json()["id"]},
        headers=auth(world.admin),
    )
    grandchild = await api.post(
        CATEGORIES,
        json={"code": random_category_code(), "name": "Pod-pod", "parent_id": child.json()["id"]},
        headers=auth(world.admin),
    )
    assert_problem(grandchild, 422, "category.depth_exceeded")
    missing = await api.post(
        CATEGORIES,
        json={
            "code": random_category_code(),
            "name": "Sierota",
            "parent_id": "00000000-0000-0000-0000-000000000001",
        },
        headers=auth(world.admin),
    )
    assert_problem(missing, 422, "category.parent_not_found")


@pytest.mark.parametrize(
    ("body", "code"),
    [
        ({"code": "acc", "name": "X"}, "category.invalid_data"),
        ({"code": "ACC_1", "name": "X"}, "category.invalid_data"),
        ({"code": "TST-OK", "name": "   "}, "category.invalid_data"),
        ({"code": "TST-OK", "name": "X", "default_risk": "critical"}, "request.validation_error"),
        ({"code": "TST-OK", "name": "X", "extra": 1}, "request.validation_error"),
        ({"code": "TST-OK", "name": "X\u0000"}, "request.validation_error"),
    ],
)
async def test_invalid_category_is_422(
    api: AsyncClient, world: World, body: dict[str, Any], code: str
) -> None:
    response = await api.post(CATEGORIES, json=body, headers=auth(world.admin))
    assert_problem(response, 422, code)


async def test_category_code_taken_also_under_concurrency(api: AsyncClient, world: World) -> None:
    taken = await api.post(
        CATEGORIES,
        json={"code": world.category.code, "name": "Duplikat"},
        headers=auth(world.admin),
    )
    assert_problem(taken, 409, "category.code_taken")
    code = random_category_code()
    responses = await asyncio.gather(
        *(
            api.post(CATEGORIES, json={"code": code, "name": "Wyścig"}, headers=auth(world.admin))
            for _ in range(5)
        )
    )
    statuses = sorted(r.status_code for r in responses)
    assert statuses == [201, 409, 409, 409, 409], [r.text for r in responses]


async def test_admin_updates_and_deactivates_category(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    url = f"{CATEGORIES}/{world.category.id}"
    renamed = await api.patch(
        url,
        json={
            "name": "Sieć i routing",
            "default_risk": "high",
            "code": world.category.code,  # unchanged: accepted
            "parent_id": None,  # unchanged: accepted
        },
        headers=auth(world.admin),
    )
    assert renamed.status_code == 200, renamed.text
    assert (renamed.json()["name"], renamed.json()["default_risk"]) == ("Sieć i routing", "high")
    same = await api.patch(url, json={"name": "Sieć i routing"}, headers=auth(world.admin))
    assert same.status_code == 200
    off = await api.patch(url, json={"is_active": False}, headers=auth(world.admin))
    assert off.json()["is_active"] is False

    entries = await audit_entries(rw_engine, world.category.id)
    assert [e.action for e in entries] == ["create", "update", "deactivate"]
    assert entries[1].diff == {
        "default_risk": {"before": "medium", "after": "high"},
        "name": {"before": "Kategoria testowa", "after": "Sieć i routing"},
    }
    assert entries[2].diff == {"is_active": {"before": True, "after": False}}
    assert entries[2].context == {"code": world.category.code}
    assert (await verify(rw_engine, None)).ok


@pytest.mark.parametrize(
    ("body", "status", "code"),
    [
        ({"code": "TST-INNY"}, 422, "category.code_immutable"),
        ({"parent_id": "00000000-0000-0000-0000-000000000001"}, 422, "category.parent_immutable"),
        ({"name": None}, 422, "category.invalid_data"),
        ({"requires_approval": None}, 422, "category.invalid_data"),
        ({"is_active": None}, 422, "category.invalid_data"),
    ],
)
async def test_category_update_rejections(
    api: AsyncClient, world: World, body: dict[str, Any], status: int, code: str
) -> None:
    response = await api.patch(
        f"{CATEGORIES}/{world.category.id}", json=body, headers=auth(world.admin)
    )
    assert_problem(response, status, code)


async def test_unknown_category_is_404(api: AsyncClient, world: World) -> None:
    response = await api.patch(
        f"{CATEGORIES}/00000000-0000-0000-0000-000000000001",
        json={"name": "X"},
        headers=auth(world.admin),
    )
    assert_problem(response, 404, "category.not_found")


async def test_subcategory_of_an_inactive_category_is_rejected(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    parent = await make_category(rw_engine)
    await api.patch(
        f"{CATEGORIES}/{parent.id}", json={"is_active": False}, headers=auth(world.admin)
    )
    response = await api.post(
        CATEGORIES,
        json={"code": random_category_code(), "name": "Pod", "parent_id": str(parent.id)},
        headers=auth(world.admin),
    )
    assert_problem(response, 422, "category.parent_inactive")


async def test_members_list_categories_in_tree_order(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    root = await make_category(rw_engine, code="TST-ZZ" + random_category_code()[4:9])
    child = await make_category(rw_engine, parent=root, code=root.code + "-A")
    inactive = await make_category(rw_engine, parent=root, code=root.code + "-B")
    await api.patch(
        f"{CATEGORIES}/{inactive.id}", json={"is_active": False}, headers=auth(world.admin)
    )

    response = await api.get(CATEGORIES, params={"limit": 500}, headers=auth(world.viewer))
    assert response.status_code == 200, response.text
    codes = [c["code"] for c in response.json()["items"]]
    position = codes.index(root.code)
    assert codes[position : position + 3] == [root.code, child.code, inactive.code]
    assert response.json()["total"] >= 3

    active = await api.get(
        CATEGORIES, params={"active": "true", "limit": 500}, headers=auth(world.viewer)
    )
    active_codes = {c["code"] for c in active.json()["items"]}
    assert {root.code, child.code} <= active_codes
    assert inactive.code not in active_codes

    children = await api.get(
        CATEGORIES, params={"parent_id": str(root.id)}, headers=auth(world.outsider)
    )
    assert [c["code"] for c in children.json()["items"]] == [child.code, inactive.code]


# --------------------------------------------------------------------------- CI types


async def test_admin_manages_ci_types_with_audit(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    code = random_ci_type_code()
    created = await api.post(
        CI_TYPES, json={"code": code, "name": "Drukarka sieciowa"}, headers=auth(world.admin)
    )
    assert created.status_code == 201, created.text
    type_id = created.json()["id"]
    assert created.json()["is_active"] is True
    assert_problem(
        await api.post(CI_TYPES, json={"code": code, "name": "Inna"}, headers=auth(world.admin)),
        409,
        "ci_type.code_taken",
    )
    assert_problem(
        await api.post(CI_TYPES, json={"code": "Drukarka", "name": "X"}, headers=auth(world.admin)),
        422,
        "ci_type.invalid_data",
    )
    url = f"{CI_TYPES}/{type_id}"
    assert_problem(
        await api.patch(url, json={"code": "inny_kod"}, headers=auth(world.admin)),
        422,
        "ci_type.code_immutable",
    )
    renamed = await api.patch(url, json={"name": "Drukarka"}, headers=auth(world.admin))
    assert renamed.json()["name"] == "Drukarka"
    off = await api.patch(url, json={"is_active": False}, headers=auth(world.admin))
    assert off.json()["is_active"] is False
    on = await api.patch(url, json={"is_active": True}, headers=auth(world.admin))
    assert on.json()["is_active"] is True
    assert_problem(
        await api.patch(
            f"{CI_TYPES}/00000000-0000-0000-0000-000000000001",
            json={"name": "X"},
            headers=auth(world.admin),
        ),
        404,
        "ci_type.not_found",
    )

    entries = await audit_entries(rw_engine, type_id)
    assert [(e.company_id, e.entity_type, e.action) for e in entries] == [
        (None, "ci_type", "create"),
        (None, "ci_type", "update"),
        (None, "ci_type", "deactivate"),
        (None, "ci_type", "update"),
    ]
    assert (await verify(rw_engine, None)).ok


async def test_members_list_ci_types(api: AsyncClient, world: World) -> None:
    response = await api.get(CI_TYPES, params={"limit": 500}, headers=auth(world.auditor))
    assert response.status_code == 200, response.text
    assert world.ci_type.code in {t["code"] for t in response.json()["items"]}
    inactive = await api.get(CI_TYPES, params={"active": "false"}, headers=auth(world.auditor))
    assert all(t["is_active"] is False for t in inactive.json()["items"])
