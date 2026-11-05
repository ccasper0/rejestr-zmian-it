"""Global dictionaries (CLAUDE.md §4.1, §8): change categories and CI types.

Reads: anybody with a role in any company, and the app admin (``require_in_any_company``,
ADR 0011). Writes: app admin only (``dictionary.manage``, explicit admin path).
"""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Query, Request, Response

from app.auth.principal import CurrentUser
from app.db import SessionDep
from app.domain.dictionaries import InvalidDataError, Risk
from app.errors import ProblemError
from app.permissions import Action, require, require_in_any_company
from app.schemas.common import DEFAULT_LIMIT, MAX_LIMIT, Page
from app.schemas.inventory import (
    CategoryCreate,
    CategoryOut,
    CategoryUpdate,
    CiTypeCreate,
    CiTypeOut,
    CiTypeUpdate,
)
from app.services import categories as categories_service
from app.services import ci_types as ci_types_service

categories_router = APIRouter(prefix="/categories", tags=["dictionaries"])
ci_types_router = APIRouter(prefix="/ci-types", tags=["dictionaries"])

Limit = Annotated[int, Query(ge=1, le=MAX_LIMIT)]
Offset = Annotated[int, Query(ge=0)]


def provided(body: Any, non_nullable: tuple[str, ...], invalid: Any) -> dict[str, Any]:
    """Fields present in a PATCH body; ``null`` for a non-nullable field is a 422."""
    changes = {name: getattr(body, name) for name in body.model_fields_set}
    for name in non_nullable:
        if name in changes and changes[name] is None:
            error: ProblemError = invalid(InvalidDataError(name, "To pole nie może być puste."))
            raise error
    return changes


# --------------------------------------------------------------------------- categories


@categories_router.get("", response_model=Page[CategoryOut])
async def list_categories(
    session: SessionDep,
    _: CurrentUser = require_in_any_company(Action.REGISTER_VIEW),
    active: bool | None = None,
    parent_id: UUID | None = None,
    top_level: Annotated[bool, Query(description="Tylko kategorie główne")] = False,
    limit: Limit = DEFAULT_LIMIT,
    offset: Offset = 0,
) -> Page[CategoryOut]:
    """Categories in tree order (each category followed by its subcategories)."""
    items, total = await categories_service.list_categories(
        session,
        active=active,
        parent_id=parent_id,
        roots_only=top_level,
        limit=limit,
        offset=offset,
    )
    return Page[CategoryOut](
        items=[CategoryOut.model_validate(c) for c in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@categories_router.post("", response_model=CategoryOut, status_code=201)
async def create_category(
    body: CategoryCreate,
    request: Request,
    response: Response,
    session: SessionDep,
    user: CurrentUser = require(Action.DICTIONARY_MANAGE),
) -> CategoryOut:
    category = await categories_service.create_category(
        session,
        actor=user.actor(),
        code=body.code,
        name=body.name,
        parent_id=body.parent_id,
        requires_approval=body.requires_approval,
        default_risk=Risk(body.default_risk) if body.default_risk else None,
        requires_ci_owner_consent=body.requires_ci_owner_consent,
    )
    response.headers["Location"] = f"{request.url.path}/{category.id}"
    return CategoryOut.model_validate(category)


@categories_router.patch("/{category_id}", response_model=CategoryOut)
async def update_category(
    category_id: UUID,
    body: CategoryUpdate,
    session: SessionDep,
    user: CurrentUser = require(Action.DICTIONARY_MANAGE),
) -> CategoryOut:
    changes = provided(
        body,
        (
            "code",
            "name",
            "requires_approval",
            "requires_ci_owner_consent",
            "default_risk",
            "is_active",
        ),
        categories_service.invalid,
    )
    category = await categories_service.update_category(
        session, actor=user.actor(), category_id=category_id, changes=changes
    )
    return CategoryOut.model_validate(category)


# --------------------------------------------------------------------------- CI types


@ci_types_router.get("", response_model=Page[CiTypeOut])
async def list_ci_types(
    session: SessionDep,
    _: CurrentUser = require_in_any_company(Action.REGISTER_VIEW),
    active: bool | None = None,
    limit: Limit = DEFAULT_LIMIT,
    offset: Offset = 0,
) -> Page[CiTypeOut]:
    items, total = await ci_types_service.list_ci_types(
        session, active=active, limit=limit, offset=offset
    )
    return Page[CiTypeOut](
        items=[CiTypeOut.model_validate(t) for t in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@ci_types_router.post("", response_model=CiTypeOut, status_code=201)
async def create_ci_type(
    body: CiTypeCreate,
    request: Request,
    response: Response,
    session: SessionDep,
    user: CurrentUser = require(Action.DICTIONARY_MANAGE),
) -> CiTypeOut:
    ci_type = await ci_types_service.create_ci_type(
        session, actor=user.actor(), code=body.code, name=body.name
    )
    response.headers["Location"] = f"{request.url.path}/{ci_type.id}"
    return CiTypeOut.model_validate(ci_type)


@ci_types_router.patch("/{ci_type_id}", response_model=CiTypeOut)
async def update_ci_type(
    ci_type_id: UUID,
    body: CiTypeUpdate,
    session: SessionDep,
    user: CurrentUser = require(Action.DICTIONARY_MANAGE),
) -> CiTypeOut:
    changes = provided(body, ("code", "name", "is_active"), ci_types_service.invalid)
    ci_type = await ci_types_service.update_ci_type(
        session, actor=user.actor(), ci_type_id=ci_type_id, changes=changes
    )
    return CiTypeOut.model_validate(ci_type)
