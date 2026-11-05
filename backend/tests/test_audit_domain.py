"""Audit domain (pure): actor, diff, payload and hash."""

from __future__ import annotations

import hashlib
import random
from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from ipaddress import IPv4Address, IPv4Interface, IPv6Address, IPv6Interface
from typing import Any
from uuid import UUID, uuid4

import pytest

from app.domain.audit import (
    GENESIS_HASH,
    USER_AGENT_MAX_LENGTH,
    Actor,
    AuditAction,
    EntityType,
    build_payload,
    compute_hash,
    format_ip,
    make_diff,
    normalize_context,
    normalize_diff,
    normalize_ip,
    normalize_user_agent,
)
from app.domain.canonical import canonical_json

COMPANY = UUID("11111111-1111-4111-8111-111111111111")
REQUEST = UUID("22222222-2222-4222-8222-222222222222")


def _payload(**overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "company_id": COMPANY,
        "seq": 1,
        "occurred_at": datetime(2026, 10, 28, 12, 0, tzinfo=UTC),
        "actor_id": None,
        "actor_display": "system",
        "actor_roles": [],
        "ip_address": None,
        "user_agent": None,
        "request_id": REQUEST,
        "entity_type": EntityType.CHANGE,
        "entity_id": None,
        "action": AuditAction.CREATE,
        "diff": {},
        "context": {},
        "prev_hash": GENESIS_HASH,
    }
    values.update(overrides)
    return build_payload(**values)


# --------------------------------------------------------------------------- Actor


def test_system_actor() -> None:
    actor = Actor.system()
    assert actor.id is None
    assert actor.display == "system"
    assert actor.roles == ()
    assert actor.is_system


def test_user_actor_roles_are_sorted_and_unique() -> None:
    actor = Actor(id=uuid4(), display="Anna Nowak", roles=("editor", "approver", "editor"))
    assert actor.roles == ("approver", "editor")
    assert not actor.is_system


@pytest.mark.parametrize(
    ("actor_id", "display", "roles", "message"),
    [
        (None, "Anna", (), "system"),
        (uuid4(), "  ", (), "empty"),
        (uuid4(), "Anna", ("",), "roles"),
    ],
)
def test_actor_validation(
    actor_id: UUID | None, display: str, roles: tuple[str, ...], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        Actor(id=actor_id, display=display, roles=roles)


# --------------------------------------------------------------------------- diff / context


def test_make_diff_reports_only_changed_fields() -> None:
    before = {"title": "Stary", "risk": "low", "at": datetime(2026, 1, 1, 13, tzinfo=UTC)}
    after = {
        "title": "Nowy — zażółć",
        "risk": "low",
        # same instant, different zone: not a change
        "at": datetime(2026, 1, 1, 14, tzinfo=timezone(timedelta(hours=1))),
        "assignee_id": UUID(int=5),
    }
    assert make_diff(before, after) == {
        "assignee_id": {"before": None, "after": str(UUID(int=5))},
        "title": {"before": "Stary", "after": "Nowy — zażółć"},
    }


def test_make_diff_for_creation() -> None:
    assert make_diff({}, {"name": "Alfa"}) == {"name": {"before": None, "after": "Alfa"}}


def test_normalize_diff_validates_shape() -> None:
    assert normalize_diff({"x": {"before": Decimal("1.0"), "after": 2}}) == {
        "x": {"before": "1.0", "after": 2}
    }
    with pytest.raises(ValueError, match="before"):
        normalize_diff({"x": {"before": 1}})
    with pytest.raises(ValueError, match="before"):
        normalize_diff({"x": "flat value"})


def test_normalize_context() -> None:
    assert normalize_context({"to_status": EntityType.CHANGE, "n": 1}) == {
        "to_status": "change",
        "n": 1,
    }


# --------------------------------------------------------------------------- ip / user agent


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        ("192.168.0.10", "192.168.0.10"),
        ("2001:0DB8:0000::0001", "2001:db8::1"),
        (IPv6Address("::1"), "::1"),
        (IPv4Interface("10.1.2.3/32"), "10.1.2.3"),
        (IPv6Interface("2001:db8::5/128"), "2001:db8::5"),
    ],
)
def test_normalize_ip(value: Any, expected: str | None) -> None:
    assert normalize_ip(value) == expected


