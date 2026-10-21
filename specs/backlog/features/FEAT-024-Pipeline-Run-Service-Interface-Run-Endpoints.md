# FEAT-024 Pipeline run service interface, run endpoints and as-of resolution

| Field | Value |
|---|---|
| Epic | Backend API |
| Build phase | Phase 5 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-021, FEAT-011 |
| Status | Not Started |

## Purpose

Fix, before the analytics engine exists, the one door through which every pipeline execution passes: `services.pipeline_runner.run(scope, trigger, profile, as_of)`, with its run-row lifecycle, as-of precedence, profile guard, abandoned-run handling and audit events; and expose the operator endpoints `POST /api/v1/pipeline/run`, `GET /api/v1/pipeline/runs` and `GET /api/v1/pipeline/runs/{id}`. Ingest, nightly, manual and CLI triggers all call this interface; Phase 6 (FEAT-053) fills in the stage execution and persistence behind it.

## Business Context

- BR-15: every run is reproducible and recorded with profile, config snapshot, code version, as-of, counts and warnings (ARC-060, API-063).
- BR-02 / BR-15: admins (or the scheduler key) can trigger full or resident-scoped runs (FR-223); admins and researchers can inspect runs (FR-224, FR-225).
- D-01 / D-50: the `test_v0_1` profile and a fixed as-of are never used in production (FR-230, API-066).

## Referenced TRDs

- TRD 05 API-063..API-069, API-134, API-135, API-061 (nightly dedupe referenced by API-065).
- TRD 19 §4.3 E-20, E-21, E-31; schemas `PipelineRunRequest`, `PipelineRunAccepted`, `PipelineRun`, `PipelineRunList`.
- TRD 07 ANL-046.
- TRD 21 ENV-017.
- TRD 01 ARC-060, ARC-068.
- TRD 17 LOG-060, LOG-066; AC-LOG-06.
- TRD 23 §4.2.10 (`pipeline_runs` attributes, `counts` keys, `warnings` shape).
- TRD 02 FR-223..FR-225, FR-230.
- TRD 13 TST-038, TST-069.
- TRD 24 D-43, D-50, D-70.

## Scope

- `backend/services/pipeline_runner.py`:
  - `run(scope, trigger, profile, as_of) -> PipelineRunHandle` — the single entry point; resolves `as_of` (explicit → `PIPELINE_AS_OF` outside production → current time), checks the profile, marks abandoned runs, inserts the `pipeline_runs` row (`running`, `trigger`, `scope` JSON, `config_profile`, `config_snapshot` with all 23 keys plus `as_of`, `code_version` = `GIT_SHA`, `started_at`), writes `pipeline.run.started`, invokes the stage executor, then updates the row (`succeeded` with `counts`, or `failed` with `finished_at`, `error_message`, `warnings`) and writes `pipeline.run.finished`.
  - Pluggable stage executor interface (`execute(run, scope, config, as_of) -> ExecutorResult`) that FEAT-053 implements; until then the default (interim) executor ends the run `failed` with `error_message` "pipeline not available until Phase 6", so `POST /api/v1/sessions` returns `status_after_processing: "pending"` and every caller's failure path is exercised (TRD 25 Phase 5, TRD 24 D-91, D-52).
  - `resolve_as_of(explicit, settings, clock)` shared by every trigger and the seed command.
  - `abandon_stale_runs(now)`: any `running` row older than 30 minutes is marked `failed` with warning `{"code": "run_abandoned", …}` and a non-empty `error_message` before a new run proceeds.
  - Helpers `latest_succeeded_as_of()` (used by FEAT-019 `get_meta()`), `full_run_in_progress()`, `nightly_run_for_local_date(date)`.
- `backend/api/pipeline.py`:
  - `POST /api/v1/pipeline/run` (E-20): admin JWT (`trigger = manual`) or API key with scope `pipeline:run` (`trigger = nightly`, scope forced to `all`, once-per-night dedupe returning 202 with the existing run id); body `PipelineRunRequest` (`scope`: `"all"` or a non-empty list of resident codes; optional `profile`; optional `as_of`); unknown resident code → 404 `RESIDENT_NOT_FOUND`; full-scope run running → 409 `PIPELINE_RUN_IN_PROGRESS`; production with `test_v0_1` or a profile ≠ `PIPELINE_PROFILE` → 422 `PROFILE_NOT_ALLOWED`; starts the run as a FastAPI background task; returns 202 `PipelineRunAccepted`.
  - `GET /api/v1/pipeline/runs` (E-31): admin, researcher; optional `trigger` and `status` filters; pagination; newest first; `PipelineRunList` with `meta`.
  - `GET /api/v1/pipeline/runs/{id}` (E-21): admin, researcher; `PipelineRun`; unknown id → 404 `PIPELINE_RUN_NOT_FOUND`.
