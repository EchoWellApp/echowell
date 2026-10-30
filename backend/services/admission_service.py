"""New-admission comparison, the experimental arm (TRD 05 API-089, API-090; TRD 02 FR-201..FR-206;
TRD 19 E-22..E-24; TRD 24 OQ-29 interim decision; FEAT-036).

Read-only: these endpoints never create alerts, scores or CUSUM rows (FR-206). The comparison uses
the median of the resident's morning-adjusted usable values of the 7 composite features; below 5
usable check-ins it is `not_enough_checkins`; the range row of the resident's sex is used, else
the row without sex, else `range_not_available`.
"""

from __future__ import annotations

import statistics
from typing import Any

from sqlalchemy.orm import Session

from analytics.config import FEATURES
from backend.core.errors import ResidentNotFoundError
from backend.models import FacilityReferenceRange, Resident, ResidentCohort, ResidentStatus
from backend.repositories import read_models as rm
from backend.repositories.facility_repository import FacilityRepository
from backend.repositories.reference_range_repository import ReferenceRangeRepository
from backend.repositories.resident_repository import ResidentRepository
from backend.services.resident_service import ReadContext, natural_key

MIN_CHECKINS = 5
SCORED = tuple(f.key for f in FEATURES if f.in_composite)
_ORDER = {f.key: i for i, f in enumerate(FEATURES)}


def _ranges(session: Session) -> list[FacilityReferenceRange]:
    facility = FacilityRepository(session).get_single()
    return ReferenceRangeRepository(session).latest(facility.id) if facility else []


def _range_for(
    ranges: list[FacilityReferenceRange], key: str, sex: str | None
) -> FacilityReferenceRange | None:
    rows = [r for r in ranges if r.feature_key == key]
    return next((r for r in rows if r.sex == sex and sex is not None), None) or next(
        (r for r in rows if r.sex is None), None
    )


def _comparison(
    session: Session, resident: Resident, ranges: list[FacilityReferenceRange]
) -> tuple[str, list[dict[str, Any]], int]:
    rows = rm.usable_since(session, resident.id, resident.admitted_on)
    features = []
    for key in SCORED:
        values = [float((row.adjusted_features or {})[key]) for row in rows]
        value = statistics.median(values) if values else None
        band = _range_for(ranges, key, resident.sex)
        outside = None
        if value is not None and band is not None:
            outside = not band.low <= value <= band.high
        features.append(
            {
                "feature_key": key, "resident_value": value,
                "low": band.low if band else None, "high": band.high if band else None,
                "outside_range": outside,
            }
        )  # fmt: skip
    if not any(f["low"] is not None for f in features):
        status = "range_not_available"
    elif len(rows) < MIN_CHECKINS:
        status = "not_enough_checkins"
    elif any(f["outside_range"] for f in features):
        status = "outside_range"
    else:
        status = "within_range"
    return status, features, len(rows)


def list_admissions(
    session: Session, ctx: ReadContext, *, limit: int, offset: int
) -> dict[str, Any]:
    """Active new-admission residents whose own baseline has not formed (FR-201)."""
    ranges = _ranges(session)
    candidates = [
        r
        for r in ResidentRepository(session).list_all()
        if r.cohort == ResidentCohort.NEW_ADMISSION and r.status == ResidentStatus.ACTIVE
    ]
    epochs = rm.current_epochs(session, [r.id for r in candidates])
    items = []
    for resident in sorted(candidates, key=lambda r: natural_key(r.resident_code)):
        progress = rm.baseline_progress(session, epochs.get(resident.id), ctx.baseline_n)
        if progress.frozen:
            continue
        status, _, checkins = _comparison(session, resident, ranges)
        items.append(
            {
                "resident_code": resident.resident_code, "admitted_on": resident.admitted_on,
                "checkins_so_far": checkins, "comparison_status": status,
                "own_baseline_progress": {"n_usable": progress.n, "n_required": progress.of},
            }
        )  # fmt: skip
    return {
        "meta": ctx.meta, "items": items[offset : offset + limit], "total": len(items),
        "limit": limit, "offset": offset,
    }  # fmt: skip


def comparison(session: Session, ctx: ReadContext, resident_code: str) -> dict[str, Any]:
    """404 for an unknown code or a resident outside the new-admission cohort (API-090)."""
    resident = ResidentRepository(session).get_by_code(resident_code)
    if resident is None or resident.cohort != ResidentCohort.NEW_ADMISSION:
        raise ResidentNotFoundError(f"No new-admission resident {resident_code}.")
    status, features, _ = _comparison(session, resident, _ranges(session))
    return {
        "meta": ctx.meta, "resident_code": resident.resident_code, "comparison_status": status,
        "features": features,
    }  # fmt: skip


def reference_ranges(
    session: Session, ctx: ReadContext, *, limit: int, offset: int
) -> dict[str, Any]:
    rows = sorted(_ranges(session), key=lambda r: (_ORDER.get(r.feature_key, 99), r.sex or ""))
    items = [
        {
            "feature_key": r.feature_key, "low": r.low, "high": r.high, "method": r.method,
            "n_residents": r.n_residents, "computed_at": r.computed_at,
            "pipeline_run_id": r.pipeline_run_id,
        }
        for r in rows[offset : offset + limit]
    ]  # fmt: skip
    return {"meta": ctx.meta, "items": items, "total": len(rows), "limit": limit, "offset": offset}
