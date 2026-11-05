"""Shared fixtures.

Tests marked ``db`` use a real PostgreSQL 16 started by testcontainers. When Docker
is not reachable those tests are skipped (never silently passed).

The container is bootstrapped exactly like production: ``deploy/postgres/init`` is mounted
as ``/docker-entrypoint-initdb.d`` (roles ``app_owner`` / ``app_rw`` from ``roles.psql``),
then ``alembic upgrade head`` runs as ``app_owner``. Application code under test connects
as ``app_rw`` — the table owner would bypass RLS.
"""

from __future__ import annotations

import os
import secrets
import subprocess
import sys
import tempfile
from collections.abc import AsyncIterator, Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import Settings
from app.main import create_app
from tests.auth_helpers import DEV_SECRET

__all__ = ["DEV_SECRET", "DbUrls", "make_settings", "run_alembic"]

POSTGRES_IMAGE = "postgres:16-alpine"
BACKEND_DIR = Path(__file__).resolve().parents[1]
PG_INIT_DIR = BACKEND_DIR.parent / "deploy" / "postgres" / "init"
TEST_DB_NAME = "rejestr_test"

ClientFactory = Callable[[FastAPI], AsyncClient]

# Attachment storage of the test applications (never the developer's ./storage).
TEST_STORAGE = Path(tempfile.mkdtemp(prefix="rejestr-test-storage-"))


def make_settings(**overrides: Any) -> Settings:
    """Settings for tests, independent of the developer's environment and .env file."""
    values: dict[str, Any] = {
        "app_env": "dev",
        "auth_mode": "dev",
        "database_url": "postgresql+asyncpg://app_rw:test@localhost:5432/rejestr_test",
        "migrations_database_url": (
            "postgresql+asyncpg://app_owner:test@localhost:5432/rejestr_test"
        ),
        "redis_url": "redis://localhost:6379/15",
        "cors_origins": ["http://localhost:5000"],
        "dev_auth_secret": DEV_SECRET,
        "storage_path": TEST_STORAGE,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.fixture
def settings() -> Settings:
    return make_settings()


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
def client_factory() -> ClientFactory:
    def _make(application: FastAPI) -> AsyncClient:
        return AsyncClient(transport=ASGITransport(app=application), base_url="http://test")

    return _make


@pytest.fixture
async def client(app: FastAPI, client_factory: ClientFactory) -> AsyncIterator[AsyncClient]:
    async with client_factory(app) as c:
        yield c


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Tests marked ``pdf`` need WeasyPrint with Pango (Docker image, CI); skipped - never
    silently passed - on a host without it."""
    from app.reports.render import weasyprint_available

    if weasyprint_available():
        return
    if os.environ.get("REQUIRE_WEASYPRINT"):  # CI: the PDF tests must run, never skip
        raise pytest.UsageError("REQUIRE_WEASYPRINT is set, but WeasyPrint cannot be imported")
    skip = pytest.mark.skip(reason="WeasyPrint/Pango niedostępne — pomijam testy z markerem 'pdf'")
    for item in items:
        if "pdf" in item.keywords:
            item.add_marker(skip)


# --------------------------------------------------------------------------- Docker / Postgres


def _docker_available() -> bool:
    try:
        import docker  # transitive dependency of testcontainers

        docker.from_env().ping()
    except Exception:
        return False
    return True


@dataclass(frozen=True)
class DbUrls:
    """asyncpg URLs of the test database, one per role."""

    superuser: str  # bootstrap superuser: test setup/inspection only, never for app code
    owner: str  # app_owner: migrations (and tamper simulation in audit tests)
    rw: str  # app_rw: the application role — default for every application test


def run_alembic(db_url: str, *args: str) -> subprocess.CompletedProcess[str]:
    """Run the real Alembic CLI (same env.py as production) against ``db_url``."""
    return subprocess.run(  # noqa: S603 - fixed argv, test-only
        [sys.executable, "-m", "alembic", "-x", f"db_url={db_url}", *args],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )


@pytest.fixture(scope="session")
def db_urls() -> Iterator[DbUrls]:
    """PostgreSQL 16 with production roles and all migrations applied (session-scoped).

    Use only from tests marked ``@pytest.mark.db``.
    """
    if not _docker_available():
        pytest.skip("Docker niedostępny — pomijam testy z markerem 'db'")
    from testcontainers.community.postgres import PostgresContainer

    owner_pw = secrets.token_urlsafe(18)
    rw_pw = secrets.token_urlsafe(18)
    container = (
        PostgresContainer(
            POSTGRES_IMAGE,
            username="postgres",
            password=secrets.token_urlsafe(18),
            dbname=TEST_DB_NAME,
            driver="asyncpg",
        )
        .with_env("APP_OWNER_PASSWORD", owner_pw)
        .with_env("APP_RW_PASSWORD", rw_pw)
        .with_env("POSTGRES_INITDB_ARGS", "--encoding=UTF8 --locale=C.UTF-8")
        .with_env("TZ", "UTC")
        .with_volume_mapping(str(PG_INIT_DIR), "/docker-entrypoint-initdb.d", "ro")
    )
    with container as pg:
        superuser = pg.get_connection_url()
        host, port = pg.get_container_host_ip(), pg.get_exposed_port(5432)
        base = f"postgresql+asyncpg://{{user}}:{{pw}}@{host}:{port}/{TEST_DB_NAME}"
        urls = DbUrls(
            superuser=superuser,
            owner=base.format(user="app_owner", pw=owner_pw),
            rw=base.format(user="app_rw", pw=rw_pw),
        )
        result = run_alembic(urls.owner, "upgrade", "head")
        if result.returncode != 0:
            pytest.fail(f"alembic upgrade head failed:\n{result.stdout}\n{result.stderr}")
        yield urls


@pytest.fixture
async def rw_engine(db_urls: DbUrls) -> AsyncIterator[AsyncEngine]:
    """Engine connected as ``app_rw`` (NullPool: no connection outlives the test loop)."""
    engine = create_async_engine(db_urls.rw, poolclass=NullPool)
    yield engine
    await engine.dispose()


@pytest.fixture
async def owner_engine(db_urls: DbUrls) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(db_urls.owner, poolclass=NullPool)
    yield engine
    await engine.dispose()


# --------------------------------------------------------------------------- API on the database


@pytest.fixture
async def db_app(db_urls: DbUrls) -> AsyncIterator[FastAPI]:
    """The real application (dev auth) connected as app_rw to the test database."""
    from app.reports.render import weasyprint_available
    from tests.factories import RecordingQueue, stub_pdf

    application = create_app(make_settings(database_url=db_urls.rw))
    # Reports (ADR 0017): background jobs are recorded, not sent to Redis; without Pango
    # (bare Windows host) the permission/isolation tests use a stand-in renderer - the PDF
    # content tests are marked ``pdf`` and skipped there.
    application.state.report_queue = RecordingQueue()
    if not weasyprint_available():
        application.state.pdf_renderer = stub_pdf
    yield application
    await application.state.db.dispose()


@pytest.fixture
async def api(db_app: FastAPI) -> AsyncIterator[AsyncClient]:
    from tests.factories import client_for

    async with client_for(db_app) as c:
        yield c


@pytest.fixture
async def world(rw_engine: AsyncEngine) -> Any:
    from tests.factories import make_world

    return await make_world(rw_engine)
