# Golden fixtures, answer-key integrity and evaluation ground-truth loader

## Feature Description

FEAT-057 puts the answer key and the pipeline test input under test control and keeps them away from the pipeline. The golden files are checksummed copies: `tests/fixtures/answer_key/EchoWell_pipeline_test_v0_1.xlsx` (SRC-03, DS-02), `tests/fixtures/pipeline_input/EchoWell_pipeline_test_input_v0_1.csv` (SRC-05, DS-01) and the legacy `tests/fixtures/legacy/echowell_mock_data_500.csv` (SRC-06, negative ingest fixture only), with digests in `tests/fixtures/answer_key/SHA256SUMS`. `tests/validation/test_answer_key_integrity.py` checks byte identity with `specs/`, the checksums, a fresh regeneration with seed 20261004, the input-folder contents and the separation scans; `python -m tests.validation.diff_answer_key` prints changed cells. The evaluation ground truth DS-10 (`evaluation_ground_truth_v0_1.csv`, 10 rows) is loaded only by `database/seeds/load_evaluation_ground_truth.py`, which refuses outside `test_v0_1` and in production.

## Preconditions

- Repository checkout at the root; Python dependencies from `backend/requirements-dev.txt` (pandas, openpyxl).
- For loader cases: migrated test database; environment `APP_ENV` (development or test), `PIPELINE_PROFILE=test_v0_1`, `DATABASE_MIGRATION_URL` and the other ENV-053 variables from the environment file.
- `psql` for read-only checks.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-057-01 | Fixture checksums equal the TDV-013 baseline and `SHA256SUMS`; copies are byte-identical to `specs/` | High | Positive |
| TC-057-02 | Regeneration with seed 20261004 reproduces the CSV byte-for-byte and the workbook cell-for-cell | High | Positive |
| TC-057-03 | Separation scans pass; no pipeline code references the answer key | High | Security |
| TC-057-04 | `tests/fixtures/pipeline_input/` holds only DS-01 | High | Negative |
| TC-057-05 | Loader loads exactly 10 rows with R09 2026-10-21 and R10 2026-10-17 | High | Database |
| TC-057-06 | Loader refuses with `APP_ENV=production` and with `PIPELINE_PROFILE=production` | High | Security |
| TC-057-07 | Loader rejects a malformed CSV and leaves the table unchanged | Medium | Negative |
| TC-057-08 | `diff_answer_key` prints exactly the changed Exp_scores cell | High | Positive |
| TC-057-09 | Legacy SRC-06 file exists and is referenced only by negative ingest tests | Medium | Negative |
| TC-057-10 | DS-10 content equals TRD 14 §4.9.3 and agrees with the Test_plan sheet | High | Positive |
| TC-057-11 | Workbook is opened read-only and never written | Medium | Security |
| TC-057-12 | Golden files change only through the `answer-key-change` procedure | Medium | Documentation |

### TC-057-01 Fixture checksums equal the TDV-013 baseline and `SHA256SUMS`; copies are byte-identical to `specs/`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `sha256sum tests/fixtures/answer_key/EchoWell_pipeline_test_v0_1.xlsx tests/fixtures/pipeline_input/EchoWell_pipeline_test_input_v0_1.csv` | `ddbc03ea6fef37388d2f0265902096cc0fe28559d36cb2855f63ec51ec482257` (workbook) and `78e77faad423f305dfb83429ccd21978f089e843c181b5d244a5d7d4f5fabe28` (CSV) |
| 2 | `cat tests/fixtures/answer_key/SHA256SUMS` | Same two digests for `answer_key/EchoWell_pipeline_test_v0_1.xlsx` and `pipeline_input/EchoWell_pipeline_test_input_v0_1.csv` |
| 3 | `cmp tests/fixtures/answer_key/EchoWell_pipeline_test_v0_1.xlsx specs/business-requirements/EchoWell_pipeline_test_v0_1.xlsx && cmp tests/fixtures/pipeline_input/EchoWell_pipeline_test_input_v0_1.csv specs/data-samples/EchoWell_pipeline_test_input_v0_1.csv && echo identical` | `identical` |
| 4 | `pytest tests/validation/test_answer_key_integrity.py -q -k golden_files` | `test_golden_files_match_specs_and_checksums` passes |

