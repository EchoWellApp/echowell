"""The `meta` block of every list, detail and analytics response (TRD 05 API-057, API-069;
TRD 21 ENV-016; FEAT-019-FR-10, FR-11)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from backend.core.config import Settings
from backend.repositories.config_repository import ConfigRepository
from backend.repositories.facility_repository import FacilityRepository
from backend.repositories.pipeline_run_repository import PipelineRunRepository
from backend.schemas.common import Meta


def get_meta(session: Session, settings: Settings) -> Meta:
    """`facilities.name`, FACILITY_TZ, DATA_SOURCE_LABEL, the latest succeeded run's `as_of`
    (None before any) and the active profile's `baseline_n` and `cusum_h`."""
    facility = FacilityRepository(session).get_single()
    latest = PipelineRunRepository(session).latest_succeeded()
    values = ConfigRepository(session).values_for_profile(settings.pipeline_profile)
    return Meta(
        facility_name=facility.name if facility is not None else settings.facility_name,
        facility_tz=settings.facility_tz,
        data_source_label=settings.data_source_label,
        as_of=latest.as_of if latest is not None else None,
        baseline_n=int(values["baseline_n"]),
        cusum_h=float(values["cusum_h"]),
        pipeline_profile=settings.pipeline_profile,
    )
