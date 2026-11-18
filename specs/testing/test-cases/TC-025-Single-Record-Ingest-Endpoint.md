# Single-record ingest endpoint (POST /api/v1/sessions)

## Feature Description

`POST /api/v1/sessions` (TRD 19 E-05) is the device-facing door of EchoWell. A device holding an API key with scope `ingest:write` posts one schema v0.1 feature record as `application/json` (≤ 64 KB). An invalid record is stored in `ingest_rejections` and answered with a 422 Problem listing every violation; a valid record is stored unaltered in `raw_sessions` under the per-`session_id` advisory lock and committed before the pipeline runs synchronously for the affected residents. The response tells the caller what happened: `usable`, `set_aside`, `quarantined` (201), `duplicate` (200) or `pending` (201, record stored but the run failed). No audio is ever accepted (415). Source: FEAT-025; TRD 10 ING-001..ING-004, ING-012, ING-029, ING-030, ING-033, ING-038, ING-057; TRD 05 API-030..API-047, API-056; TRD 17 LOG-050..LOG-054.

## Preconditions

1. Local Docker Compose stack running (`docs/deployment.md` local procedure steps 1–5); `curl -s http://localhost:8000/api/v1/health` returns `"status":"ok"`. The environment file is a copy of `.env.development.example` (`PIPELINE_PROFILE=test_v0_1`, `PIPELINE_AS_OF=2026-10-30T15:00:00-05:00`, `APP_ENV=local`).
2. **Ingest test database (master data only, no records):** `docker compose exec backend python -m backend.cli seed test_v0_1 --master-only --reset`. This loads residents R01–R10, devices, assignments, the three seeded users and the seeded API key `test-ingest` (scopes `ingest:write` and `pipeline:run`), with empty `raw_sessions`, `ingest_rejections` and `pipeline_runs`. Most cases below start from this state; repeat the command to return to it.
3. Shell variables: `API=http://localhost:8000/api/v1`; `KEY` = the ingest API key from the environment file (`SEED_INGEST_API_KEY`); never paste the value into a test record.
4. JSON record files built from SRC-05 (`tests/fixtures/pipeline_input/EchoWell_pipeline_test_input_v0_1.csv`): `r09_1021.json` = row `R09-20261021-01` exactly as in the TRD 19 E-05 request example (numbers as JSON numbers, 30 fields). Further rows are named by their `session_id` when needed.
5. `psql` access to the local database for read-only `SELECT` checks (e.g. `docker compose exec db psql -U echowell_app_login -d echowell`).
6. After the run, restore the demo state with `docker compose exec backend python -m backend.cli seed test_v0_1 --reset`.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-025-01 | Valid SRC-05 record R09-20261021-01 returns 201 and is stored once with payload as posted | High | Positive |
| TC-025-02 | Same record posted again returns 200 `duplicate`, adds a raw row and starts no run | High | Positive |
| TC-025-03 | Record for unknown resident R11 returns 422 `UNKNOWN_RESIDENT` and is stored only in `ingest_rejections` | High | Negative |
| TC-025-04 | Extra field `audio_base64` returns 422 `VALIDATION_ERROR` / `extra_forbidden` | High | Negative |
| TC-025-05 | `Content-Type: audio/wav` and `text/plain` return 415 and store nothing | High | Security |
| TC-025-06 | Record for a withdrawn resident returns 422 `RESIDENT_WITHDRAWN` with detail "resident withdrawn" | High | Negative |
| TC-025-07 | Pipeline failure after commit returns 201 `pending`; the raw row survives and the next run processes it | High | Negative |
| TC-025-08 | Two concurrent POSTs of one `session_id` give one non-duplicate and one 200 `duplicate` | High | Database |
| TC-025-09 | Logs for a valid, an invalid and a duplicate POST carry the required events and no feature value or key | High | Security |
| TC-025-10 | Database stopped returns 503 `SERVICE_UNAVAILABLE` with `Retry-After: 30` | High | Negative |
| TC-025-11 | Device-bound key posting another device's record returns 403 `DEVICE_KEY_MISMATCH`; body kept in `ingest_rejections` | Medium | Security |
| TC-025-12 | Wrong credentials: user JWT 401, `pipeline:run`-only key 403, no key 401 | Medium | Security |
| TC-025-13 | Unsupported schema version, malformed timestamp and malformed JSON return 422 with the right codes | Medium | Negative |
| TC-025-14 | Corrected re-send after a rejection is a new first arrival | Medium | Positive |
| TC-025-15 | Body over 64 KB returns 413 `PAYLOAD_TOO_LARGE` | Low | Negative |
| TC-025-16 | E-05 is documented in the OpenAPI document with `IngestRecord` / `IngestResult` | Low | API |

