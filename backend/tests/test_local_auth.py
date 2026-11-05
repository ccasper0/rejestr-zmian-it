"""Local accounts with passwords (AUTH_MODE=local, ADR 0018): login, lockout, sessions,
refresh rotation and reuse detection, logout, password change, temporary passwords,
admin account management, audit without secrets."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app import logs
from app.auth.passwords import hash_password
from app.errors import ProblemError
from app.main import create_app
from app.models import User
from app.services import users as users_service
from app.services.local_auth import db_now, refresh_token_hash
from tests.auth_helpers import LOCAL_SECRET
from tests.conftest import DbUrls, make_settings
from tests.factories import SYSTEM, audit_entries, scoped, verify
from tests.test_api_auth import assert_problem

pytestmark = pytest.mark.db

PASSWORD = "Zielony-Rower-Nad-Wisłą-7"
OTHER_PASSWORD = "Pochmurny-Kot-Na-Dachu-42"
ME = "/api/v1/me"


# --------------------------------------------------------------------------- fixtures


def local_settings(db_urls: DbUrls, **overrides: Any) -> Any:
    values: dict[str, Any] = {
        "auth_mode": "local",
        "auth_jwt_secret": LOCAL_SECRET,
        "dev_auth_secret": None,
        "database_url": db_urls.rw,
        # Off by default: every test client shares one address (the limit is tested
        # explicitly with its own address).
        "auth_login_max_failures_per_network": 0,
    }
    values.update(overrides)
    return make_settings(**values)


@pytest.fixture
async def local_app(db_urls: DbUrls) -> AsyncIterator[FastAPI]:
    application = create_app(local_settings(db_urls))
    yield application
    await application.state.db.dispose()


def client(app: FastAPI, ip: str = "127.0.0.1") -> AsyncClient:
    return AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False, client=(ip, 123)),
        base_url="http://test",
    )


@pytest.fixture
async def api(local_app: FastAPI) -> AsyncIterator[AsyncClient]:
    async with client(local_app) as c:
        yield c


@dataclass
class Account:
    user: User
    email: str
    password: str


async def make_account(
    engine: AsyncEngine,
    *,
    admin: bool = False,
    password: str = PASSWORD,
    must_change: bool = False,
    name: str | None = None,
) -> Account:
    suffix = uuid4().hex[:10]
    email = f"Lokalny.{suffix}@Example.com"
    async with scoped(engine) as session:
        account = await users_service.create_local_account(
            session,
            actor=SYSTEM,
            email=email,
            display_name=name or f"Konto {suffix}",
            is_app_admin=admin,
            password_hash=hash_password(password),
        )
        if must_change:
            # As issued by POST /users: valid for TEMP_PASSWORD_TTL_HOURS (default 7 days).
            now = await db_now(session)  # (before the change: autoflush)
            account.credential.must_change_password = True
            account.credential.temp_password_expires_at = now + timedelta(hours=168)
    return Account(account.user, email, password)


async def login(api: AsyncClient, email: str, password: str) -> Response:
    return await api.post("/api/v1/auth/login", json={"email": email, "password": password})


async def tokens(api: AsyncClient, account: Account) -> dict[str, Any]:
    response = await login(api, account.email, account.password)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def bearer(body: dict[str, Any]) -> dict[str, str]:
    return {"Authorization": f"Bearer {body['access_token']}"}


async def credential_row(engine: AsyncEngine, user_id: UUID) -> Any:
    async with scoped(engine) as session:
        return (
            await session.execute(
                text("SELECT * FROM user_credentials WHERE user_id = :u"), {"u": user_id}
            )
        ).one()


async def entries(engine: AsyncEngine, user_id: UUID) -> list[Any]:
    return await audit_entries(engine, user_id, include_auth=True)


def actions(rows: list[Any]) -> list[str]:
    return [r.action for r in rows]


def comparable(response: Response) -> dict[str, Any]:
    body: dict[str, Any] = response.json()
    return {k: v for k, v in body.items() if k not in {"request_id"}}


# --------------------------------------------------------------------------- login


async def test_login_issues_tokens_and_the_session_works(
    api: AsyncClient, rw_engine: AsyncEngine
) -> None:
    account = await make_account(rw_engine)
    response = await login(api, account.email.upper(), account.password)  # any case
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body["token_type"] == "Bearer"
    assert 0 < body["expires_in"] <= 3600
    assert body["refresh_token"]
    assert body["refresh_expires_in"] > 0
    assert body["session_expires_at"].endswith("Z")
    assert body["must_change_password"] is False

    me = await api.get(ME, headers=bearer(body))
    assert me.status_code == 200, me.text
    assert me.json()["id"] == str(account.user.id)
    assert me.json()["must_change_password"] is False

    rows = await entries(rw_engine, account.user.id)
    login_entry = next(r for r in rows if r.action == "login")
    assert login_entry.entity_type == "auth"
    assert login_entry.actor_id == account.user.id
    assert login_entry.context["method"] == "password"
    assert UUID(login_entry.context["session_id"])
    # One login entry: requests with the access token do not log in again (ADR 0018).
    assert actions(rows).count("login") == 1
    assert (await verify(rw_engine, None)).ok


async def test_failures_look_the_same_whatever_the_reason(
    api: AsyncClient, rw_engine: AsyncEngine
) -> None:
    account = await make_account(rw_engine)
    inactive = await make_account(rw_engine)
    async with scoped(rw_engine) as session:
        await users_service.update_user(
            session, actor=SYSTEM, user_id=inactive.user.id, is_active=False
        )
    async with scoped(rw_engine) as session:
        no_password = await users_service.create_user(
            session,
            actor=SYSTEM,
            external_id=f"nopw-{uuid4().hex[:8]}",
            email=f"nopw-{uuid4().hex[:8]}@example.com",
            display_name="Bez Hasła",
        )

    responses = [
        await login(api, account.email, "Zle-Haslo-Calkiem-Inne-1"),
        await login(api, f"nikt-{uuid4().hex[:8]}@example.com", PASSWORD),
        await login(api, inactive.email, inactive.password),  # correct password
        await login(api, no_password.email, PASSWORD),
    ]
    bodies = []
    for response in responses:
        assert_problem(response, 401, "auth.invalid_credentials")
        assert response.headers["cache-control"] == "no-store"
        bodies.append(comparable(response))
    assert all(b == bodies[0] for b in bodies)

    # The log tells them apart; never with the password or the unknown e-mail.
    async with scoped(rw_engine, [], global_read=True) as session:
        rows = (
            await session.execute(
                text(
                    "SELECT context FROM audit_log WHERE company_id IS NULL "
                    "AND action = 'login_failed' AND entity_id = ANY(:ids)"
                ),
                {"ids": [account.user.id, inactive.user.id, no_password.id]},
            )
        ).all()
    reasons = {r.context["reason"] for r in rows}
    assert {"invalid_password", "user_inactive", "no_password"} <= reasons


async def test_login_validation(api: AsyncClient) -> None:
    response = await api.post("/api/v1/auth/login", json={"email": "a@example.com"})
    assert response.status_code == 422
    too_long = await api.post(
        "/api/v1/auth/login", json={"email": "a@example.com", "password": "x" * 2000}
    )
    assert too_long.status_code == 422


# --------------------------------------------------------------------------- lockout


async def test_lockout_after_threshold_and_unlock_by_time(
    api: AsyncClient, rw_engine: AsyncEngine
) -> None:
    account = await make_account(rw_engine)
    for _ in range(4):
        assert_problem(
            await login(api, account.email, "Zle-Haslo-123456"), 401, "auth.invalid_credentials"
        )
    assert (await credential_row(rw_engine, account.user.id)).failed_attempts == 4
    assert_problem(
        await login(api, account.email, "Zle-Haslo-123456"), 401, "auth.invalid_credentials"
    )
    row = await credential_row(rw_engine, account.user.id)
    assert row.locked_until is not None
    assert row.failed_attempts == 0

    # Locked: even the correct password fails, with the same answer.
    assert_problem(
        await login(api, account.email, account.password), 401, "auth.invalid_credentials"
    )
    # Attempts during the lock do not extend it.
    assert (await credential_row(rw_engine, account.user.id)).locked_until == row.locked_until

    rows = await entries(rw_engine, account.user.id)
    lockout = [r for r in rows if r.action == "lockout"]
    assert len(lockout) == 1
    assert lockout[0].entity_type == "user"
    assert lockout[0].actor_id is None  # system
    assert lockout[0].context["trigger"] == "login"
    assert lockout[0].context["threshold"] == 5
    assert "locked_until" in lockout[0].diff

    # The lock expires (simulated: the lock moved to the past).
    async with scoped(rw_engine) as session:
        await session.execute(
            text(
                "UPDATE user_credentials SET locked_until = now() - interval '1 second' "
                "WHERE user_id = :u"
            ),
            {"u": account.user.id},
        )
    assert (await login(api, account.email, account.password)).status_code == 200
    after = await credential_row(rw_engine, account.user.id)
    assert (after.failed_attempts, after.locked_until) == (0, None)


async def test_successful_login_resets_the_counter(
    api: AsyncClient, rw_engine: AsyncEngine
) -> None:
    account = await make_account(rw_engine)
    for _ in range(3):
        await login(api, account.email, "Zle-Haslo-123456")
    assert (await login(api, account.email, account.password)).status_code == 200
    assert (await credential_row(rw_engine, account.user.id)).failed_attempts == 0


async def test_rate_limit_per_network(db_urls: DbUrls, rw_engine: AsyncEngine) -> None:
    app = create_app(local_settings(db_urls, auth_login_max_failures_per_network=3))
    account = await make_account(rw_engine)
    ip = f"10.{uuid4().int % 250}.{uuid4().int % 250}.{uuid4().int % 250 + 1}"
    try:
        async with client(app, ip) as attacker, client(app, "10.255.255.254") as other:
            for _ in range(3):
                emails = f"nikt-{uuid4().hex[:6]}@example.com"
                assert (await login(attacker, emails, PASSWORD)).status_code == 401
            limited = await login(attacker, account.email, account.password)
            body = assert_problem(limited, 429, "auth.too_many_attempts")
            assert int(limited.headers["retry-after"]) >= 1
            assert "konto" not in body["detail"].lower()
            # Another network is not affected.
            assert (await login(other, account.email, account.password)).status_code == 200
    finally:
        await app.state.db.dispose()


# --------------------------------------------------------------------------- refresh / logout


async def test_refresh_rotates_and_reuse_revokes_the_session(
    api: AsyncClient, rw_engine: AsyncEngine
) -> None:
    account = await make_account(rw_engine)
    first = await tokens(api, account)
    second_response = await api.post(
        "/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]}
    )
    assert second_response.status_code == 200, second_response.text
    second = second_response.json()
    assert second["refresh_token"] != first["refresh_token"]
    assert second["access_token"] != first["access_token"]
    assert second["session_expires_at"] == first["session_expires_at"]
    assert (await api.get(ME, headers=bearer(second))).status_code == 200
    assert (await api.get(ME, headers=bearer(first))).status_code == 200  # same session

    # The old refresh token presented again: reuse -> the whole session is revoked.
    reused = await api.post("/api/v1/auth/refresh", json={"refresh_token": first["refresh_token"]})
    assert_problem(reused, 401, "auth.invalid_refresh_token")
    assert_problem(
        await api.post("/api/v1/auth/refresh", json={"refresh_token": second["refresh_token"]}),
        401,
        "auth.invalid_refresh_token",
    )
    assert_problem(await api.get(ME, headers=bearer(second)), 401, "auth.session_expired")

    rows = await entries(rw_engine, account.user.id)
    assert "token_refresh" in actions(rows)
    revoke = [r for r in rows if r.action == "session_revoke"]
    assert len(revoke) == 1
    assert revoke[0].context["reason"] == "refresh_token_reuse"
    assert revoke[0].context["session_id"] == first_session(rows)


def first_session(rows: list[Any]) -> str:
    return str(next(r for r in rows if r.action == "login").context["session_id"])


async def test_unknown_refresh_token_is_401(api: AsyncClient) -> None:
    response = await api.post("/api/v1/auth/refresh", json={"refresh_token": "x" * 43})
    assert_problem(response, 401, "auth.invalid_refresh_token")


async def test_logout_revokes_the_session(api: AsyncClient, rw_engine: AsyncEngine) -> None:
    account = await make_account(rw_engine)
    body = await tokens(api, account)
    other = await tokens(api, account)  # a second session (another tab)
    response = await api.post("/api/v1/auth/logout", headers=bearer(body))
    assert response.status_code == 204, response.text
    assert_problem(await api.get(ME, headers=bearer(body)), 401, "auth.session_expired")
    assert_problem(
        await api.post("/api/v1/auth/refresh", json={"refresh_token": body["refresh_token"]}),
        401,
        "auth.invalid_refresh_token",
    )
    assert (await api.get(ME, headers=bearer(other))).status_code == 200
    rows = await entries(rw_engine, account.user.id)
    logout = [r for r in rows if r.action == "logout"]
    assert len(logout) == 1
    assert logout[0].actor_id == account.user.id


async def test_expired_session_cannot_be_refreshed(
    api: AsyncClient, rw_engine: AsyncEngine, owner_engine: AsyncEngine
) -> None:
    account = await make_account(rw_engine)
    body = await tokens(api, account)
    expired = f"expired-{uuid4().hex}"
    async with owner_engine.begin() as conn:
        # A refresh token past its idle limit (inserted as the owner: expires_at is
        # immutable and app_rw cannot set it in the past through the API).
        await conn.execute(
            text(
                "INSERT INTO auth_refresh_tokens (session_id, token_hash, expires_at) "
                "SELECT id, :h, now() - interval '1 second' FROM auth_sessions "
                "WHERE user_id = :u"
            ),
            {"u": account.user.id, "h": refresh_token_hash(expired)},
        )
    body = {"refresh_token": expired}
    assert_problem(
        await api.post("/api/v1/auth/refresh", json={"refresh_token": body["refresh_token"]}),
        401,
        "auth.invalid_refresh_token",
    )


# --------------------------------------------------------------------------- password change


async def test_temporary_password_restricts_access_until_changed(
    api: AsyncClient, rw_engine: AsyncEngine
) -> None:
    account = await make_account(rw_engine, must_change=True)
    body = await tokens(api, account)
    assert body["must_change_password"] is True
    me = await api.get(ME, headers=bearer(body))
    assert me.status_code == 200
    assert me.json()["must_change_password"] is True
    for method, url in (("GET", "/api/v1/companies"), ("GET", "/api/v1/permissions/matrix")):
        response = await api.request(method, url, headers=bearer(body))
        assert_problem(response, 403, "auth.password_change_required")
    denied = [r for r in await entries(rw_engine, account.user.id) if r.action == "access_denied"]
    assert denied
    assert denied[-1].context["reason"] == "password_change_required"

    changed = await api.post(
        "/api/v1/auth/password",
        json={"current_password": account.password, "new_password": OTHER_PASSWORD},
        headers=bearer(body),
    )
    assert changed.status_code == 200, changed.text
    fresh = changed.json()
    assert fresh["must_change_password"] is False
    assert (await api.get("/api/v1/companies", headers=bearer(fresh))).status_code == 200
    # The password change ended the old session.
    assert_problem(await api.get(ME, headers=bearer(body)), 401, "auth.session_expired")
    assert (await login(api, account.email, OTHER_PASSWORD)).status_code == 200
    assert_problem(
        await login(api, account.email, account.password), 401, "auth.invalid_credentials"
    )

    rows = await entries(rw_engine, account.user.id)
    change = [r for r in rows if r.action == "password_change"]
    assert len(change) == 1
    assert change[0].entity_type == "user"
    assert change[0].actor_id == account.user.id
    assert change[0].diff["must_change_password"] == {"before": True, "after": False}
    assert change[0].context["sessions_revoked"]


async def test_logout_is_allowed_with_a_temporary_password(
    api: AsyncClient, rw_engine: AsyncEngine
) -> None:
    account = await make_account(rw_engine, must_change=True)
    body = await tokens(api, account)
    assert (await api.post("/api/v1/auth/logout", headers=bearer(body))).status_code == 204


@pytest.mark.parametrize(
    ("new_password", "code"),
    [
        ("krotkie", "auth.password_too_short"),
        ("x" * 129 + "Ab1", "auth.password_too_long"),
        ("aaaaaaaaaaaaaaaa", "auth.password_too_simple"),
        ("qwertyuiopasdfgh", "auth.password_too_simple"),
        ("Password1234", "auth.password_too_common"),
        ("haslo1234567", "auth.password_too_common"),
        (PASSWORD, "auth.password_reused"),
    ],
)
async def test_password_policy_on_change(
    api: AsyncClient, rw_engine: AsyncEngine, new_password: str, code: str
) -> None:
    account = await make_account(rw_engine)
    body = await tokens(api, account)
    response = await api.post(
        "/api/v1/auth/password",
        json={"current_password": account.password, "new_password": new_password},
        headers=bearer(body),
    )
    assert_problem(response, 422, code)


async def test_password_must_not_contain_the_identity(
    api: AsyncClient, rw_engine: AsyncEngine
) -> None:
    account = await make_account(rw_engine, name="Grzegorz Brzęczyszczykiewicz")
    body = await tokens(api, account)
    for candidate in (
        account.email,
        f"x{account.email.split('@')[0]}!2026",
        "GrzegorzBrzęczyszczykiewicz!",
    ):
        response = await api.post(
            "/api/v1/auth/password",
            json={"current_password": account.password, "new_password": candidate},
            headers=bearer(body),
        )
        assert_problem(response, 422, "auth.password_contains_identity")


async def test_wrong_current_password_is_counted_and_locks_with_sessions(
    api: AsyncClient, rw_engine: AsyncEngine
) -> None:
    account = await make_account(rw_engine)
    body = await tokens(api, account)
    for _ in range(4):
        response = await api.post(
            "/api/v1/auth/password",
            json={"current_password": "Zle-Haslo-123456", "new_password": OTHER_PASSWORD},
            headers=bearer(body),
        )
        assert_problem(response, 400, "auth.invalid_current_password")
    assert (await credential_row(rw_engine, account.user.id)).failed_attempts == 4
    await api.post(
        "/api/v1/auth/password",
        json={"current_password": "Zle-Haslo-123456", "new_password": OTHER_PASSWORD},
        headers=bearer(body),
    )
    # Locked, and whoever held the session is out.
    assert_problem(await api.get(ME, headers=bearer(body)), 401, "auth.session_expired")
    rows = await entries(rw_engine, account.user.id)
    lockout = next(r for r in rows if r.action == "lockout")
    assert lockout.context["trigger"] == "password_change"
    assert lockout.context["sessions_revoked"]
    failed = [r for r in rows if r.action == "login_failed"]
    guesses = [r for r in failed if r.context["reason"] == "invalid_current_password"]
    assert guesses
    assert guesses[0].actor_id == account.user.id  # an authenticated attempt
    # Then the revoked session itself was refused.
    assert "session_invalid" in {r.context["reason"] for r in failed}


async def test_password_change_on_a_locked_account_is_423(
    api: AsyncClient, rw_engine: AsyncEngine
) -> None:
    account = await make_account(rw_engine)
    body = await tokens(api, account)
    async with scoped(rw_engine) as session:
        await session.execute(
            text(
                "UPDATE user_credentials SET locked_until = now() + interval '5 minutes' "
                "WHERE user_id = :u"
            ),
            {"u": account.user.id},
        )
    response = await api.post(
        "/api/v1/auth/password",
        json={"current_password": account.password, "new_password": OTHER_PASSWORD},
        headers=bearer(body),
    )
    assert_problem(response, 423, "auth.account_locked")


# --------------------------------------------------------------------------- temporary password TTL
# ADR 0018 §12 p. 4 (decision of the owner 2026-11-04): a temporary password (POST /users,
# POST /users/{id}/reset-password, create-admin --generate-password) is valid for
# TEMP_PASSWORD_TTL_HOURS (default 168 h = 7 days); time is moved by rewriting
# temp_password_expires_at (app_rw may update it, like locked_until).


async def expire_temporary_password(engine: AsyncEngine, user_id: UUID, seconds: int = -1) -> None:
    """Move the deadline to ``seconds`` from now (negative: already past)."""
    async with scoped(engine) as session:
        await session.execute(
            text(
                "UPDATE user_credentials "
                "SET temp_password_expires_at = now() + make_interval(secs => :s) "
                "WHERE user_id = :u"
            ),
            {"u": user_id, "s": seconds},
        )


async def session_rows(engine: AsyncEngine, user_id: UUID) -> list[Any]:
    async with scoped(engine) as session:
        return list(
            (
                await session.execute(
                    text("SELECT * FROM auth_sessions WHERE user_id = :u ORDER BY created_at"),
                    {"u": user_id},
                )
            ).all()
        )


def parse_utc(value: str) -> datetime:
    assert value.endswith("Z"), value
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


async def test_expired_temporary_password_is_refused_without_a_session(
    api: AsyncClient, rw_engine: AsyncEngine
) -> None:
    account = await make_account(rw_engine, must_change=True)
    await expire_temporary_password(rw_engine, account.user.id)

    response = await login(api, account.email, account.password)
    assert_problem(response, 401, "auth.temporary_password_expired")
    assert response.headers["cache-control"] == "no-store"
    assert "administrator" in response.json()["detail"]
    assert await session_rows(rw_engine, account.user.id) == []
    # The password was right: not a failed guess, the lockout counter is untouched.
    assert (await credential_row(rw_engine, account.user.id)).failed_attempts == 0

    rows = await entries(rw_engine, account.user.id)
    failed = [r for r in rows if r.action == "login_failed"]
    assert [r.context["reason"] for r in failed] == ["temporary_password_expired"]
    assert "login" not in actions(rows)
    assert_no_secrets(rows, [account.password])
    assert (await verify(rw_engine, None)).ok


async def test_wrong_password_on_an_expired_temporary_password_reveals_nothing(
    api: AsyncClient, rw_engine: AsyncEngine
) -> None:
    account = await make_account(rw_engine, must_change=True)
    await expire_temporary_password(rw_engine, account.user.id)
    response = await login(api, account.email, "Zle-Haslo-Calkiem-Inne-1")
    assert_problem(response, 401, "auth.invalid_credentials")
    assert (await credential_row(rw_engine, account.user.id)).failed_attempts == 1
    reasons = [
        r.context["reason"]
        for r in await entries(rw_engine, account.user.id)
        if r.action == "login_failed"
    ]
    assert reasons == ["invalid_password"]


async def test_temporary_password_works_until_the_deadline_and_caps_the_session(
    api: AsyncClient, rw_engine: AsyncEngine
) -> None:
    account = await make_account(rw_engine, must_change=True)
    await expire_temporary_password(rw_engine, account.user.id, 60)
    response = await login(api, account.email, account.password)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["must_change_password"] is True
    deadline = (await credential_row(rw_engine, account.user.id)).temp_password_expires_at
    # The session cannot outlive the temporary password (nor can its refresh token).
    assert parse_utc(body["session_expires_at"]) == deadline
    assert body["refresh_expires_in"] <= 60
    [row] = await session_rows(rw_engine, account.user.id)
    assert row.expires_at == deadline


async def test_session_with_a_temporary_password_ends_at_the_deadline(
    api: AsyncClient, rw_engine: AsyncEngine
) -> None:
    account = await make_account(rw_engine, must_change=True)
    body = await tokens(api, account)
    await expire_temporary_password(rw_engine, account.user.id)

    # The access token stops working at once (the session check sees the deadline) ...
    assert_problem(await api.get(ME, headers=bearer(body)), 401, "auth.session_expired")
    changed = await api.post(
        "/api/v1/auth/password",
        json={"current_password": account.password, "new_password": OTHER_PASSWORD},
        headers=bearer(body),
    )
    assert_problem(changed, 401, "auth.session_expired")
    # ... and the refresh token cannot extend it: 401 and the session is revoked.
    refreshed = await api.post(
        "/api/v1/auth/refresh", json={"refresh_token": body["refresh_token"]}
    )
    assert_problem(refreshed, 401, "auth.temporary_password_expired")
    [row] = await session_rows(rw_engine, account.user.id)
    assert row.revoked_at is not None
    assert row.revoke_reason == "temporary_password_expired"
    # Revoked: refreshing again is just an invalid token.
    assert_problem(
        await api.post("/api/v1/auth/refresh", json={"refresh_token": body["refresh_token"]}),
        401,
        "auth.invalid_refresh_token",
    )

    rows = await entries(rw_engine, account.user.id)
    revoke = [r for r in rows if r.action == "session_revoke"]
    assert len(revoke) == 1
    assert revoke[0].actor_id is None  # system
    assert revoke[0].context["reason"] == "temporary_password_expired"
    assert revoke[0].context["session_id"] == str(row.id)
    reasons = [r.context["reason"] for r in rows if r.action == "login_failed"]
    assert "temporary_password_expired" in reasons
    assert "token_refresh" not in actions(rows)
    assert (await verify(rw_engine, None)).ok


async def test_password_change_before_the_deadline_clears_it(
    api: AsyncClient, rw_engine: AsyncEngine
) -> None:
    account = await make_account(rw_engine, must_change=True)
    body = await tokens(api, account)
    refreshed = await api.post(
        "/api/v1/auth/refresh", json={"refresh_token": body["refresh_token"]}
    )
    assert refreshed.status_code == 200, refreshed.text
    changed = await api.post(
        "/api/v1/auth/password",
        json={"current_password": account.password, "new_password": OTHER_PASSWORD},
        headers=bearer(refreshed.json()),
    )
    assert changed.status_code == 200, changed.text
    credential = await credential_row(rw_engine, account.user.id)
    assert credential.must_change_password is False
    assert credential.temp_password_expires_at is None
    # A permanent password: the new session has the full lifetime (12 h by default).
    session_end = parse_utc(changed.json()["session_expires_at"])
    assert session_end - datetime.now(UTC) > timedelta(hours=11)
    entry = next(
        r for r in await entries(rw_engine, account.user.id) if r.action == "password_change"
    )
    assert entry.diff["temp_password_expires_at"]["after"] is None


async def test_reset_issues_a_new_deadline_visible_to_the_admin(
    db_urls: DbUrls, rw_engine: AsyncEngine
) -> None:
    application = create_app(local_settings(db_urls, temp_password_ttl_hours=24))
    try:
        async with client(application) as api:
            admin = await make_account(rw_engine, admin=True)
            admin_tokens = await tokens(api, admin)
            created = await api.post(
                "/api/v1/users",
                json={"email": f"ttl.{uuid4().hex[:8]}@example.com", "display_name": "Nowy TTL"},
                headers=bearer(admin_tokens),
            )
            assert created.status_code == 201, created.text
            user = created.json()["user"]
            user_id = UUID(user["id"])
            first_deadline = parse_utc(user["temp_password_expires_at"])
            row = await credential_row(rw_engine, user_id)
            assert first_deadline == row.temp_password_expires_at
            assert first_deadline - row.password_changed_at == timedelta(hours=24)
            create_entry = next(
                r for r in await entries(rw_engine, user_id) if r.action == "create"
            )
            assert create_entry.diff["temp_password_expires_at"]["after"]

            await expire_temporary_password(rw_engine, user_id)
            assert_problem(
                await login(api, user["email"], created.json()["temporary_password"]),
                401,
                "auth.temporary_password_expired",
            )
            listed = await api.get(
                "/api/v1/users", params={"q": user["email"]}, headers=bearer(admin_tokens)
            )
            [item] = listed.json()["items"]
            assert item["must_change_password"] is True
            assert parse_utc(item["temp_password_expires_at"]) < datetime.now(UTC)

            reset = await api.post(
                f"/api/v1/users/{user_id}/reset-password", headers=bearer(admin_tokens)
            )
            assert reset.status_code == 200, reset.text
            renewed = parse_utc(reset.json()["user"]["temp_password_expires_at"])
            assert renewed - datetime.now(UTC) > timedelta(hours=23)
            detail = await api.get(f"/api/v1/users/{user_id}", headers=bearer(admin_tokens))
            assert parse_utc(detail.json()["temp_password_expires_at"]) == renewed
            fresh = await login(api, user["email"], reset.json()["temporary_password"])
            assert fresh.status_code == 200, fresh.text
            reset_entry = next(
                r for r in await entries(rw_engine, user_id) if r.action == "password_reset"
            )
            assert reset_entry.diff["temp_password_expires_at"]["after"]
    finally:
        await application.state.db.dispose()


async def test_permanent_password_has_no_deadline(api: AsyncClient, rw_engine: AsyncEngine) -> None:
    account = await make_account(rw_engine)
    assert (await credential_row(rw_engine, account.user.id)).temp_password_expires_at is None
    admin = await make_account(rw_engine, admin=True)
    detail = await api.get(
        f"/api/v1/users/{account.user.id}", headers=bearer(await tokens(api, admin))
    )
    assert detail.json()["temp_password_expires_at"] is None


async def test_database_keeps_the_deadline_consistent(rw_engine: AsyncEngine) -> None:
    from sqlalchemy.exc import DBAPIError

    account = await make_account(rw_engine, must_change=True)
    with pytest.raises(DBAPIError, match="temp_password"):
        async with scoped(rw_engine) as session:
            await session.execute(
                text(
                    "UPDATE user_credentials SET temp_password_expires_at = NULL WHERE user_id = :u"
                ),
                {"u": account.user.id},
            )


# --------------------------------------------------------------------------- admin


async def test_admin_creates_account_with_one_time_temporary_password(
    api: AsyncClient, rw_engine: AsyncEngine
) -> None:
    admin = await make_account(rw_engine, admin=True)
    admin_tokens = await tokens(api, admin)
    email = f"Nowy.{uuid4().hex[:8]}@Example.com"
    created = await api.post(
        "/api/v1/users",
        json={"email": email, "display_name": "Nowy Pracownik"},
        headers=bearer(admin_tokens),
    )
    assert created.status_code == 201, created.text
    assert created.headers["cache-control"] == "no-store"
    body = created.json()
    temporary = body["temporary_password"]
    user = body["user"]
    assert user["has_password"] is True
    assert user["must_change_password"] is True
    assert user["external_id"].startswith("local:")
    assert "password_hash" not in json.dumps(body)

    detail = await api.get(f"/api/v1/users/{user['id']}", headers=bearer(admin_tokens))
    assert temporary not in detail.text
    assert "argon2" not in detail.text

    duplicate = await api.post(
        "/api/v1/users",
        json={"email": email.lower(), "display_name": "Duplikat"},
        headers=bearer(admin_tokens),
    )
    assert_problem(duplicate, 409, "user.email_taken")

    first = await login(api, email, temporary)
    assert first.status_code == 200
    assert first.json()["must_change_password"] is True

    rows = await entries(rw_engine, UUID(user["id"]))
    create = next(r for r in rows if r.action == "create")
    assert create.actor_id == admin.user.id
    assert create.context["temporary_password_issued"] is True
    assert create.diff["must_change_password"]["after"] is True
    assert_no_secrets(rows, [temporary])


async def test_admin_reset_unlocks_and_ends_every_session(
    api: AsyncClient, rw_engine: AsyncEngine
) -> None:
    admin = await make_account(rw_engine, admin=True)
    account = await make_account(rw_engine)
    admin_tokens = await tokens(api, admin)
    user_tokens = await tokens(api, account)
    for _ in range(5):
        await login(api, account.email, "Zle-Haslo-123456")
    assert (await credential_row(rw_engine, account.user.id)).locked_until is not None

    reset = await api.post(
        f"/api/v1/users/{account.user.id}/reset-password", headers=bearer(admin_tokens)
    )
    assert reset.status_code == 200, reset.text
    temporary = reset.json()["temporary_password"]
    assert reset.json()["user"]["locked_until"] is None
    assert_problem(await api.get(ME, headers=bearer(user_tokens)), 401, "auth.session_expired")
    assert_problem(
        await api.post(
            "/api/v1/auth/refresh", json={"refresh_token": user_tokens["refresh_token"]}
        ),
        401,
        "auth.invalid_refresh_token",
    )
    assert_problem(
        await login(api, account.email, account.password), 401, "auth.invalid_credentials"
    )
    fresh = await login(api, account.email, temporary)
    assert fresh.status_code == 200
    assert fresh.json()["must_change_password"] is True

    rows = await entries(rw_engine, account.user.id)
    entry = next(r for r in rows if r.action == "password_reset")
    assert entry.actor_id == admin.user.id
    assert entry.context["sessions_revoked"]
    assert entry.diff["must_change_password"] == {"before": False, "after": True}
    assert_no_secrets(rows, [temporary, account.password])

    # Own password: through POST /auth/password only.
    own = await api.post(
        f"/api/v1/users/{admin.user.id}/reset-password", headers=bearer(admin_tokens)
    )
    assert_problem(own, 409, "user.self_password_reset")
    missing = await api.post(
        f"/api/v1/users/{uuid4()}/reset-password", headers=bearer(admin_tokens)
    )
    assert_problem(missing, 404, "user.not_found")


async def test_deactivation_ends_sessions_and_blocks_login(
    api: AsyncClient, rw_engine: AsyncEngine
) -> None:
    admin = await make_account(rw_engine, admin=True)
    account = await make_account(rw_engine)
    admin_tokens = await tokens(api, admin)
    user_tokens = await tokens(api, account)
    response = await api.patch(
        f"/api/v1/users/{account.user.id}",
        json={"is_active": False, "display_name": "Były Pracownik"},
        headers=bearer(admin_tokens),
    )
    assert response.status_code == 200, response.text
    assert response.json()["is_active"] is False
    assert_problem(await api.get(ME, headers=bearer(user_tokens)), 403, "auth.user_inactive")
    assert_problem(
        await api.post(
            "/api/v1/auth/refresh", json={"refresh_token": user_tokens["refresh_token"]}
        ),
        401,
        "auth.invalid_refresh_token",
    )
    assert_problem(
        await login(api, account.email, account.password), 401, "auth.invalid_credentials"
    )
    rows = await entries(rw_engine, account.user.id)
    entry = next(r for r in rows if r.action == "deactivate")
    assert entry.diff["is_active"] == {"before": True, "after": False}
    assert entry.diff["display_name"]["after"] == "Były Pracownik"
    assert entry.context["sessions_revoked"]

    # Reactivation is an ordinary update (sessions stay ended).
    again = await api.patch(
        f"/api/v1/users/{account.user.id}", json={"is_active": True}, headers=bearer(admin_tokens)
    )
    assert again.status_code == 200
    assert (await login(api, account.email, account.password)).status_code == 200
    # No change, no entry.
    before = len(await entries(rw_engine, account.user.id))
    same = await api.patch(
        f"/api/v1/users/{account.user.id}", json={"is_active": True}, headers=bearer(admin_tokens)
    )
    assert same.status_code == 200
    assert len(await entries(rw_engine, account.user.id)) == before


async def test_admin_cannot_remove_themself_or_the_last_admin(
    api: AsyncClient, rw_engine: AsyncEngine, owner_engine: AsyncEngine
) -> None:
    admin = await make_account(rw_engine, admin=True)
    admin_tokens = await tokens(api, admin)
    for body in ({"is_active": False}, {"is_app_admin": False}):
        response = await api.patch(
            f"/api/v1/users/{admin.user.id}", json=body, headers=bearer(admin_tokens)
        )
        assert_problem(response, 409, "user.cannot_modify_self")

    other = await make_account(rw_engine, admin=True)
    # Only these two admins stay active: the other admins of the shared test database
    # are demoted directly (as the owner) for this test and restored afterwards.
    async with owner_engine.begin() as conn:
        demoted = (
            (
                await conn.execute(
                    text(
                        "UPDATE users SET is_app_admin = false WHERE is_app_admin AND is_active "
                        "AND id NOT IN (:a, :b) RETURNING id"
                    ),
                    {"a": admin.user.id, "b": other.user.id},
                )
            )
            .scalars()
            .all()
        )
    try:
        demote = await api.patch(
            f"/api/v1/users/{other.user.id}",
            json={"is_app_admin": False},
            headers=bearer(admin_tokens),
        )
        assert demote.status_code == 200, demote.text
        # "admin" is the last active app admin now: nobody may deactivate or demote it.
        for change in ({"is_active": False}, {"is_app_admin": False}):
            async with scoped(rw_engine) as session:
                with pytest.raises(ProblemError) as info:
                    await users_service.update_user(
                        session, actor=SYSTEM, user_id=admin.user.id, **change
                    )
            assert info.value.code == "user.last_admin"
        # A non-admin can still be deactivated.
        async with scoped(rw_engine) as session:
            await users_service.update_user(
                session, actor=SYSTEM, user_id=other.user.id, is_active=False
            )
    finally:
        async with owner_engine.begin() as conn:
            await conn.execute(
                text("UPDATE users SET is_app_admin = true WHERE id = ANY(:ids)"),
                {"ids": list(demoted)},
            )


async def test_user_management_requires_the_admin(api: AsyncClient, rw_engine: AsyncEngine) -> None:
    account = await make_account(rw_engine)
    body = await tokens(api, account)
    for method, url, payload in (
        ("POST", "/api/v1/users", {"email": "x@example.com", "display_name": "X"}),
        ("POST", f"/api/v1/users/{account.user.id}/reset-password", None),
        ("PATCH", f"/api/v1/users/{account.user.id}", {"display_name": "Y"}),
    ):
        response = await api.request(method, url, json=payload, headers=bearer(body))
        assert_problem(response, 403, "auth.forbidden")


async def test_create_user_validation(api: AsyncClient, rw_engine: AsyncEngine) -> None:
    admin = await make_account(rw_engine, admin=True)
    body = await tokens(api, admin)
    for payload in (
        {"email": "bez-malpy", "display_name": "X"},
        {"email": "a b@example.com", "display_name": "X"},
        {"email": "a@example.com", "display_name": ""},
        {"email": "a@example.com", "display_name": "X", "password": "narzucone-haslo"},
    ):
        response = await api.post("/api/v1/users", json=payload, headers=bearer(body))
        assert response.status_code == 422, payload


async def test_concurrent_duplicate_email_is_409_not_500(
    api: AsyncClient, rw_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The race of two POST /users with one e-mail: the second passes the existence
    check before the first commits and hits ``uq_users_email_lower`` at the INSERT."""
    admin = await make_account(rw_engine, admin=True)
    admin_tokens = await tokens(api, admin)
    existing = await make_account(rw_engine)
    before = await entries(rw_engine, existing.user.id)

    async def check_passes(session: Any, email: str) -> None:
        return None  # the competing account is inserted "after" the check

    monkeypatch.setattr(users_service, "_ensure_email_free", check_passes)
    response = await api.post(
        "/api/v1/users",
        json={"email": existing.email.upper(), "display_name": "Wyścig"},
        headers=bearer(admin_tokens),
    )
    assert_problem(response, 409, "user.email_taken")
    assert await entries(rw_engine, existing.user.id) == before  # the account is untouched
    assert (await verify(rw_engine, None)).ok


