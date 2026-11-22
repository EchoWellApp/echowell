# API error model, HTTP middleware and response metadata

## Feature Description

FEAT-019 gives every endpoint the same outer contract: one RFC 7807 `application/problem+json` error body `{type, title, status, detail, request_id, errors}` with `type` = `urn:echowell:error:<CODE>` from the closed TRD 05 §4.7 catalogue; exception handlers that never leak internals (500 detail "An unexpected error occurred."; `OperationalError` → 503 `SERVICE_UNAVAILABLE` with `Retry-After: 30`; SQLSTATE `EW001` → 500 with an `error` log naming the table); exact-origin CORS (API-101); security headers (API-106); request-size limits (64 KB, 5 MB for `POST /api/v1/ingest`, 413 `PAYLOAD_TOO_LARGE`); the media-type guard (JSON everywhere, a single CSV part only on `POST /api/v1/ingest`, `audio/*` and others 415 `UNSUPPORTED_MEDIA_TYPE`); the shared list envelope `{meta, items, total, limit, offset}`; ISO date and range validation (`from` > `to` → 422 `INVALID_QUERY_PARAMETER`); and the `meta` block `{facility_name, facility_tz, data_source_label, as_of, baseline_n, cusum_h, pipeline_profile}` whose `as_of` is the latest succeeded pipeline run.

## Preconditions

- Local development stack running; `.env` from `.env.development.example` (`APP_ENV=local`, `PIPELINE_PROFILE=test_v0_1`, `FACILITY_TZ=America/Chicago`, `DATA_SOURCE_LABEL=pipeline test data v0.1`, `CORS_ORIGINS=http://localhost:3000`, `CORS_ORIGIN_REGEX` empty, `SEED_*` set).
- Database seeded: `python -m backend.cli seed test_v0_1 --reset` (one succeeded run with `as_of` 2026-10-30T20:00:00Z).
- Bearer tokens of `admin@example.com`, `clinician@example.com`, `researcher@example.com` (passwords from `SEED_*`); ingest key from `SEED_INGEST_API_KEY`.
- `curl -i` against `http://localhost:8000/api/v1`; Python 3.12 virtual environment for pytest and REPL steps.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-019-01 | Forced exception returns the generic 500 Problem with the request ID | High | Negative |
| TC-019-02 | Unknown path 404 `NOT_FOUND` and wrong method 405 `METHOD_NOT_ALLOWED` | High | API |
| TC-019-03 | Unknown body property returns 422 `extra_forbidden` without echoing input | High | API |
| TC-019-04 | Validation `errors[]` field paths drop the `body`/`query` segment | Medium | API |
| TC-019-05 | Database stopped returns 503 `SERVICE_UNAVAILABLE` with `Retry-After: 30` | High | Negative |
| TC-019-06 | 64 KB body limit (413) and 5 MB ingest limit | High | API |
| TC-019-07 | Media-type guard: `audio/wav` and other types return 415 and store nothing | High | Security |
| TC-019-08 | CORS: allowed origin echoed with exposed headers; other origins get no allow header | High | Security |
| TC-019-09 | Security headers on every response; HSTS only in staging and production | High | Security |
| TC-019-10 | `meta` block values under `test_v0_1` | High | API |
| TC-019-11 | `meta.as_of` is null before any succeeded run | Medium | API |
| TC-019-12 | `from` later than `to` returns 422 `INVALID_QUERY_PARAMETER` | High | Negative |
| TC-019-13 | List envelope and pagination bounds | Medium | API |
| TC-019-14 | Timestamp serialisation: UTC `Z`, `*_local` with offset, `local_date` `YYYY-MM-DD` | Medium | API |
| TC-019-15 | Query patterns and enums are validated | Medium | Negative |
| TC-019-16 | Error catalogue in code equals TRD 05 §4.7; append-only violation logs the table | Medium | Positive |
| TC-019-17 | CSV cells starting with `=`, `+`, `-`, `@` are kept as data | Low | Security |
| TC-019-18 | Problem bodies never contain internals | High | Security |

