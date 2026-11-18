# OpenAPI contract export and drift check

## Feature Description

FEAT-038 makes the TRD 19 API contract executable. The FastAPI application serves the generated OpenAPI 3.1 document unauthenticated at `/api/v1/openapi.json` (Swagger UI at `/api/v1/docs` only outside production, ReDoc disabled); `python -m backend.cli export-openapi` prints the same document to standard output without opening a database connection; the committed copy `docs/api_reference/openapi.json` is regenerated only with `python -m backend.cli export-openapi > docs/api_reference/openapi.json`. Contract tests fail when the code drifts from the committed file or from the TRD 19 skeleton (`tests/fixtures/trd19_openapi_skeleton.yaml`), when a response does not validate against its schema, when a TRD 19 path is missing or extra, when a list, detail or analytics response lacks `meta`, or when an audio or personal-identity property appears.

## Preconditions

- Local development stack per `README.md` quick start (Python virtual environment with `backend/requirements-dev.txt` installed, including `openapi-spec-validator` 0.7.x and `openapi-core` 0.19.x), working directory = repository root.
- For the HTTP cases: Local Docker Compose (demo profile) running, seeded with `python -m backend.cli seed test_v0_1 --reset`; API at `http://localhost:8000/api/v1`.
- Seeded users and their `SEED_*` passwords from the environment file; tokens obtained with `POST /api/v1/auth/login` (ADMIN_TOKEN, CLINICIAN_TOKEN, RESEARCHER_TOKEN). The ingest API key from the environment file (INGEST_KEY).
- For TC-038-07 and TC-038-12: the PostgreSQL 16 test database used by `pytest tests/integration` (README).
- A random JWT secret for the export command, generated in the shell (`openssl rand -hex 32`), never written down.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-038-01 | `export-openapi` with an unreachable dummy `DATABASE_URL` exits 0 and equals the committed file | High | Positive |
| TC-038-02 | Drift is detected: a differing committed copy makes the diff and the contract test fail | High | Negative |
| TC-038-03 | Committed document and TRD 19 skeleton both validate as OpenAPI 3.1 | High | Documentation |
| TC-038-04 | Document header: `openapi` 3.1.0, title "EchoWell API", version "0.1.0", server `/api/v1`, ReDoc off | High | API |
| TC-038-05 | Path set equals TRD 19 E-01..E-32; `/alerts/{id}/acknowledge` absent | High | API |
| TC-038-06 | Security schemes `bearerAuth` / `apiKeyAuth` attached per operation as in TRD 19 | High | Security |
| TC-038-07 | DTO enums equal the `pg_enum` labels | High | Database |
| TC-038-08 | Non-2xx responses use `application/problem+json`; every response declares `X-Request-ID`; nullable fields always present | High | API |
| TC-038-09 | CSV alternatives on `GET /scores` and `GET /analytics/baselines`; ingest bodies declared via `openapi_extra` | Medium | API |
| TC-038-10 | No audio, name or date-of-birth property in the document | High | Security |
| TC-038-11 | TRD 19 §4.3 examples are included and validate | Low | Documentation |
| TC-038-12 | Every response captured by the integration suite validates against its schema | High | API |
| TC-038-13 | `meta` present with 7 fields on list, detail and analytics responses; absent on `Token`, `User`, `IngestBatchAccepted`, `Alert`, `Health` | High | API |
| TC-038-14 | `/openapi.json` served without credentials; `/docs` 404 in production and 200 in test; Swagger UI renders | High | UI |
| TC-038-15 | Contract suite `pytest -m contract` passes on the delivered commit | High | Positive |

### TC-038-01 export-openapi with an unreachable dummy DATABASE_URL equals the committed file

