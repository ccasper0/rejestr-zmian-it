"""Password policy of local accounts (ADR 0018 §3; NIST SP 800-63B §5.1.1.2). No I/O
except reading the bundled list of common passwords once.

Rules (checked in this order, the first violation is reported):

- the password is normalized to Unicode NFKC before it is checked and hashed, so
  visually identical input always yields the same password (63B §5.1.1.2);
- length in code points: at least :data:`MIN_LENGTH`, at most :data:`MAX_LENGTH`;
- not one repeated character and not a trivial keyboard / digit sequence;
- not equal to, and not containing, the e-mail address, its local part or the whole
  display name (case-insensitive, whitespace ignored; only parts of at least
  :data:`IDENTITY_MIN_LENGTH` characters);
- not on the bundled list of common passwords (``common_passwords.txt``, offline,
  case-insensitive);
- no composition rules ("one special character" etc.) - 63B advises against them.

Error codes are English (``auth.password_*``); the Polish message is in
:data:`MESSAGES` (CLAUDE.md §11.8).
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from enum import StrEnum
from functools import lru_cache
from pathlib import Path

MIN_LENGTH = 12
MAX_LENGTH = 128
IDENTITY_MIN_LENGTH = 4
COMMON_PASSWORDS_FILE = Path(__file__).with_name("common_passwords.txt")

_SEQUENCES = (
    "0123456789012345678901234567890",
    "9876543210987654321098765432109",
    "abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyz",
    "zyxwvutsrqponmlkjihgfedcbazyxwvutsrqponmlkjihgfedcba",
    "qwertyuiopasdfghjklzxcvbnmqwertyuiopasdfghjklzxcvbnm",
    "qwertzuiopasdfghjklyxcvbnmqwertzuiopasdfghjklyxcvbnm",
    "1qaz2wsx3edc4rfv5tgb6yhn7ujm8ik9ol0p",
    "zaq12wsxcde34rfvbgt56yhnmju78ik9ol0p",
    "1q2w3e4r5t6y7u8i9o0p",
)


class PasswordProblem(StrEnum):
    TOO_SHORT = "auth.password_too_short"
    TOO_LONG = "auth.password_too_long"
    TOO_SIMPLE = "auth.password_too_simple"
    CONTAINS_IDENTITY = "auth.password_contains_identity"
    TOO_COMMON = "auth.password_too_common"


MESSAGES: dict[PasswordProblem, str] = {
    PasswordProblem.TOO_SHORT: f"Hasło musi mieć co najmniej {MIN_LENGTH} znaków.",
    PasswordProblem.TOO_LONG: f"Hasło może mieć najwyżej {MAX_LENGTH} znaków.",
    PasswordProblem.TOO_SIMPLE: (
        "Hasło jest zbyt proste (powtórzony znak albo prosty ciąg z klawiatury). "
        "Użyj np. kilku niepowiązanych słów."
    ),
    PasswordProblem.CONTAINS_IDENTITY: (
        "Hasło nie może zawierać adresu e-mail ani imienia i nazwiska użytkownika."
    ),
    PasswordProblem.TOO_COMMON: (
        "To hasło jest zbyt popularne (znajduje się na liście często używanych haseł)."
    ),
}


@dataclass(frozen=True, slots=True)
class PasswordCheck:
    problem: PasswordProblem | None

    @property
    def ok(self) -> bool:
        return self.problem is None

    @property
    def message(self) -> str | None:
        return None if self.problem is None else MESSAGES[self.problem]


def normalize_password(password: str) -> str:
    """NFKC form - the form that is checked AND hashed (also at login)."""
    return unicodedata.normalize("NFKC", password)


def _fold(value: str) -> str:
    return "".join(unicodedata.normalize("NFKC", value).casefold().split())


@lru_cache(maxsize=1)
def common_passwords() -> frozenset[str]:
    """The bundled list (one per line, ``#`` comments), case-folded."""
    lines = COMMON_PASSWORDS_FILE.read_text(encoding="utf-8").splitlines()
    return frozenset(
        _fold(line) for line in lines if line.strip() and not line.lstrip().startswith("#")
    )


def _is_trivial(folded: str) -> bool:
    if len(set(folded)) <= 2:
        return True
    return any(folded in sequence for sequence in _SEQUENCES)


def _identity_parts(email: str | None, display_name: str | None) -> list[str]:
    parts: list[str] = []
    if email:
        folded = _fold(email)
        parts.append(folded)
        parts.append(folded.split("@", 1)[0])
    if display_name:
        parts.append(_fold(display_name))
    return [p for p in parts if len(p) >= IDENTITY_MIN_LENGTH]


def check_password(
    password: str, *, email: str | None = None, display_name: str | None = None
) -> PasswordCheck:
    """The first rule ``password`` violates (``problem = None``: acceptable)."""
    normalized = normalize_password(password)
    length = len(normalized)
    if length < MIN_LENGTH:
        return PasswordCheck(PasswordProblem.TOO_SHORT)
    if length > MAX_LENGTH:
        return PasswordCheck(PasswordProblem.TOO_LONG)
    folded = _fold(normalized)
    if _is_trivial(folded):
        return PasswordCheck(PasswordProblem.TOO_SIMPLE)
    if any(part in folded for part in _identity_parts(email, display_name)):
        return PasswordCheck(PasswordProblem.CONTAINS_IDENTITY)
    if folded in common_passwords():
        return PasswordCheck(PasswordProblem.TOO_COMMON)
    return PasswordCheck(None)
