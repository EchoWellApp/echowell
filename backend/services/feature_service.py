"""The 7 scored voice measurements of a resident (TRD 05 API-078; TRD 19 E-11; TRD 11 §4.5.4;
FEAT-028).

Points are the usable, non-duplicate sessions of the current epoch in the window; raw values come
from the typed `raw_sessions` columns, adjusted values from `processed_sessions`, and `z` is the
unsigned stored z of `scores` (null when the session was not scored).
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy.orm import Session

from analytics.config import FEATURES
from backend.repositories import read_models as rm
from backend.services.resident_service import ReadContext, get_resident

# Card label and technical name of TRD 11 §4.5.4, by feature key (contract §6 order).
CARD_LABELS: dict[str, tuple[str, str]] = {
    "loudness_dbfs": ("Quieter", "loudness"),
    "total_phrase_duration_s": ("Slower to say the phrase", "phrase duration"),
    "speech_rate_syl_per_s": ("Fewer syllables per second", "speech rate"),
    "articulation_rate_syl_per_s": ("Slower while talking", "articulation rate"),
    "number_of_pauses": ("More pauses", "number of pauses"),
    "pause_fraction": ("More time in pauses", "pause fraction"),
    "voiced_fraction": ("Less voiced sound", "voiced fraction"),
}


def default_window(ctx: ReadContext) -> tuple[date, date]:
    """The 30 local days ending on the as-of date (FEAT-028-FR-12)."""
    return ctx.as_of_date - timedelta(days=rm.WINDOW_DAYS - 1), ctx.as_of_date


def series(
    session: Session, ctx: ReadContext, resident_code: str, start: date, end: date
) -> dict[str, Any]:
    """`FeaturesResponse` for the current epoch (TRD 19 E-11)."""
    resident = get_resident(session, resident_code)
    epoch = rm.current_epochs(session, [resident.id]).get(resident.id)
    baselines = rm.feature_baselines(session, epoch)
    rows = rm.usable_sessions(session, epoch, start, end) if epoch is not None else []
    scored = []
    for spec in (f for f in FEATURES if f.in_composite):
        card, technical = CARD_LABELS[spec.key]
        baseline = baselines.get(spec.key)
        scored.append(
            {
                "feature_key": spec.key,
                "label": f"{card} ({technical})",
                "unit": spec.unit,
                "composite_sign": spec.sign,
                "baseline_median": baseline.median if baseline else None,
                "baseline_robust_spread": baseline.robust_spread if baseline else None,
                "points": [
                    {
                        "session_id": row.processed.session_id,
                        "local_date": row.processed.local_date,
                        "is_morning": row.processed.is_morning,
                        "raw_value": float(getattr(row.raw, spec.key)),
                        "adjusted_value": float((row.processed.adjusted_features or {})[spec.key]),
                        "z": row.z.get(f"z_{spec.key}") if row.z else None,
                        "in_baseline": row.processed.in_baseline,
                    }
                    for row in rows
                ],
            }
        )
    return {
        "meta": ctx.meta,
        "resident_code": resident.resident_code,
        "epoch_number": epoch.epoch_number if epoch else None,
        "scored_features": scored,
        "stored_feature_keys": [f.key for f in FEATURES if not f.in_composite],
    }
