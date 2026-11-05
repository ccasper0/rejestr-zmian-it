"""Reports (CLAUDE.md §9, ADR 0017): kinds, numbering format, register tiles. No I/O.

The deviations themselves are decided by :mod:`app.domain.deviations` (one rule each);
this module only orders and counts them for the register report.
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from app.domain.changes import ChangeStatus, ChangeType
from app.domain.deviations import DeviationKind

REPORT_DATA_FORMAT = 2
"""Version of the report data structure hashed into ``data_sha256`` (ADR 0017 §4).
2: appendix B trails carry ``truncated`` / ``omitted`` (ADR 0017 §14)."""

NUMBER_DIGITS = 4
REPORT_NUMBER_PATTERN = re.compile(r"^RAP-(?:[A-Z]{2,8}-)?[0-9]{4}-[0-9]{4,}$")


class ReportKind(StrEnum):
    REGISTER = "register"
    CHANGE_CARD = "change_card"


class ReportFormat(StrEnum):
    PDF = "pdf"
    CSV = "csv"


class ReportStatus(StrEnum):
    PENDING = "pending"
    DONE = "done"
    FAILED = "failed"


class ExportEvent(StrEnum):
    """``context.event`` of the ``report`` / ``export`` audit entries (ADR 0017 §6)."""

    REQUESTED = "requested"  # a background report was ordered (pending)
    GENERATED = "generated"  # the file was generated (carries data_sha256)
    FAILED = "failed"  # a background generation failed
    DOWNLOADED = "downloaded"  # the stored file was downloaded
    # A download refused: the stored file is missing or no longer has its sha256.
    INTEGRITY_FAILED = "integrity_failed"


def format_report_number(prefix: str | None, year: int, value: int) -> str:
    """``RAP-ALFA-2026-0007`` for a company, ``RAP-2026-0007`` for a multi-company report.

    The multi-company form has no prefix segment, so it can never collide with a company
    report whatever prefixes the companies have (ADR 0017 §2). Past 9999 the counter
    simply gets a fifth digit (like change numbers).
    """
    if value < 1:
        raise ValueError("report numbers start at 1")
    middle = f"{prefix}-" if prefix is not None else ""
    return f"RAP-{middle}{year:04d}-{value:0{NUMBER_DIGITS}d}"


# Order of the deviation sections of the register report (§9 point 5, ADR 0012 §7).
DEVIATION_SECTIONS: tuple[DeviationKind, ...] = (
    DeviationKind.EMERGENCY_NOT_APPROVED_IN_24H,
    DeviationKind.IMPLEMENTED_NOT_VERIFIED,
    DeviationKind.IMPLEMENTED_OUTSIDE_WINDOW,
    DeviationKind.ROLLED_BACK,
    DeviationKind.APPROVED_BY_REQUESTER_OR_ASSIGNEE,
)


class TileSubject(Protocol):
    @property
    def status(self) -> ChangeStatus: ...
    @property
    def change_type(self) -> ChangeType | None: ...
    @property
    def approved_at(self) -> datetime | None: ...
    @property
    def implemented_at(self) -> datetime | None: ...


def approved_before_implementation(change: TileSubject) -> bool:
    """An implemented change whose approval (by a person or ``system``) came no later
    than its implementation - i.e. not an emergency implemented first."""
    return (
        change.implemented_at is not None
        and change.approved_at is not None
        and change.approved_at <= change.implemented_at
    )


@dataclass(frozen=True, slots=True)
class RegisterTiles:
    """Tiles of the register report (§9 point 2)."""

    total: int
    implemented: int  # changes with an implementation date (base of the next tile)
    approved_before_implementation: int
    emergency: int
    not_verified: int  # implemented, not verified (status ``implemented``)


def register_tiles(changes: Iterable[TileSubject]) -> RegisterTiles:
    total = implemented = approved_first = emergency = not_verified = 0
    for change in changes:
        total += 1
        if change.implemented_at is not None:
            implemented += 1
        if approved_before_implementation(change):
            approved_first += 1
        if change.change_type is ChangeType.EMERGENCY:
            emergency += 1
        if change.status is ChangeStatus.IMPLEMENTED:
            not_verified += 1
    return RegisterTiles(total, implemented, approved_first, emergency, not_verified)


def count_by(keys: Iterable[str]) -> list[tuple[str, int]]:
    """``[(key, count)]`` sorted by count (descending), then key - Załącznik A."""
    counts = Counter(keys)
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))
