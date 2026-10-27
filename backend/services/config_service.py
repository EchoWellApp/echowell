"""UI configuration of the review form (TRD 05 API-137; TRD 19 E-32; FEAT-030)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from backend.repositories.config_repository import ConfigRepository
from backend.schemas.common import Meta


def ui_config(session: Session, profile: str, meta: Meta) -> dict[str, Any]:
    """Read on every request, so a `set-config` change applies at once (ENV-020, D-56)."""
    values = ConfigRepository(session).values_for_profile(profile)
    return {
        "meta": meta,
        "alert_snooze_hours": int(values["alert_snooze_hours"]),
        "review_explanations": [
            {"code": item["code"], "label": item["label"]}
            for item in values.get("review_explanations") or []
        ],
    }
