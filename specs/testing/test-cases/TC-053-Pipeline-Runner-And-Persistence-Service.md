# Pipeline runner and persistence service

## Feature Description

`backend/services/pipeline_runner.py` (FEAT-053) is the only backend caller of `analytics.run_pipeline`. A run inserts and commits a `pipeline_runs` row (`status` `running`, trigger, scope, `config_profile`, `config_snapshot` with the 23 keys plus `config_hash` and `as_of`, `code_version` = `GIT_SHA`), writes audit `pipeline.run.started`, loads `raw_sessions` (typed columns), residents, all facility `device_assignments` and persisted baselines (`frozen_baselines`), calls the engine, then writes each resident in its own transaction under `pg_advisory_xact_lock(advisory_key('resident', code))`: delete+insert `processed_sessions`, `scores`, `cusum_state`, `day_ledger`; upsert `epochs`; insert-only `baselines`; natural-key upsert/close of `alerts`; reconcile resident data alerts; cohort change for new admissions. `device_silent` data alerts are reconciled at the end under `advisory_key('device_alerts', 'all')`. The run ends `succeeded` or `failed` with `counts`, `warnings`, `error_message` and audit `pipeline.run.finished`. Reviews, notes, snoozes and frozen baselines survive any number of re-runs.

## Preconditions

- Local development stack with PostgreSQL 16; migrated database seeded with `python -m backend.cli seed test_v0_1` (DS-07; run trigger `manual`, as-of 2026-10-30T20:00:00Z).
- Backend API running for the API steps; tokens from `POST /api/v1/auth/login` with the `SEED_*` passwords.
- `psql` sessions: one with `DATABASE_URL` (role `echowell_app`) and one read-only for checks.
- Integration-test cases need Docker for testcontainers (`pytest tests/integration -q -k pipeline`).
- Second-run command used below: `python -m backend.cli run-pipeline --scope all --as-of 2026-10-30T15:00:00-05:00`.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-053-01 | SRC-05 run row: counts 283/267/12/2/2/17/2/0/98/2/0/10, config snapshot 23 keys + `config_hash` + `as_of` | High | Database |
| TC-053-02 | Derived tables after the SRC-05 run match the engine output | High | Database |
| TC-053-03 | `alerts` holds exactly R09 and R10 open; `data_alerts` the four open rows | High | Database |
| TC-053-04 | Two consecutive full runs leave derived tables identical | High | Database |
| TC-053-05 | Re-run keeps R09 alert id, review, `acknowledged` and `snoozed_until` | High | Positive |
| TC-053-06 | Failing write for R05 rolls back R05 only; run `failed` naming R05 | High | Negative |
| TC-053-07 | Late record inside R01's baseline window leaves baselines byte-identical with a `late_arrival` warning | High | Analytics |
| TC-053-08 | `echowell_app` cannot read `evaluation_ground_truth`; runner never references it | High | Security |
| TC-053-09 | Data-alert reconciliation: one open row, `last_detected_at` moves, resolved when the rule stops | High | Database |
| TC-053-10 | N01 moves from `new_admission` to `longitudinal` with one `resident.cohort_changed` audit row | High | Positive |
| TC-053-11 | Non-closed alert no longer produced is closed `superseded by rebuild` with audit `alert.closed` | Medium | Database |
| TC-053-12 | Audit rows `pipeline.run.started` / `pipeline.run.finished` and the run lifecycle | Medium | Database |
| TC-053-13 | Invariants: status counts sum to arrivals; ledger statuses sum to ledger days | Medium | Database |
| TC-053-14 | Run rows are readable through `GET /api/v1/pipeline/runs` and `/{id}` | Medium | API |

### TC-053-01 SRC-05 run row: counts 283/267/12/2/2/17/2/0/98/2/0/10, config snapshot 23 keys + `config_hash` + `as_of`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT trigger, status, scope, config_profile, code_version, as_of, finished_at IS NOT NULL AS done, error_message FROM pipeline_runs ORDER BY started_at DESC LIMIT 1;` | `manual`, `succeeded`, `{"type": "all"}`, `test_v0_1`, value of `GIT_SHA` (or `unknown`), `2026-10-30 20:00:00+00`, `t`, NULL |
| 2 | `SELECT counts FROM pipeline_runs ORDER BY started_at DESC LIMIT 1;` | `{"arrivals": 283, "usable": 267, "set_aside": 12, "quarantined": 2, "duplicate": 2, "missing_resident": 17, "missing_device_gap": 2, "late_arrival": 0, "scored": 98, "alerts_opened": 2, "excluded_after_as_of": 0, "residents": 10}` |
| 3 | `SELECT (SELECT count(*) FROM jsonb_object_keys(config_snapshot)), config_snapshot->>'config_hash', config_snapshot->>'as_of' FROM pipeline_runs ORDER BY started_at DESC LIMIT 1;` | `25` keys (23 + 2); 64-hex `config_hash`; `as_of` `2026-10-30T20:00:00+00:00` |
| 4 | `SELECT warnings FROM pipeline_runs ORDER BY started_at DESC LIMIT 1;` | `[]` |

