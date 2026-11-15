# Ingest-triggered and nightly pipeline runs

## Feature Description

FEAT-054 connects the automatic triggers to the pipeline runner: `POST /api/v1/sessions` runs the pipeline synchronously after a first-arrival record commits (trigger `ingest`, scope = the record's resident plus every resident assigned to the same device on the record's local date) and returns `status_after_processing` and `pipeline_run_id` (or `pending` with 201 when the run fails); `POST /api/v1/ingest` creates one run row per batch, executes it through FastAPI `BackgroundTasks` and returns its id in the 202; `python -m backend.jobs.nightly_run` (external cron `0 7,8 * * *` UTC) runs a full pipeline (`scope = all`, trigger `nightly`) only during facility-local hour `NIGHTLY_RUN_HOUR_LOCAL` (default 2) and only once per facility-local date, checks the schema revision first, and extends the day ledger to the new as-of date. There is no in-process scheduler.

## Preconditions

- Local development stack; a disposable migrated database seeded with `python -m backend.cli seed test_v0_1` (DS-07) unless the case says "empty roster database", which means `python -m backend.cli seed test_v0_1 --master-only` (roster, users and ingest API key only).
- Backend API running locally with `APP_ENV` not `production`, `PIPELINE_PROFILE=test_v0_1`, `FACILITY_TZ=America/Chicago`.
- Ingest calls use header `X-API-Key` with the ingest API key from the environment file (`SEED_INGEST_API_KEY`); user calls a Bearer token from `POST /api/v1/auth/login` (`SEED_*` passwords).
- Synthetic record body "R01-new": copy all 30 fields of the SRC-05 row `R01-20261030-01` from `tests/fixtures/pipeline_input/EchoWell_pipeline_test_input_v0_1.csv` into JSON (numbers as numbers), then set `session_id` to `R01-20261031-01` and `timestamp_utc` to `2026-10-31 19:05:00`. "R02-new": same from row `R02-20261030-01`, `session_id` `R02-20261031-01`, `timestamp_utc` `2026-10-31 19:10:00`.
- For single-record cases the API process is started with `PIPELINE_AS_OF=2026-10-31T15:00:00-05:00`.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-054-01 | Single usable record returns 201 with processed status and `pipeline_run_id` | High | API |
| TC-054-02 | Single-record run scope includes the device's co-assigned residents | High | Database |
| TC-054-03 | Duplicate arrival returns 200 `duplicate` and starts no run | High | Negative |
| TC-054-04 | Failed synchronous run returns 201 `pending`; the raw row is kept and the next run processes it | High | Negative |
| TC-054-05 | Usable record shows on `GET /api/v1/residents` and `GET /api/v1/scores` right after the response | High | API |
| TC-054-06 | Batch ingest of SRC-05 returns 202 with `pipeline_run_id`; run reaches `succeeded` within 30 s | High | API |
| TC-054-07 | Nightly job outside the local nightly hour exits 0 without a run | High | Negative |
| TC-054-08 | Nightly job in the local nightly hour starts exactly one run; a second invocation exits 0 | High | Positive |
| TC-054-09 | One nightly run per local night across the 1 Nov 2026 DST change | High | Positive |
| TC-054-10 | Nightly run extends `day_ledger` to the new as-of date | High | Database |
| TC-054-11 | Nightly job refuses on a schema revision mismatch and never migrates | Medium | Negative |
| TC-054-12 | No in-process scheduler exists; cron is `0 7,8 * * *` UTC | Medium | Documentation |
| TC-054-13 | 283 single POSTs equal one batch ingest plus a full run | High | Analytics |
| TC-054-14 | `PIPELINE_AS_OF` is never used in production | Medium | Security |

### TC-054-01 Single usable record returns 201 with processed status and `pipeline_run_id`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `POST /api/v1/sessions` with header `X-API-Key: <ingest key>`, `Content-Type: application/json`, body "R01-new" | 201 |
| 2 | Inspect body | Fields `raw_session_id` (uuid), `arrival_seq` 284, `session_id` "R01-20261031-01", `status_after_processing` "usable", `reasons` [], `pipeline_run_id` (uuid, non-null) |
| 3 | `SELECT trigger, status, as_of FROM pipeline_runs WHERE id = '<pipeline_run_id>';` | `ingest`, `succeeded`, `2026-10-31 20:00:00+00` (from `PIPELINE_AS_OF`) |
| 4 | `SELECT p.status FROM processed_sessions p WHERE p.session_id='R01-20261031-01';` | `usable` |

### TC-054-02 Single-record run scope includes the device's co-assigned residents

