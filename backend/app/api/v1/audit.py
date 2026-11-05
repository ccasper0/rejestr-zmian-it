"""Audit log: chain verification and browsing (CLAUDE.md 6.4, 8; ADR 0009).

The chain is chosen by the optional query parameter ``company_id``: omitted = the GLOBAL
chain (app admins only), given = that company's chain (membership, 404 otherwise).
"""

from __future__ import annotations

from datetime import timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request
from pydantic import AwareDatetime

from app.auth.principal import AuditChainContext, CompanyContext
from app.db import SessionDep
from app.domain.audit import AuditAction, EntityType, normalize_ip
from app.errors import ProblemError
from app.permissions import Action, company_not_found, require_audit_chain, require_company
from app.schemas.audit import AuditEntryOut, AuditEntryRef, ChainStatusOut, VerifyOut
from app.schemas.common import DEFAULT_LIMIT, MAX_LIMIT, Page
from app.services import audit as audit_service

router = APIRouter(prefix="/audit", tags=["audit"])
company_router = APIRouter(prefix="/companies", tags=["audit"])


@company_router.get("/{company_id}/audit/status", response_model=ChainStatusOut)
async def get_chain_status(
    request: Request,
    session: SessionDep,
    ctx: CompanyContext = require_company(
        Action.REGISTER_VIEW, admin_action=Action.AUDIT_READ, admin_read_only=True
    ),
) -> ChainStatusOut:
    """Verdict of the company's audit chain for the "Łańcuch spójny" badge (§10.2): any
    member, and the app admin of any company on the narrow read path (ADR 0015 §7); no
    details of a violation, no audit entry per view (ADR 0013 §11)."""
    from app.services.changes import db_now

    max_age = timedelta(hours=request.app.state.settings.audit_status_max_age_hours)
    status = await audit_service.chain_status(
        session, ctx.company_id, max_age=max_age, now=await db_now(session)
    )
    ok = {"ok": True, "broken": False}.get(status.status)
    return ChainStatusOut(
        status=status.status,
        ok=ok,
        checked_at=status.checked_at,
        verified_head_seq=status.verified_head_seq,
        head_seq=status.head_seq,
    )


@router.post("/verify", response_model=VerifyOut)
async def verify_audit_chain(
    session: SessionDep,
    chain: AuditChainContext = require_audit_chain(Action.AUDIT_VERIFY, admin_any_company=True),
) -> VerifyOut:
    """Recompute the chain; the verification and its result are appended to the log."""
    try:
        outcome = await audit_service.verify_and_record(
            session,
            chain.company_id,
            actor=chain.actor(),
            context={"source": "api", "admin_path": chain.admin_path},
        )
    except audit_service.AuditScopeError as exc:  # pragma: no cover - the dependency scopes it
        raise company_not_found() from exc
    verification, entry = outcome.verification, outcome.entry
    result = verification.result
    return VerifyOut(
        company_id=chain.company_id,
        chain="global" if chain.company_id is None else "company",
        ok=result.ok,
        checked=result.checked,
        first_broken_seq=result.first_broken_seq,
        head_seq=verification.head_seq,
        head_hash=verification.head_hash,
        verified_at=entry.occurred_at if entry else None,
        recorded_in=outcome.recorded_in,
        audit_entry=(
            AuditEntryRef(company_id=entry.company_id, seq=entry.seq, hash=entry.hash)
            if entry
            else None
        ),
    )


@router.get("", response_model=Page[AuditEntryOut])
async def list_audit_entries(
    session: SessionDep,
    chain: AuditChainContext = require_audit_chain(Action.AUDIT_READ, admin_read_any_company=True),
    entity_type: EntityType | None = None,
    entity_id: UUID | None = None,
    action: AuditAction | None = None,
    actor_id: UUID | None = None,
    occurred_from: Annotated[
        AwareDatetime | None, Query(description="Od (włącznie), ISO 8601 ze strefą")
    ] = None,
    occurred_to: Annotated[
        AwareDatetime | None, Query(description="Do (wyłącznie), ISO 8601 ze strefą")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[AuditEntryOut]:
    """Entries of one chain, newest first (``seq`` descending), with ``hash``/``prev_hash``."""
    if occurred_from is not None and occurred_to is not None and occurred_from >= occurred_to:
        raise ProblemError(
            status=422,
            code="audit.invalid_period",
            detail="Początek okresu musi być wcześniejszy niż jego koniec.",
        )
    filters = audit_service.EntryFilters(
        entity_type=entity_type.value if entity_type else None,
        entity_id=entity_id,
        action=action.value if action else None,
        actor_id=actor_id,
        occurred_from=occurred_from,
        occurred_to=occurred_to,
    )
    try:
        rows, total = await audit_service.list_entries(
            session, chain.company_id, filters, limit=limit, offset=offset
        )
    except audit_service.AuditScopeError as exc:  # pragma: no cover - the dependency scopes it
        raise company_not_found() from exc
    items = [
        AuditEntryOut(
            id=row.id,
            company_id=row.company_id,
            seq=row.seq,
            occurred_at=row.occurred_at,
            actor_id=row.actor_id,
            actor_display=row.actor_display,
            actor_roles=list(row.actor_roles),
            ip_address=normalize_ip(row.ip_address),
            user_agent=row.user_agent,
            request_id=row.request_id,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            action=row.action,
            diff=row.diff,
            context=row.context,
            prev_hash=row.prev_hash,
            hash=row.hash,
        )
        for row in rows
    ]
    return Page[AuditEntryOut](items=items, total=total, limit=limit, offset=offset)
