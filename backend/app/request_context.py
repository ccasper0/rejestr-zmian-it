"""Per-request context: request ID (``audit_log.request_id``, CLAUDE.md 6.1).

``RequestIdMiddleware`` accepts an incoming ``X-Request-ID`` only when it parses as a UUID
(nginx sends ``$request_id`` — 32 hex chars, which ``uuid.UUID`` accepts); otherwise it
generates a uuid4. The id is:

- available to services via :func:`get_request_id` (contextvar),
- stored in ``scope["state"]["request_id"]`` (read by the problem+json handlers, which for
  unhandled 500s run outside this middleware),
- echoed in the ``X-Request-ID`` response header.

The middleware also exposes the client IP (``scope["client"]``, already rewritten by
uvicorn's proxy-headers middleware for the trusted nginx only, ADR 0004) and the
``User-Agent`` through :func:`get_client_info`, so ``audit.record`` fills
``audit_log.ip_address`` / ``user_agent`` without every service passing them around.
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from ipaddress import ip_address
from typing import Any
from uuid import UUID, uuid4

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

REQUEST_ID_HEADER = "X-Request-ID"
STATE_KEY = "request_id"

# Longest textual UUID form accepted by uuid.UUID is "urn:uuid:" + 36 chars.
_MAX_RAW_LENGTH = 45

_request_id: ContextVar[UUID | None] = ContextVar("request_id", default=None)


@dataclass(frozen=True, slots=True)
class ClientInfo:
    ip: str | None = None
    user_agent: str | None = None


_NO_CLIENT = ClientInfo()
_client_info: ContextVar[ClientInfo] = ContextVar("client_info", default=_NO_CLIENT)


def get_client_info() -> ClientInfo:
    """Client IP and User-Agent of the request being handled (empty outside a request)."""
    return _client_info.get()


def _client_from_scope(scope: Scope) -> ClientInfo:
    ip: str | None = None
    client = scope.get("client")
    if client:
        try:
            ip = str(ip_address(client[0]))
        except ValueError:
            ip = None
    agent: str | None = None
    for name, value in scope.get("headers", ()):
        if name == b"user-agent":
            agent = value.decode("latin-1")
            break
    return ClientInfo(ip=ip, user_agent=agent)


def parse_request_id(raw: str | None) -> UUID | None:
    """Return the UUID carried by ``raw`` or None if it is absent/invalid."""
    if not raw or len(raw) > _MAX_RAW_LENGTH:
        return None
    try:
        return UUID(raw.strip())
    except ValueError:
        return None


def get_request_id() -> UUID | None:
    """Request ID of the request being handled (None outside a request)."""
    return _request_id.get()


def request_id_from_scope(scope: Scope | Any) -> UUID | None:
    """Request ID stored by the middleware in the ASGI scope (fallback: contextvar)."""
    state = scope.get("state") if isinstance(scope, dict) else None
    value = state.get(STATE_KEY) if isinstance(state, dict) else None
    return value if isinstance(value, UUID) else get_request_id()


class RequestIdMiddleware:
    """Pure ASGI middleware (no BaseHTTPMiddleware: keeps contextvars and streaming intact)."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        raw: str | None = None
        for name, value in scope.get("headers", ()):
            if name == b"x-request-id":
                raw = value.decode("latin-1")
                break
        request_id = parse_request_id(raw) or uuid4()

        scope.setdefault("state", {})[STATE_KEY] = request_id
        header_value = str(request_id)

        async def send_with_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers[REQUEST_ID_HEADER] = header_value
            await send(message)

        token = _request_id.set(request_id)
        client_token = _client_info.set(_client_from_scope(scope))
        try:
            await self.app(scope, receive, send_with_id)
        finally:
            _client_info.reset(client_token)
            _request_id.reset(token)
