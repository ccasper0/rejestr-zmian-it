"""Changes: create, edit, readiness, actions, register, stats (CLAUDE.md 4.1-4.3, 8).

The service loads the facts, calls the pure domain (``app.domain.readiness``,
``app.domain.state_machine``, ``app.domain.deviations``) and persists the outcome together
with the audit entry in the SAME transaction (chain of the change's company). No rule of
§4.2/§4.3 is re-implemented here: who may do what, which fields are editable and what a
change needs before submission is decided only by the domain (ADR 0012, ADR 0013).

Every query filters by ``company_id`` explicitly (RLS is the second line of defence); a
change of another company is ``404 change.not_found``, exactly like a missing one.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any, Literal, cast
from uuid import UUID, uuid4

from sqlalchemy import ColumnElement, Select, delete, exists, func, or_, select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.audit import Actor, AuditAction, EntityType, make_diff
from app.domain.changes import (
    ActorFacts,
    CategoryFacts,
    ChangeAction,
    ChangeContext,
    ChangeData,
    ChangeErrorCode,
    ChangeField,
    ChangeRuleError,
    ChangeStatus,
    ChangeType,
    CIFacts,
    CompanyFacts,
    ErrorKind,
    MemberFacts,
    Risk,
)
from app.domain.companies import CompanyStatus
from app.domain.deviations import (
    Deviation,
    deviations,
    emergency_approval_overdue,
    implemented_outside_window,
)
from app.domain.readiness import ReadinessReport, default_approver_id, readiness
from app.domain.roles import Role
from app.domain.state_machine import (
    TransitionOutcome,
    allowed_actions,
    check_edit,
    editable_fields,
    execute,
)
from app.errors import ProblemError
from app.models import (
    Attachment,
    AuditLog,
    Change,
    ChangeCategory,
    ChangeCiConsent,
    ChangeComment,
    ChangeItem,
    CiType,
    Company,
    CompanyCategory,
    CompanyMembership,
    ConfigurationItem,
    User,
)
from app.services import audit, numbering

__all__ = [
    "ChangeActor",
    "ChangeFilters",
    "ChangeStats",
    "ChangeView",
    "SortKey",
    "count_changes",
    "create_change",
    "db_now",
    "get_change_view",
    "list_changes",
    "perform_action",
    "readiness_of",
    "rule_problem",
    "stats",
    "update_change",
]

_ARCHIVED_MARKER = "company_archived:"  # trigger company_must_be_active (migration 0007)
_WINDOW_CHECK = "ck_changes_window_order"
_CHANGE_ACTION_SETTING = "app.change_action"  # migration 0008: the action path
EMERGENCY_TILE_DAYS = 30

# Fields of a change recorded in the audit diff besides the editable ones.
_LIFECYCLE = (
    "status",
    "approved_at",
    "approved_by_id",
    "implemented_at",
    "verified_at",
    "rejected_at",
)


# --------------------------------------------------------------------------- actor, errors


@dataclass(frozen=True, slots=True)
class ChangeActor:
    """The user acting on a change: the audit actor and the MEMBERSHIP roles in the
    change's company (``app_admin`` gives no rights on changes, §5 / ADR 0007)."""

    audit: Actor
    user_id: UUID
    roles: frozenset[Role]

    @property
    def facts(self) -> ActorFacts:
        return ActorFacts(self.user_id, frozenset(r for r in self.roles if r != Role.APP_ADMIN))


_KIND_STATUS: Mapping[ErrorKind, int] = {
    ErrorKind.FORBIDDEN: 403,
    ErrorKind.CONFLICT: 409,
    ErrorKind.VALIDATION: 422,
}


def rule_problem(error: ChangeRuleError) -> ProblemError:
    """Domain error -> problem+json (``code.kind`` -> 403 / 409 / 422, ADR 0012 §8)."""
    extra: dict[str, object] = {}
    if error.fields:
        extra["fields"] = list(error.fields)
    if error.checks:
        extra["checks"] = [c.as_dict() for c in error.checks]
    return ProblemError(
        status=_KIND_STATUS[error.kind], code=error.code.value, detail=error.message_pl, extra=extra
    )


def not_found() -> ProblemError:
    return ProblemError(status=404, code="change.not_found", detail="Nie znaleziono zmiany.")


def _unprocessable(code: str, detail: str, *fields: str) -> ProblemError:
    return ProblemError(status=422, code=code, detail=detail, extra={"fields": list(fields)})


def company_archived() -> ProblemError:
    return rule_problem(ChangeRuleError(ChangeErrorCode.COMPANY_ARCHIVED))


def _version_conflict(current: int) -> ProblemError:
    return ProblemError(
        status=409,
        code="change.version_conflict",
        detail=(
            "Zmiana została w międzyczasie zmodyfikowana przez kogoś innego. Odśwież kartę "
            "zmiany i wprowadź poprawki ponownie."
        ),
        extra={"current_version": current},
    )


async def db_now(session: AsyncSession) -> datetime:
    """The database clock (transaction start, UTC): one time source for every instance."""
    value: datetime = (await session.execute(select(func.now()))).scalar_one()
    return value


async def flush_guarded(session: AsyncSession) -> None:
    """Flush in a savepoint; database guards become problems instead of 500s."""
    try:
        async with session.begin_nested():
            await session.flush()
    except IntegrityError as exc:
        message = str(exc.orig)
        if _ARCHIVED_MARKER in message:
            # Archived concurrently, after the (lock-free) check (trigger, migration 0007).
            raise company_archived() from exc
        if _WINDOW_CHECK in message:
            raise _unprocessable(
                "change.invalid_window",
                "Początek okna serwisowego musi być wcześniejszy niż jego koniec.",
                "window_start",
                "window_end",
            ) from exc
        raise


