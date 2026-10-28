"""JSON column shapes (TRD 23 §4.5; PGS-032, PGS-033; FEAT-011-FR-12)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.models import COMPOSITE_Z_KEYS, FEATURE_KEYS
from backend.schemas import json_columns as jc

pytestmark = pytest.mark.unit


@pytest.mark.req("PGS-033")
def test_adjusted_features_need_exactly_the_19_keys() -> None:
    values = dict.fromkeys(FEATURE_KEYS, 1)
    assert jc.adjusted_features_json(values) == dict.fromkeys(FEATURE_KEYS, 1.0)
    with pytest.raises(ValueError, match="exactly the 19"):
        jc.adjusted_features_json({**values, "extra": 1})
    with pytest.raises(ValueError, match="exactly the 19"):
        jc.adjusted_features_json({k: v for k, v in values.items() if k != "mfcc4"})


@pytest.mark.req("PGS-032", "FEAT-011-AC-07")
def test_score_z_needs_the_composite_keys() -> None:
    z = dict.fromkeys(COMPOSITE_Z_KEYS, 0.5)
    assert jc.score_z_json({**z, "z_mfcc1": 1}) == {**z, "z_mfcc1": 1.0}
    with pytest.raises(ValueError, match="z_voiced_fraction"):
        jc.score_z_json({k: v for k, v in z.items() if k != "z_voiced_fraction"})


@pytest.mark.req("TRD-23-4.5")
def test_scope_shapes() -> None:
    assert jc.scope_json({"type": "all"}) == {"type": "all"}
    residents = {"type": "residents", "resident_codes": ["R01"]}
    assert jc.scope_json(residents) == residents
    with pytest.raises(ValidationError):
        jc.scope_json({"type": "residents", "resident_codes": []})
    with pytest.raises(ValidationError):
        jc.scope_json({"type": "some"})


@pytest.mark.req("FR-028")
def test_ingest_errors_must_be_a_non_empty_list() -> None:
    error = {"field": "mean_f0_hz", "code": "out_of_range", "message": "must be > 0"}
    assert jc.ingest_errors_json([error]) == [error]
    with pytest.raises(ValidationError):
        jc.ingest_errors_json([])


@pytest.mark.req("TRD-23-4.5")
def test_counts_and_snapshot() -> None:
    counts = dict.fromkeys(jc.PIPELINE_COUNT_KEYS, 0)
    assert jc.counts_json(counts) == counts
    with pytest.raises(ValidationError):
        jc.counts_json({**counts, "unknown": 1})
    with pytest.raises(ValueError, match="JSON object"):
        jc.config_snapshot_json(["baseline_n"])