async def demote_other_admins(owner_engine: AsyncEngine, keep: list[UUID]) -> list[UUID]:
    """Demote (as the owner) every active admin of the shared test database but ``keep``;
    returns the demoted ids for :func:`restore_admins`."""
    async with owner_engine.begin() as conn:
        rows = await conn.execute(
            text(
                "UPDATE users SET is_app_admin = false WHERE is_app_admin AND is_active "
                "AND NOT (id = ANY(:keep)) RETURNING id"
            ),
            {"keep": keep},
        )
        return list(rows.scalars().all())


async def restore_admins(owner_engine: AsyncEngine, ids: list[UUID]) -> None:
    async with owner_engine.begin() as conn:
        await conn.execute(
            text("UPDATE users SET is_app_admin = true WHERE id = ANY(:ids)"), {"ids": ids}
        )


async def test_last_admin_counts_only_admins_who_can_sign_in(
    rw_engine: AsyncEngine, owner_engine: AsyncEngine
) -> None:
    """AUTH_MODE=local: an active admin WITHOUT a password cannot sign in, so it does not
    keep the application administrable (ADR 0018); the dev mode counts every admin."""
    admin = await make_account(rw_engine, admin=True)
    async with scoped(rw_engine) as session:
        passwordless = await users_service.create_user(
            session,
            actor=SYSTEM,
            external_id=f"dev-nopw-{uuid4().hex[:8]}",
            email=f"nopw-admin-{uuid4().hex[:8]}@example.com",
            display_name="Admin Bez Hasła",
            is_app_admin=True,
        )
    demoted = await demote_other_admins(owner_engine, [admin.user.id, passwordless.id])
    try:
        for change in ({"is_active": False}, {"is_app_admin": False}):
            async with scoped(rw_engine) as session:
                with pytest.raises(ProblemError) as info:
                    await users_service.update_user(
                        session,
                        actor=SYSTEM,
                        user_id=admin.user.id,
                        admins_need_password=True,
                        **change,
                    )
            assert info.value.code == "user.last_admin"
            assert info.value.status == 409
        # Dev mode (default): the passwordless admin counts - unchanged behaviour.
        async with scoped(rw_engine) as session:
            user = await users_service.update_user(
                session, actor=SYSTEM, user_id=admin.user.id, is_app_admin=False
            )
            assert user.is_app_admin is False
    finally:
        await restore_admins(owner_engine, demoted)
        async with owner_engine.begin() as conn:
            await conn.execute(
                text("UPDATE users SET is_app_admin = false WHERE id = :p"),
                {"p": passwordless.id},
            )


