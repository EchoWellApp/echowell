"""Supplementary checks VC-R04-INV, VC-R10-FRZ and VC-R06-MUT (TRD 14 §4.7.4, §4.7.6, §4.7.10;
TDV-054, TDV-056, TDV-060; FR-031; FEAT-058-FR-15, FEAT-059-FR-04, FEAT-059-FR-06, FEAT-059-FR-10).

VC-R04-INV and VC-R10-FRZ gate "Overall: PASS"; VC-R06-MUT is a Should and is reported only.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from analytics import TEST_V0_1, PipelineConfig
from backend.api.deps import get_clock
from tests.validation import report
from tests.validation.answer_key import INPUT_CSV
from tests.validation.comparator import Mismatch, Result, compare_outputs, compare_sheet
from tests.validation.outputs import Outputs, from_result, input_rows, run_tier_a
from tests.validation.tier_b import TierB, tier_b

pytestmark = pytest.mark.validation

COPY_ARRIVALS = {89, 283}


def _resident(out: Outputs, code: str) -> Outputs:
    """A resident's outputs keyed independently of arrival order, for exact comparison."""
    view = Outputs()
    view.annotated = {(r, d): row for (r, d, _), row in out.annotated.items()
                      if r == code and row["expected_status"] != "duplicate"}  # fmt: skip
    for name in ("status_counts", "outcomes", "baselines", "cusum"):
        setattr(view, name, {k: v for k, v in getattr(out, name).items() if k[0] == code})
    view.scores = {k: v for k, v in out.scores.items() if v["resident_id"] == code}
    view.adjusted = {k: v for k, v in out.adjusted.items() if k[0].startswith(f"{code}-")}
    view.alerts = [a for a in out.alerts if a["resident_id"] == code]
    view.ledger = [d for d in out.ledger if d[0] == code]
    view.status_counts = {}  # the duplicate count differs by design
    return view


@pytest.mark.req("VC-R04-INV", "TDV-054", "FR-031", "AGT-043", "FEAT-058-FR-15",
                 "FEAT-059-FR-04", "FEAT-059-AC-03")  # fmt: skip
def test_vc_r04_inv_identical_without_the_copies(tier_a: Outputs) -> None:
    rows = [row for n, row in enumerate(input_rows(), start=1) if n not in COPY_ARRIVALS]
    reduced = from_result(run_tier_a(rows), rows)
    result = compare_outputs(_resident(tier_a, "R04"), _resident(reduced, "R04"),
                             "VC-R04-INV full vs without copies")  # fmt: skip
    report.RESULTS.record_supplementary("VC-R04-INV", result)
    assert result.checks > 0
    assert result.mismatches == []


def _r10_baselines(harness: TierB) -> list[tuple[Any, ...]]:
    return [tuple(r) for r in harness.select(
        "SELECT b.feature_key, b.n_sessions, b.first_session_id, b.frozen_after_session_id, "
        "b.median, b.mad, b.robust_spread, b.floor_applied, b.frozen_at FROM baselines b "
        "JOIN residents r ON r.id = b.resident_id WHERE r.resident_code = 'R10' "
        "ORDER BY b.feature_key")]  # fmt: skip


def _ingest_one(harness: TierB, header: str, line: str, clock: list[datetime]) -> None:
    stamp = datetime.strptime(line.split(",")[header.split(",").index("timestamp_utc")],
                              "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)  # fmt: skip
    clock[0] = stamp + timedelta(minutes=1)  # each record's timestamp + 1 minute (TDV-061)
    harness.ingest(f"{header}\n{line}\n".encode(), filename="r10.csv")


@pytest.mark.req("VC-R10-FRZ", "TDV-060", "AGT-051", "ASM-07", "FEAT-059-FR-10",
                 "FEAT-059-AC-03")  # fmt: skip
def test_vc_r10_frz_frozen_baseline(tier_a: Outputs) -> None:
    result = compare_sheet("Exp_baselines", tier_a, lambda k: k[0] == "R10")  # (a)
    truncated = [
        row
        for row in input_rows()
        if row["resident_id"] != "R10" or row["timestamp_utc"][:10] <= "2026-10-16"
    ]
    early = from_result(run_tier_a(truncated), truncated)  # (b)
    result += compare_outputs(
        _baselines(tier_a, "R10"), _baselines(early, "R10"), "VC-R10-FRZ (b) full vs day 16"
    )
    result += _incremental_tier_b()  # (c)
    report.RESULTS.record_supplementary("VC-R10-FRZ", result)
    assert result.checks > 0
    assert result.mismatches == []


def _baselines(out: Outputs, code: str) -> Outputs:
    view = Outputs()
    view.baselines = {k: v for k, v in out.baselines.items() if k[0] == code}
    return view


def _incremental_tier_b() -> Result:
    """(c): R10 ingested one record at a time with the application clock at each record's
    timestamp + 1 minute; its baselines (values and frozen_at) do not change after day 16."""
    lines = [line for line in _csv_lines() if line.split(",")[2] == "R10"]
    header = _csv_lines(header=True)[0]
    clock = [datetime(2026, 10, 1, tzinfo=UTC)]
    result = Result()
    with tier_b(ingest=False) as harness:
        harness.client.app.dependency_overrides[get_clock] = _clock(clock)  # type: ignore[attr-defined]
        for line in lines[:16]:
            _ingest_one(harness, header, line, clock)
        frozen = _r10_baselines(harness)
        result.checks += 1
        if len(frozen) != 20:
            result.mismatches.append(Mismatch("baselines", "R10", "rows after day 16", 20,
                                              len(frozen), None, 6))  # fmt: skip
        for line in lines[16:]:
            _ingest_one(harness, header, line, clock)
        after = _r10_baselines(harness)
        result += compare_outputs(_as_outputs(frozen), _as_outputs(after),
                                  "VC-R10-FRZ (c) after day 16 vs after day 30")  # fmt: skip
    return result


def _clock(cell: list[datetime]) -> Callable[[], Callable[[], datetime]]:
    return lambda: lambda: cell[0]


def _as_outputs(rows: list[tuple[Any, ...]]) -> Outputs:
    view = Outputs()
    view.baselines = {(r[0],): {"row": r} for r in rows}
    return view


def _csv_lines(header: bool = False) -> list[str]:
    text = INPUT_CSV.read_text(encoding="utf-8").splitlines()
    return text[:1] if header else text[1:]


@pytest.mark.req("VC-R06-MUT", "TDV-056", "AGT-050", "FEAT-059-FR-06")
def test_vc_r06_mut_missing_adjustment_is_detected() -> None:
    values = TEST_V0_1.snapshot()
    values["morning_offsets"] = dict.fromkeys(values["morning_offsets"], 0.0)
    mutated = PipelineConfig.from_mapping(
        {k: v for k, v in values.items() if k not in ("features", "operational")}
        | dict(values["operational"])
    )  # fmt: skip
    out = from_result(run_tier_a(config=mutated))
    found = compare_sheet("Exp_baselines", out, lambda k: k[0] == "R06")
    detected = any(m.key == "R06/1/loudness_dbfs" for m in found.mismatches)
    report.RESULTS.record_supplementary("VC-R06-MUT", Result(found.checks, [] if detected else [
        *found.mismatches]))  # fmt: skip
    assert detected, "zero morning offsets must break the R06 loudness baseline"
