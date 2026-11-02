"""Global checks VC-G01..VC-G12 (TRD 14 §4.6, TDV-050; TRD 09 CUS-028; FEAT-059-FR-11).

Each runs in Tier A and Tier B (VC-G11 is Tier B only) and records its result for the report.
"""

from __future__ import annotations

import csv
import re
from collections import Counter
from typing import Any

import pytest

from analytics import FEATURE_KEYS
from tests.support.system import TierB
from tests.validation.answer_key import INPUT_CSV, rows
from tests.validation.cases import TIERS, finish, outputs, rule
from tests.validation.comparator import Result, compare_outputs, compare_sheet
from tests.validation.outputs import STATUS_COLUMNS, Outputs, from_result, run_tier_a
from tests.validation.tier_b import collect

pytestmark = pytest.mark.validation

TOTALS = {"usable": 267, "set_aside": 12, "quarantined": 2, "duplicate": 2,
          "missing_resident": 17, "missing_device_gap": 2}  # fmt: skip
FLOORED = {"R01", "R02", "R03", "R04", "R05", "R06", "R07", "R10"}
SCORED = {"R01": 14, "R02": 8, "R03": 6, "R04": 14, "R05": 12, "R06": 14, "R07": 2, "R08": 0,
          "R09": 14, "R10": 14}  # fmt: skip
OFFSETS = {"loudness_dbfs": -1.50, "total_phrase_duration_s": 0.10,
           "speech_rate_syl_per_s": -0.12, "articulation_rate_syl_per_s": -0.10,
           "number_of_pauses": 0.00, "pause_fraction": 0.01, "voiced_fraction": -0.02}  # fmt: skip
ALERTS = [
    {"resident_id": "R09", "epoch": 1, "session_id": "R09-20261021-01",
     "triggered_at": "2026-10-21 19:07:50", "local_date": "2026-10-21", "cusum_value": 5.431965,
     "status": "open"},
    {"resident_id": "R10", "epoch": 1, "session_id": "R10-20261024-01",
     "triggered_at": "2026-10-24 19:25:37", "local_date": "2026-10-24", "cusum_value": 5.972050,
     "status": "open"},
]  # fmt: skip


@pytest.mark.req("VC-G01", "TDV-050", "AC-TDV-02")
@pytest.mark.parametrize("tier", TIERS)
def test_vc_g01_status_totals(request: pytest.FixtureRequest, tier: str) -> None:
    out = outputs(request, tier)
    found = Counter(row["expected_status"] for row in out.annotated.values())
    expected = Counter(r["expected_status"] for r in rows("Annotated_sessions"))
    result = Result()
    for status in STATUS_COLUMNS:
        result += rule("Annotated_sessions", "all", status, TOTALS[status], found[status], 1)
        result += rule("Annotated_sessions", "all", f"{status} (workbook)", expected[status],
                       found[status], 1)  # fmt: skip
    result += rule("Annotated_sessions", "all", "rows", 302, sum(found.values()), 1)
    finish("VC-G01", tier, result)


@pytest.mark.req("VC-G02", "TDV-050")
@pytest.mark.parametrize("tier", TIERS)
def test_vc_g02_annotated_sessions(request: pytest.FixtureRequest, tier: str) -> None:
    finish("VC-G02", tier, compare_sheet("Annotated_sessions", outputs(request, tier)))


@pytest.mark.req("VC-G03", "TDV-050")
@pytest.mark.parametrize("tier", TIERS)
def test_vc_g03_status_counts(request: pytest.FixtureRequest, tier: str) -> None:
    out = outputs(request, tier)
    result = compare_sheet("Exp_status_counts", out)
    result += rule("Exp_status_counts", "all", "rows", 10, len(out.status_counts), 10)
    finish("VC-G03", tier, result)


@pytest.mark.req("VC-G04", "TDV-050")
@pytest.mark.parametrize("tier", TIERS)
def test_vc_g04_resident_outcomes(request: pytest.FixtureRequest, tier: str) -> None:
    out = outputs(request, tier)
    result = compare_sheet("Exp_resident_outcomes", out)
    result += rule("Exp_resident_outcomes", "all", "rows", 11, len(out.outcomes), 3)
    finish("VC-G04", tier, result)


