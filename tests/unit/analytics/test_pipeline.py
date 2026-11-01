"""run_pipeline: order, determinism, as-of filter, late arrivals, contracts (TRD 07 §4.5-§4.6;
FEAT-052)."""

from __future__ import annotations

import random
import time
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from analytics import pipeline
from analytics.config import TEST_V0_1, ContractError, DeviceAssignment, ResidentInfo
from analytics.pipeline import run_pipeline
from tests.unit.analytics import src05
from tests.unit.analytics.src05 import AS_OF, ASSIGNMENTS, RESIDENTS, records, result

pytestmark = pytest.mark.unit


def _run(recs, **kw):  # type: ignore[no-untyped-def]
    return run_pipeline(recs, RESIDENTS, ASSIGNMENTS, TEST_V0_1, kw.pop("as_of", AS_OF), **kw)


@pytest.mark.req("ANL-012", "ANL-014", "FEAT-052-FR-10", "FEAT-052-FR-11", "VC-G01")
def test_src05_counts_and_sessions() -> None:
    res = result()
    assert res.counts == {
        "arrivals": 283, "usable": 267, "set_aside": 12, "quarantined": 2, "duplicate": 2,
        "missing_resident": 17, "missing_device_gap": 2, "late_arrival": 0, "scored": 98,
        "alerts_opened": 2, "excluded_after_as_of": 0, "residents": 10,
    }  # fmt: skip
    assert [s.record.arrival_seq for s in res.sessions] == list(range(1, 284))
    assert res.warnings == ()
    assert res.config_hash == TEST_V0_1.config_hash()
    assert res.engine_version == "0.1.0"


@pytest.mark.req("ANL-020", "AC-ANL-02", "AGT-021", "TST-022", "FEAT-052-FR-08")
def test_deterministic_and_order_independent() -> None:
    shuffled = list(records())
    random.Random(7).shuffle(shuffled)  # noqa: S311 - test order only
    assert _run(shuffled) == result()
    assert _run(list(records())) == result()


@pytest.mark.req("AC-ANL-03", "FR-031", "FEAT-041-AC-06", "FEAT-052-FR-14")
def test_dropping_duplicates_changes_nothing_else() -> None:
    without = _run([r for r in records() if r.arrival_seq not in (89, 283)])
    for part in ("baselines", "scores", "ledger", "alerts", "data_alerts"):
        assert getattr(without, part) == getattr(result(), part), part
    assert [s for s in without.sessions] == [
        s for s in result().sessions if s.status != "duplicate"
    ]


@pytest.mark.req("ANL-015", "FEAT-052-FR-04")
def test_records_after_as_of_are_excluded() -> None:
    as_of = datetime(2026, 10, 20, 12, tzinfo=UTC)
    res = _run(list(records()), as_of=as_of)
    assert all(s.record.timestamp_utc <= as_of for s in res.sessions)
    after = sum(r.timestamp_utc > as_of for r in records())
    assert res.counts["excluded_after_as_of"] == after > 0
    assert sum(w.code == "after_as_of" for w in res.warnings) == after
    assert max(d.local_date for d in res.ledger).day == 20


@pytest.mark.req("ANL-024", "ANL-025", "AC-ANL-05", "BSC-040", "BSC-041", "FEAT-045-AC-06",
                 "FEAT-052-AC-04")  # fmt: skip
def test_late_arrival_leaves_r01_unchanged() -> None:
    day10 = next(r for r in records() if r.session_id == "R01-20261010-01")
    late = replace(day10, session_id="R01-20261010-02", arrival_seq=1000,
                   raw_session_id="00000000-0000-0000-0000-000000001000",
                   timestamp_utc=datetime(2026, 10, 10, 19, tzinfo=UTC))  # fmt: skip
    res = _run([*records(), late])
    assert [w.code for w in res.warnings] == ["late_arrival"]
    row = next(s for s in res.sessions if s.record.session_id == "R01-20261010-02")
    assert (row.status, row.in_baseline, row.late_arrival, row.baseline_ordinal) == (
        "usable", False, True, None
    )  # fmt: skip
    assert row.reasons == ("late arrival (not used for baseline or scores)",)
    r01 = lambda rows: [x for x in rows if x.resident_code == "R01"]  # noqa: E731
    assert r01(res.baselines) == r01(result().baselines)
    assert r01(res.scores) == r01(result().scores)


