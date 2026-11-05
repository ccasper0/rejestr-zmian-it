"""Configuration items (CI) of a company (CLAUDE.md 4.1, 5; ADR 0011).

Never deleted, only deactivated (``is_active = false``, audit action ``deactivate``).
Every query filters by ``company_id`` explicitly (RLS is the second line of defence).
Every change is written to the audit chain OF THE COMPANY in the same transaction.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.audit import Actor, AuditAction, EntityType, make_diff
from app.domain.companies import CompanyStatus
from app.domain.dictionaries import (
    InvalidDataError,
    normalize_ci_identifier,
    normalize_description,
    normalize_name,
)
from app.errors import ProblemError
from app.models import (
    Change,
    ChangeCategory,
    ChangeItem,
    CiType,
    Company,
    ConfigurationItem,
    User,
)
from app.services import audit
from app.services import memberships as memberships_service

AUDITED_FIELDS = (
    "ci_type_id",
    "identifier",
    "name",
    "description",
    "owner_user_id",
    "is_active",
)
UPDATABLE_FIELDS = frozenset(AUDITED_FIELDS)
_IDENTIFIER_INDEX = "uq_configuration_items_company_id_identifier_lower"
_ARCHIVED_MARKER = "company_archived:"  # trigger company_must_be_active (migration 0007)


@dataclass(frozen=True, slots=True)
class CiRow:
    item: ConfigurationItem
    ci_type: CiType


def snapshot(item: ConfigurationItem) -> dict[str, object]:
    return {name: getattr(item, name) for name in AUDITED_FIELDS}


def invalid(error: InvalidDataError) -> ProblemError:
    return ProblemError(
        status=422, code="ci.invalid_data", detail=error.message, extra={"field": error.field}
    )


def not_found() -> ProblemError:
    return ProblemError(status=404, code="ci.not_found", detail="Nie znaleziono obiektu (CI).")


def _identifier_taken() -> ProblemError:
    return ProblemError(
        status=409,
        code="ci.identifier_taken",
        detail="Obiekt o tym identyfikatorze już istnieje w tej spółce.",
        extra={"field": "identifier"},
    )


def _like_pattern(text: str) -> str:
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


async def list_items(
    session: AsyncSession,
    company_id: UUID,
    *,
    q: str | None = None,
    type_codes: Sequence[str] = (),
    active: bool | None = None,
    limit: int,
    offset: int,
) -> tuple[list[CiRow], int]:
    stmt = (
        select(ConfigurationItem, CiType)
        .join(CiType, CiType.id == ConfigurationItem.ci_type_id)
        .where(ConfigurationItem.company_id == company_id)
    )
    if q is not None and q.strip():
        pattern = _like_pattern(q.strip())
        stmt = stmt.where(
            or_(
                ConfigurationItem.identifier.ilike(pattern, escape="\\"),
                ConfigurationItem.name.ilike(pattern, escape="\\"),
            )
        )
    if type_codes:
        stmt = stmt.where(CiType.code.in_(list(type_codes)))
    if active is not None:
        stmt = stmt.where(ConfigurationItem.is_active.is_(active))
    total = (await session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = await session.execute(
        stmt.order_by(func.lower(ConfigurationItem.identifier), ConfigurationItem.id)
        .limit(limit)
        .offset(offset)
    )
    return [CiRow(item=item, ci_type=ci_type) for item, ci_type in rows.all()], int(total)


async def get_item(session: AsyncSession, company_id: UUID, ci_id: UUID) -> CiRow | None:
    """The CI ``ci_id`` OF THE COMPANY ``company_id`` (another company's CI: ``None``)."""
    row = (
        await session.execute(
            select(ConfigurationItem, CiType)
            .join(CiType, CiType.id == ConfigurationItem.ci_type_id)
            .where(ConfigurationItem.company_id == company_id, ConfigurationItem.id == ci_id)
        )
    ).one_or_none()
    return None if row is None else CiRow(item=row[0], ci_type=row[1])


def _company_archived() -> ProblemError:
    return ProblemError(
        status=409,
        code="company.archived",
        detail="Spółka jest zarchiwizowana: jej inwentarza obiektów nie można zmieniać.",
    )


def _ensure_company_active(company: Company) -> None:
    """Fast path only (no lock): a concurrent archive is caught by the database trigger
    ``company_must_be_active`` (FOR SHARE on the company row) at flush time."""
    if company.status == CompanyStatus.ARCHIVED:
        raise _company_archived()


async def _active_type(session: AsyncSession, ci_type_id: UUID) -> CiType:
    ci_type = await session.get(CiType, ci_type_id)
    if ci_type is None:
        raise ProblemError(
            status=422,
            code="ci.type_not_found",
            detail="Nie znaleziono typu obiektu.",
            extra={"field": "ci_type_id"},
        )
    if not ci_type.is_active:
        raise ProblemError(
            status=422,
            code="ci.type_inactive",
            detail="Typ obiektu jest nieaktywny: nie można go przypisać.",
            extra={"field": "ci_type_id"},
        )
    return ci_type


async def _check_owner(session: AsyncSession, company_id: UUID, user_id: UUID) -> None:
    """The owner must be an ACTIVE user with any role in this company."""
    user = await session.get(User, user_id)
    roles = await memberships_service.user_roles_in(session, company_id, user_id)
    if user is None or not user.is_active or not roles:
        raise ProblemError(
            status=422,
            code="ci.owner_not_member",
            detail="Właściciel obiektu musi być aktywnym członkiem tej spółki.",
            extra={"field": "owner_user_id"},
        )


async def _owner_locking_changes(session: AsyncSession, company_id: UUID, ci_id: UUID) -> list[str]:
    """Numbers of changes waiting for approval of this CI (ADR 0013 §5): ``pending_approval``
    or an emergency change implemented without approval - and only changes whose category
    or subcategory requires the CI owner's consent (the flag only tightens, ADR 0011 §3);
    other changes do not depend on the owner. While they wait, the owner of the CI - the
    person whose consent counts - cannot change, so nobody (e.g. the requester) can make
    themselves the owner and consent to their own change."""
    consent_categories = select(ChangeCategory.id).where(
        ChangeCategory.requires_ci_owner_consent.is_(True)
    )
    rows = await session.execute(
        select(Change.number)
        .join(
            ChangeItem,
            (ChangeItem.change_id == Change.id) & (ChangeItem.company_id == Change.company_id),
        )
        .where(
            ChangeItem.company_id == company_id,
            ChangeItem.ci_id == ci_id,
            or_(
                Change.status == "pending_approval",
                and_(
                    Change.status == "implemented",
                    Change.change_type == "emergency",
                    Change.approved_at.is_(None),
                ),
            ),
            or_(
                Change.category_id.in_(consent_categories),
                Change.subcategory_id.in_(consent_categories),
            ),
        )
        .order_by(Change.number)
    )
    return list(rows.scalars().all())


async def _ensure_identifier_free(
    session: AsyncSession, company_id: UUID, identifier: str, *, except_id: UUID | None = None
) -> None:
    stmt = select(ConfigurationItem.id).where(
        ConfigurationItem.company_id == company_id,
        func.lower(ConfigurationItem.identifier) == identifier.lower(),
    )
    if except_id is not None:
        stmt = stmt.where(ConfigurationItem.id != except_id)
    if (await session.execute(stmt.limit(1))).first() is not None:
        raise _identifier_taken()


async def _flush(session: AsyncSession) -> None:
    """Flush in a savepoint; a concurrent duplicate identifier becomes 409, not 500."""
    try:
        async with session.begin_nested():
            await session.flush()
    except IntegrityError as exc:
        if _IDENTIFIER_INDEX in str(exc.orig):
            raise _identifier_taken() from exc
        if _ARCHIVED_MARKER in str(exc.orig):
            # Archived concurrently, after _ensure_company_active (trigger, migration 0007).
            raise _company_archived() from exc
        raise


async def create_item(
    session: AsyncSession,
    *,
    actor: Actor,
    company: Company,
    ci_type_id: UUID,
    identifier: str,
    name: str,
    description: str | None = None,
    owner_user_id: UUID | None = None,
) -> CiRow:
    _ensure_company_active(company)
    try:
        clean_identifier = normalize_ci_identifier(identifier)
        clean_name = normalize_name(name)
        clean_description = normalize_description(description)
    except InvalidDataError as exc:
        raise invalid(exc) from exc
    ci_type = await _active_type(session, ci_type_id)
    if owner_user_id is not None:
        await _check_owner(session, company.id, owner_user_id)
    await _ensure_identifier_free(session, company.id, clean_identifier)

    item = ConfigurationItem(
        id=uuid4(),
        company_id=company.id,
        ci_type_id=ci_type.id,
        identifier=clean_identifier,
        name=clean_name,
        description=clean_description,
        owner_user_id=owner_user_id,
        is_active=True,
    )
    session.add(item)
    await _flush(session)
    await audit.record(
        session,
        company_id=company.id,
        actor=actor,
        entity_type=EntityType.CI,
        entity_id=item.id,
        action=AuditAction.CREATE,
        diff=make_diff({}, snapshot(item)),
        context={"identifier": item.identifier, "ci_type_code": ci_type.code},
    )
    await session.refresh(item)
    return CiRow(item=item, ci_type=ci_type)


async def update_item(
    session: AsyncSession,
    *,
    actor: Actor,
    company: Company,
    ci_id: UUID,
    changes: Mapping[str, Any],
) -> CiRow:
    """Apply the provided fields (only changed ones are validated).

    ``is_active`` true -> false is recorded as ``deactivate``, anything else as
    ``update``. A request that changes nothing writes nothing (no audit entry).
    """
    unknown = set(changes) - UPDATABLE_FIELDS
    if unknown:
        raise ValueError(f"fields not updatable: {sorted(unknown)}")
    _ensure_company_active(company)
    item = (
        await session.execute(
            select(ConfigurationItem)
            .where(ConfigurationItem.company_id == company.id, ConfigurationItem.id == ci_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    ).scalar_one_or_none()
    if item is None:
        raise not_found()
    before = snapshot(item)
    # No autoflush while the row is dirty: the lookups below would flush it OUTSIDE
    # _flush, so a concurrent duplicate identifier (or an archive, migration 0007)
    # would surface as a 500 instead of 409.
    with session.no_autoflush:
        try:
            if "identifier" in changes:
                identifier = normalize_ci_identifier(str(changes["identifier"]))
                if identifier.lower() != item.identifier.lower():
                    await _ensure_identifier_free(
                        session, company.id, identifier, except_id=item.id
                    )
                item.identifier = identifier
            if "name" in changes:
                item.name = normalize_name(str(changes["name"]))
            if "description" in changes:
                item.description = normalize_description(changes["description"])
        except InvalidDataError as exc:
            raise invalid(exc) from exc
        if "ci_type_id" in changes and changes["ci_type_id"] != item.ci_type_id:
            item.ci_type_id = (await _active_type(session, changes["ci_type_id"])).id
        if "owner_user_id" in changes and changes["owner_user_id"] != item.owner_user_id:
            waiting = await _owner_locking_changes(session, company.id, item.id)
            if waiting:
                raise ProblemError(
                    status=409,
                    code="ci.owner_locked_by_change",
                    detail=(
                        "Nie można zmienić właściciela obiektu, dopóki czekają na "
                        "zatwierdzenie zmiany, które go dotyczą: " + ", ".join(waiting) + "."
                    ),
                    extra={"field": "owner_user_id", "changes": waiting},
                )
            owner = changes["owner_user_id"]
            if owner is not None:
                await _check_owner(session, company.id, owner)
            item.owner_user_id = owner
        if "is_active" in changes:
            item.is_active = bool(changes["is_active"])

        ci_type = await session.get(CiType, item.ci_type_id)
        assert ci_type is not None  # noqa: S101 - FK
    diff = make_diff(before, snapshot(item))
    if not diff:
        return CiRow(item=item, ci_type=ci_type)
    await _flush(session)
    deactivated = before["is_active"] is True and item.is_active is False
    await audit.record(
        session,
        company_id=company.id,
        actor=actor,
        entity_type=EntityType.CI,
        entity_id=item.id,
        action=AuditAction.DEACTIVATE if deactivated else AuditAction.UPDATE,
        diff=diff,
        context={"identifier": item.identifier, "ci_type_code": ci_type.code},
    )
    await session.refresh(item)
    return CiRow(item=item, ci_type=ci_type)
