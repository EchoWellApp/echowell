# False-alarm robustness check (informational, not gating)

## Feature Description

`tests/validation/robustness.py` regenerates the synthetic `test_v0_1` input data for seeds 1..100 with the reference generator (`specs/algorithm/generate_pipeline_test_v0_1.py`, run with `python -I`, never imported) into a temporary directory, runs the Tier A pipeline with profile `test_v0_1` on each seed, records for R01–R08 whether any alarm rang, and compares each seed's output with that seed's generated answer key (S2 defect on mismatch). It reports the false-alarm count over R01–R06, the rate = count / 600 and per-resident counts for R01–R08 (R07 and R08 reported but excluded from the rate) into section 7 of `docs/reports/ALGORITHM_VALIDATION_REPORT.md` and into `docs/reports/validation_results.json` field `robustness`. The check is informational: it runs only in the nightly `nightly-validation` job of `.github/workflows/e2e.yml` (schedule or manual dispatch) with `continue-on-error: true` and never gates a build or a pull request (TRD 14 TDV-080..TDV-083, TRD 13 TST-084, TST-151, TRD 16 CIC-037).

## Preconditions

- Local development stack (README quick start): Python 3.12 virtual environment with `backend/requirements.txt` and `backend/requirements-dev.txt` installed; commands run from the repository root.
- The gating validation suite passes: `pytest tests/validation -q` exits 0 (FEAT-059).
- `specs/algorithm/generate_pipeline_test_v0_1.py` (SRC-04) present and unchanged.
- No database is required (Tier A runs in-process).
- For the CI cases: read access to the repository's GitHub Actions runs of the `E2E` workflow (`.github/workflows/e2e.yml`).
- `git status --porcelain` is empty before the run, so any file the run creates is visible.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-061-01 | Full 100-seed run writes report section 7 with seeds, count, rate and per-resident counts | High | Positive |
| TC-061-02 | `validation_results.json` holds a non-null `robustness` object with the expected fields | High | Positive |
| TC-061-03 | Rate equals false-alarm count over R01–R06 divided by 600; R07/R08 excluded from the rate | High | Analytics |
| TC-061-04 | Short run (`--seeds 2`) renders section 7 and keeps the rest of the report unchanged | Medium | Positive |
| TC-061-05 | Generated files stay in a temporary directory; nothing is written under `tests/fixtures/` or `specs/` | High | Positive |
| TC-061-06 | Generator executed with `python -I`, never imported | Medium | Security |
| TC-061-07 | Pull-request validation run does not collect the 100-seed loop | High | Negative |
| TC-061-08 | Forced failure inside the robustness step leaves the nightly CI job successful | High | Negative |
| TC-061-09 | Nightly job runs the step only on schedule or manual dispatch, never on pull requests | High | Negative |
| TC-061-10 | Multi-seed answer-key mismatch is logged as an S2 defect, not a failure | Medium | Negative |
| TC-061-11 | Generator failure for one seed is recorded and the loop continues | Medium | Negative |
| TC-061-12 | Unit tests of the aggregation and section 7 writer pass | Medium | Analytics |

### TC-061-01 Full 100-seed run writes report section 7

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `python -m tests.validation.robustness` from the repository root | The command exits with code 0; the last stdout line is a JSON object |
| 2 | Inspect the stdout JSON | It contains `"seeds": "1..100"`, `"denominator": 600`, an integer `false_alarms`, a numeric `rate`, `per_resident` with exactly the keys `R01`..`R08`, `reproduction_mismatches` and `mismatched_seeds` |
| 3 | Open `docs/reports/ALGORITHM_VALIDATION_REPORT.md` and find the heading | The heading reads exactly "## 7. Informational: false-alarm robustness (not gating)" |
| 4 | Read the first line under the heading | It reads "Latest run <UTC timestamp>: seeds 1..100, residents R01-R06 (rate) and R07-R08 (reported), false alarms <n>, rate <r>% (<n> of 600)." with `<n>` equal to the JSON `false_alarms` |
| 5 | Read the second line | It reads "Per resident: R01 <a>, R02 <b>, R03 <c>, R04 <d>, R05 <e>, R06 <f>, R07 <g>, R08 <h>." with the counts equal to the JSON `per_resident` values |
| 6 | Read the third line | It reads "Answer-key reproduction mismatches (S2 when non-zero): <m> seeds." with `<m>` equal to JSON `reproduction_mismatches` |
| 7 | Compare the rate with the TRD 09 §4.6 reference (61 of 600 = 10.2 %) | Recorded for information only; no pass/fail threshold applies (OQ-13) |

### TC-061-02 `robustness` object in validation_results.json

| Step | Action | Expected Result |
|---|---|---|
| 1 | After TC-061-01, open `docs/reports/validation_results.json` | File is valid JSON |
| 2 | Read the `robustness` field | It is an object (not `null`) with keys `generated_at`, `seeds`, `false_alarms`, `denominator`, `rate`, `per_resident`, `reproduction_mismatches`, `mismatched_seeds` |
| 3 | Check the other top-level fields written by FEAT-059 | They are still present and unchanged from before the run (only `robustness` was replaced) |

