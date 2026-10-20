# FEAT-017 Operator CLI: master data import, withdrawal, purge, seed (--master-only) and test-database reset

| Field | Value |
|---|---|
| Epic | Database |
| Build phase | Phase 4 (TRD 25) |
| Priority | P0 |
| Complexity | High |
| MVP status | Required |
| Dependencies | FEAT-016, FEAT-014 |
| Status | Not Started |

## Purpose

Give operators the only supported way to manage master data and test databases: `python -m backend.cli` commands that bootstrap the facility, import the roster CSVs, withdraw and (on IRB direction) purge a resident, seed the synthetic `test_v0_1` roster with the test users and API key, and reset a test database. There are no HTTP endpoints for master data (FR-227, D-34), and every command that could load test data refuses to run in production (DB-059, AGT-014).

## Business Context

- BR-16 and FR-227: residents, devices, assignments and the facility are managed by version-controlled seed files and CLI only, with study IDs only.
- OQ-11 and FR-228: withdrawal stops ingestion and hides the resident; IRB-directed purge is possible but tightly controlled (DB-062..DB-064).
- BR-15: the `test_v0_1` roster (R01–R10, D01–D10 with D07B, shared D02) is the base of the answer-key dataset (DB-056, D-68).
- AGT-014 / D-28: no seed or test data ever reaches production.

## Referenced TRDs

- TRD 15 §4.8 command table (`bootstrap`, `import-master-data`, `withdraw-resident`, `seed`, `reset-test-db`, `purge-resident`), DEP-070..DEP-074; AC-DEP-02.
- TRD 06 DB-024, DB-056, DB-057, DB-059..DB-064; AC-DB-08, AC-DB-10.
- TRD 20 PGS-026, PGS-019, §4.3 (migrator closed list), §4.12 roster CSVs.
- TRD 23 DME-009.
- TRD 21 ENV-053, ENV-041.
- TRD 02 FR-227, FR-228.
- TRD 24 D-34, D-68, D-71.

## Scope

- Roster files `database/seeds/test_v0_1/facilities.csv`, `residents.csv`, `devices.csv`, `device_assignments.csv` with exactly the TRD 20 §4.12 content.
- `backend/cli.py` commands:
  - `bootstrap`: idempotently creates the facility row from `FACILITY_NAME`/`FACILITY_TZ` if missing and verifies that `config_parameters` holds the rows of both profiles seeded by migration 0002 (exit code 2 naming any missing row); it never inserts or overwrites parameter rows (TRD 15 §4.8, TRD 24 D-85).
  - `import-master-data --dir D`: one transaction; idempotent upsert of facility, residents, devices and device assignments from the four CSV files (format DB-060); one `roster.loaded` audit row with counts and operator.
  - `withdraw-resident <resident_code> --on <YYYY-MM-DD>`: one UPDATE of `status`/`withdrawn_on` plus `resident.withdrawn` audit row; existing rows unchanged.
  - `purge-resident <resident_code> --confirm <resident_code>`: as `echowell_migrator` with `SET echowell.allow_purge = 'on'`, delete the withdrawn resident's rows in the DB-064 FK order in one transaction and insert one `resident.purged` audit row with per-table counts; audit rows are never deleted.
  - `seed test_v0_1 [--master-only] [--reset]`: refuse with exit code 2 and "seeding is not allowed in production" when `APP_ENV=production`; refuse with exit code 2 when any `SEED_*` variable is missing; run `import-master-data` on `database/seeds/test_v0_1/`; upsert users `admin@example.com`, `clinician@example.com`, `researcher@example.com` (by e-mail) and API key `test-ingest` with scopes `ingest:write`, `pipeline:run` (by name) from `SEED_*`, storing only hashes, never printing; `--master-only` stops here; `--reset` runs `reset-test-db` first. The ingest-and-run part of the full seed is added by FEAT-055.
  - `reset-test-db`: refuse with exit code 2 unless `APP_ENV` ∈ {local, test, staging} and `PIPELINE_PROFILE = test_v0_1`; connect with `DATABASE_MIGRATION_URL`, `SET ROLE echowell_migrator`, run `alembic downgrade base` then `alembic upgrade head`, then write one `seed.reset` audit row.
- Command-specific refusals are checked before settings validation (exit code 2), settings validation uses the ENV-053 subset (exit code 1).

## Out of Scope

