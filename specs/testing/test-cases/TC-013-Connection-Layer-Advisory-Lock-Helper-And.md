# Connection layer, advisory-lock helper and index set

## Feature Description

FEAT-013 provides the single database engine factory `create_engine_for(url, app_env=...)` in `backend/core/db.py` (synchronous SQLAlchemy 2.0 on psycopg 3, `pool_size=5`, `max_overflow=5`, `pool_pre_ping=True`, `pool_recycle=300`, `connect_args={"prepare_threshold": None}`, TLS required for every non-local URL), the session factory used by `get_db()`, the transaction-scoped advisory-lock helpers `advisory_key(namespace, value)` = `hashtextextended('echowell:' || namespace || ':' || value, 0)`, `lock_xact()` and the ascending-order multi-resident lock, and the complete index set of TRD 20 §4.7 in migration 0001. It exposes no endpoint and no screen; it is verified by database catalogue queries, Python REPL checks against the local development stack, concurrent `psql` sessions and code inspection.

## Preconditions

- Local development stack running (`README.md` quick start; `docker compose up -d`), database migrated to head (`alembic upgrade head`).
- `.env` copied from `.env.development.example`; `APP_ENV=local`, `PIPELINE_PROFILE=test_v0_1`, all `SEED_*` variables set (values never written into this document).
- Seed loaded: `python -m backend.cli seed test_v0_1` (roster R01–R10, D01–D10 with D07B, pipeline run as of 2026-10-30 15:00 America/Chicago).
- `psql` access to the local database as the `echowell_app` login role (connection string from `DATABASE_URL` in the environment file).
- Python 3.12 virtual environment with `backend/requirements.txt` and `backend/requirements-dev.txt` installed, run from the repository root.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-013-01 | Every TRD 20 §4.7 index name exists in `pg_indexes` | High | Database |
| TC-013-02 | INCLUDE lists, predicates and column order of the special indexes match TRD 20 §4.7 exactly | High | Database |
| TC-013-03 | Every DB-047 foreign-key column leads some index | High | Database |
| TC-013-04 | Automated index and FK-coverage suite passes | High | Positive |
| TC-013-05 | Non-local URL without `sslmode` is refused at engine creation | High | Negative |
| TC-013-06 | Non-local URL with `sslmode=require` or `verify-full` is accepted | High | Positive |
| TC-013-07 | Local and test URLs without `sslmode` are accepted | High | Positive |
| TC-013-08 | App engine reports the API-125 pool settings and `prepare_threshold=None` | High | Positive |
| TC-013-09 | Schema reset under a running backend causes no prepared-statement error | Medium | Positive |
| TC-013-10 | Stale pooled connection is replaced transparently after a database restart | Medium | Positive |
| TC-013-11 | Two transactions locking `advisory_key('resident','R02')` are serialised | High | Database |
| TC-013-12 | Advisory lock is released at rollback as well as at commit | Medium | Database |
| TC-013-13 | Multi-resident locking takes keys in ascending `resident_code` order | Medium | Positive |
| TC-013-14 | `advisory_key` returns the DB-021 expression and refuses an unknown namespace | Medium | Negative |
| TC-013-15 | Inspection: no session-level advisory lock and `hashtextextended` only in `backend/core/db.py` | High | Security |
| TC-013-16 | `alembic check` is clean (model `Index` names equal migration names) | Medium | Database |
| TC-013-17 | Inspection: indexes added after migration 0001 follow DB-046 | Low | Documentation |

### TC-013-01 Every TRD 20 §4.7 index name exists in `pg_indexes`

