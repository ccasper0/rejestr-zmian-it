"""Company configuration: available categories and the CI inventory (CLAUDE.md §5, §8).

- ``/companies/{id}/categories``: read by members (and the app admin on the admin path);
  ``PUT`` - app admin only (company configuration, ``company.manage``).
- ``/companies/{id}/ci``: read by members (and the app admin on the admin path); writes by
  editors and approvers of the company and by the app admin on the explicit admin path
  (``ci.manage`` - the admin holds it in the matrix, §5; ADR 0011).
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request, Response

from app.api.v1.dictionaries import provided
from app.auth.principal import CompanyContext
from app.db import SessionDep
from app.permissions import Action, require_admin_company, require_company
from app.schemas.common import DEFAULT_LIMIT, MAX_LIMIT, Page, SafeLine
from app.schemas.inventory import (
    CiCreate,
    CiOut,
    CiUpdate,
    CompanyCategoriesIn,
    CompanyCategoriesOut,
    CompanyCategoryOut,
)
from app.services import company_categories as company_categories_service
from app.services import configuration_items as ci_service

router = APIRouter(prefix="/companies", tags=["inventory"])

Limit = Annotated[int, Query(ge=1, le=MAX_LIMIT)]
Offset = Annotated[int, Query(ge=0)]


def _categories_out(
    items: list[company_categories_service.AvailableCategory],
) -> CompanyCategoriesOut:
    return CompanyCategoriesOut(
        items=[
            CompanyCategoryOut(
                category_id=i.category.id,
                code=i.category.code,
                name=i.category.name,
                requires_approval=i.category.requires_approval,
                default_risk=i.category.default_risk,
                is_active=i.category.is_active,
                approver_override_id=i.approver_override_id,
            )
            for i in items
        ]
    )


def _ci_out(row: ci_service.CiRow) -> CiOut:
    item = row.item
    return CiOut(
        id=item.id,
        company_id=item.company_id,
        ci_type_id=item.ci_type_id,
        ci_type_code=row.ci_type.code,
        ci_type_name=row.ci_type.name,
        identifier=item.identifier,
        name=item.name,
        description=item.description,
        owner_user_id=item.owner_user_id,
        is_active=item.is_active,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


# --------------------------------------------------------------------------- categories


@router.get("/{company_id}/categories", response_model=CompanyCategoriesOut)
async def list_company_categories(
    session: SessionDep,
    ctx: CompanyContext = require_company(Action.REGISTER_VIEW, admin_action=Action.COMPANY_MANAGE),
) -> CompanyCategoriesOut:
    """Top-level categories available in the company (subcategories: ``GET /categories``)."""
    items = await company_categories_service.list_company_categories(session, ctx.company_id)
    return _categories_out(items)


@router.put("/{company_id}/categories", response_model=CompanyCategoriesOut)
async def set_company_categories(
    body: CompanyCategoriesIn,
    session: SessionDep,
    ctx: CompanyContext = require_admin_company(Action.COMPANY_MANAGE),
) -> CompanyCategoriesOut:
    """Set the FULL list of available categories (missing ones are withdrawn)."""
    items = await company_categories_service.set_company_categories(
        session,
        actor=ctx.actor(),
        company_id=ctx.company_id,
        assignments=[
            company_categories_service.Assignment(
                category_id=c.category_id, approver_override_id=c.approver_override_id
            )
            for c in body.categories
        ],
    )
    return _categories_out(items)


# --------------------------------------------------------------------------- CI


@router.get("/{company_id}/ci", response_model=Page[CiOut])
async def list_ci(
    session: SessionDep,
    ctx: CompanyContext = require_company(Action.REGISTER_VIEW, admin_action=Action.CI_MANAGE),
    q: Annotated[
        SafeLine | None, Query(max_length=200, description="Szukaj w identyfikatorze i nazwie")
    ] = None,
    type: Annotated[
        list[SafeLine] | None, Query(max_length=50, description="Kody typów obiektów")
    ] = None,
    active: bool | None = None,
    limit: Limit = DEFAULT_LIMIT,
    offset: Offset = 0,
) -> Page[CiOut]:
    rows, total = await ci_service.list_items(
        session,
        ctx.company_id,
        q=q,
        type_codes=type or (),
        active=active,
        limit=limit,
        offset=offset,
    )
    return Page[CiOut](items=[_ci_out(r) for r in rows], total=total, limit=limit, offset=offset)


@router.post("/{company_id}/ci", response_model=CiOut, status_code=201)
async def create_ci(
    body: CiCreate,
    request: Request,
    response: Response,
    session: SessionDep,
    ctx: CompanyContext = require_company(Action.CI_MANAGE, admin_action=Action.CI_MANAGE),
) -> CiOut:
    row = await ci_service.create_item(
        session,
        actor=ctx.actor(),
        company=ctx.company,
        ci_type_id=body.ci_type_id,
        identifier=body.identifier,
        name=body.name,
        description=body.description,
        owner_user_id=body.owner_user_id,
    )
    response.headers["Location"] = f"{request.url.path}/{row.item.id}"
    return _ci_out(row)


@router.get("/{company_id}/ci/{ci_id}", response_model=CiOut)
async def get_ci(
    ci_id: UUID,
    session: SessionDep,
    ctx: CompanyContext = require_company(Action.REGISTER_VIEW, admin_action=Action.CI_MANAGE),
) -> CiOut:
    row = await ci_service.get_item(session, ctx.company_id, ci_id)
    if row is None:
        raise ci_service.not_found()
    return _ci_out(row)


@router.patch("/{company_id}/ci/{ci_id}", response_model=CiOut)
async def update_ci(
    ci_id: UUID,
    body: CiUpdate,
    session: SessionDep,
    ctx: CompanyContext = require_company(Action.CI_MANAGE, admin_action=Action.CI_MANAGE),
) -> CiOut:
    changes = provided(body, ("ci_type_id", "identifier", "name", "is_active"), ci_service.invalid)
    row = await ci_service.update_item(
        session, actor=ctx.actor(), company=ctx.company, ci_id=ci_id, changes=changes
    )
    return _ci_out(row)
