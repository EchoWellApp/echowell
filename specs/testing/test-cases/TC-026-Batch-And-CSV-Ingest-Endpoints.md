# Batch and CSV ingest endpoints (POST /api/v1/ingest, GET /api/v1/ingest/batches/{id})

## Feature Description

`POST /api/v1/ingest` (TRD 19 E-06) accepts many schema v0.1 feature records at once, either as `application/json` `{"records": [...]}` (1–5,000 records, ≤ 5 MB) or as a `multipart/form-data` upload with one part named `file` holding a UTF-8 CSV in the exact SRC-05 format. Callers are an API key with scope `ingest:write` or an admin user. Envelope errors (malformed JSON, empty batch, too many records, CSV header mismatch, answer-key columns, the legacy SRC-06 file, `.xlsx`, audio) store nothing; within a valid envelope each record is validated alone, accepted records land in `raw_sessions` in input order and rejected ones in `ingest_rejections` with their batch position. One `ingest_batches` row, one `ingest.batch.received` audit row and one background pipeline run per batch are created, and the call answers 202 `IngestBatchAccepted`. `GET /api/v1/ingest/batches/{id}` (E-07, admin and researcher) reads a batch back with its rejections but never the raw bodies. Source: FEAT-026; TRD 10 ING-005..ING-009, ING-031, ING-032, ING-053..ING-058; TRD 05 API-048..API-056, API-104.

## Preconditions

1. Local Docker Compose stack running (`docs/deployment.md` steps 1–5), environment file from `.env.development.example` (`PIPELINE_PROFILE=test_v0_1`, `PIPELINE_AS_OF=2026-10-30T15:00:00-05:00`, `APP_ENV=local`).
2. **Ingest test database:** `docker compose exec backend python -m backend.cli seed test_v0_1 --master-only --reset` (roster R01–R10, devices, users, seeded API key; no records). Repeat it to return to an empty raw store.
3. Shell variables: `API=http://localhost:8000/api/v1`; `KEY` = the ingest API key from the environment file (`SEED_INGEST_API_KEY`); `ADMIN`, `RES`, `CLIN` = `access_token` values from `POST $API/auth/login` for `admin@example.com`, `researcher@example.com`, `clinician@example.com` with their `SEED_*` passwords.
4. Files: `SRC05=tests/fixtures/pipeline_input/EchoWell_pipeline_test_input_v0_1.csv` (283 data rows); `LEGACY=tests/fixtures/legacy/echowell_mock_data_500.csv` (SRC-06); `XLSX=tests/fixtures/answer_key/EchoWell_pipeline_test_v0_1.xlsx`.
5. `psql` read access to the local database.
6. After the run: `docker compose exec backend python -m backend.cli seed test_v0_1 --reset` to restore the demo state.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-026-01 | Admin uploads SRC-05 CSV: 202, accepted 283, rejected 0, duplicates 2, 283 raw rows in file order | High | Positive |
| TC-026-02 | Legacy SRC-06 file returns 422 `CSV_HEADER_MISMATCH` and stores nothing | High | Negative |
| TC-026-03 | CSV with answer-key column `expected_status` returns 422 `CSV_HEADER_MISMATCH` / `extra_forbidden` | High | Negative |
| TC-026-04 | Envelope errors: empty batch 422 `EMPTY_BATCH`, 5,001 records 413, `audio/wav` 415, `.xlsx` 415 | High | Negative |
| TC-026-05 | JSON batch of 3 with one bad `audio_quality_flag`: 202, accepted 2, rejected 1, `invalid_enum` rejection with `row_number` 2 | High | Positive |
| TC-026-06 | Re-upload of SRC-05 returns duplicates 283, accepted 283, no pipeline run | High | Positive |
| TC-026-07 | One `ingest.batch.received` audit row with counts and the response `X-Request-ID` | High | Database |
| TC-026-08 | Role checks: clinician POST 403; researcher GET 200; clinician GET 403; unknown id 404 | High | Security |
| TC-026-09 | Batch read-out validates against `IngestBatch` and holds no `raw_body` or payload | High | API |
| TC-026-10 | Exactly one background run per batch with a first arrival; none when all rejected or duplicates | High | Analytics |
| TC-026-11 | JSON batch via API key: `source` `api_batch`, `api_key_id` set, `api_keys.last_used_at` updated | Medium | Positive |
| TC-026-12 | Duplicate inside one batch is counted; differing copy carries `duplicate_payload_differs` | Medium | Database |
| TC-026-13 | Malformed JSON / missing `records` returns 422 `VALIDATION_ERROR`; malformed batch id returns 422 `INVALID_QUERY_PARAMETER` | Medium | Negative |
| TC-026-14 | CSV with a missing column lists the missing name; reordered columns with BOM and CRLF are accepted | Medium | Negative |
| TC-026-15 | Responses and logs carry no feature value; log events `ingest_batch_completed` and `ingest_request` present | Medium | Security |