| Step | Action | Expected Result |
|---|---|---|
| 1 | In `psql`, run `SELECT count(*) FROM pg_indexes WHERE schemaname = 'public' AND indexname IN ('residents_facility_idx','residents_status_cohort_idx','devices_facility_idx','device_assignments_device_idx','device_assignments_resident_idx','api_keys_device_idx','ingest_batches_received_idx','ingest_batches_uploaded_by_idx','ingest_batches_api_key_idx','ingest_rejections_batch_idx','ingest_rejections_received_idx','ingest_rejections_api_key_idx','raw_sessions_session_id_idx','raw_sessions_resident_ts_idx','raw_sessions_device_ts_idx','raw_sessions_batch_idx','raw_sessions_api_key_idx','pipeline_runs_started_idx','pipeline_runs_status_idx','epochs_current_uq','epochs_device_idx','epochs_run_idx','processed_sessions_resident_date_idx','processed_sessions_resident_ts_idx','processed_sessions_epoch_idx','processed_sessions_session_id_idx','processed_sessions_run_idx','day_ledger_missing_idx','day_ledger_device_date_idx','day_ledger_run_idx','baselines_resident_idx','baselines_run_idx','scores_resident_date_idx','scores_epoch_date_idx','scores_run_idx','cusum_state_resident_idx','cusum_state_run_idx','alerts_one_active_per_epoch_uq','alerts_status_triggered_idx','alerts_resident_triggered_idx','alerts_acknowledged_by_idx','alerts_run_idx','alerts_snoozed_by_idx','alert_reviews_alert_created_idx','alert_reviews_reviewer_idx','alert_reviews_outcome_idx','data_alerts_open_subject_uq','data_alerts_status_detected_idx','data_alerts_resident_idx','data_alerts_device_idx','data_alerts_run_idx','staff_notes_resident_created_idx','staff_notes_alert_idx','staff_notes_author_idx','facility_reference_ranges_lookup_idx','facility_reference_ranges_run_idx','config_parameters_updated_by_idx','audit_logs_occurred_idx','audit_logs_entity_idx','audit_logs_actor_idx','audit_logs_action_idx');` | Result is `61` (all 61 `CREATE INDEX` / `CREATE UNIQUE INDEX` statements of TRD 20 §4.7) |
| 2 | Run `SELECT indexname, tablename FROM pg_indexes WHERE indexname IN ('epochs_current_uq','alerts_one_active_per_epoch_uq','data_alerts_open_subject_uq');` | 3 rows: `epochs_current_uq` on `epochs`, `alerts_one_active_per_epoch_uq` on `alerts`, `data_alerts_open_subject_uq` on `data_alerts` (created by FEAT-011/FEAT-012, verified here) |

### TC-013-02 INCLUDE lists, predicates and column order of the special indexes match TRD 20 §4.7 exactly

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `SELECT indexdef FROM pg_indexes WHERE indexname = 'processed_sessions_resident_date_idx';` | `CREATE INDEX processed_sessions_resident_date_idx ON public.processed_sessions USING btree (resident_id, local_date) INCLUDE (status)` |
| 2 | Run the same query for `processed_sessions_resident_ts_idx` | Definition contains `(resident_id, timestamp_utc DESC)` and `WHERE (status <> 'duplicate'::...)` |
| 3 | Run the same query for `day_ledger_missing_idx` | Definition contains `(resident_id, local_date)` and `WHERE (status <> 'checked_in'::...)` |
| 4 | Run the same query for `pipeline_runs_status_idx` | Definition contains `(status)` and `WHERE (status = 'running'::...)` |
| 5 | Run the same query for `raw_sessions_resident_ts_idx` and `audit_logs_actor_idx` | `(resident_id, timestamp_utc, arrival_seq)` and `(actor_type, actor_id, occurred_at DESC)` respectively, in that column order |
| 6 | Run the same query for `data_alerts_open_subject_uq` | `CREATE UNIQUE INDEX` on `(kind, resident_id, device_id) NULLS NOT DISTINCT` with `WHERE ((status = 'open'...) AND (kind <> 'review_flagged_data_problem'...))` |

### TC-013-03 Every DB-047 foreign-key column leads some index

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `SELECT a.attname AS col, t.relname AS tbl FROM pg_attribute a JOIN pg_class t ON t.oid = a.attrelid JOIN pg_namespace n ON n.oid = t.relnamespace WHERE n.nspname = 'public' AND t.relkind = 'r' AND a.attname IN ('pipeline_run_id','ingest_batch_id','api_key_id','acknowledged_by','author_user_id','alert_id','device_id') AND NOT EXISTS (SELECT 1 FROM pg_index i WHERE i.indrelid = t.oid AND i.indkey[0] = a.attnum);` | 0 rows: every listed column in every table is the first column of at least one index |
| 2 | Run `SELECT indexname FROM pg_indexes WHERE indexname IN ('alerts_acknowledged_by_idx','staff_notes_author_idx','staff_notes_alert_idx','api_keys_device_idx','raw_sessions_batch_idx');` | 5 rows returned |

### TC-013-04 Automated index and FK-coverage suite passes

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `pytest -m integration tests/integration/db/test_indexes.py -q` | All tests pass; summary line shows `passed` and `0 failed` |
| 2 | Run `pytest -m integration tests/integration/test_schema_reference.py -q` | All tests pass (PGS-016 schema reference) |

