# FEAT-010 Immutable ingest store tables

## Feature Description

FEAT-010 creates the raw record store, the single source of truth of EchoWell: `raw_sessions` (every accepted arrival exactly as received, duplicates included, never edited), `ingest_rejections` (schema-invalid records with a non-empty error list) and `ingest_batches` (one row per upload or batch). `raw_sessions` has one typed column per schema-v0.1 field and per feature (19 features, `number_of_pauses` integer, the rest `double precision`), `arrival_seq` from a sequence, `payload` jsonb, CHECK constraints (TRD 20 §4.6.9), and is protected twice: `echowell_app` holds only SELECT and INSERT, and the triggers `raw_sessions_no_update_delete` / `raw_sessions_no_truncate` call `reject_mutation()` (SQLSTATE `EW001`). No column stores audio; the only audio-related column is `audio_quality_flag`.

## Preconditions

- Local Docker Compose stack running and seeded: `cp .env.development.example .env && docker compose up --build -d`, then `docker compose exec backend python -m backend.cli seed test_v0_1` (283 arrivals of DS-01 / SRC-05).
- Connection shorthands (inside the `db` container, which holds the `ECHOWELL_*_DB_PASSWORD` variables; no password typed):
  - `SU` = `docker compose exec db psql -U echowell -d echowell -v VERBOSITY=verbose -v ON_ERROR_ROLLBACK=on`
  - `APP` = `docker compose exec db sh -c 'PGPASSWORD=$ECHOWELL_APP_DB_PASSWORD psql -h 127.0.0.1 -U echowell_app_login -d echowell -v VERBOSITY=verbose -v ON_ERROR_ROLLBACK=on'`
  - `OWNER` = the same with `ECHOWELL_MIGRATOR_DB_PASSWORD` and `echowell_migrator_login`, followed by `SET ROLE echowell_migrator;` (the table owner).
- Every mutating case runs inside `BEGIN; … ROLLBACK;`. `ON_ERROR_ROLLBACK=on` keeps the transaction usable after an expected error; `VERBOSITY=verbose` prints the SQLSTATE after `ERROR:`.
- Clone recipe for `raw_sessions` inserts (as `APP`, inside the transaction):
  1. `SELECT string_agg(quote_ident(column_name), ', ' ORDER BY ordinal_position) AS cols FROM information_schema.columns WHERE table_schema='public' AND table_name='raw_sessions' AND column_name NOT IN ('id','arrival_seq','received_at') \gset`
  2. `CREATE TEMP TABLE t AS SELECT :cols FROM raw_sessions WHERE session_id = 'R01-20261001-01' ORDER BY arrival_seq LIMIT 1;`
  3. `UPDATE t SET <column> = <value>;` (the override named in the step)
  4. `INSERT INTO raw_sessions (:cols) SELECT :cols FROM t;` (the sequence assigns `arrival_seq`)
  5. `DROP TABLE t;`

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-010-01 | UPDATE on `raw_sessions` fails 42501 as app and `EW001` as owner; row unchanged | High | Security |
| TC-010-02 | DELETE and TRUNCATE fail for app and for owner without the purge setting | High | Security |
| TC-010-03 | `has_table_privilege` shows no UPDATE/DELETE for app on `raw_sessions` and `ingest_rejections`; INSERT allowed | High | Database |
| TC-010-04 | CHECK violations on insert fail with 23514 | High | Negative |
| TC-010-05 | Feature column names equal the 19 SRC-05 feature names; `number_of_pauses` is integer | High | Database |
| TC-010-06 | Two inserts with the same `session_id` both succeed with increasing `arrival_seq` | High | Database |
| TC-010-07 | `ingest_rejections` with empty `errors` and `csv_upload` batch without filename fail 23514 | High | Negative |
| TC-010-08 | Migration round trip leaves the three tables present | High | Database |
| TC-010-09 | `payload` keeps the record as received; typed columns, codes and UTC instants match it | Medium | Database |
| TC-010-10 | Seed batch row and counts; ingest batch CHECKs | Medium | Database |
| TC-010-11 | Sequence grant, repository without update/delete, no audio column, no answer key | Medium | Security |

