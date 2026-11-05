"""Dev login (``AUTH_MODE=dev`` only — the router is not mounted otherwise).

Public (``PUBLIC_ENDPOINTS``): lists the users in the database and issues HS256 tokens
signed with ``DEV_AUTH_SECRET`` for them. Never available in production.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from sqlalchemy import select

from app.auth.dev import issue_dev_token
from app.db import SessionDep
from app.errors import ProblemError
from app.models import User
from app.schemas.identity import DevTokenIn, DevUserOut, TokenOut
from app.services import users as users_service

router = APIRouter(prefix="/auth/dev", tags=["auth (dev)"])


@router.get("/users", response_model=list[DevUserOut])
async def dev_users(session: SessionDep) -> list[DevUserOut]:
    rows = await session.execute(select(User).order_by(User.display_name, User.id))
    return [DevUserOut.model_validate(u) for u in rows.scalars().all()]


@router.post("/token", response_model=TokenOut)
async def dev_token(body: DevTokenIn, request: Request, session: SessionDep) -> TokenOut:
    user = await users_service.get_user_by_external_id(session, body.external_id)
    if user is None:
        raise ProblemError(
            status=404,
            code="auth.dev_user_not_found",
            detail="Nie znaleziono użytkownika testowego o podanym identyfikatorze.",
        )
    secret = request.app.state.settings.dev_auth_secret.get_secret_value()
    token, expires_in = issue_dev_token(secret, user.external_id)
    return TokenOut(access_token=token, expires_in=expires_in)
