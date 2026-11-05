"""Companies and company members (CLAUDE.md §8). Writes: app admin only."""

from __future__ import annotations

from dataclasses import asdict
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request, Response

from app.auth.principal import CompanyContext, CurrentUser
from app.db import SessionDep, get_database, run_read_only
from app.domain.companies import InvalidCompanyDataError
from app.permissions import (
    Action,
    CompanyVisibility,
    Role,
    require,
    require_admin_company,
    require_company,
    visible_companies,
)
from app.schemas.common import DEFAULT_LIMIT, MAX_LIMIT, Page
from app.schemas.identity import (
    CompanyCreate,
    CompanyListItem,
    CompanyOut,
    CompanyUpdate,
    MemberOut,
    MemberRolesIn,
)
from app.services import companies as companies_service
from app.services import memberships as memberships_service
from app.services import users as users_service

router = APIRouter(prefix="/companies", tags=["companies"])

Limit = Annotated[int, Query(ge=1, le=MAX_LIMIT)]
Offset = Annotated[int, Query(ge=0)]
NON_NULLABLE = ("name", "prefix", "is_ksc_entity")


@router.get("", response_model=Page[CompanyListItem])
async def list_companies(
    request: Request,
    session: SessionDep,
    visibility: CompanyVisibility = visible_companies(
        Action.REGISTER_VIEW, admin_action=Action.COMPANY_MANAGE
    ),
    limit: Limit = DEFAULT_LIMIT,
    offset: Offset = 0,
) -> Page[CompanyListItem]:
    user = visibility.user
    items, total = await companies_service.list_companies(
        session,
        company_ids=None if visibility.all else visibility.company_ids,
        limit=limit,
        offset=offset,
    )
    # Counters in a SEPARATE read-only transaction scoped to the companies of this page
    # (no admin_scope): the CI inventory has no admin_scope policy (ADR 0011 §7), and the
    # request transaction must never be widened (ADR 0015 §2). For members the page holds
    # only their own companies, so the scope is the same as their membership scope.
    page_ids = [c.id for c in items]
    counts = (
        await run_read_only(
            get_database(request),
            lambda s: companies_service.company_counts(s, page_ids),
            company_ids=page_ids,
        )
        if page_ids
        else {}
    )
    return Page[CompanyListItem](
        items=[
            CompanyListItem.model_validate(
                {
                    **CompanyOut.model_validate(c).model_dump(),
                    "my_roles": sorted(r.value for r in user.roles_in(c.id)),
                    "counts": asdict(counts[c.id]),
                }
            )
            for c in items
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=CompanyOut, status_code=201)
async def create_company(
    body: CompanyCreate,
    request: Request,
    response: Response,
    session: SessionDep,
    user: CurrentUser = require(Action.COMPANY_MANAGE),
) -> CompanyOut:
    company = await companies_service.create_company(
        session,
        actor=user.actor(),
        name=body.name,
        prefix=body.prefix,
        tax_id=body.tax_id,
        is_ksc_entity=body.is_ksc_entity,
        default_approver_id=body.default_approver_id,
    )
    response.headers["Location"] = f"{request.url.path}/{company.id}"
    return CompanyOut.model_validate(company)


@router.patch("/{company_id}", response_model=CompanyOut)
async def update_company(
    body: CompanyUpdate,
    session: SessionDep,
    ctx: CompanyContext = require_admin_company(Action.COMPANY_MANAGE),
) -> CompanyOut:
    changes = {name: getattr(body, name) for name in body.model_fields_set}
    for name in NON_NULLABLE:
        if name in changes and changes[name] is None:
            raise companies_service.invalid(
                InvalidCompanyDataError(name, "To pole nie może być puste.")
            )
    company = await companies_service.update_company(
        session, actor=ctx.user.actor(), company_id=ctx.company_id, changes=changes
    )
    return CompanyOut.model_validate(company)


@router.post("/{company_id}/archive", response_model=CompanyOut)
async def archive_company(
    session: SessionDep,
    ctx: CompanyContext = require_admin_company(Action.COMPANY_MANAGE),
) -> CompanyOut:
    company = await companies_service.archive_company(
        session, actor=ctx.user.actor(), company_id=ctx.company_id
    )
    return CompanyOut.model_validate(company)


@router.get("/{company_id}/members", response_model=Page[MemberOut])
async def list_members(
    session: SessionDep,
    ctx: CompanyContext = require_company(
        Action.REGISTER_VIEW, admin_action=Action.MEMBERSHIP_MANAGE
    ),
    limit: Limit = DEFAULT_LIMIT,
    offset: Offset = 0,
) -> Page[MemberOut]:
    members, total = await memberships_service.page_members(
        session, ctx.company_id, limit=limit, offset=offset
    )
    items = [
        MemberOut(
            user_id=m.user.id,
            display_name=m.user.display_name,
            email=m.user.email,
            is_active=m.user.is_active,
            roles=sorted(r.value for r in m.roles),
        )
        for m in members
    ]
    return Page[MemberOut](items=items, total=total, limit=limit, offset=offset)


@router.put("/{company_id}/members/{user_id}", response_model=MemberOut)
async def set_member_roles(
    user_id: UUID,
    body: MemberRolesIn,
    session: SessionDep,
    ctx: CompanyContext = require_admin_company(Action.MEMBERSHIP_MANAGE),
) -> MemberOut:
    """Set the user's roles in the company to exactly ``roles`` (``[]`` removes access)."""
    change = await memberships_service.set_member_roles(
        session,
        actor=ctx.actor(),
        company_id=ctx.company_id,
        user_id=user_id,
        roles={Role(r) for r in body.roles},
    )
    user = await users_service.get_user(session, user_id)
    assert user is not None  # noqa: S101 - set_member_roles raised 404 otherwise
    return MemberOut(
        user_id=user.id,
        display_name=user.display_name,
        email=user.email,
        is_active=user.is_active,
        roles=sorted(r.value for r in change.after),
    )
