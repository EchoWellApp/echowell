"""Devices and device assignments (TRD 23 §4.2.4, §4.2.5; FEAT-009).

Devices are looked up by `device_code` (DME-004). An assignment's `valid_to` is inclusive; one
resident never has two overlapping assignments (`device_assignments_no_overlap_ex`), while several
residents may share a device.
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.models import Device, DeviceAssignment, Resident


class DeviceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_code(self, device_code: str) -> Device | None:
        return self.session.scalars(select(Device).where(Device.device_code == device_code)).first()

    def list_all(self) -> list[Device]:
        return list(self.session.scalars(select(Device).order_by(Device.device_code)).all())

    def upsert(
        self,
        *,
        facility_id: uuid.UUID,
        device_code: str,
        room_label: str | None,
        active: bool,
        firmware_version_last: str | None,
    ) -> Device:
        """Roster import (DB-060): insert or update a device by `device_code`."""
        device = self.get_by_code(device_code)
        if device is None:
            device = Device(facility_id=facility_id, device_code=device_code)
            self.session.add(device)
        device.room_label = room_label
        device.active = active
        device.firmware_version_last = firmware_version_last
        self.session.flush()
        return device

    def upsert_assignment(
        self,
        *,
        resident_id: uuid.UUID,
        device_id: uuid.UUID,
        valid_from: date,
        valid_to: date | None,
    ) -> DeviceAssignment:
        """Insert or update the assignment keyed by (resident, device, valid_from) (DB-060)."""
        assignment = self.session.scalars(
            select(DeviceAssignment).where(
                DeviceAssignment.resident_id == resident_id,
                DeviceAssignment.device_id == device_id,
                DeviceAssignment.valid_from == valid_from,
            )
        ).first()
        if assignment is None:
            assignment = DeviceAssignment(
                resident_id=resident_id, device_id=device_id, valid_from=valid_from
            )
            self.session.add(assignment)
        assignment.valid_to = valid_to
        self.session.flush()
        return assignment

    def assignments_for_resident(self, resident_id: uuid.UUID) -> list[DeviceAssignment]:
        return list(
            self.session.scalars(
                select(DeviceAssignment)
                .where(DeviceAssignment.resident_id == resident_id)
                .order_by(DeviceAssignment.valid_from)
            ).all()
        )

    def assignments_for_device(self, device_id: uuid.UUID) -> list[DeviceAssignment]:
        return list(
            self.session.scalars(
                select(DeviceAssignment)
                .where(DeviceAssignment.device_id == device_id)
                .order_by(DeviceAssignment.valid_from)
            ).all()
        )

    def assignment_on(self, resident_id: uuid.UUID, day: date) -> DeviceAssignment | None:
        """The resident's assignment covering `day` (at most one, by the exclusion constraint)."""
        return self.session.scalars(
            select(DeviceAssignment).where(
                DeviceAssignment.resident_id == resident_id,
                DeviceAssignment.valid_from <= day,
                or_(DeviceAssignment.valid_to.is_(None), DeviceAssignment.valid_to >= day),
            )
        ).first()

    def residents_on_device(self, device_id: uuid.UUID, day: date) -> list[Resident]:
        """Residents assigned to the device on `day`, in `resident_code` order (shared devices)."""
        return list(
            self.session.scalars(
                select(Resident)
                .join(DeviceAssignment, DeviceAssignment.resident_id == Resident.id)
                .where(
                    DeviceAssignment.device_id == device_id,
                    DeviceAssignment.valid_from <= day,
                    or_(DeviceAssignment.valid_to.is_(None), DeviceAssignment.valid_to >= day),
                )
                .order_by(Resident.resident_code)
            ).all()
        )
