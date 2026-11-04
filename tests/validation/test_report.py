"""The validation report writer (TRD 14 §4.10, TDV-070, TDV-071; FEAT-059-FR-12, FEAT-059-FR-13,
FEAT-059-AC-07)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.validation import report
from tests.validation.comparator import Mismatch, Result

pytestmark = pytest.mark.validation

SCHEMA_KEYS = {"generated_at", "git_sha", "profile", "config_snapshot_sha256", "inputs",
               "tolerance_abs", "overall", "cases", "supplementary", "robustness"}  # fmt: skip


def _all_passing() -> report.Results:
    results = report.Results(config_snapshot={"baseline_n": 16})
    for case in report.CASES:
        for tier in ("A", "B"):
            if not (tier == "A" and case in report.TIER_B_ONLY):
                results.record(case, tier, Result(3, []))
    for check in ("VC-R04-INV", "VC-R10-FRZ", "VC-R06-MUT"):
        results.record_supplementary(check, Result(1, []))
    return results


@pytest.mark.req("TDV-070", "FEAT-059-FR-12", "FEAT-059-AC-04")
def test_passing_run(tmp_path: Path) -> None:
    data = report.write(_all_passing(), tmp_path)
    assert set(data) == SCHEMA_KEYS
    assert data["overall"] == "PASS"
    assert len(data["cases"]) == 22
    assert data["supplementary"] == {"VC-R04-INV": "PASS", "VC-R10-FRZ": "PASS",
                                     "VC-R06-MUT": "PASS"}  # fmt: skip
    assert [c["tier_a"] for c in data["cases"] if c["id"] == "VC-G11"] == ["n/a"]
    text = (tmp_path / report.MARKDOWN).read_text(encoding="utf-8")
    assert text.startswith("# ALGORITHM_VALIDATION_REPORT\n")
    assert "\nOverall: PASS\n" in text
    for heading in (
        "## 1. Summary",
        "## 2. Passed cases",
        "## 3. Failed cases",
        "## 4. Root cause analysis",
        "## 5. Recommended fixes",
        "## 6. Supplementary checks",
        "## 7. Informational: false-alarm robustness (not gating)",
    ):
        assert heading in text
    assert json.loads((tmp_path / report.JSON).read_text(encoding="utf-8")) == data


@pytest.mark.req("TDV-070", "TDV-071", "FEAT-059-FR-13", "FEAT-059-FR-14", "FEAT-059-AC-07")
def test_failing_case_and_zero_checks(tmp_path: Path) -> None:
    results = _all_passing()
    mismatch = Mismatch("Exp_scores", "R09-20261021-01", "cusum_tally", 5.431965, 5.4319661,
                        1.1e-6, 8)  # fmt: skip
    results.record("VC-R09", "B", Result(14, [mismatch]))
    data = report.write(results, tmp_path)
    text = (tmp_path / report.MARKDOWN).read_text(encoding="utf-8")
    assert data["overall"] == "FAIL"
    assert "Overall: FAIL (1 of 22 cases failed)" in text
    assert "### VC-R09 Step change" in text
    assert (
        "| Exp_scores | R09-20261021-01 | cusum_tally | 5.431965 | 5.4319661 | 1.1e-06 | 8 |"
        in text
    )
    assert "8 CUSUM" in text
    results.record("VC-R01", "A", Result(0, []))
    assert report.overall(results) == ("FAIL", 2)  # a case with 0 checks fails (TDV-071)
    missing = report.Results()
    assert report.overall(missing) == ("FAIL", 22)


@pytest.mark.req("TDV-070")
def test_gating_supplementary_check_fails_overall() -> None:
    results = _all_passing()
    results.record_supplementary("VC-R10-FRZ", Result(1, [
        Mismatch("baselines", "R10", "row", 1, 2, None, 6)]))  # fmt: skip
    assert report.overall(results)[0] == "FAIL"
    results = _all_passing()
    results.record_supplementary("VC-R06-MUT", Result(1, [
        Mismatch("Exp_baselines", "R06", "row", 1, 2, None, 6)]))  # fmt: skip
    assert report.overall(results)[0] == "PASS"  # VC-R06-MUT is a Should, not gating


@pytest.mark.req("TDV-073", "D-137")
def test_only_a_full_session_is_complete() -> None:
    assert report.complete(_all_passing())
    partial = report.Results()
    partial.record("VC-R09", "A", Result(3, []))
    partial.record("VC-R09", "B", Result(3, []))
    assert not report.complete(partial)
    missing_tier = _all_passing()
    del missing_tier.cases["VC-G11"]["B"]
    assert not report.complete(missing_tier)
    no_supplementary = _all_passing()
    del no_supplementary.supplementary["VC-R10-FRZ"]
    assert not report.complete(no_supplementary)
