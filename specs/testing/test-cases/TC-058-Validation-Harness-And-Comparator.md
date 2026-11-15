# Validation harness (Tier A in-process, Tier B database) and comparator

## Feature Description

FEAT-058 builds the infrastructure under `tests/validation/` that runs the pipeline on the reference input DS-01 and compares the output with the answer key DS-02. Tier A runs `analytics.pipeline.run_pipeline` in-process (profile `test_v0_1`, America/Chicago, R01–R10 enrolled 2026-10-01, TRD 10 §4.9 assignments, as-of 2026-10-30 15:00 America/Chicago). Tier B starts from an empty migrated PostgreSQL 16 database, loads the roster, uploads DS-01 through `POST /api/v1/ingest`, starts `POST /api/v1/pipeline/run` with `{"scope": "all", "profile": "test_v0_1", "as_of": "2026-10-30T15:00:00-05:00"}`, waits up to 60 s for `succeeded` and reads results through the API and read-only SELECTs. `tests/validation/comparator.py` matches rows by natural keys (floats within 1e-6, strings exact, blank = null/"", "none" = null), records every mismatch with sheet, key, column, expected, actual, absolute difference and stage (Table 4.5-G), continues after mismatches, and checks Tier A = Tier B. The harness also proves outputs do not change when `evaluation_ground_truth` is loaded and fails the session on any skip, xfail or retry.

## Preconditions

- Repository root; `backend/requirements-dev.txt` installed; Docker available for testcontainers (Tier B).
- Golden files of FEAT-057 present and unmodified (TC-057-01 passes).
- `SEED_*` variables set in the environment (Tier B logs in as admin with `SEED_ADMIN_PASSWORD`).
- For the manual Tier B replay (TC-058-03): migrated empty database, `python -m backend.cli seed test_v0_1 --master-only`, backend API running with `PIPELINE_AS_OF=2026-10-30T15:00:00-05:00` (non-production).

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-058-01 | Tier A reports 0 mismatches against the five answer-key sheets | High | Analytics |
| TC-058-02 | Tier B from an empty database reaches a succeeded explicit-as-of run within 60 s with 0 mismatches | High | Analytics |
| TC-058-03 | Manual replay of the Tier B API path gives the reference values | High | API |
| TC-058-04 | Tier A and Tier B compared values are identical | High | Analytics |
| TC-058-05 | Tolerance boundary: 0.9e-6 passes, 1.1e-6 fails; NaN or missing actual fails | High | Negative |
| TC-058-06 | Injected mismatches are all recorded with sheet, key, column, expected, actual, abs diff and stage | High | Negative |
| TC-058-07 | Blank, "none", case, trimming, yes/no and alarm-string rules | Medium | Negative |
| TC-058-08 | Rows matched by natural keys; missing and extra rows fail | Medium | Negative |
| TC-058-09 | Outputs identical with `evaluation_ground_truth` empty and loaded; static scan passes | High | Security |
| TC-058-10 | A skipped validation test makes `pytest tests/validation -q` exit non-zero | High | Negative |
| TC-058-11 | Comparator mappings are declarative; only DS-01 reaches the pipeline | Medium | Documentation |

### TC-058-01 Tier A reports 0 mismatches against the five answer-key sheets

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/validation/test_harness.py -q -k tier_a_matches` | `test_tier_a_matches_the_answer_key` passes |
| 2 | Review its assertions | Row counts Annotated_sessions 302, Exp_status_counts 10, Exp_resident_outcomes 11, Exp_baselines 180, Exp_scores 98; mismatch list empty |

### TC-058-02 Tier B from an empty database reaches a succeeded explicit-as-of run within 60 s with 0 mismatches

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/validation/test_harness.py -q -k tier_b_matches` | `test_tier_b_matches_the_answer_key` passes |
| 2 | Review its assertions | Explicit-as-of run `status` "succeeded", `as_of` "2026-10-30T20:00:00Z"; mismatches `[]` for the same five sheets |
| 3 | Check the wait logic in `tests/support/system.py` (used by the Tier B fixture) | Polls `GET /api/v1/pipeline/runs/{id}` (no fixed sleep) with a 60 s timeout; a run not `succeeded` within 60 s fails the test with the run's `error_message` and warnings |

