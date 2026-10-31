"""The device panel (TRD 05 API-086; TRD 19 E-17; TRD 23 §4.4.2; TRD 06 DB-044, DB-066;
FEAT-029)."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlalchemy.orm import Session

from backend.repositories import read_models as rm
from backend.repositories.device_repository import DeviceRepository
from backend.services.resident_service import ReadContext, natural_key


def _neighbours(rows: list[rm.AssignmentRow], device_code: str) -> tuple[str | None, str | None]:
    """The device before and after this one in its residents' assignment histories (FR-155)."""
    replaces = replaced_by = None
    by_resident: dict[str, list[rm.AssignmentRow]] = {}
    for row in rows:
        by_resident.setdefault(row.resident_code, []).append(row)
    for history in by_resident.values():
        for i, row in enumerate(history):
            if row.device_code != device_code:
                continue
            if i > 0 and history[i - 1].device_code != device_code and replaces is None:
                replaces = history[i - 1].device_code
            if i + 1 < len(history) and history[i + 1].device_code != device_code:
                replaced_by = history[i + 1].device_code
    return replaces, replaced_by


def panel(session: Session, ctx: ReadContext, *, limit: int, offset: int) -> dict[str, Any]:
    """`DeviceList`: every device, active and retired, in natural code order (TRD 19 E-17)."""
    devices = sorted(DeviceRepository(session).list_all(), key=lambda d: natural_key(d.device_code))
    page = devices[offset : offset + limit]
    ids = [d.id for d in page]
    history = rm.assignments(session)
    uploads = rm.last_upload(session, ids)
    uploaded_today = rm.devices_uploaded_on(session, ids, ctx.as_of_date, ctx.tz.key)
    window = rm.Window(ctx.as_of_date - timedelta(days=rm.WINDOW_DAYS - 1), ctx.as_of_date)
    items = []
    for device in page:
        on_date = [
            row.resident_code
            for row in history
            if row.device_code == device.device_code
            and row.valid_from <= ctx.as_of_date
            and (row.valid_to is None or row.valid_to >= ctx.as_of_date)
        ]
        replaces, replaced_by = _neighbours(history, device.device_code)
        use = rm.device_use(session, device.id, ctx.as_of_date)
        silent = rm.device_silent_days(session, device.id, window)
        items.append(
            {
                "device_code": device.device_code,
                "room_label": device.room_label,
                "active": device.active,
                "resident_codes": sorted(set(on_date), key=natural_key),
                "shared": len(set(on_date)) >= ctx.shared_device_min_residents,
                "replaces_device_code": replaces,
                "replaced_by_device_code": replaced_by,
                "in_use_since": use.in_use_since,
                "in_use_until": use.in_use_until,
                "last_upload_at": uploads.get(device.id),
                "last_upload_local": ctx.local(uploads.get(device.id)),
                "firmware_version": device.firmware_version_last,
                "uploaded_on_as_of_date": device.id in uploaded_today,
                "silent_days_last_30": [
                    day for day in silent if use.in_use_since and day >= use.in_use_since
                ],
                "device_gap_days_last_30": rm.device_gap_days(session, device.id, window),
            }
        )
    return {
        "meta": ctx.meta,
        "items": items,
        "total": len(devices),
        "limit": limit,
        "offset": offset,
    }
