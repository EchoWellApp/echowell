# Pipeline operator CLI (run-pipeline, rebuild, set-config) and full test_v0_1 seed

## Feature Description

FEAT-055 adds the operator commands of `backend.cli`: `run-pipeline --scope all [--profile P]` (full run, trigger `manual`), `rebuild --profile P --confirm REBUILD` (the only path that deletes and recomputes frozen baselines, as `echowell_migrator`, audited `pipeline.rebuild`) and `set-config --profile P --key K --value '<json>' --reason "<text>"` (validated, audited `config.changed`, prints the rebuild hint for algorithm keys). Every non-rebuild run ends `failed` with `error_message` "configuration changed; run the rebuild command" and warning `config_changed_requires_rebuild` when the active `config_hash()` differs from the latest succeeded run. `seed test_v0_1` (without `--master-only`) ingests SRC-05 through the batch-ingest code path as one `seed` batch and runs the pipeline with trigger `manual` at as-of 2026-10-30T20:00:00Z; it is refused in production.

## Preconditions

- Local development stack with PostgreSQL 16; `alembic upgrade head` applied to an empty test database.
- Environment file loaded: `APP_ENV` (development or test), `PIPELINE_PROFILE=test_v0_1`, `DATABASE_URL`, `DATABASE_MIGRATION_URL`, `GIT_SHA`, `SEED_ADMIN_PASSWORD`, `SEED_CLINICIAN_PASSWORD`, `SEED_RESEARCHER_PASSWORD`, `SEED_INGEST_API_KEY` (values never typed into the test record).
- CLI messages are printed on stderr; capture with `2>&1`.
- Cases TC-055-03..TC-055-07 run in sequence on the same seeded database (disposable).

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-055-01 | `seed test_v0_1` yields 283 raw rows from one `seed` batch and a succeeded `manual` run with the reference counts | High | Positive |
| TC-055-02 | Seed uses the ingest code path and writes the expected audit rows | High | Database |
| TC-055-03 | `set-config cusum_h 6.0` writes one `config.changed` row and prints the rebuild command | High | Positive |
| TC-055-04 | `run-pipeline` after an algorithm-key change fails with `config_changed_requires_rebuild` | High | Negative |
| TC-055-05 | `rebuild` refuses without the exact confirmation token | High | Negative |
| TC-055-06 | `rebuild --confirm REBUILD` succeeds, audits old and new hashes; next `run-pipeline` succeeds | High | Positive |
| TC-055-07 | `set-config` with an unknown key or `cusum_h` = -1 exits 2 and changes nothing | High | Negative |
| TC-055-08 | `set-config` on an operational key prints no rebuild hint and keeps `config_hash` | Medium | Positive |
| TC-055-09 | `seed test_v0_1` with `APP_ENV=production` exits 2 and writes nothing | High | Security |
| TC-055-10 | `backend/cli.py` never references the evaluation ground truth | High | Security |
| TC-055-11 | `run-pipeline --scope all` records a `manual` run and prints run id and status only | Medium | Positive |
| TC-055-12 | `set-config` with invalid JSON or an empty reason exits 2 | Medium | Negative |

### TC-055-01 `seed test_v0_1` yields 283 raw rows from one `seed` batch and a succeeded `manual` run with the reference counts

| Step | Action | Expected Result |
|---|---|---|
| 1 | `python -m backend.cli seed test_v0_1 2>&1; echo $?` | Output lines `Ingested 283 records (2 duplicates).`, `Pipeline run <uuid> succeeded.`, `Seed test_v0_1 complete.`; exit `0` |
| 2 | `SELECT count(*) FROM raw_sessions;` | `283` |
| 3 | `SELECT source, record_count, accepted_count, duplicate_count, rejected_count FROM ingest_batches;` | One row: `seed`, 283, 283, 2, 0 |
| 4 | `SELECT trigger, status, as_of, counts FROM pipeline_runs;` | One row: `manual`, `succeeded`, `2026-10-30 20:00:00+00`, counts `arrivals` 283, `usable` 267, `set_aside` 12, `quarantined` 2, `duplicate` 2, `missing_resident` 17, `missing_device_gap` 2, `late_arrival` 0, `scored` 98, `alerts_opened` 2, `excluded_after_as_of` 0, `residents` 10 |
| 5 | `POST /api/v1/auth/login` for each of `admin@example.com`, `clinician@example.com`, `researcher@example.com` with the matching `SEED_*` password | 200 for all three (TST-188) |

