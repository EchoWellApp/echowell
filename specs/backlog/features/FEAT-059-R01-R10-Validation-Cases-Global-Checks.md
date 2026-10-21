# FEAT-059 R01–R10 validation cases, global checks and validation report

| Field | Value |
|---|---|
| Epic | Testing & Validation |
| Build phase | Phase 7 (TRD 25) |
| Priority | P0 |
| Complexity | High |
| MVP status | Required |
| Dependencies | FEAT-058 |
| Status | Not Started |

## Purpose

Implement the ten resident validation cases VC-R01..VC-R10 (including the invariance check VC-R04-INV and the frozen-baseline check VC-R10-FRZ), the twelve global checks VC-G01..VC-G12 and the totals test, and write `docs/reports/ALGORITHM_VALIDATION_REPORT.md` and `docs/reports/validation_results.json` after every run. Passing this suite is the gate before the frontend phase: Phase 8 starts only when `pytest tests/validation -q` passes with zero failures (AGT-023).

## Business Context

- BR-15 (reproduce the pipeline test workbook answer key exactly, R01–R10) and the first half of demo step 4 (SRC-15, TST-180).
- BR-03..BR-11: each case isolates one rule — clean control, missing days, set-aside, duplicates, other speaker, morning effect, device move, too few sessions, step change, gradual drift.
- FRs covered (BACKLOG.md): FR-031 (VC-R04-INV: identical results without the duplicate copies).

## Referenced TRDs

- TRD 14 TDV-050 (global checks file), TDV-051..TDV-060 (VC-R01..VC-R10), TDV-070..TDV-073 (report contents, check counts, RCA sections, CI artifact), §4.6 VC-G01..VC-G12, §4.7 Tables 4.7-A/B/C and §4.7.1–§4.7.10, §4.8 validation sequence, §4.10 report format and JSON schema.
- TRD 13 TST-048, TST-050, TST-080, TST-082, TST-083, TST-012, MVP-01.
- TRD 09 CUS-027 (tally and alarm strings), CUS-028 (exactly two alerts).
- TRD 16 CIC-100 (report written and uploaded even on failure), CIC-102 (job summary table).
- TRD 25 AGT-023 (frontend gate), AGT-040..AGT-058 (pitfalls each case catches), §4.6 Phase 7.

## Scope

- One module per case: `tests/validation/test_r01_clean_control.py`, `test_r02_missing_days.py`, `test_r03_set_aside_sessions.py`, `test_r04_duplicate_records.py`, `test_r05_possible_other_speaker.py`, `test_r06_morning_effect.py`, `test_r07_device_move.py`, `test_r08_too_few_sessions.py`, `test_r09_step_change.py`, `test_r10_gradual_drift.py`; each runs its checks in Tier A and Tier B through the FEAT-058 harness.
- `tests/validation/test_global_checks.py`: VC-G01..VC-G12 (VC-G11 Tier B only), including the totals test (usable 267, set_aside 12, quarantined 2, duplicate 2, missing_resident 17, missing_device_gap 2).
- Supplementary checks VC-R04-INV, VC-R10-FRZ (gating) and VC-R06-MUT (Should, excluded from the PASS/FAIL total).
- `tests/validation/report.py` writing the Markdown report and JSON results; CI artifact upload and job-summary table (consumed by FEAT-078).

## Out of Scope

