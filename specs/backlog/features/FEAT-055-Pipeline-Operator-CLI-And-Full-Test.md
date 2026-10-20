# FEAT-055 Pipeline operator CLI (run-pipeline, rebuild, set-config) and full test_v0_1 seed

| Field | Value |
|---|---|
| Epic | Data Processing |
| Build phase | Phase 6 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-053, FEAT-017, FEAT-026 |
| Status | Not Started |

## Purpose

Give operators the command-line tools that run and reconfigure the pipeline, and complete the test seed. The feature adds three `backend.cli` commands — `run-pipeline --scope all`, `rebuild --profile P --confirm REBUILD` and `set-config` — and completes `seed test_v0_1` so that, after the roster step delivered by FEAT-017, it ingests SRC-05 through the normal ingest code path and runs the pipeline at as-of 2026-10-30 15:00 America/Chicago, giving a fully populated test system (D-68). It also enforces the rule that an algorithm-key change takes effect only through `rebuild` (D-56, D-69).

## Business Context

- BR-15 (answer key): `seed test_v0_1` produces the reference test system used by validation Tier B, the UI fixture DS-07, E2E and staging smoke tests.
- BR-09, BR-11, BR-16 (controlled parameters, frozen baselines, audit): parameters change only through an audited command; frozen baselines are recomputed only by the explicit operator rebuild (FR-229).
- RSK-12 (demo fallback): `run-pipeline` runs the pipeline from the command line for local use, CI and the demo (ARC-066).
- FRs covered (BACKLOG.md): FR-229.

## Referenced TRDs

- TRD 15 §4.8 (command table: `seed`, `set-config`, `run-pipeline`, `rebuild`, refusal rules), DEP-070, DEP-071, DEP-074.
- TRD 07 ANL-031 (profile loading, `pipeline_config_invalid`), ANL-032 (rebuild path, `config_changed_requires_rebuild`), ANL-029 (value validation), ANL-030 (`config_hash`), §4.7 (algorithm vs operational keys).
- TRD 06 DB-056..DB-059 (seed steps, `--master-only`, ingest of SRC-05 with `source = 'seed'`, trigger `manual`, refusal in production), DB-009 (only `echowell_migrator` may DELETE `baselines`), DB-016.
- TRD 10 ING-059 (seed uses the ingest code path), ING-017 (ingest key validation for `set-config`).
- TRD 01 ARC-066 (`run-pipeline` CLI).
- TRD 12 SEC-103 (CLI audit rows with `details.operator`), §4.12 actions `config.changed`, `pipeline.rebuild`.
- TRD 02 FR-229; TRD 21 `DATABASE_MIGRATION_URL`; TRD 24 D-56, D-68, D-69.
- TRD 13 TST-053, TST-188; TRD 14 TDV-031, TDV-061.

## Scope

- `python -m backend.cli run-pipeline --scope all [--profile P]`: full run through `pipeline_runner.run` with trigger `manual`.
- `python -m backend.cli rebuild --profile P --confirm REBUILD`: connect with `DATABASE_MIGRATION_URL`, run `pipeline_runner.run(scope="all", trigger="manual", rebuild=True, ...)`, which deletes and recomputes each resident's `baselines` inside that resident's transaction; audit `pipeline.rebuild` with old and new config hashes. Adds the `rebuild` keyword to the runner of FEAT-053.
- The runner check that ends every non-rebuild run `failed` with `error_message` "configuration changed; run the rebuild command" and warning `config_changed_requires_rebuild` when the active `config_hash()` differs from the latest succeeded run's hash.
- `python -m backend.cli set-config --profile P --key K --value '<json>' --reason "<text>"`: runs as `echowell_migrator`, validates against the key's schema, refuses unknown keys and invalid values with exit code 2, updates the row and writes `config.changed` (profile, key, old, new, reason, operator) in one transaction; prints the rebuild hint for algorithm keys.
- Completion of `python -m backend.cli seed test_v0_1` (without `--master-only`): ingest `tests/fixtures/pipeline_input/EchoWell_pipeline_test_input_v0_1.csv` through the ingestion service as one `ingest_batches` row with `source = 'seed'`, then run the pipeline with trigger `manual` and explicit as-of 2026-10-30T20:00:00Z.

