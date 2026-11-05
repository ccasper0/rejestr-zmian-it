"""Changes: vocabulary, input facts and errors (CLAUDE.md §4.1-4.3, ADR 0012). No I/O.

The service layer loads the change and the facts it depends on (company, categories, CI,
company members) into the frozen dataclasses below, calls the pure functions from
``app.domain.readiness``, ``app.domain.state_machine`` and ``app.domain.deviations`` and
persists the result together with the audit entry. Nothing here touches a database, a
clock or the network: the current time is always the ``now`` parameter (aware, UTC).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from uuid import UUID

from app.domain.dictionaries import Risk
from app.domain.roles import Role

__all__ = [
    "APPROVER_ROLES",
    "COMMENT_MAX_LENGTH",
    "WRITER_ROLES",
    "ActorFacts",
    "CIFacts",
    "CategoryFacts",
    "ChangeAction",
    "ChangeContext",
    "ChangeData",
    "ChangeErrorCode",
    "ChangeField",
    "ChangeRuleError",
    "ChangeStatus",
    "ChangeType",
    "Check",
    "CheckLevel",
    "CompanyFacts",
    "ErrorKind",
    "MemberFacts",
    "Risk",
    "require_aware",
]


class ChangeStatus(StrEnum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    IMPLEMENTED = "implemented"
    VERIFIED = "verified"
    REJECTED = "rejected"
    ROLLED_BACK = "rolled_back"
    CANCELLED = "cancelled"

    @property
    def label_pl(self) -> str:
        return STATUS_LABELS_PL[self]


STATUS_LABELS_PL: Mapping[ChangeStatus, str] = MappingProxyType(
    {
        ChangeStatus.DRAFT: "Szkic",
        ChangeStatus.PENDING_APPROVAL: "Do zatwierdzenia",
        ChangeStatus.APPROVED: "Zatwierdzona",
        ChangeStatus.IMPLEMENTED: "Wdrożona",
        ChangeStatus.VERIFIED: "Zweryfikowana",
        ChangeStatus.REJECTED: "Odrzucona",
        ChangeStatus.ROLLED_BACK: "Wycofana",
        ChangeStatus.CANCELLED: "Anulowana",
    }
)

FROZEN_STATUSES: frozenset[ChangeStatus] = frozenset(
    {
        # §4.2: "od statusu implemented w górę" ...
        ChangeStatus.IMPLEMENTED,
        ChangeStatus.VERIFIED,
        ChangeStatus.ROLLED_BACK,
        # ... and the terminal statuses that never reached implementation (ADR 0012 §6).
        ChangeStatus.REJECTED,
        ChangeStatus.CANCELLED,
    }
)


class ChangeType(StrEnum):
    STANDARD = "standard"
    NORMAL = "normal"
    EMERGENCY = "emergency"


class ChangeAction(StrEnum):
    """``POST /companies/{cid}/changes/{id}/actions/{action}`` (CLAUDE.md §8)."""

    SUBMIT = "submit"
    RETURN = "return"
    APPROVE = "approve"
    REJECT = "reject"
    IMPLEMENT = "implement"
    VERIFY = "verify"
    ROLLBACK = "rollback"
    CANCEL = "cancel"
    CONSENT = "consent"  # CI owner consent (OT, ADR 0011 §3, ADR 0012 §5)


class ChangeField(StrEnum):
    """Fields of a change editable through ``PATCH`` (values = ``ChangeData`` attributes).

    ``requested_by_id`` is deliberately absent: it is set once to the creator and never
    edited, otherwise an approver could create a change "for" someone else and approve it
    (four-eyes bypass, ADR 0012 §4).
    """

    TITLE = "title"
    CATEGORY_ID = "category_id"
    SUBCATEGORY_ID = "subcategory_id"
    CHANGE_TYPE = "change_type"
    RISK = "risk"
    DESCRIPTION = "description"
    IMPLEMENTATION_PLAN = "implementation_plan"
    ROLLBACK_PLAN = "rollback_plan"
    IMPACT = "impact"
    REQUIREMENT_REF = "requirement_ref"
    TICKET_REF = "ticket_ref"
    ASSIGNEE_ID = "assignee_id"
    APPROVER_ID = "approver_id"
    VERIFIER_ID = "verifier_id"
    WINDOW_START = "window_start"
    WINDOW_END = "window_end"
    CI_IDS = "ci_ids"


# Roles allowed to create, edit, submit and carry out changes. Equal to
# ``PERMISSIONS[Action.CHANGE_EDIT_DRAFT]`` (asserted by tests/test_change_state_machine.py).
WRITER_ROLES: frozenset[Role] = frozenset({Role.EDITOR, Role.APPROVER})
# Roles allowed to approve / reject / return. Equal to ``PERMISSIONS[Action.CHANGE_APPROVE]``.
APPROVER_ROLES: frozenset[Role] = frozenset({Role.APPROVER})

COMMENT_MAX_LENGTH = 4000


def require_aware(value: datetime, name: str) -> datetime:
    """Domain times are aware (UTC in the database); naive values are programming errors."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be a timezone-aware datetime")
    return value


