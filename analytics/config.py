"""PipelineConfig, FeatureSpec, built-in profiles, config snapshot and hash (TRD 07 §4.2;
FEAT-040).

Checkpoint 4 adds only `FeatureSpec` and the built-in `FEATURES` (contract §6, TRD 23 §4.2.9) so
the API reads units and composite signs from this single copy (DME-002); `PipelineConfig`, the
profiles and the hash follow with FEAT-052.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FeatureSpec:
    """One acoustic feature (TRD 07 §4.2): `sign` 0 means stored, not scored."""

    key: str
    unit: str
    sign: int
    morning_offset: float = 0.0
    spread_floor: float = 0.0

    @property
    def in_composite(self) -> bool:
        return self.sign != 0


# The 19 features in contract §6 order: 7 composite features, then 12 stored, not scored.
FEATURES: tuple[FeatureSpec, ...] = (
    FeatureSpec("loudness_dbfs", "dBFS", -1, -1.50),
    FeatureSpec("total_phrase_duration_s", "s", +1, +0.10),
    FeatureSpec("speech_rate_syl_per_s", "syllables/s", -1, -0.12),
    FeatureSpec("articulation_rate_syl_per_s", "syllables/s", -1, -0.10),
    FeatureSpec("number_of_pauses", "count", +1, 0.0, spread_floor=0.5),
    FeatureSpec("pause_fraction", "proportion", +1, +0.010),
    FeatureSpec("voiced_fraction", "proportion", -1, -0.020),
    FeatureSpec("mean_f0_hz", "Hz", 0),
    FeatureSpec("f0_variability_st", "semitones", 0),
    FeatureSpec("jitter_local_pct", "percent", 0),
    FeatureSpec("shimmer_local_pct", "percent", 0),
    FeatureSpec("hnr_db", "dB", 0),
    FeatureSpec("cpps_db", "dB", 0),
    FeatureSpec("alpha_ratio_db", "dB", 0),
    FeatureSpec("hammarberg_index_db", "dB", 0),
    FeatureSpec("mfcc1", "unitless", 0),
    FeatureSpec("mfcc2", "unitless", 0),
    FeatureSpec("mfcc3", "unitless", 0),
    FeatureSpec("mfcc4", "unitless", 0),
)
