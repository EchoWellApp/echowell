"""SQLAlchemy 2.0 ORM models (TRD 23 §4.6; TRD 20 §4.4, §4.9; FEAT-008..FEAT-012).

This package exposes the declarative `Base`, the 15 PostgreSQL enum types (`create_type=False`:
the migrations create them, TRD 20 §8) and the `str`-valued Python enums that mirror them
(DME-003), defined in `backend.models.base`, and imports every model so that `Base.metadata` is
complete for Alembic (`alembic check`, PGS-023). Constraint and index names are declared
explicitly in each model (DB-012); the naming convention only reproduces PostgreSQL's default
primary-key and foreign-key names (TRD 20 §4.9).
"""

from __future__ import annotations

from backend.models.alarm import Alert, AlertReview, DataAlert
from backend.models.api_key import ApiKey
from backend.models.audit_log import AuditLog
from backend.models.base import (
    ACTOR_TYPE,
    ALARM_STATE,
    ALERT_STATUS,
    COMPOSITE_FEATURE_KEYS,
    COMPOSITE_Z_KEYS,
    DATA_ALERT_KIND,
    DATA_ALERT_STATUS,
    DAY_STATUS,
    FEATURE_KEYS,
    INGEST_SOURCE,
    NAMING_CONVENTION,
    NOTE_TYPE,
    PG_ENUMS,
    PIPELINE_RUN_STATUS,
    PIPELINE_TRIGGER,
    RESIDENT_COHORT,
    RESIDENT_STATUS,
    REVIEW_OUTCOME,
    SESSION_STATUS,
    USER_ROLE,
    ActorType,
    AlarmState,
    AlertStatus,
    Base,
    DataAlertKind,
    DataAlertStatus,
    DayStatus,
    IngestSource,
    NoteType,
    PipelineRunStatus,
    PipelineTrigger,
    ResidentCohort,
    ResidentStatus,
    ReviewOutcome,
    SessionStatus,
    UserRole,
    sql_list,
)
from backend.models.baseline import Baseline
from backend.models.config_parameter import ConfigParameter
from backend.models.day_ledger import DayLedgerEntry
from backend.models.device import Device, DeviceAssignment
from backend.models.epoch import Epoch
from backend.models.evaluation import EvaluationGroundTruth
from backend.models.facility import Facility
from backend.models.ingest_batch import IngestBatch, IngestRejection
from backend.models.pipeline_run import PipelineRun
from backend.models.reference_range import FacilityReferenceRange
from backend.models.resident import Resident
from backend.models.score import CusumState, Score
from backend.models.session import ProcessedSession, RawSession
from backend.models.staff_note import StaffNote
from backend.models.user import User

__all__ = [
    "ACTOR_TYPE",
    "ALARM_STATE",
    "ALERT_STATUS",
    "DATA_ALERT_KIND",
    "DATA_ALERT_STATUS",
    "DAY_STATUS",
    "INGEST_SOURCE",
    "NAMING_CONVENTION",
    "NOTE_TYPE",
    "PIPELINE_RUN_STATUS",
    "PIPELINE_TRIGGER",
    "RESIDENT_COHORT",
    "RESIDENT_STATUS",
    "REVIEW_OUTCOME",
    "SESSION_STATUS",
    "USER_ROLE",
    "COMPOSITE_FEATURE_KEYS",
    "COMPOSITE_Z_KEYS",
    "FEATURE_KEYS",
    "PG_ENUMS",
    "ActorType",
    "AlarmState",
    "Alert",
    "AlertReview",
    "AlertStatus",
    "ApiKey",
    "AuditLog",
    "Base",
    "Baseline",
    "ConfigParameter",
    "CusumState",
    "DataAlert",
    "DataAlertKind",
    "DataAlertStatus",
    "DayLedgerEntry",
    "DayStatus",
    "Device",
    "DeviceAssignment",
    "Epoch",
    "EvaluationGroundTruth",
    "Facility",
    "FacilityReferenceRange",
    "IngestBatch",
    "IngestRejection",
    "IngestSource",
    "NoteType",
    "PipelineRun",
    "PipelineRunStatus",
    "PipelineTrigger",
    "ProcessedSession",
    "RawSession",
    "Resident",
    "ResidentCohort",
    "ResidentStatus",
    "ReviewOutcome",
    "Score",
    "SessionStatus",
    "StaffNote",
    "User",
    "UserRole",
    "sql_list",
]
