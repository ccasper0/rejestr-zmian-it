"""FastAPI application factory.

``uvicorn app.main:app`` uses the module-level ``app``; tests call ``create_app(settings)``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.v1 import api_router, dev_auth
from app.api.v1 import auth as local_auth_api
from app.auth.verifier import build_verifier
from app.config import Settings, get_settings
from app.db import Database
from app.errors import install_problem_handlers
from app.logs import AccessLogMiddleware, configure_logging
from app.reports.queue import ArqReportQueue
from app.reports.render import weasyprint_pdf
from app.request_context import RequestIdMiddleware

API_PREFIX = "/api/v1"


def create_app(settings: Settings | None = None) -> FastAPI:
    # get_settings() validates the environment: APP_ENV=prod + AUTH_MODE=dev, or a too short
    # AUTH_JWT_SECRET, raises here - the process refuses to start. A missing
    # AUTH_JWT_SECRET (AUTH_MODE=local) is refused when serving starts (lifespan).
    settings = settings or get_settings()
    # JSON (or console) logs with request_id / user_id / company_id, secrets masked
    # (app.logs, ADR 0019 §4); replaces uvicorn's access log.
    configure_logging(settings.log_level, settings.log_format)

    db = Database.from_settings(settings)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        # Refuse to serve without the token key: every login would fail.
        missing = settings.missing_auth_settings()
        if missing:
            raise RuntimeError(
                f"AUTH_MODE=local requires {', '.join(missing)} to be set (see .env.example)"
            )
        try:
            yield
        finally:
            await application.state.token_verifier.aclose()
            await application.state.report_queue.aclose()
            await db.dispose()

    # Interactive docs and the OpenAPI schema only with APP_ENV=dev (ADR 0019 §9 p. 4,
    # decision of the owner 2026-11-04): in production they would map the whole attack
    # surface for anyone who can reach the API. Elsewhere all three paths are 404.
    docs_enabled = settings.is_dev
    app = FastAPI(
        title="Rejestr zmian IT — API",
        version=__version__,
        lifespan=lifespan,
        docs_url=f"{API_PREFIX}/docs" if docs_enabled else None,
        redoc_url=None,
        openapi_url=f"{API_PREFIX}/openapi.json" if docs_enabled else None,
    )
    app.state.settings = settings
    app.state.db = db
    # Access tokens of AUTH_MODE (local accounts or dev login, ADR 0018).
    app.state.token_verifier = build_verifier(settings)
    # Reports (ADR 0017): PDF renderer and the queue of background jobs (tests replace them).
    app.state.pdf_renderer = weasyprint_pdf
    app.state.report_queue = ArqReportQueue(settings.redis_url)

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type", "If-Match", "X-Request-ID"],
            expose_headers=[
                "ETag",
                "Location",
                "X-Request-ID",
                "Retry-After",
                "Content-Disposition",
                "X-Report-Id",
                "X-Report-Number",
                "X-Data-SHA256",
                "X-Content-SHA256",
            ],
        )

    # Inside RequestIdMiddleware: the access log line carries the request id.
    app.add_middleware(AccessLogMiddleware)
    # Added last = outermost user middleware: every response (incl. CORS preflight) gets an id.
    app.add_middleware(RequestIdMiddleware)

    install_problem_handlers(app)
    app.include_router(api_router, prefix=API_PREFIX)
    if settings.auth_mode == "dev":
        # Dev login exists ONLY in dev mode (404 otherwise); Settings forbids it in prod.
        app.include_router(dev_auth.router, prefix=API_PREFIX)
    else:
        # Local accounts: login, refresh, logout, password change (ADR 0018).
        app.include_router(local_auth_api.router, prefix=API_PREFIX)
    return app


app = create_app()
