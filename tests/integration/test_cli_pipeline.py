"""Pipeline operator commands and the full test_v0_1 seed (TRD 15 §4.8; TRD 07 ANL-031, ANL-032;
TRD 06 DB-058; FEAT-055). Runs `backend.cli.main` in-process against a throwaway database."""

from __future__ import annotations

import pytest

from tests.integration.conftest import SEED_SECRETS, Cli

pytestmark = pytest.mark.integration

SRC05_COUNTS = {"arrivals": 283, "usable": 267, "set_aside": 12, "quarantined": 2,
                "duplicate": 2, "missing_resident": 17, "missing_device_gap": 2,
                "late_arrival": 0, "scored": 98, "alerts_opened": 2,
                "excluded_after_as_of": 0, "residents": 10}  # fmt: skip


DERIVED = ("epochs", "processed_sessions", "baselines", "scores", "cusum_state", "day_ledger",
           "alerts", "data_alerts")  # fmt: skip
VOLATILE = {"id", "created_at", "updated_at", "pipeline_run_id", "epoch_id",
            "processed_session_id", "last_detected_at"}  # fmt: skip


def _derived(cli: Cli) -> dict[str, list[tuple[str, ...]]]:
    tables = {}
    for table in DERIVED:
        rows = cli.rows(f"SELECT * FROM {table}")  # noqa: S608
        tables[table] = sorted(
            tuple(str(v) for k, v in row._mapping.items() if k not in VOLATILE) for row in rows
        )
    return tables


def _seed(cli: Cli) -> None:
    cli.env(**SEED_SECRETS)
    run = cli("seed", "test_v0_1")
    assert run.code == 0, run.err


@pytest.mark.req("DB-058", "TDV-061", "FEAT-055-AC-01", "FEAT-055-FR-06", "FEAT-055-FR-07",
                 "FEAT-053-AC-01", "FEAT-053-AC-05")  # fmt: skip
def test_full_seed_ingests_src05_and_runs(cli: Cli) -> None:
    _seed(cli)
    batch = cli.rows("SELECT source, record_count, accepted_count, duplicate_count, "
                     "pipeline_run_id FROM ingest_batches")  # fmt: skip
    assert [tuple(b[:4]) for b in batch] == [("seed", 283, 283, 2)]
    assert batch[0].pipeline_run_id is None  # the seed runs the pipeline itself
    runs = cli.rows("SELECT trigger, status, as_of, counts FROM pipeline_runs")
    assert [(r.trigger, r.status) for r in runs] == [("manual", "succeeded")]
    assert runs[0].as_of.isoformat() == "2026-10-30T20:00:00+00:00"
    assert runs[0].counts == SRC05_COUNTS
    assert cli.scalar("SELECT count(*) FROM baselines") == 180
    assert cli.scalar("SELECT count(*) FROM alerts WHERE status = 'open'") == 2
    assert cli.scalar("SELECT count(*) FROM data_alerts WHERE status = 'open'") == 4


@pytest.mark.req("FEAT-055-FR-01", "TRD 15 §4.8")
def test_run_pipeline_command(cli: Cli) -> None:
    _seed(cli)
    run = cli("run-pipeline", "--scope", "R01,R02", "--as-of", "2026-10-30T15:00:00-05:00")
    assert run.code == 0, run.err
    latest = cli.rows("SELECT trigger, status, scope FROM pipeline_runs ORDER BY started_at "
                      "DESC LIMIT 1")[0]  # fmt: skip
    assert (latest.trigger, latest.status) == ("manual", "succeeded")
    assert latest.scope == {"type": "residents", "resident_codes": ["R01", "R02"]}
    assert cli("run-pipeline", "--as-of", "2026-10-30T15:00:00").code == 2  # no offset


@pytest.mark.req("ANL-032", "ANL-033", "AC-ANL-09", "FEAT-055-FR-04")
def test_rebuild_reproduces_identical_derived_tables(cli: Cli) -> None:
    """With an unchanged configuration, a rebuild re-derives every frozen baseline from
    `raw_sessions` and every derived table comes back identical (roadmap §5.5 exit criterion)."""
    _seed(cli)
    before = _derived(cli)
    rebuilt = cli("rebuild", "--profile", "test_v0_1", "--confirm", "REBUILD")
    assert rebuilt.code == 0, rebuilt.err
    assert cli.scalar("SELECT count(*) FROM pipeline_runs WHERE status = 'succeeded'") == 2
    assert _derived(cli) == before


@pytest.mark.req("ANL-032", "D-56", "D-69", "FEAT-055-AC-02", "FEAT-055-AC-03", "FEAT-055-FR-02",
                 "FEAT-055-FR-03", "FEAT-055-FR-04", "FEAT-055-FR-05")  # fmt: skip
def test_set_config_then_rebuild(cli: Cli) -> None:
    _seed(cli)
    refused = cli("set-config", "--profile", "test_v0_1", "--key", "cusum_h", "--value", "0",
                  "--reason", "test")  # fmt: skip
    assert refused.code == 2
    assert cli.scalar("SELECT value FROM config_parameters WHERE profile = 'test_v0_1' "
                      "AND key = 'cusum_h'") == 5.0  # fmt: skip
    assert cli("set-config", "--profile", "test_v0_1", "--key", "nope", "--value", "1",
               "--reason", "test").code == 2  # fmt: skip
    changed = cli("set-config", "--profile", "test_v0_1", "--key", "cusum_h", "--value", "4.0",
                  "--reason", "calibration test")  # fmt: skip
    assert changed.code == 0, changed.err
    assert "Algorithm key changed" in changed.err
    audit = cli.rows("SELECT entity_id, details FROM audit_logs WHERE action = 'config.changed'")
    assert audit[0].entity_id == "test_v0_1.cusum_h"
    assert {k: audit[0].details[k] for k in ("old", "new", "reason")} == {
        "old": 5.0, "new": 4.0, "reason": "calibration test"}  # fmt: skip
    blocked = cli("run-pipeline", "--as-of", "2026-10-30T15:00:00-05:00")
    assert blocked.code == 1
    last = cli.rows("SELECT status, error_message, warnings FROM pipeline_runs "
                    "ORDER BY started_at DESC LIMIT 1")[0]  # fmt: skip
    assert (last.status, last.error_message) == ("failed", "configuration changed; run the "
                                                 "rebuild command")  # fmt: skip
    assert [w["code"] for w in last.warnings] == ["config_changed_requires_rebuild"]
    assert cli("rebuild", "--profile", "test_v0_1", "--confirm", "yes").code == 2
    rebuilt = cli("rebuild", "--profile", "test_v0_1", "--confirm", "REBUILD")
    assert rebuilt.code == 0, rebuilt.err
    assert cli.scalar("SELECT count(*) FROM baselines") == 180
    rebuild_audit = cli.rows("SELECT details FROM audit_logs WHERE action = 'pipeline.rebuild'")
    assert (
        rebuild_audit[0].details["old_config_hash"] != rebuild_audit[0].details["new_config_hash"]
    )
    operational = cli("set-config", "--profile", "test_v0_1", "--key", "alert_snooze_hours",
                      "--value", "48", "--reason", "test")  # fmt: skip
    assert operational.code == 0
    assert "Algorithm key changed" not in operational.err
    assert cli("run-pipeline", "--as-of", "2026-10-30T15:00:00-05:00").code == 0