### TC-053-02 Derived tables after the SRC-05 run match the engine output

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT (SELECT count(*) FROM processed_sessions), (SELECT count(*) FROM raw_sessions), (SELECT count(*) FROM baselines), (SELECT count(*) FROM scores), (SELECT count(*) FROM day_ledger), (SELECT count(*) FROM epochs), (SELECT count(*) FROM cusum_state);` | 283, 283, 180, 98, 300, 11, one `cusum_state` row per resident-epoch |
| 2 | `SELECT status, count(*) FROM processed_sessions GROUP BY 1 ORDER BY 1;` | duplicate 2, quarantined 2, set_aside 12, usable 267 |
| 3 | `SELECT alarm_state, count(*) FROM scores GROUP BY 1 ORDER BY 1;` | off 81, on 15, rings 2 |
| 4 | `SELECT p.session_id, s.cusum_tally FROM scores s JOIN processed_sessions p ON p.id = s.processed_session_id WHERE p.session_id IN ('R09-20261021-01','R10-20261024-01');` | R09 5.431965 ±1e-6, R10 5.972050 ±1e-6 (stored as `double precision`, unrounded) |
| 5 | `SELECT count(*) FROM baselines WHERE feature_key = 'composite';` | `9` (one per formed resident-epoch) |

### TC-053-03 `alerts` holds exactly R09 and R10 open; `data_alerts` the four open rows

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT session_id, local_date, status FROM alerts ORDER BY session_id;` | `R09-20261021-01` 2026-10-21 `open`; `R10-20261024-01` 2026-10-24 `open` |
| 2 | `SELECT title, status, first_detected_at FROM data_alerts ORDER BY title;` | "D02 · device silent all day", "R03 · many check-ins set aside", "R05 · possible other speaker", "R08 · baseline stuck at 13 of 16"; all `open`; `first_detected_at` `2026-10-30 20:00:00+00` |

### TC-053-04 Two consecutive full runs leave derived tables identical

| Step | Action | Expected Result |
|---|---|---|
| 1 | Save a snapshot: `\copy (SELECT session_id, status, reasons, reason_text FROM processed_sessions ORDER BY session_id, timestamp_utc) TO '/tmp/ps1.csv' CSV`; repeat for `scores` (`session`, z, composite_raw, composite_z, cusum_tally, alarm_state), `day_ledger`, `epochs`, `baselines`; note `SELECT id FROM alerts ORDER BY session_id;` | Files written |
| 2 | Run the second-run command | Prints `Pipeline run <uuid> succeeded.`; exit 0 |
| 3 | Repeat the snapshot into `*2.csv` files and `diff` each pair | No difference on any column except `id`, `created_at`, `updated_at`, `pipeline_run_id` (excluded from the export) |
| 4 | Row counts of `alerts`, `epochs`, `day_ledger` and alert ids | Unchanged (2, 11, 300); same two alert ids |
| 5 | `pytest tests/integration/pipeline/test_runner_persistence.py -q -k second_run` | `test_second_run_changes_nothing` passes |

### TC-053-05 Re-run keeps R09 alert id, review, `acknowledged` and `snoozed_until`

Run on a disposable copy of DS-07.

| Step | Action | Expected Result |
|---|---|---|
| 1 | Clinician: `GET /api/v1/alerts?resident_code=R09`; note `id` | 200, 1 item, `status` `open` |
| 2 | `POST /api/v1/alerts/{id}/reviews` `{"explanations": [], "outcome": "no_concern"}` then `POST /api/v1/alerts/{id}/snooze` `{"hours": 24}` | 201, then 200 with `snoozed_until` set |
| 3 | Run the second-run command | `succeeded` |
| 4 | `SELECT id, status, snoozed_until, acknowledged_by IS NOT NULL FROM alerts WHERE session_id='R09-20261021-01';` | Same `id` as step 1; `acknowledged`; `snoozed_until` unchanged; `t` |
| 5 | `SELECT count(*) FROM alert_reviews WHERE alert_id = '<id>';` | `1` |
| 6 | `pytest tests/integration/pipeline/test_runner_persistence.py -q -k reviews_and_snooze` | Passes |