### TC-055-02 Seed uses the ingest code path and writes the expected audit rows

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT action, count(*) FROM audit_logs WHERE action IN ('ingest.batch.received','pipeline.run.started','pipeline.run.finished') GROUP BY 1 ORDER BY 1;` | `ingest.batch.received` 1, `pipeline.run.finished` 1, `pipeline.run.started` 1 |
| 2 | `SELECT count(*) FROM raw_sessions WHERE ingest_batch_id = (SELECT id FROM ingest_batches WHERE source='seed');` | `283` (all rows linked to the seed batch, none inserted by direct SQL) |
| 3 | `SELECT count(*) FROM ingest_rejections;` | `0` |

### TC-055-03 `set-config cusum_h 6.0` writes one `config.changed` row and prints the rebuild command

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT value FROM config_parameters WHERE profile='test_v0_1' AND key='cusum_h';` | `5.0` |
| 2 | `python -m backend.cli set-config --profile test_v0_1 --key cusum_h --value '6.0' --reason "test" 2>&1; echo $?` | Prints `test_v0_1.cusum_h updated.` and `Algorithm key changed: run python -m backend.cli rebuild --profile test_v0_1 --confirm REBUILD`; exit `0` |
| 3 | `SELECT value FROM config_parameters WHERE profile='test_v0_1' AND key='cusum_h';` | `6.0` |
| 4 | `SELECT actor_type, entity_type, entity_id, details FROM audit_logs WHERE action='config.changed';` | Exactly 1 row: `system`, `config_parameter`, `test_v0_1.cusum_h`, details `old` 5.0, `new` 6.0, `reason` "test", `operator` = OS user name |

Note: FEAT-055-FR-02 lists `profile` and `key` inside `details`; the code records them in `entity_id` ("test_v0_1.cusum_h") and writes `details` {old, new, reason, operator} (`backend/cli.py:599-601`).

### TC-055-04 `run-pipeline` after an algorithm-key change fails with `config_changed_requires_rebuild`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `python -m backend.cli run-pipeline --scope all 2>&1; echo $?` | Prints `Pipeline run <uuid> failed.`; non-zero exit (1) |
| 2 | `SELECT status, error_message, warnings FROM pipeline_runs ORDER BY started_at DESC LIMIT 1;` | `failed`; `configuration changed; run the rebuild command`; warnings `[{"code": "config_changed_requires_rebuild", "resident_code": null, "session_id": null, "detail": "configuration changed; run the rebuild command"}]` |
| 3 | `SELECT count(*) FROM baselines;` | `180` (unchanged; no derived write) |
| 4 | Admin `POST /api/v1/pipeline/run` `{"scope": "all", "profile": "test_v0_1", "as_of": "2026-10-30T20:00:00Z"}` and poll the run | 202, then the run ends `failed` with the same `error_message` |

### TC-055-05 `rebuild` refuses without the exact confirmation token

| Step | Action | Expected Result |
|---|---|---|
| 1 | `python -m backend.cli rebuild --profile test_v0_1 --confirm rebuild 2>&1; echo $?` | `Refused: type --confirm REBUILD to delete and recompute all baselines`; exit `2` |
| 2 | `python -m backend.cli rebuild --profile test_v0_1 2>&1; echo $?` | argparse error "the following arguments are required: --confirm"; exit `2` |
| 3 | `SELECT count(*) FROM pipeline_runs; SELECT count(*) FROM audit_logs WHERE action='pipeline.rebuild';` | Run count unchanged; `0` rebuild audit rows |

### TC-055-06 `rebuild --confirm REBUILD` succeeds, audits old and new hashes; next `run-pipeline` succeeds

| Step | Action | Expected Result |
|---|---|---|
| 1 | Note `SELECT config_snapshot->>'config_hash' FROM pipeline_runs WHERE status='succeeded' ORDER BY started_at DESC LIMIT 1;` | Old hash H1 |
| 2 | `python -m backend.cli rebuild --profile test_v0_1 --confirm REBUILD 2>&1; echo $?` | `Pipeline run <uuid> succeeded.`; exit `0` |
| 3 | `SELECT actor_type, entity_type, details FROM audit_logs WHERE action='pipeline.rebuild';` | 1 row: `system`, `pipeline_run`, details `profile` "test_v0_1", `old_config_hash` H1, `new_config_hash` H2 ≠ H1, `operator` |
| 4 | `SELECT count(*), count(DISTINCT pipeline_run_id), max(pipeline_run_id::text) = (SELECT id::text FROM pipeline_runs WHERE status='succeeded' ORDER BY started_at DESC LIMIT 1) FROM baselines;` | `180`, `1`, `t` (all baselines deleted and re-inserted by the rebuild run) |
| 5 | `python -m backend.cli run-pipeline --scope all 2>&1; echo $?` | `Pipeline run <uuid> succeeded.`; exit `0` |