@pytest.mark.req("ANL-027", "FEAT-052-AC-05")
def test_out_of_order_after_freeze_is_not_late() -> None:
    last = max((r for r in records() if r.resident_code == "R01"), key=lambda r: r.timestamp_utc)
    resent = replace(last, session_id="R01-20261029-02", arrival_seq=1001,
                     raw_session_id="00000000-0000-0000-0000-000000001001",
                     timestamp_utc=last.timestamp_utc - timedelta(hours=1))  # fmt: skip
    res = _run([*records(), resent])
    assert not [w for w in res.warnings if w.code == "late_arrival"]
    assert any(s.session_id == "R01-20261029-02" for s in res.scores)


@pytest.mark.req("ANL-018", "FEAT-052-FR-03")
def test_contract_violations() -> None:
    recs = list(records())
    with pytest.raises(ContractError):
        _run(recs, as_of=AS_OF.replace(tzinfo=None))
    with pytest.raises(ContractError):
        _run([recs[0], replace(recs[1], arrival_seq=1)])
    with pytest.raises(ContractError):
        run_pipeline(
            recs, RESIDENTS, [DeviceAssignment("R99", "D9", AS_OF.date())], TEST_V0_1, AS_OF
        )
    with pytest.raises(ContractError):
        run_pipeline(recs, RESIDENTS, ASSIGNMENTS, {}, AS_OF)  # type: ignore[arg-type]


@pytest.mark.req("ANL-019", "FEAT-052-FR-09")
def test_normal_conditions_do_not_raise() -> None:
    empty = run_pipeline([], RESIDENTS, ASSIGNMENTS, TEST_V0_1, AS_OF)
    assert empty.counts["arrivals"] == 0
    assert all(d.status != "checked_in" for d in empty.ledger)
    only_dup = [r for r in records() if r.session_id == "R04-20261005-01"]
    r04 = [a for a in ASSIGNMENTS if a.resident_code == "R04"]
    res = run_pipeline(only_dup, [ResidentInfo("R04", src05.ENROLLED)], r04, TEST_V0_1, AS_OF)
    assert res.counts["duplicate"] == 1


@pytest.mark.req("ANL-037", "FEAT-052-FR-12", "FEAT-045-AC-07")
def test_frozen_baselines_win_and_mismatch_warns() -> None:
    r09 = tuple(b for b in result().baselines if b.resident_code == "R09")
    same = _run(list(records()), frozen_baselines={("R09", 1): r09})
    assert same.scores == result().scores
    assert same.warnings == ()
    shifted = tuple(replace(b, median=b.median + 0.5) if b.feature_key == "loudness_dbfs" else b
                    for b in r09)  # fmt: skip
    res = _run(list(records()), frozen_baselines={("R09", 1): shifted})
    assert [w.code for w in res.warnings] == ["baseline_mismatch"]
    assert next(b for b in res.baselines if b.resident_code == "R09"
                and b.feature_key == "loudness_dbfs").median == shifted[0].median  # fmt: skip
    r09_scores = [s for s in res.scores if s.resident_code == "R09"]
    assert r09_scores != [s for s in result().scores if s.resident_code == "R09"]


@pytest.mark.req("ANL-047", "TST-120", "FEAT-052-FR-15", "D-40")
def test_src05_runs_within_five_seconds() -> None:
    start = time.perf_counter()
    _run(list(records()))
    assert time.perf_counter() - start < 5.0


@pytest.mark.req("ANL-021")
def test_detect_late_arrivals_in_order_input_is_empty() -> None:
    from analytics.duplicate_detection import mark_duplicates
    from analytics.quality_screening import apply_quality_gate

    screened = apply_quality_gate(mark_duplicates(records()), TEST_V0_1)
    assert pipeline.detect_late_arrivals(screened, TEST_V0_1) == []
