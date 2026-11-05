"""CI types: global dictionary (CLAUDE.md 4.1; ADR 0011).

Never deleted, only deactivated (existing CI keep their type; new CI and type changes
require an active type). ``code`` is immutable (also enforced by a trigger). Every change
is written to the GLOBAL audit chain; writes only on the explicit admin path (RLS).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.audit import Actor, AuditAction, EntityType, make_diff
from app.domain.dictionaries import InvalidDataError, normalize_name, validate_ci_type_code
from app.errors import ProblemError
from app.models import CiType
from app.services import audit

AUDITED_FIELDS = ("code", "name", "is_active")
UPDATABLE_FIELDS = frozenset(AUDITED_FIELDS)


def snapshot(ci_type: CiType) -> dict[str, object]:
    return {name: getattr(ci_type, name) for name in AUDITED_FIELDS}


def invalid(error: InvalidDataError) -> ProblemError:
    return ProblemError(
        status=422, code="ci_type.invalid_data", detail=error.message, extra={"field": error.field}
    )


def not_found() -> ProblemError:
    return ProblemError(
        status=404, code="ci_type.not_found", detail="Nie znaleziono typu obiektu (CI)."
    )


def _code_taken() -> ProblemError:
    return ProblemError(
        status=409, code="ci_type.code_taken", detail="Typ obiektu o tym kodzie już istnieje."
    )


async def get_ci_type(session: AsyncSession, ci_type_id: UUID) -> CiType | None:
    return await session.get(CiType, ci_type_id)


async def get_ci_type_by_code(session: AsyncSession, code: str) -> CiType | None:
    result = await session.execute(select(CiType).where(CiType.code == code))
    return result.scalar_one_or_none()


async def list_ci_types(
    session: AsyncSession, *, active: bool | None = None, limit: int, offset: int
) -> tuple[list[CiType], int]:
    stmt = select(CiType)
    if active is not None:
        stmt = stmt.where(CiType.is_active.is_(active))
    total = (await session.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = await session.execute(
        stmt.order_by(CiType.name, CiType.code).limit(limit).offset(offset)
    )
    return list(rows.scalars().all()), int(total)


async def _flush(session: AsyncSession) -> None:
    try:
        async with session.begin_nested():
            await session.flush()
    except IntegrityError as exc:
        if "uq_ci_types_code" in str(exc.orig):
            raise _code_taken() from exc
        raise


async def create_ci_type(
    session: AsyncSession,
    *,
    actor: Actor,
    code: str,
    name: str,
    context: Mapping[str, object] | None = None,
) -> CiType:
    """``context`` is merged into the audit entry's context (e.g. the CLI operator)."""
    try:
        clean_code = validate_ci_type_code(code)
        clean_name = normalize_name(name)
    except InvalidDataError as exc:
        raise invalid(exc) from exc
    if await get_ci_type_by_code(session, clean_code) is not None:
        raise _code_taken()
    ci_type = CiType(id=uuid4(), code=clean_code, name=clean_name, is_active=True)
    session.add(ci_type)
    await _flush(session)
    await audit.record(
        session,
        company_id=None,
        actor=actor,
        entity_type=EntityType.CI_TYPE,
        entity_id=ci_type.id,
        action=AuditAction.CREATE,
        diff=make_diff({}, snapshot(ci_type)),
        context=dict(context or {}),
    )
    await session.refresh(ci_type)
    return ci_type


async def update_ci_type(
    session: AsyncSession, *, actor: Actor, ci_type_id: UUID, changes: Mapping[str, Any]
) -> CiType:
    """Apply the provided fields; ``code`` only unchanged. No change = no audit entry."""
    unknown = set(changes) - UPDATABLE_FIELDS
    if unknown:
        raise ValueError(f"fields not updatable: {sorted(unknown)}")
    result = await session.execute(
        select(CiType)
        .where(CiType.id == ci_type_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    ci_type = result.scalar_one_or_none()
    if ci_type is None:
        raise not_found()
    if "code" in changes and changes["code"] != ci_type.code:
        raise ProblemError(
            status=422,
            code="ci_type.code_immutable",
            detail="Kodu typu obiektu nie można zmienić po jego utworzeniu.",
            extra={"field": "code"},
        )
    before = snapshot(ci_type)
    try:
        if "name" in changes:
            ci_type.name = normalize_name(str(changes["name"]))
    except InvalidDataError as exc:
        raise invalid(exc) from exc
    if "is_active" in changes:
        ci_type.is_active = bool(changes["is_active"])
    diff = make_diff(before, snapshot(ci_type))
    if not diff:
        return ci_type
    await session.flush()
    deactivated = before["is_active"] is True and ci_type.is_active is False
    await audit.record(
        session,
        company_id=None,
        actor=actor,
        entity_type=EntityType.CI_TYPE,
        entity_id=ci_type.id,
        action=AuditAction.DEACTIVATE if deactivated else AuditAction.UPDATE,
        diff=diff,
        context={"code": ci_type.code},
    )
    await session.refresh(ci_type)
    return ci_type
