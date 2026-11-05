"""Application logs: JSON formatter, secret masking, access log (ADR 0019 §4)."""

from __future__ import annotations

import contextlib
import json
import logging
import sys
from collections.abc import Iterator
from typing import Any
from uuid import UUID

import pytest
from fastapi import FastAPI, HTTPException
from httpx import AsyncClient

from app import logs
from app.logs import REDACTED, ConsoleFormatter, JsonFormatter, configure_logging, redact
from app.request_context import REQUEST_ID_HEADER
from tests.conftest import make_settings

JWT = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJzdWIiOiJkZXYtZWRpdG9yIn0.c2lnbmF0dXJlLXZhbHVlLWZvci10ZXN0cw"
)


def record(message: str, *args: Any, **extra: Any) -> logging.LogRecord:
    rec = logging.LogRecord("app.test", logging.INFO, __file__, 1, message, args, None)
    for key, value in extra.items():
        setattr(rec, key, value)
    return rec


def as_json(rec: logging.LogRecord) -> dict[str, Any]:
    line = JsonFormatter().format(rec)
    assert "\n" not in line
    parsed: dict[str, Any] = json.loads(line)
    return parsed


@pytest.fixture
def restore_logging() -> Iterator[None]:
    root = logging.getLogger()
    handlers, level = list(root.handlers), root.level
    access_disabled = logging.getLogger("uvicorn.access").disabled
    yield
    for handler in list(root.handlers):
        if handler not in handlers:
            root.removeHandler(handler)
    root.setLevel(level)
    logging.getLogger("uvicorn.access").disabled = access_disabled


# --------------------------------------------------------------------------- formatter


def test_json_line_has_the_standard_fields() -> None:
    rec = record("zmiana %s zapisana", "CHG-ALFA-2026-0001", status=201)
    rec.created = 1_793_700_000.5  # 2026-11-02T...Z
    body = as_json(rec)
    assert body["timestamp"].endswith("Z")
    assert body["timestamp"].startswith("2026-")
    assert ".500Z" in body["timestamp"]
    assert body["level"] == "INFO"
    assert body["logger"] == "app.test"
    assert body["message"] == "zmiana CHG-ALFA-2026-0001 zapisana"  # Polish kept (UTF-8)
    assert body["status"] == 201
    assert "request_id" not in body  # outside a request


def test_exception_is_included_and_masked() -> None:
    try:
        raise RuntimeError(f"token rejected: Bearer {JWT}")
    except RuntimeError:
        rec = logging.LogRecord(
            "app.test", logging.ERROR, __file__, 1, "boom", None, sys.exc_info()
        )
    body = as_json(rec)
    assert "RuntimeError" in body["exception"]
    assert JWT not in body["exception"]
    assert "c2lnbmF0dXJl" not in json.dumps(body)


# --------------------------------------------------------------------------- masking


@pytest.mark.parametrize(
    "text",
    [
        f"Authorization: Bearer {JWT}",
        f"token={JWT}",
        "password=Tajne-Haslo-123 user=jan",
        '{"password": "Tajne-Haslo-123", "login": "jan"}',
        "postgresql+asyncpg://app_rw:Tajne-Haslo-123@db:5432/rejestr",
        "DEV_AUTH_SECRET=Tajne-Haslo-123",
        "refresh_token: 'Tajne-Haslo-123'",
        "Basic dXNlcjpUYWpuZS1IYXNsby0xMjM=",
    ],
)
def test_secrets_in_messages_are_masked(text: str) -> None:
    body = as_json(record(text))
    assert "Tajne-Haslo-123" not in body["message"]
    assert "dXNlcjpUYWpuZS" not in body["message"]
    assert JWT not in body["message"]
    assert REDACTED in body["message"]


def test_secret_message_arguments_are_masked() -> None:
    body = as_json(record("login failed for %s with %s", "jan", f"Bearer {JWT}"))
    assert body["message"] == f"login failed for jan with Bearer {REDACTED}"


def test_sensitive_extra_fields_are_masked() -> None:
    body = as_json(
        record(
            "x",
            password="Tajne-Haslo-123",
            access_token=JWT,
            headers={"Authorization": f"Bearer {JWT}", "Accept": "application/json"},
            payload={"new_password": "Tajne", "nested": [{"client_secret": "s"}], "ok": 1},
            user_id=UUID(int=7),
        )
    )
    assert body["password"] == REDACTED
    assert body["access_token"] == REDACTED
    assert body["headers"] == {"Authorization": REDACTED, "Accept": "application/json"}
    assert body["payload"] == {
        "new_password": REDACTED,
        "nested": [{"client_secret": REDACTED}],
        "ok": 1,
    }
    assert body["user_id"] == str(UUID(int=7))


def test_redact_keeps_harmless_values() -> None:
    assert redact({"status": 200, "path": "/api/v1/me", "items": (1, None, True)}) == {
        "status": 200,
        "path": "/api/v1/me",
        "items": [1, None, True],
    }
    assert redact("CHG-ALFA-2026-0142 zatwierdzona") == "CHG-ALFA-2026-0142 zatwierdzona"


def test_console_formatter_masks_too() -> None:
    line = ConsoleFormatter().format(record(f"Bearer {JWT}", password="x", status=200))
    assert JWT not in line
    assert "password=[REDACTED]" in line
    assert "status=200" in line
    assert "Z INFO" in line


# --------------------------------------------------------------------------- configuration


