"""Baseline membership, freeze, per-feature and composite baseline (TRD 08 §4.6-§4.7;
FEAT-045)."""

from __future__ import annotations

import math

import pytest

from tests.unit.analytics.src05 import result

pytestmark = pytest.mark.unit


def _baseline(resident: str, feature: str) -> object:
    return next(b for b in result().baselines if b.resident_code == resident
                and b.feature_key == feature)  # fmt: skip


@pytest.mark.req("BSC-034", "AC-BSC-02", "FEAT-045-AC-01")
def test_twenty_rows_per_formed_epoch() -> None:
    assert len(result().baselines) == 180
    keys = {(b.resident_code, b.epoch_number) for b in result().baselines}
    assert len(keys) == 9
    assert ("R08", 1) not in keys
    assert ("R07", 1) not in keys


@pytest.mark.req("BSC-026", "BSC-028", "BSC-029", "FEAT-045-AC-02")
def test_freeze_points_skip_non_usable_records() -> None:
    frozen = {b.resident_code: b.frozen_after_session_id for b in result().baselines
              if b.feature_key == "composite"}  # fmt: skip
    assert frozen["R02"] == "R02-20261021-01"
    assert frozen["R03"] == "R03-20261023-01"
    assert frozen["R05"] == "R05-20261017-01"
    assert frozen["R09"] == "R09-20261016-01"
    r09 = _baseline("R09", "composite")
    assert (r09.first_session_id, r09.n_sessions) == ("R09-20261001-01", 16)  # type: ignore[attr-defined]


@pytest.mark.req("BSC-031", "BSC-033", "AC-BSC-06", "FEAT-045-AC-03")
def test_r09_worked_example() -> None:
    loud = _baseline("R09", "loudness_dbfs")
    assert math.isclose(loud.median, -22.405, abs_tol=1e-9)  # type: ignore[attr-defined]
    assert math.isclose(loud.mad, 1.45, abs_tol=1e-9)  # type: ignore[attr-defined]
    assert math.isclose(loud.robust_spread, 2.149770, abs_tol=1e-6)  # type: ignore[attr-defined]
    comp = _baseline("R09", "composite")
    assert math.isclose(comp.median, 0.038219, abs_tol=1e-6)  # type: ignore[attr-defined]
    assert math.isclose(comp.mad, 0.359758, abs_tol=1e-6)  # type: ignore[attr-defined]
    assert math.isclose(comp.robust_spread, 0.533378, abs_tol=1e-6)  # type: ignore[attr-defined]
    assert comp.floor_applied is False  # type: ignore[attr-defined]


@pytest.mark.req("BSC-003", "BSC-004", "FEAT-045-AC-04")
def test_pause_floor_rows() -> None:
    floored = [b for b in result().baselines if b.floor_applied]
    assert len(floored) == 8
    assert {b.feature_key for b in floored} == {"number_of_pauses"}
    assert all(b.mad == 0 and b.robust_spread == 0.5 for b in floored)


@pytest.mark.req("BSC-025", "BSC-027", "VC-R08", "FEAT-045-AC-05")
def test_membership_and_forming_epochs() -> None:
    epochs = {(e.resident_code, e.epoch_number): e for e in result().epochs}
    assert (epochs[("R08", 1)].usable_count, epochs[("R08", 1)].baseline_formed) == (13, False)
    assert (epochs[("R07", 1)].usable_count, epochs[("R07", 1)].baseline_formed) == (12, False)
    assert epochs[("R07", 2)].frozen_after_session_id == "R07-20261028-01"
    in_base = [s for s in result().sessions if s.in_baseline]
    # the first N usable sessions of an epoch that never forms are marked too (SRC-03 R07, R08)
    assert len(in_base) == 9 * 16 + 12 + 13
    assert all(s.baseline_ordinal is not None and s.baseline_ordinal <= 16 for s in in_base)
