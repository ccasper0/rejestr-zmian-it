"""Comments of a change (CLAUDE.md 4.1, 6.5): only added, never edited or removed.

``app_rw`` has only SELECT, INSERT on ``change_comments`` and a trigger rejects UPDATE /
DELETE for every role (migration 0008). A comment may be added in every status (it does
not change the frozen fields of the change), but not in an archived company (trigger
``company_must_be_active``). Comments given with an action (return, reject, ...) are
written by ``app.services.changes.perform_action`` (ADR 0013 §6).
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.audit import AuditAction, EntityType
from app.domain.changes import ChangeRuleError
from app.domain.companies import CompanyStatus
from app.domain.state_machine import normalize_comment
from app.models import Change, ChangeComment, Company
from app.services import audit
from app.services.changes import (
    ChangeActor,
    company_archived,
    db_now,
    flush_guarded,
    not_found,
    rule_problem,
)


async def add_comment(
    session: AsyncSession,
    *,
    actor: ChangeActor,
    company: Company,
    change_id: UUID,
    body: str,
    now: datetime | None = None,
    audit_context: Mapping[str, object] | None = None,
) -> ChangeComment:
    """Append a comment (1-4000 characters after trimming, ``change.comment_*`` errors)."""
    if company.status == CompanyStatus.ARCHIVED:
        raise company_archived()
    change = (
        await session.execute(
            select(Change).where(Change.company_id == company.id, Change.id == change_id)
        )
    ).scalar_one_or_none()
    if change is None:
        raise not_found()
    try:
        clean = normalize_comment(body, required=True)
    except ChangeRuleError as exc:
        raise rule_problem(exc) from exc
    assert clean is not None  # noqa: S101 - required=True never returns None
    clock = now or await db_now(session)
    comment = ChangeComment(
        id=uuid4(),
        company_id=company.id,
        change_id=change.id,
        author_id=actor.user_id,
        body=clean,
        action=None,
        created_at=clock,
        updated_at=clock,
    )
    session.add(comment)
    await flush_guarded(session)
    await audit.record(
        session,
        company_id=company.id,
        actor=actor.audit,
        entity_type=EntityType.CHANGE,
        entity_id=change.id,
        action=AuditAction.COMMENT,
        context={
            "number": change.number,
            "comment_id": comment.id,
            "comment": clean,
            **(audit_context or {}),
        },
    )
    return comment