@pytest.mark.req("VC-G05", "TDV-050", "AGT-042")
@pytest.mark.parametrize("tier", TIERS)
def test_vc_g05_baselines(request: pytest.FixtureRequest, tier: str) -> None:
    out = outputs(request, tier)
    result = compare_sheet("Exp_baselines", out)
    result += rule("Exp_baselines", "all", "rows", 180, len(out.baselines), 6)
    floored = sorted(k for k, b in out.baselines.items() if b["floor_applied"])
    result += rule("Exp_baselines", "all", "floor_applied rows",
                   sorted((r, 2 if r == "R07" else 1, "number_of_pauses") for r in FLOORED),
                   floored, 6)  # fmt: skip
    for key in floored:
        b = out.baselines[key]
        result += rule("Exp_baselines", key, "mad", 0.0, b["mad"], 6, "float")
        result += rule("Exp_baselines", key, "robust_spread", 0.5, b["robust_spread"], 6, "float")
    r09 = out.baselines[("R09", 1, "number_of_pauses")]
    result += rule("Exp_baselines", "R09/1/number_of_pauses", "floor_applied", False,
                   r09["floor_applied"], 6)  # fmt: skip
    result += rule("Exp_baselines", "R09/1/number_of_pauses", "mad", 0.5, r09["mad"], 6, "float")
    result += rule("Exp_baselines", "R09/1/number_of_pauses", "robust_spread", 0.7413,
                   r09["robust_spread"], 6, "float")  # fmt: skip
    for epoch in (("R07", 1), ("R08", 1)):
        result += rule("Exp_baselines", epoch, "rows", 0,
                       sum(k[:2] == epoch for k in out.baselines), 6)  # fmt: skip
    finish("VC-G05", tier, result)


@pytest.mark.req("VC-G06", "TDV-050")
@pytest.mark.parametrize("tier", TIERS)
def test_vc_g06_scores(request: pytest.FixtureRequest, tier: str) -> None:
    out = outputs(request, tier)
    result = compare_sheet("Exp_scores", out)
    result += rule("Exp_scores", "all", "rows", 98, len(out.scores), 7)
    per = Counter(s["resident_id"] for s in out.scores.values())
    for code, count in SCORED.items():
        result += rule("Exp_scores", code, "rows", count, per[code], 7)
    alarms = Counter(s["alarm"] for s in out.scores.values())
    result += rule("Exp_scores", "all", "alarm counts", {"off": 81, "on": 15, "rings": 2},
                   dict(alarms), 8)  # fmt: skip
    finish("VC-G06", tier, result)


@pytest.mark.req("VC-G07", "TDV-050", "TDV-003")
@pytest.mark.parametrize("tier", TIERS)
def test_vc_g07_morning_offsets(request: pytest.FixtureRequest, tier: str) -> None:
    out = outputs(request, tier)
    result = compare_sheet("Exp_morning_offset", out)
    result += rule("Exp_morning_offset", "all", "rows", 19, len(out.morning_offsets), 5)
    for key in FEATURE_KEYS:
        result += rule(
            "Exp_morning_offset",
            key,
            "configured_morning_offset",
            OFFSETS.get(key, 0.0),
            out.morning_offsets[(key,)]["configured_morning_offset"],
            5,
            "float",
        )
    finish("VC-G07", tier, result)


def _parameters() -> dict[str, Any]:
    """Table 4.5-E read from the Parameters sheet."""
    sheet = {r["parameter"]: r for r in rows("Parameters")}

    def number(text: Any, pattern: str) -> float:
        match = re.search(pattern, str(text))
        assert match is not None, (pattern, text)
        return float(match.group(1))

    rule_text = sheet["speaker screen rule"]["value"]
    return {
        "facility_tz": sheet["facility_tz"]["value"],
        "morning_cutoff_hour": int(number(sheet["morning rule"]["value"], r"before (\d+):00")),
        "noise_limit_dbfs": float(sheet["noise limit"]["value"]),
        "min_speech_s": float(sheet["minimum speech duration"]["value"]),
        "baseline_n": int(sheet["baseline length (test only)"]["value"]),
        "mad_scale": number(sheet["baseline spread"]["value"], r"MAD x ([\d.]+)"),
        "pause_floor": float(sheet["spread floor, number_of_pauses"]["value"]),
        "composite_floor": number(sheet["composite z"]["meaning"], r"floor ([\d.]+)"),
        "screen_min_n": int(number(sheet["speaker screen reference"]["meaning"],
                                   r"at least (\d+) prior")),
        "screen_f0_z": number(rule_text, r"\|F0 z\| >= ([\d.]+)"),
        "screen_other_z": number(rule_text, r"features with \|z\| >= ([\d.]+)"),
        "screen_other_count": int(number(rule_text, r"at least (\d+) composite")),
        "cusum_k": number(sheet["CUSUM"]["value"], r"- ([\d.]+)\)"),
        "cusum_h": number(sheet["alarm"]["value"], r">= ([\d.]+)"),
        "shared_device_min_residents": int(number(sheet["missing_device_gap"]["meaning"],
                                                  r"serves (\d+) or more")),
    }  # fmt: skip


