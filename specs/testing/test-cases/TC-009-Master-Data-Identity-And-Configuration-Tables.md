# FEAT-009 Master data, identity and configuration tables

## Feature Description

FEAT-009 creates the reference tables every other table points to: `facilities`, `users`, `residents`, `devices`, `device_assignments`, `api_keys` and `config_parameters` (TRD 20 §4.6.1–§4.6.6, §4.6.22), with their named constraints, `<table>_set_updated_at` triggers, grants, SQLAlchemy models and repositories, and seeds the 46 pipeline parameter rows (23 keys × profiles `production` and `test_v0_1`) through migration `0002_seed_config_parameters`. The tables hold study IDs only (R01–R10, D01–D10, D07B), never personal data, and no HTTP endpoint writes facilities, residents, devices, assignments or configuration.

## Preconditions

- Local Docker Compose stack running and seeded: `cp .env.development.example .env && docker compose up --build -d`, then `docker compose exec backend python -m backend.cli seed test_v0_1`.
- Connection shorthands (inside the `db` container, which holds the `ECHOWELL_*_DB_PASSWORD` variables; no password is typed):
  - `SU` = `docker compose exec db psql -U echowell -d echowell -v VERBOSITY=verbose -v ON_ERROR_ROLLBACK=on`
  - `APP` = `docker compose exec db sh -c 'PGPASSWORD=$ECHOWELL_APP_DB_PASSWORD psql -h 127.0.0.1 -U echowell_app_login -d echowell -v VERBOSITY=verbose -v ON_ERROR_ROLLBACK=on'`
  - `RO` = the same with `ECHOWELL_READONLY_DB_PASSWORD` and `echowell_readonly_login`.
- Every case that inserts, updates or deletes starts with `BEGIN;` and ends with `ROLLBACK;` so the seed is left unchanged. `ON_ERROR_ROLLBACK=on` keeps the transaction usable after an expected error. With `VERBOSITY=verbose` psql prints the SQLSTATE after `ERROR:`.
- Seeded master data (TRD 20 §4.12, TRD 14 DS-04): facility `Edgewood` (`America/Chicago`); residents R01–R10; devices D01, D02, D04–D10 and D07B (D07 inactive); assignments R02 and R03 both on D02 from 2026-10-01 (open), R07 on D07 2026-10-01..2026-10-12 and on D07B from 2026-10-13 (open); users `admin@example.com`, `clinician@example.com`, `researcher@example.com`; API key `test-ingest`.
- For TC-009-14 a Bearer token from `POST /api/v1/auth/login` as `admin@example.com` (password `SEED_ADMIN_PASSWORD` from `.env`).

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-009-01 | `config_parameters` holds 23 rows per profile with the DB-055 values | High | Database |
| TC-009-02 | R02 and R03 share D02; an overlapping R07 assignment fails with 23P01 | High | Database |
| TC-009-03 | Upper-case email and non-argon2id hash fail 23514; duplicate email fails 23505 | High | Negative |
| TC-009-04 | API key with bad hash length/case, empty scopes or scope `admin` fails 23514 | High | Negative |
| TC-009-05 | `status = 'withdrawn'` without `withdrawn_on` fails 23514; other resident CHECKs | High | Negative |
| TC-009-06 | Read-only role cannot read credential columns; app role cannot DELETE | High | Security |
| TC-009-07 | `alembic check` exits 0 and Python enum labels equal `pg_enum` labels | High | Positive |
| TC-009-08 | No identifying column in the seven tables (column whitelist) | High | Security |
| TC-009-09 | The seven tables carry the named constraints of TRD 20 | Medium | Database |
| TC-009-10 | `updated_at` triggers set the time on update | Medium | Database |
| TC-009-11 | Device code, room label and assignment range CHECKs; duplicates fail 23505 | Medium | Negative |
| TC-009-12 | Exactly one facility; every resident and device references it | Medium | Database |
| TC-009-13 | Grant matrix of the seven tables matches TRD 20 §4.8 | Medium | Security |
| TC-009-14 | No endpoint writes master data or configuration; APIs never expose `residents.id`/`devices.id` | Medium | API |

