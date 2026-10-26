"""Configuration seed of migration 0002 (TRD 20 §4.11; PGS-024, PGS-025; FEAT-009)."""

from __future__ import annotations

import pytest
from sqlalchemy import Connection, text
from sqlalchemy.orm import Session

from backend.repositories.config_repository import CONFIG_KEYS, ConfigRepository

pytestmark = pytest.mark.integration


@pytest.mark.req("AC-PGS-10", "PGS-024", "PGS-025", "DB-055", "FEAT-009-AC-01")
def test_ac_pgs_10_config_rows_per_profile(app_conn: Connection) -> None:
    counts = dict(
        app_conn.execute(
            text("SELECT profile, count(*) FROM config_parameters GROUP BY profile")
        ).all()
    )
    assert counts == {"production": 23, "test_v0_1": 23}
    baseline_n = dict(
        app_conn.execute(
            text("SELECT profile, value FROM config_parameters WHERE key = 'baseline_n'")
        ).all()
    )
    assert baseline_n == {"production": 30, "test_v0_1": 16}
    offsets = app_conn.execute(
        text("SELECT value FROM config_parameters WHERE key = 'morning_offsets'")
    ).scalars()
    for value in offsets:
        assert len(value) == 19
        assert value["loudness_dbfs"] == -1.5


@pytest.mark.req("PGS-024", "FEAT-009-FR-06")
def test_repository_reads_the_23_keys(app_session: Session) -> None:
    values = ConfigRepository(app_session).values_for_profile("test_v0_1")
    assert set(values) == set(CONFIG_KEYS)
    assert len(CONFIG_KEYS) == 23
