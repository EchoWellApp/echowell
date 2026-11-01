"""Pure EchoWell analytics engine (TRD 07 ANL-001..ANL-005, ANL-009; TRD 01 ARC-013).

No database, HTTP, clock, randomness or file I/O. `run_pipeline` is the single entry point for
every run; the backend reads `build_analytics_summary` and `leaning_most` on request (D-79).
"""

from analytics.config import (
    COMPOSITE_KEYS,
    ENGINE_VERSION,
    FEATURE_KEYS,
    FEATURES,
    PRODUCTION,
    TEST_V0_1,
    AdjustedRecord,
    AlertEvent,
    AnalyticsError,
    AnalyticsSummary,
    Baseline,
    BaselineMembership,
    ConfigError,
    ContractError,
    DataAlert,
    DeviceAssignment,
    EpochedRecord,
    EpochKey,
    EpochSummary,
    FeatureSpec,
    LedgerDay,
    OperationalConfig,
    PipelineConfig,
    PipelineResult,
    RawRecord,
    ResidentInfo,
    ReviewExplanation,
    RobustStats,
    RunWarning,
    ScoreRow,
    ScreenedRecord,
)
from analytics.pipeline import run_pipeline

__all__ = [
    "COMPOSITE_KEYS", "ENGINE_VERSION", "FEATURES", "FEATURE_KEYS", "PRODUCTION", "TEST_V0_1",
    "AdjustedRecord", "AlertEvent", "AnalyticsError", "AnalyticsSummary", "Baseline",
    "BaselineMembership", "ConfigError", "ContractError", "DataAlert", "DeviceAssignment",
    "EpochKey", "EpochSummary", "EpochedRecord", "FeatureSpec", "LedgerDay", "OperationalConfig",
    "PipelineConfig", "PipelineResult", "RawRecord", "ResidentInfo", "ReviewExplanation",
    "RobustStats", "RunWarning", "ScoreRow", "ScreenedRecord", "run_pipeline",
]  # fmt: skip
