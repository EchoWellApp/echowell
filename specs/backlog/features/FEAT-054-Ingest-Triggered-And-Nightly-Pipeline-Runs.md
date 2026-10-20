# FEAT-054 Ingest-triggered and nightly pipeline runs

| Field | Value |
|---|---|
| Epic | Data Processing |
| Build phase | Phase 6 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-053, FEAT-025, FEAT-026 |
| Status | Not Started |

## Purpose

Connect the automatic triggers to the pipeline runner (FEAT-053) so that results appear without manual action: a synchronous resident-scoped run inside `POST /api/v1/sessions`, one background run per batch from `POST /api/v1/ingest`, and the nightly full run started by the separate cron command `python -m backend.jobs.nightly_run`, which proceeds only at 02:xx facility-local time and only once per night (DST-safe, no in-process scheduler). The nightly run extends the day ledger to the new as-of date even when no record arrived.

## Business Context

- BR-01, BR-13 and demo step 5 (SRC-15): a newly ingested usable record shows on the dashboard right after the ingest response (FR-184, D-67).
- BR-06 (missed check-ins are visible): the nightly run records missing days even without new records (FR-125).
- BR-02 (raw data is never lost): a failed synchronous run keeps the record stored and returns `pending` (D-52, R23).
- RSK-07 / D-47: nightly scheduling without an in-process scheduler on the interim Railway stack.
- FRs covered (BACKLOG.md): FR-125, FR-184.

## Referenced TRDs

- TRD 07 ANL-043 (synchronous ingest run), ANL-044 (batch background run), ANL-045 (nightly cron job), ANL-046 (as-of precedence for ingest and nightly runs).
- TRD 05 API-045 (single-record scope), API-046, API-047 (`pending` on failure), API-053 (batch scope and `pipeline_run_id` in the 202), API-060..API-062 (nightly hour, dedupe, full run, exit code), API-135 (as-of resolution).
- TRD 01 ARC-061 (cron service, hour `NIGHTLY_RUN_HOUR_LOCAL`, dedupe, no in-process scheduler), ARC-062 (ledger extended nightly), ARC-065 (co-residents in scope).
- TRD 15 DEP-046, DEP-047 (single dedupe condition), DEP-048 (schema-revision check, no migrations).
- TRD 06 DB-021 (d) (nightly advisory key), DB-022.
- TRD 21 `NIGHTLY_RUN_HOUR_LOCAL` (default 2), `FACILITY_TZ`, `PIPELINE_AS_OF`.
- TRD 13 TST-037, TST-049, TST-052, TST-121, TST-124; TRD 25 AGT-059; TRD 24 D-15, D-47, D-52, D-70.

## Scope

- In the `POST /api/v1/sessions` handler (FEAT-025): after the raw record commits, call `pipeline_runner.run(scope=[resident] ∪ co-assigned residents of the device on the record's local date, trigger="ingest", profile=PIPELINE_PROFILE, as_of=PIPELINE_AS_OF or now)` synchronously, then return `status_after_processing` and `pipeline_run_id`; on run failure return 201 with `pending`.
- In the `POST /api/v1/ingest` handler (FEAT-026): after the batch transaction commits, create the run row and schedule one FastAPI `BackgroundTasks` run scoped to the residents that received a first-arrival record plus their co-assigned residents; return its `pipeline_run_id` in the 202.
- `backend/jobs/nightly_run.py` runnable as `python -m backend.jobs.nightly_run`: facility-local hour gate, once-per-local-date dedupe, nightly advisory lock, full run (`scope = all`, `trigger = nightly`), exit codes, schema-revision check.
- Tests for each trigger including the DST-boundary clock tests.

## Out of Scope

