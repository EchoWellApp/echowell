"""Score and baseline read-outs with CSV export (TRD 05 API-079, API-088, API-129; TRD 19 E-12,
E-19; FEAT-034)."""

from __future__ import annotations

from dataclasses import asdict
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from backend.core.errors import InvalidQueryParameterError
from backend.models import COMPOSITE_Z_KEYS
from backend.repositories import read_models as rm
from backend.repositories.baseline_repository import BaselineRepository
from backend.repositories.config_repository import ConfigRepository
from backend.repositories.score_repository import ScoreFilter, ScoreReadRow, ScoreRepository
from backend.services.resident_service import ReadContext, get_resident

SCORE_FIELDS: tuple[str, ...] = (
    "session_id", "resident_code", "epoch_number", "local_date", "is_morning", *COMPOSITE_Z_KEYS,
    "composite_raw", "composite_z", "cusum_tally", "alarm_state",
)  # fmt: skip
BASELINE_FIELDS: tuple[str, ...] = (
    "resident_code", "epoch_number", "device_code", "feature_key", "n_sessions",
    "first_session_id", "frozen_after_session_id", "median", "mad", "robust_spread",
    "floor_applied",
)  # fmt: skip


def score_filter(
    session: Session,
    *,
    resident_code: str | None,
    epoch: int | None,
    start: date | None,
    end: date | None,
) -> ScoreFilter:
    """422 for `epoch` without `resident_code`; 404 for an unknown resident (API-079)."""
    if epoch is not None and resident_code is None:
        raise InvalidQueryParameterError("'epoch' requires 'resident_code'")
    resident_id = get_resident(session, resident_code).id if resident_code is not None else None
    return ScoreFilter(resident_id=resident_id, epoch_number=epoch, start=start, end=end)


def _z(row: ScoreReadRow) -> dict[str, float]:
    return {key: float(row.z[key]) for key in COMPOSITE_Z_KEYS}


def _score_dict(row: ScoreReadRow) -> dict[str, Any]:
    return {
        "session_id": row.session_id, "resident_code": row.resident_code,
        "epoch_number": row.epoch_number, "local_date": row.local_date,
        "is_morning": row.is_morning, "z": _z(row), "composite_raw": row.composite_raw,
        "composite_z": row.composite_z, "cusum_tally": row.cusum_tally,
        "alarm_state": row.alarm_state,
    }  # fmt: skip


def scores(
    session: Session, ctx: ReadContext, profile: str, where: ScoreFilter, *, limit: int, offset: int
) -> dict[str, Any]:
    """`ScoresResponse`: rows, `cusum_k` and one baseline period per resident-epoch (API-079)."""
    repository = ScoreRepository(session)
    rows = repository.read_rows(where, limit=limit, offset=offset)
    periods = [asdict(p) for p in rm.baseline_periods(session, repository.epochs_in(where))]
    k = float(ConfigRepository(session).values_for_profile(profile)["cusum_k"])
    return {
        "meta": ctx.meta, "cusum_k": k, "baseline_periods": periods,
        "items": [_score_dict(r) for r in rows], "total": repository.count_rows(where),
        "limit": limit, "offset": offset,
    }  # fmt: skip


def score_csv_rows(session: Session, where: ScoreFilter) -> list[list[Any]]:
    """Every matching row in `SCORE_FIELDS` order (pagination ignored)."""
    return [
        [r.session_id, r.resident_code, r.epoch_number, r.local_date, r.is_morning,
         *_z(r).values(), r.composite_raw, r.composite_z, r.cusum_tally, r.alarm_state]
        for r in ScoreRepository(session).read_rows(where)
    ]  # fmt: skip


def count_scores(session: Session, where: ScoreFilter) -> int:
    return ScoreRepository(session).count_rows(where)


def baseline_rows(
    session: Session, *, resident_code: str | None, epoch: int | None
) -> list[dict[str, Any]]:
    """`BaselineRow` items in API-088 order; `epoch` requires `resident_code`."""
    if epoch is not None and resident_code is None:
        raise InvalidQueryParameterError("'epoch' requires 'resident_code'")
    resident_id = get_resident(session, resident_code).id if resident_code is not None else None
    return [
        {
            "resident_code": code, "epoch_number": number, "device_code": device,
            "feature_key": b.feature_key, "n_sessions": b.n_sessions,
            "first_session_id": b.first_session_id,
            "frozen_after_session_id": b.frozen_after_session_id, "median": b.median,
            "mad": b.mad, "robust_spread": b.robust_spread, "floor_applied": b.floor_applied,
        }
        for b, code, number, device in BaselineRepository(session).read_rows(
            resident_id=resident_id, epoch_number=epoch
        )
    ]  # fmt: skip
