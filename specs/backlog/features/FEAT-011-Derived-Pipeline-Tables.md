# FEAT-011 Derived pipeline tables (pipeline_runs, epochs, processed_sessions, day_ledger, baselines, scores, cusum_state)

| Field | Value |
|---|---|
| Epic | Database |
| Build phase | Phase 4 (TRD 25) |
| Priority | P0 |
| Complexity | High |
| MVP status | Required |
| Dependencies | FEAT-010 |
| Status | Not Started |

## Purpose

Create the tables that hold every result the pipeline derives from `raw_sessions` — run metadata, epochs, per-arrival status, the resident-day ledger, frozen baselines, scores and CUSUM state — with database constraints strict enough that a defect in application code cannot persist an invalid status, reason, late-arrival combination, ledger reason or baseline key (DB-032). This is the persistence target of the analytics engine and the source of every read API.

## Business Context

- BR-02 and D-07: derived tables are fully rebuildable from the raw store and reference tables (DB-006, DB-019).
- BR-03..BR-05: each arrival's status (`usable`, `set_aside`, `quarantined`, `duplicate`) and reasons are stored with consistency CHECKs (PGS-012).
- BR-06: missing days are ledger rows only, with honest reasons (PGS-014).
- BR-08..BR-11: epochs, frozen baselines (20 rows per frozen resident-epoch), scores with 7 z values and CUSUM tally/alarm state (FR-051, FR-086, FR-094, FR-105).
- BR-15: values stored as float64 without rounding so the answer key compares at 1e-6 (DME-014).

## Referenced TRDs

- TRD 20 PGS-012..PGS-014, PGS-030..PGS-033; §4.6.10–§4.6.16 DDL; §4.7 (`epochs_current_uq`); §4.8 triggers and grants for these tables; §8 notes; AC-PGS-04..AC-PGS-07.
- TRD 06 DB-006, DB-016, DB-019, DB-020.
- TRD 23 DME-006, DME-010, DME-013, DME-014; §4.2.10–§4.2.16 entity definitions; §4.5 JSON column shapes; §4.3.1, §4.3.5, §4.3.6 state machines.
- TRD 02 FR-051, FR-086, FR-094, FR-105.
- TRD 13 TST-041, TST-042.
- TRD 24 D-57.

## Scope

- Migration 0001 sections for `pipeline_runs`, `epochs`, `processed_sessions`, `day_ledger`, `baselines`, `scores`, `cusum_state` exactly as TRD 20 §4.6.10–§4.6.16, including every named CHECK.
- Partial unique index `epochs_current_uq ON epochs (resident_id) WHERE ended_at IS NULL` (needed for PGS-030; the other §4.7 indexes of these tables are FEAT-013).
- Triggers `pipeline_runs_set_updated_at`, `epochs_set_updated_at`, `cusum_state_set_updated_at`.
- Grants per §4.8: `echowell_app` SELECT, INSERT, UPDATE on `pipeline_runs`; SELECT, INSERT only on `baselines`; SELECT, INSERT, UPDATE, DELETE on `epochs`, `processed_sessions`, `day_ledger`, `scores`, `cusum_state`; `echowell_readonly` SELECT on all seven.
- Pydantic validation models for the JSON columns (`pipeline_runs.scope`, `config_snapshot`, `counts`, `warnings`; `processed_sessions.adjusted_features`; `scores.z`) with the TRD 23 §4.5 shapes, applied before insert.
- Models (TRD 23 §4.6): `pipeline_run.py:PipelineRun`, `epoch.py:Epoch`, `session.py:ProcessedSession`, `day_ledger.py:DayLedgerEntry`, `baseline.py:Baseline` (existing file), `score.py:Score` and `CusumState` (existing file).
- Repositories with typed read methods (by resident, epoch, date range, run id; latest succeeded run) and plain insert/update/delete primitives. The per-resident delete/insert and upsert persistence logic is out of scope (FEAT-053).

## Out of Scope