- The runner itself (FEAT-053) and the engine (FEAT-052).
- The ingest validation, duplicate handling and storage of the endpoints (FEAT-025, FEAT-026).
- `POST /api/v1/pipeline/run`, including the scheduler API-key path with `trigger = nightly` and its dedupe (FEAT-024; API-065, D-70).
- The `nightly_run_missing` check, `run_abandoned` handling and retry limits (FEAT-056).
- The Railway Cron Job service definition and AWS EventBridge setup (FEAT-081 and later DevOps features).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-054-FR-01 | After a first-arrival record of `POST /api/v1/sessions` is committed, the backend shall run the pipeline synchronously in the same request with `trigger = ingest` and scope = the record's resident plus every resident with an assignment to the record's device valid on the record's local date. | ANL-043, API-045, ARC-065, DB-022 |
| FEAT-054-FR-02 | The synchronous run's `as_of` shall be `PIPELINE_AS_OF` when set (non-production only), else the current time. | ANL-046, API-135 |
| FEAT-054-FR-03 | On success `POST /api/v1/sessions` shall return 201 with `raw_session_id`, `arrival_seq`, `session_id`, `status_after_processing` ∈ {usable, set_aside, quarantined}, `reasons` and `pipeline_run_id`. | API-046 |
| FEAT-054-FR-04 | If the synchronous run raises, the raw record shall stay stored, the run shall be `failed`, the error logged with the request ID, and the response shall be 201 with `status_after_processing = "pending"`; the next ingest or nightly run processes the record with no manual repair. | ANL-043, API-047, NFR-129, D-52 |
| FEAT-054-FR-05 | A duplicate arrival (200 response) shall not start a run (`pipeline_run_id` null). | API-045 ("first-arrival"); TRD 19 E-05 |
| FEAT-054-FR-06 | After a batch ingest commits, the backend shall create one run (status `running`, `trigger = ingest`) scoped to all residents that received a first-arrival record in the batch plus their co-assigned residents, execute it through FastAPI `BackgroundTasks`, and return its id as `pipeline_run_id` in the 202. | ANL-044, API-053 |
| FEAT-054-FR-07 | `python -m backend.jobs.nightly_run` shall exit 0 without running when the current hour in `FACILITY_TZ` is not `NIGHTLY_RUN_HOUR_LOCAL` (default 2, i.e. 02:00–02:59). | API-060, DEP-047, ANL-045 |
| FEAT-054-FR-08 | The job shall exit 0 without running when a `pipeline_runs` row with trigger `nightly` and status `running` or `succeeded` has `started_at` on the same facility-local date; the run row shall be inserted in a transaction holding `pg_advisory_xact_lock(advisory_key('nightly', <facility-local date>))`. | API-061, DEP-047, DB-021 (d) |
| FEAT-054-FR-09 | Otherwise the job shall run the full pipeline with `scope = all`, `trigger = nightly`, profile `PIPELINE_PROFILE` and as-of per API-135, and exit non-zero when the run fails. | API-062, ANL-045 |
| FEAT-054-FR-10 | The nightly run shall extend `day_ledger` to the new as-of local date so a resident without a record on the previous day gets a missing-day row. | FR-125, ARC-062 |
| FEAT-054-FR-11 | There shall be no in-process scheduler (no APScheduler, no `NIGHTLY_SCHEDULER_ENABLED`); scheduling is the external cron `0 7,8 * * *` UTC, which yields exactly one run per local night across DST changes. | ARC-061, DEP-046, AGT-059, D-47 |
| FEAT-054-FR-12 | The nightly job shall never run `alembic upgrade` and shall exit non-zero when the database schema revision differs from the revision bundled in its image. | DEP-048 |
| FEAT-054-FR-13 | After `POST /api/v1/sessions` returns for a usable record, `GET /api/v1/residents` shall show the record's local time as last check-in and a 30-day `used` count higher by 1, and, when the baseline is frozen, `GET /api/v1/scores` shall contain one more row for that session. | FR-184, D-67 |
| FEAT-054-FR-14 | Ingesting SRC-05 one record at a time in arrival order shall produce derived tables equal to one batch ingest plus a full run with the same as-of. | TST-049, AC-ANL-06 |

## Inputs

