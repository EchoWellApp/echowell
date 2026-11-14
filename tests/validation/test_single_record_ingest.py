"""One record at a time equals one batch (TRD 13 TST-049; MVP-02; TRD 07 AC-ANL-06).

SRC-05 is posted record by record through `POST /api/v1/sessions` in arrival order, each request
running the synchronous per-resident pipeline, with the application clock frozen at the test
as-of (2026-10-30 15:00 America/Chicago). The derived tables must equal those of one batch
ingest plus a full run with the same as-of (the session-scoped `tier_b_outputs`).

A duplicate starts no pipeline run (TRD 05 API-044), so a duplicate that arrives after its
resident's last first arrival gets its `duplicate` row at the next run. In SRC-05 that is exactly
one record, the last one (R04-20261018-01 again, arrival 283). The test checks that this is the
only difference straight after the single posts, and that the next run (the nightly run, here the
explicit as-of run) makes the derived tables equal to the batch in full.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from backend.api.deps import get_clock
from tests.support.system import SEED_SECRETS, TierB, tier_b
from tests.validation.comparator import compare_outputs
from tests.validation.outputs import Outputs, input_rows
from tests.validation.tier_b import collect

pytestmark = pytest.mark.validation

AS_OF = datetime(2026, 10, 30, 20, 0, tzinfo=UTC)  # 2026-10-30 15:00 America/Chicago
TEXT_FIELDS = {
    "schema_version", "session_id", "resident_id", "device_id", "timestamp_utc",
    "audio_quality_flag", "extraction_software_version", "device_firmware_version", "phrase_id",
}  # fmt: skip


def _record(row: dict[str, str]) -> dict[str, Any]:
    """One SRC-05 row as a JSON record (numbers as JSON numbers)."""
    return {
        k: v if k in TEXT_FIELDS else int(v) if k == "number_of_pauses" else float(v)
        for k, v in row.items()
    }


def _post_one_by_one(harness: TierB) -> dict[int, int]:
    harness.client.app.dependency_overrides[get_clock] = lambda: lambda: AS_OF  # type: ignore[attr-defined]
    key = {"X-API-Key": SEED_SECRETS["SEED_INGEST_API_KEY"]}
    codes: dict[int, int] = {}
    for row in input_rows():
        response = harness.client.post("/api/v1/sessions", json=_record(row), headers=key)
        assert response.status_code in (200, 201), (row["session_id"], response.text)
        codes[response.status_code] = codes.get(response.status_code, 0) + 1
    latest = harness.select(
        "SELECT id FROM pipeline_runs ORDER BY started_at DESC, id DESC LIMIT 1"
    )
    harness.run = {"id": latest[0][0]}
    return codes


TRAILING_DUPLICATE = {"annotated/('R04', 18, 283)", "status_counts/('R04',)/duplicate"}


@pytest.mark.slow
@pytest.mark.req("TST-049", "AC-ANL-06", "MVP-02", "BR-15", "API-044", "ING-036")
def test_tst_049_one_record_at_a_time_equals_one_batch(tier_b_outputs: Outputs) -> None:
    with tier_b(ingest=False) as harness:
        codes = _post_one_by_one(harness)
        single = collect(harness)
        harness.run_at_as_of()  # the next run (nightly run in production)
        after_run = collect(harness)
    assert sum(codes.values()) == 283
    assert codes.get(200, 0) == 2  # the two SRC-05 duplicates answer 200, no run (API-044)
    before = compare_outputs(tier_b_outputs, single, "TST-049 batch vs one record at a time")
    assert before.checks > 0
    assert {m.key for m in before.mismatches} == TRAILING_DUPLICATE, before.mismatches[:10]
    result = compare_outputs(tier_b_outputs, after_run, "TST-049 batch vs single posts + next run")
    assert result.checks > 0
    assert result.mismatches == [], result.mismatches[:10]