- Harness, comparator, tiers (FEAT-058); golden files (FEAT-057).
- UI-fixture API checks for the pages (FEAT-060) and the robustness check, which fills report section 7 (FEAT-061).
- Fixing pipeline defects found by the suite (they are fixed in the analytics features, never by editing expected values, TST-162).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-059-FR-01 | VC-R01 shall pass: R01 30 usable, epoch 1, frozen after R01-20261016-01, 14 scored, no alarm, max tally 0.333077, ledger 30 `checked_in`; Exp_baselines R01 (20 rows) and Exp_scores R01 (14 rows) compared. | TDV-051 |
| FEAT-059-FR-02 | VC-R02 shall pass: days 4, 9, 10, 17, 23 `missing_resident` "no record received"; day 12 `missing_device_gap` "all residents on shared device D02 have no record"; frozen after R02-20261021-01; 8 scored; nothing carried forward. | TDV-052, AGT-046 |
| FEAT-059-FR-03 | VC-R03 shall pass with the exact set-aside reasons of TRD 14 §4.7.3 (e.g. day 18 "quality flag poor; noise above limit"), day 12 device gap, frozen after R03-20261023-01, 6 scored, max tally 2.202944. | TDV-053, AGT-049 |
| FEAT-059-FR-04 | VC-R04 shall pass: arrivals 89 and 283 `duplicate` "session_id already received", 30 usable, frozen after R04-20261016-01, 14 scored; VC-R04-INV: Tier A without arrivals 89 and 283 gives identical R04 outputs; Tier B stores both duplicates in `raw_sessions` and `processed_sessions` as `duplicate`. | TDV-054, FR-031, AGT-043 |
| FEAT-059-FR-05 | VC-R05 shall pass: day 8 quarantined "possible other speaker (F0 z=-8.61; composite features with \|z\|>=3: 4)", day 22 "possible other speaker (F0 z=-7.34; composite features with \|z\|>=3: 3)", frozen after R05-20261017-01, 12 scored, max tally 4.005975. | TDV-055, AGT-044 |
| FEAT-059-FR-06 | VC-R06 shall pass: the 10 sessions on days 1, 4, …, 28 are morning by local hour, adjusted values per Table 4.5-E (e.g. day 1 loudness −25.42 → −23.92), 4 morning scored sessions; VC-R06-MUT (all offsets 0) shall make the R06 loudness baseline comparison fail and is excluded from the total. | TDV-056, AGT-040, AGT-050 |
| FEAT-059-FR-07 | VC-R07 shall pass: epoch 1 (D07) 12 usable, not formed, note "Too few usable sessions: baseline pending, nothing scored", no baselines/scores/alerts; epoch 2 (D07B) from R07-20261013-01, frozen after R07-20261028-01, 2 scored with tally 0.000000. | TDV-057, AGT-045 |
| FEAT-059-FR-08 | VC-R08 shall pass: 13 usable, 5 set aside with exact reasons, 12 `missing_resident`, no baselines/scores/alerts, run `succeeded`. | TDV-058 |
| FEAT-059-FR-09 | VC-R09 shall pass with the 14-row table of TRD 14 §4.7.9 (first alarm R09-20261021-01 tally 5.431965 "RINGS (first crossing)", final 26.830256) and one alert. | TDV-059, CUS-027, AGT-047, AGT-048 |
| FEAT-059-FR-10 | VC-R10 shall pass with the 14-row table of §4.7.10 (first alarm R10-20261024-01 tally 5.972050, final 13.418183); VC-R10-FRZ: (a) Exp_baselines R10 match, (b) Tier A truncated to R10 days ≤ 2026-10-16 gives identical R10 baselines, (c) Tier B incremental ingestion with `time-machine` keeps R10 `baselines` (values and `frozen_at`) unchanged after days 17–30. | TDV-060, AGT-051 |
| FEAT-059-FR-11 | `test_global_checks.py` shall implement VC-G01..VC-G12 and pass in both tiers (VC-G11 Tier B only): status totals 267/12/2/2/17/2; 302 Annotated_sessions rows; 10 status-count rows; 11 outcome rows; 180 baselines with `floor_applied` "yes" on exactly 8 `number_of_pauses` rows; 98 scores (off 81, on 15, RINGS 2); 19 morning offsets; parameters; 300 ledger rows; exactly 2 open alerts with `cusum_state` tallies; 283 raw rows with exact payloads; determinism and rebuild. | TDV-050, TRD 14 §4.6, CUS-028, TST-050 |
| FEAT-059-FR-12 | `tests/validation/report.py` shall write `docs/reports/ALGORITHM_VALIDATION_REPORT.md` with the header fields (Generated, Git SHA, Profile, Config snapshot SHA-256, input and workbook SHA-256, tolerance, Overall) and sections 1–7 of TRD 14 §4.10, and `docs/reports/validation_results.json` with the §4.10 schema. | TST-082, TDV-070, CIC-100 |
| FEAT-059-FR-13 | "Overall: PASS" shall be written only when all 22 cases pass in both tiers and VC-R04-INV and VC-R10-FRZ pass; `checks` shall equal the number of value comparisons and a case with 0 checks shall be FAIL. | TDV-070, TDV-071 |
| FEAT-059-FR-14 | The report shall list up to 50 mismatches per failed case with stage attribution and leave sections 4 (root cause analysis) and 5 (recommended fixes) for the engineer to complete in the PR. | TDV-070, TDV-072 |
| FEAT-059-FR-15 | CI shall upload both report files as artifacts even when tests fail and show the R01–R10 pass/fail table in the job summary; the committed copies in `docs/reports/` shall be refreshed in each PR #3 review checkpoint (and any later PR) that touches `analytics/`. | CIC-100, CIC-102, TDV-073 |
| FEAT-059-FR-16 | Test function names shall include the case ID (e.g. `test_vc_r09_first_alarm`). | TST-012 |

## Inputs

- Harness fixtures, comparator and Tier A/Tier B results (FEAT-058); DS-01, DS-02 (FEAT-057).
- Expected values of TRD 14 §4.6–§4.7 (read from DS-02 at full precision, not from the rounded tables in the TRD).
- `GIT_SHA`, config snapshot of the validation run (for the report header).

## Outputs

- Ten case modules plus `test_global_checks.py` and `report.py` under `tests/validation/`.
- `docs/reports/ALGORITHM_VALIDATION_REPORT.md` and `docs/reports/validation_results.json` (22 cases, supplementary results, `robustness: null` until FEAT-061 fills it).

## Data Flow

Integrity checks (FEAT-057) → load DS-01 + registry → Tier A run and Tier B ingest + run (FEAT-058) → each VC case selects its rows and calls the comparator → results aggregated → `report.py` writes Markdown and JSON → CI uploads artifacts and writes the job summary → merge allowed only on "Overall: PASS" (TRD 14 §4.8).

