"""Companies: create, update (prefix immutable), archive (never delete), list.

Company events are written to the GLOBAL audit chain in the same transaction.
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.audit import Actor, AuditAction, EntityType, make_diff
from app.domain.companies import (
    CompanyStatus,
    InvalidCompanyDataError,
    normalize_name,
    normalize_tax_id,
    validate_prefix,
)
from app.errors import ProblemError
from app.models import Company, CompanyMembership, ConfigurationItem, User
from app.services import audit

AUDITED_FIELDS = ("name", "tax_id", "prefix", "status", "is_ksc_entity", "default_approver_id")
UPDATABLE_FIELDS = frozenset({"name", "tax_id", "is_ksc_entity", "default_approver_id", "prefix"})


def snapshot(company: Company) -> dict[str, object]:
    return {name: getattr(company, name) for name in AUDITED_FIELDS}


def invalid(error: InvalidCompanyDataError) -> ProblemError:
    return ProblemError(
        status=422, code="company.invalid_data", detail=error.message, extra={"field": error.field}
    )


def not_found() -> ProblemError:
    return ProblemError(status=404, code="company.not_found", detail="Nie znaleziono spółki.")


def _name_taken() -> ProblemError:
    return ProblemError(
        status=409, code="company.name_taken", detail="Spółka o tej nazwie już istnieje."
    )


def _prefix_taken() -> ProblemError:
    return ProblemError(
        status=409,
        code="company.prefix_taken",
        detail="Prefiks jest już używany przez inną spółkę.",
    )


async def get_company(session: AsyncSession, company_id: UUID) -> Company | None:
    return await session.get(Company, company_id)


async def get_company_by_prefix(session: AsyncSession, prefix: str) -> Company | None:
    result = await session.execute(select(Company).where(Company.prefix == prefix))
    return result.scalar_one_or_none()


async def _lock(session: AsyncSession, company_id: UUID) -> Company:
    result = await session.execute(
        select(Company)
        .where(Company.id == company_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    company = result.scalar_one_or_none()
    if company is None:
        raise not_found()
    return company


async def _ensure_name_free(
    session: AsyncSession, name: str, *, except_id: UUID | None = None
) -> None:
    stmt = select(Company.id).where(func.lower(Company.name) == name.lower())
    if except_id is not None:
        stmt = stmt.where(Company.id != except_id)
    if (await session.execute(stmt.limit(1))).first() is not None:
        raise _name_taken()


async def _validate_approver(session: AsyncSession, approver_id: UUID | None) -> None:
    if approver_id is None:
        return
    user = await session.get(User, approver_id)
    if user is None or not user.is_active:
        raise invalid(
            InvalidCompanyDataError(
                "default_approver_id",
                "Domyślny zatwierdzający musi być aktywnym użytkownikiem.",
            )
        )


async def _flush_mapping_conflicts(session: AsyncSession) -> None:
    """Flush in a savepoint; a concurrent duplicate becomes 409 instead of a 500."""
    try:
        async with session.begin_nested():
            await session.flush()
    except IntegrityError as exc:
        message = str(exc.orig)
        if "uq_companies_prefix" in message:
            raise _prefix_taken() from exc
        if "uq_companies_name_lower" in message:
            raise _name_taken() from exc
        raise


async def create_company(
    session: AsyncSession,
    *,
    actor: Actor,
    name: str,
    prefix: str,
    tax_id: str | None = None,
    is_ksc_entity: bool = False,
    default_approver_id: UUID | None = None,
) -> Company:
    try:
        clean_name = normalize_name(name)
        clean_prefix = validate_prefix(prefix)
        clean_tax_id = normalize_tax_id(tax_id)
    except InvalidCompanyDataError as exc:
        raise invalid(exc) from exc
    if await get_company_by_prefix(session, clean_prefix) is not None:
        raise _prefix_taken()
    await _ensure_name_free(session, clean_name)
    await _validate_approver(session, default_approver_id)

    company = Company(
        id=uuid4(),
        name=clean_name,
        prefix=clean_prefix,
        tax_id=clean_tax_id,
        status=CompanyStatus.ACTIVE.value,
        is_ksc_entity=is_ksc_entity,
        default_approver_id=default_approver_id,
    )
    session.add(company)
    await _flush_mapping_conflicts(session)
    await audit.record(
        session,
        company_id=None,
        actor=actor,
        entity_type=EntityType.COMPANY,
        entity_id=company.id,
        action=AuditAction.CREATE,
        diff=make_diff({}, snapshot(company)),
    )
    await session.refresh(company)
    return company


async def update_company(
    session: AsyncSession, *, actor: Actor, company_id: UUID, changes: Mapping[str, Any]
) -> Company:
    """Apply the provided fields; ``prefix`` may only be repeated unchanged."""
    unknown = set(changes) - UPDATABLE_FIELDS
    if unknown:
        raise ValueError(f"fields not updatable: {sorted(unknown)}")
    company = await _lock(session, company_id)
    if "prefix" in changes and changes["prefix"] != company.prefix:
        raise ProblemError(
            status=422,
            code="company.prefix_immutable",
            detail="Prefiksu spółki nie można zmienić po jej utworzeniu.",
            extra={"field": "prefix"},
        )
    before = snapshot(company)
    try:
        if "name" in changes:
            name = normalize_name(str(changes["name"]))
            if name != company.name:
                await _ensure_name_free(session, name, except_id=company.id)
            company.name = name
        if "tax_id" in changes:
            company.tax_id = normalize_tax_id(changes["tax_id"])
    except InvalidCompanyDataError as exc:
        raise invalid(exc) from exc
    if "is_ksc_entity" in changes:
        company.is_ksc_entity = bool(changes["is_ksc_entity"])
    if "default_approver_id" in changes:
        approver = changes["default_approver_id"]
        if approver != company.default_approver_id:
            await _validate_approver(session, approver)
        company.default_approver_id = approver

    diff = make_diff(before, snapshot(company))
    if not diff:
        return company
    await _flush_mapping_conflicts(session)
    await audit.record(
        session,
        company_id=None,
        actor=actor,
        entity_type=EntityType.COMPANY,
        entity_id=company.id,
        action=AuditAction.UPDATE,
        diff=diff,
    )
    await session.refresh(company)
    return company


async def archive_company(session: AsyncSession, *, actor: Actor, company_id: UUID) -> Company:
    company = await _lock(session, company_id)
    if company.status == CompanyStatus.ARCHIVED:
        raise ProblemError(
            status=409,
            code="company.already_archived",
            detail="Spółka jest już zarchiwizowana.",
        )
    before = snapshot(company)
    company.status = CompanyStatus.ARCHIVED.value
    await session.flush()
    await audit.record(
        session,
        company_id=None,
        actor=actor,
        entity_type=EntityType.COMPANY,
        entity_id=company.id,
        action=AuditAction.ARCHIVE,
        diff=make_diff(before, snapshot(company)),
    )
    await session.refresh(company)
    return company


async def list_companies(
    session: AsyncSession,
    *,
    company_ids: Collection[UUID] | None,
    limit: int,
    offset: int,
) -> tuple[list[Company], int]:
    """``company_ids=None`` lists all companies (admin path only)."""
    stmt = select(Company)
    if company_ids is not None:
        if not company_ids:
            return [], 0
        stmt = stmt.where(Company.id.in_(list(company_ids)))
    total = (await session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = await session.execute(
        stmt.order_by(Company.name, Company.id).limit(limit).offset(offset)
    )
    return list(rows.scalars().all()), int(total)


@dataclass(frozen=True, slots=True)
class CompanyCounts:
    """Counters of the admin companies table (§10.4): CI and members per role."""

    active_ci: int = 0
    all_ci: int = 0
    editors: int = 0
    approvers: int = 0
    auditors: int = 0
    viewers: int = 0


async def company_counts(
    session: AsyncSession, company_ids: Collection[UUID]
) -> dict[UUID, CompanyCounts]:
    """Counters for the listed companies (two grouped queries, no per-company round trip).

    Rows outside the transaction's RLS scope are not counted: the caller must have the
    companies in scope (members: their companies; admin path: widened, ADR 0015).
    """
    ids = list(company_ids)
    if not ids:
        return {}
    ci_rows = await session.execute(
        select(
            ConfigurationItem.company_id,
            func.count().filter(ConfigurationItem.is_active.is_(True)),
            func.count(),
        )
        .where(ConfigurationItem.company_id.in_(ids))
        .group_by(ConfigurationItem.company_id)
    )
    ci = {cid: (int(active), int(total)) for cid, active, total in ci_rows.all()}
    role_rows = await session.execute(
        select(CompanyMembership.company_id, CompanyMembership.role, func.count())
        .where(CompanyMembership.company_id.in_(ids))
        .group_by(CompanyMembership.company_id, CompanyMembership.role)
    )
    roles: dict[UUID, dict[str, int]] = {}
    for cid, role, count in role_rows.all():
        roles.setdefault(cid, {})[str(role)] = int(count)
    result = {}
    for cid in ids:
        active, total = ci.get(cid, (0, 0))
        per_role = roles.get(cid, {})
        result[cid] = CompanyCounts(
            active_ci=active,
            all_ci=total,
            editors=per_role.get("editor", 0),
            approvers=per_role.get("approver", 0),
            auditors=per_role.get("auditor", 0),
            viewers=per_role.get("viewer", 0),
        )
    return result
