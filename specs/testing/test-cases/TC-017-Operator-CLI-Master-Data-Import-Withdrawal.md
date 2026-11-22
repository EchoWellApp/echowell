# Operator CLI: master data import, withdrawal, purge, seed (--master-only) and test-database reset

## Feature Description

FEAT-017 gives operators the only supported way to manage master data and test databases through `python -m backend.cli`: `bootstrap` (idempotent facility row from `FACILITY_NAME`/`FACILITY_TZ`, verification of the 46 `config_parameters` rows of migration 0002), `import-master-data --dir D` (idempotent upsert of `facilities.csv`, `residents.csv`, `devices.csv`, `device_assignments.csv` in one transaction with one `roster.loaded` audit row), `withdraw-resident <code> --on <date>`, `purge-resident <code> --confirm <code>` (IRB-directed deletion in the DB-064 order as `echowell_migrator`), `seed test_v0_1 [--master-only] [--reset]` (roster, the three `@example.com` users and the API key `test-ingest` from the `SEED_*` variables, hashes only) and `reset-test-db` (Alembic downgrade base / upgrade head, one `seed.reset` row). Command refusals exit with code 2 and write nothing; invalid settings exit with code 1; `seed` and `reset-test-db` refuse to run in production. There is no HTTP endpoint for master data.

## Preconditions

- Local development stack running; `.env` from `.env.development.example` (`APP_ENV=local`, `PIPELINE_PROFILE=test_v0_1`, `FACILITY_NAME=Demo Facility`, `FACILITY_TZ=America/Chicago`, all four `SEED_*` variables set; values never written down).
- `DATABASE_URL` (app role) and `DATABASE_MIGRATION_URL` (migrator) set in the environment file.
- CLI run from the repository root (or `docker compose exec backend python -m backend.cli …`); exit code read with `echo $?`; stdout and stderr captured to files for the secret checks.
- `psql` access to the local database (read-only `SELECT`).
- Start state for most cases: `python -m backend.cli seed test_v0_1 --reset --master-only` (exit code 0).

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-017-01 | `seed test_v0_1 --master-only` loads 1/10/10/11/3/1 rows and D07 is inactive | High | Database |
| TC-017-02 | Roster CSV files contain exactly the TRD 20 §4.12 content | High | Documentation |
| TC-017-03 | Seeding twice keeps the counts and never prints a `SEED_*` value | High | Security |
| TC-017-04 | Seed users and `test-ingest` key are stored as hashes and work for login and ingest | High | API |
| TC-017-05 | `seed` and `reset-test-db` refuse with `APP_ENV=production` | High | Negative |
| TC-017-06 | `reset-test-db` refuses with `PIPELINE_PROFILE=production` | High | Negative |
| TC-017-07 | Missing `SEED_*` variable makes `seed` exit 2 and write nothing | High | Negative |
| TC-017-08 | `reset-test-db` leaves 46 config rows and one `seed.reset` row; `seed --reset` succeeds twice | High | Database |
| TC-017-09 | `withdraw-resident R08 --on 2026-10-20` | High | Database |
| TC-017-10 | `withdraw-resident` refusals (already withdrawn, unknown code, date before enrolment, bad date) | Medium | Negative |
| TC-017-11 | `purge-resident` refusals (mismatched confirm, not withdrawn) | High | Negative |
| TC-017-12 | `purge-resident R08 --confirm R08` removes every R08 row from the 13 tables and keeps audit rows | High | Database |
| TC-017-13 | `bootstrap` twice equals once | High | Database |
| TC-017-14 | `import-master-data` adds R11/D11 idempotently with one `roster.loaded` row each run | Medium | Positive |
| TC-017-15 | `import-master-data` with a bad row rolls back and names the file and row | Medium | Negative |
| TC-017-16 | Inspection: CLI never references `evaluation_ground_truth`; no router writes master data | High | Security |
| TC-017-17 | No HTTP endpoint creates or changes residents, devices or assignments | Medium | API |

