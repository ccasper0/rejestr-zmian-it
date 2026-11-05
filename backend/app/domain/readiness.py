"""Readiness of a change for submission (CLAUDE.md §4.3, ADR 0012 §3). No I/O.

:func:`readiness` is the single implementation of the rules: ``submit`` and the emergency
``implement`` refuse a change whose report has an error (``change.not_ready``), and
``GET /changes/{id}/readiness`` returns the same report to the panel "Kontrola przed
wysłaniem". The approver's edits in ``pending_approval`` re-run the window and approver
groups (:func:`window_checks`, :func:`approver_checks`) - the rules are not duplicated.

Only checks that apply to the change are returned (e.g. the rollback plan check appears
only for high risk), in a stable order.
"""

from __future__ import annotations

from collections.abc import Collection, Iterator
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.changes import (
    APPROVER_ROLES,
    WRITER_ROLES,
    CategoryFacts,
    ChangeContext,
    ChangeData,
    ChangeType,
    Check,
    CheckLevel,
    Risk,
    require_aware,
)
from app.domain.dictionaries import effective_requires_approval as _effective_flag


@dataclass(frozen=True, slots=True)
class ReadinessReport:
    checks: tuple[Check, ...]

    @property
    def ok(self) -> bool:
        return all(check.ok for check in self.checks)

    @property
    def errors(self) -> tuple[Check, ...]:
        return tuple(c for c in self.checks if c.level is CheckLevel.ERROR)

    @property
    def warnings(self) -> tuple[Check, ...]:
        return tuple(c for c in self.checks if c.level is CheckLevel.WARNING)


def _check(code: str, ok: bool, message_pl: str, field: str | None) -> Check:
    return Check(code, CheckLevel.OK if ok else CheckLevel.ERROR, message_pl, field)


def _filled(value: str | None) -> bool:
    return value is not None and bool(value.strip())


# --------------------------------------------------------------------------- categories


def _category(change: ChangeData, ctx: ChangeContext) -> CategoryFacts | None:
    return None if change.category_id is None else ctx.categories.get(change.category_id)


def _subcategory(change: ChangeData, ctx: ChangeContext) -> CategoryFacts | None:
    return None if change.subcategory_id is None else ctx.categories.get(change.subcategory_id)


def requires_ci_owner_consent(change: ChangeData, ctx: ChangeContext) -> bool:
    """Category OR subcategory flag (a subcategory only tightens, ADR 0011 §3)."""
    category = _category(change, ctx)
    subcategory = _subcategory(change, ctx)
    return _effective_flag(
        category is not None and category.requires_ci_owner_consent,
        None if subcategory is None else subcategory.requires_ci_owner_consent,
    )


def effective_requires_approval(change: ChangeData, ctx: ChangeContext) -> bool:
    """Whether the change needs an approver's decision (ADR 0011 §3, ADR 0012 §2).

    ``category OR subcategory`` (a subcategory only tightens). An unknown category is
    treated as requiring approval, and so is a category that requires the CI owner's
    consent: the consent is collected in the approval round, so such changes are never
    auto-approved.
    """
    category = _category(change, ctx)
    if category is None:
        return True
    subcategory = _subcategory(change, ctx)
    return _effective_flag(
        category.requires_approval,
        None if subcategory is None else subcategory.requires_approval,
    ) or requires_ci_owner_consent(change, ctx)


def is_auto_approved(change: ChangeData, ctx: ChangeContext) -> bool:
    """A standard change whose category/subcategory need neither approval nor the CI
    owner's consent: ``submit`` approves it as ``system`` (§4.2) and readiness does not
    require an approver (owner decision 2026-10-29, ADR 0012 §3)."""
    return change.change_type is ChangeType.STANDARD and not effective_requires_approval(
        change, ctx
    )


def default_approver_id(
    *,
    category_override_id: UUID | None,
    company_default_approver_id: UUID | None,
    excluded: Collection[UUID] = (),
) -> UUID | None:
    """Suggested approver: ``company_categories.approver_override_id`` and then
    ``companies.default_approver_id`` (§4.3). A candidate in ``excluded`` (pass the
    requester and the assignee - four eyes) is skipped. Eligibility (role ``approver``)
    is reported by readiness, not decided here."""
    for candidate in (category_override_id, company_default_approver_id):
        if candidate is not None and candidate not in excluded:
            return candidate
    return None


# --------------------------------------------------------------------------- groups


def _basic_checks(change: ChangeData) -> Iterator[Check]:
    yield _check("title.required", _filled(change.title), "Tytuł zmiany jest podany.", "title")
    yield _check(
        "change_type.required",
        change.change_type is not None,
        "Typ zmiany jest wybrany (standardowa, normalna lub awaryjna).",
        "change_type",
    )
    yield _check("risk.required", change.risk is not None, "Ryzyko jest określone.", "risk")
    yield _check(
        "description.required",
        _filled(change.description),
        "Opis zmiany i uzasadnienie są podane.",
        "description",
    )
    yield _check(
        "implementation_plan.required",
        _filled(change.implementation_plan),
        "Plan wdrożenia jest podany.",
        "implementation_plan",
    )


