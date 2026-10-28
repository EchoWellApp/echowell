"""Repository round trips as `echowell_app` (TRD 06 §4.5; Database_ERD §5; FEAT-009..FEAT-012).

Each test writes through one repository, reads back through the same repository and checks the
rules the repository adds on top of the schema. All rows are rolled back.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import text

from backend.models import (
    Alert,
    AlertStatus,
    Baseline,
    CusumState,
    DataAlert,
    DataAlertKind,
    DayLedgerEntry,
    Epoch,
    IngestSource,
    NoteType,
    PipelineRunStatus,
    PipelineTrigger,
    ProcessedSession,
    ResidentCohort,
    ReviewOutcome,
    Score,
    UserRole,
)
from backend.repositories.alert_repository import AlertRepository
from backend.repositories.api_key_repository import ApiKeyRepository
from backend.repositories.baseline_repository import (
    BASELINE_KEYS,
    BaselineRepository,
    BaselineState,
)
from backend.repositories.config_repository import ConfigRepository
from backend.repositories.data_alert_repository import DataAlertRepository
from backend.repositories.day_ledger_repository import DayLedgerRepository
from backend.repositories.device_repository import DeviceRepository
from backend.repositories.epoch_repository import EpochRepository
from backend.repositories.facility_repository import FacilityRepository
from backend.repositories.ingest_repository import IngestRepository
from backend.repositories.pipeline_run_repository import PipelineRunRepository
from backend.repositories.processed_session_repository import ProcessedSessionRepository
from backend.repositories.reference_range_repository import ReferenceRangeRepository
from backend.repositories.resident_repository import ResidentRepository, ResidentTransitionError
from backend.repositories.score_repository import ScoreRepository
from backend.repositories.staff_note_repository import StaffNoteRepository
from backend.repositories.user_repository import UserRepository
from tests.integration.world import FEATURES, T0, World

pytestmark = pytest.mark.integration

HASH = "$argon2id$v=19$m=65536,t=3,p=4$c2FsdA$aGFzaA"


def _user(world: World, email: str = "c@example.com") -> uuid.UUID:
    return (
        UserRepository(world.session)
        .insert(email=email, display_name="C", password_hash=HASH, role=UserRole.CLINICIAN)
        .id
    )


def _processed_row(
    world: World, resident: str, device: str, epoch: uuid.UUID, n: int
) -> ProcessedSession:
    values = world.processed_values(
        resident, device, status="usable", epoch_id=epoch, baseline_ordinal=n,
        local_date=date(2026, 10, n), timestamp_utc=datetime(2026, 10, n, 13, tzinfo=UTC),
    )  # fmt: skip
    return ProcessedSession(**values)


@pytest.mark.req("DB-060", "DME-008", "DME-009", "FEAT-009-FR-05")
def test_resident_transitions(world: World) -> None:
    repo = ResidentRepository(world.session)
    r01 = repo.get_by_code("R01")
    assert r01 is not None
    with pytest.raises(ResidentTransitionError):
        repo.set_cohort_longitudinal(r01)  # already longitudinal
    facility = FacilityRepository(world.session).get_single()
    assert facility is not None
    new = repo.upsert_roster(
        facility_id=facility.id, resident_code="R11", sex=None,
        cohort=ResidentCohort.NEW_ADMISSION, enrolled_on=date(2026, 10, 20),
        admitted_on=date(2026, 10, 19),
    )  # fmt: skip
    assert [r.resident_code for r in repo.list_active(ResidentCohort.NEW_ADMISSION)] == ["R11"]
    repo.set_cohort_longitudinal(new)
    with pytest.raises(ResidentTransitionError):
        repo.upsert_roster(
            facility_id=facility.id, resident_code="R11", sex=None,
            cohort=ResidentCohort.NEW_ADMISSION, enrolled_on=date(2026, 10, 20), admitted_on=None,
        )  # fmt: skip
    repo.set_withdrawn(r01, date(2026, 10, 25))
    with pytest.raises(ResidentTransitionError):
        repo.set_withdrawn(r01, date(2026, 10, 26))
    assert "R01" not in [r.resident_code for r in repo.list_active()]
    assert len(repo.list_all()) == 11


@pytest.mark.req("DB-066", "FEAT-009-FR-06")
def test_device_assignment_queries(world: World) -> None:
    repo = DeviceRepository(world.session)
    d02 = repo.get_by_code("D02")
    assert d02 is not None
    on = date(2026, 10, 15)
    sharing = repo.residents_on_device(d02.id, on)
    assert sorted(r.resident_code for r in sharing) == ["R02", "R03"]
    current = repo.assignment_on(world.residents["R07"], on)
    assert current is not None
    assert current.device_id == world.devices["D07B"]
    assert len(repo.assignments_for_resident(world.residents["R07"])) == 2
    assert len(repo.assignments_for_device(d02.id)) == 2
    assert len(repo.list_all()) == 10


@pytest.mark.req("SEC-016", "SEC-021", "SEC-024", "FEAT-009-FR-07")
def test_users_and_api_keys(world: World) -> None:
    users = UserRepository(world.session)
    user_id = _user(world, "Clinician@Example.com")
    user = users.get_by_email("CLINICIAN@example.com")
    assert user is not None
    assert user.id == user_id
    users.update(user, role=UserRole.ADMIN, active=False)
    users.touch_login(user, T0)
    page, total = users.list_page(limit=10)
    assert (total, page[0].role, page[0].active, page[0].last_login_at) == (
        1, UserRole.ADMIN, False, T0,
    )  # fmt: skip
    keys = ApiKeyRepository(world.session)
    key = keys.insert(name="k1", key_hash="a" * 64, scopes=["ingest:write"], device_id=None)
    assert keys.get_active_by_hash("a" * 64) is not None
    keys.touch_last_used(key, T0)
    keys.revoke(key)
    assert keys.get_active_by_hash("a" * 64) is None
    same = keys.upsert_by_name(name="k1", key_hash="b" * 64, scopes=["pipeline:run"])
    assert (same.id, same.active, same.scopes) == (key.id, True, ["pipeline:run"])


@pytest.mark.req("PGS-024", "CFG-01")
def test_config_update(world: World) -> None:
    repo = ConfigRepository(world.session)
    assert repo.counts_by_profile() == {"production": 23, "test_v0_1": 23}
    user = _user(world)
    row = repo.update_value("test_v0_1", "baseline_n", 18, updated_by=user)
    assert (row.value, row.updated_by) == (18, user)
    with pytest.raises(KeyError):
        repo.update_value("test_v0_1", "no_such_key", 1)


@pytest.mark.req("FR-010", "FR-028", "FEAT-010-FR-05")
def test_ingest_batches_and_rejections(world: World) -> None:
    repo = IngestRepository(world.session)
    batch = repo.insert_batch(source=IngestSource.SEED)
    repo.update_counts(batch, record=3, accepted=2, rejected=1, duplicates=1)
    error = {"field": "mean_f0_hz", "code": "out_of_range", "message": "must be > 0"}
    repo.insert_rejection(
        raw_body={"mean_f0_hz": 0}, errors=[error], ingest_batch_id=batch.id, row_number=2
    )
    found = repo.get_batch(batch.id)
    assert found is not None
    assert (found.accepted_count, found.duplicate_count) == (2, 1)
    assert [r.row_number for r in repo.rejections_for_batch(batch.id)] == [2]
    with pytest.raises(ValueError, match="at least 1 item"):
        repo.insert_rejection(raw_body={}, errors=[])


@pytest.mark.req("DB-020", "FEAT-011-FR-12")
def test_pipeline_runs(world: World) -> None:
    repo = PipelineRunRepository(world.session)
    run = repo.get(world.run_id)  # type: ignore[arg-type]
    assert run is not None
    with pytest.raises(ValueError, match="succeeded or failed"):
        repo.finish(run, status=PipelineRunStatus.RUNNING, finished_at=T0)
    assert repo.latest_succeeded() is None
    repo.finish(
        run, status=PipelineRunStatus.SUCCEEDED,
        finished_at=datetime.now(UTC) + timedelta(minutes=1),
        warnings=[{"code": "w", "resident_code": None, "session_id": None, "detail": "d"}],
    )  # fmt: skip
    assert repo.latest_succeeded("test_v0_1") is run
    assert repo.latest_succeeded("production") is None
    rows, total = repo.list_page(trigger=PipelineTrigger.TEST, status=PipelineRunStatus.SUCCEEDED)
    assert (total, rows) == (1, [run])
    with pytest.raises(ValueError, match="does not match any of the expected tags"):
        repo.insert_running(
            trigger=PipelineTrigger.TEST, scope={"type": "some"}, config_profile="test_v0_1",
            config_snapshot={}, code_version="t", as_of=T0,
        )  # fmt: skip


@pytest.mark.req("DB-016", "DB-018", "PGS-031", "FEAT-011-AC-06", "TST-042")
def test_epochs_sessions_ledger_baselines_scores(world: World) -> None:
    epochs = EpochRepository(world.session)
    epoch_id = world.epoch("R01", "D01")
    assert epochs.current(world.residents["R01"]).id == epoch_id  # type: ignore[union-attr]
    assert epochs.get_by_number(world.residents["R01"], 1).id == epoch_id  # type: ignore[union-attr]
    assert set(epochs.current_for_residents(world.residents.values())) == {world.residents["R01"]}
    processed = ProcessedSessionRepository(world.session)
    rows = processed.insert_many(_processed_row(world, "R01", "D01", epoch_id, n) for n in (2, 3))
    bad = _processed_row(world, "R01", "D01", epoch_id, 4)
    bad.adjusted_features = {"loudness_dbfs": 1.0}
    with pytest.raises(ValueError, match="exactly the 19"):
        processed.insert_many([bad])
    assert [p.local_date.day for p in processed.by_epoch(epoch_id)] == [2, 3]
    assert processed.by_raw_session(rows[0].raw_session_id) is rows[0]
    assert processed.by_session_id(rows[0].session_id) == [rows[0]]
    ledger = DayLedgerRepository(world.session)
    ledger.insert_many(
        DayLedgerEntry(
            resident_id=world.residents["R01"], local_date=date(2026, 10, d), status=status,
            reason=reason, pipeline_run_id=world.run_id,
        )
        for d, status, reason in (
            (2, "checked_in", ""), (4, "missing_resident", "no record received"),
        )
    )  # fmt: skip
    window = (date(2026, 10, 1), date(2026, 10, 31))
    assert len(ledger.for_resident(world.residents["R01"], *window)) == 2
    assert [e.local_date.day for e in ledger.missing_days(world.residents["R01"], *window)] == [4]
    baselines = BaselineRepository(world.session)
    epoch = world.session.get(Epoch, epoch_id)
    assert baselines.state(epoch) is BaselineState.FORMING

    def baseline(key: str) -> Baseline:
        return Baseline(
            resident_id=world.residents["R01"], epoch_id=epoch_id, feature_key=key, n_sessions=16,
            first_session_id=rows[0].session_id, frozen_after_session_id=rows[1].session_id,
            median=1.0, mad=0.1, robust_spread=0.15, floor_applied=False, frozen_at=T0,
            pipeline_run_id=world.run_id,
        )  # fmt: skip

    with pytest.raises(ValueError, match="exactly the 20 rows"):
        baselines.insert_frozen(baseline(k) for k in BASELINE_KEYS[:19])
    baselines.insert_frozen(baseline(k) for k in BASELINE_KEYS)
    assert baselines.state(epoch) is BaselineState.FROZEN
    assert baselines.composite(epoch_id) is not None
    assert len(baselines.for_epoch(epoch_id)) == len(baselines.list_all()) == 20
    scores = ScoreRepository(world.session)
    z = {f"z_{k}": 0.1 for k in FEATURES}
    scores.insert_many(
        Score(
            processed_session_id=p.id, resident_id=world.residents["R01"], epoch_id=epoch_id,
            local_date=p.local_date, is_morning=True, z=z, composite_raw=0.1, composite_z=0.1,
            cusum_tally=0.0, alarm_state="off", pipeline_run_id=world.run_id,
        )
        for p in rows
    )  # fmt: skip
    assert [s.local_date.day for s in scores.series(epoch_id)] == [2, 3]
    assert scores.first_for_epoch(epoch_id).local_date.day == 2  # type: ignore[union-attr]
    state = scores.upsert_cusum_state(
        CusumState(
            epoch_id=epoch_id, resident_id=world.residents["R01"], current_tally=0.4,
            last_scored_session_id=rows[1].session_id, alarm_on=False,
            pipeline_run_id=world.run_id,
        )
    )  # fmt: skip
    assert scores.cusum_state(epoch_id) is state
    # Rebuild path: derived rows are deletable per resident (DB-016).
    assert scores.delete_cusum_for_resident(world.residents["R01"]) == 1
    assert scores.delete_for_resident(world.residents["R01"]) == 2
    assert ledger.delete_for_resident(world.residents["R01"]) == 2
    assert processed.delete_for_resident(world.residents["R01"]) == 2
    assert processed.by_resident(world.residents["R01"]) == []


@pytest.mark.req("PGS-029", "OQ-05", "D-37", "FEAT-012-FR-02")
def test_alerts_reviews_notes_and_data_alerts(world: World) -> None:
    epoch_id = world.epoch("R09", "D09")
    user = _user(world)
    alerts = AlertRepository(world.session)
    alert = alerts.insert(
        Alert(
            resident_id=world.residents["R09"], epoch_id=epoch_id, session_id="S1",
            triggered_at=T0, local_date=date(2026, 10, 21), cusum_value=5.0,
            pipeline_run_id=world.run_id,
        )
    )  # fmt: skip
    assert alerts.get_by_key(epoch_id, "S1") is alert
    assert alerts.non_closed_for_epoch(epoch_id) is alert
    alerts.snooze(alert, by=user, until=T0 + timedelta(hours=24))
    review = alerts.insert_review(
        alert_id=alert.id, reviewer_user_id=user, outcome=ReviewOutcome.KNOWN_CAUSE,
        explanations=["cold"], note="Synthetic",
    )  # fmt: skip
    alerts.set_acknowledged(alert, by=user, at=T0)
    assert [a.status for a in alerts.list_by_status()] == [AlertStatus.ACKNOWLEDGED]
    assert alerts.reviews(alert.id) == [review]
    with pytest.raises(ValueError, match="unknown closed_reason"):
        alerts.close(alert, reason="because", at=T0)
    alerts.close(alert, reason="admin", at=T0)
    with pytest.raises(ValueError, match="closed alert"):
        alerts.set_acknowledged(alert, by=user, at=T0)
    assert alerts.non_closed_for_epoch(epoch_id) is None
    notes = StaffNoteRepository(world.session)
    first = notes.insert(
        resident_id=world.residents["R09"], author_user_id=user,
        note_type=NoteType.OBSERVATION, body="First",
    )  # fmt: skip
    second = notes.insert(
        resident_id=world.residents["R09"], author_user_id=user,
        note_type=NoteType.OBSERVATION, body="Corrected", supersedes_id=first.id,
    )  # fmt: skip
    assert notes.current_for_resident(world.residents["R09"]) == [second]
    data_alerts = DataAlertRepository(world.session)
    silent = data_alerts.insert(
        DataAlert(
            kind=DataAlertKind.DEVICE_SILENT, device_id=world.devices["D02"], title="D02 silent",
            first_detected_at=T0, last_detected_at=T0, pipeline_run_id=world.run_id,
        )
    )  # fmt: skip
    found = data_alerts.open_for_subject(
        DataAlertKind.DEVICE_SILENT, device_id=world.devices["D02"]
    )
    assert found is silent
    assert data_alerts.list_open() == [silent]
    data_alerts.resolve(silent, at=T0)
    assert data_alerts.list_open() == []


@pytest.mark.req("FEAT-012-FR-05", "D-63")
def test_reference_ranges_latest_per_feature_and_sex(world: World) -> None:
    facility = FacilityRepository(world.session).get_single()
    assert facility is not None
    later = PipelineRunRepository(world.session).insert_running(
        trigger=PipelineTrigger.TEST, scope={"type": "all"}, config_profile="test_v0_1",
        config_snapshot={}, code_version="t", as_of=T0,
    )  # fmt: skip
    insert = text(
        "INSERT INTO facility_reference_ranges (facility_id, feature_key, sex, low, high, method, "
        "n_residents, computed_at, pipeline_run_id) "
        "VALUES (:f, 'mean_f0_hz', 'F', :low, 250, 'p5-p95', 5, :at, :run)"
    )
    world.session.execute(insert, {"f": facility.id, "low": 150, "at": T0, "run": world.run_id})
    world.session.execute(
        insert, {"f": facility.id, "low": 160, "at": T0 + timedelta(days=1), "run": later.id}
    )
    latest = ReferenceRangeRepository(world.session).latest(facility.id)
    assert [(r.feature_key, r.sex, r.low) for r in latest] == [("mean_f0_hz", "F", 160)]
