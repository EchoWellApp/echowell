"""Seed, reset, bootstrap, withdrawal and purge commands (TRD 06 DB-056..DB-064; FEAT-017)."""

from __future__ import annotations

import pytest

from tests.integration.conftest import SEED_SECRETS, Cli

pytestmark = pytest.mark.integration

MASTER_TABLES = ("facilities", "residents", "devices", "device_assignments", "users", "api_keys")
PURGED_TABLES = (
    "scores", "cusum_state", "data_alerts", "staff_notes", "alerts", "baselines", "day_ledger",
    "processed_sessions", "epochs", "raw_sessions", "device_assignments", "residents",
)  # fmt: skip


def _counts(cli: Cli) -> tuple[int, ...]:
    return tuple(cli.scalar(f"SELECT count(*) FROM {t}") for t in MASTER_TABLES)  # noqa: S608


def _all_tables(cli: Cli) -> dict[str, int]:
    names = [r[0] for r in cli.rows("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")]
    return {n: cli.scalar(f"SELECT count(*) FROM {n}") for n in names}  # noqa: S608


@pytest.mark.req("DB-056", "DB-057", "D-71", "FEAT-017-AC-01", "FEAT-017-AC-02")
def test_seed_master_only_is_idempotent_and_hides_secrets(
    cli: Cli, caplog: pytest.LogCaptureFixture
) -> None:
    cli.env(**SEED_SECRETS)
    first = cli("seed", "test_v0_1", "--master-only")
    assert first.code == 0, first.err
    assert _counts(cli) == (1, 10, 10, 11, 3, 1)
    assert cli.scalar("SELECT active FROM devices WHERE device_code = 'D07'") is False
    second = cli("seed", "test_v0_1", "--master-only")
    assert second.code == 0, second.err
    assert _counts(cli) == (1, 10, 10, 11, 3, 1)
    output = first.out + first.err + second.out + second.err + caplog.text
    audit = "".join(r[0] for r in cli.rows("SELECT details::text FROM audit_logs"))
    for secret in SEED_SECRETS.values():
        assert secret not in output
        assert secret not in audit


@pytest.mark.req("DB-056", "D-71")
def test_seed_refuses_without_the_secrets(cli: Cli) -> None:
    run = cli("seed", "test_v0_1", "--master-only")
    assert run.code == 2
    assert "SEED_ADMIN_PASSWORD" in run.err
    assert cli.scalar("SELECT count(*) FROM users") == 0


@pytest.mark.req("DEP-070", "DB-059", "AC-DB-08", "FEAT-017-AC-03")
def test_production_refuses_seed_and_reset(cli: Cli) -> None:
    before = _all_tables(cli)
    cli.env(APP_ENV="production", **SEED_SECRETS)
    seed = cli("seed", "test_v0_1")
    assert seed.code == 2
    assert "seeding is not allowed in production" in seed.err
    assert cli("reset-test-db").code == 2
    assert _all_tables(cli) == before


@pytest.mark.req("DB-024", "AC-DB-08", "FEAT-017-AC-04")
def test_reset_refuses_the_production_profile(cli: Cli) -> None:
    cli.env(APP_ENV="local", PIPELINE_PROFILE="production")
    assert cli("reset-test-db").code == 2


@pytest.mark.req("DB-024", "DEP-071", "AC-DB-08", "FEAT-017-AC-05")
def test_reset_leaves_config_and_one_audit_row(cli: Cli) -> None:
    cli.env(**SEED_SECRETS)
    assert cli("seed", "test_v0_1", "--master-only").code == 0
    run = cli("reset-test-db")
    assert run.code == 0, run.err
    tables = _all_tables(cli)
    assert tables.pop("config_parameters") == 46
    assert tables.pop("audit_logs") == 1
    assert tables.pop("alembic_version") == 1
    assert set(tables.values()) == {0}
    assert cli.scalar("SELECT action FROM audit_logs") == "seed.reset"
    for _ in range(2):
        again = cli("seed", "test_v0_1", "--reset", "--master-only")
        assert again.code == 0, again.err
    assert _counts(cli) == (1, 10, 10, 11, 3, 1)


@pytest.mark.req("DB-062", "DME-009", "FEAT-017-AC-06")
def test_withdraw_resident(cli: Cli) -> None:
    assert cli("import-master-data", "--dir", "database/seeds/test_v0_1").code == 0
    before = cli.rows("SELECT * FROM device_assignments ORDER BY id")
    run = cli("withdraw-resident", "R08", "--on", "2026-10-20")
    assert run.code == 0, run.err
    status, on = cli.rows(
        "SELECT status, withdrawn_on::text FROM residents WHERE resident_code = 'R08'"
    )[0]
    assert (status, on) == ("withdrawn", "2026-10-20")
    assert cli.scalar("SELECT count(*) FROM audit_logs WHERE action = 'resident.withdrawn'") == 1
    assert cli.rows("SELECT * FROM device_assignments ORDER BY id") == before
    assert cli("withdraw-resident", "R08", "--on", "2026-10-21").code == 2


@pytest.mark.req("DB-064", "PGS-019", "FEAT-017-AC-07")
def test_purge_resident_removes_every_row_but_keeps_audit(cli: Cli) -> None:
    assert cli("import-master-data", "--dir", "database/seeds/test_v0_1").code == 0
    assert cli("purge-resident", "R08", "--confirm", "R08").code == 2  # not withdrawn yet
    assert cli("withdraw-resident", "R08", "--on", "2026-10-20").code == 0
    assert cli("purge-resident", "R08", "--confirm", "R09").code == 2
    audit_before = cli.scalar("SELECT count(*) FROM audit_logs")
    run = cli("purge-resident", "R08", "--confirm", "R08")
    assert run.code == 0, run.err
    assert cli.scalar("SELECT count(*) FROM residents WHERE resident_code = 'R08'") == 0
    assert cli.scalar("SELECT count(*) FROM residents") == 9
    assert cli.scalar("SELECT count(*) FROM device_assignments") == 10
    assert cli.scalar("SELECT count(*) FROM audit_logs") == audit_before + 1
    details = cli.scalar("SELECT details FROM audit_logs WHERE action = 'resident.purged'")
    assert set(details["row_counts"]) == {*PURGED_TABLES, "alert_reviews"}


@pytest.mark.req("DEP-072", "D-85", "FEAT-017-AC-08")
def test_bootstrap_is_idempotent(cli: Cli) -> None:
    assert cli("bootstrap").code == 0
    once = cli.rows("SELECT id, name, timezone FROM facilities")
    assert cli("bootstrap").code == 0
    assert cli.rows("SELECT id, name, timezone FROM facilities") == once
    assert len(once) == 1
