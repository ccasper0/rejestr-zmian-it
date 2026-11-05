"""Request/response schemas of the report exports (CLAUDE.md §8, §9; ADR 0017)."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.schemas.changes import ChangeTypeValue, StatusValue
from app.schemas.common import SafeLine, UtcDateTime

ReportKindValue = Literal["register", "change_card"]
ReportFormatValue = Literal["pdf", "csv"]
ReportStatusValue = Literal["pending", "done", "failed"]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReportFilters(_Strict):
    """The filters of the register (``GET /companies/{cid}/changes``), without the period
    (``period_from`` / ``period_to`` are top-level fields of :class:`ReportCreate`)."""

    period_by: Literal["created", "implemented"] = "created"
    status: list[StatusValue] = Field(default_factory=list, max_length=8)
    type: list[ChangeTypeValue] = Field(default_factory=list, max_length=3)
    category: list[UUID] = Field(default_factory=list, max_length=100)
    ci: list[UUID] = Field(default_factory=list, max_length=100)
    assignee: UUID | None = None
    approver: UUID | None = None  # the designated approver
    approved_by: str | None = Field(
        default=None,
        max_length=36,
        description="Kto faktycznie zatwierdził: id użytkownika albo 'system' (automatycznie)",
    )
    q: SafeLine | None = Field(default=None, max_length=200)


class ReportCreate(_Strict):
    """``POST /reports``.

    - ``kind = register``: PDF register report of one company (``company_id``) or of all
      companies where the caller is an auditor (``company_id = null``); ``period_from`` and
      ``period_to`` required (``[from, to)``);
    - ``kind = change_card``: PDF card of the change ``change_id`` of ``company_id``.
    """

    kind: ReportKindValue
    company_id: UUID | None = None
    change_id: UUID | None = None
    period_from: AwareDatetime | None = None
    period_to: AwareDatetime | None = None
    filters: ReportFilters = Field(default_factory=ReportFilters)
    include_audit_trail: bool = Field(
        default=False, description="Załącznik B: pełna ścieżka audytu każdej zmiany"
    )


class CompanyRef(BaseModel):
    id: UUID
    name: str
    prefix: str


class UserRef(BaseModel):
    id: UUID
    display_name: str


class ReportOut(BaseModel):
    id: UUID
    number: str
    kind: ReportKindValue
    format: ReportFormatValue
    status: ReportStatusValue
    company_id: UUID | None  # null = multi-company report (auditor)
    company: CompanyRef | None
    companies: list[CompanyRef]  # every company of the report
    change_id: UUID | None
    change_number: str | None
    period_from: UtcDateTime | None
    period_to: UtcDateTime | None
    filters: dict[str, Any]
    include_audit_trail: bool
    generated_by: UserRef
    created_at: UtcDateTime
    completed_at: UtcDateTime | None
    change_count: int | None
    data_sha256: str | None
    file_sha256: str | None
    size: int | None
    error: str | None
    download_url: str | None  # set when status = done
