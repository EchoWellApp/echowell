"""The experimental new-admission arm (TRD 05 API-089, API-090; TRD 02 FR-201..FR-206; TRD 24
OQ-29 interim decision; FEAT-036; the cohort change of TRD 13 TST-185, TRD 06 DB-025)."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from backend.api.deps import get_clock, get_session_factory
from backend.cli import load_roster
from backend.models import (
    Facility,
    FacilityReferenceRange,
    PipelineRunStatus,
    PipelineTrigger,
    Resident,
)
from backend.services import pipeline_persistence
from backend.services.pipeline_runner import PipelineRunner
from tests.conftest import make_settings
from tests.integration.api.conftest import Principals
from tests.integration.api.test_sessions import src05_record
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


AS_OF = datetime(2026, 10, 30, 20, 0, tzinfo=UTC)  # 2026-10-30 15:00 America/Chicago
N01_ROSTER = {
    "facilities.csv": "name,timezone\nDemo Facility,America/Chicago\n",
    "residents.csv": "resident_code,sex,cohort,enrolled_on,admitted_on\n"
                     "N01,F,new_admission,2026-10-15,2026-10-15\n",
    "devices.csv": "device_code,room_label,active,firmware_version_last\nDN01,,true,fw-1.0.0\n",
    "device_assignments.csv": "resident_code,device_code,valid_from,valid_to\n"
                              "N01,DN01,2026-10-15,\n",
}  # fmt: skip


def _n01_record(n: int) -> dict[str, Any]:
    """N01's n-th check-in (1..16, Oct 15..30): the features and time of day of SRC-05 R01's
    n-th usable record (R01 is the clean control), on N01's own device DN01."""
    source = src05_record(f"R01-202610{n:02d}-01")
    day = 14 + n
    clock = source["timestamp_utc"].split(" ")[1]  # 19:xx UTC = 14:xx CDT, before the as-of
    return {**source, "session_id": f"N01-202610{day:02d}-01", "resident_id": "N01",
            "device_id": "DN01", "timestamp_utc": f"2026-10-{day:02d} {clock}"}  # fmt: skip


def _codes(api: TestClient, principals: Principals, path: str) -> list[str]:
    response = api.get(path, headers=principals.bearer("clinician"))
    assert response.status_code == 200, response.text
    return [item["resident_code"] for item in response.json()["items"]]


COHORT = text("SELECT cohort::text FROM residents WHERE resident_code = 'N01'")
COHORT_AUDIT = text("SELECT actor_type::text, entity_id, details, request_id FROM audit_logs "
                    "WHERE action = 'resident.cohort_changed'")  # fmt: skip
N01_USABLE = text(
    "SELECT count(*) FROM processed_sessions p JOIN residents r "
    "ON r.id = p.resident_id WHERE r.resident_code = 'N01' AND p.status = 'usable'"
)
N01_BASELINES = text("SELECT DISTINCT b.pipeline_run_id FROM baselines b JOIN residents r "
                     "ON r.id = b.resident_id WHERE r.resident_code = 'N01'")  # fmt: skip


def _n01_with_15_usable(
    api: TestClient, session: Session, principals: Principals, directory: Path
) -> None:
    """Roster N01 on DN01, the application clock at the as-of, then 15 usable check-ins through
    `POST /api/v1/sessions` (each runs the synchronous per-resident pipeline)."""
    for name, body in N01_ROSTER.items():
        (directory / name).write_text(body, encoding="utf-8")
    load_roster(session, directory)
    session.commit()
    app: FastAPI = api.app  # type: ignore[assignment]
    app.dependency_overrides[get_clock] = lambda: lambda: AS_OF
    for n in range(1, 16):
        response = api.post("/api/v1/sessions", json=_n01_record(n),
                            headers=principals.api_key("ingest"))  # fmt: skip
        assert response.status_code == 201, response.text
    assert session.execute(N01_USABLE).scalar_one() == 15
    assert session.execute(COHORT).scalar_one() == "new_admission"
    assert session.execute(COHORT_AUDIT).all() == []
    assert session.execute(N01_BASELINES).all() == []


