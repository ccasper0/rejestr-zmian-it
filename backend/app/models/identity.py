"""Users, companies and company memberships (CLAUDE.md 4.1, 5).

Mirrors migrations ``0002`` and ``0004``. The prefix-immutability trigger, grants and the
RLS policies (migration ``0003``, ADR 0008) exist only in the migrations.
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

PREFIX_PATTERN = "^[A-Z]{2,8}$"
COMPANY_STATUSES = ("active", "archived")
MEMBERSHIP_ROLES = ("editor", "approver", "auditor", "viewer")


def _in_list(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


class User(UuidPkMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("external_id"),
        # The login of a local account: unique regardless of case (migration 0010).
        Index("uq_users_email_lower", func.lower(text("email")), unique=True),
    )

    # Stable subject of the access tokens: "local:<uuid>" for local accounts, the seed
    # identifier ("dev-admin", ...) for dev users (ADR 0018).
    external_id: Mapped[str] = mapped_column(Text)
    email: Mapped[str] = mapped_column(Text)
    display_name: Mapped[str] = mapped_column(Text)
    is_app_admin: Mapped[bool] = mapped_column(Boolean, server_default=false())
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=sql_true())


class Company(UuidPkMixin, TimestampMixin, Base):
    __tablename__ = "companies"
    __table_args__ = (
        # Case-insensitive: "Alfa" and "ALFA" are the same company (migration 0004).
        Index("uq_companies_name_lower", func.lower(text("name")), unique=True),
        UniqueConstraint("prefix"),
        CheckConstraint(f"prefix ~ '{PREFIX_PATTERN}'", name="prefix_format"),
        CheckConstraint(_in_list("status", COMPANY_STATUSES), name="status_values"),
    )

    name: Mapped[str] = mapped_column(Text)
    tax_id: Mapped[str | None] = mapped_column(Text)
    prefix: Mapped[str] = mapped_column(Text)  # immutable (trigger in migration 0002)
    status: Mapped[str] = mapped_column(Text, server_default="active")
    is_ksc_entity: Mapped[bool] = mapped_column(Boolean, server_default=false())
    default_approver_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )


class CompanyMembership(UuidPkMixin, TimestampMixin, Base):
    __tablename__ = "company_memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "company_id", "role"),
        CheckConstraint(_in_list("role", MEMBERSHIP_ROLES), name="role_values"),
        Index("ix_company_memberships_company_id", "company_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    company_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"))
    role: Mapped[str] = mapped_column(Text)