### TC-057-02 Regeneration with seed 20261004 reproduces the CSV byte-for-byte and the workbook cell-for-cell

| Step | Action | Expected Result |
|---|---|---|
| 1 | `mkdir /tmp/regen && python -I specs/algorithm/generate_pipeline_test_v0_1.py /tmp/regen 20261004` | Exit 0; CSV and workbook written to `/tmp/regen` only |
| 2 | `cmp /tmp/regen/EchoWell_pipeline_test_input_v0_1.csv tests/fixtures/pipeline_input/EchoWell_pipeline_test_input_v0_1.csv && echo same` | `same` |
| 3 | `python -m tests.validation.diff_answer_key tests/fixtures/answer_key/EchoWell_pipeline_test_v0_1.xlsx /tmp/regen/EchoWell_pipeline_test_v0_1.xlsx` | Only `<sheet>: rows N -> N` lines (same counts, e.g. Exp_scores 98 -> 98); no changed-cell line |
| 4 | `pytest tests/validation/test_answer_key_integrity.py -q -k regeneration` | `test_regeneration_reproduces_the_golden_files` passes (floats within 1e-12, strings exact; generator run as a subprocess, never imported) |

### TC-057-03 Separation scans pass; no pipeline code references the answer key

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -rn "pipeline_test_v0_1.xlsx" analytics backend` | No output |
| 2 | `grep -rn --include=*.py --include=*.ts --include=*.tsx --exclude=analytics_summary.py --exclude-dir=seeds -e answer_key -e Exp_ -e EchoWell_pipeline_test_v0_1.xlsx -e openpyxl analytics backend frontend/app frontend/components frontend/lib frontend/services database` | No output |
| 3 | `pytest tests/validation/test_answer_key_integrity.py -q -k no_production_code` | `test_no_production_code_reads_the_answer_key` passes |

### TC-057-04 `tests/fixtures/pipeline_input/` holds only DS-01

| Step | Action | Expected Result |
|---|---|---|
| 1 | `ls -A tests/fixtures/pipeline_input/` | Exactly `EchoWell_pipeline_test_input_v0_1.csv` |
| 2 | Negative check: `cp tests/fixtures/answer_key/EchoWell_pipeline_test_v0_1.xlsx tests/fixtures/pipeline_input/`, run `pytest tests/validation/test_answer_key_integrity.py -q -k pipeline_input_folder`, then delete the copy | The test FAILS while the `.xlsx` is present; passes again after removal |

### TC-057-05 Loader loads exactly 10 rows with R09 2026-10-21 and R10 2026-10-17

| Step | Action | Expected Result |
|---|---|---|
| 1 | `python database/seeds/load_evaluation_ground_truth.py tests/fixtures/answer_key/evaluation_ground_truth_v0_1.csv; echo $?` | `Loaded 10 evaluation ground-truth rows (profile test_v0_1).`; exit `0` |
| 2 | `SELECT resident_code, planted_change, true_onset_date, source_file FROM evaluation_ground_truth ORDER BY resident_code;` (as `echowell_migrator` or readonly role) | 10 rows: R01–R08 `None` / NULL; R09 `Sudden step` 2026-10-21; R10 `Slow drift` 2026-10-17; `source_file` `EchoWell_pipeline_test_v0_1.xlsx` on all |
| 3 | Run step 1 again, repeat step 2 | Still exactly 10 rows (contents replaced, not appended) |

### TC-057-06 Loader refuses with `APP_ENV=production` and with `PIPELINE_PROFILE=production`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Note `SELECT count(*) FROM evaluation_ground_truth;` | Value N |
| 2 | `APP_ENV=production python database/seeds/load_evaluation_ground_truth.py tests/fixtures/answer_key/evaluation_ground_truth_v0_1.csv; echo $?` | `Refused: the evaluation ground truth is never loaded in production.`; exit `2` (non-zero) |
| 3 | `PIPELINE_PROFILE=production python database/seeds/load_evaluation_ground_truth.py tests/fixtures/answer_key/evaluation_ground_truth_v0_1.csv; echo $?` | `Refused: the evaluation ground truth is loaded only under PIPELINE_PROFILE=test_v0_1.`; exit `2` |
| 4 | Repeat step 1 | Still N |
| 5 | `pytest tests/integration/db/test_ground_truth_loader.py -q` | All three tests pass |

### TC-057-07 Loader rejects a malformed CSV and leaves the table unchanged

| Step | Action | Expected Result |
|---|---|---|
| 1 | Create `/tmp/bad_gt.csv` with header `resident_code,planted_change,true_onset_date,source_file` and one row `R09,Sudden step,,EchoWell_pipeline_test_v0_1.xlsx` (planted change without onset) | File created |
| 2 | `python database/seeds/load_evaluation_ground_truth.py /tmp/bad_gt.csv; echo $?` | `Not loaded: line 2: onset date must be set iff a change is planted.`; exit `1` |
| 3 | `SELECT count(*) FROM evaluation_ground_truth;` | Unchanged |
| 4 | Run the loader with no argument | `usage: load_evaluation_ground_truth.py <csv_path>`; exit `2` |

### TC-057-08 `diff_answer_key` prints exactly the changed Exp_scores cell

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/validation/test_answer_key_integrity.py -q -k diff_answer_key` | `test_diff_answer_key_prints_the_changed_cell` passes |
| 2 | Manual: copy the workbook to `/tmp/b.xlsx`, open the copy in a spreadsheet tool, change one `cusum_tally` cell on sheet Exp_scores (e.g. session R09-20261021-01) and save | Copy modified; golden file untouched |
| 3 | `python -m tests.validation.diff_answer_key tests/fixtures/answer_key/EchoWell_pipeline_test_v0_1.xlsx /tmp/b.xlsx` | Exactly one changed-cell line `Exp_scores!R09-20261021-01.cusum_tally: <old> -> <new>` plus `<sheet>: rows N -> N` lines |
| 4 | `python -m tests.validation.diff_answer_key` with one argument | Usage line `usage: python -m tests.validation.diff_answer_key <old.xlsx> <new.xlsx>`; non-zero exit |