async def test_patch_user_in_local_mode_counts_only_admins_with_password(
    api: AsyncClient, rw_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    admin = await make_account(rw_engine, admin=True)
    target = await make_account(rw_engine)
    admin_tokens = await tokens(api, admin)
    seen: dict[str, Any] = {}
    original = users_service.update_user

    async def spy(session: Any, **kwargs: Any) -> User:
        seen.update(kwargs)
        return await original(session, **kwargs)

    monkeypatch.setattr(users_service, "update_user", spy)
    response = await api.patch(
        f"/api/v1/users/{target.user.id}",
        json={"display_name": "Nowa Nazwa"},
        headers=bearer(admin_tokens),
    )
    assert response.status_code == 200, response.text
    assert seen["admins_need_password"] is True


async def test_routes_without_a_permission_declaration_log_the_user(
    api: AsyncClient, rw_engine: AsyncEngine
) -> None:
    """/me and /auth/* declare no action (app.permissions binds the principal only
    there): the authentication itself binds user_id to the JSON log lines (ADR 0019 §4)."""
    account = await make_account(rw_engine)
    body = await tokens(api, account)
    lines: list[dict[str, Any]] = []

    class Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            lines.append(json.loads(logs.JsonFormatter().format(record)))

    handler = Capture()
    logger = logging.getLogger(logs.ACCESS_LOGGER)
    previous = logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    try:
        assert (await api.get(ME, headers=bearer(body))).status_code == 200
        assert (await api.post("/api/v1/auth/logout", headers=bearer(body))).status_code == 204
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous)
    by_path = {line["path"]: line for line in lines}
    assert by_path[ME]["user_id"] == str(account.user.id)
    assert by_path["/api/v1/auth/logout"]["user_id"] == str(account.user.id)


