# FEAT-057 Golden fixtures, answer-key integrity and evaluation ground-truth loader

| Field | Value |
|---|---|
| Epic | Testing & Validation |
| Build phase | Phase 7 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-005, FEAT-012 |
| Status | Not Started |

## Purpose

Put the answer key and the pipeline test input under test control and keep them apart from the pipeline. The feature copies SRC-03 (workbook), SRC-05 (input CSV) and the legacy SRC-06 file into `tests/fixtures/` with SHA-256 checksums and byte-identity tests, adds the regeneration check against the reference generator and the `diff_answer_key` tool, creates the evaluation ground-truth file DS-10 and its `test_v0_1`-only loader, and adds the scans that prove no pipeline code reads the answer key. These golden files are the basis of every R01–R10 validation case.

## Business Context

- BR-15 (reproduce the answer key exactly): the golden files must be the exact, checksummed copies of the source of truth, and any change must go through a reviewed regeneration (TST-072, TST-073).
- SRC-02 ("the answer key never touches the analytics") and D-38: the evaluation ground truth exists only for the Analytics "Alarm timing check" and never reaches the pipeline.
- D-25: the legacy mock file is kept only as a negative ingest fixture.
- FRs covered (BACKLOG.md): FR-318 (alarm timing read from `evaluation_ground_truth` after the run).

## Referenced TRDs

- TRD 14 TDV-001..TDV-008 (dataset catalogue and permitted use), TDV-010..TDV-016 (fixture storage and separation), TDV-020..TDV-024 (regeneration, `answer-key-change`, `diff_answer_key`, generator run as subprocess), TDV-100 (DS-10 agrees with Test_plan), TDV-103 (loader refusal rules), §4.1 DS-01..DS-10, §4.3 procedure, §4.9.3 DS-10 content.
- TRD 13 TST-070..TST-075 (golden files, byte identity, no hand edits, diff in PR, regression rule, defect regression tests).
- TRD 09 CUS-048 (loader only in test_v0_1; pipeline uses `echowell_app`).
- TRD 01 ARC-034; TRD 20 §4.6.24 `evaluation_ground_truth`.
- TRD 25 AGT-007, AGT-008, AGT-025; TRD 24 D-25, D-26, D-38.
- TRD 02 FR-318.

## Scope

- Fixture copies: `tests/fixtures/answer_key/EchoWell_pipeline_test_v0_1.xlsx` (SRC-03), `tests/fixtures/pipeline_input/EchoWell_pipeline_test_input_v0_1.csv` (SRC-05), `tests/fixtures/legacy/echowell_mock_data_500.csv` (SRC-06), and `tests/fixtures/answer_key/SHA256SUMS`.
- `tests/validation/test_answer_key_integrity.py`: byte identity with `specs/` files, checksum match, regeneration with seed 20261004 (CSV byte-identical, workbook cell-identical within 1e-12), DS-10 vs Test_plan agreement.
- Separation scans: no `.xlsx`, `answer_key` or `Exp_` file under `tests/fixtures/pipeline_input/`; no reference to `answer_key`, `Exp_`, `EchoWell_pipeline_test_v0_1.xlsx` or `openpyxl` in `analytics/`, `backend/` (except `backend/services/analytics_summary.py`), `frontend/app`, `frontend/components`, `frontend/lib`, `frontend/services`, `database/` (except `database/seeds/`).
- `python -m tests.validation.diff_answer_key <old.xlsx> <new.xlsx>`.
- DS-10 file `tests/fixtures/answer_key/evaluation_ground_truth_v0_1.csv` (columns `resident_code, planted_change, true_onset_date, source_file`; 10 rows).
- Loader `database/seeds/load_evaluation_ground_truth.py <csv_path>` (direct script, not wrapped by `backend.cli`).

## Out of Scope