## Out of Scope

- Roster import, users, API key, `--master-only`, `--reset` and `reset-test-db` (FEAT-017).
- The evaluation ground-truth loader `database/seeds/load_evaluation_ground_truth.py` (FEAT-057); `backend/cli.py` never references it.
- `POST /api/v1/pipeline/run` (FEAT-024) and automatic triggers (FEAT-054).
- `resolve-data-alert` (FEAT-032), credential commands (FEAT-016), `export-openapi` (FEAT-038).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-055-FR-01 | `run-pipeline --scope all [--profile P]` shall run the full pipeline through `pipeline_runner.run` and record a `pipeline_runs` row with trigger `manual`. | TRD 15 §4.8; ARC-066 |
| FEAT-055-FR-02 | `set-config` shall run as `echowell_migrator` (`DATABASE_MIGRATION_URL`), validate the JSON value against the key's schema (TRD 07 ANL-029, TRD 10 ING-017), refuse unknown keys and invalid values with exit code 2 and no change, and otherwise update the `config_parameters` row and write one `audit_logs` row `config.changed` with `details` profile, key, old, new, reason and `operator` in the same transaction. | TRD 15 §4.8; FR-229; SEC-103; D-69 |
| FEAT-055-FR-03 | For an algorithm key (a `PipelineConfig` field other than `operational`), `set-config` shall print "Algorithm key changed: run python -m backend.cli rebuild --profile P --confirm REBUILD"; operational keys take effect at the next run or request. | TRD 15 §4.8; ANL-032; TRD 07 §4.7; D-56 |
| FEAT-055-FR-04 | Every run other than `rebuild` (ingest, nightly, `POST /api/v1/pipeline/run`, `run-pipeline`) shall end `failed` with `error_message` "configuration changed; run the rebuild command" and warning `config_changed_requires_rebuild` when the active `config_hash()` differs from the hash of the latest succeeded run. | ANL-032; D-56 |
| FEAT-055-FR-05 | `rebuild --profile P --confirm REBUILD` shall refuse to run without the exact confirmation token, connect with `DATABASE_MIGRATION_URL`, run `pipeline_runner.run(scope="all", trigger="manual", rebuild=True)`, delete each resident's `baselines` inside that resident's transaction before writing the recomputed rows, and write audit `pipeline.rebuild` with `{profile, old_config_hash, new_config_hash, operator}`; it is the only path that deletes frozen baselines. | ANL-032; DB-009; DB-016; TRD 12 §4.12 |
| FEAT-055-FR-06 | `seed test_v0_1` (no `--master-only`) shall, after the roster step, ingest SRC-05 through the same validation and insertion code path as `POST /api/v1/ingest` as one `ingest_batches` row with `source = 'seed'` (never by direct SQL into `raw_sessions`). | DB-058; ING-059; D-68 |
| FEAT-055-FR-07 | The seed shall then run the pipeline with trigger `manual` and explicit as-of 2026-10-30 15:00 America/Chicago (2026-10-30T20:00:00Z), as `POST /api/v1/pipeline/run {as_of}` would. | DB-058; TRD 15 §4.8; TDV-061 |
| FEAT-055-FR-08 | `seed` shall exit 2 with "seeding is not allowed in production" and touch nothing when `APP_ENV = production`. | DEP-070; DB-059 |
| FEAT-055-FR-09 | CLI commands shall write audit rows with `actor_type = system` and `details.operator` = the OS user name. | SEC-103 |
| FEAT-055-FR-10 | No CLI command shall print or log a secret, connection string or feature value. | DB-057; SEC-104 |

## Inputs

- Command-line arguments; env `APP_ENV`, `PIPELINE_PROFILE`, `DATABASE_URL`, `DATABASE_MIGRATION_URL`, `GIT_SHA`.
- `config_parameters` rows; SRC-05 fixture `tests/fixtures/pipeline_input/EchoWell_pipeline_test_input_v0_1.csv`; roster and users from FEAT-017.