### TC-026-01 Admin uploads SRC-05 CSV: 202, accepted 283, rejected 0, duplicates 2, 283 raw rows in file order

| Step | Action | Expected Result |
|---|---|---|
| 1 | Ingest test database state; `SELECT count(*) FROM raw_sessions;` | 0 |
| 2 | `curl -s -i -X POST $API/ingest -H "Authorization: Bearer $ADMIN" -F "file=@$SRC05;type=text/csv"` | HTTP 202; body `{ingest_batch_id, source, accepted, rejected, duplicates, pipeline_run_id}` with `source` "csv_upload", `accepted` 283, `rejected` 0, `duplicates` 2, `pipeline_run_id` a uuid (not null) |
| 3 | `SELECT count(*) FROM raw_sessions WHERE ingest_batch_id='<ingest_batch_id>';` | 283 |
| 4 | `SELECT session_id FROM raw_sessions ORDER BY arrival_seq;` and compare with column `session_id` of the CSV (`cut -d, -f2 $SRC05 \| tail -n +2`) | The two lists are identical in order (arrival order = file order); the last arrival is R04's late copy (the 283rd CSV row) |
| 5 | `SELECT source, filename, record_count, accepted_count, rejected_count, duplicate_count, uploaded_by, api_key_id FROM ingest_batches;` | 1 row: `csv_upload`, "EchoWell_pipeline_test_input_v0_1.csv", 283, 283, 0, 2, `uploaded_by` = id of `admin@example.com`, `api_key_id` NULL |
| 6 | `SELECT payload->>'loudness_dbfs' FROM raw_sessions WHERE session_id='R01-20261001-01' ORDER BY arrival_seq LIMIT 1;` | "-30.67" (CSV cell text kept as received) |

### TC-026-02 Legacy SRC-06 file returns 422 `CSV_HEADER_MISMATCH` and stores nothing

| Step | Action | Expected Result |
|---|---|---|
| 1 | Record counts: `SELECT (SELECT count(*) FROM raw_sessions), (SELECT count(*) FROM ingest_rejections), (SELECT count(*) FROM ingest_batches);` | Three numbers noted |
| 2 | `curl -s -i -X POST $API/ingest -H "Authorization: Bearer $ADMIN" -F "file=@$LEGACY;type=text/csv"` | HTTP 422; `type` = "urn:echowell:error:CSV_HEADER_MISMATCH"; `title` = "CSV header does not match schema v0.1"; `errors[]` has `extra_forbidden` items for legacy columns (e.g. `entry_id`, `health_wifi`, `speech_feature_1`) and `missing_field` items for schema v0.1 columns (e.g. `session_id`, `loudness_dbfs`) |
| 3 | Re-run the count query of step 1 | All three counts unchanged (no converter, no rows) |

### TC-026-03 CSV with answer-key column `expected_status` returns 422 `CSV_HEADER_MISMATCH` / `extra_forbidden`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Create `answerkey.csv`: `sed '1s/$/,expected_status/; 2,$s/$/,usable/' $SRC05 > answerkey.csv` | File with 31 columns |
| 2 | Upload it as admin (`-F "file=@answerkey.csv;type=text/csv"`) | HTTP 422 `CSV_HEADER_MISMATCH`; `errors[]` contains `{"field": "expected_status", "code": "extra_forbidden", ...}` |
| 3 | Check the three counts of TC-026-02 step 1 | Unchanged |
| 4 | Repeat with column `in_baseline` instead of `expected_status` | HTTP 422; `errors[]` names `in_baseline` with `extra_forbidden` |

