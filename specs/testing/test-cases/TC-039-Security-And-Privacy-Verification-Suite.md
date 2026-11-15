# Security and privacy verification suite (auth matrix, token attacks, no-audio, data minimisation)

## Feature Description

FEAT-039 is the automated evidence (MVP-07, AC-SEC-01/02/04) that the finished API enforces the TRD 12 §4.6 role matrix for every endpoint and caller type (TRD 13 Table 4.13-A), that no route is reachable without an explicit auth dependency except `/health`, `/auth/login`, `/openapi.json` (and `/docs` outside production), that expired, forged and `alg: none` tokens and revoked or under-scoped API keys are refused, that nothing accepts or returns audio, that CORS refuses unknown origins, and that responses, logs, schemas and CSV exports expose study IDs only — no names, birth dates, room numbers, password or key hashes, raw payloads or ground truth — and that no LLM, tracker, voice, notification or third-party-auth dependency exists. The manual cases re-run the suite and spot-check the same rules against the running stack.

## Preconditions

- Local Docker Compose (demo profile) running per `docs/deployment.md`, seeded with `python -m backend.cli seed test_v0_1 --reset` (DS-07: SRC-05 with as-of 2026-10-30 15:00 America/Chicago); API at `http://localhost:8000/api/v1`; `CORS_ORIGINS=http://localhost:3000,http://localhost:3001` (from `.env.development.example`).
- Seeded users `admin@example.com`, `clinician@example.com`, `researcher@example.com` with the `SEED_*` passwords from the environment file; Bearer tokens ADMIN_TOKEN, CLINICIAN_TOKEN, RESEARCHER_TOKEN from `POST /api/v1/auth/login`.
- The ingest API key from the environment file (`SEED_INGEST_API_KEY`, scope `ingest:write`), referred to as INGEST_KEY.
- A second key with scope `pipeline:run` created with `python -m backend.cli create-api-key --name qa-pipeline --scope pipeline:run` (the command prints the key once; keep it as PIPELINE_KEY, never record it).
- Local development stack (README quick start) with the PostgreSQL 16 test database for the `pytest` steps.
- `psql` read access; ids of one open alert (R09), one ingest batch, one pipeline run and one user taken from `GET /api/v1/alerts?status=open`, `SELECT id FROM ingest_batches LIMIT 1`, `GET /api/v1/pipeline/runs`, `GET /api/v1/users`.
- Cases that create records (TC-039-02 step 7, TC-039-07) are run last or followed by a reseed.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-039-01 | Automated auth matrix passes for every Table 4.13-A row and caller | High | Security |
| TC-039-02 | Spot-check of matrix rows against the running stack (anon, key, admin, clinician, researcher) | High | Security |
| TC-039-03 | `POST /pipeline/run` with both API-key scopes and all roles | High | Security |
| TC-039-04 | Route-coverage test passes and detects an unprotected route | High | Security |
| TC-039-05 | Expired, altered-signature and `alg: none` JWTs are refused | High | Negative |
| TC-039-06 | JWT of a deactivated user is refused | High | Negative |
| TC-039-07 | Revoked key returns 401 `API_KEY_INVALID`; key without `ingest:write` on `POST /ingest` returns 403 | High | Negative |
| TC-039-08 | No audio in the OpenAPI document; `Content-Type: audio/wav` to every endpoint returns 415 or 422 and stores nothing | High | Security |
| TC-039-09 | CORS preflight: unknown origin gets no `Access-Control-Allow-Origin`; allowed origin is echoed | High | Security |
| TC-039-10 | Data minimisation during and after an SRC-05 upload (responses and logs) | High | Security |
| TC-039-11 | Static scans: no secret/raw/ground-truth fields in response schemas, no personal or audio columns, no forbidden dependencies | High | Security |
| TC-039-12 | Every researcher write call returns 403; no self role change or self deactivation | High | Negative |
| TC-039-13 | CSV exports contain study IDs only and no staff-note text | High | Security |
| TC-039-14 | Unknown API key and a key sent in the query string are refused | Medium | Negative |

