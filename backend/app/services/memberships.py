"""Company memberships (roles per company, CLAUDE.md 4.1 / 5).

Role changes are written to the audit chain OF THE COMPANY (entity ``membership``,
``entity_id`` = the user whose roles changed): one ``role_grant`` entry for added roles
and one ``role_revoke`` entry for removed roles, each with a ``roles`` before -> after diff.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Collection
from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.audit import Actor, AuditAction, EntityType
from app.errors import ProblemError
from app.models import Company, CompanyMembership, User
from app.permissions import MEMBERSHIP_ROLES, Role
from app.services import audit


@dataclass(frozen=True, slots=True)
class Member:
    user: User
    roles: frozenset[Role]


@dataclass(frozen=True, slots=True)
class RoleChange:
    before: frozenset[Role]
    after: frozenset[Role]


def _sorted(roles: Collection[Role]) -> list[str]:
    return sorted(r.value for r in roles)


async def roles_by_company(session: AsyncSession, user_id: UUID) -> dict[UUID, frozenset[Role]]:
    rows = await session.execute(
        select(CompanyMembership.company_id, CompanyMembership.role).where(
            CompanyMembership.user_id == user_id
        )
    )
    result: dict[UUID, set[Role]] = defaultdict(set)
    for company_id, role in rows.all():
        result[company_id].add(Role(role))
    return {cid: frozenset(roles) for cid, roles in result.items()}


async def user_roles_in(session: AsyncSession, company_id: UUID, user_id: UUID) -> frozenset[Role]:
    rows = await session.execute(
        select(CompanyMembership.role).where(
            CompanyMembership.company_id == company_id, CompanyMembership.user_id == user_id
        )
    )
    return frozenset(Role(r) for r in rows.scalars().all())


async def list_members(session: AsyncSession, company_id: UUID) -> list[Member]:
    rows = await session.execute(
        select(User, CompanyMembership.role)
        .join(CompanyMembership, CompanyMembership.user_id == User.id)
        .where(CompanyMembership.company_id == company_id)
        .order_by(User.display_name, User.id)
    )
    users: dict[UUID, User] = {}
    roles: dict[UUID, set[Role]] = defaultdict(set)
    for user, role in rows.all():
        users[user.id] = user
        roles[user.id].add(Role(role))
    return [Member(user=u, roles=frozenset(roles[uid])) for uid, u in users.items()]


async def page_members(
    session: AsyncSession, company_id: UUID, *, limit: int, offset: int
) -> tuple[list[Member], int]:
    """One page of members (a user with all roles counts once), plus the total count."""
    member_ids = (
        select(CompanyMembership.user_id)
        .where(CompanyMembership.company_id == company_id)
        .distinct()
        .subquery()
    )
    total = (await session.execute(select(func.count()).select_from(member_ids))).scalar_one()
    page_users = (
        (
            await session.execute(
                select(User)
                .where(User.id.in_(select(member_ids.c.user_id)))
                .order_by(User.display_name, User.id)
                .limit(limit)
                .offset(offset)
            )
        )
        .scalars()
        .all()
    )
    if not page_users:
        return [], int(total)
    rows = await session.execute(
        select(CompanyMembership.user_id, CompanyMembership.role).where(
            CompanyMembership.company_id == company_id,
            CompanyMembership.user_id.in_([u.id for u in page_users]),
        )
    )
    roles: dict[UUID, set[Role]] = defaultdict(set)
    for user_id, role in rows.all():
        roles[user_id].add(Role(role))
    members = [Member(user=u, roles=frozenset(roles[u.id])) for u in page_users]
    return members, int(total)


async def set_member_roles(
    session: AsyncSession,
    *,
    actor: Actor,
    company_id: UUID,
    user_id: UUID,
    roles: Collection[Role],
) -> RoleChange:
    """Set the user's roles in the company to exactly ``roles`` (empty = remove access)."""
    wanted = frozenset(roles)
    if not wanted <= MEMBERSHIP_ROLES:
        raise ValueError(f"not membership roles: {_sorted(wanted - MEMBERSHIP_ROLES)}")

    # Serialize role changes of one company (consistent before -> after in the audit diff).
    company = (
        await session.execute(select(Company).where(Company.id == company_id).with_for_update())
    ).scalar_one_or_none()
    if company is None:
        raise ProblemError(status=404, code="company.not_found", detail="Nie znaleziono spółki.")
    user = await session.get(User, user_id)
    if user is None:
        raise ProblemError(status=404, code="user.not_found", detail="Nie znaleziono użytkownika.")

    current = await user_roles_in(session, company_id, user_id)
    granted = wanted - current
    revoked = current - wanted
    if granted and not user.is_active:
        raise ProblemError(
            status=422,
            code="membership.user_inactive",
            detail="Nie można nadać roli nieaktywnemu użytkownikowi.",
        )

    context_base: dict[str, object] = {
        "user_id": user.id,
        "user_display": user.display_name,
        "self_grant": actor.id == user.id,
    }
    if granted:
        for role in sorted(granted):
            session.add(
                CompanyMembership(id=uuid4(), user_id=user.id, company_id=company_id, role=role)
            )
        await session.flush()
        await audit_role_change(
            session,
            actor=actor,
            company_id=company_id,
            user_id=user.id,
            action=AuditAction.ROLE_GRANT,
            before=current,
            after=current | granted,
            context={**context_base, "granted": _sorted(granted)},
        )
    if revoked:
        await session.execute(
            delete(CompanyMembership).where(
                CompanyMembership.company_id == company_id,
                CompanyMembership.user_id == user.id,
                CompanyMembership.role.in_([r.value for r in revoked]),
            )
        )
        await audit_role_change(
            session,
            actor=actor,
            company_id=company_id,
            user_id=user.id,
            action=AuditAction.ROLE_REVOKE,
            before=current | granted,
            after=wanted,
            context={**context_base, "revoked": _sorted(revoked)},
        )
    return RoleChange(before=current, after=wanted)


async def audit_role_change(
    session: AsyncSession,
    *,
    actor: Actor,
    company_id: UUID,
    user_id: UUID,
    action: AuditAction,
    before: frozenset[Role],
    after: frozenset[Role],
    context: dict[str, object],
) -> None:
    await audit.record(
        session,
        company_id=company_id,
        actor=actor,
        entity_type=EntityType.MEMBERSHIP,
        entity_id=user_id,
        action=action,
        diff={"roles": {"before": _sorted(before), "after": _sorted(after)}},
        context=context,
    )
