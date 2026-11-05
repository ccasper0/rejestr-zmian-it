"""Global dictionaries and the CI inventory: formats and rules (CLAUDE.md 4.1, ADR 0011).

Pure Python, no I/O. The same formats are enforced by CHECK constraints in migration 0006
(defence in depth); the services reject invalid data first with Polish messages.
"""

from __future__ import annotations

import re
from enum import StrEnum

CATEGORY_CODE_RE = re.compile(r"^[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*$")
CATEGORY_CODE_MAX = 32
CI_TYPE_CODE_RE = re.compile(r"^[a-z][a-z0-9_]{1,31}$")
NAME_MAX_LENGTH = 200
CI_IDENTIFIER_MAX_LENGTH = 100
CI_DESCRIPTION_MAX_LENGTH = 4000


class Risk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class InvalidDataError(ValueError):
    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.message = message


def validate_category_code(code: str) -> str:
    """Upper-case ASCII letters and digits, groups joined with ``-`` (``ACC``, ``ACC-PRIV``).

    Not normalized: a code is an identifier used in reports, the caller must send it
    exactly. Upper case only, so uniqueness is case-insensitive by construction.
    """
    if not (2 <= len(code) <= CATEGORY_CODE_MAX and CATEGORY_CODE_RE.fullmatch(code)):
        raise InvalidDataError(
            "code",
            "Kod kategorii musi mieć od 2 do 32 znaków: wielkie litery A-Z i cyfry, "
            "grupy oddzielone myślnikiem (np. ACC, ACC-PRIV).",
        )
    return code


def validate_ci_type_code(code: str) -> str:
    """Lower-case snake case (``server``, ``network_device``), 2-32 characters."""
    if not CI_TYPE_CODE_RE.fullmatch(code):
        raise InvalidDataError(
            "code",
            "Kod typu obiektu musi mieć od 2 do 32 znaków: małe litery a-z, cyfry i podkreślenie, "
            "zaczynać się od litery (np. network_device).",
        )
    return code


def normalize_name(value: str, *, field: str = "name") -> str:
    clean = value.strip()
    if not clean or len(clean) > NAME_MAX_LENGTH:
        raise InvalidDataError(
            field, f"Nazwa jest wymagana i może mieć najwyżej {NAME_MAX_LENGTH} znaków."
        )
    return clean


def normalize_ci_identifier(value: str) -> str:
    """Trimmed, case preserved; uniqueness in the company ignores letter case (ADR 0011)."""
    clean = value.strip()
    if not clean or len(clean) > CI_IDENTIFIER_MAX_LENGTH:
        raise InvalidDataError(
            "identifier",
            f"Identyfikator obiektu jest wymagany i może mieć najwyżej "
            f"{CI_IDENTIFIER_MAX_LENGTH} znaków.",
        )
    return clean


def normalize_description(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    clean = value.strip()
    if len(clean) > CI_DESCRIPTION_MAX_LENGTH:
        raise InvalidDataError(
            "description", f"Opis może mieć najwyżej {CI_DESCRIPTION_MAX_LENGTH} znaków."
        )
    return clean


def effective_requires_approval(category: bool, subcategory: bool | None) -> bool:
    """Whether a change in the category / subcategory needs approval (ADR 0011 §3).

    A subcategory can only TIGHTEN its category: ``ACC`` (no approval, standard changes)
    with the subcategory ``ACC-PRIV`` (privileged accounts, approval required) gives
    ``True``; a subcategory of a category that requires approval never removes it.
    """
    return category or bool(subcategory)
