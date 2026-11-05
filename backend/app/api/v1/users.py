"""Users (app admin): ``GET /users`` — directory for role assignment; ``GET /users/{id}`` —
one user with the roles in every company (ADR 0015); local accounts (ADR 0018):
``POST /users`` (temporary password returned once), ``POST /users/{id}/reset-password``,
``PATCH /users/{id}`` (name, (de)activation, admin flag)."""

from __future__ import annotations

from datetime import timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, Request, Response
from sqlalchemy import select

from app.auth.principal import CurrentUser
from app.config import Settings
from app.db import SessionDep
from app.errors import ProblemError
from app.models import Company, User, UserCredential
from app.permissions import Action, require
from app.schemas.common import DEFAULT_LIMIT, MAX_LIMIT, Page, SafeLine
from app.schemas.identity import (
    UserCreate,
    UserDetailOut,
    UserMembershipOut,
    UserOut,
    UserUpdate,
    UserWithTemporaryPasswordOut,
)
from app.services import memberships as memberships_service
from app.services import users as users_service

router = APIRouter(prefix="/users", tags=["users"])

NO_STORE = {"Cache-Control": "no-store", "Pragma": "no-cache"}


def _temp_password_ttl(request: Request) -> timedelta:
    settings: Settings = request.app.state.settings
    return timedelta(hours=settings.temp_password_ttl_hours)


def user_out(user: User, credential: UserCredential | None) -> UserOut:
    """The user with the password STATE of the account (never the hash)."""
    out = UserOut.model_validate(user)
    if credential is None:
        return out
    return out.model_copy(
        update={
            "has_password": True,
            "must_change_password": credential.must_change_password,
            "password_changed_at": credential.password_changed_at,
            "locked_until": credential.locked_until,
            "temp_password_expires_at": credential.temp_password_expires_at,
        }
    )


@router.get("", response_model=Page[UserOut])
async def list_users(
    session: SessionDep,
    _: CurrentUser = require(Action.MEMBERSHIP_MANAGE),
    q: Annotated[
        SafeLine | None, Query(max_length=200, description="Szukaj w nazwie/e-mailu")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_LIMIT)] = DEFAULT_LIMIT,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Page[UserOut]:
    items, total = await users_service.list_users(session, q=q, limit=limit, offset=offset)
    credentials = await users_service.credentials_by_user(session, [u.id for u in items])
    return Page[UserOut](
        items=[user_out(u, credentials.get(u.id)) for u in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{user_id}", response_model=UserDetailOut)
async def get_user(
    user_id: UUID,
    session: SessionDep,
    _: CurrentUser = require(Action.MEMBERSHIP_MANAGE),
) -> UserDetailOut:
    """The user and their roles in every company (admin path: all memberships visible)."""
    user = await users_service.get_user(session, user_id)
    if user is None:
        raise ProblemError(status=404, code="user.not_found", detail="Nie znaleziono użytkownika.")
    credentials = await users_service.credentials_by_user(session, [user.id])
    roles = await memberships_service.roles_by_company(session, user_id)
    companies = []
    if roles:
        rows = await session.execute(
            select(Company).where(Company.id.in_(list(roles))).order_by(Company.name, Company.id)
        )
        companies = list(rows.scalars().all())
    return UserDetailOut.model_validate(
        {
            **user_out(user, credentials.get(user.id)).model_dump(),
            "memberships": [
                UserMembershipOut(
                    company_id=c.id,
                    company_name=c.name,
                    company_prefix=c.prefix,
                    company_status=c.status,
                    roles=sorted(r.value for r in roles[c.id]),
                )
                for c in companies
            ],
        }
    )


@router.post("", response_model=UserWithTemporaryPasswordOut, status_code=201)
async def create_user(
    body: UserCreate,
    request: Request,
    response: Response,
    session: SessionDep,
    admin: CurrentUser = require(Action.USER_MANAGE),
) -> UserWithTemporaryPasswordOut:
    """A local account with a generated temporary password, shown ONCE (ADR 0018 §5)."""
    account = await users_service.create_local_account(
        session,
        actor=admin.actor(),
        email=body.email,
        display_name=body.display_name,
        is_app_admin=body.is_app_admin,
        context={"source": "admin"},
        temp_password_ttl=_temp_password_ttl(request),
    )
    if account.temporary_password is None:  # pragma: no cover - no hash was passed
        raise RuntimeError("temporary password missing")
    response.headers.update(NO_STORE)
    return UserWithTemporaryPasswordOut(
        user=user_out(account.user, account.credential),
        temporary_password=account.temporary_password,
    )


@router.post("/{user_id}/reset-password", response_model=UserWithTemporaryPasswordOut)
async def reset_password(
    user_id: UUID,
    request: Request,
    response: Response,
    session: SessionDep,
    admin: CurrentUser = require(Action.USER_MANAGE),
) -> UserWithTemporaryPasswordOut:
    """New temporary password (shown ONCE), lockout cleared, every session revoked."""
    account = await users_service.reset_password(
        session,
        actor=admin.actor(),
        user_id=user_id,
        temp_password_ttl=_temp_password_ttl(request),
    )
    if account.temporary_password is None:  # pragma: no cover
        raise RuntimeError("temporary password missing")
    response.headers.update(NO_STORE)
    return UserWithTemporaryPasswordOut(
        user=user_out(account.user, account.credential),
        temporary_password=account.temporary_password,
    )


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: UUID,
    body: UserUpdate,
    request: Request,
    session: SessionDep,
    admin: CurrentUser = require(Action.USER_MANAGE),
) -> UserOut:
    """Display name, (de)activation (revokes every session), the app admin flag."""
    settings: Settings = request.app.state.settings
    user = await users_service.update_user(
        session,
        actor=admin.actor(),
        user_id=user_id,
        display_name=body.display_name,
        is_active=body.is_active,
        is_app_admin=body.is_app_admin,
        # Only admins who can sign in keep the application administrable (ADR 0018).
        admins_need_password=settings.auth_mode == "local",
    )
    credentials = await users_service.credentials_by_user(session, [user.id])
    return user_out(user, credentials.get(user.id))
