"""Score and baseline read-outs with CSV export (TRD 05 API-079, API-088, API-129; TRD 13 TST-079;
FEAT-034). Data come from the `scene` fixture: R01 has 4 scores (Oct 17..20) and R05 one, and
R01, R03 and R07 (epoch 2) have frozen baselines."""

from __future__ import annotations

import csv
import io
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from backend.models import FEATURE_KEYS
from backend.services import export_service, score_service
from tests.integration.api.conftest import Principals
from tests.integration.world import World

pytestmark = pytest.mark.integration

SCORES = "/api/v1/scores"
BASELINES = "/api/v1/analytics/baselines"
CSV = {"Accept": "text/csv"}


def _problem(response: Any, status: int, code: str) -> None:
    assert response.status_code == status, response.text
    assert response.json()["type"] == f"urn:echowell:error:{code}"


def _csv(response: Any) -> list[dict[str, str]]:
    assert response.status_code == 200, response.text
    return list(csv.DictReader(io.StringIO(response.text)))


@pytest.mark.req("API-079", "CUS-024", "OAS-011", "FR-242", "FEAT-034-FR-01", "FEAT-034-FR-02",
                 "FEAT-034-FR-03", "FEAT-034-FR-04")  # fmt: skip
def test_scores_json(api: TestClient, scene: World, principals: Principals) -> None:
    body = api.get(SCORES, params={"resident_code": "R01"},
                   headers=principals.bearer("clinician")).json()  # fmt: skip
    assert (body["total"], body["cusum_k"], body["meta"]["cusum_h"]) == (4, 0.5, 5.0)
    assert body["baseline_periods"] == [
        {"resident_code": "R01", "epoch_number": 1, "first_local_date": "2026-10-01",
         "frozen_after_local_date": "2026-10-16", "frozen_after_session_id": "R01-20261016-01",
         "n_sessions": 16}
    ]  # fmt: skip
    assert [r["session_id"] for r in body["items"]] == [
        "R01-20261017-01", "R01-20261018-01", "R01-20261019-01", "R01-20261020-01"
    ]  # fmt: skip
    last = body["items"][-1]
    assert (last["cusum_tally"], last["alarm_state"], last["epoch_number"]) == (5.4, "off", 1)
    assert list(last["z"]) == [f"z_{k}" for k in FEATURE_KEYS[:7]]
    everything = api.get(SCORES, headers=principals.bearer("admin")).json()
    assert everything["total"] == 5
    assert [p["resident_code"] for p in everything["baseline_periods"]] == ["R01"]
    window = api.get(SCORES, params={"from": "2026-10-18", "to": "2026-10-19"},
                     headers=principals.bearer("admin")).json()  # fmt: skip
    assert window["total"] == 2
    epoch2 = api.get(SCORES, params={"resident_code": "R05", "epoch": 2},
                     headers=principals.bearer("admin")).json()  # fmt: skip
    assert (epoch2["total"], epoch2["baseline_periods"]) == (1, [])


@pytest.mark.req("API-079", "API-093", "FEAT-034-AC-01")
def test_scores_parameters(api: TestClient, scene: World, principals: Principals) -> None:
    admin = principals.bearer("admin")
    _problem(api.get(SCORES, params={"epoch": 1}, headers=admin), 422, "INVALID_QUERY_PARAMETER")
    _problem(api.get(SCORES, params={"resident_code": "R11"}, headers=admin), 404,
             "RESIDENT_NOT_FOUND")  # fmt: skip
    _problem(api.get(SCORES, params={"from": "2026-10-20", "to": "2026-10-01"}, headers=admin),
             422, "INVALID_QUERY_PARAMETER")  # fmt: skip
    _problem(api.get(SCORES, params={"epoch": 0, "resident_code": "R01"}, headers=admin), 422,
             "INVALID_QUERY_PARAMETER")  # fmt: skip


@pytest.mark.req("API-129", "OAS-018", "TST-079", "AC-API-16", "FR-244", "SEC-108",
                 "FEAT-034-FR-06", "FEAT-034-FR-07", "FEAT-034-FR-08", "FEAT-034-AC-03",
                 "FEAT-034-AC-06")  # fmt: skip