## Dependencies

Required before implementation (BACKLOG.md): FEAT-058

- FEAT-058 provides the tiers, the comparator and mismatch records that every case uses.

Features that build directly on this one (BACKLOG.md §4): FEAT-060, FEAT-061, FEAT-078, FEAT-093, FEAT-094. The frontend phase starts only after this suite passes (AGT-023).

## Database Impact

None beyond the Tier B test database of FEAT-058 (read-only checks of `raw_sessions`, `processed_sessions`, `day_ledger`, `epochs`, `baselines`, `scores`, `alerts`, `cusum_state`, `pipeline_runs`, `ingest_rejections`).

## API Impact

Endpoints consumed through the harness: E-06, E-07, E-12, E-13, E-18, E-19, E-20, E-21 (and E-08 for VC-G checks). None exposed.

## Frontend Impact

None. Passing this suite unblocks Phase 8 (AGT-023).

## Analytics Impact

None in production code. Each case targets one pitfall of TRD 25 §4.8 (AGT-040 timezone, AGT-041 even median, AGT-042 floors, AGT-043 duplicates, AGT-044 first-N screen, AGT-045 epoch keys, AGT-046 missing days, AGT-047/AGT-048 CUSUM, AGT-049 reason order, AGT-050 adjusted vs raw, AGT-051 frozen baseline, AGT-054 rounding, AGT-055 signs, AGT-056 idempotency, AGT-057 answer key, AGT-058 reviews).

## Security Requirements

- The report contains only study IDs and synthetic values (TRD 14 §8); no secrets, no real data.
- The workbook is read only by tests (AGT-007).

## Error Handling

- A failing case reports all its mismatches and the first failing stage; the suite does not stop at the first failure (TDV-037).
- No skip, xfail or retry (TST-083); a validation failure is an S1 defect fixed in code, never by editing golden files (TST-162).
- The report is written even when cases fail (CIC-100).

## Logging Requirements

- The report and JSON are the run record (TDV-070); the job summary shows the pass/fail table (CIC-102).
- No audit records beyond the Tier B API calls.

## Testing Requirements

- Validation suite (marker `validation`): the ten case modules, `test_global_checks.py`, `test_invariance.py` (VC-R04-INV, VC-R10-FRZ (b)) and the Tier B incremental part of VC-R10-FRZ (c) with `time-machine`.
- Report tests: a synthetic run with one failed case produces "Overall: FAIL (1 of 22 cases failed)", a section-3 table for that case, and JSON matching the §4.10 schema; a case with 0 checks is FAIL (TDV-071).
- Command: `pytest tests/validation -q`.

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-059-AC-01 | `pytest tests/validation -q` exits 0 with VC-R01..VC-R10 passing in Tier A and Tier B. | AC-TDV-01; TST-080 |
| FEAT-059-AC-02 | VC-G01..VC-G12 pass: totals 267/12/2/2/17/2, 98 Exp_scores rows, 180 Exp_baselines rows, 2 alerts, 300 ledger rows, 283 raw rows. | AC-TDV-02; TDV-050 |
| FEAT-059-AC-03 | VC-R04-INV and VC-R10-FRZ pass. | AC-TDV-03 |
| FEAT-059-AC-04 | `docs/reports/ALGORITHM_VALIDATION_REPORT.md` shows "Overall: PASS" with a 22-row summary table and `docs/reports/validation_results.json` has `overall` "PASS" and `supplementary` VC-R04-INV/VC-R10-FRZ "PASS". | AC-TDV-06; TDV-070 |
| FEAT-059-AC-05 | The persisted `alerts` table after Tier B contains exactly R09 (R09-20261021-01, 2026-10-21, 5.431965) and R10 (R10-20261024-01, 2026-10-24, 5.972050), both `open`. | CUS-028; VC-G10 |
| FEAT-059-AC-06 | A CI run with a forced failure still uploads both report files as artifacts. Verified by: Inspection (the inspection method of CIC-100, applied to the condition stated in the criterion). | CIC-100 |
| FEAT-059-AC-07 | Every case module and global check has at least one comparison (`checks` > 0) in the JSON. Verified by: Report tests (a case with 0 checks is FAIL (TDV-071)). | TDV-071 |

## Definition of Done

- All FEAT-059 acceptance criteria pass.
- All R01–R10 tests and the totals test pass; numeric comparisons within 1e-6 and strings exact; R04 output identical without the two copies (TRD 25 Phase 7 DoD).
- Report and JSON committed in the Phase 7 checkpoint of PR #3 (TDV-073); Phase 8 may start (AGT-023).
- Batch report lists IDs, commands and results (AGT-022).

## Implementation Notes

- The rounded numbers in TRD 14 §4.7 are for reading; compare against the workbook's stored precision (TDV-038).
- VC-R06-MUT changes the config only for its own Tier A run; never change the `test_v0_1` profile values (AGT-008).
- Use the R09/R10 tables to name checks so mismatches point at specific sessions.
- When a case fails, fill report sections 4 and 5 in the PR before requesting review (TDV-072).
