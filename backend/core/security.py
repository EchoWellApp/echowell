"""Credential primitives (TRD 12 SEC-010..SEC-024; FEAT-016).

Passwords: argon2id (argon2-cffi 23.x) with the SEC-010 parameters; plaintext is never stored or
logged. API keys: `ewk_` + `secrets.token_urlsafe(32)`, stored only as the SHA-256 hex digest
(SEC-020, SEC-021). JWT issuing and verification are added by FEAT-020.
"""

from __future__ import annotations

import hashlib
import secrets
from functools import lru_cache
from pathlib import Path

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from backend.core.errors import PasswordPolicyError

# SEC-010: time_cost 3, memory_cost 65536 KiB, parallelism 4, hash_len 32, salt_len 16.
_HASHER = PasswordHasher(
    time_cost=3, memory_cost=65536, parallelism=4, hash_len=32, salt_len=16, type=Type.ID
)
PASSWORD_MIN_LENGTH = 12
PASSWORD_MAX_LENGTH = 128
API_KEY_PREFIX = "ewk_"
COMMON_PASSWORDS_FILE = Path(__file__).with_name("common_passwords.txt")


def hash_password(plain: str) -> str:
    """argon2id hash in PHC form, `$argon2id$v=19$m=65536,t=3,p=4$…` (SEC-010)."""
    return _HASHER.hash(plain)


def verify_password(plain: str, password_hash: str) -> bool:
    """True when `plain` matches `password_hash`; never raises on a mismatch or bad hash."""
    try:
        return _HASHER.verify(password_hash, plain)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    """True when the stored hash uses parameters other than SEC-010 (SEC-011)."""
    return _HASHER.check_needs_rehash(password_hash)


# Hash of a random value, verified against when an e-mail is unknown so the response time does
# not reveal whether the account exists (SEC-013; consumed by FEAT-020).
# The plaintext was random and discarded; this is not a credential.
DUMMY_PASSWORD_HASH = "$argon2id$v=19$m=65536,t=3,p=4$E8gB9txZdj3H5eSB2tNKEg$FLeA1U+3l0JQVdfJiw/TC9mG4bUg522kDFLl6Ck0Q/E"  # noqa: E501, S105


def normalise_email(email: str) -> str:
    """Trimmed, lower-case e-mail (SEC-016)."""
    return email.strip().lower()


@lru_cache(maxsize=1)
def common_passwords() -> frozenset[str]:
    """The bundled top-10,000 list (SEC-012), compared case-insensitively."""
    lines = COMMON_PASSWORDS_FILE.read_text(encoding="utf-8").splitlines()
    return frozenset(
        line.strip().lower() for line in lines if line.strip() and not line.startswith("#")
    )


def validate_password(plain: str, email: str) -> None:
    """SEC-012: 12..128 characters, not the e-mail, not a common password; no composition rules."""
    if not PASSWORD_MIN_LENGTH <= len(plain) <= PASSWORD_MAX_LENGTH:
        raise PasswordPolicyError(
            f"password must be {PASSWORD_MIN_LENGTH} to {PASSWORD_MAX_LENGTH} characters"
        )
    if plain.strip().lower() == normalise_email(email):
        raise PasswordPolicyError("password must not be the e-mail address")
    if plain.lower() in common_passwords():
        raise PasswordPolicyError("password is in the list of common passwords")


def generate_api_key() -> str:
    """`ewk_` + 43 URL-safe characters (256 bits) (SEC-020)."""
    return API_KEY_PREFIX + secrets.token_urlsafe(32)


def hash_api_key(key: str) -> str:
    """SHA-256 lower-case hex digest stored in `api_keys.key_hash` (SEC-021, PGS-035)."""
    return hashlib.sha256(key.encode("utf-8")).hexdigest()
