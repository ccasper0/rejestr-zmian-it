import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from app import __version__
from app.db import check_database
from app.main import create_app
from tests.auth_helpers import LOCAL_SECRET
from tests.conftest import ClientFactory, DbUrls, make_settings


def _override_db(app: FastAPI, ok: bool) -> None:
    async def _fake() -> bool:
        return ok

    app.dependency_overrides[check_database] = _fake


async def test_health_ok(app: FastAPI, client: AsyncClient) -> None:
    _override_db(app, ok=True)
    r = await client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")
    assert r.json() == {"status": "ok", "version": __version__, "db": "ok"}


async def test_health_db_error_returns_problem_json(app: FastAPI, client: AsyncClient) -> None:
    _override_db(app, ok=False)
    r = await client.get("/api/v1/health")
    assert r.status_code == 503
    assert r.headers["content-type"].startswith("application/problem+json")
    body = r.json()
    assert body["status"] == 503
    assert body["code"] == "health.db_unavailable"
    assert body["db"] == "error"
    assert body["version"] == __version__
    assert body["title"]
    assert body["detail"] == "Baza danych jest niedostępna."
    assert body["instance"] == "/api/v1/health"


async def test_health_with_unreachable_db_reports_error(client_factory: ClientFactory) -> None:
    # Nothing listens on port 1: the real check must fail fast instead of hanging or crashing.
    app = create_app(
        make_settings(
            database_url="postgresql+asyncpg://app_rw:x@127.0.0.1:1/none",
            db_health_timeout_seconds=3.0,
        )
    )
    async with client_factory(app) as c:
        r = await c.get("/api/v1/health")
    assert r.status_code == 503
    assert r.json()["db"] == "error"


@pytest.mark.db
async def test_health_against_real_postgres(db_urls: DbUrls, client_factory: ClientFactory) -> None:
    app = create_app(make_settings(database_url=db_urls.rw))
    async with client_factory(app) as c:
        r = await c.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["db"] == "ok"


# --------------------------------------------------------------------------- API docs
# ADR 0019 §9 p. 4 (decision of the owner 2026-11-04): the interactive documentation and
# the OpenAPI schema exist only with APP_ENV=dev.

DOC_PATHS = (
    "/api/v1/docs",
    "/api/v1/redoc",
    "/api/v1/openapi.json",
    "/api/v1/docs/oauth2-redirect",
)


async def test_api_docs_are_served_in_dev(client_factory: ClientFactory) -> None:
    app = create_app(make_settings(app_env="dev"))
    async with client_factory(app) as c:
        docs = await c.get("/api/v1/docs")
        schema = await c.get("/api/v1/openapi.json")
    assert docs.status_code == 200
    assert schema.status_code == 200
    assert schema.json()["info"]["title"]


@pytest.mark.parametrize("path", DOC_PATHS)
async def test_api_docs_are_not_served_outside_dev(
    client_factory: ClientFactory, path: str
) -> None:
    app = create_app(
        make_settings(
            app_env="prod",
            auth_mode="local",
            auth_jwt_secret=LOCAL_SECRET,
            dev_auth_secret=None,
        )
    )
    async with client_factory(app) as c:
        r = await c.get(path)
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/problem+json")