| Step | Action | Expected Result |
|---|---|---|
| 1 | `POST /api/v1/sessions` with body "R02-new" | 201, non-null `pipeline_run_id` |
| 2 | `SELECT scope FROM pipeline_runs WHERE id = '<pipeline_run_id>';` | `{"type": "residents", "resident_codes": ["R02", "R03"]}` (R03 shares D02 on 2026-10-31) |
| 3 | `SELECT scope FROM pipeline_runs WHERE id = '<run id of TC-054-01>';` | `{"type": "residents", "resident_codes": ["R01"]}` |

### TC-054-03 Duplicate arrival returns 200 `duplicate` and starts no run

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT count(*) FROM pipeline_runs;` | Note value N |
| 2 | Repeat the `POST /api/v1/sessions` of TC-054-01 with the same body | 200; `status_after_processing` "duplicate", `reasons` ["session_id already received"], `pipeline_run_id` null |
| 3 | `SELECT count(*) FROM pipeline_runs;` | Still N |
| 4 | `SELECT count(*) FROM raw_sessions WHERE session_id='R01-20261031-01';` | `2` (the duplicate copy is stored) |

### TC-054-04 Failed synchronous run returns 201 `pending`; the raw row is kept and the next run processes it

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/integration/api/test_sessions.py -q -k failed_run_answers_pending` | `test_failed_run_answers_pending` passes |
| 2 | Review its assertions | Response 201 with `status_after_processing` "pending"; the `raw_sessions` row exists; the run row is `failed`; the error is logged with the request ID |
| 3 | Same test: next run | After the next run the record's `processed_sessions.status` is set (no manual repair) |

### TC-054-05 Usable record shows on `GET /api/v1/residents` and `GET /api/v1/scores` right after the response

Fresh copy of DS-07; API started with `PIPELINE_AS_OF=2026-10-30T15:00:00-05:00`. Body "R01-second": all 30 fields of SRC-05 row `R01-20261030-01` with `session_id` `R01-20261030-02` and `timestamp_utc` `2026-10-30 19:50:00`.

| Step | Action | Expected Result |
|---|---|---|
| 1 | Clinician `GET /api/v1/residents?sort=resident_id` and `GET /api/v1/scores?resident_code=R01` | R01 `last_30_days.used` 30, `last_checkin_local` on 2026-10-30 at 14:07; scores `total` 14 |
| 2 | `POST /api/v1/sessions` with body "R01-second" (`X-API-Key`) | 201, `status_after_processing` "usable", non-null `pipeline_run_id` |
| 3 | Immediately repeat both calls of step 1 | R01 `last_checkin_at` "2026-10-30T19:50:00Z" (`last_checkin_local` "2026-10-30T14:50:00-05:00"); `last_30_days.used` 31 (higher by 1); scores `total` 15 including session `R01-20261030-02` (R01 baseline frozen) |
| 4 | Other residents in `GET /api/v1/residents` | Unchanged values |

### TC-054-06 Batch ingest of SRC-05 returns 202 with `pipeline_run_id`; run reaches `succeeded` within 30 s

Empty roster database (`seed test_v0_1 --master-only`), API with `PIPELINE_AS_OF=2026-10-30T15:00:00-05:00`.

| Step | Action | Expected Result |
|---|---|---|
| 1 | Admin token; `POST /api/v1/ingest` multipart, part `file` = `tests/fixtures/pipeline_input/EchoWell_pipeline_test_input_v0_1.csv` (text/csv) | 202 `{"ingest_batch_id": ..., "source": "csv_upload", "accepted": 283, "rejected": 0, "duplicates": 2, "pipeline_run_id": "<uuid>"}` within 2 s |
| 2 | Poll `GET /api/v1/pipeline/runs/{pipeline_run_id}` every 2 s | `trigger` "ingest", `status` "succeeded" within 30 s of step 1 |
| 3 | `GET /api/v1/ingest/batches/{ingest_batch_id}` | `pipeline_run_id` equal to step 1; `record_count` 283 |
| 4 | `SELECT scope FROM pipeline_runs WHERE id='<pipeline_run_id>';` | `{"type": "residents", "resident_codes": ["R01", ..., "R10"]}` (all 10 received first arrivals) |

### TC-054-07 Nightly job outside the local nightly hour exits 0 without a run

| Step | Action | Expected Result |
|---|---|---|
| 1 | Find the current hour in America/Chicago; set `NIGHTLY_RUN_HOUR_LOCAL` to a different hour | Environment ready |
| 2 | `python -m backend.jobs.nightly_run; echo $?` | Exit code `0` |
| 3 | `SELECT count(*) FROM pipeline_runs WHERE trigger='nightly';` | Unchanged (0 on DS-07) |
| 4 | Read the job log | No `pipeline_run_started`; an ERROR `nightly_run_missing` line may appear (FEAT-056) |

