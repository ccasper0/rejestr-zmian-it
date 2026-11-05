"""Change categories: global dictionary, two levels (CLAUDE.md 4.1, 13; ADR 0011).

Categories are never deleted, only deactivated. ``code`` and ``parent_id`` are immutable
(also enforced by a trigger). Every change is written to the GLOBAL audit chain in the
same transaction. The caller must be on the explicit admin path (RLS: dictionaries are
written only with ``app.admin_scope = on``).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.domain.audit import Actor, AuditAction, EntityType, make_diff
from app.domain.dictionaries import (
    InvalidDataError,
    Risk,
    normalize_name,
    validate_category_code,
)
from app.errors import ProblemError
from app.models import ChangeCategory
from app.services import audit

AUDITED_FIELDS = (
    "code",
    "name",
    "parent_id",
    "requires_approval",
    "requires_ci_owner_consent",
    "default_risk",
    "is_active",
)
UPDATABLE_FIELDS = frozenset(AUDITED_FIELDS)


def snapshot(category: ChangeCategory) -> dict[str, object]:
    return {name: getattr(category, name) for name in AUDITED_FIELDS}


def invalid(error: InvalidDataError) -> ProblemError:
    return ProblemError(
        status=422, code="category.invalid_data", detail=error.message, extra={"field": error.field}
    )


def not_found() -> ProblemError:
    return ProblemError(
        status=404, code="category.not_found", detail="Nie znaleziono kategorii zmian."
    )


def _code_taken() -> ProblemError:
    return ProblemError(
        status=409, code="category.code_taken", detail="Kategoria o tym kodzie już istnieje."
    )


async def get_category(session: AsyncSession, category_id: UUID) -> ChangeCategory | None:
    return await session.get(ChangeCategory, category_id)


async def get_category_by_code(session: AsyncSession, code: str) -> ChangeCategory | None:
    result = await session.execute(select(ChangeCategory).where(ChangeCategory.code == code))
    return result.scalar_one_or_none()


async def list_categories(
    session: AsyncSession,
    *,
    active: bool | None = None,
    parent_id: UUID | None = None,
    roots_only: bool = False,
    limit: int,
    offset: int,
) -> tuple[list[ChangeCategory], int]:
    """Categories in tree order: each category followed by its subcategories (by code)."""
    parent = aliased(ChangeCategory)
    stmt = select(ChangeCategory).outerjoin(parent, ChangeCategory.parent_id == parent.id)
    if active is not None:
        stmt = stmt.where(ChangeCategory.is_active.is_(active))
    if parent_id is not None:
        stmt = stmt.where(ChangeCategory.parent_id == parent_id)
    if roots_only:
        stmt = stmt.where(ChangeCategory.parent_id.is_(None))
    total = (await session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = await session.execute(
        stmt.order_by(
            func.coalesce(parent.code, ChangeCategory.code),
            ChangeCategory.parent_id.is_not(None),
            ChangeCategory.code,
        )
        .limit(limit)
        .offset(offset)
    )
    return list(rows.scalars().all()), int(total)


async def _flush(session: AsyncSession) -> None:
    """Flush in a savepoint; a concurrent duplicate code becomes 409 instead of a 500."""
    try:
        async with session.begin_nested():
            await session.flush()
    except IntegrityError as exc:
        if "uq_change_categories_code" in str(exc.orig):
            raise _code_taken() from exc
        raise


async def create_category(
    session: AsyncSession,
    *,
    actor: Actor,
    code: str,
    name: str,
    parent_id: UUID | None = None,
    requires_approval: bool | None = None,
    default_risk: Risk | None = None,
    requires_ci_owner_consent: bool = False,
    context: Mapping[str, object] | None = None,
) -> ChangeCategory:
    """New active category (``parent_id=None``) or subcategory.

    A subcategory without ``requires_approval`` / ``default_risk`` takes its category's
    values; a category defaults to the safe side: approval required, medium risk.
    ``requires_ci_owner_consent`` (ADR 0012 §5) only tightens: a subcategory of a category
    requiring the consent requires it anyway.
    """
    try:
        clean_code = validate_category_code(code)
        clean_name = normalize_name(name)
    except InvalidDataError as exc:
        raise invalid(exc) from exc
    parent: ChangeCategory | None = None
    if parent_id is not None:
        # FOR SHARE: a concurrent deactivation of the parent (update_category, FOR UPDATE)
        # either waits for this transaction or - committed first - is seen here, so an
        # active subcategory of an inactive category cannot be created.
        parent = (
            await session.execute(
                select(ChangeCategory)
                .where(ChangeCategory.id == parent_id)
                .with_for_update(read=True)
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()
        if parent is None:
            raise ProblemError(
                status=422,
                code="category.parent_not_found",
                detail="Nie znaleziono kategorii nadrzędnej.",
                extra={"field": "parent_id"},
            )
        if parent.parent_id is not None:
            raise ProblemError(
                status=422,
                code="category.depth_exceeded",
                detail="Kategorie mają dwa poziomy: podkategoria nie może mieć podkategorii.",
                extra={"field": "parent_id"},
            )
        if not parent.is_active:
            raise ProblemError(
                status=422,
                code="category.parent_inactive",
                detail="Nie można dodać podkategorii do nieaktywnej kategorii.",
                extra={"field": "parent_id"},
            )
    if await get_category_by_code(session, clean_code) is not None:
        raise _code_taken()

    if requires_approval is None:
        requires_approval = parent.requires_approval if parent is not None else True
    if default_risk is None:
        default_risk = Risk(parent.default_risk) if parent is not None else Risk.MEDIUM
    category = ChangeCategory(
        id=uuid4(),
        code=clean_code,
        name=clean_name,
        parent_id=parent_id,
        requires_approval=requires_approval,
        requires_ci_owner_consent=requires_ci_owner_consent,
        default_risk=Risk(default_risk).value,
        is_active=True,
    )
    session.add(category)
    await _flush(session)
    await audit.record(
        session,
        company_id=None,
        actor=actor,
        entity_type=EntityType.CATEGORY,
        entity_id=category.id,
        action=AuditAction.CREATE,
        diff=make_diff({}, snapshot(category)),
        context={
            **({"parent_code": parent.code} if parent is not None else {}),
            **(context or {}),
        },
    )
    await session.refresh(category)
    return category


async def _lock(session: AsyncSession, category_id: UUID) -> ChangeCategory:
    result = await session.execute(
        select(ChangeCategory)
        .where(ChangeCategory.id == category_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    category = result.scalar_one_or_none()
    if category is None:
        raise not_found()
    return category


async def update_category(
    session: AsyncSession, *, actor: Actor, category_id: UUID, changes: Mapping[str, Any]
) -> ChangeCategory:
    """Apply the provided fields. ``code`` and ``parent_id`` only unchanged (immutable).

    ``is_active = false`` is recorded as ``deactivate``; anything else as ``update``.
    A request that changes nothing writes nothing (no audit entry).
    """
    unknown = set(changes) - UPDATABLE_FIELDS
    if unknown:
        raise ValueError(f"fields not updatable: {sorted(unknown)}")
    category = await _lock(session, category_id)
    if "code" in changes and changes["code"] != category.code:
        raise ProblemError(
            status=422,
            code="category.code_immutable",
            detail="Kodu kategorii nie można zmienić po jej utworzeniu.",
            extra={"field": "code"},
        )
    if "parent_id" in changes and changes["parent_id"] != category.parent_id:
        raise ProblemError(
            status=422,
            code="category.parent_immutable",
            detail="Nie można przenieść kategorii do innej kategorii nadrzędnej.",
            extra={"field": "parent_id"},
        )
    before = snapshot(category)
    try:
        if "name" in changes:
            category.name = normalize_name(str(changes["name"]))
    except InvalidDataError as exc:
        raise invalid(exc) from exc
    if "requires_approval" in changes:
        category.requires_approval = bool(changes["requires_approval"])
    if "requires_ci_owner_consent" in changes:
        category.requires_ci_owner_consent = bool(changes["requires_ci_owner_consent"])
    if "default_risk" in changes:
        category.default_risk = Risk(changes["default_risk"]).value
    if "is_active" in changes:
        category.is_active = bool(changes["is_active"])

    diff = make_diff(before, snapshot(category))
    if not diff:
        return category
    await session.flush()
    deactivated = before["is_active"] is True and category.is_active is False
    await audit.record(
        session,
        company_id=None,
        actor=actor,
        entity_type=EntityType.CATEGORY,
        entity_id=category.id,
        action=AuditAction.DEACTIVATE if deactivated else AuditAction.UPDATE,
        diff=diff,
        context={"code": category.code},
    )
    await session.refresh(category)
    return category
