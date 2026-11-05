"""Global dictionaries (change categories, CI types) and the company CI inventory.

CLAUDE.md 4.1; decisions in docs/decisions/0011-dictionaries-and-ci-inventory.md.
Mirrors migration ``0006``. Triggers (two-level categories, immutable codes and company),
grants and Row-Level Security policies exist only in the migration.
"""

from __future__ import annotations

import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
    false,
    func,
    text,
)
from sqlalchemy import true as sql_true
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import TimestampMixin, UuidPkMixin

CATEGORY_CODE_CHECK = "code ~ '^[A-Z][A-Z0-9]*(-[A-Z0-9]+)*$' AND length(code) BETWEEN 2 AND 32"
CI_TYPE_CODE_CHECK = "code ~ '^[a-z][a-z0-9_]{1,31}$'"
RISK_CHECK = "default_risk IN ('low', 'medium', 'high')"


class ChangeCategory(UuidPkMixin, TimestampMixin, Base):
    """Global dictionary, two levels: ``parent_id IS NULL`` = category, else subcategory."""

    __tablename__ = "change_categories"
    __table_args__ = (
        UniqueConstraint("code"),
        CheckConstraint(CATEGORY_CODE_CHECK, name="code_format"),
        CheckConstraint(RISK_CHECK, name="default_risk_values"),
        CheckConstraint("parent_id IS NULL OR parent_id <> id", name="parent_not_self"),
        Index("ix_change_categories_parent_id", "parent_id"),
    )

    code: Mapped[str] = mapped_column(Text)  # immutable (trigger)
    name: Mapped[str] = mapped_column(Text)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(  # immutable (trigger)
        UUID(as_uuid=True), ForeignKey("change_categories.id")
    )
    requires_approval: Mapped[bool] = mapped_column(Boolean)
    # CI owner consent before approval (e.g. OT; ADR 0012 §5, migration 0008).
    requires_ci_owner_consent: Mapped[bool] = mapped_column(Boolean, server_default=false())
    default_risk: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=sql_true())


class CiType(UuidPkMixin, TimestampMixin, Base):
    __tablename__ = "ci_types"
    __table_args__ = (
        UniqueConstraint("code"),
        CheckConstraint(CI_TYPE_CODE_CHECK, name="code_format"),
    )

    code: Mapped[str] = mapped_column(Text)  # immutable (trigger)
    name: Mapped[str] = mapped_column(Text)  # Polish display name
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=sql_true())


class CompanyCategory(UuidPkMixin, TimestampMixin, Base):
    """A (top-level) category available in a company, with an optional approver override."""

    __tablename__ = "company_categories"
    __table_args__ = (UniqueConstraint("company_id", "category_id"),)

    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"))
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("change_categories.id")
    )
    approver_override_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )


class ConfigurationItem(UuidPkMixin, TimestampMixin, Base):
    """A configuration item (CI) of a company. Never deleted - deactivated."""

    __tablename__ = "configuration_items"
    __table_args__ = (
        # Unique in the company regardless of letter case ("FW-01" = "fw-01"), like
        # company names (migration 0004).
        Index(
            "uq_configuration_items_company_id_identifier_lower",
            "company_id",
            func.lower(text("identifier")),
            unique=True,
        ),
        Index("ix_configuration_items_ci_type_id", "ci_type_id"),
        # Target of the composite foreign keys of the change tables (migration 0008).
        UniqueConstraint("id", "company_id"),
    )

    company_id: Mapped[uuid.UUID] = mapped_column(  # immutable (trigger)
        UUID(as_uuid=True), ForeignKey("companies.id")
    )
    ci_type_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ci_types.id"))
    identifier: Mapped[str] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=sql_true())
