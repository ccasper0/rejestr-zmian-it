"""Password policy (NIST SP 800-63B) and argon2id hashing (ADR 0018 §2-3). No database."""

from __future__ import annotations

import time

import pytest
from argon2 import PasswordHasher

from app.auth import passwords
from app.domain.passwords import (
    MAX_LENGTH,
    MESSAGES,
    MIN_LENGTH,
    PasswordProblem,
    check_password,
    common_passwords,
    normalize_password,
)

# --------------------------------------------------------------------------- policy


@pytest.mark.parametrize(
    ("password", "problem"),
    [
        ("a" * (MIN_LENGTH - 1), PasswordProblem.TOO_SHORT),
        ("Zażółć-1", PasswordProblem.TOO_SHORT),
        ("Ab1-" * 40, PasswordProblem.TOO_LONG),
        ("111111111111111", PasswordProblem.TOO_SIMPLE),
        ("abababababababab", PasswordProblem.TOO_SIMPLE),
        ("1234567890123", PasswordProblem.TOO_SIMPLE),
        ("ZYXWVUTSRQPONM", PasswordProblem.TOO_SIMPLE),
        ("QwertyUiopAsdf", PasswordProblem.TOO_SIMPLE),
        ("Password1234", PasswordProblem.TOO_COMMON),
        ("P A S S W O R D 1 2 3 4", PasswordProblem.TOO_COMMON),  # whitespace ignored
        ("Polska123456", PasswordProblem.TOO_COMMON),
        ("rejestrzmian123", PasswordProblem.TOO_COMMON),
    ],
)
def test_rejected_passwords(password: str, problem: PasswordProblem) -> None:
    result = check_password(password)
    assert result.problem is problem
    assert not result.ok
    assert result.message == MESSAGES[problem]


@pytest.mark.parametrize(
    "password",
    [
        "Zielony rower nad Wisłą",
        "zażółć gęślą jaźń 2026",
        "correct horse battery staple!",  # NOT the famous one (it has a "!")
        "x" * 3 + "Kot-Na-Dachu",
        "ż" * 4 + "ółćęśąźń12",
        "a" * MIN_LENGTH + "bc",  # mostly one character, but three distinct ones
    ],
)
def test_accepted_passwords(password: str) -> None:
    assert check_password(password).ok, check_password(password).problem


def test_length_is_counted_in_code_points_after_nfkc() -> None:
    assert check_password("ąęółżźćń" + "śĄĘÓ").ok  # 12 non-ASCII characters
    # NFKC: the ligature "ﬁ" is "fi" - checked and hashed in the same form.
    assert normalize_password("ﬁ") == "fi"
    assert check_password("x" * (MAX_LENGTH - 3) + "abc").ok


def test_no_composition_rules() -> None:
    """No "special character" / "digit" / "upper case" requirements (63B §5.1.1.2)."""
    assert check_password("dlugie haslo bez cyfr").ok


def test_identity_is_rejected() -> None:
    email = "Jan.Kowalski@example.com"
    name = "Jan Kowalski"
    for candidate in (
        "jan.kowalski@example.com",
        "JAN.KOWALSKI2026!",
        "Moje-jan.kowalski-hasło",
        "Jan Kowalski 1234",
        "jankowalski#2026",
    ):
        result = check_password(candidate, email=email, display_name=name)
        assert result.problem is PasswordProblem.CONTAINS_IDENTITY, candidate
    # Short parts (< 4 characters) are not checked.
    assert check_password("ola-ma-kota-na-dachu", email="ola@example.com", display_name="Ol").ok


def test_common_list_is_bundled_and_long_entries_only_matter() -> None:
    entries = common_passwords()
    assert len(entries) >= 5000
    assert "password1234" in entries
    assert all(not entry.startswith("#") for entry in entries)
    # Only entries the earlier rules would let through are worth listing.
    assert all(len(entry) >= MIN_LENGTH for entry in entries)


@pytest.mark.parametrize(
    "candidate",
    [
        "zaq1@WSXcde3",
        "QwertyUiop12",
        "haslo1234567",
        "Hasło2024!",  # too short: rejected earlier, by the length rule
        "LegiaWarszawa1",
        "Październik2025",
        "november2026!",
        "Kochanie1234!",
        "Sunshine1991!",
        "1qaz@WSX3edc2024",
        "Agnieszka1990!",
    ],
)
def test_extended_common_list_rejects_typical_patterns(candidate: str) -> None:
    expected = (
        PasswordProblem.TOO_SHORT if len(candidate) < MIN_LENGTH else PasswordProblem.TOO_COMMON
    )
    assert check_password(candidate).problem is expected, candidate


# --------------------------------------------------------------------------- hashing


def test_hash_is_argon2id_with_owasp_parameters() -> None:
    encoded = passwords.hash_password("Zielony rower nad Wisłą")
    assert encoded.startswith("$argon2id$v=19$m=19456,t=2,p=1$")
    assert passwords.verify_password(encoded, "Zielony rower nad Wisłą")
    assert not passwords.verify_password(encoded, "zielony rower nad wisłą")
    assert not passwords.verify_password("not-a-hash", "x")
    assert not passwords.needs_rehash(encoded)
    # Salted: the same password never gives the same hash.
    assert passwords.hash_password("Zielony rower nad Wisłą") != encoded


def test_verification_uses_the_nfkc_form() -> None:
    encoded = passwords.hash_password("ﬁlm o kotach i psach")
    assert passwords.verify_password(encoded, "film o kotach i psach")


def test_weaker_hashes_are_upgraded() -> None:
    weak = PasswordHasher(time_cost=1, memory_cost=8192, parallelism=1).hash("abc")
    assert passwords.needs_rehash(weak)


async def test_unknown_account_costs_a_hash_verification() -> None:
    """No account (or no password): verified against the dummy hash - same cost."""
    passwords.dummy_hash()  # computed once, not part of the measurement
    encoded = passwords.hash_password("Zielony rower nad Wisłą")
    start = time.perf_counter()
    assert await passwords.verify_password_async(None, "Zielony rower nad Wisłą") is False
    missing = time.perf_counter() - start
    start = time.perf_counter()
    assert await passwords.verify_password_async(encoded, "zle haslo zle haslo") is False
    wrong = time.perf_counter() - start
    # Both run one argon2id verification with the same parameters (loose bound: CI noise).
    assert missing > wrong / 5
    assert passwords.dummy_hash().startswith("$argon2id$")


def test_temporary_passwords_are_random_and_valid() -> None:
    generated = {passwords.generate_temporary_password() for _ in range(50)}
    assert len(generated) == 50
    for value in generated:
        assert len(value) == 23
        assert check_password(value).ok
        assert not set(value) & set("0O1lI")
