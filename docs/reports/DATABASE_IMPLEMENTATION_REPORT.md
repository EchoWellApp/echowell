# Database Implementation Report

Block 3 checkpoint 3 · Prompt: `specs/prompts/Implement_Feature_Batches.md` "Phase 9: Implement Database Layer" · TRD 25 Phase 4 · Features FEAT-008..FEAT-017 · Branch `feat/cp3-database` · Date: 26 October 2026

This report answers requirement 7 of the Phase 9 prompt. The process report (commands run, exit criteria, deviations and reviewer questions) is `docs/reports/CHECKPOINT_3_DATABASE.md`.

The database holds synthetic test data only. No real resident data may be loaded until the AWS environment is approved.

## 1. Summary

| Prompt item | Delivered | Where |
|---|---|---|
| SQLAlchemy models | 24 mapped tables plus the 15 PostgreSQL enum types, generated from the TRD 20 DDL; `alembic check` finds no difference between models and migrations | `backend/models/` |
| Database connection layer | One engine per URL with the API-125 pool settings, TLS refusal outside local/test, the migrator connection (`SET ROLE echowell_migrator`), transaction-scoped advisory-lock helper | `backend/core/db.py` |
| Repository layer | 19 repository classes, one per aggregate, plus the read-model derivations of TRD 06 / DME-012 | `backend/repositories/` |
| Alembic migrations | `0001_initial_schema` (TRD 20 §4.4–§4.8 verbatim) and `0002_seed_config_parameters` (TRD 20 §4.11, 46 rows) | `backend/alembic/versions/` |
| Database configuration | Settings already existed (FEAT-003); this checkpoint adds role setup, lock and statement timeouts for the migrator, the migration advisory lock and the regenerated `database/schema.sql` | `backend/alembic/env.py`, `scripts/dump_schema.sh` |
| Seed framework | Operator CLI `seed test_v0_1 [--master-only] [--reset]`, `reset-test-db`, `bootstrap`, `import-master-data`; the test_v0_1 roster CSV files | `backend/cli.py`, `database/seeds/test_v0_1/` |
| Residents, Devices, RawSessions, ProcessedSessions, Baselines, Scores, CusumState, Alerts, Users, AuditLogs | All ten, with the other 14 tables of TRD 20 §4.6 | see section 2 |
| Tables match the documented schema | The migration contains the TRD 20 SQL unchanged; `tests/integration/test_schema_reference.py` compares a `pg_dump` of the migrated database with `database/schema.sql` | AC-PGS-11 |
| Relationships | 51 foreign keys; ORM relationships where a caller navigates them (section 3) | |
| Primary and foreign keys enforced | 25 primary keys (24 tables and `alembic_version`), 51 foreign keys, all `ON DELETE RESTRICT` except `scores → processed_sessions` (`CASCADE`) | AC-PGS-13 |
| Indexes | Every index of TRD 20 §4.7, checked definition by definition against the TRD text; every foreign-key column of DB-047 leads an index | `tests/integration/db/test_indexes.py` |
| Unit tests | 6 new unit modules and 16 new integration modules (section 5) | `tests/` |
| Backlog completion status | `BACKLOG.md` §10, feature-file Status fields and roadmap §2.1 refreshed (D-104) | |

No API endpoint was added; `backend/api/` only switched to the new engine helper.

## 2. Tables

The 24 tables of TRD 20 §4.6, in creation order. "App grants" are the rights of `echowell_app` (TRD 20 §4.8); every table is owned by `echowell_migrator` and readable by `echowell_readonly`, except the credential columns `users.password_hash` and `api_keys.key_hash`.