@pytest.mark.req("TST-185", "BR-14", "FR-205", "DB-025", "FEAT-036-FR-01")
def test_new_admission_moves_to_the_resident_list_when_its_baseline_forms(
    api: TestClient, roster: Session, principals: Principals, tmp_path: Path
) -> None:
    """TRD 13 TST-185: new admission N01 (own device, test_v0_1) with 15 usable check-ins is on
    `GET /api/v1/admissions` and not on `GET /api/v1/residents`; its 16th usable check-in forms
    the baseline, and that check-in's pipeline run sets `residents.cohort` to `longitudinal` with
    one `resident.cohort_changed` audit row (TRD 06 DB-025), so N01 leaves `/admissions` and
    appears on `/residents` as "Usual" (TRD 02 FR-205)."""
    _n01_with_15_usable(api, roster, principals, tmp_path)
    admissions = api.get("/api/v1/admissions", headers=principals.bearer("clinician")).json()
    assert [(i["resident_code"], i["own_baseline_progress"]) for i in admissions["items"]] == [
        ("N01", {"n_usable": 15, "n_required": 16})
    ]
    assert "N01" not in _codes(api, principals, "/api/v1/residents")

    response = api.post("/api/v1/sessions", json=_n01_record(16),
                        headers=principals.api_key("ingest"))  # fmt: skip
    assert response.status_code == 201, response.text
    run_id = response.json()["pipeline_run_id"]
    run = roster.execute(text("SELECT status::text, scope FROM pipeline_runs WHERE id = :i"),
                         {"i": run_id}).one()  # fmt: skip
    assert (run.status, run.scope) == ("succeeded", {"type": "residents",
                                                     "resident_codes": ["N01"]})  # fmt: skip
    assert roster.execute(N01_USABLE).scalar_one() == 16
    assert roster.execute(COHORT).scalar_one() == "longitudinal"
    (row,) = roster.execute(COHORT_AUDIT).all()
    assert (row.actor_type, row.entity_id) == ("system", "N01")
    assert row.details == {"from": "new_admission", "to": "longitudinal", "epoch_number": 1}
    assert row.request_id == response.headers["x-request-id"]  # written by this check-in's run
    assert roster.execute(N01_BASELINES).scalars().all() == [uuid.UUID(run_id)]
    assert _codes(api, principals, "/api/v1/admissions") == []
    residents = api.get("/api/v1/residents", headers=principals.bearer("clinician")).json()
    (n01,) = (i for i in residents["items"] if i["resident_code"] == "N01")
    # status no_alarm without attention is the "● Usual" pill (D-109 display status)
    assert (n01["cohort"], n01["status"], n01["needs_attention"]) == (
        "longitudinal", "no_alarm", False
    )  # fmt: skip
    assert n01["baseline_progress"] == {"n_usable": 16, "n_required": 16}
    assert residents["summary"]["usual"] >= 1


@pytest.mark.req("TST-185", "DB-025", "DB-013")
def test_cohort_change_shares_the_pipeline_transaction(
    api: TestClient, roster: Session, principals: Principals, tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:  # fmt: skip
    """TRD 13 TST-185, TRD 06 DB-025: the cohort change and its audit row are written in the
    same per-resident pipeline transaction as the derived rows. A failure injected right after
    the change rolls back the cohort, the audit row and the new baseline together; the next run
    writes all of them."""
    _n01_with_15_usable(api, roster, principals, tmp_path)
    original = pipeline_persistence._update_cohort

    def change_then_fail(session: Session, resident: Any, code: str, result: Any) -> None:
        original(session, resident, code, result)
        raise RuntimeError("injected failure after the cohort change")

    monkeypatch.setattr(pipeline_persistence, "_update_cohort", change_then_fail)
    response = api.post("/api/v1/sessions", json=_n01_record(16),
                        headers=principals.api_key("ingest"))  # fmt: skip
    assert response.status_code == 201, response.text
    failed = roster.execute(text("SELECT status::text FROM pipeline_runs WHERE id = :i"),
                            {"i": response.json()["pipeline_run_id"]}).scalar_one()  # fmt: skip
    assert failed == "failed"
    assert roster.execute(COHORT).scalar_one() == "new_admission"
    assert roster.execute(COHORT_AUDIT).all() == []
    assert roster.execute(N01_BASELINES).all() == []
    assert roster.execute(N01_USABLE).scalar_one() == 15  # the run's derived rows rolled back

    monkeypatch.setattr(pipeline_persistence, "_update_cohort", original)
    app: FastAPI = api.app  # type: ignore[assignment]
    runner = PipelineRunner(app.dependency_overrides[get_session_factory](), make_settings())
    handle, status = runner.run(["N01"], PipelineTrigger.TEST, as_of=AS_OF)
    assert status == PipelineRunStatus.SUCCEEDED
    assert roster.execute(COHORT).scalar_one() == "longitudinal"
    assert len(roster.execute(COHORT_AUDIT).all()) == 1
    assert roster.execute(N01_BASELINES).scalars().all() == [handle.id]