### TC-026-04 Envelope errors: empty batch 422 `EMPTY_BATCH`, 5,001 records 413, `audio/wav` 415, `.xlsx` 415

| Step | Action | Expected Result |
|---|---|---|
| 1 | Record the three counts of TC-026-02 step 1 | Noted |
| 2 | `curl -s -i -X POST $API/ingest -H "X-API-Key: $KEY" -H "Content-Type: application/json" -d '{"records": []}'` | HTTP 422; `type` "urn:echowell:error:EMPTY_BATCH"; `title` "Empty batch" |
| 3 | Build `big.json` with 5,001 copies of SRC-05 row R01-20261001-01: `python -c "import csv,json; r=next(csv.DictReader(open('$SRC05'))); json.dump({'records':[r]*5001}, open('big.json','w'))"`; POST it with the ingest key | HTTP 413; `type` "urn:echowell:error:PAYLOAD_TOO_LARGE" |
| 4 | `curl -s -i -X POST $API/ingest -H "X-API-Key: $KEY" -H "Content-Type: audio/wav" --data-binary "not-audio"` | HTTP 415 `UNSUPPORTED_MEDIA_TYPE` |
| 5 | Upload `$XLSX` as admin with `-F "file=@$XLSX;type=application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"` | HTTP 415 `UNSUPPORTED_MEDIA_TYPE`, detail "Upload a CSV file (text/csv)." |
| 6 | Re-run the counts | All unchanged after steps 2–5 |

### TC-026-05 JSON batch of 3 with one bad `audio_quality_flag`: 202, accepted 2, rejected 1, `invalid_enum` rejection with `row_number` 2

| Step | Action | Expected Result |
|---|---|---|
| 1 | Ingest test database state. Build `mixed.json` = `{"records": [R01-20261001-01, R01-20261002-01 with "audio_quality_flag": "bad", R01-20261003-01]}` from SRC-05 rows (numbers as JSON numbers) | File ready |
| 2 | POST it with the ingest key | HTTP 202; `source` "api_batch"; `accepted` 2; `rejected` 1; `duplicates` 0; `pipeline_run_id` not null |
| 3 | `SELECT row_number, errors, raw_body->>'session_id', ingest_batch_id FROM ingest_rejections;` | 1 row: `row_number` 2; `errors` contains an item with `field` "audio_quality_flag" and `code` "invalid_enum"; session id "R01-20261002-01"; `ingest_batch_id` = the response batch id |
| 4 | `SELECT session_id FROM raw_sessions ORDER BY arrival_seq;` | R01-20261001-01, R01-20261003-01 (the rejected record is not stored) |

### TC-026-06 Re-upload of SRC-05 returns duplicates 283, accepted 283, no pipeline run

| Step | Action | Expected Result |
|---|---|---|
| 1 | After TC-026-01, wait until its run is finished (`GET $API/pipeline/runs/<pipeline_run_id>` as admin shows `status` "succeeded"); note `SELECT count(*) FROM pipeline_runs;` (= N) | Run succeeded |
| 2 | Upload `$SRC05` again as admin | HTTP 202; `accepted` 283; `rejected` 0; `duplicates` 283; `pipeline_run_id` null |
| 3 | `SELECT count(*) FROM raw_sessions;` and `SELECT count(*) FROM pipeline_runs;` | 566 raw rows; `pipeline_runs` still N |
| 4 | `GET $API/residents` as admin | Same `summary` and rows as before step 2 (re-sent records change no derived result) |

### TC-026-07 One `ingest.batch.received` audit row with counts and the response `X-Request-ID`

| Step | Action | Expected Result |
|---|---|---|
| 1 | In TC-026-01 step 2, note the response header `X-Request-ID` and `ingest_batch_id` | Values noted |
| 2 | `SELECT actor_type, actor_id, entity_type, entity_id, details, request_id FROM audit_logs WHERE action='ingest.batch.received';` | Exactly 1 row per upload so far; for the SRC-05 upload: `actor_type` `user`, `actor_id` = admin user id, `entity_type` "ingest_batch", `entity_id` = the batch id, `details` contains `source` "csv_upload", `record_count` 283, `accepted` 283, `rejected` 0, `duplicates` 2; `request_id` = the `X-Request-ID` value |
| 3 | Inspect `details` | No feature value, payload or `raw_body` in the details |