### TC-054-08 Nightly job in the local nightly hour starts exactly one run; a second invocation exits 0

| Step | Action | Expected Result |
|---|---|---|
| 1 | Set `NIGHTLY_RUN_HOUR_LOCAL` to the current America/Chicago hour (simulates the 02:xx firing); unset `PIPELINE_AS_OF` | Environment ready |
| 2 | `python -m backend.jobs.nightly_run; echo $?` | Exit `0`; log `pipeline_run_started` then `pipeline_run_succeeded` |
| 3 | `SELECT trigger, status, scope FROM pipeline_runs WHERE trigger='nightly';` | 1 row: `nightly`, `succeeded`, `{"type": "all"}` |
| 4 | Run step 2 again within the same local date | Exit `0`; log `nightly_run_skipped`; still 1 nightly row |
| 5 | `pytest tests/integration/pipeline/test_nightly_run.py -q -k across_dst` | Passes: 07:30 UTC in CDT runs once, 07:45 UTC deduped, 08:30 UTC (03:30 CDT) exits 0 without a run |

### TC-054-09 One nightly run per local night across the 1 Nov 2026 DST change

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/integration/pipeline/test_nightly_run.py -q -k across_dst` | Passes |
| 2 | Review the clock points | 2026-10-31 07:30 UTC (02:30 CDT) runs; 2026-11-02 07:30 UTC (01:30 CST) exits 0; 2026-11-02 08:30 UTC (02:30 CST) runs |
| 3 | Result | Exactly 2 `nightly` rows, both `succeeded`, one per local night |

### TC-054-10 Nightly run extends `day_ledger` to the new as-of date

| Step | Action | Expected Result |
|---|---|---|
| 1 | On DS-07 start the job with `PIPELINE_AS_OF=2026-10-31T02:30:00-05:00` and `NIGHTLY_RUN_HOUR_LOCAL` = current local hour | Exit 0; run `succeeded` |
| 2 | `SELECT r.resident_code, l.status, l.reason FROM day_ledger l JOIN residents r ON r.id=l.resident_id WHERE l.local_date='2026-10-31' ORDER BY 1;` | 10 rows although no record arrived for Oct 31: R01, R04–R10 `missing_resident` "no record received"; R02 and R03 `missing_device_gap` "all residents on shared device D02 have no record" (shared device silent) |
| 3 | `SELECT count(*) FROM day_ledger;` | `310` |

### TC-054-11 Nightly job refuses on a schema revision mismatch and never migrates

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/integration/pipeline/test_nightly_run.py -q -k schema_mismatch` | Passes: revision "0001" and an unreadable `alembic_version` each give exit `1` and no `pipeline_runs` row |
| 2 | `grep -n "upgrade" backend/jobs/nightly_run.py` | No `alembic upgrade` call |

### TC-054-12 No in-process scheduler exists; cron is `0 7,8 * * *` UTC

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -rn -e apscheduler -e NIGHTLY_SCHEDULER_ENABLED backend` | No output |
| 2 | `grep -n "schedule:" render.yaml` | Nightly cron entries `"0 7,8 * * *"` with `python -m backend.jobs.nightly_run` |

### TC-054-13 283 single POSTs equal one batch ingest plus a full run

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/validation/test_single_record_ingest.py -q` | Exit code 0 |
| 2 | Review the comparison | SRC-05 posted one record at a time in arrival order with the clock frozen at 2026-10-30 15:00 America/Chicago gives derived tables equal to one batch ingest plus a full run (0 mismatches) |

### TC-054-14 `PIPELINE_AS_OF` is never used in production

