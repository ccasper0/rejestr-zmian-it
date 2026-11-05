"""Change state machine (CLAUDE.md §4.2, ADR 0012) - pure domain, no database.

The full matrix status x change type x approval state x action x actor is compared with
an oracle written directly from table §4.2 (``EXPECTED`` below), independently of the
declarative table in ``app.domain.state_machine``.
"""

from __future__ import annotations

import itertools
from dataclasses import replace
from datetime import datetime, timedelta
from uuid import UUID, uuid4

import pytest

from app.domain.changes import (
    APPROVER_ROLES,
    WRITER_ROLES,
    ActorFacts,
    ChangeAction,
    ChangeContext,
    ChangeData,
    ChangeErrorCode,
    ChangeField,
    ChangeRuleError,
    ChangeStatus,
    ChangeType,
    CompanyFacts,
    ErrorKind,
    MemberFacts,
    Risk,
)
from app.domain.roles import Role
from app.domain.state_machine import (
    DRAFT_EDITABLE,
    PENDING_APPROVAL_EDITABLE,
    TRANSITIONS,
    allowed_actions,
    approver_reassignable,
    check_access,
    check_edit,
    editable_fields,
    execute,
    normalize_comment,
)
from app.permissions import PERMISSIONS, Action
from tests.change_world import (
    ACC,
    ACC_GRANT,
    ACC_OT,
    ACC_PRIV,
    ACTORS,
    APPROVER,
    APPROVER2,
    ASSIGNEE,
    AUDITOR,
    AUTHOR,
    CI_FW,
    CI_INACTIVE,
    CI_OT,
    CI_OT2,
    CI_SRV,
    COMPANY_ID,
    EDITOR2,
    NET,
    NOW,
    OT,
    OUTSIDER,
    OWNER,
    VERIFIER,
    VIEWER,
    actor,
    context,
    in_status,
    ready_change,
)

S = ChangeStatus
A = ChangeAction
T = ChangeType

# --------------------------------------------------------------------------- oracle (§4.2)

ANY_TYPE = frozenset(ChangeType)


def _expected(action: A, status: S, change_type: T, approved: bool) -> frozenset[str]:
    """Actors (names from ``ACTORS``) allowed by table §4.2 for a NET change (no CI owner
    consent rule). Written from the spec, not from the implementation."""
    if status is S.DRAFT:
        if action is A.SUBMIT:  # editor (author or assignee)
            return frozenset({"author", "assignee"})
        if action is A.CANCEL:  # author
            return frozenset({"author"})
        if action is A.IMPLEMENT and change_type is T.EMERGENCY:  # emergency: editor
            return frozenset({"author", "assignee"})
    if status is S.PENDING_APPROVAL and action in {A.RETURN, A.APPROVE, A.REJECT}:
        return frozenset({"approver"})  # the designated approver, four eyes
    if status is S.APPROVED and action is A.IMPLEMENT:
        return frozenset({"assignee"})
    if status is S.APPROVED and action is A.CANCEL:  # owner decision 2026-10-29
        return frozenset({"author", "approver"})
    if status is S.IMPLEMENTED:
        if action is A.VERIFY and approved:
            return frozenset({"verifier"})
        if action is A.ROLLBACK:
            return frozenset({"assignee", "approver"})
        if action is A.APPROVE and change_type is T.EMERGENCY and not approved:
            return frozenset({"approver"})  # after the fact
    return frozenset()


MATRIX = list(itertools.product(ChangeStatus, ChangeType, [True, False], ChangeAction))


def _change(status: S, change_type: T, approved: bool) -> ChangeData:
    return in_status(
        status,
        change_type=change_type,
        approved_at=NOW - timedelta(hours=1) if approved else None,
    )


def _ids(case: tuple[S, T, bool, A]) -> str:
    status, change_type, approved, action = case
    return f"{action}-{status}-{change_type}-{'approved' if approved else 'unapproved'}"


@pytest.mark.parametrize("case", MATRIX, ids=[_ids(c) for c in MATRIX])
def test_transition_matrix(case: tuple[S, T, bool, A]) -> None:
    status, change_type, approved, action = case
    change = _change(status, change_type, approved)
    ctx = context()
    expected = _expected(action, status, change_type, approved)
    status_allows = any(
        (
            action is row.action
            and status is row.source
            and (row.change_types is None or change_type in row.change_types)
            and not (row.only_unapproved and approved)
            and not row.only_with_consent_rule
        )
        for row in TRANSITIONS
    )
    for name, user_id in ACTORS.items():
        who = actor(user_id)
        allowed = action in allowed_actions(change, who, ctx)
        assert allowed is (name in expected), f"{name}: allowed={allowed}"
        if allowed:
            outcome = execute(action, change, who, ctx, now=NOW, comment="Uzasadnienie.")
            assert outcome.action is action
            assert outcome.from_status is status
            continue
        with pytest.raises(ChangeRuleError) as info:
            execute(action, change, who, ctx, now=NOW, comment="Uzasadnienie.")
        code = info.value.code
        if not status_allows:
            assert code is ChangeErrorCode.INVALID_TRANSITION, name
        else:
            assert code in {
                ChangeErrorCode.FORBIDDEN_ACTOR,
                ChangeErrorCode.FOUR_EYES_VIOLATION,
                ChangeErrorCode.APPROVAL_MISSING,
                ChangeErrorCode.VERIFIER_IS_ASSIGNEE,
            }, (name, code)


@pytest.mark.parametrize(
    ("action", "status", "target"),
    [
        (A.SUBMIT, S.DRAFT, S.PENDING_APPROVAL),
        (A.RETURN, S.PENDING_APPROVAL, S.DRAFT),
        (A.APPROVE, S.PENDING_APPROVAL, S.APPROVED),
        (A.REJECT, S.PENDING_APPROVAL, S.REJECTED),
        (A.IMPLEMENT, S.APPROVED, S.IMPLEMENTED),
        (A.VERIFY, S.IMPLEMENTED, S.VERIFIED),
        (A.ROLLBACK, S.IMPLEMENTED, S.ROLLED_BACK),
        (A.CANCEL, S.DRAFT, S.CANCELLED),
        (A.CANCEL, S.APPROVED, S.CANCELLED),
    ],
)
def test_table_rows_reach_their_target(action: A, status: S, target: S) -> None:
    performer = {
        A.SUBMIT: AUTHOR,
        A.CANCEL: AUTHOR,
        A.IMPLEMENT: ASSIGNEE,
        A.VERIFY: VERIFIER,
        A.ROLLBACK: ASSIGNEE,
    }.get(action, APPROVER)
    outcome = execute(
        action, in_status(status), actor(performer), context(), now=NOW, comment="Powód."
    )
    assert outcome.to_status is target
    assert outcome.updates["status"] is target
    assert outcome.status_changed
    assert not outcome.performed_by_system


