"""`GET /api/v1/config/ui` (TRD 05 API-137; TRD 19 E-32; FEAT-030-FR-06)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.repositories.config_repository import ConfigRepository
from tests.integration.api.conftest import Principals

pytestmark = pytest.mark.integration


@pytest.mark.req("API-137", "ENV-020", "D-56", "FEAT-030-AC-05", "FEAT-030-FR-06")
def test_ui_config(api: TestClient, roster: Session, principals: Principals) -> None:
    response = api.get("/api/v1/config/ui", headers=principals.bearer("researcher"))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["meta"]["pipeline_profile"] == "test_v0_1"
    assert body["alert_snooze_hours"] == 24
    assert body["review_explanations"] == [
        {"code": "cold_cough_sore_throat", "label": "Cold, cough or sore throat"},
        {"code": "dental_dentures", "label": "Dental problem or dentures out"},
        {"code": "medication_change", "label": "New or changed medication"},
        {"code": "poor_sleep_unusual_day", "label": "Poor sleep or unusual day"},
        {"code": "room_device_moved", "label": "Room or device moved"},
    ]
    ConfigRepository(roster).update_value("test_v0_1", "alert_snooze_hours", 12)
    roster.commit()
    again = api.get("/api/v1/config/ui", headers=principals.bearer("admin")).json()
    assert again["alert_snooze_hours"] == 12  # read on every request, no cache
