"""The authorisation matrix with exact statuses (TRD 13 TST-130, Table 4.13-A, AC-TST-05; TRD 12
SEC-041, SEC-045, AC-SEC-01; FEAT-039-FR-01, FEAT-039-FR-09, FEAT-039-AC-01, FEAT-039-AC-08).

`MATRIX` mirrors Table 4.13-A row by row (grouped rows split per endpoint). Every call is a valid
request on the `scene` data, so an allowed caller gets the endpoint's success status and a refused
one 401 or 403. "key" is an API key with `ingest:write`; `POST /pipeline/run` is also called with a
`pipeline:run` key (contract R18). `POST /auth/login`, `GET /config/ui` and `GET /openapi.json` are
not in the table; their rows follow the TRD 12 §4.6 matrix.
"""

from __future__ import annotations

import csv
import uuid
from dataclasses import dataclass
from datetime import date
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.api.permissions import PERMISSIONS
from backend.models import Alert, Facility, Resident
from tests.integration.api.conftest import PASSWORD, Principals
from tests.integration.api.test_sessions import SRC_05, src05_record
from tests.integration.world import World

pytestmark = pytest.mark.security

CALLERS = ("anon", "key", "admin", "clinician", "researcher")
READ = (401, 401, 200, 200, 200)
STUDY_TEAM = (401, 401, 200, 403, 200)
STAFF_WRITE = (401, 401, 201, 201, 403)
# (endpoint as in PERMISSIONS, statuses for CALLERS); ids come from `Targets`.
MATRIX: dict[str, tuple[int, ...]] = {
    "GET /health": (200, 200, 200, 200, 200),
    "GET /openapi.json": (200, 200, 200, 200, 200),
    "POST /auth/login": (200, 200, 200, 200, 200),
    "GET /auth/me": READ,
    "POST /auth/logout": (401, 401, 204, 204, 204),
    "GET /config/ui": READ,
    "POST /sessions": (401, 201, 401, 401, 401),
    "POST /ingest": (401, 202, 202, 403, 403),
    "GET /ingest/batches/{id}": STUDY_TEAM,
    "GET /residents": READ,
    "GET /residents/{resident_code}": READ,
    "GET /residents/{resident_code}/checkins": READ,
    "GET /residents/{resident_code}/features": READ,
    "GET /residents/{resident_code}/notes": READ,
    "GET /scores": READ,
    "GET /scores (text/csv)": STUDY_TEAM,
    "GET /alerts": READ,
    "GET /alerts/{id}/reviews": READ,
    "GET /data-alerts": READ,
    "GET /devices": READ,
    "GET /admissions": READ,
    "GET /admissions/{resident_code}/comparison": READ,
    "GET /facility/reference-ranges": READ,
    "POST /alerts/{id}/reviews": STAFF_WRITE,
    "POST /alerts/{id}/snooze": (401, 401, 200, 200, 403),
    "POST /residents/{resident_code}/notes": STAFF_WRITE,
    "GET /analytics": STUDY_TEAM,
    "GET /analytics/baselines": STUDY_TEAM,
    "POST /pipeline/run": (401, 403, 202, 403, 403),
    "GET /pipeline/runs": STUDY_TEAM,
    "GET /pipeline/runs/{id}": STUDY_TEAM,
    "GET /users": (401, 401, 200, 403, 403),
    "POST /users": (401, 401, 201, 403, 403),
    "PATCH /users/{id}": (401, 401, 200, 403, 403),
}


def _session_ids() -> list[str]:
    with SRC_05.open(newline="", encoding="utf-8") as handle:
        return [r["session_id"] for r in csv.DictReader(handle) if r["resident_id"] == "R09"]


SESSION_IDS = _session_ids()  # R09 has no rows in `scene`, so no call is a duplicate


@dataclass
class Targets:
    alert_id: uuid.UUID
    run_id: uuid.UUID
    batch_id: str
    user_id: uuid.UUID