### TC-010-01 UPDATE on `raw_sessions` fails 42501 as app and `EW001` as owner; row unchanged

| Step | Action | Expected Result |
|---|---|---|
| 1 | `APP`: `SELECT arrival_seq, phrase_id FROM raw_sessions WHERE session_id='R01-20261001-01';` | One row, `phrase_id` = `P01`; note `arrival_seq`. |
| 2 | `APP`: `BEGIN; UPDATE raw_sessions SET phrase_id = 'x' WHERE session_id='R01-20261001-01'; ROLLBACK;` | `ERROR:  42501: permission denied for table raw_sessions`. |
| 3 | `OWNER`: `BEGIN; UPDATE raw_sessions SET phrase_id = 'x' WHERE session_id='R01-20261001-01'; ROLLBACK;` | `ERROR:  EW001: table raw_sessions is append-only: UPDATE is not allowed`. |
| 4 | `OWNER`: `BEGIN; SET LOCAL echowell.allow_purge = 'on'; UPDATE raw_sessions SET phrase_id = 'x' WHERE session_id='R01-20261001-01'; ROLLBACK;` | `EW001 … UPDATE is not allowed` (the purge setting never allows UPDATE). |
| 5 | Repeat step 1. | Same `arrival_seq`, `phrase_id` still `P01`. |
| 6 | Run `pytest -q tests/integration/db/test_raw_store.py`. | All tests pass. |

### TC-010-02 DELETE and TRUNCATE fail for app and for owner without the purge setting

| Step | Action | Expected Result |
|---|---|---|
| 1 | `APP`: `BEGIN; DELETE FROM raw_sessions WHERE session_id='R01-20261001-01';` | `42501: permission denied for table raw_sessions`. |
| 2 | `APP` (same transaction): `TRUNCATE raw_sessions;` then `ROLLBACK;` | `42501: permission denied for table raw_sessions`. |
| 3 | `OWNER`: `BEGIN; DELETE FROM raw_sessions WHERE session_id='R01-20261001-01';` | `EW001: table raw_sessions is append-only: DELETE is not allowed`. |
| 4 | `OWNER` (same transaction): `TRUNCATE raw_sessions CASCADE;` then `ROLLBACK;` | `EW001: table raw_sessions is append-only: TRUNCATE is not allowed` (CASCADE is used only because derived tables reference `raw_sessions`; the trigger rejects the statement, nothing is truncated). |
| 5 | `APP`: `SELECT count(*) FROM raw_sessions;` | `283` (unchanged). |
| 6 | `OWNER`: `BEGIN;` run the clone recipe (no override) to add one fresh row, then `DELETE FROM raw_sessions WHERE arrival_seq = (SELECT max(arrival_seq) FROM raw_sessions);` | `EW001 … DELETE is not allowed` (no purge setting yet). |
| 7 | `OWNER` (same transaction): `SET LOCAL echowell.allow_purge = 'on';` and repeat the DELETE of step 6, then `ROLLBACK;` | `DELETE 1`: the trigger lets DELETE through only for `echowell_migrator` with the purge setting (PGS-019); the rollback removes the test row. |

