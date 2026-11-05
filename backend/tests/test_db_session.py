"""Per-request transaction: commit happens BEFORE the response is sent.

If the commit fails (e.g. a deferred constraint), the client must get 5xx problem+json,
never 2xx — otherwise it would believe the data (and its audit entry) were saved.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Any

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.db import SessionDep
from app.errors import ProblemError
from app.main import create_app
from app.request_context import REQUEST_ID_HEADER
from tests.conftest import DbUrls, make_settings

pytestmark = pytest.mark.db


@pytest.fixture
async def tables(db_urls: DbUrls) -> AsyncIterator[tuple[str, str]]:
    # Created by app_owner (like migrations); the app under test runs as app_rw and gets
    # DML through the default privileges from deploy/postgres/init/roles.psql.
    suffix = uuid.uuid4().hex[:8]
    parent, child = f"t_parent_{suffix}", f"t_child_{suffix}"
    engine = create_async_engine(db_urls.owner)
    async with engine.begin() as conn:
        await conn.execute(text(f"CREATE TABLE {parent} (id int PRIMARY KEY)"))
        await conn.execute(
            text(
                f"CREATE TABLE {child} (id int PRIMARY KEY, parent_id int NOT NULL "
                f"REFERENCES {parent}(id) DEFERRABLE INITIALLY DEFERRED)"
            )
        )
        await conn.execute(text(f"INSERT INTO {parent} VALUES (1)"))  # noqa: S608
    yield parent, child
    async with engine.begin() as conn:
        await conn.execute(text(f"DROP TABLE {child}"))
        await conn.execute(text(f"DROP TABLE {parent}"))
    await engine.dispose()


@pytest.fixture
def db_app(db_urls: DbUrls, tables: tuple[str, str]) -> FastAPI:
    _, child = tables
    app = create_app(make_settings(database_url=db_urls.rw))

    @app.post("/api/v1/_test/child/{child_id}/{parent_id}")
    async def _insert(child_id: int, parent_id: int, session: SessionDep) -> dict[str, int]:
        await session.execute(
            text(f"INSERT INTO {child} VALUES (:c, :p)"),  # noqa: S608 - test-only table
            {"c": child_id, "p": parent_id},
        )
        return {"id": child_id}

    @app.post("/api/v1/_test/child-then-fail/{child_id}")
    async def _insert_then_fail(child_id: int, session: SessionDep) -> None:
        await session.execute(
            text(f"INSERT INTO {child} VALUES (:c, 1)"),  # noqa: S608 - test-only table
            {"c": child_id},
        )
        raise ProblemError(status=409, code="test.conflict", detail="Konflikt testowy.")

    return app


async def _count(db_urls: DbUrls, child: str, child_id: int) -> int:
    engine = create_async_engine(db_urls.rw)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text(f"SELECT count(*) FROM {child} WHERE id = :c"),  # noqa: S608
                {"c": child_id},
            )
            return int(result.scalar_one())
    finally:
        await engine.dispose()


async def _post(app: FastAPI, path: str) -> tuple[int, dict[str, Any], dict[str, str]]:
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post(path)
    await app.state.db.dispose()
    return r.status_code, r.json(), dict(r.headers)


async def test_successful_request_is_committed(
    db_app: FastAPI, db_urls: DbUrls, tables: tuple[str, str]
) -> None:
    status, body, _ = await _post(db_app, "/api/v1/_test/child/10/1")
    assert status == 200
    assert body == {"id": 10}
    assert await _count(db_urls, tables[1], 10) == 1


async def test_commit_failure_returns_5xx_problem_json(
    db_app: FastAPI, db_urls: DbUrls, tables: tuple[str, str]
) -> None:
    # Parent 999 does not exist; the FK is deferred, so it fails only at COMMIT.
    status, body, headers = await _post(db_app, "/api/v1/_test/child/11/999")
    assert status == 500
    assert headers["content-type"].startswith("application/problem+json")
    assert body["code"] == "server.internal_error"
    assert body["request_id"] == headers[REQUEST_ID_HEADER.lower()]
    assert await _count(db_urls, tables[1], 11) == 0


async def test_error_in_endpoint_rolls_back(
    db_app: FastAPI, db_urls: DbUrls, tables: tuple[str, str]
) -> None:
    status, body, _ = await _post(db_app, "/api/v1/_test/child-then-fail/12")
    assert status == 409
    assert body["code"] == "test.conflict"
    assert await _count(db_urls, tables[1], 12) == 0