| Step | Action | Expected Result |
|---|---|---|
| 1 | Start the API with `APP_ENV=production` and `PIPELINE_AS_OF` set | Startup refused by the settings guard (FEAT-003); the API does not serve requests |
| 2 | `grep -n "app_env != \"production\"" backend/services/pipeline_runner.py` | `resolve_as_of` uses `PIPELINE_AS_OF` only when `APP_ENV` is not production |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `POST /api/v1/sessions` first arrival | 201 `IngestResult` with `pipeline_run_id` |
| 2 | Same body again | 200, `duplicate`, `pipeline_run_id` null |
| 3 | `POST /api/v1/sessions` without `X-API-Key` | 401 |
| 4 | `POST /api/v1/sessions` with `resident_id` "R11" (synthetic, not enrolled) | 422 `UNKNOWN_RESIDENT`, detail "resident_id 'R11' is not enrolled."; no run started |
| 5 | `POST /api/v1/ingest` CSV | 202 `IngestBatchAccepted` with non-null `pipeline_run_id` |
| 6 | `GET /api/v1/pipeline/runs?trigger=nightly` (admin) | 200; nightly rows only |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT trigger, count(*) FROM pipeline_runs GROUP BY 1;` after TC-054-01..03 | `manual` 1 (seed), `ingest` 2 |
| 2 | `SELECT count(*) FROM raw_sessions;` after a failed synchronous run | Includes the new record (never lost) |
| 3 | `SELECT trigger, status, (started_at AT TIME ZONE 'America/Chicago')::date FROM pipeline_runs WHERE trigger='nightly';` | At most one `running`/`succeeded` row per local date |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Duplicate POST | 200 `duplicate`, no run |
| 2 | Synchronous run failure | 201 `pending`, run `failed`, raw row kept |
| 3 | Nightly job outside the hour | Exit 0, no run |
| 4 | Nightly job second invocation the same night | Exit 0, no run |
| 5 | Schema revision mismatch | Exit 1, no run, no migration |
| 6 | A `failed` nightly run earlier the same night, then a firing in the hour | A new nightly run starts (only `running`/`succeeded` block) |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-054-AC-01 | Forced synchronous failure → 201 `pending`, raw row exists, next run sets its status | TC-054-04 |
| FEAT-054-AC-02 | 283 single POSTs equal one batch ingest plus a full run | TC-054-13 |
| FEAT-054-AC-03 | 07:30 UTC in CDT starts exactly one run; second invocation and 08:30 UTC exit 0 without a run | TC-054-08 |
| FEAT-054-AC-04 | Exactly one nightly run per local night across the 1 Nov 2026 DST change | TC-054-09 |
| FEAT-054-AC-05 | `POST /api/v1/ingest` SRC-05 → 202 with non-null `pipeline_run_id`, `succeeded` within 30 s | TC-054-06 |
| FEAT-054-AC-06 | Nightly run adds the new day to `day_ledger` as missing for residents without a record | TC-054-10 |
| FEAT-054-AC-07 | `grep -rn "apscheduler\|NIGHTLY_SCHEDULER_ENABLED" backend` returns nothing | TC-054-12 |

## Test Data Requirements

- DS-07 and an empty roster database (`seed test_v0_1 --master-only`); SRC-05 CSV; synthetic records "R01-new" and "R02-new" derived from SRC-05 rows (study IDs only).
- Environment: `SEED_INGEST_API_KEY`, `SEED_ADMIN_PASSWORD`, `SEED_CLINICIAN_PASSWORD`, `PIPELINE_AS_OF` (non-production only), `NIGHTLY_RUN_HOUR_LOCAL`, `FACILITY_TZ=America/Chicago`, `PIPELINE_PROFILE=test_v0_1`, `DATABASE_URL`.
- No audio; a body containing an audio field is refused by FEAT-025 validation.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-054-FR-01 / ANL-043, API-045, ARC-065 | FEAT-054 | TC-054-01, TC-054-02 |
| FEAT-054-FR-02 / ANL-046, API-135 | FEAT-054 | TC-054-01, TC-054-14 |
| FEAT-054-FR-03 / API-046 | FEAT-054 | TC-054-01 |
| FEAT-054-FR-04 / API-047, NFR-129, D-52 | FEAT-054 | TC-054-04 |
| FEAT-054-FR-05 / API-045 | FEAT-054 | TC-054-03 |
| FEAT-054-FR-06 / ANL-044, API-053 | FEAT-054 | TC-054-06 |
| FEAT-054-FR-07 / API-060, DEP-047 | FEAT-054 | TC-054-07 |
| FEAT-054-FR-08 / API-061, DB-021 (d) | FEAT-054 | TC-054-08, Negative 6 |
| FEAT-054-FR-09 / API-062, ANL-045 | FEAT-054 | TC-054-08 |
| FEAT-054-FR-10 / FR-125, ARC-062 | FEAT-054 | TC-054-10 |
| FEAT-054-FR-11 / ARC-061, DEP-046, AGT-059 | FEAT-054 | TC-054-09, TC-054-12 |
| FEAT-054-FR-12 / DEP-048 | FEAT-054 | TC-054-11 |
| FEAT-054-FR-13 / FR-184, D-67 | FEAT-054 | TC-054-05 |
| FEAT-054-FR-14 / TST-049, AC-ANL-06 | FEAT-054 | TC-054-13 |
| TST-037, TST-052, TST-124 | FEAT-054 | TC-054-04, TC-054-08, TC-054-06 |
| AC-ANL-13 | FEAT-054 | TC-054-08 |
