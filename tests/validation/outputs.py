"""Pipeline outputs in the shape of the answer key (TRD 14 §4.5; FEAT-058).

Both tiers reduce their results to `Outputs`, keyed by the natural keys of TDV-036 and named by the
workbook columns, so one comparator checks either tier against DS-02 and Tier A equals Tier B is a
plain comparison of two `Outputs` (TST-081). Values keep full float64 precision (TDV-038).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from analytics import (
    COMPOSITE_KEYS,
    FEATURE_KEYS,
    TEST_V0_1,
    DeviceAssignment,
    PipelineConfig,
    PipelineResult,
    RawRecord,
    ResidentInfo,
    run_pipeline,
)
from analytics.config import COMPOSITE
from tests.validation.answer_key import COMPOSITE_LABEL, FIRST_DAY, INPUT_CSV, ROOT

REGISTRY = ROOT / "database" / "seeds" / "test_v0_1"
AS_OF = datetime(2026, 10, 30, 20, 0, tzinfo=UTC)  # 2026-10-30 15:00 America/Chicago (TDV-030)
NO_RECORD = "no record"
RECORD_COLUMNS = (
    "schema_version", "session_id", "device_id", "timestamp_utc", "mic_noise_level_dbfs",
    "audio_quality_flag", "extraction_software_version", "device_firmware_version",
    "speech_duration_s", "phrase_id", *FEATURE_KEYS,
)  # fmt: skip
STATUS_COLUMNS = ("usable", "set_aside", "quarantined", "duplicate", "missing_resident",
                  "missing_device_gap")  # fmt: skip
NOT_FORMED_NOTE = "Too few usable sessions: baseline pending, nothing scored"

Key = tuple[Any, ...]


@dataclass
class Outputs:
    annotated: dict[Key, dict[str, Any]] = field(default_factory=dict)
    status_counts: dict[Key, dict[str, Any]] = field(default_factory=dict)
    outcomes: dict[Key, dict[str, Any]] = field(default_factory=dict)
    baselines: dict[Key, dict[str, Any]] = field(default_factory=dict)
    morning_offsets: dict[Key, dict[str, Any]] = field(default_factory=dict)
    scores: dict[Key, dict[str, Any]] = field(default_factory=dict)
    params: dict[str, Any] = field(default_factory=dict)
    alerts: list[dict[str, Any]] = field(default_factory=list)
    cusum: dict[Key, dict[str, Any]] = field(default_factory=dict)
    ledger: list[tuple[str, date, str, str | None, str]] = field(default_factory=list)
    data_alerts: list[tuple[str, str, str, str]] = field(default_factory=list)

    def compared(self) -> dict[str, Any]:
        """Every value the comparator checks, for Tier A = Tier B (TST-081)."""
        return {name: getattr(self, name) for name in self.__dataclass_fields__}


# --- inputs (DS-01 in file order, registry from the seed CSVs) ----------------------------------


def _date(text: str) -> date | None:
    return date.fromisoformat(text) if text else None


def input_rows(path: Path = INPUT_CSV) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def records(rows: list[dict[str, str]] | None = None) -> list[RawRecord]:
    """DS-01 rows as engine records; file order is arrival order 1..283 (TDV-002)."""
    received = AS_OF
    out = []
    for seq, row in enumerate(rows if rows is not None else input_rows(), start=1):
        out.append(RawRecord(
            raw_session_id=f"seq-{seq:04d}", arrival_seq=seq, received_at=received,
            schema_version=row["schema_version"], session_id=row["session_id"],
            resident_code=row["resident_id"], device_code=row["device_id"],
            timestamp_utc=datetime.strptime(row["timestamp_utc"], "%Y-%m-%d %H:%M:%S")
            .replace(tzinfo=UTC),
            mic_noise_level_dbfs=float(row["mic_noise_level_dbfs"]),
            audio_quality_flag=row["audio_quality_flag"],
            extraction_software_version=row["extraction_software_version"],
            device_firmware_version=row["device_firmware_version"],
            speech_duration_s=float(row["speech_duration_s"]), phrase_id=row["phrase_id"],
            features={key: float(row[key]) for key in FEATURE_KEYS},
        ))  # fmt: skip
    return out


def registry() -> tuple[list[ResidentInfo], list[DeviceAssignment]]:
    with (REGISTRY / "residents.csv").open(newline="", encoding="utf-8") as handle:
        residents = [ResidentInfo(r["resident_code"], date.fromisoformat(r["enrolled_on"]))
                     for r in csv.DictReader(handle)]  # fmt: skip
    with (REGISTRY / "device_assignments.csv").open(newline="", encoding="utf-8") as handle:
        assignments = [DeviceAssignment(a["resident_code"], a["device_code"],
                                        date.fromisoformat(a["valid_from"]), _date(a["valid_to"]))
                       for a in csv.DictReader(handle)]  # fmt: skip
    return residents, assignments


def run_tier_a(
    rows: list[dict[str, str]] | None = None, config: PipelineConfig = TEST_V0_1
) -> PipelineResult:
    """Tier A: `run_pipeline` in-process on DS-01 (TDV-030, FEAT-058-FR-01)."""
    residents, assignments = registry()
    return run_pipeline(records(rows), residents, assignments, config, AS_OF)


# --- normalisation ------------------------------------------------------------------------------


def day_of(local: date) -> int:
    return (local - FIRST_DAY).days + 1


def feature_label(key: str) -> str:
    return COMPOSITE_LABEL if key == COMPOSITE else key


def record_values(row: dict[str, str] | None, device: str | None = None) -> dict[str, Any]:
    """The DS-01 record columns as the workbook stores them (strings exact, numbers float); a
    missing day carries only the resident's device, from the day ledger (Table 4.5-A)."""
    if row is None:
        return {column: device if column == "device_id" else None for column in RECORD_COLUMNS}
    numeric = {"mic_noise_level_dbfs", "speech_duration_s", *FEATURE_KEYS}
    return {c: float(row[c]) if c in numeric else row[c] for c in RECORD_COLUMNS}