- The pipeline runner's persistence transaction (delete/insert per resident, natural-key upserts, frozen-baseline loading, late-arrival warning) (FEAT-053) and the rebuild command that deletes baselines (FEAT-055).
- Analytics computations (FEAT-040..FEAT-052).
- Non-constraint indexes (FEAT-013); read-model derivations (FEAT-014).
- `alerts`, `data_alerts` and the other human-state tables (FEAT-012).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-011-FR-01 | The seven tables shall be created with exactly the columns, types, nullability, defaults and named constraints of TRD 20 §4.6.10–§4.6.16. | PGS-006 |
| FEAT-011-FR-02 | `processed_sessions` shall enforce the status/reason CHECK `processed_sessions_status_reason_ck` (usable without reasons; late usable with exactly "late arrival (not used for baseline or scores)"; duplicate with exactly "session_id already received"; set_aside with 1–3 reasons from the fixed three; quarantined with one "possible other speaker (F0 z=…; composite features with \|z\|>=3: …)" reason, plus the late reason second when late), `reason_text` = reasons joined by "; ", `screen_detail` non-null for quarantined, `baseline_ordinal` set iff usable and not late, `in_baseline` only for non-late usable, `epoch_id` NULL for duplicates and allowed NULL only for late rows, and `late_arrival` never true for duplicates. | PGS-012, D-57 |
| FEAT-011-FR-03 | `processed_sessions.local_date` shall be within one calendar day of the UTC date of `timestamp_utc`. | PGS-013 |
| FEAT-011-FR-04 | `processed_sessions.adjusted_features` shall be NULL for duplicates and otherwise an object containing all 19 feature keys. | PGS-033 |
| FEAT-011-FR-05 | `day_ledger` shall enforce `checked_in` ⇒ empty reason, `missing_resident` ⇒ "no record received", `missing_device_gap` ⇒ non-null `device_id` and reason "all residents on shared device % have no record", and uniqueness of `(resident_id, local_date)`. | PGS-014 |
| FEAT-011-FR-06 | `epochs` shall be unique on `(resident_id, epoch_number)`, numbered from 1, and at most one row per resident shall have `ended_at IS NULL` (`epochs_current_uq`). | PGS-030, FR-051 |
| FEAT-011-FR-07 | `baselines.feature_key` shall be one of the 19 feature keys or `composite`, unique per `(epoch_id, feature_key)`, with `n_sessions`, `first_session_id`, `frozen_after_session_id`, `median`, `mad`, `robust_spread`, `floor_applied`, `frozen_at`. | PGS-031, FR-086 |
| FEAT-011-FR-08 | `echowell_app` shall have only SELECT, INSERT on `baselines`, so a frozen baseline cannot be updated or deleted by the application. | DB-016, PGS-021 |
| FEAT-011-FR-09 | `scores.z` shall contain at least the 7 composite z keys and `scores.cusum_tally` shall be ≥ 0; each score row stores `local_date`, `is_morning`, `composite_raw`, `composite_z`, `alarm_state`; FK to `processed_sessions` is `ON DELETE CASCADE`. | PGS-032, PGS-010, FR-094 |
| FEAT-011-FR-10 | `cusum_state` shall hold one row per epoch (`epoch_id` primary key) with `current_tally` ≥ 0, `last_scored_session_id`, `alarm_on`, and the rule that an unscored state has tally 0 and no alarm. | FR-105, PGS-007 |
| FEAT-011-FR-11 | `pipeline_runs` shall store `trigger`, `scope`, `config_profile`, `config_snapshot`, `code_version`, `as_of`, `started_at`, `finished_at`, `status`, `counts`, `warnings`, `error_message` with the §4.6.10 CHECKs (running ⇔ no `finished_at`; failed ⇔ `error_message`). | DB-020, TRD 23 §4.2.10 |
| FEAT-011-FR-12 | JSON columns shall be validated by Pydantic models with the TRD 23 §4.5 shapes before insert, including the exact `counts` key list (`arrivals, usable, set_aside, quarantined, duplicate, missing_resident, missing_device_gap, late_arrival, scored, alerts_opened, excluded_after_as_of, residents`, plus `db_size_bytes` on nightly runs) and `warnings` items `{code, resident_code, session_id, detail}`. | DME-013, DB-020 |
| FEAT-011-FR-13 | `double precision` columns and JSON numbers shall be Python `float` without rounding (models use `sqlalchemy.Double`). | DME-014 |
| FEAT-011-FR-14 | `processed_sessions.status` shall only take the persisted values `usable`, `set_aside`, `quarantined`, `duplicate`; `pending_screen` never reaches the database. | DME-006 |
| FEAT-011-FR-15 | Every row of `epochs`, `processed_sessions`, `day_ledger`, `scores`, `cusum_state` shall reference the `pipeline_runs` row that wrote it and be computable solely from `raw_sessions`, reference tables and the config profile. | DB-006, TRD 20 §4.10 |
| FEAT-011-FR-16 | Repositories shall expose the baseline state of a resident-epoch as `not_started`, `forming` or `frozen` (20 `baselines` rows), never returning from `frozen` to `forming`. | DME-010 |