- The validation harness, comparator and R01–R10 cases (FEAT-058, FEAT-059).
- Reading `evaluation_ground_truth` for the alarm-timing block (`backend/services/analytics_summary.py`, FEAT-035).
- The DS-08 load-dataset generator `tests/performance/make_load_dataset.py` (TDV-008, FEAT-079).
- Recording the frontend MSW fixtures with `npm run fixtures:capture` (TDV-016, FEAT-062); this feature only ensures UI fixtures are never built from workbook values.
- The negative ingest test with SRC-06 (TST-047, FEAT-026), which uses the legacy fixture copied here.

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-057-FR-01 | The golden files shall be stored as `tests/fixtures/answer_key/EchoWell_pipeline_test_v0_1.xlsx` and `tests/fixtures/pipeline_input/EchoWell_pipeline_test_input_v0_1.csv`, with their SHA-256 digests in `tests/fixtures/answer_key/SHA256SUMS` (baseline: workbook `ddbc03ea6fef37388d2f0265902096cc0fe28559d36cb2855f63ec51ec482257`, CSV `78e77faad423f305dfb83429ccd21978f089e843c181b5d244a5d7d4f5fabe28`). | TST-070, TDV-013 |
| FEAT-057-FR-02 | A test shall assert that the fixture copies are byte-identical to `specs/business-requirements/EchoWell_pipeline_test_v0_1.xlsx` and `specs/data-samples/EchoWell_pipeline_test_input_v0_1.csv` and match `SHA256SUMS`. | TST-071, TDV-014 |
| FEAT-057-FR-03 | `test_answer_key_integrity.py` shall run `python -I specs/algorithm/generate_pipeline_test_v0_1.py <tmpdir> 20261004` as a subprocess and assert the regenerated CSV is byte-identical to DS-01 and every workbook sheet equals DS-02 cell by cell (strings exact, floats within 1e-12); the generator shall never be imported. | TDV-020, TDV-024 |
| FEAT-057-FR-04 | `tests/fixtures/pipeline_input/` shall contain only `EchoWell_pipeline_test_input_v0_1.csv`; a test shall fail on any `.xlsx` file or any name containing `answer_key` or `Exp_` there. | TDV-010, TDV-012 |
| FEAT-057-FR-05 | A scan test shall fail on any occurrence of `answer_key`, `Exp_`, `EchoWell_pipeline_test_v0_1.xlsx` or `openpyxl` in `analytics/`, `backend/` (excluding `backend/services/analytics_summary.py`), `frontend/app`, `frontend/components`, `frontend/lib`, `frontend/services` and `database/` (excluding `database/seeds/`); `backend/cli.py` shall not reference `evaluation_ground_truth` or the loader. | TDV-011, AGT-007 |
| FEAT-057-FR-06 | The harness shall open the workbook read-only (`openpyxl` `read_only=True` via pandas) and never write it. | TDV-015 |
| FEAT-057-FR-07 | `python -m tests.validation.diff_answer_key <old.xlsx> <new.xlsx>` shall print, per sheet, row count before/after and every changed cell as `sheet!key.column: old -> new`. | TDV-023, TST-073 |
| FEAT-057-FR-08 | Golden files shall change only through the TRD 14 §4.3 regeneration procedure in a PR labelled `answer-key-change` that includes the `diff_answer_key` output; expected values and `test_v0_1` parameters shall never be edited to make a test pass. | TST-072, TST-073, TDV-021, AGT-008 |
| FEAT-057-FR-09 | `tests/fixtures/answer_key/evaluation_ground_truth_v0_1.csv` (DS-10) shall contain exactly: R01–R08 `None` with null onset; R09 `Sudden step` 2026-10-21; R10 `Slow drift` 2026-10-17; `source_file` `EchoWell_pipeline_test_v0_1.xlsx`; a test shall check agreement with SRC-03 Test_plan. | TDV-100, TRD 14 §4.9.3 |
| FEAT-057-FR-10 | `python database/seeds/load_evaluation_ground_truth.py <csv_path>` shall refuse (non-zero exit, no rows written) when `APP_ENV` is `production` or `PIPELINE_PROFILE` is not `test_v0_1`, and otherwise replace the contents of `evaluation_ground_truth`; it reads only the CSV path given on its command line. | TDV-103, CUS-048, ARC-034, D-38 |
| FEAT-057-FR-11 | The legacy SRC-06 copy shall be stored at `tests/fixtures/legacy/echowell_mock_data_500.csv` and used only as a negative ingest fixture; no mapping from its columns to v0.1 features shall exist. | TDV-005, AGT-025, D-25 |
| FEAT-057-FR-12 | DS-01 shall be the only validation pipeline input; DS-06 corpora and DS-04 answer keys shall never be committed into input folders; fixture data and real records never share a database. | TDV-001, TDV-004, TDV-006, TDV-007 |
| FEAT-057-FR-13 | UI and MSW fixtures shall be produced from pipeline output, never from workbook values. | TDV-016 |

## Inputs

- `specs/business-requirements/EchoWell_pipeline_test_v0_1.xlsx` (SRC-03), `specs/data-samples/EchoWell_pipeline_test_input_v0_1.csv` (SRC-05), `specs/data-samples/echowell_mock_data_500.csv` (SRC-06), `specs/algorithm/generate_pipeline_test_v0_1.py` (SRC-04).
- SRC-03 Test_plan sheet (for DS-10).

## Outputs

- Fixture files and `SHA256SUMS` under `tests/fixtures/`.
- `tests/validation/test_answer_key_integrity.py`, `tests/validation/diff_answer_key.py`, separation scan tests.
- `tests/fixtures/answer_key/evaluation_ground_truth_v0_1.csv`; `database/seeds/load_evaluation_ground_truth.py`.
- 10 rows in `evaluation_ground_truth` after loading DS-10 in a `test_v0_1` database.

## Data Flow

`specs/` source files → byte copy → `tests/fixtures/` + `SHA256SUMS` → integrity tests compare copies, checksums and a fresh regeneration. DS-10 CSV → loader (test_v0_1 only, connecting with `DATABASE_MIGRATION_URL` as `echowell_migrator`) → `evaluation_ground_truth` → read only by `analytics_summary.py` through `DATABASE_READONLY_URL` after a run (FEAT-035). The pipeline never touches any of it.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-005, FEAT-012