### TC-039-01 Automated auth matrix

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest -m security tests/security/test_auth_matrix.py -v` | `test_matrix_covers_every_endpoint` PASSED; every parametrisation of `test_every_cell` (callers anon, key, admin, clinician, researcher) PASSED; `test_pipeline_run_key_scopes` PASSED; 0 failed, 0 skipped |
| 2 | Open `tests/security/test_auth_matrix.py` and compare its table with TRD 13 Table 4.13-A | One entry per Table 4.13-A row, including `GET /openapi.json`, `POST /auth/login`, `GET /config/ui` and `GET /scores` with `Accept: text/csv` |
| 3 | Read the assertion message of `test_every_cell` in the module | A failing cell reports endpoint, caller and expected vs actual status |

### TC-039-02 Spot-check of matrix rows against the running stack

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/health`, `GET /api/v1/openapi.json` with no credentials | 200, 200 |
| 2 | `GET /api/v1/config/ui` and `GET /api/v1/auth/me` with no credentials, then with `X-API-Key: INGEST_KEY` | 401, 401, 401, 401 (`urn:echowell:error:NOT_AUTHENTICATED`) |
| 3 | `GET /api/v1/config/ui` with ADMIN_TOKEN, CLINICIAN_TOKEN, RESEARCHER_TOKEN | 200, 200, 200 |
| 4 | `GET /api/v1/ingest/batches/<batch id>` with admin, clinician, researcher | 200, 403, 200 |
| 5 | `GET /api/v1/analytics` and `GET /api/v1/pipeline/runs` with admin, clinician, researcher | 200, 403, 200 for each endpoint |
| 6 | `GET /api/v1/scores` with header `Accept: text/csv` as admin, clinician, researcher | 200, 403, 200 |
| 7 | `POST /api/v1/sessions` with a synthetic record (SRC-05 row R01-20261001-01 with `session_id` "R01-20261031-01" and `timestamp_utc` "2026-10-31 19:45:11") using `X-API-Key: INGEST_KEY`, then the same body with ADMIN_TOKEN | 201 with the key; 401 with the admin JWT (sessions accept API keys only) |
| 8 | `POST /api/v1/ingest` (JSON body `{"records": [<one synthetic record>]}`) with CLINICIAN_TOKEN and RESEARCHER_TOKEN | 403, 403 |
| 9 | `GET /api/v1/residents`, `/api/v1/residents/R09`, `/api/v1/residents/R09/checkins`, `/api/v1/residents/R09/features`, `/api/v1/residents/R09/notes`, `/api/v1/alerts`, `/api/v1/data-alerts`, `/api/v1/devices`, `/api/v1/admissions`, `/api/v1/facility/reference-ranges` with no credentials, then with RESEARCHER_TOKEN | 401 for each without credentials; 200 for each as researcher |

### TC-039-03 POST /pipeline/run with both key scopes and all roles

| Step | Action | Expected Result |
|---|---|---|
| 1 | `POST /api/v1/pipeline/run` body `{"scope": "all", "profile": "test_v0_1", "as_of": "2026-10-30T15:00:00-05:00"}` with `X-API-Key: INGEST_KEY` | 403 `urn:echowell:error:FORBIDDEN` |
| 2 | Same with `X-API-Key: PIPELINE_KEY` | 202 `PipelineRunAccepted` |
| 3 | Same with ADMIN_TOKEN | 202 |
| 4 | Same with CLINICIAN_TOKEN, RESEARCHER_TOKEN | 403, 403 |
| 5 | Same with no credentials | 401 |
| 6 | `SELECT trigger, status FROM pipeline_runs ORDER BY started_at DESC LIMIT 2;` | Two `manual` runs from steps 2–3, `succeeded` |