### TC-013-05 Non-local URL without `sslmode` is refused at engine creation

| Step | Action | Expected Result |
|---|---|---|
| 1 | In a Python REPL run `from backend.core.db import create_engine_for` then `create_engine_for("postgresql+psycopg://u:p@db.example.org/x", app_env="staging")` | Raises `InsecureDatabaseUrlError` with message `database URLs outside local and test must specify sslmode=require or verify-full`; no connection is attempted |
| 2 | Repeat with `app_env="production"` | Same exception and message |
| 3 | Repeat with `"postgresql+psycopg://u:p@db.example.org/x?sslmode=disable"` and `app_env="staging"` | Same exception (only `require` and `verify-full` are accepted) |
| 4 | Start the backend with `APP_ENV=staging` and a `DATABASE_URL` without `sslmode` (all other staging variables valid) | Process exits with code 1 and a CRITICAL `startup_config_invalid` log line; the URL value is not printed |

### TC-013-06 Non-local URL with `sslmode=require` or `verify-full` is accepted

| Step | Action | Expected Result |
|---|---|---|
| 1 | In the REPL run `create_engine_for("postgresql+psycopg://u:p@db.example.org/x?sslmode=require", app_env="staging")` | Returns an `Engine` object without raising (engine creation does not connect) |
| 2 | Run `create_engine_for("postgresql+psycopg://u:p@db.example.org/x?sslmode=verify-full", app_env="production")` | Returns an `Engine` object without raising |

### TC-013-07 Local and test URLs without `sslmode` are accepted

| Step | Action | Expected Result |
|---|---|---|
| 1 | In the REPL run `create_engine_for(os.environ["DATABASE_URL"], app_env="local")` with the Compose URL (no `sslmode`) | Returns an `Engine`; `engine.connect()` succeeds and `SELECT 1` returns `1` |
| 2 | Run `create_engine_for("postgresql+psycopg://u:p@localhost:5432/x", app_env="test")` | Returns an `Engine` without raising |

### TC-013-08 App engine reports the API-125 pool settings and `prepare_threshold=None`

| Step | Action | Expected Result |
|---|---|---|
| 1 | In the REPL run `e = create_engine_for(os.environ["DATABASE_URL"], app_env="local")` | Engine created |
| 2 | Inspect `e.pool.size()`, `e.pool._max_overflow`, `e.pool._pre_ping`, `e.pool._recycle` | `5`, `5`, `True`, `300` |
| 3 | Inspect `e.dialect.driver` and `e.url.drivername` | `psycopg` and `postgresql+psycopg` |
| 4 | Run `with e.connect() as c: print(c.connection.dbapi_connection.prepare_threshold)` | Prints `None` |
| 5 | Call `create_engine_for` a second time with the same URL and compare with `is` | Same engine object is returned (one engine per URL) |

Note: TRD 05 API-136 sets `pool_size=1` and read-only transactions for the read-only engine; `create_read_only_engine` (backend/core/db.py:78) follows API-136, while API-125/FEAT-013-FR-01 list the same pool settings for every engine. This case checks the app engine only.

### TC-013-09 Schema reset under a running backend causes no prepared-statement error

| Step | Action | Expected Result |
|---|---|---|
| 1 | With the backend running, call `GET http://localhost:8000/api/v1/health` | 200 with `"status":"ok"` |
| 2 | Run `python -m backend.cli seed test_v0_1 --reset` (drops and recreates the schema, then reseeds) | Exit code 0; stderr ends with `Seed test_v0_1 complete.` |
| 3 | Without restarting the backend, log in as `admin@example.com` (password from `SEED_ADMIN_PASSWORD`) and call `GET /api/v1/residents` | 200 with `total` 10; backend logs contain no `prepared statement` error and no 500 response |

### TC-013-10 Stale pooled connection is replaced transparently after a database restart

| Step | Action | Expected Result |
|---|---|---|
| 1 | Log in as admin and call `GET /api/v1/residents` | 200 |
| 2 | Run `docker compose restart db` and wait until `docker compose ps` shows `db` healthy | Database restarted |
| 3 | Call `GET /api/v1/residents` again with the same token | 200 with `total` 10 (no 500 `INTERNAL_ERROR`; `pool_pre_ping` replaced the dead connection) |

