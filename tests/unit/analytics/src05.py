"""The SRC-05 engine inputs: records, the R01-R10 roster and assignments of TRD 10 §4.9, and the
test as-of 2026-10-30 15:00 America/Chicago (TRD 07 ANL-017). Shared by the analytics tests."""

from __future__ import annotations

import csv
import uuid
from datetime import UTC, date, datetime
from functools import cache
from pathlib import Path
from zoneinfo import ZoneInfo

from analytics.config import FEATURE_KEYS, DeviceAssignment, RawRecord, ResidentInfo

ROOT = Path(__file__).resolve().parents[3]
SRC_05 = ROOT / "tests" / "fixtures" / "pipeline_input" / "EchoWell_pipeline_test_input_v0_1.csv"
AS_OF = datetime(2026, 10, 30, 15, 0, tzinfo=ZoneInfo("America/Chicago"))
ENROLLED = date(2026, 10, 1)
RECEIVED = datetime(2026, 10, 30, 20, 0, tzinfo=UTC)


def parse_utc(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)


def record(row: dict[str, str], seq: int) -> RawRecord:
    return RawRecord(
        raw_session_id=str(uuid.UUID(int=seq)), arrival_seq=seq, received_at=RECEIVED,
        schema_version=row["schema_version"], session_id=row["session_id"],
        resident_code=row["resident_id"], device_code=row["device_id"],
        timestamp_utc=parse_utc(row["timestamp_utc"]),
        mic_noise_level_dbfs=float(row["mic_noise_level_dbfs"]),
        audio_quality_flag=row["audio_quality_flag"],
        extraction_software_version=row["extraction_software_version"],
        device_firmware_version=row["device_firmware_version"],
        speech_duration_s=float(row["speech_duration_s"]), phrase_id=row["phrase_id"],
        features={k: float(row[k]) for k in FEATURE_KEYS},
    )  # fmt: skip


@cache
def records() -> tuple[RawRecord, ...]:
    with SRC_05.open(newline="", encoding="utf-8") as handle:
        return tuple(record(row, i) for i, row in enumerate(csv.DictReader(handle), start=1))


RESIDENTS = tuple(ResidentInfo(f"R{n:02d}", ENROLLED) for n in range(1, 11))
ASSIGNMENTS = (
    DeviceAssignment("R01", "D01", ENROLLED),
    DeviceAssignment("R02", "D02", ENROLLED),
    DeviceAssignment("R03", "D02", ENROLLED),
    DeviceAssignment("R04", "D04", ENROLLED),
    DeviceAssignment("R05", "D05", ENROLLED),
    DeviceAssignment("R06", "D06", ENROLLED),
    DeviceAssignment("R07", "D07", ENROLLED, date(2026, 10, 12)),
    DeviceAssignment("R07", "D07B", date(2026, 10, 13)),
    DeviceAssignment("R08", "D08", ENROLLED),
    DeviceAssignment("R09", "D09", ENROLLED),
    DeviceAssignment("R10", "D10", ENROLLED),
)