Note: on timeout the code raises `run <id> still running after 60.0 s` without the run's `error_message` or warnings (`tests/support/system.py:131-132`).

### TC-058-03 Manual replay of the Tier B API path gives the reference values

| Step | Action | Expected Result |
|---|---|---|
| 1 | `POST /api/v1/auth/login` as `admin@example.com` | 200, access token |
| 2 | `POST /api/v1/ingest` multipart `file` = `tests/fixtures/pipeline_input/EchoWell_pipeline_test_input_v0_1.csv` | 202, `accepted` 283, `rejected` 0, `duplicates` 2, non-null `pipeline_run_id` |
| 3 | Poll `GET /api/v1/pipeline/runs/{pipeline_run_id}` | Batch run `succeeded` |
| 4 | `POST /api/v1/pipeline/run` `{"scope": "all", "profile": "test_v0_1", "as_of": "2026-10-30T15:00:00-05:00"}` | 202 `{"pipeline_run_id": "<uuid>"}` |
| 5 | Poll `GET /api/v1/pipeline/runs/{id}` every 2 s | `succeeded` within 60 s; `as_of` "2026-10-30T20:00:00Z"; `counts` 283/267/12/2/2/17/2/0/98/2/0/10 |
| 6 | `GET /api/v1/analytics` (admin) | `status_totals` usable 267, set_aside 12, quarantined 2, duplicate 2, missing_resident 17, missing_device_gap 2 |
| 7 | `GET /api/v1/analytics/baselines?limit=1`, `GET /api/v1/scores?limit=1`, `GET /api/v1/alerts` | `total` 180, 98 and 2 respectively |
| 8 | `SELECT (SELECT count(*) FROM processed_sessions), (SELECT count(*) FROM day_ledger), (SELECT count(*) FROM epochs);` | 283, 300, 11 |

### TC-058-04 Tier A and Tier B compared values are identical

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/validation/test_harness.py -q -k tier_a_equals_tier_b` | `test_tier_a_equals_tier_b` passes with 0 differences |

### TC-058-05 Tolerance boundary: 0.9e-6 passes, 1.1e-6 fails; NaN or missing actual fails

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/validation/test_comparator.py -q -k "tolerance or nan"` | `test_tolerance_boundary` and `test_nan_or_missing_actual_fails` pass |
| 2 | REPL: `from tests.validation.comparator import compare_value, Column; c = Column("cusum_tally", "float", 8); compare_value("s","k",c,5.0,5.0+0.9e-6), compare_value("s","k",c,5.0,5.0+1.1e-6).abs_diff` | `None` (pass) and ≈ `1.1e-06` (mismatch) |
| 3 | `compare_value("s","k",c,1.0,float("nan")) is not None, compare_value("s","k",c,1.0,None) is not None` | `(True, True)` |

### TC-058-06 Injected mismatches are all recorded with sheet, key, column, expected, actual, abs diff and stage

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/validation/test_comparator.py -q -k "recorded_with_stage or stage_follows"` | Both tests pass |
| 2 | Review `test_mismatches_are_all_recorded_with_stage` | Adding 1.1e-6 to R09-20261021-01 `cusum_tally` and setting R10-20261024-01 `alarm` to "on" gives exactly 2 mismatches; the tally one has sheet `Exp_scores`, key `R09-20261021-01`, column `cusum_tally`, expected 5.431965 ±1e-6, `abs_diff` > 1e-6, stage `8`; the comparison continued to the second |
| 3 | Same test, Exp_baselines | Missing R01 composite row → `(row)` expected "present" actual "absent"; extra R08 row → expected "absent" actual "present" |
| 4 | Review `test_stage_follows_the_status` | A wrong status on R03 day 18 is attributed to stage 2 (quality gate), on R05 day 8 to stage 4 (speaker screen) |

### TC-058-07 Blank, "none", case, trimming, yes/no and alarm-string rules

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/validation/test_comparator.py -q -k blank_none` | `test_blank_none_and_type_rules` passes |
| 2 | Review the assertions | Blank expected = null or ""; "noise above limit" vs "Noise above limit" mismatch (case-sensitive); "x " vs "x" mismatch (no trimming); `first_alarm_session` "none" = null; `floor_applied` "yes" = true; integer 16 vs string "16" mismatch; "RINGS (first crossing)" = "rings" |