### TC-025-01 Valid SRC-05 record R09-20261021-01 returns 201 and is stored once with payload as posted

| Step | Action | Expected Result |
|---|---|---|
| 1 | From the ingest test database state, run `SELECT count(*) FROM raw_sessions; SELECT count(*) FROM pipeline_runs;` | Both counts are 0 |
| 2 | `curl -s -i -X POST $API/sessions -H "X-API-Key: $KEY" -H "Content-Type: application/json" --data-binary @r09_1021.json` | HTTP 201; body has exactly the keys `raw_session_id`, `arrival_seq`, `session_id`, `status_after_processing`, `reasons`, `pipeline_run_id`; `session_id` = "R09-20261021-01"; `status_after_processing` = "usable" and `reasons` = [] (TRD 19 E-05 example); `pipeline_run_id` is a uuid |
| 3 | `SELECT id, arrival_seq, payload, ingest_batch_id, api_key_id, received_at FROM raw_sessions;` | Exactly 1 row; `id` and `arrival_seq` equal the response values; `payload` equals the posted JSON key for key and value for value; `ingest_batch_id` NULL; `api_key_id` = id of the `test-ingest` key (`SELECT id FROM api_keys WHERE name='test-ingest'`); `received_at` is the server UTC time of the request (within a few seconds) |
| 4 | `SELECT trigger, status, scope FROM pipeline_runs WHERE id = '<pipeline_run_id>';` | 1 row: `trigger` = `ingest`, `status` = `succeeded`, `scope` = `{"type": "residents", "resident_codes": ["R09"]}` (R09 plus the residents sharing D09 on 2026-10-21; D09 is not shared) |
| 5 | `SELECT count(*) FROM ingest_batches; SELECT status FROM processed_sessions WHERE session_id='R09-20261021-01';` | `ingest_batches` count 0 (single-record ingest creates no batch); one processed row with status `usable` |

### TC-025-02 Same record posted again returns 200 `duplicate`, adds a raw row and starts no run

| Step | Action | Expected Result |
|---|---|---|
| 1 | After TC-025-01, note `SELECT count(*) FROM pipeline_runs;` (= N) and the `arrival_seq` returned in TC-025-01 | N = 1 |
| 2 | Repeat the POST of `r09_1021.json` unchanged | HTTP 200; `status_after_processing` = "duplicate"; `reasons` = ["session_id already received"]; `pipeline_run_id` = null; `arrival_seq` greater than the first one |
| 3 | `SELECT count(*) FROM raw_sessions WHERE session_id='R09-20261021-01';` | 2 rows |
| 4 | `SELECT count(*) FROM pipeline_runs;` and `SELECT status, count(*) FROM processed_sessions GROUP BY status;` | `pipeline_runs` still N (no new run); processed results unchanged from TC-025-01 |
| 5 | Post the same record once more with `hnr_db` increased by 1 | HTTP 200 `duplicate`; `SELECT ingest_warnings FROM raw_sessions WHERE id='<raw_session_id of this response>'` contains an item with `code` "duplicate_payload_differs" |

### TC-025-03 Record for unknown resident R11 returns 422 `UNKNOWN_RESIDENT` and is stored only in `ingest_rejections`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Reset to the ingest test database state. Create `r11.json` = `r09_1021.json` with `resident_id` "R11" and `session_id` "R11-20261021-01" | File ready (R11 is not in the roster) |
| 2 | POST `r11.json` with the ingest key | HTTP 422; `Content-Type: application/problem+json`; `type` = "urn:echowell:error:UNKNOWN_RESIDENT"; `title` = "Unknown resident"; `errors[0].field` = "resident_id", `errors[0].code` = "unknown_resident"; `request_id` present |
| 3 | `SELECT raw_body, errors, ingest_batch_id, row_number, api_key_id FROM ingest_rejections;` | Exactly 1 row; `raw_body` equals the posted body; `errors` equals the response `errors` array; `ingest_batch_id` NULL; `row_number` NULL; `api_key_id` = the `test-ingest` key id |
| 4 | `SELECT count(*) FROM raw_sessions; SELECT count(*) FROM pipeline_runs;` | Both 0 (rejected records are never stored or processed) |

