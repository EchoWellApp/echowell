"""Small builders for analytics unit tests: one record with every field defaulted."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from analytics.config import FEATURE_KEYS, RawRecord

BASE_FEATURES = {
    "loudness_dbfs": -24.0, "total_phrase_duration_s": 2.5, "speech_rate_syl_per_s": 3.6,
    "articulation_rate_syl_per_s": 5.2, "number_of_pauses": 1.0, "pause_fraction": 0.14,
    "voiced_fraction": 0.65, "mean_f0_hz": 200.0, "f0_variability_st": 4.0,
    "jitter_local_pct": 0.8, "shimmer_local_pct": 1.5, "hnr_db": 11.0, "cpps_db": 12.0,
    "alpha_ratio_db": -14.0, "hammarberg_index_db": 16.0, "mfcc1": 38.0, "mfcc2": 15.0,
    "mfcc3": -2.0, "mfcc4": -8.0,
}  # fmt: skip


def rec(
    seq: int, ts: str, *, resident: str = "R01", device: str = "D01", session: str | None = None,
    firmware: str = "fw-1.0.0", software: str = "openSMILE 3.0.2", flag: str = "ok",
    noise: float = -55.0, speech: float = 2.5, **features: float,
) -> RawRecord:  # fmt: skip
    stamp = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S").replace(tzinfo=UTC)
    values: dict[str, Any] = {**BASE_FEATURES, **features}
    return RawRecord(
        raw_session_id=str(uuid.UUID(int=seq)), arrival_seq=seq, received_at=stamp,
        schema_version="0.1",
        session_id=session or f"{resident}-{stamp:%Y%m%d}-01", resident_code=resident,
        device_code=device, timestamp_utc=stamp, mic_noise_level_dbfs=noise,
        audio_quality_flag=flag, extraction_software_version=software,
        device_firmware_version=firmware, speech_duration_s=speech, phrase_id="P01",
        features={k: float(values[k]) for k in FEATURE_KEYS},
    )  # fmt: skip
