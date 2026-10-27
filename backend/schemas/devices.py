"""Device DTOs of TRD 19 §4.5 (`Device`, `DeviceList`)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated

from pydantic import Field

from backend.schemas.common import CODE_PATTERN, PageMeta, ResponseModel

DeviceCode = Annotated[str, Field(pattern=CODE_PATTERN, examples=["D07B"])]


class Device(ResponseModel):
    device_code: DeviceCode
    room_label: str | None = Field(description="non-identifying label only")
    active: bool
    resident_codes: list[str]
    shared: bool
    replaces_device_code: str | None
    replaced_by_device_code: str | None
    in_use_since: date | None
    in_use_until: date | None = Field(
        description="last local day of the device's last assignment; null while it has a current "
        "assignment"
    )
    last_upload_at: datetime | None
    last_upload_local: datetime | None
    firmware_version: str | None
    uploaded_on_as_of_date: bool
    silent_days_last_30: list[date]
    device_gap_days_last_30: list[date]


class DeviceList(PageMeta):
    items: list[Device]