## Outputs

- `pipeline_runs` rows (trigger `manual`); derived tables (FEAT-053); recomputed `baselines` after `rebuild`.
- `config_parameters` updates; `audit_logs` rows `config.changed`, `pipeline.rebuild`, `ingest.batch.received` (seed batch).
- After `seed test_v0_1`: 283 `raw_sessions` rows and run counts 283/267/12/2/2/17/2/0/98/2/0/10 (DB-058, DB-020).
- Exit codes: 0 success, 2 refusal or validation error, non-zero on run failure.

## Data Flow

- `set-config`: CLI → migrator connection → validate → UPDATE `config_parameters` + INSERT audit (one transaction) → print hint for algorithm keys.
- `rebuild`: CLI → migrator connection → runner (`rebuild=True`) → per resident: lock, DELETE baselines, write recomputed rows → audit `pipeline.rebuild` → later runs see an equal hash and succeed.
- `seed test_v0_1`: FEAT-017 roster step → ingestion service (batch, `source = seed`) → runner with as-of 2026-10-30T20:00:00Z → populated system.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-053, FEAT-017, FEAT-026

- FEAT-053 provides the runner the commands call (and that this feature extends with `rebuild=True` and the hash check).
- FEAT-017 provides `backend/cli.py`, the roster/users/key seed steps, `--master-only` and `--reset`.
- FEAT-026 provides the batch ingestion service the seed reuses.

## Database Impact

- Tables written: `config_parameters` (`value`, `updated_at`), `audit_logs`, `ingest_batches`, `raw_sessions` (through the ingest service), `pipeline_runs` and all derived tables (through FEAT-053), `baselines` (DELETE then INSERT, rebuild only, as `echowell_migrator`).
- Tables read: `config_parameters`, `pipeline_runs` (`config_snapshot.config_hash` of the latest succeeded run).
- No schema change.

## API Impact

None exposed. The hash check of FEAT-055-FR-04 also affects runs started by `POST /api/v1/pipeline/run` (E-20), which then end `failed` until the rebuild runs.

## Frontend Impact

None. Failed runs caused by `config_changed_requires_rebuild` appear in the `/admin` pipeline-runs list (FEAT-074).

## Analytics Impact

- Uses `PipelineConfig.from_mapping`, `snapshot()` and `config_hash()` (FEAT-040) to validate values and compare hashes.
- `rebuild=True` recomputes frozen baselines through the normal engine path (no new algorithm).

## Security Requirements

- `set-config` and `rebuild` run only with `DATABASE_MIGRATION_URL` (role `echowell_migrator`, the only role allowed to DELETE `baselines`) from an operator workstation (`railway run`), never from the web service (TRD 15 §4.8, DB-009).
- `seed` belongs to the closed list of commands that connect as `echowell_migrator` (TRD 20 §4.3, SEC-111) and is refused in production (DEP-070); the interim stack holds synthetic data only (AGT-014).
- Audit rows record the operator name and never secrets (SEC-103, SEC-104).

## Error Handling

- Unknown key, invalid JSON or out-of-range value → exit 2, no change (TRD 15 §4.8).
- Missing or wrong `--confirm REBUILD` → refuse without connecting.
- Seed in production → exit 2 "seeding is not allowed in production" (DEP-070).
- Pipeline failure during `run-pipeline`, `rebuild` or `seed` → non-zero exit; the run row is `failed` with `error_message` (FEAT-053).
- Profile without rows or invalid stored value → run `failed` with `pipeline_config_invalid` (ANL-031).

## Logging Requirements

- Audit rows: `config.changed` (old, new, reason, operator), `pipeline.rebuild` (old/new hash, operator), `ingest.batch.received` for the seed batch, plus the runner's `pipeline.run.*` rows.
- CLI console output: command result, run id and counts only.

## Testing Requirements