# --------------------------------------------------------------------------- facts


async def _ci_ids(session: AsyncSession, change: Change) -> frozenset[UUID]:
    rows = await session.execute(
        select(ChangeItem.ci_id).where(
            ChangeItem.company_id == change.company_id, ChangeItem.change_id == change.id
        )
    )
    return frozenset(rows.scalars().all())


def to_data(change: Change, ci_ids: Collection[UUID]) -> ChangeData:
    return ChangeData(
        id=change.id,
        company_id=change.company_id,
        status=ChangeStatus(change.status),
        requested_by_id=change.requested_by_id,
        title=change.title,
        category_id=change.category_id,
        subcategory_id=change.subcategory_id,
        change_type=ChangeType(change.change_type) if change.change_type else None,
        risk=Risk(change.risk) if change.risk else None,
        description=change.description,
        implementation_plan=change.implementation_plan,
        rollback_plan=change.rollback_plan,
        impact=change.impact,
        requirement_ref=change.requirement_ref,
        ticket_ref=change.ticket_ref,
        assignee_id=change.assignee_id,
        approver_id=change.approver_id,
        verifier_id=change.verifier_id,
        window_start=change.window_start,
        window_end=change.window_end,
        ci_ids=frozenset(ci_ids),
        implemented_at=change.implemented_at,
        verified_at=change.verified_at,
        approved_at=change.approved_at,
        rejected_at=change.rejected_at,
        approved_by_id=change.approved_by_id,
    )


async def _members(session: AsyncSession, company_id: UUID) -> dict[UUID, MemberFacts]:
    rows = await session.execute(
        select(CompanyMembership.user_id, CompanyMembership.role, User.is_active)
        .join(User, User.id == CompanyMembership.user_id)
        .where(CompanyMembership.company_id == company_id)
    )
    roles: dict[UUID, set[Role]] = defaultdict(set)
    active: dict[UUID, bool] = {}
    for user_id, role, is_active in rows.all():
        roles[user_id].add(Role(role))
        active[user_id] = bool(is_active)
    return {uid: MemberFacts(is_active=active[uid], roles=frozenset(r)) for uid, r in roles.items()}


async def _consented(session: AsyncSession, change: Change) -> frozenset[UUID]:
    """CI with a consent of the current round given by the CURRENT owner of the CI.

    A consent of a former owner does not count (ADR 0013 §5): if the owner changes after
    a consent, the new owner has to consent again.
    """
    rows = await session.execute(
        select(ChangeCiConsent.ci_id)
        .join(
            ConfigurationItem,
            (ConfigurationItem.id == ChangeCiConsent.ci_id)
            & (ConfigurationItem.company_id == ChangeCiConsent.company_id),
        )
        .where(
            ChangeCiConsent.company_id == change.company_id,
            ChangeCiConsent.change_id == change.id,
            ChangeCiConsent.consent_round == change.consent_round,
            ChangeCiConsent.owner_user_id == ConfigurationItem.owner_user_id,
        )
    )
    return frozenset(rows.scalars().all())


async def _category_facts(
    session: AsyncSession, company_id: UUID, ids: Collection[UUID]
) -> dict[UUID, CategoryFacts]:
    if not ids:
        return {}
    categories = (
        (await session.execute(select(ChangeCategory).where(ChangeCategory.id.in_(list(ids)))))
        .scalars()
        .all()
    )
    available = set(
        (
            await session.execute(
                select(CompanyCategory.category_id).where(
                    CompanyCategory.company_id == company_id,
                    CompanyCategory.category_id.in_(list(ids)),
                )
            )
        )
        .scalars()
        .all()
    )
    return {
        c.id: CategoryFacts(
            id=c.id,
            parent_id=c.parent_id,
            is_active=c.is_active,
            requires_approval=c.requires_approval,
            requires_ci_owner_consent=c.requires_ci_owner_consent,
            available_in_company=c.id in available,
        )
        for c in categories
    }


async def _ci_facts(
    session: AsyncSession, company_id: UUID, ids: Collection[UUID]
) -> dict[UUID, CIFacts]:
    if not ids:
        return {}
    rows = (
        (
            await session.execute(
                select(ConfigurationItem).where(
                    ConfigurationItem.company_id == company_id,
                    ConfigurationItem.id.in_(list(ids)),
                )
            )
        )
        .scalars()
        .all()
    )
    return {
        ci.id: CIFacts(
            id=ci.id,
            company_id=ci.company_id,
            is_active=ci.is_active,
            identifier=ci.identifier,
            owner_user_id=ci.owner_user_id,
        )
        for ci in rows
    }


def company_facts(company: Company) -> CompanyFacts:
    return CompanyFacts(
        id=company.id,
        is_ksc_entity=company.is_ksc_entity,
        is_archived=company.status == CompanyStatus.ARCHIVED,
    )


async def load_context(
    session: AsyncSession,
    company: Company,
    data: ChangeData,
    *,
    change: Change | None = None,
) -> ChangeContext:
    """Facts of ``data`` (categories, CI, all members, current consent round)."""
    category_ids = {i for i in (data.category_id, data.subcategory_id) if i is not None}
    return ChangeContext(
        company=company_facts(company),
        categories=await _category_facts(session, company.id, category_ids),
        cis=await _ci_facts(session, company.id, data.ci_ids),
        members=await _members(session, company.id),
        consented_ci_ids=await _consented(session, change) if change is not None else frozenset(),
    )


# --------------------------------------------------------------------------- values


def _clean_text(value: object) -> str | None:
    if value is None:
        return None
    clean = str(value).strip()
    return clean or None