## Inputs

- `raw_sessions`, `residents`, `devices` (FEAT-009, FEAT-010); enums `session_status`, `day_status`, `alarm_state`, `pipeline_trigger`, `pipeline_run_status` (FEAT-008).

## Outputs

- Seven tables with constraints, triggers and grants; models, JSON validation models and repositories used by the pipeline runner and read APIs.

## Data Flow

Pipeline runner (FEAT-053) inserts a `pipeline_runs` row (`running`) → analytics result rows are validated by the JSON models and written to `epochs`, `processed_sessions`, `day_ledger`, `baselines` (insert-only), `scores`, `cusum_state` → the run row is updated to `succeeded`/`failed` with `counts` and `warnings` → read APIs (FEAT-027, FEAT-028, FEAT-034) and read-model queries (FEAT-014) select from these tables.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-010

- FEAT-010 provides `raw_sessions`, referenced by `processed_sessions.raw_session_id`.

Features that build directly on this one: FEAT-012, FEAT-024.

## Database Impact

- Tables created: `pipeline_runs`, `epochs`, `processed_sessions`, `day_ledger`, `baselines`, `scores`, `cusum_state`.
- Constraints: `pipeline_runs_profile_ck`, `pipeline_runs_scope_ck`, `pipeline_runs_snapshot_ck`, `pipeline_runs_counts_ck`, `pipeline_runs_warnings_ck`, `pipeline_runs_finished_ck`, `pipeline_runs_error_ck`, `pipeline_runs_order_ck`, `epochs_resident_number_uq`, `epochs_number_ck`, `epochs_order_ck`, `processed_sessions_raw_session_uq`, `processed_sessions_epoch_ck`, `processed_sessions_local_date_ck`, `processed_sessions_reason_text_ck`, `processed_sessions_status_reason_ck`, `processed_sessions_screen_ck`, `processed_sessions_ordinal_ck`, `processed_sessions_in_baseline_ck`, `processed_sessions_adjusted_ck`, `day_ledger_resident_date_uq`, `day_ledger_reason_ck`, `baselines_epoch_feature_uq`, `baselines_feature_key_ck`, `baselines_n_sessions_ck`, `baselines_spread_ck`, `scores_processed_session_uq`, `scores_z_ck`, `scores_cusum_ck`, `cusum_state_tally_ck`, `cusum_state_scored_ck`.
- Index: `epochs_current_uq` (partial unique).
- Triggers: `pipeline_runs_set_updated_at`, `epochs_set_updated_at`, `cusum_state_set_updated_at`.
- Tables used: `raw_sessions`, `residents`, `devices` (FK targets).

## API Impact

None exposed. These tables back E-08..E-12, E-18..E-21 delivered by later features.

## Frontend Impact

None.

## Analytics Impact

None computed. The tables store the outputs of the TRD 07 stages (epochs, statuses, adjusted features, baselines, z, composite, CUSUM).

## Security Requirements

- Baselines append-only for the app (no UPDATE/DELETE grant) (DB-016).
- `echowell_readonly` SELECT only; no PII and no audio columns (DB-035).
- Derived tables writable only by the pipeline service code path (ARC-032), enforced by code structure in FEAT-053.

## Error Handling

| Failure | Behaviour | Trace |
|---|---|---|
| Invalid status/reason combination | Insert fails with SQLSTATE 23514 (`processed_sessions_status_reason_ck`) | AC-PGS-04, AC-PGS-05 |
| Duplicate row with `epoch_id` | 23514 | AC-PGS-06 |
| Wrong ledger reason | 23514 | AC-PGS-07 |
| Second current epoch or second ledger row per day | 23505 | PGS-030, PGS-014 |
| JSON shape invalid | Pydantic `ValidationError` before insert; the pipeline run fails and records `error_message` (FEAT-053) | DME-013 |
| UPDATE/DELETE on `baselines` by app | 42501 | DB-016 |

