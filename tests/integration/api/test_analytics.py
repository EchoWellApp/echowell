"""The study-team summary `GET /api/v1/analytics` (TRD 05 API-087, API-136; TRD 09 CUS-047,
CUS-049; TRD 23 §4.7; FEAT-035). Data come from the `scene` fixture (as-of 2026-10-30)."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Connection, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from backend.api import analytics as analytics_router
from backend.core import db
from backend.models import Epoch
from backend.services import analytics_summary
from backend.services.resident_service import read_context
from tests.conftest import make_settings
from tests.integration.api.conftest import Principals
from tests.integration.db_support import PgUrls
from tests.integration.world import World

pytestmark = pytest.mark.integration

ANALYTICS = "/api/v1/analytics"
TRUTH = (
    ("R01", "Sudden step", date(2026, 10, 18)),  # alarm Oct 20: detected, 2 days
    ("R02", "Slow drift", date(2026, 10, 10)),  # no alarm: missed
    ("R03", "None", None),  # alarm Oct 3 (added below): false alarm
    ("R04", "None", None),  # no alarm: correct
    ("R05", "Sudden step", date(2026, 10, 25)),  # no alarm: missed
)


@pytest.fixture
def ground_truth(migrator_conn: Connection) -> Iterator[Session]:
    """Answer-key rows on the table owner's rolled-back connection, standing in for the
    read-only engine (its rows would need a committed transaction)."""
    for code, planted, onset in TRUTH:
        migrator_conn.execute(
            text("INSERT INTO evaluation_ground_truth (resident_code, planted_change, "
                 "true_onset_date, source_file) VALUES (:c, :p, :o, 'fixture')"),
            {"c": code, "p": planted, "o": onset},
        )  # fmt: skip
    with Session(bind=migrator_conn, join_transaction_mode="create_savepoint") as session:
        yield session


def _app(api: TestClient) -> FastAPI:
    app: FastAPI = api.app  # type: ignore[assignment]
    return app


@pytest.mark.req("FR-240", "FR-243", "FR-312", "API-087", "TRD 23 §4.7.3", "TRD 23 §4.7.4",
                 "FEAT-035-AC-01", "FEAT-035-AC-06", "FEAT-035-FR-01", "FEAT-035-FR-02",
                 "FEAT-035-FR-03", "FEAT-035-FR-04", "FEAT-035-FR-05", "FEAT-035-FR-06",
                 "FEAT-035-FR-07", "FEAT-035-FR-10", "CUS-047", "D-81")  # fmt: skip
def test_summary(
    api: TestClient, scene: World, principals: Principals, ground_truth: Session
) -> None:
    epoch = scene.session.scalars(
        select(Epoch.id).where(Epoch.resident_id == scene.residents["R03"])
    ).one()
    scene.alert("R03", epoch, "R03-20261003-01", date(2026, 10, 3), status="closed")
    scene.session.commit()
    _app(api).dependency_overrides[analytics_router.get_ground_truth] = lambda: lambda: (
        ground_truth
    )
    assert api.get(ANALYTICS, headers=principals.bearer("clinician")).status_code == 403
    assert api.get(ANALYTICS, headers=principals.bearer("admin")).status_code == 200
    body = api.get(ANALYTICS, headers=principals.bearer("researcher")).json()
    assert body["period"] == {"from": "2026-10-01", "to": "2026-10-30", "days": 30}
    counts = {row["resident_code"]: row for row in body["status_counts"]}
    assert len(counts) == 10
    keys = ("usable", "set_aside", "duplicate", "missing_resident")
    assert [counts["R01"][k] for k in keys] == [20, 1, 1, 1]
    assert (counts["R02"]["usable"], counts["R02"]["missing_device_gap"]) == (13, 1)
    assert body["status_totals"] == {
        "usable": 40, "set_aside": 2, "quarantined": 0, "duplicate": 1, "missing_resident": 1,
        "missing_device_gap": 2,
    }  # fmt: skip
    outcomes = [(o["resident_code"], o["epoch_number"]) for o in body["resident_outcomes"]]
    assert outcomes == [("R01", 1), ("R02", 1), ("R03", 1), ("R05", 2), ("R07", 1), ("R07", 2)]
    r01, r02 = body["resident_outcomes"][0], body["resident_outcomes"][1]
    assert r01 == {
        "resident_code": "R01", "epoch_number": 1, "device_code": "D01", "usable_in_epoch": 20,
        "baseline_formed": True, "baseline_frozen_after": "R01-20261016-01",
        "scored_sessions": 4, "first_alarm_session": "R01-20261020-01", "note": None,
    }  # fmt: skip
    assert (r02["baseline_formed"], r02["scored_sessions"], r02["note"]) == (
        False, None, "Too few usable sessions: baseline pending, nothing scored"
    )  # fmt: skip
    assert body["pipeline_run"]["id"] == str(scene.run_id)
    assert body["pipeline_run"]["status"] == "succeeded"
    assert body["review_outcomes"] is None
    timing = {row["resident_code"]: row for row in body["alarm_timing"]}
    assert [row["resident_code"] for row in body["alarm_timing"]] == ["R01", "R02", "R03", "R04",
                                                                       "R05"]  # fmt: skip
    assert timing["R01"] == {"resident_code": "R01", "planted_change": "Sudden step",
                             "change_began": "2026-10-18", "alarm_rang": "2026-10-20",
                             "delay_days": 2, "result": "detected"}  # fmt: skip
    assert (timing["R02"]["result"], timing["R02"]["delay_days"]) == ("missed", None)
    assert (timing["R03"]["result"], timing["R03"]["alarm_rang"]) == ("false_alarm", "2026-10-03")
    assert timing["R04"]["result"] == "correct_no_alarm"
    assert set(body) >= {"kpis", "daily_series", "funnel", "by_resident"}  # FEAT-051 seam


@pytest.mark.req("TDV-104", "CUS-049", "API-136", "FEAT-035-AC-04", "FEAT-035-FR-09",
                 "FEAT-035-FR-11")  # fmt: skip
def test_production_profile(
    scene: World, principals: Principals, monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_engine(*_: Any, **__: Any) -> None:
        raise AssertionError("the read-only engine must not be created in production")

    monkeypatch.setattr(db, "create_read_only_engine", no_engine)
    settings = make_settings(pipeline_profile="production")
    assert analytics_summary.ground_truth_sessions(settings) is None
    session = scene.session
    body = analytics_summary.build(session, read_context(session, settings), settings, None)
    assert body["alarm_timing"] is None
    assert body["review_outcomes"] == {
        "alarms_raised": 1, "reviewed": 0,
        "by_outcome": {"no_concern": 0, "known_cause": 0, "referred": 0, "data_problem": 0},
    }  # fmt: skip


@pytest.mark.req("API-136", "SEC-116", "ARC-015", "D-38", "FEAT-035-FR-08")
def test_read_only_engine(pg_urls: PgUrls, migrated: Any) -> None:
    settings = make_settings(database_url=pg_urls.app, database_readonly_url=pg_urls.readonly)
    sessions = analytics_summary.ground_truth_sessions(settings)
    assert sessions is not None
    with sessions() as session:
        engine = session.get_bind()
        assert engine.pool.size() == 1  # type: ignore[union-attr]
        assert (
            session.execute(text("SELECT current_user")).scalar_one() == "echowell_readonly_login"
        )
        session.execute(text("SELECT count(*) FROM evaluation_ground_truth")).scalar_one()
        with pytest.raises(DBAPIError, match="read-only transaction"):
            session.execute(text("CREATE TEMP TABLE x (i int)"))