_TEXT_FIELDS = frozenset(
    {
        ChangeField.TITLE,
        ChangeField.DESCRIPTION,
        ChangeField.IMPLEMENTATION_PLAN,
        ChangeField.ROLLBACK_PLAN,
        ChangeField.IMPACT,
        ChangeField.REQUIREMENT_REF,
        ChangeField.TICKET_REF,
    }
)
_USER_FIELDS = frozenset(
    {ChangeField.ASSIGNEE_ID, ChangeField.APPROVER_ID, ChangeField.VERIFIER_ID}
)


def _convert(values: Mapping[str, object]) -> dict[str, Any]:
    """API values -> ``ChangeData`` attribute values (unknown keys: programming error)."""
    unknown = set(values) - {f.value for f in ChangeField}
    if unknown:
        raise ValueError(f"not change fields: {sorted(unknown)}")
    result: dict[str, Any] = {}
    for name, value in values.items():
        key = ChangeField(name)
        if key in _TEXT_FIELDS:
            result[name] = _clean_text(value)
        elif key is ChangeField.CHANGE_TYPE:
            result[name] = None if value is None else ChangeType(str(value))
        elif key is ChangeField.RISK:
            result[name] = None if value is None else Risk(str(value))
        elif key is ChangeField.CI_IDS:
            result[name] = frozenset(cast(Iterable[UUID], value or ()))
        else:
            result[name] = value
    return result


async def _validate_references(
    session: AsyncSession, company_id: UUID, values: Mapping[str, Any]
) -> None:
    """Referenced rows must exist; CI must be CI OF THIS COMPANY (a CI of another company
    is reported exactly like a missing one). Eligibility is readiness's job (§4.3)."""
    ci_ids = values.get(ChangeField.CI_IDS.value)
    if ci_ids:
        found = await _ci_facts(session, company_id, ci_ids)
        if set(ci_ids) - set(found):
            raise _unprocessable(
                "change.ci_not_found",
                "Nie znaleziono obiektu (CI) w tej spółce.",
                ChangeField.CI_IDS.value,
            )
    for name in (ChangeField.CATEGORY_ID.value, ChangeField.SUBCATEGORY_ID.value):
        category_id = values.get(name)
        if category_id is not None and await session.get(ChangeCategory, category_id) is None:
            raise _unprocessable("change.category_not_found", "Nie znaleziono kategorii.", name)
    for user_field in _USER_FIELDS:
        user_id = values.get(user_field.value)
        if user_id is None:
            continue
        # A member of THIS company (any role); a non-member is reported exactly like an
        # unknown id - the user directory of other companies is not revealed. Eligibility
        # (role, active) is readiness's job.
        member = (
            await session.execute(
                select(CompanyMembership.id)
                .where(
                    CompanyMembership.company_id == company_id,
                    CompanyMembership.user_id == user_id,
                )
                .limit(1)
            )
        ).first()
        if member is None:
            raise _unprocessable(
                "change.user_not_found",
                "Nie znaleziono użytkownika wśród członków tej spółki.",
                user_field.value,
            )


def _audited(data: ChangeData) -> dict[str, object]:
    """Field values recorded in the audit diff (CI as a sorted id list)."""
    values: dict[str, object] = {f.value: getattr(data, f.value) for f in ChangeField}
    values[ChangeField.CI_IDS.value] = sorted(str(i) for i in data.ci_ids)
    return values


def _lifecycle(change: Change) -> dict[str, object]:
    return {name: getattr(change, name) for name in _LIFECYCLE}


def _apply(change: Change, data: ChangeData, fields: Iterable[ChangeField]) -> None:
    for name in fields:
        if name is ChangeField.CI_IDS:
            continue
        value = getattr(data, name.value)
        if isinstance(value, StrEnum):
            value = value.value
        setattr(change, name.value, value)


async def _set_items(
    session: AsyncSession, change: Change, before: frozenset[UUID], after: frozenset[UUID]
) -> None:
    removed, added = before - after, after - before
    if removed:
        await session.execute(
            delete(ChangeItem).where(
                ChangeItem.company_id == change.company_id,
                ChangeItem.change_id == change.id,
                ChangeItem.ci_id.in_(list(removed)),
            )
        )
    for ci_id in sorted(added):
        session.add(
            ChangeItem(id=uuid4(), company_id=change.company_id, change_id=change.id, ci_id=ci_id)
        )


# --------------------------------------------------------------------------- create


async def _suggested_approver(
    session: AsyncSession, company: Company, data: ChangeData
) -> UUID | None:
    """``company_categories.approver_override_id`` -> ``companies.default_approver_id``,
    skipping the requester and the assignee (§4.3; four eyes)."""
    override = None
    if data.category_id is not None:
        override = (
            await session.execute(
                select(CompanyCategory.approver_override_id).where(
                    CompanyCategory.company_id == company.id,
                    CompanyCategory.category_id == data.category_id,
                )
            )
        ).scalar_one_or_none()
    excluded = {i for i in (data.requested_by_id, data.assignee_id) if i is not None}
    return default_approver_id(
        category_override_id=override,
        company_default_approver_id=company.default_approver_id,
        excluded=excluded,
    )