### TC-039-04 Route-coverage test

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest -m integration tests/integration/test_auth_coverage.py -v` | `test_every_route_has_its_auth_dependency`, `test_production_has_no_docs_route`, `test_a_route_without_auth_is_detected` PASSED |
| 2 | Read `test_a_route_without_auth_is_detected` | It registers a test-only route without an auth dependency and asserts the coverage check reports it (the check fails for an unprotected route) |
| 3 | Read the allow-list in the test | Only `/api/v1/health`, `/api/v1/auth/login`, `/api/v1/openapi.json` (and `/api/v1/docs` outside production) |

### TC-039-05 Expired, altered-signature and alg: none JWTs

| Step | Action | Expected Result |
|---|---|---|
| 1 | Take ADMIN_TOKEN, change its last character (signature) and call `GET /api/v1/auth/me` | 401; `type` = `urn:echowell:error:TOKEN_INVALID`; `title` = "Token invalid" |
| 2 | Build an unsigned token: header `{"alg":"none","typ":"JWT"}` base64url-encoded, the payload segment copied from ADMIN_TOKEN, and an empty signature (`<header>.<payload>.`); call `GET /api/v1/auth/me` | 401 `urn:echowell:error:TOKEN_INVALID` |
| 3 | `pytest -m security tests/security/test_tokens.py -v` | `test_token_61_minutes_old_is_expired` (401 `TOKEN_EXPIRED`, title "Token expired"), `test_altered_and_unsigned_tokens_are_invalid`, `test_token_of_a_deactivated_user_is_invalid` PASSED |
| 4 | Call `GET /api/v1/residents` with header `Authorization: Bearer abc` | 401 `urn:echowell:error:TOKEN_INVALID` |

### TC-039-06 JWT of a deactivated user

| Step | Action | Expected Result |
|---|---|---|
| 1 | Log in as `researcher@example.com`; keep RESEARCHER_TOKEN; `GET /api/v1/auth/me` | 200 |
| 2 | As admin `PATCH /api/v1/users/<researcher id>` with `{"active": false}` | 200 |
| 3 | `GET /api/v1/auth/me` with the old RESEARCHER_TOKEN | 401 `urn:echowell:error:TOKEN_INVALID` |
| 4 | `POST /api/v1/auth/login` as the researcher | 401 (inactive account cannot log in) |
| 5 | Restore with admin `PATCH ... {"active": true}` | 200 |

### TC-039-07 Revoked key and key without ingest:write

| Step | Action | Expected Result |
|---|---|---|
| 1 | `python -m backend.cli create-api-key --name qa-revoke` (scope defaults to `ingest:write`); keep the printed key as REVOKE_KEY | Exit 0; key printed once, starts with `ewk_` |
| 2 | `POST /api/v1/sessions` with `X-API-Key: REVOKE_KEY` and a new synthetic record (`session_id` "R02-20261031-01") | 201 |
| 3 | `python -m backend.cli revoke-api-key --name qa-revoke` | Exit 0 |
| 4 | Repeat step 2 with `session_id` "R02-20261031-02" | 401; `type` = `urn:echowell:error:API_KEY_INVALID`; `title` = "API key invalid" |
| 5 | `POST /api/v1/ingest` with `X-API-Key: PIPELINE_KEY` (scope `pipeline:run` only) and body `{"records": [<one synthetic record>]}` | 403 `urn:echowell:error:FORBIDDEN` |
| 6 | `SELECT count(*) FROM raw_sessions WHERE session_id IN ('R02-20261031-02');` | 0 |
| 7 | `SELECT active FROM api_keys WHERE name = 'qa-revoke';` | false |
| 8 | `pytest -m security tests/security/test_api_keys.py -v` | `test_revoked_key_is_invalid`, `test_key_without_ingest_scope_is_forbidden`, `test_unknown_or_query_string_key_is_refused` PASSED |

### TC-039-08 No audio anywhere

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -o '"[a-z_]*audio[a-z_]*"' docs/api_reference/openapi.json \| sort -u` | Exactly `"audio_quality_flag"` |
| 2 | List request-body media types of every operation in the document | None starts with `audio/` |
| 3 | `SELECT count(*) FROM raw_sessions;` — note value N | N (283 on a fresh DS-07 seed) |
| 4 | `POST /api/v1/sessions` with `X-API-Key: INGEST_KEY`, `Content-Type: audio/wav` and a small byte body | 415 `urn:echowell:error:UNSUPPORTED_MEDIA_TYPE` or 422 `urn:echowell:error:VALIDATION_ERROR` |
| 5 | `POST /api/v1/ingest` multipart with part `file` named `voice.wav` and content type `audio/wav` | 415 or 422 |
| 6 | `POST /api/v1/residents/R09/notes` with CLINICIAN_TOKEN and `Content-Type: audio/wav` | 415 or 422 |
| 7 | `SELECT count(*) FROM raw_sessions;` | Still N; `ingest_batches` and `staff_notes` counts unchanged |
| 8 | `pytest -m security tests/security/test_no_audio.py -v` | `test_audio_is_refused_everywhere` (media types `audio/wav`, `audio/mpeg`, `Audio/WAV` against every route) and `test_audio_inside_a_multipart_upload_is_refused` PASSED |

