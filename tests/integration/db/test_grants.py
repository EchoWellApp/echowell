"""Grants, credential columns and FK delete rules (TRD 20 §4.8; PGS-021, PGS-022; TST-041)."""

from __future__ import annotations

import pytest
from sqlalchemy import Connection, insert, text

from backend.models import COMPOSITE_Z_KEYS, ProcessedSession, Score
from tests.integration.db_support import outcome
from tests.integration.world import World

pytestmark = pytest.mark.integration

APPEND_ONLY = (
    "raw_sessions",
    "audit_logs",
    "ingest_rejections",
    "staff_notes",
    "baselines",
    "alert_reviews",
)
NO_DELETE = (
    "facilities", "residents", "devices", "device_assignments", "users", "api_keys",
    "ingest_batches", "pipeline_runs", "config_parameters", "alerts", "data_alerts",
)  # fmt: skip
DERIVED = (
    "epochs", "processed_sessions", "day_ledger", "scores", "cusum_state",
    "facility_reference_ranges",
)  # fmt: skip
ALL_PRIVILEGES = ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE")


def _privileges(conn: Connection, role: str, table: str) -> set[str]:
    return {
        p
        for p in ALL_PRIVILEGES
        if conn.execute(
            text("SELECT has_table_privilege(:role, :table, :p)"),
            {"role": role, "table": table, "p": p},
        ).scalar_one()
    }


@pytest.mark.req("PGS-021", "PGS-040", "TST-041", "FEAT-010-AC-03", "FEAT-011-AC-08")
def test_app_privileges_are_exactly_section_4_8(app_conn: Connection) -> None:
    for table in APPEND_ONLY:
        assert _privileges(app_conn, "echowell_app", table) == {"SELECT", "INSERT"}, table
    for table in NO_DELETE:
        assert _privileges(app_conn, "echowell_app", table) == {"SELECT", "INSERT", "UPDATE"}, table
    for table in DERIVED:
        expected = {"SELECT", "INSERT", "UPDATE", "DELETE"}
        assert _privileges(app_conn, "echowell_app", table) == expected, table
    assert _privileges(app_conn, "echowell_app", "evaluation_ground_truth") == set()


@pytest.mark.req("PGS-021", "FEAT-012-FR-08")
def test_readonly_reads_everything_but_credentials(app_conn: Connection) -> None:
    tables = app_conn.execute(
        text(
            "SELECT tablename FROM pg_tables "
            "WHERE schemaname = 'public' AND tablename <> 'alembic_version'"
        )
    ).scalars()
    for table in tables:
        if table in ("users", "api_keys"):
            continue
        assert _privileges(app_conn, "echowell_readonly", table) == {"SELECT"}, table
    for table, column in (("users", "password_hash"), ("api_keys", "key_hash")):
        allowed = app_conn.execute(
            text("SELECT has_column_privilege('echowell_readonly', :t, :c, 'SELECT')"),
            {"t": table, "c": column},
        ).scalar_one()
        assert allowed is False


@pytest.mark.req("AC-PGS-12", "PGS-021", "FEAT-009-AC-06")
def test_ac_pgs_12_readonly_cannot_read_password_hash(
    readonly_conn: Connection, app_conn: Connection
) -> None:
    assert outcome(readonly_conn, "SELECT password_hash FROM users") == "42501"
    assert outcome(readonly_conn, "SELECT email FROM users") == "ok"
    assert outcome(readonly_conn, "SELECT key_hash FROM api_keys") == "42501"
    assert outcome(app_conn, "DELETE FROM residents") == "42501"


@pytest.mark.req("AC-PGS-13", "PGS-022", "DB-010")
def test_ac_pgs_13_every_fk_restricts_except_scores(app_conn: Connection) -> None:
    rows = app_conn.execute(
        text("SELECT conname, confdeltype FROM pg_constraint WHERE contype = 'f' ORDER BY 1")
    ).all()
    assert len(rows) > 40
    rules = dict(rows)
    assert rules.pop("scores_processed_session_id_fkey") == "c"
    assert set(rules.values()) == {"r"}


@pytest.mark.req("PGS-032", "TST-041", "FEAT-011-AC-07")
@pytest.mark.parametrize(("drop", "tally"), [(None, 0.0), ("z_voiced_fraction", 0.0), (None, -0.1)])
def test_scores_z_and_tally_checks(world: World, drop: str | None, tally: float) -> None:
    epoch = world.epoch("R09", "D09")
    values = world.processed_values(
        "R09", "D09", status="usable", epoch_id=epoch, baseline_ordinal=17
    )
    processed = world.session.execute(
        insert(ProcessedSession).values(**values).returning(ProcessedSession.id)
    ).scalar_one()
    z = {key: 0.5 for key in COMPOSITE_Z_KEYS if key != drop}
    stmt = insert(Score).values(
        processed_session_id=processed, resident_id=world.residents["R09"], epoch_id=epoch,
        local_date=values["local_date"], is_morning=True, z=z, composite_raw=0.1,
        composite_z=0.2, cusum_tally=tally, alarm_state="off",
        pipeline_run_id=world.run_id,
    )  # fmt: skip
    expected = "ok" if drop is None and tally >= 0 else "23514"
    assert outcome(world.session, stmt) == expected