## Logging Requirements

None from the tables. Run lifecycle logs (`pipeline_run_started`, `pipeline_run_succeeded` / `pipeline_run_failed`, D-80) belong to FEAT-056.

## Testing Requirements

- Integration (`tests/integration/test_schema_behaviour.py`, marker `integration`): AC-PGS-04, AC-PGS-05, AC-PGS-06, AC-PGS-07; late-arrival combinations of D-57 accepted (late usable with the late reason and NULL epoch; late quarantined with two reasons) and rejected for duplicates.
- Integration: TST-042 uniqueness of `epochs(resident_id, epoch_number)`, `baselines(epoch_id, feature_key)`, `day_ledger(resident_id, local_date)`, `processed_sessions.raw_session_id`; `epochs_current_uq` rejects a second open epoch (PGS-030); `local_date` two days off fails (PGS-013).
- Integration (`tests/integration/db/test_grants.py`): `echowell_app` cannot UPDATE or DELETE `baselines` (part of TST-041 and DB-016).
- Integration: `pg_constraint` shows `scores_processed_session_id_fkey` with `confdeltype = 'c'` (AC-PGS-13).
- Unit (`tests/unit/backend/schemas/test_json_columns.py`): JSON shape models accept the TRD 23 §4.5 examples and reject a `counts` object with a missing or extra key.

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-011-AC-01 | A `set_aside` row with reasons `{quality flag poor, noise above limit}` and reason_text `quality flag poor; noise above limit` inserts; with reason_text `noise above limit` it fails with 23514. | AC-PGS-04 |
| FEAT-011-AC-02 | A `quarantined` row with reason `possible other speaker (F0 z=5.12; composite features with \|z\|>=3: 3)` and non-null `screen_detail` inserts; with `screen_detail` NULL it fails. | AC-PGS-05 |
| FEAT-011-AC-03 | A `duplicate` row with non-null `epoch_id` fails; a `duplicate` row with `late_arrival = true` fails. | AC-PGS-06, D-57 |
| FEAT-011-AC-04 | A `missing_resident` ledger row with reason `no record` fails; a `missing_device_gap` row for R02 on 2026-10-12 with device D02 and reason `all residents on shared device D02 have no record` inserts. | AC-PGS-07 |
| FEAT-011-AC-05 | A late `usable` row with `epoch_id` NULL, no `baseline_ordinal`, `in_baseline = false` and reason `late arrival (not used for baseline or scores)` inserts. | D-57, PGS-012 |
| FEAT-011-AC-06 | Inserting a 21st baselines row for an epoch with an existing `feature_key`, or with `feature_key = 'f0'`, fails. | PGS-031 |
| FEAT-011-AC-07 | A `scores` row whose `z` lacks `z_voiced_fraction` or whose `cusum_tally = -0.1` fails with 23514. | PGS-032 |
| FEAT-011-AC-08 | `has_table_privilege('echowell_app','baselines','UPDATE')` and `…'DELETE')` are false; `…'scores','DELETE')` is true. | DB-016, PGS-021 |
| FEAT-011-AC-09 | A second epoch row with `ended_at IS NULL` for the same resident fails with 23505. | PGS-030 |

## Definition of Done

- All FEAT-011 acceptance criteria pass; `database/schema.sql` regenerated; `alembic check` clean; migration round-trip passes (TST-040).
- JSON shape models live in `backend/schemas/` and are reused by FEAT-053; delivered in the Phase 4 PR.

## Implementation Notes

- Copy the CHECK expressions verbatim; the `LIKE` patterns and the reason strings must match the analytics output byte for byte (AGT-049 order "quality flag poor; noise above limit").
- The `local_date` CHECK uses `timestamp_utc AT TIME ZONE 'UTC'` (immutable); do not replace it with a facility-timezone expression (TRD 20 §8).
- `cusum_state` has no `created_at` and its primary key is `epoch_id` (PGS-007).
- Rebuild idempotency (DB-019, AGT-056) depends on natural keys; FEAT-053 implements it, but keep repository methods keyed by `raw_session_id`, `(resident_id, epoch_number)`, `(epoch_id, feature_key)`, `processed_session_id`, `(resident_id, local_date)` (ARC-045).
