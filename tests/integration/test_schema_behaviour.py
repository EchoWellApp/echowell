"""Schema behaviour acceptance criteria AC-PGS-01..AC-PGS-15 (TRD 20 §9; FEAT-010..FEAT-012).

Each case runs in a savepoint of a rolled-back transaction; failures are asserted by SQLSTATE.
AC-PGS-10 lives in db/test_config_seed.py, AC-PGS-11 in db/test_migrations.py and
test_schema_reference.py, AC-PGS-12 and AC-PGS-13 in db/test_grants.py.
"""

from __future__ import annotations

from datetime import date, timedelta

import psycopg
import pytest
from sqlalchemy import Connection, insert, text

from backend.models import Alert, DataAlert, DayLedgerEntry, ProcessedSession, StaffNote
from tests.integration.db_support import PgUrls, libpq, outcome
from tests.integration.world import LATE, OTHER_SPEAKER, T0, World

pytestmark = pytest.mark.integration

PRIVILEGE = "42501"
APPEND_ONLY = "EW001"
CHECK = "23514"
UNIQUE = "23505"
EXCLUSION = "23P01"


def _processed(world: World, **values: object) -> str:
    return outcome(world.session, insert(ProcessedSession).values(**values))


@pytest.mark.req("AC-PGS-01", "DB-004", "FEAT-010-AC-01")
def test_ac_pgs_01_raw_sessions_update_fails_for_app(world: World) -> None:
    world.raw("R01", "D01")
    assert outcome(world.session, "UPDATE raw_sessions SET phrase_id = 'x'") == PRIVILEGE


@pytest.mark.req("AC-PGS-01", "DB-004", "FEAT-010-AC-01")
def test_ac_pgs_01_raw_sessions_update_fails_for_owner(owner_world: World) -> None:
    owner_world.raw("R01", "D01")
    session = owner_world.session
    assert outcome(session, "UPDATE raw_sessions SET phrase_id = 'x'") == APPEND_ONLY
    phrases = session.execute(text("SELECT DISTINCT phrase_id FROM raw_sessions")).scalars()
    assert phrases.all() == ["P1"]


@pytest.mark.req("AC-PGS-02", "PGS-018", "FEAT-010-AC-02")
@pytest.mark.parametrize("stmt", ["DELETE FROM raw_sessions", "TRUNCATE raw_sessions CASCADE"])
def test_ac_pgs_02_raw_sessions_delete_and_truncate_fail_for_app(world: World, stmt: str) -> None:
    world.raw("R01", "D01")
    assert outcome(world.session, stmt) == PRIVILEGE


@pytest.mark.req("AC-PGS-02", "PGS-018", "FEAT-010-AC-02")
@pytest.mark.parametrize("stmt", ["DELETE FROM raw_sessions", "TRUNCATE raw_sessions CASCADE"])
def test_ac_pgs_02_raw_sessions_delete_and_truncate_fail_for_owner(
    owner_world: World, stmt: str
) -> None:
    owner_world.raw("R01", "D01")
    assert outcome(owner_world.session, stmt) == APPEND_ONLY


@pytest.mark.req("AC-PGS-03", "FR-252", "FEAT-012-AC-01")
@pytest.mark.parametrize(
    "stmt",
    ["UPDATE audit_logs SET action = 'x.y'", "DELETE FROM audit_logs", "TRUNCATE audit_logs"],
)
def test_ac_pgs_03_audit_logs_are_append_only_for_app(app_conn: Connection, stmt: str) -> None:
    app_conn.execute(text("INSERT INTO audit_logs (actor_type, action) VALUES ('system', 'a.b')"))
    assert outcome(app_conn, stmt) == PRIVILEGE


@pytest.mark.req("AC-PGS-04", "PGS-012", "FEAT-011-AC-01")
def test_ac_pgs_04_reason_text_must_join_reasons(world: World) -> None:
    epoch = world.epoch("R01", "D01")
    reasons = ["quality flag poor", "noise above limit"]
    good = world.processed_values(
        "R01", "D01", status="set_aside", epoch_id=epoch, reasons=reasons,
        reason_text="quality flag poor; noise above limit",
    )  # fmt: skip
    assert _processed(world, **good) == "ok"
    bad = world.processed_values(
        "R01", "D01", status="set_aside", epoch_id=epoch, reasons=reasons,
        reason_text="noise above limit",
    )  # fmt: skip
    assert _processed(world, **bad) == CHECK


@pytest.mark.req("AC-PGS-05", "PGS-012", "FEAT-011-AC-02")
def test_ac_pgs_05_quarantined_needs_screen_detail(world: World) -> None:
    epoch = world.epoch("R01", "D01")
    common = {"status": "quarantined", "epoch_id": epoch, "reasons": [OTHER_SPEAKER]}
    good = world.processed_values(
        "R01", "D01", **common, reason_text=OTHER_SPEAKER, screen_detail="F0 z=5.12"
    )
    assert _processed(world, **good) == "ok"
    bad = world.processed_values("R01", "D01", **common, reason_text=OTHER_SPEAKER)
    assert _processed(world, **bad) == CHECK


