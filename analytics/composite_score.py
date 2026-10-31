"""Signed composite raw and composite z (TRD 08 §4.7-§4.8 BSC-032, BSC-033, BSC-038; FEAT-046).

composite_raw is the signed z summed in canonical feature order and divided by 7 (ANL-022); a
positive composite_z means a change toward the depression-associated direction.
"""

from __future__ import annotations

from collections.abc import Mapping

from analytics.config import COMPOSITE_KEYS, COMPOSITE_SIGNS, Baseline, PipelineConfig


def composite_raw(z: Mapping[str, float], config: PipelineConfig) -> float:
    total = 0.0
    for key in COMPOSITE_KEYS:
        total += COMPOSITE_SIGNS[key] * z[key]
    return total / len(COMPOSITE_KEYS)


def composite_z(raw: float, composite_baseline: Baseline) -> float:
    spread = composite_baseline.robust_spread
    return (raw - composite_baseline.median) / spread if spread > 0 else 0.0
