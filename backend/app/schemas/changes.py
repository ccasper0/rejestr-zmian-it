"""Request/response schemas of changes, comments, attachments and register tiles (§8)."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.schemas.common import SafeLine, SafeStr, UtcDateTime

ChangeTypeValue = Literal["standard", "normal", "emergency"]
RiskValue = Literal["low", "medium", "high"]
StatusValue = Literal[
    "draft",
    "pending_approval",
    "approved",
    "implemented",
    "verified",
    "rejected",
    "rolled_back",
    "cancelled",
]
ActionValue = Literal[
    "submit", "return", "approve", "reject", "implement", "verify", "rollback", "cancel", "consent"
]

TITLE_MAX = 500
TEXT_MAX = 20_000
REF_MAX = 500
MAX_CI = 200


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _ChangeFields(_Strict):
    """Editable fields (``app.domain.changes.ChangeField``); a draft may leave them empty."""

    title: SafeLine | None = Field(default=None, max_length=TITLE_MAX)
    category_id: UUID | None = None
    subcategory_id: UUID | None = None
    change_type: ChangeTypeValue | None = None
    risk: RiskValue | None = None
    description: SafeStr | None = Field(default=None, max_length=TEXT_MAX)
    implementation_plan: SafeStr | None = Field(default=None, max_length=TEXT_MAX)
    rollback_plan: SafeStr | None = Field(default=None, max_length=TEXT_MAX)
    impact: SafeStr | None = Field(default=None, max_length=TEXT_MAX)
    requirement_ref: SafeLine | None = Field(default=None, max_length=REF_MAX)
    ticket_ref: SafeLine | None = Field(default=None, max_length=REF_MAX)
    assignee_id: UUID | None = None
    approver_id: UUID | None = None
    verifier_id: UUID | None = None
    window_start: AwareDatetime | None = None
    window_end: AwareDatetime | None = None
    ci_ids: list[UUID] | None = Field(default=None, max_length=MAX_CI)


class ChangeCreate(_ChangeFields):
    """A new draft; a missing ``approver_id`` is filled with the default approver (§4.3)."""

    supersedes_change_id: UUID | None = Field(
        default=None, description="Korekta zamrożonej zmiany: wskazuje oryginał (§4.2)"
    )


class ChangeUpdate(_ChangeFields):
    """Only provided fields change. ``version`` (or the ``If-Match`` header) is required."""

    version: int | None = Field(default=None, ge=1)


class ActionIn(_Strict):
    comment: SafeStr | None = Field(default=None, max_length=10_000)
    version: int | None = Field(default=None, ge=1)


class CommentIn(_Strict):
    body: SafeStr = Field(max_length=10_000)


class UserRef(BaseModel):
    id: UUID
    display_name: str


class CategoryRef(BaseModel):
    id: UUID
    code: str
    name: str


class ChangeCiOut(BaseModel):
    """A CI of the change: ``identifier`` / ``name`` are the snapshot once implemented."""

    id: UUID
    identifier: str
    name: str
    ci_type_code: str
    is_active: bool
    snapshot: bool
    current_identifier: str
    current_name: str
    owner: UserRef | None
    consented: bool


class DeviationOut(BaseModel):
    kind: str
    critical: bool
    message_pl: str


class ConsentOut(BaseModel):
    """A consent of the current round; ``valid`` = given by the CI's current owner."""

    ci_id: UUID
    owner: UserRef
    consented_at: UtcDateTime
    valid: bool
    by_requester_or_assignee: bool


class CommentOut(BaseModel):
    id: UUID
    author: UserRef
    body: str
    action: ActionValue | None
    created_at: UtcDateTime


class LinkedChangeOut(BaseModel):
    """A correction of the change (``supersedes_change_id`` pointing to it, ADR 0021)."""

    id: UUID
    number: str
    status: StatusValue


class ChangeSummaryOut(BaseModel):
    """A row of the register (``GET /companies/{cid}/changes``)."""

    id: UUID
    company_id: UUID
    number: str
    title: str | None
    status: StatusValue
    change_type: ChangeTypeValue | None
    risk: RiskValue | None
    category: CategoryRef | None
    subcategory: CategoryRef | None
    ci: list[ChangeCiOut]
    requested_by: UserRef
    assignee: UserRef | None
    approver: UserRef | None
    verifier: UserRef | None
    window_start: UtcDateTime | None
    window_end: UtcDateTime | None
    approved_at: UtcDateTime | None
    # Who approved: the approve action's actor; ``auto_approved`` = approved by ``system``
    # (standard change, ``approved_by`` null). ``approver`` is only the designated one.
    approved_by: UserRef | None
    auto_approved: bool
    implemented_at: UtcDateTime | None
    verified_at: UtcDateTime | None
    rejected_at: UtcDateTime | None
    deviations: list[DeviationOut]
    created_at: UtcDateTime
    updated_at: UtcDateTime


class ChangeOut(ChangeSummaryOut):
    """The change card: all fields, what the caller may do now and the comments."""

    description: str | None
    implementation_plan: str | None
    rollback_plan: str | None
    impact: str | None
    requirement_ref: str | None
    ticket_ref: str | None
    supersedes_change_id: UUID | None
    # Read-only correction links (ADR 0021): the original's number and the corrections
    # of this change (same company, oldest first).
    supersedes_number: str | None
    superseded_by: list[LinkedChangeOut]
    version: int
    allowed_actions: list[ActionValue]
    editable_fields: list[str]
    # How the caller reads the card: "member" (by their roles in the company) or
    # "admin_read_only" (app admin without a role, narrow read path, ADR 0016: no actions,
    # no edits, no attachment download).
    access: Literal["member", "admin_read_only"]
    suggested_approver_id: UUID | None
    consents: list[ConsentOut]
    comments: list[CommentOut]


class CheckOut(BaseModel):
    code: str
    ok: bool
    level: Literal["ok", "warning", "error"]
    message_pl: str
    field: str | None


class ReadinessOut(BaseModel):
    """``GET .../readiness``: the §4.3 checks (panel "Kontrola przed wysłaniem")."""

    ok: bool
    checks: list[CheckOut]


class ActionOut(BaseModel):
    action: ActionValue
    from_status: StatusValue
    to_status: StatusValue
    performed_by_system: bool
    warnings: list[dict[str, Any]]
    change: ChangeOut


class AttachmentOut(BaseModel):
    id: UUID
    change_id: UUID
    filename: str
    content_type: str
    size: int
    sha256: str
    uploaded_by: UserRef
    created_at: UtcDateTime


class StatsOut(BaseModel):
    """Register tiles (§10.1)."""

    pending_approval: int
    approved_not_implemented: int
    emergency_last_30_days: int
    implemented_not_verified: int
    emergency_not_approved_in_24h: int
    implemented_outside_window: int
    by_status: dict[str, int]


class ChangeAuditEntryOut(BaseModel):
    """An entry of the change's audit trail (``hash_valid``: the entry's own hash
    recomputed from its stored content; the whole chain: ``POST /audit/verify``)."""

    seq: int
    occurred_at: UtcDateTime
    actor_id: UUID | None
    actor_display: str
    actor_roles: list[str]
    ip_address: str | None
    request_id: UUID
    entity_type: str
    entity_id: UUID | None
    action: str
    diff: dict[str, Any]
    context: dict[str, Any]
    prev_hash: str
    hash: str
    hash_valid: bool
