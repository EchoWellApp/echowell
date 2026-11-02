"""VC-R04 Duplicate records (TRD 14 §4.7.4, TDV-054; FEAT-059-FR-04; FR-031; AGT-043).

VC-R04-INV (identical outputs without the two copies) is in `test_invariance.py`.
"""

from __future__ import annotations

import pytest

from tests.validation.cases import TIERS, days, duplicates, finish, outputs, resident_sheets, rule
from tests.validation.comparator import Result
from tests.validation.tier_b import TierB

pytestmark = pytest.mark.validation

COPIES = {89: "R04-20261005-01", 283: "R04-20261018-01"}
FIRST = {88: "R04-20261005-01", 102: "R04-20261018-01"}


@pytest.mark.req("VC-R04", "TDV-054", "FEAT-059-FR-04", "AGT-043", "FR-031")
@pytest.mark.parametrize("tier", TIERS)
def test_vc_r04_duplicate_records(request: pytest.FixtureRequest, tier: str) -> None:
    out = outputs(request, tier)
    result = resident_sheets(out, "R04")
    copies = duplicates(out, "R04")
    result += rule(
        "Annotated_sessions", "R04", "duplicate arrivals", sorted(COPIES), sorted(copies), 1
    )
    for arrival, session in COPIES.items():
        row = copies.get(arrival, {})
        result += rule(
            "Annotated_sessions", f"R04/{arrival}", "session_id", session, row.get("session_id"), 1
        )
        result += rule(
            "Annotated_sessions",
            f"R04/{arrival}",
            "expected_reason",
            "session_id already received",
            row.get("expected_reason"),
            1,
        )
        result += rule(
            "Annotated_sessions",
            f"R04/{arrival}",
            "expected_epoch",
            None,
            row.get("expected_epoch"),
            3,
        )
        result += rule(
            "Annotated_sessions", f"R04/{arrival}", "in_baseline", False, row.get("in_baseline"), 6
        )
    kept = {r["session_id"]: r for r in days(out, "R04").values()}
    for session in FIRST.values():
        result += rule(
            "Annotated_sessions",
            session,
            "expected_status",
            "usable",
            kept[session]["expected_status"],
            1,
        )
    result += rule("Annotated_sessions", "R04", "usable", 30, len(kept), 1)
    result += rule(
        "Exp_resident_outcomes",
        "R04/1",
        "scored_sessions",
        14,
        out.outcomes[("R04", 1)]["scored_sessions"],
        7,
    )
    if tier == "B":
        result += _raw_store_keeps_both_copies(request.getfixturevalue("tier_b_harness"))
    finish("VC-R04", tier, result)


def _raw_store_keeps_both_copies(harness: TierB) -> Result:
    rows = harness.select(
        "SELECT r.session_id, p.status FROM raw_sessions r "
        "JOIN processed_sessions p ON p.raw_session_id = r.id "
        "WHERE r.session_id IN ('R04-20261005-01', 'R04-20261018-01') ORDER BY r.arrival_seq"
    )
    return rule(
        "raw_sessions",
        "R04",
        "arrivals and statuses",
        [
            ("R04-20261005-01", "usable"),
            ("R04-20261005-01", "duplicate"),
            ("R04-20261018-01", "usable"),
            ("R04-20261018-01", "duplicate"),
        ],
        [(r.session_id, r.status) for r in rows],
        1,
    )