### TC-061-03 Rate calculation over R01–R06

| Step | Action | Expected Result |
|---|---|---|
| 1 | From the JSON of TC-061-02 sum `per_resident.R01` .. `per_resident.R06` | The sum equals `false_alarms` |
| 2 | Compute `false_alarms / 600` | Equals `rate` exactly |
| 3 | Check `per_resident.R07` and `per_resident.R08` | Both are present as integers 0..100 and are not included in `false_alarms` |
| 4 | Check every per-resident count | Each is an integer from 0 to 100 (at most one alarm flag per resident per seed) |

### TC-061-04 Short run renders section 7 only

| Step | Action | Expected Result |
|---|---|---|
| 1 | Copy `docs/reports/ALGORITHM_VALIDATION_REPORT.md` to a scratch location for comparison | Copy saved |
| 2 | Run `python -m tests.validation.robustness --seeds 2` | Exits 0; stdout JSON has `"seeds": "1..2"` and `"denominator": 12` |
| 3 | Diff the report against the saved copy | Only the text from "## 7. Informational: false-alarm robustness (not gating)" to the end of the file differs; sections 1–6 are byte-identical |
| 4 | Read section 7 | First line contains "seeds 1..2" and "(<n> of 12)" |
| 5 | Restore the report with `python -m tests.validation.robustness` (100 seeds) or the saved copy | Report back to its committed state |

### TC-061-05 No generated file under tests/fixtures or specs

| Step | Action | Expected Result |
|---|---|---|
| 1 | Before a run, record `git status --porcelain tests/fixtures specs` | Empty output |
| 2 | Run `python -m tests.validation.robustness --seeds 2` | Exits 0 |
| 3 | Run `git status --porcelain tests/fixtures specs` again | Empty output: no new or modified file under `tests/fixtures/` or `specs/` |
| 4 | Run `git status --porcelain` for the whole tree | Only `docs/reports/ALGORITHM_VALIDATION_REPORT.md` and `docs/reports/validation_results.json` are modified |
| 5 | Inspect `tests/validation/robustness.py` `run()` | Seed folders are created inside `tempfile.TemporaryDirectory()`, which is deleted when the loop ends |

### TC-061-06 Generator run with python -I, never imported

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `grep -n "generate_pipeline_test_v0_1" tests/validation/robustness.py` | Only the `GENERATOR` path constant matches; no `import generate_pipeline_test_v0_1` or `importlib` load |
| 2 | Read `run_seed()` | It calls `subprocess.run([sys.executable, "-I", str(GENERATOR), str(folder), str(seed)], …)` with the seed folder inside the temporary directory |

### TC-061-07 PR validation run excludes the 100-seed loop

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `pytest tests/validation -q --collect-only` | No collected item comes from `tests/validation/robustness.py` (the file name does not start with `test_`) |
| 2 | Run `pytest tests/validation -q` and time it | Completes without regenerating 100 seeds (no 100× generator subprocesses); `docs/reports/validation_results.json.robustness` is not replaced with a new `generated_at` by this command |
| 3 | Run `pytest tests/validation/test_robustness_check.py::test_not_part_of_the_gating_selection -q` | 1 passed |

### TC-061-08 Forced failure leaves the CI job successful

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `.github/workflows/e2e.yml`, job `nightly-validation`, step "Multi-seed robustness check (TDV-080..TDV-083, TST-084; informational, never gates)" | Step has `continue-on-error: true` and runs `python -m tests.validation.robustness` |
| 2 | On a throwaway branch, make the step fail (for example a temporary `raise SystemExit(1)` at the start of `main()`), then trigger the `E2E` workflow by manual dispatch on that branch | The robustness step is shown as failed (annotated) but the `nightly-validation` job conclusion is "success" |
| 3 | Check the next step "Upload nightly-validation-report" | It runs (`if: always()`) and uploads the `nightly-validation-report` artifact |
| 4 | Check the repository's branch-protection required checks | `nightly-validation` is not a required check (CIC-037) |
| 5 | Delete the throwaway branch | No change reaches `main` |

### TC-061-09 Runs only nightly or on manual dispatch

| Step | Action | Expected Result |
|---|---|---|
| 1 | Read the `nightly-validation` job condition | `if: github.event_name == 'schedule' \|\| github.event_name == 'workflow_dispatch'` |
| 2 | Open the Actions run of any recent pull request for the `E2E` workflow | Job `nightly-validation` is listed as skipped; the robustness step did not run |
| 3 | Open the most recent scheduled run (cron `0 8 * * *`) | Job `nightly-validation` ran and its log contains the robustness JSON line |

### TC-061-10 Answer-key mismatch logged as S2 defect

