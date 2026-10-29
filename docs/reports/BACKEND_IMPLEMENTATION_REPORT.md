# Backend Implementation Report

Block 3 checkpoint 4 · Prompt: `specs/prompts/Implement_Feature_Batches.md` "Phase 10: Implement Backend Layer" · TRD 25 Phase 5 · Features FEAT-018..FEAT-039 · Branch `feat/cp4-backend-api` · Date: 27 October 2026

This report answers requirement 8 of the Phase 10 prompt. The process report (commands run, exit criteria, deviations and reviewer questions) is `docs/reports/CHECKPOINT_4_BACKEND_API.md`.

The interim stack holds synthetic test data only. No real resident data may be loaded until the AWS environment is approved. Nothing in the backend records, stores or accepts audio, and nothing calls a language model or any other AI service.

## 1. Summary

| Prompt item | Delivered | Where |
|---|---|---|
| FastAPI application | `create_app()` mounts 13 routers under `/api/v1`, the middleware chain of TRD 05 §4.11, the error handlers and the OpenAPI post-processor | `backend/main.py` |
| Route handlers | 32 operations on 29 paths: every TRD 19 endpoint E-01..E-32 and nothing else (`/alerts/{id}/acknowledge` does not exist, D-35) | `backend/api/` |
| Service layer | One service per resource; handlers only parse, authorise and call a service | `backend/services/` |
| Validation layer | Ingest validation of TRD 10 (every violation collected, ING-019), schema-version registry and feature-name map; Pydantic DTOs for every other body | `backend/services/validation.py`, `backend/schemas/` |
| DTOs, request and response schemas | The TRD 19 §4.5 schemas with the same names, properties, types, `required` lists and enums | `backend/schemas/` |
| Error handling | `application/problem+json` with `type` = `urn:echowell:error:<CODE>` (D-48) for every non-2xx response, including 413, 415, 429 and 503 raised in middleware | `backend/core/errors.py`, `backend/core/error_handlers.py`, `backend/core/middleware.py` |
| Logging | One JSON line per event, redaction of secrets and feature values, `X-Request-ID` on every response and log line (LOG-001..LOG-035) | `backend/core/logging.py`, `backend/core/middleware.py` |
| Database integration | Repositories and read models of checkpoint 3; one transaction per request; audit rows in the same transaction as the change | `backend/repositories/`, `backend/api/deps.py` |
| Integration tests | One module per resource, plus contract and security suites (section 5) | `tests/` |
| Match OpenAPI exactly | `docs/api_reference/openapi.json` is generated from the code and compared with the TRD 19 skeleton on every PR; every integration-test response is validated against it | `backend/api/openapi.py`, `tests/contract/` |
| Backlog status | `BACKLOG.md` §10, feature Status fields and roadmap §2.1 refreshed (D-104) | |

## 2. Endpoints

Paths are relative to `/api/v1`. "Key" is an API key in `X-API-Key`; "JWT" is a bearer token. Roles: A admin, C clinician, R researcher.

| Endpoint | operationId | Who may call | Success | Service | Feature |
|---|---|---|---|---|---|
| `GET /health` | getHealth | anyone | 200 (503 `degraded` without the database) | `health_service` | FEAT-003 |
| `POST /auth/login` | login | anyone | 200 | `auth_service` | FEAT-020 |
| `POST /auth/logout` | logout | A C R | 204 | `auth_service` | FEAT-020 |
| `GET /auth/me` | getMe | A C R | 200 | `auth_service` | FEAT-020 |
| `GET /config/ui` | getUiConfig | A C R | 200 | `config_service` | FEAT-030 |
| `POST /sessions` | ingestSession | key `ingest:write` | 201 (200 for a duplicate) | `ingestion` | FEAT-025 |
| `POST /ingest` | ingestBatch | key `ingest:write`, A | 202 | `ingestion` | FEAT-026 |
| `GET /ingest/batches/{id}` | getIngestBatch | A R | 200 | `ingestion` | FEAT-026 |
| `GET /residents` | listResidents | A C R | 200 | `resident_service` | FEAT-027 |
| `GET /residents/{resident_code}` | getResident | A C R | 200 | `resident_service` | FEAT-028 |
| `GET /residents/{resident_code}/checkins` | listCheckinEvents | A C R | 200 | `checkin_service` | FEAT-028 |
| `GET /residents/{resident_code}/features` | getResidentFeatures | A C R | 200 | `feature_service` | FEAT-028 |
| `GET /residents/{resident_code}/notes` | listNotes | A C R | 200 | `note_service` | FEAT-033 |
| `POST /residents/{resident_code}/notes` | createNote | A C | 201 | `note_service` | FEAT-033 |
| `GET /devices` | listDevices | A C R | 200 | `device_service` | FEAT-029 |
| `GET /alerts` | listAlerts | A C R | 200 | `alert_service` | FEAT-030 |
| `GET /alerts/{id}/reviews` | listAlertReviews | A C R | 200 | `review_service` | FEAT-031 |
| `POST /alerts/{id}/reviews` | createAlertReview | A C | 201 | `review_service` | FEAT-031 |
| `POST /alerts/{id}/snooze` | snoozeAlert | A C | 200 | `alert_service` | FEAT-031 |
| `GET /data-alerts` | listDataAlerts | A C R | 200 | `data_alert_service` | FEAT-032 |
| `GET /scores` | listScores | A C R (CSV: A R) | 200 | `score_service`, `export_service` | FEAT-034 |
| `GET /analytics/baselines` | listBaselines | A R | 200 | `score_service`, `export_service` | FEAT-034 |
| `GET /analytics` | getAnalytics | A R | 200 | `analytics_summary` | FEAT-035 |
| `GET /admissions` | listAdmissions | A C R | 200 | `admission_service` | FEAT-036 |
| `GET /admissions/{resident_code}/comparison` | getAdmissionComparison | A C R | 200 | `admission_service` | FEAT-036 |
| `GET /facility/reference-ranges` | listReferenceRanges | A C R | 200 | `admission_service` | FEAT-036 |
| `POST /pipeline/run` | startPipelineRun | A, key `pipeline:run` | 202 | `pipeline_service`, `pipeline_runner` | FEAT-024 |
| `GET /pipeline/runs` | listPipelineRuns | A R | 200 | `pipeline_service` | FEAT-024 |
| `GET /pipeline/runs/{id}` | getPipelineRun | A R | 200 | `pipeline_service` | FEAT-024 |
| `GET /users` | listUsers | A | 200 | `user_service` | FEAT-037 |
| `POST /users` | createUser | A | 201 | `user_service` | FEAT-037 |
| `PATCH /users/{id}` | updateUser | A | 200 | `user_service` | FEAT-037 |