# --------------------------------------------------------------------------- input facts


@dataclass(frozen=True, slots=True)
class ChangeData:
    """The change as stored (``changes`` + ``change_items``). Optional fields may be empty
    in ``draft``; readiness (§4.3) decides what must be filled before submission."""

    id: UUID
    company_id: UUID
    status: ChangeStatus
    requested_by_id: UUID
    title: str | None = None
    category_id: UUID | None = None
    subcategory_id: UUID | None = None
    change_type: ChangeType | None = None
    risk: Risk | None = None
    description: str | None = None
    implementation_plan: str | None = None
    rollback_plan: str | None = None
    impact: str | None = None
    requirement_ref: str | None = None
    ticket_ref: str | None = None
    assignee_id: UUID | None = None
    approver_id: UUID | None = None
    verifier_id: UUID | None = None
    window_start: datetime | None = None
    window_end: datetime | None = None
    ci_ids: frozenset[UUID] = frozenset()
    implemented_at: datetime | None = None
    verified_at: datetime | None = None
    approved_at: datetime | None = None
    rejected_at: datetime | None = None
    # Who actually approved (set only by ``approve``); ``None`` with ``approved_at`` = the
    # ``system`` (standard auto-approval). ``approver_id`` is only the DESIGNATED approver.
    approved_by_id: UUID | None = None

    def __post_init__(self) -> None:
        for name in (
            "window_start",
            "window_end",
            "implemented_at",
            "verified_at",
            "approved_at",
            "rejected_at",
        ):
            value = getattr(self, name)
            if value is not None:
                require_aware(value, name)


@dataclass(frozen=True, slots=True)
class ActorFacts:
    """The authenticated user acting on a change and their roles **in the change's company**
    (``company_memberships``). ``app_admin`` is not a membership role and gives no rights
    on changes (§5, ADR 0007) - pass only membership roles."""

    user_id: UUID
    roles: frozenset[Role] = frozenset()


@dataclass(frozen=True, slots=True)
class MemberFacts:
    """A company member: active flag of the user and their roles in the company."""

    is_active: bool
    roles: frozenset[Role]

    def has_any(self, roles: frozenset[Role]) -> bool:
        return self.is_active and bool(self.roles & roles)


@dataclass(frozen=True, slots=True)
class CompanyFacts:
    id: UUID
    is_ksc_entity: bool = False
    is_archived: bool = False


@dataclass(frozen=True, slots=True)
class CategoryFacts:
    """A ``change_categories`` row. ``available_in_company`` matters only for top-level
    categories (``company_categories``; subcategories come with their category, ADR 0011)."""

    id: UUID
    parent_id: UUID | None
    is_active: bool
    requires_approval: bool
    requires_ci_owner_consent: bool = False
    available_in_company: bool = False


