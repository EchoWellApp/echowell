"""Hand-built rows for the database tests (TRD 20 §4.12 roster; TRD 13 §4.2).

`World` loads the test_v0_1 roster (database/seeds/test_v0_1/) in the caller's transaction and
offers small builders for the derived tables, so each test states only the rows it is about.
Feature values are synthetic.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.cli import load_roster
from backend.models import (
    FEATURE_KEYS,
    Alert,
    Baseline,
    CusumState,
    DataAlert,
    DayLedgerEntry,
    Epoch,
    PipelineRunStatus,
    PipelineTrigger,
    ProcessedSession,
    Score,
)
from backend.repositories.pipeline_run_repository import PipelineRunRepository
from backend.repositories.raw_session_repository import RawSessionRepository
from tests.integration.db_support import ROOT

ROSTER = ROOT / "database" / "seeds" / "test_v0_1"
T0 = datetime(2026, 10, 2, 13, 0, tzinfo=UTC)
OTHER_SPEAKER = "possible other speaker (F0 z=5.12; composite features with |z|>=3: 3)"
LATE = "late arrival (not used for baseline or scores)"

FEATURES: dict[str, float] = {
    "loudness_dbfs": -24.0,
    "total_phrase_duration_s": 3.1,
    "speech_rate_syl_per_s": 4.2,
    "articulation_rate_syl_per_s": 4.8,
    "number_of_pauses": 2,
    "pause_fraction": 0.18,
    "voiced_fraction": 0.62,
    "mean_f0_hz": 190.0,
    "f0_variability_st": 2.4,
    "jitter_local_pct": 0.9,
    "shimmer_local_pct": 3.2,
    "hnr_db": 18.0,
    "cpps_db": 12.0,
    "alpha_ratio_db": -14.0,
    "hammarberg_index_db": 22.0,
    "mfcc1": 1.0,
    "mfcc2": -0.4,
    "mfcc3": 0.2,
    "mfcc4": -0.1,
}
assert tuple(FEATURES) == FEATURE_KEYS


@dataclass
class World:
    session: Session
    residents: dict[str, uuid.UUID] = field(default_factory=dict)
    devices: dict[str, uuid.UUID] = field(default_factory=dict)
    run_id: uuid.UUID | None = None
    _seq: int = 0

    @classmethod
    def build(cls, session: Session) -> World:
        load_roster(session, ROSTER)
        world = cls(session)
        world.residents = dict(
            session.execute(text("SELECT resident_code, id FROM residents")).tuples().all()
        )
        world.devices = dict(
            session.execute(text("SELECT device_code, id FROM devices")).tuples().all()
        )
        run = PipelineRunRepository(session).insert_running(
            trigger=PipelineTrigger.TEST,
            scope={"type": "all"},
            config_profile="test_v0_1",
            config_snapshot={"baseline_n": 16},
            code_version="test",
            as_of=T0,
        )
        world.run_id = run.id
        return world

    def raw_values(
        self,
        resident: str,
        device: str,
        *,
        at: datetime = T0,
        session_id: str | None = None,
        **overrides: Any,
    ) -> dict[str, Any]:
        """Column values for one `raw_sessions` arrival (payload included)."""
        self._seq += 1
        fields: dict[str, Any] = {
            "schema_version": "0.1",
            "session_id": session_id or f"S-{resident}-{self._seq:04d}",
            "resident_code": resident,
            "device_code": device,
            "timestamp_utc": at,
            "mic_noise_level_dbfs": -55.0,
            "audio_quality_flag": "ok",
            "extraction_software_version": "ext-1.0.0",
            "device_firmware_version": "fw-1.0.0",
            "speech_duration_s": 3.0,
            "phrase_id": "P1",
            **FEATURES,
            **overrides,
        }
        payload = {k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in fields.items()}
        return {
            **fields,
            "payload": payload,
            "resident_id": self.residents[resident],
            "device_id": self.devices[device],
        }

    def raw(
        self, resident: str, device: str, *, at: datetime = T0, session_id: str | None = None
    ) -> tuple[uuid.UUID, str]:
        values = self.raw_values(resident, device, at=at, session_id=session_id)
        raw_id, _ = RawSessionRepository(self.session).insert(values)
        return raw_id, values["session_id"]

    def epoch(
        self,
        resident: str,
        device: str,
        *,
        number: int = 1,
        started_at: datetime = T0 - timedelta(hours=1),
        firmware: str = "fw-1.0.0",
        ended_at: datetime | None = None,
    ) -> uuid.UUID:
        epoch = Epoch(
            resident_id=self.residents[resident],
            epoch_number=number,
            device_id=self.devices[device],
            device_firmware_version=firmware,
            extraction_software_version="ext-1.0.0",
            started_at=started_at,
            ended_at=ended_at,
            pipeline_run_id=self.run_id,
        )
        self.session.add(epoch)
        self.session.flush()
        return epoch.id

    def processed_values(
        self, resident: str, device: str, *, status: str, **overrides: Any
    ) -> dict[str, Any]:
        """Column values for a `processed_sessions` row (a new raw arrival included)."""
        raw_id, sid = self.raw(resident, device)
        values: dict[str, Any] = {
            "raw_session_id": raw_id,
            "session_id": sid,
            "resident_id": self.residents[resident],
            "epoch_id": None,
            "status": status,
            "reasons": [],
            "reason_text": "",
            "timestamp_utc": T0,
            "local_date": date(2026, 10, 2),
            "local_time": "08:00:00",
            "is_morning": True,
            "screen_detail": None,
            "baseline_ordinal": None,
            "late_arrival": False,
            "adjusted_features": None if status == "duplicate" else dict(FEATURES),
            "pipeline_run_id": self.run_id,
        }
        values.update(overrides)
        return values

    # --- derived rows for the read endpoints (FEAT-027..FEAT-029) --------------------------

    def processed(
        self,
        resident: str,
        device: str,
        day: date,
        status: str,
        epoch: uuid.UUID | None,
        *,
        ordinal: int | None = None,
        hour: int = 13,
        session_id: str | None = None,
        in_baseline: bool = False,
    ) -> tuple[uuid.UUID, str]:
        """One arrival and its `processed_sessions` row (`hour` in UTC; 13:00 UTC is 08:00 CDT)."""
        at = datetime(day.year, day.month, day.day, hour, tzinfo=UTC)
        sid = session_id or f"{resident}-{day:%Y%m%d}-{self._seq % 100:02d}"
        raw_id, sid = self.raw(resident, device, at=at, session_id=sid)
        reasons = {
            "usable": [], "set_aside": ["noise above limit"], "quarantined": [OTHER_SPEAKER],
            "duplicate": ["session_id already received"],
        }[status]  # fmt: skip
        row = ProcessedSession(
            raw_session_id=raw_id, session_id=sid, resident_id=self.residents[resident],
            epoch_id=None if status == "duplicate" else epoch, status=status, reasons=reasons,
            reason_text="; ".join(reasons), timestamp_utc=at, local_date=day,
            local_time=(at - timedelta(hours=5)).time(), is_morning=hour - 5 < 12,
            screen_detail="F0 z=5.12" if status == "quarantined" else None,
            baseline_ordinal=ordinal if status == "usable" else None,
            in_baseline=in_baseline,
            adjusted_features=None if status == "duplicate" else dict(FEATURES),
            pipeline_run_id=self.run_id,
        )  # fmt: skip
        self.session.add(row)
        self.session.flush()
        return row.id, sid

    def ledger(self, resident: str, day: date, status: str, device: str | None = None) -> None:
        reason = {
            "checked_in": "", "missing_resident": "no record received",
            "missing_device_gap": f"all residents on shared device {device} have no record",
        }[status]  # fmt: skip
        self.session.add(
            DayLedgerEntry(
                resident_id=self.residents[resident], local_date=day, status=status,
                device_id=self.devices[device] if device else None, reason=reason,
                pipeline_run_id=self.run_id,
            )
        )  # fmt: skip
        self.session.flush()

    def freeze(self, resident: str, epoch: uuid.UUID, first: str, last: str, n: int = 16) -> None:
        """A frozen baseline: the 19 feature rows and the composite row (median 1.0)."""
        for key in (*FEATURE_KEYS, "composite"):
            self.session.add(
                Baseline(
                    resident_id=self.residents[resident], epoch_id=epoch, feature_key=key,
                    n_sessions=n, first_session_id=first, frozen_after_session_id=last,
                    median=1.0, mad=0.1, robust_spread=0.15, floor_applied=False,
                    frozen_at=T0, pipeline_run_id=self.run_id,
                )
            )  # fmt: skip
        self.session.flush()

    def score(
        self,
        resident: str,
        epoch: uuid.UUID,
        processed: uuid.UUID,
        day: date,
        *,
        tally: float = 0.0,
        z: float = 0.5,
    ) -> None:
        self.session.add(
            Score(
                processed_session_id=processed, resident_id=self.residents[resident],
                epoch_id=epoch, local_date=day, is_morning=True,
                z={f"z_{k}": z for k in FEATURE_KEYS}, composite_raw=z, composite_z=z,
                cusum_tally=tally, alarm_state="off", pipeline_run_id=self.run_id,
            )
        )  # fmt: skip
        self.session.flush()

    def cusum(self, resident: str, epoch: uuid.UUID, tally: float, last: str) -> None:
        self.session.add(
            CusumState(
                epoch_id=epoch, resident_id=self.residents[resident], current_tally=tally,
                last_scored_session_id=last, alarm_on=tally >= 5.0, pipeline_run_id=self.run_id,
            )
        )  # fmt: skip
        self.session.flush()

    def alert(
        self,
        resident: str,
        epoch: uuid.UUID,
        session_id: str,
        day: date,
        *,
        value: float = 5.4,
        status: str = "open",
    ) -> uuid.UUID:
        alert = Alert(
            resident_id=self.residents[resident], epoch_id=epoch, session_id=session_id,
            triggered_at=datetime(day.year, day.month, day.day, 13, tzinfo=UTC), local_date=day,
            cusum_value=value, status=status, pipeline_run_id=self.run_id,
            closed_reason="admin" if status == "closed" else None,
            closed_at=T0 if status == "closed" else None,
        )  # fmt: skip
        self.session.add(alert)
        self.session.flush()
        return alert.id

    def data_alert(self, resident: str, kind: str, *, status: str = "open") -> uuid.UUID:
        row = DataAlert(
            kind=kind, resident_id=self.residents[resident], title=kind.replace("_", " "),
            detail="", first_detected_at=T0, last_detected_at=T0, status=status,
            resolved_at=T0 if status == "resolved" else None, pipeline_run_id=self.run_id,
        )  # fmt: skip
        self.session.add(row)
        self.session.flush()
        return row.id

    def succeed(self, as_of: datetime) -> None:
        """Mark the world's run succeeded with `as_of` (the API as-of, API-069)."""
        run = PipelineRunRepository(self.session).get(self.run_id)  # type: ignore[arg-type]
        assert run is not None
        run.as_of = as_of
        PipelineRunRepository(self.session).finish(
            run, status=PipelineRunStatus.SUCCEEDED, finished_at=as_of,
            counts=dict.fromkeys(
                ("arrivals", "usable", "set_aside", "quarantined", "duplicate",
                 "missing_resident", "missing_device_gap", "late_arrival", "scored",
                 "alerts_opened", "excluded_after_as_of", "residents"), 0),
        )  # fmt: skip