def _category_checks(change: ChangeData, ctx: ChangeContext) -> Iterator[Check]:
    yield _check(
        "category.required",
        change.category_id is not None,
        "Kategoria zmiany jest wybrana.",
        "category_id",
    )
    if change.category_id is not None:
        category = _category(change, ctx)
        yield _check(
            "category.available",
            category is not None
            and category.parent_id is None
            and category.is_active
            and category.available_in_company,
            "Kategoria jest aktywna i dostępna w tej spółce.",
            "category_id",
        )
    if change.subcategory_id is not None:
        subcategory = _subcategory(change, ctx)
        yield _check(
            "subcategory.valid",
            subcategory is not None
            and subcategory.is_active
            and subcategory.parent_id is not None
            and subcategory.parent_id == change.category_id,
            "Podkategoria jest aktywna i należy do wybranej kategorii.",
            "subcategory_id",
        )


def _ci_checks(change: ChangeData, ctx: ChangeContext) -> Iterator[Check]:
    yield _check(
        "ci.required",
        bool(change.ci_ids),
        "Wskazano co najmniej jeden obiekt (CI), którego dotyczy zmiana.",
        "ci_ids",
    )
    if not change.ci_ids:
        return
    found = [ctx.cis.get(ci_id) for ci_id in change.ci_ids]
    yield _check(
        "ci.same_company",
        all(ci is not None and ci.company_id == change.company_id for ci in found),
        "Wszystkie obiekty (CI) należą do spółki zmiany.",
        "ci_ids",
    )
    yield _check(
        "ci.active",
        all(ci is not None and ci.is_active for ci in found),
        "Wszystkie obiekty (CI) są aktywne.",
        "ci_ids",
    )
    if requires_ci_owner_consent(change, ctx):
        yield _check(
            "ci.owner_consent_possible",
            all(
                ci is not None
                and ci.owner_user_id is not None
                and (owner := ctx.member(ci.owner_user_id)) is not None
                and owner.is_active
                for ci in found
            ),
            "Każdy obiekt (CI) ma aktywnego właściciela w spółce, który wyrazi zgodę "
            "na zmianę (wymóg kategorii).",
            "ci_ids",
        )


def _assignee_checks(change: ChangeData, ctx: ChangeContext) -> Iterator[Check]:
    yield _check(
        "assignee.required",
        change.assignee_id is not None,
        "Wykonawca jest wskazany.",
        "assignee_id",
    )
    if change.assignee_id is not None:
        yield _check(
            "assignee.eligible",
            ctx.is_member_with(change.assignee_id, WRITER_ROLES),
            "Wykonawca jest aktywnym użytkownikiem z rolą edytora lub zatwierdzającego w spółce.",
            "assignee_id",
        )


def approver_checks(change: ChangeData, ctx: ChangeContext) -> tuple[Check, ...]:
    """Approver present, holding the ``approver`` role, and four eyes (§4.2, §4.3).

    An auto-approved standard change (:func:`is_auto_approved`) may have no approver; if
    one is designated anyway, eligibility and four eyes still apply.
    """
    if change.approver_id is None and is_auto_approved(change, ctx):
        return (
            _check(
                "approver.required",
                True,
                "Zatwierdzający nie jest wymagany - zmiana standardowa zostanie zatwierdzona "
                "automatycznie.",
                "approver_id",
            ),
        )
    checks = [
        _check(
            "approver.required",
            change.approver_id is not None,
            "Zatwierdzający jest wskazany.",
            "approver_id",
        )
    ]
    if change.approver_id is not None:
        checks.append(
            _check(
                "approver.eligible",
                ctx.is_member_with(change.approver_id, APPROVER_ROLES),
                "Zatwierdzający jest aktywnym użytkownikiem z rolą zatwierdzającego w spółce.",
                "approver_id",
            )
        )
        checks.append(
            _check(
                "approver.four_eyes",
                change.approver_id not in {change.requested_by_id, change.assignee_id},
                "Zatwierdzający jest inną osobą niż zgłaszający i wykonawca (zasada "
                "czterech oczu).",
                "approver_id",
            )
        )
    return tuple(checks)


def window_checks(change: ChangeData, *, now: datetime) -> tuple[Check, ...]:
    """Service window: required for high risk; ``start < end``; ``start`` in the future
    except for emergency changes (§4.3)."""
    require_aware(now, "now")
    start, end = change.window_start, change.window_end
    checks: list[Check] = []
    if change.risk is Risk.HIGH:
        checks.append(
            _check(
                "window.required_high_risk",
                start is not None and end is not None,
                "Okno serwisowe (od i do) jest podane - wymagane przy wysokim ryzyku.",
                "window_start",
            )
        )
    elif (start is None) != (end is None):
        checks.append(
            _check(
                "window.complete",
                False,
                "Okno serwisowe ma podany zarówno początek, jak i koniec.",
                "window_end" if end is None else "window_start",
            )
        )
    if start is not None and end is not None:
        checks.append(
            _check(
                "window.order",
                start < end,
                "Początek okna serwisowego jest wcześniejszy niż jego koniec.",
                "window_end",
            )
        )
    if start is not None and change.change_type is not ChangeType.EMERGENCY:
        checks.append(
            _check(
                "window.future",
                start > now,
                "Początek okna serwisowego jest w przyszłości.",
                "window_start",
            )
        )
    return tuple(checks)


