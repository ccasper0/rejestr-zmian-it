"""Authentication / authorization events — the ONE place the API records them (ADR 0010).

``login_failed`` and ``access_denied`` (403, and 404 for a company the user has no
membership in) go to the GLOBAL audit chain (``context.target_company_id`` for denials,
ADR 0006 §7) through ``app.services.auth_events``. They are written in a SEPARATE
transaction (``app.db.run_in_separate_transaction``), committed before the request fails:
the request transaction is rolled back on 401/403/404 and must not take the entry with it.

``login`` is recorded while the identity is resolved (``app.auth.dependencies``), in the
same separate transaction as JIT provisioning / profile sync.

Never pass tokens, claims of an unverified token or secrets to these functions: only the
verifier's error message (``detail``) and, for a VERIFIED token, its subject.

Call these BEFORE the request transaction locks any audit chain head (the helper refuses
otherwise) — the permission dependencies call them before the endpoint runs. The outer
transaction may hold a main-pool connection at that point; the event transaction takes
its connection from the separate auxiliary pool, so they cannot deadlock (ADR 0010 §5).
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.auth.principal import CurrentUser
from app.config import Settings
from app.db import get_database, run_in_separate_transaction
from app.domain.audit import Actor
from app.services import auth_events
from app.services.auth_events import FailureReason

__all__ = ["FailureReason", "record_access_denied", "record_login_failed"]

logger = logging.getLogger(__name__)


def _settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


async def record_login_failed(
    request: Request,
    outer: AsyncSession | None,
    *,
    reason: FailureReason,
    actor: Actor | None = None,
    subject: str | None = None,
    detail: str | None = None,
) -> None:
    """A failed authentication (aggregated per window and client, ADR 0010 §3)."""
    settings = _settings(request)
    logger.info(
        "auth event login_failed reason=%s path=%s user_id=%s",
        reason.value,
        request.url.path,
        actor.id if actor else None,
    )
    await run_in_separate_transaction(
        get_database(request),
        lambda session: auth_events.record_login_failure(
            session,
            reason=reason,
            window_seconds=settings.auth_failure_window_seconds,
            max_buckets=settings.auth_failure_max_buckets,
            max_immediate_entries=settings.auth_failure_max_immediate_entries,
            actor=actor,
            subject=subject,
            detail=detail,
            method=request.method,
            path=request.url.path,
        ),
        outer=outer,
    )


async def record_access_denied(
    request: Request,
    outer: AsyncSession | None,
    *,
    user: CurrentUser,
    status: int,
    reason: str,
    company_id: UUID | None = None,
) -> None:
    """A denied request of an authenticated user (403, or 404 for a foreign company)."""
    logger.info(
        "auth event access_denied status=%s path=%s user_id=%s company_id=%s reason=%s",
        status,
        request.url.path,
        user.id,
        company_id,
        reason,
    )
    actor = user.actor(company_id)
    await run_in_separate_transaction(
        get_database(request),
        lambda session: auth_events.record_access_denied(
            session,
            actor=actor,
            status=status,
            reason=reason,
            company_id=company_id,
            method=request.method,
            path=request.url.path,
        ),
        outer=outer,
    )
