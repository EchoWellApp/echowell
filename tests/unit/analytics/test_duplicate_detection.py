"""Arrival-order duplicates (TRD 10 §4.7; FEAT-041)."""

from __future__ import annotations

import pytest

from analytics.duplicate_detection import mark_duplicates
from tests.unit.analytics.factory import rec

pytestmark = pytest.mark.unit


@pytest.mark.req("ING-034", "ING-037", "DUP-02", "DUP-03", "FEAT-041-AC-01", "FEAT-041-AC-02",
                 "FEAT-041-FR-01", "FEAT-041-FR-02")  # fmt: skip
def test_first_arrival_wins_in_arrival_order() -> None:
    a = rec(1, "2026-10-02 19:00:00", session="S1")
    b = rec(2, "2026-10-01 19:00:00", session="S2")
    c = rec(3, "2026-10-01 18:00:00", session="S1", loudness_dbfs=-10.0)  # earlier timestamp
    out = mark_duplicates([c, b, a])
    assert [(r.record.arrival_seq, r.status) for r in out] == [
        (1, "pending_screen"), (2, "pending_screen"), (3, "duplicate")
    ]  # fmt: skip
    assert out[2].reasons == ("session_id already received",)
    assert out[2].reason_text == "session_id already received"
    assert out[0].record.features["loudness_dbfs"] == -24.0


@pytest.mark.req("FEAT-041-AC-05", "ING-039")
def test_src05_duplicates() -> None:
    from tests.unit.analytics.src05 import records

    dups = [r.record.arrival_seq for r in mark_duplicates(records()) if r.status == "duplicate"]
    assert dups == [89, 283]
