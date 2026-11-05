"""Pure rules of the dictionaries and the CI inventory (ADR 0011)."""

from __future__ import annotations

import pytest

from app.domain.dictionaries import (
    InvalidDataError,
    Risk,
    effective_requires_approval,
    normalize_ci_identifier,
    normalize_description,
    normalize_name,
    validate_category_code,
    validate_ci_type_code,
)


@pytest.mark.parametrize("code", ["ACC", "ACC-PRIV", "OT", "PATCH-OS", "A1", "NET-VLAN-2"])
def test_valid_category_codes(code: str) -> None:
    assert validate_category_code(code) == code


@pytest.mark.parametrize(
    "code", ["", "A", "acc", "Acc", "ACC_PRIV", "-ACC", "ACC-", "ACC--X", "1ACC", "ĄCC", "A" * 33]
)
def test_invalid_category_codes(code: str) -> None:
    with pytest.raises(InvalidDataError) as info:
        validate_category_code(code)
    assert info.value.field == "code"


@pytest.mark.parametrize("code", ["server", "vm", "network_device", "ot_system", "a1"])
def test_valid_ci_type_codes(code: str) -> None:
    assert validate_ci_type_code(code) == code


@pytest.mark.parametrize("code", ["", "s", "Server", "1vm", "network-device", "ą_typ", "a" * 33])
def test_invalid_ci_type_codes(code: str) -> None:
    with pytest.raises(InvalidDataError):
        validate_ci_type_code(code)


def test_names_and_identifiers_are_trimmed_and_bounded() -> None:
    assert normalize_name("  Sieć  ") == "Sieć"
    assert normalize_ci_identifier("  FW-01 ") == "FW-01"
    for bad in ("", "   ", "x" * 201):
        with pytest.raises(InvalidDataError):
            normalize_name(bad)
    with pytest.raises(InvalidDataError) as info:
        normalize_ci_identifier("x" * 101)
    assert info.value.field == "identifier"


def test_description_empty_is_none() -> None:
    assert normalize_description(None) is None
    assert normalize_description("  \n ") is None
    assert normalize_description(" Zażółć gęślą jaźń\n") == "Zażółć gęślą jaźń"
    with pytest.raises(InvalidDataError):
        normalize_description("x" * 4001)


@pytest.mark.parametrize(
    ("category", "subcategory", "expected"),
    [
        (False, None, False),
        (False, False, False),
        (False, True, True),  # ACC + privileged account
        (True, None, True),
        (True, False, True),  # a subcategory never loosens its category
        (True, True, True),
    ],
)
def test_subcategory_only_tightens_approval(
    category: bool, subcategory: bool | None, expected: bool
) -> None:
    assert effective_requires_approval(category, subcategory) is expected


def test_risk_values() -> None:
    assert [r.value for r in Risk] == ["low", "medium", "high"]
