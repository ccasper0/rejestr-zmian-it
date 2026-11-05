"""Shared API types: safe text, UTC timestamps with ``Z``, pagination."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, PlainSerializer
from pydantic_core import PydanticCustomError

from app.domain.canonical import format_datetime

CONTROL_CHARACTERS_MESSAGE = "Tekst zawiera niedozwolone znaki sterujące."

# C0 controls except TAB, LF, CR; DEL; C1 controls. NUL in particular cannot be stored in
# PostgreSQL text (asyncpg raises CharacterNotInRepertoireError -> it would be a 500).
_MULTI_LINE_FORBIDDEN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
# Single-line fields additionally reject line breaks (TAB stays allowed).
_SINGLE_LINE_FORBIDDEN = re.compile(r"[\x00-\x08\x0a-\x1f\x7f-\x9f]")


def _reject(pattern: re.Pattern[str]) -> AfterValidator:
    def check(value: str) -> str:
        if pattern.search(value):
            raise PydanticCustomError("string_control_characters", CONTROL_CHARACTERS_MESSAGE)
        return value

    return AfterValidator(check)


SafeStr = Annotated[str, _reject(_MULTI_LINE_FORBIDDEN)]
"""Multi-line text (descriptions, plans, comments): TAB, LF and CR allowed."""

SafeLine = Annotated[str, _reject(_SINGLE_LINE_FORBIDDEN)]
"""Single-line text (names, identifiers, search queries): no line breaks either."""


def _utc(value: datetime) -> str:
    return format_datetime(value if value.tzinfo else value.replace(tzinfo=UTC))


UtcDateTime = Annotated[datetime, PlainSerializer(_utc, return_type=str, when_used="json")]
"""ISO 8601 in UTC with ``Z`` (CLAUDE.md 8), e.g. ``2026-10-28T12:00:00.000000Z``."""

DEFAULT_LIMIT = 100
MAX_LIMIT = 500


class Page[T](BaseModel):
    items: list[T]
    total: int
    limit: int
    offset: int
