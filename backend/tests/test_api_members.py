"""Company members (roles per company) and the users list for role assignment."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine

from tests.factories import World, audit_entries, auth, make_user, verify
from tests.test_api_auth import assert_problem

pytestmark = pytest.mark.db


async def test_members_list(api: AsyncClient, world: World) -> None:
    response = await api.get(f"/api/v1/companies/{world.a.id}/members", headers=auth(world.viewer))
    assert response.status_code == 200, response.text
    body = response.json()
    members = {m["user_id"]: m for m in body["items"]}
    assert body["total"] == 4
    assert members[str(world.approver.id)]["roles"] == ["approver"]
    assert members[str(world.editor.id)]["display_name"] == "Ewa Edytorska"
    assert str(world.outsider.id) not in members


async def test_members_list_is_paginated(api: AsyncClient, world: World) -> None:
    url = f"/api/v1/companies/{world.a.id}/members"
    full = (await api.get(url, headers=auth(world.viewer))).json()
    assert (full["limit"], full["offset"]) == (100, 0)
    everyone = [m["user_id"] for m in full["items"]]

    pages = []
    for offset in range(0, 4, 3):
        response = await api.get(
            url, params={"limit": 3, "offset": offset}, headers=auth(world.viewer)
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert (body["total"], body["limit"], body["offset"]) == (4, 3, offset)
        pages.append([m["user_id"] for m in body["items"]])
    assert [len(p) for p in pages] == [3, 1]
    assert pages[0] + pages[1] == everyone  # stable order, a user is never split
    for item in full["items"]:
        assert item["roles"]  # all roles of a user stay on one page

    for params in ({"limit": 0}, {"limit": 501}, {"offset": -1}):
        bad = await api.get(url, params=params, headers=auth(world.viewer))
        assert bad.status_code == 422


# Foreign / missing company -> 404: tests/test_isolation_api.py (tests/isolation_cases.py).


async def test_admin_lists_members_without_membership(api: AsyncClient, world: World) -> None:
    response = await api.get(f"/api/v1/companies/{world.b.id}/members", headers=auth(world.admin))
    assert response.status_code == 200, response.text
    assert [m["user_id"] for m in response.json()["items"]] == [str(world.outsider.id)]


async def test_set_roles_grants_and_revokes_with_audit(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    url = f"/api/v1/companies/{world.a.id}/members/{world.editor.id}"
    response = await api.put(url, json={"roles": ["approver", "viewer"]}, headers=auth(world.admin))
    assert response.status_code == 200, response.text
    assert response.json()["roles"] == ["approver", "viewer"]

    entries = [e for e in await audit_entries(rw_engine, world.editor.id) if e.action != "create"]
    assert [(e.action, e.company_id, e.entity_type) for e in entries[-2:]] == [
        ("role_grant", world.a.id, "membership"),
        ("role_revoke", world.a.id, "membership"),
    ]
    grant, revoke = entries[-2:]
    assert grant.diff == {
        "roles": {"before": ["editor"], "after": ["approver", "editor", "viewer"]}
    }
    assert grant.context["granted"] == ["approver", "viewer"]
    assert grant.context["user_id"] == str(world.editor.id)
    assert grant.context["self_grant"] is False
    assert revoke.diff == {
        "roles": {"before": ["approver", "editor", "viewer"], "after": ["approver", "viewer"]}
    }
    assert revoke.context["revoked"] == ["editor"]
    assert grant.actor_id == world.admin.id
    assert grant.actor_roles == ["app_admin"]
    assert (await verify(rw_engine, world.a.id)).ok

    # The new roles apply to the next request.
    me = (await api.get("/api/v1/me", headers=auth(world.editor))).json()
    assert me["memberships"][0]["roles"] == ["approver", "viewer"]


async def test_set_same_roles_is_noop(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    before = len(await audit_entries(rw_engine, world.viewer.id))
    response = await api.put(
        f"/api/v1/companies/{world.a.id}/members/{world.viewer.id}",
        json={"roles": ["viewer"]},
        headers=auth(world.admin),
    )
    assert response.status_code == 200, response.text
    assert len(await audit_entries(rw_engine, world.viewer.id)) == before


async def test_remove_all_roles(api: AsyncClient, world: World, rw_engine: AsyncEngine) -> None:
    response = await api.put(
        f"/api/v1/companies/{world.a.id}/members/{world.viewer.id}",
        json={"roles": []},
        headers=auth(world.admin),
    )
    assert response.status_code == 200, response.text
    assert response.json()["roles"] == []
    gone = await api.get(f"/api/v1/companies/{world.a.id}/members", headers=auth(world.viewer))
    assert_problem(gone, 404, "company.not_found")
    entry = (await audit_entries(rw_engine, world.viewer.id))[-1]
    assert entry.action == "role_revoke"
    assert entry.diff == {"roles": {"before": ["viewer"], "after": []}}


async def test_admin_grants_role_to_self_is_audited(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    response = await api.put(
        f"/api/v1/companies/{world.b.id}/members/{world.admin.id}",
        json={"roles": ["approver"]},
        headers=auth(world.admin),
    )
    assert response.status_code == 200, response.text
    entry = (await audit_entries(rw_engine, world.admin.id))[-1]
    assert (entry.action, entry.company_id) == ("role_grant", world.b.id)
    assert entry.context["self_grant"] is True
    assert (await verify(rw_engine, world.b.id)).ok


async def test_admin_does_not_get_company_register_context_without_membership(
    api: AsyncClient, world: World
) -> None:
    # Admin path works (members), but admin is not a member: not listed as own company.
    me = (await api.get("/api/v1/me", headers=auth(world.admin))).json()
    assert me["memberships"] == []


async def test_set_roles_validation(api: AsyncClient, world: World, rw_engine: AsyncEngine) -> None:
    url = f"/api/v1/companies/{world.a.id}/members"
    bad_role = await api.put(
        f"{url}/{world.editor.id}", json={"roles": ["app_admin"]}, headers=auth(world.admin)
    )
    assert_problem(bad_role, 422, "request.validation_error")
    unknown_user = await api.put(
        f"{url}/{uuid4()}", json={"roles": ["viewer"]}, headers=auth(world.admin)
    )
    assert_problem(unknown_user, 404, "user.not_found")
    unknown_company = await api.put(
        f"/api/v1/companies/{uuid4()}/members/{world.editor.id}",
        json={"roles": ["viewer"]},
        headers=auth(world.admin),
    )
    assert_problem(unknown_company, 404, "company.not_found")
    inactive = await make_user(rw_engine, active=False)
    response = await api.put(
        f"{url}/{inactive.id}", json={"roles": ["viewer"]}, headers=auth(world.admin)
    )
    assert_problem(response, 422, "membership.user_inactive")


async def test_users_list_for_admin(api: AsyncClient, world: World) -> None:
    # Search by the unique e-mail: the shared test database holds many users with the same
    # display name, so a name search could push this one beyond the first page.
    response = await api.get(
        "/api/v1/users", params={"q": world.editor.email}, headers=auth(world.admin)
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert [u["id"] for u in body["items"]] == [str(world.editor.id)]
    user = next(u for u in body["items"] if u["id"] == str(world.editor.id))
    assert set(user) == {
        "id",
        "external_id",
        "email",
        "display_name",
        "is_app_admin",
        "is_active",
        "created_at",
        "updated_at",
        # Password STATE of a local account (ADR 0018) - never the hash.
        "has_password",
        "must_change_password",
        "temp_password_expires_at",
        "password_changed_at",
        "locked_until",
    }
    assert user["has_password"] is False  # a user without a password (factory)
    assert user["temp_password_expires_at"] is None