| Step | Action | Expected Result |
|---|---|---|
| 1 | Read the stderr output of TC-061-01 (or the nightly job log) | If `reproduction_mismatches` > 0, each mismatching seed has a line "S2 defect: seed <s> differs from its answer key (<k> mismatches; first <sheet> <key> <column>)" |
| 2 | Check the exit code in that case | Still 0; JSON `mismatched_seeds` lists the same seeds |
| 3 | With `reproduction_mismatches` = 0 | No "S2 defect" line is printed and `mismatched_seeds` is `[]` |

### TC-061-11 Generator failure for one seed does not stop the loop

| Step | Action | Expected Result |
|---|---|---|
| 1 | In a scratch copy of the repository, make the generator fail for one seed (for example seed 2) and run `python -m tests.validation.robustness --seeds 3` | The failure for seed 2 is recorded for that seed, seeds 1 and 3 are still processed, and the command exits 0 (TDV-081) |
| 2 | Check section 7 and the JSON | They are written for the processed seeds |

Note: the code differs from FEAT-061 Error Handling: `run_seed()` raises `RuntimeError` on a generator failure (tests/validation/robustness.py:47) and `run()` does not catch it (tests/validation/robustness.py:62-63), so the script stops; in CI the step is still non-gating through `continue-on-error: true`.

### TC-061-12 Aggregation and writer unit tests

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `pytest tests/validation/test_robustness_check.py -q` | All tests pass (`test_fixture_seed_has_no_false_alarm_and_reproduces`, `test_publish_fills_section_7_only`, `test_not_part_of_the_gating_selection`) |
| 2 | Read `test_publish_fills_section_7_only` | It asserts that only section 7 and the `robustness` field are replaced |

## API Validation

Not applicable: the check runs Tier A in-process and calls no API endpoint (FEAT-061 API Impact: none).

## Database Validation

Not applicable: Tier A runs without a database (FEAT-061 Database Impact: none).

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `pytest tests/validation -q` (PR selection) | The 100-seed loop is not executed (TC-061-07) |
| 2 | Force the robustness step to fail in the nightly job | Job conclusion "success"; step marked failed only (TC-061-08) |
| 3 | Open a pull request run of `E2E` | `nightly-validation` skipped (TC-061-09) |
| 4 | A seed's output differs from its own answer key | "S2 defect: seed <s> …" on stderr, exit 0 (TC-061-10) |
| 5 | Generator fails for one seed | Recorded, loop continues, exit 0 (TC-061-11; see Note) |
| 6 | Look for generated files under `tests/fixtures/` or `specs/` after a run | None (TC-061-05) |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-061-AC-01 | `python -m tests.validation.robustness` writes section 7 with seeds 1..100, the false-alarm count over R01–R06, rate = count / 600 and per-resident counts R01–R08 | TC-061-01, TC-061-03 |
| FEAT-061-AC-02 | `validation_results.json` has a non-null `robustness` object after the run | TC-061-02 |
| FEAT-061-AC-03 | A forced failure inside the robustness step leaves the CI job status successful | TC-061-08 |
| FEAT-061-AC-04 | `pytest tests/validation -q` does not execute the 100-seed loop | TC-061-07 |
| FEAT-061-AC-05 | No generated file exists under `tests/fixtures/` or `specs/` after the run | TC-061-05 |

## Test Data Requirements

- Reference generator SRC-04 `specs/algorithm/generate_pipeline_test_v0_1.py`; seeds 1..100 (and 1..2 / 1..3 for short runs).
- Profile `test_v0_1` (unchanged `baseline_n`, `cusum_h`); residents R01–R10 registry; synthetic data only, no audio.
- Committed `docs/reports/ALGORITHM_VALIDATION_REPORT.md` and `docs/reports/validation_results.json` from FEAT-059.
- No environment secrets needed for local runs; CI credentials are generated per job.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-061-FR-01 | FEAT-061 | TC-061-01, TC-061-06 |
| FEAT-061-FR-02 | FEAT-061 | TC-061-01, TC-061-03 |
| FEAT-061-FR-03 | FEAT-061 | TC-061-01, TC-061-02, TC-061-04 |
| FEAT-061-FR-04 | FEAT-061 | TC-061-10 |
| FEAT-061-FR-05 | FEAT-061 | TC-061-07, TC-061-08, TC-061-09 |
| FEAT-061-FR-06 | FEAT-061 | TC-061-05 |
| TDV-080 | FEAT-061 | TC-061-01, TC-061-06 |
| TDV-081 | FEAT-061 | TC-061-01, TC-061-02, TC-061-03, TC-061-08, TC-061-11 |
| TDV-082 | FEAT-061 | TC-061-10 |
| TDV-083 | FEAT-061 | TC-061-07, TC-061-09 |
| TDV-010 | FEAT-061 | TC-061-05 |
| TDV-024 | FEAT-061 | TC-061-06 |
| TST-084 | FEAT-061 | TC-061-07, TC-061-12 |
| TST-151 | FEAT-061 | TC-061-09 |
| CIC-037 | FEAT-061 | TC-061-08, TC-061-09 |