@pytest.mark.parametrize(
    ("action", "status", "stamp"),
    [
        (A.APPROVE, S.PENDING_APPROVAL, "approved_at"),
        (A.REJECT, S.PENDING_APPROVAL, "rejected_at"),
        (A.IMPLEMENT, S.APPROVED, "implemented_at"),
        (A.VERIFY, S.IMPLEMENTED, "verified_at"),
    ],
)
def test_timestamps_are_set_to_now(action: A, status: S, stamp: str) -> None:
    performer = {A.IMPLEMENT: ASSIGNEE, A.VERIFY: VERIFIER}.get(action, APPROVER)
    outcome = execute(
        action, in_status(status), actor(performer), context(), now=NOW, comment="Powód."
    )
    assert outcome.updates[stamp] == NOW


def test_role_sets_match_the_permission_matrix() -> None:
    assert PERMISSIONS[Action.CHANGE_EDIT_DRAFT] == WRITER_ROLES
    assert PERMISSIONS[Action.CHANGE_ASSIGN] == WRITER_ROLES
    assert PERMISSIONS[Action.CHANGE_APPROVE] == APPROVER_ROLES


def test_app_admin_without_company_role_can_do_nothing() -> None:
    admin = ActorFacts(OUTSIDER, frozenset())
    for status in ChangeStatus:
        change = in_status(status, change_type=T.EMERGENCY)
        assert allowed_actions(change, admin, context()) == ()
        assert editable_fields(change, admin, context()) == frozenset()


def test_app_admin_role_value_gives_no_rights() -> None:
    """Even if a caller passed ``app_admin`` as a role by mistake."""
    admin = ActorFacts(AUTHOR, frozenset({Role.APP_ADMIN}))
    assert allowed_actions(ready_change(), admin, context()) == ()


# --------------------------------------------------------------------------- four eyes


@pytest.mark.parametrize("action", [A.APPROVE, A.REJECT, A.RETURN])
@pytest.mark.parametrize("role_of_approver", ["requested_by_id", "assignee_id"])
def test_four_eyes_designated_approver_who_is_requester_or_assignee(
    action: A, role_of_approver: str
) -> None:
    approver_requester = uuid4()
    roles = frozenset({Role.APPROVER, Role.EDITOR})
    members = dict(context().members) | {approver_requester: MemberFacts(True, roles)}
    change = in_status(
        S.PENDING_APPROVAL,
        approver_id=approver_requester,
        **{role_of_approver: approver_requester},
    )
    with pytest.raises(ChangeRuleError) as info:
        execute(
            action,
            change,
            ActorFacts(approver_requester, roles),
            context(members=members),
            now=NOW,
            comment="x",
        )
    assert info.value.code is ChangeErrorCode.FOUR_EYES_VIOLATION
    assert info.value.kind is ErrorKind.FORBIDDEN
    assert action not in allowed_actions(
        change, ActorFacts(approver_requester, roles), context(members=members)
    )


def test_four_eyes_applies_to_emergency_approval_after_the_fact() -> None:
    change = in_status(
        S.IMPLEMENTED, change_type=T.EMERGENCY, approved_at=None, assignee_id=APPROVER2
    )
    with pytest.raises(ChangeRuleError) as info:
        execute(A.APPROVE, change, actor(APPROVER2), context(), now=NOW)
    assert info.value.code is ChangeErrorCode.FOUR_EYES_VIOLATION


def test_non_designated_approver_cannot_approve() -> None:
    with pytest.raises(ChangeRuleError) as info:
        execute(A.APPROVE, in_status(S.PENDING_APPROVAL), actor(APPROVER2), context(), now=NOW)
    assert info.value.code is ChangeErrorCode.FORBIDDEN_ACTOR


def test_designated_user_without_approver_role_cannot_approve() -> None:
    change = in_status(S.PENDING_APPROVAL, approver_id=EDITOR2)
    with pytest.raises(ChangeRuleError) as info:
        execute(A.APPROVE, change, actor(EDITOR2), context(), now=NOW)
    assert info.value.code is ChangeErrorCode.FORBIDDEN_ACTOR


def test_pending_change_without_approver_cannot_be_decided() -> None:
    change = in_status(S.PENDING_APPROVAL, approver_id=None)
    for user_id in (APPROVER, APPROVER2):
        assert allowed_actions(change, actor(user_id), context()) == ()


# --------------------------------------------------------------------------- comments


@pytest.mark.parametrize(
    ("action", "status", "performer"),
    [
        (A.RETURN, S.PENDING_APPROVAL, APPROVER),
        (A.REJECT, S.PENDING_APPROVAL, APPROVER),
        (A.ROLLBACK, S.IMPLEMENTED, ASSIGNEE),
        (A.ROLLBACK, S.IMPLEMENTED, APPROVER),
        (A.CANCEL, S.APPROVED, AUTHOR),
        (A.CANCEL, S.APPROVED, APPROVER),
    ],
)
@pytest.mark.parametrize("comment", [None, "", "   \n\t"])
def test_comment_required(action: A, status: S, performer: UUID, comment: str | None) -> None:
    change = in_status(status)
    assert action in allowed_actions(change, actor(performer), context())  # availability
    with pytest.raises(ChangeRuleError) as info:
        execute(action, change, actor(performer), context(), now=NOW, comment=comment)
    assert info.value.code is ChangeErrorCode.COMMENT_REQUIRED
    assert info.value.kind is ErrorKind.VALIDATION


def test_comment_is_trimmed_and_recorded_in_the_audit_context() -> None:
    outcome = execute(
        A.REJECT, in_status(S.PENDING_APPROVAL), actor(APPROVER), context(), now=NOW,
        comment="  Brak planu testów.  ",
    )  # fmt: skip
    assert outcome.comment == "Brak planu testów."
    assert outcome.audit_context() == {
        "action": "reject",
        "from_status": "pending_approval",
        "to_status": "rejected",
        "comment": "Brak planu testów.",
    }


def test_optional_comment_is_kept_and_blank_dropped() -> None:
    change = in_status(S.APPROVED)
    with_comment = execute(A.IMPLEMENT, change, actor(ASSIGNEE), context(), now=NOW, comment="OK")
    assert with_comment.comment == "OK"
    blank = execute(A.IMPLEMENT, change, actor(ASSIGNEE), context(), now=NOW, comment=" ")
    assert blank.comment is None
    assert "comment" not in blank.audit_context()


def test_comment_too_long() -> None:
    with pytest.raises(ChangeRuleError) as info:
        normalize_comment("x" * 4001, required=False)
    assert info.value.code is ChangeErrorCode.COMMENT_TOO_LONG
    assert normalize_comment("x" * 4000, required=True) == "x" * 4000


# --------------------------------------------------------------------------- submit