| Step | Action | Expected Result |
|---|---|---|
| 1 | Make sure no PostgreSQL is reachable at `localhost:5432` for user `x` (e.g. stop the Compose `db` service) | — |
| 2 | Run `APP_ENV=test JWT_SECRET=$(openssl rand -hex 32) DATABASE_URL=postgresql+psycopg://x:x@localhost/x python -m backend.cli export-openapi > /tmp/openapi.json; echo "exit=$?"` | `exit=0`; nothing printed on the terminal except the echo (no log line on stdout) |
| 3 | `python -m json.tool /tmp/openapi.json > /dev/null; echo $?` | `0` (stdout is valid JSON only) |
| 4 | `diff -u docs/api_reference/openapi.json /tmp/openapi.json; echo "diff=$?"` | No diff output; `diff=0` |
| 5 | Run step 2 a second time to `/tmp/openapi2.json` and `cmp /tmp/openapi.json /tmp/openapi2.json` | No output, exit 0 (keys sorted, byte-stable) |

### TC-038-02 Drift is detected

| Step | Action | Expected Result |
|---|---|---|
| 1 | `cp docs/api_reference/openapi.json /tmp/committed_copy.json`; edit `/tmp/committed_copy.json` and change `info.version` to "0.1.1" | Copy differs in one value |
| 2 | `diff -u /tmp/committed_copy.json /tmp/openapi.json; echo "diff=$?"` (with `/tmp/openapi.json` from TC-038-01) | A unified diff showing the `version` line; `diff=1` (CI job `openapi-contract` would fail, CIC-018) |
| 3 | Read `.github/workflows/ci.yml` job `openapi-contract` | It runs `python -m backend.cli export-openapi > /tmp/openapi.json` with a dummy `DATABASE_URL` and fails with the message "The API changed: run 'python -m backend.cli export-openapi > docs/api_reference/openapi.json' and 'cd frontend && npm run gen:api', and commit both (CIC-018)" when the diff is not empty |
| 4 | `git status --short docs/api_reference/openapi.json` after running `export-openapi` in TC-038-01 | No change: the command wrote no file (D-89) |

### TC-038-03 Committed document and TRD 19 skeleton validate as OpenAPI 3.1

| Step | Action | Expected Result |
|---|---|---|
| 1 | `python -c "import json; from openapi_spec_validator import validate; validate(json.load(open('docs/api_reference/openapi.json'))); print('ok')"` | Prints `ok`; no exception |
| 2 | `python -c "import yaml; from openapi_spec_validator import validate; validate(yaml.safe_load(open('tests/fixtures/trd19_openapi_skeleton.yaml'))); print('ok')"` | Prints `ok` |
| 3 | `pytest -m contract tests/contract/test_openapi_contract.py -k valid_openapi_31 -v` | `test_documents_are_valid_openapi_31` PASSED |

### TC-038-04 Document header

| Step | Action | Expected Result |
|---|---|---|
| 1 | `curl -s http://localhost:8000/api/v1/openapi.json \| python -c "import sys,json; d=json.load(sys.stdin); print(d['openapi'], d['info']['title'], d['info']['version'], [s['url'] for s in d['servers']], d['security'])"` | `3.1.0 EchoWell API 0.1.0 ['/api/v1'] []` |
| 2 | Read `info.description` | States the system detects a change relative to the resident's own frozen baseline, "a prompt to check in, not a diagnosis", and "No audio endpoints exist." |
| 3 | `GET http://localhost:8000/api/v1/redoc` | HTTP 404 |
| 4 | Tag names in order | `health, auth, ingest, residents, scores, alerts, devices, analytics, pipeline, admissions, users, config` (equal to the skeleton) |

### TC-038-05 Path set equals TRD 19 E-01..E-32

