"""canonical_json — the single serialization used for every hash (ADR 0006)."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum, IntEnum, StrEnum
from ipaddress import IPv4Address, IPv6Address
from uuid import UUID

import pytest

from app.domain.canonical import (
    canonical_json,
    canonical_json_bytes,
    format_datetime,
    sha256_hex,
    to_json_value,
)


class Color(StrEnum):
    RED = "red"


class Level(IntEnum):
    HIGH = 3


class Plain(Enum):
    A = Decimal("1.50")


def test_sorted_keys_and_compact_separators() -> None:
    assert canonical_json({"b": 1, "a": [1, 2], "c": {"z": None, "y": True}}) == (
        '{"a":[1,2],"b":1,"c":{"y":true,"z":null}}'
    )


def test_deterministic_regardless_of_insertion_order() -> None:
    one = {"title": "x", "risk": "high", "nested": {"b": 2, "a": 1}}
    two = {"nested": {"a": 1, "b": 2}, "risk": "high", "title": "x"}
    assert canonical_json(one) == canonical_json(two)


def test_polish_characters_are_not_escaped_and_encoded_as_utf8() -> None:
    text = "zażółć gęślą jaźń ZAŻÓŁĆ GĘŚLĄ JAŹŃ"
    out = canonical_json({"t": text})
    assert out == '{"t":"' + text + '"}'
    assert "\\u" not in out
    assert canonical_json_bytes({"t": text}) == out.encode("utf-8")
    assert json.loads(canonical_json_bytes({"t": text}).decode("utf-8")) == {"t": text}


def test_keys_sorted_by_code_point_including_polish_letters() -> None:
    # "ą" (U+0105) sorts after "z" (U+007A) by code point.
    assert canonical_json({"ą": 1, "z": 2, "a": 3}) == '{"a":3,"z":2,"ą":1}'


@pytest.mark.parametrize(
    "value",
    [
        datetime(2026, 10, 28, 13, 0, 0, 123456, tzinfo=timezone(timedelta(hours=1))),
        datetime(2026, 10, 28, 17, 30, 0, 123456, tzinfo=timezone(timedelta(hours=5, minutes=30))),
        datetime(2026, 10, 28, 7, 0, 0, 123456, tzinfo=timezone(timedelta(hours=-5))),
        datetime(2026, 10, 28, 12, 0, 0, 123456, tzinfo=UTC),
    ],
)
def test_datetimes_in_any_zone_render_as_the_same_utc_instant(value: datetime) -> None:
    assert canonical_json(value) == '"2026-10-28T12:00:00.123456Z"'


def test_datetime_always_has_six_fraction_digits() -> None:
    assert format_datetime(datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)) == (
        "2026-01-02T03:04:05.000000Z"
    )


def test_naive_datetime_rejected() -> None:
    with pytest.raises(ValueError, match="naive"):
        canonical_json({"at": datetime(2026, 1, 1)})  # noqa: DTZ001


def test_scalar_types() -> None:
    uid = UUID("6F1C2D3E-0000-4000-8000-00000000ABCD")
    assert to_json_value(uid) == "6f1c2d3e-0000-4000-8000-00000000abcd"
    assert to_json_value(Decimal("10.50")) == "10.50"
    assert to_json_value(date(2026, 2, 3)) == "2026-02-03"
    assert to_json_value(IPv4Address("10.0.0.1")) == "10.0.0.1"
    assert to_json_value(IPv6Address("2001:DB8:0:0:0:0:0:1")) == "2001:db8::1"
    assert to_json_value(True) is True
    assert to_json_value(None) is None
    assert to_json_value(2**70) == 2**70


def test_enums_use_their_value() -> None:
    assert canonical_json({Color.RED: Color.RED, "lvl": Level.HIGH, "p": Plain.A}) == (
        '{"lvl":3,"p":"1.50","red":"red"}'
    )


def test_sequences_and_sets() -> None:
    assert canonical_json((1, "a")) == '[1,"a"]'
    assert canonical_json({"b", "a", "c"}) == '["a","b","c"]'
    assert canonical_json(frozenset({3, 1, 2})) == "[1,2,3]"


@pytest.mark.parametrize("value", [1.5, float("nan"), {"x": 0.1}])
def test_float_rejected(value: object) -> None:
    with pytest.raises(TypeError, match="float"):
        canonical_json(value)


@pytest.mark.parametrize("value", [Decimal("NaN"), Decimal("Infinity")])
def test_non_finite_decimal_rejected(value: Decimal) -> None:
    with pytest.raises(ValueError, match="non-finite"):
        canonical_json(value)


@pytest.mark.parametrize("value", [b"bytes", object(), {1: "int key"}])
def test_unsupported_types_rejected(value: object) -> None:
    with pytest.raises(TypeError):
        canonical_json(value)


def test_sha256_hex() -> None:
    assert sha256_hex(b"abc") == hashlib.sha256(b"abc").hexdigest()