### TC-055-07 `set-config` with an unknown key or `cusum_h` = -1 exits 2 and changes nothing

| Step | Action | Expected Result |
|---|---|---|
| 1 | `\copy (SELECT profile, key, value FROM config_parameters ORDER BY 1,2) TO '/tmp/cfg_before.csv' CSV` | Snapshot written |
| 2 | `python -m backend.cli set-config --profile test_v0_1 --key no_such_key --value '1' --reason "test" 2>&1; echo $?` | `Refused: unknown key no_such_key for profile test_v0_1`; exit `2` |
| 3 | `python -m backend.cli set-config --profile test_v0_1 --key cusum_h --value '-1' --reason "test" 2>&1; echo $?` | `Refused: cusum_h: value -1.0 is out of range`; exit `2` |
| 4 | Snapshot again to `/tmp/cfg_after.csv`; `diff /tmp/cfg_before.csv /tmp/cfg_after.csv` | No difference |
| 5 | `SELECT count(*) FROM audit_logs WHERE action='config.changed';` | Unchanged from before step 2 |

### TC-055-08 `set-config` on an operational key prints no rebuild hint and keeps `config_hash`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `python -m backend.cli set-config --profile test_v0_1 --key alert_snooze_hours --value '12' --reason "test" 2>&1` | Prints `test_v0_1.alert_snooze_hours updated.` only; no "Algorithm key changed" line |
| 2 | `python -m backend.cli run-pipeline --scope all 2>&1` | `succeeded` |
| 3 | Compare `config_snapshot->>'config_hash'` of the last two succeeded runs | Equal |

### TC-055-09 `seed test_v0_1` with `APP_ENV=production` exits 2 and writes nothing

| Step | Action | Expected Result |
|---|---|---|
| 1 | On an empty migrated database: `APP_ENV=production python -m backend.cli seed test_v0_1 2>&1; echo $?` | `Refused: seeding is not allowed in production`; exit `2` |
| 2 | `SELECT (SELECT count(*) FROM residents), (SELECT count(*) FROM users), (SELECT count(*) FROM raw_sessions), (SELECT count(*) FROM pipeline_runs);` | `0, 0, 0, 0` |

