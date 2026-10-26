"""Residents (TRD 23 §4.2.3, §4.3.3, §4.3.4; DME-004, DME-008, DME-009; FEAT-009).

Residents are looked up by `resident_code`, so APIs never need `residents.id` (DME-004). The only
state transitions exposed are active → withdrawn (CLI, FEAT-017) and new_admission → longitudinal
(pipeline, FEAT-053); nothing returns a resident to `active` or to `new_admission`.
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Resident, ResidentCohort, ResidentStatus


class ResidentTransitionError(ValueError):
    """A status or cohort change that TRD 23 §4.3.3/§4.3.4 does not allow."""


class ResidentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_code(self, resident_code: str) -> Resident | None:
        return self.session.scalars(
            select(Resident).where(Resident.resident_code == resident_code)
        ).first()

    def list_active(self, cohort: ResidentCohort | None = None) -> list[Resident]:
        """Active residents, optionally of one cohort, in `resident_code` order."""
        query = select(Resident).where(Resident.status == ResidentStatus.ACTIVE)
        if cohort is not None:
            query = query.where(Resident.cohort == cohort)
        return list(self.session.scalars(query.order_by(Resident.resident_code)).all())

    def list_all(self) -> list[Resident]:
        return list(self.session.scalars(select(Resident).order_by(Resident.resident_code)).all())

    def upsert_roster(
        self,
        *,
        facility_id: uuid.UUID,
        resident_code: str,
        sex: str | None,
        cohort: ResidentCohort,
        enrolled_on: date,
        admitted_on: date | None,
    ) -> Resident:
        """Roster import (DB-060): insert, or update sex and dates of an existing resident.

        The cohort of an existing resident only follows the allowed new_admission → longitudinal
        transition; a roster file can never move a resident back.
        """
        resident = self.get_by_code(resident_code)
        if resident is None:
            resident = Resident(
                facility_id=facility_id,
                resident_code=resident_code,
                sex=sex,
                cohort=cohort,
                enrolled_on=enrolled_on,
                admitted_on=admitted_on,
            )
            self.session.add(resident)
        else:
            resident.sex = sex
            resident.enrolled_on = enrolled_on
            resident.admitted_on = admitted_on
            if cohort != resident.cohort:
                self._check_cohort_transition(resident.cohort, cohort)
                resident.cohort = cohort
        self.session.flush()
        return resident

    def set_withdrawn(self, resident: Resident, on: date) -> Resident:
        """active → withdrawn with the withdrawal date (DB-062, DME-009)."""
        if resident.status != ResidentStatus.ACTIVE:
            raise ResidentTransitionError(f"resident {resident.resident_code} is already withdrawn")
        resident.status = ResidentStatus.WITHDRAWN
        resident.withdrawn_on = on
        self.session.flush()
        return resident

    def set_cohort_longitudinal(self, resident: Resident) -> Resident:
        """new_admission → longitudinal when the own baseline froze (DB-025, DME-008)."""
        self._check_cohort_transition(resident.cohort, ResidentCohort.LONGITUDINAL)
        resident.cohort = ResidentCohort.LONGITUDINAL
        self.session.flush()
        return resident

    @staticmethod
    def _check_cohort_transition(current: ResidentCohort, new: ResidentCohort) -> None:
        if not (current == ResidentCohort.NEW_ADMISSION and new == ResidentCohort.LONGITUDINAL):
            raise ResidentTransitionError(f"cohort cannot change from {current} to {new}")