| Step | Action | Expected Result |
|---|---|---|
| 1 | `python -c "import json; d=json.load(open('docs/api_reference/openapi.json')); ops=[(m,p) for p,v in d['paths'].items() for m in v]; print(len(d['paths']), len(ops)); print(sorted(d['paths']))"` | `29 32`; the paths are exactly `/admissions`, `/admissions/{resident_code}/comparison`, `/alerts`, `/alerts/{id}/reviews`, `/alerts/{id}/snooze`, `/analytics`, `/analytics/baselines`, `/auth/login`, `/auth/logout`, `/auth/me`, `/config/ui`, `/data-alerts`, `/devices`, `/facility/reference-ranges`, `/health`, `/ingest`, `/ingest/batches/{id}`, `/pipeline/run`, `/pipeline/runs`, `/pipeline/runs/{id}`, `/residents`, `/residents/{resident_code}`, `/residents/{resident_code}/checkins`, `/residents/{resident_code}/features`, `/residents/{resident_code}/notes`, `/scores`, `/sessions`, `/users`, `/users/{id}` (relative to server `/api/v1`) |
| 2 | Check for the retired route | `/alerts/{id}/acknowledge` is not in `paths` |
| 3 | `POST http://localhost:8000/api/v1/alerts/<any alert id>/acknowledge` with ADMIN_TOKEN | HTTP 404 or 405 (route not mounted) |
| 4 | `pytest -m contract tests/contract/test_openapi_contract.py -k "path_set or operations_match" -v` | `test_path_set` and `test_operations_match_skeleton` PASSED (paths, methods, operationIds, parameters, request bodies and response status codes equal the skeleton; mounted routes equal `/api/v1` + skeleton paths) |
| 5 | `GET http://localhost:8000/api/v1/openapi.json` | HTTP 200 (served by the framework in addition to the 29 contract paths) |

### TC-038-06 Security schemes attached per operation

| Step | Action | Expected Result |
|---|---|---|
| 1 | Read `components.securitySchemes` | `bearerAuth` = `{"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}`; `apiKeyAuth` = `{"type": "apiKey", "in": "header", "name": "X-API-Key"}`; no other scheme |
| 2 | Read `security` of `POST /ingest` and of `POST /pipeline/run` | `POST /ingest`: `[{"apiKeyAuth": []}, {"bearerAuth": []}]`; `POST /pipeline/run`: `[{"bearerAuth": []}, {"apiKeyAuth": []}]` |
| 3 | Read `security` of `GET /health` and `POST /auth/login` | Empty or absent (no credentials required) |
| 4 | Read `security` of `GET /residents` and `PATCH /users/{id}` | `[{"bearerAuth": []}]` |
| 5 | Compare every operation's `security` with the skeleton (`pytest ... -k operations_match`) | PASSED |

### TC-038-07 DTO enums equal the pg_enum labels

| Step | Action | Expected Result |
|---|---|---|
| 1 | `psql -c "SELECT t.typname, string_agg(e.enumlabel, ',' ORDER BY e.enumsortorder) FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid GROUP BY 1 ORDER BY 1;"` | Includes `alarm_state` = `off,rings,on`; `alert_status` = `open,acknowledged,closed`; `day_status` = `checked_in,missing_resident,missing_device_gap`; `session_status` = `usable,set_aside,quarantined,duplicate`; `user_role` = `admin,clinician,researcher`; `pipeline_run_status` = `running,succeeded,failed`; `pipeline_trigger` = `ingest,nightly,manual,test`; `ingest_source` = `api_single,api_batch,csv_upload,seed`; `review_outcome` = `no_concern,known_cause,referred,data_problem`; `note_type` = `observation,action_taken,follow_up`; `resident_cohort` = `longitudinal,new_admission`; `resident_status` = `active,withdrawn`; `data_alert_status` = `open,resolved` |
| 2 | Read `components.schemas` `AlarmState`, `AlertStatus`, `DayStatus`, `ProcessedStatus`, `Role`, `PipelineStatus`, `PipelineTrigger`, `IngestSource`, `ReviewOutcome`, `NoteType`, `Cohort`, `ResidentStatus`, `DataAlertKind`, `DataAlertStatus` | Each `enum` list equals the matching row of step 1 in the same order |
| 3 | `pytest -m integration tests/integration/db/test_enums.py -v` | `test_dto_enums_equal_pg_enums` PASSED |

### TC-038-08 Problem media type, X-Request-ID and nullable fields

