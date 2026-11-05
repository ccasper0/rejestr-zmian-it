import pytest

from app.domain.companies import (
    CompanyStatus,
    InvalidCompanyDataError,
    normalize_name,
    normalize_tax_id,
    validate_prefix,
)


@pytest.mark.parametrize("prefix", ["AB", "ALFA", "ABCDEFGH"])
def test_valid_prefixes(prefix: str) -> None:
    assert validate_prefix(prefix) == prefix


@pytest.mark.parametrize("prefix", ["A", "ABCDEFGHI", "alfa", "AL1", "AŁFA", "AL FA", "", "all"])
def test_invalid_prefixes(prefix: str) -> None:
    with pytest.raises(InvalidCompanyDataError) as info:
        validate_prefix(prefix)
    assert info.value.field == "prefix"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("5260250995", "5260250995"),
        ("526-025-09-95", "5260250995"),
        ("526 025 09 95", "5260250995"),
        ("PL5260250995", "5260250995"),
        (None, None),
        ("", None),
        ("   ", None),
    ],
)
def test_tax_id_normalized(raw: str | None, expected: str | None) -> None:
    assert normalize_tax_id(raw) == expected


@pytest.mark.parametrize("raw", ["5260250994", "123", "52602509951", "ABCDEFGHIJ", "0000000000x"])
def test_invalid_tax_id(raw: str) -> None:
    with pytest.raises(InvalidCompanyDataError) as info:
        normalize_tax_id(raw)
    assert info.value.field == "tax_id"


def test_name_is_trimmed_and_required() -> None:
    assert normalize_name("  Alfa S.A. ") == "Alfa S.A."
    for bad in ("", "   ", "x" * 201):
        with pytest.raises(InvalidCompanyDataError):
            normalize_name(bad)


def test_statuses() -> None:
    assert {s.value for s in CompanyStatus} == {"active", "archived"}