Note: TRD 19 E-05 shows the detail "resident_id 'R11' is not enrolled."; the code returns detail "The resident is not enrolled." (`backend/services/ingestion.py:79`) and error message "resident_id is not enrolled." (`backend/services/validation.py:343`). The pass condition is the `type`, status and `errors[].code`.

### TC-025-04 Extra field `audio_base64` returns 422 `VALIDATION_ERROR` / `extra_forbidden`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Create `extra.json` = `r09_1021.json` plus `"audio_base64": "bm90LWF1ZGlv"` (the base64 of the text "not-audio"; no audio content) | File ready |
| 2 | POST `extra.json` with the ingest key | HTTP 422; `type` = "urn:echowell:error:VALIDATION_ERROR"; `errors[0].code` = "extra_forbidden" and `errors[0].field` = "audio_base64" |
| 3 | `SELECT count(*) FROM raw_sessions WHERE session_id='R09-20261021-01';` and `SELECT errors FROM ingest_rejections ORDER BY received_at DESC LIMIT 1;` | `raw_sessions` count unchanged (0 on a fresh database); newest rejection holds the same `errors` array |

### TC-025-05 `Content-Type: audio/wav` and `text/plain` return 415 and store nothing

| Step | Action | Expected Result |
|---|---|---|
| 1 | Note the counts of `raw_sessions` and `ingest_rejections` | Counts recorded |
| 2 | `curl -s -i -X POST $API/sessions -H "X-API-Key: $KEY" -H "Content-Type: audio/wav" --data-binary "not-audio"` | HTTP 415; `type` = "urn:echowell:error:UNSUPPORTED_MEDIA_TYPE"; `title` = "Unsupported media type" |
| 3 | Repeat with `-H "Content-Type: text/plain" --data-binary @r09_1021.json` | HTTP 415 `UNSUPPORTED_MEDIA_TYPE` |
| 4 | Re-read both counts | Both unchanged (nothing stored in either table) |

### TC-025-06 Record for a withdrawn resident returns 422 `RESIDENT_WITHDRAWN` with detail "resident withdrawn"

| Step | Action | Expected Result |
|---|---|---|
| 1 | Reset to the ingest test database state. `docker compose exec backend python -m backend.cli withdraw-resident R09 --on 2026-10-20` | Output "Resident R09 withdrawn on 2026-10-20."; exit code 0 |
| 2 | POST `r09_1021.json` (timestamp 2026-10-21) with the ingest key | HTTP 422; `type` = "urn:echowell:error:RESIDENT_WITHDRAWN"; `title` = "Resident withdrawn"; `detail` = "resident withdrawn" |
| 3 | `SELECT count(*) FROM raw_sessions; SELECT count(*) FROM ingest_rejections;` | `raw_sessions` 0; `ingest_rejections` 1 |
| 4 | Reset to the ingest test database state (re-enrols R09) | R09 active again |

### TC-025-07 Pipeline failure after commit returns 201 `pending`; the raw row survives and the next run processes it

