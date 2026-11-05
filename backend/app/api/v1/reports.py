"""Report exports (CLAUDE.md §8, §9; ADR 0017).

- ``POST /reports`` - PDF register report (one company or all companies of an auditor) or
  PDF change card; 201 when generated in the request, 202 when the worker generates it
  (more than ``REPORT_ASYNC_THRESHOLD`` changes) - then poll ``GET /reports/{id}``;
- ``GET /reports`` - the list of the screen "Raporty i eksport";
- ``GET /reports/{id}`` - status; ``GET /reports/{id}/download`` - the file (audited);
- ``GET /companies/{cid}/changes/export.csv`` - the register as CSV (same filters as the
  register list; numbered, stored and audited like every export).

Permissions: ``app.permissions.require_report_order`` / ``require_report_list`` /
``require_report`` and ``require_register_export`` (CSV).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Annotated, Any, Literal
from uuid import UUID

from fastapi import APIRouter, Query, Request, Response
from pydantic import AwareDatetime

from app.auth.principal import (
    CompanyContext,
    CurrentUser,
    ReportAccess,
    ReportListing,
    ReportOrder,
)
from app.db import SessionDep, get_database
from app.domain.changes import ChangeStatus, ChangeType
from app.domain.reports import ReportKind, ReportStatus
from app.errors import ProblemError
from app.models import Company, ReportExport, User
from app.permissions import (
    require_register_export,
    require_report,
    require_report_list,
    require_report_order,
)
from app.schemas.common import DEFAULT_LIMIT, MAX_LIMIT, Page, SafeLine
from app.schemas.reports import CompanyRef, ReportCreate, ReportFilters, ReportOut, UserRef
from app.services import changes as changes_service
from app.services import reports as reports_service

router = APIRouter(prefix="/reports", tags=["reports"])
# Declared BEFORE the changes router (app.api.v1.__init__): ``/changes/export.csv`` must
# not be matched by ``/changes/{change_id}`` (ADR 0013 §7).
company_router = APIRouter(prefix="/companies", tags=["reports"])

Limit = Annotated[int, Query(ge=1, le=MAX_LIMIT)]
Offset = Annotated[int, Query(ge=0)]

DOWNLOAD_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Cache-Control": "private, no-store",
}


def exporter(user: CurrentUser) -> reports_service.Exporter:
    return reports_service.Exporter(
        user_id=user.id,
        display_name=user.display_name,
        roles_by_company={
            cid: frozenset(r.value for r in roles) for cid, roles in user.memberships.items()
        },
        is_app_admin=user.is_app_admin,
    )


def options(request: Request) -> reports_service.ReportOptions:
    settings = request.app.state.settings
    return reports_service.ReportOptions(
        storage_root=settings.storage_path,
        async_threshold=settings.report_async_threshold,
        max_changes=settings.report_max_changes,
    )


def _approved_by(value: str | None) -> tuple[UUID | None, bool]:
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


def change_filters(
    filters: ReportFilters, period_from: Any, period_to: Any
) -> changes_service.ChangeFilters:
    approved_by_id, approved_by_system = _approved_by(filters.approved_by)
    return changes_service.ChangeFilters(
        period_from=period_from,
        period_to=period_to,
        period_by=filters.period_by,
        statuses=tuple(ChangeStatus(s) for s in filters.status),
        types=tuple(ChangeType(t) for t in filters.type),
        categories=tuple(filters.category),
        cis=tuple(filters.ci),
        assignee_id=filters.assignee,
        approver_id=filters.approver,
        approved_by_id=approved_by_id,
        approved_by_system=approved_by_system,
        q=filters.q,
    )


def _company_ref(company: Company | None) -> CompanyRef | None:
    if company is None:
        return None
    return CompanyRef(id=company.id, name=company.name, prefix=company.prefix)


def report_out(
    report: ReportExport,
    companies: Mapping[UUID, Company],
    users: Mapping[UUID, User],
    change_numbers: Mapping[UUID, str],
) -> ReportOut:
    author = users.get(report.generated_by_id)
    scope = [companies[c] for c in report.scope_company_ids if c in companies]
    return ReportOut(
        id=report.id,
        number=report.number,
        kind=report.kind,
        format=report.format,
        status=report.status,
        company_id=report.company_id,
        company=_company_ref(companies.get(report.company_id)) if report.company_id else None,
        companies=[
            CompanyRef(id=c.id, name=c.name, prefix=c.prefix)
            for c in sorted(scope, key=lambda c: c.prefix)
        ],
        change_id=report.change_id,
        change_number=change_numbers.get(report.change_id) if report.change_id else None,
        period_from=report.period_from,
        period_to=report.period_to,
        filters=report.filters,
        include_audit_trail=report.include_audit_trail,
        generated_by=UserRef(
            id=report.generated_by_id,
            display_name=author.display_name if author else str(report.generated_by_id),
        ),
        created_at=report.created_at,
        completed_at=report.completed_at,
        change_count=report.change_count,
        data_sha256=report.data_sha256,
        file_sha256=report.file_sha256,
        size=report.size,
        error=report.error,
        download_url=(
            f"/api/v1/reports/{report.id}/download"
            if report.status == ReportStatus.DONE.value
            else None
        ),
    )


async def _out(session: SessionDep, report: ReportExport) -> ReportOut:
    companies, users, numbers = await reports_service.describe(session, [report])
    return report_out(report, companies, users, numbers)


# --------------------------------------------------------------------------- /reports


@router.post(
    "",
    response_model=ReportOut,
    status_code=201,
    responses={202: {"model": ReportOut, "description": "Raport generowany w tle (pending)"}},
)
async def create_report(
    request: Request,
    response: Response,
    session: SessionDep,
    order: ReportOrder = require_report_order(),
) -> ReportOut:
    """Generate a PDF report (register or change card)."""
    body: ReportCreate = order.body
    queue = request.app.state.report_queue
    report = await reports_service.create_report(
        session,
        request=reports_service.ReportRequest(
            kind=ReportKind(body.kind),
            company=order.company,
            companies=order.companies,
            filters=change_filters(body.filters, body.period_from, body.period_to),
            change_id=body.change_id,
            include_audit_trail=body.include_audit_trail,
            admin_path=order.admin_path,
        ),
        exporter=exporter(order.user),
        options=options(request),
        renderer=request.app.state.pdf_renderer,
        enqueue=queue.enqueue,
        failure_db=get_database(request),
    )
    if report.status == ReportStatus.PENDING.value:
        response.status_code = 202
    response.headers["Location"] = f"{request.url.path}/{report.id}"
    return await _out(session, report)


@router.get("", response_model=Page[ReportOut])
async def list_reports(
    session: SessionDep,
    listing: ReportListing = require_report_list(),
    kind: ReportKind | None = None,
    status: ReportStatus | None = None,
    limit: Limit = DEFAULT_LIMIT,
    offset: Offset = 0,
) -> Page[ReportOut]:
    """Reports the user may see, newest first (``company_id`` - one company)."""
    page = await reports_service.list_reports(
        session,
        reports_service.ReportVisibility(
            all_rows=listing.all_rows,
            register_company_ids=listing.register_company_ids,
            card_company_ids=listing.card_company_ids,
            user_id=None if listing.all_rows else listing.user.id,
        ),
        company_id=listing.company_id,
        kind=kind,
        status=status,
        limit=limit,
        offset=offset,
    )
    return Page[ReportOut](
        items=[report_out(r, page.companies, page.users, page.change_numbers) for r in page.rows],
        total=page.total,
        limit=limit,
        offset=offset,
    )


@router.get("/{report_id}", response_model=ReportOut)
async def get_report(
    session: SessionDep,
    access: ReportAccess = require_report(download=False),
) -> ReportOut:
    """Status of a report (``pending`` -> ``done`` | ``failed``)."""
    return await _out(session, access.report)


@router.get("/{report_id}/download")
async def download_report(
    request: Request,
    session: SessionDep,
    access: ReportAccess = require_report(download=True),
) -> Response:
    """The file (PDF or CSV) as a download; recorded in the audit log before it is sent.

    The response carries exactly the bytes whose sha256 was verified (read once - no
    second read of a file that could have been replaced in between)."""
    report = access.report
    content = await reports_service.download(
        session,
        report,
        exporter=exporter(access.user),
        storage_root=request.app.state.settings.storage_path,
        db=get_database(request),
        extra={"admin_path": True} if access.admin_path else None,
    )
    return Response(
        content=content,
        media_type=reports_service.media_type(report),
        headers={
            **DOWNLOAD_HEADERS,
            "Content-Disposition": f'attachment; filename="{reports_service.filename(report)}"',
            "X-Report-Number": report.number,
            "X-Data-SHA256": report.data_sha256 or "",
            "X-Content-SHA256": report.file_sha256 or "",
        },
    )


# --------------------------------------------------------------------------- CSV


@company_router.get("/{company_id}/changes/export.csv")
async def export_register_csv(
    request: Request,
    session: SessionDep,
    ctx: CompanyContext = require_register_export(),
    period_from: Annotated[
        AwareDatetime | None, Query(description="Od (włącznie), ISO 8601 ze strefą")
    ] = None,
    period_to: Annotated[
        AwareDatetime | None, Query(description="Do (wyłącznie), ISO 8601 ze strefą")
    ] = None,
    period_by: Literal["created", "implemented"] = "created",
    status: Annotated[list[ChangeStatus] | None, Query(max_length=8)] = None,
    type: Annotated[list[ChangeType] | None, Query(max_length=3)] = None,
    category: Annotated[list[UUID] | None, Query(max_length=100)] = None,
    ci: Annotated[list[UUID] | None, Query(max_length=100)] = None,
    assignee: UUID | None = None,
    approver: Annotated[UUID | None, Query(description="Wskazany zatwierdzający")] = None,
    approved_by: Annotated[str | None, Query(max_length=36)] = None,
    q: Annotated[SafeLine | None, Query(max_length=200)] = None,
) -> Response:
    """The register as CSV (UTF-8 with BOM, ``;``, dates Europe/Warsaw; ADR 0017 §7) with
    the filters of ``GET /companies/{cid}/changes``."""
    approved_by_id, approved_by_system = _approved_by(approved_by)
    filters = changes_service.ChangeFilters(
        period_from=period_from,
        period_to=period_to,
        period_by=period_by,
        statuses=tuple(status or ()),
        types=tuple(type or ()),
        categories=tuple(category or ()),
        cis=tuple(ci or ()),
        assignee_id=assignee,
        approver_id=approver,
        approved_by_id=approved_by_id,
        approved_by_system=approved_by_system,
        q=q,
    )
    report, content = await reports_service.export_csv(
        session,
        company=ctx.company,
        filters=filters,
        exporter=exporter(ctx.user),
        options=options(request),
        admin_path=ctx.admin_path,
        failure_db=get_database(request),
    )
    filename = reports_service.filename(report)
    return Response(
        content=content,
        media_type=reports_service.CSV_MEDIA_TYPE,
        headers={
            **DOWNLOAD_HEADERS,
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Report-Id": str(report.id),
            "X-Report-Number": report.number,
            "X-Data-SHA256": report.data_sha256 or "",
            "X-Content-SHA256": report.file_sha256 or "",
        },
    )
