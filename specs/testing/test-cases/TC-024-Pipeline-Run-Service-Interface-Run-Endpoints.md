# Pipeline run service interface, run endpoints and as-of resolution

## Feature Description

FEAT-024 fixes the single door for every pipeline execution, `backend/services/pipeline_runner.py` (`run(scope, trigger, profile, as_of)`): it resolves `as_of` (explicit → `PIPELINE_AS_OF` outside production → current time), checks the profile (production refuses `test_v0_1` or any profile other than `PIPELINE_PROFILE`), marks runs still `running` 30 minutes after `started_at` as `failed` with warning `run_abandoned`, inserts the `pipeline_runs` row (`running`, `trigger`, `scope`, `config_profile`, `config_snapshot` with the 23 profile keys plus `as_of`, `code_version` = `GIT_SHA`, `started_at`) with audit `pipeline.run.started`, invokes the stage executor and finishes the row (`succeeded` with `counts`, or `failed` with `finished_at`, `error_message`, `warnings`) with audit `pipeline.run.finished`. It exposes E-20 `POST /api/v1/pipeline/run` (admin JWT → `trigger = manual`; `pipeline:run` key → `trigger = nightly`, scope forced to `all`, once per facility-local date; 202 `{pipeline_run_id}`; 404 `RESIDENT_NOT_FOUND`; 409 `PIPELINE_RUN_IN_PROGRESS`; 422 `PROFILE_NOT_ALLOWED` / `VALIDATION_ERROR`), E-31 `GET /api/v1/pipeline/runs` (admin, researcher; newest first; `trigger` and `status` filters; paging; `meta`) and E-21 `GET /api/v1/pipeline/runs/{id}` (404 `PIPELINE_RUN_NOT_FOUND`). Read endpoints take `meta.as_of` from the latest succeeded run.

## Preconditions

- Local development stack running; `.env` from `.env.development.example` (`APP_ENV=local`, `PIPELINE_PROFILE=test_v0_1`, `FACILITY_TZ=America/Chicago`, `GIT_SHA` set, `PIPELINE_AS_OF` empty unless a case sets it, `SEED_*` set).
- Database seeded: `python -m backend.cli seed test_v0_1 --reset` (one succeeded `manual` run with `as_of` 2026-10-30T20:00:00Z).
- Bearer tokens `ADMIN`, `CLIN`, `RES` (passwords from `SEED_*`; distinct `X-Forwarded-For: 203.0.113.<n>` per login or 60 s pause after five logins).
- Keys: `SEED_INGEST_API_KEY` (`ingest:write` + `pipeline:run`); `python -m backend.cli create-api-key --name qa-ingest-only` (scope `ingest:write` only).
- `psql` read access; write steps marked "local only" use the migrator connection (`DATABASE_MIGRATION_URL`) and are followed by `seed test_v0_1 --reset`.
- Runs are executed as a background task: after a 202, poll `GET /api/v1/pipeline/runs/{id}` until `status` is not `running`.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-024-01 | `as_of` precedence: explicit → `PIPELINE_AS_OF` → current time | High | Analytics |
| TC-024-02 | Admin full run returns 202; row `trigger = manual`; started and finished audit rows | High | API |
| TC-024-03 | Run row content: `config_snapshot` (23 keys + `as_of`), `code_version`, `config_profile`, counts | High | Database |
| TC-024-04 | Second request while a full-scope run is `running` returns 409 | High | Negative |
| TC-024-05 | Production refuses `test_v0_1` and foreign profiles with 422 `PROFILE_NOT_ALLOWED` | High | Security |
| TC-024-06 | `pipeline:run` key runs nightly scope `all` once per facility-local date | High | API |
| TC-024-07 | `GET /pipeline/runs`: newest first, `meta`, paging, filters, roles | High | API |
| TC-024-08 | `GET /pipeline/runs/{id}`: known id returns every field; unknown id 404 | High | API |
| TC-024-09 | Run left `running` 31 minutes is abandoned before the next run | High | Database |
| TC-024-10 | Unknown resident in scope 404; invalid bodies 422 | Medium | Negative |
| TC-024-11 | Executor failure ends the run `failed` with `finished_at`, `error_message` and a `failed` finish audit | Medium | Negative |
| TC-024-12 | `meta.as_of` follows the latest succeeded run | High | API |
| TC-024-13 | Resident-scoped admin run and ingest-triggered run go through the same runner | Medium | Positive |
| TC-024-14 | Credential checks on E-20 | High | Security |
| TC-024-15 | Inspection: only the runner creates `pipeline_runs` rows; no global or session-level lock | Medium | Documentation |
| TC-024-16 | Pipeline runs table on the Admin page | Low | UI |