- DTOs in `backend/schemas/pipeline.py`.

## Out of Scope

- Loading raw records and frozen baselines, calling `analytics.pipeline.run_pipeline`, per-resident transactions with advisory locks, natural-key upserts, counts and warnings content (FEAT-053).
- Ingest-triggered and nightly triggers and the cron job (FEAT-054); the CLI `run-pipeline`, `rebuild`, `set-config` (FEAT-055).
- Pipeline log events `pipeline_run_succeeded`, stage warnings and operational alerts (FEAT-056).
- Admin page pipeline-runs table (FEAT-074).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-024-FR-01 | Every pipeline invocation (ingest, nightly, manual, test) shall go through `services.pipeline_runner.run(scope, trigger, profile, as_of)`, which creates the `pipeline_runs` row, stores `config_snapshot` (including `as_of`), `code_version` = `GIT_SHA`, `counts`, `warnings`, and writes `pipeline.run.started` and `pipeline.run.finished`. | API-063, ARC-060 |
| FEAT-024-FR-02 | The run row shall be inserted with status `running`, `config_profile`, `config_snapshot`, `code_version` and `started_at` before the first stage executes. | LOG-060 |
| FEAT-024-FR-03 | The run's `as_of` shall be resolved as explicit `as_of` in `POST /pipeline/run` → `PIPELINE_AS_OF` (non-production only) → current time, and stored in `config_snapshot.as_of` and `pipeline_runs.as_of`; ingest and nightly runs use `PIPELINE_AS_OF` if set (non-production), else the current time. | API-135, ARC-068, ANL-046, ENV-017, D-50 |
| FEAT-024-FR-04 | Runs shall serialise with each other only through per-resident transaction-scoped advisory locks in ascending `resident_code` order (applied by the executor, FEAT-053); this interface takes no session-level or global lock. | API-064 |
| FEAT-024-FR-05 | `POST /api/v1/pipeline/run` shall accept an admin JWT or an API key with scope `pipeline:run`, accept `{scope, profile?, as_of?}`, start the run as a background task and return 202 `{pipeline_run_id}`. | API-065, FR-223, ANL-046 |
| FEAT-024-FR-06 | It shall return 409 `PIPELINE_RUN_IN_PROGRESS` when a full-scope run is running. | API-065 |
| FEAT-024-FR-07 | A request authenticated by a `pipeline:run` key shall always run scope `all` with `trigger = nightly` and, when a nightly run with status `running` or `succeeded` already exists for the facility-local date, start nothing and return 202 with that run's id; admin JWT requests record `trigger = manual`. | API-065, D-70 |
| FEAT-024-FR-08 | With `APP_ENV=production`, a `profile` of `test_v0_1` or any profile different from `PIPELINE_PROFILE` shall return 422 `PROFILE_NOT_ALLOWED`. | API-066, FR-230 |
| FEAT-024-FR-09 | A scope list containing an unknown resident code shall return 404 `RESIDENT_NOT_FOUND`. | TRD 19 E-20 |
| FEAT-024-FR-10 | `GET /api/v1/pipeline/runs/{id}` (admin, researcher) shall return the `PipelineRun` DTO (trigger, scope, profile, code version, as-of, start/finish, status, counts, warnings); an unknown id returns 404 `PIPELINE_RUN_NOT_FOUND`. | API-067, FR-224 |
| FEAT-024-FR-11 | `GET /api/v1/pipeline/runs` (admin, researcher) shall list runs newest first with optional `trigger` and `status` filters and pagination. | API-134, FR-225 |
| FEAT-024-FR-12 | A run still `running` 30 minutes after `started_at` when the next run starts shall be marked `failed` with warning code `run_abandoned` and a non-empty `error_message` before the new run proceeds. | API-068, LOG-066 |
| FEAT-024-FR-13 | Read endpoints shall obtain their reference date from the `as_of` of the most recent `succeeded` run (helper used by `get_meta()`). | API-069 |
| FEAT-024-FR-14 | The `test` trigger value shall be used only by the automated validation suite. | ANL-046 |

