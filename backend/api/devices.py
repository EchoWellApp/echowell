"""Router for E-17 `GET /api/v1/devices` (TRD 05 API-086; FEAT-029)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.api.deps import (
    Pagination,
    Principal,
    authorize,
    get_db,
    get_pagination,
    get_read_context,
)
from backend.api.responses import errors
from backend.schemas.devices import DeviceList
from backend.services import device_service
from backend.services.resident_service import ReadContext

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get("", response_model=DeviceList, operation_id="listDevices", responses=errors(401))
def list_devices(
    _: Annotated[Principal, Depends(authorize("GET /devices"))],
    session: Annotated[Session, Depends(get_db)],
    ctx: Annotated[ReadContext, Depends(get_read_context)],
    page: Annotated[Pagination, Depends(get_pagination)],
) -> DeviceList:
    body = device_service.panel(session, ctx, limit=page.limit, offset=page.offset)
    return DeviceList.model_validate(body)
