"""PipelineConfig, profiles, contracts and errors (TRD 07 §4.3-§4.4, §4.7, §4.11; FEAT-040)."""

from __future__ import annotations

import dataclasses
import json
from typing import Any

import pytest

from analytics import config as cfg
from tests.unit.analytics.factory import rec

pytestmark = pytest.mark.unit


@pytest.mark.req("ANL-028", "FEAT-040-FR-04", "CFG-01", "CFG-02")
def test_profiles_differ_only_in_profile_and_baseline_n() -> None:
    test, prod = cfg.TEST_V0_1.values(), cfg.PRODUCTION.values()
    assert (test["baseline_n"], prod["baseline_n"]) == (16, 30)
    assert {k for k in test if test[k] != prod[k]} == {"profile", "baseline_n"}
    assert cfg.TEST_V0_1.cusum_h == 5.0
    assert cfg.TEST_V0_1.operational.data_alert_set_aside_fraction == 0.20
    assert cfg.TEST_V0_1.operational.review_explanations[0].code == "cold_cough_sore_throat"


@pytest.mark.req("FEAT-040-FR-03", "DME-002")
def test_feature_constants() -> None:
    assert len(cfg.FEATURE_KEYS) == 19
    assert cfg.FEATURE_KEYS[-1] == "mfcc4"
    assert cfg.FEATURE_KEYS[:7] == cfg.COMPOSITE_KEYS
    assert cfg.COMPOSITE_SIGNS == {
        "loudness_dbfs": -1, "total_phrase_duration_s": 1, "speech_rate_syl_per_s": -1,
        "articulation_rate_syl_per_s": -1, "number_of_pauses": 1, "pause_fraction": 1,
        "voiced_fraction": -1,
    }  # fmt: skip
    pauses = cfg.FEATURES[4]
    assert (pauses.key, pauses.spread_floor, pauses.in_composite) == ("number_of_pauses", 0.5, True)
    assert cfg.TEST_V0_1.morning_offsets["loudness_dbfs"] == -1.5


def _values(**changes: Any) -> dict[str, Any]:
    return {**cfg.TEST_V0_1.values(), **changes}


@pytest.mark.req("ANL-029", "CFG-03", "FEAT-040-AC-04", "FEAT-040-FR-05")
@pytest.mark.parametrize(
    ("changes", "key"),
    [
        ({"cusum_h": 0}, "cusum_h"),
        ({"foo": 1}, "foo"),
        ({"morning_offsets": {k: 0.0 for k in cfg.FEATURE_KEYS[:-1]}}, "morning_offsets"),
        ({"screen_min_n": 20}, "baseline_n"),
        ({"mad_scale": 0}, "mad_scale"),
        ({"facility_tz": "Mars/Base"}, "facility_tz"),
        ({"data_alert_set_aside_fraction": 0}, "data_alert_set_aside_fraction"),
        ({"alert_snooze_hours": 169}, "alert_snooze_hours"),
        ({"baseline_n": 16.0}, "baseline_n"),
        ({"review_explanations": [{"code": "A", "label": "x"}]}, "review_explanations"),
        ({"review_explanations": []}, "review_explanations"),
    ],
)
def test_from_mapping_refuses(changes: dict[str, Any], key: str) -> None:
    with pytest.raises(cfg.ConfigError, match=key):
        cfg.PipelineConfig.from_mapping(_values(**changes))


@pytest.mark.req("ANL-029")
def test_missing_key_is_refused() -> None:
    values = _values()
    del values["cusum_k"]
    with pytest.raises(cfg.ConfigError, match="cusum_k"):
        cfg.PipelineConfig.from_mapping(values)


@pytest.mark.req("ANL-030", "CFG-04", "FEAT-040-AC-05", "FEAT-040-FR-06", "D-56")
def test_hash_covers_algorithm_keys_only() -> None:
    base = cfg.TEST_V0_1.config_hash()
    snooze = cfg.PipelineConfig.from_mapping(_values(alert_snooze_hours=48))
    tighter = cfg.PipelineConfig.from_mapping(_values(cusum_h=4.0))
    assert snooze.config_hash() == base
    assert tighter.config_hash() != base
    snap = cfg.TEST_V0_1.snapshot()
    assert json.loads(json.dumps(snap)) == snap
    assert len(base) == 64
    assert cfg.PipelineConfig.from_mapping(cfg.TEST_V0_1.values()) == cfg.TEST_V0_1


@pytest.mark.req("ANL-010", "ANL-013", "FEAT-040-AC-07", "FEAT-040-FR-01", "FEAT-040-FR-02")
def test_contracts_are_frozen_and_check_features() -> None:
    record = rec(1, "2026-10-01 19:00:00")
    with pytest.raises(dataclasses.FrozenInstanceError):
        record.session_id = "x"  # type: ignore[misc]
    features = dict(record.features)
    del features["mfcc4"]
    with pytest.raises(cfg.ContractError):
        dataclasses.replace(record, features=features)
    reordered = dict(reversed(list(record.features.items())))
    with pytest.raises(cfg.ContractError):
        dataclasses.replace(record, features=reordered)
    with pytest.raises(cfg.ContractError):
        dataclasses.replace(record, timestamp_utc=record.timestamp_utc.replace(tzinfo=None))


@pytest.mark.req("ANL-051", "ANL-052", "FEAT-040-FR-10")
def test_errors_and_warning_codes() -> None:
    assert issubclass(cfg.ContractError, cfg.AnalyticsError)
    assert issubclass(cfg.ConfigError, cfg.AnalyticsError)
    codes = cfg.ENGINE_WARNING_CODES + cfg.RUNNER_WARNING_CODES + cfg.FAILURE_CODES
    assert all(code == code.lower() for code in codes)
    assert "late_arrival" in cfg.ENGINE_WARNING_CODES
    assert "exception" in cfg.RUNNER_WARNING_CODES