### TC-009-01 `config_parameters` holds 23 rows per profile with the DB-055 values

| Step | Action | Expected Result |
|---|---|---|
| 1 | `APP`: `SELECT profile, count(*) FROM config_parameters GROUP BY profile ORDER BY profile;` | 2 rows: `production` 23, `test_v0_1` 23. |
| 2 | `APP`: `SELECT profile, value FROM config_parameters WHERE key = 'baseline_n' ORDER BY profile;` | `production` `30`; `test_v0_1` `16`. |
| 3 | `APP`: `SELECT profile, (SELECT count(*) FROM jsonb_object_keys(value)) AS n, value->'loudness_dbfs' AS loud FROM config_parameters WHERE key = 'morning_offsets' ORDER BY profile;` | Both profiles: `n` = 19, `loud` = `-1.5`. |
| 4 | `APP`: `SELECT key, value FROM config_parameters WHERE profile = 'test_v0_1' AND key IN ('facility_tz','noise_limit_dbfs','min_speech_s','screen_min_n','screen_f0_z','screen_other_z','screen_other_count','mad_scale','pause_floor','composite_floor','cusum_k','cusum_h','morning_cutoff_hour','shared_device_min_residents') ORDER BY key;` | `composite_floor` 0.1, `cusum_h` 5.0, `cusum_k` 0.5, `facility_tz` "America/Chicago", `mad_scale` 1.4826, `min_speech_s` 1.0, `morning_cutoff_hour` 12, `noise_limit_dbfs` -40.0, `pause_floor` 0.5, `screen_f0_z` 4.0, `screen_min_n` 5, `screen_other_count` 2, `screen_other_z` 3.0, `shared_device_min_residents` 2. |
| 5 | `APP`: `SELECT key, value FROM config_parameters WHERE profile = 'production' AND key IN ('data_alert_baseline_stalled_enabled','data_alert_set_aside_fraction','data_alert_device_silent_days','alert_snooze_hours','supported_schema_versions') ORDER BY key;` | `alert_snooze_hours` 24, `data_alert_baseline_stalled_enabled` true, `data_alert_device_silent_days` 2, `data_alert_set_aside_fraction` 0.20, `supported_schema_versions` ["0.1"]. |
| 6 | `APP`: `SELECT jsonb_array_length(value) FROM config_parameters WHERE key = 'review_explanations' AND profile = 'test_v0_1';` and `SELECT (SELECT count(*) FROM jsonb_object_keys(value)) FROM config_parameters WHERE key = 'feature_name_map' AND profile = 'test_v0_1';` | `5` explanation codes; `30` mapped names (11 record fields + 19 features). |
| 7 | Run `pytest -q tests/integration/db/test_config_seed.py`. | All tests pass. |

### TC-009-02 R02 and R03 share D02; an overlapping R07 assignment fails with 23P01

| Step | Action | Expected Result |
|---|---|---|
| 1 | `APP`: `SELECT r.resident_code, d.device_code, a.valid_from, a.valid_to FROM device_assignments a JOIN residents r ON r.id=a.resident_id JOIN devices d ON d.id=a.device_id WHERE r.resident_code IN ('R02','R03','R07') ORDER BY 1,3;` | R02 D02 2026-10-01 NULL; R03 D02 2026-10-01 NULL; R07 D07 2026-10-01 2026-10-12; R07 D07B 2026-10-13 NULL (two residents hold overlapping open assignments to the same device). |
| 2 | `APP`: `BEGIN; INSERT INTO device_assignments (resident_id, device_id, valid_from) SELECT r.id, d.id, DATE '2026-10-20' FROM residents r, devices d WHERE r.resident_code='R07' AND d.device_code='D01';` | `ERROR:  23P01: conflicting key value violates exclusion constraint "device_assignments_no_overlap_ex"`. |
| 3 | In the same transaction insert R07 → D01 with `valid_from` 2026-10-12 and `valid_to` 2026-10-12. | `23P01` (inclusive bounds: 2026-10-12 overlaps the D07 range ending 2026-10-12). |
| 4 | In the same transaction insert R07 → D01 with `valid_from` 2026-09-01 and `valid_to` 2026-09-30. | `INSERT 0 1` (no overlap). |
| 5 | `ROLLBACK;` | Seed unchanged. |

