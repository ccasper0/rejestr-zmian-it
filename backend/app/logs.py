"""Application logs (api, worker): JSON lines or console text, with secrets masked.

ADR 0019 §4. ``LOG_FORMAT=json`` (default) writes one JSON object per line to stderr:

    {"timestamp": "2026-11-03T10:15:02.123Z", "level": "INFO", "logger": "app.access",
     "message": "GET /api/v1/me 200", "request_id": "...", "user_id": "...",
     "company_id": "...", "method": "GET", "path": "/api/v1/me", "status": 200,
     "duration_ms": 12.3, "client_ip": "203.0.113.7"}

- ``request_id`` is the id of ``audit_log.request_id`` and of the ``X-Request-ID``
  header (nginx logs the same value), so a log line, an audit entry and a proxy access
  log entry of one request can be joined.
- ``user_id`` / ``company_id`` are bound by the permission dependencies
  (:func:`bind_principal`) into a per-request holder (:class:`AccessLogMiddleware`).
- Secrets never reach the output: :func:`redact` masks values of sensitive keys
  (password, token, secret, authorization, cookie, ...) in ``extra`` fields and
  bearer tokens / JWTs / ``password=...`` pairs inside messages and tracebacks.
- uvicorn's own access log is replaced by :class:`AccessLogMiddleware` (one line per
  request with the fields above; query strings are not logged).
"""

from __future__ import annotations

import json
import logging
import re
import sys
import time
from collections.abc import Mapping
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any, Final
from uuid import UUID

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.request_context import get_client_info, get_request_id

ACCESS_LOGGER = "app.access"
REDACTED: Final = "[REDACTED]"

# Keys whose VALUES are never logged (substring match, case-insensitive).
_SENSITIVE_KEY = re.compile(
    r"pass(word|wd)?|secret|token|authori[sz]ation|cookie|api[-_]?key|credential|session"
    r"|private[-_]?key|signature",
    re.IGNORECASE,
)
# Secrets embedded in free text (messages, exception texts).
_TEXT_PATTERNS: Final = (
    # "Bearer <token>" / "Basic <credentials>"
    (re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]+"), r"\1 " + REDACTED),
    # JWT (header.payload.signature, base64url, header starts with "eyJ")
    (re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*"), REDACTED),
    # key=value / key: value / "key": "value" for sensitive keys
    (
        re.compile(
            r"(?i)([\"']?\b[\w-]*(?:password|passwd|secret|token|api[-_]?key|authorization)"
            r"[\w-]*[\"']?\s*[=:]\s*)(\"[^\"]*\"|'[^']*'|[^\s,;&}]+)"
        ),
        r"\1" + REDACTED,
    ),
    # credentials in URLs: scheme://user:password@host
    (re.compile(r"(?i)\b([a-z][a-z0-9+.-]*://[^\s/:@]+:)[^\s/@]+@"), r"\1" + REDACTED + "@"),
)

# Standard LogRecord attributes - everything else on a record came from ``extra=``.
_RECORD_ATTRS: Final = frozenset(
    logging.LogRecord("", 0, "", 0, "", None, None).__dict__.keys()
    | {"message", "asctime", "taskName"}
)

_OWN_HANDLER = "_rejestr_handler"

# Loggers configured by uvicorn / arq with their own handlers: routed to ours instead.
_FOREIGN_LOGGERS: Final = ("uvicorn", "uvicorn.error", "uvicorn.access", "arq", "arq.worker")


def redact_text(text: str) -> str:
    for pattern, replacement in _TEXT_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def redact(value: Any, *, key: str | None = None, _depth: int = 0) -> Any:
    """``value`` with secrets masked; mappings/sequences recursively (bounded depth)."""
    if key is not None and _SENSITIVE_KEY.search(key):
        return REDACTED
    if _depth > 6:
        return "..."
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, Mapping):
        return {str(k): redact(v, key=str(k), _depth=_depth + 1) for k, v in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [redact(v, _depth=_depth + 1) for v in value]
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, UUID | datetime):
        return str(value)
    return redact_text(str(value))


# --------------------------------------------------------------------------- context
# One mutable holder per request (set by AccessLogMiddleware): dependencies may run in
# other contexts (copies), so they mutate the holder instead of setting variables.
_log_context: ContextVar[dict[str, Any] | None] = ContextVar("log_context", default=None)


def bind(**fields: Any) -> None:
    """Attach fields (e.g. user_id, company_id) to every log line of this request."""
    holder = _log_context.get()
    if holder is not None:
        holder.update({k: v for k, v in fields.items() if v is not None})