# --------------------------------------------------------------------------- audit


def assert_no_secrets(rows: list[Any], plaintexts: list[str]) -> None:
    for row in rows:
        dumped = json.dumps({"diff": row.diff, "context": row.context}, ensure_ascii=False)
        assert "$argon2" not in dumped
        for secret in plaintexts:
            assert secret not in dumped


async def test_every_local_auth_endpoint_writes_audit_without_secrets(
    api: AsyncClient, rw_engine: AsyncEngine
) -> None:
    account = await make_account(rw_engine)

    async def written(response: Response) -> list[Any]:
        async with scoped(rw_engine, [], global_read=True) as session:
            return list(
                (
                    await session.execute(
                        text("SELECT * FROM audit_log WHERE request_id = :r"),
                        {"r": response.headers["X-Request-ID"]},
                    )
                ).all()
            )

    logged_in = await login(api, account.email, account.password)
    body = logged_in.json()
    refreshed = await api.post(
        "/api/v1/auth/refresh", json={"refresh_token": body["refresh_token"]}
    )
    new = refreshed.json()
    changed = await api.post(
        "/api/v1/auth/password",
        json={"current_password": account.password, "new_password": OTHER_PASSWORD},
        headers=bearer(new),
    )
    final = changed.json()
    logged_out = await api.post("/api/v1/auth/logout", headers=bearer(final))
    plaintexts = [
        account.password,
        OTHER_PASSWORD,
        body["refresh_token"],
        body["access_token"],
        new["refresh_token"],
        final["refresh_token"],
    ]
    expected = {
        "login": logged_in,
        "token_refresh": refreshed,
        "password_change": changed,
        "logout": logged_out,
    }
    for action, response in expected.items():
        rows = await written(response)
        assert action in actions(rows), (action, actions(rows))
        assert_no_secrets(rows, plaintexts)
    assert (await verify(rw_engine, None)).ok


