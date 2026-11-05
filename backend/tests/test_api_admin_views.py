"""Read models of the admin UI (ADR 0015): company counters, user detail, RBAC matrix."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI, Request
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncEngine

from app.api.v1 import companies as companies_api
from app.auth.principal import AuditChainContext
from app.db import SessionDep, run_read_only
from app.permissions import (
    ACTION_DESCRIPTIONS,
    CHANGE_ACTION_PERMISSIONS,
    PERMISSIONS,
    Action,
    CompanyVisibility,
    Role,
    require_audit_chain,
    visible_companies,
)
from tests.factories import (
    World,
    all_companies,
    auth,
    client_for,
    grant,
    make_ci,
    make_company,
    make_user,
    scoped,
)
from tests.test_api_auth import assert_problem


def test_every_action_has_a_polish_description() -> None:
    assert set(ACTION_DESCRIPTIONS) == set(Action)
    for label, note in ACTION_DESCRIPTIONS.values():
        assert label.strip()
        assert note is None or note.strip()


# --------------------------------------------------------------------------- companies


@pytest.mark.db
async def test_company_list_counts_ci_and_roles(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    inactive = await make_ci(rw_engine, world.a, world.ci_type, name="Stary serwer")
    async with scoped(rw_engine, [world.a.id]) as session:
        await session.execute(
            text("UPDATE configuration_items SET is_active = false WHERE id = :id"),
            {"id": inactive.id},
        )
    expected = {
        "active_ci": 1,
        "all_ci": 2,
        "editors": 1,
        "approvers": 1,
        "auditors": 1,
        "viewers": 1,
    }
    # A member sees the counters of their own company.
    member = (await api.get("/api/v1/companies", headers=auth(world.viewer))).json()
    assert member["items"][0]["counts"] == expected

    # The admin (no membership) gets them for every company on the page - the CI scope is
    # widened for the listing, otherwise RLS would hide the inventory (counts = 0).
    by_id = {c["id"]: c for c in await all_companies(api, world.admin)}
    assert by_id[str(world.a.id)]["counts"] == expected
    assert by_id[str(world.b.id)]["counts"] == {
        "active_ci": 1,
        "all_ci": 1,
        "editors": 1,
        "approvers": 1,
        "auditors": 0,
        "viewers": 0,
    }
    assert by_id[str(world.a.id)]["my_roles"] == []


@pytest.mark.db
async def test_new_company_has_zero_counts(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    company = await make_company(rw_engine)
    item = next(c for c in await all_companies(api, world.admin) if c["id"] == str(company.id))
    assert set(item["counts"].values()) == {0}


# --------------------------------------------------------------------------- users


@pytest.mark.db
async def test_user_detail_lists_roles_in_every_company(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    user = await make_user(rw_engine, name="Wiele Spółek")
    await grant(rw_engine, world.a, user, Role.EDITOR, Role.VIEWER)
    await grant(rw_engine, world.b, user, Role.AUDITOR)
    response = await api.get(f"/api/v1/users/{user.id}", headers=auth(world.admin))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == str(user.id)
    assert body["is_active"] is True
    roles = {m["company_id"]: m["roles"] for m in body["memberships"]}
    assert roles == {str(world.a.id): ["editor", "viewer"], str(world.b.id): ["auditor"]}
    first = body["memberships"][0]
    assert set(first) == {"company_id", "company_name", "company_prefix", "company_status", "roles"}

    lonely = await api.get(f"/api/v1/users/{world.nobody.id}", headers=auth(world.admin))
    assert lonely.json()["memberships"] == []


@pytest.mark.db
async def test_user_detail_unknown_is_404(api: AsyncClient, world: World) -> None:
    response = await api.get(f"/api/v1/users/{uuid4()}", headers=auth(world.admin))
    assert_problem(response, 404, "user.not_found")


@pytest.mark.db
async def test_user_detail_is_admin_only(api: AsyncClient, world: World) -> None:
    response = await api.get(f"/api/v1/users/{world.editor.id}", headers=auth(world.approver))
    assert_problem(response, 403, "auth.forbidden")


# --------------------------------------------------------------------------- matrix


@pytest.mark.db
async def test_permission_matrix_mirrors_permissions(api: AsyncClient, world: World) -> None:
    response = await api.get("/api/v1/permissions/matrix", headers=auth(world.viewer))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["roles"] == ["app_admin", "approver", "editor", "auditor", "viewer"]
    assert [row["action"] for row in body["actions"]] == [a.value for a in Action]
    for row in body["actions"]:
        action = Action(row["action"])
        assert set(row["roles"]) == {r.value for r in PERMISSIONS[action]}
        assert row["label"] == ACTION_DESCRIPTIONS[action][0]
    assert {r["action"]: r["requires"] for r in body["change_actions"]} == {
        k: v.value for k, v in CHANGE_ACTION_PERMISSIONS.items()
    }
    # The admin without memberships reads it too; a user without roles does not.
    assert (
        await api.get("/api/v1/permissions/matrix", headers=auth(world.admin))
    ).status_code == 200
    denied = await api.get("/api/v1/permissions/matrix", headers=auth(world.nobody))
    assert_problem(denied, 403, "auth.forbidden")


# --------------------------------------------------------------------------- scope of admin reads


async def _rejected(session: Any, sql: str, params: dict[str, Any]) -> str:
    """Run a write in a savepoint; return the database error (empty when it passed)."""
    try:
        async with session.begin_nested():
            await session.execute(text(sql), params)
    except DBAPIError as exc:
        return str(exc.orig)
    return ""


_MEMBERSHIP_INSERT = (
    "INSERT INTO company_memberships (id, user_id, company_id, role, created_at, updated_at) "
    "VALUES (gen_random_uuid(), :u, :c, 'viewer', now(), now())"
)


@pytest.mark.db
async def test_company_list_does_not_widen_the_request_transaction(
    db_app: FastAPI, world: World
) -> None:
    """Counters come from a separate read-only transaction (ADR 0015 §2): after listing
    the admin's companies, the REQUEST transaction still cannot read other companies'
    audit chains or write their memberships."""
    a_id = world.a.id

    @db_app.get("/test/probe-company-list")
    async def probe(
        request: Request,
        session: SessionDep,
        visibility: CompanyVisibility = visible_companies(
            Action.REGISTER_VIEW, admin_action=Action.COMPANY_MANAGE
        ),
    ) -> dict[str, Any]:
        page = await companies_api.list_companies(
            request=request, session=session, visibility=visibility, limit=500, offset=0
        )
        audit_rows = (
            await session.execute(
                text("SELECT count(*) FROM audit_log WHERE company_id = :c"), {"c": a_id}
            )
        ).scalar_one()
        error = await _rejected(session, _MEMBERSHIP_INSERT, {"u": world.nobody.id, "c": a_id})
        return {"items": page.total, "audit_rows": audit_rows, "error": error}

    async with client_for(db_app) as client:
        body = (await client.get("/test/probe-company-list", headers=auth(world.admin))).json()
    assert body["items"] >= 2
    assert body["audit_rows"] == 0
    assert "row-level security" in body["error"]


@pytest.mark.db
async def test_read_only_helper_refuses_writes(db_app: FastAPI, world: World) -> None:
    async def write(session: Any) -> str:
        return await _rejected(session, _MEMBERSHIP_INSERT, {"u": world.nobody.id, "c": world.a.id})

    error = await run_read_only(db_app.state.db, write, company_ids=[world.a.id])
    assert "read-only transaction" in error


@pytest.mark.db
async def test_admin_reads_any_company_log_on_a_narrow_read_only_path(
    db_app: FastAPI, world: World
) -> None:
    """Owner decision 2026-11-02 (ADR 0015 §7): the admin reads the log of a company
    without membership; the transaction holds only that company and is READ ONLY."""
    b_id = world.b.id

    @db_app.get("/test/probe-admin-audit")
    async def probe(
        session: SessionDep,
        chain: AuditChainContext = require_audit_chain(
            Action.AUDIT_READ, admin_read_any_company=True
        ),
    ) -> dict[str, Any]:
        own = (
            await session.execute(
                text("SELECT count(*) FROM audit_log WHERE company_id = :c"),
                {"c": chain.company_id},
            )
        ).scalar_one()
        other = (
            await session.execute(
                text("SELECT count(*) FROM audit_log WHERE company_id = :c"), {"c": b_id}
            )
        ).scalar_one()
        error = await _rejected(
            session, _MEMBERSHIP_INSERT, {"u": world.nobody.id, "c": chain.company_id}
        )
        return {"own": own, "other": other, "error": error}

    async with client_for(db_app) as client:
        response = await client.get(
            "/test/probe-admin-audit",
            params={"company_id": str(world.a.id)},
            headers=auth(world.admin),
        )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["own"] > 0
    assert body["other"] == 0
    assert "read-only transaction" in body["error"]


@pytest.mark.db
async def test_admin_audit_log_and_status_without_membership(
    api: AsyncClient, world: World, rw_engine: AsyncEngine
) -> None:
    entries = await api.get(
        "/api/v1/audit", params={"company_id": str(world.a.id)}, headers=auth(world.admin)
    )
    assert entries.status_code == 200, entries.text
    assert entries.json()["total"] > 0
    status = await api.get(
        f"/api/v1/companies/{world.a.id}/audit/status", headers=auth(world.admin)
    )
    assert status.status_code == 200, status.text
    missing = await api.get(
        "/api/v1/audit", params={"company_id": str(uuid4())}, headers=auth(world.admin)
    )
    assert_problem(missing, 404, "company.not_found")
    # An auditor of another company only: still 404 (§7.3).
    foreign_auditor = await make_user(rw_engine, name="Obca Audytorka")
    await grant(rw_engine, world.b, foreign_auditor, Role.AUDITOR)
    denied = await api.get(
        "/api/v1/audit", params={"company_id": str(world.a.id)}, headers=auth(foreign_auditor)
    )
    assert_problem(denied, 404, "company.not_found")