### TC-053-06 Failing write for R05 rolls back R05 only; run `failed` naming R05

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/integration/pipeline/test_runner_persistence.py -q -k failing_resident` | `test_a_failing_resident_is_rolled_back_alone` passes |
| 2 | Review its assertions: run row | `status` `failed`; `error_message` `failed residents: R05`; `warnings` contains `{"code": "exception", "resident_code": "R05", "session_id": null, "detail": "persistence: <ExceptionType>: ..."}` |
| 3 | R05 rows | R05's previously persisted `processed_sessions`, `scores`, `day_ledger` unchanged; the other nine residents updated by the run |

Note: FEAT-056-FR-03 names the stage in `detail` ("<stage name>: …"); the code writes `persistence:` for write failures (`backend/services/pipeline_runner.py:397`).

### TC-053-07 Late record inside R01's baseline window leaves baselines byte-identical with a `late_arrival` warning

| Step | Action | Expected Result |
|---|---|---|
| 1 | `\copy (SELECT feature_key, median, mad, robust_spread, floor_applied, frozen_at FROM baselines b JOIN residents r ON r.id=b.resident_id WHERE r.resident_code='R01' ORDER BY feature_key) TO '/tmp/r01_before.csv' CSV` | 20 rows exported |
| 2 | `pytest tests/integration/pipeline/test_runner_persistence.py -q -k late_record` | `test_late_record_keeps_frozen_baselines` passes: a record dated inside R01's baseline window (first 16 usable days, Oct 1–16) is ingested and the run re-executed |
| 3 | In the test's assertions | R01 `baselines` rows identical on every value column; run `warnings` contains a `late_arrival` item for R01 |

### TC-053-08 `echowell_app` cannot read `evaluation_ground_truth`; runner never references it

| Step | Action | Expected Result |
|---|---|---|
| 1 | `psql "$DATABASE_URL" -c "SELECT * FROM evaluation_ground_truth"` | `ERROR: permission denied for table evaluation_ground_truth` |
| 2 | `grep -n "evaluation_ground_truth\|true_onset\|planted_change" backend/services/pipeline_runner.py backend/services/pipeline_persistence.py` | No output |
| 3 | `pytest tests/integration/pipeline/test_runner_persistence.py -q -k answer_key` | `test_runner_never_reads_the_answer_key` passes |

### TC-053-09 Data-alert reconciliation: one open row, `last_detected_at` moves, resolved when the rule stops

| Step | Action | Expected Result |
|---|---|---|
| 1 | Note `SELECT id, first_detected_at, last_detected_at FROM data_alerts WHERE title='R05 · possible other speaker';` | One `open` row, both timestamps `2026-10-30 20:00:00+00` |
| 2 | `python -m backend.cli run-pipeline --scope all --as-of 2026-10-30T16:00:00-05:00` (one hour later) | `succeeded` |
| 3 | Repeat step 1 | Same `id`, still 1 row, `first_detected_at` unchanged, `last_detected_at` `2026-10-30 21:00:00+00` |
| 4 | `pytest tests/integration/pipeline/test_runner_persistence.py -q -k data_alert_history` | `test_data_alert_history_and_resolution` passes (condition gone → `resolved`, `resolved_at` = run as-of, row never reopened) |
| 5 | `SELECT count(*) FROM data_alerts WHERE kind = 'review_flagged_data_problem' AND pipeline_run_id IS NOT NULL;` | `0` (runs never modify review-flagged rows) |

### TC-053-10 N01 moves from `new_admission` to `longitudinal` with one `resident.cohort_changed` audit row

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/integration/api/test_admissions.py -q -k "moves_to_the_resident_list or cohort_change"` | Both tests pass |
| 2 | In the test: N01 (cohort `new_admission`, own device) with 15 usable records | Listed by `GET /api/v1/admissions`, absent from `GET /api/v1/residents` |
| 3 | 16th usable record ingested; its run freezes the baseline | `residents.cohort` = `longitudinal`; exactly one `audit_logs` row `resident.cohort_changed` with `details` `{"from": "new_admission", "to": "longitudinal", "epoch_number": 1}` |