def test_submit_requires_readiness_and_reports_the_failed_checks() -> None:
    change = ready_change(title=" ", ci_ids=frozenset())
    assert A.SUBMIT in allowed_actions(change, actor(AUTHOR), context())
    with pytest.raises(ChangeRuleError) as info:
        execute(A.SUBMIT, change, actor(AUTHOR), context(), now=NOW)
    error = info.value
    assert error.code is ChangeErrorCode.NOT_READY
    assert error.fields == ("title", "ci_ids")
    failed = {c.code for c in error.checks if not c.ok}
    assert failed == {"title.required", "ci.required"}


def test_submit_by_assignee_and_by_author_with_approver_role() -> None:
    assert execute(A.SUBMIT, ready_change(), actor(ASSIGNEE), context(), now=NOW).to_status is (
        S.PENDING_APPROVAL
    )
    change = ready_change(requested_by_id=APPROVER2)
    outcome = execute(A.SUBMIT, change, actor(APPROVER2), context(), now=NOW)
    assert outcome.to_status is S.PENDING_APPROVAL


def test_submit_with_verifier_equal_to_assignee_fails_when_an_approver_exists() -> None:
    """The approver required by §4.3 is also a possible verifier, so at submission the
    "one person in the company" exception cannot apply (ADR 0012, question 3)."""
    solo = uuid4()
    members = {
        solo: MemberFacts(True, frozenset({Role.EDITOR})),
        APPROVER2: MemberFacts(True, frozenset({Role.APPROVER})),
    }
    change = ready_change(requested_by_id=solo, assignee_id=solo, verifier_id=solo,
                          approver_id=APPROVER2)  # fmt: skip
    with pytest.raises(ChangeRuleError) as info:
        execute(
            A.SUBMIT, change, actor(solo, frozenset({Role.EDITOR})), context(members=members),
            now=NOW,
        )  # fmt: skip
    assert info.value.code is ChangeErrorCode.NOT_READY
    assert [c.code for c in info.value.checks if not c.ok] == ["verifier.not_assignee"]


# --------------------------------------------------------------------------- standard


@pytest.mark.parametrize(
    ("category", "subcategory", "auto"),
    [
        (ACC, None, True),
        (ACC, ACC_GRANT, True),
        (ACC, ACC_PRIV, False),  # subcategory tightens (ADR 0011 §3)
        (ACC, ACC_OT, False),  # consent needs an approval round
        (NET, None, False),
        (OT, None, False),
    ],
)
def test_standard_auto_approval_depends_on_category_and_subcategory(
    category: UUID, subcategory: UUID | None, auto: bool
) -> None:
    cis = frozenset({CI_OT}) if subcategory is ACC_OT or category is OT else frozenset({CI_FW})
    change = ready_change(
        change_type=T.STANDARD, category_id=category, subcategory_id=subcategory, ci_ids=cis
    )
    outcome = execute(A.SUBMIT, change, actor(AUTHOR), context(), now=NOW)
    if auto:
        assert outcome.to_status is S.APPROVED
        assert outcome.performed_by_system
        # approved by system: no approver of record (ADR 0012 §4)
        assert outcome.updates == {"status": S.APPROVED, "approved_at": NOW}
        assert "approved_by_id" not in outcome.updates
        context_ = outcome.audit_context()
        assert context_["auto_approved"] is True
        assert context_["triggered_by"] == AUTHOR
        assert context_["to_status"] == "approved"
    else:
        assert outcome.to_status is S.PENDING_APPROVAL
        assert not outcome.performed_by_system
        assert outcome.updates == {"status": S.PENDING_APPROVAL}


@pytest.mark.parametrize("change_type", [T.NORMAL, T.EMERGENCY])
def test_only_standard_changes_are_auto_approved(change_type: T) -> None:
    change = ready_change(change_type=change_type, category_id=ACC)
    outcome = execute(A.SUBMIT, change, actor(AUTHOR), context(), now=NOW)
    assert outcome.to_status is S.PENDING_APPROVAL


# --------------------------------------------------------------------------- emergency


def test_emergency_implemented_from_draft_without_approval() -> None:
    change = ready_change(
        change_type=T.EMERGENCY,
        window_start=NOW - timedelta(hours=2),  # in the past: allowed for emergency
        window_end=NOW - timedelta(hours=1),
    )
    outcome = execute(A.IMPLEMENT, change, actor(AUTHOR), context(), now=NOW)
    assert outcome.to_status is S.IMPLEMENTED
    assert outcome.updates == {"status": S.IMPLEMENTED, "implemented_at": NOW}
    assert outcome.snapshot_ci
    assert outcome.approval_due_at == NOW + timedelta(hours=24)
    assert outcome.audit_context()["approval_due_at"] == NOW + timedelta(hours=24)


def test_emergency_implement_from_draft_requires_readiness() -> None:
    change = ready_change(change_type=T.EMERGENCY, implementation_plan=None)
    with pytest.raises(ChangeRuleError) as info:
        execute(A.IMPLEMENT, change, actor(ASSIGNEE), context(), now=NOW)
    assert info.value.code is ChangeErrorCode.NOT_READY


@pytest.mark.parametrize("change_type", [T.STANDARD, T.NORMAL])
def test_only_emergency_can_be_implemented_from_draft(change_type: T) -> None:
    with pytest.raises(ChangeRuleError) as info:
        execute(
            A.IMPLEMENT, ready_change(change_type=change_type), actor(AUTHOR), context(), now=NOW
        )
    assert info.value.code is ChangeErrorCode.INVALID_TRANSITION


def _emergency_implemented(implemented_at: datetime) -> ChangeData:
    return in_status(
        S.IMPLEMENTED, change_type=T.EMERGENCY, implemented_at=implemented_at, approved_at=None
    )


@pytest.mark.parametrize(
    ("elapsed", "late"),
    [
        (timedelta(hours=1), False),
        (timedelta(hours=24), False),  # exactly 24 h: still in time
        (timedelta(hours=24, microseconds=1), True),
        (timedelta(days=3), True),
    ],
)
def test_emergency_approval_after_the_fact(elapsed: timedelta, late: bool) -> None:
    change = _emergency_implemented(NOW - elapsed)
    outcome = execute(A.APPROVE, change, actor(APPROVER), context(), now=NOW)
    assert outcome.to_status is S.IMPLEMENTED
    assert not outcome.status_changed
    assert outcome.updates == {"approved_at": NOW, "approved_by_id": APPROVER}
    assert not outcome.snapshot_ci
    codes = [w.code for w in outcome.warnings]
    assert codes == (["emergency.approval_late"] if late else [])


def test_emergency_cannot_be_approved_twice() -> None:
    change = in_status(S.IMPLEMENTED, change_type=T.EMERGENCY)  # approved_at set
    with pytest.raises(ChangeRuleError) as info:
        execute(A.APPROVE, change, actor(APPROVER), context(), now=NOW)
    assert info.value.code is ChangeErrorCode.INVALID_TRANSITION