### TC-013-11 Two transactions locking `advisory_key('resident','R02')` are serialised

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `psql` session A; run `BEGIN; SELECT pg_advisory_xact_lock(hashtextextended('echowell:' \|\| 'resident' \|\| ':' \|\| 'R02', 0));` | Returns one row immediately |
| 2 | Open `psql` session B; run the same two statements | Session B does not return (blocked waiting on the lock) |
| 3 | In a third session run `SELECT count(*) FROM pg_locks WHERE locktype = 'advisory' AND NOT granted;` | `1` |
| 4 | In session A run `COMMIT;` | Session B's `SELECT` returns within 1 second |
| 5 | In session B run `COMMIT;` then repeat step 3 | `0` |
| 6 | Run `pytest -m integration tests/integration/db/test_advisory_locks.py -q` | All tests pass (two transactions on `advisory_key('session', 'R01-20261001-01')` serialised) |

### TC-013-12 Advisory lock is released at rollback as well as at commit

| Step | Action | Expected Result |
|---|---|---|
| 1 | Session A: `BEGIN; SELECT pg_advisory_xact_lock(hashtextextended('echowell:session:R01-20261001-01', 0));` | Lock granted |
| 2 | Session B: same statements | Session B blocks |
| 3 | Session A: `ROLLBACK;` | Session B proceeds within 1 second |
| 4 | After both sessions end, run `SELECT count(*) FROM pg_locks WHERE locktype = 'advisory';` | `0` (no lock survives the transaction; no session-level lock) |

### TC-013-13 Multi-resident locking takes keys in ascending `resident_code` order

| Step | Action | Expected Result |
|---|---|---|
| 1 | Read `lock_residents` in `backend/core/db.py` | It iterates `sorted(set(resident_codes))` and calls `lock_xact(session, "resident", code)` for each |
| 2 | In the REPL, open a session on the app engine, call `lock_residents(s, ["R10", "R02", "R09"])`, then in `psql` run `SELECT count(*) FROM pg_locks WHERE locktype = 'advisory' AND granted;` | `3` |
| 3 | Roll back the REPL session and repeat the `pg_locks` query | `0` |

### TC-013-14 `advisory_key` returns the DB-021 expression and refuses an unknown namespace

| Step | Action | Expected Result |
|---|---|---|
| 1 | In the REPL run `k = advisory_key("session", "R01-20261001-01"); print(k.text, k.compile().params)` | Text is `hashtextextended('echowell:' \|\| :namespace \|\| ':' \|\| :value, 0)`; params `{'namespace': 'session', 'value': 'R01-20261001-01'}` |
| 2 | Run `advisory_key("device_alerts", "all")` and `advisory_key("nightly", "2026-10-30")` | Both return without error |
| 3 | Run `advisory_key("global", "x")` | Raises `ValueError: unknown advisory-lock namespace: global` |
| 4 | Run `pytest tests/unit/backend/core/test_db.py -q` | All tests pass |

### TC-013-15 Inspection: no session-level advisory lock and `hashtextextended` only in `backend/core/db.py`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `grep -rn "pg_advisory_lock\b\|pg_try_advisory_lock\b" backend` | No output |
| 2 | Run `grep -rln "hashtextextended" backend --include=*.py` | Exactly one line: `backend/core/db.py` |

### TC-013-16 `alembic check` is clean (model `Index` names equal migration names)

| Step | Action | Expected Result |
|---|---|---|
| 1 | On a database at head, run `alembic check` | Output `No new upgrade operations detected.`; exit code 0 |
| 2 | Run `grep -rn "Index(\"processed_sessions_resident_date_idx\"" backend/models` | One match in the processed-session model |

### TC-013-17 Inspection: indexes added after migration 0001 follow DB-046

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `grep -n "CREATE INDEX" backend/alembic/versions/0003_*.py backend/alembic/versions/0004_*.py` | Each index listed has a documented query pattern in TRD 06 §4.7 / TRD 20 §4.13 |
| 2 | Check whether each such index uses `CREATE INDEX CONCURRENTLY` inside `op.get_context().autocommit_block()` | Per DB-046 each new index is created `CONCURRENTLY` in an autocommit block |

Note: `backend/alembic/versions/0003_ingest_batch_pipeline_run.py:24` creates `ingest_batches_pipeline_run_idx` with plain `CREATE INDEX`, copying TRD 20 §4.13 verbatim (D-124); DB-046 asks for `CONCURRENTLY`. Record the result as an observation against DB-046 (Should).

## API Validation

