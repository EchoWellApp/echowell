"""Facilities: the single facility row of the MVP (TRD 23 §4.2.1; ARC-105; FEAT-009)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Facility


class FacilityRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_single(self) -> Facility | None:
        """The facility of this deployment; the MVP operates exactly one (ARC-105)."""
        return self.session.scalars(select(Facility).order_by(Facility.created_at).limit(1)).first()

    def get_by_name(self, name: str) -> Facility | None:
        return self.session.scalars(select(Facility).where(Facility.name == name)).first()

    def upsert(self, name: str, timezone: str) -> Facility:
        """Insert the facility or update its time zone (roster import, bootstrap; DB-060)."""
        facility = self.get_by_name(name)
        if facility is None:
            facility = Facility(name=name, timezone=timezone)
            self.session.add(facility)
        elif facility.timezone != timezone:
            facility.timezone = timezone
        self.session.flush()
        return facility