@pytest.mark.req("AC-PGS-06", "D-57", "FEAT-011-AC-03")
def test_ac_pgs_06_duplicates_have_no_epoch_and_are_not_late(world: World) -> None:
    epoch = world.epoch("R01", "D01")
    reason = {
        "reasons": ["session_id already received"],
        "reason_text": "session_id already received",
    }
    good = world.processed_values("R01", "D01", status="duplicate", **reason)
    assert _processed(world, **good) == "ok"
    with_epoch = world.processed_values("R01", "D01", status="duplicate", epoch_id=epoch, **reason)
    assert _processed(world, **with_epoch) == CHECK
    late = world.processed_values("R01", "D01", status="duplicate", late_arrival=True, **reason)
    assert _processed(world, **late) == CHECK


@pytest.mark.req("D-57", "PGS-012", "FEAT-011-AC-05")
def test_late_usable_row_without_epoch_or_ordinal(world: World) -> None:
    late = world.processed_values(
        "R01", "D01", status="usable", late_arrival=True, reasons=[LATE], reason_text=LATE
    )
    assert _processed(world, **late) == "ok"
    epoch = world.epoch("R01", "D01")
    no_ordinal = world.processed_values("R01", "D01", status="usable", epoch_id=epoch)
    assert _processed(world, **no_ordinal) == CHECK  # an on-time usable row needs an ordinal
    on_time = world.processed_values(
        "R01", "D01", status="usable", epoch_id=epoch, baseline_ordinal=1, in_baseline=True
    )
    assert _processed(world, **on_time) == "ok"


@pytest.mark.req("AC-PGS-07", "FEAT-011-AC-04")
def test_ac_pgs_07_day_ledger_reasons(world: World) -> None:
    base = {"pipeline_run_id": world.run_id, "local_date": date(2026, 10, 12)}
    missing = insert(DayLedgerEntry).values(
        resident_id=world.residents["R01"], status="missing_resident", reason="no record", **base
    )
    assert outcome(world.session, missing) == CHECK
    gap = insert(DayLedgerEntry).values(
        resident_id=world.residents["R02"], status="missing_device_gap",
        device_id=world.devices["D02"],
        reason="all residents on shared device D02 have no record", **base,
    )  # fmt: skip
    assert outcome(world.session, gap) == "ok"


@pytest.mark.req("AC-PGS-08", "PGS-015", "FEAT-009-AC-02")
def test_ac_pgs_08_one_device_per_resident_per_day(world: World) -> None:
    shared = world.session.execute(
        text(
            "SELECT r.resident_code FROM device_assignments a "
            "JOIN residents r ON r.id = a.resident_id JOIN devices d ON d.id = a.device_id "
            "WHERE d.device_code = 'D02' AND a.valid_to IS NULL ORDER BY 1"
        )
    ).scalars()
    assert shared.all() == ["R02", "R03"]
    overlap = text(
        "INSERT INTO device_assignments (resident_id, device_id, valid_from) "
        "VALUES (:resident, :device, DATE '2026-10-20')"
    )
    params = {"resident": world.residents["R07"], "device": world.devices["D09"]}
    assert outcome(world.session, overlap, params) == EXCLUSION


@pytest.mark.req("AC-PGS-09", "PGS-019", "FEAT-012-AC-02")
def test_ac_pgs_09_purge_setting_allows_delete_only(owner_world: World) -> None:
    session = owner_world.session
    owner_world.raw("R01", "D01")
    session.execute(text("INSERT INTO audit_logs (actor_type, action) VALUES ('system', 'a.b')"))
    session.execute(text("SET LOCAL echowell.allow_purge = 'on'"))
    assert outcome(session, "DELETE FROM audit_logs") == "ok"
    assert session.execute(text("SELECT count(*) FROM audit_logs")).scalar_one() == 0
    assert outcome(session, "UPDATE raw_sessions SET phrase_id = 'x'") == APPEND_ONLY


@pytest.mark.req("AC-PGS-14", "PGS-040", "SEC-114", "FEAT-012-AC-03")
def test_ac_pgs_14_ground_truth_only_through_readonly(
    app_conn: Connection, readonly_conn: Connection
) -> None:
    assert outcome(app_conn, "SELECT count(*) FROM evaluation_ground_truth") == PRIVILEGE
    assert outcome(app_conn, "SET ROLE echowell_readonly") == PRIVILEGE
    assert outcome(readonly_conn, "SELECT count(*) FROM evaluation_ground_truth") == "ok"


@pytest.mark.req("AC-PGS-14", "PGS-040", "FEAT-012-AC-03")
def test_ac_pgs_14_readonly_sees_ten_loaded_rows(fresh_db: PgUrls) -> None:
    # The loader script is FEAT-057; ten committed rows stand in for its output here.
    with psycopg.connect(libpq(fresh_db.migrator)) as conn:
        conn.execute("SET ROLE echowell_migrator")
        for n in range(1, 11):
            onset = None if n % 2 else date(2026, 10, 20)
            conn.execute(
                "INSERT INTO evaluation_ground_truth "
                "(resident_code, planted_change, true_onset_date, source_file) VALUES (%s, %s, %s, %s)",
                (f"R{n:02d}", "None" if onset is None else "gradual", onset, "fixture.csv"),
            )
    with psycopg.connect(libpq(fresh_db.readonly)) as conn:
        row = conn.execute("SELECT count(*) FROM evaluation_ground_truth").fetchone()
    assert row == (10,)


