"""The device panel (TRD 05 API-086; TRD 19 E-17; TRD 06 DB-044, DB-066; FEAT-029). Values come
from the `scene` fixture (as-of 2026-10-30)."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.integration.api.conftest import Principals
from tests.integration.world import World

pytestmark = pytest.mark.integration

DEVICES = "/api/v1/devices"


def _devices(api: TestClient, principals: Principals, **params: Any) -> dict[str, Any]:
    response = api.get(DEVICES, params=params, headers=principals.bearer("researcher"))
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


@pytest.mark.req("API-086", "FR-150", "FR-151", "FR-152", "FR-153", "FR-154", "FR-155", "DB-044",
                 "DB-066", "D-114", "FEAT-029-AC-01", "FEAT-029-AC-03", "FEAT-029-AC-05",
                 "FEAT-029-AC-06", "FEAT-029-FR-01", "FEAT-029-FR-02", "FEAT-029-FR-03",
                 "FEAT-029-FR-04", "FEAT-029-FR-05", "FEAT-029-FR-06", "FEAT-029-FR-07",
                 "FEAT-029-FR-08", "FEAT-029-FR-09")  # fmt: skip
def test_device_panel(api: TestClient, scene: World, principals: Principals) -> None:
    body = _devices(api, principals)
    assert body["meta"]["as_of"] == "2026-10-30T20:00:00Z"
    assert body["total"] == 10
    items = {d["device_code"]: d for d in body["items"]}
    assert list(items) == ["D01", "D02", "D04", "D05", "D06", "D07", "D07B", "D08", "D09", "D10"]
    d02 = items["D02"]
    assert (d02["resident_codes"], d02["shared"]) == (["R02", "R03"], True)
    assert d02["silent_days_last_30"] == ["2026-10-14"]
    assert d02["device_gap_days_last_30"] == ["2026-10-14"]
    d07, d07b = items["D07"], items["D07B"]
    assert (d07["active"], d07["in_use_since"], d07["in_use_until"]) == (
        False, "2026-10-01", "2026-10-12"
    )  # fmt: skip
    assert (d07["replaces_device_code"], d07["replaced_by_device_code"]) == (None, "D07B")
    assert d07["resident_codes"] == []
    assert (d07b["replaces_device_code"], d07b["replaced_by_device_code"]) == ("D07", None)
    assert (d07b["in_use_since"], d07b["in_use_until"]) == ("2026-10-13", None)
    assert d07b["uploaded_on_as_of_date"] is True
    assert d07b["last_upload_at"] == "2026-10-30T19:00:00Z"
    assert d07b["last_upload_local"] == "2026-10-30T14:00:00-05:00"
    d01 = items["D01"]
    assert d01["uploaded_on_as_of_date"] is False  # last record Oct 22, the day before is not it
    assert d01["last_upload_at"] == "2026-10-22T13:00:00Z"  # a duplicate arrival is still an upload
    assert d01["silent_days_last_30"] == ["2026-10-23"]
    assert d01["device_gap_days_last_30"] == []
    assert d01["firmware_version"] == "fw-1.0.0"
    assert items["D04"]["last_upload_at"] is None
    assert {d["device_code"] for d in body["items"] if d["uploaded_on_as_of_date"]} == {"D07B"}


@pytest.mark.req("API-100", "FEAT-029-FR-01")
def test_device_paging(api: TestClient, scene: World, principals: Principals) -> None:
    page = _devices(api, principals, limit=2, offset=5)
    assert [d["device_code"] for d in page["items"]] == ["D07", "D07B"]
    assert (page["total"], page["limit"], page["offset"]) == (10, 2, 5)
