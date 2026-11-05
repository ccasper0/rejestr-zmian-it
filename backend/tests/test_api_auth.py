"""Authentication through the API: current_user, dev endpoints, mode-specific routes."""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.auth.dependencies import CurrentUserDep
from app.auth.dev import issue_dev_token
from app.db import SessionDep
from app.main import create_app
from tests.auth_helpers import LOCAL_SECRET
from tests.conftest import DEV_SECRET, DbUrls, make_settings
from tests.factories import (
    World,
    auth,
    client_for,
    make_user,
)

pytestmark = pytest.mark.db


def assert_problem(response: Any, status: int, code: str) -> dict[str, Any]:
    assert response.status_code == status, response.text
    assert response.headers["content-type"].startswith("application/problem+json")
    body: dict[str, Any] = response.json()
    assert body["code"] == code
    assert body["detail"]  # Polish, user facing
    return body


# --------------------------------------------------------------------------- bearer handling


async def test_missing_token_is_401(api: AsyncClient) -> None:
    response = await api.get("/api/v1/me")
    assert_problem(response, 401, "auth.invalid_token")
    assert response.headers["www-authenticate"].startswith("Bearer")


@pytest.mark.parametrize(
    "header",
    ["Bearer garbage", "Basic dXNlcjpwYXNz", "Bearer ", "Token abc"],
)
async def test_malformed_credentials_are_401(api: AsyncClient, header: str) -> None:
    response = await api.get("/api/v1/me", headers={"Authorization": header})
    assert_problem(response, 401, "auth.invalid_token")


async def test_token_signed_with_other_secret_is_401(api: AsyncClient, world: World) -> None:
    token, _ = issue_dev_token("z" * 40, world.editor.external_id)
    response = await api.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert_problem(response, 401, "auth.invalid_token")


async def test_dev_token_of_unknown_user_is_401(api: AsyncClient) -> None:
    token, _ = issue_dev_token(DEV_SECRET, "nobody-knows-me")
    response = await api.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert_problem(response, 401, "auth.invalid_token")


async def test_inactive_user_is_403(api: AsyncClient, rw_engine: AsyncEngine) -> None:
    user = await make_user(rw_engine, active=False)
    response = await api.get("/api/v1/me", headers=auth(user))
    assert_problem(response, 403, "auth.user_inactive")


# --------------------------------------------------------------------------- /me


async def test_me_returns_profile_and_memberships(api: AsyncClient, world: World) -> None:
    response = await api.get("/api/v1/me", headers=auth(world.approver))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == str(world.approver.id)
    assert body["display_name"] == "Jan Zatwierdzający"
    assert body["is_app_admin"] is False
    assert body["memberships"] == [
        {
            "company_id": str(world.a.id),
            "company_name": world.a.name,
            "company_prefix": world.a.prefix,
            "company_status": "active",
            "roles": ["approver"],
        }
    ]


async def test_me_for_user_with_several_roles_and_admin(api: AsyncClient, world: World) -> None:
    body = (await api.get("/api/v1/me", headers=auth(world.outsider))).json()
    assert [m["roles"] for m in body["memberships"]] == [["approver", "editor"]]
    admin = (await api.get("/api/v1/me", headers=auth(world.admin))).json()
    assert admin["is_app_admin"] is True
    assert admin["memberships"] == []


# --------------------------------------------------------------------------- request scope


async def test_request_transaction_is_scoped_to_user_companies(
    db_urls: DbUrls, world: World
) -> None:
    """The session used by endpoints is the one scoped by current_user (same transaction)."""
    app = create_app(make_settings(database_url=db_urls.rw))

    @app.get("/api/v1/_test/scope")
    async def _scope(user: CurrentUserDep, session: SessionDep) -> dict[str, Any]:
        row = (
            await session.execute(
                text(
                    "SELECT current_setting('app.company_ids', true) AS ids, "
                    "current_setting('app.user_id', true) AS uid, "
                    "current_setting('app.audit_global_read', true) AS audit_read, "
                    "current_setting('app.admin_scope', true) AS admin_scope"
                )
            )
        ).one()
        return {"ids": row.ids, "uid": row.uid, "audit": row.audit_read, "admin": row.admin_scope}

    try:
        async with client_for(app) as client:
            editor = (await client.get("/api/v1/_test/scope", headers=auth(world.editor))).json()
            auditor = (await client.get("/api/v1/_test/scope", headers=auth(world.auditor))).json()
            admin = (await client.get("/api/v1/_test/scope", headers=auth(world.admin))).json()
    finally:
        await app.state.db.dispose()
    assert editor == {
        "ids": "{" + str(world.a.id) + "}",
        "uid": str(world.editor.id),
        "audit": "off",
        "admin": "off",
    }
    # The global chain holds data of every company: app admins only (ADR 0006 §6).
    assert auditor == {
        "ids": "{" + str(world.a.id) + "}",
        "uid": str(world.auditor.id),
        "audit": "off",
        "admin": "off",
    }
    assert admin == {"ids": "{}", "uid": str(world.admin.id), "audit": "on", "admin": "off"}


# --------------------------------------------------------------------------- dev endpoints


async def test_dev_users_lists_database_users(api: AsyncClient, world: World) -> None:
    response = await api.get("/api/v1/auth/dev/users")
    assert response.status_code == 200, response.text
    by_id = {u["external_id"]: u for u in response.json()}
    assert by_id[world.admin.external_id]["is_app_admin"] is True
    assert by_id[world.editor.external_id]["display_name"] == "Ewa Edytorska"


async def test_dev_token_endpoint_issues_a_working_token(api: AsyncClient, world: World) -> None:
    response = await api.post(
        "/api/v1/auth/dev/token", json={"external_id": world.editor.external_id}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "Bearer"
    assert body["expires_in"] > 0
    me = await api.get("/api/v1/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.json()["id"] == str(world.editor.id)


async def test_dev_token_for_unknown_user_is_404(api: AsyncClient) -> None:
    response = await api.post("/api/v1/auth/dev/token", json={"external_id": "ghost"})
    assert_problem(response, 404, "auth.dev_user_not_found")


async def test_dev_endpoints_do_not_exist_outside_dev_mode(db_urls: DbUrls) -> None:
    app = create_app(
        make_settings(
            auth_mode="local",
            app_env="prod",
            dev_auth_secret=None,
            auth_jwt_secret=LOCAL_SECRET,
            database_url=db_urls.rw,
        )
    )
    try:
        async with client_for(app) as client:
            users = await client.get("/api/v1/auth/dev/users")
            token = await client.post("/api/v1/auth/dev/token", json={"external_id": "x"})
    finally:
        await app.state.db.dispose()
    assert users.status_code == 404
    assert token.status_code == 404
    assert not [r for r in app.routes if "/auth/dev" in getattr(r, "path", "")]


async def test_app_refuses_to_serve_in_local_mode_without_secret() -> None:
    app = create_app(make_settings(auth_mode="local", dev_auth_secret=None))
    with pytest.raises(RuntimeError, match="AUTH_JWT_SECRET"):
        async with app.router.lifespan_context(app):
            pass


async def test_local_auth_endpoints_do_not_exist_in_dev_mode(api: AsyncClient) -> None:
    for path in ("/api/v1/auth/login", "/api/v1/auth/refresh", "/api/v1/auth/password"):
        response = await api.post(path, json={})
        assert response.status_code == 404, path
