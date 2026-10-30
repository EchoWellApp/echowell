"""Resident overview, detail, check-in log and voice measurements (TRD 05 API-070..API-078;
TRD 19 E-08..E-11; TRD 23 §4.4; FEAT-027, FEAT-028). Values come from the `scene` fixture."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.services.resident_service import natural_key
from tests.integration.api.conftest import Principals
from tests.integration.world import World

pytestmark = pytest.mark.integration

RESIDENTS = "/api/v1/residents"
META_KEYS = {"facility_name", "facility_tz", "data_source_label", "as_of", "baseline_n",
             "cusum_h", "pipeline_profile"}  # fmt: skip


def _get(api: TestClient, principals: Principals, path: str, **params: Any) -> Any:
    response = api.get(path, params=params, headers=principals.bearer("clinician"))
    assert response.status_code == 200, response.text
    return response.json()


def _problem(response: Any, status: int, code: str) -> None:
    assert response.status_code == status, response.text
    assert response.json()["type"] == f"urn:echowell:error:{code}"


def _rows(body: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["resident_code"]: row for row in body["items"]}


@pytest.mark.req("FR-131", "FR-132", "FR-302", "D-109", "D-114", "TST-033", "FEAT-027-AC-02",
                 "FEAT-027-FR-03", "FEAT-027-FR-04", "FEAT-027-FR-05", "FEAT-027-FR-06",
                 "FEAT-027-FR-07", "FEAT-027-FR-10", "FEAT-027-FR-12", "FEAT-027-FR-13",
                 "FEAT-027-AC-09")  # fmt: skip
def test_overview(api: TestClient, scene: World, principals: Principals) -> None:
    body = _get(api, principals, RESIDENTS)
    assert set(body["meta"]) == META_KEYS
    assert body["meta"]["as_of"] == "2026-10-30T20:00:00Z"
    assert body["window"] == {"from": "2026-10-01", "to": "2026-10-30", "days": 30}
    order = [row["resident_code"] for row in body["items"]]
    assert order == ["R01", "R03", "R02", "R04", "R05", "R06", "R08", "R09", "R07"]
    assert body["summary"] == {"changed": 1, "needs_attention": 1, "learning": 6, "usual": 1}
    assert body["total"] == 9
    rows = _rows(body)
    r01 = rows["R01"]
    assert (r01["status"], r01["alarm_since"], r01["alarm_reviewed"]) == (
        "alarm_on", "2026-10-20", False
    )  # fmt: skip
    assert r01["open_alert_id"] is not None
    assert r01["baseline_progress"] == {"n_usable": 16, "n_required": 16}
    assert r01["last_30_days"] == {"used": 20, "set_aside": 1, "quarantined": 0, "missed": 1}
    assert r01["last_checkin_at"] == "2026-10-21T13:00:00Z"  # the Oct 22 duplicate never counts
    assert r01["last_checkin_local"] == "2026-10-21T08:00:00-05:00"
    r03 = rows["R03"]
    assert (r03["status"], r03["needs_attention"], r03["attention_reasons"]) == (
        "no_alarm", True, ["high_set_aside"]
    )  # fmt: skip
    assert (r03["device_code"], r03["device_shared"]) == ("D02", True)
    r02 = rows["R02"]
    assert (r02["status"], r02["needs_attention"], r02["attention_reasons"]) == (
        "baseline_forming", False, []
    )  # fmt: skip
    assert r02["baseline_progress"] == {"n_usable": 13, "n_required": 16}
    assert r02["last_30_days"]["missed"] == 1
    r07 = rows["R07"]
    assert (r07["status"], r07["current_epoch"], r07["restart_cause"]) == ("no_alarm", 2, "device")
    assert (r07["device_code"], r07["previous_device_code"]) == ("D07B", "D07")
    assert r07["baseline_restarted_on"] == "2026-10-13"
    assert r07["alarm_reviewed"] is None
    r05 = rows["R05"]
    assert (r05["current_epoch"], r05["restart_cause"]) == (2, "firmware")
    r04 = rows["R04"]
    assert (r04["current_epoch"], r04["baseline_restarted_on"], r04["restart_cause"]) == (
        None, None, None
    )  # fmt: skip
    assert r04["last_checkin_at"] is None


@pytest.mark.req("API-072", "AGT-052", "FEAT-027-AC-03", "FEAT-027-FR-11", "FEAT-027-AC-08")
def test_other_sort_orders(api: TestClient, scene: World, principals: Principals) -> None:
    by_code = _get(api, principals, RESIDENTS, sort="resident_id")
    assert [r["resident_code"] for r in by_code["items"]] == [
        "R01", "R02", "R03", "R04", "R05", "R06", "R07", "R08", "R09"
    ]  # fmt: skip
    by_checkin = _get(api, principals, RESIDENTS, sort="last_checkin")
    assert [r["resident_code"] for r in by_checkin["items"]] == [
        "R07", "R01", "R02", "R05", "R03", "R04", "R06", "R08", "R09"
    ]  # fmt: skip
    assert sorted(["R10", "R2", "R1"], key=natural_key) == ["R1", "R2", "R10"]
    assert sorted(["D08", "D07B", "D07"], key=natural_key) == ["D07", "D07B", "D08"]


@pytest.mark.req("TST-055", "FR-130", "FEAT-027-AC-04", "FEAT-027-AC-05", "FEAT-027-FR-02",
                 "API-073")  # fmt: skip
def test_filters_and_paging(api: TestClient, scene: World, principals: Principals) -> None:
    assert "R10" not in _rows(_get(api, principals, RESIDENTS))
    withdrawn = _rows(_get(api, principals, RESIDENTS, include_withdrawn="true"))["R10"]
    assert withdrawn["resident_status"] == "withdrawn"
    page = _get(api, principals, RESIDENTS, limit=1, offset=1)
    assert [r["resident_code"] for r in page["items"]] == ["R03"]
    assert page["total"] == 9
    assert sum(page["summary"].values()) == 9
    assert _get(api, principals, RESIDENTS, cohort="new_admission")["total"] == 0


@pytest.mark.req("API-070", "API-016", "FEAT-027-AC-01", "FEAT-027-FR-01")
@pytest.mark.parametrize(
    "params",
    [{"sort": "foo"}, {"limit": 0}, {"limit": 501}, {"offset": -1}, {"cohort": "x"},
     {"include_withdrawn": "maybe"}],
)  # fmt: skip
def test_invalid_query_parameters(
    api: TestClient, roster: Session, principals: Principals, params: dict[str, Any]
) -> None:
    response = api.get(RESIDENTS, params=params, headers=principals.bearer("admin"))
    _problem(response, 422, "INVALID_QUERY_PARAMETER")


@pytest.mark.req("ANL-019", "FEAT-027-FR-14")
def test_before_any_run(api: TestClient, roster: Session, principals: Principals) -> None:
    body = _get(api, principals, RESIDENTS)
    assert body["meta"]["as_of"] is None
    assert {r["status"] for r in body["items"]} == {"baseline_forming"}
    assert body["summary"] == {"changed": 0, "needs_attention": 0, "learning": 10, "usual": 0}
    assert {tuple(r["last_30_days"].values()) for r in body["items"]} == {(0, 0, 0, 0)}


@pytest.mark.req("API-075", "API-076", "D-41", "D-82", "FEAT-028-FR-01", "FEAT-028-FR-02",
                 "FEAT-028-FR-03", "FEAT-028-FR-04", "FEAT-028-FR-05", "FEAT-028-FR-06",
                 "FEAT-028-FR-07", "FEAT-028-AC-09")  # fmt: skip
def test_detail(api: TestClient, scene: World, principals: Principals) -> None:
    r01 = _get(api, principals, f"{RESIDENTS}/R01")
    assert set(r01["meta"]) == META_KEYS
    assert (r01["status"], r01["alarm_since"], r01["current_tally"]) == (
        "alarm_on", "2026-10-20", 7.5
    )  # fmt: skip
    assert r01["baseline"] == {
        "state": "frozen", "n_usable": 16, "n_required": 16,
        "first_session_id": "R01-20261001-01", "frozen_after_session_id": "R01-20261016-01",
        "first_local_date": "2026-10-01", "frozen_after_local_date": "2026-10-16",
    }  # fmt: skip
    assert r01["watching_since"] == "2026-10-17"
    assert r01["explanation"] == {
        "compared_with": "own_baseline", "alarm_crossed_on": "2026-10-20",
        "still_above_line": True, "baseline_restarted_on": None, "baseline_n_usable": 16,
        "baseline_n_required": 16,
    }  # fmt: skip
    assert r01["window"] == {"from": "2026-10-01", "to": "2026-10-30", "days": 30}
    assert r01["epoch_count"] == 1
    assert (r01["current_epoch"]["from_value"], r01["current_epoch"]["to_value"]) == (None, None)
    assert r01["device"] == {"device_code": "D01", "shared": False, "shared_with": [],
                             "previous_device_code": None}  # fmt: skip
    r03 = _get(api, principals, f"{RESIDENTS}/R03")
    assert r03["device"]["shared_with"] == ["R02"]
    r07 = _get(api, principals, f"{RESIDENTS}/R07")
    assert (r07["restart_cause"], r07["epoch_count"]) == ("device", 2)
    epoch = r07["current_epoch"]
    assert (epoch["epoch_number"], epoch["device_code"], epoch["started_on"]) == (
        2, "D07B", "2026-10-13"
    )  # fmt: skip
    assert (epoch["from_value"], epoch["to_value"]) == ("D07", "D07B")
    assert r07["explanation"]["baseline_restarted_on"] == "2026-10-13"
    r02 = _get(api, principals, f"{RESIDENTS}/R02")
    assert r02["baseline"]["state"] == "forming"
    assert r02["baseline"]["first_session_id"] is None
    assert r02["watching_since"] is None
    assert r02["explanation"]["still_above_line"] is False
    r10 = _get(api, principals, f"{RESIDENTS}/R10")
    assert (r10["resident_status"], r10["withdrawn_on"]) == ("withdrawn", "2026-10-25")


@pytest.mark.req("API-075", "FR-173", "TST-064", "FEAT-028-AC-01")
@pytest.mark.parametrize("code", ["R11", "r01", "R-01"])
@pytest.mark.parametrize("suffix", ["", "/checkins", "/features"])
def test_unknown_resident_is_404(
    api: TestClient, roster: Session, principals: Principals, code: str, suffix: str
) -> None:
    response = api.get(f"{RESIDENTS}/{code}{suffix}", headers=principals.bearer("researcher"))
    _problem(response, 404, "RESIDENT_NOT_FOUND")


@pytest.mark.req("API-077", "UX-141", "D-82", "D-113", "D-114", "FR-182", "D-67",
                 "FEAT-028-FR-08", "FEAT-028-FR-09", "FEAT-028-FR-10", "FEAT-028-FR-11",
                 "FEAT-028-AC-05")  # fmt: skip
def test_checkin_log(api: TestClient, scene: World, principals: Principals) -> None:
    r01 = _get(api, principals, f"{RESIDENTS}/R01/checkins")
    assert set(r01["meta"]) == META_KEYS
    summary = [(e["local_date"], e["event_type"], e["session_id"], e["detail"])
               for e in r01["items"]]  # fmt: skip
    assert summary == [
        ("2026-10-23", "missed", None, "no record received"),
        ("2026-10-21", "set_aside", "R01-20261021-01", "noise above limit"),
        ("2026-10-20", "alarm_on", "R01-20261020-01", "tally crossed 5.0"),
        ("2026-10-17", "watching_started", "R01-20261017-01", None),
        ("2026-10-16", "baseline_complete", "R01-20261016-01", "16 of 16"),
        ("2026-10-01", "checkins_started", "R01-20261001-01", None),
    ]
    alarm = r01["items"][2]
    assert (alarm["cusum_tally"], alarm["epoch_number"]) == (5.4, 1)
    first = r01["items"][-1]
    assert (first["device_code"], first["epoch_number"]) == ("D01", 1)
    restart_fields = ("restart_cause", "previous_device_code", "from_value", "to_value")
    for event in r01["items"]:
        assert all(event[k] is None for k in restart_fields)
        assert set(event) == {"local_date", "event_type", "epoch_number", "session_id", "detail",
                              "cusum_tally", *restart_fields, "device_code"}  # fmt: skip
    r07 = _get(api, principals, f"{RESIDENTS}/R07/checkins")["items"]
    restart = next(e for e in r07 if e["event_type"] == "baseline_restarted")
    assert {k: restart[k] for k in ("local_date", "epoch_number", "detail", *restart_fields)} == {
        "local_date": "2026-10-13", "epoch_number": 2, "detail": "new epoch 2 on device D07B",
        "restart_cause": "device", "previous_device_code": "D07", "from_value": "D07",
        "to_value": "D07B",
    }  # fmt: skip
    assert restart["device_code"] is None
    assert (r07[-1]["event_type"], r07[-1]["device_code"]) == ("checkins_started", "D07")
    r02 = _get(api, principals, f"{RESIDENTS}/R02/checkins")["items"]
    assert r02[0] == {
        "local_date": "2026-10-14", "event_type": "device_silent", "epoch_number": None,
        "session_id": None, "detail": "all residents on shared device D02 have no record",
        "cusum_tally": None, "restart_cause": None, "previous_device_code": None,
        "from_value": None, "to_value": None, "device_code": None,
    }  # fmt: skip


@pytest.mark.req("API-077", "UX-141", "FEAT-028-AC-10")
def test_same_date_events_follow_ux_141(
    api: TestClient, scene: World, principals: Principals
) -> None:
    events = _get(api, principals, f"{RESIDENTS}/R05/checkins")["items"]
    same_day = [e["event_type"] for e in events if e["local_date"] == "2026-10-05"]
    # R05's first record is also on Oct 5, so checkins_started closes the day (UX-141)
    assert same_day == ["watching_started", "baseline_restarted", "set_aside", "checkins_started"]
    restart = next(e for e in events if e["event_type"] == "baseline_restarted")
    assert (restart["restart_cause"], restart["from_value"], restart["to_value"]) == (
        "firmware", "fw-1.0.0", "fw-1.1.0"
    )  # fmt: skip
    assert restart["detail"] == "new epoch 2 on device D05"


@pytest.mark.req("API-077", "API-093", "FEAT-028-AC-06")
def test_checkin_log_filters(api: TestClient, scene: World, principals: Principals) -> None:
    path = f"{RESIDENTS}/R01/checkins"
    window = _get(api, principals, path, **{"from": "2026-10-16", "to": "2026-10-20"})
    assert [e["event_type"] for e in window["items"]] == [
        "alarm_on", "watching_started", "baseline_complete"
    ]  # fmt: skip
    page = _get(api, principals, path, limit=2, offset=1)
    assert ([e["event_type"] for e in page["items"]], page["total"]) == (
        ["set_aside", "alarm_on"], 6
    )  # fmt: skip
    admin = principals.bearer("admin")
    for params in ({"from": "2026-10-20", "to": "2026-10-10"},
                   {"from": "2025-10-01", "to": "2026-10-02"},
                   {"from": "not-a-date"}):  # fmt: skip
        _problem(api.get(path, params=params, headers=admin), 422, "INVALID_QUERY_PARAMETER")
    assert api.get(path, params={"from": "2025-10-02", "to": "2026-10-02"},
                   headers=admin).status_code == 200  # 366 days  # fmt: skip


@pytest.mark.req("API-078", "BSC-037", "BSC-039", "TRD 11 §4.5.4", "FEAT-028-FR-12",
                 "FEAT-028-FR-13", "FEAT-028-FR-14", "FEAT-028-AC-07")  # fmt: skip
def test_features(api: TestClient, scene: World, principals: Principals) -> None:
    body = _get(api, principals, f"{RESIDENTS}/R01/features")
    assert set(body["meta"]) == META_KEYS
    assert body["epoch_number"] == 1
    series = body["scored_features"]
    assert [(s["feature_key"], s["label"], s["unit"], s["composite_sign"]) for s in series] == [
        ("loudness_dbfs", "Quieter (loudness)", "dBFS", -1),
        ("total_phrase_duration_s", "Slower to say the phrase (phrase duration)", "s", 1),
        ("speech_rate_syl_per_s", "Fewer syllables per second (speech rate)", "syllables/s", -1),
        ("articulation_rate_syl_per_s", "Slower while talking (articulation rate)", "syllables/s",
         -1),
        ("number_of_pauses", "More pauses (number of pauses)", "count", 1),
        ("pause_fraction", "More time in pauses (pause fraction)", "proportion", 1),
        ("voiced_fraction", "Less voiced sound (voiced fraction)", "proportion", -1),
    ]  # fmt: skip
    loudness = series[0]
    assert (loudness["baseline_median"], loudness["baseline_robust_spread"]) == (1.0, 0.15)
    points = loudness["points"]
    assert len(points) == 20  # usable sessions only: no set-aside, no duplicate
    assert points[0] == {
        "session_id": "R01-20261001-01", "local_date": "2026-10-01", "is_morning": True,
        "raw_value": -24.0, "adjusted_value": -24.0, "z": None, "in_baseline": True,
    }  # fmt: skip
    assert (points[-1]["session_id"], points[-1]["z"], points[-1]["in_baseline"]) == (
        "R01-20261020-01", 0.5, False
    )  # fmt: skip
    assert body["stored_feature_keys"][0] == "mean_f0_hz"
    assert body["stored_feature_keys"][-1] == "mfcc4"
    assert len(body["stored_feature_keys"]) == 12
    narrow = _get(api, principals, f"{RESIDENTS}/R01/features",
                  **{"from": "2026-10-19", "to": "2026-10-20"})  # fmt: skip
    assert [p["session_id"] for p in narrow["scored_features"][0]["points"]] == [
        "R01-20261019-01", "R01-20261020-01"
    ]  # fmt: skip
    forming = _get(api, principals, f"{RESIDENTS}/R02/features")["scored_features"][0]
    assert (forming["baseline_median"], forming["baseline_robust_spread"]) == (None, None)
    assert {p["z"] for p in forming["points"]} == {None}
    empty = _get(api, principals, f"{RESIDENTS}/R04/features")
    assert empty["epoch_number"] is None
    assert all(s["points"] == [] for s in empty["scored_features"])
