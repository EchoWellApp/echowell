# Checkpoint 6 Report — Phase 12 Pass R01-R10 Validation Tests

Block 3 "Implement Features", checkpoint 6 of 9, its own PR (branch `feat/cp6-validation`, created from `main` after GitHub PR #20 was merged on 1 November 2026) · Prompt: `specs/prompts/Implement_Feature_Batches.md` "Phase 12: Pass R01-R10 Validation Tests" · TRD 25 Phase 7 · Features: FEAT-057..FEAT-061 · Date: 2 November 2026 · Status: in review (GitHub PR #22); review round 1 answered and applied, section 10.

Build order followed roadmap §5.6: [FEAT-057, FEAT-058, FEAT-059] → [FEAT-060, FEAT-061]. TRDs read in the roadmap order: 13, 14, 08, 09, then the SRC-03 Exp_ sheets.

Everything here runs on the synthetic test data (SRC-05 input, SRC-03 answer key). The answer key is read only under `tests/` and by the test-only ground-truth loader; no pipeline code reads it (AGT-007).

## 1. Result

**Overall: PASS.** All 22 validation cases (VC-R01..VC-R10, VC-G01..VC-G12) pass in Tier A (the engine in-process) and Tier B (the full system on PostgreSQL 16, data ingested through the API). Both gating supplementary checks (VC-R04-INV, VC-R10-FRZ) pass. `docs/reports/ALGORITHM_VALIDATION_REPORT.md` reads "Overall: PASS" (AC-TST-03).

| Measure | Value |
|---|---|
| Value comparisons against the answer key | about 14,500 per tier, 0 mismatches (302 annotated rows, 10 status counts, 11 outcomes, 180 baselines, 19 morning offsets, 98 scores) |
| Tier A vs Tier B | about 14,300 compared values, identical |
| Status totals | usable 267, set aside 12, quarantined 2, duplicate 2, missing resident 17, device gap 2 |
| Alerts | exactly R09 (R09-20261021-01, tally 5.431965) and R10 (R10-20261024-01, 5.972050), both open |
| Ground truth loaded vs empty | identical outputs, alerts and data alerts (TDV-102) |
| DS-07 page values | Resident list, chart, devices, alarms, data alerts and Study team figures equal TRD 14 §4.9; Table 4.9-E also recomputed from the workbook |
| False-alarm robustness (informational) | 61 of 600 no-change resident-runs over seeds 1..100 = 10.2 %, exactly the TRD 09 §4.6 reference; every seed reproduced its own answer key (0 mismatches) |

Because this suite passes, checkpoint 7 (frontend) may start once this PR is merged and `pytest tests/validation -q` passes on `main` (AGT-023).

## 2. What was built

| Group | Feature | Delivered |
|---|---|---|
| 1 | FEAT-057 | Golden fixtures in `tests/fixtures/answer_key/` (workbook copy, `SHA256SUMS`, DS-10 `evaluation_ground_truth_v0_1.csv`); integrity tests (byte identity, checksums, regeneration with seed 20261004 run as `python -I`, DS-10 vs Test_plan, input-folder contents, separation scan, legacy fixture use); `python -m tests.validation.diff_answer_key`; `database/seeds/load_evaluation_ground_truth.py` |
| 2 | FEAT-058 | `outputs.py` (both tiers in the answer-key shape), `comparator.py` (Tables 4.5-A..4.5-F as declarative mappings, stage attribution), `tier_b.py` (throwaway database, `seed --master-only`, CSV upload, explicit-as-of run, API and read-only SELECTs), `guard.py` (no skip, xfail or retry under `tests/validation/`) |
| 3 | FEAT-059 | Ten case modules `test_r01_clean_control.py` … `test_r10_gradual_drift.py`, `test_global_checks.py`, `test_invariance.py` (VC-R04-INV, VC-R10-FRZ, VC-R06-MUT), `report.py` (Markdown report and JSON after every validation session); CI uploads both even on failure and shows the pass/fail table in the job summary |
| 4 | FEAT-060, FEAT-061 | `tests/integration/api/test_ui_fixture_ds07.py` (DS-07 built as CI builds it; after-review check on its own copy), `tests/validation/test_ui_fixture_recompute.py` (TDV-075), `tests/validation/robustness.py` (informational, not collected by the gating suite) |

## 3. Defects found and fixed

The validation suite found two problems in code from earlier checkpoints. Both are fixed in code; no expected value was changed (AGT-008, TST-162).

| # | Found by | Problem | Root cause | Fix |
|---|---|---|---|---|
| F-1 | Tier B, the TDV-031 sequence | Upload DS-01, which starts a run at the current time (2 Nov), then run explicitly at the test as-of (30 Oct): the second run failed with `data_alerts_detected_ck`. | Re-detecting an open data alert set `last_detected_at` to the earlier as-of, before `first_detected_at`. Stage 11 (data alerts), persistence only. | After review round 1 (section 10, D-135): `first_detected_at` is never rewritten and `last_detected_at` only moves forward, so such a run succeeds without rewriting history; Tier B sets PIPELINE_AS_OF to the test as-of, so the ingest-triggered run already evaluates 30 Oct. Regression test `test_a_run_at_an_earlier_as_of_keeps_alert_history`. |
| F-2 | VC-R10-FRZ (c) | Runs started through the API read `datetime.now()` directly, not the application clock, so the clock could not be set consistently (D-131, from the checkpoint 5 review). | `get_pipeline_runner` built the runner without `get_clock`. | The runner now takes the application clock (`backend/api/deps.py`). |

## 4. Files

**Created:**
- `tests/fixtures/answer_key/EchoWell_pipeline_test_v0_1.xlsx`, `SHA256SUMS` and `evaluation_ground_truth_v0_1.csv`;
- `database/seeds/load_evaluation_ground_truth.py`;
- `tests/support/system.py` (the full-system builder, moved there in review round 1);
- `tests/validation/`: `answer_key.py`, `outputs.py`, `comparator.py`, `tier_b.py`, `guard.py`, `conftest.py`, `cases.py`, `report.py`, `diff_answer_key.py`, `robustness.py` and 18 test modules;
- `tests/integration/api/test_ui_fixture_ds07.py`;
- `tests/integration/db/test_ground_truth_loader.py`;
- `docs/reports/ALGORITHM_VALIDATION_REPORT.md` and `docs/reports/validation_results.json`;
- this report.

**Changed:**
- `backend/services/pipeline_persistence.py` (F-1) and `backend/api/deps.py` (F-2);
- `tests/integration/pipeline/test_runner_persistence.py` (regression test for F-1);
- `.github/workflows/ci.yml` (report artifact and job summary);
- `BACKLOG.md` §10, roadmap §2.1, the FEAT-057..FEAT-061 Status fields.

**Size:** about 4,200 added lines.
- About 380 are copied data and generated reports.
- About 3,800 are tests, mostly the validation harness and cases.
- About 130 are application code: the loader, the two fixes and the CI steps.

## 5. Commands run and results

Environment: Linux container, Python 3.12 (virtualenv), PostgreSQL 16 (local cluster provisioned with `database/roles/provision_login_roles.sql`).

| # | Command | Result |
|---|---|---|
| 1 | `pytest tests/unit tests/integration tests/contract tests/security tests/validation`, random order, with coverage | 648 passed, 0 skipped (5 min 41 s); coverage of `analytics` and `backend` together 97 % |
| 2 | `pytest tests/validation -q` | 70 passed, 0 skipped (about 20 s); report "Overall: PASS", 22 of 22 cases in both tiers |
| 3 | `pytest tests/validation -q -k integrity` | 7 passed |
| 4 | `pytest tests/integration -q -k ui_fixture` | 10 passed |
| 5 | `python -m tests.validation.robustness --seeds 100` | 61 false alarms of 600 (10.2 %); per resident R01 14, R02 7, R03 8, R04 8, R05 13, R06 11, R07 0, R08 0; 0 reproduction mismatches |
| 6 | `sha256sum` of the fixture workbook and CSV | `ddbc03ea…482257` and `78e77faa…fabe28`, equal to TDV-013 |
| 7 | `grep -rn "pipeline_test_v0_1.xlsx" analytics backend` | no match (AGT-007) |
| 8 | `ruff check .`; `ruff format --check .`; `mypy analytics backend`; `lint-imports` | all exit 0 |

## 6. Exit criteria (roadmap §5.6)

| Criterion | Evidence | Result |
|---|---|---|
| All R01–R10 tests pass with zero failures and zero skips; the report reads "Overall: PASS" (AC-TST-03) | item 2; the guard fails the session on any skip, xfail or retry (`test_a_skipped_validation_test_fails_the_session`) | PASS |
| Totals 267/12/2/2/17/2; numbers within 1e-6, strings exact; R04 identical without the two copies | VC-G01, the comparator, VC-R04-INV | PASS |
| Answer-key integrity and isolation (TDV-013, TDV-014, TST-068) | `test_answer_key_integrity.py`, `test_ground_truth_never_changes_the_outputs`, `test_ground_truth_loader.py` | PASS |
| DS-07 UI fixture checks (TDV-061..TDV-076) | item 4, TDV-075 recomputation | PASS |
| FEAT-061 informational, never gating (TDV-083) | `robustness.py` is not a `test_*` module; it always exits 0 | PASS |
| `pytest tests/validation -q` passes on the PR head and on `main` after merge (AC-AGT-04) | CI on the PR, then on `main` | PENDING |
| Algorithm lead approves and merges (D-101) | review | PENDING |

## 7. New OQ and D IDs

None. Decisions from this review will be recorded in TRD 24 from D-135.

## 8. Notes

| # | Note |
|---|---|
| N-1 | Tier B and DS-07 each build their own throwaway database. CI therefore runs the full system twice more, plus the 30-record incremental ingestion of VC-R10-FRZ (c); together that adds about 20 seconds. |
| N-2 | The `PipelineRun` response has no `config_snapshot`, so VC-G08 reads the snapshot from the `pipeline_runs` row, as TRD 14 Table 4.5-E allows ("the `config_snapshot` of the validation `pipeline_runs` row"). |
| N-3 | Before review round 1, the TDV-031 sequence left 8 resolved `device_silent` alerts from the run at the current time. With PIPELINE_AS_OF set (D-135) Tier B no longer creates them; where an earlier run does, they are kept as history (D-138). |
| N-4 | Capturing the frontend MSW fixtures from DS-07 (`npm run fixtures:capture`) is FEAT-062 (checkpoint 7); the DS-07 assertions here are the values those fixtures must hold. |

## 9. Questions for the reviewer

| ID | Question |
|---|---|
| Q-1 | F-1: when a run at an earlier as-of re-detects an open data alert, `first_detected_at` moves back to that as-of. Agree, or should the TDV-031 procedure set `PIPELINE_AS_OF` so the ingest-triggered run already uses 30 Oct? |
| Q-2 | N-3: the 8 resolved `device_silent` alerts from the run at the current time stay in the table (resolved rows are never deleted). Acceptable for the test procedure? |
| Q-3 | F-2: API-started pipeline runs now use the application clock, completing D-131. Agree? |
| Q-4 | VC-R10-FRZ (c) and TDV-061 ask for `time-machine`. I set the application clock instead, because time-machine breaks psycopg connections (checkpoint 4 note N-2). Update TDV-061 and FEAT-059-FR-10 to say "freeze the application clock"? |
| Q-5 | The report files are rewritten after every validation session, including partial selections such as `-k r09`, where the cases that did not run show FAIL. CI always runs the full suite. Keep that, or write the files only when all 22 cases ran? |
| Q-6 | The robustness figures come from a local 100-seed run. Wiring the script into the nightly `nightly-validation` job is FEAT-080 (checkpoint 8). Agree? |
| Q-7 | The DS-07 builder lives in `tests/validation/tier_b.py` and is imported by the integration test. Keep it there, or move the shared test helpers to a `tests/support/` module? |
| Q-8 | Size: about 3,900 hand-written lines, almost all tests, for 5 features. Accept as one PR? |

## 10. Review round 1 resolutions (2 November 2026)

Shaba's review of GitHub PR #22 (changes requested). Decisions recorded in TRD 24 as D-135 to D-139.

| Q | Answer | Change | Documents |
|---|---|---|---|
| Q-1 | Set PIPELINE_AS_OF in TDV-031 instead of moving `first_detected_at` back; keep it a stable historical fact. | `first_detected_at` is no longer rewritten. `last_detected_at` only moves forward, so a run at an earlier as-of still succeeds instead of failing the database check. Tier B sets PIPELINE_AS_OF to the test as-of, so the ingest-triggered run already evaluates 30 Oct (D-135). | TRD 14 TDV-031 (v0.13), TRD 23 (v0.14), FEAT-058-FR-03 |
| Q-2 | Acceptable; resolved alerts are history. | No change (D-138). With PIPELINE_AS_OF, Tier B no longer creates them. | — |
| Q-3 | Agree. | No change. | — |
| Q-4 | Freeze the application clock; update the wording. | TDV-061, §4.7.10 VC-R10-FRZ (c) and FEAT-059-FR-10 say "freeze the application clock" (D-136). | TRD 14 (v0.13), FEAT-058, FEAT-059 |
| Q-5 | Write the canonical report only on full-suite runs. | `report.complete` checks that every case ran in its tiers and every supplementary check ran; otherwise the session prints a note and leaves both files alone. New test `test_only_a_full_session_is_complete` (D-137). | TRD 14 TDV-073 (v0.13) |
| Q-6 | Agree. | No change (D-138). | — |
| Q-7 | Move the builder to `tests/support/`. | `tests/support/system.py` holds the throwaway database, operator commands, API client, `tier_b()` and `ds07()`; `tests/validation/tier_b.py` keeps only the answer-key collection (D-139). | — |
| Q-8 | One PR is fine. | No change (D-138). | — |

Verification after review round 1:

- ruff, mypy and lint-imports are clean.
- `pytest tests/validation -q`: 71 passed, and the report still reads "Overall: PASS".
- A partial run (`-k r09`) leaves the report files byte-identical.
- Full suite, random order: 649 passed, 0 skipped.