@pytest.mark.parametrize(
    ("value", "message"),
    [
        (IPv4Interface("10.0.0.0/8"), "single host"),
        ("10.0.0.0/8", "single host"),
        ("2001:db8::/64", "single host"),
        ("fe80::1%eth0", "zone"),
    ],
)
def test_normalize_ip_rejects(value: Any, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        normalize_ip(value)


# Frozen vectors (ADR 0006 §3): changing any of them invalidates stored audit hashes.
IP_VECTORS = [
    # IPv4
    ("0.0.0.0", "0.0.0.0"),  # noqa: S104 - an address value, not a bind
    ("10.0.0.5", "10.0.0.5"),
    ("255.255.255.255", "255.255.255.255"),
    # IPv4-mapped IPv6 -> IPv4 (both textual forms)
    ("::ffff:192.0.2.1", "192.0.2.1"),
    ("::ffff:c000:201", "192.0.2.1"),
    ("::FFFF:10.0.0.5", "10.0.0.5"),
    ("::ffff:0.0.0.0", "0.0.0.0"),  # noqa: S104 - an address value, not a bind
    # IPv4-compatible (deprecated) and NAT64: plain hexadecimal groups, no dotted quad
    ("::192.0.2.1", "::c000:201"),
    ("::0.0.0.1", "::1"),
    ("64:ff9b::192.0.2.1", "64:ff9b::c000:201"),
    # not IPv4-mapped (the ffff is not in the 6th group)
    ("::ffff:0:0:0", "::ffff:0:0:0"),
    ("::1:ffff:c000:201", "::1:ffff:c000:201"),
    # RFC 5952 §4.1 leading zeros, §4.3 lower case
    ("2001:0DB8:0000::0001", "2001:db8::1"),
    ("2001:DB8::AAAA", "2001:db8::aaaa"),
    # §4.2.1 shorten as much as possible
    ("2001:db8:0:0:0:0:2:1", "2001:db8::2:1"),
    ("2001:db8::0:1", "2001:db8::1"),
    # §4.2.2 a single 16-bit zero field is not shortened
    ("2001:db8:0:1:1:1:1:1", "2001:db8:0:1:1:1:1:1"),
    ("2001:db8::1:1:1:1:1", "2001:db8:0:1:1:1:1:1"),
    # §4.2.3 the longest run; on a tie the first one
    ("2001:0:0:1:0:0:0:1", "2001:0:0:1::1"),
    ("2001:db8:0:0:1:0:0:1", "2001:db8::1:0:0:1"),
    ("1:0:0:2:0:0:3:4", "1::2:0:0:3:4"),
    # edges
    ("::", "::"),
    ("::1", "::1"),
    ("1::", "1::"),
    ("0:0:1:0:0:0:0:1", "0:0:1::1"),
    ("1:0:0:0:0:0:0:0", "1::"),
    ("fe80::a", "fe80::a"),
    ("ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff", "ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff"),
    ("1:2:3:4:5:6:7:8", "1:2:3:4:5:6:7:8"),
]


@pytest.mark.parametrize(("value", "expected"), IP_VECTORS)
def test_ip_canonical_vectors(value: str, expected: str) -> None:
    assert normalize_ip(value) == expected
    # idempotent, and the same for every input form (text, address, host interface)
    assert normalize_ip(expected) == expected
    assert format_ip(IPv6Address(value) if ":" in value else IPv4Address(value)) == expected
    interface = IPv6Interface(value) if ":" in value else IPv4Interface(value)
    assert normalize_ip(interface) == expected
    assert normalize_ip(str(interface.with_prefixlen)) == expected


def test_ip_format_matches_rfc5952_for_ordinary_addresses() -> None:
    """Cross-check against CPython for addresses whose ``str()`` has always been RFC 5952
    (outside ``::/96`` and ``::ffff:0:0/96``). The vectors above, not CPython, are the
    definition — this only guards the implementation against typos."""
    rng = random.Random(5952)  # noqa: S311 - deterministic test data
    checked = 0
    while checked < 5000:
        groups = [rng.choice((0, 0, 0, 1, 0xFFFF, rng.getrandbits(16))) for _ in range(8)]
        value = 0
        for group in groups:
            value = (value << 16) | group
        if value >> 32 in (0, 0xFFFF):
            continue
        assert format_ip(IPv6Address(value)) == IPv6Address(value).compressed
        checked += 1


def test_normalize_ip_rejects_garbage() -> None:
    with pytest.raises(ValueError, match="does not appear to be an IPv4 or IPv6 address"):
        normalize_ip("not-an-ip")


def test_user_agent_is_truncated() -> None:
    assert normalize_user_agent(None) is None
    assert normalize_user_agent("x" * 5000) == "x" * USER_AGENT_MAX_LENGTH


# --------------------------------------------------------------------------- payload / hash


def test_payload_contains_every_column_except_id_and_hash() -> None:
    assert set(_payload()) == {
        "company_id",
        "seq",
        "occurred_at",
        "actor_id",
        "actor_display",
        "actor_roles",
        "ip_address",
        "user_agent",
        "request_id",
        "entity_type",
        "entity_id",
        "action",
        "diff",
        "context",
        "prev_hash",
    }


def test_payload_values_are_canonical() -> None:
    payload = _payload(
        occurred_at=datetime(2026, 10, 28, 13, 0, tzinfo=timezone(timedelta(hours=1))),
        ip_address="2001:DB8::1",
    )
    assert payload["occurred_at"] == "2026-10-28T12:00:00.000000Z"
    assert payload["company_id"] == str(COMPANY)
    assert payload["entity_type"] == "change"
    assert payload["action"] == "create"
    assert payload["ip_address"] == "2001:db8::1"


def test_compute_hash_is_sha256_of_prev_hash_and_canonical_payload() -> None:
    payload = _payload(diff={"title": {"before": None, "after": "Zmiana łączności"}})
    expected = hashlib.sha256((GENESIS_HASH + canonical_json(payload)).encode("utf-8")).hexdigest()
    assert compute_hash(GENESIS_HASH, payload) == expected
    assert len(expected) == 64


def test_hash_changes_with_any_field_and_with_prev_hash() -> None:
    base = compute_hash(GENESIS_HASH, _payload())
    assert compute_hash(GENESIS_HASH, _payload(seq=2)) != base
    assert compute_hash(GENESIS_HASH, _payload(context={"comment": "x"})) != base
    assert compute_hash("f" * 64, _payload()) != base


def test_compute_hash_rejects_bad_prev_hash() -> None:
    with pytest.raises(ValueError, match="64"):
        compute_hash("abc", _payload())