async def test_password_hash_never_reaches_any_user_endpoint(
    api: AsyncClient, rw_engine: AsyncEngine
) -> None:
    admin = await make_account(rw_engine, admin=True)
    body = await tokens(api, admin)
    for url in ("/api/v1/users?limit=200", f"/api/v1/users/{admin.user.id}", ME):
        response = await api.get(url, headers=bearer(body))
        assert response.status_code == 200
        assert "argon2" not in response.text
        assert "password_hash" not in response.text


async def test_audit_record_refuses_secret_keys(rw_engine: AsyncEngine) -> None:
    from app.domain.audit import AuditAction, EntityType
    from app.services import audit

    for kwargs in (
        {"context": {"password": "x"}},
        {"context": {"nested": [{"refresh_token": "x"}]}},
        {"diff": {"password_hash": {"before": None, "after": "x"}}},
    ):
        async with scoped(rw_engine) as session:
            with pytest.raises(audit.AuditError, match="secrets"):
                await audit.record(
                    session,
                    company_id=None,
                    actor=SYSTEM,
                    entity_type=EntityType.USER,
                    entity_id=None,
                    action=AuditAction.UPDATE,
                    **kwargs,  # type: ignore[arg-type]
                )


# --------------------------------------------------------------------------- database guards


async def test_revoked_session_cannot_be_revived(rw_engine: AsyncEngine, api: AsyncClient) -> None:
    from sqlalchemy.exc import DBAPIError

    account = await make_account(rw_engine)
    body = await tokens(api, account)
    await api.post("/api/v1/auth/logout", headers=bearer(body))
    with pytest.raises(DBAPIError, match="revoked session"):
        async with scoped(rw_engine) as session:
            await session.execute(
                text("UPDATE auth_sessions SET revoked_at = NULL WHERE user_id = :u"),
                {"u": account.user.id},
            )
    with pytest.raises(DBAPIError, match="permission denied"):
        async with scoped(rw_engine) as session:
            await session.execute(
                text("DELETE FROM user_credentials WHERE user_id = :u"), {"u": account.user.id}
            )


