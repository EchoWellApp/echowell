"""Per-feature z of the 7 composite features (TRD 08 §4.8 BSC-036, BSC-037; FEAT-046).

z = (adjusted - baseline median) / robust spread, unsigned; a zero spread gives z = 0
(BSC-035, the run warns `zero_spread`).
"""

from __future__ import annotations

from collections.abc import Mapping

from analytics.config import COMPOSITE_KEYS, AdjustedRecord, Baseline, PipelineConfig


def feature_z(
    row: AdjustedRecord, baselines: Mapping[str, Baseline], config: PipelineConfig
) -> dict[str, float]:
    """`{feature_key: z}` for the composite features in canonical order."""
    out = {}
    for key in COMPOSITE_KEYS:
        b = baselines[key]
        out[key] = (row.adjusted[key] - b.median) / b.robust_spread if b.robust_spread > 0 else 0.0
    return out
