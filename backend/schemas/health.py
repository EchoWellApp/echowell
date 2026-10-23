"""`Health` DTO of TRD 19 §4.5 (E-01)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class Health(BaseModel):
    status: Literal["ok", "degraded"]
    database: Literal["ok", "unavailable"]
    version: str
    time: datetime