### TC-010-03 `has_table_privilege` shows no UPDATE/DELETE for app on `raw_sessions` and `ingest_rejections`; INSERT allowed

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SU`: `SELECT has_table_privilege('echowell_app','raw_sessions','UPDATE'), has_table_privilege('echowell_app','raw_sessions','DELETE'), has_table_privilege('echowell_app','raw_sessions','TRUNCATE'), has_table_privilege('echowell_app','ingest_rejections','UPDATE'), has_table_privilege('echowell_app','ingest_rejections','DELETE');` | `f`, `f`, `f`, `f`, `f`. |
| 2 | `SU`: `SELECT has_table_privilege('echowell_app','raw_sessions','INSERT'), has_table_privilege('echowell_app','raw_sessions','SELECT'), has_table_privilege('echowell_app','ingest_rejections','INSERT');` | `t`, `t`, `t`. |
| 3 | `SU`: `SELECT has_table_privilege('echowell_app','ingest_batches','UPDATE'), has_table_privilege('echowell_app','ingest_batches','DELETE');` | `t`, `f` (batches carry counts updated by the service; never deleted). |
| 4 | Run `pytest -q tests/integration/db/test_grants.py`. | All tests pass (TST-041). |

### TC-010-04 CHECK violations on insert fail with 23514

| Step | Action | Expected Result |
|---|---|---|
| 1 | `APP`: `BEGIN;` then the clone recipe with override `audio_quality_flag = 'bad'`. | `ERROR:  23514: new row for relation "raw_sessions" violates check constraint "raw_sessions_audio_quality_flag_ck"`. |
| 2 | Clone recipe with `number_of_pauses = -1`. | `23514` on `raw_sessions_number_of_pauses_ck`. |
| 3 | Clone recipe with `pause_fraction = 1.5`. | `23514` on `raw_sessions_pause_fraction_ck`. |
| 4 | Clone recipe with `mean_f0_hz = 0`. | `23514` on `raw_sessions_mean_f0_ck`. |
| 5 | Clone recipe with `phrase_id = repeat('P', 17)`. | `23514` on `raw_sessions_phrase_id_ck`. |
| 6 | Clone recipe with `voiced_fraction = -0.01`; then `speech_duration_s = -1`; then `payload = '[]'::jsonb`; then `extraction_software_version = ''`. | `23514` on `raw_sessions_voiced_fraction_ck`, `raw_sessions_speech_duration_ck`, `raw_sessions_payload_ck`, `raw_sessions_versions_ck` respectively. |
| 7 | Clone recipe with `audio_quality_flag = 'poor'`. | `INSERT 0 1` (boundary value accepted). |
| 8 | Clone recipe with `resident_id = gen_random_uuid()`. | `ERROR:  23503: … violates foreign key constraint "raw_sessions_resident_id_fkey"`. |
| 9 | `ROLLBACK;` | Nothing stored. |

### TC-010-05 Feature column names equal the 19 SRC-05 feature names; `number_of_pauses` is integer

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `head -1 database/seeds/test_v0_1/EchoWell_pipeline_test_input_v0_1.csv \| tr ',' '\n' \| tail -n 19`. | The 19 feature names: `loudness_dbfs`, `total_phrase_duration_s`, `speech_rate_syl_per_s`, `articulation_rate_syl_per_s`, `number_of_pauses`, `pause_fraction`, `voiced_fraction`, `mean_f0_hz`, `f0_variability_st`, `jitter_local_pct`, `shimmer_local_pct`, `hnr_db`, `cpps_db`, `alpha_ratio_db`, `hammarberg_index_db`, `mfcc1`, `mfcc2`, `mfcc3`, `mfcc4`. |
| 2 | `APP`: `SELECT column_name, data_type FROM information_schema.columns WHERE table_name='raw_sessions' AND ordinal_position > (SELECT ordinal_position FROM information_schema.columns WHERE table_name='raw_sessions' AND column_name='phrase_id') ORDER BY ordinal_position;` | The same 19 names in the same order; `number_of_pauses` = `integer`; the other 18 = `double precision`; all `NOT NULL`. |
| 3 | `APP`: `SELECT column_name FROM information_schema.columns WHERE table_name='raw_sessions' AND ordinal_position BETWEEN (SELECT ordinal_position FROM information_schema.columns WHERE table_name='raw_sessions' AND column_name='schema_version') AND (SELECT ordinal_position FROM information_schema.columns WHERE table_name='raw_sessions' AND column_name='phrase_id') ORDER BY ordinal_position;` | `schema_version, session_id, resident_code, device_code, timestamp_utc, mic_noise_level_dbfs, audio_quality_flag, extraction_software_version, device_firmware_version, speech_duration_s, phrase_id` (SRC-05 order, codes stored in `*_code`). |

### TC-010-06 Two inserts with the same `session_id` both succeed with increasing `arrival_seq`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `APP`: `SELECT session_id, array_agg(arrival_seq ORDER BY arrival_seq) FROM raw_sessions GROUP BY session_id HAVING count(*) > 1;` | 2 rows (the 2 DS-01 duplicates), each with two increasing `arrival_seq` values. |
| 2 | `APP`: `BEGIN;` run the clone recipe twice without override (same `session_id` `R01-20261001-01`). | Both `INSERT 0 1`. |
| 3 | `SELECT arrival_seq FROM raw_sessions WHERE session_id='R01-20261001-01' ORDER BY arrival_seq;` | 3 values, strictly increasing; the two new values are greater than every earlier `arrival_seq`. `ROLLBACK;` |
| 4 | Run `pytest -q tests/unit/backend/repositories/test_raw_session_repository.py`. | Passes (the repository never sets `arrival_seq`). |

### TC-010-07 `ingest_rejections` with empty `errors` and `csv_upload` batch without filename fail 23514

| Step | Action | Expected Result |
|---|---|---|
| 1 | `APP`: `BEGIN; INSERT INTO ingest_rejections (raw_body, errors) VALUES ('{"session_id":"R11-20261001-01"}', '[]');` | `23514` on `ingest_rejections_errors_ck`. |
| 2 | `INSERT INTO ingest_rejections (raw_body, errors, row_number) VALUES ('{}', '[{"field":"session_id","code":"missing","message":"required"}]', 0);` | `23514` on `ingest_rejections_row_number_ck`. |
| 3 | Same with `row_number` 1. | `INSERT 0 1`. |
| 4 | `INSERT INTO ingest_batches (source, uploaded_by) SELECT 'csv_upload', id FROM users WHERE email='admin@example.com';` | `23514` on `ingest_batches_filename_ck`. |
| 5 | Same with `filename` `'qa.csv'`. | `INSERT 0 1`. |
| 6 | `ROLLBACK;` | Nothing stored. |

### TC-010-08 Migration round trip leaves the three tables present

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run the round trip of TC-008-01 on a throwaway database `echowell_qa` (`upgrade head`, `downgrade base`, `upgrade head`). | All three commands exit 0. |
| 2 | `SU` on `echowell_qa`: `SELECT tablename FROM pg_tables WHERE tablename IN ('raw_sessions','ingest_rejections','ingest_batches') ORDER BY 1;` | 3 rows: `ingest_batches`, `ingest_rejections`, `raw_sessions`. |
| 3 | `SU` on `echowell_qa`: `SELECT tgname FROM pg_trigger WHERE tgrelid IN ('raw_sessions'::regclass, 'ingest_batches'::regclass) AND NOT tgisinternal ORDER BY 1;` | `ingest_batches_set_updated_at`, `raw_sessions_no_truncate`, `raw_sessions_no_update_delete`. Drop `echowell_qa` afterwards. |

### TC-010-09 `payload` keeps the record as received; typed columns, codes and UTC instants match it

| Step | Action | Expected Result |
|---|---|---|
| 1 | `APP`: `SELECT payload->>'loudness_dbfs', loudness_dbfs, payload->>'number_of_pauses', number_of_pauses, payload->>'timestamp_utc', timestamp_utc FROM raw_sessions WHERE session_id='R01-20261001-01';` | `-30.67`, `-30.67`, `1`, `1`, `2026-10-01 19:45:11`, `2026-10-01 19:45:11+00` (payload holds the CSV cell strings; typed columns are conversions; instant in UTC). |
| 2 | `APP`: `SELECT count(*) FROM jsonb_object_keys((SELECT payload FROM raw_sessions WHERE session_id='R01-20261001-01'));` | `30` (one key per SRC-05 header column). |
| 3 | `APP`: `SELECT r.resident_code, rs.resident_code, d.device_code, rs.device_code FROM raw_sessions rs JOIN residents r ON r.id = rs.resident_id JOIN devices d ON d.id = rs.device_id WHERE rs.session_id='R01-20261001-01';` | `R01`, `R01`, `D01`, `D01` (UUID FKs resolve to the received codes). |
| 4 | `APP`: `SELECT jsonb_typeof(ingest_warnings) FROM raw_sessions LIMIT 1;` | `array`. |

### TC-010-10 Seed batch row and counts; ingest batch CHECKs

| Step | Action | Expected Result |
|---|---|---|
| 1 | `APP`: `SELECT source, filename, record_count, accepted_count, rejected_count, duplicate_count, uploaded_by, api_key_id FROM ingest_batches WHERE source='seed';` | One row per seed run: `seed`, filename may be NULL, `record_count` 283, `accepted_count` 283, `rejected_count` 0, `duplicate_count` 2; `uploaded_by` and `api_key_id` NULL (allowed only for `seed`). |
| 2 | `APP`: `BEGIN; INSERT INTO ingest_batches (source) VALUES ('api_batch');` | `23514` on `ingest_batches_actor_ck`. |
| 3 | `INSERT INTO ingest_batches (source, record_count, accepted_count, rejected_count) VALUES ('seed', 2, 2, 1);` | `23514` on `ingest_batches_counts_ck` (accepted + rejected > record). |
| 4 | `INSERT INTO ingest_batches (source, record_count, accepted_count, duplicate_count) VALUES ('seed', 2, 1, 2);` then `ROLLBACK;` | `23514` on `ingest_batches_counts_ck` (duplicates > accepted). |
| 5 | `APP`: `SELECT count(*) FROM ingest_rejections;` | `0` after the seed (all DS-01 rows are schema-valid). |

### TC-010-11 Sequence grant, repository without update/delete, no audio column, no answer key

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SU`: `SELECT has_sequence_privilege('echowell_app','raw_sessions_arrival_seq_seq','USAGE'), has_sequence_privilege('echowell_app','raw_sessions_arrival_seq_seq','UPDATE');` | `t`, `f`. |
| 2 | Run `grep -n "def " backend/repositories/raw_session_repository.py \| grep -iE "update\|delete\|truncate"; echo "exit=$?"`. | `exit=1`: no update, delete or truncate method. |
| 3 | `APP`: `SELECT table_name, column_name FROM information_schema.columns WHERE table_schema='public' AND column_name ILIKE '%audio%';` | One row: `raw_sessions`, `audio_quality_flag`. |
| 4 | `APP`: `SELECT table_name, column_name FROM information_schema.columns WHERE table_name IN ('raw_sessions','ingest_rejections','ingest_batches') AND column_name ~ '(expected\|planted\|onset\|answer)';` | 0 rows (no SRC-03 answer-key column in the ingest store). |
| 5 | `APP`: `SELECT data_type FROM information_schema.columns WHERE table_name='raw_sessions' AND column_name IN ('timestamp_utc','received_at');` | `timestamp with time zone` for both. |