### TC-055-10 `backend/cli.py` never references the evaluation ground truth

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -rn "evaluation_ground_truth\|load_evaluation_ground_truth" backend/cli.py` | No output |

### TC-055-11 `run-pipeline --scope all` records a `manual` run and prints run id and status only

| Step | Action | Expected Result |
|---|---|---|
| 1 | On DS-07: `python -m backend.cli run-pipeline --scope all --as-of 2026-10-30T15:00:00-05:00 2>&1` | One line `Pipeline run <uuid> succeeded.`; no password, API key, connection string or feature value printed |
| 2 | `SELECT trigger, scope, status FROM pipeline_runs ORDER BY started_at DESC LIMIT 1;` | `manual`, `{"type": "all"}`, `succeeded` |
| 3 | `SELECT actor_type, actor_id FROM audit_logs WHERE action='pipeline.run.started' ORDER BY occurred_at DESC LIMIT 1;` | `system`, OS user name |
| 4 | `python -m backend.cli run-pipeline --scope all --as-of 2026-10-30T15:00:00 2>&1; echo $?` | `Refused: --as-of needs a time-zone offset`; exit `2` |

### TC-055-12 `set-config` with invalid JSON or an empty reason exits 2

| Step | Action | Expected Result |
|---|---|---|
| 1 | `python -m backend.cli set-config --profile test_v0_1 --key cusum_h --value 'six' --reason "test" 2>&1; echo $?` | `Refused: --value must be JSON`; exit `2` |
| 2 | `python -m backend.cli set-config --profile test_v0_1 --key cusum_h --value '6.0' --reason " " 2>&1; echo $?` | `Refused: --reason must not be empty`; exit `2` |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | After TC-055-03, admin `POST /api/v1/pipeline/run` (E-20) | 202; run ends `failed` with warning `config_changed_requires_rebuild` |
| 2 | After TC-055-06, `GET /api/v1/pipeline/runs?status=failed` (admin) | Lists the failed runs of TC-055-04 with the warning code |
| 3 | After TC-055-01, researcher `GET /api/v1/analytics` | `pipeline_run.trigger` "manual", `as_of` "2026-10-30T20:00:00Z" |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT key, value, updated_at FROM config_parameters WHERE profile='test_v0_1' AND key IN ('cusum_h','alert_snooze_hours');` after TC-055-03/08 | `cusum_h` 6.0, `alert_snooze_hours` 12, `updated_at` refreshed |
| 2 | `SELECT action, details->>'operator' FROM audit_logs WHERE action IN ('config.changed','pipeline.rebuild');` | Every row carries a non-empty `operator` |
| 3 | `SELECT details::text FROM audit_logs WHERE action IN ('config.changed','pipeline.rebuild');` | No password, API key or connection string |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Unknown key | Exit 2, no change |
| 2 | `cusum_h` = -1 | Exit 2, no change |
| 3 | Invalid JSON value | Exit 2 |
| 4 | `rebuild` with a wrong or missing token | Exit 2, no run |
| 5 | Seed in production | Exit 2, nothing written |
| 6 | Non-rebuild run after an algorithm-key change | Run `failed`, `config_changed_requires_rebuild` |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-055-AC-01 | 283 raw rows from one `seed` batch; succeeded `manual` run at 2026-10-30T20:00:00Z with counts 283/267/12/2/2/17/2/0/98/2/0/10 | TC-055-01, TC-055-02 |
| FEAT-055-AC-02 | `set-config ... cusum_h 6.0` writes exactly one `config.changed` row (old 5.0, new 6.0, reason, operator) and prints the rebuild command | TC-055-03 |
| FEAT-055-AC-03 | Next `run-pipeline` is `failed` with `config_changed_requires_rebuild` and the exact `error_message` | TC-055-04 |
| FEAT-055-AC-04 | `rebuild --confirm REBUILD` succeeds, one `pipeline.rebuild` row with old and new hashes; next `run-pipeline` succeeds | TC-055-06 |
| FEAT-055-AC-05 | Unknown key or `cusum_h` = -1 exits 2, `config_parameters` unchanged | TC-055-07 |
| FEAT-055-AC-06 | `APP_ENV=production` seed exits 2 with "seeding is not allowed in production", writes nothing | TC-055-09 |
| FEAT-055-AC-07 | `grep -rn "evaluation_ground_truth\|load_evaluation_ground_truth" backend/cli.py` returns nothing | TC-055-10 |

## Test Data Requirements

- Empty migrated test database; SRC-05 (seed copy `database/seeds/test_v0_1/EchoWell_pipeline_test_input_v0_1.csv`, byte-identical to `tests/fixtures/pipeline_input/`, SHA-256 `78e77faad423f305dfb83429ccd21978f089e843c181b5d244a5d7d4f5fabe28`); roster `database/seeds/test_v0_1/`.
- Environment variables listed in Preconditions; values come from the environment file and are never written into results.
- Integration alternative: `pytest tests/integration/test_cli_pipeline.py -q` (Docker required).

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-055-FR-01 / ARC-066 | FEAT-055 | TC-055-11 |
| FEAT-055-FR-02 / FR-229, SEC-103, D-69 | FEAT-055 | TC-055-03, TC-055-07, TC-055-12 |
| FEAT-055-FR-03 / ANL-032, D-56 | FEAT-055 | TC-055-03, TC-055-08 |
| FEAT-055-FR-04 / ANL-032 | FEAT-055 | TC-055-04 |
| FEAT-055-FR-05 / ANL-032, DB-009, DB-016 | FEAT-055 | TC-055-05, TC-055-06 |
| FEAT-055-FR-06 / DB-058, ING-059, D-68 | FEAT-055 | TC-055-01, TC-055-02 |
| FEAT-055-FR-07 / DB-058, TDV-061 | FEAT-055 | TC-055-01 |
| FEAT-055-FR-08 / DEP-070, DB-059 | FEAT-055 | TC-055-09 |
| FEAT-055-FR-09 / SEC-103 | FEAT-055 | TC-055-03, TC-055-06, TC-055-11 |
| FEAT-055-FR-10 / DB-057, SEC-104 | FEAT-055 | TC-055-11, Database Validation 3 |
| TST-053, TST-188, TST-192, TST-193, TST-194 | FEAT-055 | TC-055-03, TC-055-01, TC-055-03, TC-055-06, TC-055-11 |
| TDV-011 | FEAT-055 | TC-055-10 |
