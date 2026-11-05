"""Change state machine (CLAUDE.md §4.2, ADR 0012). Pure Python, no I/O.

The only place that decides status transitions and field editability of a change. The
service loads :class:`~app.domain.changes.ChangeData`, the actor's company roles and the
:class:`~app.domain.changes.ChangeContext`, then:

- ``POST …/actions/{action}`` -> :func:`execute` -> apply ``outcome.updates``, record the
  audit entry (``outcome.performed_by_system`` -> actor ``system``; ``outcome.audit_context()``);
- ``PATCH`` -> :func:`check_edit` (raises, or returns the changed fields);
- responses -> :func:`allowed_actions` and :func:`editable_fields`.

Errors are :class:`~app.domain.changes.ChangeRuleError`. They come in two groups:

1. **access** (:func:`check_access`): archived company, action impossible in the status
   (or for the change type / approval state), actor not allowed, four eyes, verifier =
   assignee. :func:`allowed_actions` is exactly the set of actions without an access
   error.
2. **input / data preconditions** (only in :func:`execute`): comment required or too
   long, readiness for ``submit`` and the emergency ``implement``, missing CI owner
   consent for ``approve``. The action stays in ``allowed_actions``; the frontend shows
   readiness separately and the error explains what is missing.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, fields
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from uuid import UUID

from app.domain.changes import (
    APPROVER_ROLES,
    COMMENT_MAX_LENGTH,
    FROZEN_STATUSES,
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
    Check,
    CheckLevel,
    require_aware,
)
from app.domain.deviations import emergency_approval_deadline, implemented_outside_window
from app.domain.readiness import (
    approval_readiness,
    approver_checks,
    is_auto_approved,
    readiness,
    requires_ci_owner_consent,
    verifier_checks,
    verifier_may_be_assignee,
    window_checks,
)

S = ChangeStatus
A = ChangeAction


class ActorRule(StrEnum):
    """Who may perform a transition (column "Kto" of §4.2, ADR 0012 §4)."""

    AUTHOR = "author"  # requested_by, role editor/approver
    AUTHOR_OR_ASSIGNEE = "author_or_assignee"  # requested_by or assignee, editor/approver
    ASSIGNEE = "assignee"  # assignee, editor/approver
    DESIGNATED_APPROVER = "designated_approver"  # approver_id, role approver, four eyes
    ASSIGNEE_OR_APPROVER = "assignee_or_approver"
    AUTHOR_OR_APPROVER = "author_or_approver"  # requested_by (editor/approver) or approver_id
    VERIFIER = "verifier"  # verifier_id (or any editor/approver), != assignee if possible
    CI_OWNER = "ci_owner"  # owner of a CI of the change, any membership role


@dataclass(frozen=True, slots=True)
class Transition:
    action: ChangeAction
    source: ChangeStatus
    target: ChangeStatus
    actor: ActorRule
    change_types: frozenset[ChangeType] | None = None  # None = every type
    comment_required: bool = False
    sets_timestamp: str | None = None  # ChangeData attribute set to ``now``
    requires_readiness: bool = False  # readiness() without errors (submit, emergency)
    rechecks_readiness: bool = False  # approval_readiness() without errors (approve)
    only_unapproved: bool = False  # emergency after-the-fact (approved_at IS NULL)
    only_with_consent_rule: bool = False  # category requires the CI owner's consent


_EMERGENCY = frozenset({ChangeType.EMERGENCY})

TRANSITIONS: tuple[Transition, ...] = (
    # draft -> pending_approval; a standard change whose category needs no approval goes
    # straight to approved, performed by ``system`` (see execute()).
    Transition(A.SUBMIT, S.DRAFT, S.PENDING_APPROVAL, ActorRule.AUTHOR_OR_ASSIGNEE,
               requires_readiness=True),
    Transition(A.RETURN, S.PENDING_APPROVAL, S.DRAFT, ActorRule.DESIGNATED_APPROVER,
               comment_required=True),
    Transition(A.APPROVE, S.PENDING_APPROVAL, S.APPROVED, ActorRule.DESIGNATED_APPROVER,
               sets_timestamp="approved_at", rechecks_readiness=True),
    Transition(A.REJECT, S.PENDING_APPROVAL, S.REJECTED, ActorRule.DESIGNATED_APPROVER,
               comment_required=True, sets_timestamp="rejected_at"),
    Transition(A.IMPLEMENT, S.APPROVED, S.IMPLEMENTED, ActorRule.ASSIGNEE,
               sets_timestamp="implemented_at"),
    Transition(A.VERIFY, S.IMPLEMENTED, S.VERIFIED, ActorRule.VERIFIER,
               sets_timestamp="verified_at"),
    Transition(A.ROLLBACK, S.IMPLEMENTED, S.ROLLED_BACK, ActorRule.ASSIGNEE_OR_APPROVER,
               comment_required=True),
    Transition(A.CANCEL, S.DRAFT, S.CANCELLED, ActorRule.AUTHOR),
    # approved but no longer needed (owner decision 2026-10-29)
    Transition(A.CANCEL, S.APPROVED, S.CANCELLED, ActorRule.AUTHOR_OR_APPROVER,
               comment_required=True),
    # emergency: implemented first, approved after the fact within 24 h
    Transition(A.IMPLEMENT, S.DRAFT, S.IMPLEMENTED, ActorRule.AUTHOR_OR_ASSIGNEE,
               change_types=_EMERGENCY, sets_timestamp="implemented_at",
               requires_readiness=True),
    Transition(A.APPROVE, S.IMPLEMENTED, S.IMPLEMENTED, ActorRule.DESIGNATED_APPROVER,
               change_types=_EMERGENCY, sets_timestamp="approved_at", only_unapproved=True),
    # CI owner consent (OT): in the approval round, or before the after-the-fact approval
    Transition(A.CONSENT, S.PENDING_APPROVAL, S.PENDING_APPROVAL, ActorRule.CI_OWNER,
               only_with_consent_rule=True),
    Transition(A.CONSENT, S.IMPLEMENTED, S.IMPLEMENTED, ActorRule.CI_OWNER,
               change_types=_EMERGENCY, only_unapproved=True, only_with_consent_rule=True),
)  # fmt: skip

ACTION_LABELS_PL: Mapping[ChangeAction, str] = MappingProxyType(
    {
        A.SUBMIT: "Wyślij do zatwierdzenia",
        A.RETURN: "Zwróć do poprawy",
        A.APPROVE: "Zatwierdź",
        A.REJECT: "Odrzuć",
        A.IMPLEMENT: "Oznacz jako wdrożoną",
        A.VERIFY: "Zweryfikuj",
        A.ROLLBACK: "Wycofaj",
        A.CANCEL: "Anuluj",
        A.CONSENT: "Wyraź zgodę właściciela obiektu",
    }
)

DRAFT_EDITABLE: frozenset[ChangeField] = frozenset(ChangeField)
PENDING_APPROVAL_EDITABLE: frozenset[ChangeField] = frozenset(
    {ChangeField.APPROVER_ID, ChangeField.WINDOW_START, ChangeField.WINDOW_END}
)
# implemented: only re-assigning a verifier who can no longer verify (ADR 0012 §6)
IMPLEMENTED_EDITABLE: frozenset[ChangeField] = frozenset(
    {ChangeField.VERIFIER_ID, ChangeField.APPROVER_ID}
)
_WINDOW_FIELDS = frozenset({ChangeField.WINDOW_START, ChangeField.WINDOW_END})
# ChangeData attributes that are not edited through PATCH: identity, status, timestamps.
_NON_EDITABLE_ATTRIBUTES = frozenset(f.name for f in fields(ChangeData)) - {
    f.value for f in ChangeField
}

SYSTEM_TRIGGER_REASON = "standard_change_without_approval"


# --------------------------------------------------------------------------- outcome


@dataclass(frozen=True, slots=True)
class TransitionOutcome:
    """What the service persists after a successful action.

    - ``updates``: ChangeData attributes to set (``status`` and timestamps; empty for
      ``consent``);
    - ``performed_by_system``: record the audit entry with actor ``system``
      (standard auto-approval); ``triggered_by`` is the user who submitted;
    - ``consented_ci_ids``: consents to store (``consent``);
    - ``clear_consents``: drop the consents of the change (``return`` - the change may be
      edited again, so the owners consent anew);
    - ``snapshot_ci``: entering ``implemented`` freezes the change - store the CI
      identifier/name snapshot in ``change_items`` (ADR 0011 §9 pt 5);
    - ``warnings``: recorded in the audit context (e.g. verifier = assignee in a company
      with one person, §4.2).
    """

    action: ChangeAction
    from_status: ChangeStatus
    to_status: ChangeStatus
    triggered_by: UUID
    performed_by_system: bool = False
    updates: Mapping[str, object] = field(default_factory=dict)
    comment: str | None = None
    warnings: tuple[Check, ...] = ()
    consented_ci_ids: frozenset[UUID] = frozenset()
    clear_consents: bool = False
    snapshot_ci: bool = False
    approval_due_at: datetime | None = None

    @property
    def status_changed(self) -> bool:
        return self.from_status is not self.to_status

    def audit_context(self) -> dict[str, object]:
        """``audit_log.context`` for this action (JSON-normalized by ``app.domain.audit``)."""
        context: dict[str, object] = {
            "action": self.action.value,
            "from_status": self.from_status.value,
            "to_status": self.to_status.value,
        }
        if self.comment is not None:
            context["comment"] = self.comment
        if self.performed_by_system:
            context["auto_approved"] = True
            context["reason"] = SYSTEM_TRIGGER_REASON
            context["triggered_by"] = self.triggered_by
        if self.warnings:
            context["warnings"] = [
                {"code": w.code, "message_pl": w.message_pl} for w in self.warnings
            ]
        if self.consented_ci_ids:
            context["consented_ci_ids"] = sorted(str(ci) for ci in self.consented_ci_ids)
        if self.approval_due_at is not None:
            context["approval_due_at"] = self.approval_due_at
        return context


# --------------------------------------------------------------------------- access


def _error(code: ChangeErrorCode, message_pl: str | None = None) -> ChangeRuleError:
    return ChangeRuleError(code, message_pl)


def _invalid_transition(action: ChangeAction, change: ChangeData) -> ChangeRuleError:
    return _error(
        ChangeErrorCode.INVALID_TRANSITION,
        f"Akcji „{ACTION_LABELS_PL[action]}” nie można wykonać dla zmiany w statusie "
        f"„{change.status.label_pl}”.",
    )


def _find_transition(
    action: ChangeAction, change: ChangeData, ctx: ChangeContext
) -> Transition | ChangeRuleError:
    for row in TRANSITIONS:
        if row.action is not action or row.source is not change.status:
            continue
        if row.change_types is not None and change.change_type not in row.change_types:
            continue
        if row.only_unapproved and change.approved_at is not None:
            continue
        if row.only_with_consent_rule and not requires_ci_owner_consent(change, ctx):
            continue
        return row
    return _invalid_transition(action, change)


def _approver_error(change: ChangeData, actor: ActorFacts) -> ChangeRuleError | None:
    if not actor.roles & APPROVER_ROLES:
        return _error(
            ChangeErrorCode.FORBIDDEN_ACTOR,
            "Tę akcję może wykonać tylko użytkownik z rolą zatwierdzającego w spółce.",
        )
    if actor.user_id in {change.requested_by_id, change.assignee_id}:
        return _error(ChangeErrorCode.FOUR_EYES_VIOLATION)
    if actor.user_id != change.approver_id:
        return _error(
            ChangeErrorCode.FORBIDDEN_ACTOR,
            "Tę akcję może wykonać tylko zatwierdzający wskazany w zmianie.",
        )
    return None


def _owned_pending_ci(change: ChangeData, actor: ActorFacts, ctx: ChangeContext) -> set[UUID]:
    return {
        ci_id
        for ci_id in change.ci_ids
        if (ci := ctx.cis.get(ci_id)) is not None and ci.owner_user_id == actor.user_id
    }


def _actor_error(
    rule: ActorRule, change: ChangeData, actor: ActorFacts, ctx: ChangeContext
) -> ChangeRuleError | None:
    uid = actor.user_id
    writer = bool(actor.roles & WRITER_ROLES)
    if rule is ActorRule.DESIGNATED_APPROVER:
        return _approver_error(change, actor)
    if rule is ActorRule.CI_OWNER:
        owned = _owned_pending_ci(change, actor, ctx) if actor.roles else set()
        if not owned:
            return _error(
                ChangeErrorCode.FORBIDDEN_ACTOR,
                "Zgodę może wyrazić tylko właściciel obiektu (CI), którego dotyczy zmiana.",
            )
        if owned <= ctx.consented_ci_ids:
            return _error(
                ChangeErrorCode.INVALID_TRANSITION,
                "Zgoda na zmianę Twoich obiektów (CI) została już wyrażona.",
            )
        return None
    if rule is ActorRule.VERIFIER:
        if not writer or (change.verifier_id is not None and uid != change.verifier_id):
            return _error(
                ChangeErrorCode.FORBIDDEN_ACTOR,
                "Zmianę może zweryfikować tylko wskazany weryfikujący."
                if change.verifier_id is not None
                else "Zmianę może zweryfikować użytkownik z rolą edytora lub zatwierdzającego.",
            )
        if uid == change.assignee_id and not verifier_may_be_assignee(change, ctx):
            return _error(ChangeErrorCode.VERIFIER_IS_ASSIGNEE)
        return None
    allowed: bool
    if rule is ActorRule.AUTHOR:
        allowed = writer and uid == change.requested_by_id
        message = "Tę akcję może wykonać tylko autor (zgłaszający) zmiany."
    elif rule is ActorRule.AUTHOR_OR_ASSIGNEE:
        allowed = writer and uid in {change.requested_by_id, change.assignee_id}
        message = "Tę akcję może wykonać tylko autor (zgłaszający) lub wykonawca zmiany."
    elif rule is ActorRule.ASSIGNEE:
        allowed = writer and uid == change.assignee_id
        message = "Tę akcję może wykonać tylko wykonawca zmiany."
    elif rule is ActorRule.AUTHOR_OR_APPROVER:
        allowed = (writer and uid == change.requested_by_id) or (
            bool(actor.roles & APPROVER_ROLES) and uid == change.approver_id
        )
        message = "Tę akcję może wykonać tylko autor (zgłaszający) lub zatwierdzający zmiany."
    else:  # ASSIGNEE_OR_APPROVER
        allowed = (writer and uid == change.assignee_id) or (
            bool(actor.roles & APPROVER_ROLES) and uid == change.approver_id
        )
        message = "Tę akcję może wykonać tylko wykonawca lub zatwierdzający zmiany."
    return None if allowed else _error(ChangeErrorCode.FORBIDDEN_ACTOR, message)


def check_access(
    action: ChangeAction, change: ChangeData, actor: ActorFacts, ctx: ChangeContext
) -> Transition:
    """The transition ``action`` would perform, or raise the access error (see module doc)."""
    if ctx.company.is_archived:
        raise _error(ChangeErrorCode.COMPANY_ARCHIVED)
    found = _find_transition(action, change, ctx)
    if isinstance(found, ChangeRuleError):
        raise found
    error = _actor_error(found.actor, change, actor, ctx)
    if error is not None:
        raise error
    if found.action is A.VERIFY and change.approved_at is None:
        # only an emergency change can reach implemented without approval
        raise _error(ChangeErrorCode.APPROVAL_MISSING)
    return found


def allowed_actions(
    change: ChangeData, actor: ActorFacts, ctx: ChangeContext
) -> tuple[ChangeAction, ...]:
    """Actions the actor can perform now (``allowed_actions`` in the change response)."""
    result = []
    for action in ChangeAction:
        try:
            check_access(action, change, actor, ctx)
        except ChangeRuleError:
            continue
        result.append(action)
    return tuple(result)


# --------------------------------------------------------------------------- execute


def normalize_comment(comment: str | None, *, required: bool) -> str | None:
    clean = None if comment is None or not comment.strip() else comment.strip()
    if clean is None and required:
        raise _error(ChangeErrorCode.COMMENT_REQUIRED)
    if clean is not None and len(clean) > COMMENT_MAX_LENGTH:
        raise _error(ChangeErrorCode.COMMENT_TOO_LONG)
    return clean


def _consent_missing(change: ChangeData, ctx: ChangeContext) -> ChangeRuleError | None:
    if not requires_ci_owner_consent(change, ctx):
        return None
    missing = change.ci_ids - ctx.consented_ci_ids
    if not missing:
        return None
    names = sorted(ci.identifier if (ci := ctx.cis.get(i)) else str(i) for i in missing)
    return ChangeRuleError(
        ChangeErrorCode.CI_OWNER_CONSENT_MISSING,
        "Brak zgody właściciela obiektów (CI): " + ", ".join(names) + ".",
        fields=("ci_ids",),
    )


def execute(
    action: ChangeAction,
    change: ChangeData,
    actor: ActorFacts,
    ctx: ChangeContext,
    *,
    now: datetime,
    comment: str | None = None,
) -> TransitionOutcome:
    """Validate ``action`` and return what to persist; raises :class:`ChangeRuleError`."""
    require_aware(now, "now")
    row = check_access(action, change, actor, ctx)
    clean_comment = normalize_comment(comment, required=row.comment_required)

    warnings: list[Check] = []
    if row.requires_readiness or row.rechecks_readiness:
        report = (
            readiness(change, ctx, now=now)
            if row.requires_readiness
            else approval_readiness(change, ctx, now=now)
        )
        if not report.ok:
            raise ChangeRuleError(
                ChangeErrorCode.NOT_READY,
                fields=tuple(dict.fromkeys(c.field for c in report.errors if c.field)),
                checks=report.checks,
            )
        warnings.extend(report.warnings)
    if row.action is A.APPROVE:
        consent_error = _consent_missing(change, ctx)
        if consent_error is not None:
            raise consent_error

    target = row.target
    timestamp = row.sets_timestamp
    by_system = False
    if row.action is A.SUBMIT and is_auto_approved(change, ctx):
        target, timestamp, by_system = S.APPROVED, "approved_at", True

    updates: dict[str, object] = {}
    if target is not change.status:
        updates["status"] = target
    if timestamp is not None:
        updates[timestamp] = now
    if row.action is A.APPROVE:
        # the approver of record (ADR 0012 §4); auto-approval leaves it None (= system)
        updates["approved_by_id"] = actor.user_id

    # emergency implemented from draft: the after-the-fact approval is due within 24 h
    approval_due_at = (
        emergency_approval_deadline(now)
        if row.action is A.IMPLEMENT and row.source is S.DRAFT
        else None
    )
    if row.action is A.APPROVE and row.only_unapproved and change.implemented_at is not None:
        deadline = emergency_approval_deadline(change.implemented_at)
        if now > deadline:
            warnings.append(
                Check(
                    "emergency.approval_late",
                    CheckLevel.WARNING,
                    "Zmiana awaryjna zatwierdzona po upływie 24 h od wdrożenia - odstępstwo.",
                )
            )
    if row.action is A.IMPLEMENT and implemented_outside_window(
        change.change_type, now, change.window_start, change.window_end
    ):
        warnings.append(
            Check(
                "implementation.outside_window",
                CheckLevel.WARNING,
                "Zmianę wdrożono poza zatwierdzonym oknem serwisowym - odstępstwo.",
            )
        )
    if row.action is A.VERIFY and actor.user_id == change.assignee_id:
        warnings.append(
            Check(
                "verifier.is_assignee",
                CheckLevel.WARNING,
                "Zmianę zweryfikował jej wykonawca - w spółce nie ma innej osoby, która "
                "może ją zweryfikować.",
            )
        )

    return TransitionOutcome(
        action=row.action,
        from_status=change.status,
        to_status=target,
        triggered_by=actor.user_id,
        performed_by_system=by_system,
        updates=updates,
        comment=clean_comment,
        warnings=tuple(warnings),
        consented_ci_ids=(
            frozenset(_owned_pending_ci(change, actor, ctx) - ctx.consented_ci_ids)
            if row.action is A.CONSENT
            else frozenset()
        ),
        clear_consents=row.action is A.RETURN,
        snapshot_ci=target is S.IMPLEMENTED and change.status is not S.IMPLEMENTED,
        approval_due_at=approval_due_at,
    )


# --------------------------------------------------------------------------- editing


def _eligible_pending_editor(change: ChangeData, actor: ActorFacts) -> bool:
    """In ``pending_approval`` any company approver who could approve the change (not its
    requester or assignee) may re-assign the approver and move the window (ADR 0012 §6)."""
    return bool(actor.roles & APPROVER_ROLES) and actor.user_id not in {
        change.requested_by_id,
        change.assignee_id,
    }


def verifier_reassignable(change: ChangeData, ctx: ChangeContext) -> bool:
    """An implemented change whose designated verifier can no longer verify (inactive or
    without the editor/approver role) - otherwise it could never be verified."""
    return (
        change.status is S.IMPLEMENTED
        and change.verifier_id is not None
        and not ctx.is_member_with(change.verifier_id, WRITER_ROLES)
    )


def approver_reassignable(change: ChangeData, ctx: ChangeContext) -> bool:
    """An emergency change implemented without approval whose designated approver can no
    longer approve (inactive or without the ``approver`` role) - otherwise it could never
    be approved after the fact (owner decision 2026-10-29). The 24 h deviation stays."""
    return (
        change.status is S.IMPLEMENTED
        and change.change_type is ChangeType.EMERGENCY
        and change.approved_at is None
        and not ctx.is_member_with(change.approver_id, APPROVER_ROLES)
    )


def _reassignable_fields(change: ChangeData, ctx: ChangeContext) -> frozenset[ChangeField]:
    """Fields of an implemented change an approver may re-point now (subset of
    :data:`IMPLEMENTED_EDITABLE`)."""
    fields_: set[ChangeField] = set()
    if verifier_reassignable(change, ctx):
        fields_.add(ChangeField.VERIFIER_ID)
    if approver_reassignable(change, ctx):
        fields_.add(ChangeField.APPROVER_ID)
    return frozenset(fields_)


def editable_fields(
    change: ChangeData, actor: ActorFacts, ctx: ChangeContext
) -> frozenset[ChangeField]:
    """Fields the actor may change now (``editable_fields`` for the form)."""
    if ctx.company.is_archived:
        return frozenset()
    if change.status is S.DRAFT and actor.roles & WRITER_ROLES:
        return DRAFT_EDITABLE
    if change.status is S.PENDING_APPROVAL and _eligible_pending_editor(change, actor):
        return PENDING_APPROVAL_EDITABLE
    if _eligible_pending_editor(change, actor):
        return _reassignable_fields(change, ctx)
    return frozenset()


def changed_fields(current: ChangeData, proposed: ChangeData) -> frozenset[ChangeField]:
    """Editable fields that differ; ``proposed`` must not touch anything else."""
    touched = [
        name
        for name in _NON_EDITABLE_ATTRIBUTES
        if getattr(current, name) != getattr(proposed, name)
    ]
    if touched:
        raise ValueError(f"not editable through PATCH: {sorted(touched)}")
    return frozenset(
        f for f in ChangeField if getattr(current, f.value) != getattr(proposed, f.value)
    )


def check_edit(
    current: ChangeData,
    proposed: ChangeData,
    actor: ActorFacts,
    ctx: ChangeContext,
    *,
    now: datetime,
) -> frozenset[ChangeField]:
    """Validate a ``PATCH`` (``proposed`` = ``current`` with the requested values) and
    return the fields that actually change (empty = nothing to save, no audit entry).

    A draft may be incomplete - completeness is checked by readiness on ``submit``. In
    ``pending_approval`` the new approver and window must satisfy their readiness groups.
    """
    require_aware(now, "now")
    changed = changed_fields(current, proposed)
    if ctx.company.is_archived:
        raise _error(ChangeErrorCode.COMPANY_ARCHIVED)
    reassignable = _reassignable_fields(current, ctx)
    if changed and changed <= reassignable and _eligible_pending_editor(current, actor):
        failed_checks: list[Check] = []
        if ChangeField.VERIFIER_ID in changed:
            failed_checks.extend(c for c in verifier_checks(proposed, ctx) if not c.ok)
        if ChangeField.APPROVER_ID in changed:
            failed_checks.extend(c for c in approver_checks(proposed, ctx) if not c.ok)
        if failed_checks:
            raise _invalid_edit(tuple(failed_checks))
        return changed
    if current.status in FROZEN_STATUSES:
        raise _error(ChangeErrorCode.FROZEN)
    if current.status is S.DRAFT:
        if not actor.roles & WRITER_ROLES:
            raise _error(
                ChangeErrorCode.FORBIDDEN_ACTOR,
                "Szkic zmiany może edytować użytkownik z rolą edytora lub zatwierdzającego.",
            )
        return changed
    if current.status is S.APPROVED:
        raise ChangeRuleError(
            ChangeErrorCode.FIELD_NOT_EDITABLE,
            "Zatwierdzonej zmiany nie można edytować.",
            fields=tuple(sorted(f.value for f in changed)),
        )
    # pending_approval
    if not _eligible_pending_editor(current, actor):
        raise _error(
            ChangeErrorCode.FORBIDDEN_ACTOR,
            "Zmianę oczekującą na zatwierdzenie może edytować tylko zatwierdzający, który "
            "nie jest jej zgłaszającym ani wykonawcą.",
        )
    not_editable = changed - PENDING_APPROVAL_EDITABLE
    if not_editable:
        raise ChangeRuleError(
            ChangeErrorCode.FIELD_NOT_EDITABLE,
            "W statusie „Do zatwierdzenia” można zmienić tylko zatwierdzającego i okno serwisowe.",
            fields=tuple(sorted(f.value for f in not_editable)),
        )
    failed: list[Check] = []
    if ChangeField.APPROVER_ID in changed:
        failed.extend(c for c in approver_checks(proposed, ctx) if not c.ok)
    if changed & _WINDOW_FIELDS:
        failed.extend(c for c in window_checks(proposed, now=now) if not c.ok)
    if failed:
        raise _invalid_edit(tuple(failed))
    return changed


def _invalid_edit(failed: tuple[Check, ...]) -> ChangeRuleError:
    return ChangeRuleError(
        ChangeErrorCode.INVALID_EDIT,
        "Niespełnione warunki: " + " ".join(c.message_pl for c in failed),
        fields=tuple(dict.fromkeys(c.field for c in failed if c.field)),
        checks=failed,
    )
