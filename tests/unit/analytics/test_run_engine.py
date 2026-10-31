"""`scripts/run_engine.py` on SRC-05 and the test_v0_1 seed files (TRD 07 ANL-007;
FEAT-052-FR-16)."""

from __future__ import annotations

import importlib.util
import json
import time
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[3]
pytestmark = pytest.mark.unit

SEED = ROOT / "database" / "seeds" / "test_v0_1"


def _script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("run_engine", ROOT / "scripts" / "run_engine.py")
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.req("ANL-007", "FEAT-052-FR-16", "TST-120")
def test_run_engine_on_the_seed_files(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    started = time.perf_counter()
    code = _script().main([
        "--input", str(SEED / "EchoWell_pipeline_test_input_v0_1.csv"), "--profile", "test_v0_1",
        "--as-of", "2026-10-30 15:00", "--assignments", str(SEED / "device_assignments.csv"),
        "--residents", str(SEED / "residents.csv"), "--out", str(tmp_path),
    ])  # fmt: skip
    assert code == 0
    assert time.perf_counter() - started < 5
    assert "wrote 14 files" in capsys.readouterr().out
    counts = json.loads((tmp_path / "counts.json").read_text(encoding="utf-8"))
    assert (counts["arrivals"], counts["usable"], counts["scored"]) == (283, 267, 98)
    assert len(json.loads((tmp_path / "baselines.json").read_text(encoding="utf-8"))) == 180
    alerts = json.loads((tmp_path / "alerts.json").read_text(encoding="utf-8"))
    assert [a["resident_code"] for a in alerts] == ["R09", "R10"]
    assert len(json.loads((tmp_path / "data_alerts.json").read_text(encoding="utf-8"))) == 4


@pytest.mark.req("ANL-007")
def test_json_and_csv_rows_read_alike(tmp_path: Path) -> None:
    script = _script()
    as_json = tmp_path / "residents.json"
    as_json.write_text(json.dumps(script.read_rows(SEED / "residents.csv")), encoding="utf-8")
    assert script.read_rows(as_json) == script.read_rows(SEED / "residents.csv")
    assert "admitted_on" not in script.read_rows(SEED / "residents.csv")[0]  # empty cell: absent