async def test_maintenance_purges_long_expired_sessions(
    rw_engine: AsyncEngine, owner_engine: AsyncEngine
) -> None:
    from app.services import auth_events

    account = await make_account(rw_engine)
    async with owner_engine.begin() as conn:
        sid = (
            await conn.execute(
                text(
                    "INSERT INTO auth_sessions (user_id, expires_at) "
                    "VALUES (:u, now() - interval '3 days') RETURNING id"
                ),
                {"u": account.user.id},
            )
        ).scalar_one()
        await conn.execute(
            text(
                "INSERT INTO auth_refresh_tokens (session_id, token_hash, expires_at) "
                "VALUES (:s, :h, now() - interval '3 days')"
            ),
            {"s": sid, "h": refresh_token_hash(uuid4().hex)},
        )
    async with scoped(rw_engine) as session:
        await auth_events.purge_expired(session)
    async with scoped(rw_engine) as session:
        remaining = (
            await session.execute(
                text(
                    "SELECT (SELECT count(*) FROM auth_sessions WHERE id = :s) + "
                    "(SELECT count(*) FROM auth_refresh_tokens WHERE session_id = :s)"
                ),
                {"s": sid},
            )
        ).scalar_one()
    assert remaining == 0


# --------------------------------------------------------------------------- CLI create-admin


