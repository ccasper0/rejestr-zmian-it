"""Password hashing (argon2id, ADR 0018 §2) and temporary passwords.

Parameters follow the OWASP Password Storage Cheat Sheet for argon2id: m = 19 MiB,
t = 2, p = 1 (salt 16 B, hash 32 B). The encoded hash carries its parameters, so they can
be raised later: :func:`needs_rehash` is checked after every successful login and the
hash is upgraded then.

Hashing is CPU and memory heavy (tens of milliseconds): the async helpers run it in a
worker thread, never on the event loop. A login of an unknown e-mail verifies against
:func:`dummy_hash` (same parameters), so it takes the same time as a wrong password of an
existing account (no account enumeration by timing).

The password is normalized to NFKC (``app.domain.passwords.normalize_password``) before
hashing and before verification.
"""

from __future__ import annotations

import asyncio
import secrets
from functools import lru_cache

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.domain.passwords import normalize_password

ARGON2_TIME_COST = 2
ARGON2_MEMORY_COST_KIB = 19 * 1024
ARGON2_PARALLELISM = 1
ARGON2_HASH_LENGTH = 32
ARGON2_SALT_LENGTH = 16

# Temporary passwords: 20 characters from an alphabet without look-alikes (0/O, 1/l/I),
# ~113 bits of entropy; grouped by dashes for dictation (the dashes are part of it).
TEMPORARY_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
TEMPORARY_GROUPS = 4
TEMPORARY_GROUP_LENGTH = 5

_hasher = PasswordHasher(
    time_cost=ARGON2_TIME_COST,
    memory_cost=ARGON2_MEMORY_COST_KIB,
    parallelism=ARGON2_PARALLELISM,
    hash_len=ARGON2_HASH_LENGTH,
    salt_len=ARGON2_SALT_LENGTH,
    type=Type.ID,
)


def hash_password(password: str) -> str:
    return _hasher.hash(normalize_password(password))


def verify_password(encoded: str, password: str) -> bool:
    """True when ``password`` matches; False for a mismatch or an unusable hash."""
    try:
        return _hasher.verify(encoded, normalize_password(password))
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(encoded: str) -> bool:
    try:
        return _hasher.check_needs_rehash(encoded)
    except InvalidHashError:  # pragma: no cover - only hashes of this module are stored
        return True


@lru_cache(maxsize=1)
def dummy_hash() -> str:
    """A hash of a random password with the current parameters (timing equalizer)."""
    return hash_password(secrets.token_urlsafe(32))


async def hash_password_async(password: str) -> str:
    return await asyncio.to_thread(hash_password, password)


async def verify_password_async(encoded: str | None, password: str) -> bool:
    """Verify in a thread; ``encoded = None`` (no account / no password) still costs the
    same time and returns False."""
    if encoded is None:
        await asyncio.to_thread(verify_password, dummy_hash(), password)
        return False
    return await asyncio.to_thread(verify_password, encoded, password)


def generate_temporary_password() -> str:
    """A random temporary password (CSPRNG), e.g. ``Kq7mZ-x3PaR-...``; satisfies the policy."""
    groups = [
        "".join(secrets.choice(TEMPORARY_ALPHABET) for _ in range(TEMPORARY_GROUP_LENGTH))
        for _ in range(TEMPORARY_GROUPS)
    ]
    return "-".join(groups)
