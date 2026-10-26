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
from backend.models import FEATURE_KEYS, Epoch, PipelineTrigger
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

    def raw(
        self, resident: str, device: str, *, at: datetime = T0, session_id: str | None = None
    ) -> tuple[uuid.UUID, str]:
        self._seq += 1
        sid = session_id or f"S-{resident}-{self._seq:04d}"
        fields = {
            "schema_version": "0.1",
            "session_id": sid,
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
        }
        payload = {k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in fields.items()}
        raw_id, _ = RawSessionRepository(self.session).insert(
            {
                **fields,
                "payload": payload,
                "resident_id": self.residents[resident],
                "device_id": self.devices[device],
            }
        )
        return raw_id, sid

    def epoch(self, resident: str, device: str, *, number: int = 1) -> uuid.UUID:
        epoch = Epoch(
            resident_id=self.residents[resident],
            epoch_number=number,
            device_id=self.devices[device],
            device_firmware_version="fw-1.0.0",
            extraction_software_version="ext-1.0.0",
            started_at=T0 - timedelta(hours=1),
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