def annotated_row(
    *, local_time: str, status: str, reason: str | None, morning: bool | None,
    epoch: int | None, ordinal: int | None, in_baseline: bool, record: dict[str, Any],
    baseline_n: int,
) -> dict[str, Any]:  # fmt: skip
    candidate = status == "usable" and ordinal is not None and ordinal <= baseline_n
    return {
        "local_time": local_time, "expected_status": status, "expected_reason": reason or None,
        "expected_morning": morning, "expected_epoch": epoch, "in_baseline": candidate,
        "in_baseline_stored": in_baseline, **record,
    }  # fmt: skip


def from_result(result: PipelineResult, rows: list[dict[str, str]] | None = None) -> Outputs:
    """Tier A outputs (FEAT-058-FR-01)."""
    data = rows if rows is not None else input_rows()
    by_seq = dict(enumerate(data, start=1))
    baseline_n = int(result.run_config["baseline_n"])
    out = Outputs()
    for s in result.sessions:
        rec = s.record
        key = (rec.resident_code, day_of(s.local_date), rec.arrival_seq)
        out.annotated[key] = annotated_row(
            local_time=s.local_datetime.strftime("%Y-%m-%d %H:%M"), status=s.status,
            reason=s.reason_text, morning=s.is_morning, epoch=s.epoch_number,
            ordinal=s.baseline_ordinal, in_baseline=s.in_baseline,
            record=record_values(by_seq[rec.arrival_seq]), baseline_n=baseline_n,
        )  # fmt: skip
    for d in result.ledger:
        out.ledger.append((d.resident_code, d.local_date, d.status, d.device_code, d.reason))
        if d.status != "checked_in":
            out.annotated[(d.resident_code, day_of(d.local_date), NO_RECORD)] = annotated_row(
                local_time=d.local_date.isoformat(), status=d.status, reason=d.reason,
                morning=None, epoch=None, ordinal=None, in_baseline=False,
                record=record_values(None, device=d.device_code), baseline_n=baseline_n,
            )  # fmt: skip
    out.ledger.sort()
    _status_counts(out)
    scored: dict[Key, int] = {}
    for score in result.scores:
        scored[(score.resident_code, score.epoch_number)] = (
            scored.get((score.resident_code, score.epoch_number), 0) + 1)  # fmt: skip
        out.scores[(score.session_id,)] = score_row(
            resident=score.resident_code, epoch=score.epoch_number, local=score.local_date,
            morning=score.is_morning, z=dict(score.z), composite_raw=score.composite_raw,
            composite_z=score.composite_z, tally=score.cusum_tally, alarm=score.alarm_state,
        )  # fmt: skip
    alarms = {(a.resident_code, a.epoch_number): a.session_id for a in result.alerts}
    for e in result.epochs:
        key = (e.resident_code, e.epoch_number)
        out.outcomes[key] = outcome_row(
            device=e.device_code, usable=e.usable_count, formed=e.baseline_formed,
            frozen_after=e.frozen_after_session_id, scored=scored.get(key, 0),
            first_alarm=alarms.get(key),
        )  # fmt: skip
        out.cusum[key] = {"current_tally": e.current_tally, "alarm_on": e.alarm_on}
    devices = {(e.resident_code, e.epoch_number): e.device_code for e in result.epochs}
    for b in result.baselines:
        out.baselines[(b.resident_code, b.epoch_number, feature_label(b.feature_key))] = {
            "device_id": devices[(b.resident_code, b.epoch_number)], "n_sessions": b.n_sessions,
            "first_session": b.first_session_id, "baseline_frozen_after": b.frozen_after_session_id,
            "median": b.median, "mad": b.mad, "robust_spread": b.robust_spread,
            "floor_applied": b.floor_applied,
        }  # fmt: skip
    out.params = params_of(result.run_config)
    out.morning_offsets = offsets_of(result.run_config)
    for a in result.alerts:
        out.alerts.append(alert_row(
            resident=a.resident_code, epoch=a.epoch_number, session=a.session_id,
            triggered=a.triggered_at, local=a.local_date, value=a.cusum_value,
            status="closed" if a.epoch_ended else "open",
        ))  # fmt: skip
    out.alerts.sort(key=lambda a: (a["resident_id"], a["epoch"]))
    out.data_alerts = sorted((a.kind, a.resident_code or a.device_code or "", a.title, a.detail)
                             for a in result.data_alerts)  # fmt: skip
    return out