### TC-039-09 CORS preflight

| Step | Action | Expected Result |
|---|---|---|
| 1 | `curl -si -X OPTIONS http://localhost:8000/api/v1/residents -H "Origin: https://evil.example" -H "Access-Control-Request-Method: GET"` | Response has no `access-control-allow-origin` header |
| 2 | Same with `-H "Origin: http://localhost:3000"` | `access-control-allow-origin: http://localhost:3000` |
| 3 | `curl -si http://localhost:8000/api/v1/health -H "Origin: https://evil.example"` | No `access-control-allow-origin` header |
| 4 | `pytest -m security tests/security/test_cors.py -v` | All PASSED |

### TC-039-10 Data minimisation during and after an SRC-05 upload

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest -m security tests/security/test_data_minimisation.py -v` (runs with JSON logs) | `test_responses_and_logs_hold_study_ids_only` and `test_csv_exports_hold_no_note_text` PASSED |
| 2 | On the stack, fetch `GET /api/v1/residents`, `/residents/R09`, `/residents/R09/checkins`, `/residents/R09/features`, `/alerts`, `/devices` as admin and list every JSON key recursively | No key named like `name`, `first_name`, `last_name`, `full_name`, `dob`, `date_of_birth`, `birth_date`, `room`, `room_number`; persons are identified only by `resident_code` (e.g. "R09"), devices by `device_code`, sessions by `session_id` |
| 3 | Watch `docker compose logs backend` while running `python -m backend.cli seed test_v0_1 --reset` (SRC-05 upload and run) | Log lines carry users by UUID and residents by study ID only; no feature value (e.g. `-28.29` loudness of R09-20261021-01), no e-mail, no password or key value |

### TC-039-11 Static scans

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest -m security tests/security/test_static_scans.py -v` | `test_no_secret_or_raw_fields_in_the_api`, `test_no_personal_or_audio_columns`, `test_no_forbidden_dependencies`, `test_the_scan_recognises_forbidden_names` PASSED |
| 2 | `grep -c -E '"(password_hash\|key_hash\|payload\|raw_body)"' docs/api_reference/openapi.json` | `0` |
| 3 | `grep -i -E -c '^(openai\|anthropic\|langchain\|google-generativeai\|cohere\|mistralai)' backend/requirements.txt backend/requirements-dev.txt` and search `frontend/package.json` for the same names | 0 matches in every file |
| 4 | `psql -c "SELECT table_name, column_name FROM information_schema.columns WHERE table_schema='public' AND column_name ~* '(first_name\|last_name\|full_name\|birth\|dob\|phone\|address\|audio\|wav)' AND column_name <> 'audio_quality_flag';"` | 0 rows |
| 5 | Check ground-truth exposure: in the document, find the schemas holding `planted_change` or `change_began` | Only `AlarmTimingRow` (used by the Analytics `alarm_timing` block); no other schema exposes an `evaluation_ground_truth` column |

### TC-039-12 Researcher write calls and self changes

| Step | Action | Expected Result |
|---|---|---|
| 1 | With RESEARCHER_TOKEN: `POST /api/v1/alerts/<R09 alert id>/reviews` body `{"outcome": "no_concern"}` | 403 `urn:echowell:error:FORBIDDEN` |
| 2 | `POST /api/v1/alerts/<R09 alert id>/snooze` body `{}` | 403 |
| 3 | `POST /api/v1/residents/R09/notes` with a valid note body | 403 |
| 4 | `POST /api/v1/ingest` with one synthetic record | 403 |
| 5 | `POST /api/v1/pipeline/run` body `{"scope": "all"}` | 403 |
| 6 | `POST /api/v1/users` (valid body) and `PATCH /api/v1/users/<clinician id>` (`{"display_name": "x"}`) | 403, 403 |
| 7 | `SELECT count(*) FROM alert_reviews; SELECT count(*) FROM staff_notes; SELECT snoozed_until FROM alerts WHERE session_id = 'R09-20261021-01';` | Counts unchanged; `snoozed_until` unchanged |
| 8 | As admin, `PATCH /api/v1/users/<own id>` with `{"role": "clinician"}` and with `{"active": false}` | 403, 403 `FORBIDDEN` (SEC-044) |