## Inputs

- `PipelineRunRequest` JSON; admin JWT or `pipeline:run` key principal; settings `APP_ENV`, `PIPELINE_PROFILE`, `PIPELINE_AS_OF`, `GIT_SHA`, `FACILITY_TZ`; `config_parameters` of the profile; existing `pipeline_runs` rows.

## Outputs

- `pipeline_runs` rows and their status transitions; audit rows `pipeline.run.started`, `pipeline.run.finished`; 202/200/404/409/422 responses.

## Data Flow

`POST /pipeline/run` → auth (FEAT-020/021) → resolve trigger from credential → validate scope (resident codes exist) and profile (production guard) → check full-scope run in progress (409) or nightly dedupe (202 existing id) → schedule background task → 202. Background task → `run()` → abandon stale runs → resolve `as_of` → load profile config → insert run row (`running`) + `pipeline.run.started` → executor (FEAT-053) → update row `succeeded`/`failed` + `pipeline.run.finished`. `GET /pipeline/runs` and `/{id}` read the rows.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-021, FEAT-011

- FEAT-021 provides `require_roles` and the admin-or-`pipeline:run` composite permission for E-20 and admin/researcher for E-21/E-31.
- FEAT-011 provides the `pipeline_runs` table and JSON shape models for `scope`, `config_snapshot`, `counts`, `warnings`.

Features that build directly on this one (BACKLOG.md §4): FEAT-025, FEAT-038, FEAT-053, FEAT-074.

## Database Impact

- Tables written: `pipeline_runs` (INSERT, UPDATE), `audit_logs` (`pipeline.run.started`, `pipeline.run.finished`).
- Tables read: `pipeline_runs`, `config_parameters`, `residents` (scope validation).
- Tables created or modified (schema): none.

## API Impact

- Exposed: E-20 `POST /api/v1/pipeline/run` (202; 404 `RESIDENT_NOT_FOUND`, 409 `PIPELINE_RUN_IN_PROGRESS`, 422 `VALIDATION_ERROR`/`PROFILE_NOT_ALLOWED`), E-31 `GET /api/v1/pipeline/runs` (200 `PipelineRunList`), E-21 `GET /api/v1/pipeline/runs/{id}` (200 `PipelineRun`; 404 `PIPELINE_RUN_NOT_FOUND`).
- Provides the as-of helper used for `meta.as_of` on all read endpoints.

## Frontend Impact

None in code; `/admin` (FEAT-074) lists the 50 most recent runs and triggers runs through these endpoints.

## Analytics Impact

None computed here. The config snapshot handed to the executor is the input of `analytics.pipeline.run_pipeline` (FEAT-052, FEAT-053).

## Security Requirements

- E-20: admin JWT or API key with scope `pipeline:run` only (TRD 12 §4.6); E-21/E-31: admin and researcher.
- Production cannot run `test_v0_1` or a foreign profile (API-066) and cannot use a fixed as-of (startup guard, FEAT-003).
- Run rows never contain record content (`error_message` is a summary, TRD 23 §4.2.10).

## Error Handling

| Condition | Response / behaviour |
|---|---|
| Full-scope run in progress | 409 `PIPELINE_RUN_IN_PROGRESS` |
| Unknown resident code in scope | 404 `RESIDENT_NOT_FOUND` |
| Production with `test_v0_1` or other profile | 422 `PROFILE_NOT_ALLOWED` |
| Invalid body | 422 `VALIDATION_ERROR` |
| Unknown run id | 404 `PIPELINE_RUN_NOT_FOUND` |
| Executor raises | Run `failed` with `finished_at`, non-empty `error_message`; `pipeline.run.finished` written with `status = failed` |
| Stale `running` row (> 30 min) | Marked `failed` with `run_abandoned` before the new run |

## Logging Requirements

- Audit: `pipeline.run.started` (actor user, api_key or system; details `trigger`, `scope`, `profile`) and `pipeline.run.finished` (actor system; details `status`, `duration_ms`, `warning_count`) (TRD 12 §4.12).
- Log context `pipeline_run_id` (and `request_id` when started by a request, LOG-034) set for the run.
- Detailed run log events are FEAT-056.

## Testing Requirements

