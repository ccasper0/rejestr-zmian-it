"""Readiness of a change for submission (CLAUDE.md §4.3, ADR 0012 §3) - pure domain."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from uuid import uuid4

import pytest

from app.domain.changes import (
    ChangeErrorCode,
    ChangeType,
    Check,
    CheckLevel,
    CompanyFacts,
    ErrorKind,
    MemberFacts,
    Risk,
)
from app.domain.readiness import (
    approval_readiness,
    default_approver_id,
    effective_requires_approval,
    is_auto_approved,
    readiness,
    requires_ci_owner_consent,
    verifier_checks,
    verifier_may_be_assignee,
)
from app.domain.roles import Role
from tests.change_world import (
    ACC,
    ACC_GRANT,
    ACC_OT,
    ACC_PRIV,
    APPROVER,
    APPROVER2,
    ASSIGNEE,
    AUTHOR,
    CI_FOREIGN,
    CI_FW,
    CI_INACTIVE,
    CI_NO_OWNER,
    CI_OT,
    CI_SRV,
    COMPANY_ID,
    EDITOR2,
    INACTIVE_APPROVER,
    INACTIVE_CAT,
    MEMBERS,
    NET,
    NET_VLAN_INACTIVE,
    NOW,
    OT,
    OUTSIDER,
    OWNER,
    UNAVAILABLE_CAT,
    VERIFIER,
    VIEWER,
    context,
    ready_change,
)


def _failed(**overrides: Any) -> set[str]:
    ctx = overrides.pop("ctx", context())
    report = readiness(ready_change(**overrides), ctx, now=NOW)
    return {c.code for c in report.errors}


def test_ready_change_passes_with_stable_check_list() -> None:
    report = readiness(ready_change(), context(), now=NOW)
    assert report.ok
    assert report.errors == ()
    assert report.warnings == ()
    assert [c.code for c in report.checks] == [
        "title.required",
        "change_type.required",
        "risk.required",
        "description.required",
        "implementation_plan.required",
        "category.required",
        "category.available",
        "ci.required",
        "ci.same_company",
        "ci.active",
        "window.order",
        "window.future",
        "assignee.required",
        "assignee.eligible",
        "approver.required",
        "approver.eligible",
        "approver.four_eyes",
        "verifier.eligible",
    ]
    assert all(c.message_pl and c.field for c in report.checks)


@pytest.mark.parametrize(
    ("overrides", "failed"),
    [
        ({"title": None}, {"title.required"}),
        ({"title": "  "}, {"title.required"}),
        ({"change_type": None}, {"change_type.required"}),
        ({"risk": None}, {"risk.required"}),
        ({"description": ""}, {"description.required"}),
        ({"implementation_plan": None}, {"implementation_plan.required"}),
        ({"category_id": None}, {"category.required"}),
        ({"ci_ids": frozenset()}, {"ci.required"}),
        ({"assignee_id": None}, {"assignee.required"}),
        ({"approver_id": None}, {"approver.required"}),
    ],
)
def test_required_fields(overrides: dict[str, Any], failed: set[str]) -> None:
    assert _failed(**overrides) == failed


def test_check_as_dict() -> None:
    check = readiness(ready_change(title=None), context(), now=NOW).checks[0]
    assert check.as_dict() == {
        "code": "title.required",
        "ok": False,
        "level": "error",
        "message_pl": "Tytuł zmiany jest podany.",
        "field": "title",
    }


# --------------------------------------------------------------------------- risk, window


def test_high_risk_requires_rollback_plan_and_window() -> None:
    assert _failed(risk=Risk.HIGH, window_start=None, window_end=None) == {
        "rollback_plan.required_high_risk",
        "window.required_high_risk",
    }
    assert _failed(risk=Risk.HIGH, rollback_plan="Przywróć kopię konfiguracji.") == set()
    assert _failed(risk=Risk.HIGH, rollback_plan="x", window_end=None) == {
        "window.required_high_risk"
    }


@pytest.mark.parametrize("risk", [Risk.LOW, Risk.MEDIUM])
def test_window_is_optional_below_high_risk_but_must_be_complete(risk: Risk) -> None:
    assert _failed(risk=risk, window_start=None, window_end=None) == set()
    assert _failed(risk=risk, window_end=None) == {"window.complete"}
    assert _failed(risk=risk, window_start=None) == {"window.complete"}


@pytest.mark.parametrize(
    ("start", "end", "failed"),
    [
        (timedelta(hours=1), timedelta(hours=2), set()),
        (timedelta(hours=2), timedelta(hours=2), {"window.order"}),
        (timedelta(hours=3), timedelta(hours=2), {"window.order"}),
        (timedelta(0), timedelta(hours=2), {"window.future"}),  # start == now: not future
        (timedelta(microseconds=1), timedelta(hours=2), set()),
        (-timedelta(hours=1), timedelta(hours=2), {"window.future"}),
    ],
)
def test_window_order_and_future(start: timedelta, end: timedelta, failed: set[str]) -> None:
    assert _failed(window_start=NOW + start, window_end=NOW + end) == failed


def test_emergency_window_may_be_in_the_past_but_ordered() -> None:
    past = {"window_start": NOW - timedelta(hours=3), "window_end": NOW - timedelta(hours=1)}
    assert _failed(change_type=ChangeType.EMERGENCY, **past) == set()
    assert _failed(change_type=ChangeType.NORMAL, **past) == {"window.future"}
    assert _failed(
        change_type=ChangeType.EMERGENCY,
        window_start=NOW - timedelta(hours=1),
        window_end=NOW - timedelta(hours=3),
    ) == {"window.order"}


# --------------------------------------------------------------------------- KSC


def test_ksc_entity_requires_requirement_ref_and_verifier() -> None:
    ksc = context(company=CompanyFacts(COMPANY_ID, is_ksc_entity=True))
    assert _failed(ctx=ksc, verifier_id=None) == {
        "requirement_ref.required_ksc",
        "verifier.required_ksc",
    }
    assert _failed(ctx=ksc, requirement_ref="ISO/IEC 27001 A.8.32") == set()
    assert _failed(verifier_id=None) == set()  # not required outside KSC


# --------------------------------------------------------------------------- categories


@pytest.mark.parametrize("category", [INACTIVE_CAT, UNAVAILABLE_CAT, ACC_PRIV, uuid4()], ids=str)
def test_category_must_be_active_top_level_and_available(category: object) -> None:
    assert _failed(category_id=category) == {"category.available"}


@pytest.mark.parametrize(
    ("category", "subcategory", "failed"),
    [
        (ACC, ACC_PRIV, set()),
        (NET, ACC_PRIV, {"subcategory.valid"}),  # another category's subcategory
        (NET, NET_VLAN_INACTIVE, {"subcategory.valid"}),
        (NET, uuid4(), {"subcategory.valid"}),
        (ACC, NET, {"subcategory.valid"}),  # a top-level category is not a subcategory
        (None, ACC_PRIV, {"category.required", "subcategory.valid"}),
    ],
)
def test_subcategory_must_belong_to_the_category(
    category: object, subcategory: object, failed: set[str]
) -> None:
    assert _failed(category_id=category, subcategory_id=subcategory) == failed


# --------------------------------------------------------------------------- CI


@pytest.mark.parametrize(
    ("cis", "failed"),
    [
        ({CI_FW, CI_SRV}, set()),
        ({CI_FW, CI_FOREIGN}, {"ci.same_company"}),
        ({uuid4()}, {"ci.same_company", "ci.active"}),  # unknown / hidden by RLS
        ({CI_INACTIVE}, {"ci.active"}),
    ],
)
def test_ci_same_company_and_active(cis: set[Any], failed: set[str]) -> None:
    assert _failed(ci_ids=frozenset(cis)) == failed


def test_ci_owner_consent_possible_only_checked_when_required() -> None:
    assert _failed(ci_ids=frozenset({CI_NO_OWNER})) == set()
    assert _failed(category_id=OT, ci_ids=frozenset({CI_OT, CI_SRV})) == set()
    assert _failed(category_id=OT, ci_ids=frozenset({CI_OT, CI_NO_OWNER})) == {
        "ci.owner_consent_possible"
    }
    inactive_owner = dict(MEMBERS) | {OWNER: MemberFacts(False, frozenset({Role.VIEWER}))}
    assert _failed(
        category_id=OT, ci_ids=frozenset({CI_OT}), ctx=context(members=inactive_owner)
    ) == {"ci.owner_consent_possible"}
    no_owner_membership = {k: v for k, v in MEMBERS.items() if k != OWNER}
    assert _failed(
        category_id=OT, ci_ids=frozenset({CI_OT}), ctx=context(members=no_owner_membership)
    ) == {"ci.owner_consent_possible"}
    assert _failed(category_id=ACC, subcategory_id=ACC_OT, ci_ids=frozenset({CI_NO_OWNER})) == {
        "ci.owner_consent_possible"
    }


# --------------------------------------------------------------------------- people


@pytest.mark.parametrize("assignee", [VIEWER, OUTSIDER, OWNER])
def test_assignee_must_be_an_active_editor_or_approver(assignee: Any) -> None:
    assert _failed(assignee_id=assignee) == {"assignee.eligible"}


def test_assignee_with_approver_role_is_eligible() -> None:
    assert _failed(assignee_id=APPROVER2) == set()


@pytest.mark.parametrize(
    ("approver", "failed"),
    [
        (APPROVER2, set()),
        (EDITOR2, {"approver.eligible"}),
        (INACTIVE_APPROVER, {"approver.eligible"}),
        (OUTSIDER, {"approver.eligible"}),
        (AUTHOR, {"approver.eligible", "approver.four_eyes"}),
        (ASSIGNEE, {"approver.eligible", "approver.four_eyes"}),
    ],
)
def test_approver_eligibility_and_four_eyes(approver: Any, failed: set[str]) -> None:
    assert _failed(approver_id=approver) == failed


def test_approver_who_is_requester_fails_four_eyes_even_with_approver_role() -> None:
    assert _failed(requested_by_id=APPROVER2, approver_id=APPROVER2) == {"approver.four_eyes"}
    assert _failed(assignee_id=APPROVER2, approver_id=APPROVER2) == {"approver.four_eyes"}


@pytest.mark.parametrize(
    ("verifier", "failed"),
    [(VERIFIER, set()), (APPROVER, set()), (VIEWER, {"verifier.eligible"})],
)
def test_verifier_eligibility(verifier: Any, failed: set[str]) -> None:
    assert _failed(verifier_id=verifier) == failed


def test_verifier_equal_to_assignee() -> None:
    assert _failed(verifier_id=ASSIGNEE) == {"verifier.not_assignee"}
    # a company where nobody else may verify: warning only (the approver would count, so
    # this situation needs a company whose only writer is the assignee)
    solo = uuid4()
    members = {solo: MemberFacts(True, frozenset({Role.EDITOR}))}
    report = readiness(
        ready_change(requested_by_id=solo, assignee_id=solo, verifier_id=solo),
        context(members=members),
        now=NOW,
    )
    warning = next(c for c in report.checks if c.code == "verifier.not_assignee")
    assert warning.level is CheckLevel.WARNING
    assert warning.ok
    assert report.warnings == (warning,)


# --------------------------------------------------------------------------- helpers


@pytest.mark.parametrize(
    ("override", "company_default", "excluded", "expected"),
    [
        (APPROVER, APPROVER2, (), APPROVER),
        (None, APPROVER2, (), APPROVER2),
        (None, None, (), None),
        (APPROVER, APPROVER2, (APPROVER,), APPROVER2),
        (APPROVER, APPROVER2, (APPROVER, APPROVER2), None),
    ],
)
def test_default_approver(
    override: Any, company_default: Any, excluded: tuple[Any, ...], expected: Any
) -> None:
    assert (
        default_approver_id(
            category_override_id=override,
            company_default_approver_id=company_default,
            excluded=excluded,
        )
        == expected
    )


@pytest.mark.parametrize(
    ("category", "subcategory", "approval", "consent"),
    [
        (ACC, None, False, False),
        (ACC, ACC_GRANT, False, False),
        (ACC, ACC_PRIV, True, False),
        (ACC, ACC_OT, True, True),
        (NET, None, True, False),
        (OT, None, True, True),
        (None, None, True, False),  # unknown category: approval required
        (uuid4(), None, True, False),
    ],
)
def test_effective_flags(category: Any, subcategory: Any, approval: bool, consent: bool) -> None:
    change = ready_change(category_id=category, subcategory_id=subcategory)
    assert effective_requires_approval(change, context()) is approval
    assert requires_ci_owner_consent(change, context()) is consent


def test_naive_now_rejected() -> None:
    from datetime import datetime

    with pytest.raises(ValueError, match="timezone-aware"):
        readiness(ready_change(), context(), now=datetime(2026, 1, 1))  # noqa: DTZ001


def test_error_codes_have_kinds_and_polish_messages() -> None:
    for code in ChangeErrorCode:
        assert isinstance(code.kind, ErrorKind)
        assert code.default_message_pl.endswith(".")
    assert ChangeErrorCode.FOUR_EYES_VIOLATION.value == "change.four_eyes_violation"
    assert ChangeErrorCode.NOT_READY.kind is ErrorKind.VALIDATION


def test_check_level_ok() -> None:
    assert Check("x", CheckLevel.WARNING, "m").ok
    assert not Check("x", CheckLevel.ERROR, "m").ok


# --------------------------------------------------------------------------- owner decisions
# (ADR 0012 §10, 2026-10-29)


@pytest.mark.parametrize(
    ("change_type", "category", "subcategory", "auto"),
    [
        (ChangeType.STANDARD, ACC, None, True),
        (ChangeType.STANDARD, ACC, ACC_GRANT, True),
        (ChangeType.STANDARD, ACC, ACC_PRIV, False),
        (ChangeType.STANDARD, ACC, ACC_OT, False),
        (ChangeType.STANDARD, NET, None, False),
        (ChangeType.NORMAL, ACC, None, False),
        (ChangeType.EMERGENCY, ACC, None, False),
    ],
)
def test_approver_optional_only_for_auto_approved_standard_changes(
    change_type: ChangeType, category: Any, subcategory: Any, auto: bool
) -> None:
    change = ready_change(
        change_type=change_type,
        category_id=category,
        subcategory_id=subcategory,
        approver_id=None,
        ci_ids=frozenset({CI_OT}),
    )
    assert is_auto_approved(change, context()) is auto
    report = readiness(change, context(), now=NOW)
    approver = [c for c in report.checks if c.code.startswith("approver.")]
    assert [c.code for c in approver] == ["approver.required"]
    assert approver[0].ok is auto


def test_designated_approver_of_auto_approved_change_still_checked() -> None:
    standard = {"change_type": ChangeType.STANDARD, "category_id": ACC}
    assert _failed(approver_id=AUTHOR, **standard) == {
        "approver.eligible",
        "approver.four_eyes",
    }
    assert _failed(approver_id=APPROVER2, **standard) == set()


def test_one_person_company_reaches_the_verifier_exception() -> None:
    solo = uuid4()
    members = {
        solo: MemberFacts(True, frozenset({Role.EDITOR})),
        VIEWER: MemberFacts(True, frozenset({Role.VIEWER})),  # cannot verify
    }
    change = ready_change(
        change_type=ChangeType.STANDARD,
        category_id=ACC,
        requested_by_id=solo,
        assignee_id=solo,
        approver_id=None,
        verifier_id=solo,
    )
    report = readiness(change, context(members=members), now=NOW)
    assert report.ok
    assert [c.code for c in report.warnings] == ["verifier.not_assignee"]
    assert verifier_may_be_assignee(change, context(members=members))


def test_approval_readiness_downgrades_only_a_started_window() -> None:
    change = ready_change()
    assert change.window_start is not None
    late = change.window_start + timedelta(minutes=1)
    assert {c.code for c in readiness(change, context(), now=late).errors} == {"window.future"}
    report = approval_readiness(change, context(), now=late)
    assert report.ok
    assert [(c.code, c.level) for c in report.warnings] == [("window.future", CheckLevel.WARNING)]
    stale = ready_change(title=None)
    assert {c.code for c in approval_readiness(stale, context(), now=late).errors} == {
        "title.required"
    }
    in_time = approval_readiness(change, context(), now=NOW)
    assert in_time.checks == readiness(change, context(), now=NOW).checks


def test_verifier_checks_group() -> None:
    assert verifier_checks(ready_change(verifier_id=None), context()) == ()
    assert [c.code for c in verifier_checks(ready_change(), context())] == ["verifier.eligible"]