### TC-057-09 Legacy SRC-06 file exists and is referenced only by negative ingest tests

| Step | Action | Expected Result |
|---|---|---|
| 1 | `ls tests/fixtures/legacy/echowell_mock_data_500.csv` | File exists |
| 2 | `grep -rln "echowell_mock_data_500" analytics backend frontend database tests --include=*.py --include=*.ts` | Only `tests/integration/api/test_ingest.py` (negative ingest test) and `tests/validation/test_answer_key_integrity.py` (the check itself) |
| 3 | `pytest tests/validation/test_answer_key_integrity.py -q -k legacy_file` | Passes |

### TC-057-10 DS-10 content equals TRD 14 §4.9.3 and agrees with the Test_plan sheet

| Step | Action | Expected Result |
|---|---|---|
| 1 | `cat tests/fixtures/answer_key/evaluation_ground_truth_v0_1.csv` | Header `resident_code,planted_change,true_onset_date,source_file`; R01–R08 `None` with empty onset; `R09,Sudden step,2026-10-21`; `R10,Slow drift,2026-10-17`; 10 data rows |
| 2 | `pytest tests/validation/test_answer_key_integrity.py -q -k test_plan` | `test_ground_truth_agrees_with_test_plan` passes (R09 step from day 21, R10 drift from day 17) |