- `POST /api/v1/sessions` first-arrival record (committed `raw_sessions` row) and its resident/device assignments.
- `POST /api/v1/ingest` committed batch with its first-arrival resident set.
- Cron invocation of `python -m backend.jobs.nightly_run` with env `FACILITY_TZ`, `NIGHTLY_RUN_HOUR_LOCAL`, `PIPELINE_PROFILE`, `PIPELINE_AS_OF`, `DATABASE_URL`.

## Outputs

- `pipeline_runs` rows with trigger `ingest` or `nightly` and the derived rows written by FEAT-053.
- `IngestResult` with `status_after_processing` and `pipeline_run_id` (E-05); `IngestBatchAccepted.pipeline_run_id` (E-06).
- Nightly job exit code: 0 (ran successfully, wrong hour, or already ran), non-zero (run failed or schema revision mismatch).

## Data Flow

- Single record: device → `POST /sessions` → validate + commit raw row (FEAT-025) → `pipeline_runner.run(scope, "ingest", profile, as_of)` → response 201 (usable/set_aside/quarantined or pending).
- Batch: `POST /ingest` → commit batch (FEAT-026) → create run row → `BackgroundTasks` → `pipeline_runner.run(...)` → poll via `GET /ingest/batches/{id}` / `GET /pipeline/runs/{id}`.
- Nightly: Railway cron 07:00 and 08:00 UTC → `nightly_run` → local-hour check → advisory lock + dedupe check + run row → `pipeline_runner.run("all", "nightly", ...)` → exit code.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-053, FEAT-025, FEAT-026

- FEAT-053 provides `pipeline_runner.run`.
- FEAT-025 provides `POST /api/v1/sessions` and its storage path.
- FEAT-026 provides `POST /api/v1/ingest` and `GET /api/v1/ingest/batches/{id}`.

## Database Impact

- Tables written (through FEAT-053): `pipeline_runs` and all derived tables; no new table or column.
- Tables read by the nightly job: `pipeline_runs` (`trigger`, `status`, `started_at`) for the dedupe; `alembic_version` for the revision check.
- Advisory key `advisory_key('nightly', <facility-local date>)` (TRD 06 DB-021 d).

## API Impact

- `POST /api/v1/sessions` (E-05): fills `status_after_processing` (`usable`, `set_aside`, `quarantined`, `pending`, `duplicate`) and `pipeline_run_id`.
- `POST /api/v1/ingest` (E-06): returns `pipeline_run_id` of the scheduled background run.
- No new endpoint; no change to the OpenAPI contract.

## Frontend Impact

None in code. Pages refetch every 5 minutes (FE-081, FEAT-062/FEAT-065) and therefore show ingest-triggered results; the demo path is verified by E2E-15 (FEAT-076).

## Analytics Impact

None beyond calling the runner; the scope rule (resident plus device co-residents) satisfies the ledger dependency of ANL-016.

## Security Requirements

- `POST /api/v1/sessions` keeps API-key auth with scope `ingest:write`; `POST /api/v1/ingest` keeps key or admin JWT (API-049); the trigger adds no new access path.
- `PIPELINE_AS_OF` is refused when `APP_ENV = production` (startup guard of FEAT-003, AGT-015); the trigger code only reads the resolved value.
- The nightly job connects with `DATABASE_URL` (`echowell_app`) only and never with the migrator role (DEP-048).

## Error Handling

- Synchronous run failure → 201 `pending`, run `failed`, error logged with request ID (API-047); next ingest/nightly run reprocesses (NFR-129).
- Background batch run failure → run row `failed`; the batch stays accepted; visible on `/admin` (FEAT-074) and `GET /pipeline/runs/{id}`.
- Nightly job: outside the hour or already ran → exit 0; run failure or schema mismatch → non-zero exit so the cron platform reports it.
- Concurrent triggers on the same resident serialise through the per-resident advisory lock in FEAT-053.

## Logging Requirements

- Request log of the ingest call carries the request ID; on synchronous failure an ERROR log with request ID and `pipeline_run_id` (API-047, TRD 17).
- Nightly job logs at INFO whether it ran, skipped for the hour, or skipped as already run; run lifecycle events come from FEAT-056.
- Audit rows `pipeline.run.started` / `pipeline.run.finished` are written by the runner (FEAT-053).

