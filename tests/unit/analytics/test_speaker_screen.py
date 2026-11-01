"""Speaker screen (TRD 08 §4.4, §4.9; FEAT-044)."""

from __future__ import annotations

import pytest

from analytics.config import TEST_V0_1
from analytics.duplicate_detection import mark_duplicates
from analytics.epoch_detection import assign_epochs
from analytics.quality_screening import apply_quality_gate
from analytics.speaker_screen import LATE_REASON, screen_speakers
from tests.unit.analytics.factory import rec

pytestmark = pytest.mark.unit


def _run(records: list, late_seqs: tuple[int, ...] = ()) -> dict:  # type: ignore[type-arg]
    rows = apply_quality_gate(mark_duplicates(records), TEST_V0_1)
    late = [r for r in rows if r.record.arrival_seq in late_seqs]
    return {r.record.arrival_seq: r for r in screen_speakers(assign_epochs(rows, late), TEST_V0_1)}


def _normal(n: int) -> list:  # type: ignore[type-arg]
    """n ordinary sessions with small variation, days 1..n."""
    return [rec(i, f"2026-10-{i:02d} 19:00:00", mean_f0_hz=200.0 + (i % 3),
                loudness_dbfs=-24.0 + 0.1 * (i % 4), total_phrase_duration_s=2.5 + 0.05 * (i % 3))
            for i in range(1, n + 1)]  # fmt: skip


@pytest.mark.req("BSC-013", "SS-01")
def test_no_screen_below_screen_min_n() -> None:
    other = rec(5, "2026-10-05 19:00:00", mean_f0_hz=120.0, loudness_dbfs=-10.0,
                voiced_fraction=0.2)  # fmt: skip
    out = _run([*_normal(4), other])
    assert (out[5].status, out[5].screen_detail) == ("usable", None)


@pytest.mark.req("BSC-015", "BSC-016", "BSC-017", "FEAT-044-AC-01")
def test_quarantine_needs_f0_and_two_composite_features() -> None:
    other = rec(6, "2026-10-06 19:00:00", mean_f0_hz=120.0, loudness_dbfs=-10.0,
                total_phrase_duration_s=9.0)  # fmt: skip
    f0_only = rec(7, "2026-10-07 19:00:00", mean_f0_hz=120.0)
    out = _run([*_normal(5), other, f0_only])
    assert out[6].status == "quarantined"
    assert out[6].reason_text.startswith("possible other speaker (F0 z=")
    assert out[6].reasons == (out[6].reason_text,)
    assert out[6].reason_text.endswith("composite features with |z|>=3: 2)")
    assert out[7].status == "usable"
    assert out[7].screen_detail is not None


@pytest.mark.req("BSC-040", "ANL-025")
def test_late_record_reasons() -> None:
    records = [*_normal(6), rec(7, "2026-10-03 21:00:00", session="R01-20261003-02")]
    out = _run(records, late_seqs=(7,))
    assert (out[7].status, out[7].reasons, out[7].late_arrival) == ("usable", (LATE_REASON,), True)
    late_other = rec(8, "2026-10-06 21:00:00", session="R01-20261006-02", mean_f0_hz=120.0,
                     loudness_dbfs=-10.0, total_phrase_duration_s=9.0)  # fmt: skip
    out = _run([*_normal(7), late_other], late_seqs=(8,))
    assert out[8].status == "quarantined"
    assert out[8].reasons[1] == LATE_REASON


@pytest.mark.req("BSC-012", "BSC-016", "BSC-018", "AC-BSC-04", "FEAT-044-AC-02", "VC-R05")
def test_src05_r05_quarantines_use_the_first_n() -> None:
    from tests.unit.analytics.src05 import result

    q = {s.record.session_id: s.reason_text for s in result().sessions if s.status == "quarantined"}
    assert q == {
        "R05-20261008-01": "possible other speaker (F0 z=-8.61; composite features with |z|>=3: 4)",
        "R05-20261022-01": "possible other speaker (F0 z=-7.34; composite features with |z|>=3: 3)",
    }
    assert sum(s.status == "usable" for s in result().sessions) == 267