### TC-017-01 `seed test_v0_1 --master-only` loads 1/10/10/11/3/1 rows and D07 is inactive

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `python -m backend.cli seed test_v0_1 --reset --master-only` | Exit code 0; stderr ends with `Seed test_v0_1 complete.` |
| 2 | `SELECT (SELECT count(*) FROM facilities), (SELECT count(*) FROM residents), (SELECT count(*) FROM devices), (SELECT count(*) FROM device_assignments), (SELECT count(*) FROM users), (SELECT count(*) FROM api_keys);` | `1, 10, 10, 11, 3, 1` |
| 3 | `SELECT device_code, active FROM devices WHERE device_code IN ('D07','D07B');` | `D07` `false`; `D07B` `true` |
| 4 | `SELECT count(*) FROM evaluation_ground_truth;` (as `echowell_readonly`) | 0 |
| 5 | `SELECT count(*) FROM raw_sessions;` and `SELECT count(*) FROM pipeline_runs;` | Both 0 (`--master-only` loads no records and starts no run) |

### TC-017-02 Roster CSV files contain exactly the TRD 20 §4.12 content

| Step | Action | Expected Result |
|---|---|---|
| 1 | `ls database/seeds/test_v0_1/` | Contains `facilities.csv`, `residents.csv`, `devices.csv`, `device_assignments.csv` (plus the SRC-05 input CSV and `README.md`) |
| 2 | `cat database/seeds/test_v0_1/facilities.csv` | Header `name,timezone`; one row `Demo Facility,America/Chicago` |
| 3 | Inspect `residents.csv` | Header `resident_code,sex,cohort,enrolled_on,admitted_on`; 10 rows R01–R10; every `enrolled_on` `2026-10-01`; study IDs only, no names or rooms |
| 4 | Inspect `devices.csv` | Header `device_code,room_label,active,firmware_version_last`; 10 rows (D01–D06, D07, D07B, D08–D10); D07 `active` `false`; `room_label` empty; firmware `fw-1.0.0` |
| 5 | Inspect `device_assignments.csv` | Header `resident_code,device_code,valid_from,valid_to`; 11 rows; R02 and R03 both on D02; R07 on D07 until `2026-10-12` and on D07B from `2026-10-13` |

### TC-017-03 Seeding twice keeps the counts and never prints a `SEED_*` value

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `python -m backend.cli seed test_v0_1 --master-only > out1.txt 2> err1.txt` | Exit code 0 |
| 2 | Repeat into `out2.txt`/`err2.txt` | Exit code 0 |
| 3 | Re-run the count query of TC-017-01 step 2 | `1, 10, 10, 11, 3, 1` |
| 4 | For each of the four `SEED_*` variables run `grep -cF "$SEED_ADMIN_PASSWORD" out*.txt err*.txt` (and likewise for the other three) and search `docker compose logs backend` | Count 0 in every file and in the logs |
| 5 | `SELECT action, count(*) FROM audit_logs WHERE action IN ('user.created','user.updated','api_key.created','roster.loaded') GROUP BY 1;` | Second run added `user.updated` rows (one per user) instead of new users; one `roster.loaded` row per run |
| 6 | Delete the captured files | Removed |

