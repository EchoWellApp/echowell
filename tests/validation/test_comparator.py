"""Comparator self-tests (TRD 14 TDV-032..TDV-037, TDV-040..TDV-042; FEAT-058-AC-04;
FEAT-058 testing requirements)."""

from __future__ import annotations

import copy
import math

import pytest

from tests.validation.comparator import Column, compare_sheet, compare_value
from tests.validation.outputs import Outputs

pytestmark = pytest.mark.validation

FLOAT = Column("cusum_tally", "float", 8)


@pytest.mark.req("TDV-032", "D-26")
def test_tolerance_boundary() -> None:
    assert compare_value("s", "k", FLOAT, 5.0, 5.0 + 0.9e-6) is None
    assert compare_value("s", "k", FLOAT, 0.0, 1e-6) is None
    found = compare_value("s", "k", FLOAT, 5.0, 5.0 + 1.1e-6)
    assert found is not None
    assert found.abs_diff == pytest.approx(1.1e-6)


@pytest.mark.req("TDV-032")
def test_nan_or_missing_actual_fails() -> None:
    assert compare_value("s", "k", FLOAT, 1.0, math.nan) is not None
    assert compare_value("s", "k", FLOAT, 1.0, None) is not None
    assert compare_value("s", "k", FLOAT, math.nan, None) is None  # blank expected cell


@pytest.mark.req("TDV-033", "TDV-034", "TDV-035")
def test_blank_none_and_type_rules() -> None:
    reason = Column("expected_reason", "exact", 2)
    assert compare_value("s", "k", reason, math.nan, None) is None
    assert compare_value("s", "k", reason, math.nan, "") is None
    assert compare_value("s", "k", reason, "noise above limit", "Noise above limit") is not None
    assert compare_value("s", "k", reason, "x ", "x") is not None  # no trimming
    alarm = Column("first_alarm_session", "none_null", 9)
    assert compare_value("s", "k", alarm, "none", None) is None
    assert compare_value("s", "k", alarm, "none", "R09-20261021-01") is not None
    yesno = Column("floor_applied", "yesno", 6)
    assert compare_value("s", "k", yesno, "yes", True) is None
    assert compare_value("s", "k", yesno, "no", True) is not None
    count = Column("n_sessions", "exact", 6)
    assert compare_value("s", "k", count, 16, 16) is None
    assert compare_value("s", "k", count, 16, "16") is not None
    assert compare_value("s", "k", Column("alarm", "alarm", 8), "RINGS (first crossing)",
                         "rings") is None  # fmt: skip


@pytest.mark.req("TDV-036", "TDV-037", "TDV-042", "FEAT-058-AC-04")
def test_mismatches_are_all_recorded_with_stage(tier_a: Outputs) -> None:
    broken = copy.deepcopy(tier_a)
    broken.scores[("R09-20261021-01",)]["cusum_tally"] += 1.1e-6
    broken.scores[("R10-20261024-01",)]["alarm"] = "on"
    result = compare_sheet("Exp_scores", broken)
    found = {(m.key, m.column): m for m in result.mismatches}
    assert set(found) == {("R09-20261021-01", "cusum_tally"), ("R10-20261024-01", "alarm")}
    tally = found[("R09-20261021-01", "cusum_tally")]
    assert (tally.sheet, tally.stage) == ("Exp_scores", 8)
    assert tally.abs_diff is not None
    assert tally.abs_diff > 1e-6
    assert tally.expected == pytest.approx(5.431965, abs=1e-6)
    assert found[("R10-20261024-01", "alarm")].expected == "rings"
    del broken.baselines[("R01", 1, "COMPOSITE (raw signed mean of 7 z)")]
    broken.baselines[("R08", 1, "loudness_dbfs")] = {}
    rows = compare_sheet("Exp_baselines", broken)
    assert {(m.key, m.column, m.expected, m.actual) for m in rows.mismatches} == {
        ("R01/1/COMPOSITE (raw signed mean of 7 z)", "(row)", "present", "absent"),
        ("R08/1/loudness_dbfs", "(row)", "absent", "present"),
    }  # fmt: skip


@pytest.mark.req("TDV-037")
def test_stage_follows_the_status(tier_a: Outputs) -> None:
    broken = copy.deepcopy(tier_a)
    broken.annotated[("R03", 18, 71)]["expected_status"] = "usable"
    broken.annotated[("R05", 8, 122)]["expected_status"] = "usable"
    stages = {m.key: m.stage for m in compare_sheet("Annotated_sessions", broken).mismatches
              if m.column == "expected_status"}  # fmt: skip
    assert stages == {"R03/18/71": 2, "R05/8/122": 4}