@dataclass(frozen=True, slots=True)
class CIFacts:
    id: UUID
    company_id: UUID
    is_active: bool
    identifier: str
    owner_user_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class ChangeContext:
    """Facts a rule may need besides the change itself.

    - ``categories``: rows for ``change.category_id`` and ``change.subcategory_id`` (missing
      = not found);
    - ``cis``: rows for ``change.ci_ids`` visible in the company (missing = not found or
      another company - RLS hides it);
    - ``members``: **all** members of the company with at least one role (user id -> facts);
      used for eligibility of the assignee/approver/verifier/CI owners and for the
      "only one person in the company" verification exception;
    - ``consented_ci_ids``: CI of this change whose owner consented in the current approval
      round (ADR 0012 §5).
    """

    company: CompanyFacts
    categories: Mapping[UUID, CategoryFacts] = field(default_factory=dict)
    cis: Mapping[UUID, CIFacts] = field(default_factory=dict)
    members: Mapping[UUID, MemberFacts] = field(default_factory=dict)
    consented_ci_ids: frozenset[UUID] = frozenset()

    def member(self, user_id: UUID | None) -> MemberFacts | None:
        return None if user_id is None else self.members.get(user_id)

    def is_member_with(self, user_id: UUID | None, roles: frozenset[Role]) -> bool:
        facts = self.member(user_id)
        return facts is not None and facts.has_any(roles)


# --------------------------------------------------------------------------- checks


class CheckLevel(StrEnum):
    OK = "ok"
    WARNING = "warning"  # satisfied, but worth showing / recording in the audit context
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class Check:
    """One readiness rule: ``{code, ok, level, message_pl, field}`` (``GET /readiness``)."""

    code: str
    level: CheckLevel
    message_pl: str
    field: str | None = None

    @property
    def ok(self) -> bool:
        return self.level is not CheckLevel.ERROR

    def as_dict(self) -> dict[str, str | bool | None]:
        return {
            "code": self.code,
            "ok": self.ok,
            "level": self.level.value,
            "message_pl": self.message_pl,
            "field": self.field,
        }


# --------------------------------------------------------------------------- errors


class ErrorKind(StrEnum):
    """How the service maps a domain error to HTTP: 403 / 409 / 422."""

    FORBIDDEN = "forbidden"
    CONFLICT = "conflict"
    VALIDATION = "validation"


class ChangeErrorCode(StrEnum):
    INVALID_TRANSITION = "change.invalid_transition"
    FORBIDDEN_ACTOR = "change.forbidden_actor"
    FOUR_EYES_VIOLATION = "change.four_eyes_violation"
    VERIFIER_IS_ASSIGNEE = "change.verifier_is_assignee"
    APPROVAL_MISSING = "change.approval_missing"
    COMMENT_REQUIRED = "change.comment_required"
    COMMENT_TOO_LONG = "change.comment_too_long"
    NOT_READY = "change.not_ready"
    CI_OWNER_CONSENT_MISSING = "change.ci_owner_consent_missing"
    FROZEN = "change.frozen"
    FIELD_NOT_EDITABLE = "change.field_not_editable"
    INVALID_EDIT = "change.invalid_edit"
    COMPANY_ARCHIVED = "company.archived"

    @property
    def kind(self) -> ErrorKind:
        return _ERROR_KINDS[self]

    @property
    def default_message_pl(self) -> str:
        return _ERROR_MESSAGES[self]


