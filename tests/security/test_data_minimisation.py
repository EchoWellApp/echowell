"""Study IDs only: responses and logs for an SRC-05 upload identify no person (TRD 13 TST-137;
TRD 12 SEC-120; TRD 03 NFR-041, NFR-048, NFR-050; TRD 25 AGT-017; FEAT-039-FR-06,
FEAT-039-FR-10, FEAT-039-AC-06, FEAT-039-AC-08).

Staff accounts (`/users`, `/auth/me`, reviewer and author names) are not residents and are left
out; `room_label` is the TRD 19 non-identifying device label."""

from __future__ import annotations

import csv
import io
import re
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.models import FEATURE_KEYS
from tests.integration.api.conftest import LogCapture, Principals
from tests.integration.api.test_sessions import SRC_05

pytestmark = pytest.mark.security

PERSONAL = re.compile(
    r"(^|_)(first|last|full|given|family|sur)?_?name$|dob|birth|room_?(number|no)$|phone|address"
    r"|^email$|contact|ssn|mrn|insurance",
    re.IGNORECASE,
)
STAFF_KEYS = {"display_name", "facility_name"}
READS = (
    "/api/v1/residents", "/api/v1/residents/R01", "/api/v1/residents/R01/checkins",
    "/api/v1/residents/R01/features", "/api/v1/residents/R01/notes", "/api/v1/scores",
    "/api/v1/alerts", "/api/v1/data-alerts", "/api/v1/devices", "/api/v1/analytics",
    "/api/v1/analytics/baselines", "/api/v1/pipeline/runs", "/api/v1/admissions",
    "/api/v1/config/ui",
)  # fmt: skip


def _keys(node: Any) -> set[str]:
    if isinstance(node, dict):
        return set(node) | {k for v in node.values() for k in _keys(v)}
    if isinstance(node, list):
        return {k for v in node for k in _keys(v)}
    return set()


def _feature_values() -> set[str]:
    """Distinctive feature cells of SRC-05 (two or more decimals), to look for in logs."""
    with SRC_05.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return {row[k] for row in rows for k in FEATURE_KEYS if re.fullmatch(r"-?\d+\.\d{2,}", row[k])}


@pytest.mark.req("TST-137", "SEC-120", "NFR-041", "NFR-048", "AGT-017", "FEAT-039-FR-06",
                 "FEAT-039-AC-06")  # fmt: skip
def test_responses_and_logs_hold_study_ids_only(
    api: TestClient, roster: Session, principals: Principals, log_capture: LogCapture
) -> None:
    log_capture.start()
    upload = api.post("/api/v1/ingest", files={"file": ("input.csv", SRC_05.read_bytes(),
                      "text/csv")}, headers=principals.bearer("admin"))  # fmt: skip
    assert upload.status_code == 202, upload.text
    bodies = [upload.json(), api.get(f"/api/v1/ingest/batches/{upload.json()['ingest_batch_id']}",
                                     headers=principals.bearer("admin")).json()]  # fmt: skip
    for path in READS:
        response = api.get(path, headers=principals.bearer("admin"))
        assert response.status_code == 200, (path, response.text)
        bodies.append(response.json())
    keys = _keys(bodies) - STAFF_KEYS
    assert sorted(k for k in keys if PERSONAL.search(k)) == []
    records = log_capture.lines()
    assert records, "no log records captured"
    log_keys = _keys(records)
    assert sorted(k for k in log_keys if PERSONAL.search(k)) == []
    assert not log_keys & set(FEATURE_KEYS), "a feature value was logged"
    text = "\n".join(str(r) for r in records)
    leaked = [v for v in _feature_values() if re.search(rf"(?<![\d.]){re.escape(v)}(?![\d])", text)]
    assert leaked == []


@pytest.mark.req("FR-245", "NFR-050", "FEAT-039-FR-10", "FEAT-039-AC-08")
def test_csv_exports_hold_no_note_text(api: TestClient, scene: Any, principals: Principals) -> None:
    note = "Synthetic note text 7f3a: resident seemed tired."
    created = api.post("/api/v1/residents/R01/notes", json={"note_type": "observation",
                       "body": note}, headers=principals.bearer("clinician"))  # fmt: skip
    assert created.status_code == 201, created.text
    for path in ("/api/v1/scores", "/api/v1/analytics/baselines"):
        response = api.get(path, headers={**principals.bearer("researcher"), "Accept": "text/csv"})
        assert response.status_code == 200, response.text
        assert "7f3a" not in response.text
        header = next(csv.reader(io.StringIO(response.text)))
        assert sorted(h for h in header if PERSONAL.search(h)) == []
        assert not {"body", "note", "notes"} & set(header)
