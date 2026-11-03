"""Shared steps of the R01-R10 cases (TRD 14 §4.7; FEAT-059).

Every case compares its resident's rows of each DS-02 sheet (Tables 4.5-A..4.5-F) and then the
case-specific rules of TRD 14 §4.7.x, in Tier A and Tier B, and records the result for the report.
Rule values stated in the TRD rounded to 6 decimals compare within the 1e-6 tolerance.
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.validation import report
from tests.validation.comparator import Result, check, compare_sheet
from tests.validation.outputs import NO_RECORD, Outputs

TIERS = ("A", "B")
RESIDENT_SHEETS = ("Annotated_sessions", "Exp_status_counts", "Exp_resident_outcomes",
                   "Exp_baselines", "Exp_scores")  # fmt: skip


def outputs(request: pytest.FixtureRequest, tier: str) -> Outputs:
    found: Outputs = request.getfixturevalue("tier_a" if tier == "A" else "tier_b_outputs")
    return found


def resident_sheets(out: Outputs, code: str, sheets: tuple[str, ...] = RESIDENT_SHEETS) -> Result:
    """The resident's rows of each sheet (scores matched by session_id prefix)."""
    result = Result()
    for sheet in sheets:
        if sheet == "Exp_scores":
            result += compare_sheet(sheet, out, lambda k: str(k[0]).startswith(f"{code}-"))
        else:
            result += compare_sheet(sheet, out, lambda k: k[0] == code)
    return result


def days(out: Outputs, code: str) -> dict[int, dict[str, Any]]:
    """Annotated rows of a resident by day: the first arrival, or the no-record row."""
    found: dict[int, dict[str, Any]] = {}
    for (resident, day, _arrival), row in sorted(out.annotated.items(), key=lambda i: str(i[0])):
        if resident == code and row["expected_status"] != "duplicate":
            found[day] = row
    return found


def duplicates(out: Outputs, code: str) -> dict[int, dict[str, Any]]:
    """Duplicate copies of a resident by arrival order."""
    return {arrival: row for (resident, _, arrival), row in out.annotated.items()
            if resident == code and arrival != NO_RECORD
            and row["expected_status"] == "duplicate"}  # fmt: skip


def rule(sheet: str, key: Any, column: str, expected: Any, actual: Any, stage: int,
         kind: str = "exact") -> Result:  # fmt: skip
    return check(sheet, str(key), column, expected, actual, stage, kind)


def finish(case: str, tier: str, result: Result) -> None:
    """Record the case result for the report and fail on any mismatch (TDV-037, TDV-071)."""
    report.record(case, tier, result)
    assert result.checks > 0
    assert result.mismatches == []
