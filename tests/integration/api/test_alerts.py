"""Alerts, reviews, snooze and data alerts (TRD 05 API-080..API-082, API-130..API-133; TRD 09
CUS-016..CUS-045; FEAT-030, FEAT-031, FEAT-032). Data come from the `scene` fixture: R01 has an
open alert on 2026-10-20 (current tally 7.5)."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import pytest
import time_machine
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from backend.models import Alert, DataAlert, Epoch
from tests.integration.api.conftest import Principals
from tests.integration.world import World

pytestmark = pytest.mark.integration

ALERTS = "/api/v1/alerts"
SILENT_AT = datetime(2026, 10, 12, 13, tzinfo=UTC)


def _problem(response: Any, status: int, code: str) -> dict[str, Any]:
    assert response.status_code == status, response.text
    body: dict[str, Any] = response.json()
    assert body["type"] == f"urn:echowell:error:{code}", body
    return body


def _epoch(scene: World, resident: str) -> uuid.UUID:
    epoch_id: uuid.UUID = scene.session.scalars(
        select(Epoch.id).where(
            Epoch.resident_id == scene.residents[resident], Epoch.ended_at.is_(None)
        )
    ).one()
    return epoch_id


def _r01_alert(scene: World) -> uuid.UUID:
    alert_id: uuid.UUID = scene.session.scalars(
        select(Alert.id).where(Alert.resident_id == scene.residents["R01"])
    ).one()
    return alert_id


def _snapshot(scene: World) -> list[Any]:
    """`scores` and `cusum_state` rows, to show a review or snooze changes neither (AGT-058)."""
    rows = []
    for table in ("scores", "cusum_state"):
        rows += [tuple(r) for r in scene.session.execute(text(f"SELECT * FROM {table} ORDER BY 1"))]  # noqa: S608
    return rows


def _review(api: TestClient, principals: Principals, alert_id: Any, role: str = "clinician",
            **body: Any) -> Any:  # fmt: skip
    return api.post(f"{ALERTS}/{alert_id}/reviews", json={"outcome": "known_cause", **body},
                    headers=principals.bearer(role))  # fmt: skip


@pytest.mark.req("API-080", "CUS-022", "CUS-025", "FR-109", "FEAT-030-AC-02", "FEAT-030-AC-06",
                 "FEAT-030-FR-01", "FEAT-030-FR-02", "FEAT-030-FR-03", "FEAT-030-FR-04",
                 "FEAT-030-FR-08", "FEAT-032-FR-04")  # fmt: skip
def test_alert_list(api: TestClient, scene: World, principals: Principals) -> None:
    scene.alert("R02", _epoch(scene, "R02"), "R02-20261024-01", date(2026, 10, 24), value=5.1)
    scene.session.commit()
    body = api.get(ALERTS, headers=principals.bearer("researcher")).json()
    assert body["meta"]["as_of"] == "2026-10-30T20:00:00Z"
    assert [(a["resident_code"], a["local_date"]) for a in body["items"]] == [
        ("R01", "2026-10-20"), ("R02", "2026-10-24")
    ]  # fmt: skip
    r01 = body["items"][0]
    assert {k: r01[k] for k in ("device_code", "epoch_number", "session_id", "cusum_value",
                                "current_tally", "open_days", "status", "reviewed",
                                "review_count", "last_reviewed_at", "snoozed_until",
                                "snoozed_by", "leaning_most", "closed_reason")} == {
        "device_code": "D01", "epoch_number": 1, "session_id": "R01-20261020-01",
        "cusum_value": 5.4, "current_tally": 7.5, "open_days": 10, "status": "open",
        "reviewed": False, "review_count": 0, "last_reviewed_at": None, "snoozed_until": None,
        "snoozed_by": None, "leaning_most": [], "closed_reason": None,
    }  # fmt: skip
    assert body["items"][1]["current_tally"] is None  # R02 has no cusum_state row
    assert api.get(ALERTS, params={"status": "open"},
                   headers=principals.bearer("admin")).json()["total"] == 2  # fmt: skip
    mine = api.get(ALERTS, params={"resident_code": "R02"}, headers=principals.bearer("admin"))
    assert [a["resident_code"] for a in mine.json()["items"]] == ["R02"]
    nobody = api.get(ALERTS, params={"resident_code": "R99"}, headers=principals.bearer("admin"))
    assert nobody.json()["total"] == 0
    for params in ({"status": "bogus"}, {"resident_code": "r01"}, {"limit": 0}):
        _problem(api.get(ALERTS, params=params, headers=principals.bearer("admin")), 422,
                 "INVALID_QUERY_PARAMETER")  # fmt: skip


@pytest.mark.req("API-081", "CUS-016", "CUS-017", "CUS-008", "DME-007", "D-03", "TST-056",
                 "TST-057", "AC-CUS-06", "FEAT-031-AC-01", "FEAT-031-AC-02", "FEAT-031-AC-08",
                 "FEAT-030-AC-03", "FEAT-031-FR-03", "FEAT-031-FR-04", "FEAT-031-FR-06",
                 "FEAT-031-FR-10")  # fmt: skip
def test_reviews(api: TestClient, scene: World, principals: Principals) -> None:
    alert_id = _r01_alert(scene)
    before = _snapshot(scene)
    first = _review(api, principals, alert_id, explanations=["poor_sleep_unusual_day"],
                    note="Slept badly; family visit.")  # fmt: skip
    assert first.status_code == 201, first.text
    review = first.json()
    clinician = principals.users["clinician"]
    assert review["reviewer"] == {"id": str(clinician.id), "display_name": clinician.display_name}
    assert (review["outcome"], review["explanations"]) == (
        "known_cause",
        ["poor_sleep_unusual_day"],
    )
    alert = scene.session.execute(
        text("SELECT status, acknowledged_by, cusum_value FROM alerts WHERE id = :i"),
        {"i": alert_id},
    ).one()
    assert tuple(alert) == ("acknowledged", clinician.id, 5.4)
    second = _review(api, principals, alert_id, role="admin", outcome="no_concern")
    assert second.status_code == 201
    assert _snapshot(scene) == before  # scores and cusum_state untouched
    listed = api.get(f"{ALERTS}/{alert_id}/reviews", headers=principals.bearer("researcher"))
    assert [r["id"] for r in listed.json()["items"]] == [second.json()["id"], review["id"]]
    assert listed.json()["total"] == 2
    item = api.get(ALERTS, headers=principals.bearer("admin")).json()["items"][0]
    assert (item["status"], item["reviewed"], item["review_count"]) == ("acknowledged", True, 2)
    assert item["last_reviewed_at"] == second.json()["created_at"]
    audits = (
        scene.session.execute(
            text("SELECT details FROM audit_logs WHERE action = 'alert.reviewed' ORDER BY id")
        )
        .scalars()
        .all()
    )
    assert [a["previous_status"] for a in audits] == ["open", "acknowledged"]
    assert audits[0] == {"resident_code": "R01", "review_id": review["id"],
                         "outcome": "known_cause", "explanation_count": 1,
                         "previous_status": "open"}  # fmt: skip
    assert "Slept badly" not in str(audits)


@pytest.mark.req("API-082", "CUS-038", "DME-021", "TST-058", "FR-271", "FEAT-031-AC-03",
                 "FEAT-031-FR-02")  # fmt: skip
@pytest.mark.parametrize(
    "body",
    [
        {"explanations": []},
        {"outcome": "fine"},
        {"outcome": "known_cause", "explanations": ["headache"]},
        {"outcome": "known_cause", "explanations": ["dental_dentures", "dental_dentures"]},
        {"outcome": "known_cause", "explanations": ["a", "b", "c", "d", "e", "f"]},
        {"outcome": "known_cause", "note": "x" * 2001},
        {"outcome": "known_cause", "extra": 1},
    ],
)
def test_invalid_reviews_write_nothing(
    api: TestClient, scene: World, principals: Principals, body: dict[str, Any]
) -> None:
    alert_id = _r01_alert(scene)
    response = api.post(f"{ALERTS}/{alert_id}/reviews", json=body,
                        headers=principals.bearer("clinician"))  # fmt: skip
    _problem(response, 422, "VALIDATION_ERROR")
    assert scene.session.execute(text("SELECT count(*) FROM alert_reviews")).scalar_one() == 0
    status = scene.session.execute(
        text("SELECT status FROM alerts WHERE id = :i"), {"i": alert_id}
    ).scalar_one()
    assert status == "open"


@pytest.mark.req("API-130", "CUS-040", "D-114", "TST-059", "FR-273", "FEAT-031-AC-04",
                 "FEAT-031-FR-05")  # fmt: skip
def test_data_problem_review_creates_then_links(
    api: TestClient, scene: World, principals: Principals
) -> None:
    alert_id = _r01_alert(scene)
    first = _review(api, principals, alert_id, outcome="data_problem").json()
    second = _review(api, principals, alert_id, role="admin", outcome="data_problem").json()
    rows = scene.session.execute(
        text("SELECT resident_id, alert_review_id, title, detail, status, pipeline_run_id "
             "FROM data_alerts WHERE kind = 'review_flagged_data_problem'")
    ).all()  # fmt: skip
    assert len(rows) == 1
    row = rows[0]
    assert row.resident_id == scene.residents["R01"]
    assert str(row.alert_review_id) == second["id"] != first["id"]
    assert (row.title, row.status, row.pipeline_run_id) == (
        "R01 · review flagged a data problem", "open", None
    )  # fmt: skip
    local = datetime.fromisoformat(second["created_at"]).astimezone(ZoneInfo("America/Chicago"))
    admin = principals.users["admin"].display_name
    assert row.detail == f"a review flagged a data problem ({local:%b} {local.day}, {admin})."


@pytest.mark.req("API-132", "CUS-039", "DME-022", "D-37", "TST-065", "AC-CUS-10",
                 "FEAT-031-AC-05", "FEAT-031-FR-07", "FEAT-031-AC-08")  # fmt: skip
def test_snooze(api: TestClient, scene: World, principals: Principals) -> None:
    alert_id = _r01_alert(scene)
    before = _snapshot(scene)
    frozen = datetime(2026, 10, 30, 21, 0, tzinfo=UTC)
    with time_machine.travel(frozen, tick=False):
        default = api.post(f"{ALERTS}/{alert_id}/snooze", headers=principals.bearer("clinician"))
        assert default.status_code == 200, default.text
        assert default.json()["snoozed_until"] == "2026-10-31T21:00:00Z"
        assert default.json()["snoozed_by"] == str(principals.users["clinician"].id)
        assert default.json()["status"] == "open"
        four = api.post(f"{ALERTS}/{alert_id}/snooze", json={"hours": 4},
                        headers=principals.bearer("admin"))  # fmt: skip
    assert datetime.fromisoformat(four.json()["snoozed_until"]) == frozen + timedelta(hours=4)
    assert _snapshot(scene) == before
    for hours in (0, 169):
        _problem(api.post(f"{ALERTS}/{alert_id}/snooze", json={"hours": hours},
                          headers=principals.bearer("admin")), 422, "VALIDATION_ERROR")  # fmt: skip
    audits = (
        scene.session.execute(
            text("SELECT details FROM audit_logs WHERE action = 'alert.snoozed' ORDER BY id")
        )
        .scalars()
        .all()
    )
    assert [a["hours"] for a in audits] == [24, 4]
    assert audits[0]["snoozed_until"] == "2026-10-31T21:00:00+00:00"


@pytest.mark.req(
    "API-082", "D-35", "TST-066", "FR-275", "SEC-045", "FEAT-031-AC-06", "FEAT-031-AC-07",
    "FEAT-031-FR-01", "FEAT-031-FR-08", "FEAT-031-FR-09",
)  # fmt: skip
def test_refusals(api: TestClient, scene: World, principals: Principals) -> None:
    alert_id = _r01_alert(scene)
    closed = scene.alert("R03", _epoch(scene, "R03"), "R03-20261002-01", date(2026, 10, 2),
                         status="closed")  # fmt: skip
    scene.session.commit()
    clinician = principals.bearer("clinician")
    _problem(_review(api, principals, closed), 409, "ALERT_CLOSED")
    _problem(api.post(f"{ALERTS}/{closed}/snooze", headers=clinician), 409, "ALERT_CLOSED")
    _problem(_review(api, principals, uuid.uuid4()), 404, "ALERT_NOT_FOUND")
    _problem(api.post(f"{ALERTS}/{uuid.uuid4()}/snooze", headers=clinician), 404,
             "ALERT_NOT_FOUND")  # fmt: skip
    _problem(api.get(f"{ALERTS}/{uuid.uuid4()}/reviews", headers=clinician), 404,
             "ALERT_NOT_FOUND")  # fmt: skip
    assert _review(api, principals, "not-a-uuid").status_code == 422
    _problem(_review(api, principals, alert_id, role="researcher"), 403, "FORBIDDEN")
    _problem(api.post(f"{ALERTS}/{alert_id}/snooze", headers=principals.bearer("researcher")),
             403, "FORBIDDEN")  # fmt: skip
    acknowledge = api.post(f"{ALERTS}/{alert_id}/acknowledge", headers=clinician)
    assert acknowledge.status_code in (404, 405)
    assert scene.session.execute(text("SELECT count(*) FROM alert_reviews")).scalar_one() == 0


@pytest.mark.req("API-133", "CUS-045", "FR-299", "FEAT-032-AC-01", "FEAT-032-AC-02",
                 "FEAT-032-AC-07", "FEAT-032-FR-01", "FEAT-032-FR-02")  # fmt: skip
def test_data_alert_list(api: TestClient, scene: World, principals: Principals) -> None:
    scene.data_alert("R08", "baseline_stalled")
    scene.session.add(
        DataAlert(kind="device_silent", device_id=scene.devices["D02"], title="D02 · silent",
                  detail="d", first_detected_at=SILENT_AT, last_detected_at=SILENT_AT,
                  status="open", pipeline_run_id=scene.run_id)
    )  # fmt: skip
    scene.data_alert("R04", "baseline_stalled", status="resolved")
    scene.session.commit()
    body = api.get("/api/v1/data-alerts", headers=principals.bearer("clinician")).json()
    assert [(d["kind"], d["resident_code"] or d["device_code"]) for d in body["items"]] == [
        ("baseline_stalled", "R08"), ("possible_other_speaker", "R02"),
        ("high_set_aside", "R03"), ("device_silent", "D02"),
    ]  # fmt: skip
    assert set(body["items"][0]) == {"id", "kind", "resident_code", "device_code", "title",
                                     "detail", "status", "first_detected_at",
                                     "last_detected_at", "pipeline_run_id"}  # fmt: skip
    resolved = api.get("/api/v1/data-alerts", params={"status": "resolved"},
                       headers=principals.bearer("admin")).json()  # fmt: skip
    assert [d["resident_code"] for d in resolved["items"]] == ["R04"]
    stalled = api.get("/api/v1/data-alerts", params={"kind": "baseline_stalled"},
                      headers=principals.bearer("admin")).json()  # fmt: skip
    assert [d["resident_code"] for d in stalled["items"]] == ["R08"]
    unknown = api.get(
        "/api/v1/data-alerts", params={"kind": "unknown"}, headers=principals.bearer("admin")
    )
    _problem(unknown, 422, "INVALID_QUERY_PARAMETER")
    alerts = api.get(ALERTS, headers=principals.bearer("admin")).json()
    assert alerts["total"] == 1  # data alerts never count as alarms