- Integration (`tests/integration/test_cli_pipeline.py`, marker `integration`):
  - `set-config` on `cusum_h` writes one `config.changed` row with old, new, reason and operator, prints the rebuild hint; the next `run-pipeline` ends `failed` with `config_changed_requires_rebuild`; after `rebuild` the next run succeeds (ANL-032, TST-053).
  - `set-config` on `alert_snooze_hours` changes no `config_hash` and prints no rebuild hint (ANL-030 verification).
  - Unknown key and invalid value → exit 2, row unchanged.
  - `rebuild` without `--confirm REBUILD` refuses; with it, baselines are deleted and re-inserted inside each resident transaction and `pipeline.rebuild` is audited.
  - `seed test_v0_1` on an empty migrated database: 283 raw rows, one `ingest_batches` row with `source = 'seed'`, a `manual` run with as-of 2026-10-30T20:00:00Z and counts of DB-020; `APP_ENV=production` → exit 2.
  - TST-188 logins after `seed test_v0_1`.
- No dedicated TRD 13 test ID exists for `run-pipeline`, `rebuild` and `set-config`; tests carry `@pytest.mark.req("ANL-032")`, `req("FR-229")`, `req("DB-058")` (TST-013).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-055-AC-01 | `python -m backend.cli seed test_v0_1` on an empty migrated test database yields 283 `raw_sessions` rows from one `seed` batch and a succeeded `manual` run with as-of 2026-10-30T20:00:00Z and counts 283/267/12/2/2/17/2/0/98/2/0/10. | DB-058; DB-020 |
| FEAT-055-AC-02 | `python -m backend.cli set-config --profile test_v0_1 --key cusum_h --value '6.0' --reason "test"` writes exactly one `config.changed` audit row with old 5.0, new 6.0, reason and operator, and prints the rebuild command. | FR-229; TST-053; SEC-103 |
| FEAT-055-AC-03 | After that change, `python -m backend.cli run-pipeline --scope all` produces a `failed` run with warning `config_changed_requires_rebuild` and `error_message` "configuration changed; run the rebuild command". | ANL-032 |
| FEAT-055-AC-04 | `python -m backend.cli rebuild --profile test_v0_1 --confirm REBUILD` then succeeds, writes one `pipeline.rebuild` audit row with old and new config hashes, and the next `run-pipeline` succeeds. | ANL-032; D-56 |
| FEAT-055-AC-05 | `set-config` with an unknown key, or with `cusum_h` = `-1`, exits 2 and leaves `config_parameters` unchanged. | TRD 15 §4.8; ANL-029 |
| FEAT-055-AC-06 | With `APP_ENV=production`, `python -m backend.cli seed test_v0_1` exits 2 with "seeding is not allowed in production" and writes nothing. | DEP-070; DB-059 |
| FEAT-055-AC-07 | `grep -rn "evaluation_ground_truth\|load_evaluation_ground_truth" backend/cli.py` returns nothing. | TDV-011; TRD 15 §4.8 |

## Definition of Done

- All FEAT-055 acceptance criteria pass; `pytest tests/integration -q -k pipeline` green.
- `seed test_v0_1` produces the DS-07 system used by FEAT-058..FEAT-060 and E2E (D-68).
- Batch report lists IDs, commands and results (AGT-022).

## Implementation Notes

- The `rebuild` keyword is the only runner path allowed to DELETE `baselines`; it must use the migrator connection passed in by the CLI, never the app engine.
- Compare the active `config_hash()` with `pipeline_runs.config_snapshot ->> 'config_hash'` of the latest `succeeded` run; with no succeeded run yet, there is nothing to compare and the run proceeds.
- Reuse the FEAT-026 ingestion service function directly for the seed (ING-059); do not shell out to the HTTP API.
- The seed's as-of must be passed explicitly (DB-058); do not rely on any ingest-triggered run for the seeded state, because such runs use the R21 as-of precedence (TDV-031).
- TRD 13 has no test ID for these CLI commands; this gap should be noted for TRD 13 (traceability through `req` markers is used meanwhile).
