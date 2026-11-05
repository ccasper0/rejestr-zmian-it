"""Change numbers ``CHG-{PREFIX}-{YYYY}-{NNNN}`` (CLAUDE.md 4.1; ADR 0013 §2).

One counter per company and year in ``number_sequences``, advanced in the business
transaction that creates the change: the row is created if missing (``INSERT ... ON
CONFLICT DO NOTHING``), locked with ``SELECT ... FOR UPDATE`` and incremented. Concurrent
creators of one company wait for each other until COMMIT, so numbers are unique and
consecutive; a rolled back creation rolls its number back too (no gaps from failures).

The year is the calendar year in ``Europe/Warsaw`` (the time zone of the users, CLAUDE.md
§11.6), computed by PostgreSQL, so a change created on 1 January 00:30 local time gets
the new year although it is still 31 December in UTC.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, text, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import NumberSequence

NUMBER_TIME_ZONE = "Europe/Warsaw"
NUMBER_DIGITS = 4


def format_number(prefix: str, year: int, value: int) -> str:
    """``CHG-ALFA-2026-0142``; past 9999 the counter simply gets a fifth digit."""
    return f"CHG-{prefix}-{year:04d}-{value:0{NUMBER_DIGITS}d}"


async def numbering_year(session: AsyncSession, at: datetime) -> int:
    """Calendar year of ``at`` in Europe/Warsaw (PostgreSQL time zone database)."""
    year = (
        await session.execute(
            text(
                "SELECT CAST(extract(year FROM CAST(:at AS timestamptz) AT TIME ZONE :tz) AS int)"
            ),
            {"at": at, "tz": NUMBER_TIME_ZONE},
        )
    ).scalar_one()
    return int(year)


async def next_value(session: AsyncSession, company_id: UUID, year: int) -> int:
    """Advance and return the counter of (company, year); locked until the transaction ends."""
    await session.execute(
        pg_insert(NumberSequence)
        .values(company_id=company_id, year=year, last_value=0)
        .on_conflict_do_nothing(index_elements=["company_id", "year"])
    )
    row = (
        await session.execute(
            select(NumberSequence.id, NumberSequence.last_value)
            .where(NumberSequence.company_id == company_id, NumberSequence.year == year)
            .with_for_update()
        )
    ).one()
    value = int(row.last_value) + 1
    await session.execute(
        update(NumberSequence)
        .where(NumberSequence.id == row.id)
        .values(last_value=value)
        .execution_options(synchronize_session=False)
    )
    return value


async def next_number(session: AsyncSession, *, company_id: UUID, prefix: str, at: datetime) -> str:
    year = await numbering_year(session, at)
    return format_number(prefix, year, await next_value(session, company_id, year))
