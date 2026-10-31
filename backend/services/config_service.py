"""UI configuration of the review form (TRD 05 API-137; TRD 19 E-32; FEAT-030) and the pipeline
configuration loader (TRD 07 ANL-031; FEAT-040-FR-07)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from sqlalchemy.orm import Session

from analytics.config import PRODUCTION, TEST_V0_1, ConfigError, PipelineConfig
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


# Read by the ingestion service, not by `PipelineConfig` (TRD 07 §4.7).
INGEST_KEYS = ("supported_schema_versions", "feature_name_map")
BUILT_IN = {"production": PRODUCTION, "test_v0_1": TEST_V0_1}


def pipeline_config(
    values: Mapping[str, Any], profile: str, facility_tz: str | None = None
) -> tuple[PipelineConfig, list[dict[str, Any]]]:
    """The profile's `config_parameters` rows as a `PipelineConfig` (ANL-031, FEAT-040-FR-07).

    A missing key takes the built-in constant's value with warning `config_default_used`; a
    `FACILITY_TZ` different from the profile's `facility_tz` gives `config_mismatch` and the
    profile value wins. No rows, an unknown profile or an invalid value raise `ConfigError`.
    """
    if not values or profile not in BUILT_IN:
        raise ConfigError(f"profile {profile}: no configuration rows")
    defaults = BUILT_IN[profile].values()
    given = {k: v for k, v in values.items() if k not in INGEST_KEYS}
    warnings = []
    for key in sorted(set(defaults) - set(given) - {"profile"}):
        given[key] = defaults[key]
        warnings.append(_warning("config_default_used", f"{key}: built-in value used"))
    config = PipelineConfig.from_mapping({**given, "profile": profile})
    if facility_tz and facility_tz != config.facility_tz:
        warnings.append(_warning(
            "config_mismatch",
            f"FACILITY_TZ {facility_tz} differs from the profile's {config.facility_tz}",
        ))  # fmt: skip
    return config, warnings


def _warning(code: str, detail: str) -> dict[str, Any]:
    return {"code": code, "resident_code": None, "session_id": None, "detail": detail}