### TC-019-01 Forced exception returns the generic 500 Problem with the request ID

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `pytest -m integration tests/integration/api/test_http_middleware.py -q -k unhandled_exception_is_a_generic_500` | Test passes (AC-LOG-08) |
| 2 | Alternatively in a REPL: build the app with `create_app(settings)`, add a temporary route that raises `RuntimeError("qa boom /tmp/x.py")`, call it through `TestClient(app, raise_server_exceptions=False)` with `X-Request-ID: qa-err-500-01` | Status 500; `Content-Type: application/problem+json` |
| 3 | Inspect the body | `{"type": "urn:echowell:error:INTERNAL_ERROR", "title": "Internal error", "status": 500, "detail": "An unexpected error occurred.", "request_id": "qa-err-500-01", "errors": []}`; no `qa boom`, no `/tmp/x.py`, no `Traceback`, no library version |
| 4 | Compare the `X-Request-ID` response header with `request_id` | Equal |

### TC-019-02 Unknown path 404 `NOT_FOUND` and wrong method 405 `METHOD_NOT_ALLOWED`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `curl -i http://localhost:8000/api/v1/does-not-exist` | 404; `Content-Type: application/problem+json`; `type` `urn:echowell:error:NOT_FOUND`, `title` `Not found`, `detail` `The requested resource does not exist.`, `errors` `[]` |
| 2 | `curl -i -X DELETE http://localhost:8000/api/v1/residents` | 405; `type` `urn:echowell:error:METHOD_NOT_ALLOWED`, `title` `Method not allowed`, `detail` `This method is not allowed on this path.`, `errors` `[]` |
| 3 | Run `pytest tests/unit/backend/core/test_errors.py -q` | All tests pass (TST-034) |

### TC-019-03 Unknown body property returns 422 `extra_forbidden` without echoing input

| Step | Action | Expected Result |
|---|---|---|
| 1 | `POST /api/v1/auth/login` with `Content-Type: application/json` and body `{"email": "admin@example.com", "password": "x-qa-probe", "remember_me": "qa-echo-probe"}` | 422; `type` `urn:echowell:error:VALIDATION_ERROR`, `title` `Validation failed` |
| 2 | Inspect `errors` | One item `{"field": "remember_me", "code": "extra_forbidden", "message": …}`; no item has an `input` key; the string `qa-echo-probe` and the password value appear nowhere in the body |
| 3 | As the clinician, `POST /api/v1/residents/R01/notes` with `{"note_type": "observation", "body": "QA synthetic note", "colour": "red"}` | 422 with an `errors[]` item `field` `colour`, `code` `extra_forbidden`; no note created |

### TC-019-04 Validation `errors[]` field paths drop the `body`/`query` segment

| Step | Action | Expected Result |
|---|---|---|
| 1 | `POST /api/v1/auth/login` with body `{"email": "admin@example.com"}` | 422 `VALIDATION_ERROR`; `errors` contains `{"field": "password", "code": "missing", …}` (not `body.password`) |
| 2 | As admin, `POST /api/v1/pipeline/run` with `{"scope": []}` | 422 `VALIDATION_ERROR`; one `errors[]` item whose `field` starts with `scope` |
| 3 | `POST /api/v1/auth/login` with an invalid JSON body `{"email":` | 422 `VALIDATION_ERROR` Problem body (no stack trace) |

### TC-019-05 Database stopped returns 503 `SERVICE_UNAVAILABLE` with `Retry-After: 30`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Obtain an admin token, then run `docker compose stop db` | Database stopped |
| 2 | `curl -i -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/residents` | 503; `Retry-After: 30`; `type` `urn:echowell:error:SERVICE_UNAVAILABLE`, `title` `Service unavailable`, `detail` `The database is not reachable. Try again shortly.` |
| 3 | `curl -i http://localhost:8000/api/v1/health` | 503 with the `Health` body of FEAT-003 (not a Problem body; API-111) |
| 4 | `docker compose start db`; wait for healthy; repeat step 2 | 200 |

### TC-019-06 64 KB body limit (413) and 5 MB ingest limit