### TC-053-11 Non-closed alert no longer produced is closed `superseded by rebuild` with audit `alert.closed`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/integration/pipeline/test_runner_persistence.py -q -k supersedes` | `test_rebuild_without_the_first_crossing_supersedes_the_alert` passes |
| 2 | In the test's assertions | Alert row kept (no DELETE), `status` `closed`, `closed_reason` `superseded by rebuild`, `closed_at` = run as-of; one `alert.closed` audit row |

### TC-053-12 Audit rows `pipeline.run.started` / `pipeline.run.finished` and the run lifecycle

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT action, actor_type, entity_id, details FROM audit_logs WHERE entity_type='pipeline_run' ORDER BY occurred_at DESC LIMIT 2;` | `pipeline.run.finished` (details `status` `succeeded`, `duration_ms`, `warning_count` 0) and `pipeline.run.started` (details `trigger`, `scope`, `profile`), same `entity_id` = latest run id, `actor_type` `system` |
| 2 | Inspect `details` of both | No feature value, password or connection string |

### TC-053-13 Invariants: status counts sum to arrivals; ledger statuses sum to ledger days

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT r.resident_code, count(*) FILTER (WHERE p.status IN ('usable','set_aside','quarantined','duplicate')) AS statuses, (SELECT count(*) FROM raw_sessions s WHERE s.resident_id=r.id) AS arrivals FROM residents r JOIN processed_sessions p ON p.resident_id=r.id GROUP BY r.id, r.resident_code ORDER BY 1;` | `statuses` = `arrivals` for each resident (R04: 32 = 32; R08: 18 = 18) |
| 2 | `SELECT count(*) FROM day_ledger WHERE status IN ('checked_in','missing_resident','missing_device_gap');` | `300` = total ledger rows |

