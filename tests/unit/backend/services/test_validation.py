"""Record validation, the schema-version registry and feature-name mapping (TRD 10 §4.2-§4.5;
FEAT-023)."""

from __future__ import annotations

import csv
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest

from backend.services import validation
from backend.services.validation import (
    CANONICAL_FIELDS,
    DeviceInfo,
    NameMapError,
    ResidentInfo,
    ValidationContext,
)

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[4]
ROSTER = ROOT / "database" / "seeds" / "test_v0_1"
SRC_05 = ROOT / "tests" / "fixtures" / "pipeline_input" / "EchoWell_pipeline_test_input_v0_1.csv"
IDENTITY = {name: name for name in CANONICAL_FIELDS}


def _rows(name: str) -> list[dict[str, str]]:
    with (ROSTER / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _context(**overrides: Any) -> ValidationContext:
    residents = {
        r["resident_code"]: ResidentInfo(
            "active", date.fromisoformat(r["enrolled_on"]), r["sex"] or None
        )
        for r in _rows("residents.csv")
    }
    devices = {
        d["device_code"]: DeviceInfo(d["active"].lower() == "true") for d in _rows("devices.csv")
    }
    context = ValidationContext(
        supported_versions=frozenset({"0.1"}), name_map=IDENTITY, residents=residents,
        devices=devices, facility_tz=ZoneInfo("America/Chicago"),
        received_at=datetime(2026, 10, 31, 12, 0, tzinfo=UTC),
    )  # fmt: skip
    return replace(context, **overrides)


def record(**changes: Any) -> dict[str, Any]:
    """A valid JSON record (SRC-05 row R09-20261021-01 shape, synthetic values)."""
    base: dict[str, Any] = {
        "schema_version": "0.1", "session_id": "R09-20261021-01", "resident_id": "R09",
        "device_id": "D09", "timestamp_utc": "2026-10-21 19:07:50", "mic_noise_level_dbfs": -52.0,
        "audio_quality_flag": "ok", "extraction_software_version": "openSMILE 3.0.2",
        "device_firmware_version": "fw-1.0.0", "speech_duration_s": 2.9, "phrase_id": "P01",
        "loudness_dbfs": -24.0, "total_phrase_duration_s": 3.1, "speech_rate_syl_per_s": 4.2,
        "articulation_rate_syl_per_s": 4.8, "number_of_pauses": 2, "pause_fraction": 0.18,
        "voiced_fraction": 0.62, "mean_f0_hz": 180.0, "f0_variability_st": 2.4,
        "jitter_local_pct": 0.9, "shimmer_local_pct": 3.2, "hnr_db": 18.0, "cpps_db": 12.0,
        "alpha_ratio_db": -14.0, "hammarberg_index_db": 22.0, "mfcc1": 30.0, "mfcc2": 5.0,
        "mfcc3": 1.0, "mfcc4": -1.0,
    }  # fmt: skip
    base.update(changes)
    return base


Check = Callable[..., validation.ValidationResult]


def check(
    raw: Any, source: validation.Source = "json", **context: Any
) -> validation.ValidationResult:
    return validation.validate(raw, source=source, context=_context(**context))


def codes(result: validation.ValidationResult) -> list[tuple[str, str]]:
    return [(e.field, e.code) for e in result.errors]


def test_a_plausible_record_is_accepted_without_warnings() -> None:
    assert _context().residents["R09"].sex == "F"  # mean_f0_hz 180 is plausible for F
    result = check(record())
    assert result.accepted, result.errors
    assert result.warnings == []
    assert result.values["timestamp_utc"] == datetime(2026, 10, 21, 19, 7, 50, tzinfo=UTC)
    assert result.values["number_of_pauses"] == 2


@pytest.mark.req("AC-ING-04", "ING-019", "FEAT-023-AC-01", "FEAT-023-FR-06", "FEAT-023-FR-07")
def test_all_violations_are_collected() -> None:
    result = check(record(pause_fraction=1.2, number_of_pauses=1.5, audio_base64="AAAA"))
    assert sorted(e.code for e in result.errors) == [
        "extra_forbidden",
        "not_integer",
        "out_of_range",
    ]
    assert result.request_code == "VALIDATION_ERROR"
    assert all("AAAA" not in e.message and "1.2" not in e.message for e in result.errors)


@pytest.mark.req("AC-ING-04", "ING-020", "FEAT-023-AC-02", "FEAT-023-FR-17")
def test_implausible_value_is_a_warning() -> None:
    result = check(record(loudness_dbfs=-35))
    assert result.accepted
    assert [(w.field, w.code) for w in result.warnings] == [("loudness_dbfs", "implausible_value")]


@pytest.mark.req("ING-021", "FEAT-023-AC-09", "FEAT-023-FR-08")
def test_json_numbers_and_csv_cells() -> None:
    assert codes(check(record(loudness_dbfs="-30.1"))) == [("loudness_dbfs", "invalid_type")]
    assert codes(check(record(loudness_dbfs=True))) == [("loudness_dbfs", "invalid_type")]
    assert codes(check(record(loudness_dbfs=float("nan")))) == [("loudness_dbfs", "non_finite")]
    as_text = {k: str(v) for k, v in record().items()}
    assert check(as_text, "csv").accepted
    for cell in ("NaN", "inf", "-INF"):
        assert codes(check({**as_text, "loudness_dbfs": cell}, "csv")) == [
            ("loudness_dbfs", "non_finite")
        ]
    assert codes(check({**as_text, "hnr_db": ""}, "csv")) == [("hnr_db", "missing_field")]
    assert codes(check({**as_text, "hnr_db": "x"}, "csv")) == [("hnr_db", "invalid_type")]


@pytest.mark.req("TRD 10 §4.4", "FEAT-023-FR-09")
@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({"number_of_pauses": -1}, ("number_of_pauses", "out_of_range")),
        ({"number_of_pauses": 2.0}, None),
        ({"voiced_fraction": -0.01}, ("voiced_fraction", "out_of_range")),
        ({"mic_noise_level_dbfs": 0.1}, ("mic_noise_level_dbfs", "out_of_range")),
        ({"loudness_dbfs": 0.5}, ("loudness_dbfs", "out_of_range")),
        ({"mean_f0_hz": 0}, ("mean_f0_hz", "out_of_range")),
        ({"speech_duration_s": -0.1}, ("speech_duration_s", "out_of_range")),
        ({"audio_quality_flag": "OK"}, ("audio_quality_flag", "invalid_enum")),
        ({"phrase_id": ""}, ("phrase_id", "invalid_format")),
        (
            {"extraction_software_version": " openSMILE"},
            ("extraction_software_version", "invalid_format"),
        ),
        ({"device_firmware_version": "x" * 65}, ("device_firmware_version", "invalid_format")),
        ({"session_id": "R09-2026102-01"}, ("session_id", "invalid_format")),
        ({"hnr_db": None}, ("hnr_db", "missing_field")),
    ],
)
def test_reject_rules(changes: dict[str, Any], expected: tuple[str, str] | None) -> None:
    assert codes(check(record(**changes))) == ([expected] if expected else [])


