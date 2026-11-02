"""Validation harness: both tiers against the answer key, Tier A = Tier B, ground-truth isolation
and the no-skip guard (TRD 14 TDV-030, TDV-031, TDV-101, TDV-102; TRD 13 TST-081, TST-083;
FEAT-058-AC-01..AC-06)."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.pool import NullPool

from tests.support.system import TierB, load_ground_truth
from tests.validation.comparator import SHEETS, Result, compare_outputs, compare_sheet
from tests.validation.outputs import Outputs
from tests.validation.tier_b import collect

pytestmark = pytest.mark.validation

ROOT = Path(__file__).resolve().parents[2]
ROWS = {"Annotated_sessions": 302, "Exp_status_counts": 10, "Exp_resident_outcomes": 11,
        "Exp_baselines": 180, "Exp_morning_offset": 19, "Exp_scores": 98}  # fmt: skip
GROUND_TRUTH_TERMS = re.compile(r"evaluation_ground_truth|true_onset|planted_change")
PIPELINE_CODE = ("analytics", "backend/services/pipeline_runner.py",
                 "backend/services/pipeline_persistence.py", "backend/services/ingestion.py",
                 "backend/services/engine_read.py", "backend/repositories")  # fmt: skip


def _all_sheets(outputs: Outputs) -> Result:
    total = Result()
    for name in SHEETS:
        total += compare_sheet(name, outputs)
    return total


@pytest.mark.req("TDV-030", "TDV-001", "TDV-002", "AC-ANL-01", "FEAT-058-FR-01",
                 "FEAT-058-FR-02", "FEAT-058-AC-01")  # fmt: skip
def test_tier_a_matches_the_answer_key(tier_a: Outputs) -> None:
    result = _all_sheets(tier_a)
    assert result.mismatches == []
    assert {name: len(getattr(tier_a, SHEETS[name].outputs)) for name in SHEETS} == ROWS


@pytest.mark.req("TDV-031", "TST-048", "TST-081", "FEAT-058-FR-03", "FEAT-058-AC-02")
def test_tier_b_matches_the_answer_key(tier_b_harness: TierB, tier_b_outputs: Outputs) -> None:
    assert tier_b_harness.run["status"] == "succeeded"
    assert tier_b_harness.run["as_of"] == "2026-10-30T20:00:00Z"
    assert _all_sheets(tier_b_outputs).mismatches == []


@pytest.mark.req("TST-081", "FEAT-058-FR-12", "FEAT-058-AC-03")
def test_tier_a_equals_tier_b(tier_a: Outputs, tier_b_outputs: Outputs) -> None:
    result = compare_outputs(tier_a, tier_b_outputs)
    assert result.checks > 10_000
    assert result.mismatches == []


def _pipeline_files() -> list[Path]:
    found: list[Path] = []
    for entry in PIPELINE_CODE:
        path = ROOT / entry
        found.extend(sorted(path.rglob("*.py")) if path.is_dir() else [path])
    return found


@pytest.mark.req("TDV-101", "TDV-102", "AC-TDV-12", "FEAT-058-FR-13", "FEAT-058-AC-05")
def test_ground_truth_never_changes_the_outputs(
    tier_b_harness: TierB, tier_b_outputs: Outputs
) -> None:
    offenders = [p.relative_to(ROOT).as_posix() for p in _pipeline_files()
                 if GROUND_TRUTH_TERMS.search(p.read_text(encoding="utf-8"))]  # fmt: skip
    assert offenders == []
    engine = create_engine(tier_b_harness.urls.app, poolclass=NullPool)
    try:
        with engine.connect() as connection, pytest.raises(ProgrammingError, match="permission"):
            connection.execute(text("SELECT count(*) FROM evaluation_ground_truth"))
    finally:
        engine.dispose()
    load_ground_truth(tier_b_harness.urls)
    assert tier_b_harness.select("SELECT count(*) FROM evaluation_ground_truth")[0][0] == 10
    tier_b_harness.run_at_as_of()
    after = collect(tier_b_harness)
    assert compare_outputs(tier_b_outputs, after, "without vs with ground truth").mismatches == []


GUARDED_CONFTEST = "from tests.validation.guard import *  # noqa: F403\n"
SKIPPED_TEST = """import pytest

pytestmark = pytest.mark.validation


def test_left_out():
    pytest.skip("not allowed")


def test_ok():
    assert True
"""


@pytest.mark.req("TST-083", "FEAT-058-FR-14", "FEAT-058-AC-06")
def test_a_skipped_validation_test_fails_the_session(tmp_path: Path) -> None:
    (tmp_path / "conftest.py").write_text(GUARDED_CONFTEST, encoding="utf-8")
    (tmp_path / "test_guarded.py").write_text(SKIPPED_TEST, encoding="utf-8")
    done = subprocess.run(  # noqa: S603 - fixed interpreter and arguments
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-p", "no:randomly",
         "--rootdir", str(tmp_path), "-o", "addopts=", "-o", "markers=validation",
         str(tmp_path)],
        cwd=ROOT, capture_output=True, text=True, timeout=120, check=False,
        env={"PYTHONPATH": str(ROOT), "PATH": "/usr/bin:/bin"},
    )  # fmt: skip
    assert done.returncode != 0, done.stdout
    assert "TST-083" in done.stdout
    assert "test_left_out: skipped" in done.stdout