### TC-039-13 CSV exports contain study IDs only and no staff-note text

| Step | Action | Expected Result |
|---|---|---|
| 1 | As clinician, `POST /api/v1/residents/R09/notes` with a note whose text is the marker "QA-NOTE-MARKER-039" | 201 |
| 2 | As researcher, `GET /api/v1/scores` with `Accept: text/csv`; save the body | 200; `content-type` starts with `text/csv`; the header row holds the `ScoreRow` field names (`resident_code`, `session_id`, `epoch_number`, `local_date`, `is_morning`, `z_<feature>` ×7, `composite_raw`, `composite_z`, `cusum_tally`, `alarm_state`); 98 data rows for DS-07 |
| 3 | Search the CSV for "QA-NOTE-MARKER-039" and for any column named like name, birth date or room | No match |
| 4 | As researcher, `GET /api/v1/analytics/baselines` with `Accept: text/csv` | 200; 180 data rows; no note text, only study IDs |

### TC-039-14 Unknown API key and a key in the query string

| Step | Action | Expected Result |
|---|---|---|
| 1 | `POST /api/v1/sessions` with `X-API-Key: ewk_unknownunknownunknownunknownunknownunkno` | 401 `urn:echowell:error:API_KEY_INVALID` |
| 2 | `POST /api/v1/sessions?api_key=<INGEST_KEY>` with no header | 401 `urn:echowell:error:NOT_AUTHENTICATED` (query-string keys are not accepted) |
| 3 | `SELECT count(*) FROM raw_sessions;` | Unchanged |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | Every endpoint × caller of Table 4.13-A | Exactly the listed status (TC-039-01, TC-039-02) |
| 2 | 401 responses | `NOT_AUTHENTICATED`, `TOKEN_EXPIRED`, `TOKEN_INVALID` or `API_KEY_INVALID` problem+json |
| 3 | 403 responses | `FORBIDDEN` problem+json, title "Not allowed for this role" |
| 4 | Audio content type to any endpoint | 415 `UNSUPPORTED_MEDIA_TYPE` or 422 `VALIDATION_ERROR` |
| 5 | CORS preflight | Origin echoed only for configured origins |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `raw_sessions`, `ingest_batches`, `staff_notes`, `alert_reviews` counts before/after every refused call | Unchanged |
| 2 | Column whitelist (TC-039-11 step 4) | No names, birth dates, contacts or audio columns |
| 3 | `SELECT count(*) FROM audit_logs WHERE action = 'access.denied' AND occurred_at > now() - interval '30 minutes';` | ≥ 1 per 403 response produced during the session |
| 4 | `SELECT active FROM api_keys WHERE name = 'qa-revoke';` | false after revoke |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Altered signature / `alg: none` / malformed bearer | 401 `TOKEN_INVALID` (TC-039-05) |
| 2 | Token 61 minutes old | 401 `TOKEN_EXPIRED` (TC-039-05) |
| 3 | Token of a deactivated user | 401 `TOKEN_INVALID` (TC-039-06) |
| 4 | Revoked key / unknown key / key in query string | 401 `API_KEY_INVALID` (TC-039-07, TC-039-14) |
| 5 | `pipeline:run`-only key on `POST /ingest`; `ingest:write` key on `POST /pipeline/run` | 403 / 403 (TC-039-07, TC-039-03) |
| 6 | Researcher write calls | 403 each, nothing stored (TC-039-12) |
| 7 | `Content-Type: audio/wav` | 415 or 422, nothing stored (TC-039-08) |
| 8 | Preflight from `https://evil.example` | No `Access-Control-Allow-Origin` (TC-039-09) |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-039-AC-01 | Matrix test passes for every Table 4.13-A row and caller, API keys in both scopes | TC-039-01, TC-039-02, TC-039-03 |
| FEAT-039-AC-02 | Route-coverage test passes and fails for a registered test-only route without auth | TC-039-04 |
| FEAT-039-AC-03 | 61-minute JWT → 401 `TOKEN_EXPIRED`; altered and `alg: none` → 401 `TOKEN_INVALID`; revoked key → 401 `API_KEY_INVALID`; key without `ingest:write` on `POST /ingest` → 403 | TC-039-05, TC-039-07 |
| FEAT-039-AC-04 | Only `audio_quality_flag` contains "audio"; `audio/wav` to every endpoint → 415 or 422 with `raw_sessions` count unchanged | TC-039-08 |
| FEAT-039-AC-05 | Preflight from `https://evil.example` gets no `Access-Control-Allow-Origin`; a configured origin is echoed | TC-039-09 |
| FEAT-039-AC-06 | During and after an SRC-05 upload no response or log has a name / birth-date / room-number field and no log holds a feature value | TC-039-10 |
| FEAT-039-AC-07 | Static scans find no `password_hash`, `key_hash`, `payload`, `raw_body` or ground-truth column (except `alarm_timing`) and no LLM, tracker, voice, notification or third-party-auth dependency | TC-039-11 |
| FEAT-039-AC-08 | Every researcher write call returns 403; researcher scores CSV contains no note text | TC-039-12, TC-039-13 |

