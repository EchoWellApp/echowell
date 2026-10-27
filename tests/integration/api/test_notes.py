"""Staff notes (TRD 05 API-083..API-085; TRD 19 E-15, E-16; TRD 06 DB-010; FEAT-033). Data come
from the `scene` fixture (R01 has an open alert)."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from backend.models import Alert, Epoch
from tests.integration.api.conftest import Principals
from tests.integration.world import World

pytestmark = pytest.mark.integration


def _notes(code: str) -> str:
    return f"/api/v1/residents/{code}/notes"


def _post(api: TestClient, principals: Principals, code: str, role: str = "clinician",
          **body: Any) -> Any:  # fmt: skip
    return api.post(_notes(code), json={"note_type": "observation", **body},
                    headers=principals.bearer(role))  # fmt: skip


def _problem(response: Any, status: int, code: str) -> dict[str, Any]:
    assert response.status_code == status, response.text
    body: dict[str, Any] = response.json()
    assert body["type"] == f"urn:echowell:error:{code}", body
    return body


def _count(scene: World, table: str) -> int:
    return int(scene.session.execute(text(f"SELECT count(*) FROM {table}")).scalar_one())  # noqa: S608


def _alert(scene: World, resident: str) -> uuid.UUID:
    alert_id: uuid.UUID = scene.session.scalars(
        select(Alert.id).where(Alert.resident_id == scene.residents[resident])
    ).one()
    return alert_id


@pytest.mark.req(
    "API-084", "TST-053", "AC-SEC-09", "SEC-104", "FR-190", "FR-191", "FEAT-033-AC-01",
    "FEAT-033-AC-05", "FEAT-033-FR-04", "FEAT-033-FR-06",
)  # fmt: skip
def test_create_note(api: TestClient, scene: World, principals: Principals) -> None:
    alert_id = _alert(scene, "R01")
    body = "Resident has a cold; nurse notified."
    response = _post(api, principals, "R01", body=body, alert_id=str(alert_id))
    assert response.status_code == 201, response.text
    note = response.json()
    clinician = principals.users["clinician"]
    assert note["author"] == {"id": str(clinician.id), "display_name": clinician.display_name}
    assert (note["resident_code"], note["note_type"], note["body"], note["supersedes_id"]) == (
        "R01", "observation", body, None
    )  # fmt: skip
    assert note["alert_id"] == str(alert_id)
    audit = scene.session.execute(
        text("SELECT entity_id, details FROM audit_logs WHERE action = 'note.created'")
    ).one()
    assert audit.entity_id == note["id"]
    assert audit.details == {"resident_code": "R01", "note_type": "observation",
                             "alert_id": str(alert_id), "supersedes_id": None}  # fmt: skip
    assert body not in str(audit.details)
    alert = scene.session.execute(
        text("SELECT status, acknowledged_at, snoozed_until FROM alerts WHERE id = :i"),
        {"i": alert_id},
    ).one()
    assert tuple(alert) == ("open", None, None)
    marked = scene.session.execute(text("SELECT marked_reviewed FROM staff_notes")).scalar_one()
    assert marked is False


@pytest.mark.req("API-084", "PGS-036", "FEAT-033-AC-02", "FEAT-033-FR-02")
@pytest.mark.parametrize(
    "body",
    [
        {"body": "   "},
        {"body": "x" * 2001},
        {"body": ""},
        {"note_type": "diagnosis", "body": "x"},
        {"body": "x", "marked_reviewed": True},
    ],
)
def test_invalid_notes(
    api: TestClient, scene: World, principals: Principals, body: dict[str, Any]
) -> None:
    _problem(_post(api, principals, "R01", **body), 422, "VALIDATION_ERROR")
    assert _count(scene, "staff_notes") == 0


@pytest.mark.req("API-085", "FEAT-033-AC-03", "FEAT-033-FR-03")
def test_alert_and_supersedes_ownership(
    api: TestClient, scene: World, principals: Principals
) -> None:
    epoch = scene.session.scalars(
        select(Epoch.id).where(Epoch.resident_id == scene.residents["R03"])
    ).one()
    other = scene.alert("R03", epoch, "R03-20261002-01", date(2026, 10, 2))
    scene.session.commit()
    _problem(_post(api, principals, "R01", body="x", alert_id=str(other)), 422,
             "ALERT_RESIDENT_MISMATCH")  # fmt: skip
    _problem(_post(api, principals, "R01", body="x", alert_id=str(uuid.uuid4())), 404,
             "ALERT_NOT_FOUND")  # fmt: skip
    r03_note = _post(api, principals, "R03", body="R03 note").json()
    wrong = _problem(_post(api, principals, "R01", body="x", supersedes_id=r03_note["id"]), 422,
                     "VALIDATION_ERROR")  # fmt: skip
    assert wrong["errors"][0]["field"] == "supersedes_id"
    _problem(_post(api, principals, "R01", body="x", supersedes_id=str(uuid.uuid4())), 422,
             "VALIDATION_ERROR")  # fmt: skip
    _problem(_post(api, principals, "R11", body="x"), 404, "RESIDENT_NOT_FOUND")
    _problem(_post(api, principals, "R01", role="researcher", body="x"), 403, "FORBIDDEN")
    assert _count(scene, "staff_notes") == 1


@pytest.mark.req("API-083", "DB-010", "FR-192", "FR-193", "D-83", "FEAT-033-AC-04",
                 "FEAT-033-AC-06", "FEAT-033-FR-05", "FEAT-033-FR-07")  # fmt: skip
def test_superseding_and_listing(api: TestClient, scene: World, principals: Principals) -> None:
    a = _post(api, principals, "R01", body="Note A").json()
    b = _post(api, principals, "R01", role="admin", body="Note B (corrects A)",
              supersedes_id=a["id"]).json()  # fmt: skip
    assert b["supersedes_id"] == a["id"]
    again = _problem(_post(api, principals, "R01", body="C", supersedes_id=a["id"]), 422,
                     "VALIDATION_ERROR")  # fmt: skip
    assert again["errors"][0]["field"] == "supersedes_id"
    current = api.get(_notes("R01"), headers=principals.bearer("researcher")).json()
    assert [n["id"] for n in current["items"]] == [b["id"]]
    assert current["total"] == 1
    everything = api.get(_notes("R01"), params={"include_superseded": "true"},
                         headers=principals.bearer("researcher")).json()  # fmt: skip
    assert [n["id"] for n in everything["items"]] == [b["id"], a["id"]]
    assert api.get(_notes("R02"), headers=principals.bearer("clinician")).json()["total"] == 0
    _problem(api.get(_notes("R11"), headers=principals.bearer("clinician")), 404,
             "RESIDENT_NOT_FOUND")  # fmt: skip