_ERROR_KINDS: Mapping[ChangeErrorCode, ErrorKind] = MappingProxyType(
    {
        ChangeErrorCode.INVALID_TRANSITION: ErrorKind.CONFLICT,
        ChangeErrorCode.FORBIDDEN_ACTOR: ErrorKind.FORBIDDEN,
        ChangeErrorCode.FOUR_EYES_VIOLATION: ErrorKind.FORBIDDEN,
        ChangeErrorCode.VERIFIER_IS_ASSIGNEE: ErrorKind.FORBIDDEN,
        ChangeErrorCode.APPROVAL_MISSING: ErrorKind.CONFLICT,
        ChangeErrorCode.COMMENT_REQUIRED: ErrorKind.VALIDATION,
        ChangeErrorCode.COMMENT_TOO_LONG: ErrorKind.VALIDATION,
        ChangeErrorCode.NOT_READY: ErrorKind.VALIDATION,
        ChangeErrorCode.CI_OWNER_CONSENT_MISSING: ErrorKind.CONFLICT,
        ChangeErrorCode.FROZEN: ErrorKind.CONFLICT,
        ChangeErrorCode.FIELD_NOT_EDITABLE: ErrorKind.VALIDATION,
        ChangeErrorCode.INVALID_EDIT: ErrorKind.VALIDATION,
        ChangeErrorCode.COMPANY_ARCHIVED: ErrorKind.CONFLICT,
    }
)

_ERROR_MESSAGES: Mapping[ChangeErrorCode, str] = MappingProxyType(
    {
        ChangeErrorCode.INVALID_TRANSITION: (
            "Tej akcji nie można wykonać w bieżącym statusie zmiany."
        ),
        ChangeErrorCode.FORBIDDEN_ACTOR: "Nie możesz wykonać tej akcji dla tej zmiany.",
        ChangeErrorCode.FOUR_EYES_VIOLATION: (
            "Zasada czterech oczu: zatwierdzający nie może być zgłaszającym ani wykonawcą zmiany."
        ),
        ChangeErrorCode.VERIFIER_IS_ASSIGNEE: (
            "Weryfikujący nie może być wykonawcą zmiany, gdy w spółce jest inna osoba, "
            "która może ją zweryfikować."
        ),
        ChangeErrorCode.APPROVAL_MISSING: (
            "Zmiana awaryjna musi zostać zatwierdzona po fakcie przed weryfikacją."
        ),
        ChangeErrorCode.COMMENT_REQUIRED: "Ta akcja wymaga komentarza.",
        ChangeErrorCode.COMMENT_TOO_LONG: (
            f"Komentarz może mieć najwyżej {COMMENT_MAX_LENGTH} znaków."
        ),
        ChangeErrorCode.NOT_READY: (
            "Zmiana nie spełnia warunków wysłania. Popraw pozycje oznaczone w kontroli "
            "przed wysłaniem."
        ),
        ChangeErrorCode.CI_OWNER_CONSENT_MISSING: (
            "Brak zgody właściciela obiektu (CI) wymaganej dla tej kategorii zmian."
        ),
        ChangeErrorCode.FROZEN: (
            "Zmiana jest zamrożona i nie można jej edytować. Korektę wprowadź jako nową "
            "zmianę wskazującą na tę zmianę."
        ),
        ChangeErrorCode.FIELD_NOT_EDITABLE: "Tego pola nie można edytować w bieżącym statusie.",
        ChangeErrorCode.INVALID_EDIT: "Wprowadzone wartości są nieprawidłowe.",
        ChangeErrorCode.COMPANY_ARCHIVED: (
            "Spółka jest zarchiwizowana. Zmian nie można tworzyć ani modyfikować."
        ),
    }
)


class ChangeRuleError(Exception):
    """A domain rule rejected the operation.

    The service maps it to problem+json: ``code`` -> ``code``, ``message_pl`` -> ``detail``,
    ``code.kind`` -> HTTP status (403 / 409 / 422), ``fields`` and ``checks`` -> extension
    members.
    """

    def __init__(
        self,
        code: ChangeErrorCode,
        message_pl: str | None = None,
        *,
        fields: tuple[str, ...] = (),
        checks: tuple[Check, ...] = (),
    ) -> None:
        self.code = code
        self.message_pl = message_pl or code.default_message_pl
        self.fields = fields
        self.checks = checks
        super().__init__(f"{code.value}: {self.message_pl}")

    @property
    def kind(self) -> ErrorKind:
        return self.code.kind