def _status_counts(out: Outputs) -> None:
    for (resident, _, _), row in out.annotated.items():
        counts = out.status_counts.setdefault((resident,), dict.fromkeys(STATUS_COLUMNS, 0))
        counts[row["expected_status"]] += 1


def score_row(
    *, resident: str, epoch: int, local: date, morning: bool, z: dict[str, float],
    composite_raw: float, composite_z: float, tally: float, alarm: str,
) -> dict[str, Any]:  # fmt: skip
    return {
        "resident_id": resident, "epoch": epoch, "local_date": local.isoformat(),
        "morning": morning, **{f"z_{k}": z[f"z_{k}"] for k in COMPOSITE_KEYS},
        "composite_raw": composite_raw, "composite_z": composite_z, "cusum_tally": tally,
        "alarm": alarm,
    }  # fmt: skip


def outcome_row(
    *, device: str, usable: int, formed: bool, frozen_after: str | None, scored: int,
    first_alarm: str | None,
) -> dict[str, Any]:  # fmt: skip
    return {
        "device_id": device, "usable_in_epoch": usable, "baseline_formed": formed,
        "baseline_frozen_after": frozen_after if formed else None,
        "scored_sessions": scored if formed else None,
        "first_alarm_session": first_alarm, "note": None if formed else NOT_FORMED_NOTE,
    }  # fmt: skip


def alert_row(
    *, resident: str, epoch: int, session: str, triggered: datetime, local: date, value: float,
    status: str,
) -> dict[str, Any]:  # fmt: skip
    return {"resident_id": resident, "epoch": epoch, "session_id": session,
            "triggered_at": triggered.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S"),
            "local_date": local.isoformat(), "cusum_value": value, "status": status}  # fmt: skip


PARAM_KEYS = ("facility_tz", "morning_cutoff_hour", "noise_limit_dbfs", "min_speech_s",
              "baseline_n", "mad_scale", "pause_floor", "composite_floor", "screen_min_n",
              "screen_f0_z", "screen_other_z", "screen_other_count", "cusum_k", "cusum_h",
              "shared_device_min_residents")  # fmt: skip


def params_of(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {key: snapshot[key] for key in PARAM_KEYS}


def offsets_of(snapshot: dict[str, Any]) -> dict[Key, dict[str, Any]]:
    offsets = snapshot["morning_offsets"]
    return {(key,): {"configured_morning_offset": float(offsets[key])} for key in FEATURE_KEYS}
