"""Audit log tables (CLAUDE.md 6.1, 6.2; ADR 0006).

The ORM definitions mirror migration ``0001`` (used by Alembic autogenerate comparison).
Triggers, RLS policies and grants exist only in the migration.

No foreign keys on ``company_id`` / ``actor_id`` on purpose (ADR 0006): the log is
self-contained evidence (``actor_display`` is frozen), global events have no company,
failed logins may name users that do not exist, and an FK would take a KEY SHARE lock
on the referenced row for every audit insert.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from ipaddress import IPv4Address, IPv6Address
from typing import Any

from sqlalchemy import (
    CHAR,
    BigInteger,
    CheckConstraint,
    DateTime,
    Index,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, INET, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

HEX64 = "^[0-9a-f]{64}$"


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        # PostgreSQL treats NULLs as distinct in UNIQUE by default; the global chain
        # (company_id IS NULL) needs NULLS NOT DISTINCT, otherwise seq could repeat.
        UniqueConstraint("company_id", "seq", postgresql_nulls_not_distinct=True),
        CheckConstraint("seq >= 1", name="seq_positive"),
        CheckConstraint(f"hash ~ '{HEX64}'", name="hash_hex"),
        CheckConstraint(f"prev_hash ~ '{HEX64}'", name="prev_hash_hex"),
        CheckConstraint("jsonb_typeof(diff) = 'object'", name="diff_object"),
        CheckConstraint("jsonb_typeof(context) = 'object'", name="context_object"),
        Index("ix_audit_log_entity", "entity_type", "entity_id"),
        Index("ix_audit_log_occurred_at", "occurred_at"),
        # Never add an implicit "RETURNING id": RETURNING needs SELECT visibility of the
        # new row, which RLS denies for global entries written by ordinary users.
        {"implicit_returning": False},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    company_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    seq: Mapped[int] = mapped_column(BigInteger)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    actor_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    actor_display: Mapped[str] = mapped_column(Text)
    actor_roles: Mapped[list[str]] = mapped_column(ARRAY(Text))
    ip_address: Mapped[IPv4Address | IPv6Address | None] = mapped_column(INET)
    user_agent: Mapped[str | None] = mapped_column(Text)
    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    entity_type: Mapped[str] = mapped_column(Text)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    action: Mapped[str] = mapped_column(Text)
    diff: Mapped[dict[str, Any]] = mapped_column(JSONB)
    context: Mapped[dict[str, Any]] = mapped_column(JSONB)
    prev_hash: Mapped[str] = mapped_column(CHAR(64))
    hash: Mapped[str] = mapped_column(CHAR(64))


class AuditChainHead(Base):
    """Head of one chain: one row per company + one global row (company_id IS NULL)."""

    __tablename__ = "audit_chain_heads"
    __table_args__ = (
        UniqueConstraint("company_id", postgresql_nulls_not_distinct=True),
        CheckConstraint("last_seq >= 0", name="last_seq_non_negative"),
        CheckConstraint(f"last_hash ~ '{HEX64}'", name="last_hash_hex"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    company_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    last_seq: Mapped[int] = mapped_column(BigInteger)
    last_hash: Mapped[str] = mapped_column(CHAR(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
