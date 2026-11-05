"""Categories available in a company and their approver overrides (CLAUDE.md 4.1; ADR 0011).

Only top-level categories are assigned; their subcategories follow them. ``PUT`` sets the
full list: rows are added, removed (DELETE - the removal is in the audit log, like a role
revocation) or get a new ``approver_override_id``.

One audit entry per effective PUT in the chain OF THE COMPANY: ``entity_type =
company_category``, ``entity_id`` = the company, ``action = update``, ``diff`` keyed by the
(immutable) category code: ``{"NET": {"before": null, "after": {"approver_override_id":
...}}}`` - ``null`` means "not available in the company". The caller must be on the
explicit admin path with the company in the transaction scope (RLS).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.audit import Actor, AuditAction, EntityType, make_diff
from app.errors import ProblemError
from app.models import ChangeCategory, Company, CompanyCategory, User
from app.permissions import Role
from app.services import audit
from app.services import memberships as memberships_service


@dataclass(frozen=True, slots=True)
class Assignment:
    """One entry of the requested list."""

    category_id: UUID
    approver_override_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class AvailableCategory:
    category: ChangeCategory
    approver_override_id: UUID | None


async def list_company_categories(
    session: AsyncSession, company_id: UUID
) -> list[AvailableCategory]:
    rows = await session.execute(
        select(CompanyCategory, ChangeCategory)
        .join(ChangeCategory, ChangeCategory.id == CompanyCategory.category_id)
        .where(CompanyCategory.company_id == company_id)
        .order_by(ChangeCategory.code)
    )
    return [
        AvailableCategory(category=category, approver_override_id=link.approver_override_id)
        for link, category in rows.all()
    ]


def _unprocessable(code: str, detail: str, **extra: object) -> ProblemError:
    return ProblemError(status=422, code=code, detail=detail, extra=extra)


async def _check_approver(session: AsyncSession, company_id: UUID, user_id: UUID) -> None:
    """The override must be an ACTIVE user with the ``approver`` role in this company."""
    user = await session.get(User, user_id)
    roles = await memberships_service.user_roles_in(session, company_id, user_id)
    if user is None or not user.is_active or Role.APPROVER not in roles:
        raise _unprocessable(
            "company_category.approver_not_eligible",
            "Zatwierdzający dla kategorii musi być aktywnym użytkownikiem z rolą "
            "zatwierdzającego w tej spółce.",
            approver_override_id=user_id,
        )


async def set_company_categories(
    session: AsyncSession,
    *,
    actor: Actor,
    company_id: UUID,
    assignments: Sequence[Assignment],
) -> list[AvailableCategory]:
    """Set the categories available in the company to exactly ``assignments``."""
    ids = [a.category_id for a in assignments]
    if len(ids) != len(set(ids)):
        raise _unprocessable(
            "company_category.duplicate", "Kategoria występuje na liście więcej niż raz."
        )
    # Serialize changes of one company (consistent before -> after in the audit diff).
    # Only the admin path can lock a company row (RLS, ADR 0008).
    company = (
        await session.execute(select(Company).where(Company.id == company_id).with_for_update())
    ).scalar_one_or_none()
    if company is None:
        raise ProblemError(status=404, code="company.not_found", detail="Nie znaleziono spółki.")

    categories = {
        c.id: c
        for c in (
            await session.execute(select(ChangeCategory).where(ChangeCategory.id.in_(ids)))
        ).scalars()
    }
    current = {
        link.category_id: link
        for link in (
            await session.execute(
                select(CompanyCategory).where(CompanyCategory.company_id == company_id)
            )
        ).scalars()
    }
    for assignment in assignments:
        category = categories.get(assignment.category_id)
        if category is None:
            raise _unprocessable(
                "company_category.category_not_found",
                "Nie znaleziono kategorii zmian.",
                category_id=assignment.category_id,
            )
        if category.parent_id is not None:
            raise _unprocessable(
                "company_category.not_top_level",
                "Spółce przypisuje się kategorie główne; ich podkategorie są dostępne razem z "
                "nimi.",
                category_id=assignment.category_id,
            )
        existing = current.get(category.id)
        if existing is None and not category.is_active:
            raise _unprocessable(
                "company_category.category_inactive",
                "Nie można udostępnić spółce nieaktywnej kategorii.",
                category_id=assignment.category_id,
            )
        before_override = existing.approver_override_id if existing is not None else None
        if (
            assignment.approver_override_id is not None
            and assignment.approver_override_id != before_override
        ):
            await _check_approver(session, company_id, assignment.approver_override_id)

    # Codes of categories leaving the company (not in ``categories`` when removed).
    removed_ids = set(current) - set(ids)
    if removed_ids:
        for category in (
            await session.execute(select(ChangeCategory).where(ChangeCategory.id.in_(removed_ids)))
        ).scalars():
            categories[category.id] = category
    before = {
        categories[cid].code: {"approver_override_id": link.approver_override_id}
        for cid, link in current.items()
    }
    after = {
        categories[a.category_id].code: {"approver_override_id": a.approver_override_id}
        for a in assignments
    }
    diff = make_diff(before, after)
    if not diff:
        return await list_company_categories(session, company_id)

    if removed_ids:
        await session.execute(
            delete(CompanyCategory).where(
                CompanyCategory.company_id == company_id,
                CompanyCategory.category_id.in_(removed_ids),
            )
        )
    for assignment in assignments:
        link = current.get(assignment.category_id)
        if link is None:
            session.add(
                CompanyCategory(
                    id=uuid4(),
                    company_id=company_id,
                    category_id=assignment.category_id,
                    approver_override_id=assignment.approver_override_id,
                )
            )
        elif link.approver_override_id != assignment.approver_override_id:
            link.approver_override_id = assignment.approver_override_id
    await session.flush()
    await audit.record(
        session,
        company_id=company_id,
        actor=actor,
        entity_type=EntityType.COMPANY_CATEGORY,
        entity_id=company_id,
        action=AuditAction.UPDATE,
        diff=diff,
        context={
            "added": sorted(set(after) - set(before)),
            "removed": sorted(set(before) - set(after)),
            "override_changed": sorted(
                code for code in set(before) & set(after) if before[code] != after[code]
            ),
        },
    )
    return await list_company_categories(session, company_id)