- `create-user`, `create-api-key`, `revoke-api-key` (FEAT-016).
- The SRC-05 ingest and pipeline-run steps of `seed test_v0_1`, `run-pipeline`, `rebuild`, `set-config` (FEAT-055); `resolve-data-alert` (FEAT-032); `export-openapi` (FEAT-038).
- The ground-truth loader `database/seeds/load_evaluation_ground_truth.py` (FEAT-057); `backend/cli.py` never references `evaluation_ground_truth`.
- Ingest rejection of withdrawn residents (FEAT-023) and stopping the day ledger at `withdrawn_on` (FEAT-049), which realise the rest of DB-063.
- Staging re-seed automation in the deploy workflow (FEAT-086, DEP-074).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-017-FR-01 | Master data (facility, residents, devices, assignments) shall be managed only through version-controlled CSV files and `python -m backend.cli` commands; no HTTP endpoint exists for them. | FR-227, ARC-067, D-34 |
| FEAT-017-FR-02 | `import-master-data --dir D` shall load `facilities.csv` (`name,timezone`), `residents.csv` (`resident_code,sex,cohort,enrolled_on,admitted_on`), `devices.csv` (`device_code,room_label,active,firmware_version_last`), `device_assignments.csv` (`resident_code,device_code,valid_from,valid_to`) in one transaction as an idempotent upsert, writing one `roster.loaded` audit row with row counts; files contain study IDs only. | DB-060, TRD 15 §4.8 |
| FEAT-017-FR-03 | `database/seeds/test_v0_1/` shall contain exactly the four CSV files of TRD 20 §4.12 (facility Edgewood, R01–R10 with SRC-04 sex values, 10 devices with D07 inactive, 11 assignments including shared D02 and R07 D07 → D07B on 2026-10-13). | DB-056, PGS-026, D-68 |
| FEAT-017-FR-04 | `seed test_v0_1` shall run the roster import and create or update (upsert by e-mail and key name) the three users and the API key `test-ingest` (scopes `ingest:write`, `pipeline:run`) from `SEED_ADMIN_PASSWORD`, `SEED_CLINICIAN_PASSWORD`, `SEED_RESEARCHER_PASSWORD`, `SEED_INGEST_API_KEY`, storing only argon2id/SHA-256 hashes and never printing or logging a secret; running it twice leaves one row per user and key. | DB-056, DB-057, D-71 |
| FEAT-017-FR-05 | `seed` shall exit with code 2 and write nothing when `APP_ENV=production` (message "seeding is not allowed in production") or when any `SEED_*` variable is missing. | DEP-070, DB-057, DB-059, PGS-026 |
| FEAT-017-FR-06 | `seed test_v0_1 --master-only` shall load the roster, users and API key only. | D-68, TRD 15 §4.8 |
| FEAT-017-FR-07 | `reset-test-db` shall refuse with exit code 2 unless `APP_ENV` ∈ {local, test, staging} and `PIPELINE_PROFILE = test_v0_1`; otherwise, as `echowell_migrator`, run `alembic downgrade base` then `alembic upgrade head` (no TRUNCATE, no purge path), leaving 46 `config_parameters` rows, and write exactly one `seed.reset` audit row. | DB-024, D-71 |
| FEAT-017-FR-08 | `seed test_v0_1 --reset` shall equal `reset-test-db` followed by `seed test_v0_1` and shall succeed twice in a row on a populated database. | DEP-071, AC-DB-08 |
| FEAT-017-FR-09 | `bootstrap` shall be idempotent: running it twice leaves the database identical to running it once. | DEP-072 |
| FEAT-017-FR-10 | `withdraw-resident <code> --on <date>` shall set `status = 'withdrawn'` and `withdrawn_on` with one UPDATE plus one `resident.withdrawn` audit row, leaving existing rows of that resident unchanged; status never returns to `active`. | DB-062, DME-009, FR-228 |
| FEAT-017-FR-11 | `purge-resident <code> --confirm <code>` shall run as `echowell_migrator` with `echowell.allow_purge = 'on'`, delete in the order scores, cusum_state, data_alerts, alert_reviews, staff_notes, alerts, baselines, day_ledger, processed_sessions, epochs, raw_sessions, device_assignments, residents in one transaction, and insert one `resident.purged` audit row with only the resident code and per-table counts; no `audit_logs` row is deleted. | DB-064, PGS-019 |
| FEAT-017-FR-12 | The MVP shall contain no automated deletion, archiving or expiry job. | DB-061 |
| FEAT-017-FR-13 | Production shall never receive rows with `ingest_batches.source = 'seed'`; staging and local receive only synthetic or test data. | DEP-073, DB-059, AGT-014 |
| FEAT-017-FR-14 | Operator commands shall validate only the ENV-053 variable subset, check command-specific refusals first (exit 2), and fail settings validation with exit 1; placeholder `local-dev-only`/`ci-only` secrets are refused in staging and production. | ENV-053, ENV-002, ENV-041 |