### TC-026-08 Role checks: clinician POST 403; researcher GET 200; clinician GET 403; unknown id 404

| Step | Action | Expected Result |
|---|---|---|
| 1 | Upload `$SRC05` with `Authorization: Bearer $CLIN` | HTTP 403 `FORBIDDEN`; no new `ingest_batches` row |
| 2 | Upload with `Authorization: Bearer $RES` | HTTP 403 `FORBIDDEN` |
| 3 | `GET $API/ingest/batches/<id from TC-026-01>` with `$RES` | HTTP 200 |
| 4 | Same GET with `$CLIN` | HTTP 403 `FORBIDDEN` |
| 5 | Same GET with `X-API-Key: $KEY` only | HTTP 401 `NOT_AUTHENTICATED` |
| 6 | `GET $API/ingest/batches/00000000-0000-4000-8000-000000000000` with `$ADMIN` | HTTP 404; `type` "urn:echowell:error:BATCH_NOT_FOUND"; `title` "Ingest batch not found" |
| 7 | Upload with no credentials | HTTP 401 |

### TC-026-09 Batch read-out validates against `IngestBatch` and holds no `raw_body` or payload

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET $API/ingest/batches/<batch id of TC-026-05>` as admin | HTTP 200; keys `id`, `source` ("api_batch"), `filename` (null), `record_count` 3, `accepted_count` 2, `rejected_count` 1, `duplicate_count` 0, `uploaded_by` (null, API key), `received_at` (UTC with Z), `pipeline_run_id`, `rejections` |
| 2 | Inspect `rejections` | 1 item with `row_number` 2, `session_id` "R01-20261002-01", `received_at`, `errors` (incl. `invalid_enum`); no `raw_body` key |
| 3 | `grep` the whole response for `raw_body`, `payload` and `loudness_dbfs` | No match |
| 4 | Validate the body against `components.schemas.IngestBatch` of `GET $API/openapi.json` (e.g. Swagger "Schema" tab or a JSON-schema validator) | Valid; no `meta` block (OAS-017) |

### TC-026-10 Exactly one background run per batch with a first arrival; none when all rejected or duplicates

| Step | Action | Expected Result |
|---|---|---|
| 1 | After TC-026-01: `SELECT id, trigger, status, scope FROM pipeline_runs;` | Exactly 1 row, `id` = response `pipeline_run_id`, `trigger` `ingest`, `scope` type `residents` with codes R01–R10; status moves from `running` to `succeeded` within 30 s (TST-124 budget) |
| 2 | `SELECT pipeline_run_id FROM ingest_batches WHERE id='<batch id>';` | Equals the response `pipeline_run_id` |
| 3 | POST a JSON batch whose only record has `resident_id` "R11" | HTTP 202; `accepted` 0; `rejected` 1; `pipeline_run_id` null; no new `pipeline_runs` row |
| 4 | The re-upload of TC-026-06 | `pipeline_run_id` null; no new `pipeline_runs` row |

### TC-026-11 JSON batch via API key: `source` `api_batch`, `api_key_id` set, `api_keys.last_used_at` updated

| Step | Action | Expected Result |
|---|---|---|
| 1 | Note `SELECT last_used_at FROM api_keys WHERE name='test-ingest';` | Value noted (may be NULL) |
| 2 | POST `{"records": [SRC-05 row R02-20261001-01]}` with the ingest key | HTTP 202, `source` "api_batch", `accepted` 1 |
| 3 | `SELECT source, uploaded_by, api_key_id FROM ingest_batches ORDER BY received_at DESC LIMIT 1;` | `api_batch`, NULL, the `test-ingest` key id |
| 4 | Re-read `last_used_at` | Later than the value of step 1 |
| 5 | `SELECT actor_type FROM audit_logs WHERE action='ingest.batch.received' ORDER BY id DESC LIMIT 1;` | `api_key` |

### TC-026-12 Duplicate inside one batch is counted; differing copy carries `duplicate_payload_differs`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Ingest test database state. POST `{"records": [R05-20261001-01, R05-20261001-01 with hnr_db + 1]}` with the ingest key | HTTP 202; `accepted` 2; `duplicates` 1 |
| 2 | `SELECT arrival_seq, ingest_warnings FROM raw_sessions WHERE session_id='R05-20261001-01' ORDER BY arrival_seq;` | 2 rows; first `ingest_warnings` has no `duplicate_payload_differs`; second contains an item with `code` "duplicate_payload_differs" |
| 3 | POST `{"records": [R05-20261001-01]}` again (unchanged) | `duplicates` 1 (already in `raw_sessions` before the batch); `pipeline_run_id` null |

### TC-026-13 Malformed JSON / missing `records` returns 422 `VALIDATION_ERROR`; malformed batch id returns 422 `INVALID_QUERY_PARAMETER`

| Step | Action | Expected Result |
|---|---|---|
| 1 | POST body `{not json` with `Content-Type: application/json` and the ingest key | HTTP 422 `VALIDATION_ERROR`, detail "The request body is not valid JSON." |
| 2 | POST `{"items": []}` | HTTP 422 `VALIDATION_ERROR`; `errors[]` has `field` "records", `code` "missing_field" |
| 3 | `GET $API/ingest/batches/not-a-uuid` as admin | HTTP 422; `type` "urn:echowell:error:INVALID_QUERY_PARAMETER" |
| 4 | Count `raw_sessions`, `ingest_rejections`, `ingest_batches` | Unchanged by steps 1–2 |

### TC-026-14 CSV with a missing column lists the missing name; reordered columns with BOM and CRLF are accepted

| Step | Action | Expected Result |
|---|---|---|
| 1 | Create `nomfcc4.csv` = `$SRC05` without the last column: `cut -d, -f1-29 $SRC05 > nomfcc4.csv` | 29 columns |
| 2 | Upload it as admin | HTTP 422 `CSV_HEADER_MISMATCH`; `errors[]` contains `{"field": "mfcc4", "code": "missing_field", ...}`; nothing stored |
| 3 | Ingest test database state. Create `reordered.csv`: first 3 lines of `$SRC05` with columns `mfcc4` and `schema_version` swapped, a UTF-8 BOM at the start and CRLF line ends | File ready |
| 4 | Upload `reordered.csv` as admin | HTTP 202; `accepted` 2; `rejected` 0 |

### TC-026-15 Responses and logs carry no feature value; log events `ingest_batch_completed` and `ingest_request` present

| Step | Action | Expected Result |
|---|---|---|
| 1 | Perform TC-026-05 | 202 |
| 2 | `docker compose logs backend --since 2m \| grep '"event": *"ingest_'` | One `ingest_record_rejected` (WARNING, `session_id` "R01-20261002-01", `row_number` 2, field `audio_quality_flag`); one `ingest_batch_completed` (INFO, `ingest_batch_id`, `accepted` 2, `rejected` 1, `duplicates` 0, `duration_ms`); one `ingest_request` (`endpoint` "POST /api/v1/ingest", `api_key_id`, `record_count` 3, counts, `warning_count`, `duration_ms`) |
| 3 | Search the same log window for "-30.67" and for the ingest key value from the environment file | No match |

Note: TRD 17 LOG-053 (and FEAT-026 Logging Requirements) require `ingest_batch_completed`; the code emits no such event (no occurrence under `backend/`; the batch path logs only `ingest_request` at `backend/services/ingestion.py:176-193` and `ingest_record_rejected` at `ingestion.py:445-454`). Expected result written per the TRD.

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `POST /api/v1/ingest` JSON or multipart, valid envelope | 202 `IngestBatchAccepted` `{ingest_batch_id, source, accepted, rejected, duplicates, pipeline_run_id}`; no `meta` |
| 2 | Record-level errors only | Still 202, counted in `rejected` (also when `accepted` = 0) |
| 3 | Envelope errors | 422 `VALIDATION_ERROR` / `EMPTY_BATCH` / `CSV_HEADER_MISMATCH`, 413 `PAYLOAD_TOO_LARGE`, 415 `UNSUPPORTED_MEDIA_TYPE`, all `application/problem+json` |
| 4 | `GET /api/v1/ingest/batches/{id}` | 200 `IngestBatch`; 404 `BATCH_NOT_FOUND`; 422 `INVALID_QUERY_PARAMETER` for a malformed uuid |
| 5 | Auth | POST: admin JWT or `ingest:write` key; clinician/researcher 403; none 401. GET: admin, researcher 200; clinician 403; API key 401 |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `ingest_batches` per accepted envelope | 1 row; CHECKs hold: `filename` set for `csv_upload`; `uploaded_by` or `api_key_id` set; counts ≥ 0 |
| 2 | `raw_sessions` | One row per accepted record (duplicates included), `ingest_batch_id` set, `arrival_seq` in input order, `payload` = record as received (CSV: header → cell text) |
| 3 | `ingest_rejections` | One row per invalid record with `ingest_batch_id`, `row_number` = 1-based batch position, `raw_body`, `errors` |
| 4 | `audit_logs` | One `ingest.batch.received` row per accepted envelope, none for envelope errors |
| 5 | `pipeline_runs` | One `ingest` row per batch with a first arrival, linked from `ingest_batches.pipeline_run_id` |
| 6 | Envelope error | No row in any of the tables above |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Legacy SRC-06 file (TC-026-02) | 422 `CSV_HEADER_MISMATCH`; nothing stored |
| 2 | Answer-key columns (TC-026-03) | 422 `CSV_HEADER_MISMATCH`, `extra_forbidden` |
| 3 | Empty / oversize / audio / `.xlsx` (TC-026-04) | 422 / 413 / 415 / 415; nothing stored |
| 4 | Malformed JSON, missing `records` (TC-026-13) | 422 `VALIDATION_ERROR` |
| 5 | Missing CSV column (TC-026-14) | 422 `CSV_HEADER_MISMATCH` with `missing_field` |
| 6 | Clinician or researcher POST; clinician GET; unknown id (TC-026-08) | 403 / 403 / 404 `BATCH_NOT_FOUND` |
| 7 | Database stopped (`docker compose stop db`) then a JSON batch POST | 503 `SERVICE_UNAVAILABLE` with `Retry-After: 30`; after `docker compose start db` no partial rows |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-026-AC-01 | SRC-05 upload as admin: 202, accepted 283, rejected 0, duplicates 2, `source` csv_upload, non-null `pipeline_run_id`; 283 raw rows in CSV row order | TC-026-01 |
| FEAT-026-AC-02 | Legacy SRC-06 file: 422 `urn:echowell:error:CSV_HEADER_MISMATCH`; counts of `raw_sessions`, `ingest_rejections`, `ingest_batches` unchanged | TC-026-02 |
| FEAT-026-AC-03 | Header with `expected_status`: 422 `CSV_HEADER_MISMATCH` with an `extra_forbidden` item naming `expected_status`; nothing stored | TC-026-03 |
| FEAT-026-AC-04 | `{"records": []}` 422 `EMPTY_BATCH`; 5,001 records 413 `PAYLOAD_TOO_LARGE`; `audio/wav` 415; no rows | TC-026-04 |
| FEAT-026-AC-05 | 3-record batch with `audio_quality_flag` "bad" in the second: 202, accepted 2, rejected 1, one rejection with code `invalid_enum` | TC-026-05 |
| FEAT-026-AC-06 | Re-upload of SRC-05: `duplicates` 283, `accepted` 283 | TC-026-06 |
| FEAT-026-AC-07 | One `ingest.batch.received` row, entity id = batch id, details with `record_count`, `accepted`, `rejected`, `duplicates`; `request_id` = response `X-Request-ID` | TC-026-07 |
| FEAT-026-AC-08 | Clinician POST 403; researcher GET 200; clinician GET 403; unknown id 404 `BATCH_NOT_FOUND` | TC-026-08 |
| FEAT-026-AC-09 | GET body validates against `IngestBatch`; no `raw_body` or payload field | TC-026-09 |
| FEAT-026-AC-10 | One background `pipeline_runner.run` with `trigger` "ingest" per accepted batch; none (`pipeline_run_id` null) when all records rejected or duplicates | TC-026-10, TC-026-06 |

## Test Data Requirements

- `test_v0_1` master data via `seed test_v0_1 --master-only --reset`.
- SRC-05 `tests/fixtures/pipeline_input/EchoWell_pipeline_test_input_v0_1.csv` (283 rows, 2 duplicate arrivals of R04); derived files `answerkey.csv`, `nomfcc4.csv`, `reordered.csv`, `mixed.json`, `big.json` built by the commands in the steps.
- Legacy SRC-06 `tests/fixtures/legacy/echowell_mock_data_500.csv` (synthetic, never ingested).
- `.xlsx` answer key `tests/fixtures/answer_key/EchoWell_pipeline_test_v0_1.xlsx` (only as a refused upload).
- Synthetic fixture R11 (not enrolled).
- Environment: `SEED_INGEST_API_KEY`, `SEED_ADMIN_PASSWORD`, `SEED_CLINICIAN_PASSWORD`, `SEED_RESEARCHER_PASSWORD` from the environment file; `RATE_LIMIT_INGEST=600/minute` (not exceeded by these cases).
- No audio: the 415 case sends the text "not-audio".

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-026-FR-01 (API-048, ING-005, ING-012, ING-053; FR-002, FR-003) | FEAT-026 | TC-026-01, TC-026-04, TC-026-11 |
| FEAT-026-FR-02 (API-049, API-015; FR-004) | FEAT-026 | TC-026-08, TC-026-11 |
| FEAT-026-FR-03 (API-031) | FEAT-026 | TC-026-05, TC-026-09 |
| FEAT-026-FR-04 (ING-007, API-050, API-104) | FEAT-026 | TC-026-04, TC-026-13 |
| FEAT-026-FR-05 (ING-031; FR-003) | FEAT-026 | TC-026-14 |
| FEAT-026-FR-06 (ING-053) | FEAT-026 | TC-026-03 |
| FEAT-026-FR-07 (ING-055, ING-056, D-25; FR-032) | FEAT-026 | TC-026-02 |
| FEAT-026-FR-08 (ING-006, API-051; FR-011) | FEAT-026 | TC-026-05, TC-026-10 |
| FEAT-026-FR-09 (ING-032, ING-029, API-042, API-043) | FEAT-026 | TC-026-01 |
| FEAT-026-FR-10 (ING-032, API-041, D-84) | FEAT-026 | TC-026-05 |
| FEAT-026-FR-11 (ING-006; FR-010) | FEAT-026 | TC-026-01, TC-026-11 |
| FEAT-026-FR-12 (ING-008, ING-037, ING-023) | FEAT-026 | TC-026-12, TC-026-06 |
| FEAT-026-FR-13 (ING-058) | FEAT-026 | TC-026-07, TC-026-11 |
| FEAT-026-FR-14 (API-053, ANL-044) | FEAT-026 | TC-026-10 |
| FEAT-026-FR-15 (API-052; FR-009) | FEAT-026 | TC-026-01 |
| FEAT-026-FR-16 (API-055) | FEAT-026 | TC-026-10 (step 1: run `warnings` checked by FEAT-054) |
| FEAT-026-FR-17 (ING-009, API-054, DME-005) | FEAT-026 | TC-026-08, TC-026-09 |
| FEAT-026-FR-18 (API-056, LOG-021) | FEAT-026 | TC-026-15 |
| FEAT-026-FR-19 (DME-018, D-25) | FEAT-026 | TC-026-02 |
| TST-046 / AC-ING-01 | FEAT-026 | TC-026-01 |
| TST-047 / AC-API-17 / TDV-005 | FEAT-026 | TC-026-02 |
| AC-ING-06 | FEAT-026 | TC-026-03 |
| AC-ING-03 | FEAT-026 | TC-026-06 |
| TST-053 / AC-SEC-09 | FEAT-026 | TC-026-07 |
| TST-124 | FEAT-026 | TC-026-10 (run within 30 s) |
| TRD 19 E-06, E-07 | FEAT-026 | TC-026-01, TC-026-09 |
