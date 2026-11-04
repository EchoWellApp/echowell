"""The robustness script itself (TRD 14 TDV-080..TDV-083; FEAT-061).

The 100-seed run is informational and nightly only; here the script is exercised on the fixture
seed, where the eight no-change residents never alarm and the output reproduces the seed's answer
key, and its publishing step is checked on a scratch copy of the report.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.validation import report, robustness

pytestmark = pytest.mark.validation

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.req("TDV-080", "TDV-082", "FEAT-061-FR-01", "FEAT-061-FR-04", "FEAT-061-FR-06")
def test_fixture_seed_has_no_false_alarm_and_reproduces(tmp_path: Path) -> None:
    alarmed, comparison = robustness.run_seed(20261004, tmp_path)
    assert alarmed == set()
    assert comparison.checks > 10_000
    assert comparison.mismatches == []
    assert sorted(p.name for p in (tmp_path / "20261004").iterdir()) == [
        "EchoWell_pipeline_test_input_v0_1.csv", "EchoWell_pipeline_test_v0_1.xlsx"]  # fmt: skip


@pytest.mark.req("TDV-081", "FEAT-061-FR-02", "FEAT-061-FR-03")
def test_publish_fills_section_7_only(tmp_path: Path) -> None:
    (tmp_path / report.MARKDOWN).write_text(
        "# ALGORITHM_VALIDATION_REPORT\n\nOverall: PASS\n\n"
        "## 7. Informational: false-alarm robustness (not gating)\n\nNot run.\n",
        encoding="utf-8",
    )
    (tmp_path / report.JSON).write_text(json.dumps({"overall": "PASS", "robustness": None}),
                                        encoding="utf-8")  # fmt: skip
    result = {"generated_at": "2026-11-02T03:00:00Z", "seeds": "1..100", "false_alarms": 61,
              "denominator": 600, "rate": 61 / 600,
              "per_resident": {f"R0{n}": 10 for n in range(1, 9)},
              "reproduction_mismatches": 0, "mismatched_seeds": []}  # fmt: skip
    robustness.publish(result, tmp_path)
    data = json.loads((tmp_path / report.JSON).read_text(encoding="utf-8"))
    assert data == {"overall": "PASS", "robustness": result}
    text = (tmp_path / report.MARKDOWN).read_text(encoding="utf-8")
    assert "Overall: PASS" in text
    assert "rate 10.2% (61 of 600)" in text
    assert "Not run." not in text


@pytest.mark.req("TDV-083", "TST-084", "FEAT-061-FR-05")
def test_not_part_of_the_gating_selection() -> None:
    """`pytest tests/validation` collects only `test_*.py`, so the 100-seed run never gates."""
    assert Path(robustness.__file__).name == "robustness.py"