### TC-009-03 Upper-case email and non-argon2id hash fail 23514; duplicate email fails 23505

| Step | Action | Expected Result |
|---|---|---|
| 1 | `APP`: `BEGIN; INSERT INTO users (email, display_name, password_hash, role) VALUES ('Admin@Example.com', 'QA user', '$argon2id$v=19$m=65536,t=3,p=4$synthetic$synthetic', 'admin');` | `ERROR:  23514: … violates check constraint "users_email_lower_ck"`. |
| 2 | Insert `('qa1@example.com', 'QA user', 'bcrypt$synthetic', 'clinician')`. | `23514` on `users_password_hash_ck`. |
| 3 | Insert `('admin@example.com', 'QA user', '$argon2id$v=19$m=65536,t=3,p=4$synthetic$synthetic', 'admin')`. | `ERROR:  23505: duplicate key value violates unique constraint "users_email_uq"`. |
| 4 | Insert `('not-an-email', 'QA user', '$argon2id$v=19$synthetic', 'researcher')`. | `23514` on `users_email_format_ck`. |
| 5 | Insert `('qa2@example.com', 'QA user', '$argon2id$v=19$synthetic', 'researcher')`. | `INSERT 0 1`; `active` defaults to `true`, `last_login_at` NULL. |
| 6 | `ROLLBACK;` | No user added. |

### TC-009-04 API key with bad hash length/case, empty scopes or scope `admin` fails 23514

| Step | Action | Expected Result |
|---|---|---|
| 1 | `APP`: `BEGIN; INSERT INTO api_keys (name, key_hash, scopes) VALUES ('qa', repeat('a', 63), ARRAY['ingest:write']);` | `23514` on `api_keys_key_hash_ck`. |
| 2 | Insert `('qa', repeat('A', 64), ARRAY['ingest:write'])`. | `23514` on `api_keys_key_hash_ck`. |
| 3 | Insert `('qa', repeat('b', 64), ARRAY[]::text[])`. | `23514` on `api_keys_scopes_ck`. |
| 4 | Insert `('qa', repeat('c', 64), ARRAY['admin'])`. | `23514` on `api_keys_scopes_ck`. |
| 5 | Insert `('qa', repeat('d', 64), ARRAY['ingest:write','pipeline:run'])`, then the same `key_hash` again. | First `INSERT 0 1`; second `23505` on `api_keys_key_hash_uq`. |
| 6 | `ROLLBACK;` | No key added. |

The hash values are synthetic patterns, not hashes of any key.

### TC-009-05 `status = 'withdrawn'` without `withdrawn_on` fails 23514; other resident CHECKs

| Step | Action | Expected Result |
|---|---|---|
| 1 | `APP`: `BEGIN; UPDATE residents SET status = 'withdrawn' WHERE resident_code = 'R10';` | `23514` on `residents_withdrawn_ck`. |
| 2 | `UPDATE residents SET withdrawn_on = DATE '2026-10-20' WHERE resident_code = 'R10';` (status stays `active`). | `23514` on `residents_withdrawn_ck`. |
| 3 | `UPDATE residents SET status = 'withdrawn', withdrawn_on = DATE '2026-09-30' WHERE resident_code = 'R10';` (before `enrolled_on` 2026-10-01). | `23514` on `residents_withdrawn_after_enrol_ck`. |
| 4 | `UPDATE residents SET admitted_on = DATE '2026-10-05' WHERE resident_code = 'R10';` | `23514` on `residents_admitted_ck`. |
| 5 | `UPDATE residents SET status = 'withdrawn', withdrawn_on = DATE '2026-10-20' WHERE resident_code = 'R10';` | `UPDATE 1`. |
| 6 | `INSERT INTO residents (facility_id, resident_code, enrolled_on) SELECT id, 'r11x', DATE '2026-10-01' FROM facilities;` | `23514` on `residents_resident_code_ck` (pattern `^[A-Z0-9]{1,16}$`). |
| 7 | Same with code `'R01'`. | `23505` on `residents_resident_code_uq`. |
| 8 | Same with code `'R11'` and `sex = 'X'`. | `23514` on `residents_sex_ck`. |
| 9 | `ROLLBACK;` | Seed unchanged. |