- FEAT-005 provides pytest, markers (`validation`) and fixture conventions.
- FEAT-012 provides the `evaluation_ground_truth` table and its grants.

## Database Impact

- Table written: `evaluation_ground_truth` (loader replaces contents; columns `resident_code`, `planted_change`, `true_onset_date`, `source_file`; TRD 20 §4.6.24, constraint `evaluation_ground_truth_onset_ck`).
- No table created or altered; `echowell_app` keeps no privilege on the table (DB-009).

## API Impact

None. The data loaded here feeds the `alarm_timing` block of `GET /api/v1/analytics` (E-18), served by FEAT-035.

## Frontend Impact

None.

## Analytics Impact

None; the feature proves the opposite — that no `analytics/` module reads the workbook or the ground truth (AGT-007, AGT-057).

## Security Requirements

- The loader refuses `APP_ENV=production` and any profile other than `test_v0_1` (TDV-103); production never holds ground truth (NFR-127).
- The loader connects with `DATABASE_MIGRATION_URL` (role `echowell_migrator`, closed list of TRD 20 §4.3, SEC-111) and validates only the variables of ENV-053; the app role `echowell_app` has no privilege on the table (DB-009).
- Fixture files contain synthetic study IDs only (AGT-017); no audio fixture exists (TST-007).

## Error Handling

- Checksum or byte mismatch → test failure naming the file; the fix is regeneration through `answer-key-change`, never editing expected values (TST-072, AGT-008).
- Generator failure → test failure with the subprocess stderr.
- Loader refusal → non-zero exit, no rows written; malformed CSV → non-zero exit, table unchanged.

## Logging Requirements

- The loader prints the number of rows loaded and the target profile; it logs no secrets.
- No audit action is defined for the loader in TRD 12 §4.12; none is written.

## Testing Requirements

- Validation (`tests/validation/test_answer_key_integrity.py`, marker `validation`): TST-071 / TDV-014 byte identity, TDV-013 checksums, TDV-020 regeneration, TDV-100 DS-10 vs Test_plan, TDV-010 / TDV-012 input folder contents.
- Static scan (`tests/validation/test_answer_key_integrity.py` or `tests/unit/backend/test_answer_key_separation.py`): TDV-011, AGT-007 (`grep -rn "pipeline_test_v0_1.xlsx" analytics backend` returns nothing).
- Integration (`tests/integration/db/test_ground_truth_loader.py`): TDV-103 refusal with `APP_ENV=production` and with `PIPELINE_PROFILE=production`; successful load of 10 rows in test_v0_1; TST-068 (c).
- Unit: `diff_answer_key` on two workbooks with one changed cell prints that cell (TDV-023).
- No validation test may be skipped or xfailed (TST-083).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-057-AC-01 | `sha256sum` of the fixture workbook and CSV equals the TDV-013 baseline values and `SHA256SUMS`, and both are byte-identical to the `specs/` files. | AC-TDV-04; TST-071 |
| FEAT-057-AC-02 | Regenerating with seed 20261004 into a temporary directory reproduces the CSV byte-for-byte and every workbook sheet cell-for-cell. | AC-TDV-04; TDV-020 |
| FEAT-057-AC-03 | The separation scans of TDV-010, TDV-011 and TDV-012 pass, and `grep -rn "pipeline_test_v0_1.xlsx" analytics backend` returns no match. | AC-TDV-05; AC-AGT-02 |
| FEAT-057-AC-04 | `python database/seeds/load_evaluation_ground_truth.py tests/fixtures/answer_key/evaluation_ground_truth_v0_1.csv` loads exactly 10 rows in a `test_v0_1` database, with R09 2026-10-21 and R10 2026-10-17. | TDV-100; TDV-103 |
| FEAT-057-AC-05 | The loader exits non-zero and writes nothing with `APP_ENV=production`, and also with `PIPELINE_PROFILE=production`. | TDV-103; TST-068 |
| FEAT-057-AC-06 | `python -m tests.validation.diff_answer_key a.xlsx b.xlsx` on two workbooks differing in one Exp_scores cell prints exactly that cell as `Exp_scores!<key>.<column>: <old> -> <new>`. | TDV-023 |
| FEAT-057-AC-07 | `tests/fixtures/legacy/echowell_mock_data_500.csv` exists and is referenced only by negative ingest tests. | TDV-005; D-25 |

## Definition of Done

- All FEAT-057 acceptance criteria pass; `pytest tests/validation -q -k integrity` green.
- PR carries no edit of expected values; any future change follows `answer-key-change` (TST-072).
- Batch report lists IDs, commands and checksums (AGT-022).

## Implementation Notes

- Run the generator only in a scratch temp directory; it writes both CSV and workbook into one folder (TRD 14 §4.3) and executes on import, so always use `python -I` as a subprocess (TDV-024).
- `.xlsx` byte equality is not required (zip timestamp); compare sheets cell by cell (TDV-020).
- Read sheets with `pd.read_excel(path, sheet_name=None, dtype=object, engine="openpyxl")` (TRD 14 §8).
- Keep `database/seeds/load_evaluation_ground_truth.py` independent of `backend/cli.py` (TRD 15 §4.8, D-68).
