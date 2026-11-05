"""DS-08, the performance load dataset (TRD 14 DS-08, TDV-008; TRD 13 TST-121..TST-123; FEAT-079).

    python tests/performance/make_load_dataset.py --seed 20261004 --out /tmp/ds08

writes, into `--out` (a temporary directory; DS-08 is never committed, FEAT-079-AC-06):

- `ds08_sessions.csv`: the records in the SRC-05 column order (TRD 10 §4.1);
- `facilities.csv`, `residents.csv`, `devices.csv`, `device_assignments.csv`: the roster in the
  TRD 06 DB-060 format read by `python -m backend.cli import-master-data --dir`.

Rules (TDV-008): resident codes `L001`..`L100`, devices `LD001`..`LD100`, start 2026-06-01,
120 days, one record per resident-day between 14:00 and 15:00 America/Chicago, exactly 10 % of
the 12,000 resident-days dropped (10,800 records), exactly 5 % of the records with
`mic_noise_level_dbfs` -32.0, and feature values drawn as the SRC-04 generator's `make_values`
draws them (person means from the feature ranges, a shared composite factor, rounding as
`finish`). The SRC-04 script is read for its rules only and never imported (TRD 25 §8); this module
imports nothing from `analytics/` or `backend/`. The same seed always yields byte-identical files.
Synthetic data only: the residents are `L`-prefixed study IDs (AGT-017), performance only, no
correctness claims (TRD 14 DS-08).
"""

from __future__ import annotations

import argparse
import csv
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np

SEED = 20261004
FACILITY = ("Edgewood", "America/Chicago")
TZ = ZoneInfo(FACILITY[1])
UTC = ZoneInfo("UTC")
START = date(2026, 6, 1)
N_RESIDENTS = 100
N_DAYS = 120
DROP_FRACTION = 0.10
NOISY_FRACTION = 0.05
NOISY_DBFS = -32.0
SESSIONS_CSV = "ds08_sessions.csv"

# SRC-05 column order (TRD 10 §4.1).
COLUMNS = (
    "schema_version", "session_id", "resident_id", "device_id", "timestamp_utc",
    "mic_noise_level_dbfs", "audio_quality_flag", "extraction_software_version",
    "device_firmware_version", "speech_duration_s", "phrase_id", "loudness_dbfs",
    "total_phrase_duration_s", "speech_rate_syl_per_s", "articulation_rate_syl_per_s",
    "number_of_pauses", "pause_fraction", "voiced_fraction", "mean_f0_hz", "f0_variability_st",
    "jitter_local_pct", "shimmer_local_pct", "hnr_db", "cpps_db", "alpha_ratio_db",
    "hammarberg_index_db", "mfcc1", "mfcc2", "mfcc3", "mfcc4",
)  # fmt: skip

# SRC-04 FEATS: name, lo, hi, cv (None = absolute sd), absolute sd, decimals, composite direction.
FEATS: tuple[tuple[str, float | None, float | None, float | None, float | None, int, int], ...] = (
    ("loudness_dbfs", -30, -18, None, 2.8, 2, -1),
    ("total_phrase_duration_s", 2.0, 4.0, 0.06, None, 2, +1),
    ("speech_rate_syl_per_s", 3.0, 4.5, 0.04, None, 2, -1),
    ("articulation_rate_syl_per_s", 4.0, 5.5, 0.04, None, 2, -1),
    ("number_of_pauses", 0.8, 2.0, None, 0.7, 0, +1),
    ("pause_fraction", 0.05, 0.25, 0.15, None, 3, +1),
    ("voiced_fraction", 0.50, 0.75, 0.05, None, 3, -1),
    ("mean_f0_hz", None, None, 0.04, None, 1, 0),
    ("f0_variability_st", 2.0, 4.5, 0.08, None, 2, 0),
    ("jitter_local_pct", 0.2, 1.0, 0.25, None, 3, 0),
    ("shimmer_local_pct", 2.0, 6.0, 0.25, None, 2, 0),
    ("hnr_db", 10, 20, 0.06, None, 2, 0),
    ("cpps_db", 8, 16, 0.06, None, 2, 0),
    ("alpha_ratio_db", -20, 0, None, 1.5, 2, 0),
    ("hammarberg_index_db", 15, 30, 0.06, None, 2, 0),
    ("mfcc1", 20, 40, None, 2.0, 2, 0),
    ("mfcc2", 0, 15, None, 1.5, 2, 0),
    ("mfcc3", -5, 10, None, 1.5, 2, 0),
    ("mfcc4", -10, 5, None, 1.5, 2, 0),
)
F0_RANGE = {"F": (165.0, 200.0), "M": (110.0, 145.0)}


@dataclass
class Dataset:
    records: list[dict[str, Any]] = field(default_factory=list)
    residents: list[dict[str, str]] = field(default_factory=list)
    devices: list[dict[str, str]] = field(default_factory=list)
    assignments: list[dict[str, str]] = field(default_factory=list)


def _sd(spec: tuple[Any, ...], mean: float) -> float:
    cv, absolute = spec[3], spec[4]
    return float(absolute) if cv is None else float(cv) * abs(mean)


def _draw_means(rng: np.random.Generator, sex: str) -> dict[str, float]:
    means: dict[str, float] = {}
    for name, lo, hi, *_ in FEATS:
        low, high = F0_RANGE[sex] if name == "mean_f0_hz" else (lo, hi)
        means[name] = float(rng.uniform(low, high))
    return means


