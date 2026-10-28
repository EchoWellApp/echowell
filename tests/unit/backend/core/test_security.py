"""Credential primitives (TRD 12 SEC-010..SEC-024; FEAT-016)."""

from __future__ import annotations

import hashlib
import re

import pytest

from backend.core import security
from backend.core.errors import PasswordPolicyError

pytestmark = pytest.mark.unit


@pytest.mark.req("SEC-010", "TST-032", "FEAT-016-AC-01")
def test_hash_and_verify() -> None:
    hashed = security.hash_password("correct horse battery")
    assert hashed.startswith("$argon2id$v=19$m=65536,t=3,p=4$")
    assert security.verify_password("correct horse battery", hashed)
    assert not security.verify_password("correct horse batterY", hashed)
    assert not security.verify_password("x", "not-a-hash")
    assert not security.needs_rehash(hashed)


@pytest.mark.req("SEC-011")
def test_dummy_hash_is_a_real_argon2id_hash() -> None:
    assert security.DUMMY_PASSWORD_HASH.startswith("$argon2id$v=19$m=65536,t=3,p=4$")
    assert not security.verify_password("anything", security.DUMMY_PASSWORD_HASH)


@pytest.mark.req("SEC-012", "FEAT-016-AC-02")
@pytest.mark.parametrize(
    "password",
    ["a" * 11, "b" * 129, "Admin@Example.COM", "unbelievable"],
)
def test_validate_password_rejects(password: str) -> None:
    with pytest.raises(PasswordPolicyError):
        security.validate_password(password, "admin@example.com")


@pytest.mark.req("SEC-012", "FEAT-016-AC-02")
def test_validate_password_accepts_a_long_unlisted_password() -> None:
    security.validate_password("tangerine-owl", "admin@example.com")
    security.validate_password("x" * 128, "admin@example.com")


@pytest.mark.req("SEC-012")
def test_common_password_list_is_bundled() -> None:
    words = security.common_passwords()
    assert len(words) >= 9_000
    assert "unbelievable" in words
    assert not any(w.startswith("#") for w in words)


@pytest.mark.req("SEC-020", "SEC-021", "FEAT-016-AC-03")
def test_api_key_format_and_hash() -> None:
    key = security.generate_api_key()
    assert re.fullmatch(r"ewk_[A-Za-z0-9_-]{43}", key)
    assert security.generate_api_key() != key
    assert security.hash_api_key(key) == hashlib.sha256(key.encode()).hexdigest()
    assert re.fullmatch(r"[0-9a-f]{64}", security.hash_api_key(key))


@pytest.mark.req("SEC-016")
def test_email_normalisation() -> None:
    assert security.normalise_email("  Admin@Example.COM ") == "admin@example.com"
