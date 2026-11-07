"""The evaluation ground-truth loader (TRD 14 TDV-103, §4.9.3; TRD 09 CUS-048; TRD 13 TST-068 (c);
FEAT-057-FR-10, FEAT-057-AC-04, FEAT-057-AC-05).

`database/seeds/load_evaluation_ground_truth.py` runs as a subprocess, as an operator would run it,
against a throwaway migrated database.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from tests.integration.db_support import ROOT, PgUrls, cli_environment

pytestmark = pytest.mark.integration

LOADER = ROOT / "database" / "seeds" / "load_evaluation_ground_truth.py"
DS10 = ROOT / "tests" / "fixtures" / "answer_key" / "evaluation_ground_truth_v0_1.csv"


def _load(urls: PgUrls, csv_path: Path, **env: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed interpreter and script
        [sys.executable, str(LOADER), str(csv_path)],
        env=cli_environment(urls, **env), capture_output=True, text=True, timeout=60,
        check=False, cwd=ROOT,
    )  # fmt: skip


def _rows(urls: PgUrls) -> list[tuple[str, str, date | None]]:
    engine = create_engine(urls.migrator, poolclass=NullPool)
    try:
        with engine.connect() as connection:
            result = connection.execute(text(
                "SELECT resident_code, planted_change, true_onset_date "
                "FROM evaluation_ground_truth ORDER BY resident_code"))  # fmt: skip
            return [tuple(row) for row in result]  # type: ignore[misc]
    finally:
        engine.dispose()


@pytest.mark.req("TDV-103", "TDV-100", "FEAT-057-FR-10", "FEAT-057-AC-04")
def test_loads_ds10_and_replaces_contents(fresh_db: PgUrls) -> None:
    for _ in range(2):  # a second load replaces, never appends
        done = _load(fresh_db, DS10)
        assert done.returncode == 0, done.stderr
        assert "Loaded 10 evaluation ground-truth rows (profile test_v0_1)." in done.stdout
    loaded = _rows(fresh_db)
    assert len(loaded) == 10
    assert loaded[8] == ("R09", "Sudden step", date(2026, 10, 21))
    assert loaded[9] == ("R10", "Slow drift", date(2026, 10, 17))
    assert {row[1:] for row in loaded[:8]} == {("None", None)}


@pytest.mark.req("TDV-103", "TST-068", "CUS-048", "FEAT-057-AC-05")
@pytest.mark.parametrize("env", [{"APP_ENV": "production"}, {"PIPELINE_PROFILE": "production"}],
                         ids=["production-env", "production-profile"])  # fmt: skip
def test_refuses_outside_test_v0_1(fresh_db: PgUrls, env: dict[str, str]) -> None:
    done = _load(fresh_db, DS10, **env)
    assert done.returncode == 2
    assert done.stderr.startswith("Refused:")
    assert _rows(fresh_db) == []


@pytest.mark.req("TDV-103", "FEAT-057-FR-10")
def test_malformed_file_leaves_the_table_unchanged(fresh_db: PgUrls, tmp_path: Path) -> None:
    assert _load(fresh_db, DS10).returncode == 0
    bad = tmp_path / "bad.csv"
    bad.write_text(DS10.read_text(encoding="utf-8").replace(",2026-10-21,", ",,"),
                   encoding="utf-8")  # fmt: skip
    done = _load(fresh_db, bad)
    assert done.returncode == 1
    assert "onset date must be set iff a change is planted" in done.stderr
    assert len(_rows(fresh_db)) == 10
