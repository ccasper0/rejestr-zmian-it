"""Deviations from the change process (CLAUDE.md §4.2, §9 section 5, ADR 0012 §7)."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.domain.changes import ChangeData, ChangeStatus, ChangeType
from app.domain.deviations import (
    EMERGENCY_APPROVAL_WINDOW,
    DeviationKind,
    approved_by_requester_or_assignee,
    deviations,
    emergency_approval_deadline,
    emergency_approval_overdue,
    implemented_outside_window,
)
from tests.change_world import APPROVER, ASSIGNEE, AUTHOR, NOW, in_status

S = ChangeStatus
IMPLEMENTED_AT = NOW - timedelta(days=2)
WINDOW_START = NOW - timedelta(days=5)
WINDOW_END = WINDOW_START + timedelta(hours=2)


def _emergency(status: S = S.IMPLEMENTED, **overrides: object) -> ChangeData:
    values: dict[str, object] = {
        "change_type": ChangeType.EMERGENCY,
        "implemented_at": IMPLEMENTED_AT,
        "approved_at": None,
    }
    values.update(overrides)
    return in_status(status, **values)  # type: ignore[arg-type]


def test_window_is_24_hours() -> None:
    assert timedelta(hours=24) == EMERGENCY_APPROVAL_WINDOW
    assert emergency_approval_deadline(IMPLEMENTED_AT) == IMPLEMENTED_AT + timedelta(hours=24)


@pytest.mark.parametrize(
    ("now_after", "overdue"),
    [
        (timedelta(hours=23), False),
        (timedelta(hours=24), False),  # exactly at the deadline: still possible
        (timedelta(hours=24, microseconds=1), True),
    ],
)
def test_unapproved_emergency_becomes_overdue_after_24h(
    now_after: timedelta, overdue: bool
) -> None:
    change = _emergency()
    assert emergency_approval_overdue(change, now=IMPLEMENTED_AT + now_after) is overdue


@pytest.mark.parametrize(
    ("approved_after", "overdue"),
    [
        (timedelta(hours=1), False),
        (timedelta(hours=24), False),
        (timedelta(hours=24, seconds=1), True),  # late approval keeps the deviation
    ],
)
def test_approved_emergency(approved_after: timedelta, overdue: bool) -> None:
    change = _emergency(approved_at=IMPLEMENTED_AT + approved_after)
    assert emergency_approval_overdue(change, now=NOW + timedelta(days=30)) is overdue


def test_not_emergency_or_not_implemented_is_never_overdue() -> None:
    normal = in_status(S.IMPLEMENTED, approved_at=None)
    assert not emergency_approval_overdue(normal, now=NOW + timedelta(days=9))
    draft = in_status(S.DRAFT, change_type=ChangeType.EMERGENCY)
    assert not emergency_approval_overdue(draft, now=NOW + timedelta(days=9))


def test_deviations_of_an_overdue_emergency() -> None:
    found = deviations(_emergency(), now=NOW)
    assert [d.kind for d in found] == [
        DeviationKind.EMERGENCY_NOT_APPROVED_IN_24H,
        DeviationKind.IMPLEMENTED_NOT_VERIFIED,
    ]
    assert not any(d.critical for d in found)
    assert all(d.message_pl for d in found)


@pytest.mark.parametrize(
    ("status", "kinds"),
    [
        (S.DRAFT, []),
        (S.PENDING_APPROVAL, []),
        (S.APPROVED, []),
        (S.IMPLEMENTED, [DeviationKind.IMPLEMENTED_NOT_VERIFIED]),
        (S.VERIFIED, []),
        (S.ROLLED_BACK, [DeviationKind.ROLLED_BACK]),
        (S.REJECTED, []),
        (S.CANCELLED, []),
    ],
)
def test_deviations_by_status(status: S, kinds: list[DeviationKind]) -> None:
    assert [d.kind for d in deviations(in_status(status), now=NOW)] == kinds


@pytest.mark.parametrize("who", [AUTHOR, ASSIGNEE])
def test_approval_by_requester_or_assignee_is_critical(who: object) -> None:
    change = in_status(S.VERIFIED, approver_id=who, approved_by_id=who)
    assert approved_by_requester_or_assignee(change)
    (found,) = deviations(change, now=NOW)
    assert found.kind is DeviationKind.APPROVED_BY_REQUESTER_OR_ASSIGNEE
    assert found.critical


def test_not_approved_is_not_an_author_approval() -> None:
    assert not approved_by_requester_or_assignee(in_status(S.DRAFT, approved_by_id=AUTHOR))
    assert not approved_by_requester_or_assignee(in_status(S.VERIFIED, approved_by_id=None))
    assert not approved_by_requester_or_assignee(in_status(S.VERIFIED, approver_id=APPROVER))
    # Auto-approved by system: the designated approver (even the author) did not approve.
    system = in_status(S.APPROVED, approver_id=AUTHOR, approved_by_id=None)
    assert not approved_by_requester_or_assignee(system)


def test_naive_now_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        deviations(in_status(S.DRAFT), now=datetime(2026, 1, 1))  # noqa: DTZ001


@pytest.mark.parametrize(
    ("implemented_at", "outside"),
    [
        (WINDOW_START - timedelta(microseconds=1), True),
        (WINDOW_START, False),
        (WINDOW_START + timedelta(minutes=30), False),
        (WINDOW_END, False),
        (WINDOW_END + timedelta(seconds=1), True),
    ],
)
def test_implemented_outside_window(implemented_at: datetime, outside: bool) -> None:
    change = in_status(
        S.VERIFIED,
        window_start=WINDOW_START,
        window_end=WINDOW_END,
        implemented_at=implemented_at,
    )
    kinds = [d.kind for d in deviations(change, now=NOW)]
    assert kinds == ([DeviationKind.IMPLEMENTED_OUTSIDE_WINDOW] if outside else [])
    assert (
        implemented_outside_window(
            change.change_type, change.implemented_at, change.window_start, change.window_end
        )
        is outside
    )


def test_outside_window_not_for_emergency_or_without_window() -> None:
    late = WINDOW_END + timedelta(days=1)
    assert not implemented_outside_window(ChangeType.EMERGENCY, late, WINDOW_START, WINDOW_END)
    assert not implemented_outside_window(ChangeType.NORMAL, late, None, WINDOW_END)
    assert not implemented_outside_window(ChangeType.NORMAL, late, WINDOW_START, None)
    assert not implemented_outside_window(ChangeType.NORMAL, None, WINDOW_START, WINDOW_END)
    assert implemented_outside_window(ChangeType.STANDARD, late, WINDOW_START, WINDOW_END)