def test_a_missing_field_is_reported() -> None:
    raw = record()
    del raw["mfcc4"]
    assert codes(check(raw)) == [("mfcc4", "missing_field")]


def test_csv_whole_numbers() -> None:
    as_text = {k: str(v) for k, v in record().items()}
    assert check({**as_text, "number_of_pauses": "3.0"}, "csv").values["number_of_pauses"] == 3
    assert codes(check({**as_text, "number_of_pauses": "1.5"}, "csv")) == [
        ("number_of_pauses", "not_integer")
    ]


@pytest.mark.req("ING-025", "AC-ING-05", "FEAT-023-AC-03", "FEAT-023-FR-11")
@pytest.mark.parametrize(
    "stamp",
    [
        "2026-10-01T19:45:11Z",
        "2026-10-01 19:45:11Z",
        "2026-10-01 19:45:11.5",
        "2026-10-01 19:45:11+00:00",
        "2026-02-30 10:00:00",
        "2026-10-01 24:00:00",
    ],
)
def test_timestamp_formats(stamp: str) -> None:
    assert codes(check(record(timestamp_utc=stamp))) == [("timestamp_utc", "invalid_format")]


@pytest.mark.req("ING-013", "ING-015", "AC-ING-05", "FEAT-023-AC-03", "FEAT-023-FR-05")
def test_schema_versions() -> None:
    result = check(record(schema_version="0.2"))
    assert codes(result) == [("schema_version", "unsupported_schema_version")]
    assert result.request_code == "UNSUPPORTED_SCHEMA_VERSION"
    assert codes(check(record(schema_version=0.1))) == [("schema_version", "invalid_type")]
    assert codes(check(record(schema_version=" 0.1"))) == [
        ("schema_version", "unsupported_schema_version")
    ]
    assert not check(record(), supported_versions=frozenset()).accepted


@pytest.mark.req("ING-014", "FEAT-023-FR-04")
def test_validator_registry() -> None:
    assert validation.VALIDATORS == {"0.1": validation.validate_v0_1}


@pytest.mark.req("API-036", "API-037", "API-038", "API-039", "FEAT-023-FR-13", "FEAT-023-FR-14",
                 "FEAT-023-FR-15", "FEAT-023-AC-04")  # fmt: skip
