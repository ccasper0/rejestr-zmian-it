"""Audit log domain: actor, event vocabulary, payload and hash (CLAUDE.md 6). No I/O.

The hash of an entry is ``sha256(prev_hash + canonical_json(payload))`` where ``payload``
holds every ``audit_log`` column except ``id`` and ``hash`` (CLAUDE.md 6.2). The payload is
built by :func:`build_payload` both when writing (``app.services.audit.record``) and when
verifying (``app.services.audit.verify_chain``) — never construct it elsewhere.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from ipaddress import (
    IPv4Address,
    IPv4Interface,
    IPv6Address,
    IPv6Interface,
    ip_address,
    ip_interface,
)
from uuid import UUID

from app.domain.canonical import JsonValue, canonical_json, sha256_hex, to_json_value

GENESIS_HASH = "0" * 64
"""``prev_hash`` of the first entry of every chain."""

SYSTEM_ACTOR_DISPLAY = "system"
USER_AGENT_MAX_LENGTH = 1024


class EntityType(StrEnum):
    CHANGE = "change"
    CI = "ci"
    CI_TYPE = "ci_type"
    COMPANY = "company"
    MEMBERSHIP = "membership"
    CATEGORY = "category"
    COMPANY_CATEGORY = "company_category"  # categories available in a company (ADR 0011)
    ATTACHMENT = "attachment"
    REPORT = "report"
    USER = "user"
    AUTH = "auth"
    AUDIT = "audit"


class AuditAction(StrEnum):
    CREATE = "create"
    UPDATE = "update"
    TRANSITION = "transition"
    ARCHIVE = "archive"
    DEACTIVATE = "deactivate"
    ATTACH = "attach"
    DOWNLOAD = "download"  # an attachment was downloaded (owner decision 2026-10-29)
    COMMENT = "comment"
    EXPORT = "export"
    LOGIN = "login"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    # Local accounts (ADR 0018). Action names, not secrets (hence the noqa).
    TOKEN_REFRESH = "token_refresh"  # noqa: S105 - a session's tokens were renewed
    SESSION_REVOKE = "session_revoke"  # e.g. refresh-token reuse detected
    LOCKOUT = "lockout"  # the account was locked after failed passwords
    PASSWORD_CHANGE = "password_change"  # noqa: S105 - by the user
    PASSWORD_RESET = "password_reset"  # noqa: S105 - by an app admin (temporary password)
    ROLE_GRANT = "role_grant"
    ROLE_REVOKE = "role_revoke"
    ACCESS_DENIED = "access_denied"
    VERIFY = "verify"


@dataclass(frozen=True, slots=True)
class Actor:
    """Who performed the action. ``id=None`` means the ``system`` actor (CLAUDE.md 6.1).

    ``display`` and ``roles`` are frozen into the entry at the time of the event.
    """

    id: UUID | None
    display: str
    roles: tuple[str, ...] = field(default=())

    def __post_init__(self) -> None:
        if not self.display.strip():
            raise ValueError("actor display name must not be empty")
        if self.id is None and self.display != SYSTEM_ACTOR_DISPLAY:
            raise ValueError("an actor without id must be the 'system' actor")
        roles = tuple(sorted(set(self.roles)))
        if any(not role for role in roles):
            raise ValueError("actor roles must be non-empty strings")
        object.__setattr__(self, "roles", roles)

    @classmethod
    def system(cls) -> Actor:
        return cls(id=None, display=SYSTEM_ACTOR_DISPLAY, roles=())

    @property
    def is_system(self) -> bool:
        return self.id is None


@dataclass(frozen=True, slots=True)
class VerifyResult:
    """Outcome of a chain verification (CLAUDE.md 6.4)."""

    ok: bool
    checked: int
    first_broken_seq: int | None


DiffValue = dict[str, dict[str, JsonValue]]


def make_diff(before: Mapping[str, object], after: Mapping[str, object]) -> DiffValue:
    """``{"field": {"before": ..., "after": ...}}`` for fields whose canonical value differs.

    A field missing on one side is treated as ``None`` (e.g. creation: ``before = {}``).
    """
    result: DiffValue = {}
    for key in sorted(set(before) | set(after)):
        old = to_json_value(before.get(key))
        new = to_json_value(after.get(key))
        if canonical_json(old) != canonical_json(new):
            result[key] = {"before": old, "after": new}
    return result


def normalize_diff(diff: Mapping[str, object]) -> DiffValue:
    """Validate the diff shape and normalize its values to canonical JSON types."""
    normalized = to_json_value(diff)
    if not isinstance(normalized, dict):  # pragma: no cover - Mapping always yields dict
        raise TypeError("diff must be a mapping")
    result: DiffValue = {}
    for key, item in normalized.items():
        if not isinstance(item, dict) or set(item) != {"before", "after"}:
            raise ValueError(
                f"diff[{key!r}] must be a mapping with exactly the keys 'before' and 'after'"
            )
        result[key] = item
    return result


# Keys that must never appear in an audit entry (diff or context, at any depth): secrets
# and their hashes (ADR 0018 §7). A defensive check - services never pass them.
SECRET_KEYS = frozenset(
    {
        "password",
        "password_hash",
        "new_password",
        "current_password",
        "temporary_password",
        "access_token",
        "refresh_token",
        "token_hash",
        "secret",
    }
)


def find_secret_keys(value: object, path: str = "") -> list[str]:
    """Paths of keys named like a secret (:data:`SECRET_KEYS`) anywhere in ``value``."""
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            here = f"{path}.{key}" if path else str(key)
            if str(key).lower() in SECRET_KEYS:
                found.append(here)
            found.extend(find_secret_keys(item, here))
    elif isinstance(value, list | tuple):
        for index, item in enumerate(value):
            found.extend(find_secret_keys(item, f"{path}[{index}]"))
    return found


def normalize_context(context: Mapping[str, object]) -> dict[str, JsonValue]:
    normalized = to_json_value(context)
    if not isinstance(normalized, dict):  # pragma: no cover - Mapping always yields dict
        raise TypeError("context must be a mapping")
    return normalized


_IPV4_MAPPED_PREFIX = 0xFFFF << 32  # ::ffff:0:0/96 (RFC 4291 §2.5.5.2)
_IPV4_MAPPED_MASK = ((1 << 128) - 1) ^ ((1 << 32) - 1)


def _format_ipv4(value: int) -> str:
    return ".".join(str((value >> shift) & 0xFF) for shift in (24, 16, 8, 0))


def _format_ipv6(value: int) -> str:
    """RFC 5952 §4 text form, implemented here (NOT ``str(IPv6Address)``).

    - hexadecimal groups in lower case without leading zeros (§4.1, §4.3);
    - ``::`` replaces the LONGEST run of two or more all-zero groups; on a tie the FIRST
      run (§4.2.1-4.2.3); a single zero group is never shortened (§4.2.2);
    - no mixed IPv4 notation (§5 is a recommendation only): IPv4-mapped addresses never
      get here (:func:`format_ip` turns them into IPv4), IPv4-compatible (``::a.b.c.d``,
      deprecated) and other embeddings are written as plain hexadecimal groups.
    """
    groups = [(value >> (16 * (7 - i))) & 0xFFFF for i in range(8)]
    best_start, best_len = -1, 0
    run_start, run_len = -1, 0
    for i, group in enumerate(groups):
        if group == 0:
            if run_len == 0:
                run_start = i
            run_len += 1
            if run_len > best_len:
                best_start, best_len = run_start, run_len
        else:
            run_len = 0
    hextets = [format(group, "x") for group in groups]
    if best_len < 2:
        return ":".join(hextets)
    head = ":".join(hextets[:best_start])
    tail = ":".join(hextets[best_start + best_len :])
    return f"{head}::{tail}"


def format_ip(address: IPv4Address | IPv6Address) -> str:
    """FROZEN canonical text of a host address (hashed in ``ip_address``, ADR 0006 §3).

    Deliberately independent of ``str(ipaddress.*)``, whose output for IPv4-mapped IPv6
    addresses changed between CPython releases (``::ffff:102:304`` vs
    ``::ffff:1.2.3.4``): ``verify`` on another Python version would report a broken chain.

    - IPv4: dotted decimal without leading zeros;
    - IPv4-mapped IPv6 (``::ffff:a.b.c.d``, what dual-stack sockets report for IPv4
      clients) → the IPv4 address (``a.b.c.d``) — it is also STORED as IPv4, so the
      ``inet`` column read back gives the same text;
    - any other IPv6: :func:`_format_ipv6` (RFC 5952).

    Changing these rules invalidates every stored hash.
    """
    value = int(address)
    if isinstance(address, IPv4Address):
        return _format_ipv4(value)
    if value & _IPV4_MAPPED_MASK == _IPV4_MAPPED_PREFIX:
        return _format_ipv4(value & 0xFFFFFFFF)
    return _format_ipv6(value)


def normalize_ip(
    value: str | IPv4Address | IPv6Address | IPv4Interface | IPv6Interface | None,
) -> str | None:
    """Host IP in the canonical text form of :func:`format_ip` (no zone id, no prefix).

    The same function normalizes the value before it is hashed and stored (``record``)
    and the value read back from the ``inet`` column (``verify_chain``), whatever form
    the driver returns it in (text with or without the ``/32`` / ``/128`` host prefix,
    address or interface object).
    """
    if value is None:
        return None
    if isinstance(value, str) and "/" in value:
        # ``inet::text`` of a host is "a.b.c.d/32" / "x::y/128"
        value = ip_interface(value)
    if isinstance(value, IPv4Interface | IPv6Interface):
        if value.network.prefixlen != value.max_prefixlen:
            raise ValueError("ip_address must be a single host address")
        value = value.ip
    address = ip_address(value) if isinstance(value, str) else value
    if isinstance(address, IPv6Address) and address.scope_id is not None:
        raise ValueError("IPv6 zone identifiers are not supported in ip_address")
    return format_ip(address)


def normalize_user_agent(value: str | None) -> str | None:
    if value is None:
        return None
    return value[:USER_AGENT_MAX_LENGTH]


def build_payload(
    *,
    company_id: UUID | None,
    seq: int,
    occurred_at: datetime,
    actor_id: UUID | None,
    actor_display: str,
    actor_roles: Iterable[str],
    ip_address: str | IPv4Address | IPv6Address | IPv4Interface | IPv6Interface | None,
    user_agent: str | None,
    request_id: UUID,
    entity_type: str,
    entity_id: UUID | None,
    action: str,
    diff: Mapping[str, object],
    context: Mapping[str, object],
    prev_hash: str,
) -> dict[str, JsonValue]:
    """Hashed payload: every ``audit_log`` column except ``id`` and ``hash``."""
    payload = to_json_value(
        {
            "company_id": company_id,
            "seq": seq,
            "occurred_at": occurred_at,
            "actor_id": actor_id,
            "actor_display": actor_display,
            "actor_roles": list(actor_roles),
            "ip_address": normalize_ip(ip_address),
            "user_agent": user_agent,
            "request_id": request_id,
            "entity_type": str(entity_type),
            "entity_id": entity_id,
            "action": str(action),
            "diff": diff,
            "context": context,
            "prev_hash": prev_hash,
        }
    )
    assert isinstance(payload, dict)  # noqa: S101 - a dict literal always normalizes to dict
    return payload


def compute_hash(prev_hash: str, payload: Mapping[str, object]) -> str:
    """``sha256(prev_hash + canonical_json(payload))`` as 64 lower-case hex chars."""
    if len(prev_hash) != 64:
        raise ValueError("prev_hash must be 64 hex characters")
    return sha256_hex((prev_hash + canonical_json(payload)).encode("utf-8"))
