"""The validation report (TRD 14 §4.10, TDV-070..TDV-073; TRD 16 CIC-100, CIC-102; FEAT-059).

Case tests record each tier's comparison `Result` in `RESULTS`; after the session `write` renders
`docs/reports/ALGORITHM_VALIDATION_REPORT.md` and `docs/reports/validation_results.json`. A case
that did not run, or ran with 0 checks, is FAIL (TDV-071). "Overall: PASS" requires all 22 cases
to pass in both tiers (VC-G11 is Tier B only) and VC-R04-INV and VC-R10-FRZ to pass (TDV-070).
Sections 4 and 5 are left for the engineer to complete in the PR for each failed case (TDV-072).
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tests.validation.answer_key import INPUT_CSV, ROOT, WORKBOOK
from tests.validation.comparator import Result

REPORTS = ROOT / "docs" / "reports"
MARKDOWN = "ALGORITHM_VALIDATION_REPORT.md"
JSON = "validation_results.json"
MAX_LISTED = 50
TIER_B_ONLY = {"VC-G11"}
GATING_SUPPLEMENTARY = ("VC-R04-INV", "VC-R10-FRZ")
CASES: dict[str, str] = {
    "VC-R01": "Clean control", "VC-R02": "Missing days", "VC-R03": "Set-aside sessions",
    "VC-R04": "Duplicate records", "VC-R05": "Possible other speaker",
    "VC-R06": "Morning effect", "VC-R07": "Device move", "VC-R08": "Too few sessions",
    "VC-R09": "Step change", "VC-R10": "Gradual drift",
    "VC-G01": "Status totals", "VC-G02": "Annotated sessions row by row",
    "VC-G03": "Per-resident status counts", "VC-G04": "Resident outcomes",
    "VC-G05": "Baselines", "VC-G06": "Scores", "VC-G07": "Morning offsets",
    "VC-G08": "Parameters", "VC-G09": "Day ledger", "VC-G10": "Alerts",
    "VC-G11": "Raw store fidelity", "VC-G12": "Determinism and rebuild",
}  # fmt: skip
STAGES = {1: "1 Duplicate detection / ingest", 2: "2 Quality gate", 3: "3 Epoch detection",
          4: "4 Speaker screen", 5: "5 Context adjustment", 6: "6 Personal baseline",
          7: "7 Daily deviation score", 8: "8 CUSUM", 9: "9 Alert generation",
          10: "10 Day ledger"}  # fmt: skip


@dataclass
class Results:
    cases: dict[str, dict[str, Result]] = field(default_factory=dict)
    supplementary: dict[str, Result] = field(default_factory=dict)
    config_snapshot: dict[str, Any] | None = None
    robustness: dict[str, Any] | None = None

    def record(self, case: str, tier: str, result: Result) -> Result:
        assert case in CASES, case
        self.cases.setdefault(case, {})[tier] = result
        return result

    def record_supplementary(self, check: str, result: Result) -> Result:
        self.supplementary[check] = result
        return result


RESULTS = Results()


def record(case: str, tier: str, result: Result) -> Result:
    return RESULTS.record(case, tier, result)


def _status(result: Result | None) -> str:
    return "PASS" if result is not None and result.passed else "FAIL"


def tier_status(results: Results, case: str, tier: str) -> str:
    if tier == "A" and case in TIER_B_ONLY:
        return "n/a"
    return _status(results.cases.get(case, {}).get(tier))


def case_passed(results: Results, case: str) -> bool:
    return all(tier_status(results, case, t) in ("PASS", "n/a") for t in ("A", "B"))


def combined(results: Results, case: str) -> Result:
    total = Result()
    for tier in ("A", "B"):
        found = results.cases.get(case, {}).get(tier)
        if found is not None:
            total += found
    return total


def overall(results: Results) -> tuple[str, int]:
    failed = sum(not case_passed(results, case) for case in CASES)
    supplementary_ok = all(_status(results.supplementary.get(s)) == "PASS"
                           for s in GATING_SUPPLEMENTARY)  # fmt: skip
    return ("PASS" if failed == 0 and supplementary_ok else "FAIL"), failed


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_sha() -> str:
    if os.environ.get("GIT_SHA"):
        return os.environ["GIT_SHA"]
    try:
        return subprocess.run(  # noqa: S603 - fixed command
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,  # noqa: S607
            capture_output=True, text=True, check=True, timeout=10,
        ).stdout.strip()  # fmt: skip
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def _config_sha(results: Results) -> str:
    snapshot = results.config_snapshot or {}
    canonical = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def as_json(results: Results, generated: datetime) -> dict[str, Any]:
    verdict, _ = overall(results)
    return {
        "generated_at": generated.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git_sha": _git_sha(),
        "profile": "test_v0_1",
        "config_snapshot_sha256": _config_sha(results),
        "inputs": {"csv_sha256": _sha256(INPUT_CSV), "workbook_sha256": _sha256(WORKBOOK)},
        "tolerance_abs": 1e-6,
        "overall": verdict,
        "cases": [
            {"id": case, "title": title, "tier_a": tier_status(results, case, "A"),
             "tier_b": tier_status(results, case, "B"), "checks": combined(results, case).checks,
             "mismatches": [m.as_json() for m in combined(results, case).mismatches]}
            for case, title in CASES.items()
        ],
        "supplementary": {name: _status(results.supplementary.get(name))
                          for name in ("VC-R04-INV", "VC-R10-FRZ", "VC-R06-MUT")},
        "robustness": results.robustness,
    }  # fmt: skip


def _cell(value: Any) -> str:
    return "" if value is None else str(value).replace("|", "\\|")


def as_markdown(results: Results, data: dict[str, Any]) -> str:
    verdict, failed = overall(results)
    lines = [
        "# ALGORITHM_VALIDATION_REPORT",
        "",
        f"Generated: {data['generated_at']} · Git SHA: {data['git_sha']} · Profile: test_v0_1 · "
        f"Config snapshot SHA-256: {data['config_snapshot_sha256']}",
        f"Input: {INPUT_CSV.name} (SHA-256 {data['inputs']['csv_sha256']}) · Answer key: "
        f"{WORKBOOK.name} (SHA-256 {data['inputs']['workbook_sha256']})",
        "Tolerance: abs 1e-6 (float64); strings, integers, booleans exact",
        f"Overall: {verdict}" if verdict == "PASS" else
        f"Overall: FAIL ({failed} of {len(CASES)} cases failed)",
        "",
        "Synthetic test data only (study IDs and generated values; no real resident data).",
        "",
        "## 1. Summary",
        "",
        "| Case | Title | Tier A | Tier B | Checks | Mismatches | First failing stage |",
        "|---|---|---|---|---|---|---|",
    ]  # fmt: skip
    for case in data["cases"]:
        stage = combined(results, case["id"]).first_stage
        lines.append(f"| {case['id']} | {case['title']} | {case['tier_a']} | {case['tier_b']} | "
                     f"{case['checks']} | {len(case['mismatches'])} | "
                     f"{STAGES.get(stage, '') if stage else ''} |")  # fmt: skip
    passed = [c["id"] for c in data["cases"] if case_passed(results, c["id"])]
    failing = [c for c in data["cases"] if not case_passed(results, c["id"])]
    lines += ["", "## 2. Passed cases", "", ", ".join(passed) if passed else "None.", "",
              "## 3. Failed cases", ""]  # fmt: skip
    if not failing:
        lines.append("None.")
    for case in failing:
        lines += [f"### {case['id']} {case['title']}", ""]
        if case["checks"] == 0:
            lines += ["No comparison ran for this case (0 checks), so it fails (TDV-071).", ""]
            continue
        lines += ["| Sheet | Key | Column | Expected | Actual | Abs diff | Stage |",
                  "|---|---|---|---|---|---|---|"]  # fmt: skip
        for m in case["mismatches"][:MAX_LISTED]:
            lines.append(f"| {_cell(m['sheet'])} | {_cell(m['key'])} | {_cell(m['column'])} | "
                         f"{_cell(m['expected'])} | {_cell(m['actual'])} | "
                         f"{_cell(m['abs_diff'])} | {m['stage']} |")  # fmt: skip
        if len(case["mismatches"]) > MAX_LISTED:
            listed = len(case["mismatches"])
            lines.append(f"(first {MAX_LISTED} of {listed}; full list in {JSON})")
        lines.append("")
    todo = "" if not failing else (
        "To be completed by the engineer in the PR for each failed case (TDV-072).")  # fmt: skip
    lines += ["", "## 4. Root cause analysis", "", todo or "No failed case.", "",
              "## 5. Recommended fixes", "", todo or "No failed case.", "",
              "## 6. Supplementary checks", "",
              "| Check | Result | Checks | Mismatches | Gating |",
              "|---|---|---|---|---|"]  # fmt: skip
    for name in ("VC-R04-INV", "VC-R10-FRZ", "VC-R06-MUT"):
        found = results.supplementary.get(name)
        lines.append(f"| {name} | {_status(found)} | {found.checks if found else 0} | "
                     f"{len(found.mismatches) if found else 0} | "
                     f"{'yes' if name in GATING_SUPPLEMENTARY else 'no (Should)'} |")  # fmt: skip
    lines += ["", "## 7. Informational: false-alarm robustness (not gating)", ""]
    lines += robustness_lines(results.robustness)
    return "\n".join(lines) + "\n"


def robustness_lines(robustness: dict[str, Any] | None) -> list[str]:
    if robustness is None:
        return ["Not run in this session; the nightly job runs `tests/validation/robustness.py` "
                "(TDV-083)."]  # fmt: skip
    per = ", ".join(f"{code} {count}" for code, count in robustness["per_resident"].items())
    return [
        f"Latest run {robustness['generated_at']}: seeds {robustness['seeds']}, residents "
        f"R01-R06 (rate) and R07-R08 (reported), false alarms {robustness['false_alarms']}, "
        f"rate {robustness['rate']:.1%} ({robustness['false_alarms']} of "
        f"{robustness['denominator']}).",
        f"Per resident: {per}.",
        f"Answer-key reproduction mismatches (S2 when non-zero): "
        f"{robustness['reproduction_mismatches']} seeds.",
    ]  # fmt: skip


def write(results: Results, directory: Path = REPORTS) -> dict[str, Any]:
    generated = datetime.now(UTC)
    data = as_json(results, generated)
    if results.robustness is None:
        previous = directory / JSON
        if previous.exists():  # keep the latest nightly robustness section (TDV-081)
            data["robustness"] = results.robustness = json.loads(
                previous.read_text(encoding="utf-8")).get("robustness")  # fmt: skip
    directory.mkdir(parents=True, exist_ok=True)
    (directory / JSON).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    (directory / MARKDOWN).write_text(as_markdown(results, data), encoding="utf-8")
    return data
