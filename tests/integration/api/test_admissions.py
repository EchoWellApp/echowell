"""The experimental new-admission arm (TRD 05 API-089, API-090; TRD 02 FR-201..FR-206; TRD 24
OQ-29 interim decision; FEAT-036)."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from backend.models import Facility, FacilityReferenceRange, Resident
from tests.integration.api.conftest import Principals
from tests.integration.world import FEATURES, T0, World

pytestmark = pytest.mark.integration

ADMISSIONS = "/api/v1/admissions"
RANGES = "/api/v1/facility/reference-ranges"
SCORED = list(FEATURES)[:7]


def _new_admission(scene: World, usable: int) -> None:
    """Resident N01 (F, admitted Oct 20) with `usable` usable check-ins on D01."""
    facility_id = scene.session.scalars(select(Facility.id)).one()
    resident = Resident(facility_id=facility_id, resident_code="N01", sex="F",
                        cohort="new_admission", enrolled_on=date(2026, 10, 20),
                        admitted_on=date(2026, 10, 20))  # fmt: skip
    scene.session.add(resident)
    scene.session.flush()
    scene.residents["N01"] = resident.id
    epoch = scene.epoch("N01", "D01")
    for n in range(usable):
        day = date(2026, 10, 20 + n)
        scene.processed("N01", "D01", day, "usable", epoch, ordinal=n + 1,
                        session_id=f"N01-{day:%Y%m%d}-01")  # fmt: skip
    scene.session.commit()


def _ranges(scene: World, **overrides: tuple[float, float]) -> None:
    """A range around each scored feature's fixture value, unless overridden."""
    facility_id = scene.session.scalars(select(Facility.id)).one()
    for key in SCORED:
        low, high = overrides.get(key, (FEATURES[key] - 1, FEATURES[key] + 1))
        scene.session.add(
            FacilityReferenceRange(
                facility_id=facility_id, feature_key=key, sex=None, low=low, high=high,
                method="fixture", n_residents=8, computed_at=T0, pipeline_run_id=scene.run_id,
            )
        )  # fmt: skip
    scene.session.commit()


def _get(api: TestClient, principals: Principals, path: str, role: str = "clinician") -> Any:
    response = api.get(path, headers=principals.bearer(role))
    assert response.status_code == 200, response.text
    assert response.headers["x-echowell-experimental"] == "true"
    return response.json()


def _counts(scene: World) -> list[int]:
    return [
        int(scene.session.execute(text(f"SELECT count(*) FROM {t}")).scalar_one())  # noqa: S608
        for t in ("alerts", "scores", "cusum_state")
    ]


@pytest.mark.req("API-089", "VIS-009", "D-06", "UX-194", "FEAT-036-AC-01", "FEAT-036-AC-06",
                 "FEAT-036-FR-01", "FEAT-036-FR-05")  # fmt: skip
def test_empty_state(api: TestClient, scene: World, principals: Principals) -> None:
    for role in ("admin", "clinician", "researcher"):
        body = _get(api, principals, ADMISSIONS, role)
        assert (body["items"], body["total"]) == ([], 0)
        assert body["meta"]["pipeline_profile"] == "test_v0_1"
        assert _get(api, principals, RANGES, role)["items"] == []


@pytest.mark.req("API-090", "FEAT-036-AC-02")
def test_comparison_only_for_new_admissions(
    api: TestClient, scene: World, principals: Principals
) -> None:
    for code in ("R01", "R99"):
        response = api.get(f"{ADMISSIONS}/{code}/comparison", headers=principals.bearer("admin"))
        assert response.status_code == 404
        assert response.json()["type"] == "urn:echowell:error:RESIDENT_NOT_FOUND"


@pytest.mark.req(
    "FR-201", "FR-202", "FR-206", "UX-184", "UX-185", "UX-186", "FEAT-036-AC-03",
    "FEAT-036-AC-05", "FEAT-036-FR-02", "FEAT-036-FR-03", "FEAT-036-FR-06",
)  # fmt: skip
def test_range_not_available(api: TestClient, scene: World, principals: Principals) -> None:
    before = _counts(scene)
    _new_admission(scene, usable=3)
    body = _get(api, principals, ADMISSIONS)
    assert body["items"] == [
        {"resident_code": "N01", "admitted_on": "2026-10-20", "checkins_so_far": 3,
         "comparison_status": "range_not_available",
         "own_baseline_progress": {"n_usable": 3, "n_required": 16}},
    ]  # fmt: skip
    comparison = _get(api, principals, f"{ADMISSIONS}/N01/comparison")
    assert comparison["comparison_status"] == "range_not_available"
    assert [f["feature_key"] for f in comparison["features"]] == SCORED
    assert comparison["features"][0] == {
        "feature_key": "loudness_dbfs", "resident_value": FEATURES["loudness_dbfs"],
        "low": None, "high": None, "outside_range": None,
    }  # fmt: skip
    _get(api, principals, RANGES)
    assert _counts(scene) == before


@pytest.mark.req("TST-186", "FR-202", "FR-204", "FEAT-036-AC-04", "FEAT-036-FR-04",
                 "FEAT-036-FR-05")  # fmt: skip
def test_comparison_with_ranges(api: TestClient, scene: World, principals: Principals) -> None:
    _new_admission(scene, usable=3)
    _ranges(scene)
    assert _get(api, principals, ADMISSIONS)["items"][0]["comparison_status"] == (
        "not_enough_checkins"
    )
    for n in (23, 24):
        day = date(2026, 10, n)
        epoch = scene.session.scalars(
            text("SELECT id FROM epochs WHERE resident_id = :r").bindparams(
                r=scene.residents["N01"]
            )
        ).one()
        scene.processed("N01", "D01", day, "usable", epoch, ordinal=n - 19,
                        session_id=f"N01-{day:%Y%m%d}-01")  # fmt: skip
    scene.session.commit()
    assert _get(api, principals, ADMISSIONS)["items"][0]["comparison_status"] == "within_range"
    ranges = _get(api, principals, RANGES)
    assert [r["feature_key"] for r in ranges["items"]] == SCORED
    assert ranges["items"][0]["n_residents"] == 8
    scene.session.execute(
        text("UPDATE facility_reference_ranges SET low = -20, high = -10 "
             "WHERE feature_key = 'loudness_dbfs'")
    )  # fmt: skip
    scene.session.commit()
    comparison = _get(api, principals, f"{ADMISSIONS}/N01/comparison")
    assert comparison["comparison_status"] == "outside_range"
    loudness = comparison["features"][0]
    assert (loudness["resident_value"], loudness["low"], loudness["outside_range"]) == (
        -24.0, -20.0, True
    )  # fmt: skip
    assert all(f["outside_range"] is False for f in comparison["features"][1:])
