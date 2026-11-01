"""Quality gate (TRD 10 §4.8; FEAT-041)."""

from __future__ import annotations

import pytest

from analytics.config import TEST_V0_1
from analytics.duplicate_detection import mark_duplicates
from analytics.quality_screening import apply_quality_gate
from tests.unit.analytics.factory import rec

pytestmark = pytest.mark.unit


def _gate(**kw: object) -> tuple[str, str]:
    row = apply_quality_gate(mark_duplicates([rec(1, "2026-10-01 19:00:00", **kw)]), TEST_V0_1)[0]  # type: ignore[arg-type]
    return row.status, row.reason_text


@pytest.mark.req("ING-040", "QG-02", "QG-03", "QG-04", "QG-05", "FEAT-041-AC-03",
                 "FEAT-041-FR-04")  # fmt: skip
def test_thresholds_are_strict() -> None:
    assert _gate(noise=-40.0) == ("pending_screen", "")
    assert _gate(noise=-39.9) == ("set_aside", "noise above limit")
    assert _gate(speech=1.0) == ("pending_screen", "")
    assert _gate(speech=0.99) == ("set_aside", "speech too short")
    assert _gate(flag="poor") == ("set_aside", "quality flag poor")


@pytest.mark.req("ING-041", "QG-06", "FEAT-041-AC-04", "FEAT-041-FR-05")
def test_all_reasons_in_fixed_order() -> None:
    row = apply_quality_gate(
        mark_duplicates([rec(1, "2026-10-01 19:00:00", flag="poor", noise=-30.0, speech=0.5)]),
        TEST_V0_1,
    )[0]
    assert row.reasons == ("quality flag poor", "noise above limit", "speech too short")
    assert row.reason_text == "quality flag poor; noise above limit; speech too short"


@pytest.mark.req("ING-035", "FEAT-041-FR-03")
def test_duplicates_pass_through_ungated() -> None:
    rows = mark_duplicates([rec(1, "2026-10-01 19:00:00", session="S"),
                            rec(2, "2026-10-01 19:00:00", session="S", flag="poor")])  # fmt: skip
    assert [r.status for r in apply_quality_gate(rows, TEST_V0_1)] == [
        "pending_screen",
        "duplicate",
    ]


@pytest.mark.req("FEAT-041-AC-05", "VC-G01")
def test_src05_set_aside() -> None:
    from tests.unit.analytics.src05 import records

    rows = apply_quality_gate(mark_duplicates(records()), TEST_V0_1)
    aside = sorted((r.record.resident_code, r.record.timestamp_utc.day) for r in rows
                   if r.status == "set_aside")  # fmt: skip
    assert aside == [("R03", d) for d in (3, 7, 10, 14, 18, 22, 26)] + [
        ("R08", d) for d in (5, 9, 20, 25, 29)
    ]
    r03_18 = next(r for r in rows if r.record.session_id == "R03-20261018-01")
    assert r03_18.reason_text == "quality flag poor; noise above limit"