| Step | Action | Expected Result |
|---|---|---|
| 1 | In the document, inspect every response with a status not starting with 2 (except the `GET /health` 503, which is a `Health` body) | Content type is only `application/problem+json`, schema `Problem` (`type`, `title`, `status`, `detail`, `request_id`, `errors` all required) |
| 2 | Inspect the `headers` of every response of every operation | `X-Request-ID` declared on each |
| 3 | `curl -si http://localhost:8000/api/v1/residents` (no token) | HTTP 401; `content-type: application/problem+json`; header `x-request-id` present; body `type` = `urn:echowell:error:NOT_AUTHENTICATED` |
| 4 | `GET /api/v1/alerts?status=open` with ADMIN_TOKEN (DS-07) | Each item contains the keys `snoozed_until`, `snoozed_by`, `last_reviewed_at`, `closed_reason` even when their value is null (nullable fields always present) |
| 5 | In `GET /api/v1/scores?resident_code=R09` read `composite_z` of R09-20261021-01 | 4.288307289401839 (full float precision, not rounded) |

### TC-038-09 CSV alternatives and ingest bodies

| Step | Action | Expected Result |
|---|---|---|
| 1 | Read `paths./scores.get.responses.200.content` and `paths./analytics/baselines.get.responses.200.content` | Both list `application/json` and `text/csv` |
| 2 | Read `paths./ingest.post.requestBody.content` | `application/json` (schema `IngestBatchRequest`, `records` 1..5000 `IngestRecord`) and `multipart/form-data` (part `file`) |
| 3 | Read `paths./sessions.post.requestBody.content` | `application/json` with schema `IngestRecord` (30 required fields from `schema_version` to `mfcc4`) |
| 4 | `GET /api/v1/scores` with RESEARCHER_TOKEN and `Accept: text/csv` | HTTP 200; `content-type` starts with `text/csv` |

### TC-038-10 No audio, name or date-of-birth property

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -o '"[a-z_]*audio[a-z_]*"' docs/api_reference/openapi.json \| sort -u` | Exactly one line: `"audio_quality_flag"` |
| 2 | `grep -c -E '"(dob\|date_of_birth\|birth_date\|first_name\|last_name\|full_name\|audio_url\|recording)"' docs/api_reference/openapi.json` | `0` |
| 3 | Search the paths for "audio" or "recording" | None |
| 4 | List all request-body media types | None starts with `audio/` |
| 5 | `pytest -m contract tests/contract/test_openapi_contract.py -k no_audio -v` | `test_no_audio_or_identity_properties` PASSED |

### TC-038-11 TRD 19 examples are included and validate

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest -m contract tests/contract/test_openapi_examples.py -v` | All tests PASSED |
| 2 | Inspect two examples in the document (e.g. the `Token` and an `Alert` example) | Study IDs only (e.g. `R09`, `D09`); no real token value, password or person name |

### TC-038-12 Every captured integration response validates

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `pytest tests/integration -q` against the test database | All PASSED; 0 failed. `tests/integration/api/conftest.py` installs `check_response` on the `api` client, so every response of the integration API tests is validated against the committed document while the suite runs; a mismatch raises `ContractViolationError` and fails the test |
| 2 | Run `pytest -m contract tests/contract/test_response_schemas.py -v` | `test_valid_responses_pass`, `test_contract_breaks_are_caught`, `test_request_id_header_is_required`, `test_meta_only_where_declared` PASSED (the checker rejects a wrong status, a wrong body, a missing `X-Request-ID` and misplaced `meta`) |
| 3 | Confirm Problem responses are covered | Recorded 401/403/404/409/422 bodies validate against `Problem` |