def test_emergency_must_be_approved_before_verification() -> None:
    change = _emergency_implemented(NOW - timedelta(hours=1))
    assert A.VERIFY not in allowed_actions(change, actor(VERIFIER), context())
    with pytest.raises(ChangeRuleError) as info:
        execute(A.VERIFY, change, actor(VERIFIER), context(), now=NOW)
    assert info.value.code is ChangeErrorCode.APPROVAL_MISSING
    assert info.value.kind is ErrorKind.CONFLICT
    # but it can be rolled back
    assert A.ROLLBACK in allowed_actions(change, actor(ASSIGNEE), context())


def test_emergency_can_also_take_the_normal_approval_path() -> None:
    change = ready_change(change_type=T.EMERGENCY)
    assert execute(A.SUBMIT, change, actor(AUTHOR), context(), now=NOW).to_status is (
        S.PENDING_APPROVAL
    )


# --------------------------------------------------------------------------- verify


def _solo_context(*extra: tuple[UUID, frozenset[Role]]) -> tuple[UUID, ChangeContext]:
    solo = uuid4()
    members = {
        solo: MemberFacts(True, frozenset({Role.EDITOR})),
        AUDITOR: MemberFacts(True, frozenset({Role.AUDITOR})),
        VIEWER: MemberFacts(True, frozenset({Role.VIEWER})),
        EDITOR2: MemberFacts(False, frozenset({Role.EDITOR})),  # inactive does not count
    } | {uid: MemberFacts(True, roles) for uid, roles in extra}
    return solo, context(members=members)


@pytest.mark.parametrize("designated", [True, False])
def test_verifier_equal_to_assignee_allowed_with_warning_in_one_person_company(
    designated: bool,
) -> None:
    solo, ctx = _solo_context()
    change = in_status(
        S.IMPLEMENTED,
        requested_by_id=solo,
        assignee_id=solo,
        verifier_id=solo if designated else None,
    )
    assert A.VERIFY in allowed_actions(change, actor(solo, frozenset({Role.EDITOR})), ctx)
    outcome = execute(A.VERIFY, change, ActorFacts(solo, frozenset({Role.EDITOR})), ctx, now=NOW)
    assert outcome.to_status is S.VERIFIED
    assert [w.code for w in outcome.warnings] == ["verifier.is_assignee"]
    assert outcome.audit_context()["warnings"] == [
        {"code": "verifier.is_assignee", "message_pl": outcome.warnings[0].message_pl}
    ]


@pytest.mark.parametrize("other_role", [Role.EDITOR, Role.APPROVER])
def test_verifier_equal_to_assignee_rejected_when_someone_else_can_verify(
    other_role: Role,
) -> None:
    solo, ctx = _solo_context((uuid4(), frozenset({other_role})))
    change = in_status(S.IMPLEMENTED, requested_by_id=solo, assignee_id=solo, verifier_id=solo)
    who = ActorFacts(solo, frozenset({Role.EDITOR}))
    assert A.VERIFY not in allowed_actions(change, who, ctx)
    with pytest.raises(ChangeRuleError) as info:
        execute(A.VERIFY, change, who, ctx, now=NOW)
    assert info.value.code is ChangeErrorCode.VERIFIER_IS_ASSIGNEE


def test_verification_without_designated_verifier_by_any_editor_but_not_viewer() -> None:
    change = in_status(S.IMPLEMENTED, verifier_id=None)
    assert A.VERIFY in allowed_actions(change, actor(EDITOR2), context())
    assert A.VERIFY in allowed_actions(change, actor(APPROVER2), context())
    assert A.VERIFY not in allowed_actions(change, actor(VIEWER), context())
    assert A.VERIFY not in allowed_actions(change, actor(ASSIGNEE), context())
    outcome = execute(A.VERIFY, change, actor(EDITOR2), context(), now=NOW)
    assert outcome.warnings == ()


# --------------------------------------------------------------------------- CI owner consent


def _ot_pending(**overrides: object) -> ChangeData:
    return in_status(
        S.PENDING_APPROVAL,
        category_id=OT,
        ci_ids=frozenset({CI_OT, CI_OT2, CI_SRV}),
        **overrides,
    )


def test_ci_owner_consent_flow() -> None:
    change = _ot_pending()
    ctx = context()
    assert A.CONSENT in allowed_actions(change, actor(OWNER), ctx)  # viewer role suffices
    assert A.CONSENT in allowed_actions(change, actor(EDITOR2), ctx)
    assert A.CONSENT not in allowed_actions(change, actor(APPROVER), ctx)

    with pytest.raises(ChangeRuleError) as info:
        execute(A.APPROVE, change, actor(APPROVER), ctx, now=NOW)
    assert info.value.code is ChangeErrorCode.CI_OWNER_CONSENT_MISSING
    assert info.value.message_pl.endswith("PLC-01, PLC-02, SRV-01.")

    outcome = execute(A.CONSENT, change, actor(OWNER), ctx, now=NOW)
    assert outcome.consented_ci_ids == {CI_OT, CI_OT2}
    assert outcome.updates == {}
    assert outcome.to_status is S.PENDING_APPROVAL
    assert outcome.audit_context()["consented_ci_ids"] == sorted([str(CI_OT), str(CI_OT2)])

    ctx = context(consented_ci_ids=frozenset({CI_OT, CI_OT2}))
    assert A.CONSENT not in allowed_actions(change, actor(OWNER), ctx)
    with pytest.raises(ChangeRuleError) as info:
        execute(A.CONSENT, change, actor(OWNER), ctx, now=NOW)
    assert info.value.code is ChangeErrorCode.INVALID_TRANSITION
    with pytest.raises(ChangeRuleError) as info:
        execute(A.APPROVE, change, actor(APPROVER), ctx, now=NOW)
    assert info.value.message_pl.endswith("SRV-01.")

    ctx = context(consented_ci_ids=frozenset({CI_OT, CI_OT2, CI_SRV}))
    assert execute(A.APPROVE, change, actor(APPROVER), ctx, now=NOW).to_status is S.APPROVED


def test_consent_by_a_non_owner_or_without_membership_is_forbidden() -> None:
    change = _ot_pending()
    for who in (actor(AUTHOR), ActorFacts(OWNER, frozenset())):
        with pytest.raises(ChangeRuleError) as info:
            execute(A.CONSENT, change, who, context(), now=NOW)
        assert info.value.code is ChangeErrorCode.FORBIDDEN_ACTOR


def test_consent_is_not_an_action_for_categories_without_the_rule() -> None:
    change = in_status(S.PENDING_APPROVAL, ci_ids=frozenset({CI_OT}))
    with pytest.raises(ChangeRuleError) as info:
        execute(A.CONSENT, change, actor(OWNER), context(), now=NOW)
    assert info.value.code is ChangeErrorCode.INVALID_TRANSITION