| Table | Model (file) | Repository | App grants | Feature |
|---|---|---|---|---|
| `facilities` | `Facility` (`facility.py`) | `FacilityRepository` | SELECT, INSERT, UPDATE | FEAT-009 |
| `users` | `User` (`user.py`) | `UserRepository` | SELECT, INSERT, UPDATE | FEAT-009 |
| `residents` | `Resident` (`resident.py`) | `ResidentRepository` | SELECT, INSERT, UPDATE | FEAT-009 |
| `devices` | `Device` (`device.py`) | `DeviceRepository` | SELECT, INSERT, UPDATE | FEAT-009 |
| `device_assignments` | `DeviceAssignment` (`device.py`) | `DeviceRepository` | SELECT, INSERT, UPDATE | FEAT-009 |
| `api_keys` | `ApiKey` (`api_key.py`) | `ApiKeyRepository` | SELECT, INSERT, UPDATE | FEAT-009 |
| `ingest_batches` | `IngestBatch` (`ingest_batch.py`) | `IngestRepository` | SELECT, INSERT, UPDATE | FEAT-010 |
| `ingest_rejections` | `IngestRejection` (`ingest_batch.py`) | `IngestRepository` | SELECT, INSERT | FEAT-010 |
| `raw_sessions` | `RawSession` (`session.py`) | `RawSessionRepository` (insert-only) | SELECT, INSERT; trigger blocks UPDATE/DELETE/TRUNCATE | FEAT-010 |
| `pipeline_runs` | `PipelineRun` (`pipeline_run.py`) | `PipelineRunRepository` | SELECT, INSERT, UPDATE | FEAT-011 |
| `epochs` | `Epoch` (`epoch.py`) | `EpochRepository` | SELECT, INSERT, UPDATE, DELETE | FEAT-011 |
| `processed_sessions` | `ProcessedSession` (`session.py`) | `ProcessedSessionRepository` | SELECT, INSERT, UPDATE, DELETE | FEAT-011 |
| `day_ledger` | `DayLedgerEntry` (`day_ledger.py`) | `DayLedgerRepository` | SELECT, INSERT, UPDATE, DELETE | FEAT-011 |
| `baselines` | `Baseline` (`baseline.py`) | `BaselineRepository` | SELECT, INSERT | FEAT-011 |
| `scores` | `Score` (`score.py`) | `ScoreRepository` | SELECT, INSERT, UPDATE, DELETE | FEAT-011 |
| `cusum_state` | `CusumState` (`score.py`) | `ScoreRepository` | SELECT, INSERT, UPDATE, DELETE | FEAT-011 |
| `alerts` | `Alert` (`alarm.py`) | `AlertRepository` | SELECT, INSERT, UPDATE | FEAT-012 |
| `alert_reviews` | `AlertReview` (`alarm.py`) | `AlertRepository` | SELECT, INSERT | FEAT-012 |
| `data_alerts` | `DataAlert` (`alarm.py`) | `DataAlertRepository` | SELECT, INSERT, UPDATE | FEAT-012 |
| `staff_notes` | `StaffNote` (`staff_note.py`) | `StaffNoteRepository` | SELECT, INSERT | FEAT-012 |
| `facility_reference_ranges` | `FacilityReferenceRange` (`reference_range.py`) | `ReferenceRangeRepository` | SELECT, INSERT, UPDATE, DELETE | FEAT-012 |
| `config_parameters` | `ConfigParameter` (`config_parameter.py`) | `ConfigRepository` | SELECT, INSERT, UPDATE | FEAT-009 |
| `audit_logs` | `AuditLog` (`audit_log.py`) | `AuditRepository` (through `audit_service`) | SELECT, INSERT; trigger blocks UPDATE/DELETE/TRUNCATE | FEAT-012, FEAT-015 |
| `evaluation_ground_truth` | `EvaluationGroundTruth` (`evaluation.py`) | none (no application code reads it) | none | FEAT-012 |

Catalogue counts on the migrated database: 86 CHECK, 51 FOREIGN KEY, 25 PRIMARY KEY, 16 UNIQUE and 1 EXCLUDE constraints; 103 indexes (constraint indexes included); 17 triggers (4 append-only, 13 `updated_at`); 15 enum types.