### TC-017-04 Seed users and `test-ingest` key are stored as hashes and work for login and ingest

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT email, role, left(password_hash, 10) FROM users ORDER BY email;` | `admin@example.com` `admin`, `clinician@example.com` `clinician`, `researcher@example.com` `researcher`; each hash starts `$argon2id$` |
| 2 | `SELECT name, scopes, device_id, key_hash ~ '^[0-9a-f]{64}$' FROM api_keys;` | One row `test-ingest`; scopes contain `ingest:write` and `pipeline:run`; `device_id` NULL; `true` |
| 3 | `POST /api/v1/auth/login` as `clinician@example.com` with `SEED_CLINICIAN_PASSWORD` | 200; `user.role` `clinician` |
| 4 | `POST /api/v1/pipeline/run` with header `X-API-Key: $SEED_INGEST_API_KEY` and body `{"scope": "all"}` | 202 with a `pipeline_run_id` (key accepted with scope `pipeline:run`) |

### TC-017-05 `seed` and `reset-test-db` refuse with `APP_ENV=production`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Record all row counts (TC-017-01 step 2 plus `audit_logs`) | Baseline |
| 2 | Run `APP_ENV=production python -m backend.cli seed test_v0_1` | Exit code 2; stderr `Refused: seeding is not allowed in production` |
| 3 | Run `APP_ENV=production python -m backend.cli reset-test-db` | Exit code 2; stderr `Refused: reset-test-db is not allowed in production` |
| 4 | Run `APP_ENV=production python -m backend.cli seed test_v0_1 --reset` | Exit code 2; same seeding message |
| 5 | Re-count | All counts unchanged (no audit row either) |

### TC-017-06 `reset-test-db` refuses with `PIPELINE_PROFILE=production`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `APP_ENV=local PIPELINE_PROFILE=production python -m backend.cli reset-test-db` | Exit code 2; stderr `Refused: reset-test-db is allowed only with PIPELINE_PROFILE=test_v0_1`; counts unchanged |
| 2 | Run `APP_ENV=demo PIPELINE_PROFILE=test_v0_1 python -m backend.cli reset-test-db` | Exit code 2; stderr `Refused: reset-test-db is allowed only when APP_ENV is local, test or staging` |

### TC-017-07 Missing `SEED_*` variable makes `seed` exit 2 and write nothing

| Step | Action | Expected Result |
|---|---|---|
| 1 | Record row counts | Baseline |
| 2 | Run `SEED_ADMIN_PASSWORD= python -m backend.cli seed test_v0_1 --master-only` | Exit code 2; stderr `Refused: missing SEED_ADMIN_PASSWORD` |
| 3 | Run with `SEED_INGEST_API_KEY=` instead | Exit code 2; stderr `Refused: missing SEED_INGEST_API_KEY` |
| 4 | Re-count | Unchanged; no `roster.loaded` or `user.*` audit row added |

### TC-017-08 `reset-test-db` leaves 46 config rows and one `seed.reset` row; `seed --reset` succeeds twice

| Step | Action | Expected Result |
|---|---|---|
| 1 | Populate fully: `python -m backend.cli seed test_v0_1` (records and pipeline run) | Exit code 0; `raw_sessions` count > 0 |
| 2 | Run `python -m backend.cli reset-test-db` | Exit code 0; stderr `Test database reset.` |
| 3 | `SELECT count(*) FROM config_parameters;` | 46 |
| 4 | `SELECT action, actor_type, details FROM audit_logs;` | Exactly 1 row: `seed.reset`, `actor_type` `system`, `details` `{"profile": "test_v0_1", "operator": "<whoami>"}` |
| 5 | Count rows in `facilities`, `residents`, `devices`, `device_assignments`, `users`, `api_keys`, `raw_sessions`, `processed_sessions`, `pipeline_runs`, `alerts`, `scores`, `day_ledger` | Every count 0 |
| 6 | Run `python -m backend.cli seed test_v0_1 --reset` twice in a row | Both exit code 0 with `Seed test_v0_1 complete.` |

### TC-017-09 `withdraw-resident R08 --on 2026-10-20`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Start from a full seed (`seed test_v0_1 --reset`); record `SELECT count(*) FROM raw_sessions rs JOIN residents r ON r.id = rs.resident_id WHERE r.resident_code = 'R08';` and the same for `processed_sessions`, `day_ledger`, `scores` | Baseline counts for R08 |
| 2 | Run `python -m backend.cli withdraw-resident R08 --on 2026-10-20` | Exit code 0; stderr `Resident R08 withdrawn on 2026-10-20.` |
| 3 | `SELECT status, withdrawn_on FROM residents WHERE resident_code = 'R08';` | `withdrawn`, `2026-10-20` |
| 4 | `SELECT actor_type, details FROM audit_logs WHERE action = 'resident.withdrawn';` | Exactly 1 row; `system`; `details` `{"resident_code": "R08", "withdrawn_on": "2026-10-20", "operator": "<whoami>"}` |
| 5 | Re-count R08 rows of step 1 | Unchanged |
| 6 | As admin, `GET /api/v1/residents` | R08 not in the default list (FR-228; `total` 9); `GET /api/v1/residents?include_withdrawn=true` lists R08 with `resident_status` `withdrawn` |

### TC-017-10 `withdraw-resident` refusals (already withdrawn, unknown code, date before enrolment, bad date)

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `withdraw-resident R08 --on 2026-10-21` after TC-017-09 | Exit code 2; stderr `Refused: resident R08 is already withdrawn`; `status` stays `withdrawn`, `withdrawn_on` stays `2026-10-20` |
| 2 | Run `withdraw-resident R99 --on 2026-10-20` | Exit code 2; stderr `Refused: unknown resident R99` |
| 3 | Run `withdraw-resident R05 --on 2026-09-30` | Exit code 2; stderr `Refused: the withdrawal date is before the enrolment date` |
| 4 | Run `withdraw-resident R05 --on 20-10-2026` | Exit code 2; stderr `Refused: '20-10-2026' is not a date (YYYY-MM-DD)` |
| 5 | Check R05 | `status` `active`; no new audit row |

### TC-017-11 `purge-resident` refusals (mismatched confirm, not withdrawn)

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `python -m backend.cli purge-resident R08 --confirm R09` | Exit code 2; stderr `Refused: --confirm must repeat the resident code`; no row deleted |
| 2 | Run `python -m backend.cli purge-resident R05 --confirm R05` (R05 active) | Exit code 2; stderr `Refused: resident R05 is not withdrawn`; R05 rows intact |

### TC-017-12 `purge-resident R08 --confirm R08` removes every R08 row from the 13 tables and keeps audit rows

| Step | Action | Expected Result |
|---|---|---|
| 1 | After TC-017-09, record `SELECT count(*) FROM audit_logs;` | Baseline A |
| 2 | Run `python -m backend.cli purge-resident R08 --confirm R08` | Exit code 0; stderr `Purged resident R08: {…}` listing per-table counts |
| 3 | `SELECT count(*) FROM residents WHERE resident_code = 'R08';` | 0 |
| 4 | Using R08's former `id`, count rows in `scores`, `cusum_state`, `data_alerts`, `alerts`, `baselines`, `day_ledger`, `processed_sessions`, `epochs`, `raw_sessions`, `device_assignments`, `staff_notes`; and `alert_reviews` of R08's alerts | All 0 |
| 5 | `SELECT count(*) FROM audit_logs;` and the newest row | A + 1; newest is `resident.purged` with `details.resident_code` `R08`, `details.row_counts` (one key per table) and `details.operator`; no feature value |
| 6 | `SELECT count(*) FROM audit_logs WHERE details->>'resident_code' = 'R08' AND action = 'resident.withdrawn';` | 1 (earlier audit rows not deleted) |
| 7 | Other residents: `SELECT count(*) FROM residents;` | 9 |

### TC-017-13 `bootstrap` twice equals once

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `python -m backend.cli reset-test-db`, then `python -m backend.cli bootstrap` | Exit code 0; stderr `Bootstrap complete.` |
| 2 | Dump: `SELECT * FROM facilities ORDER BY id; SELECT * FROM config_parameters ORDER BY profile, key;` into a file | One facility `Demo Facility` / `America/Chicago`; 46 parameter rows |
| 3 | Run `bootstrap` again and repeat the dump into a second file; `diff` the files | No difference (identical rows, including timestamps) |
| 4 | `SELECT count(*) FROM config_parameters;` | 46 (bootstrap never inserts or overwrites parameter rows) |

### TC-017-14 `import-master-data` adds R11/D11 idempotently with one `roster.loaded` row each run

| Step | Action | Expected Result |
|---|---|---|
| 1 | From the master-only seed, run `python -m backend.cli import-master-data --dir tests/fixtures/seeds/demo_overlay` | Exit code 0; stderr `Loaded 1 residents, 1 devices, 1 assignments.` |
| 2 | Counts of residents / devices / device_assignments | 11 / 11 / 12 |
| 3 | Run the command again | Exit code 0; counts still 11 / 11 / 12 |
| 4 | `SELECT details FROM audit_logs WHERE action = 'roster.loaded' ORDER BY id DESC LIMIT 1;` | `{"residents": 1, "devices": 1, "device_assignments": 1, "operator": "<whoami>"}` |
| 5 | Reset afterwards: `seed test_v0_1 --reset --master-only` | Exit code 0 |

### TC-017-15 `import-master-data` with a bad row rolls back and names the file and row

| Step | Action | Expected Result |
|---|---|---|
| 1 | Copy `tests/fixtures/seeds/demo_overlay` to a scratch folder and change the device code in row 2 of its `device_assignments.csv` to `D99` | Scratch overlay prepared |
| 2 | Run `python -m backend.cli import-master-data --dir <scratch folder>` | Non-zero exit (2); stderr `Refused: device_assignments.csv row 2: unknown resident_code or device_code` |
| 3 | `SELECT count(*) FROM residents WHERE resident_code = 'R11';` | 0 (whole transaction rolled back, including the R11 and D11 rows) |
| 4 | Change the header of the scratch `residents.csv` to `code,sex,cohort,enrolled_on,admitted_on` and rerun | Exit code 2; stderr `Refused: residents.csv: header must be resident_code,sex,cohort,enrolled_on,admitted_on` |
| 5 | Delete the scratch folder | Removed |

### TC-017-16 Inspection: CLI never references `evaluation_ground_truth`; no router writes master data

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `grep -rn "evaluation_ground_truth" backend/cli.py` | No output |
| 2 | Run `grep -rnE "ResidentRepository\(.*\)\.(upsert|insert|set_withdrawn)|DeviceRepository\(.*\)\.(upsert|upsert_assignment)" backend/api` | No output |
| 3 | Run `grep -rnE "^(def|@router\.(post|patch|put|delete))" backend/api/residents.py backend/api/devices.py` | Only `@router.get` routes and the notes `POST` (`/residents/{resident_code}/notes`) exist; no route writes `residents`, `devices` or `device_assignments` |

### TC-017-17 No HTTP endpoint creates or changes residents, devices or assignments

| Step | Action | Expected Result |
|---|---|---|
| 1 | As admin, `POST /api/v1/residents` with `{"resident_code": "R12"}` | 405 `METHOD_NOT_ALLOWED` Problem body; no row added |
| 2 | As admin, `PATCH /api/v1/residents/R01` with `{"status": "withdrawn"}` | 405 `METHOD_NOT_ALLOWED`; R01 stays `active` |
| 3 | As admin, `POST /api/v1/devices` with `{}` | 405 `METHOD_NOT_ALLOWED` |
| 4 | `GET /api/v1/openapi.json`: list methods under `/api/v1/residents` and `/api/v1/devices` | Only `get` |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `POST /api/v1/auth/login` with each seeded user and its `SEED_*` password | 200 for all three (TC-017-04) |
| 2 | `POST /api/v1/pipeline/run` with `X-API-Key: $SEED_INGEST_API_KEY` | 202 (TC-017-04) |
| 3 | `GET /api/v1/residents` after withdrawing R08 | 200; `total` 9; R08 absent (TC-017-09) |
| 4 | `POST`/`PATCH` on `/api/v1/residents`, `POST /api/v1/devices` | 405 `METHOD_NOT_ALLOWED` (TC-017-17) |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | Row counts after `seed test_v0_1 --master-only` | facilities 1, residents 10, devices 10, device_assignments 11, users 3, api_keys 1 |
| 2 | `SELECT count(*) FROM config_parameters;` after reset | 46 |
| 3 | `SELECT count(*) FROM ingest_batches WHERE source = 'seed';` in a production database (Hosted) | 0 (FR-13; read-only check by the team) |
| 4 | `SELECT count(*) FROM audit_logs WHERE action IN ('roster.loaded','resident.withdrawn','resident.purged','seed.reset','user.created','user.updated','api_key.created') AND details->>'operator' IS NULL;` | 0 |
| 5 | `SELECT count(*) FROM users WHERE email NOT LIKE '%@example.com';` after seed | 0 |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | `seed` / `reset-test-db` with `APP_ENV=production` | Exit 2, nothing written (TC-017-05) |
| 2 | `reset-test-db` with `PIPELINE_PROFILE=production` | Exit 2 (TC-017-06) |
| 3 | `seed` with a missing `SEED_*` | Exit 2, nothing written (TC-017-07) |
| 4 | `purge-resident` with mismatching `--confirm` or an active resident | Refused, nothing deleted (TC-017-11) |
| 5 | Bad code or header in a roster CSV | Rolled back; exit 2 naming file and row (TC-017-15) |
| 6 | Run `APP_ENV=staging python -m backend.cli bootstrap` with a `DATABASE_URL` lacking `sslmode` | Exit 1; CRITICAL `startup_config_invalid` (ENV-002) |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-017-AC-01 | Counts 1/10/10/11/3/1 and D07 `active = false` after `seed test_v0_1 --master-only` | TC-017-01 |
| FEAT-017-AC-02 | Second run leaves the same counts; stdout, stderr and logs contain none of the four `SEED_*` values | TC-017-03 |
| FEAT-017-AC-03 | `APP_ENV=production`: `seed test_v0_1` exits 2 with "seeding is not allowed in production"; `reset-test-db` exits 2; no count changes | TC-017-05 |
| FEAT-017-AC-04 | `PIPELINE_PROFILE=production`, `APP_ENV=local`: `reset-test-db` exits 2 | TC-017-06 |
| FEAT-017-AC-05 | After reset: 46 `config_parameters`, exactly one `seed.reset` audit row, every other table empty; `seed test_v0_1 --reset` succeeds twice | TC-017-08 |
| FEAT-017-AC-06 | R08 `withdrawn`, `withdrawn_on` 2026-10-20, one `resident.withdrawn` row, other R08 rows unchanged | TC-017-09 |
| FEAT-017-AC-07 | Purge removes every R08 row from the 13 DB-064 tables, writes one `resident.purged` row, deletes no audit row | TC-017-12 |
| FEAT-017-AC-08 | `bootstrap` twice produces a database identical to once | TC-017-13 |
| FEAT-017-AC-09 | grep for `evaluation_ground_truth` in `backend/cli.py` returns nothing; no router writes master data | TC-017-16, TC-017-17 |

## Test Data Requirements

- Roster `database/seeds/test_v0_1/` (facility Demo Facility, R01–R10, D01–D10 with D07B, 11 assignments) and the SRC-05 input used by the full seed.
- Fixture overlay `tests/fixtures/seeds/demo_overlay` (R11, D11) and a scratch copy with device `D99` for TC-017-15.
- Non-existent codes R99 and D99; synthetic withdrawal date 2026-10-20.
- Environment: `APP_ENV`, `PIPELINE_PROFILE`, `DATABASE_URL`, `DATABASE_MIGRATION_URL`, `FACILITY_NAME`, `FACILITY_TZ`, `SEED_ADMIN_PASSWORD`, `SEED_CLINICIAN_PASSWORD`, `SEED_RESEARCHER_PASSWORD`, `SEED_INGEST_API_KEY` (values never written down).

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-017-FR-01 / FR-227 / ARC-067 / D-34 | FEAT-017 | TC-017-16, TC-017-17 |
| FEAT-017-FR-02 / DB-060 | FEAT-017 | TC-017-14, TC-017-15 |
| FEAT-017-FR-03 / DB-056 / PGS-026 / D-68 | FEAT-017 | TC-017-01, TC-017-02 |
| FEAT-017-FR-04 / DB-056 / DB-057 / D-71 | FEAT-017 | TC-017-03, TC-017-04 |
| FEAT-017-FR-05 / DEP-070 / DB-059 | FEAT-017 | TC-017-05, TC-017-07 |
| FEAT-017-FR-06 / D-68 | FEAT-017 | TC-017-01 |
| FEAT-017-FR-07 / DB-024 / D-71 | FEAT-017 | TC-017-06, TC-017-08 |
| FEAT-017-FR-08 / DEP-071 / AC-DB-08 | FEAT-017 | TC-017-08 |
| FEAT-017-FR-09 / DEP-072 | FEAT-017 | TC-017-13 |
| FEAT-017-FR-10 / DB-062 / DME-009 / FR-228 | FEAT-017 | TC-017-09, TC-017-10 |
| FEAT-017-FR-11 / DB-064 / PGS-019 | FEAT-017 | TC-017-11, TC-017-12 |
| FEAT-017-FR-12 / DB-061 | FEAT-017 | TC-017-16 (no deletion job in `backend/`; only `purge-resident` deletes) |
| FEAT-017-FR-13 / DEP-073 / AGT-014 | FEAT-017 | TC-017-05, Database Validation 3 |
| FEAT-017-FR-14 / ENV-053 / ENV-002 / ENV-041 | FEAT-017 | TC-017-05, TC-017-07, Negative 6 |
| AC-DB-08, AC-DEP-02 (master-data part) | FEAT-017 | TC-017-05, TC-017-06, TC-017-08 |
| AC-DB-10 (withdrawn R08, completed with FEAT-023/FEAT-049) | FEAT-017 | TC-017-09 |
| TST-195 / D-86 | FEAT-017 | TC-017-10, TC-017-11, TC-017-15 |
