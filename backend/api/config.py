"""Router for E-32 `GET /api/v1/config/ui` (TRD 05 API-137, §4.12; FEAT-030)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.api.deps import Principal, authorize, get_db, get_read_context, get_settings
from backend.api.responses import errors
from backend.core.config import Settings
from backend.schemas.alerts import UiConfig
from backend.services import config_service
from backend.services.resident_service import ReadContext

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/ui", response_model=UiConfig, operation_id="getUiConfig", responses=errors(401))
def get_ui_config(
    _: Annotated[Principal, Depends(authorize("GET /config/ui"))],
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    ctx: Annotated[ReadContext, Depends(get_read_context)],
) -> UiConfig:
    return UiConfig.model_validate(
        config_service.ui_config(session, settings.pipeline_profile, ctx.meta)
    )