def test_roster_checks_and_request_codes() -> None:
    unknown = check(record(resident_id="R11", session_id="R11-20261021-01"))
    assert codes(unknown) == [("resident_id", "unknown_resident")]
    assert unknown.request_code == "UNKNOWN_RESIDENT"
    assert check(record(device_id="D99")).request_code == "UNKNOWN_DEVICE"
    mismatch = check(record(session_id="R08-20261021-01"))
    assert codes(mismatch) == [("session_id", "session_id_mismatch")]
    assert mismatch.request_code == "SESSION_ID_MISMATCH"
    residents = dict(_context().residents)
    residents["R09"] = replace(residents["R09"], status="withdrawn")
    withdrawn = check(record(), residents=residents)
    assert withdrawn.request_code == "RESIDENT_WITHDRAWN"
    assert withdrawn.errors[0].message == "resident withdrawn"
    both = check(record(schema_version="0.2", resident_id="R11", session_id="R11-20261021-01"))
    assert both.request_code == "UNSUPPORTED_SCHEMA_VERSION"  # first in the ING-004 order


@pytest.mark.req("ING-023", "ING-027", "ING-028", "FEAT-023-FR-12", "FEAT-023-FR-18")
def test_warnings() -> None:
    # 2026-10-22 03:00 UTC is 2026-10-21 22:00 in Chicago: the local date matches session_id.
    assert check(record(timestamp_utc="2026-10-22 03:00:00")).warnings == []
    late = check(record(timestamp_utc="2026-10-22 06:00:00"))
    assert [(w.field, w.code) for w in late.warnings] == [
        ("session_id", "session_id_date_mismatch")
    ]
    future = check(record(timestamp_utc="2026-11-01 12:00:01", session_id="R09-20261101-01"))
    assert [w.code for w in future.warnings] == ["timestamp_in_future"]
    early = check(record(timestamp_utc="2026-09-01 18:00:00", session_id="R09-20260901-01"))
    assert [w.code for w in early.warnings] == ["before_enrollment"]
    devices = {**_context().devices, "D09": DeviceInfo(active=False)}
    assert [w.code for w in check(record(), devices=devices).warnings] == ["device_inactive"]


@pytest.mark.req("TRD 10 §4.4")
@pytest.mark.parametrize(
    ("sex", "f0", "warned"),
    [("F", 150.0, True), ("M", 150.0, True), (None, 150.0, False), ("M", 120.0, False)],
)
def test_mean_f0_range_depends_on_sex(sex: str | None, f0: float, warned: bool) -> None:
    residents = dict(_context().residents)
    residents["R09"] = replace(residents["R09"], sex=sex)
    result = check(record(mean_f0_hz=f0), residents=residents)
    assert ("mean_f0_hz" in {w.field for w in result.warnings}) is warned


@pytest.mark.req("ING-022", "FEAT-023-FR-10")
def test_text_is_kept_exactly() -> None:
    result = check(record(phrase_id="p 01 ", extraction_software_version="openSMILE 3.0.2"))
    assert result.values["phrase_id"] == "p 01 "


@pytest.mark.req("ING-016", "ING-018", "FEAT-023-FR-01", "FEAT-023-AC-05")
def test_name_mapping() -> None:
    raw = record()
    raw["Loudness_sma3_amean"] = raw.pop("loudness_dbfs")
    name_map = validation.check_name_map({"Loudness_sma3_amean": "loudness_dbfs"})
    result = check(raw, name_map=name_map)
    assert result.accepted
    assert result.values["loudness_dbfs"] == -24.0
    assert "Loudness_sma3_amean" in raw  # the caller's payload is not changed
    both = {**raw, "loudness_dbfs": -24.0}
    assert codes(check(both, name_map=name_map)) == [("loudness_dbfs", "extra_forbidden")]


@pytest.mark.req("ING-017", "FEAT-023-AC-06", "FEAT-023-FR-02")
@pytest.mark.parametrize(
    "bad",
    [
        {"A": "loudness_dbfs", "B": "loudness_dbfs"},
        {"loudness_dbfs": "hnr_db"},
        {"A": "not_a_field"},
        {"A": 1},
        [],
    ],
)
def test_invalid_name_maps_are_refused(bad: Any) -> None:
    with pytest.raises(NameMapError):
        validation.check_name_map(bad)


def test_the_seeded_identity_map_is_valid() -> None:
    assert validation.check_name_map(IDENTITY) == IDENTITY


@pytest.mark.req("ING-031", "ING-053", "ING-055", "FEAT-026-FR-05", "FEAT-026-FR-06")
def test_csv_header_errors() -> None:
    assert validation.csv_header_errors(list(CANONICAL_FIELDS), IDENTITY) == []
    shuffled = list(reversed(CANONICAL_FIELDS))
    assert validation.csv_header_errors(shuffled, IDENTITY) == []
    header = [*CANONICAL_FIELDS[:-1], "expected_status"]
    errors = validation.csv_header_errors(header, IDENTITY)
    assert [(e.field, e.code) for e in errors] == [
        ("expected_status", "extra_forbidden"),
        ("mfcc4", "missing_field"),
    ]


@pytest.mark.req("ING-024", "FEAT-023-AC-07", "FEAT-023-FR-20")
def test_every_src_05_row_validates() -> None:
    with SRC_05.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 283
    context = _context()
    for number, row in enumerate(rows, start=1):
        result = validation.validate(row, source="csv", context=context)
        assert result.accepted, (number, result.errors)
