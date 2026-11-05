"""RFC 9457 problem+json is the single error format of the API."""

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.errors import ProblemError


async def test_unknown_route_is_problem_json(client: AsyncClient) -> None:
    r = await client.get("/api/v1/does-not-exist")
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/problem+json")
    body = r.json()
    assert body["status"] == 404
    assert body["code"] == "http.not_found"
    assert body["detail"] == "Nie znaleziono zasobu."


async def test_method_not_allowed_is_problem_json(client: AsyncClient) -> None:
    r = await client.delete("/api/v1/health")
    assert r.status_code == 405
    assert r.headers["content-type"].startswith("application/problem+json")
    assert r.json()["code"] == "http.method_not_allowed"


async def test_problem_error_raised_in_endpoint(app: FastAPI, client: AsyncClient) -> None:
    @app.get("/api/v1/_test/conflict")
    async def _conflict() -> None:
        raise ProblemError(
            status=409,
            code="change.version_conflict",
            detail="Zmiana została zmodyfikowana przez innego użytkownika.",
            extra={"current_version": 7},
        )

    r = await client.get("/api/v1/_test/conflict")
    assert r.status_code == 409
    assert r.headers["content-type"].startswith("application/problem+json")
    body = r.json()
    assert body["code"] == "change.version_conflict"
    assert body["type"] == "urn:rejestr:problem:change.version_conflict"
    assert body["detail"] == "Zmiana została zmodyfikowana przez innego użytkownika."
    assert body["current_version"] == 7
    assert body["instance"] == "/api/v1/_test/conflict"


async def test_problem_extra_cannot_override_standard_members() -> None:
    err = ProblemError(status=400, code="x.y", detail="d", extra={"status": 200, "a": 1})
    body = err.to_body(instance="/p")
    assert body["status"] == 400
    assert body["a"] == 1


async def test_validation_error_is_problem_json(app: FastAPI, client: AsyncClient) -> None:
    @app.get("/api/v1/_test/validate")
    async def _validate(limit: int) -> dict[str, int]:
        return {"limit": limit}

    r = await client.get("/api/v1/_test/validate", params={"limit": "abc"})
    assert r.status_code == 422
    assert r.headers["content-type"].startswith("application/problem+json")
    body = r.json()
    assert body["code"] == "request.validation_error"
    assert body["errors"][0]["loc"] == ["query", "limit"]


async def test_unhandled_exception_is_problem_json_without_leaking(app: FastAPI) -> None:
    @app.get("/api/v1/_test/boom")
    async def _boom() -> None:
        raise RuntimeError("secret internals")

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as c:
        r = await c.get("/api/v1/_test/boom")
    assert r.status_code == 500
    assert r.headers["content-type"].startswith("application/problem+json")
    assert "secret" not in r.text
    assert r.json()["code"] == "server.internal_error"


async def test_cors_preflight_allows_configured_origin(client: AsyncClient) -> None:
    r = await client.options(
        "/api/v1/health",
        headers={"Origin": "http://localhost:5000", "Access-Control-Request-Method": "GET"},
    )
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "http://localhost:5000"


async def test_cors_ignores_unknown_origin(app: FastAPI, client: AsyncClient) -> None:
    from app.db import check_database

    async def _ok() -> bool:
        return True

    app.dependency_overrides[check_database] = _ok
    r = await client.get("/api/v1/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in r.headers
