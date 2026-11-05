"""DS-08 generator (TRD 14 DS-08, TDV-008; FEAT-079-FR-01, AC-03, AC-06).

Seed 20261004 run twice yields byte-identical files with 10,800 records for L001..L100, exactly
10 % of resident-days dropped, 5 % noisy records at -32.0 dBFS, 14:00-15:00 local; and no generated
dataset file is tracked under `tests/performance` (AC-06).
"""

from __future__ import annotations

import csv
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from tests.integration.db_support import ROOT
from tests.performance import make_load_dataset as ds

pytestmark = pytest.mark.performance


@pytest.mark.req("TDV-008")
def test_ds08_is_deterministic_and_follows_tdv_008(tmp_path: Path) -> None:
    first, second = tmp_path / "a", tmp_path / "b"
    assert ds.main(["--seed", "20261004", "--out", str(first)]) == 0
    assert ds.main(["--seed", "20261004", "--out", str(second)]) == 0
    names = sorted(p.name for p in first.iterdir())
    assert names == sorted(p.name for p in second.iterdir())
    for name in names:
        assert (first / name).read_bytes() == (second / name).read_bytes(), name
    with (first / ds.SESSIONS_CSV).open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 10_800
    assert {r["resident_id"] for r in rows} == {f"L{n:03d}" for n in range(1, 101)}
    assert {r["device_id"] for r in rows} == {f"LD{n:03d}" for n in range(1, 101)}
    assert sum(r["mic_noise_level_dbfs"] == "-32.0" for r in rows) == 540
    tz = ZoneInfo("America/Chicago")
    for row in rows:
        utc = datetime.strptime(row["timestamp_utc"], "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=ZoneInfo("UTC")
        )
        local = utc.astimezone(tz)
        assert local.hour == 14, row["session_id"]
        assert row["session_id"] == f"{row['resident_id']}-{local:%Y%m%d}-01"
    days = sorted({r["session_id"][5:13] for r in rows})
    assert days[0] == "20260601"
    assert days[-1] == "20260928"
    assert ds.generate(20261005).records != ds.generate(20261004).records


@pytest.mark.req("TDV-008")
def test_no_generated_dataset_is_tracked() -> None:
    tracked = subprocess.run(  # noqa: S603 - fixed arguments
        ["git", "ls-files", "tests/performance"],  # noqa: S607 - git from PATH
        cwd=ROOT, capture_output=True, text=True, check=True, timeout=30,
    ).stdout.split()  # fmt: skip
    data = [n for n in tracked if n.endswith((".csv", ".json", ".xlsx", ".parquet", ".gz"))]
    assert data == [], f"generated datasets must not be committed (TDV-008): {data}"