### TC-053-14 Run rows are readable through `GET /api/v1/pipeline/runs` and `/{id}`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Admin: `GET /api/v1/pipeline/runs?trigger=manual&status=succeeded` | 200 `PipelineRunList`, newest first; first item `config_profile` `test_v0_1`, `scope` "all", `as_of` "2026-10-30T20:00:00Z", `counts` as TC-053-01 |
| 2 | `GET /api/v1/pipeline/runs/{id}` with that id | 200 `PipelineRun` with the same values and `warnings` [] |
| 3 | `GET /api/v1/pipeline/runs/00000000-0000-0000-0000-000000000000` | 404 `PIPELINE_RUN_NOT_FOUND` |
| 4 | Clinician: `GET /api/v1/pipeline/runs` | 403 |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `POST /api/v1/pipeline/run` (admin) `{"scope": "all", "profile": "test_v0_1", "as_of": "2026-10-30T20:00:00Z"}` | 202 `{"pipeline_run_id": "<uuid>"}` |
| 2 | Poll `GET /api/v1/pipeline/runs/{id}` | `status` reaches `succeeded`; `counts` as TC-053-01 |
| 3 | `POST /api/v1/pipeline/run` with `{"scope": ["R99"], ...}` | 404 `RESIDENT_NOT_FOUND` |
| 4 | Start a full run while another full run is `running` | 409 `PIPELINE_RUN_IN_PROGRESS` |
| 5 | `GET /api/v1/alerts?status=open` | R09 and R10 only, ids equal to `alerts.id` |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT count(*) FROM raw_sessions;` before and after any run | 283 both times (raw store never modified) |
| 2 | `SELECT count(*) FROM baselines;` after the second run | 180 (insert-only, no duplicates) |
| 3 | `SELECT resident_id, epoch_number, count(*) FROM epochs GROUP BY 1,2 HAVING count(*)>1;` | 0 rows |
| 4 | `SELECT epoch_id, session_id, count(*) FROM alerts GROUP BY 1,2 HAVING count(*)>1;` | 0 rows |
| 5 | As `echowell_app`: `DELETE FROM alerts WHERE false;` | `permission denied for table alerts` (no DELETE grant) |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Resident-level write failure (TC-053-06) | That resident rolled back, others committed, run `failed`, `exception` warning |
| 2 | Invalid stored configuration (e.g. a value violating its schema) then a run | Run `failed`, `error_message` starts `invalid configuration:`, warning `pipeline_config_invalid`; no derived writes |
| 3 | `SELECT * FROM evaluation_ground_truth` as `echowell_app` | Permission denied |
| 4 | Epoch renumbering of a frozen epoch | Resident's derived rows unchanged; warning `late_arrival` with detail `epoch renumbering blocked`; run continues |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-053-AC-01 | `counts` 283/267/12/2/2/17/2/0/98/2/0/10; `config_snapshot` 23 keys + `config_hash` + `as_of` | TC-053-01 |
| FEAT-053-AC-02 | Two runs leave derived tables identical except id/timestamps/run id; alert, epoch, ledger counts unchanged | TC-053-04 |
| FEAT-053-AC-03 | Rebuild keeps R09 alert id, reviews, `acknowledged`, `snoozed_until` | TC-053-05 |
| FEAT-053-AC-04 | Failing R05 write: R05 unchanged, others updated, run `failed` with `exception` warning and `error_message` naming R05 | TC-053-06 |
| FEAT-053-AC-05 | `alerts` exactly R09 and R10 open; `data_alerts` the four open rows with `first_detected_at` 2026-10-30T20:00:00Z | TC-053-03 |
| FEAT-053-AC-06 | `echowell_app` SELECT on `evaluation_ground_truth` fails; runner has no reference | TC-053-08 |
| FEAT-053-AC-07 | Late record in R01's baseline window: baselines byte-identical, `late_arrival` warning | TC-053-07 |
| FEAT-053-AC-08 | N01 moves to `longitudinal` with one `resident.cohort_changed` audit row | TC-053-10 |

## Test Data Requirements

- DS-07 (seed `test_v0_1`), a disposable copy for TC-053-05; synthetic fixture N01 (integration test only).
- Environment: `DATABASE_URL` (`echowell_app`), `DATABASE_MIGRATION_URL`, `GIT_SHA`, `PIPELINE_PROFILE=test_v0_1`, `FACILITY_TZ=America/Chicago`, `SEED_*` passwords.
- Docker for testcontainers integration tests.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-053-FR-01 / ANL-033, DB-020, API-063 | FEAT-053 | TC-053-01, TC-053-12 |
| FEAT-053-FR-02 / ANL-016, ANL-037 | FEAT-053 | TC-053-02, TC-053-07 |
| FEAT-053-FR-03 / ANL-035 | FEAT-053 | TC-053-02 |
| FEAT-053-FR-04 / ANL-034, DB-021, API-064 | FEAT-053 | TC-053-06 |
| FEAT-053-FR-05 / ANL-036, DB-014, FR-094, FR-105 | FEAT-053 | TC-053-02, TC-053-04 |
| FEAT-053-FR-06 / NFR-120, NFR-126 | FEAT-053 | TC-053-05, Database Validation 1, 5 |
| FEAT-053-FR-07 / ANL-038, DB-015, DB-017, FR-051 | FEAT-053 | Database Validation 3, Negative 4 |
| FEAT-053-FR-08 / ANL-037, DB-016, NFR-124 | FEAT-053 | TC-053-07, Database Validation 2 |
| FEAT-053-FR-09 / ANL-039, DB-018, API-128, FR-110 | FEAT-053 | TC-053-05, TC-053-11 |
| FEAT-053-FR-10 / ANL-060, DB-036, FR-296 | FEAT-053 | TC-053-03, TC-053-09 |
| FEAT-053-FR-11 / DB-021 (c) | FEAT-053 | TC-053-09 |
| FEAT-053-FR-12 / DB-025, FR-205 | FEAT-053 | TC-053-10 |
| FEAT-053-FR-13 / ANL-041, DB-013 | FEAT-053 | TC-053-06 |
| FEAT-053-FR-14 / ANL-040, LOG-061 | FEAT-053 | TC-053-01, TC-053-06, TC-053-12 |
| FEAT-053-FR-15 / DB-022, NFR-129 | FEAT-053 | Database Validation 1 |
| FEAT-053-FR-16 / ANL-042, NFR-032 | FEAT-053 | TC-053-02 |
| FEAT-053-FR-17 / DB-019, ANL-023, AGT-056 | FEAT-053 | TC-053-04 |
| FEAT-053-FR-18 / ANL-064, AGT-057 | FEAT-053 | TC-053-08 |
| FEAT-053-FR-19 / NFR-125 | FEAT-053 | TC-053-13 |
| TST-050, TST-051, TST-067, TST-068, TST-185, AL-04, DA-11 | FEAT-053 | TC-053-04, TC-053-01, TC-053-05, TC-053-08, TC-053-10, TC-053-05, TC-053-09 |
| TST-041, TDV-101, TDV-102 | FEAT-053 | TC-053-08 |
| VC-G12 | FEAT-053 | TC-053-04 |