def test_subcategory_can_require_consent() -> None:
    change = in_status(
        S.PENDING_APPROVAL, category_id=ACC, subcategory_id=ACC_OT, ci_ids=frozenset({CI_OT})
    )
    assert A.CONSENT in allowed_actions(change, actor(OWNER), context())


def test_return_clears_consents() -> None:
    outcome = execute(
        A.RETURN, _ot_pending(), actor(APPROVER), context(), now=NOW, comment="Popraw plan."
    )
    assert outcome.clear_consents
    assert outcome.to_status is S.DRAFT


def test_emergency_ot_consent_before_approval_after_the_fact() -> None:
    change = in_status(
        S.IMPLEMENTED,
        change_type=T.EMERGENCY,
        approved_at=None,
        category_id=OT,
        ci_ids=frozenset({CI_OT}),
    )
    assert A.CONSENT in allowed_actions(change, actor(OWNER), context())
    with pytest.raises(ChangeRuleError) as info:
        execute(A.APPROVE, change, actor(APPROVER), context(), now=NOW)
    assert info.value.code is ChangeErrorCode.CI_OWNER_CONSENT_MISSING
    ctx = context(consented_ci_ids=frozenset({CI_OT}))
    assert execute(A.APPROVE, change, actor(APPROVER), ctx, now=NOW).updates == {
        "approved_at": NOW,
        "approved_by_id": APPROVER,
    }
    approved = replace(change, approved_at=NOW)
    assert A.CONSENT not in allowed_actions(approved, actor(OWNER), context())


# --------------------------------------------------------------------------- archived, time


def test_archived_company_blocks_every_action_and_edit() -> None:
    ctx = context(company=CompanyFacts(COMPANY_ID, is_archived=True))
    change = ready_change()
    assert allowed_actions(change, actor(AUTHOR), ctx) == ()
    with pytest.raises(ChangeRuleError) as info:
        execute(A.SUBMIT, change, actor(AUTHOR), ctx, now=NOW)
    assert info.value.code is ChangeErrorCode.COMPANY_ARCHIVED
    assert editable_fields(change, actor(AUTHOR), ctx) == frozenset()
    with pytest.raises(ChangeRuleError) as info:
        check_edit(change, replace(change, title="Nowy"), actor(AUTHOR), ctx, now=NOW)
    assert info.value.code is ChangeErrorCode.COMPANY_ARCHIVED


def test_naive_now_is_rejected() -> None:
    naive_now = datetime(2026, 10, 29, 12, 0)  # noqa: DTZ001
    with pytest.raises(ValueError, match="timezone-aware"):
        execute(A.SUBMIT, ready_change(), actor(AUTHOR), context(), now=naive_now)


def test_naive_change_timestamps_are_rejected() -> None:
    with pytest.raises(ValueError, match="window_start"):
        ready_change(window_start=datetime(2026, 11, 1, 8, 0))  # noqa: DTZ001


def test_check_access_returns_the_transition_row() -> None:
    row = check_access(A.APPROVE, in_status(S.PENDING_APPROVAL), actor(APPROVER), context())
    assert (row.source, row.target) == (S.PENDING_APPROVAL, S.APPROVED)


def test_snapshot_only_when_entering_implemented() -> None:
    implement = execute(A.IMPLEMENT, in_status(S.APPROVED), actor(ASSIGNEE), context(), now=NOW)
    assert implement.snapshot_ci
    verify = execute(A.VERIFY, in_status(S.IMPLEMENTED), actor(VERIFIER), context(), now=NOW)
    assert not verify.snapshot_ci
    assert not verify.clear_consents


# --------------------------------------------------------------------------- editing


def test_draft_is_fully_editable_by_editors_and_approvers() -> None:
    change = ready_change()
    for user_id in (AUTHOR, ASSIGNEE, EDITOR2, APPROVER, APPROVER2):
        assert editable_fields(change, actor(user_id), context()) == DRAFT_EDITABLE
    proposed = replace(change, title="Inny", risk=Risk.HIGH, ci_ids=frozenset({CI_FW, CI_SRV}))
    changed = check_edit(change, proposed, actor(EDITOR2), context(), now=NOW)
    assert changed == {ChangeField.TITLE, ChangeField.RISK, ChangeField.CI_IDS}
    # a draft may be incomplete
    incomplete = replace(change, title=None, window_start=NOW - timedelta(days=1))
    assert check_edit(change, incomplete, actor(AUTHOR), context(), now=NOW) == {
        ChangeField.TITLE,
        ChangeField.WINDOW_START,
    }


@pytest.mark.parametrize("user_id", [VIEWER, AUDITOR, OUTSIDER])
def test_draft_cannot_be_edited_without_writer_role(user_id: UUID) -> None:
    change = ready_change()
    assert editable_fields(change, actor(user_id), context()) == frozenset()
    with pytest.raises(ChangeRuleError) as info:
        check_edit(change, replace(change, title="X"), actor(user_id), context(), now=NOW)
    assert info.value.code is ChangeErrorCode.FORBIDDEN_ACTOR


def test_no_change_means_nothing_to_save() -> None:
    change = ready_change()
    assert check_edit(change, change, actor(AUTHOR), context(), now=NOW) == frozenset()


def test_requested_by_status_and_timestamps_are_never_edited_through_patch() -> None:
    change = ready_change()
    for proposed in (
        replace(change, requested_by_id=EDITOR2),
        replace(change, status=S.APPROVED),
        replace(change, approved_at=NOW),
        replace(change, company_id=uuid4()),
    ):
        with pytest.raises(ValueError, match="not editable through PATCH"):
            check_edit(change, proposed, actor(AUTHOR), context(), now=NOW)


def test_pending_approval_editable_by_approver_only_approver_and_window() -> None:
    change = in_status(S.PENDING_APPROVAL)
    for user_id in (APPROVER, APPROVER2):
        assert editable_fields(change, actor(user_id), context()) == PENDING_APPROVAL_EDITABLE
    for user_id in (AUTHOR, ASSIGNEE, EDITOR2, VIEWER):
        assert editable_fields(change, actor(user_id), context()) == frozenset()
    proposed = replace(
        change,
        approver_id=APPROVER2,
        window_start=NOW + timedelta(days=2),
        window_end=NOW + timedelta(days=2, hours=1),
    )
    assert check_edit(change, proposed, actor(APPROVER), context(), now=NOW) == {
        ChangeField.APPROVER_ID,
        ChangeField.WINDOW_START,
        ChangeField.WINDOW_END,
    }


