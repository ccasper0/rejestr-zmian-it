"""``GET /me`` — profile, memberships and roles of the caller (``SELF_ENDPOINTS``).

Allowed also while a temporary password must be changed (``must_change_password``,
ADR 0018 §5): the frontend reads the flag here and shows the password form.
"""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from app.auth.dependencies import PendingPasswordUserDep
from app.db import SessionDep
from app.models import Company
from app.schemas.identity import MembershipOut, MeOut

router = APIRouter(tags=["auth"])


@router.get("/me", response_model=MeOut)
async def me(user: PendingPasswordUserDep, session: SessionDep) -> MeOut:
    companies = []
    if user.company_ids:
        rows = await session.execute(
            select(Company).where(Company.id.in_(user.company_ids)).order_by(Company.name)
        )
        companies = list(rows.scalars().all())
    return MeOut(
        id=user.id,
        external_id=user.external_id,
        email=user.email,
        display_name=user.display_name,
        is_app_admin=user.is_app_admin,
        must_change_password=user.must_change_password,
        memberships=[
            MembershipOut(
                company_id=c.id,
                company_name=c.name,
                company_prefix=c.prefix,
                company_status=c.status,
                roles=sorted(r.value for r in user.roles_in(c.id)),
            )
            for c in companies
        ],
    )