def test_configure_logging_installs_one_handler(restore_logging: None) -> None:
    uvicorn_error = logging.getLogger("uvicorn.error")
    uvicorn_error.addHandler(logging.NullHandler())
    uvicorn_error.propagate = False
    root = logging.getLogger()
    foreign = logging.NullHandler()
    root.addHandler(foreign)
    configure_logging("WARNING", "json")
    own = [h for h in root.handlers if getattr(h, "_rejestr_handler", False)]
    assert len(own) == 1
    assert isinstance(own[0].formatter, JsonFormatter)
    assert foreign in root.handlers  # handlers of others (pytest) are kept
    assert root.level == logging.WARNING
    assert uvicorn_error.handlers == []
    assert uvicorn_error.propagate is True
    assert logging.getLogger("uvicorn.access").disabled is True
    configure_logging("DEBUG", "console")
    own = [h for h in root.handlers if getattr(h, "_rejestr_handler", False)]
    assert len(own) == 1
    assert isinstance(own[0].formatter, ConsoleFormatter)
    root.removeHandler(foreign)


def test_log_format_setting(monkeypatch: pytest.MonkeyPatch) -> None:
    assert make_settings().log_format == "json"
    monkeypatch.setenv("LOG_FORMAT", "Console")
    assert make_settings().log_format == "console"
    with pytest.raises(ValueError, match="log_format"):
        make_settings(log_format="xml")


# --------------------------------------------------------------------------- access log


class Capture(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


@pytest.fixture
def access_records() -> Iterator[list[logging.LogRecord]]:
    handler = Capture()
    logger = logging.getLogger(logs.ACCESS_LOGGER)
    logger.addHandler(handler)
    previous = logger.level
    logger.setLevel(logging.INFO)
    yield handler.records
    logger.removeHandler(handler)
    logger.setLevel(previous)


async def test_access_log_line_per_request(
    app: FastAPI, client: AsyncClient, access_records: list[logging.LogRecord]
) -> None:
    @app.get("/api/v1/_test/bound")
    async def bound() -> dict[str, str]:
        logs.bind(user_id=UUID(int=1), company_id=UUID(int=2))
        logging.getLogger("app.test").info("inside")
        return {}

    response = await client.get("/api/v1/_test/bound?q=tajne-zapytanie")
    assert response.status_code == 200
    [line] = access_records
    body = as_json(line)  # formatted outside the request: fields come from the record
    assert body["method"] == "GET"
    assert body["path"] == "/api/v1/_test/bound"  # no query string
    assert "tajne-zapytanie" not in json.dumps(body)
    assert body["status"] == 200
    assert body["duration_ms"] >= 0
    assert line.levelno == logging.INFO


async def test_access_log_carries_request_and_principal_ids(
    app: FastAPI, client: AsyncClient
) -> None:
    lines: list[str] = []

    class Format(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            lines.append(JsonFormatter().format(record))

    handler = Format()
    logger = logging.getLogger(logs.ACCESS_LOGGER)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    @app.get("/api/v1/_test/principal")
    async def principal() -> dict[str, str]:
        logs.bind(user_id=UUID(int=1), company_id=UUID(int=2))
        return {}

    try:
        response = await client.get("/api/v1/_test/principal")
    finally:
        logger.removeHandler(handler)
    body = json.loads(lines[-1])
    assert body["request_id"] == response.headers[REQUEST_ID_HEADER]
    assert body["user_id"] == str(UUID(int=1))
    assert body["company_id"] == str(UUID(int=2))


async def test_health_probe_is_not_logged_and_levels_follow_status(
    app: FastAPI, client: AsyncClient, access_records: list[logging.LogRecord]
) -> None:
    @app.get("/api/v1/_test/denied")
    async def denied() -> None:
        raise HTTPException(status_code=403)

    @app.get("/api/v1/_test/crash")
    async def crash() -> None:
        raise RuntimeError("boom")

    await client.get("/api/v1/health")  # 200 or 503 depending on the database
    assert (await client.get("/api/v1/_test/denied")).status_code == 403
    assert (await client.get("/api/v1/_test/nothing-here")).status_code == 404
    with contextlib.suppress(RuntimeError):
        await client.get("/api/v1/_test/crash")
    by_path = {getattr(r, "path", ""): r for r in access_records}
    assert by_path["/api/v1/_test/denied"].levelno == logging.WARNING
    assert by_path["/api/v1/_test/nothing-here"].levelno == logging.INFO
    assert by_path["/api/v1/_test/crash"].levelno == logging.ERROR
    assert getattr(by_path["/api/v1/_test/crash"], "status", None) == 500
    health = by_path.get("/api/v1/health")
    assert health is None or getattr(health, "status", None) != 200


def test_bind_outside_a_request_is_ignored() -> None:
    logs.bind(user_id=UUID(int=1))
    assert logs.current_context() == {}


def test_bind_principal_shapes() -> None:
    class User:
        id = UUID(int=3)
        memberships: dict[UUID, Any] = {}  # noqa: RUF012

    class Company:
        id = UUID(int=4)

    class Context:
        user = User()
        company = Company()

    holder: dict[str, Any] = {}
    token = logs._log_context.set(holder)
    try:
        logs.bind_principal(User())
        assert holder == {"user_id": UUID(int=3)}
        logs.bind_principal(Context())
        assert holder == {"user_id": UUID(int=3), "company_id": UUID(int=4)}
        logs.bind_principal(object())  # e.g. a visibility object: nothing bound
        assert len(holder) == 2
    finally:
        logs._log_context.reset(token)