@pytest.mark.parametrize(
    "field_name",
    sorted(f.value for f in ChangeField if f not in PENDING_APPROVAL_EDITABLE),
)
def test_pending_approval_other_fields_not_editable(field_name: str) -> None:
    change = in_status(S.PENDING_APPROVAL)
    new_value: object = {
        "ci_ids": frozenset({CI_SRV}),
        "change_type": T.EMERGENCY,
        "risk": Risk.LOW,
        "category_id": ACC,
        "subcategory_id": ACC_GRANT,
        "assignee_id": EDITOR2,
        "verifier_id": EDITOR2,
    }.get(field_name, "zmieniony tekst")
    with pytest.raises(ChangeRuleError) as info:
        check_edit(
            change, replace(change, **{field_name: new_value}), actor(APPROVER), context(), now=NOW
        )
    assert info.value.code is ChangeErrorCode.FIELD_NOT_EDITABLE
    assert info.value.fields == (field_name,)


def test_pending_approval_edit_by_requester_with_approver_role_is_forbidden() -> None:
    change = in_status(S.PENDING_APPROVAL, requested_by_id=APPROVER2)
    with pytest.raises(ChangeRuleError) as info:
        check_edit(
            change, replace(change, approver_id=APPROVER), actor(APPROVER2), context(), now=NOW
        )
    assert info.value.code is ChangeErrorCode.FORBIDDEN_ACTOR


@pytest.mark.parametrize(
    ("overrides", "failed"),
    [
        ({"approver_id": AUTHOR}, {"approver.eligible", "approver.four_eyes"}),
        ({"approver_id": EDITOR2}, {"approver.eligible"}),
        ({"approver_id": None}, {"approver.required"}),
        ({"window_start": NOW - timedelta(minutes=1)}, {"window.future"}),
        ({"window_end": NOW}, {"window.order"}),
    ],
)
def test_pending_approval_edit_is_validated_with_readiness_rules(
    overrides: dict[str, object], failed: set[str]
) -> None:
    change = in_status(S.PENDING_APPROVAL)
    with pytest.raises(ChangeRuleError) as info:
        check_edit(change, replace(change, **overrides), actor(APPROVER), context(), now=NOW)
    assert info.value.code is ChangeErrorCode.INVALID_EDIT
    assert {c.code for c in info.value.checks} == failed
    assert info.value.message_pl.startswith("Niespełnione warunki: ")


def test_approved_change_is_not_editable() -> None:
    change = in_status(S.APPROVED)
    for user_id in ACTORS.values():
        assert editable_fields(change, actor(user_id), context()) == frozenset()
    with pytest.raises(ChangeRuleError) as info:
        check_edit(change, replace(change, title="X"), actor(APPROVER), context(), now=NOW)
    assert info.value.code is ChangeErrorCode.FIELD_NOT_EDITABLE


@pytest.mark.parametrize(
    "status", [S.IMPLEMENTED, S.VERIFIED, S.ROLLED_BACK, S.REJECTED, S.CANCELLED]
)
@pytest.mark.parametrize("user_id", [AUTHOR, ASSIGNEE, APPROVER, APPROVER2])
def test_frozen_statuses(status: S, user_id: UUID) -> None:
    change = in_status(status)
    assert editable_fields(change, actor(user_id), context()) == frozenset()
    for proposed in (replace(change, title="Korekta"), change):
        with pytest.raises(ChangeRuleError) as info:
            check_edit(change, proposed, actor(user_id), context(), now=NOW)
        assert info.value.code is ChangeErrorCode.FROZEN
        assert info.value.kind is ErrorKind.CONFLICT


def test_editable_fields_is_consistent_with_check_edit() -> None:
    samples: dict[ChangeField, object] = {
        ChangeField.TITLE: "T",
        ChangeField.CATEGORY_ID: ACC,
        ChangeField.SUBCATEGORY_ID: ACC_GRANT,
        ChangeField.CHANGE_TYPE: T.EMERGENCY,
        ChangeField.RISK: Risk.LOW,
        ChangeField.DESCRIPTION: "D",
        ChangeField.IMPLEMENTATION_PLAN: "P",
        ChangeField.ROLLBACK_PLAN: "R",
        ChangeField.IMPACT: "I",
        ChangeField.REQUIREMENT_REF: "ISO",
        ChangeField.TICKET_REF: "T-1",
        ChangeField.ASSIGNEE_ID: EDITOR2,
        ChangeField.APPROVER_ID: APPROVER2,
        ChangeField.VERIFIER_ID: EDITOR2,
        ChangeField.WINDOW_START: NOW + timedelta(hours=3),
        ChangeField.WINDOW_END: NOW + timedelta(days=5),
        ChangeField.CI_IDS: frozenset({CI_SRV}),
    }
    assert set(samples) == set(ChangeField)
    for status, user_id, (field_, value) in itertools.product(
        ChangeStatus, ACTORS.values(), samples.items()
    ):
        change = in_status(status)
        who = actor(user_id)
        editable = field_ in editable_fields(change, who, context())
        try:
            check_edit(change, replace(change, **{field_.value: value}), who, context(), now=NOW)
        except ChangeRuleError:
            accepted = False
        else:
            accepted = True
        assert accepted is editable, (status, user_id, field_)


# --------------------------------------------------------------------------- owner decisions
# (ADR 0012 §10, 2026-10-29)


def test_one_person_company_standard_change_end_to_end() -> None:
    """Standard change without approval: no approver needed, submit auto-approves as system,
    the only person implements and verifies it with a warning for the audit."""
    solo = uuid4()
    who = ActorFacts(solo, frozenset({Role.EDITOR}))
    ctx = context(members={solo: MemberFacts(True, frozenset({Role.EDITOR}))})
    change = ready_change(
        change_type=T.STANDARD,
        category_id=ACC,
        requested_by_id=solo,
        assignee_id=solo,
        approver_id=None,
        verifier_id=None,
    )
    submitted = execute(A.SUBMIT, change, who, ctx, now=NOW)
    assert submitted.performed_by_system
    assert submitted.to_status is S.APPROVED

    change = replace(change, status=S.APPROVED, approved_at=NOW)
    assert change.window_start is not None
    implement_at = change.window_start + timedelta(minutes=5)
    implemented = execute(A.IMPLEMENT, change, who, ctx, now=implement_at)
    assert implemented.to_status is S.IMPLEMENTED
    assert implemented.warnings == ()

    change = replace(change, status=S.IMPLEMENTED, implemented_at=implement_at)
    assert A.VERIFY in allowed_actions(change, who, ctx)
    verified = execute(A.VERIFY, change, who, ctx, now=implement_at + timedelta(hours=1))
    assert verified.to_status is S.VERIFIED
    assert [w.code for w in verified.warnings] == ["verifier.is_assignee"]
    warnings = verified.audit_context()["warnings"]
    assert isinstance(warnings, list)
    assert warnings[0]["code"] == "verifier.is_assignee"