def _cli_env(monkeypatch: pytest.MonkeyPatch, db_urls: DbUrls, mode: str = "local") -> None:
    from app.config import get_settings

    monkeypatch.setenv("APP_ENV", "prod" if mode == "local" else "dev")
    monkeypatch.setenv("AUTH_MODE", mode)
    monkeypatch.setenv("AUTH_JWT_SECRET", LOCAL_SECRET)
    monkeypatch.setenv("DEV_AUTH_SECRET", "test-dev-auth-secret-0123456789abcdef")
    monkeypatch.setenv("DATABASE_URL", db_urls.rw)
    get_settings.cache_clear()


def _stdin(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    import io
    import sys

    monkeypatch.setattr(sys, "stdin", io.StringIO(value))


async def _user_by_email(engine: AsyncEngine, email: str) -> User | None:
    from app.services.local_auth import get_user_by_email

    async with scoped(engine) as session:
        return await get_user_by_email(session, email)


def test_cli_create_admin_with_password_from_stdin(
    monkeypatch: pytest.MonkeyPatch,
    db_urls: DbUrls,
    rw_engine: AsyncEngine,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import asyncio

    from app.cli import main
    from app.config import get_settings

    email = f"admin-{uuid4().hex[:8]}@example.com"
    _cli_env(monkeypatch, db_urls)
    _stdin(monkeypatch, PASSWORD + "\n")
    try:
        assert main(["create-admin", "--email", email, "--name", "Pierwszy Admin"]) == 0
    finally:
        get_settings.cache_clear()
    out = capsys.readouterr().out
    assert PASSWORD not in out
    assert "Hasło tymczasowe" not in out
    user = asyncio.run(_user_by_email(rw_engine, email))
    assert user is not None
    assert user.is_app_admin
    row = asyncio.run(credential_row(rw_engine, user.id))
    assert row.must_change_password is False
    rows = asyncio.run(entries(rw_engine, user.id))
    create = next(r for r in rows if r.action == "create")
    assert create.actor_id is None  # system
    assert create.context["source"] == "cli"
    assert create.context["command"] == "create-admin"
    assert_no_secrets(rows, [PASSWORD])


def test_cli_create_admin_generates_a_temporary_password(
    monkeypatch: pytest.MonkeyPatch,
    db_urls: DbUrls,
    rw_engine: AsyncEngine,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import asyncio

    from app.cli import main
    from app.config import get_settings

    email = f"admin-{uuid4().hex[:8]}@example.com"
    _cli_env(monkeypatch, db_urls)
    try:
        code = main(["create-admin", "--email", email, "--name", "Admin", "--generate-password"])
    finally:
        get_settings.cache_clear()
    assert code == 0
    out = capsys.readouterr().out
    temporary = out.strip().rsplit(" ", 1)[-1]
    user = asyncio.run(_user_by_email(rw_engine, email))
    assert user is not None
    row = asyncio.run(credential_row(rw_engine, user.id))
    assert row.must_change_password is True
    assert passwords_ok(row.password_hash, temporary)
    # Shown on a terminal like any temporary password: the same deadline (7 days).
    assert row.temp_password_expires_at - row.password_changed_at == timedelta(hours=168)


def passwords_ok(encoded: str, password: str) -> bool:
    from app.auth.passwords import verify_password

    return verify_password(encoded, password)


@pytest.mark.parametrize(
    ("argv", "stdin", "mode", "message"),
    [
        (["--email", "zly-adres", "--name", "X"], PASSWORD + "\n", "local", "e-mail"),
        (["--email", "a@example.com", "--name", "X"], "krotkie\n", "local", "co najmniej"),
        (["--email", "a@example.com", "--name", "X"], PASSWORD + "\n", "dev", "AUTH_MODE=local"),
    ],
)
def test_cli_create_admin_refusals(
    monkeypatch: pytest.MonkeyPatch,
    db_urls: DbUrls,
    capsys: pytest.CaptureFixture[str],
    argv: list[str],
    stdin: str,
    mode: str,
    message: str,
) -> None:
    from app.cli import main
    from app.config import get_settings

    _cli_env(monkeypatch, db_urls, mode)
    _stdin(monkeypatch, stdin)
    try:
        assert main(["create-admin", *argv]) == 1
    finally:
        get_settings.cache_clear()
    assert message in capsys.readouterr().err


def test_cli_create_admin_duplicate_email(
    monkeypatch: pytest.MonkeyPatch,
    db_urls: DbUrls,
    rw_engine: AsyncEngine,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import asyncio

    from app.cli import main
    from app.config import get_settings

    account = asyncio.run(make_account(rw_engine))
    _cli_env(monkeypatch, db_urls)
    _stdin(monkeypatch, OTHER_PASSWORD + "\n")
    try:
        assert main(["create-admin", "--email", account.email.lower(), "--name", "X"]) == 1
    finally:
        get_settings.cache_clear()
    assert "user.email_taken" in capsys.readouterr().err
