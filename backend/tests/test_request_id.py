"""Request ID: accepted from ``X-Request-ID`` only when it is a UUID, otherwise generated.

It is the foundation of ``audit_log.request_id`` (CLAUDE.md 6.1).
"""

from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.db import check_database
from app.errors import ProblemError
from app.request_context import REQUEST_ID_HEADER, get_request_id, parse_request_id

SAMPLE = "0f8fad5b-d9cb-469f-a165-70867728950e"


@pytest.fixture(autouse=True)
def _db_ok(app: FastAPI) -> None:
    async def _ok() -> bool:
        return True

    app.dependency_overrides[check_database] = _ok


def _install_echo(app: FastAPI) -> None:
    @app.get("/api/v1/_test/request-id")
    async def _echo() -> dict[str, str | None]:
        rid = get_request_id()
        return {"request_id": str(rid) if rid else None}


@pytest.mark.parametrize(
    "raw",
    [
        SAMPLE,
        # nginx $request_id: 32 hex characters
        "0f8fad5bd9cb469fa16570867728950e",
        SAMPLE.upper(),
    ],
)
def test_parse_accepts_uuid_forms(raw: str) -> None:
    assert parse_request_id(raw) == UUID(SAMPLE)


@pytest.mark.parametrize(
    "raw",
    [None, "", "abc", "x" * 32, "1; DROP TABLE audit_log", "0f8fad5b" * 20, "1234"],
)
def test_parse_rejects_non_uuid(raw: str | None) -> None:
    assert parse_request_id(raw) is None


async def test_generates_uuid4_when_header_missing(app: FastAPI, client: AsyncClient) -> None:
    _install_echo(app)
    r = await client.get("/api/v1/_test/request-id")
    assert r.status_code == 200
    rid = UUID(r.headers[REQUEST_ID_HEADER])
    assert rid.version == 4
    assert r.json()["request_id"] == str(rid)


async def test_accepts_valid_header(app: FastAPI, client: AsyncClient) -> None:
    _install_echo(app)
    r = await client.get(
        "/api/v1/_test/request-id",
        headers={REQUEST_ID_HEADER: "0f8fad5bd9cb469fa16570867728950e"},
    )
    assert r.headers[REQUEST_ID_HEADER] == SAMPLE
    assert r.json()["request_id"] == SAMPLE


async def test_replaces_invalid_header(app: FastAPI, client: AsyncClient) -> None:
    _install_echo(app)
    r = await client.get("/api/v1/_test/request-id", headers={REQUEST_ID_HEADER: "evil-value"})
    rid = UUID(r.headers[REQUEST_ID_HEADER])
    assert rid.version == 4
    assert r.json()["request_id"] == str(rid)


async def test_each_request_gets_its_own_id(client: AsyncClient) -> None:
    a = await client.get("/api/v1/health")
    b = await client.get("/api/v1/health")
    assert a.headers[REQUEST_ID_HEADER] != b.headers[REQUEST_ID_HEADER]


async def test_not_set_outside_request() -> None:
    assert get_request_id() is None


async def test_problem_json_contains_request_id(client: AsyncClient) -> None:
    r = await client.get("/api/v1/does-not-exist", headers={REQUEST_ID_HEADER: SAMPLE})
    assert r.status_code == 404
    assert r.headers[REQUEST_ID_HEADER] == SAMPLE
    assert r.json()["request_id"] == SAMPLE


async def test_problem_error_from_endpoint_contains_request_id(
    app: FastAPI, client: AsyncClient
) -> None:
    @app.get("/api/v1/_test/conflict")
    async def _conflict() -> None:
        raise ProblemError(status=409, code="x.conflict", detail="Konflikt.")

    r = await client.get("/api/v1/_test/conflict")
    assert r.json()["request_id"] == r.headers[REQUEST_ID_HEADER]


async def test_validation_problem_contains_request_id(app: FastAPI, client: AsyncClient) -> None:
    @app.get("/api/v1/_test/validate")
    async def _validate(limit: int) -> dict[str, int]:
        return {"limit": limit}

    r = await client.get("/api/v1/_test/validate", params={"limit": "x"})
    assert r.status_code == 422
    assert r.json()["request_id"] == r.headers[REQUEST_ID_HEADER]


async def test_unhandled_500_contains_request_id(app: FastAPI) -> None:
    @app.get("/api/v1/_test/boom")
    async def _boom() -> None:
        raise RuntimeError("boom")

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as c:
        r = await c.get("/api/v1/_test/boom", headers={REQUEST_ID_HEADER: SAMPLE})
    assert r.status_code == 500
    assert r.headers["content-type"].startswith("application/problem+json")
    assert r.headers[REQUEST_ID_HEADER] == SAMPLE
    assert r.json()["request_id"] == SAMPLE


async def test_extra_cannot_override_request_id() -> None:
    err = ProblemError(status=400, code="x.y", detail="d", extra={"request_id": "forged"})
    assert "request_id" not in err.to_body()


async def test_client_ip_and_user_agent_available_to_services(app: FastAPI) -> None:
    from app.request_context import get_client_info

    @app.get("/api/v1/_test/client")
    async def _client() -> dict[str, str | None]:
        info = get_client_info()
        return {"ip": info.ip, "user_agent": info.user_agent}

    transport = ASGITransport(app=app, client=("203.0.113.7", 5555))
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/api/v1/_test/client", headers={"User-Agent": "Mozilla/5.0 (test)"})
        bad = AsyncClient(
            transport=ASGITransport(app=app, client=("not-an-ip", 1)), base_url="http://test"
        )
        async with bad:
            r_bad = await bad.get("/api/v1/_test/client")
    assert r.json() == {"ip": "203.0.113.7", "user_agent": "Mozilla/5.0 (test)"}
    assert r_bad.json()["ip"] is None
    assert get_client_info().ip is None  # outside a request
