"""Ingest record validation, schema-version registry and feature-name mapping (TRD 10 §4.2-§4.5
ING-013..ING-028; TRD 05 API-033..API-040; FEAT-023).

`validate(raw, source=..., context=...)` maps the field names through `feature_name_map`, picks the
validator of `schema_version` from `VALIDATORS` and returns every violation of the record (ING-019)
plus its warnings (ING-020). JSON and CSV records share one code path; only the number and text
parsing differs (ING-021). Messages never contain the submitted value (LOG-043).
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Any, Literal
from zoneinfo import ZoneInfo

from backend.core.errors import FieldError
from backend.models import FEATURE_KEYS

Source = Literal["json", "csv"]

RECORD_FIELDS: tuple[str, ...] = (
    "schema_version",
    "session_id",
    "resident_id",
    "device_id",
    "timestamp_utc",
    "mic_noise_level_dbfs",
    "audio_quality_flag",
    "extraction_software_version",
    "device_firmware_version",
    "speech_duration_s",
    "phrase_id",
)
CANONICAL_FIELDS: tuple[str, ...] = RECORD_FIELDS + FEATURE_KEYS  # the SRC-05 header order

# Columns of the answer key that must never be ingested (ING-053).
ANSWER_KEY_COLUMNS = frozenset(
    {
        "expected_status",
        "expected_reason",
        "expected_morning",
        "expected_epoch",
        "in_baseline",
        "error_mode_tested",
        "test_case",
        "arrival_order",
    }
)

# Request-level code of a rejected record: the first of these whose field code occurs (ING-004).
REQUEST_CODES: tuple[tuple[str, str], ...] = (
    ("unsupported_schema_version", "UNSUPPORTED_SCHEMA_VERSION"),
    ("unknown_resident", "UNKNOWN_RESIDENT"),
    ("unknown_device", "UNKNOWN_DEVICE"),
    ("resident_withdrawn", "RESIDENT_WITHDRAWN"),
    ("session_id_mismatch", "SESSION_ID_MISMATCH"),
)

SESSION_ID = re.compile(r"^([A-Z0-9]{1,16})-(\d{8})-(\d{2})$")
TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
CSV_INTEGER = re.compile(r"^\d+(\.0+)?$")
FUTURE_TOLERANCE = timedelta(hours=24)

# Lower and upper reject bounds of the numeric fields (TRD 10 §4.4 "Reject if").
# (minimum, minimum exclusive, maximum)
_BOUNDS: dict[str, tuple[float | None, bool, float | None]] = {
    "mic_noise_level_dbfs": (None, False, 0.0),
    "speech_duration_s": (0.0, False, None),
    "loudness_dbfs": (None, False, 0.0),
    "total_phrase_duration_s": (0.0, False, None),
    "speech_rate_syl_per_s": (0.0, False, None),
    "articulation_rate_syl_per_s": (0.0, False, None),
    "number_of_pauses": (0.0, False, None),
    "pause_fraction": (0.0, False, 1.0),
    "voiced_fraction": (0.0, False, 1.0),
    "mean_f0_hz": (0.0, True, None),
    "jitter_local_pct": (0.0, False, None),
    "shimmer_local_pct": (0.0, False, None),
}

# Plausibility ranges (TRD 10 §4.4 "Warn if"); placeholders until the v1 rig (ING-020).
PLAUSIBLE: dict[str, tuple[float, float]] = {
    "loudness_dbfs": (-30.0, -18.0),
    "total_phrase_duration_s": (2.0, 4.0),
    "speech_rate_syl_per_s": (3.0, 4.5),
    "articulation_rate_syl_per_s": (4.0, 5.5),
    "number_of_pauses": (0.0, 3.0),
    "pause_fraction": (0.05, 0.25),
    "voiced_fraction": (0.50, 0.75),
    "f0_variability_st": (2.0, 4.5),
    "jitter_local_pct": (0.2, 1.0),
    "shimmer_local_pct": (2.0, 6.0),
    "hnr_db": (10.0, 20.0),
    "cpps_db": (8.0, 16.0),
    "alpha_ratio_db": (-20.0, 0.0),
    "hammarberg_index_db": (15.0, 30.0),
    "mfcc1": (20.0, 40.0),
    "mfcc2": (0.0, 15.0),
    "mfcc3": (-5.0, 10.0),
    "mfcc4": (-10.0, 5.0),
}
MEAN_F0_BY_SEX: dict[str | None, tuple[float, float]] = {
    "F": (165.0, 200.0),
    "M": (110.0, 145.0),
    None: (110.0, 200.0),
}

NUMBER_FIELDS = frozenset({"mic_noise_level_dbfs", "speech_duration_s"} | set(FEATURE_KEYS)) - {
    "number_of_pauses"
}
TEXT_LENGTHS: dict[str, tuple[int, int]] = {
    "extraction_software_version": (1, 64),
    "device_firmware_version": (1, 64),
    "phrase_id": (1, 16),
}


class NameMapError(ValueError):
    """`feature_name_map` breaks ING-017; the application must not start."""


def check_name_map(name_map: Mapping[str, Any]) -> dict[str, str]:
    """Validate a `feature_name_map` value (ING-017) and return it as `{external: canonical}`."""
    if not isinstance(name_map, Mapping):
        raise NameMapError("feature_name_map must be a JSON object")
    targets: dict[str, str] = {}
    for external, canonical in name_map.items():
        if not isinstance(external, str) or not isinstance(canonical, str):
            raise NameMapError("feature_name_map keys and values must be strings")
        if canonical not in CANONICAL_FIELDS:
            raise NameMapError(f"feature_name_map target {canonical!r} is not a schema field")
        if canonical in targets:
            raise NameMapError(
                f"feature_name_map maps {targets[canonical]!r} and {external!r} to {canonical!r}"
            )
        if external in CANONICAL_FIELDS and external != canonical:
            raise NameMapError(f"feature_name_map renames the schema field {external!r}")
        targets[canonical] = external
    return {external: canonical for canonical, external in targets.items()}


@dataclass(frozen=True)
class ResidentInfo:
    status: str
    enrolled_on: date
    sex: str | None


@dataclass(frozen=True)
class DeviceInfo:
    active: bool


@dataclass(frozen=True)
class ValidationContext:
    """What a record is checked against: configuration, roster and the arrival time."""

    supported_versions: frozenset[str]
    name_map: Mapping[str, str]
    residents: Mapping[str, ResidentInfo]
    devices: Mapping[str, DeviceInfo]
    facility_tz: ZoneInfo
    received_at: datetime


@dataclass
class ValidationResult:
    """`errors` empty means accepted; `values` then holds the typed canonical fields."""

    errors: list[FieldError] = field(default_factory=list)
    warnings: list[FieldError] = field(default_factory=list)
    values: dict[str, Any] = field(default_factory=dict)

    @property
    def accepted(self) -> bool:
        return not self.errors

    @property
    def request_code(self) -> str:
        """The problem `type` code of a rejected record (ING-004)."""
        codes = {e.code for e in self.errors}
        return next(
            (req for field_code, req in REQUEST_CODES if field_code in codes), "VALIDATION_ERROR"
        )

    def error(self, name: str, code: str, message: str) -> None:
        self.errors.append(FieldError(name, code, message))

    def warn(self, name: str, code: str, message: str) -> None:
        self.warnings.append(FieldError(name, code, message))


def map_names(
    raw: Mapping[str, Any], name_map: Mapping[str, str], result: ValidationResult
) -> dict[str, Any]:
    """Canonical field → value; unknown names and second names for one field are extra (ING-016)."""
    mapped: dict[str, Any] = {}
    for name, value in raw.items():
        canonical = name_map.get(name, name)
        if canonical not in CANONICAL_FIELDS or canonical in mapped:
            result.error(name, "extra_forbidden", "This field is not part of schema v0.1.")
            continue
        mapped[canonical] = value
    return mapped


def validate(raw: Any, *, source: Source, context: ValidationContext) -> ValidationResult:
    """Every violation and warning of one record (ING-019, ING-020)."""
    result = ValidationResult()
    if not isinstance(raw, Mapping):
        result.error("", "invalid_type", "A record must be a JSON object.")
        return result
    record = map_names(raw, context.name_map, result)
    version = record.get("schema_version")
    if "schema_version" not in record:
        result.error("schema_version", "missing_field", "This field is required.")
    elif not isinstance(version, str):
        result.error("schema_version", "invalid_type", "schema_version must be a string.")
    elif version not in context.supported_versions or version not in VALIDATORS:
        result.error(
            "schema_version", "unsupported_schema_version", "This schema version is not supported."
        )
    validator = VALIDATORS.get(version if isinstance(version, str) else "", validate_v0_1)
    validator(record, source, context, result)
    if result.accepted:
        result.values["schema_version"] = version  # stored as received (ING-015)
    return result


# --- schema v0.1 ------------------------------------------------------------------------------


def _number(value: Any, name: str, source: Source, result: ValidationResult) -> float | None:
    if source == "json":
        if isinstance(value, bool) or not isinstance(value, int | float):
            result.error(name, "invalid_type", f"{name} must be a JSON number.")
            return None
        number = float(value)
    else:
        if not isinstance(value, str) or value == "":
            result.error(name, "missing_field", "This field is required.")
            return None
        try:
            number = float(value)
        except ValueError:
            result.error(name, "invalid_type", f"{name} must be a number.")
            return None
    if not math.isfinite(number):
        result.error(name, "non_finite", f"{name} must be a finite number.")
        return None
    return number


def _bounds(name: str, number: float, result: ValidationResult) -> bool:
    low, exclusive, high = _BOUNDS.get(name, (None, False, None))
    too_low = low is not None and (number <= low if exclusive else number < low)
    too_high = high is not None and number > high
    if too_low or too_high:
        result.error(name, "out_of_range", f"{name} is outside its allowed range.")
        return False
    return True


def _integer(value: Any, source: Source, result: ValidationResult) -> int | None:
    name = "number_of_pauses"
    number = _number(value, name, source, result)
    if number is None:
        return None
    if number < 0:
        result.error(name, "out_of_range", f"{name} is outside its allowed range.")
        return None
    whole = number.is_integer() if source == "json" else bool(CSV_INTEGER.match(str(value)))
    if not whole:
        result.error(name, "not_integer", f"{name} must be a whole number.")
        return None
    return int(number)


def _text(value: Any, name: str, result: ValidationResult) -> str | None:
    if not isinstance(value, str):
        result.error(name, "invalid_type", f"{name} must be a string.")
        return None
    return value  # kept exactly as received (ING-022)


def _timestamp(value: str, result: ValidationResult) -> datetime | None:
    if not TIMESTAMP.match(value):
        result.error("timestamp_utc", "invalid_format", "Use the format YYYY-MM-DD HH:MM:SS (UTC).")
        return None
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")  # noqa: DTZ007 - UTC per ING-025
    except ValueError:
        result.error(
            "timestamp_utc", "invalid_format", "timestamp_utc is not a valid date and time."
        )
        return None
    return parsed.replace(tzinfo=UTC)


def validate_v0_1(
    record: Mapping[str, Any], source: Source, context: ValidationContext, result: ValidationResult
) -> None:
    """The TRD 10 §4.4 rules of schema v0.1: reject rules first, then warnings."""
    values: dict[str, Any] = {}
    for name in CANONICAL_FIELDS:
        if name == "schema_version":
            continue
        if name not in record or (record[name] is None and source == "json"):
            result.error(name, "missing_field", "This field is required.")
            continue
        value = record[name]
        if name == "number_of_pauses":
            values[name] = _integer(value, source, result)
        elif name in NUMBER_FIELDS:
            number = _number(value, name, source, result)
            values[name] = number if number is not None and _bounds(name, number, result) else None
        else:
            values[name] = _text(value, name, result)

    session_id, resident_code = values.get("session_id"), values.get("resident_id")
    device_code, stamp = values.get("device_id"), values.get("timestamp_utc")
    match = None
    if session_id is not None:
        match = SESSION_ID.match(session_id) if len(session_id) <= 64 else None
        if match is None:
            result.error(
                "session_id", "invalid_format", "session_id must look like R01-20261005-01."
            )
        elif resident_code is not None and match.group(1) != resident_code:
            result.error(
                "session_id", "session_id_mismatch", "session_id does not start with resident_id."
            )
    resident = None
    if resident_code is not None:
        resident = context.residents.get(resident_code)
        if len(resident_code) > 16:
            result.error("resident_id", "invalid_format", "resident_id is at most 16 characters.")
        elif resident is None:
            result.error("resident_id", "unknown_resident", "resident_id is not enrolled.")
        elif resident.status == "withdrawn":
            result.error("resident_id", "resident_withdrawn", "resident withdrawn")
    device = None
    if device_code is not None:
        device = context.devices.get(device_code)
        if len(device_code) > 16:
            result.error("device_id", "invalid_format", "device_id is at most 16 characters.")
        elif device is None:
            result.error("device_id", "unknown_device", "device_id is not registered.")
    instant = _timestamp(stamp, result) if stamp is not None else None
    flag = values.get("audio_quality_flag")
    if flag is not None and flag not in ("ok", "poor"):
        result.error("audio_quality_flag", "invalid_enum", "audio_quality_flag must be ok or poor.")
    for name, (shortest, longest) in TEXT_LENGTHS.items():
        text = values.get(name)
        if text is None:
            continue
        stripped = text != text.strip() and name != "phrase_id"
        if not shortest <= len(text) <= longest or stripped:
            result.error(
                name, "invalid_format",
                f"{name} must be {shortest} to {longest} characters without outer spaces.",
            )  # fmt: skip
    if result.errors:
        return

    # no errors, so the timestamp parsed and the roster lookups succeeded
    assert instant is not None  # noqa: S101
    assert resident is not None  # noqa: S101
    assert device is not None  # noqa: S101
    local_date = instant.astimezone(context.facility_tz).date()  # ING-027
    values["timestamp_utc"] = instant
    if match is not None and match.group(2) != local_date.strftime("%Y%m%d"):
        result.warn(
            "session_id", "session_id_date_mismatch",
            "The date in session_id differs from the local date of timestamp_utc.",
        )  # fmt: skip
    if local_date < resident.enrolled_on:
        result.warn("timestamp_utc", "before_enrollment", "The record is from before enrollment.")
    if not device.active:
        result.warn("device_id", "device_inactive", "The device is marked inactive.")
    if instant > context.received_at + FUTURE_TOLERANCE:
        result.warn("timestamp_utc", "timestamp_in_future", "timestamp_utc is in the future.")
    ranges = {**PLAUSIBLE, "mean_f0_hz": MEAN_F0_BY_SEX.get(resident.sex, MEAN_F0_BY_SEX[None])}
    for name, (low, high) in ranges.items():
        if not low <= values[name] <= high:
            result.warn(name, "implausible_value", f"{name} is outside its plausible range.")
    result.values = values


Validator = Callable[[Mapping[str, Any], Source, ValidationContext, ValidationResult], None]

# Schema-version registry (ING-014): a new version adds an entry, existing ones stay unchanged.
VALIDATORS: dict[str, Validator] = {"0.1": validate_v0_1}


def csv_header_errors(header: list[str], name_map: Mapping[str, str]) -> list[FieldError]:
    """Missing and extra columns of a CSV header after name mapping (ING-031, ING-053)."""
    errors: list[FieldError] = []
    seen: set[str] = set()
    for column in header:
        canonical = name_map.get(column, column)
        if column in ANSWER_KEY_COLUMNS or canonical not in CANONICAL_FIELDS or canonical in seen:
            errors.append(
                FieldError(column, "extra_forbidden", "This column is not part of schema v0.1.")
            )
        seen.add(canonical)
    for name in CANONICAL_FIELDS:
        if name not in seen:
            errors.append(FieldError(name, "missing_field", "This column is required."))
    return errors
