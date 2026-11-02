"""Golden files, answer-key integrity and separation (TRD 14 TDV-010..TDV-016, TDV-020, TDV-023,
TDV-024, TDV-100; TRD 13 TST-070, TST-071; FEAT-057).

The generator is never imported: it runs as `python -I` in a temporary directory (TDV-024).
"""

from __future__ import annotations

import hashlib
import math
import re
import shutil
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import openpyxl
import pytest

from tests.validation import diff_answer_key
from tests.validation.answer_key import (
    GROUND_TRUTH,
    INPUT_CSV,
    ROOT,
    WORKBOOK,
    blank,
    read_sheets,
    rows,
)

pytestmark = pytest.mark.validation

SPECS_WORKBOOK = ROOT / "specs" / "business-requirements" / WORKBOOK.name
SPECS_CSV = ROOT / "specs" / "data-samples" / INPUT_CSV.name
GENERATOR = ROOT / "specs" / "algorithm" / "generate_pipeline_test_v0_1.py"
SHA256SUMS = WORKBOOK.parent / "SHA256SUMS"
BASELINE = {
    "answer_key/EchoWell_pipeline_test_v0_1.xlsx":
        "ddbc03ea6fef37388d2f0265902096cc0fe28559d36cb2855f63ec51ec482257",
    "pipeline_input/EchoWell_pipeline_test_input_v0_1.csv":
        "78e77faad423f305dfb83429ccd21978f089e843c181b5d244a5d7d4f5fabe28",
}  # fmt: skip
SEED = "20261004"
FORBIDDEN = re.compile(r"answer_key|Exp_|EchoWell_pipeline_test_v0_1\.xlsx|openpyxl")
SCANNED = ("analytics", "backend", "frontend/app", "frontend/components", "frontend/lib",
           "frontend/services", "database")  # fmt: skip
SCAN_EXEMPT = ("backend/services/analytics_summary.py", "database/seeds/")
TEXT_SUFFIXES = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".sql",
    ".json",
    ".md",
    ".csv",
    ".ini",
    ".toml",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.req("TST-070", "TST-071", "TDV-013", "TDV-014", "FEAT-057-FR-01", "FEAT-057-FR-02",
                 "FEAT-057-AC-01")  # fmt: skip
def test_golden_files_match_specs_and_checksums() -> None:
    assert WORKBOOK.read_bytes() == SPECS_WORKBOOK.read_bytes()
    assert INPUT_CSV.read_bytes() == SPECS_CSV.read_bytes()
    listed = {}
    for line in SHA256SUMS.read_text(encoding="utf-8").splitlines():
        digest, name = line.split(maxsplit=1)
        listed[name] = digest
    assert listed == BASELINE
    fixtures = WORKBOOK.parents[1]
    for name, digest in BASELINE.items():
        assert _sha256(fixtures / name) == digest, name


def _same_cell(a: Any, b: Any) -> bool:
    if blank(a) and blank(b):
        return True
    if isinstance(a, int | float) and isinstance(b, int | float) and not isinstance(a, bool):
        return math.isclose(float(a), float(b), rel_tol=0.0, abs_tol=1e-12)
    return bool(a == b)


@pytest.mark.req("TDV-020", "TDV-024", "FEAT-057-FR-03", "FEAT-057-AC-02")
def test_regeneration_reproduces_the_golden_files(tmp_path: Path) -> None:
    done = subprocess.run(  # noqa: S603 - fixed interpreter and script, never imported
        [sys.executable, "-I", str(GENERATOR), str(tmp_path), SEED],
        capture_output=True, text=True, timeout=300, check=False,
    )  # fmt: skip
    assert done.returncode == 0, done.stderr
    assert (tmp_path / INPUT_CSV.name).read_bytes() == INPUT_CSV.read_bytes()
    regenerated, golden = read_sheets(tmp_path / WORKBOOK.name), read_sheets(WORKBOOK)
    assert list(regenerated) == list(golden)
    for sheet, frame in golden.items():
        fresh = regenerated[sheet]
        assert list(fresh.columns) == list(frame.columns), sheet
        assert fresh.shape == frame.shape, sheet
        for (i, j), value in _cells(frame):
            assert _same_cell(fresh.iat[i, j], value), f"{sheet}[{i},{frame.columns[j]}]"


def _cells(frame: Any) -> list[tuple[tuple[int, int], Any]]:
    return [((i, j), frame.iat[i, j]) for i in range(frame.shape[0]) for j in range(frame.shape[1])]


