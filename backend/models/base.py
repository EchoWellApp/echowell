"""Declarative base, Python enums and PostgreSQL enum types (TRD 20 §4.4, §4.9; TRD 23 DME-003).

Re-exported by `backend.models`; kept in its own module so model modules import it without an
import cycle.
"""

from __future__ import annotations

from enum import StrEnum

from sqlalchemy import MetaData
from sqlalchemy.dialects.postgresql import ENUM
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION = {
    "pk": "%(table_name)s_pkey",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
}


class Base(DeclarativeBase):
    """Declarative base whose metadata Alembic compares against (TRD 06 DB-012)."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


# The 19 acoustic feature keys in SRC-05 column order (TRD 20 PGS-009; names are placeholders,
# OQ-03) and the 7 composite z keys of `scores.z` (PGS-032).
FEATURE_KEYS: tuple[str, ...] = (
    "loudness_dbfs",
    "total_phrase_duration_s",
    "speech_rate_syl_per_s",
    "articulation_rate_syl_per_s",
    "number_of_pauses",
    "pause_fraction",
    "voiced_fraction",
    "mean_f0_hz",
    "f0_variability_st",
    "jitter_local_pct",
    "shimmer_local_pct",
    "hnr_db",
    "cpps_db",
    "alpha_ratio_db",
    "hammarberg_index_db",
    "mfcc1",
    "mfcc2",
    "mfcc3",
    "mfcc4",
)
COMPOSITE_FEATURE_KEYS: tuple[str, ...] = FEATURE_KEYS[:7]
COMPOSITE_Z_KEYS: tuple[str, ...] = tuple(f"z_{key}" for key in COMPOSITE_FEATURE_KEYS)


def sql_list(values: tuple[str, ...]) -> str:
    """`'a','b'` for CHECK constraints built from the key tuples above."""
    return ",".join(f"'{value}'" for value in values)


class ResidentCohort(StrEnum):
    LONGITUDINAL = "longitudinal"
    NEW_ADMISSION = "new_admission"


class ResidentStatus(StrEnum):
    ACTIVE = "active"
    WITHDRAWN = "withdrawn"


class IngestSource(StrEnum):
    API_SINGLE = "api_single"
    API_BATCH = "api_batch"
    CSV_UPLOAD = "csv_upload"
    SEED = "seed"


class SessionStatus(StrEnum):
    USABLE = "usable"
    SET_ASIDE = "set_aside"
    QUARANTINED = "quarantined"
    DUPLICATE = "duplicate"


class DayStatus(StrEnum):
    CHECKED_IN = "checked_in"
    MISSING_RESIDENT = "missing_resident"
    MISSING_DEVICE_GAP = "missing_device_gap"


class AlarmState(StrEnum):
    OFF = "off"
    RINGS = "rings"
    ON = "on"


class AlertStatus(StrEnum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    CLOSED = "closed"


class NoteType(StrEnum):
    OBSERVATION = "observation"
    ACTION_TAKEN = "action_taken"
    FOLLOW_UP = "follow_up"


class PipelineTrigger(StrEnum):
    INGEST = "ingest"
    NIGHTLY = "nightly"
    MANUAL = "manual"
    TEST = "test"


class PipelineRunStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class UserRole(StrEnum):
    ADMIN = "admin"
    CLINICIAN = "clinician"
    RESEARCHER = "researcher"


class ActorType(StrEnum):
    USER = "user"
    API_KEY = "api_key"
    SYSTEM = "system"


class ReviewOutcome(StrEnum):
    NO_CONCERN = "no_concern"
    KNOWN_CAUSE = "known_cause"
    REFERRED = "referred"
    DATA_PROBLEM = "data_problem"


class DataAlertKind(StrEnum):
    BASELINE_STALLED = "baseline_stalled"
    POSSIBLE_OTHER_SPEAKER = "possible_other_speaker"
    HIGH_SET_ASIDE = "high_set_aside"
    DEVICE_SILENT = "device_silent"
    REVIEW_FLAGGED_DATA_PROBLEM = "review_flagged_data_problem"


class DataAlertStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"


def _pg_enum(enum_cls: type[StrEnum], name: str) -> ENUM:
    return ENUM(
        enum_cls,
        name=name,
        create_type=False,
        values_callable=lambda members: [m.value for m in members],
    )


# TRD 20 §4.4, in the listed order (PGS-005).
RESIDENT_COHORT = _pg_enum(ResidentCohort, "resident_cohort")
RESIDENT_STATUS = _pg_enum(ResidentStatus, "resident_status")
INGEST_SOURCE = _pg_enum(IngestSource, "ingest_source")
SESSION_STATUS = _pg_enum(SessionStatus, "session_status")
DAY_STATUS = _pg_enum(DayStatus, "day_status")
ALARM_STATE = _pg_enum(AlarmState, "alarm_state")
ALERT_STATUS = _pg_enum(AlertStatus, "alert_status")
NOTE_TYPE = _pg_enum(NoteType, "note_type")
PIPELINE_TRIGGER = _pg_enum(PipelineTrigger, "pipeline_trigger")
PIPELINE_RUN_STATUS = _pg_enum(PipelineRunStatus, "pipeline_run_status")
USER_ROLE = _pg_enum(UserRole, "user_role")
ACTOR_TYPE = _pg_enum(ActorType, "actor_type")
REVIEW_OUTCOME = _pg_enum(ReviewOutcome, "review_outcome")
DATA_ALERT_KIND = _pg_enum(DataAlertKind, "data_alert_kind")
DATA_ALERT_STATUS = _pg_enum(DataAlertStatus, "data_alert_status")

PG_ENUMS: tuple[ENUM, ...] = (
    RESIDENT_COHORT,
    RESIDENT_STATUS,
    INGEST_SOURCE,
    SESSION_STATUS,
    DAY_STATUS,
    ALARM_STATE,
    ALERT_STATUS,
    NOTE_TYPE,
    PIPELINE_TRIGGER,
    PIPELINE_RUN_STATUS,
    USER_ROLE,
    ACTOR_TYPE,
    REVIEW_OUTCOME,
    DATA_ALERT_KIND,
    DATA_ALERT_STATUS,
)
