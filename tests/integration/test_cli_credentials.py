"""Credential CLI commands against PostgreSQL (TRD 12 SEC-016..SEC-024; FEAT-016)."""

from __future__ import annotations

import hashlib
import re

import pytest

from tests.integration.conftest import Cli

pytestmark = pytest.mark.integration

KEY = re.compile(r"^ewk_[A-Za-z0-9_-]{43}$")


@pytest.mark.req("SEC-016", "SEC-017", "SEC-103", "FEAT-016-AC-06")
def test_create_user_normalises_email_and_audits(cli: Cli) -> None:
    run = cli(
        "create-user", "--email", "Admin@Example.com", "--display-name", "Admin",
        "--role", "admin", "--password-stdin", stdin="a-valid-password-123\n",
    )  # fmt: skip
    assert run.code == 0, run.err
    email, password_hash = cli.rows("SELECT email, password_hash FROM users")[0]
    assert email == "admin@example.com"
    assert password_hash.startswith("$argon2id$v=19$m=65536,t=3,p=4$")
    audit = cli.rows("SELECT actor_type, details FROM audit_logs WHERE action = 'user.created'")
    assert len(audit) == 1
    assert audit[0][0] == "system"
    assert audit[0][1]["role"] == "admin"
    assert audit[0][1]["operator"]
    assert "a-valid-password-123" not in run.out + run.err


@pytest.mark.req("SEC-012", "FEAT-016-FR-03")
def test_create_user_refuses_a_weak_password(cli: Cli) -> None:
    run = cli(
        "create-user", "--email", "a@example.com", "--display-name", "A", "--role", "admin",
        "--password-stdin", stdin="short\n",
    )  # fmt: skip
    assert run.code == 2
    assert cli.scalar("SELECT count(*) FROM users") == 0


@pytest.mark.req("SEC-020", "SEC-021", "FR-226", "FEAT-016-AC-03")
def test_create_api_key_prints_the_key_once_and_stores_its_hash(
    cli: Cli, caplog: pytest.LogCaptureFixture
) -> None:
    run = cli("create-api-key", "--name", "t1")
    assert run.code == 0, run.err
    key = run.out.strip()
    assert KEY.match(key)
    scopes, key_hash = cli.rows("SELECT scopes, key_hash FROM api_keys WHERE name = 't1'")[0]
    assert scopes == ["ingest:write"]
    assert key_hash == hashlib.sha256(key.encode()).hexdigest()
    assert key not in run.err
    assert key not in caplog.text
    details = cli.scalar("SELECT details::text FROM audit_logs WHERE action = 'api_key.created'")
    assert key not in details


@pytest.mark.req("SEC-020", "SEC-022", "SEC-023", "FEAT-016-AC-04")
def test_create_api_key_with_scopes_and_device(cli: Cli) -> None:
    assert cli("import-master-data", "--dir", "database/seeds/test_v0_1").code == 0
    run = cli(
        "create-api-key", "--name", "t2", "--scope", "pipeline:run", "--scope", "ingest:write",
        "--device", "D01",
    )  # fmt: skip
    assert run.code == 0, run.err
    scopes, device = cli.rows(
        "SELECT k.scopes, d.device_code FROM api_keys k JOIN devices d ON d.id = k.device_id"
    )[0]
    assert sorted(scopes) == ["ingest:write", "pipeline:run"]
    assert device == "D01"
    refused = cli("create-api-key", "--name", "t3", "--scope", "admin")
    assert refused.code == 2
    assert cli.scalar("SELECT count(*) FROM api_keys WHERE name = 't3'") == 0


@pytest.mark.req("SEC-024", "SEC-103", "FEAT-016-AC-05")
def test_revoke_api_key(cli: Cli) -> None:
    assert cli("create-api-key", "--name", "t1").code == 0
    run = cli("revoke-api-key", "--name", "t1")
    assert run.code == 0, run.err
    assert cli.scalar("SELECT active FROM api_keys WHERE name = 't1'") is False
    audit = cli.rows("SELECT actor_type, details FROM audit_logs WHERE action = 'api_key.revoked'")
    assert len(audit) == 1
    assert audit[0][0] == "system"
    assert audit[0][1]["operator"]
    assert cli("revoke-api-key", "--name", "t1").code == 2
