"""Changes of a company: register, card, edit, readiness, actions, audit trail, comments,
attachments and register tiles (CLAUDE.md §8; ADR 0012, ADR 0013).

Reads (list, card, readiness, change audit trail, attachment list, tiles) declare
``require_register_read``: members by their roles; an app admin WITHOUT a role in the
company on the named narrow READ-ONLY path (owner decision 2026-11-02, ADR 0016) - the card
then has ``access = "admin_read_only"`` and no actions / editable fields. Every other route
needs a membership in ``{company_id}`` (otherwise 404, also for app admins: §5 / ADR 0007
§4 - the admin is not implicitly a member and performs no change actions), including the
attachment download (it writes an audit entry). Writes declare ``change.edit_draft``
(editor, approver); actions declare the matrix row of the path's action
(``require_change_action``). Finer rules (author, assignee, designated approver, four
eyes, frozen fields) are decided by the state machine.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, File, Header, Path, Query, Request, Response, UploadFile
from fastapi.responses import FileResponse
from pydantic import AwareDatetime

from app.auth.principal import CompanyContext
from app.db import SessionDep
from app.domain.audit import normalize_ip
from app.domain.changes import ChangeAction, ChangeStatus, ChangeType
from app.errors import ProblemError
from app.models import Attachment, ChangeCategory, User
from app.permissions import (
    Action,
    require_change_action,
    require_company,
    require_register_read,
)
from app.schemas.changes import (
    ActionIn,
    ActionOut,
    AttachmentOut,
    CategoryRef,
    ChangeAuditEntryOut,
    ChangeCiOut,
    ChangeCreate,
    ChangeOut,
    ChangeSummaryOut,
    ChangeUpdate,
    CheckOut,
    CommentIn,
    CommentOut,
    ConsentOut,
    DeviationOut,
    LinkedChangeOut,
    ReadinessOut,
    StatsOut,
    UserRef,
)
from app.schemas.common import DEFAULT_LIMIT, MAX_LIMIT, Page, SafeLine
from app.services import attachments as attachments_service
from app.services import audit as audit_service
from app.services import changes as changes_service
from app.services import comments as comments_service

router = APIRouter(prefix="/companies", tags=["changes"])

Limit = Annotated[int, Query(ge=1, le=MAX_LIMIT)]
Offset = Annotated[int, Query(ge=0)]

CHANGE_FIELDS = (
    "title",
    "category_id",
    "subcategory_id",
    "change_type",
    "risk",
    "description",
    "implementation_plan",
    "rollback_plan",
    "impact",
    "requirement_ref",
    "ticket_ref",
    "assignee_id",
    "approver_id",
    "verifier_id",
    "window_start",
    "window_end",
    "ci_ids",
)
NUMBER_PATTERN = r"^CHG-[A-Z]{2,8}-[0-9]{4}-[0-9]{4,}$"
# Served with their own type (always as a download); anything else as octet-stream.
SAFE_DOWNLOAD_TYPES = frozenset(
    {"application/pdf", "image/png", "image/jpeg", "image/gif", "text/plain", "text/csv"}
)


def _actor(ctx: CompanyContext) -> changes_service.ChangeActor:
    return changes_service.ChangeActor(
        audit=ctx.actor(), user_id=ctx.user.id, roles=ctx.user.roles_in(ctx.company_id)
    )


def _user(users: dict[Any, User] | Any, user_id: UUID | None) -> UserRef | None:
    if user_id is None:
        return None
    user = users.get(user_id)
    return UserRef(id=user_id, display_name=user.display_name if user else str(user_id))


def _category(categories: Any, category_id: UUID | None) -> CategoryRef | None:
    if category_id is None:
        return None
    category: ChangeCategory | None = categories.get(category_id)
    if category is None:  # pragma: no cover - FK
        return None
    return CategoryRef(id=category.id, code=category.code, name=category.name)


def _ci_out(item: changes_service.ItemView, users: Any) -> ChangeCiOut:
    return ChangeCiOut(
        id=item.ci_id,
        identifier=item.identifier,
        name=item.name,
        ci_type_code=item.ci_type_code,
        is_active=item.is_active,
        snapshot=item.snapshot,
        current_identifier=item.current_identifier,
        current_name=item.current_name,
        owner=_user(users, item.owner_user_id),
        consented=item.consented,
    )


def _summary_fields(
    change: Any, items: list[changes_service.ItemView], devs: Any, users: Any, categories: Any
) -> dict[str, Any]:
    return {
        "id": change.id,
        "company_id": change.company_id,
        "number": change.number,
        "title": change.title,
        "status": change.status,
        "change_type": change.change_type,
        "risk": change.risk,
        "category": _category(categories, change.category_id),
        "subcategory": _category(categories, change.subcategory_id),
        "ci": [_ci_out(i, users) for i in items],
        "requested_by": _user(users, change.requested_by_id),
        "assignee": _user(users, change.assignee_id),
        "approver": _user(users, change.approver_id),
        "verifier": _user(users, change.verifier_id),
        "window_start": change.window_start,
        "window_end": change.window_end,
        "approved_at": change.approved_at,
        "approved_by": _user(users, change.approved_by_id),
        "auto_approved": change.approved_at is not None and change.approved_by_id is None,
        "implemented_at": change.implemented_at,
        "verified_at": change.verified_at,
        "rejected_at": change.rejected_at,
        "deviations": [
            DeviationOut(kind=d.kind.value, critical=d.critical, message_pl=d.message_pl)
            for d in devs
        ],
        "created_at": change.created_at,
        "updated_at": change.updated_at,
    }


def _change_out(view: changes_service.ChangeView, *, read_only: bool = False) -> ChangeOut:
    """``read_only``: the admin read path (ADR 0016) - no actions, no editable fields."""
    change = view.change
    return ChangeOut(
        **_summary_fields(change, view.items, view.deviations, view.users, view.categories),
        description=change.description,
        implementation_plan=change.implementation_plan,
        rollback_plan=change.rollback_plan,
        impact=change.impact,
        requirement_ref=change.requirement_ref,
        ticket_ref=change.ticket_ref,
        supersedes_change_id=change.supersedes_change_id,
        supersedes_number=view.links.supersedes_number,
        superseded_by=[
            LinkedChangeOut(id=c.id, number=c.number, status=c.status)
            for c in view.links.superseded_by
        ],
        version=change.version,
        allowed_actions=[] if read_only else [a.value for a in view.allowed_actions],
        editable_fields=[] if read_only else sorted(f.value for f in view.editable_fields),
        access="admin_read_only" if read_only else "member",
        suggested_approver_id=view.suggested_approver_id,
        consents=[
            ConsentOut(
                ci_id=c.ci_id,
                owner=_user(view.users, c.owner_user_id),
                consented_at=c.consented_at,
                valid=c.valid,
                by_requester_or_assignee=c.by_requester_or_assignee,
            )
            for c in view.consents
        ],
        comments=[
            CommentOut(
                id=c.id,
                author=_user(view.users, c.author_id),
                body=c.body,
                action=c.action,
                created_at=c.created_at,
            )
            for c in view.comments
        ],
    )


def _etag(version: int) -> str:
    return f'"{version}"'


def _optional_version(body_version: int | None, if_match: str | None) -> int | None:
    """``version`` from the body or ``If-Match`` (``"3"``, ``W/"3"`` or ``3``)."""
    header_version = None
    if if_match is not None:
        raw = if_match.strip().removeprefix("W/").strip('"')
        if not raw.isdigit():
            raise ProblemError(
                status=400,
                code="change.invalid_if_match",
                detail='Nagłówek If-Match musi zawierać wersję zmiany, np. "3".',
            )
        header_version = int(raw)
    if body_version is not None and header_version is not None and body_version != header_version:
        raise ProblemError(
            status=400,
            code="change.version_mismatch",
            detail="Wersja w treści żądania różni się od wersji w nagłówku If-Match.",
        )
    return body_version if body_version is not None else header_version


def _version(body_version: int | None, if_match: str | None) -> int:
    """Like :func:`_optional_version`, but required (428 without it)."""
    version = _optional_version(body_version, if_match)
    if version is None:
        raise ProblemError(
            status=428,
            code="change.version_required",
            detail="Podaj wersję zmiany (pole version lub nagłówek If-Match).",
        )
    return version


def _approved_by(value: str | None) -> tuple[UUID | None, bool]:
    """``approved_by`` filter: a user id or ``system`` (auto-approved standard changes)."""
    if value is None:
        return None, False
    if value == "system":
        return None, True
    try:
        return UUID(value), False
    except ValueError:
        raise ProblemError(
            status=422,
            code="change.invalid_filter",
            detail="Filtr approved_by przyjmuje identyfikator użytkownika albo 'system'.",
            extra={"fields": ["approved_by"]},
        ) from None


async def _card(
    session: SessionDep, ctx: CompanyContext, change_id: UUID, response: Response | None = None
) -> ChangeOut:
    view = await changes_service.get_change_view(
        session, company=ctx.company, change_id=change_id, actor=_actor(ctx)
    )
    if response is not None:
        response.headers["ETag"] = _etag(view.change.version)
    return _change_out(view, read_only=ctx.read_only)


# --------------------------------------------------------------------------- register


@router.get("/{company_id}/changes", response_model=Page[ChangeSummaryOut])
async def list_changes(
    session: SessionDep,
    ctx: CompanyContext = require_register_read(),
    period_from: Annotated[
        AwareDatetime | None, Query(description="Od (włącznie), ISO 8601 ze strefą")
    ] = None,
    period_to: Annotated[
        AwareDatetime | None, Query(description="Do (wyłącznie), ISO 8601 ze strefą")
    ] = None,
    period_by: Annotated[
        Literal["created", "implemented"],
        Query(description="Data, której dotyczy okres: rejestracji lub wdrożenia"),
    ] = "created",
    status: Annotated[list[ChangeStatus] | None, Query(max_length=8)] = None,
    type: Annotated[list[ChangeType] | None, Query(max_length=3)] = None,
    category: Annotated[list[UUID] | None, Query(max_length=100)] = None,
    ci: Annotated[list[UUID] | None, Query(max_length=100)] = None,
    assignee: UUID | None = None,
    approver: Annotated[UUID | None, Query(description="Wskazany zatwierdzający")] = None,
    approved_by: Annotated[
        str | None,
        Query(
            max_length=36,
            description="Kto faktycznie zatwierdził: id użytkownika albo 'system' (automatycznie)",
        ),
    ] = None,
    q: Annotated[
        SafeLine | None, Query(max_length=200, description="Szukaj w numerze, tytule, zgłoszeniu")
    ] = None,
    sort: changes_service.SortKey = changes_service.SortKey.CREATED_AT_DESC,
    limit: Limit = DEFAULT_LIMIT,
    offset: Offset = 0,
) -> Page[ChangeSummaryOut]:
    if period_from is not None and period_to is not None and period_from >= period_to:
        raise ProblemError(
            status=422,
            code="change.invalid_period",
            detail="Początek okresu musi być wcześniejszy niż jego koniec.",
        )
    approved_by_id, approved_by_system = _approved_by(approved_by)
    page = await changes_service.list_changes(
        session,
        ctx.company_id,
        changes_service.ChangeFilters(
            period_from=period_from,
            period_to=period_to,
            period_by=period_by,
            statuses=status or (),
            types=type or (),
            categories=category or (),
            cis=ci or (),
            assignee_id=assignee,
            approver_id=approver,
            approved_by_id=approved_by_id,
            approved_by_system=approved_by_system,
            q=q,
        ),
        sort=sort,
        limit=limit,
        offset=offset,
    )
    items = [
        ChangeSummaryOut(
            **_summary_fields(row.change, row.items, row.deviations, page.users, page.categories)
        )
        for row in page.rows
    ]
    return Page[ChangeSummaryOut](items=items, total=page.total, limit=limit, offset=offset)


@router.post("/{company_id}/changes", response_model=ChangeOut, status_code=201)
async def create_change(
    body: ChangeCreate,
    request: Request,
    response: Response,
    session: SessionDep,
    ctx: CompanyContext = require_company(Action.CHANGE_EDIT_DRAFT),
) -> ChangeOut:
    """A new draft with its number (``CHG-{PREFIX}-{YYYY}-{NNNN}``)."""
    values = {name: getattr(body, name) for name in body.model_fields_set if name in CHANGE_FIELDS}
    change = await changes_service.create_change(
        session,
        actor=_actor(ctx),
        company=ctx.company,
        values=values,
        supersedes_change_id=body.supersedes_change_id,
    )
    response.headers["Location"] = f"{request.url.path}/{change.id}"
    return await _card(session, ctx, change.id, response)


@router.get("/{company_id}/changes/by-number/{number}", response_model=ChangeOut)
async def get_change_by_number(
    number: Annotated[str, Path(max_length=40, pattern=NUMBER_PATTERN)],
    response: Response,
    session: SessionDep,
    ctx: CompanyContext = require_register_read(),
) -> ChangeOut:
    """The change card by its number (URL ``/c/:prefix/changes/:number`` of the frontend)."""
    change_id = await changes_service.find_id_by_number(session, ctx.company_id, number)
    if change_id is None:
        raise changes_service.not_found()
    return await _card(session, ctx, change_id, response)


@router.get("/{company_id}/changes/{change_id}", response_model=ChangeOut)
async def get_change(
    change_id: UUID,
    response: Response,
    session: SessionDep,
    ctx: CompanyContext = require_register_read(),
) -> ChangeOut:
    return await _card(session, ctx, change_id, response)


@router.patch("/{company_id}/changes/{change_id}", response_model=ChangeOut)
async def update_change(
    change_id: UUID,
    body: ChangeUpdate,
    response: Response,
    session: SessionDep,
    ctx: CompanyContext = require_company(Action.CHANGE_EDIT_DRAFT),
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> ChangeOut:
    """Edit the provided fields; ``version`` in the body or ``If-Match`` is required
    (409 ``change.version_conflict`` when stale, 409 ``change.frozen`` from implemented)."""
    version = _version(body.version, if_match)
    values = {name: getattr(body, name) for name in body.model_fields_set if name in CHANGE_FIELDS}
    await changes_service.update_change(
        session,
        actor=_actor(ctx),
        company=ctx.company,
        change_id=change_id,
        expected_version=version,
        values=values,
    )
    return await _card(session, ctx, change_id, response)


@router.get("/{company_id}/changes/{change_id}/readiness", response_model=ReadinessOut)
async def get_readiness(
    change_id: UUID,
    session: SessionDep,
    ctx: CompanyContext = require_register_read(),
) -> ReadinessOut:
    report = await changes_service.readiness_of(session, company=ctx.company, change_id=change_id)
    return ReadinessOut(
        ok=report.ok, checks=[CheckOut.model_validate(c.as_dict()) for c in report.checks]
    )


@router.post("/{company_id}/changes/{change_id}/actions/{action}", response_model=ActionOut)
async def perform_action(
    change_id: UUID,
    action: str,
    response: Response,
    session: SessionDep,
    body: ActionIn | None = None,
    ctx: CompanyContext = require_change_action(),
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> ActionOut:
    """``submit|return|approve|reject|implement|verify|rollback|cancel|consent`` (§4.2).

    ``version`` (body) or ``If-Match`` is optional, except for ``approve``: the approver
    must approve the version they have seen (428 without it, 409 when stale)."""
    payload = body or ActionIn()
    version = (
        _version(payload.version, if_match)
        if action == ChangeAction.APPROVE.value
        else _optional_version(payload.version, if_match)
    )
    result = await changes_service.perform_action(
        session,
        actor=_actor(ctx),
        company=ctx.company,
        change_id=change_id,
        action=ChangeAction(action),
        comment=payload.comment,
        expected_version=version,
    )
    outcome = result.outcome
    return ActionOut(
        action=outcome.action.value,
        from_status=outcome.from_status.value,
        to_status=outcome.to_status.value,
        performed_by_system=outcome.performed_by_system,
        warnings=[w.as_dict() for w in outcome.warnings],
        change=await _card(session, ctx, change_id, response),
    )


@router.get("/{company_id}/changes/{change_id}/audit", response_model=Page[ChangeAuditEntryOut])
async def get_change_audit(
    change_id: UUID,
    session: SessionDep,
    ctx: CompanyContext = require_register_read(),
    limit: Limit = DEFAULT_LIMIT,
    offset: Offset = 0,
) -> Page[ChangeAuditEntryOut]:
    """The audit trail of the change (and of its attachments), oldest first."""
    rows, total = await changes_service.audit_trail(
        session, ctx.company_id, change_id, limit=limit, offset=offset
    )
    items = [
        ChangeAuditEntryOut(
            seq=row.seq,
            occurred_at=row.occurred_at,
            actor_id=row.actor_id,
            actor_display=row.actor_display,
            actor_roles=list(row.actor_roles),
            ip_address=normalize_ip(row.ip_address),
            request_id=row.request_id,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            action=row.action,
            diff=row.diff,
            context=row.context,
            prev_hash=row.prev_hash,
            hash=row.hash,
            hash_valid=audit_service.entry_hash_valid(row),
        )
        for row in rows
    ]
    return Page[ChangeAuditEntryOut](items=items, total=total, limit=limit, offset=offset)


# --------------------------------------------------------------------------- comments


@router.post(
    "/{company_id}/changes/{change_id}/comments", response_model=CommentOut, status_code=201
)
async def add_comment(
    change_id: UUID,
    body: CommentIn,
    session: SessionDep,
    ctx: CompanyContext = require_company(Action.CHANGE_EDIT_DRAFT),
) -> CommentOut:
    comment = await comments_service.add_comment(
        session, actor=_actor(ctx), company=ctx.company, change_id=change_id, body=body.body
    )
    return CommentOut(
        id=comment.id,
        author=UserRef(id=ctx.user.id, display_name=ctx.user.display_name),
        body=comment.body,
        action=None,
        created_at=comment.created_at,
    )


# --------------------------------------------------------------------------- attachments


def _attachment_out(attachment: Attachment, uploader: UserRef) -> AttachmentOut:
    return AttachmentOut(
        id=attachment.id,
        change_id=attachment.change_id,
        filename=attachment.filename,
        content_type=attachment.content_type,
        size=attachment.size,
        sha256=attachment.sha256,
        uploaded_by=uploader,
        created_at=attachment.created_at,
    )


@router.get("/{company_id}/changes/{change_id}/attachments", response_model=list[AttachmentOut])
async def list_attachments(
    change_id: UUID,
    session: SessionDep,
    ctx: CompanyContext = require_register_read(),
) -> list[AttachmentOut]:
    rows = await attachments_service.list_attachments(session, ctx.company_id, change_id)
    users = await changes_service.users_by_id(session, [a.uploaded_by_id for a in rows])
    return [
        _attachment_out(a, _user(users, a.uploaded_by_id))  # type: ignore[arg-type]
        for a in rows
    ]


@router.post(
    "/{company_id}/changes/{change_id}/attachments",
    response_model=AttachmentOut,
    status_code=201,
)
async def upload_attachment(
    change_id: UUID,
    request: Request,
    response: Response,
    session: SessionDep,
    file: Annotated[UploadFile, File(description="Plik załącznika")],
    ctx: CompanyContext = require_company(Action.CHANGE_EDIT_DRAFT),
) -> AttachmentOut:
    """Multipart upload (field ``file``); a new version of a file is a new attachment."""
    settings = request.app.state.settings
    attachment = await attachments_service.add_attachment(
        session,
        actor=_actor(ctx),
        company=ctx.company,
        change_id=change_id,
        filename=file.filename,
        content_type=file.content_type,
        reader=file.read,
        storage_root=settings.storage_path,
        max_bytes=settings.attachment_max_bytes,
        allowed_types=settings.attachment_allowed_types,
    )
    response.headers["Location"] = f"{request.url.path}/{attachment.id}"
    return _attachment_out(attachment, UserRef(id=ctx.user.id, display_name=ctx.user.display_name))


@router.get("/{company_id}/changes/{change_id}/attachments/{attachment_id}")
async def download_attachment(
    change_id: UUID,
    attachment_id: UUID,
    request: Request,
    session: SessionDep,
    ctx: CompanyContext = require_company(Action.REGISTER_VIEW),
) -> FileResponse:
    """The file, always as a download (``Content-Disposition: attachment``, ``nosniff``)."""
    attachment = await attachments_service.get_attachment(
        session, ctx.company_id, change_id, attachment_id
    )
    storage_root = request.app.state.settings.storage_path
    path = attachments_service.resolve(storage_root, attachment.storage_key)
    if not path.is_file():
        raise ProblemError(
            status=500,
            code="attachment.file_missing",
            detail=(
                "Plik załącznika jest niedostępny w magazynie. Skontaktuj się z administratorem."
            ),
        )
    await attachments_service.record_download(session, actor=_actor(ctx), attachment=attachment)
    media_type = (
        attachment.content_type
        if attachment.content_type in SAFE_DOWNLOAD_TYPES
        else "application/octet-stream"
    )
    return FileResponse(
        path,
        media_type=media_type,
        filename=attachment.filename,
        content_disposition_type="attachment",
        headers={
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; sandbox",
            "X-Content-SHA256": attachment.sha256,
            "Cache-Control": "private, no-store",
        },
    )


# --------------------------------------------------------------------------- stats


@router.get("/{company_id}/stats", response_model=StatsOut)
async def get_stats(
    session: SessionDep,
    ctx: CompanyContext = require_register_read(),
) -> StatsOut:
    """Register tiles (§10.1)."""
    result = await changes_service.stats(session, ctx.company_id)
    return StatsOut(
        pending_approval=result.pending_approval,
        approved_not_implemented=result.approved_not_implemented,
        emergency_last_30_days=result.emergency_last_30_days,
        implemented_not_verified=result.implemented_not_verified,
        emergency_not_approved_in_24h=result.emergency_not_approved_in_24h,
        implemented_outside_window=result.implemented_outside_window,
        by_status=dict(result.by_status),
    )