@pytest.mark.req("VC-G08", "TDV-050", "TDV-003", "TDV-022")
@pytest.mark.parametrize("tier", TIERS)
def test_vc_g08_parameters(request: pytest.FixtureRequest, tier: str) -> None:
    out = outputs(request, tier)
    expected = _parameters()
    result = rule("Parameters", "all", "keys", sorted(expected), sorted(out.params), 6)
    for key, value in expected.items():
        kind = "float" if isinstance(value, float) else "exact"
        result += rule("Parameters", key, "value", value, out.params.get(key), 6, kind)
    finish("VC-G08", tier, result)


@pytest.mark.req("VC-G09", "TDV-050", "AGT-046")
@pytest.mark.parametrize("tier", TIERS)
def test_vc_g09_day_ledger(request: pytest.FixtureRequest, tier: str) -> None:
    out = outputs(request, tier)
    result = rule("day_ledger", "all", "rows", 300, len(out.ledger), 10)
    statuses = Counter(d[2] for d in out.ledger)
    result += rule("day_ledger", "all", "statuses",
                   {"checked_in": 281, "missing_resident": 17, "missing_device_gap": 2},
                   dict(statuses), 10)  # fmt: skip
    dates = sorted({d[1].isoformat() for d in out.ledger})
    result += rule("day_ledger", "all", "dates", ["2026-10-01", "2026-10-30", 30],
                   [dates[0], dates[-1], len(dates)], 10)  # fmt: skip
    if tier == "B":
        harness: TierB = request.getfixturevalue("tier_b_harness")
        columns = {
            r[0]
            for r in harness.select(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'day_ledger'"
            )
        }
        result += rule("day_ledger", "columns", "feature columns", [],
                       sorted(columns & set(FEATURE_KEYS)), 10)  # fmt: skip
    else:
        result += rule("day_ledger", "rows", "fields", 5, len(out.ledger[0]), 10)
    finish("VC-G09", tier, result)


@pytest.mark.req("VC-G10", "TDV-050", "CUS-028", "FEAT-059-AC-05")
@pytest.mark.parametrize("tier", TIERS)
def test_vc_g10_alerts(request: pytest.FixtureRequest, tier: str) -> None:
    out = outputs(request, tier)
    result = rule("alerts", "all", "rows", 2, len(out.alerts), 9)
    for expected, actual in zip(ALERTS, out.alerts, strict=False):
        for column, value in expected.items():
            kind = "float" if column == "cusum_value" else "exact"
            result += rule("alerts", expected["resident_id"], column, value, actual[column], 9,
                           kind)  # fmt: skip
    tallies = {("R09", 1): 26.830256, ("R10", 1): 13.418183}
    for key, value in tallies.items():
        result += rule("cusum_state", key, "current_tally", value,
                       out.cusum[key]["current_tally"], 8, "float")  # fmt: skip
        result += rule("cusum_state", key, "alarm_on", True, out.cusum[key]["alarm_on"], 8)
    formed = {k for k, o in out.outcomes.items() if o["baseline_formed"]} - set(tallies)
    result += rule("cusum_state", "other formed epochs", "alarm_on", [],
                   sorted(k for k in formed if out.cusum[k]["alarm_on"]), 8)  # fmt: skip
    finish("VC-G10", tier, result)


@pytest.mark.req("VC-G11", "TDV-050", "TDV-002", "BR-02")
def test_vc_g11_raw_store_fidelity(tier_b_harness: TierB) -> None:
    with INPUT_CSV.open(newline="", encoding="utf-8") as handle:
        source = list(csv.DictReader(handle))
    stored = tier_b_harness.select("SELECT payload FROM raw_sessions ORDER BY arrival_seq")
    result = rule("raw_sessions", "all", "rows", 283, len(stored), 1)
    for number, (row, (payload,)) in enumerate(zip(source, stored, strict=False), start=1):
        result += rule("raw_sessions", number, "payload", row, payload, 1)
    result += rule(
        "ingest_rejections",
        "all",
        "rows",
        0,
        tier_b_harness.select("SELECT count(*) FROM ingest_rejections")[0][0],
        1,
    )
    batch = tier_b_harness.batch
    result += rule(
        "ingest_batches",
        batch["ingest_batch_id"],
        "accepted/rejected/duplicates",
        [283, 0, 2],
        [batch["accepted"], batch["rejected"], batch["duplicates"]],
        1,
    )
    finish("VC-G11", "B", result)


@pytest.mark.req("VC-G12", "TDV-050", "TST-050", "AGT-021", "AGT-056")
@pytest.mark.parametrize("tier", TIERS)
def test_vc_g12_determinism_and_rebuild(request: pytest.FixtureRequest, tier: str) -> None:
    before: Outputs = outputs(request, tier)
    if tier == "A":
        again = from_result(run_tier_a())
    else:
        harness: TierB = request.getfixturevalue("tier_b_harness")
        harness.run_at_as_of()  # a full rebuild of the derived results at the same as-of
        again = collect(harness)
    finish("VC-G12", tier, compare_outputs(before, again, f"Tier {tier} run vs rerun"))