def _risk_checks(change: ChangeData) -> Iterator[Check]:
    if change.risk is Risk.HIGH:
        yield _check(
            "rollback_plan.required_high_risk",
            _filled(change.rollback_plan),
            "Plan wycofania jest podany - wymagany przy wysokim ryzyku.",
            "rollback_plan",
        )


def verifier_may_be_assignee(change: ChangeData, ctx: ChangeContext) -> bool:
    """§4.2: the verifier should differ from the assignee "if possible". It is not possible
    when the company has no other active member who may verify (role editor/approver).

    Since an auto-approved standard change needs no approver (ADR 0012 §3), a company
    whose only active editor/approver is the assignee really reaches this exception.
    """
    others = {
        user_id
        for user_id, member in ctx.members.items()
        if member.has_any(WRITER_ROLES) and user_id != change.assignee_id
    }
    return not others


def verifier_checks(change: ChangeData, ctx: ChangeContext) -> tuple[Check, ...]:
    """Verifier group: KSC requirement and eligibility (also used when an approver
    re-assigns the verifier of an implemented change, ADR 0012 §6)."""
    return tuple(_verifier_checks(change, ctx))


def _requirement_checks(change: ChangeData, ctx: ChangeContext) -> Iterator[Check]:
    if ctx.company.is_ksc_entity:
        yield _check(
            "requirement_ref.required_ksc",
            _filled(change.requirement_ref),
            "Podstawa/wymóg jest podany - wymagany w podmiocie objętym uoKSC.",
            "requirement_ref",
        )


def _verifier_checks(change: ChangeData, ctx: ChangeContext) -> Iterator[Check]:
    if ctx.company.is_ksc_entity:
        yield _check(
            "verifier.required_ksc",
            change.verifier_id is not None,
            "Weryfikujący jest wskazany - wymagany w podmiocie objętym uoKSC.",
            "verifier_id",
        )
    if change.verifier_id is None:
        return
    yield _check(
        "verifier.eligible",
        ctx.is_member_with(change.verifier_id, WRITER_ROLES),
        "Weryfikujący jest aktywnym użytkownikiem z rolą edytora lub zatwierdzającego w spółce.",
        "verifier_id",
    )
    if change.verifier_id == change.assignee_id:
        if verifier_may_be_assignee(change, ctx):
            yield Check(
                "verifier.not_assignee",
                CheckLevel.WARNING,
                "Weryfikujący jest wykonawcą zmiany. Dopuszczalne, bo w spółce nie ma innej "
                "osoby, która może zweryfikować zmianę - zostanie to odnotowane w audycie.",
                "verifier_id",
            )
        else:
            yield _check(
                "verifier.not_assignee",
                False,
                "Weryfikujący jest inną osobą niż wykonawca.",
                "verifier_id",
            )


def readiness(change: ChangeData, ctx: ChangeContext, *, now: datetime) -> ReadinessReport:
    """All §4.3 rules applicable to ``change`` (the change's own type decides the
    emergency exception from "window in the future")."""
    require_aware(now, "now")
    checks: list[Check] = []
    checks.extend(_basic_checks(change))
    checks.extend(_category_checks(change, ctx))
    checks.extend(_ci_checks(change, ctx))
    checks.extend(_risk_checks(change))
    checks.extend(window_checks(change, now=now))
    checks.extend(_assignee_checks(change, ctx))
    checks.extend(approver_checks(change, ctx))
    checks.extend(_requirement_checks(change, ctx))
    checks.extend(_verifier_checks(change, ctx))
    return ReadinessReport(tuple(checks))


def approval_readiness(change: ChangeData, ctx: ChangeContext, *, now: datetime) -> ReadinessReport:
    """Readiness re-checked by ``approve`` (``pending_approval -> approved``; the change may
    have aged since submission). Every error blocks, except ``window.future``: a window
    whose start has already passed is downgraded to a warning recorded in the audit
    (owner decision 2026-10-29, ADR 0012 §2)."""
    report = readiness(change, ctx, now=now)
    return ReadinessReport(
        tuple(
            Check(
                check.code,
                CheckLevel.WARNING,
                "Początek okna serwisowego już minął - zatwierdzenie jest dozwolone i "
                "zostanie odnotowane w audycie.",
                check.field,
            )
            if check.code == "window.future" and not check.ok
            else check
            for check in report.checks
        )
    )