### TC-038-13 meta presence and absence

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/residents` (list), `GET /api/v1/residents/R09` (detail), `GET /api/v1/analytics` (analytics) with ADMIN_TOKEN on DS-07 | Each body has `meta` with exactly `facility_name` ("Edgewood"), `facility_tz` ("America/Chicago"), `data_source_label` ("pipeline test data v0.1"), `as_of` ("2026-10-30T20:00:00Z"), `baseline_n` (16), `cusum_h` (5.0), `pipeline_profile` ("test_v0_1") |
| 2 | `POST /api/v1/auth/login` (Token) | No `meta` key |
| 3 | `GET /api/v1/health` (Health) | No `meta` key |
| 4 | `POST /api/v1/users` as admin (User, 201) | No `meta` key |
| 5 | `POST /api/v1/alerts/<R09 alert id>/snooze` as clinician, body `{}` (Alert) | No `meta` key |
| 6 | `POST /api/v1/ingest` with `X-API-Key: INGEST_KEY` and one valid synthetic record (IngestBatchAccepted, 202) | No `meta` key |
| 7 | `pytest -m contract tests/contract/test_response_schemas.py -k meta -v` | PASSED |

### TC-038-14 Served document and Swagger UI per environment

| Step | Action | Expected Result |
|---|---|---|
| 1 | `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/openapi.json` (no credentials) | `200` |
| 2 | Compare the served JSON with `docs/api_reference/openapi.json` (`curl -s ... \| python -m json.tool --sort-keys > /tmp/served.json; python -m json.tool --sort-keys docs/api_reference/openapi.json \| diff - /tmp/served.json`) | No difference |
| 3 | Open `http://localhost:8000/api/v1/docs` in a browser (local, `APP_ENV` = local) | Swagger UI page renders with the heading "EchoWell API" and version "0.1.0"; the "Authorize" button offers `bearerAuth` and `apiKeyAuth` |
| 4 | `pytest -m contract tests/contract/test_openapi_contract.py -k served_document -v` | Both parametrisations PASSED: `APP_ENV=production` → `/docs` 404, `APP_ENV=test` → `/docs` 200; `/openapi.json` 200 and `/redoc` 404 in both |
| 5 | **Hosted** (production URL held by the team): `GET <production API>/api/v1/docs` | HTTP 404; `GET <production API>/api/v1/openapi.json` = 200 |

### TC-038-15 Contract suite passes

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest -m contract -q` | All tests PASSED, 0 failed, 0 skipped without a requirement-ID reason |
| 2 | Check `docs/api_reference.md` | Lists every endpoint with its auth and status codes and gives the regeneration command `python -m backend.cli export-openapi > docs/api_reference/openapi.json` |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/openapi.json` without credentials | 200, `application/json`, OpenAPI 3.1.0 document equal to the committed file |
| 2 | `GET /api/v1/docs` | 200 when `APP_ENV` ∈ {local, staging, test}; 404 when `APP_ENV=production` |
| 3 | `GET /api/v1/redoc` | 404 in every environment |
| 4 | Any 4xx/5xx response of the API | `application/problem+json`, `Problem` schema, `X-Request-ID` header |
| 5 | List, detail and analytics responses | `meta` with 7 fields |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `pg_enum` labels per type (TC-038-07) | Equal to the OpenAPI enum lists |
| 2 | `export-openapi` with an unreachable `DATABASE_URL` | Succeeds; no connection attempt (TC-038-01) |