### TC-057-11 Workbook is opened read-only and never written

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -rn -e to_excel -e ".save(" -e ExcelWriter tests/validation` | No write to `tests/fixtures/answer_key/` (only the temporary copy in the diff test may be written) |
| 2 | `sha256sum tests/fixtures/answer_key/EchoWell_pipeline_test_v0_1.xlsx` after `pytest tests/validation -q` | Unchanged `ddbc03ea…482257` |

### TC-057-12 Golden files change only through the `answer-key-change` procedure

| Step | Action | Expected Result |
|---|---|---|
| 1 | On GitHub, list merged PRs that touched `tests/fixtures/answer_key/` or `tests/fixtures/pipeline_input/` | Each carries the label `answer-key-change` and includes `diff_answer_key` output in its description |
| 2 | Inspect those PRs | No hand edit of expected values or `test_v0_1` parameters to make a test pass |

## API Validation

Not applicable directly: no endpoint is added. The loaded ground truth feeds `alarm_timing` of `GET /api/v1/analytics` (checked in TC-051 and TC-060-07).

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT count(*) FROM evaluation_ground_truth;` after TC-057-05 | `10` |
| 2 | `SELECT count(*) FROM evaluation_ground_truth WHERE (planted_change = 'None') <> (true_onset_date IS NULL);` | `0` (`evaluation_ground_truth_onset_ck`) |
| 3 | `psql "$DATABASE_URL" -c "SELECT 1 FROM evaluation_ground_truth"` (role `echowell_app`) | `permission denied for table evaluation_ground_truth` |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Loader with `APP_ENV=production` | Exit 2, nothing written |
| 2 | Loader with `PIPELINE_PROFILE=production` | Exit 2, nothing written |
| 3 | Malformed CSV | Exit 1, table unchanged |
| 4 | `.xlsx` placed in `tests/fixtures/pipeline_input/` | Integrity test fails |
| 5 | Any byte change to a golden file | `test_golden_files_match_specs_and_checksums` fails naming the file |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-057-AC-01 | `sha256sum` equals TDV-013 and `SHA256SUMS`; byte-identical to `specs/` | TC-057-01 |
| FEAT-057-AC-02 | Regeneration with seed 20261004 reproduces CSV and every sheet | TC-057-02 |
| FEAT-057-AC-03 | TDV-010/011/012 scans pass; `grep -rn "pipeline_test_v0_1.xlsx" analytics backend` returns nothing | TC-057-03, TC-057-04 |
| FEAT-057-AC-04 | Loader loads exactly 10 rows, R09 2026-10-21, R10 2026-10-17 | TC-057-05 |
| FEAT-057-AC-05 | Loader exits non-zero and writes nothing with `APP_ENV=production` and with `PIPELINE_PROFILE=production` | TC-057-06 |
| FEAT-057-AC-06 | `diff_answer_key` prints exactly `Exp_scores!<key>.<column>: <old> -> <new>` | TC-057-08 |
| FEAT-057-AC-07 | Legacy file exists and is referenced only by negative ingest tests | TC-057-09 |

## Test Data Requirements

- Golden files under `tests/fixtures/` and their `specs/` sources; generator `specs/algorithm/generate_pipeline_test_v0_1.py`; DS-10 `tests/fixtures/answer_key/evaluation_ground_truth_v0_1.csv`.
- Temporary files in `/tmp` only (`/tmp/regen`, `/tmp/b.xlsx`, `/tmp/bad_gt.csv`).
- Environment: `APP_ENV`, `PIPELINE_PROFILE`, `DATABASE_MIGRATION_URL`, `DATABASE_URL` from the environment file.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-057-FR-01 / TST-070, TDV-013 | FEAT-057 | TC-057-01 |
| FEAT-057-FR-02 / TST-071, TDV-014 | FEAT-057 | TC-057-01 |
| FEAT-057-FR-03 / TDV-020, TDV-024 | FEAT-057 | TC-057-02 |
| FEAT-057-FR-04 / TDV-010, TDV-012 | FEAT-057 | TC-057-04 |
| FEAT-057-FR-05 / TDV-011, AGT-007 | FEAT-057 | TC-057-03 |
| FEAT-057-FR-06 / TDV-015 | FEAT-057 | TC-057-11 |
| FEAT-057-FR-07 / TDV-023, TST-073 | FEAT-057 | TC-057-08 |
| FEAT-057-FR-08 / TST-072, TDV-021, AGT-008 | FEAT-057 | TC-057-12 |
| FEAT-057-FR-09 / TDV-100 | FEAT-057 | TC-057-10 |
| FEAT-057-FR-10 / TDV-103, CUS-048 | FEAT-057 | TC-057-05, TC-057-06, TC-057-07 |
| FEAT-057-FR-11 / TDV-005, D-25 | FEAT-057 | TC-057-09 |
| FEAT-057-FR-12 / TDV-001, TDV-004 | FEAT-057 | TC-057-04 |
| FEAT-057-FR-13 / TDV-016 | FEAT-057 | TC-057-03 (no workbook reference in `frontend/`) |
| TST-068, FR-318 | FEAT-057 | TC-057-06, Database Validation 3 |
| AC-TDV-04, AC-TDV-05, AC-AGT-02 | FEAT-057 | TC-057-01, TC-057-02, TC-057-03 |