## Testing Requirements

- Integration (`tests/integration/pipeline/`, marker `integration`):
  - TST-037: fault-injected synchronous run → 201 `pending`, raw row stored, next run processes it.
  - TST-049: SRC-05 ingested one record at a time via `TestClient` with `time-machine` frozen at 2026-10-30 15:00 America/Chicago equals batch + full run (AC-ANL-06).
  - Batch: SRC-05 CSV → 202 with `pipeline_run_id`, run reaches `succeeded` (TST-124 ≤ 30 s background).
  - FR-184: after one usable POST, `GET /residents` last check-in and `used` count change; when frozen, `GET /scores` gains a row.
- Unit (`tests/unit/backend/jobs/test_nightly_run.py`): TST-052 with injected clock — CDT 07:30 UTC runs once, second invocation exits 0, 08:30 UTC exits 0; CST 08:xx runs and 07:xx exits; DST dates 2026-11-01 and 2027-03-14 (ARC-061, AGT-059); schema-revision mismatch exits non-zero (DEP-048).
- Performance: TST-121 (`POST /sessions` p95 ≤ 1,000 ms, 50 requests on PRs).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-054-AC-01 | With the synchronous pipeline forced to raise, `POST /api/v1/sessions` returns 201 with `status_after_processing: "pending"`, the `raw_sessions` row exists, and the next run sets its processed status. | TST-037; API-047 |
| FEAT-054-AC-02 | 283 single POSTs of SRC-05 in arrival order produce derived tables identical to one batch ingest plus a full run at the same as-of. | TST-049; AC-ANL-06 |
| FEAT-054-AC-03 | `python -m backend.jobs.nightly_run` at 07:30 UTC in CDT starts exactly one nightly run; a second invocation the same night exits 0 without a run; at 08:30 UTC in CDT it exits 0 without a run. | AC-ANL-13; TST-052 |
| FEAT-054-AC-04 | With a frozen clock on both sides of the 1 Nov 2026 DST change, the job produces exactly one nightly run per local night. | AGT-059; ARC-061 |
| FEAT-054-AC-05 | `POST /api/v1/ingest` with SRC-05 returns 202 with a non-null `pipeline_run_id` whose run reaches `succeeded` within 30 s. | API-053; TST-124 |
| FEAT-054-AC-06 | A nightly run on a database whose latest record is from the previous day adds that day to `day_ledger` as `missing_resident` for residents without a record. | FR-125; ARC-062 |
| FEAT-054-AC-07 | No module imports APScheduler and no setting `NIGHTLY_SCHEDULER_ENABLED` exists (`grep -rn "apscheduler\|NIGHTLY_SCHEDULER_ENABLED" backend` returns nothing). | AGT-059; DEP-046 |

## Definition of Done

- All FEAT-054 acceptance criteria pass; `python -m backend.jobs.nightly_run` exits without running outside the facility-local hour `NIGHTLY_RUN_HOUR_LOCAL` (02:xx by default) or when that night already ran (TRD 25 Phase 6 Commands).
- Integration and unit tests above pass; backend coverage ≥ 85 % (TST-141).
- Batch report lists IDs and commands (AGT-022).

## Implementation Notes

- ANL-045, ARC-061, DEP-047 and API-060/LOG-110 all use `NIGHTLY_RUN_HOUR_LOCAL` (default 2, i.e. 02:xx) after the PR #2 consistency fixes; implement the env-driven hour.
- Compute the facility-local hour and date with `zoneinfo.ZoneInfo(FACILITY_TZ)` from an injectable clock; never use a fixed UTC offset (AGT-040).
- The dedupe condition is exactly the one of API-061 / DEP-047 (`running` or `succeeded`, same facility-local date of `started_at`); a `failed` nightly run does not block a later run.
- Create the background run row before returning 202 so the response can carry its id (API-053).
- Keep the scheduler-key path of `POST /api/v1/pipeline/run` (D-70) in FEAT-024; both paths share the same dedupe helper.