async def create_change(
    session: AsyncSession,
    *,
    actor: ChangeActor,
    company: Company,
    values: Mapping[str, object],
    supersedes_change_id: UUID | None = None,
    now: datetime | None = None,
    audit_context: Mapping[str, object] | None = None,
) -> Change:
    """A new draft with its number (§8 ``POST /changes``); ``requested_by`` = the actor.

    A draft may be incomplete (readiness decides on submission). Without ``approver_id``
    in ``values`` the default approver is suggested (§4.3). ``now``: the business clock
    (``created_at``, numbering year); the database clock by default, a fixed time only
    for sample data (ADR 0013 §9).
    """
    if company.status == CompanyStatus.ARCHIVED:
        raise company_archived()
    converted = _convert(values)
    await _validate_references(session, company.id, converted)
    if supersedes_change_id is not None and (
        await _get(session, company.id, supersedes_change_id) is None
    ):
        raise _unprocessable(
            "change.supersedes_not_found",
            "Nie znaleziono zmiany, którą ta zmiana koryguje.",
            "supersedes_change_id",
        )
    clock = now or await db_now(session)
    data = replace(
        ChangeData(
            id=uuid4(),
            company_id=company.id,
            status=ChangeStatus.DRAFT,
            requested_by_id=actor.user_id,
        ),
        **converted,
    )
    if ChangeField.APPROVER_ID.value not in converted:
        data = replace(data, approver_id=await _suggested_approver(session, company, data))

    number = await numbering.next_number(
        session, company_id=company.id, prefix=company.prefix, at=clock
    )
    change = Change(
        id=data.id,
        company_id=company.id,
        number=number,
        status=ChangeStatus.DRAFT.value,
        requested_by_id=actor.user_id,
        supersedes_change_id=supersedes_change_id,
        consent_round=1,
        version=1,
        created_at=clock,
        updated_at=clock,
    )
    _apply(change, data, ChangeField)
    session.add(change)
    await flush_guarded(session)
    await _set_items(session, change, frozenset(), data.ci_ids)
    await flush_guarded(session)

    after = _audited(data)
    after.update(number=number, status=ChangeStatus.DRAFT.value, requested_by_id=actor.user_id)
    if supersedes_change_id is not None:
        after["supersedes_change_id"] = supersedes_change_id
    await audit.record(
        session,
        company_id=company.id,
        actor=actor.audit,
        entity_type=EntityType.CHANGE,
        entity_id=change.id,
        action=AuditAction.CREATE,
        diff=make_diff({}, after),
        context={
            "number": number,
            "status": ChangeStatus.DRAFT.value,
            "version": 1,
            **(audit_context or {}),
        },
    )
    return change


# --------------------------------------------------------------------------- read


async def _get(session: AsyncSession, company_id: UUID, change_id: UUID) -> Change | None:
    return (
        await session.execute(
            select(Change).where(Change.company_id == company_id, Change.id == change_id)
        )
    ).scalar_one_or_none()