| Step | Action | Expected Result |
|---|---|---|
| 1 | Create a 65,537-byte JSON file: `python -c "open('big.json','w').write('{\"pad\":\"' + 'x'*65527 + '\"}')"`; check with `wc -c big.json` | `65537 big.json` |
| 2 | `curl -i -X POST -H "Content-Type: application/json" --data-binary @big.json http://localhost:8000/api/v1/auth/login` | 413; `type` `urn:echowell:error:PAYLOAD_TOO_LARGE`, `title` `Payload too large`, `detail` `The request body is larger than 64 KB.` |
| 3 | Same body sent with chunked transfer (`-H "Transfer-Encoding: chunked"`, no `Content-Length`) | 413 `PAYLOAD_TOO_LARGE` (streamed byte count checked) |
| 4 | As admin, `POST /api/v1/ingest` with a JSON batch of about 1 MB (synthetic records) | Not 413 (accepted by the size guard; outcome decided by ingest validation) |
| 5 | `POST /api/v1/ingest` with a body of 5,242,881 bytes | 413 with `detail` `The request body is larger than 5120 KB.` |
| 6 | Delete `big.json` | Removed |

### TC-019-07 Media-type guard: `audio/wav` and other types return 415 and store nothing

| Step | Action | Expected Result |
|---|---|---|
| 1 | Record `SELECT count(*) FROM raw_sessions;` and `SELECT count(*) FROM ingest_rejections;` | Baselines R and J |
| 2 | `curl -i -X POST -H "X-API-Key: $SEED_INGEST_API_KEY" -H "Content-Type: audio/wav" --data-binary "RIFF0000WAVE" http://localhost:8000/api/v1/sessions` (a 12-byte synthetic header, not a recording) | 415; `type` `urn:echowell:error:UNSUPPORTED_MEDIA_TYPE`; `detail` `Audio is never accepted.` |
| 3 | Same with `Content-Type: audio/wav` on `POST /api/v1/ingest` as admin | 415 |
| 4 | `POST /api/v1/auth/login` with `Content-Type: text/plain` and a body | 415; `detail` `Send application/json.` |
| 5 | `POST /api/v1/sessions` with `Content-Type: multipart/form-data` | 415; `detail` `Send application/json.` (multipart only on `/ingest`) |
| 6 | Re-count | Still R and J (nothing stored) |

### TC-019-08 CORS: allowed origin echoed with exposed headers; other origins get no allow header

| Step | Action | Expected Result |
|---|---|---|
| 1 | `curl -i -X OPTIONS -H "Origin: http://localhost:3000" -H "Access-Control-Request-Method: GET" -H "Access-Control-Request-Headers: Authorization" http://localhost:8000/api/v1/residents` | 200; `Access-Control-Allow-Origin: http://localhost:3000`; `Access-Control-Allow-Methods` lists `GET, POST, PATCH, OPTIONS`; `Access-Control-Max-Age: 600`; no `Access-Control-Allow-Credentials: true` |
| 2 | `GET /api/v1/health` with `Origin: http://localhost:3000` | `Access-Control-Allow-Origin: http://localhost:3000`; `Access-Control-Expose-Headers` contains `X-Request-ID`, `Retry-After`, `X-EchoWell-Experimental` |
| 3 | Preflight with `Origin: https://evil.example.org` | No `Access-Control-Allow-Origin` header |
| 4 | Preflight with `Origin: http://localhost:3000.evil.example.org` | No `Access-Control-Allow-Origin` header (exact match only) |
| 5 | Run `pytest -m integration tests/integration/api/test_http_middleware.py -q -k cors` and `pytest -m security tests/security/test_cors.py -q` | All pass (TST-134; staging regex honoured only when `CORS_ORIGIN_REGEX` is set) |

### TC-019-09 Security headers on every response; HSTS only in staging and production

| Step | Action | Expected Result |
|---|---|---|
| 1 | `curl -i http://localhost:8000/api/v1/health`, `GET /api/v1/residents` (200 with token), `GET /api/v1/does-not-exist` (404) | Each response has `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Cache-Control: no-store` |
| 2 | Check `Strict-Transport-Security` on the local responses | Absent (`APP_ENV=local`) |
| 3 | Run `pytest -m integration tests/integration/api/test_http_middleware.py -q -k security_headers_and_hsts` | Passes: with `APP_ENV=staging` responses carry `Strict-Transport-Security: max-age=31536000; includeSubDomains` |
| 4 | **Hosted**: `curl -I` the staging API health URL | `Strict-Transport-Security: max-age=31536000; includeSubDomains` plus the four headers of step 1 |

### TC-019-10 `meta` block values under `test_v0_1`

