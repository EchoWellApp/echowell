"""Configuration, data contracts and errors of the analytics engine (TRD 07 §4.2-§4.4, §4.7,
§4.11; FEAT-040).

Everything the stages exchange is defined here, because every stage already imports this module
(TRD 07 §4.3). Contracts are frozen, slotted dataclasses; stage functions return new instances and
never mutate their arguments (ANL-010). Feature mappings always hold the 19 canonical keys of
contract §6 in order (ANL-013).

`PipelineConfig` holds the algorithm keys, which change derived results and are covered by
`config_hash()`, and `OperationalConfig` the operational keys, which do not (TRD 24 D-56).
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, fields
from datetime import date, datetime
from typing import Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

ENGINE_VERSION = "0.1.0"


# --- errors (ANL-051) ---------------------------------------------------------------------------


class AnalyticsError(Exception):
    """Base of the two errors the engine raises on purpose."""


class ContractError(AnalyticsError):
    """An input violates a data contract (ANL-018)."""


class ConfigError(AnalyticsError):
    """A configuration value is missing, unknown or invalid; the message names the key (ANL-029)."""


# --- run warning codes (ANL-052) ----------------------------------------------------------------

ENGINE_WARNING_CODES = (
    "after_as_of", "late_arrival", "zero_spread", "baseline_mismatch", "config_default_used",
    "config_mismatch", "no_device_assignment", "alert_first_crossing_changed",
    "device_assignment_mismatch",
)  # fmt: skip
RUNNER_WARNING_CODES = ("exception", "run_abandoned")
FAILURE_CODES = ("config_changed_requires_rebuild", "pipeline_config_invalid")


# --- features (contract §6; DME-002) ------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FeatureSpec:
    """One acoustic feature (TRD 07 §4.4): `sign` 0 means stored, not scored."""

    key: str
    unit: str
    sign: int
    morning_offset: float = 0.0
    in_composite: bool = False
    spread_floor: float = 0.0

    def __post_init__(self) -> None:
        if self.sign not in (-1, 0, 1) or self.in_composite != (self.sign != 0):
            raise ContractError(f"feature {self.key}: sign and in_composite disagree")


# The 19 features in contract §6 order: 7 composite features, then 12 stored, not scored.
FEATURES: tuple[FeatureSpec, ...] = (
    FeatureSpec("loudness_dbfs", "dBFS", -1, -1.50, True),
    FeatureSpec("total_phrase_duration_s", "s", +1, +0.10, True),
    FeatureSpec("speech_rate_syl_per_s", "syllables/s", -1, -0.12, True),
    FeatureSpec("articulation_rate_syl_per_s", "syllables/s", -1, -0.10, True),
    FeatureSpec("number_of_pauses", "count", +1, 0.0, True, spread_floor=0.5),
    FeatureSpec("pause_fraction", "proportion", +1, +0.010, True),
    FeatureSpec("voiced_fraction", "proportion", -1, -0.020, True),
    FeatureSpec("mean_f0_hz", "Hz", 0),
    FeatureSpec("f0_variability_st", "semitones", 0),
    FeatureSpec("jitter_local_pct", "percent", 0),
    FeatureSpec("shimmer_local_pct", "percent", 0),
    FeatureSpec("hnr_db", "dB", 0),
    FeatureSpec("cpps_db", "dB", 0),
    FeatureSpec("alpha_ratio_db", "dB", 0),
    FeatureSpec("hammarberg_index_db", "dB", 0),
    FeatureSpec("mfcc1", "unitless", 0),
    FeatureSpec("mfcc2", "unitless", 0),
    FeatureSpec("mfcc3", "unitless", 0),
    FeatureSpec("mfcc4", "unitless", 0),
)
FEATURE_KEYS: tuple[str, ...] = tuple(f.key for f in FEATURES)
COMPOSITE_KEYS: tuple[str, ...] = tuple(f.key for f in FEATURES if f.in_composite)
COMPOSITE_SIGNS: dict[str, int] = {f.key: f.sign for f in FEATURES if f.in_composite}
COMPOSITE = "composite"  # feature_key of the composite baseline row
F0_KEY = "mean_f0_hz"
# Plain-language labels of contract §6 without the parenthetical, for "Leaning most" (CUS-041).
LEANING_LABELS: dict[str, str] = {
    "loudness_dbfs": "quieter",
    "total_phrase_duration_s": "slower to say the phrase",
    "speech_rate_syl_per_s": "fewer syllables per second",
    "articulation_rate_syl_per_s": "slower while talking",
    "number_of_pauses": "more pauses",
    "pause_fraction": "more time pausing",
    "voiced_fraction": "less voiced sound",
}


def check_features(values: Mapping[str, float], what: str) -> None:
    """The 19 canonical keys in order, each a finite number (ANL-013, BSC-042)."""
    if tuple(values) != FEATURE_KEYS:
        raise ContractError(f"{what}: features must be the 19 canonical keys in contract order")
    for key, value in values.items():
        if (
            isinstance(value, bool)
            or not isinstance(value, int | float)
            or not math.isfinite(value)
        ):
            raise ContractError(f"{what}: feature {key} is not a finite number")


# --- data contracts (TRD 07 §4.3, §4.4) ---------------------------------------------------------

EpochKey = tuple[str, int]
ScreenStatus = Literal["duplicate", "set_aside", "pending_screen"]
SessionStatus = Literal["duplicate", "set_aside", "quarantined", "usable"]
AlarmState = Literal["off", "rings", "on"]
DayStatus = Literal["checked_in", "missing_resident", "missing_device_gap"]
DataAlertKind = Literal[
    "baseline_stalled", "possible_other_speaker", "high_set_aside", "device_silent"
]


@dataclass(frozen=True, slots=True)
class RawRecord:
    """One `raw_sessions` row, built by the backend from its typed columns (ANL-035)."""

    raw_session_id: str
    arrival_seq: int
    received_at: datetime
    schema_version: str
    session_id: str
    resident_code: str
    device_code: str
    timestamp_utc: datetime
    mic_noise_level_dbfs: float
    audio_quality_flag: str
    extraction_software_version: str
    device_firmware_version: str
    speech_duration_s: float
    phrase_id: str
    features: Mapping[str, float]

    def __post_init__(self) -> None:
        check_features(self.features, self.session_id)
        for name in ("received_at", "timestamp_utc"):
            if getattr(self, name).tzinfo is None:
                raise ContractError(f"{self.session_id}: {name} must be timezone-aware")

    @property
    def epoch_key(self) -> tuple[str, str, str]:
        """(device_id, device_firmware_version, extraction_software_version) (TRD 08 §4.1)."""
        return (self.device_code, self.device_firmware_version, self.extraction_software_version)


@dataclass(frozen=True, slots=True)
class ScreenedRecord:
    record: RawRecord
    status: ScreenStatus
    reasons: tuple[str, ...] = ()
    reason_text: str = ""


@dataclass(frozen=True, slots=True)
class EpochedRecord:
    record: RawRecord
    status: SessionStatus | Literal["pending_screen"]
    reasons: tuple[str, ...]
    reason_text: str
    epoch_number: int | None
    screen_detail: str | None
    late_arrival: bool
    local_datetime: datetime
    local_date: date


@dataclass(frozen=True, slots=True)
class AdjustedRecord:
    record: RawRecord
    status: SessionStatus
    reasons: tuple[str, ...]
    reason_text: str
    epoch_number: int | None
    screen_detail: str | None
    late_arrival: bool
    local_datetime: datetime
    local_date: date
    is_morning: bool
    adjusted: Mapping[str, float]
    baseline_ordinal: int | None = None
    in_baseline: bool = False


@dataclass(frozen=True, slots=True)
class RobustStats:
    median: float
    mad: float
    spread: float
    floor_applied: bool


@dataclass(frozen=True, slots=True)
class Baseline:
    resident_code: str
    epoch_number: int
    device_code: str
    feature_key: str
    n_sessions: int
    first_session_id: str
    frozen_after_session_id: str
    median: float
    mad: float
    robust_spread: float
    floor_applied: bool
    frozen_at: datetime


@dataclass(frozen=True, slots=True)
class BaselineMembership:
    session_ids: tuple[str, ...]
    formed: bool
    usable_count: int


@dataclass(frozen=True, slots=True)
class ScoreRow:
    session_id: str
    raw_session_id: str
    resident_code: str
    epoch_number: int
    local_date: date
    is_morning: bool
    z: Mapping[str, float]
    composite_raw: float
    composite_z: float
    cusum_tally: float = 0.0
    alarm_state: AlarmState = "off"
    scored_ordinal: int = 0


@dataclass(frozen=True, slots=True)
class EpochSummary:
    resident_code: str
    epoch_number: int
    device_code: str
    device_firmware_version: str
    extraction_software_version: str
    started_at: datetime
    ended_at: datetime | None
    usable_count: int
    baseline_formed: bool
    frozen_after_session_id: str | None
    scored_count: int
    watching_since: date | None
    current_tally: float
    last_scored_session_id: str | None
    alarm_on: bool
    first_alarm_session_id: str | None


@dataclass(frozen=True, slots=True)
class AlertEvent:
    resident_code: str
    epoch_number: int
    session_id: str
    triggered_at: datetime
    local_date: date
    cusum_value: float
    epoch_ended: bool
    epoch_ended_at: datetime | None
    leaning_most: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ResidentInfo:
    resident_code: str
    enrolled_on: date
    withdrawn_on: date | None = None
    status: str = "active"


@dataclass(frozen=True, slots=True)
class DeviceAssignment:
    resident_code: str
    device_code: str
    valid_from: date
    valid_to: date | None = None  # inclusive

    def covers(self, day: date) -> bool:
        return self.valid_from <= day and (self.valid_to is None or day <= self.valid_to)


@dataclass(frozen=True, slots=True)
class LedgerDay:
    resident_code: str
    local_date: date
    status: DayStatus
    device_code: str | None
    reason: str = ""


@dataclass(frozen=True, slots=True)
class RunWarning:
    code: str
    resident_code: str | None = None
    session_id: str | None = None
    detail: str = ""

    def sort_key(self) -> tuple[str, str, str, str]:
        return (self.code, self.resident_code or "", self.session_id or "", self.detail)


@dataclass(frozen=True, slots=True)
class DataAlert:
    kind: DataAlertKind
    resident_code: str | None
    device_code: str | None
    title: str
    detail: str
    days: tuple[date, ...] = ()


@dataclass(frozen=True, slots=True)
class AnalyticsSummary:
    period_start: date
    period_end: date
    kpis: dict[str, Any]
    daily_series: tuple[dict[str, Any], ...]
    funnel: tuple[dict[str, Any], ...]
    by_resident: tuple[dict[str, Any], ...]


@dataclass(frozen=True, slots=True)
class PipelineResult:
    run_config: dict[str, Any]
    config_hash: str
    engine_version: str
    as_of: datetime
    sessions: tuple[AdjustedRecord, ...]
    epochs: tuple[EpochSummary, ...]
    baselines: tuple[Baseline, ...]
    scores: tuple[ScoreRow, ...]
    alerts: tuple[AlertEvent, ...]
    ledger: tuple[LedgerDay, ...]
    data_alerts: tuple[DataAlert, ...]
    analytics: AnalyticsSummary
    warnings: tuple[RunWarning, ...]
    counts: dict[str, int]


# --- configuration (TRD 07 §4.7) ----------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ReviewExplanation:
    code: str
    label: str


@dataclass(frozen=True, slots=True)
class OperationalConfig:
    """Operational keys: read at the next run or request, never part of `config_hash()` (D-56)."""

    data_alert_set_aside_fraction: float
    data_alert_device_silent_days: int
    data_alert_baseline_stalled_enabled: bool
    alert_snooze_hours: int
    review_explanations: tuple[ReviewExplanation, ...]


@dataclass(frozen=True, slots=True)
class PipelineConfig:
    profile: str
    facility_tz: str
    noise_limit_dbfs: float
    min_speech_s: float
    baseline_n: int
    screen_min_n: int
    screen_f0_z: float
    screen_other_z: float
    screen_other_count: int
    mad_scale: float
    pause_floor: float
    composite_floor: float
    cusum_k: float
    cusum_h: float
    morning_cutoff_hour: int
    morning_offsets: Mapping[str, float]
    shared_device_min_residents: int
    operational: OperationalConfig
    features: tuple[FeatureSpec, ...] = FEATURES

    def spread_floor(self, key: str) -> float:
        """The robust-spread floor of a feature: `pause_floor` for number_of_pauses, else 0."""
        return self.pause_floor if key == "number_of_pauses" else 0.0

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.facility_tz)

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any]) -> PipelineConfig:
        """Build and validate a config from `config_parameters` values plus `profile`
        (ANL-029); every key is required and unknown keys are refused."""
        unknown = sorted(set(values) - set(KEY_TYPES))
        if unknown:
            raise ConfigError(f"{unknown[0]}: unknown configuration key")
        for key in KEY_TYPES:
            if key not in values:
                raise ConfigError(f"{key}: missing")
        v = {key: _typed(key, values[key]) for key in KEY_TYPES}
        _validate(v)
        operational = OperationalConfig(
            data_alert_set_aside_fraction=v["data_alert_set_aside_fraction"],
            data_alert_device_silent_days=v["data_alert_device_silent_days"],
            data_alert_baseline_stalled_enabled=v["data_alert_baseline_stalled_enabled"],
            alert_snooze_hours=v["alert_snooze_hours"],
            review_explanations=v["review_explanations"],
        )
        algorithm = {k: v[k] for k in KEY_TYPES if k not in OPERATIONAL_KEYS}
        return cls(**algorithm, operational=operational)

    def snapshot(self) -> dict[str, Any]:
        """Every field as JSON-serialisable values (ANL-030)."""
        out: dict[str, Any] = {}
        for f in fields(self):
            value = getattr(self, f.name)
            if f.name == "operational":
                op = {g.name: getattr(value, g.name) for g in fields(value)}
                op["review_explanations"] = [
                    {"code": e.code, "label": e.label} for e in value.review_explanations
                ]
                out["operational"] = op
            elif f.name == "features":
                out["features"] = [
                    {g.name: getattr(spec, g.name) for g in fields(spec)} for spec in value
                ]
            elif f.name == "morning_offsets":
                out[f.name] = dict(value)
            else:
                out[f.name] = value
        return out

    def config_hash(self) -> str:
        """SHA-256 of the snapshot restricted to the algorithm keys (ANL-030, D-56)."""
        algorithm = {k: v for k, v in self.snapshot().items() if k != "operational"}
        text = json.dumps(algorithm, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def values(self) -> dict[str, Any]:
        """The `from_mapping` keys and values, so `from_mapping(c.values()) == c`."""
        snap = self.snapshot()
        out = {k: snap[k] for k in KEY_TYPES if k not in OPERATIONAL_KEYS}
        out.update(snap["operational"])
        return out


# key -> expected Python type of the stored JSON value
KEY_TYPES: dict[str, str] = {
    "profile": "str", "facility_tz": "str", "noise_limit_dbfs": "float", "min_speech_s": "float",
    "baseline_n": "int", "screen_min_n": "int", "screen_f0_z": "float", "screen_other_z": "float",
    "screen_other_count": "int", "mad_scale": "float", "pause_floor": "float",
    "composite_floor": "float", "cusum_k": "float", "cusum_h": "float",
    "morning_cutoff_hour": "int", "morning_offsets": "offsets",
    "shared_device_min_residents": "int", "data_alert_set_aside_fraction": "float",
    "data_alert_device_silent_days": "int", "data_alert_baseline_stalled_enabled": "bool",
    "alert_snooze_hours": "int", "review_explanations": "explanations",
}  # fmt: skip
OPERATIONAL_KEYS = frozenset(f.name for f in fields(OperationalConfig))


def _typed(key: str, value: Any) -> Any:
    kind = KEY_TYPES[key]
    if kind == "bool":
        if not isinstance(value, bool):
            raise ConfigError(f"{key}: must be true or false")
        return value
    if kind == "int":
        if isinstance(value, bool) or not isinstance(value, int):
            raise ConfigError(f"{key}: must be an integer")
        return value
    if kind == "float":
        if (
            isinstance(value, bool)
            or not isinstance(value, int | float)
            or not math.isfinite(value)
        ):
            raise ConfigError(f"{key}: must be a finite number")
        return float(value)
    if kind == "str":
        if not isinstance(value, str) or not value:
            raise ConfigError(f"{key}: must be a non-empty string")
        return value
    if kind == "offsets":
        if not isinstance(value, Mapping) or set(value) != set(FEATURE_KEYS):
            raise ConfigError(f"{key}: must have exactly the 19 feature keys")
        return {k: _typed_number(key, value[k]) for k in FEATURE_KEYS}
    return _explanations(key, value)


def _typed_number(key: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        raise ConfigError(f"{key}: values must be finite numbers")
    return float(value)


def _explanations(key: str, value: Any) -> tuple[ReviewExplanation, ...]:
    if not isinstance(value, Sequence) or isinstance(value, str) or not 1 <= len(value) <= 20:
        raise ConfigError(f"{key}: must be a list of 1 to 20 entries")
    out = []
    for item in value:
        if isinstance(item, ReviewExplanation):
            item = {"code": item.code, "label": item.label}
        if not isinstance(item, Mapping) or set(item) != {"code", "label"}:
            raise ConfigError(f"{key}: each entry needs exactly code and label")
        code, label = item["code"], item["label"]
        if not isinstance(code, str) or not code or code != code.lower():
            raise ConfigError(f"{key}: codes must be non-empty lower-case strings")
        if not isinstance(label, str) or not label:
            raise ConfigError(f"{key}: labels must be non-empty strings")
        out.append(ReviewExplanation(code, label))
    if len({e.code for e in out}) != len(out):
        raise ConfigError(f"{key}: codes must be unique")
    return tuple(out)


def _validate(v: dict[str, Any]) -> None:
    checks = (
        ("screen_min_n", v["screen_min_n"] >= 1),
        ("baseline_n", v["baseline_n"] >= v["screen_min_n"]),
        ("mad_scale", v["mad_scale"] > 0),
        ("pause_floor", v["pause_floor"] >= 0),
        ("composite_floor", v["composite_floor"] >= 0),
        ("cusum_k", v["cusum_k"] >= 0),
        ("cusum_h", v["cusum_h"] > 0),
        ("morning_cutoff_hour", 0 <= v["morning_cutoff_hour"] <= 24),
        ("data_alert_set_aside_fraction", 0 < v["data_alert_set_aside_fraction"] <= 1),
        ("data_alert_device_silent_days", v["data_alert_device_silent_days"] >= 1),
        ("alert_snooze_hours", 1 <= v["alert_snooze_hours"] <= 168),
    )
    for key, ok in checks:
        if not ok:
            raise ConfigError(f"{key}: value {v[key]!r} is out of range")
    try:
        ZoneInfo(v["facility_tz"])
    except (ZoneInfoNotFoundError, ValueError):
        raise ConfigError(f"facility_tz: unknown time zone {v['facility_tz']!r}") from None


_MORNING_OFFSETS = {spec.key: spec.morning_offset for spec in FEATURES}
_EXPLANATIONS = (
    ("cold_cough_sore_throat", "Cold, cough or sore throat"),
    ("dental_dentures", "Dental problem or dentures out"),
    ("medication_change", "New or changed medication"),
    ("poor_sleep_unusual_day", "Poor sleep or unusual day"),
    ("room_device_moved", "Room or device moved"),
)


def _profile(profile: str, baseline_n: int) -> PipelineConfig:
    return PipelineConfig.from_mapping(
        {
            "profile": profile, "facility_tz": "America/Chicago", "noise_limit_dbfs": -40.0,
            "min_speech_s": 1.0, "baseline_n": baseline_n, "screen_min_n": 5,
            "screen_f0_z": 4.0, "screen_other_z": 3.0, "screen_other_count": 2,
            "mad_scale": 1.4826, "pause_floor": 0.5, "composite_floor": 0.1, "cusum_k": 0.5,
            "cusum_h": 5.0, "morning_cutoff_hour": 12, "morning_offsets": _MORNING_OFFSETS,
            "shared_device_min_residents": 2, "data_alert_set_aside_fraction": 0.20,
            "data_alert_device_silent_days": 2, "data_alert_baseline_stalled_enabled": True,
            "alert_snooze_hours": 24,
            "review_explanations": [{"code": c, "label": lbl} for c, lbl in _EXPLANATIONS],
        }
    )  # fmt: skip


# TRD 07 §4.7 and the TRD 20 §4.11 seed (ANL-028): equal except `profile` and `baseline_n`.
PRODUCTION = _profile("production", 30)
TEST_V0_1 = _profile("test_v0_1", 16)