The executor cannot be forced to fail from outside the process; this case runs the integration test that injects the failing executor, then confirms the stored state rule on the live stack.

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/integration/api/test_sessions.py::test_failed_run_answers_pending -q` (local development stack, Docker available for testcontainers) | 1 passed. The test asserts: POST returns 201 with `status_after_processing` "pending" and `reasons` []; the run row has `status` `failed`, `trigger` `ingest` and an `error_message`; `raw_sessions` holds the record; the next successful run gives both R09-20261021-01 and R09-20261022-01 status `usable` in `processed_sessions` |
| 2 | On the live stack, after any `pending` answer seen in logs (`pipeline_run_failed` event with `request_id` and `pipeline_run_id`), run `SELECT status, error_message FROM pipeline_runs WHERE id='<id>'` | `status` = `failed`, `error_message` not null; the matching `raw_sessions` row is unchanged (`SELECT payload FROM raw_sessions WHERE session_id=…`) |

### TC-025-08 Two concurrent POSTs of one `session_id` give one non-duplicate and one 200 `duplicate`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Reset to the ingest test database state; prepare `r09_1023.json` (SRC-05 row R09-20261023-01) | File ready |
| 2 | Send both at once: `(curl -s -o a.json -w "%{http_code}\n" -X POST $API/sessions -H "X-API-Key: $KEY" -H "Content-Type: application/json" --data-binary @r09_1023.json &  curl -s -o b.json -w "%{http_code}\n" -X POST $API/sessions -H "X-API-Key: $KEY" -H "Content-Type: application/json" --data-binary @r09_1023.json & wait)` | One request prints 201, the other 200; no 500 |
| 3 | Compare `a.json` and `b.json` | Exactly one has `status_after_processing` "duplicate" with `pipeline_run_id` null; the other has `usable` (or `pending`) with a run id |
| 4 | `SELECT arrival_seq FROM raw_sessions WHERE session_id='R09-20261023-01' ORDER BY arrival_seq;` | 2 rows; the lower `arrival_seq` belongs to the non-duplicate response, the higher to the duplicate |
| 5 | Optional (AC-ARC-06): post R02-20261002-01 and R03-20261002-01 (both on shared device D02) concurrently the same way | Both return 201 within a few seconds; no deadlock or 500 |

### TC-025-09 Logs for a valid, an invalid and a duplicate POST carry the required events and no feature value or key

| Step | Action | Expected Result |
|---|---|---|
| 1 | Reset to the ingest test database state. Create `marked.json` = SRC-05 row R09-20261022-01 with `mfcc1` set to 31.4159265; `bad.json` = the same with `pause_fraction` 1.5 | Files ready |
| 2 | POST `marked.json`, then `bad.json`, then `marked.json` again, each with the ingest key | 201, 422 `VALIDATION_ERROR`, 200 `duplicate` |
| 3 | `docker compose logs backend --since 2m \| grep '"event": *"ingest_'` | Exactly 3 `ingest_request` events (each with `request_id`, `endpoint`, `api_key_id`, `record_count` 1, `accepted`, `rejected`, `duplicates`, `warning_count`, `duration_ms`); exactly 1 `ingest_record_rejected` at level WARNING with `session_id` "R09-20261022-01", `resident_code` "R09" and the error field `pause_fraction`; exactly 1 `ingest_duplicate` at level INFO with `session_id` "R09-20261022-01" |
| 4 | `docker compose logs backend --since 2m \| grep -c "31.4159"` | 0 (no feature value logged) |
| 5 | Search the same log window for the ingest key value from the environment file (`grep -c -F "$KEY"`) | 0 (the key is never logged) |
| 6 | Inspect the three response bodies | None contains a feature value (only identifiers, status, reasons, errors) |

### TC-025-10 Database stopped returns 503 `SERVICE_UNAVAILABLE` with `Retry-After: 30`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Note `SELECT count(*) FROM raw_sessions;` then `docker compose stop db` | Database container stopped |
| 2 | POST `r09_1021.json` with the ingest key, `curl -i` | HTTP 503; header `Retry-After: 30`; `type` = "urn:echowell:error:SERVICE_UNAVAILABLE" |
| 3 | `docker compose start db`; wait for health `"status":"ok"`; re-read the `raw_sessions` count | Count unchanged (no partial record persisted) |

### TC-025-11 Device-bound key posting another device's record returns 403 `DEVICE_KEY_MISMATCH`; body kept in `ingest_rejections`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Reset to the ingest test database state. `docker compose exec backend python -m backend.cli create-api-key --name qa-bound-d01 --device D01`; keep the printed key in variable `BOUND` (do not record it in the test report) | Key printed once; exit 0 |
| 2 | POST `r09_1021.json` (device D09) with `X-API-Key: $BOUND` | HTTP 403; `type` = "urn:echowell:error:DEVICE_KEY_MISMATCH"; `title` = "API key not valid for this device" |
| 3 | `SELECT raw_body, errors FROM ingest_rejections;` and `SELECT count(*) FROM raw_sessions;` | 1 rejection with `raw_body` = the posted record and `errors[0].code` = "device_key_mismatch"; `raw_sessions` 0 |
| 4 | POST SRC-05 row R01-20261001-01 (device D01) with `$BOUND` | HTTP 201 |

### TC-025-12 Wrong credentials: user JWT 401, `pipeline:run`-only key 403, no key 401

| Step | Action | Expected Result |
|---|---|---|
| 1 | Log in as `admin@example.com` (`POST $API/auth/login`, password `SEED_ADMIN_PASSWORD`) and POST `r09_1021.json` with `Authorization: Bearer <token>` and no API key | HTTP 401; `type` = "urn:echowell:error:NOT_AUTHENTICATED" |
| 2 | `create-api-key --name qa-pipeline --scope pipeline:run`; POST with that key | HTTP 403; `type` = "urn:echowell:error:FORBIDDEN" |
| 3 | POST with no credentials | HTTP 401 `NOT_AUTHENTICATED` |
| 4 | POST with `X-API-Key: ewk_invalid` | HTTP 401; `type` = "urn:echowell:error:API_KEY_INVALID" |
| 5 | `SELECT count(*) FROM raw_sessions;` | Unchanged by steps 1–4 |

### TC-025-13 Unsupported schema version, malformed timestamp and malformed JSON return 422 with the right codes

| Step | Action | Expected Result |
|---|---|---|
| 1 | POST `r09_1021.json` with `schema_version` "0.2" | HTTP 422 `type` "urn:echowell:error:UNSUPPORTED_SCHEMA_VERSION" |
| 2 | POST with `timestamp_utc` "2026-10-01T19:45:11Z" (ISO form instead of `YYYY-MM-DD HH:MM:SS`) | HTTP 422 `VALIDATION_ERROR`; `errors` = one item with `field` "timestamp_utc" and `code` "invalid_format" |
| 3 | POST the text `{not json` with `Content-Type: application/json` | HTTP 422 `VALIDATION_ERROR` |
| 4 | `SELECT count(*) FROM raw_sessions;` | Unchanged (0 on a fresh database) |

### TC-025-14 Corrected re-send after a rejection is a new first arrival

| Step | Action | Expected Result |
|---|---|---|
| 1 | Reset to the ingest test database state. POST `r09_1021.json` with `pause_fraction` 1.5 | HTTP 422 `VALIDATION_ERROR`; 1 row in `ingest_rejections` |
| 2 | POST the unchanged (correct) `r09_1021.json` | HTTP 201 (not 200 `duplicate`); `status_after_processing` "usable" |
| 3 | `SELECT count(*) FROM raw_sessions WHERE session_id='R09-20261021-01';` | 1 |

### TC-025-15 Body over 64 KB returns 413 `PAYLOAD_TOO_LARGE`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Create `big.json` = `r09_1021.json` with an extra field `"padding"` holding 70,000 `x` characters | File > 64 KB |
| 2 | POST `big.json` with the ingest key | HTTP 413; `type` = "urn:echowell:error:PAYLOAD_TOO_LARGE" |
| 3 | Check `raw_sessions` and `ingest_rejections` counts | Both unchanged |

### TC-025-16 E-05 is documented in the OpenAPI document with `IngestRecord` / `IngestResult`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `http://localhost:8000/api/v1/docs` and expand `POST /api/v1/sessions` | Operation `ingestSession` is listed under tag `ingest`; security `apiKeyAuth` |
| 2 | `curl -s $API/openapi.json \| jq '.paths["/api/v1/sessions"].post'` | `requestBody` `application/json` references `#/components/schemas/IngestRecord`; responses 201 and 200 reference `IngestResult`; error responses include 401, 403, 413, 415, 422, 429 |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `POST /api/v1/sessions` valid record, first arrival | 201 `IngestResult` with 6 keys; `status_after_processing` ∈ {usable, set_aside, quarantined, pending} |
| 2 | Same `session_id` again | 200 `IngestResult`; `duplicate`; `reasons` ["session_id already received"]; `pipeline_run_id` null |
| 3 | Invalid record | 422 `application/problem+json` with `type` `urn:echowell:error:<CODE>`, `title`, `status`, `detail`, `request_id`, `errors[]` (`field`, `code`, `message`) |
| 4 | Code precedence for a record with several problems (e.g. unknown resident and bad `pause_fraction`) | `type` is the first applicable of UNSUPPORTED_SCHEMA_VERSION, UNKNOWN_RESIDENT, UNKNOWN_DEVICE, RESIDENT_WITHDRAWN, SESSION_ID_MISMATCH, else VALIDATION_ERROR; `errors[]` lists every violation |
| 5 | Non-JSON or `audio/*` content type | 415 `UNSUPPORTED_MEDIA_TYPE` |
| 6 | Response bodies of steps 1–5 | No feature value appears in any response |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `raw_sessions` after a valid POST | One row per arrival; `payload` = posted JSON; typed columns (e.g. `loudness_dbfs` = -28.29 for R09-20261021-01); `ingest_batch_id` NULL; `api_key_id` set; `arrival_seq` increasing |
| 2 | `ingest_rejections` after an invalid POST | One row; `raw_body` = exact body; `errors` = response `errors`; `ingest_batch_id` NULL; `row_number` NULL |
| 3 | `pipeline_runs` after a first arrival | One row `trigger` = `ingest`; after a duplicate no new row |
| 4 | `ingest_batches` after any single-record POST | No row created |
| 5 | Insert-only rule: `SELECT count(*) FROM raw_sessions` before and after every case; no case reduces or edits a row | Counts never decrease; `payload` of earlier rows unchanged |
| 6 | `SELECT firmware_version_last FROM devices WHERE device_code='D09';` after TC-025-01 | "fw-1.0.0" (the record's firmware; record is the newest of D09) |
| 7 | `SELECT count(*) FROM audit_logs WHERE action LIKE 'ingest.%';` after TC-025-01 | 0 (single-record ingest writes no audit row of its own; only `pipeline.run.started` / `pipeline.run.finished` from the runner) |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Unknown resident R11 (TC-025-03) | 422 `UNKNOWN_RESIDENT`; rejection row; no raw row |
| 2 | Extra property `audio_base64` (TC-025-04) | 422 `VALIDATION_ERROR`, `extra_forbidden` |
| 3 | `audio/wav` / `text/plain` (TC-025-05) | 415; nothing stored |
| 4 | Withdrawn resident (TC-025-06) | 422 `RESIDENT_WITHDRAWN`, detail "resident withdrawn" |
| 5 | Device-bound key mismatch (TC-025-11) | 403 `DEVICE_KEY_MISMATCH`; body stored in `ingest_rejections` |
| 6 | User JWT / wrong scope / no key (TC-025-12) | 401 / 403 / 401 |
| 7 | Database stopped (TC-025-10) | 503 + `Retry-After: 30`; nothing persisted |
| 8 | Pipeline failure (TC-025-07) | 201 `pending`; run `failed`; raw row kept |
| 9 | Body > 64 KB (TC-025-15) | 413 `PAYLOAD_TOO_LARGE` |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-025-AC-01 | 201 with the six `IngestResult` keys; exactly one `raw_sessions` row whose `payload` equals the posted JSON | TC-025-01 |
| FEAT-025-AC-02 | Repeat returns 200 `duplicate`, reasons ["session_id already received"], `pipeline_run_id` null; one more raw row; no new `pipeline_runs` row | TC-025-02 |
| FEAT-025-AC-03 | R11 returns 422 `UNKNOWN_RESIDENT`; one rejection with `errors` = response `errors` and `ingest_batch_id` NULL; no raw row | TC-025-03 |
| FEAT-025-AC-04 | `audio_base64` gives 422 `VALIDATION_ERROR` with `errors[0].code` `extra_forbidden`; `audio/wav` gives 415 and stores nothing | TC-025-04, TC-025-05 |
| FEAT-025-AC-05 | Forced executor failure gives 201 `pending`, raw row exists, run `failed`; next successful run processes the record | TC-025-07 |
| FEAT-025-AC-06 | Two concurrent POSTs give one non-duplicate and one 200 `duplicate`, `arrival_seq` order matching | TC-025-08 |
| FEAT-025-AC-07 | Withdrawn resident gives 422 `RESIDENT_WITHDRAWN`, detail "resident withdrawn" | TC-025-06 |
| FEAT-025-AC-08 | One `ingest_request` per POST, one `ingest_record_rejected` WARNING, one `ingest_duplicate` INFO; no feature value or API key in logs | TC-025-09 |
| FEAT-025-AC-09 | Database stopped gives 503 `SERVICE_UNAVAILABLE` with `Retry-After: 30` | TC-025-10 |

## Test Data Requirements

- `test_v0_1` master data (residents R01–R10, devices D01–D10 incl. D07B, assignments) loaded with `seed test_v0_1 --master-only --reset`.
- SRC-05 rows R09-20261021-01, R09-20261022-01, R09-20261023-01, R01-20261001-01, R02-20261002-01, R03-20261002-01 as JSON bodies.
- Synthetic fixture R11 (not enrolled).
- Environment file values: `SEED_INGEST_API_KEY`, `SEED_ADMIN_PASSWORD` (never written into records), `PIPELINE_PROFILE=test_v0_1`, `PIPELINE_AS_OF=2026-10-30T15:00:00-05:00`.
- Test-only API keys `qa-bound-d01` (bound to D01) and `qa-pipeline` (scope `pipeline:run`), created with `create-api-key`.
- No audio file or audio content is used; the 415 case sends the text "not-audio".

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-025-FR-01 (ING-001, API-030, FR-001) | FEAT-025 | TC-025-01, TC-025-12 |
| FEAT-025-FR-02 (API-031) | FEAT-025 | TC-025-03, TC-025-16 |
| FEAT-025-FR-03 (ING-004, API-041, ARC-020, FR-028) | FEAT-025 | TC-025-03, TC-025-04, TC-025-13 |
| FEAT-025-FR-04 (API-040) | FEAT-025 | TC-025-11 |
| FEAT-025-FR-05 (ING-033) | FEAT-025 | TC-025-03, TC-025-14 |
| FEAT-025-FR-06 (API-042, ING-029, ARC-021, FR-005, DB-022) | FEAT-025 | TC-025-01 |
| FEAT-025-FR-07 (ING-038, API-043, DB-021) | FEAT-025 | TC-025-08 |
| FEAT-025-FR-08 (ING-003, API-044, FR-008) | FEAT-025 | TC-025-02 |
| FEAT-025-FR-09 (API-045, ING-002, ARC-022) | FEAT-025 | TC-025-01 |
| FEAT-025-FR-10 (API-046, FR-007) | FEAT-025 | TC-025-01 |
| FEAT-025-FR-11 (API-047, ARC-025, LOG-054, D-52) | FEAT-025 | TC-025-07 |
| FEAT-025-FR-12 (API-032, ING-010) | FEAT-025 | TC-025-01 |
| FEAT-025-FR-13 (ING-012, FR-015) | FEAT-025 | TC-025-05 |
| FEAT-025-FR-14 (ING-030) | FEAT-025 | TC-025-02 (Database Validation step 5) |
| FEAT-025-FR-15 (LOG-052) | FEAT-025 | TC-025-10 |
| FEAT-025-FR-16 (API-056, ING-057) | FEAT-025 | TC-025-09 |
| FEAT-025-FR-17 (LOG-050, LOG-051, ING-057) | FEAT-025 | TC-025-09 |
| FEAT-025-FR-18 (ARC-024) | FEAT-025 | TC-025-02 (reads during the cases add no `pipeline_runs` row) |
| TST-043 | FEAT-025 | TC-025-01 |
| TST-044 / AC-API-05 | FEAT-025 | TC-025-02 |
| TST-045 / AC-API-06 | FEAT-025 | TC-025-03 |
| AC-API-07 / AC-ING-04 | FEAT-025 | TC-025-04, TC-025-05 |
| AC-ING-05, AC-ING-10 | FEAT-025 | TC-025-13, TC-025-06 |
| TST-037 / AC-ING-11 | FEAT-025 | TC-025-07 |
| AC-ING-09 / DB-021 | FEAT-025 | TC-025-08 |
| AC-ARC-03 | FEAT-025 | TC-025-01 |
| AC-ARC-06 | FEAT-025 | TC-025-08 (step 5) |
| TST-137 | FEAT-025 | TC-025-09 |
| TRD 19 E-05 | FEAT-025 | TC-025-01, TC-025-16 |