### TC-024-01 `as_of` precedence: explicit → `PIPELINE_AS_OF` → current time

| Step | Action | Expected Result |
|---|---|---|
| 1 | Set `PIPELINE_AS_OF=2026-10-30T15:00:00-05:00` in `.env`; restart the backend | Healthy |
| 2 | As `ADMIN`, `POST /api/v1/pipeline/run` with `{"scope": "all", "as_of": "2026-10-31T00:00:00Z"}`; wait for completion | 202; `GET /api/v1/pipeline/runs/{id}` → `as_of` `2026-10-31T00:00:00Z` |
| 3 | `SELECT as_of, config_snapshot->>'as_of' FROM pipeline_runs WHERE id = '<id>';` | `2026-10-31 00:00:00+00` and an ISO string of the same instant |
| 4 | `POST /api/v1/pipeline/run` with `{"scope": "all"}` (no `as_of`) | Run `as_of` `2026-10-30T20:00:00Z` |
| 5 | Clear `PIPELINE_AS_OF`, restart, post `{"scope": "all"}` | Run `as_of` within a few seconds of the current UTC time |
| 6 | Run `pytest -m integration tests/integration/api/test_pipeline.py -q -k as_of_precedence` | Passes (TST-038; frozen clock) |
| 7 | Restore with `seed test_v0_1 --reset` | Exit code 0 |

### TC-024-02 Admin full run returns 202; row `trigger = manual`; started and finished audit rows

| Step | Action | Expected Result |
|---|---|---|
| 1 | As `ADMIN`, `POST /api/v1/pipeline/run` with `{"scope": "all"}` and `X-Request-ID: qa-run-01` | 202; body `{"pipeline_run_id": "<uuid>"}` and nothing else |
| 2 | Poll `GET /api/v1/pipeline/runs/<uuid>` | `trigger` `manual`; `scope` `"all"`; `status` becomes `succeeded`; `finished_at` set |
| 3 | `SELECT action, actor_type, details FROM audit_logs WHERE entity_id = '<uuid>' ORDER BY id;` | Two rows: `pipeline.run.started` (`actor_type` `user`, `details` keys `trigger` `manual`, `scope`, `profile` `test_v0_1`; `request_id` `qa-run-01`) then `pipeline.run.finished` (`actor_type` `system`, `details` keys `status` `succeeded`, `duration_ms`, `warning_count`) |

