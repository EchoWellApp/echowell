# Checkpoint 4 Report — Phase 10 Implement Backend Layer

Block 3 "Implement Features", checkpoint 4 of 9, its own PR (branch `feat/cp4-backend-api`, built on `feat/cp3-database` while GitHub PR #17 is in review; `main` is merged in before the PR is opened) · Prompt: `specs/prompts/Implement_Feature_Batches.md` "Phase 10: Implement Backend Layer" · TRD 25 Phase 5 · Features: FEAT-018..FEAT-039 · Date: 27 October 2026 · Status: ready for review.

Build order followed roadmap §5.4: [FEAT-018, FEAT-019] → [FEAT-020, FEAT-021, FEAT-022] → [FEAT-023..FEAT-026] → [FEAT-027..FEAT-029] → [FEAT-030..FEAT-033] → [FEAT-034..FEAT-037] → [FEAT-038, FEAT-039], one commit (or two) per group. TRDs read in the roadmap order: 05, 19, 10, 12, 17, 23, 09, then SRC-21 and `docs/design/`.

The interim stack holds synthetic test data only. No endpoint accepts or returns audio, and nothing calls a language model or other AI service.

## 1. What was built

The endpoint-by-endpoint account is `docs/reports/BACKEND_IMPLEMENTATION_REPORT.md`. In short:

| Group | Features | Delivered |
|---|---|---|
| 1 | FEAT-018, FEAT-019 | JSON logging with redaction and request IDs; problem+json errors; middleware for request context, body limits, media types, security headers and CORS; the `meta` block |
| 2 | FEAT-020..FEAT-022 | Login, logout, `me`; JWT and API-key checks against the database; the TRD 12 §4.6 role matrix as one table with an `access.denied` audit row per 403; rate limits (login 5, ingest 600, others 300 a minute) |
| 3 | FEAT-023..FEAT-026 | Ingest validation (all violations collected), schema-version registry, feature-name map checked at startup; `POST /sessions`, `POST /ingest` (JSON batch or CSV), `GET /ingest/batches/{id}`; the pipeline-run interface and run endpoints |
| 4 | FEAT-027..FEAT-029 | Residents overview with the wireframe v0.2 fields and default sort (D-109, D-114), resident detail, check-in log (incl. `checkins_started`), features, devices |
| 5 | FEAT-030..FEAT-033 | Alerts list, UI configuration, reviews, snooze, data alerts and the `resolve-data-alert` CLI, staff notes |
| 6 | FEAT-034..FEAT-037 | Scores and baselines with CSV export, the analytics summary (answer key read only under `test_v0_1` through a read-only engine), the new-admissions endpoints, user management |
| 7 | FEAT-038, FEAT-039 | The OpenAPI document generated from the code and committed; contract tests; the security and privacy suite |

`POST /api/v1/alerts/{id}/acknowledge` does not exist (D-35). `GET /analytics` returns its four aggregate blocks empty and `GET /alerts` returns `leaning_most` empty until FEAT-051 (checkpoint 5, D-92).

## 2. Files

Created: routers `backend/api/{auth,ingest,pipeline,devices,config,scores,admissions,users,permissions,responses,openapi}.py`; `backend/core/{error_handlers,logging,middleware,rate_limit}.py`; services `backend/services/{auth,alert,review,data_alert,note,config,resident,checkin,feature,device,score,export,admission,user,pipeline,meta}_service.py`, `pipeline_runner.py`, `analytics_summary.py`; the DTO modules in `backend/schemas/`; `docs/api_reference/openapi.json`; `tests/contract/`, `tests/security/`, one integration module per resource under `tests/integration/api/`, `tests/integration/pipeline/test_concurrent_ingest.py`, `tests/integration/db/test_enums.py`; the SRC-05 and SRC-06 test fixtures and the TRD 19 skeleton fixture; this report and `BACKEND_IMPLEMENTATION_REPORT.md`.

Changed (several were empty skeleton files from checkpoint 2): `backend/api/{alarms,analytics,deps,health,residents,sessions}.py`, `backend/services/{validation,ingestion,audit_service}.py`, `backend/main.py`, `backend/cli.py` (`resolve-data-alert`, `export-openapi`), `backend/core/{config,db,errors,security}.py`, `backend/core/common_passwords.txt` (one line, Q-6), `backend/repositories/` (read-model and list helpers), `analytics/config.py` (the 19 feature specs), `backend/requirements.txt` (PyJWT, slowapi, limits, python-multipart), `backend/requirements-dev.txt` (openapi-spec-validator, PyYAML), `.github/workflows/ci.yml` (contract and security tests in `backend-test`), `docs/api_reference.md`; TRD 12 v0.13 (`ingest.batch.received` details add `pipeline_run_id`, Q-1) and TRD 19 v0.8 (three YAML quoting fixes so the skeleton parses); `BACKLOG.md` §10, roadmap §2.1, FEAT-018..FEAT-039 Status fields.

Size: about 21,600 added lines, of which 5,950 are the generated `openapi.json` and 2,100 test fixtures copied from `specs/` (SRC-05, SRC-06, TRD 19 skeleton). Hand-written: about 7,800 backend lines and 5,700 test lines. Above the GIT-034 guideline of about 1,500 lines (Q-14).

## 3. Tests added

| Area | Files | Covers |
|---|---|---|
| Logging, errors, middleware | `tests/integration/api/test_http_middleware.py`, `test_health.py`, unit tests under `tests/unit/backend/core/` | FEAT-018, FEAT-019 acceptance criteria; 503 `degraded` without the database |
| Auth, roles, rate limits | `test_auth.py`, `test_role_checks.py`, `test_rate_limits.py`, `tests/integration/test_auth_coverage.py` | FEAT-020..FEAT-022; TST-131 |
| Ingest and pipeline | `test_sessions.py`, `test_ingest.py`, `test_pipeline.py`, `tests/integration/pipeline/test_concurrent_ingest.py`, `tests/unit/backend/services/test_validation.py` | FEAT-023..FEAT-026; duplicate = 200 `duplicate`; withdrawn resident 422; SRC-06 legacy file refused; `pending` while the interim executor fails runs |
| Read APIs | `test_residents.py`, `test_devices.py`, `test_alerts.py`, `test_notes.py`, `test_config_ui.py`, `test_scores.py`, `test_analytics.py`, `test_admissions.py`, `test_users.py` | FEAT-027..FEAT-037; audit rows for login, logout, ingest batch, note and review; role checks |
| Boundaries | `tests/unit/backend/test_no_outbound_alerts.py`, `test_ground_truth_boundary.py`, `test_import_boundary.py` | no outbound alerting; the answer key only in `analytics_summary.py` |
| Contract | `tests/contract/test_openapi_contract.py`, `test_response_schemas.py`, `response_validation.py`, `tests/integration/db/test_enums.py` | TST-060..TST-064; every integration API response is validated against the document |
| Security | `tests/security/test_auth_matrix.py`, `test_tokens.py`, `test_api_keys.py`, `test_no_audio.py`, `test_cors.py`, `test_data_minimisation.py`, `test_static_scans.py` | TST-130, TST-132..TST-134, TST-137; FEAT-039 static scans |

## 4. Commands run and results

Environment: Linux container, Python 3.12 (virtualenv), PostgreSQL 16 (local cluster provisioned with `database/roles/provision_login_roles.sql`).

| # | Command | Result |
|---|---|---|
| 1 | `pytest tests/unit tests/integration tests/contract tests/security tests/validation` | 450 passed, 2 skipped (the two skips name FEAT-055 and the Phase 6 stage tests) |
| 2 | Same, random order, seeds 101, 505 and 606 (groups 1–6) | all passed |
| 3 | `pytest … --cov=analytics --cov=backend --cov-branch` | 450 passed, 2 skipped; line and branch coverage of `analytics` and `backend` together 97 % (5,898 statements; lowest file `backend/alembic/env.py` 77 %, its online-migration path) |
| 4 | `ruff check .`; `ruff format --check .`; `mypy analytics backend`; `lint-imports` | all exit 0; 3 import contracts kept |
| 5 | `python -m backend.cli export-openapi > /tmp/openapi.json && diff -u docs/api_reference/openapi.json /tmp/openapi.json` (dummy, unreachable `DATABASE_URL`) | no difference |
| 6 | `uvicorn backend.main:create_app --factory`, then `curl -fsS http://localhost:8000/api/v1/health` | `{"status":"ok","database":"ok",…}`; `/openapi.json` 200; `/residents` without login 401; an `audio/wav` body 415 |
| 7 | Case-insensitive grep for the forbidden facility name (AGT-019) | no match |

CI change: the `backend-test` job now also runs `tests/contract` and `tests/security`. The separate `openapi-contract` job of TRD 16 (CIC-018) is still added by FEAT-078, as the `ci.yml` header says; until then the drift check runs inside `backend-test` (`test_generated_equals_committed`).

## 5. Exit criteria (roadmap §5.4)

| Criterion | Evidence | Result |
|---|---|---|
| Every TRD 19 endpoint under `/api/v1` with the documented auth, status codes and schemas; `/api/v1/openapi.json` equals the committed file | `test_openapi_contract.py` (path set, operations, schemas against the skeleton; served document equals the committed one); every integration response validated | PASS |
| Ingest stores accepted arrivals (duplicates too) and rejects invalid ones (incl. SRC-06) with 422 into `ingest_rejections` | `test_sessions.py`, `test_ingest.py` | PASS |
| `meta` on every list, detail and analytics response | the response checker (TST-064) on every integration response | PASS |
| `POST /alerts/{id}/acknowledge` does not exist | `test_path_set` | PASS |
| `GET /analytics` without the four aggregate blocks and `GET /alerts` without `leaning_most`, filled in checkpoint 5 | `test_analytics.py`, `test_alerts.py` | PASS (by design, D-92) |
| Wireframe v0.2 API additions (D-114) | `test_residents.py`, `test_devices.py`, `test_alerts.py` | PASS |
| `POST /pipeline/run` with an admin JWT or a `pipeline:run` key; one service interface | `test_pipeline.py`, `test_auth_matrix.py` | PASS |
| Security suite TST-130..TST-137 | `tests/security/` (TST-131 in `test_rate_limits.py`; TST-135 and TST-136 belong to FEAT-086 and FEAT-078) | PASS |
| Backend line coverage ≥ 85 % (TST-141) | item 3 | PASS (97 %) |
| GIT-034 size ≤ about 1,500 lines | about 13,500 hand-written lines | NOT MET (Q-14) |
| CI green on the PR head | needs the PR | PENDING |

## 6. New OQ and D IDs

None. Decisions from this review will be recorded in TRD 24 with the next free numbers.

## 7. Deviations and notes

| # | Note | Handling |
|---|---|---|
| N-1 | slowapi's ASGI middleware re-sent the response start for every chunk of a streamed CSV | our own `RateLimitMiddleware` around the slowapi `Limiter` (slowapi 0.1.9 is still the limiter, API-102) |
| N-2 | TST-005 suggests time-machine for clock control; after a travel it left `time.monotonic` on a wall-clock base and psycopg connections timed out at random | tests override the application clock (`get_clock`) instead; the expired-token test builds the token with an explicit issue time |
| N-3 | TRD 19 §4.5 skeleton had three YAML quoting errors and did not parse | quoted in TRD 19 (v0.8) and in the fixture; no content change |
| N-4 | Pydantic flattens inherited list models and writes integer bounds as floats | `backend/api/openapi.py` writes lists as `allOf: [PageMeta, …]` and bounds as integers, so the document matches the skeleton |
| N-5 | The document names a few nested objects that the skeleton writes inline (`UserRef`, `Period`, `AlarmsRaised`, `BaselinesFormed`, `SetAsideReasons`, `ByOutcome`, `ComparisonFeature`, `PipelineRunWarning`) | the contract test compares them field by field; generated frontend types get names for them |
| N-6 | `UserUpdate`, `SnoozeRequest.hours` and `PipelineRunRequest.profile` accepted `null`; their TRD 19 schemas have no `null` | they may be left out but an explicit `null` is now 422 (Q-10) |
| N-7 | A GET with an `audio/wav` body returned 200 (GET handlers ignore bodies) | any `audio/*` content type is refused with 415 before routing (Q-11) |
| N-8 | Library pins: slowapi 0.1.9, PyJWT 2.9.0, argon2-cffi 23.1.0, python-multipart 0.0.17 (TRD 05 §6, TRD 12 §6); openapi-core 0.19.4 and openapi-spec-validator 0.7.1 for the contract tests (TRD 13) | match the TRD versions |

## 8. Questions for the reviewer

| ID | Question |
|---|---|
| Q-1 | Batch → pipeline run: the link is stored in the `ingest.batch.received` audit details (`pipeline_run_id`), not in a new `ingest_batches.pipeline_run_id` column. Keep it that way, or add the column? |
| Q-2 | `device_assignment_mismatch`: FEAT-026-FR-16 says the pipeline raises it; TRD 10's table lists it as an ingest warning. I followed the feature file. Correct? |
| Q-3 | A record whose device does not match the API key's device is refused with code `device_key_mismatch`, which is not in the ING-023 code list. Add it to ING-023? |
| Q-4 | Check-in date range: counted inclusively, so at most 366 days. Correct? |
| Q-5 | Until checkpoint 5, `config_hash` is computed over all 23 configuration keys of the profile. Correct? |
| Q-6 | AC-SEC-05 uses `password1234` as a common password, but it is not in the SecLists file chosen in D-121. I added it to the bundled list (marked "EchoWell additions"). Keep that, or change the AC-SEC-05 example instead? |
| Q-7 | Before any pipeline run has succeeded, `meta.as_of` is null and read endpoints use today's date on the application clock. Correct? |
| Q-8 | `LAST_ADMIN` (409) cannot be reached through HTTP, because the caller is always an active admin and may not demote themselves (SEC-044). It is tested at service level. Is that enough? |
| Q-9 | Every route can return 413, 415 (body checks) and 429 (default rate limit), but TRD 19 declares them only on a few operations. Add them to every operation in TRD 19, or treat them as global like 500 and 503? |
| Q-10 | Optional request fields (`UserUpdate`, snooze `hours`, run `profile`) now refuse an explicit `null` with 422. Agree? |
| Q-11 | Any request with an `audio/*` content type now gets 415, GETs included. Agree? |
| Q-12 | TRD 13 Table 4.13-A has no rows for `POST /auth/login`, `GET /config/ui` and `GET /openapi.json`; the matrix test covers them from the TRD 12 §4.6 matrix. Add the three rows to Table 4.13-A? |
| Q-13 | FEAT-038-FR-10 (Should): the TRD 19 §4.3 JSON examples are not yet attached as OpenAPI `examples`. Add them in checkpoint 5, or drop the item? |
| Q-14 | Size: about 13,500 hand-written lines (7,800 backend, 5,700 tests) for 22 features. Accept as one PR, as for checkpoints 2 and 3? |
