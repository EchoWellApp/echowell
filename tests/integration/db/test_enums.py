"""DTO enums equal the database enums (TRD 19 OAS-007, AC-OAS-06; FEAT-038-AC-06).

The DTO side is read from the generated OpenAPI document, so the test covers what clients see.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import pytest
from sqlalchemy import Connection, text

from tests.contract.response_validation import document

pytestmark = pytest.mark.integration

# OpenAPI_Spec.md §9: the fourteen DTO enum / database enum pairs.
PAIRS = {
    "ProcessedStatus": "session_status",
    "DayStatus": "day_status",
    "AlarmState": "alarm_state",
    "AlertStatus": "alert_status",
    "NoteType": "note_type",
    "Role": "user_role",
    "Cohort": "resident_cohort",
    "ResidentStatus": "resident_status",
    "PipelineTrigger": "pipeline_trigger",
    "PipelineStatus": "pipeline_run_status",
    "IngestSource": "ingest_source",
    "ReviewOutcome": "review_outcome",
    "DataAlertKind": "data_alert_kind",
    "DataAlertStatus": "data_alert_status",
}


def _pg_enums(conn: Connection) -> dict[str, list[str]]:
    rows = conn.execute(
        text("SELECT t.typname, e.enumlabel FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid "
             "ORDER BY t.typname, e.enumsortorder")
    )  # fmt: skip
    labels: dict[str, list[str]] = defaultdict(list)
    for typname, label in rows:
        labels[typname].append(label)
    return labels


@pytest.mark.req("OAS-007", "AC-OAS-06", "FEAT-038-AC-06", "FEAT-038-FR-05")
def test_dto_enums_equal_pg_enums(app_conn: Connection) -> None:
    schemas: dict[str, Any] = document()["components"]["schemas"]
    labels = _pg_enums(app_conn)
    for dto, pg in PAIRS.items():
        assert schemas[dto]["enum"] == labels[pg], dto