## Inputs

- CSV files in `--dir` or `database/seeds/test_v0_1/`; command arguments; environment (`APP_ENV`, `PIPELINE_PROFILE`, `DATABASE_URL`, `DATABASE_MIGRATION_URL`, `FACILITY_NAME`, `FACILITY_TZ`, `SEED_*`).
- Credential primitives from FEAT-016; audit writer from FEAT-015.

## Outputs

- Rows in `facilities`, `residents`, `devices`, `device_assignments`, `users`, `api_keys`, `audit_logs`; status changes on `residents`; deletions by `purge-resident`; a reset schema.
- Exit codes 0 (success), 1 (settings invalid), 2 (command refusal).

## Data Flow

`python -m backend.cli seed test_v0_1 --master-only` → check `APP_ENV` and `SEED_*` (refuse with 2) → validate ENV-053 settings (fail with 1) → connect (seed runs as `echowell_migrator`, TRD 20 §4.3) → `import-master-data` upserts the four CSVs and writes `roster.loaded` → upsert users and `test-ingest` from `SEED_*` with hashes and `user.created`/`user.updated`/`api_key.created` audit rows → commit. `reset-test-db` → refusal checks → `SET ROLE echowell_migrator` → Alembic downgrade/upgrade → `seed.reset` audit row.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-016, FEAT-014

