"""Audit log API schemas: chain verification and log browsing (CLAUDE.md 6.4, 8)."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import UtcDateTime


class AuditEntryRef(BaseModel):
    """Where an entry was appended (``company_id`` null = global chain)."""

    company_id: UUID | None
    seq: int
    hash: str


class VerifyOut(BaseModel):
    """``POST /audit/verify``: ``{ok, checked, first_broken_seq}`` + the verified head.

    ``audit_entry``: the entry recording this verification (normally in the verified chain;
    in the global chain when a broken company chain refused it — ``recorded_in``).
    ``null`` only when no chain accepted it (the server logged an error).
    """

    company_id: UUID | None
    chain: Literal["company", "global"]
    ok: bool
    checked: int
    first_broken_seq: int | None
    head_seq: int
    head_hash: str
    verified_at: UtcDateTime | None
    recorded_in: Literal["chain", "global"] | None
    audit_entry: AuditEntryRef | None


class ChainStatusOut(BaseModel):
    """``GET /companies/{id}/audit/status`` (ADR 0013 §11). ``ok``: true / false, ``null``
    when there is no fresh verification (``stale`` / ``unknown``)."""

    status: Literal["ok", "stale", "broken", "unknown"]
    ok: bool | None
    checked_at: UtcDateTime | None
    verified_head_seq: int | None
    head_seq: int


class AuditEntryOut(BaseModel):
    """One ``audit_log`` row exactly as stored and hashed (CLAUDE.md 6.1)."""

    id: int
    company_id: UUID | None
    seq: int
    occurred_at: UtcDateTime
    actor_id: UUID | None
    actor_display: str
    actor_roles: list[str]
    ip_address: str | None
    user_agent: str | None
    request_id: UUID
    entity_type: str
    entity_id: UUID | None
    action: str
    diff: dict[str, Any]
    context: dict[str, Any]
    prev_hash: str
    hash: str