`GET /openapi.json` is served without login in every environment; Swagger UI (`/docs`) only in local, staging and test.

## 3. How a request is handled

1. Middleware, outermost first: request context (`X-Request-ID`, access log, security headers, HSTS when deployed); body limits (64 KB, 5 MB on `POST /ingest`; 413) and media types (415, including any `audio/*` body on any method); CORS for the configured origins only; then the rate limiter (300 requests a minute per caller by default; login 5 and ingest 600 a minute; 429 with `Retry-After`).
2. The route's `authorize("<METHOD> <path>")` dependency reads the TRD 12 §4.6 matrix (`backend/api/permissions.py`), checks the JWT or API key against the database (role and `active` come from the database, not the token), and writes an `access.denied` audit row for every 403.
3. The handler validates the body (Pydantic, or the ingest validator for raw ingest bodies), calls one service and returns a DTO. Lists and details carry `meta` (facility, time zone, data label, as-of, baseline size, alarm threshold, profile), built once per request (D-32).
4. Errors become problem+json in `error_handlers.py`; 500 responses never contain internal details.

The analytics pipeline is not part of this checkpoint. `POST /sessions`, `POST /ingest` and `POST /pipeline/run` start runs through one interface (`PipelineRunner`, D-91). Until checkpoint 5 its interim executor fails each run with "pipeline not available until Phase 6", so new arrivals report `status_after_processing: "pending"` (D-52).

## 4. Decisions made while building

| Topic | What was done | Why |
|---|---|---|
| OpenAPI document | FastAPI generates it; `backend/api/openapi.py` applies the TRD 19 conventions (relative paths, per-operation security from the role matrix, shared error responses, `X-Request-ID` everywhere, `allOf: [PageMeta, …]` lists) | the code stays the single source, and the document still matches the skeleton |
| Named schema types | Code and enum types (`ResidentCode`, `SessionId`, `ReviewOutcome`, …) are Python `type` aliases, which become named `components/schemas` entries | FEAT-038-FR-05: every skeleton schema exists by name, which the frontend's generated types rely on |
| Optional request fields | `UserUpdate`, `SnoozeRequest.hours` and `PipelineRunRequest.profile` may be left out but not sent as `null` | their TRD 19 schemas have no `null` type |
| Audio | Any request with an `audio/*` content type is refused with 415 before routing, including GETs | TST-133 asks for 415 or 422 on every endpoint |
| Rate-limit middleware | Own ASGI middleware instead of slowapi's, which re-sent the response start for each streamed chunk (CSV export) | streaming exports work and 429 is problem+json |
| CSV export | `Accept: text/csv` on `GET /scores` and `GET /analytics/baselines`; 100,000-row limit (413); one `export.csv` audit row | API-129, OAS-018 |
| Batch → pipeline run | `ingest_batches.pipeline_run_id` (migration 0003), written when a batch starts a run and read by `GET /ingest/batches/{id}`; the `ingest.batch.received` audit row keeps the id too | TRD 24 D-124 (review round 1) |
| Answer key | Read only by `analytics_summary.py`, only under profile `test_v0_1`, through a separate read-only engine; never in production | API-136, TST-068 |

## 5. Tests

| Suite | Files | What it shows |
|---|---|---|
| Unit | `tests/unit/backend/…` (services, validation, schemas, import boundaries) | rules that need no database |
| Integration | `tests/integration/api/` (one module per resource), `tests/integration/pipeline/test_concurrent_ingest.py`, `tests/integration/db/test_enums.py`, CLI tests | every endpoint: auth, role checks, 422 shapes, pagination limits, audit rows, `meta` |
| Contract | `tests/contract/` | the generated document equals the committed file, is valid OpenAPI 3.1 and matches the TRD 19 skeleton; every integration-test response validates against it |
| Security | `tests/security/` | every cell of TRD 13 Table 4.13-A with its exact status; token and key attacks; no audio on any route; CORS; study IDs only in responses, logs and CSV; static scans of schemas, columns and dependencies |

Results are in `CHECKPOINT_4_BACKEND_API.md` §4.

## 6. Backlog status

FEAT-018..FEAT-039 are implemented and verified and are marked Complete in this PR (TRD 24 D-104), with two parts that later checkpoints fill by design:

- `GET /analytics` returns empty `kpis`, `daily_series`, `funnel` and `by_resident` blocks, and `GET /alerts` returns an empty `leaning_most`, until checkpoint 5 (FEAT-051, D-92).
- Values stated on the full test_v0_1 seed are re-checked when FEAT-055 loads it (checkpoint 5).