## API Validation

Not applicable: FEAT-010 exposes no endpoint; the ingest endpoints that write these tables (`POST /api/v1/sessions`, `POST /api/v1/ingest`) belong to FEAT-025/FEAT-026.

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT count(*) FROM raw_sessions;` after the seed | 283 |
| 2 | Privileges (TC-010-03) | App: SELECT, INSERT only on `raw_sessions`, `ingest_rejections` |
| 3 | Triggers on `raw_sessions` (TC-010-08) | `raw_sessions_no_update_delete`, `raw_sessions_no_truncate` |
| 4 | Duplicates (TC-010-06) | 2 `session_id`s with two `raw_sessions` rows each |
| 5 | Column types (TC-010-05) | 19 features; `number_of_pauses` integer |
| 6 | FK targets: `SELECT conname FROM pg_constraint WHERE conrelid='raw_sessions'::regclass AND contype='f' ORDER BY 1;` | `raw_sessions_api_key_id_fkey`, `raw_sessions_device_id_fkey`, `raw_sessions_ingest_batch_id_fkey`, `raw_sessions_resident_id_fkey` |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | UPDATE as app / owner (TC-010-01) | 42501 / `EW001` |
| 2 | DELETE, TRUNCATE as app / owner (TC-010-02) | 42501 / `EW001` |
| 3 | CHECK-violating inserts (TC-010-04) | 23514 |
| 4 | Unknown resident FK (TC-010-04 step 8) | 23503 |
| 5 | Empty `errors`; `csv_upload` without filename (TC-010-07) | 23514 |
| 6 | Batch without actor or inconsistent counts (TC-010-10) | 23514 |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-010-AC-01 | App `UPDATE raw_sessions SET phrase_id = 'x'` → 42501; owner → `EW001`; row unchanged. | TC-010-01 |
| FEAT-010-AC-02 | `DELETE FROM raw_sessions` and `TRUNCATE raw_sessions` fail for app and for owner without `echowell.allow_purge = 'on'`. | TC-010-02 |
| FEAT-010-AC-03 | `has_table_privilege` app UPDATE/DELETE on `raw_sessions` and UPDATE on `ingest_rejections` false; INSERT on `raw_sessions` true. | TC-010-03 |
| FEAT-010-AC-04 | `audio_quality_flag = 'bad'`, `number_of_pauses = -1`, `pause_fraction = 1.5`, `mean_f0_hz = 0`, 17-char `phrase_id` each → 23514. | TC-010-04 |
| FEAT-010-AC-05 | Feature columns equal the 19 SRC-05 feature names; `number_of_pauses` integer. | TC-010-05 |
| FEAT-010-AC-06 | Two inserts with the same `session_id` succeed with increasing `arrival_seq`. | TC-010-06 |
| FEAT-010-AC-07 | `ingest_rejections` with `errors = '[]'` → 23514; `csv_upload` batch with NULL `filename` → 23514. | TC-010-07 |
| FEAT-010-AC-08 | `upgrade head`, `downgrade base`, `upgrade head` succeed with the three tables present. | TC-010-08 |

## Test Data Requirements

- `test_v0_1` seed (DS-01 / SRC-05: 283 arrivals, 281 unique `session_id`s, 2 duplicates; residents R01–R10).
- Template row `R01-20261001-01` for the clone recipe; synthetic code `R11-20261001-01` only inside rejected payloads.
- No audio, no real recording; `audio_quality_flag` is the only audio-related field.
- All mutations inside `BEGIN … ROLLBACK`.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-010-FR-01 (PGS-009, ING-029, DME-015) | FEAT-010 | TC-010-05, TC-010-09 |
| FEAT-010-FR-02 (PGS-011) | FEAT-010 | TC-010-04 |
| FEAT-010-FR-03 (PGS-018, PGS-019, DB-008, ING-030) | FEAT-010 | TC-010-01, TC-010-02 |
| FEAT-010-FR-04 (DB-004, DB-009, ARC-030, ING-030) | FEAT-010 | TC-010-01, TC-010-02, TC-010-03 |
| FEAT-010-FR-05 (DB-001, FR-005, D-09) | FEAT-010 | TC-010-06 |
| FEAT-010-FR-06 (DB-002, DB-003, ARC-031) | FEAT-010 | TC-010-09 |
| FEAT-010-FR-07 (DME-015) | FEAT-010 | TC-010-09, TC-010-04 |
| FEAT-010-FR-08 (DME-019, PGS-008) | FEAT-010 | TC-010-09, TC-010-11 |
| FEAT-010-FR-09 (DB-005, FR-028, D-08) | FEAT-010 | TC-010-07, TC-010-10 |
| FEAT-010-FR-10 (FR-010) | FEAT-010 | TC-010-07, TC-010-10 |
| FEAT-010-FR-11 (FR-006, PGS-028) | FEAT-010 | TC-010-06, TC-010-11 |
| FEAT-010-FR-12 (ARC-003, AC-ARC-08) | FEAT-010 | TC-010-11 |
| FEAT-010-FR-13 (ARC-033) | FEAT-010 | TC-010-11 |
| AC-PGS-01, AC-PGS-02 | FEAT-010 | TC-010-01, TC-010-02 |
| TST-040 | FEAT-010 | TC-010-08 |
| TST-041 (raw_sessions grants) | FEAT-010 | TC-010-03 |
| TST-042 (`arrival_seq` uniqueness) | FEAT-010 | TC-010-06 |
