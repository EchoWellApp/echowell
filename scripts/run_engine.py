"""Run the analytics engine from files and write the result as JSON (TRD 07 ANL-007;
FEAT-052-FR-16).

    python scripts/run_engine.py --input <csv> --profile test_v0_1 --as-of "2026-10-30 15:00" \\
        --assignments <json> --residents <json> --out <dir>

The CSV holds records with the canonical field names (SRC-05 header). `--as-of` is facility-local
time in the profile's time zone. `--residents` is a JSON list of {resident_code, enrolled_on,
withdrawn_on?, status?}; `--assignments` a JSON list of {resident_code, device_code, valid_from,
valid_to?}. File I/O lives here so that every module under `analytics/` stays pure (ARC-041).
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import json
import sys
import uuid
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from analytics import (
    FEATURE_KEYS,
    PRODUCTION,
    TEST_V0_1,
    DeviceAssignment,
    RawRecord,
    ResidentInfo,
    run_pipeline,
)

PROFILES = {"production": PRODUCTION, "test_v0_1": TEST_V0_1}


def _date(value: str | None) -> date | None:
    return date.fromisoformat(value) if value else None


def read_records(path: Path, received_at: datetime) -> list[RawRecord]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return [
        RawRecord(
            raw_session_id=str(uuid.UUID(int=seq)), arrival_seq=seq, received_at=received_at,
            schema_version=row["schema_version"], session_id=row["session_id"],
            resident_code=row["resident_id"], device_code=row["device_id"],
            timestamp_utc=datetime.strptime(row["timestamp_utc"], "%Y-%m-%d %H:%M:%S")
            .replace(tzinfo=UTC),
            mic_noise_level_dbfs=float(row["mic_noise_level_dbfs"]),
            audio_quality_flag=row["audio_quality_flag"],
            extraction_software_version=row["extraction_software_version"],
            device_firmware_version=row["device_firmware_version"],
            speech_duration_s=float(row["speech_duration_s"]), phrase_id=row["phrase_id"],
            features={key: float(row[key]) for key in FEATURE_KEYS},
        )
        for seq, row in enumerate(rows, start=1)
    ]  # fmt: skip


def _plain(value: Any) -> Any:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {f.name: _plain(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_plain(v) for v in value]
    if isinstance(value, datetime | date):
        return value.isoformat()
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--profile", required=True, choices=sorted(PROFILES))
    parser.add_argument("--as-of", required=True, help="facility-local 'YYYY-MM-DD HH:MM'")
    parser.add_argument("--assignments", required=True, type=Path)
    parser.add_argument("--residents", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)
    config = PROFILES[args.profile]
    as_of = datetime.strptime(args.as_of, "%Y-%m-%d %H:%M").replace(tzinfo=config.tz)
    residents = [
        ResidentInfo(r["resident_code"], date.fromisoformat(r["enrolled_on"]),
                     _date(r.get("withdrawn_on")), r.get("status", "active"))
        for r in json.loads(args.residents.read_text(encoding="utf-8"))
    ]  # fmt: skip
    assignments = [
        DeviceAssignment(a["resident_code"], a["device_code"], date.fromisoformat(a["valid_from"]),
                         _date(a.get("valid_to")))
        for a in json.loads(args.assignments.read_text(encoding="utf-8"))
    ]  # fmt: skip
    result = run_pipeline(read_records(args.input, as_of.astimezone(UTC)), residents, assignments,
                          config, as_of)  # fmt: skip
    args.out.mkdir(parents=True, exist_ok=True)
    for field in dataclasses.fields(result):
        path = args.out / f"{field.name}.json"
        text = json.dumps(_plain(getattr(result, field.name)), indent=2, sort_keys=True)
        path.write_text(text + "\n", encoding="utf-8")
    print(f"wrote {len(dataclasses.fields(result))} files to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
