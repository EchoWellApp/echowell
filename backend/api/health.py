"""Router for E-01 `GET /api/v1/health` (TRD 05 §4.12, TRD 19 E-01)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import Engine

from backend.api.deps import get_engine, get_settings
from backend.core.config import Settings
from backend.schemas.health import Health
from backend.services import health_service

router = APIRouter(tags=["health"])


@router.get("/health", response_model=Health, responses={503: {"model": Health}})
def health(
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
    engine: Annotated[Engine, Depends(get_engine)],
) -> Health:
    result = health_service.get_health(settings, engine)
    if result.status != "ok":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return result