### TC-009-06 Read-only role cannot read credential columns; app role cannot DELETE

| Step | Action | Expected Result |
|---|---|---|
| 1 | `RO`: `SELECT password_hash FROM users;` | `ERROR:  42501: permission denied for table users`. |
| 2 | `RO`: `SELECT email FROM users ORDER BY email;` | 3 rows: `admin@example.com`, `clinician@example.com`, `researcher@example.com`. |
| 3 | `RO`: `SELECT key_hash FROM api_keys;` | `42501`. |
| 4 | `RO`: `SELECT name, scopes FROM api_keys;` | Row `test-ingest`, `{ingest:write,pipeline:run}`. |
| 5 | `APP`: `BEGIN; DELETE FROM residents WHERE resident_code = 'R10';` | `ERROR:  42501: permission denied for table residents`. |
| 6 | `APP`: `DELETE FROM device_assignments;` then `ROLLBACK;` | `42501`; nothing deleted. |
| 7 | Run `pytest -q tests/integration/db/test_grants.py`. | All tests pass. |

### TC-009-07 `alembic check` exits 0 and Python enum labels equal `pg_enum` labels

| Step | Action | Expected Result |
|---|---|---|
| 1 | `docker compose exec backend alembic check; echo "exit=$?"`. | `No new upgrade operations detected.`; `exit=0`. |
| 2 | `docker compose exec backend python -c "from backend.models import UserRole, ResidentCohort, ResidentStatus; print([e.value for e in UserRole], [e.value for e in ResidentCohort], [e.value for e in ResidentStatus])"`. | `['admin', 'clinician', 'researcher'] ['longitudinal', 'new_admission'] ['active', 'withdrawn']`, equal to the `pg_enum` labels of TC-008-05. |
| 3 | Run `pytest -q tests/integration/db/test_enums.py`. | All tests pass (every Python enum equals its `pg_enum` labels, DME-003). |

### TC-009-08 No identifying column in the seven tables (column whitelist)

| Step | Action | Expected Result |
|---|---|---|
| 1 | `APP`: `SELECT table_name, column_name FROM information_schema.columns WHERE table_schema='public' AND table_name IN ('facilities','users','residents','devices','device_assignments','api_keys','config_parameters') AND column_name ~ '(name\|birth\|phone\|address\|email\|audio)' ORDER BY 1,2;` | Only `api_keys.name` (key label), `facilities.name` (facility), `users.display_name` and `users.email` (staff login, PGS-034). No resident name, birth date, phone, address or audio column. |
| 2 | `APP`: `SELECT column_name FROM information_schema.columns WHERE table_name='residents' ORDER BY ordinal_position;` | `id, facility_id, resident_code, sex, cohort, enrolled_on, admitted_on, withdrawn_on, status, created_at, updated_at`. |
| 3 | Run `pytest -q tests/integration/db/test_master_tables.py -k identifying`. | `test_no_identifying_columns` passes. |

### TC-009-09 The seven tables carry the named constraints of TRD 20

