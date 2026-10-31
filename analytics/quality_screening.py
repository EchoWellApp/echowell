"""Quality gate: set aside with every reason (TRD 10 §4.8 ING-040..ING-043; FEAT-041).

Reasons are recorded in the fixed order quality flag, noise, speech duration and joined with
"; " (ING-041). Thresholds are strict: noise -40.0 and speech 1.0 pass (ING-040).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace

from analytics.config import PipelineConfig, ScreenedRecord

QUALITY_FLAG = "quality flag poor"
NOISE = "noise above limit"
TOO_SHORT = "speech too short"


def gate_reasons(row: ScreenedRecord, config: PipelineConfig) -> tuple[str, ...]:
    r = row.record
    reasons = []
    if r.audio_quality_flag != "ok":
        reasons.append(QUALITY_FLAG)
    if r.mic_noise_level_dbfs > config.noise_limit_dbfs:
        reasons.append(NOISE)
    if r.speech_duration_s < config.min_speech_s:
        reasons.append(TOO_SHORT)
    return tuple(reasons)


def apply_quality_gate(
    rows: Sequence[ScreenedRecord], config: PipelineConfig
) -> list[ScreenedRecord]:
    out = []
    for row in rows:
        if row.status == "duplicate":
            out.append(row)
            continue
        reasons = gate_reasons(row, config)
        if reasons:
            out.append(replace(row, status="set_aside", reasons=reasons,
                               reason_text="; ".join(reasons)))  # fmt: skip
        else:
            out.append(replace(row, status="pending_screen", reasons=(), reason_text=""))
    return out