@pytest.mark.req("AC-PGS-15", "PGS-039", "FEAT-012-AC-04")
def test_ac_pgs_15_data_alert_rules_and_no_alert_delete(world: World) -> None:
    def silent(**values: object) -> str:
        stmt = insert(DataAlert).values(
            kind="device_silent", device_id=world.devices["D02"], title="Device D02 silent",
            first_detected_at=T0, last_detected_at=T0, **values,
        )  # fmt: skip
        return outcome(world.session, stmt)

    assert silent(pipeline_run_id=world.run_id) == "ok"
    assert silent(pipeline_run_id=world.run_id) == UNIQUE
    assert silent() == CHECK
    assert outcome(world.session, "DELETE FROM alerts") == PRIVILEGE


def _alert(world: World, epoch: object, session_id: str, **values: object) -> str:
    stmt = insert(Alert).values(
        resident_id=world.residents["R09"], epoch_id=epoch, session_id=session_id,
        triggered_at=T0, local_date=date(2026, 10, 21), cusum_value=5.2,
        pipeline_run_id=world.run_id, **values,
    )  # fmt: skip
    return outcome(world.session, stmt)


@pytest.mark.req("PGS-029", "FEAT-012-AC-05")
def test_one_non_closed_alert_per_epoch(world: World) -> None:
    epoch = world.epoch("R09", "D09")
    assert _alert(world, epoch, "S1") == "ok"
    assert _alert(world, epoch, "S2") == UNIQUE
    world.session.execute(
        text("UPDATE alerts SET status = 'closed', closed_reason = 'admin', closed_at = now()")
    )
    assert _alert(world, epoch, "S2") == "ok"


@pytest.mark.req("PGS-043", "FEAT-012-AC-06")
def test_snooze_needs_both_columns(world: World) -> None:
    epoch = world.epoch("R09", "D09")
    assert _alert(world, epoch, "S1", snoozed_until=T0 + timedelta(days=1)) == CHECK


@pytest.mark.req("SEC-113", "PGS-036", "PGS-042", "FEAT-012-AC-07")
def test_reviews_and_notes_are_append_only(world: World) -> None:
    session = world.session
    user = session.execute(
        text(
            "INSERT INTO users (email, display_name, password_hash, role) "
            "VALUES ('c@example.com', 'C', '$argon2id$x', 'clinician') RETURNING id"
        )
    ).scalar_one()
    epoch = world.epoch("R09", "D09")
    assert _alert(world, epoch, "S1") == "ok"
    alert = session.execute(text("SELECT id FROM alerts")).scalar_one()
    session.execute(
        text(
            "INSERT INTO alert_reviews (alert_id, reviewer_user_id, outcome) "
            "VALUES (:a, :u, 'no_concern')"
        ),
        {"a": alert, "u": user},
    )

    def note(**values: object) -> str:
        stmt = insert(StaffNote).values(
            resident_id=world.residents["R09"], author_user_id=user, note_type="observation",
            body="Synthetic note", **values,
        )  # fmt: skip
        return outcome(session, stmt)

    assert note() == "ok"
    first = session.execute(text("SELECT id FROM staff_notes")).scalar_one()
    assert note(supersedes_id=first) == "ok"
    assert note(supersedes_id=first) == UNIQUE
    for table in ("alert_reviews", "staff_notes"):
        assert outcome(session, f"UPDATE {table} SET created_at = now()") == PRIVILEGE
        assert outcome(session, f"DELETE FROM {table}") == PRIVILEGE


@pytest.mark.req("PGS-044", "FEAT-012-AC-08")
@pytest.mark.parametrize(
    ("action", "expected"),
    [
        ("auth.logout", "ok"),
        ("auth.login.succeeded", "ok"),
        ("Auth.Login", CHECK),
        ("login", CHECK),
    ],
)
def test_audit_action_format(app_conn: Connection, action: str, expected: str) -> None:
    stmt = "INSERT INTO audit_logs (actor_type, action) VALUES ('system', :action)"
    assert outcome(app_conn, stmt, {"action": action}) == expected


@pytest.mark.req("PGS-030", "FEAT-011-AC-09")
def test_one_open_epoch_per_resident(world: World) -> None:
    world.epoch("R01", "D01", number=1)
    stmt = text(
        "INSERT INTO epochs (resident_id, epoch_number, device_id, device_firmware_version, "
        "extraction_software_version, started_at, pipeline_run_id) "
        "VALUES (:r, 2, :d, 'fw', 'ext', now(), :run)"
    )
    params = {"r": world.residents["R01"], "d": world.devices["D01"], "run": world.run_id}
    assert outcome(world.session, stmt, params) == UNIQUE