| Step | Action | Expected Result |
|---|---|---|
| 1 | `APP`: `SELECT conname FROM pg_constraint WHERE conrelid IN ('facilities'::regclass,'users'::regclass,'residents'::regclass,'devices'::regclass,'device_assignments'::regclass,'api_keys'::regclass,'config_parameters'::regclass) AND contype IN ('u','c','x','p') ORDER BY 1;` | Contains all 26 names: `api_keys_key_hash_ck`, `api_keys_key_hash_uq`, `api_keys_name_ck`, `api_keys_scopes_ck`, `config_parameters_key_ck`, `config_parameters_pk`, `config_parameters_profile_ck`, `device_assignments_no_overlap_ex`, `device_assignments_range_ck`, `devices_device_code_ck`, `devices_device_code_uq`, `devices_room_label_ck`, `facilities_name_ck`, `facilities_name_uq`, `facilities_timezone_ck`, `residents_admitted_ck`, `residents_resident_code_ck`, `residents_resident_code_uq`, `residents_sex_ck`, `residents_withdrawn_after_enrol_ck`, `residents_withdrawn_ck`, `users_display_name_ck`, `users_email_format_ck`, `users_email_lower_ck`, `users_email_uq`, `users_password_hash_ck` (plus the `_pkey` primary keys). |
| 2 | `APP`: `INSERT INTO config_parameters (profile, key, value) VALUES ('staging', 'qa_key', '1');` inside `BEGIN … ROLLBACK`. | `23514` on `config_parameters_profile_ck`. |
| 3 | Same with `('test_v0_1', 'QA-Key', '1')`. | `23514` on `config_parameters_key_ck`. |
| 4 | Same with `('test_v0_1', 'cusum_k', '0.7')`. | `23505` on `config_parameters_pk`. |

### TC-009-10 `updated_at` triggers set the time on update

| Step | Action | Expected Result |
|---|---|---|
| 1 | `APP`: `SELECT tgname FROM pg_trigger WHERE tgname LIKE '%\_set\_updated\_at' AND tgrelid IN ('facilities'::regclass,'users'::regclass,'residents'::regclass,'devices'::regclass,'device_assignments'::regclass,'api_keys'::regclass,'config_parameters'::regclass) ORDER BY 1;` | 7 rows: `api_keys_set_updated_at`, `config_parameters_set_updated_at`, `device_assignments_set_updated_at`, `devices_set_updated_at`, `facilities_set_updated_at`, `residents_set_updated_at`, `users_set_updated_at`. |
| 2 | `APP`: `BEGIN; SELECT updated_at FROM devices WHERE device_code='D01';` | Value T0 noted. |
| 3 | `UPDATE devices SET room_label = 'QA-1' WHERE device_code='D01' RETURNING updated_at, updated_at = now() AS is_now;` | `updated_at` later than T0; `is_now` = `t`. `ROLLBACK;` |

### TC-009-11 Device code, room label and assignment range CHECKs; duplicates fail 23505

| Step | Action | Expected Result |
|---|---|---|
| 1 | `APP`: `BEGIN; INSERT INTO devices (facility_id, device_code) SELECT id, 'D01' FROM facilities;` | `23505` on `devices_device_code_uq`. |
| 2 | Same with `device_code` `'d-11'`. | `23514` on `devices_device_code_ck`. |
| 3 | `UPDATE devices SET room_label = '' WHERE device_code='D01';` | `23514` on `devices_room_label_ck`. |
| 4 | `UPDATE devices SET room_label = repeat('x', 61) WHERE device_code='D01';` | `23514` on `devices_room_label_ck`. |
| 5 | `UPDATE devices SET room_label = repeat('x', 60) WHERE device_code='D01';` | `UPDATE 1`. |
| 6 | Insert an assignment R01 → D01 with `valid_from` 2026-09-10 and `valid_to` 2026-09-01. | `23514` on `device_assignments_range_ck`. |
| 7 | `ROLLBACK;` | Seed unchanged. |

### TC-009-12 Exactly one facility; every resident and device references it

| Step | Action | Expected Result |
|---|---|---|
| 1 | `APP`: `SELECT name, timezone FROM facilities;` | One row: `Edgewood`, `America/Chicago`. |
| 2 | `APP`: `SELECT count(*) FROM residents r JOIN facilities f ON f.id = r.facility_id;` and the same for `devices`. | `10` residents, `10` devices, all joined to the one facility. |
| 3 | `APP`: `SELECT count(*) FROM residents WHERE facility_id NOT IN (SELECT id FROM facilities);` | `0`. |