async def _lock(session: AsyncSession, company_id: UUID, change_id: UUID) -> Change:
    change = (
        await session.execute(
            select(Change)
            .where(Change.company_id == company_id, Change.id == change_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if change is None:
        raise not_found()
    return change


async def find_id_by_number(session: AsyncSession, company_id: UUID, number: str) -> UUID | None:
    return (
        await session.execute(
            select(Change.id).where(Change.company_id == company_id, Change.number == number)
        )
    ).scalar_one_or_none()


@dataclass(frozen=True, slots=True)
class ItemView:
    ci_id: UUID
    identifier: str  # snapshot once frozen, current otherwise
    name: str
    current_identifier: str
    current_name: str
    ci_type_code: str
    is_active: bool
    owner_user_id: UUID | None
    snapshot: bool
    consented: bool


@dataclass(frozen=True, slots=True)
class ConsentView:
    ci_id: UUID
    owner_user_id: UUID
    consented_at: datetime
    valid: bool  # given by the current owner of the CI (only such consents count)
    # The owner is also the requester or the assignee: not an independent consent (the
    # four-eyes control is the approval; shown to the approver, ADR 0013 §5).
    by_requester_or_assignee: bool


@dataclass(frozen=True, slots=True)
class LinkedChange:
    """A change linked by a correction (``supersedes_change_id``, ADR 0021)."""

    id: UUID
    number: str
    status: str


@dataclass(frozen=True, slots=True)
class CorrectionLinks:
    supersedes_number: str | None  # the original's number (this change is a correction)
    superseded_by: list[LinkedChange]  # corrections of this change, oldest first


async def correction_links(
    session: AsyncSession, company_id: UUID, change: Change
) -> CorrectionLinks:
    """Both directions of a correction in ONE query (index on ``supersedes_change_id``);
    only within the company (composite FK; RLS enforces it too)."""
    condition: ColumnElement[bool] = Change.supersedes_change_id == change.id
    if change.supersedes_change_id is not None:
        condition = or_(condition, Change.id == change.supersedes_change_id)
    rows = (
        await session.execute(
            select(Change.id, Change.number, Change.status, Change.supersedes_change_id)
            .where(Change.company_id == company_id, condition)
            .order_by(Change.created_at, Change.id)
        )
    ).all()
    supersedes = next((r.number for r in rows if r.id == change.supersedes_change_id), None)
    return CorrectionLinks(
        supersedes_number=supersedes,
        superseded_by=[
            LinkedChange(id=r.id, number=r.number, status=str(r.status))
            for r in rows
            if r.supersedes_change_id == change.id
        ],
    )


@dataclass(frozen=True, slots=True)
class ChangeView:
    change: Change
    data: ChangeData
    ctx: ChangeContext
    items: list[ItemView]
    consents: list[ConsentView]
    comments: list[ChangeComment]
    users: Mapping[UUID, User]
    categories: Mapping[UUID, ChangeCategory]
    allowed_actions: tuple[ChangeAction, ...]
    editable_fields: frozenset[ChangeField]
    deviations: tuple[Deviation, ...]
    suggested_approver_id: UUID | None
    links: CorrectionLinks


async def users_by_id(session: AsyncSession, ids: Iterable[UUID | None]) -> dict[UUID, User]:
    wanted = {i for i in ids if i is not None}
    if not wanted:
        return {}
    rows = (await session.execute(select(User).where(User.id.in_(list(wanted))))).scalars().all()
    return {u.id: u for u in rows}


async def _categories(
    session: AsyncSession, ids: Iterable[UUID | None]
) -> dict[UUID, ChangeCategory]:
    wanted = {i for i in ids if i is not None}
    if not wanted:
        return {}
    rows = (
        (await session.execute(select(ChangeCategory).where(ChangeCategory.id.in_(list(wanted)))))
        .scalars()
        .all()
    )
    return {c.id: c for c in rows}


async def get_change_view(
    session: AsyncSession,
    *,
    company: Company,
    change_id: UUID,
    actor: ChangeActor,
    now: datetime | None = None,
) -> ChangeView:
    """The change card: fields, CI (with snapshot), consents, comments, people and what
    the actor may do now (``allowed_actions``, ``editable_fields``)."""
    change = await _get(session, company.id, change_id)
    if change is None:
        raise not_found()
    clock = now or await db_now(session)
    item_rows = (
        await session.execute(
            select(ChangeItem, ConfigurationItem, CiType)
            .join(
                ConfigurationItem,
                (ConfigurationItem.id == ChangeItem.ci_id)
                & (ConfigurationItem.company_id == ChangeItem.company_id),
            )
            .join(CiType, CiType.id == ConfigurationItem.ci_type_id)
            .where(ChangeItem.company_id == company.id, ChangeItem.change_id == change.id)
        )
    ).all()
    data = to_data(change, [item.ci_id for item, _, _ in item_rows])
    ctx = await load_context(session, company, data, change=change)
    consent_rows = (
        (
            await session.execute(
                select(ChangeCiConsent)
                .where(
                    ChangeCiConsent.company_id == company.id,
                    ChangeCiConsent.change_id == change.id,
                    ChangeCiConsent.consent_round == change.consent_round,
                )
                .order_by(ChangeCiConsent.created_at, ChangeCiConsent.id)
            )
        )
        .scalars()
        .all()
    )
    comments = list(
        (
            await session.execute(
                select(ChangeComment)
                .where(ChangeComment.company_id == company.id, ChangeComment.change_id == change.id)
                .order_by(ChangeComment.created_at, ChangeComment.id)
            )
        )
        .scalars()
        .all()
    )
    items = sorted(
        (
            ItemView(
                ci_id=ci.id,
                identifier=item.ci_identifier or ci.identifier,
                name=item.ci_name or ci.name,
                current_identifier=ci.identifier,
                current_name=ci.name,
                ci_type_code=ci_type.code,
                is_active=ci.is_active,
                owner_user_id=ci.owner_user_id,
                snapshot=item.ci_identifier is not None,
                consented=ci.id in ctx.consented_ci_ids,
            )
            for item, ci, ci_type in item_rows
        ),
        key=lambda i: (i.identifier.lower(), str(i.ci_id)),
    )
    users = await users_by_id(
        session,
        [
            change.requested_by_id,
            change.assignee_id,
            change.approver_id,
            change.verifier_id,
            change.approved_by_id,
            *(c.author_id for c in comments),
            *(c.owner_user_id for c in consent_rows),
            *(i.owner_user_id for i in items),
        ],
    )
    owners = {i.ci_id: i.owner_user_id for i in items}
    suggested = None
    if change.status == ChangeStatus.DRAFT:
        suggested = await _suggested_approver(session, company, data)
    return ChangeView(
        change=change,
        data=data,
        ctx=ctx,
        items=items,
        consents=[
            ConsentView(
                ci_id=c.ci_id,
                owner_user_id=c.owner_user_id,
                consented_at=c.created_at,
                valid=c.ci_id in ctx.consented_ci_ids and owners.get(c.ci_id) == c.owner_user_id,
                by_requester_or_assignee=c.owner_user_id
                in {change.requested_by_id, change.assignee_id},
            )
            for c in consent_rows
        ],
        comments=comments,
        users=users,
        categories=await _categories(session, [change.category_id, change.subcategory_id]),
        allowed_actions=allowed_actions(data, actor.facts, ctx),
        editable_fields=editable_fields(data, actor.facts, ctx),
        deviations=deviations(change_subject(change), now=clock),
        suggested_approver_id=suggested,
        links=await correction_links(session, company.id, change),
    )


def change_subject(change: Change) -> ChangeData:
    """A stored change as ``app.domain.deviations.DeviationSubject`` (typed enums; the
    CI list is irrelevant for deviations)."""
    return to_data(change, ())


async def readiness_of(
    session: AsyncSession, *, company: Company, change_id: UUID, now: datetime | None = None
) -> ReadinessReport:
    """§4.3 checks for the panel "Kontrola przed wysłaniem" (same rules as ``submit``)."""
    change = await _get(session, company.id, change_id)
    if change is None:
        raise not_found()
    data = to_data(change, await _ci_ids(session, change))
    ctx = await load_context(session, company, data, change=change)
    return readiness(data, ctx, now=now or await db_now(session))


# --------------------------------------------------------------------------- update


async def update_change(
    session: AsyncSession,
    *,
    actor: ChangeActor,
    company: Company,
    change_id: UUID,
    expected_version: int,
    values: Mapping[str, object],
    now: datetime | None = None,
    audit_context: Mapping[str, object] | None = None,
) -> Change:
    """``PATCH``: only the provided fields; ``expected_version`` must be the current one
    (409 ``change.version_conflict``). Which fields may change, by whom and in which
    status is decided by ``check_edit`` (ADR 0012 §6). Nothing changed = nothing written."""
    change = await _lock(session, company.id, change_id)
    if change.version != expected_version:
        raise _version_conflict(change.version)
    converted = _convert(values)
    await _validate_references(session, company.id, converted)
    current_ci = await _ci_ids(session, change)
    current = to_data(change, current_ci)
    proposed = replace(current, **converted)
    ctx = await load_context(session, company, proposed, change=change)
    try:
        changed = check_edit(current, proposed, actor.facts, ctx, now=now or await db_now(session))
    except ChangeRuleError as exc:
        raise rule_problem(exc) from exc
    if not changed:
        return change

    before = _audited(current)
    after = _audited(proposed)
    with session.no_autoflush:
        _apply(change, proposed, changed)
        change.version += 1
    await flush_guarded(session)
    if ChangeField.CI_IDS in changed:
        await _set_items(session, change, current_ci, proposed.ci_ids)
        await flush_guarded(session)
    await audit.record(
        session,
        company_id=company.id,
        actor=actor.audit,
        entity_type=EntityType.CHANGE,
        entity_id=change.id,
        action=AuditAction.UPDATE,
        diff=make_diff(
            {k: before[k] for k in sorted(f.value for f in changed)},
            {k: after[k] for k in sorted(f.value for f in changed)},
        ),
        context={
            "number": change.number,
            "status": change.status,
            "version": change.version,
            **(audit_context or {}),
        },
    )
    await session.refresh(change)
    return change


# --------------------------------------------------------------------------- actions


async def _set_action_path(session: AsyncSession, change_id: UUID | None) -> None:
    """Open (or close, ``None``) the action path of migration 0008 for one change."""
    await session.execute(
        text("SELECT set_config(:name, :value, true)"),
        {"name": _CHANGE_ACTION_SETTING, "value": "" if change_id is None else str(change_id)},
    )


async def _share_lock_ci(session: AsyncSession, company_id: UUID, ci_ids: Collection[UUID]) -> None:
    """``FOR SHARE`` on the change's CI: a concurrent change of a CI owner (``FOR UPDATE``
    in ``configuration_items.update_item``) either finishes before this action reads the
    owners, or waits and then sees the change waiting for approval (409
    ``ci.owner_locked_by_change``, ADR 0013 §5). Lock order: change row, then CI."""
    if ci_ids:
        await session.execute(
            select(ConfigurationItem.id)
            .where(
                ConfigurationItem.company_id == company_id,
                ConfigurationItem.id.in_(sorted(ci_ids)),
            )
            .order_by(ConfigurationItem.id)
            .with_for_update(read=True)
        )


async def _snapshot_ci(session: AsyncSession, change: Change) -> None:
    """Freeze the identifier and name of the change's CI (ADR 0011 §9 pt 5)."""
    rows = (
        await session.execute(
            select(ChangeItem.id, ConfigurationItem.identifier, ConfigurationItem.name)
            .join(
                ConfigurationItem,
                (ConfigurationItem.id == ChangeItem.ci_id)
                & (ConfigurationItem.company_id == ChangeItem.company_id),
            )
            .where(
                ChangeItem.company_id == change.company_id,
                ChangeItem.change_id == change.id,
                ChangeItem.ci_identifier.is_(None),
            )
        )
    ).all()
    for item_id, identifier, name in rows:
        await session.execute(
            update(ChangeItem)
            .where(ChangeItem.id == item_id)
            .values(ci_identifier=identifier, ci_name=name)
            .execution_options(synchronize_session=False)
        )


@dataclass(frozen=True, slots=True)
class ActionResult:
    change: Change
    outcome: TransitionOutcome
    comment_id: UUID | None


async def perform_action(
    session: AsyncSession,
    *,
    actor: ChangeActor,
    company: Company,
    change_id: UUID,
    action: ChangeAction,
    comment: str | None = None,
    expected_version: int | None = None,
    now: datetime | None = None,
    audit_context: Mapping[str, object] | None = None,
) -> ActionResult:
    """``POST .../actions/{action}``: the state machine decides (``execute``), the service
    persists ``outcome`` and the audit entry in one transaction (ADR 0012 §9, ADR 0013 §6).

    The change row is locked ``FOR UPDATE`` first, so concurrent actions are serialized
    and each one sees the result of the previous one. ``expected_version`` is optional for
    actions (the state machine re-validates the locked row anyway).
    """
    change = await _lock(session, company.id, change_id)
    if expected_version is not None and change.version != expected_version:
        raise _version_conflict(change.version)
    clock = now or await db_now(session)
    ci_ids = await _ci_ids(session, change)
    await _share_lock_ci(session, company.id, ci_ids)
    data = to_data(change, ci_ids)
    ctx = await load_context(session, company, data, change=change)
    try:
        outcome = execute(action, data, actor.facts, ctx, now=clock, comment=comment)
    except ChangeRuleError as exc:
        raise rule_problem(exc) from exc

    before = {**_lifecycle(change), "consent_round": change.consent_round}
    row_changes = bool(outcome.updates) or outcome.clear_consents
    await _set_action_path(session, change.id)
    with session.no_autoflush:
        for name, value in outcome.updates.items():
            setattr(change, name, value.value if isinstance(value, StrEnum) else value)
        if outcome.clear_consents:
            change.consent_round += 1
        if row_changes:
            change.version += 1
    await flush_guarded(session)
    if outcome.snapshot_ci:
        await _snapshot_ci(session, change)
    for ci_id in sorted(outcome.consented_ci_ids):
        session.add(
            ChangeCiConsent(
                id=uuid4(),
                company_id=company.id,
                change_id=change.id,
                ci_id=ci_id,
                owner_user_id=actor.user_id,
                consent_round=change.consent_round,
                created_at=clock,
                updated_at=clock,
            )
        )
    comment_id = None
    if outcome.comment is not None:
        comment_id = uuid4()
        session.add(
            ChangeComment(
                id=comment_id,
                company_id=company.id,
                change_id=change.id,
                author_id=actor.user_id,
                body=outcome.comment,
                action=action.value,
                created_at=clock,
                updated_at=clock,
            )
        )
    await flush_guarded(session)
    await _set_action_path(session, None)

    after = {**_lifecycle(change), "consent_round": change.consent_round}
    context = {**outcome.audit_context(), **(audit_context or {})}
    context.update(number=change.number, version=change.version)
    if comment_id is not None:
        context["comment_id"] = comment_id
    await audit.record(
        session,
        company_id=company.id,
        actor=Actor.system() if outcome.performed_by_system else actor.audit,
        entity_type=EntityType.CHANGE,
        entity_id=change.id,
        action=AuditAction.TRANSITION,
        diff=make_diff(before, after),
        context=context,
    )
    await session.refresh(change)
    return ActionResult(change=change, outcome=outcome, comment_id=comment_id)


# --------------------------------------------------------------------------- register


class SortKey(StrEnum):
    CREATED_AT = "created_at"
    CREATED_AT_DESC = "-created_at"
    NUMBER = "number"
    NUMBER_DESC = "-number"
    IMPLEMENTED_AT = "implemented_at"
    IMPLEMENTED_AT_DESC = "-implemented_at"
    TITLE = "title"
    TITLE_DESC = "-title"
    STATUS = "status"
    STATUS_DESC = "-status"


@dataclass(frozen=True, slots=True)
class ChangeFilters:
    """Register filters (§8). Period: ``[period_from, period_to)`` on ``period_by``."""

    period_from: datetime | None = None
    period_to: datetime | None = None
    period_by: Literal["created", "implemented"] = "created"
    statuses: Sequence[ChangeStatus] = ()
    types: Sequence[ChangeType] = ()
    categories: Sequence[UUID] = ()  # category OR subcategory
    cis: Sequence[UUID] = ()
    assignee_id: UUID | None = None
    approver_id: UUID | None = None  # the DESIGNATED approver
    approved_by_id: UUID | None = None  # who actually approved
    approved_by_system: bool = False  # approved automatically (standard change)
    q: str | None = None


@dataclass(frozen=True, slots=True)
class RegisterRow:
    change: Change
    items: list[ItemView]
    deviations: tuple[Deviation, ...]


@dataclass(frozen=True, slots=True)
class RegisterPage:
    rows: list[RegisterRow]
    total: int
    users: Mapping[UUID, User]
    categories: Mapping[UUID, ChangeCategory]


def _like(text_value: str) -> str:
    escaped = text_value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _filtered(company_id: UUID, filters: ChangeFilters) -> Select[Any]:
    stmt = select(Change).where(Change.company_id == company_id)
    period_column = Change.created_at if filters.period_by == "created" else Change.implemented_at
    if filters.period_from is not None:
        stmt = stmt.where(period_column >= filters.period_from)
    if filters.period_to is not None:
        stmt = stmt.where(period_column < filters.period_to)
    if filters.statuses:
        stmt = stmt.where(Change.status.in_([s.value for s in filters.statuses]))
    if filters.types:
        stmt = stmt.where(Change.change_type.in_([t.value for t in filters.types]))
    if filters.categories:
        ids = list(filters.categories)
        stmt = stmt.where(or_(Change.category_id.in_(ids), Change.subcategory_id.in_(ids)))
    if filters.cis:
        stmt = stmt.where(
            exists().where(
                ChangeItem.company_id == Change.company_id,
                ChangeItem.change_id == Change.id,
                ChangeItem.ci_id.in_(list(filters.cis)),
            )
        )
    if filters.assignee_id is not None:
        stmt = stmt.where(Change.assignee_id == filters.assignee_id)
    if filters.approved_by_id is not None:
        stmt = stmt.where(Change.approved_by_id == filters.approved_by_id)
    if filters.approved_by_system:
        stmt = stmt.where(Change.approved_at.is_not(None), Change.approved_by_id.is_(None))
    if filters.approver_id is not None:
        stmt = stmt.where(Change.approver_id == filters.approver_id)
    if filters.q is not None and filters.q.strip():
        pattern = _like(filters.q.strip())
        conditions: list[ColumnElement[bool]] = [
            Change.number.ilike(pattern, escape="\\"),
            Change.title.ilike(pattern, escape="\\"),
            Change.ticket_ref.ilike(pattern, escape="\\"),
        ]
        stmt = stmt.where(or_(*conditions))
    return stmt


_SORT: Mapping[SortKey, tuple[Any, bool]] = {
    SortKey.CREATED_AT: (Change.created_at, False),
    SortKey.CREATED_AT_DESC: (Change.created_at, True),
    SortKey.NUMBER: (Change.number, False),
    SortKey.NUMBER_DESC: (Change.number, True),
    SortKey.IMPLEMENTED_AT: (Change.implemented_at, False),
    SortKey.IMPLEMENTED_AT_DESC: (Change.implemented_at, True),
    SortKey.TITLE: (func.lower(Change.title), False),
    SortKey.TITLE_DESC: (func.lower(Change.title), True),
    SortKey.STATUS: (Change.status, False),
    SortKey.STATUS_DESC: (Change.status, True),
}


async def _items_of(
    session: AsyncSession, company_id: UUID, change_ids: Sequence[UUID]
) -> dict[UUID, list[ItemView]]:
    if not change_ids:
        return {}
    rows = (
        await session.execute(
            select(ChangeItem, ConfigurationItem, CiType)
            .join(
                ConfigurationItem,
                (ConfigurationItem.id == ChangeItem.ci_id)
                & (ConfigurationItem.company_id == ChangeItem.company_id),
            )
            .join(CiType, CiType.id == ConfigurationItem.ci_type_id)
            .where(ChangeItem.company_id == company_id, ChangeItem.change_id.in_(list(change_ids)))
        )
    ).all()
    result: dict[UUID, list[ItemView]] = defaultdict(list)
    for item, ci, ci_type in rows:
        result[item.change_id].append(
            ItemView(
                ci_id=ci.id,
                identifier=item.ci_identifier or ci.identifier,
                name=item.ci_name or ci.name,
                current_identifier=ci.identifier,
                current_name=ci.name,
                ci_type_code=ci_type.code,
                is_active=ci.is_active,
                owner_user_id=ci.owner_user_id,
                snapshot=item.ci_identifier is not None,
                consented=False,
            )
        )
    for views in result.values():
        views.sort(key=lambda i: (i.identifier.lower(), str(i.ci_id)))
    return result


async def count_changes(session: AsyncSession, company_id: UUID, filters: ChangeFilters) -> int:
    """How many changes of the company match the register filters (reports, ADR 0017)."""
    stmt = _filtered(company_id, filters)
    total = (await session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    return int(total)


async def list_changes(
    session: AsyncSession,
    company_id: UUID,
    filters: ChangeFilters,
    *,
    sort: SortKey = SortKey.CREATED_AT_DESC,
    limit: int,
    offset: int,
    now: datetime | None = None,
) -> RegisterPage:
    stmt = _filtered(company_id, filters)
    total = (await session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    column, descending = _SORT[sort]
    order = column.desc().nulls_last() if descending else column.asc().nulls_last()
    changes = list(
        (await session.execute(stmt.order_by(order, Change.id).limit(limit).offset(offset)))
        .scalars()
        .all()
    )
    clock = now or await db_now(session)
    items = await _items_of(session, company_id, [c.id for c in changes])
    users = await users_by_id(
        session,
        [
            u
            for c in changes
            for u in (
                c.requested_by_id,
                c.assignee_id,
                c.approver_id,
                c.verifier_id,
                c.approved_by_id,
            )
        ],
    )
    categories = await _categories(
        session, [i for c in changes for i in (c.category_id, c.subcategory_id)]
    )
    return RegisterPage(
        rows=[
            RegisterRow(
                change=c,
                items=items.get(c.id, []),
                deviations=deviations(change_subject(c), now=clock),
            )
            for c in changes
        ],
        total=int(total),
        users=users,
        categories=categories,
    )


# --------------------------------------------------------------------------- stats


@dataclass(frozen=True, slots=True)
class ChangeStats:
    """Register tiles (§10.1) and the emergency deviation counter (ADR 0013 §8)."""

    pending_approval: int
    approved_not_implemented: int
    emergency_last_30_days: int
    implemented_not_verified: int
    emergency_not_approved_in_24h: int
    implemented_outside_window: int
    by_status: Mapping[str, int] = field(default_factory=dict)


async def stats(
    session: AsyncSession, company_id: UUID, *, now: datetime | None = None
) -> ChangeStats:
    clock = now or await db_now(session)
    by_status = {
        str(status): int(count)
        for status, count in (
            await session.execute(
                select(Change.status, func.count())
                .where(Change.company_id == company_id)
                .group_by(Change.status)
            )
        ).all()
    }
    emergency_recent = (
        await session.execute(
            select(func.count()).where(
                Change.company_id == company_id,
                Change.change_type == ChangeType.EMERGENCY.value,
                Change.status != ChangeStatus.CANCELLED.value,
                Change.created_at >= clock - timedelta(days=EMERGENCY_TILE_DAYS),
            )
        )
    ).scalar_one()
    # The deviation rules live in the domain; only the candidates come from SQL.
    candidates = (
        (
            await session.execute(
                select(Change).where(
                    Change.company_id == company_id, Change.implemented_at.is_not(None)
                )
            )
        )
        .scalars()
        .all()
    )
    subjects = [change_subject(c) for c in candidates]
    overdue = sum(1 for c in subjects if emergency_approval_overdue(c, now=clock))
    outside = sum(
        1
        for c in subjects
        if implemented_outside_window(c.change_type, c.implemented_at, c.window_start, c.window_end)
    )
    return ChangeStats(
        pending_approval=by_status.get(ChangeStatus.PENDING_APPROVAL.value, 0),
        approved_not_implemented=by_status.get(ChangeStatus.APPROVED.value, 0),
        emergency_last_30_days=int(emergency_recent),
        implemented_not_verified=by_status.get(ChangeStatus.IMPLEMENTED.value, 0),
        emergency_not_approved_in_24h=overdue,
        implemented_outside_window=outside,
        by_status=by_status,
    )


# --------------------------------------------------------------------------- audit trail


async def audit_trail(
    session: AsyncSession, company_id: UUID, change_id: UUID, *, limit: int, offset: int
) -> tuple[list[Any], int]:
    """The change's entries in its company chain, oldest first: the change itself
    (create, update, transitions, consents, comments) and its attachments.

    Returns Core rows (exact stored values) and the total. Only the company chain is
    read (the transaction is scoped to the company; RLS hides every other chain).
    """
    if await _get(session, company_id, change_id) is None:
        raise not_found()
    attachment_ids = select(Attachment.id).where(
        Attachment.company_id == company_id, Attachment.change_id == change_id
    )
    condition = (AuditLog.company_id == company_id) & or_(
        (AuditLog.entity_type == EntityType.CHANGE.value) & (AuditLog.entity_id == change_id),
        (AuditLog.entity_type == EntityType.ATTACHMENT.value)
        & AuditLog.entity_id.in_(attachment_ids),
    )
    total = (
        await session.execute(select(func.count()).select_from(AuditLog).where(condition))
    ).scalar_one()
    rows = (
        await session.execute(
            select(*AuditLog.__table__.columns)
            .where(condition)
            .order_by(AuditLog.seq)
            .limit(limit)
            .offset(offset)
        )
    ).all()
    return list(rows), int(total)
