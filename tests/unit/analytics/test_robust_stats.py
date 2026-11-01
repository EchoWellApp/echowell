"""robust(): median, MAD, spread with floor (TRD 08 §4.2; FEAT-040-AC-01, AC-02)."""

from __future__ import annotations

import math

import pytest

from analytics.config import ContractError
from analytics.robust_stats import robust

pytestmark = pytest.mark.unit


@pytest.mark.req("BSC-001", "BSC-002", "BSC-003", "BSC-004", "AC-BSC-01", "FEAT-040-AC-01",
                 "FEAT-040-FR-11")  # fmt: skip
@pytest.mark.parametrize(
    ("values", "floor", "expected"),
    [
        ([1, 2, 3, 4], 0.0, (2.5, 1.0, 1.4826, False)),
        ([1, 1, 1, 1, 2, 2], 0.5, (1.0, 0.0, 0.5, True)),
        ([0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2], 0.5, (1.0, 0.5, 0.7413, False)),
    ],
)
def test_vectors(
    values: list[float], floor: float, expected: tuple[float, float, float, bool]
) -> None:
    stats = robust(values, floor, 1.4826)
    assert (stats.median, stats.mad, stats.floor_applied) == (expected[0], expected[1], expected[3])
    assert math.isclose(stats.spread, expected[2], abs_tol=1e-12)


@pytest.mark.req("ROB-03", "FEAT-040-AC-02")
def test_r01_loudness_days_1_to_16() -> None:
    from tests.unit.analytics.src05 import records

    values = [r.features["loudness_dbfs"] for r in records()
              if r.resident_code == "R01" and r.timestamp_utc.day <= 16]  # fmt: skip
    stats = robust(values, 0.0, 1.4826)
    assert len(values) == 16
    assert math.isclose(stats.median, -29.925, abs_tol=1e-6)
    assert math.isclose(stats.mad, 2.165, abs_tol=1e-6)
    assert math.isclose(stats.spread, 3.209829, abs_tol=1e-6)


@pytest.mark.req("BSC-004")
def test_floor_equal_to_scaled_mad_is_not_applied() -> None:
    assert robust([0, 2], 1.4826, 1.4826).floor_applied is False


@pytest.mark.req("BSC-005")
@pytest.mark.parametrize("values", [[], [1.0, float("nan")], [float("inf")]])
def test_refuses_empty_or_non_finite(values: list[float]) -> None:
    with pytest.raises(ContractError):
        robust(values, 0.0, 1.4826)