- FEAT-016 provides password hashing, API-key hashing and the CLI scaffolding with audited commands.
- FEAT-014 completes the Phase 4 repository layer (read models over the seeded roster are verified with this command's output).

Features that build directly on this one: FEAT-055 (full seed with SRC-05 ingest and pipeline run).

## Database Impact

- Tables written: `facilities`, `residents`, `devices`, `device_assignments`, `users`, `api_keys`, `audit_logs` (`config_parameters` is only read by `bootstrap`, D-85).
- Tables deleted from (purge-resident only, migrator with purge setting): `scores`, `cusum_state`, `data_alerts`, `alert_reviews`, `staff_notes`, `alerts`, `baselines`, `day_ledger`, `processed_sessions`, `epochs`, `raw_sessions`, `device_assignments`, `residents`.
- Schema dropped and recreated (reset-test-db, via Alembic).

## API Impact

None exposed (FR-227). Seeded users and the `test-ingest` key are later used by E-02 login and E-05/E-06/E-20 key-authenticated endpoints.

## Frontend Impact

None directly. Withdrawn residents disappear from default lists (FR-228) through FEAT-027.

## Analytics Impact

None. `bootstrap` only checks that the migration-0002 parameter rows exist (D-85); it does not use `analytics/config.py`.

## Security Requirements

- Refusal in production for `seed` and `reset-test-db` (exit 2, nothing written) (DB-059, DB-024, AGT-014).
- Seeded secrets come only from `SEED_*`; only hashes stored; never printed or logged (DB-057).
- Migrator credentials (`DATABASE_MIGRATION_URL`) used only by the closed list: `seed`, `reset-test-db`, `purge-resident` (TRD 20 §4.3, SEC-111); `import-master-data`, `bootstrap` and `withdraw-resident` outside `seed` run as `echowell_app`.
- Purge is the only use of `echowell.allow_purge` and requires `--confirm` equal to the code (DB-064).
- Every command writes an audit row with `actor_type = system` and `details.operator` (SEC-103, TRD 12 §4.12).

## Error Handling

| Failure | Behaviour | Trace |
|---|---|---|
| `seed` or `reset-test-db` with `APP_ENV=production` | Exit 2, nothing written | DEP-070, DB-059, AC-DB-08 |
| `reset-test-db` with `PIPELINE_PROFILE` ≠ `test_v0_1` | Exit 2 | DB-024 |
| Missing `SEED_*` variable | Exit 2, nothing written | DB-057 |
| Overlapping assignment or bad code in a CSV | Transaction rolls back; non-zero exit naming the file and row | DB-060, PGS-015 |
| `purge-resident` with mismatching `--confirm` or a resident that is not withdrawn | Refused, nothing deleted | DB-064 |
| Settings invalid | Exit 1, CRITICAL `startup_config_invalid` | ENV-002 |

## Logging Requirements

- Audit rows: `roster.loaded`, `resident.withdrawn`, `resident.purged`, `seed.reset`, `user.created`/`user.updated`, `api_key.created` (TRD 12 §4.12), each with `details.operator`.
- One `audit_event` INFO line per audit row (LOG-092). No secret values in any output (DB-057).

## Testing Requirements

- Integration (`tests/integration/test_cli_seed.py`, marker `integration`):
  - DB-056: after `seed test_v0_1 --master-only`, counts facilities/residents/devices/assignments/users/api_keys = 1/10/10/11/3/1; `evaluation_ground_truth` empty.
  - DB-057: running the seed twice leaves 3 users and 1 key; missing `SEED_ADMIN_PASSWORD` exits 2 and writes nothing; stdout and logs contain no seed secret.
  - AC-DB-08 and AC-DEP-02 (master-data part): `seed test_v0_1` and `reset-test-db` exit 2 with `APP_ENV=production`; `reset-test-db` exits 2 with `PIPELINE_PROFILE=production`; `seed test_v0_1 --reset` succeeds twice in a row.
  - DB-024: after `reset-test-db` on a populated test database, `config_parameters` has 46 rows, `audit_logs` exactly 1 row (`seed.reset`), every other table empty.
  - DB-062: `withdraw-resident R08 --on 2026-10-20` sets status and date, writes `resident.withdrawn`, leaves R08's other rows unchanged.
  - DB-064: local purge of a withdrawn R08 leaves no R08 rows except `audit_logs`; one `resident.purged` row with counts.
  - DEP-072: `bootstrap` twice equals once (row-by-row comparison).
  - DB-060: `import-master-data --dir tests/fixtures/seeds/demo_overlay` adds R11/D11 idempotently and writes `roster.loaded`.
- AC-DB-10 (withdrawn R08 → ledger through 2026-10-20 and 422 "resident withdrawn") is completed with FEAT-023 and FEAT-049.

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-017-AC-01 | After `seed test_v0_1 --master-only` with all `SEED_*` set, row counts facilities/residents/devices/device_assignments/users/api_keys are 1/10/10/11/3/1, and the D07 row has `active = false`. | DB-056 |
| FEAT-017-AC-02 | Running the same command a second time leaves the same counts; stdout, stderr and logs contain none of the four `SEED_*` values. | DB-057, D-71 |
| FEAT-017-AC-03 | With `APP_ENV=production`, `seed test_v0_1` exits 2 printing "seeding is not allowed in production" and `reset-test-db` exits 2; no table row count changes. | DEP-070, DB-059, AC-DB-08 |
| FEAT-017-AC-04 | With `PIPELINE_PROFILE=production` and `APP_ENV=local`, `reset-test-db` exits 2. | DB-024, AC-DB-08 |
| FEAT-017-AC-05 | On a populated local test database, `reset-test-db` leaves `config_parameters` with 46 rows, `audit_logs` with exactly one `seed.reset` row and every other table empty; `seed test_v0_1 --reset` then succeeds twice in a row. | DB-024, DEP-071, AC-DB-08 |
| FEAT-017-AC-06 | `withdraw-resident R08 --on 2026-10-20` sets R08 `status = withdrawn`, `withdrawn_on = 2026-10-20` and writes one `resident.withdrawn` audit row; R08's other rows are unchanged. | DB-062, DME-009 |
| FEAT-017-AC-07 | After withdrawing R08 locally, `purge-resident R08 --confirm R08` removes every R08 row from the 13 tables of DB-064 and writes one `resident.purged` audit row; no `audit_logs` row is deleted. | DB-064 |
| FEAT-017-AC-08 | `bootstrap` run twice produces a database identical (all rows) to running it once. | DEP-072 |
| FEAT-017-AC-09 | `grep -rn "evaluation_ground_truth" backend/cli.py` returns nothing; no router under `backend/api/` writes `residents`, `devices` or `device_assignments`. | TRD 20 §4.12, FR-227 |

## Definition of Done

- All FEAT-017 acceptance criteria pass; CLI help documents each command, its allowed `APP_ENV` and exit codes.
- Roster CSVs committed with study IDs only (AGT-017); delivered in the Phase 4 PR.

## Implementation Notes

- Check `APP_ENV`/`PIPELINE_PROFILE`/`SEED_*` refusals before building `Settings` so refusals use exit 2, not 1 (ENV-002).
- `reset-test-db` drops tables through Alembic; DROP fires no row or TRUNCATE trigger, so neither `reject_mutation()` nor the purge setting is involved (DB-024, D-71).
- Seed users use the RFC 2606 domain `example.com`; do not use `.test` (DB-057).
- Until FEAT-055 adds the SRC-05 ingest and pipeline-run steps, `seed test_v0_1` without `--master-only` performs the master-data steps only; FEAT-055 completes DB-058 and DEP-015.
- Resolved (TRD 24 D-85): migration 0002 seeds all 46 `config_parameters` rows, so `bootstrap`'s parameter step is a verification only (TRD 15 §4.8 aligned); it has no dependency on `PipelineConfig` (FEAT-040).