## Test Data Requirements

- DS-07 database (SRC-05, `test_v0_1`, as-of 2026-10-30 15:00 America/Chicago): residents R01–R10, 283 raw sessions, open alerts for R09 and R10.
- Seeded users and the ingest API key (`SEED_*` variables); test-only keys `qa-pipeline` (`pipeline:run`) and `qa-revoke` (`ingest:write`, later revoked).
- Synthetic records derived from SRC-05 rows with new session ids (R01-20261031-01, R02-20261031-01, R02-20261031-02); a small non-audio byte body labelled `audio/wav`.
- Note marker text "QA-NOTE-MARKER-039" (synthetic).
- `CORS_ORIGINS=http://localhost:3000,http://localhost:3001`.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-039-FR-01 | FEAT-039 | TC-039-01, TC-039-02, TC-039-03 |
| FEAT-039-FR-02 | FEAT-039 | TC-039-04 |
| FEAT-039-FR-03 | FEAT-039 | TC-039-05, TC-039-06, TC-039-07 |
| FEAT-039-FR-04 | FEAT-039 | TC-039-08 |
| FEAT-039-FR-05 | FEAT-039 | TC-039-09 |
| FEAT-039-FR-06 | FEAT-039 | TC-039-10 |
| FEAT-039-FR-07 | FEAT-039 | TC-039-11 |
| FEAT-039-FR-08 | FEAT-039 | TC-039-11 |
| FEAT-039-FR-09 | FEAT-039 | TC-039-12 |
| FEAT-039-FR-10 | FEAT-039 | TC-039-13 |
| TRD 12 SEC-041, AC-SEC-01 | FEAT-039 | TC-039-01, TC-039-02 |
| TRD 12 SEC-042, AC-SEC-02 | FEAT-039 | TC-039-04 |
| TRD 12 AC-SEC-04 | FEAT-039 | TC-039-05, TC-039-07 |
| TRD 12 SEC-044, SEC-045 | FEAT-039 | TC-039-12 |
| TRD 12 SEC-120..SEC-129 | FEAT-039 | TC-039-10, TC-039-11 |
| TRD 13 TST-130 | FEAT-039 | TC-039-01 |
| TRD 13 TST-132 | FEAT-039 | TC-039-05, TC-039-07 |
| TRD 13 TST-133 | FEAT-039 | TC-039-08 |
| TRD 13 TST-134 | FEAT-039 | TC-039-09 |
| TRD 13 TST-137 | FEAT-039 | TC-039-10 |
| TRD 13 Table 4.13-A, AC-TST-05, MVP-07 | FEAT-039 | TC-039-01, TC-039-02, TC-039-03 |
| TRD 23 DME-005, DME-020; TRD 06 DB-035 | FEAT-039 | TC-039-11 |
| TRD 22 TPS-080..TPS-086 | FEAT-039 | TC-039-11 |
| TRD 05 API-012, API-014, API-024, API-101 | FEAT-039 | TC-039-05, TC-039-07, TC-039-09 |
| FR-015, FR-212, FR-213, FR-245 | FEAT-039 | TC-039-08, TC-039-02, TC-039-12, TC-039-13 |
