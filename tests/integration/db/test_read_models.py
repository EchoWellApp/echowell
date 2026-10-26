"""Read-model derivations on hand-built rows (TRD 06 DB-041..DB-045, DB-065, DB-066; DME-012;
FEAT-014).

The FEAT-014 acceptance values are stated on the full test_v0_1 seed as of 2026-10-30, which
FEAT-055 loads; until then each derivation is checked here on a small hand-built scenario that
follows the same rules (and reuses the seed roster). The seed-valued assertions are in
`test_seed_values_*`, skipped until the seed exists (FEAT-055).
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import insert, select, text, update

from backend.models import (
    Alert,
    Baseline,
    DayLedgerEntry,
    Epoch,
    ProcessedSession,
    Resident,
    Score,
)
from backend.repositories import read_models as rm
from backend.repositories.epoch_repository import EpochRepository
from tests.integration.db_support import ROOT
from tests.integration.world import FEATURES, World

pytestmark = pytest.mark.integration

TZ = "America/Chicago"
AS_OF = date(2026, 10, 30)
SEED_SESSIONS = ROOT / "database" / "seeds" / "test_v0_1" / "sessions.csv"


def _day(n: int) -> date:
    return date(2026, 10, 1) + timedelta(days=n - 1)


def _at(day: date, hour: int = 13) -> datetime:
    return datetime(day.year, day.month, day.day, hour, tzinfo=UTC)


def _processed(
    world: World, resident: str, device: str, day: date, status: str, epoch: uuid.UUID | None,
    *, ordinal: int | None = None, hour: int = 13,
) -> tuple[uuid.UUID, str]:  # fmt: skip
    reasons = {
        "usable": [],
        "set_aside": ["noise above limit"],
        "quarantined": ["possible other speaker (F0 z=5.12; composite features with |z|>=3: 3)"],
        "duplicate": ["session_id already received"],
    }[status]
    values = world.processed_values(
        resident, device, status=status, reasons=reasons, reason_text="; ".join(reasons),
        timestamp_utc=_at(day, hour), local_date=day,
        epoch_id=None if status == "duplicate" else epoch,
        baseline_ordinal=ordinal if status == "usable" else None,
        screen_detail="F0 z=5.12" if status == "quarantined" else None,
    )  # fmt: skip
    row = world.session.execute(
        insert(ProcessedSession).values(**values).returning(ProcessedSession.id)
    ).scalar_one()
    return row, values["session_id"]


def _ledger(world: World, resident: str, day: date, status: str, device: str | None = None) -> None:
    reason = {
        "checked_in": "",
        "missing_resident": "no record received",
        "missing_device_gap": f"all residents on shared device {device} have no record",
    }[status]
    world.session.execute(
        insert(DayLedgerEntry).values(
            resident_id=world.residents[resident], local_date=day, status=status,
            device_id=world.devices[device] if device else None, reason=reason,
            pipeline_run_id=world.run_id,
        )
    )  # fmt: skip


def _resident(world: World, code: str) -> Resident:
    found = world.session.scalars(select(Resident).where(Resident.resident_code == code)).one()
    return found


def _freeze(world: World, resident: str, epoch: uuid.UUID, first: str, last: str, n: int) -> None:
    for key in (*FEATURES, "composite"):
        world.session.add(
            Baseline(
                resident_id=world.residents[resident],
                epoch_id=epoch,
                feature_key=key,
                n_sessions=n,
                first_session_id=first,
                frozen_after_session_id=last,
                median=1.0,
                mad=0.1,
                robust_spread=0.15,
                floor_applied=False,
                frozen_at=_at(_day(16)),
                pipeline_run_id=world.run_id,
            )  # fmt: skip
        )
    world.session.flush()


def _score(world: World, resident: str, epoch: uuid.UUID, processed: uuid.UUID, day: date) -> None:
    world.session.add(
        Score(
            processed_session_id=processed,
            resident_id=world.residents[resident],
            epoch_id=epoch,
            local_date=day,
            is_morning=True,
            z={f"z_{k}": 0.0 for k in FEATURES},
            composite_raw=0.0,
            composite_z=0.0,
            cusum_tally=0.0,
            alarm_state="off",
            pipeline_run_id=world.run_id,
        )  # fmt: skip
    )
    world.session.flush()


@pytest.mark.req("DB-041", "AC-DB-05", "FR-135", "FEAT-014-AC-01")
def test_activity_counts_exclude_duplicates_and_count_missed(world: World) -> None:
    epoch = world.epoch("R02", "D02")
    _processed(world, "R02", "D02", _day(2), "usable", epoch, ordinal=1)
    _processed(world, "R02", "D02", _day(3), "usable", epoch, ordinal=2)
    _processed(world, "R02", "D02", _day(3), "duplicate", epoch)
    _processed(world, "R02", "D02", _day(4), "set_aside", epoch)
    _processed(world, "R02", "D02", _day(5), "quarantined", epoch)
    _ledger(world, "R02", _day(6), "missing_resident")
    _ledger(world, "R02", _day(12), "missing_device_gap", "D02")
    _ledger(world, "R02", _day(13), "checked_in")
    counts = rm.activity_counts(world.session, [_resident(world, "R02")], AS_OF)
    assert counts[world.residents["R02"]] == rm.ActivityCounts(2, 1, 1, 2)
    # Outside the 30-day window (as of Nov 5 the window starts Oct 7).
    later = rm.activity_counts(world.session, [_resident(world, "R02")], date(2026, 11, 5))
    assert later[world.residents["R02"]] == rm.ActivityCounts(0, 0, 0, 1)


@pytest.mark.req("DB-041", "D-42")
def test_window_never_starts_before_enrolment() -> None:
    assert rm.window_for(date(2026, 10, 1), AS_OF) == rm.Window(date(2026, 10, 1), AS_OF)
    assert rm.window_for(date(2026, 9, 1), AS_OF).start == date(2026, 10, 1)
    assert rm.window_for(date(2026, 9, 1), AS_OF).days == 30


@pytest.mark.req("DB-045", "FEAT-014-AC-02")
def test_last_checkin_ignores_duplicates_and_converts_to_local(world: World) -> None:
    epoch = world.epoch("R09", "D09")
    _processed(world, "R09", "D09", _day(29), "set_aside", epoch)
    last = datetime(2026, 10, 30, 19, 28, tzinfo=UTC)
    values = world.processed_values(
        "R09", "D09", status="usable", epoch_id=epoch, baseline_ordinal=1,
        timestamp_utc=last, local_date=AS_OF,
    )  # fmt: skip
    world.session.execute(insert(ProcessedSession).values(**values))
    dup = world.processed_values(
        "R09", "D09", status="duplicate", reasons=["session_id already received"],
        reason_text="session_id already received", timestamp_utc=last + timedelta(hours=1),
        local_date=AS_OF,
    )  # fmt: skip
    world.session.execute(insert(ProcessedSession).values(**dup))
    found = rm.last_checkin(world.session, [world.residents["R09"]])[world.residents["R09"]]
    assert found == last
    assert found.astimezone(ZoneInfo(TZ)).strftime("%Y-%m-%d %H:%M") == "2026-10-30 14:28"


@pytest.mark.req("DB-044", "FR-154", "FEAT-014-AC-03")
def test_device_silent_and_gap_days(world: World) -> None:
    window = rm.Window(_day(1), AS_OF)
    for code in ("R02", "R03"):
        _ledger(world, code, _day(11), "checked_in")
        _ledger(world, code, _day(12), "missing_device_gap", "D02")
    _ledger(world, "R02", _day(13), "checked_in")
    _ledger(world, "R03", _day(13), "missing_resident")
    for n in (20, 21):
        _ledger(world, "R08", _day(n), "missing_resident")
    d02, d08 = world.devices["D02"], world.devices["D08"]
    assert rm.device_silent_days(world.session, d02, window) == [_day(12)]
    assert rm.device_gap_days(world.session, d02, window) == [_day(12)]
    assert rm.device_silent_days(world.session, d08, window) == [_day(20), _day(21)]


@pytest.mark.req("DB-065", "D-64", "FEAT-014-AC-04")
def test_restart_cause(world: World) -> None:
    first = world.epoch("R07", "D07", number=1)
    world.session.execute(update(Epoch).where(Epoch.id == first).values(ended_at=_at(_day(13), 12)))
    second = world.epoch("R07", "D07B", number=2)
    epochs = {e.id: e for e in world.session.scalars(select(Epoch))}
    assert rm.restart_cause(world.session, epochs[first]) is None
    assert rm.restart_cause(world.session, epochs[second]) == rm.RestartCause(
        "device", "D07", "D07", "D07B"
    )
    assert rm.baseline_restarted(epochs[second], TZ) == date(2026, 10, 2)
    assert rm.baseline_restarted(epochs[first], TZ) is None


@pytest.mark.req("DB-066", "D-82", "FEAT-014-AC-05")
def test_device_in_use_until(world: World) -> None:
    assert rm.device_use(world.session, world.devices["D07"], AS_OF) == rm.DeviceUse(
        _day(1), _day(12)
    )
    assert rm.device_use(world.session, world.devices["D07B"], AS_OF) == rm.DeviceUse(
        _day(13), None
    )


@pytest.mark.req("DME-012", "D-41", "FEAT-014-AC-06", "FEAT-014-AC-07")
def test_baseline_progress_watching_and_alarm_since(world: World) -> None:
    epoch_id = world.epoch("R09", "D09")
    epoch = world.session.get(Epoch, epoch_id)
    assert epoch is not None
    sessions = [
        _processed(world, "R09", "D09", _day(n), "usable", epoch_id, ordinal=n)
        for n in range(1, 14)
    ]
    progress = rm.baseline_progress(world.session, epoch, 16)
    assert (progress.n, progress.of, progress.frozen) == (13, 16, False)
    assert rm.watching_since(world.session, epoch, 16) is None
    sessions += [
        _processed(world, "R09", "D09", _day(n), "usable", epoch_id, ordinal=n)
        for n in range(14, 17)
    ]
    _freeze(world, "R09", epoch_id, sessions[0][1], sessions[15][1], 16)
    progress = rm.baseline_progress(world.session, epoch, 16)
    assert (progress.n, progress.frozen) == (16, True)
    assert (progress.first_session_date, progress.frozen_after_date) == (_day(1), _day(16))
    assert rm.watching_since(world.session, epoch, 16) == _day(17)
    for n in range(17, 31):
        processed, _ = _processed(world, "R09", "D09", _day(n), "usable", epoch_id, ordinal=n)
        _score(world, "R09", epoch_id, processed, _day(n))
    assert rm.watching_since(world.session, epoch, 16) == _day(17)
    world.session.execute(
        insert(Alert).values(
            resident_id=world.residents["R09"], epoch_id=epoch_id, session_id=sessions[0][1],
            triggered_at=_at(_day(21)), local_date=_day(21), cusum_value=5.0,
            pipeline_run_id=world.run_id,
        )
    )  # fmt: skip
    facts = rm.alarm_facts(world.session, epoch, AS_OF)
    assert facts is not None
    assert (facts.alarm_since, facts.open_days, facts.reviewed) == (_day(21), 9, False)
    series = rm.scores_series(world.session, epoch, 16)
    assert len(series.points) == 14
    assert [p.local_date for p in series.points] == sorted(p.local_date for p in series.points)
    assert (series.baseline_first_date, series.baseline_frozen_after_date) == (_day(1), _day(16))


@pytest.mark.req("TRD-23-4.4.1")
def test_device_label_shared_and_was(world: World) -> None:
    r02, r07 = _resident(world, "R02"), _resident(world, "R07")
    assert rm.device_label(world.session, r02, AS_OF, 2) == rm.DeviceLabel("D02", True, None)
    assert rm.device_label(world.session, r07, AS_OF, 2) == rm.DeviceLabel("D07B", False, "D07")


@pytest.mark.req("DME-012", "FEAT-014-AC-08")
def test_derived_facts_are_not_stored(world: World) -> None:
    columns = world.session.execute(
        text(
            "SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' "
            "AND column_name IN ('last_checkin', 'silent_days', 'in_use_until', "
            "'restart_cause', 'watching_since')"
        )
    ).all()
    assert columns == []


@pytest.mark.req("FEAT-014-AC-01", "FEAT-014-AC-07")
@pytest.mark.skipif(
    not SEED_SESSIONS.exists(), reason="needs the test_v0_1 session seed (FEAT-055)"
)
def test_seed_values_on_the_full_seed() -> None:  # pragma: no cover - enabled by FEAT-055
    raise AssertionError("replace with the seed-valued FEAT-014 assertions when FEAT-055 lands")


@pytest.mark.req("DB-065", "D-64")
def test_restart_cause_firmware_then_software(world: World) -> None:
    repo = EpochRepository(world.session)
    first = world.epoch("R01", "D01", number=1)
    world.session.execute(update(Epoch).where(Epoch.id == first).values(ended_at=_at(_day(5))))
    second = world.epoch("R01", "D01", number=2)
    world.session.execute(
        update(Epoch)
        .where(Epoch.id == second)
        .values(device_firmware_version="fw-1.1.0", ended_at=_at(_day(9)))
    )
    third = world.epoch("R01", "D01", number=3)
    world.session.execute(
        update(Epoch)
        .where(Epoch.id == third)
        .values(device_firmware_version="fw-1.1.0", extraction_software_version="ext-2.0.0")
    )
    world.session.expire_all()
    epochs = {e.epoch_number: e for e in repo.by_resident(world.residents["R01"])}
    assert rm.restart_cause(world.session, epochs[2]) == rm.RestartCause(
        "firmware", "D01", "fw-1.0.0", "fw-1.1.0"
    )
    assert rm.restart_cause(world.session, epochs[3]) == rm.RestartCause(
        "software", "D01", "ext-1.0.0", "ext-2.0.0"
    )
    assert repo.delete_ids([third]) == 1


@pytest.mark.req("TRD-23-4.4.4", "FR-15")
def test_checkin_event_sources(world: World) -> None:
    epoch = world.epoch("R08", "D08")
    _processed(world, "R08", "D08", _day(3), "set_aside", epoch)
    _processed(world, "R08", "D08", _day(4), "quarantined", epoch)
    _ledger(world, "R08", _day(5), "missing_resident")
    events = rm.checkin_event_sources(world.session, _resident(world, "R08"), _day(1), AS_OF, TZ)
    kinds = sorted((e.local_date.day, e.event_type) for e in events)
    assert (3, "set_aside") in kinds
    assert (4, "quarantined") in kinds
    assert (5, "missed") in kinds