No table is created or modified by this feature.

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Diff the export against a modified committed copy | Diff non-empty, exit 1 (TC-038-02) |
| 2 | `GET /api/v1/docs` with `APP_ENV=production` | 404 (TC-038-14) |
| 3 | `GET /api/v1/redoc` | 404 (TC-038-04) |
| 4 | Call the retired `/alerts/{id}/acknowledge` | 404 or 405; absent from the document (TC-038-05) |
| 5 | Scan for audio / identity properties | Only `audio_quality_flag` (TC-038-10) |
| 6 | Unauthenticated `GET /api/v1/residents` | 401 problem+json with `X-Request-ID` (TC-038-08) |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-038-AC-01 | `export-openapi > /tmp/openapi.json && diff -u docs/api_reference/openapi.json /tmp/openapi.json` exits 0, also with an unreachable dummy `DATABASE_URL` | TC-038-01, TC-038-02 |
| FEAT-038-AC-02 | Committed document and skeleton fixture both validate with `openapi-spec-validator` | TC-038-03 |
| FEAT-038-AC-03 | Path set equals E-01..E-32 (plus `/openapi.json`); `/alerts/{id}/acknowledge` absent | TC-038-05 |
| FEAT-038-AC-04 | Every response captured by `pytest tests/integration -q` validates, including Problem responses | TC-038-12 |
| FEAT-038-AC-05 | List, detail, analytics responses carry `meta` with the 7 fields; `Token`, `User`, `IngestBatchAccepted`, `Alert`, `Health` do not | TC-038-13 |
| FEAT-038-AC-06 | DTO enums and `pg_enum` have identical value sets | TC-038-07 |
| FEAT-038-AC-07 | No property containing `audio` other than `audio_quality_flag`; no resident `name` or `dob` property | TC-038-10 |
| FEAT-038-AC-08 | `/openapi.json` 200 without credentials; `/docs` 404 with `APP_ENV=production`, 200 with `APP_ENV=test` | TC-038-14 |

## Test Data Requirements

- Committed files `docs/api_reference/openapi.json`, `docs/api_reference.md`, `tests/fixtures/trd19_openapi_skeleton.yaml`.
- DS-07 (SRC-05 seeded with `test_v0_1`, as-of 2026-10-30 15:00 America/Chicago) for the HTTP cases; one open R09 alert id.
- Environment variables for the export: `APP_ENV=test`, a generated `JWT_SECRET`, dummy `DATABASE_URL=postgresql+psycopg://x:x@localhost/x`.
- Seeded users and the ingest API key from the environment file.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-038-FR-01 | FEAT-038 | TC-038-04, TC-038-05 |
| FEAT-038-FR-02 | FEAT-038 | TC-038-04, TC-038-14 |
| FEAT-038-FR-03 | FEAT-038 | TC-038-01, TC-038-02 |
| FEAT-038-FR-04 | FEAT-038 | TC-038-05 |
| FEAT-038-FR-05 | FEAT-038 | TC-038-07, TC-038-15 |
| FEAT-038-FR-06 | FEAT-038 | TC-038-08 |
| FEAT-038-FR-07 | FEAT-038 | TC-038-06 |
| FEAT-038-FR-08 | FEAT-038 | TC-038-09 |
| FEAT-038-FR-09 | FEAT-038 | TC-038-10 |
| FEAT-038-FR-10 | FEAT-038 | TC-038-11 |
| FEAT-038-FR-11 | FEAT-038 | TC-038-01, TC-038-05, TC-038-12, TC-038-13, TC-038-15 |
| TRD 19 OAS-001..OAS-016 | FEAT-038 | TC-038-04..TC-038-11 |
| TRD 19 OAS-017 | FEAT-038 | TC-038-13 |
| TRD 19 OAS-018 | FEAT-038 | TC-038-09 |
| TRD 19 OAS-020 | FEAT-038 | TC-038-05 |
| TRD 19 AC-OAS-01, AC-OAS-03, AC-OAS-06, AC-OAS-07 | FEAT-038 | TC-038-03, TC-038-12, TC-038-07, TC-038-10 |
| TRD 05 API-113, API-114 | FEAT-038 | TC-038-14, TC-038-06 |
| TRD 13 TST-060 | FEAT-038 | TC-038-01, TC-038-14 |
| TRD 13 TST-061 | FEAT-038 | TC-038-12 |
| TRD 13 TST-062 | FEAT-038 | TC-038-05 |
| TRD 13 TST-064 | FEAT-038 | TC-038-13 |
| TRD 16 CIC-018 | FEAT-038 | TC-038-02 |
| TRD 25 AGT-061, AC-AGT-11; TRD 24 D-51, D-89 | FEAT-038 | TC-038-01, TC-038-02 |
| FR-015 | FEAT-038 | TC-038-10 |
