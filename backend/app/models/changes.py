"""Changes and their child rows (CLAUDE.md 4.1; ADR 0012, ADR 0013).

Mirrors migration ``0008``. Triggers (status only through the action path, freezing,
append-only comments / attachments / consents, numbering steps), grants and the RLS
policies exist only in the migration.

Every child table carries ``company_id`` with a composite foreign key
``(change_id, company_id)`` to ``changes``, so RLS is a direct policy everywhere and a
child row can never belong to another company than its change.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    CHAR,
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.naming import conv

from app.models.base import Base
from app.models.mixins import TimestampMixin, UuidPkMixin

HEX64 = "^[0-9a-f]{64}$"


def _change_fk() -> ForeignKeyConstraint:
    return ForeignKeyConstraint(["change_id", "company_id"], ["changes.id", "changes.company_id"])


def _ci_fk() -> ForeignKeyConstraint:
    return ForeignKeyConstraint(
        ["ci_id", "company_id"], ["configuration_items.id", "configuration_items.company_id"]
    )


class NumberSequence(UuidPkMixin, TimestampMixin, Base):
    """Per company and year counter of ``CHG-{PREFIX}-{YYYY}-{NNNN}`` (ADR 0013 §2)."""

    __tablename__ = "number_sequences"
    __table_args__ = (
        UniqueConstraint("company_id", "year"),
        CheckConstraint("last_value >= 0", name="last_value_non_negative"),
        CheckConstraint("year BETWEEN 2000 AND 9999", name="year_range"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"))
    year: Mapped[int] = mapped_column(Integer)
    last_value: Mapped[int] = mapped_column(Integer, server_default=text("0"))


class Change(UuidPkMixin, TimestampMixin, Base):
    __tablename__ = "changes"
    __table_args__ = (
        UniqueConstraint("number"),
        UniqueConstraint("id", "company_id"),
        ForeignKeyConstraint(
            ["supersedes_change_id", "company_id"], ["changes.id", "changes.company_id"]
        ),
        Index("ix_changes_company_id_status", "company_id", "status"),
        Index("ix_changes_company_id_created_at", "company_id", "created_at"),
        Index("ix_changes_company_id_implemented_at", "company_id", "implemented_at"),
        Index("ix_changes_company_id_change_type", "company_id", "change_type"),
        Index("ix_changes_category_id", "category_id"),
        Index("ix_changes_subcategory_id", "subcategory_id"),
        Index("ix_changes_assignee_id", "assignee_id"),
        Index("ix_changes_approver_id", "approver_id"),
        Index("ix_changes_supersedes_change_id", "supersedes_change_id"),
        # Mirrors the CHECKs of migration 0008 (documentation; Alembic does not compare them).
        CheckConstraint(
            "window_start IS NULL OR window_end IS NULL OR window_start < window_end",
            name="window_order",
        ),
        CheckConstraint("version >= 1", name="version_positive"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(  # immutable (trigger)
        UUID(as_uuid=True), ForeignKey("companies.id")
    )
    number: Mapped[str] = mapped_column(Text)  # immutable (trigger)
    title: Mapped[str | None] = mapped_column(Text)
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("change_categories.id")
    )
    subcategory_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("change_categories.id")
    )
    change_type: Mapped[str | None] = mapped_column(Text)
    risk: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, server_default="draft")
    description: Mapped[str | None] = mapped_column(Text)
    implementation_plan: Mapped[str | None] = mapped_column(Text)
    rollback_plan: Mapped[str | None] = mapped_column(Text)
    impact: Mapped[str | None] = mapped_column(Text)
    requirement_ref: Mapped[str | None] = mapped_column(Text)
    ticket_ref: Mapped[str | None] = mapped_column(Text)
    requested_by_id: Mapped[uuid.UUID] = mapped_column(  # immutable (trigger)
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    approver_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    verifier_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    window_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    implemented_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Who actually approved (only the ``approve`` action sets it); NULL with ``approved_at``
    # = approved by ``system`` (standard auto-approval, ADR 0012 §4).
    approved_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    supersedes_change_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    # Approval round of the CI owner consents; ``return`` starts a new one (ADR 0013 §5).
    consent_round: Mapped[int] = mapped_column(Integer, server_default=text("1"))
    version: Mapped[int] = mapped_column(Integer, server_default=text("1"))


class ChangeItem(UuidPkMixin, TimestampMixin, Base):
    """A CI of a change; ``ci_identifier`` / ``ci_name``: snapshot at implementation."""

    __tablename__ = "change_items"
    __table_args__ = (
        UniqueConstraint("change_id", "ci_id"),
        _change_fk(),
        _ci_fk(),
        Index("ix_change_items_ci_id", "ci_id"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    change_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    ci_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    ci_identifier: Mapped[str | None] = mapped_column(Text)
    ci_name: Mapped[str | None] = mapped_column(Text)


class ChangeCiConsent(UuidPkMixin, TimestampMixin, Base):
    """Consent of a CI owner (append-only); ``created_at`` is the time of the consent."""

    __tablename__ = "change_ci_consents"
    __table_args__ = (
        UniqueConstraint(
            "change_id",
            "ci_id",
            "consent_round",
            "owner_user_id",
            name=conv("uq_change_ci_consents_round_owner"),
        ),
        _change_fk(),
        _ci_fk(),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    change_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    ci_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    owner_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    consent_round: Mapped[int] = mapped_column(Integer)


class ChangeComment(UuidPkMixin, TimestampMixin, Base):
    """A comment (append-only). ``action``: the action it was given with, if any."""

    __tablename__ = "change_comments"
    __table_args__ = (
        _change_fk(),
        Index("ix_change_comments_change_id_created_at", "change_id", "created_at"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    change_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    author_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    action: Mapped[str | None] = mapped_column(Text)


class Attachment(UuidPkMixin, TimestampMixin, Base):
    """An uploaded file (append-only; a new version is a new row)."""

    __tablename__ = "attachments"
    __table_args__ = (
        UniqueConstraint("storage_key"),
        _change_fk(),
        Index("ix_attachments_change_id", "change_id"),
        CheckConstraint(f"sha256 ~ '{HEX64}'", name="sha256_hex"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    change_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    filename: Mapped[str] = mapped_column(Text)
    content_type: Mapped[str] = mapped_column(Text)
    size: Mapped[int] = mapped_column(BigInteger)
    sha256: Mapped[str] = mapped_column(CHAR(64))
    storage_key: Mapped[str] = mapped_column(Text)
    uploaded_by_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