| Step | Action | Expected Result |
|---|---|---|
| 1 | As the clinician, `GET /api/v1/residents` | `meta` = `{"facility_name": "Demo Facility", "facility_tz": "America/Chicago", "data_source_label": "pipeline test data v0.1", "as_of": "2026-10-30T20:00:00Z", "baseline_n": 16, "cusum_h": 5.0, "pipeline_profile": "test_v0_1"}` |
| 2 | `GET /api/v1/residents/R09` and, as the researcher, `GET /api/v1/analytics` | Same `meta` values in both responses |
| 3 | `SELECT as_of FROM pipeline_runs WHERE status = 'succeeded' ORDER BY started_at DESC LIMIT 1;` | `2026-10-30 20:00:00+00` = `meta.as_of` |
| 4 | Open the resident list in the browser | Header shows "Showing pipeline test data v0.1 as of …" with Oct 30, 2026, 3:00 PM CT |

### TC-019-11 `meta.as_of` is null before any succeeded run

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `python -m backend.cli seed test_v0_1 --reset --master-only` (no pipeline run) | Exit code 0 |
| 2 | As the clinician, `GET /api/v1/residents` | 200; `meta.as_of` = `null` (not the current time); other `meta` fields as in TC-019-10 |
| 3 | Restore with `python -m backend.cli seed test_v0_1 --reset` | Exit code 0 |

### TC-019-12 `from` later than `to` returns 422 `INVALID_QUERY_PARAMETER`

| Step | Action | Expected Result |
|---|---|---|
| 1 | As the clinician, `GET /api/v1/scores?from=2026-10-20&to=2026-10-10` | 422; `type` `urn:echowell:error:INVALID_QUERY_PARAMETER`, `title` `Invalid query parameter`, `detail` `'from' must not be later than 'to'` |
| 2 | `GET /api/v1/residents/R09/checkins?from=2026-10-20&to=2026-10-10` | 422 `INVALID_QUERY_PARAMETER` |
| 3 | `GET /api/v1/scores?from=2026-10-10&to=2026-10-20` | 200 |
| 4 | `GET /api/v1/scores?from=2026-13-01` | 422 `INVALID_QUERY_PARAMETER` with an `errors[]` item for `from` |

### TC-019-13 List envelope and pagination bounds

| Step | Action | Expected Result |
|---|---|---|
| 1 | As the clinician, `GET /api/v1/residents?limit=3&offset=0` | Top-level keys include `meta`, `items`, `total`, `limit`, `offset`; `total` 10, `limit` 3, `offset` 0, 3 items |
| 2 | `GET /api/v1/residents?limit=0` | 422 `INVALID_QUERY_PARAMETER`, detail `limit must be between 1 and 500` |
| 3 | `GET /api/v1/residents?limit=501` and `?offset=-1` | 422 `INVALID_QUERY_PARAMETER` (`offset must be 0 or greater` for the second) |
| 4 | `GET /api/v1/devices` | Same envelope keys; `total` 10 |

### TC-019-14 Timestamp serialisation: UTC `Z`, `*_local` with offset, `local_date` `YYYY-MM-DD`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/residents/R09` | `last_checkin_at` ends with `Z`; `last_checkin_local` ends with `-05:00`; `alarm_since` `2026-10-21` (`YYYY-MM-DD`) |
| 2 | `GET /api/v1/scores?resident_code=R09` | Every `local_date` matches `^\d{4}-\d{2}-\d{2}$` |

### TC-019-15 Query patterns and enums are validated

| Step | Action | Expected Result |
|---|---|---|
| 1 | As the clinician, `GET /api/v1/scores?resident_code=r09` | 422 `INVALID_QUERY_PARAMETER` (pattern `^[A-Z0-9]{1,16}$`) |
| 2 | As admin, `GET /api/v1/pipeline/runs?status=finished` | 422 `INVALID_QUERY_PARAMETER` (enum) |
| 3 | As admin, `GET /api/v1/pipeline/runs/not-a-uuid` | 422 (UUID path parameter) Problem body |
| 4 | `GET /api/v1/residents/R99` | 404 `RESIDENT_NOT_FOUND` |

### TC-019-16 Error catalogue in code equals TRD 05 §4.7; append-only violation logs the table

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `pytest tests/unit/backend/core/test_errors.py -q -k "catalogue_equals_trd_05 or every_app_error_uses_a_catalogue_code or append_only_refusal_names_the_table"` | All pass: `CATALOGUE` in `backend/core/errors.py` holds exactly the 36 TRD 05 §4.7 codes with fixed status and title; an `EW001` refusal maps to 500 `INTERNAL_ERROR` and logs `append_only_violation` with the table name |