Not applicable. FEAT-013 exposes no endpoint (API Impact: none); its effect on the API is checked indirectly in TC-013-09 and TC-013-10 through `GET /api/v1/health` and `GET /api/v1/residents`.

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | Count of TRD 20 §4.7 index names in `pg_indexes` (TC-013-01) | 61 |
| 2 | `indexdef` of `processed_sessions_resident_date_idx` | Ends with `(resident_id, local_date) INCLUDE (status)` |
| 3 | FK leading-column catalogue query (TC-013-03) | 0 rows |
| 4 | `SELECT count(*) FROM pg_locks WHERE locktype = 'advisory'` with no open transactions | 0 |
| 5 | No table or column is created by this feature: `alembic check` | `No new upgrade operations detected.` |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | `create_engine_for("postgresql+psycopg://u:p@db.example.org/x", app_env="staging")` | `InsecureDatabaseUrlError`; no connection attempted (TC-013-05) |
| 2 | Same URL with `?sslmode=disable` and `app_env="production"` | `InsecureDatabaseUrlError` |
| 3 | `advisory_key("global", "x")` | `ValueError: unknown advisory-lock namespace: global` (TC-013-14) |
| 4 | Second transaction requests a held resident lock | Blocks until the first commits or rolls back (TC-013-11, TC-013-12) |
| 5 | Database restarted under a running backend | Next request returns 200, not 500 (TC-013-10) |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-013-AC-01 | All 61 TRD 20 §4.7 index names exist and each `indexdef` matches columns, order, INCLUDE and predicate; `test_indexes.py` passes | TC-013-01, TC-013-02, TC-013-04 |
| FEAT-013-AC-02 | Catalogue query returns 0 FK columns of DB-047 without a leading index | TC-013-03, TC-013-04 |
| FEAT-013-AC-03 | Staging URL without `sslmode` raises; with `?sslmode=require` succeeds; local/test URL without `sslmode` accepted | TC-013-05, TC-013-06, TC-013-07 |
| FEAT-013-AC-04 | `pool.size()` 5, max overflow 5, pre-ping on, recycle 300, `prepare_threshold` `None` | TC-013-08 |
| FEAT-013-AC-05 | Transaction B on `advisory_key('resident','R02')` blocks until A commits, then proceeds immediately | TC-013-11 |
| FEAT-013-AC-06 | First grep returns nothing; second returns only `backend/core/db.py` | TC-013-15 |

## Test Data Requirements

- `test_v0_1` seed (residents R01–R10, devices D01–D10 and D07B) for the lock values `R02`, `R09`, `R10` and the session ID `R01-20261001-01`.
- Synthetic, non-resolving host `db.example.org` (RFC 2606) for TLS refusal checks; no real database host.
- Environment variables: `APP_ENV`, `DATABASE_URL`, `DATABASE_MIGRATION_URL`, `PIPELINE_PROFILE=test_v0_1`, `SEED_*` (values from the environment file, never written down).
- Two concurrent `psql` sessions plus one monitoring session.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-013-FR-01 / API-125 / D-73 | FEAT-013 | TC-013-08, TC-013-09 |
| FEAT-013-FR-02 / API-007 | FEAT-013 | TC-013-08 |
| FEAT-013-FR-03 / DB-053 / PGS-027 / ENV-011 | FEAT-013 | TC-013-05, TC-013-06, TC-013-07 |
| FEAT-013-FR-04 / DB-021 / D-62 | FEAT-013 | TC-013-11, TC-013-12, TC-013-14, TC-013-15 |
| FEAT-013-FR-05 / DB-021 | FEAT-013 | TC-013-13, TC-013-14 |
| FEAT-013-FR-06 / PGS-038 | FEAT-013 | TC-013-01, TC-013-02, TC-013-04, TC-013-16 |
| FEAT-013-FR-07 / DB-047 | FEAT-013 | TC-013-03 |
| FEAT-013-FR-08 / DB-040 / DB-042 | FEAT-013 | TC-013-01 (indexes present); budgets measured by FEAT-079 on DS-08 |
| FEAT-013-FR-09 / DB-046 | FEAT-013 | TC-013-17 |
| AC-ARC-06 (concurrent same `session_id`) | FEAT-013 (helper), FEAT-025 (use) | TC-013-11, TC-013-12 |
| PGS-016 (schema reference) | FEAT-013 | TC-013-04 |
| API-125 (stale connection, D-71 reset) | FEAT-013 | TC-013-09, TC-013-10 |
