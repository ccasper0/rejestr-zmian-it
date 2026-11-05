"""Client IP (future ``audit_log.ip_address``) must not be spoofable via X-Forwarded-For.

Uvicorn reads trusted proxies from env ``FORWARDED_ALLOW_IPS`` (image default 127.0.0.1).
In Docker Compose it is the fixed compose subnet; nginx sends a single-hop
``X-Forwarded-For $remote_addr``.
"""

from pathlib import Path

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient
from uvicorn.config import Config
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from app.main import create_app
from tests.conftest import make_settings

DOCKERFILE = Path(__file__).resolve().parents[1] / "Dockerfile"


def _app_with_echo() -> FastAPI:
    app = create_app(make_settings())

    @app.get("/api/v1/_test/client")
    async def _client(request: Request) -> dict[str, str | None]:
        return {"host": request.client.host if request.client else None}

    return app


def _loaded_app(monkeypatch: pytest.MonkeyPatch, allow: str | None) -> ProxyHeadersMiddleware:
    """Build the ASGI app the way the uvicorn CLI does (proxy headers on, env-driven trust)."""
    if allow is None:
        monkeypatch.delenv("FORWARDED_ALLOW_IPS", raising=False)
    else:
        monkeypatch.setenv("FORWARDED_ALLOW_IPS", allow)
    config = Config(_app_with_echo(), proxy_headers=True, lifespan="off")
    config.load()
    assert isinstance(config.loaded_app, ProxyHeadersMiddleware)
    return config.loaded_app


async def _client_host(asgi: ProxyHeadersMiddleware, peer: str, xff: str | None) -> str:
    headers = {"X-Forwarded-For": xff} if xff is not None else {}
    transport = ASGITransport(app=asgi, client=(peer, 40000))  # type: ignore[arg-type]
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.get("/api/v1/_test/client", headers=headers)
    assert r.status_code == 200
    host: str = r.json()["host"]
    return host


async def test_untrusted_client_cannot_spoof_ip_default(monkeypatch: pytest.MonkeyPatch) -> None:
    asgi = _loaded_app(monkeypatch, None)
    assert await _client_host(asgi, "203.0.113.5", "1.2.3.4") == "203.0.113.5"


async def test_untrusted_client_cannot_spoof_ip_with_compose_subnet(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asgi = _loaded_app(monkeypatch, "172.28.0.0/16")
    assert await _client_host(asgi, "203.0.113.5", "1.2.3.4") == "203.0.113.5"


async def test_trusted_proxy_forwards_client_ip(monkeypatch: pytest.MonkeyPatch) -> None:
    asgi = _loaded_app(monkeypatch, "172.28.0.0/16")
    assert await _client_host(asgi, "172.28.0.10", "198.51.100.7") == "198.51.100.7"


async def test_trusted_proxy_ignores_client_supplied_prefix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Even if a proxy appended instead of overwriting, the client-controlled leftmost
    # entry must not win: uvicorn takes the rightmost untrusted address.
    asgi = _loaded_app(monkeypatch, "172.28.0.0/16")
    assert await _client_host(asgi, "172.28.0.10", "6.6.6.6, 198.51.100.7") == "198.51.100.7"


def test_dockerfile_does_not_trust_all_proxies() -> None:
    content = DOCKERFILE.read_text(encoding="utf-8")
    cmd = next(line for line in content.splitlines() if line.startswith("CMD"))
    assert "*" not in cmd
    assert "--forwarded-allow-ips" not in cmd  # taken from env FORWARDED_ALLOW_IPS
    assert "FORWARDED_ALLOW_IPS=127.0.0.1" in content
