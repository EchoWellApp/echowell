# FEAT-013 Connection layer, advisory-lock helper and index set

| Field | Value |
|---|---|
| Epic | Database |
| Build phase | Phase 4 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-012 |
| Status | Not Started |

## Purpose

Provide the one place where database connections are created and serialised: the engine factory in `backend/core/db.py` (synchronous SQLAlchemy 2.0 on psycopg 3, fixed pool settings, no server-side prepared statements, TLS for every non-local URL), the single `advisory_key(namespace, value)` helper used for every transaction-scoped advisory lock (per resident, per `session_id`, device data alerts, nightly date), and the complete index set of TRD 20 §4.7 that keeps the overview and pipeline queries within budget.

## Business Context

- BR-03 and BR-02: concurrent arrivals of one `session_id` and concurrent runs for one resident are serialised so only the first arrival is new and the ledger stays consistent (DB-021, AC-ARC-06, D-62).
- BR-12 and NFR: overview queries complete within the read budget on the DS-08 scale set (DB-040, DB-042).
- BR-16: TLS on every non-local database connection (DB-053, PGS-027).
- RSK-07: pool sizes fit free-tier Neon limits; pooled endpoint compatibility (API-125).

## Referenced TRDs

- TRD 06 DB-021, DB-040, DB-042, DB-046, DB-047, DB-053; §4.7 query-pattern table.
- TRD 20 PGS-027, PGS-038; §4.7 index DDL; §8 notes on the Neon pooler.
- TRD 05 API-007, API-125.
- TRD 01 AC-ARC-06.
- TRD 24 D-62, D-71, D-73.

## Scope

- `backend/core/db.py`:
  - `create_engine_for(url, ...)` — the single engine factory used by the app (`DATABASE_URL`), the read-only engine (`DATABASE_READONLY_URL`, used only by `analytics_summary.py`), Alembic and the CLI: synchronous SQLAlchemy 2.0, `postgresql+psycopg://`, `pool_size=5`, `max_overflow=5`, `pool_pre_ping=True`, `pool_recycle=300`, `connect_args={"prepare_threshold": None}`.
  - TLS enforcement: a URL without `sslmode=require` or `verify-full` is refused at engine creation unless `APP_ENV` is `local` or `test` (the TRDs define "non-local" through ENV-011 and SEC-065; this complements the FEAT-003 startup guard).
  - `SessionLocal` session factory used by `get_db()` (FEAT-003).
  - `advisory_key(namespace: str, value: str)` returning the SQL expression `hashtextextended('echowell:' || namespace || ':' || value, 0)` and a helper `lock_xact(session, namespace, value)` issuing `SELECT pg_advisory_xact_lock(<key>)`; a helper to lock several residents in ascending `resident_code` order.
- Migration 0001 index section: every index of TRD 20 §4.7 not already created by FEAT-011/FEAT-012, with exact names, columns, order, INCLUDE list and predicates.
- Model `Index(...)` declarations with the same names so `alembic check` is clean.
- Catalogue tests for index existence and FK-column coverage.

## Out of Scope

- Using the locks in the ingest path (FEAT-025), the pipeline runner (FEAT-053), the data-alert transaction (FEAT-050/FEAT-053) and the nightly job (FEAT-054); this feature only provides the helper.
- The DS-08 performance test and its dataset generator (FEAT-079), though the indexes it depends on are delivered here.
- The read-model queries (FEAT-014).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-013-FR-01 | Every engine (app, readonly, Alembic, CLI) shall be created by the one factory in `backend/core/db.py` with `pool_size=5`, `max_overflow=5`, `pool_pre_ping=True`, `pool_recycle=300` and `connect_args={"prepare_threshold": None}`. | API-125, D-73 |
| FEAT-013-FR-02 | The backend shall use synchronous SQLAlchemy 2.0.x on psycopg 3 (`postgresql+psycopg://`). | API-007 |
| FEAT-013-FR-03 | Every connection to a non-local database shall use TLS (`sslmode=require` or `verify-full`); the factory refuses a non-local URL without it. | DB-053, PGS-027 |
| FEAT-013-FR-04 | All application advisory locks shall be transaction-scoped (`pg_advisory_xact_lock`) and keyed only by `advisory_key(namespace, value)` = `hashtextextended('echowell:' \|\| namespace \|\| ':' \|\| value, 0)`; no session-level advisory lock is taken by application code. | DB-021, D-62 |
| FEAT-013-FR-05 | The helper shall support the four namespaces of DB-021: `resident` (value `resident_code`, multiple residents locked in ascending order), `session` (value `session_id`), `device_alerts` (value `all`), `nightly` (value facility-local date). | DB-021 |
| FEAT-013-FR-06 | Every index of TRD 20 §4.7 shall exist with its exact name, columns, order, INCLUDE list and predicate. | PGS-038 |
| FEAT-013-FR-07 | Foreign-key columns used in deletes or joins (`pipeline_run_id`, `ingest_batch_id`, `api_key_id`, `acknowledged_by`, `author_user_id`, `alert_id`, `device_id`) shall be the leading column of some index. | DB-047 |
| FEAT-013-FR-08 | The index set shall support the TRD 06 §4.7 query patterns so overview queries take ≤ 150 ms total database time and resident-scoped queries on `raw_sessions`, `processed_sessions`, `scores` and `day_ledger` use no sequential scan on DS-08 (verified by FEAT-079). | DB-040, DB-042 |
| FEAT-013-FR-09 | New indexes added after the initial migration shall have a documented query pattern and be created `CONCURRENTLY` inside an Alembic `autocommit_block` in staging/production migrations. | DB-046 |