def test_one_person_company_designated_self_verifier_warns_at_submit() -> None:
    solo = uuid4()
    who = ActorFacts(solo, frozenset({Role.EDITOR}))
    ctx = context(members={solo: MemberFacts(True, frozenset({Role.EDITOR}))})
    change = ready_change(
        change_type=T.STANDARD,
        category_id=ACC,
        requested_by_id=solo,
        assignee_id=solo,
        approver_id=None,
        verifier_id=solo,
    )
    outcome = execute(A.SUBMIT, change, who, ctx, now=NOW)
    assert [w.code for w in outcome.warnings] == ["verifier.not_assignee"]


def test_auto_approved_standard_with_designated_approver_keeps_four_eyes() -> None:
    change = ready_change(change_type=T.STANDARD, category_id=ACC, approver_id=AUTHOR)
    with pytest.raises(ChangeRuleError) as info:
        execute(A.SUBMIT, change, actor(AUTHOR), context(), now=NOW)
    assert "approver.four_eyes" in {c.code for c in info.value.checks if not c.ok}


def test_cancel_approved_change() -> None:
    change = in_status(S.APPROVED)
    for performer in (AUTHOR, APPROVER):
        outcome = execute(
            A.CANCEL, change, actor(performer), context(), now=NOW, comment="Nieaktualna."
        )
        assert outcome.to_status is S.CANCELLED
        assert outcome.comment == "Nieaktualna."
    for other in (ASSIGNEE, APPROVER2, EDITOR2, VIEWER):
        assert A.CANCEL not in allowed_actions(change, actor(other), context())
    # auto-approved standard change without an approver: only the author
    auto = in_status(S.APPROVED, change_type=T.STANDARD, category_id=ACC, approver_id=None)
    assert A.CANCEL in allowed_actions(auto, actor(AUTHOR), context())


def test_cancel_from_draft_comment_stays_optional() -> None:
    outcome = execute(A.CANCEL, ready_change(), actor(AUTHOR), context(), now=NOW)
    assert outcome.comment is None


@pytest.mark.parametrize(
    ("anchor", "offset", "outside"),
    [
        ("start", -timedelta(minutes=1), True),  # before the window
        ("start", timedelta(0), False),  # exactly at start
        ("start", timedelta(minutes=30), False),
        ("end", timedelta(0), False),  # exactly at end
        ("end", timedelta(microseconds=1), True),  # after the window
    ],
)
def test_implement_outside_window_is_allowed_with_warning(
    anchor: str, offset: timedelta, outside: bool
) -> None:
    change = in_status(S.APPROVED)
    assert change.window_start is not None
    assert change.window_end is not None
    when = (change.window_start if anchor == "start" else change.window_end) + offset
    outcome = execute(A.IMPLEMENT, change, actor(ASSIGNEE), context(), now=when)
    assert outcome.to_status is S.IMPLEMENTED
    codes = [w.code for w in outcome.warnings]
    assert codes == (["implementation.outside_window"] if outside else [])


def test_implement_without_window_or_emergency_never_warns() -> None:
    no_window = in_status(S.APPROVED, window_start=None, window_end=None)
    assert execute(A.IMPLEMENT, no_window, actor(ASSIGNEE), context(), now=NOW).warnings == ()
    emergency = ready_change(change_type=T.EMERGENCY)  # window in the future, still fine
    assert execute(A.IMPLEMENT, emergency, actor(AUTHOR), context(), now=NOW).warnings == ()


def test_approve_rechecks_readiness() -> None:
    # CI deactivated after submission: blocks
    change = in_status(S.PENDING_APPROVAL, ci_ids=frozenset({CI_FW, CI_INACTIVE}))
    with pytest.raises(ChangeRuleError) as info:
        execute(A.APPROVE, change, actor(APPROVER), context(), now=NOW)
    assert info.value.code is ChangeErrorCode.NOT_READY
    assert {c.code for c in info.value.checks if not c.ok} == {"ci.active"}
    # assignee lost the role: blocks
    members = dict(context().members) | {ASSIGNEE: MemberFacts(True, frozenset({Role.VIEWER}))}
    with pytest.raises(ChangeRuleError) as info:
        execute(
            A.APPROVE,
            in_status(S.PENDING_APPROVAL),
            actor(APPROVER),
            context(members=members),
            now=NOW,
        )
    assert {c.code for c in info.value.checks if not c.ok} == {"assignee.eligible"}


def test_approve_with_window_already_started_warns_only() -> None:
    change = in_status(S.PENDING_APPROVAL)
    assert change.window_start is not None
    late = change.window_start + timedelta(minutes=10)
    outcome = execute(A.APPROVE, change, actor(APPROVER), context(), now=late)
    assert outcome.to_status is S.APPROVED
    assert [w.code for w in outcome.warnings] == ["window.future"]
    assert outcome.warnings[0].ok
    # a broken window still blocks
    broken = replace(change, window_end=change.window_start)
    with pytest.raises(ChangeRuleError) as info:
        execute(A.APPROVE, broken, actor(APPROVER), context(), now=late)
    assert {c.code for c in info.value.checks if not c.ok} == {"window.order"}


def test_emergency_approval_after_the_fact_does_not_recheck_readiness() -> None:
    change = in_status(
        S.IMPLEMENTED,
        change_type=T.EMERGENCY,
        approved_at=None,
        ci_ids=frozenset({CI_INACTIVE}),  # would fail readiness
    )
    assert execute(A.APPROVE, change, actor(APPROVER), context(), now=NOW).updates == {
        "approved_at": NOW,
        "approved_by_id": APPROVER,
    }


def _verifier_gone() -> tuple[ChangeData, ChangeContext]:
    members = dict(context().members) | {VERIFIER: MemberFacts(False, frozenset({Role.EDITOR}))}
    return in_status(S.IMPLEMENTED), context(members=members)


def test_approver_can_reassign_a_verifier_who_can_no_longer_verify() -> None:
    change, ctx = _verifier_gone()
    assert A.VERIFY not in allowed_actions(change, actor(EDITOR2), ctx)
    for user_id in (APPROVER, APPROVER2):
        assert editable_fields(change, actor(user_id), ctx) == {ChangeField.VERIFIER_ID}
    for user_id in (AUTHOR, ASSIGNEE, EDITOR2, VIEWER):
        assert editable_fields(change, actor(user_id), ctx) == frozenset()
    proposed = replace(change, verifier_id=EDITOR2)
    assert check_edit(change, proposed, actor(APPROVER), ctx, now=NOW) == {ChangeField.VERIFIER_ID}
    # cleared: any editor/approver may verify
    cleared = replace(change, verifier_id=None)
    assert check_edit(change, cleared, actor(APPROVER), ctx, now=NOW) == {ChangeField.VERIFIER_ID}


