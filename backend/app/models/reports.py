"""Report exports and their numbering (CLAUDE.md 4.1, 9; ADR 0017).

Mirrors migration ``0009``. The guard triggers (a row is completed once, counters advance
by one), grants and the RLS policies exist only in the migration.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    CHAR,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    false,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import TimestampMixin, UuidPkMixin


class ReportNumberSequence(UuidPkMixin, TimestampMixin, Base):
    """Per company (``NULL`` = multi-company reports) and year counter of report numbers."""

    __tablename__ = "report_number_sequences"
    __table_args__ = (
        # NULLS NOT DISTINCT: one counter per year for the multi-company reports.
        UniqueConstraint("company_id", "year", postgresql_nulls_not_distinct=True),
    )

    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id")
    )
    year: Mapped[int] = mapped_column(Integer)
    last_value: Mapped[int] = mapped_column(Integer, server_default=text("0"))


class ReportExport(UuidPkMixin, TimestampMixin, Base):
    """One export: a PDF register report, a PDF change card or a CSV register export."""

    __tablename__ = "report_exports"
    __table_args__ = (
        UniqueConstraint("number"),
        UniqueConstraint("storage_key"),
        ForeignKeyConstraint(
            ["change_id", "company_id"],
            ["changes.id", "changes.company_id"],
            name="fk_report_exports_change_id_changes",
        ),
        Index("ix_report_exports_company_id_created_at", "company_id", "created_at"),
        Index("ix_report_exports_generated_by_id_created_at", "generated_by_id", "created_at"),
    )

    # NULL = the multi-company report of an auditor (ADR 0017 §2).
    company_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id")
    )
    number: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(Text)  # register | change_card
    format: Mapped[str] = mapped_column(Text)  # pdf | csv
    change_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    # The companies whose data the report contains ({company_id} for a company report).
    scope_company_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(UUID(as_uuid=True)))
    period_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    period_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    filters: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default=text("'{}'::jsonb"))
    include_audit_trail: Mapped[bool] = mapped_column(Boolean, server_default=false())
    generated_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(Text, server_default="pending")
    data_sha256: Mapped[str | None] = mapped_column(CHAR(64))
    file_sha256: Mapped[str | None] = mapped_column(CHAR(64))
    size: Mapped[int | None] = mapped_column(BigInteger)
    storage_key: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
    change_count: Mapped[int | None] = mapped_column(Integer)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