- Integration (`tests/integration/api/test_pipeline.py`): TST-038 (explicit `as_of` wins over `PIPELINE_AS_OF`, which wins over current time; `meta.as_of` equals the latest succeeded run's `as_of`); TST-069 (`GET /pipeline/runs` newest first); E-20 202 for admin and `pipeline:run` key, 403 for clinician/researcher, 401 for `ingest:write` key; 409 when a full-scope run is `running`; 422 `PROFILE_NOT_ALLOWED` with `APP_ENV=production` and `profile=test_v0_1`; 404 for unknown resident in scope and unknown run id; scheduler dedupe returns the existing nightly run id.
- Integration: AC-LOG-06 (a run left `running` 31 minutes ago is marked `failed` with `run_abandoned` on the next run).
- Unit (`tests/unit/backend/services/test_pipeline_runner.py`): run-row lifecycle with a stub executor (success and failure), audit actions written, `config_snapshot` contains 23 keys plus `as_of`.

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-024-AC-01 | With `PIPELINE_AS_OF=2026-10-30T15:00:00-05:00`, a run triggered with explicit `as_of` 2026-10-31T00:00:00Z stores that explicit value; a run without explicit `as_of` stores 2026-10-30T20:00:00Z; with `PIPELINE_AS_OF` unset and the clock frozen, the frozen time is stored. | TST-038, API-135, D-50 |
| FEAT-024-AC-02 | `POST /api/v1/pipeline/run {"scope":"all"}` as admin returns 202 with a `pipeline_run_id`; the run row has `trigger = manual`; audit rows `pipeline.run.started` and `pipeline.run.finished` exist for it. Verified by: Integration (`tests/integration/api/test_pipeline.py`). | API-063, API-065, FR-223 |
| FEAT-024-AC-03 | While a full-scope run is `running`, a second `POST` returns 409 `PIPELINE_RUN_IN_PROGRESS`. Verified by: Integration (`tests/integration/api/test_pipeline.py`). | API-065 |
| FEAT-024-AC-04 | With `APP_ENV=production` and `PIPELINE_PROFILE=production`, `{"scope":"all","profile":"test_v0_1"}` returns 422 `PROFILE_NOT_ALLOWED`. Verified by: Integration (`tests/integration/api/test_pipeline.py`). | API-066, FR-230 |
| FEAT-024-AC-05 | A `pipeline:run` key request with `{"scope":["R01"]}` creates a run with `trigger = nightly` and scope `all`; a second such request on the same facility-local date returns 202 with the same run id and creates no new row. Verified by: Integration (`tests/integration/api/test_pipeline.py`). | API-065, D-70 |
| FEAT-024-AC-06 | `GET /api/v1/pipeline/runs` returns runs ordered by `started_at` descending with `meta` and paging fields; `?status=failed` returns only failed runs; a researcher gets 200 and a clinician 403. | API-134, TST-069, FR-225 |
| FEAT-024-AC-07 | `GET /api/v1/pipeline/runs/{unknown-uuid}` returns 404 `PIPELINE_RUN_NOT_FOUND`; a known id returns all `PipelineRun` required fields. Verified by: Integration (`tests/integration/api/test_pipeline.py`; TST-038). | API-067, FR-224 |
| FEAT-024-AC-08 | A `pipeline_runs` row left `running` with `started_at` 31 minutes ago is `failed` with a `run_abandoned` warning and non-empty `error_message` after the next run starts. Verified by: Integration (AC-LOG-06 (a run left `running` 31 minutes ago is marked `failed` with `run_abandoned` on the next run)). | AC-LOG-06, API-068 |

## Definition of Done

- All FEAT-024 acceptance criteria pass; E-20, E-21, E-31 appear in the OpenAPI document with the TRD 19 schemas.
- No other module creates `pipeline_runs` rows (grep check); delivered in the Phase 5 checkpoint of PR #3, satisfying TRD 25 §4.6 Phase 5 "pipeline invocation goes through one service interface that Phase 6 fills".

## Implementation Notes

- FastAPI `BackgroundTasks` is acceptable at ASM-08 scale; do not add Celery, Redis or a queue (TRD 01 §8).
- The scheduler dedupe query (`trigger = nightly`, status `running` or `succeeded`, facility-local date of `started_at`) is shared with the cron job of FEAT-054 (API-061); keep it in the runner service.
- Persist `scope` as `{"type": "all"}` or `{"type": "residents", "resident_codes": [...]}` (TRD 23 §4.5) and convert to `"all"` / list in the DTO (TRD 19 `PipelineRun.scope`).
- In-process tests freeze the clock with `time-machine` (ARC-068); never call `datetime.now()` outside the injected clock.
