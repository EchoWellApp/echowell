"""Facility reference ranges for the experimental new-admission arm (TRD 23 §4.2.21; FEAT-012)."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import FacilityReferenceRange


class ReferenceRangeRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def latest(self, facility_id: uuid.UUID) -> list[FacilityReferenceRange]:
        """The most recent range per (feature, sex) (index facility_reference_ranges_lookup_idx)."""
        query = (
            select(FacilityReferenceRange)
            .where(FacilityReferenceRange.facility_id == facility_id)
            .distinct(FacilityReferenceRange.feature_key, FacilityReferenceRange.sex)
            .order_by(
                FacilityReferenceRange.feature_key,
                FacilityReferenceRange.sex,
                FacilityReferenceRange.computed_at.desc(),
            )
        )
        return list(self.session.scalars(query).all())
