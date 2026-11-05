"""Deviations from the change process (CLAUDE.md §4.2, §9 report section 5, ADR 0012 §7).

Pure functions over a change's stored fields and ``now``; used by the register tiles,
the PDF report (Stage 7) and the audit context of a late after-the-fact approval.
:class:`DeviationSubject` and :class:`WindowedDeviationSubject` are read-only protocols,
so an ORM row or ``app.domain.changes.ChangeData`` can be passed directly.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Protocol
from uuid import UUID

from app.domain.changes import ChangeStatus, ChangeType, require_aware

EMERGENCY_APPROVAL_WINDOW = timedelta(hours=24)
"""§4.2: an emergency change must be approved within 24 h of its implementation."""


class DeviationSubject(Protocol):
    @property
    def status(self) -> ChangeStatus: ...
    @property
    def change_type(self) -> ChangeType | None: ...
    @property
    def requested_by_id(self) -> UUID: ...
    @property
    def assignee_id(self) -> UUID | None: ...
    @property
    def approver_id(self) -> UUID | None: ...
    @property
    def implemented_at(self) -> datetime | None: ...
    @property
    def approved_at(self) -> datetime | None: ...
    @property
    def approved_by_id(self) -> UUID | None: ...


class WindowedDeviationSubject(DeviationSubject, Protocol):
    """:class:`DeviationSubject` plus the service window - needed by :func:`deviations`
    for ``implemented_outside_window`` (added 2026-10-29)."""

    @property
    def window_start(self) -> datetime | None: ...
    @property
    def window_end(self) -> datetime | None: ...


class DeviationKind(StrEnum):
    EMERGENCY_NOT_APPROVED_IN_24H = "emergency_not_approved_in_24h"
    IMPLEMENTED_OUTSIDE_WINDOW = "implemented_outside_window"
    IMPLEMENTED_NOT_VERIFIED = "implemented_not_verified"
    ROLLED_BACK = "rolled_back"
    APPROVED_BY_REQUESTER_OR_ASSIGNEE = "approved_by_requester_or_assignee"


_MESSAGES_PL: dict[DeviationKind, str] = {
    DeviationKind.EMERGENCY_NOT_APPROVED_IN_24H: (
        "Zmiana awaryjna nie została zatwierdzona w ciągu 24 h od wdrożenia."
    ),
    DeviationKind.IMPLEMENTED_OUTSIDE_WINDOW: (
        "Zmiana wdrożona poza zatwierdzonym oknem serwisowym."
    ),
    DeviationKind.IMPLEMENTED_NOT_VERIFIED: "Zmiana wdrożona bez weryfikacji.",
    DeviationKind.ROLLED_BACK: "Zmiana została wycofana.",
    DeviationKind.APPROVED_BY_REQUESTER_OR_ASSIGNEE: (
        "Zmiana zatwierdzona przez zgłaszającego lub wykonawcę - naruszenie zasady "
        "czterech oczu (błąd krytyczny)."
    ),
}


@dataclass(frozen=True, slots=True)
class Deviation:
    kind: DeviationKind
    critical: bool
    message_pl: str


def emergency_approval_deadline(implemented_at: datetime) -> datetime:
    return require_aware(implemented_at, "implemented_at") + EMERGENCY_APPROVAL_WINDOW


def emergency_approval_overdue(change: DeviationSubject, *, now: datetime) -> bool:
    """An implemented emergency change without approval within 24 h.

    Approval exactly at ``implemented_at + 24 h`` is in time. Without approval the
    change becomes a deviation only after the deadline (``now > deadline``); a late
    approval does not remove the deviation (``approved_at > deadline``).
    """
    require_aware(now, "now")
    if change.change_type is not ChangeType.EMERGENCY or change.implemented_at is None:
        return False
    deadline = emergency_approval_deadline(change.implemented_at)
    if change.approved_at is None:
        return now > deadline
    return require_aware(change.approved_at, "approved_at") > deadline


def implemented_outside_window(
    change_type: ChangeType | None,
    implemented_at: datetime | None,
    window_start: datetime | None,
    window_end: datetime | None,
) -> bool:
    """A non-emergency change implemented before ``window_start`` or after ``window_end``
    (both bounds inclusive = inside). Emergency changes and changes without a complete
    window are never outside (owner decision 2026-10-29). Also used by ``implement`` for
    the audit warning, so the rule exists once."""
    if (
        change_type is ChangeType.EMERGENCY
        or implemented_at is None
        or window_start is None
        or window_end is None
    ):
        return False
    return not window_start <= implemented_at <= window_end


def implemented_without_verification(change: DeviationSubject) -> bool:
    return change.status is ChangeStatus.IMPLEMENTED


def approved_by_requester_or_assignee(change: DeviationSubject) -> bool:
    """Should never happen (four eyes are enforced on approval and by a database CHECK).
    Judged by who ACTUALLY approved (``approved_by_id``); a standard change approved by
    ``system`` (``approved_by_id`` is ``None``) was approved by nobody of the two
    (ADR 0012 §4)."""
    return (
        change.approved_at is not None
        and change.approved_by_id is not None
        and change.approved_by_id in {change.requested_by_id, change.assignee_id}
    )


def deviations(change: WindowedDeviationSubject, *, now: datetime) -> tuple[Deviation, ...]:
    found: list[DeviationKind] = []
    if emergency_approval_overdue(change, now=now):
        found.append(DeviationKind.EMERGENCY_NOT_APPROVED_IN_24H)
    if implemented_outside_window(
        change.change_type, change.implemented_at, change.window_start, change.window_end
    ):
        found.append(DeviationKind.IMPLEMENTED_OUTSIDE_WINDOW)
    if implemented_without_verification(change):
        found.append(DeviationKind.IMPLEMENTED_NOT_VERIFIED)
    if change.status is ChangeStatus.ROLLED_BACK:
        found.append(DeviationKind.ROLLED_BACK)
    if approved_by_requester_or_assignee(change):
        found.append(DeviationKind.APPROVED_BY_REQUESTER_OR_ASSIGNEE)
    return tuple(
        Deviation(
            kind,
            kind is DeviationKind.APPROVED_BY_REQUESTER_OR_ASSIGNEE,
            _MESSAGES_PL[kind],
        )
        for kind in found
    )
