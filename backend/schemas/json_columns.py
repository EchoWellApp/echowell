"""Shapes of the JSON columns, validated before insert (TRD 23 §4.5; DME-013; FEAT-011-FR-12).

Each `*_json` helper validates a Python value against its shape and returns the plain JSON value
that is stored. Floats stay Python floats without rounding (DME-014).
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt, TypeAdapter

from backend.models import COMPOSITE_Z_KEYS, FEATURE_KEYS

_STRICT = ConfigDict(extra="forbid", strict=True)

# The exact `pipeline_runs.counts` keys (DB-020); `db_size_bytes` only on nightly runs (DB-049).
PIPELINE_COUNT_KEYS: tuple[str, ...] = (
    "arrivals",
    "usable",
    "set_aside",
    "quarantined",
    "duplicate",
    "missing_resident",
    "missing_device_gap",
    "late_arrival",
    "scored",
    "alerts_opened",
    "excluded_after_as_of",
    "residents",
)


class IngestError(BaseModel):
    """One `{field, code, message}` item of `ingest_rejections.errors` (no `value`, ING-004)."""

    model_config = _STRICT
    field: str
    code: str
    message: str


class AllScope(BaseModel):
    model_config = _STRICT
    type: Literal["all"]


class ResidentsScope(BaseModel):
    model_config = _STRICT
    type: Literal["residents"]
    resident_codes: Annotated[list[str], Field(min_length=1)]


class PipelineWarning(BaseModel):
    """One `pipeline_runs.warnings` item."""

    model_config = _STRICT
    code: str
    resident_code: str | None
    session_id: str | None
    detail: str


class PipelineCounts(BaseModel):
    """`pipeline_runs.counts`: exactly the DB-020 keys, plus `db_size_bytes` on nightly runs."""

    model_config = _STRICT
    arrivals: StrictInt
    usable: StrictInt
    set_aside: StrictInt
    quarantined: StrictInt
    duplicate: StrictInt
    missing_resident: StrictInt
    missing_device_gap: StrictInt
    late_arrival: StrictInt
    scored: StrictInt
    alerts_opened: StrictInt
    excluded_after_as_of: StrictInt
    residents: StrictInt
    db_size_bytes: StrictInt | None = None


_Number = StrictFloat | StrictInt
_ingest_errors: TypeAdapter[list[IngestError]] = TypeAdapter(
    Annotated[list[IngestError], Field(min_length=1)]
)
_scope: TypeAdapter[AllScope | ResidentsScope] = TypeAdapter(
    Annotated[AllScope | ResidentsScope, Field(discriminator="type")]
)
_warnings = TypeAdapter(list[PipelineWarning])
_feature_values = TypeAdapter(dict[str, _Number])


def ingest_errors_json(errors: Any) -> list[dict[str, str]]:
    """`ingest_rejections.errors`: a non-empty list of `{field, code, message}`."""
    return [e.model_dump() for e in _ingest_errors.validate_python(errors)]


def scope_json(scope: Any) -> dict[str, Any]:
    """`pipeline_runs.scope`: `{"type": "all"}` or `{"type": "residents", "resident_codes": …}`."""
    return dict(_scope.validate_python(scope).model_dump())


def counts_json(counts: Any) -> dict[str, int]:
    return PipelineCounts.model_validate(counts).model_dump(exclude_none=True)


def warnings_json(warnings: Any) -> list[dict[str, Any]]:
    return [w.model_dump() for w in _warnings.validate_python(warnings)]


def config_snapshot_json(snapshot: Any) -> dict[str, Any]:
    """`pipeline_runs.config_snapshot`: a JSON object (23 keys plus `config_hash`, `as_of`)."""
    if not isinstance(snapshot, dict) or not all(isinstance(k, str) for k in snapshot):
        raise ValueError("config_snapshot must be a JSON object")
    return snapshot


def adjusted_features_json(features: Any) -> dict[str, float]:
    """`processed_sessions.adjusted_features`: exactly the 19 feature keys → numbers (PGS-033)."""
    values = _feature_values.validate_python(features)
    if set(values) != set(FEATURE_KEYS):
        raise ValueError("adjusted_features must contain exactly the 19 feature keys")
    return {key: float(values[key]) for key in FEATURE_KEYS}


def score_z_json(z: Any) -> dict[str, float]:
    """`scores.z`: at least the 7 composite z keys → numbers (PGS-032)."""
    values = _feature_values.validate_python(z)
    missing = set(COMPOSITE_Z_KEYS) - set(values)
    if missing:
        raise ValueError(f"scores.z is missing {sorted(missing)}")
    return {key: float(value) for key, value in values.items()}