@pytest.mark.parametrize(
    ("new_verifier", "failed"),
    [(VIEWER, {"verifier.eligible"}), (ASSIGNEE, {"verifier.not_assignee"})],
)
def test_reassigned_verifier_is_validated(new_verifier: UUID, failed: set[str]) -> None:
    change, ctx = _verifier_gone()
    proposed = replace(change, verifier_id=new_verifier)
    with pytest.raises(ChangeRuleError) as info:
        check_edit(change, proposed, actor(APPROVER), ctx, now=NOW)
    assert info.value.code is ChangeErrorCode.INVALID_EDIT
    assert {c.code for c in info.value.checks} == failed


def test_ksc_reassigned_verifier_cannot_be_cleared() -> None:
    change, ctx = _verifier_gone()
    ksc = replace(ctx, company=CompanyFacts(COMPANY_ID, is_ksc_entity=True))
    with pytest.raises(ChangeRuleError) as info:
        check_edit(change, replace(change, verifier_id=None), actor(APPROVER), ksc, now=NOW)
    assert {c.code for c in info.value.checks} == {"verifier.required_ksc"}


def test_verifier_reassignment_is_narrow() -> None:
    change, ctx = _verifier_gone()
    cases = [
        (replace(change, verifier_id=EDITOR2, title="X"), actor(APPROVER), ctx),  # other field
        (replace(change, verifier_id=EDITOR2), actor(AUTHOR), ctx),  # not an approver
        (replace(change, verifier_id=EDITOR2), actor(APPROVER), context()),  # verifier fine
    ]
    for proposed, who, case_ctx in cases:
        with pytest.raises(ChangeRuleError) as info:
            check_edit(change, proposed, who, case_ctx, now=NOW)
        assert info.value.code is ChangeErrorCode.FROZEN
    verified = in_status(S.VERIFIED)
    with pytest.raises(ChangeRuleError) as info:
        check_edit(verified, replace(verified, verifier_id=EDITOR2), actor(APPROVER), ctx, now=NOW)
    assert info.value.code is ChangeErrorCode.FROZEN


# --------------------------------------------------------------------------- approver of record


def test_approve_records_the_actual_approver() -> None:
    outcome = execute(A.APPROVE, in_status(S.PENDING_APPROVAL), actor(APPROVER), context(), now=NOW)
    assert outcome.updates["approved_by_id"] == APPROVER
    for action, change, who in (
        (A.REJECT, in_status(S.PENDING_APPROVAL), APPROVER),
        (A.IMPLEMENT, in_status(S.APPROVED), ASSIGNEE),
    ):
        updates = execute(action, change, actor(who), context(), now=NOW, comment="Powód.").updates
        assert "approved_by_id" not in updates


# --------------------------------------------------------------------------- approver reassignment


def _emergency_approver_gone(
    *, approver_member: MemberFacts | None = None
) -> tuple[ChangeData, ChangeContext]:
    members = dict(context().members)
    if approver_member is None:
        members.pop(APPROVER)
    else:
        members[APPROVER] = approver_member
    change = in_status(
        S.IMPLEMENTED, change_type=T.EMERGENCY, approved_at=None, approved_by_id=None
    )
    return change, context(members=members)


@pytest.mark.parametrize(
    "gone",
    [
        None,  # no longer a member
        MemberFacts(False, frozenset({Role.APPROVER})),  # deactivated
        MemberFacts(True, frozenset({Role.EDITOR})),  # lost the approver role
    ],
)
def test_another_approver_re_points_an_emergency_approver_who_is_gone(
    gone: MemberFacts | None,
) -> None:
    change, ctx = _emergency_approver_gone(approver_member=gone)
    assert approver_reassignable(change, ctx)
    assert editable_fields(change, actor(APPROVER2), ctx) == {ChangeField.APPROVER_ID}
    for user_id in (AUTHOR, ASSIGNEE, EDITOR2, VIEWER):
        assert editable_fields(change, actor(user_id), ctx) == frozenset()
    proposed = replace(change, approver_id=APPROVER2)
    assert check_edit(change, proposed, actor(APPROVER2), ctx, now=NOW) == {ChangeField.APPROVER_ID}
    # ... and then approves after the fact
    assert A.APPROVE in allowed_actions(proposed, actor(APPROVER2), ctx)


def test_reassigned_approver_is_validated() -> None:
    change, ctx = _emergency_approver_gone()
    for new_approver, failed in (
        (ASSIGNEE, {"approver.eligible", "approver.four_eyes"}),
        (EDITOR2, {"approver.eligible"}),
        (None, {"approver.required"}),
    ):
        with pytest.raises(ChangeRuleError) as info:
            check_edit(
                change, replace(change, approver_id=new_approver), actor(APPROVER2), ctx, now=NOW
            )
        assert info.value.code is ChangeErrorCode.INVALID_EDIT
        assert {c.code for c in info.value.checks} == failed


def test_approver_reassignment_is_narrow() -> None:
    change, ctx = _emergency_approver_gone()
    approved = replace(change, approved_at=NOW, approved_by_id=APPROVER)
    normal = replace(change, change_type=T.NORMAL, approved_at=NOW)
    for subject in (approved, normal, in_status(S.VERIFIED, change_type=T.EMERGENCY)):
        assert not approver_reassignable(subject, ctx)
        with pytest.raises(ChangeRuleError) as info:
            check_edit(
                subject, replace(subject, approver_id=APPROVER2), actor(APPROVER2), ctx, now=NOW
            )
        assert info.value.code is ChangeErrorCode.FROZEN
    # designated approver still active: nothing to re-point
    still, ctx_ok = (
        in_status(S.IMPLEMENTED, change_type=T.EMERGENCY, approved_at=None, approved_by_id=None),
        context(),
    )
    assert not approver_reassignable(still, ctx_ok)
    assert editable_fields(still, actor(APPROVER2), ctx_ok) == frozenset()
    # the requester / assignee never re-points (four eyes)
    with pytest.raises(ChangeRuleError):
        check_edit(change, replace(change, approver_id=APPROVER2), actor(AUTHOR), ctx, now=NOW)


def test_both_reassignments_at_once() -> None:
    members = dict(context().members)
    members.pop(APPROVER)
    members[VERIFIER] = MemberFacts(False, frozenset({Role.EDITOR}))
    ctx = context(members=members)
    change = in_status(
        S.IMPLEMENTED, change_type=T.EMERGENCY, approved_at=None, approved_by_id=None
    )
    assert editable_fields(change, actor(APPROVER2), ctx) == {
        ChangeField.APPROVER_ID,
        ChangeField.VERIFIER_ID,
    }
    proposed = replace(change, approver_id=APPROVER2, verifier_id=EDITOR2)
    assert check_edit(change, proposed, actor(APPROVER2), ctx, now=NOW) == {
        ChangeField.APPROVER_ID,
        ChangeField.VERIFIER_ID,
    }