## Inputs

- Connection URLs from `Settings` (`DATABASE_URL`, `DATABASE_READONLY_URL`, `DATABASE_MIGRATION_URL`) (FEAT-003).
- All 24 tables (FEAT-009..FEAT-012).

## Outputs

- Engine factory, session factory, advisory-lock helpers; 50+ named indexes in migration 0001.

## Data Flow

Process start → `Settings` → `create_engine_for(DATABASE_URL)` (pooled, TLS checked) → `SessionLocal` → `get_db()` yields sessions per request. A service that needs serialisation calls `lock_xact(session, 'session', session_id)` (or `'resident'`, `'device_alerts'`, `'nightly'`) at the start of its transaction; PostgreSQL releases the lock at commit or rollback. Queries from repositories use the §4.7 indexes.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-012

- FEAT-012 completes the 24 tables, so every §4.7 index can be created in migration 0001.

Features that build directly on this one: FEAT-014, FEAT-015.

## Database Impact

- Indexes created (TRD 20 §4.7): `residents_facility_idx`, `residents_status_cohort_idx`, `devices_facility_idx`, `device_assignments_device_idx`, `device_assignments_resident_idx`, `api_keys_device_idx`, `ingest_batches_received_idx`, `ingest_batches_uploaded_by_idx`, `ingest_batches_api_key_idx`, `ingest_rejections_batch_idx`, `ingest_rejections_received_idx`, `ingest_rejections_api_key_idx`, `raw_sessions_session_id_idx`, `raw_sessions_resident_ts_idx`, `raw_sessions_device_ts_idx`, `raw_sessions_batch_idx`, `raw_sessions_api_key_idx`, `pipeline_runs_started_idx`, `pipeline_runs_status_idx`, `epochs_device_idx`, `epochs_run_idx`, `processed_sessions_resident_date_idx` (INCLUDE status), `processed_sessions_resident_ts_idx` (WHERE status <> 'duplicate'), `processed_sessions_epoch_idx`, `processed_sessions_session_id_idx`, `processed_sessions_run_idx`, `day_ledger_missing_idx` (WHERE status <> 'checked_in'), `day_ledger_device_date_idx`, `day_ledger_run_idx`, `baselines_resident_idx`, `baselines_run_idx`, `scores_resident_date_idx`, `scores_epoch_date_idx`, `scores_run_idx`, `cusum_state_resident_idx`, `cusum_state_run_idx`, `alerts_status_triggered_idx`, `alerts_resident_triggered_idx`, `alerts_acknowledged_by_idx`, `alerts_run_idx`, `alerts_snoozed_by_idx`, `alert_reviews_alert_created_idx`, `alert_reviews_reviewer_idx`, `alert_reviews_outcome_idx`, `data_alerts_status_detected_idx`, `data_alerts_resident_idx`, `data_alerts_device_idx`, `data_alerts_run_idx`, `staff_notes_resident_created_idx`, `staff_notes_alert_idx`, `staff_notes_author_idx`, `facility_reference_ranges_lookup_idx`, `facility_reference_ranges_run_idx`, `config_parameters_updated_by_idx`, `audit_logs_occurred_idx`, `audit_logs_entity_idx`, `audit_logs_actor_idx`, `audit_logs_action_idx`.
- Already created by earlier features and verified here: `epochs_current_uq` (FEAT-011), `alerts_one_active_per_epoch_uq`, `data_alerts_open_subject_uq` (FEAT-012).
- No table created or modified.