@pytest.mark.req("TDV-100", "FEAT-057-FR-09")
def test_ground_truth_agrees_with_test_plan() -> None:
    lines = GROUND_TRUTH.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "resident_code,planted_change,true_onset_date,source_file"
    truth = {line.split(",")[0]: line.split(",")[1:] for line in lines[1:]}
    assert list(truth) == [f"R{n:02d}" for n in range(1, 11)]
    plan = {r["resident_id"]: r for r in rows("Test_plan")}
    for code, (change, onset, source) in truth.items():
        assert source == WORKBOOK.name
        outcome = str(plan[code]["correct_outcome"])
        if code == "R09":
            assert plan[code]["test_case"] == "Step change"
            match = re.search(r"rings at R09-(\d{8})-01, the true onset day", outcome)
            assert match is not None
            assert (change, onset) == ("Sudden step", _iso(match.group(1)))
        elif code == "R10":
            assert plan[code]["test_case"] == "Gradual drift"
            match = re.search(r"true onset on day (\d+)", outcome)
            assert match is not None
            day = date(2026, 10, 1) + timedelta(days=int(match.group(1)) - 1)
            assert (change, onset) == ("Slow drift", day.isoformat())
        else:
            assert "onset" not in outcome
            assert (change, onset) == ("None", "")


def _iso(compact: str) -> str:
    return f"{compact[:4]}-{compact[4:6]}-{compact[6:]}"


@pytest.mark.req("TDV-010", "TDV-012", "FEAT-057-FR-04")
def test_pipeline_input_folder_holds_only_ds01() -> None:
    names = sorted(p.name for p in INPUT_CSV.parent.iterdir())
    assert names == [INPUT_CSV.name]
    assert not [n for n in names if n.endswith(".xlsx") or "answer_key" in n or "Exp_" in n]
    assert GROUND_TRUTH.parent.name == "answer_key"


def _scanned_files() -> list[Path]:
    found = []
    for top in SCANNED:
        base = ROOT / top
        if not base.exists():
            continue
        for path in base.rglob("*"):
            relative = path.relative_to(ROOT).as_posix()
            if (path.is_file() and path.suffix in TEXT_SUFFIXES and "node_modules" not in relative
                    and "__pycache__" not in relative
                    and not relative.startswith(SCAN_EXEMPT)):  # fmt: skip
                found.append(path)
    return found


@pytest.mark.req("TDV-011", "AGT-007", "FEAT-057-FR-05", "FEAT-057-AC-03")
def test_no_production_code_reads_the_answer_key() -> None:
    offenders = [p.relative_to(ROOT).as_posix() for p in _scanned_files()
                 if FORBIDDEN.search(p.read_text(encoding="utf-8", errors="replace"))]  # fmt: skip
    assert offenders == []
    cli = (ROOT / "backend" / "cli.py").read_text(encoding="utf-8")
    assert "evaluation_ground_truth" not in cli
    assert "load_evaluation_ground_truth" not in cli


@pytest.mark.req("TDV-005", "D-25", "FEAT-057-FR-11", "FEAT-057-AC-07")
def test_legacy_file_is_only_a_negative_ingest_fixture() -> None:
    legacy = ROOT / "tests" / "fixtures" / "legacy" / "echowell_mock_data_500.csv"
    assert legacy.read_bytes() == (ROOT / "specs" / "data-samples" / legacy.name).read_bytes()
    users = sorted(
        p.relative_to(ROOT).as_posix() for p in (ROOT / "tests").rglob("*.py")
        if legacy.name in p.read_text(encoding="utf-8") and p.name != Path(__file__).name
    )  # fmt: skip
    assert users == ["tests/integration/api/test_ingest.py"]
    assert "speech_feature_1" not in (ROOT / "backend" / "services" / "validation.py").read_text(
        encoding="utf-8"
    )


@pytest.mark.req("TDV-023", "TST-073", "FEAT-057-FR-07", "FEAT-057-AC-06")
def test_diff_answer_key_prints_the_changed_cell(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    changed = tmp_path / "changed.xlsx"
    shutil.copyfile(WORKBOOK, changed)
    book = openpyxl.load_workbook(changed)
    sheet = book["Exp_scores"]
    header = [c.value for c in sheet[1]]
    row = next(r for r in sheet.iter_rows(min_row=2) if r[0].value == "R09-20261021-01")
    cell = row[header.index("cusum_tally")]
    old = cell.value
    cell.value = 5.5
    book.save(changed)
    assert diff_answer_key.main([str(WORKBOOK), str(changed)]) == 0
    lines = capsys.readouterr().out.splitlines()
    cells = [line for line in lines if "!" in line]
    assert cells == [f"Exp_scores!R09-20261021-01.cusum_tally: {old} -> 5.5"]
    assert "Exp_scores: rows 98 -> 98" in lines
    assert WORKBOOK.read_bytes() == SPECS_WORKBOOK.read_bytes()  # the golden file is untouched
