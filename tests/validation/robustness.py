"""Informational false-alarm robustness check, not gating (TRD 14 §4.11, TDV-080..TDV-083;
TRD 13 TST-084, TST-151; FEAT-061).

    python -m tests.validation.robustness [--seeds 100]

For each seed 1..N the reference generator writes a fresh input CSV and answer key into a temporary
directory (run with `python -I`, never imported, TDV-024); Tier A runs on that CSV with the
unchanged `test_v0_1` profile; the script records whether any alarm rang for R01-R08 and compares
the output with that seed's own answer key (multi-seed reproduction, TDV-082: a mismatch is an S2
defect for the nightly log). It reports the false-alarm count over R01-R06, the rate over
6 x N resident-runs and per-resident counts (R07 and R08 reported, excluded from the rate), into
`validation_results.json.robustness` and report section 7. It never fails a build and is not
collected by `pytest tests/validation` (the file name does not start with `test_`); the nightly
`nightly-validation` job runs it (FEAT-080, TDV-083).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tests.validation import report
from tests.validation.answer_key import INPUT_CSV, ROOT, WORKBOOK, read_sheets
from tests.validation.comparator import SHEETS, Result, compare_sheet
from tests.validation.outputs import from_result, input_rows, run_tier_a

GENERATOR = ROOT / "specs" / "algorithm" / "generate_pipeline_test_v0_1.py"
NO_CHANGE = tuple(f"R{n:02d}" for n in range(1, 9))
IN_RATE = NO_CHANGE[:6]


def run_seed(seed: int, scratch: Path) -> tuple[set[str], Result]:
    """Residents R01-R08 that alarmed, and the comparison with the seed's own answer key."""
    folder = scratch / str(seed)
    folder.mkdir()
    done = subprocess.run(  # noqa: S603 - fixed interpreter and script, never imported
        [sys.executable, "-I", str(GENERATOR), str(folder), str(seed)],
        capture_output=True, text=True, timeout=300, check=False,
    )  # fmt: skip
    if done.returncode != 0:
        raise RuntimeError(f"generator seed {seed}: {done.stderr}")
    rows = input_rows(folder / INPUT_CSV.name)
    out = from_result(run_tier_a(rows), rows)
    alarmed = {a["resident_id"] for a in out.alerts} & set(NO_CHANGE)
    book = read_sheets(folder / WORKBOOK.name)
    total = Result()
    for name in SHEETS:
        total += compare_sheet(name, out, book=book)
    return alarmed, total


def run(seeds: int) -> dict[str, Any]:
    per_resident = dict.fromkeys(NO_CHANGE, 0)
    mismatched: list[int] = []
    with tempfile.TemporaryDirectory() as scratch:  # never tests/fixtures or specs (TDV-010)
        for seed in range(1, seeds + 1):
            alarmed, comparison = run_seed(seed, Path(scratch))
            for code in alarmed:
                per_resident[code] += 1
            if comparison.mismatches:
                mismatched.append(seed)
                first = comparison.mismatches[0]
                print(f"S2 defect: seed {seed} differs from its answer key "
                      f"({len(comparison.mismatches)} mismatches; first {first.sheet} "
                      f"{first.key} {first.column})", file=sys.stderr)  # fmt: skip
    false_alarms = sum(per_resident[code] for code in IN_RATE)
    denominator = len(IN_RATE) * seeds
    return {
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "seeds": f"1..{seeds}", "false_alarms": false_alarms, "denominator": denominator,
        "rate": false_alarms / denominator, "per_resident": per_resident,
        "reproduction_mismatches": len(mismatched), "mismatched_seeds": mismatched,
    }  # fmt: skip


def publish(robustness: dict[str, Any], directory: Path = report.REPORTS) -> None:
    """Write the result into the JSON and replace report section 7, keeping everything else."""
    json_path, markdown_path = directory / report.JSON, directory / report.MARKDOWN
    data = json.loads(json_path.read_text(encoding="utf-8")) if json_path.exists() else {}
    data["robustness"] = robustness
    json_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    heading = "## 7. Informational: false-alarm robustness (not gating)"
    text = markdown_path.read_text(encoding="utf-8") if markdown_path.exists() else ""
    head = text.split(heading)[0] if heading in text else text
    section = "\n".join([heading, "", *report.robustness_lines(robustness)])
    markdown_path.write_text(f"{head}{section}\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--seeds", type=int, default=100)
    args = parser.parse_args(argv)
    robustness = run(args.seeds)
    publish(robustness)
    print(json.dumps(robustness))
    return 0  # informational: never fails a build (TDV-081)


if __name__ == "__main__":
    raise SystemExit(main())