@pytest.fixture
def targets(api: TestClient, scene: World, principals: Principals) -> Targets:
    """An open alert (R01), a pipeline run, an ingest batch, a user to edit and a new admission
    (N01) for the comparison endpoint."""
    facility_id = scene.session.scalars(select(Facility.id)).one()
    scene.session.add(
        Resident(facility_id=facility_id, resident_code="N01", sex="F", cohort="new_admission",
                 enrolled_on=date(2026, 10, 20), admitted_on=date(2026, 10, 20))
    )  # fmt: skip
    scene.session.commit()
    alert_id = scene.session.scalars(
        select(Alert.id).where(Alert.resident_id == scene.residents["R01"])
    ).one()
    batch = api.post("/api/v1/ingest", json={"records": [src05_record(SESSION_IDS[-1])]},
                     headers=principals.api_key("ingest"))  # fmt: skip
    assert batch.status_code == 202, batch.text
    other = principals.add_user("clinician")
    return Targets(alert_id, scene.run_id, batch.json()["ingest_batch_id"], other.id)


def _call(endpoint: str, t: Targets, principals: Principals, n: int) -> dict[str, Any]:
    """Method, path and a valid body for one call; `n` keeps created records unique."""
    method, path = endpoint.split(" ")[:2]
    path = (
        path.replace("{resident_code}", "N01" if "admissions" in path else "R01")
        .replace("/alerts/{id}", f"/alerts/{t.alert_id}")
        .replace("/batches/{id}", f"/batches/{t.batch_id}")
        .replace("/runs/{id}", f"/runs/{t.run_id}")
        .replace("/users/{id}", f"/users/{t.user_id}")
    )
    call: dict[str, Any] = {"method": method, "url": f"/api/v1{path}", "headers": {}}
    if endpoint.endswith("(text/csv)"):
        call["headers"]["Accept"] = "text/csv"
    bodies: dict[str, Any] = {
        "POST /auth/login": {"email": principals.users["admin"].email, "password": PASSWORD},
        "POST /sessions": src05_record(SESSION_IDS[n % 29]),
        "POST /ingest": {"records": [src05_record(SESSION_IDS[n % 29])]},
        "POST /alerts/{id}/reviews": {"outcome": "known_cause"},
        "POST /alerts/{id}/snooze": {"hours": 4},
        "POST /residents/{resident_code}/notes": {"note_type": "observation", "body": "Synthetic."},
        "POST /pipeline/run": {"scope": ["R01"]},
        "POST /users": {"email": f"new-{n}-{uuid.uuid4().hex[:6]}@example.test",
                        "display_name": "New user", "role": "researcher", "password": PASSWORD},
        "PATCH /users/{id}": {"display_name": f"Renamed {n}"},
    }  # fmt: skip
    if endpoint in bodies:
        call["json"] = bodies[endpoint]
    return call


def _credentials(principals: Principals, caller: str) -> dict[str, str]:
    if caller == "anon":
        return {}
    if caller == "key":
        return principals.api_key("ingest")
    if caller == "pipeline-key":
        return principals.api_key("pipeline")
    return principals.bearer(caller)


@pytest.mark.req("TST-130", "SEC-041", "AC-SEC-01", "AC-TST-05")
def test_matrix_covers_every_endpoint() -> None:
    assert set(MATRIX) == set(PERMISSIONS)


@pytest.mark.req(
    "TST-130", "SEC-041", "SEC-045", "AC-SEC-01", "AC-TST-05", "FR-212", "FR-213",
    "FEAT-039-FR-01", "FEAT-039-FR-09", "FEAT-039-AC-01", "FEAT-039-AC-08",
)  # fmt: skip
@pytest.mark.parametrize("caller", CALLERS)
def test_every_cell(api: TestClient, principals: Principals, targets: Targets, caller: str) -> None:
    failures = []
    for n, (endpoint, statuses) in enumerate(MATRIX.items()):
        expected = statuses[CALLERS.index(caller)]
        call = _call(endpoint, targets, principals, n)
        call["headers"] |= _credentials(principals, caller)
        response = api.request(**call)
        if response.status_code != expected:
            failures.append(f"{endpoint} as {caller}: expected {expected}, got "
                            f"{response.status_code} {response.text[:160]}")  # fmt: skip
        elif expected in (401, 403):
            code = "FORBIDDEN" if expected == 403 else None
            if code:
                assert response.json()["type"] == f"urn:echowell:error:{code}", endpoint
    assert failures == []


@pytest.mark.req("TST-130", "TST-132", "FEAT-039-FR-01", "FEAT-039-AC-01")
def test_pipeline_run_key_scopes(api: TestClient, principals: Principals, targets: Targets) -> None:
    call = _call("POST /pipeline/run", targets, principals, 0)
    for caller, expected in (("key", 403), ("pipeline-key", 202)):
        response = api.request(**{**call, "headers": _credentials(principals, caller)})
        assert response.status_code == expected, (caller, response.text)