### TC-058-08 Rows matched by natural keys; missing and extra rows fail

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `tests/validation/comparator.py` | Keys: Annotated_sessions (resident_id, day, arrival_order); Exp_status_counts resident_id; Exp_resident_outcomes (resident_id, epoch); Exp_baselines (resident_id, epoch, feature); Exp_morning_offset feature; Exp_scores session_id |
| 2 | Evidence from TC-058-06 step 3 | Missing and extra rows reported as `(row)` mismatches |
| 3 | Confirm R04's two duplicates are keyed apart from their originals | `arrival_order` included in the Annotated_sessions key (arrivals 89 and 283 distinct rows) |

### TC-058-09 Outputs identical with `evaluation_ground_truth` empty and loaded; static scan passes

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/validation/test_harness.py -q -k ground_truth_never_changes` | Passes: after loading DS-10 (`SELECT count(*) FROM evaluation_ground_truth` = 10) and a second full run, all compared values, alerts and data alerts equal the run without it |
| 2 | `grep -rn -E "evaluation_ground_truth\|true_onset\|planted_change" analytics backend/services/pipeline_runner.py backend/services/pipeline_persistence.py backend/services/ingestion.py backend/repositories` | No output (TDV-101; `analytics_summary.py` and `database/seeds/` are outside the scan) |

### TC-058-10 A skipped validation test makes `pytest tests/validation -q` exit non-zero

| Step | Action | Expected Result |
|---|---|---|
| 1 | Add `pytest.skip("check")` as the first line of `test_vc_r01_clean_control` in `tests/validation/test_r01_clean_control.py` (local change only) | Edited |
| 2 | `pytest tests/validation -q; echo $?` | Non-zero exit; the session reports the skipped validation test as forbidden |
| 3 | Revert the change and rerun | Exit `0` |
| 4 | Repeat with `@pytest.mark.xfail` on the same test | Non-zero exit |

### TC-058-11 Comparator mappings are declarative; only DS-01 reaches the pipeline

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `tests/validation/comparator.py` | Mapping tables per sheet (Tables 4.5-A..4.5-F) list column, comparison kind (`float`, `exact`, `none_null`, `yesno`, `alarm`) and stage; `TOLERANCE = 1e-6`; `ALARMS` maps off / "RINGS (first crossing)" / on to off / rings / on |
| 2 | Open `tests/validation/conftest.py` | Tier A fixture passes only DS-01 records, the registry and `TEST_V0_1` to `run_pipeline`; the workbook is read only by the comparator |
| 3 | `grep -n "to_excel\|ExcelWriter" tests/validation/*.py` | No write to the golden workbook |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `POST /api/v1/ingest` (admin, CSV) | 202 `IngestBatchAccepted` |
| 2 | `POST /api/v1/pipeline/run` (admin) explicit as-of | 202 `PipelineRunAccepted` |
| 3 | `POST /api/v1/pipeline/run` as researcher | 403 |
| 4 | `GET /api/v1/pipeline/runs/{id}` | 200, `succeeded` within 60 s |
| 5 | `GET /api/v1/analytics`, `/analytics/baselines`, `/scores`, `/alerts`, `/residents` | 200 each; values as TC-058-03 |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT count(*) FROM raw_sessions; SELECT count(*) FROM ingest_rejections;` (Tier B replay) | 283; 0 |
| 2 | `SELECT status, count(*) FROM processed_sessions GROUP BY 1;` | usable 267, set_aside 12, quarantined 2, duplicate 2 |
| 3 | `SELECT status, count(*) FROM day_ledger GROUP BY 1;` | checked_in 281, missing_resident 17, missing_device_gap 2 |
| 4 | `SELECT count(*) FROM baselines; SELECT count(*) FROM scores; SELECT count(*) FROM alerts;` | 180; 98; 2 |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Float differs by 1.1e-6 | Mismatch recorded with stage |
| 2 | NaN or missing actual | Mismatch |
| 3 | Missing or extra row | `(row)` mismatch |
| 4 | Skip, xfail or retry under `tests/validation/` | Session exits non-zero |
| 5 | Tier B run not `succeeded` within 60 s | Test fails showing the run's `error_message` and warnings |
| 6 | Missing sheet or column in the workbook | Test fails naming it (never skipped) |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-058-AC-01 | Tier A 0 mismatches against Annotated_sessions (302), Exp_status_counts (10), Exp_resident_outcomes (11), Exp_baselines (180), Exp_scores (98) | TC-058-01 |
| FEAT-058-AC-02 | Tier B from an empty database: succeeded explicit-as-of run within 60 s, 0 mismatches | TC-058-02, TC-058-03 |
| FEAT-058-AC-03 | Tier A and Tier B compared values identical | TC-058-04 |
| FEAT-058-AC-04 | 1.1e-6 `cusum_tally` mismatch reported with sheet `Exp_scores`, key, column, expected, actual, abs diff, stage 8; second injected mismatch also reported | TC-058-06 |
| FEAT-058-AC-05 | Outputs identical with `evaluation_ground_truth` empty and loaded; TDV-101 scan passes | TC-058-09 |
| FEAT-058-AC-06 | `pytest.skip()` under `tests/validation/` makes `pytest tests/validation -q` exit non-zero | TC-058-10 |

## Test Data Requirements

- DS-01 `tests/fixtures/pipeline_input/EchoWell_pipeline_test_input_v0_1.csv`, DS-02 `tests/fixtures/answer_key/EchoWell_pipeline_test_v0_1.xlsx`, DS-10 `tests/fixtures/answer_key/evaluation_ground_truth_v0_1.csv`; registry `database/seeds/test_v0_1/`.
- Disposable PostgreSQL 16 (testcontainers or local); `SEED_ADMIN_PASSWORD` and other `SEED_*` variables; `PIPELINE_AS_OF` for the manual replay only.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-058-FR-01 / TDV-030, TDV-002, ANL-017 | FEAT-058 | TC-058-01 |
| FEAT-058-FR-02 / TDV-001 | FEAT-058 | TC-058-11 |
| FEAT-058-FR-03 / TDV-031, TST-081, TST-048 | FEAT-058 | TC-058-02, TC-058-03 |
| FEAT-058-FR-04 / TDV-032, D-26 | FEAT-058 | TC-058-05 |
| FEAT-058-FR-05 / TDV-033..TDV-035 | FEAT-058 | TC-058-07 |
| FEAT-058-FR-06 / TDV-036 | FEAT-058 | TC-058-08 |
| FEAT-058-FR-07 / TDV-037 | FEAT-058 | TC-058-06 |
| FEAT-058-FR-08 / TDV-038, TDV-015 | FEAT-058 | TC-058-11 |
| FEAT-058-FR-09 / TDV-040, DME-016 | FEAT-058 | TC-058-11 |
| FEAT-058-FR-10 / TDV-041, TDV-042, ANL-042 | FEAT-058 | TC-058-07, TC-058-11 |
| FEAT-058-FR-11 / DME-017 | FEAT-058 | TC-058-01, TC-058-06 step 4 |
| FEAT-058-FR-12 / TST-081 | FEAT-058 | TC-058-04 |
| FEAT-058-FR-13 / TDV-101, TDV-102 | FEAT-058 | TC-058-09 |
| FEAT-058-FR-14 / TST-083 | FEAT-058 | TC-058-10 |
| FEAT-058-FR-15 / FR-031 | FEAT-058 | TC-052-04 (VC-R04-INV reduced-input run) |
| TST-080, TST-012 | FEAT-058 | TC-058-01, TC-058-10 |
| AC-ANL-01, AC-TDV-12 | FEAT-058 | TC-058-01, TC-058-09 |