### TC-024-03 Run row content: `config_snapshot` (23 keys + `as_of`), `code_version`, `config_profile`, counts

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT status, config_profile, code_version, started_at, finished_at, counts FROM pipeline_runs WHERE id = '<uuid from TC-024-02>';` | `succeeded`; `test_v0_1`; `code_version` = the `GIT_SHA` value; `started_at` < `finished_at`; `counts` a JSON object |
| 2 | `SELECT jsonb_object_keys(config_snapshot) FROM pipeline_runs WHERE id = '<uuid>';` | Includes `as_of`, `baseline_n` (16), `cusum_h` (5.0) and all 23 algorithm keys of the profile (also `config_hash`, DB-020) |
| 3 | `SELECT scope FROM pipeline_runs WHERE id = '<uuid>';` | `{"type": "all"}` (stored form; the DTO shows `"all"`) |
| 4 | Run `pytest -m integration tests/integration/api/test_pipeline.py -q -k run_lifecycle_and_snapshot` | Passes |

### TC-024-04 Second request while a full-scope run is `running` returns 409

| Step | Action | Expected Result |
|---|---|---|
| 1 | Local only, as the migrator: `INSERT INTO pipeline_runs (trigger, scope, status, config_profile, config_snapshot, code_version, started_at, as_of) VALUES ('manual', '{"type":"all"}', 'running', 'test_v0_1', '{}', 'qa', now(), now());` | 1 row |
| 2 | As `ADMIN`, `POST /api/v1/pipeline/run` with `{"scope": "all"}` | 409; `type` `urn:echowell:error:PIPELINE_RUN_IN_PROGRESS`, title `A full pipeline run is in progress`, detail `A full pipeline run is in progress. Try again later.` |
| 3 | `POST` with `{"scope": ["R01"]}` | 409 (any request while a full-scope run is running) |
| 4 | `SELECT count(*) FROM pipeline_runs WHERE status = 'running';` | 1 (no new row created) |
| 5 | Run `pytest -m integration tests/integration/api/test_pipeline.py -q -k full_run_in_progress_is_409`; then `seed test_v0_1 --reset` | Passes; reset done |

### TC-024-05 Production refuses `test_v0_1` and foreign profiles with 422 `PROFILE_NOT_ALLOWED`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `pytest -m integration tests/integration/api/test_pipeline.py -q -k production_refuses_other_profiles` | Passes: with `APP_ENV=production`, `PIPELINE_PROFILE=production`, `{"scope": "all", "profile": "test_v0_1"}` returns 422 `urn:echowell:error:PROFILE_NOT_ALLOWED` (title `Pipeline profile not allowed`, detail `Profile test_v0_1 is not allowed in production.`) and no run row |
| 2 | Locally (`APP_ENV=local`), as `ADMIN` post `{"scope": ["R01"], "profile": "production"}` | 202 (guard applies only in production) |
| 3 | **Hosted** (production, read-only check by the team): `GET /api/v1/pipeline/runs` | No run with `config_profile` `test_v0_1` |

### TC-024-06 `pipeline:run` key runs nightly scope `all` once per facility-local date

| Step | Action | Expected Result |
|---|---|---|
| 1 | `POST /api/v1/pipeline/run` with `X-API-Key: $SEED_INGEST_API_KEY` and `{"scope": ["R01"]}` | 202 with `pipeline_run_id` P1 |
| 2 | `GET /api/v1/pipeline/runs/P1` as `ADMIN` | `trigger` `nightly`; `scope` `"all"` (requested list ignored) |
| 3 | Repeat step 1 on the same facility-local date | 202 with the same id P1 |
| 4 | `SELECT count(*) FROM pipeline_runs WHERE trigger = 'nightly';` | 1 (no new row) |
| 5 | `pipeline.run.started` audit row for P1 | `actor_type` `api_key` |
| 6 | Run `pytest -m integration tests/integration/api/test_pipeline.py -q -k scheduler_key_runs_nightly_once_per_local_date` | Passes |

### TC-024-07 `GET /pipeline/runs`: newest first, `meta`, paging, filters, roles

| Step | Action | Expected Result |
|---|---|---|
| 1 | After TC-024-02 and TC-024-06, as `RES`, `GET /api/v1/pipeline/runs` | 200; keys `meta`, `items`, `total`, `limit` (50), `offset` (0); `items` ordered by `started_at` descending |
| 2 | `GET /api/v1/pipeline/runs?status=failed` | Only items with `status` `failed` (empty list allowed) |
| 3 | `GET /api/v1/pipeline/runs?trigger=nightly` | Only `nightly` items |
| 4 | `GET /api/v1/pipeline/runs?limit=1&offset=1` | 1 item: the second-newest run; `total` unchanged |
| 5 | As `CLIN`, `GET /api/v1/pipeline/runs` | 403 `FORBIDDEN` |
| 6 | `GET /api/v1/pipeline/runs?status=finished` | 422 `INVALID_QUERY_PARAMETER` |

### TC-024-08 `GET /pipeline/runs/{id}`: known id returns every field; unknown id 404

| Step | Action | Expected Result |
|---|---|---|
| 1 | As `ADMIN`, `GET /api/v1/pipeline/runs/<uuid from TC-024-02>` | 200 with `id`, `trigger`, `scope`, `config_profile`, `code_version`, `as_of`, `started_at`, `finished_at`, `status`, `counts`, `warnings`; timestamps end with `Z` |
| 2 | `GET /api/v1/pipeline/runs/00000000-0000-4000-8000-000000000000` | 404; `type` `urn:echowell:error:PIPELINE_RUN_NOT_FOUND`, title `Pipeline run not found`, detail `No pipeline run with this id.` |
| 3 | `GET /api/v1/pipeline/runs/<uuid>` as `CLIN` | 403 |
| 4 | Run `pytest -m integration tests/integration/api/test_pipeline.py -q -k get_run` | Passes |

### TC-024-09 Run left `running` 31 minutes is abandoned before the next run

| Step | Action | Expected Result |
|---|---|---|
| 1 | Local only, as the migrator, insert a resident-scoped running row: `INSERT INTO pipeline_runs (trigger, scope, status, config_profile, config_snapshot, code_version, started_at, as_of) VALUES ('manual', '{"type":"residents","resident_codes":["R01"]}', 'running', 'test_v0_1', '{}', 'qa', now() - interval '31 minutes', now());` and note its id S | 1 row |
| 2 | As `ADMIN`, `POST /api/v1/pipeline/run` with `{"scope": ["R02"]}` | 202 |
| 3 | `SELECT status, finished_at IS NOT NULL, error_message, warnings FROM pipeline_runs WHERE id = 'S';` | `failed`; `true`; `Run abandoned: still running 30 minutes after it started.`; `warnings` contains an item with `code` `run_abandoned` |
| 4 | Backend log | One WARNING `pipeline_run_abandoned` line with `pipeline_run_id` S |
| 5 | Run `pytest -m integration tests/integration/api/test_pipeline.py -q -k stale_running_run_is_abandoned`; then `seed test_v0_1 --reset` | Passes (AC-LOG-06); reset done |

### TC-024-10 Unknown resident in scope 404; invalid bodies 422

| Step | Action | Expected Result |
|---|---|---|
| 1 | As `ADMIN`, post `{"scope": ["R01", "R99"]}` | 404; `type` `urn:echowell:error:RESIDENT_NOT_FOUND`; detail `Unknown resident code(s): R99.`; no run row |
| 2 | Post `{"scope": []}` | 422 `VALIDATION_ERROR` |
| 3 | Post `{"scope": "some"}` | 422 `VALIDATION_ERROR` |
| 4 | Post `{"scope": "all", "profile": "experimental"}` | 422 `VALIDATION_ERROR` (profile enum) |
| 5 | Post `{"scope": "all", "as_of": "2026-10-31T00:00:00"}` (no offset) | 422 `VALIDATION_ERROR` (aware date-time required) |
| 6 | Post `{"scope": "all", "debug": true}` | 422 with `code` `extra_forbidden` |
| 7 | `SELECT count(*) FROM pipeline_runs;` before/after steps 1–6 | Unchanged |

### TC-024-11 Executor failure ends the run `failed` with `finished_at`, `error_message` and a `failed` finish audit

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `pytest -m integration tests/integration/api/test_sessions.py -q -k failed_run_answers_pending` | Passes: with the interim executor the run row ends `failed` with `error_message` `pipeline not available until Phase 6` and `trigger` `ingest`, and `POST /sessions` answers `status_after_processing` `pending` |
| 2 | Run `pytest -m integration tests/integration/pipeline/test_runner_persistence.py -q` | All pass (failure path writes `finished_at` and `pipeline.run.finished` with `details.status` `failed`) |
| 3 | On the local database, `SELECT count(*) FROM pipeline_runs WHERE status = 'failed' AND (finished_at IS NULL OR coalesce(error_message, '') = '');` | 0 |

Note: FEAT-024 is aligned to the TRD (TRD 24 D-184): the run-row lifecycle is covered by the integration tests above (`tests/integration/pipeline/test_runner_persistence.py`, `tests/integration/api/test_sessions.py`); there is no separate unit file.

### TC-024-12 `meta.as_of` follows the latest succeeded run

| Step | Action | Expected Result |
|---|---|---|
| 1 | After the seed, as `CLIN`, `GET /api/v1/residents` | `meta.as_of` `2026-10-30T20:00:00Z` |
| 2 | As `ADMIN`, post `{"scope": "all", "as_of": "2026-10-31T00:00:00Z"}` and wait for `succeeded` | Run succeeded |
| 3 | Repeat step 1 | `meta.as_of` `2026-10-31T00:00:00Z` |
| 4 | Local only (migrator): insert a run with `status` `failed`, `as_of` `2026-11-01 00:00:00+00`, `finished_at` = `started_at` = `now()` and `error_message` `'qa failed run'` (constraints `pipeline_runs_finished_ck` and `pipeline_runs_error_ck` require both), then repeat step 1 | `meta.as_of` still `2026-10-31T00:00:00Z` (failed runs ignored) |
| 5 | `seed test_v0_1 --reset` | Restored |

### TC-024-13 Resident-scoped admin run and ingest-triggered run go through the same runner

| Step | Action | Expected Result |
|---|---|---|
| 1 | As `ADMIN`, post `{"scope": ["R02", "R01"]}` | 202; run `scope` `["R01","R02"]` or the submitted list; `trigger` `manual` |
| 2 | `POST /api/v1/sessions` with `X-API-Key: $SEED_INGEST_API_KEY` and a valid synthetic R02/D02 record (`session_id` `R02-20261031-30`) | 201; body `pipeline_run_id` R |
| 3 | `GET /api/v1/pipeline/runs/R` | Exists; `trigger` `ingest`; `pipeline.run.started` and `pipeline.run.finished` audit rows exist for R |
| 4 | `GET /api/v1/pipeline/runs?trigger=test` | 0 items (the `test` trigger is used only by the automated validation suite) |

### TC-024-14 Credential checks on E-20

| Step | Action | Expected Result |
|---|---|---|
| 1 | `POST /api/v1/pipeline/run` `{"scope": "all"}` as `CLIN` and as `RES` | 403 `FORBIDDEN` each, with an `access.denied` row |
| 2 | Same with `X-API-Key: <qa-ingest-only key>` | 403 `FORBIDDEN` (scope `pipeline:run` missing) |
| 3 | Same without credentials | 401 `NOT_AUTHENTICATED` |

Note: FEAT-024 Testing Requirements are aligned to the TRD (TRD 24 D-184): an `ingest:write` key on E-20 gets 403 `FORBIDDEN` (TRD 05 API-014, TRD 12 §4.6; `backend/api/deps.py:239`).

### TC-024-15 Inspection: only the runner creates `pipeline_runs` rows; no global or session-level lock

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `grep -rn "PipelineRun(" backend --include=*.py` and `grep -rn "INSERT INTO pipeline_runs" backend --include=*.py` | Row creation only in `backend/repositories/pipeline_run_repository.py`, called from `backend/services/pipeline_runner.py` |
| 2 | Run `grep -rn "pg_advisory_lock\b" backend` | No output (the runner takes no session-level or global lock) |

### TC-024-16 Pipeline runs table on the Admin page

| Step | Action | Expected Result |
|---|---|---|
| 1 | Sign in at `http://localhost:3000/login` as `admin@example.com`; open the Admin page | Pipeline runs section lists at most the 50 most recent runs, newest first, with trigger, status and as-of |
| 2 | Sign in as `researcher@example.com` and open `/admin` | Access-denied state "You do not have access to this page." |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `POST /api/v1/pipeline/run` (admin or `pipeline:run` key) | 202 `PipelineRunAccepted` `{pipeline_run_id}` |
| 2 | `POST /api/v1/pipeline/run` error paths | 404 `RESIDENT_NOT_FOUND`; 409 `PIPELINE_RUN_IN_PROGRESS`; 422 `VALIDATION_ERROR` / `PROFILE_NOT_ALLOWED`; 401 / 403 |
| 3 | `GET /api/v1/pipeline/runs` (admin, researcher) | 200 `PipelineRunList` with `meta`, `items`, `total`, `limit`, `offset` |
| 4 | `GET /api/v1/pipeline/runs/{id}` | 200 `PipelineRun`; 404 `PIPELINE_RUN_NOT_FOUND` |
| 5 | `GET /api/v1/openapi.json` | E-20, E-21, E-31 present with schemas `PipelineRunRequest`, `PipelineRunAccepted`, `PipelineRun`, `PipelineRunList` |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT trigger, status, config_profile, code_version FROM pipeline_runs ORDER BY started_at DESC LIMIT 5;` | Values match the API; `code_version` = `GIT_SHA` |
| 2 | `SELECT count(*) FROM pipeline_runs WHERE config_snapshot->>'as_of' IS NULL AND config_snapshot <> '{}';` | 0 |
| 3 | `SELECT action, count(*) FROM audit_logs WHERE action LIKE 'pipeline.run.%' GROUP BY 1;` | `pipeline.run.started` count = `pipeline.run.finished` count for completed runs |
| 4 | `SELECT count(*) FROM pipeline_runs WHERE status = 'running' AND started_at < now() - interval '30 minutes';` after any new run | 0 |
| 5 | `SELECT count(*) FROM pipeline_runs WHERE trigger = 'nightly' AND (started_at AT TIME ZONE 'America/Chicago')::date = (now() AT TIME ZONE 'America/Chicago')::date AND status IN ('running','succeeded');` | ≤ 1 |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Full-scope run in progress | 409 `PIPELINE_RUN_IN_PROGRESS` (TC-024-04) |
| 2 | Unknown resident code in scope | 404 `RESIDENT_NOT_FOUND` (TC-024-10) |
| 3 | Production with `test_v0_1` or another profile | 422 `PROFILE_NOT_ALLOWED` (TC-024-05) |
| 4 | Invalid body | 422 `VALIDATION_ERROR` (TC-024-10) |
| 5 | Unknown run id | 404 `PIPELINE_RUN_NOT_FOUND` (TC-024-08) |
| 6 | Executor raises | Run `failed` with `finished_at`, `error_message` (TC-024-11) |
| 7 | Stale `running` row older than 30 minutes | Marked `failed` with `run_abandoned` (TC-024-09) |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-024-AC-01 | With `PIPELINE_AS_OF=2026-10-30T15:00:00-05:00`, explicit `as_of` 2026-10-31T00:00:00Z is stored; without explicit `as_of`, 2026-10-30T20:00:00Z; with `PIPELINE_AS_OF` unset and a frozen clock, the frozen time | TC-024-01 |
| FEAT-024-AC-02 | Admin `{"scope":"all"}`: 202 with `pipeline_run_id`; row `trigger = manual`; `pipeline.run.started` and `pipeline.run.finished` exist | TC-024-02, TC-024-03 |
| FEAT-024-AC-03 | While a full-scope run is `running`, a second POST returns 409 `PIPELINE_RUN_IN_PROGRESS` | TC-024-04 |
| FEAT-024-AC-04 | `APP_ENV=production`, `PIPELINE_PROFILE=production`, `{"scope":"all","profile":"test_v0_1"}`: 422 `PROFILE_NOT_ALLOWED` | TC-024-05 |
| FEAT-024-AC-05 | `pipeline:run` key with `{"scope":["R01"]}`: run `trigger = nightly`, scope `all`; second request same local date: 202 same id, no new row | TC-024-06 |
| FEAT-024-AC-06 | `GET /pipeline/runs` ordered by `started_at` desc with `meta` and paging; `?status=failed` only failed; researcher 200, clinician 403 | TC-024-07 |
| FEAT-024-AC-07 | Unknown UUID: 404 `PIPELINE_RUN_NOT_FOUND`; known id returns all `PipelineRun` required fields | TC-024-08 |
| FEAT-024-AC-08 | Row left `running` with `started_at` 31 minutes ago is `failed` with `run_abandoned` and non-empty `error_message` after the next run starts | TC-024-09 |

## Test Data Requirements

- `test_v0_1` seed with the seed run (`as_of` 2026-10-30T20:00:00Z, `trigger` `manual`).
- `PIPELINE_AS_OF=2026-10-30T15:00:00-05:00` (TC-024-01 only); explicit `as_of` `2026-10-31T00:00:00Z`.
- Synthetic `pipeline_runs` rows inserted locally for TC-024-04, TC-024-09, TC-024-12 (reset afterwards); unknown codes R99 and UUID `00000000-0000-4000-8000-000000000000`.
- Keys `SEED_INGEST_API_KEY` and `qa-ingest-only`; seeded users with `SEED_*` passwords.
- One synthetic R02/D02 record (`R02-20261031-30`) for the ingest-triggered run.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-024-FR-01 / API-063 / ARC-060 | FEAT-024 | TC-024-02, TC-024-03, TC-024-13, TC-024-15 |
| FEAT-024-FR-02 / LOG-060 | FEAT-024 | TC-024-03, TC-024-04 |
| FEAT-024-FR-03 / API-135 / ARC-068 / ANL-046 / ENV-017 / D-50 / TST-038 | FEAT-024 | TC-024-01 |
| FEAT-024-FR-04 / API-064 | FEAT-024 | TC-024-15 |
| FEAT-024-FR-05 / API-065 / FR-223 | FEAT-024 | TC-024-02, TC-024-14 |
| FEAT-024-FR-06 / API-065 | FEAT-024 | TC-024-04 |
| FEAT-024-FR-07 / API-065 / D-70 | FEAT-024 | TC-024-06 |
| FEAT-024-FR-08 / API-066 / FR-230 | FEAT-024 | TC-024-05 |
| FEAT-024-FR-09 / TRD 19 E-20 | FEAT-024 | TC-024-10 |
| FEAT-024-FR-10 / API-067 / FR-224 | FEAT-024 | TC-024-08 |
| FEAT-024-FR-11 / API-134 / FR-225 / TST-069 | FEAT-024 | TC-024-07, TC-024-16 |
| FEAT-024-FR-12 / API-068 / LOG-066 / AC-LOG-06 | FEAT-024 | TC-024-09 |
| FEAT-024-FR-13 / API-069 | FEAT-024 | TC-024-12 |
| FEAT-024-FR-14 / ANL-046 | FEAT-024 | TC-024-13 |
| Executor failure path (Error Handling) / D-91 | FEAT-024 | TC-024-11 |