def bind_principal(result: Any) -> None:
    """Bind user/company of a resolved permission dependency (CurrentUser / CompanyContext)."""
    user = getattr(result, "user", None)
    company = getattr(result, "company", None)
    if user is not None and company is not None:
        bind(user_id=getattr(user, "id", None), company_id=getattr(company, "id", None))
    elif hasattr(result, "memberships"):
        bind(user_id=getattr(result, "id", None))


def current_context() -> dict[str, Any]:
    fields: dict[str, Any] = {}
    request_id = get_request_id()
    if request_id is not None:
        fields["request_id"] = str(request_id)
    holder = _log_context.get()
    if holder:
        fields.update(holder)
    return fields


# --------------------------------------------------------------------------- formatters
def _timestamp(created: float) -> str:
    moment = datetime.fromtimestamp(created, tz=UTC)
    return moment.strftime("%Y-%m-%dT%H:%M:%S.") + f"{moment.microsecond // 1000:03d}Z"


def _extra(record: logging.LogRecord) -> dict[str, Any]:
    return {
        key: value
        for key, value in record.__dict__.items()
        if key not in _RECORD_ATTRS and not key.startswith("_")
    }


class JsonFormatter(logging.Formatter):
    """One JSON object per line; UTC timestamps; secrets masked."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": _timestamp(record.created),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_text(record.getMessage()),
        }
        payload.update(redact(current_context()))
        for key, value in _extra(record).items():
            payload[key] = redact(value, key=key)
        if record.exc_info:
            payload["exception"] = redact_text(self.formatException(record.exc_info))
        if record.stack_info:
            payload["stack"] = redact_text(self.formatStack(record.stack_info))
        return json.dumps(payload, ensure_ascii=False, default=str)


class ConsoleFormatter(logging.Formatter):
    """Human-readable lines for local development (same masking)."""

    def __init__(self) -> None:
        super().__init__("%(asctime)s %(levelname)-7s %(name)s %(message)s")

    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:  # noqa: N802
        return _timestamp(record.created)

    def format(self, record: logging.LogRecord) -> str:
        line = redact_text(super().format(record))
        fields = {**current_context(), **_extra(record)}
        if fields:
            rendered = " ".join(f"{k}={redact(v, key=k)}" for k, v in fields.items())
            line = f"{line} [{rendered}]"
        return line


def configure_logging(level: str, log_format: str = "json") -> None:
    """Root logger -> one stderr handler; uvicorn/arq loggers routed to it."""
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter() if log_format == "json" else ConsoleFormatter())
    setattr(handler, _OWN_HANDLER, True)
    root = logging.getLogger()
    # Only our previous handler is replaced (create_app may run more than once, e.g. in
    # tests); handlers installed by others (pytest) stay.
    for existing in list(root.handlers):
        if getattr(existing, _OWN_HANDLER, False):
            root.removeHandler(existing)
    root.addHandler(handler)
    root.setLevel(level)
    for name in _FOREIGN_LOGGERS:
        foreign = logging.getLogger(name)
        for existing in list(foreign.handlers):
            foreign.removeHandler(existing)
        foreign.propagate = True
    # Replaced by AccessLogMiddleware (with request_id/user_id, without query strings).
    logging.getLogger("uvicorn.access").disabled = True
    # SQL statements may contain data; never at INFO.
    logging.getLogger("sqlalchemy.engine").setLevel(max(logging.WARNING, root.level))


# --------------------------------------------------------------------------- access log
class AccessLogMiddleware:
    """One ``app.access`` line per HTTP request: method, path (no query), status,
    duration, client IP, request/user/company ids. Must run INSIDE RequestIdMiddleware."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.logger = logging.getLogger(ACCESS_LOGGER)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        token = _log_context.set({})
        started = time.perf_counter()
        status = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = int(message["status"])
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            path = scope.get("path", "")
            # Health probes every few seconds would drown the log.
            if not (path.endswith("/health") and status == 200):
                method = scope.get("method", "")
                level = (
                    logging.ERROR
                    if status >= 500
                    else logging.WARNING
                    if status in {401, 403, 429}
                    else logging.INFO
                )
                self.logger.log(
                    level,
                    "%s %s %s",
                    method,
                    path,
                    status,
                    extra={
                        "method": method,
                        "path": path,
                        "status": status,
                        "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                        "client_ip": get_client_info().ip,
                    },
                )
            _log_context.reset(token)
