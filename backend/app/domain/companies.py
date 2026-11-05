"""Company rules (CLAUDE.md 4.1). Pure Python, no I/O."""

from __future__ import annotations

import re
from enum import StrEnum

PREFIX_RE = re.compile(r"^[A-Z]{2,8}$")
NAME_MAX_LENGTH = 200
_NIP_WEIGHTS = (6, 5, 7, 2, 3, 4, 5, 6, 7)


class CompanyStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class InvalidCompanyDataError(ValueError):
    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.message = message


def validate_prefix(prefix: str) -> str:
    """2-8 upper-case ASCII letters A-Z; immutable once the company exists."""
    if not PREFIX_RE.fullmatch(prefix):
        raise InvalidCompanyDataError(
            "prefix",
            "Prefiks musi składać się z od 2 do 8 wielkich liter A-Z (bez polskich znaków).",
        )
    return prefix


def normalize_name(name: str) -> str:
    value = name.strip()
    if not value or len(value) > NAME_MAX_LENGTH:
        raise InvalidCompanyDataError(
            "name", f"Nazwa spółki jest wymagana i może mieć najwyżej {NAME_MAX_LENGTH} znaków."
        )
    return value


def normalize_tax_id(raw: str | None) -> str | None:
    """Polish NIP: 10 digits with a valid checksum; separators and a ``PL`` prefix are dropped."""
    if raw is None or not raw.strip():
        return None
    value = re.sub(r"[\s-]", "", raw.strip().upper())
    value = value.removeprefix("PL")
    if not re.fullmatch(r"\d{10}", value):
        raise InvalidCompanyDataError("tax_id", "NIP musi składać się z 10 cyfr.")
    digits = [int(c) for c in value]
    checksum = sum(w * d for w, d in zip(_NIP_WEIGHTS, digits, strict=False)) % 11
    if checksum == 10 or checksum != digits[9]:
        raise InvalidCompanyDataError("tax_id", "NIP ma nieprawidłową sumę kontrolną.")
    return value