### TC-019-17 CSV cells starting with `=`, `+`, `-`, `@` are kept as data

| Step | Action | Expected Result |
|---|---|---|
| 1 | As admin, upload with `curl -F "file=@qa.csv;type=text/csv" …/api/v1/ingest` a one-row synthetic CSV (SRC-05 header; R01, D01, `session_id` `R01-20261031-02`) whose `phrase_id` cell is `=SUM(1,1)` | Response 2xx; the record is accepted |
| 2 | `SELECT phrase_id FROM raw_sessions WHERE session_id = 'R01-20261031-02';` | Exactly `=SUM(1,1)` (stored as text, never evaluated) |
| 3 | Upload a row whose `loudness_dbfs` cell is `=1` | Record rejected with `loudness_dbfs` `invalid_type` (not computed) |

Note: FEAT-019-FR-21 asks for a shared helper for the SEC-086 rule; no such helper is found in `backend/` (`grep -rn "SEC-086" backend` returns nothing). The behaviour is checked here end to end.

### TC-019-18 Problem bodies never contain internals

| Step | Action | Expected Result |
|---|---|---|
| 1 | Collect the bodies of TC-019-01..TC-019-15 | Every body has exactly the keys `type`, `title`, `status`, `detail`, `request_id`, `errors` |
| 2 | Search the bodies for `Traceback`, `sqlalchemy`, `psycopg`, `SELECT `, `/home/`, `.py`, `postgresql://` | 0 matches |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | Any error response | `Content-Type: application/problem+json`; `type` starts with `urn:echowell:error:`; `request_id` = `X-Request-ID` header |
| 2 | `GET /api/v1/residents` | `{meta, items, total, limit, offset}` plus `window` and `summary`; `meta` per TC-019-10 |
| 3 | Validation errors | `errors[]` items `{field, code, message}`; no `input` |
| 4 | 413 / 415 / 503 | `PAYLOAD_TOO_LARGE` / `UNSUPPORTED_MEDIA_TYPE` / `SERVICE_UNAVAILABLE` + `Retry-After: 30` |
| 5 | `GET /api/v1/openapi.json` | Components `Problem`, `ProblemFieldError`, `Meta`, `PageMeta` present |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT name FROM facilities;` | `Demo Facility` = `meta.facility_name` |
| 2 | `SELECT key, value FROM config_parameters WHERE profile = 'test_v0_1' AND key IN ('baseline_n','cusum_h');` | `baseline_n` 16, `cusum_h` 5.0 = `meta` values |
| 3 | `SELECT key, value FROM config_parameters WHERE profile = 'production' AND key = 'baseline_n';` | 30 (value used when `PIPELINE_PROFILE=production`) |
| 4 | `raw_sessions` and `ingest_rejections` counts before and after the 413/415 requests | Unchanged |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Unknown path / wrong method | 404 `NOT_FOUND` / 405 `METHOD_NOT_ALLOWED` (TC-019-02) |
| 2 | Unknown property | 422 `extra_forbidden`, no input echo (TC-019-03) |
| 3 | Body over 64 KB | 413 (TC-019-06) |
| 4 | `audio/wav` | 415, nothing stored (TC-019-07) |
| 5 | Origin not listed | No `Access-Control-Allow-Origin` (TC-019-08) |
| 6 | Database down | 503 + `Retry-After: 30` (TC-019-05) |
| 7 | `from` > `to`, bad date, bad pattern, bad enum | 422 `INVALID_QUERY_PARAMETER` (TC-019-12, TC-019-15) |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-019-AC-01 | Forced exception: 500, `application/problem+json`, `INTERNAL_ERROR`, "An unexpected error occurred.", `request_id` = header, no stack trace or exception text | TC-019-01, TC-019-18 |
| FEAT-019-AC-02 | Unknown path 404 `NOT_FOUND`; wrong method 405 `METHOD_NOT_ALLOWED`; both `errors: []` | TC-019-02 |
| FEAT-019-AC-03 | Unknown property: 422 `VALIDATION_ERROR` with `code` `extra_forbidden` and no `input` key | TC-019-03 |
| FEAT-019-AC-04 | Database stopped: 503 `SERVICE_UNAVAILABLE` with `Retry-After: 30` | TC-019-05 |
| FEAT-019-AC-05 | 65,537-byte JSON body to a non-ingest endpoint: 413; `Content-Type: audio/wav`: 415 | TC-019-06, TC-019-07 |
| FEAT-019-AC-06 | Allowed origin echoed with `X-Request-ID` exposed; unlisted origin gets no allow header | TC-019-08 |
| FEAT-019-AC-07 | Four security headers on every response; HSTS with `APP_ENV=staging` | TC-019-09 |
| FEAT-019-AC-08 | `meta.as_of` "2026-10-30T20:00:00Z", `baseline_n` 16, `cusum_h` 5.0, `pipeline_profile` "test_v0_1", `facility_name` "Demo Facility" | TC-019-10, TC-019-11 |
| FEAT-019-AC-09 | `from=2026-10-20&to=2026-10-10`: 422 `INVALID_QUERY_PARAMETER` | TC-019-12 |

## Test Data Requirements

- `test_v0_1` seed with one succeeded run (`as_of` 2026-10-30T20:00:00Z); master-only seed for TC-019-11.
- Seeded users and the ingest key from `SEED_*` (never written down).
- Synthetic files: `big.json` (> 65,536 bytes), a > 5 MB body, `qa.csv` with one synthetic R01/D01 row; 12-byte synthetic `RIFF0000WAVE` header (not audio content).
- Origins `http://localhost:3000` (allowed) and `https://evil.example.org` (RFC 2606, not allowed).
- Environment: `APP_ENV`, `CORS_ORIGINS`, `CORS_ORIGIN_REGEX`, `FACILITY_TZ`, `DATA_SOURCE_LABEL`, `PIPELINE_PROFILE`.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-019-FR-01 / LOG-040 / D-48 | FEAT-019 | TC-019-02, TC-019-18 |
| FEAT-019-FR-02 / LOG-041 | FEAT-019 | TC-019-02, TC-019-16 |
| FEAT-019-FR-03 / API-095 / LOG-044 | FEAT-019 | TC-019-01, TC-019-02, TC-019-05 |
| FEAT-019-FR-04 / LOG-043 / FR-027 | FEAT-019 | TC-019-03, TC-019-04 |
| FEAT-019-FR-05 / API-096 / LOG-042 / SEC-085 / AC-LOG-08 | FEAT-019 | TC-019-01, TC-019-18 |
| FEAT-019-FR-06 / API-097 | FEAT-019 | TC-019-05 |
| FEAT-019-FR-07 / PGS-028 | FEAT-019 | TC-019-16 |
| FEAT-019-FR-08 / API-098 | FEAT-019 | TC-018-05 step 5 (429 with `Retry-After`), TC-022-01 |
| FEAT-019-FR-09 / API-100 | FEAT-019 | TC-019-13 |
| FEAT-019-FR-10 / API-057 / ENV-016 / FR-332 / D-32 | FEAT-019 | TC-019-10 |
| FEAT-019-FR-11 / API-069 / FR-333 | FEAT-019 | TC-019-10, TC-019-11 |
| FEAT-019-FR-12 / API-093 | FEAT-019 | TC-019-12 |
| FEAT-019-FR-13 / API-094 | FEAT-019 | TC-019-14 |
| FEAT-019-FR-14 / API-101 / SEC-094 / D-66 / LOG-035 / TST-134 | FEAT-019 | TC-019-08 |
| FEAT-019-FR-15 / API-104 / SEC-081 | FEAT-019 | TC-019-06 |
| FEAT-019-FR-16 / API-106 | FEAT-019 | TC-019-09 |
| FEAT-019-FR-17 / SEC-080 | FEAT-019 | TC-019-03 |
| FEAT-019-FR-18 / SEC-082 / ING-012 / TST-133 | FEAT-019 | TC-019-07 |
| FEAT-019-FR-19 / SEC-083 | FEAT-019 | Bandit B608 job of FEAT-078 (`pytest -m security tests/security/test_static_scans.py`) |
| FEAT-019-FR-20 / SEC-084 | FEAT-019 | TC-019-15 |
| FEAT-019-FR-21 / SEC-086 | FEAT-019 | TC-019-17 |
| FEAT-019-FR-22 / ARC-100 / ARC-101 | FEAT-019 | TC-019-01, TC-019-02, TC-019-18 |
| TST-034 | FEAT-019 | TC-019-02, TC-019-16 |