## 3. Relationships

All 51 foreign keys of TRD 20 are in the DDL and in the models (`ForeignKey(..., ondelete=...)`). ORM `relationship()` attributes are declared where code navigates them:

| From | To | Use |
|---|---|---|
| `Device.assignments` ↔ `DeviceAssignment.device`; `Resident.assignments` ↔ `DeviceAssignment.resident` | | device label, shared device, `in_use_until` |
| `Alert.reviews` ↔ `AlertReview.alert` | | alert history (CUS-017) |
| `IngestBatch.rejections` ↔ `IngestRejection.batch` | | ingest batch detail |
| `ProcessedSession.raw_session` | `RawSession` | provenance of a processed row |
| `ProcessedSession.score` ↔ `Score.processed_session` | | one score per usable session (`scores_processed_session_uq`) |
| `Epoch.baselines` (view-only) | `Baseline` | baseline state per epoch |
| `StaffNote.supersedes` | `StaffNote` | note corrections (PGS-042) |

Other foreign keys are used through repository queries rather than attributes, so the models do not load rows the caller does not ask for.

## 4. Rules enforced by the database

| Rule | Mechanism | Test |
|---|---|---|
| Raw sessions and audit rows are never changed | `reject_mutation()` triggers (SQLSTATE `EW001`) plus grants (42501); one escape hatch for the IRB purge (`echowell_migrator` with `echowell.allow_purge = 'on'`, DELETE only) | AC-PGS-01, 02, 03, 09 |
| Reviews and notes are append-only | grants (no UPDATE or DELETE for the app) | FEAT-012-AC-07 |
| One device per resident per day; shared devices allowed | `EXCLUDE USING gist` on `(resident_id, daterange)` | AC-PGS-08 |
| One open epoch per resident; one non-closed alert per epoch; one open data alert per subject | partial unique indexes | PGS-029, PGS-030, AC-PGS-15 |
| Processed-session status and reason wording | CHECK constraints on `reasons`, `reason_text`, `screen_detail`, `epoch_id`, `baseline_ordinal`, `adjusted_features` | AC-PGS-04..06, D-57 |
| Day ledger wording | CHECK on `status` and `reason` | AC-PGS-07 |
| Answer key never reaches the pipeline | no app privilege on `evaluation_ground_truth`; the app login cannot `SET ROLE echowell_readonly` | AC-PGS-14 |
| Credentials | e-mail lower case, argon2id hashes, 64-char lower-case hex API-key hashes, known scopes only | FEAT-009-AC-03, AC-04 |

## 5. Tests

| Level | Modules | Tests |
|---|---|---|
| Unit | `tests/unit/backend/core/test_db.py`, `core/test_security.py`, `services/test_audit.py`, `schemas/test_json_columns.py`, `repositories/test_raw_session_repository.py`, `test_db_inspection.py` | 48 |
| Integration (database) | `tests/integration/db/` (11 modules), `test_schema_behaviour.py`, `test_schema_reference.py` | 91 |
| Integration (CLI) | `test_cli_credentials.py`, `test_cli_seed.py` | 13 |

Full suite on this branch: 190 passed, 2 skipped (TST-011 until Phase 6; the FEAT-014 seed-valued case until FEAT-055). Branch coverage of `analytics` and `backend` is 93 %. Every test runs against PostgreSQL 16, either through the CI service container or a testcontainers `postgres:16-alpine`; both paths were run.

## 6. Backlog status

FEAT-008..FEAT-017 are set to Complete in `BACKLOG.md` §10, in their feature files and in the roadmap §2.1 cell (D-104). One part is deferred: the FEAT-014 acceptance values stated on the full test_v0_1 seed (AC-01, AC-06 and AC-07 numbers) need the session seed of FEAT-055 (checkpoint 5); the same derivations are verified now on hand-built rows. See question Q-4 in the checkpoint report.