def _make_values(rng: np.random.Generator, means: dict[str, float]) -> dict[str, float | int]:
    """SRC-04 `make_values` (no shift) followed by `finish` (rounding and clamps)."""
    shared = rng.normal()
    values: dict[str, float | int] = {}
    for spec in FEATS:
        name, decimals, direction = spec[0], spec[5], spec[6]
        sd = _sd(spec, means[name])
        noise = rng.normal()
        if direction:
            x = means[name] + sd * (0.6 * shared * direction + 0.8 * noise)
        else:
            x = means[name] + sd * noise
        if name == "number_of_pauses":
            values[name] = max(0, round(x))
            continue
        if name in ("pause_fraction", "voiced_fraction"):
            x = min(max(x, 0.0), 1.0)
        if name == "jitter_local_pct":
            x = max(x, 0.05)
        if name == "shimmer_local_pct":
            x = max(x, 0.5)
        values[name] = round(x, decimals)
    return values


def generate(
    seed: int = SEED,
    *,
    residents: int = N_RESIDENTS,
    days: int = N_DAYS,
    start: date = START,
    drop_fraction: float = DROP_FRACTION,
    noisy_fraction: float = NOISY_FRACTION,
    prefix: str = "L",
) -> Dataset:
    """DS-08 by default; the keyword arguments build the smaller rosters of the latency tests
    (for example one resident with a long gap-free history for TST-121)."""
    rng = np.random.default_rng(seed)
    data = Dataset()
    codes = [(f"{prefix}{n:03d}", f"{prefix}D{n:03d}") for n in range(1, residents + 1)]
    resident_days = [(r, d) for r in range(residents) for d in range(days)]
    n_drop = round(len(resident_days) * drop_fraction)
    dropped = {resident_days[i] for i in rng.permutation(len(resident_days))[:n_drop]}
    kept = [rd for rd in resident_days if rd not in dropped]
    n_noisy = round(len(kept) * noisy_fraction)
    noisy = {kept[i] for i in rng.permutation(len(kept))[:n_noisy]}
    for index, (code, device) in enumerate(codes):
        sex = "F" if rng.random() < 0.5 else "M"
        means = _draw_means(rng, sex)
        data.residents.append({"resident_code": code, "sex": sex, "cohort": "longitudinal",
                               "enrolled_on": start.isoformat(), "admitted_on": ""})  # fmt: skip
        data.devices.append({"device_code": device, "room_label": "", "active": "true",
                             "firmware_version_last": "fw-1.0.0"})  # fmt: skip
        data.assignments.append({"resident_code": code, "device_code": device,
                                 "valid_from": start.isoformat(), "valid_to": ""})  # fmt: skip
        for day in range(days):
            values = _make_values(rng, means)  # drawn for every day, so drops do not shift draws
            minute, second = int(rng.integers(0, 60)), int(rng.integers(0, 60))
            noise = round(float(rng.uniform(-56, -46)), 1)
            if (index, day) in dropped:
                continue
            local_day = start + timedelta(days=day)
            local = datetime(local_day.year, local_day.month, local_day.day, 14, minute, second,
                             tzinfo=TZ)  # fmt: skip
            data.records.append({
                "schema_version": "0.1",
                "session_id": f"{code}-{local:%Y%m%d}-01",
                "resident_id": code,
                "device_id": device,
                "timestamp_utc": local.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S"),
                "mic_noise_level_dbfs": NOISY_DBFS if (index, day) in noisy else noise,
                "audio_quality_flag": "ok",
                "extraction_software_version": "openSMILE 3.0.2",
                "device_firmware_version": "fw-1.0.0",
                "speech_duration_s": values["total_phrase_duration_s"],
                "phrase_id": "P01",
                **values,
            })  # fmt: skip
    return data


def _write_csv(path: Path, header: Sequence[str], rows: Sequence[dict[str, Any]]) -> Path:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(header), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return path


def write(data: Dataset, out: Path) -> dict[str, Path]:
    """The sessions CSV and the four roster CSVs (DB-060) in `out`."""
    out.mkdir(parents=True, exist_ok=True)
    return {
        "sessions": _write_csv(out / SESSIONS_CSV, COLUMNS, data.records),
        "facilities": _write_csv(out / "facilities.csv", ("name", "timezone"),
                                 [{"name": FACILITY[0], "timezone": FACILITY[1]}]),
        "residents": _write_csv(out / "residents.csv",
                                ("resident_code", "sex", "cohort", "enrolled_on", "admitted_on"),
                                data.residents),
        "devices": _write_csv(out / "devices.csv",
                              ("device_code", "room_label", "active", "firmware_version_last"),
                              data.devices),
        "device_assignments": _write_csv(out / "device_assignments.csv",
                                         ("resident_code", "device_code", "valid_from", "valid_to"),
                                         data.assignments),
    }  # fmt: skip


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--out", type=Path, default=Path("build/ds08"),
                        help="output directory (default build/ds08, gitignored)")  # fmt: skip
    args = parser.parse_args(argv)
    data = generate(args.seed)
    paths = write(data, args.out)
    print(f"DS-08: {len(data.records)} records, {len(data.residents)} residents -> {args.out}")
    return 0 if paths else 1


if __name__ == "__main__":
    raise SystemExit(main())