def test_scores_csv(
    api: TestClient, scene: World, principals: Principals, audit_rows: list[dict[str, Any]]
) -> None:
    response = api.get(SCORES, headers={**principals.bearer("researcher"), **CSV})
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert response.headers["content-disposition"] == (
        'attachment; filename="echowell_scores_2026-10-30.csv"'
    )
    rows = _csv(response)
    assert list(rows[0]) == list(score_service.SCORE_FIELDS)
    assert len(rows) == 5
    json_items = api.get(SCORES, headers=principals.bearer("researcher")).json()["items"]
    for row, item in zip(rows, json_items, strict=True):
        flat = {**{k: v for k, v in item.items() if k != "z"}, **item["z"]}
        assert row == {k: export_service.cell(v) if not isinstance(v, str) else v
                       for k, v in flat.items()}  # fmt: skip
    assert rows[0]["is_morning"] == "true"
    audit = scene.session.execute(
        text("SELECT entity_type, entity_id, details FROM audit_logs WHERE action = 'export.csv'")
    ).one()
    assert (audit.entity_type, audit.entity_id) == ("route", "/api/v1/scores")
    assert audit.details == {"filters": {}, "row_count": 5}
    denied = api.get(SCORES, headers={**principals.bearer("clinician"), **CSV})
    _problem(denied, 403, "FORBIDDEN")
    assert [r["action"] for r in audit_rows] == ["access.denied"]


@pytest.mark.req("API-129", "FEAT-034-FR-07")
def test_csv_row_limit(
    api: TestClient, scene: World, principals: Principals, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(export_service, "MAX_CSV_ROWS", 4)
    _problem(api.get(SCORES, headers={**principals.bearer("admin"), **CSV}), 413,
             "PAYLOAD_TOO_LARGE")  # fmt: skip
    _problem(api.get(BASELINES, headers={**principals.bearer("admin"), **CSV}), 413,
             "PAYLOAD_TOO_LARGE")  # fmt: skip


@pytest.mark.req("API-088", "FR-241", "FEAT-034-FR-05", "FEAT-034-AC-05", "FEAT-034-AC-07")
def test_baselines(api: TestClient, scene: World, principals: Principals) -> None:
    body = api.get(BASELINES, params={"limit": 500}, headers=principals.bearer("researcher")).json()
    assert body["total"] == 60  # three frozen resident-epochs, 20 rows each
    items = body["items"]
    assert [(r["resident_code"], r["epoch_number"]) for r in items[::20]] == [
        ("R01", 1), ("R03", 1), ("R07", 2)
    ]  # fmt: skip
    assert [r["feature_key"] for r in items[:20]] == [*FEATURE_KEYS, "composite"]
    assert items[40]["device_code"] == "D07B"
    assert {k: items[0][k] for k in ("median", "mad", "robust_spread", "floor_applied")} == {
        "median": 1.0, "mad": 0.1, "robust_spread": 0.15, "floor_applied": False
    }  # fmt: skip
    one = api.get(BASELINES, params={"resident_code": "R07", "epoch": 2},
                  headers=principals.bearer("admin")).json()  # fmt: skip
    assert one["total"] == 20
    _problem(api.get(BASELINES, params={"epoch": 1}, headers=principals.bearer("admin")), 422,
             "INVALID_QUERY_PARAMETER")  # fmt: skip
    rows = _csv(api.get(BASELINES, headers={**principals.bearer("researcher"), **CSV}))
    assert list(rows[0]) == list(score_service.BASELINE_FIELDS)
    assert len(rows) == 60
    assert rows[0]["feature_key"] == "loudness_dbfs"
    assert rows[19]["feature_key"] == "composite"
    _problem(api.get(BASELINES, headers=principals.bearer("clinician")), 403, "FORBIDDEN")
    _problem(api.get(BASELINES, headers={**principals.bearer("clinician"), **CSV}), 403,
             "FORBIDDEN")  # fmt: skip