## API Impact

None exposed. All endpoints use the session factory.

## Frontend Impact

None.

## Analytics Impact

None.

## Security Requirements

- TLS for every non-local connection (DB-053); the readonly engine is created only where `DATABASE_READONLY_URL` is set and is used only by `analytics_summary.py` (SEC-116).
- No credentials logged by the factory (secrets are `SecretStr`, ENV-004).

## Error Handling

| Failure | Behaviour | Trace |
|---|---|---|
| Non-local URL without `sslmode` | Factory raises a configuration error; process exits with code 1 via settings validation | DB-053, ENV-002 |
| Stale pooled connection | `pool_pre_ping` replaces it transparently | API-125 |
| Schema recreated under a running backend (D-71 reset) | No prepared-statement errors because `prepare_threshold` is `None` | API-125, D-73 |
| Lock contention | The second transaction waits on `pg_advisory_xact_lock` until the first commits or rolls back | DB-021 |

## Logging Requirements

None beyond standard error propagation; connection failures surface through the health endpoint (FEAT-003) and request error handling (FEAT-019).

## Testing Requirements

- Unit (`tests/unit/backend/core/test_db.py`): engine options (pool settings, `prepare_threshold`), TLS refusal for a non-local URL without `sslmode`, `advisory_key` SQL expression and namespace formatting.
- Integration (`tests/integration/db/test_advisory_locks.py`): two concurrent transactions locking `advisory_key('session', 'R01-20261001-01')` are serialised; multi-resident locking acquires keys in ascending `resident_code` order. The end-to-end DB-021 test (two concurrent POSTs of one `session_id`: one 201, one 200 duplicate) and AC-ARC-06 run with FEAT-025.
- Integration (`tests/integration/db/test_indexes.py`): every §4.7 index exists with exact definition (`pg_indexes.indexdef`) (PGS-038); catalogue query shows every FK column of DB-047 leads an index; schema reference test passes (PGS-016).
- Performance (DB-040, DB-042) is executed by FEAT-079 on DS-08.

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-013-AC-01 | `pg_indexes` contains every index named in TRD 20 §4.7 and each `indexdef` matches the §4.7 definition (columns, order, INCLUDE, predicate). | PGS-038 |
| FEAT-013-AC-02 | For each column `pipeline_run_id`, `ingest_batch_id`, `api_key_id`, `acknowledged_by`, `author_user_id`, `alert_id`, `device_id` in any table, a catalogue query finds an index whose first column is that column. | DB-047 |
| FEAT-013-AC-03 | With `APP_ENV=staging`, `create_engine_for("postgresql+psycopg://u:p@db.example.org/x")` raises and the same URL with `?sslmode=require` succeeds; with `APP_ENV=local` or `test` the Compose/CI URL without `sslmode` is accepted (ENV-011 scope). | DB-053, PGS-027, ENV-011 |
| FEAT-013-AC-04 | The engine reports `pool.size() == 5`, `max_overflow == 5`, `pre_ping` enabled, `recycle == 300`, and connections are opened with `prepare_threshold=None`. | API-125 |
| FEAT-013-AC-05 | Transaction A holding `pg_advisory_xact_lock(advisory_key('resident','R02'))` blocks transaction B on the same key until A commits; B proceeds immediately after. | DB-021, D-62 |
| FEAT-013-AC-06 | `grep -rn "pg_advisory_lock\b\|pg_try_advisory_lock\b" backend` returns nothing (no session-level locks); `grep -rn "hashtextextended" backend` returns only `backend/core/db.py`. | DB-021 |

## Definition of Done

- All FEAT-013 acceptance criteria pass; `alembic check` clean; `database/schema.sql` regenerated.
- `get_db()` from FEAT-003 uses `SessionLocal` from this feature; delivered in the Phase 4 PR.

## Implementation Notes

- Alembic's own migration lock (`0x45434857`, DEP-064) is session-level and runs on the direct host; it is not an application lock and is outside DB-021 (FEAT-008).
- Session-level advisory locks do not work over the Neon pooled endpoint (PgBouncer transaction mode); this is why every application lock is transaction-scoped (D-62, TRD 20 §8).
- Create the initial indexes in migration 0001 with plain `CREATE INDEX` (empty tables); DB-046's `CONCURRENTLY` rule applies to later migrations.
- `processed_sessions_resident_date_idx` uses `INCLUDE (status)` for index-only 30-day counts; keep the INCLUDE list exact.