### TC-009-13 Grant matrix of the seven tables matches TRD 20 §4.8

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SU`: `SELECT t, p, has_table_privilege('echowell_app', t, p) FROM unnest(ARRAY['facilities','users','residents','devices','device_assignments','api_keys','config_parameters']) t, unnest(ARRAY['SELECT','INSERT','UPDATE','DELETE']) p ORDER BY 1,2;` | `t` for SELECT, INSERT, UPDATE on all seven tables; `f` for DELETE on all seven. |
| 2 | `SU`: `SELECT t, has_table_privilege('echowell_readonly', t, 'SELECT'), has_table_privilege('echowell_readonly', t, 'INSERT') FROM unnest(ARRAY['facilities','residents','devices','device_assignments','config_parameters']) t;` | SELECT `t`, INSERT `f` for all five. |
| 3 | `SU`: `SELECT has_column_privilege('echowell_readonly','users','password_hash','SELECT'), has_column_privilege('echowell_readonly','users','email','SELECT'), has_column_privilege('echowell_readonly','api_keys','key_hash','SELECT'), has_column_privilege('echowell_readonly','api_keys','scopes','SELECT');` | `f`, `t`, `f`, `t`. |

### TC-009-14 No endpoint writes master data or configuration; APIs never expose `residents.id`/`devices.id`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `curl -s http://localhost:8000/api/v1/openapi.json \| python -c "import json,sys; d=json.load(sys.stdin); print([(p,m) for p,v in d['paths'].items() for m in v if m in ('post','put','patch','delete') and (p.startswith('/residents') or p.startswith('/devices') or p.startswith('/facility') or p.startswith('/config'))])"`. | `[('/residents/{resident_code}/notes', 'post')]` only (staff notes, not a master-data write); no write method on `/residents`, `/residents/{resident_code}`, `/devices`, `/facility/…` or `/config/ui`. |
| 2 | `curl -s -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"resident_code":"R11"}' http://localhost:8000/api/v1/residents -o /dev/null -w "%{http_code}\n"`. | `405` (method not allowed). |
| 3 | `curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/residents/R01 \| python -c "import json,sys; d=json.load(sys.stdin); print('id' in d, d.get('resident_code'))"`. | `False R01` (addressed by `resident_code`; no UUID `id`). |
| 4 | `curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/devices \| python -c "import json,sys; d=json.load(sys.stdin); print(any('id' in x for x in d['items']))"`. | `False`. |
| 5 | Run `pytest -q tests/unit/backend/repositories tests/integration/db/test_repositories.py`. | All pass (lookups by `resident_code`/`device_code`; only the transitions `active → withdrawn` and `new_admission → longitudinal` are exposed). |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | List write methods in `GET /api/v1/openapi.json` for residents, devices, facility, config | Only `POST /residents/{resident_code}/notes` (staff notes) |
| 2 | `POST /api/v1/residents` with admin token | 405 |
| 3 | `GET /api/v1/residents/R01` | 200; body has `resident_code` `R01`, no `id` |
| 4 | `GET /api/v1/devices` | 200; items carry `device_code`, no `id` |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT profile, count(*) FROM config_parameters GROUP BY 1;` | 23 / 23 |
| 2 | `SELECT count(*) FROM facilities;` | 1 (`Edgewood`) |
| 3 | `SELECT count(*) FROM residents; SELECT count(*) FROM devices; SELECT count(*) FROM device_assignments;` | 10; 10; 11 |
| 4 | Grant matrix (TC-009-13) | App: SELECT/INSERT/UPDATE, no DELETE; read-only: SELECT without credential columns |
| 5 | Triggers (TC-009-10) | 7 `_set_updated_at` triggers |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Overlapping R07 assignment (TC-009-02) | 23P01 |
| 2 | `Admin@Example.com`, non-argon2id hash (TC-009-03) | 23514 |
| 3 | Duplicate email / resident code / device code / key hash (TC-009-03/04/05/11) | 23505 |
| 4 | Bad key hash, empty or unknown scope (TC-009-04) | 23514 |
| 5 | Withdrawn without date (TC-009-05) | 23514 |
| 6 | DELETE as `echowell_app_login` (TC-009-06) | 42501 |
| 7 | Read `password_hash` / `key_hash` as read-only (TC-009-06) | 42501 |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-009-AC-01 | 23 rows per profile; `baseline_n` 30 / 16; `morning_offsets` 19 keys with `loudness_dbfs = -1.5`. | TC-009-01 |
| FEAT-009-AC-02 | R02 and R03 open assignments to D02 succeed; overlapping second R07 assignment fails 23P01. | TC-009-02 |
| FEAT-009-AC-03 | `Admin@Example.com` or non-`$argon2id$` hash → 23514; duplicate email → 23505. | TC-009-03 |
| FEAT-009-AC-04 | 63-char hash, upper-case hash, empty scopes or scope `admin` → 23514. | TC-009-04 |
| FEAT-009-AC-05 | `status = 'withdrawn'` without `withdrawn_on` → 23514. | TC-009-05 |
| FEAT-009-AC-06 | Read-only `SELECT password_hash` → 42501, `SELECT email` succeeds; app `DELETE FROM residents` → 42501. | TC-009-06 |
| FEAT-009-AC-07 | `alembic check` exits 0; Python enum labels equal `pg_enum` labels. | TC-009-07 |
| FEAT-009-AC-08 | No column named like name, birth, phone, address, email (outside `users.email`) or audio, apart from the whitelisted staff/facility/key labels. | TC-009-08 |

## Test Data Requirements

- `test_v0_1` seed: facility Edgewood; residents R01–R10; devices D01, D02, D04–D10, D07B; 11 assignments; seeded users and API key `test-ingest` (secrets from the `SEED_*` variables, stored only as argon2id / SHA-256 hashes).
- Synthetic test values only: emails under `example.com`, the code `R11` for rejected inserts, pattern hashes such as `repeat('d', 64)`.
- All mutations inside `BEGIN … ROLLBACK`.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-009-FR-01 (PGS-006, DME-001) | FEAT-009 | TC-009-09 |
| FEAT-009-FR-02 (PGS-015) | FEAT-009 | TC-009-02 |
| FEAT-009-FR-03 (PGS-034) | FEAT-009 | TC-009-03 |
| FEAT-009-FR-04 (PGS-035) | FEAT-009 | TC-009-04 |
| FEAT-009-FR-05 (PGS-037) | FEAT-009 | TC-009-05 |
| FEAT-009-FR-06 (PGS-020) | FEAT-009 | TC-009-10 |
| FEAT-009-FR-07 (PGS-021, PGS-022) | FEAT-009 | TC-009-06, TC-009-13 |
| FEAT-009-FR-08 (PGS-024, PGS-025, DB-055) | FEAT-009 | TC-009-01 |
| FEAT-009-FR-09 (DME-001, DME-003) | FEAT-009 | TC-009-07 |
| FEAT-009-FR-10 (SEC-120, SEC-122, SEC-123, DME-020) | FEAT-009 | TC-009-08, TC-009-11 |
| FEAT-009-FR-11 (SEC-125) | FEAT-009 | TC-009-08 |
| FEAT-009-FR-12 (DME-004) | FEAT-009 | TC-009-14 |
| FEAT-009-FR-13 (FR-227) | FEAT-009 | TC-009-14 |
| FEAT-009-FR-14 (DME-008, DME-009) | FEAT-009 | TC-009-14 |
| FEAT-009-FR-15 (FR-229) | FEAT-009 | TC-009-14 |
| FEAT-009-FR-16 (ARC-105) | FEAT-009 | TC-009-12 |
| AC-PGS-08 | FEAT-009 | TC-009-02 |
| AC-PGS-10 | FEAT-009 | TC-009-01 |
| AC-PGS-12 | FEAT-009 | TC-009-06 |
| TST-041 (grants, part) | FEAT-009 | TC-009-06, TC-009-13 |
| TST-042 (uniqueness of `resident_code`) | FEAT-009 | TC-009-05 |
