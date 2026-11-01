"""Local time, morning flag, adjusted values (TRD 08 §4.5; FEAT-043)."""

from __future__ import annotations

import math
from datetime import UTC, datetime

import pytest

from analytics.config import FEATURE_KEYS, TEST_V0_1
from analytics.morning_offset import adjusted_values, is_morning, local_time

pytestmark = pytest.mark.unit


def _local(text: str) -> tuple[str, str, bool]:
    instant = datetime.strptime(text, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
    local, day = local_time(instant, TEST_V0_1)
    return f"{local:%H:%M:%S %Z}", day.isoformat(), is_morning(local, TEST_V0_1)


@pytest.mark.req("MO-01", "MO-02", "MO-03", "MO-04", "NFR-131", "NFR-132", "BSC-020", "BSC-021",
                 "AGT-040", "FEAT-043-AC-01", "FEAT-043-AC-02", "FEAT-043-AC-03",
                 "FEAT-043-FR-06")  # fmt: skip
@pytest.mark.parametrize(
    ("utc", "expected"),
    [
        ("2026-10-01 16:59:59", ("11:59:59 CDT", "2026-10-01", True)),
        ("2026-10-01 17:00:00", ("12:00:00 CDT", "2026-10-01", False)),
        ("2026-11-01 17:59:59", ("11:59:59 CST", "2026-11-01", True)),
        ("2026-11-01 18:00:00", ("12:00:00 CST", "2026-11-01", False)),
        ("2026-11-01 06:30:00", ("01:30:00 CDT", "2026-11-01", True)),
        ("2026-11-01 07:30:00", ("01:30:00 CST", "2026-11-01", True)),
        ("2027-03-14 08:30:00", ("03:30:00 CDT", "2027-03-14", True)),
        ("2026-10-02 04:59:59", ("23:59:59 CDT", "2026-10-01", False)),
    ],
)
def test_local_time_vectors(utc: str, expected: tuple[str, str, bool]) -> None:
    assert _local(utc) == expected


@pytest.mark.req("MO-05", "BSC-022", "FEAT-043-AC-04", "FEAT-043-FR-04")
def test_r06_day_1_adjustment() -> None:
    raw = dict.fromkeys(FEATURE_KEYS, 1.0) | {
        "loudness_dbfs": -25.42, "total_phrase_duration_s": 4.01, "speech_rate_syl_per_s": 4.14,
        "articulation_rate_syl_per_s": 4.52, "number_of_pauses": 2.0, "pause_fraction": 0.126,
        "voiced_fraction": 0.595,
    }  # fmt: skip
    got = adjusted_values({k: raw[k] for k in FEATURE_KEYS}, True, TEST_V0_1)
    expected = (-23.92, 3.91, 4.26, 4.62, 2.0, 0.116, 0.615)
    for key, value in zip(FEATURE_KEYS[:7], expected, strict=True):
        assert math.isclose(got[key], value, abs_tol=1e-9), key


@pytest.mark.req("MO-06", "MO-07", "FEAT-043-AC-05")
def test_afternoon_and_stored_features_unchanged() -> None:
    raw = {k: float(i) for i, k in enumerate(FEATURE_KEYS)}
    assert adjusted_values(raw, False, TEST_V0_1) == raw
    morning = adjusted_values(raw, True, TEST_V0_1)
    assert all(morning[k] == raw[k] for k in FEATURE_KEYS[7:])


@pytest.mark.req("VC-R06", "FEAT-043-AC-06", "BSC-024")
def test_src05_r06_mornings() -> None:
    from tests.unit.analytics.src05 import result

    mornings = sorted(s.local_date.day for s in result().sessions
                      if s.record.resident_code == "R06" and s.is_morning)  # fmt: skip
    assert mornings == [1, 4, 7, 10, 13, 16, 19, 22, 25, 28]
    scored = sorted(
        s.session_id for s in result().scores if s.resident_code == "R06" and s.is_morning
    )
    assert scored == ["R06-20261019-01", "R06-20261022-01", "R06-20261025-01", "R06-20261028-01"]
