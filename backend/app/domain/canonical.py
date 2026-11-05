"""Canonical JSON — the ONE serialization used for hashing (audit chain, report data).

``canonical_json(value)`` is used both when an audit entry is written and when the chain
is verified (CLAUDE.md 6.2), and for ``report_exports.data_sha256`` (CLAUDE.md 9). Any
change to these rules invalidates every existing hash — treat them as frozen (ADR 0006).

Rules:

- keys sorted (Python ``str`` ordering = Unicode code points), separators ``(",", ":")``,
  output UTF-8 without escaping non-ASCII (``ensure_ascii=False``);
- mapping keys must be ``str`` (a ``StrEnum`` key is used by value);
- ``datetime`` must be timezone-aware and is rendered in UTC with ALWAYS six fractional
  digits and ``Z``: ``2026-10-28T12:00:00.000000Z`` (PostgreSQL ``timestamptz`` has
  microsecond precision, so a value read back from the database renders identically);
- ``date`` → ``YYYY-MM-DD``; ``UUID`` → lower-case hyphenated string;
- ``Decimal`` → ``str(d)`` (a JSON string, never a number: ``jsonb``/``float`` round trips
  would lose precision); NaN/Infinity rejected;
- ``Enum`` → its ``value`` (normalized recursively); IP addresses → ``str``;
- ``list``/``tuple`` → array; ``set``/``frozenset`` → array sorted by the canonical form of
  each element;
- ``float`` is REJECTED: a float stored in ``jsonb`` (``numeric``) does not always read back
  with the same textual form (``1e300`` comes back as an integer), which would break the
  hash. Use ``int`` or ``Decimal``;
- ``bytes`` and any other type are rejected (``TypeError``) — never silently ``str()``-ed.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from ipaddress import IPv4Address, IPv6Address
from uuid import UUID

type JsonValue = bool | int | str | list[JsonValue] | dict[str, JsonValue] | None

_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


def format_datetime(value: datetime) -> str:
    """Render an aware datetime as UTC ISO 8601 with microseconds and ``Z``."""
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise ValueError("naive datetime is not allowed in canonical JSON (use UTC-aware)")
    return value.astimezone(UTC).strftime(_DATETIME_FORMAT)


def to_json_value(value: object) -> JsonValue:
    """Normalize ``value`` to plain JSON types following the canonical rules."""
    # bool before int (bool is a subclass of int); Enum before str/int (StrEnum, IntEnum).
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, Enum):
        return to_json_value(value.value)
    if isinstance(value, str):
        return value
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        raise TypeError("float is not allowed in canonical JSON (use int or Decimal)")
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("non-finite Decimal is not allowed in canonical JSON")
        return str(value)
    if isinstance(value, datetime):
        return format_datetime(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, IPv4Address | IPv6Address):
        return str(value)
    if isinstance(value, Mapping):
        result: dict[str, JsonValue] = {}
        for key, item in value.items():
            if isinstance(key, Enum):
                key = key.value
            if not isinstance(key, str):
                raise TypeError(f"canonical JSON keys must be str, got {type(key).__name__}")
            result[key] = to_json_value(item)
        return result
    if isinstance(value, list | tuple):
        return [to_json_value(item) for item in value]
    if isinstance(value, set | frozenset):
        items = [to_json_value(item) for item in value]
        return sorted(items, key=_dumps)
    raise TypeError(f"type {type(value).__name__} is not allowed in canonical JSON")


def _dumps(value: JsonValue) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def canonical_json(value: object) -> str:
    """Canonical JSON text of ``value`` (see module docstring for the rules)."""
    return _dumps(to_json_value(value))


def canonical_json_bytes(value: object) -> bytes:
    """UTF-8 bytes of :func:`canonical_json` — the input of every hash."""
    return canonical_json(value).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
