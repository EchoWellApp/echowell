# R01–R10 validation cases, global checks and validation report

## Feature Description

FEAT-059 implements the ten resident validation cases VC-R01..VC-R10 (one module each under `tests/validation/`), the supplementary checks VC-R04-INV and VC-R10-FRZ (gating) and VC-R06-MUT (reported only), the twelve global checks VC-G01..VC-G12 (`tests/validation/test_global_checks.py`, VC-G11 Tier B only) and the report writer `tests/validation/report.py`, which writes `docs/reports/ALGORITHM_VALIDATION_REPORT.md` and `docs/reports/validation_results.json` after every full-suite run. "Overall: PASS" requires all 22 cases to pass in both tiers plus VC-R04-INV and VC-R10-FRZ; a case with 0 checks is FAIL. CI uploads both files even when tests fail and writes the pass/fail table to the job summary. Passing `pytest tests/validation -q` is the gate before the frontend phase (AGT-023).

## Preconditions

- Repository root; `backend/requirements-dev.txt` installed; Docker for testcontainers (Tier B).
- Golden files unmodified (TC-057-01 passes); harness of FEAT-058 working (TC-058-01, TC-058-02 pass).
- `SEED_*` variables in the environment; `GIT_SHA` set (otherwise the report shows `unknown`).
- For database spot checks: a database seeded with `python -m backend.cli seed test_v0_1` (DS-07; equals the Tier B end state).

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-059-01 | `pytest tests/validation -q` exits 0 with VC-R01..VC-R10 passing in both tiers | High | Analytics |
| TC-059-02 | VC-R01 clean control | High | Analytics |
| TC-059-03 | VC-R02 missing days and device gap | High | Analytics |
| TC-059-04 | VC-R03 set-aside reasons | High | Analytics |
| TC-059-05 | VC-R04 duplicates and VC-R04-INV | High | Analytics |
| TC-059-06 | VC-R05 possible other speaker | High | Analytics |
| TC-059-07 | VC-R06 morning effect and VC-R06-MUT | High | Analytics |
| TC-059-08 | VC-R07 device move | High | Analytics |
| TC-059-09 | VC-R08 too few sessions | High | Analytics |
| TC-059-10 | VC-R09 step change | High | Analytics |
| TC-059-11 | VC-R10 gradual drift and VC-R10-FRZ | High | Analytics |
| TC-059-12 | Global checks VC-G01..VC-G12 | High | Analytics |
| TC-059-13 | Persisted `alerts` after Tier B: exactly R09 and R10 open | High | Database |
| TC-059-14 | Report shows "Overall: PASS", 22-row summary; JSON `overall` and `supplementary` PASS | High | Documentation |
| TC-059-15 | Every case has `checks` > 0; a 0-check case or a failed case gives FAIL | High | Negative |
| TC-059-16 | CI uploads both report files even on a forced failure | High | Negative |

### TC-059-01 `pytest tests/validation -q` exits 0 with VC-R01..VC-R10 passing in both tiers

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/validation -q; echo $?` | All tests pass, no skip/xfail; exit `0` |
| 2 | `grep -c "^def test_vc_r" tests/validation/test_r*.py` | One `test_vc_r0N_...` / `test_vc_r10_...` function per module (names contain the case ID) |

### TC-059-02 VC-R01 clean control

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/validation/test_r01_clean_control.py -q` | Passes (Tier A and Tier B) |
| 2 | DS-07: `SELECT count(*) FILTER (WHERE p.status='usable') FROM processed_sessions p JOIN residents r ON r.id=p.resident_id WHERE r.resident_code='R01';` | `30` |
| 3 | `SELECT count(*), max(s.cusum_tally) FROM scores s JOIN residents r ON r.id=s.resident_id WHERE r.resident_code='R01';` | 14 scored; max tally 0.333077 ±1e-6 |
| 4 | `SELECT DISTINCT frozen_after_session_id FROM baselines b JOIN residents r ON r.id=b.resident_id WHERE r.resident_code='R01';` | `R01-20261016-01` (20 rows) |
| 5 | R01 alerts and ledger | No alert; 30 `checked_in` ledger days |

### TC-059-03 VC-R02 missing days and device gap

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/validation/test_r02_missing_days.py -q` | Passes |
| 2 | DS-07: R02 ledger rows not `checked_in` | 2026-10-04, 09, 10, 17, 23 `missing_resident` "no record received"; 2026-10-12 `missing_device_gap` "all residents on shared device D02 have no record" |
| 3 | R02 baselines and scores | Frozen after `R02-20261021-01`; 8 scored sessions; no score or value on any missing day (nothing carried forward) |

### TC-059-04 VC-R03 set-aside reasons

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/validation/test_r03_set_aside_sessions.py -q` | Passes |
| 2 | DS-07: `SELECT session_id, reason_text FROM processed_sessions WHERE session_id LIKE 'R03-%' AND status='set_aside' ORDER BY session_id;` | 7 rows on days 3, 7, 10, 14, 18, 22, 26; `R03-20261018-01` reason `quality flag poor; noise above limit` (fixed reason order) |
| 3 | R03 day 12, baseline, scores | `missing_device_gap`; frozen after `R03-20261023-01`; 6 scored; max tally 2.202944 ±1e-6 |

### TC-059-05 VC-R04 duplicates and VC-R04-INV

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/validation/test_r04_duplicate_records.py tests/validation/test_invariance.py -q -k "r04"` | Both pass |
| 2 | DS-07: `SELECT s.arrival_seq, p.status, p.reason_text FROM raw_sessions s JOIN processed_sessions p ON p.raw_session_id=s.id WHERE p.status='duplicate' ORDER BY 1;` | Arrivals 89 and 283, `duplicate`, `session_id already received` (both stored in `raw_sessions` and `processed_sessions`) |
| 3 | R04 usable, baseline, scores | 30 usable; frozen after `R04-20261016-01`; 14 scored |
| 4 | VC-R04-INV (Tier A without arrivals 89 and 283) | R04 outputs identical |

### TC-059-06 VC-R05 possible other speaker

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/validation/test_r05_possible_other_speaker.py -q` | Passes |
| 2 | DS-07: `SELECT session_id, reason_text FROM processed_sessions WHERE session_id LIKE 'R05-%' AND status='quarantined' ORDER BY 1;` | `R05-20261008-01` "possible other speaker (F0 z=-8.61; composite features with \|z\|>=3: 4)"; `R05-20261022-01` "possible other speaker (F0 z=-7.34; composite features with \|z\|>=3: 3)" |
| 3 | R05 baseline and scores | Frozen after `R05-20261017-01`; 12 scored; max tally 4.005975 ±1e-6 |

### TC-059-07 VC-R06 morning effect and VC-R06-MUT

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/validation/test_r06_morning_effect.py -q` | Passes |
| 2 | Review the test's checks | 10 sessions on days 1, 4, 7, …, 28 are morning by facility-local hour; day 1 loudness −25.42 raw → −23.92 adjusted (Table 4.5-E) |
| 3 | DS-07: `SELECT count(*) FROM scores s JOIN residents r ON r.id=s.resident_id WHERE r.resident_code='R06' AND s.is_morning;` | `4` |
| 4 | `pytest tests/validation/test_invariance.py -q -k r06_mut` | Passes: with all morning offsets 0 the R06 loudness baseline comparison fails (detected); result reported as supplementary, excluded from the 22-case total |

### TC-059-08 VC-R07 device move

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/validation/test_r07_device_move.py -q` | Passes |
| 2 | DS-07: `SELECT e.epoch_number, d.device_code FROM epochs e JOIN residents r ON r.id=e.resident_id LEFT JOIN devices d ON d.id=e.device_id WHERE r.resident_code='R07' ORDER BY 1;` | Epoch 1 D07; epoch 2 D07B |
| 3 | Researcher `GET /api/v1/analytics` → `resident_outcomes` R07 rows | Epoch 1: `usable_in_epoch` 12, `baseline_formed` false, `note` "Too few usable sessions: baseline pending, nothing scored"; epoch 2: `baseline_frozen_after` "R07-20261028-01", `scored_sessions` 2 |
| 4 | R07 epoch 2 scores | 2 rows, `cusum_tally` 0.000000; no baselines, scores or alerts for epoch 1 |

### TC-059-09 VC-R08 too few sessions

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/validation/test_r08_too_few_sessions.py -q` | Passes |
| 2 | DS-07 R08 counts | 13 usable, 5 set aside (exact reasons per TRD 14 §4.7.8), 12 `missing_resident` ledger days |
| 3 | `SELECT (SELECT count(*) FROM baselines b JOIN residents r ON r.id=b.resident_id WHERE r.resident_code='R08'), (SELECT count(*) FROM scores s JOIN residents r ON r.id=s.resident_id WHERE r.resident_code='R08'), (SELECT count(*) FROM alerts a JOIN residents r ON r.id=a.resident_id WHERE r.resident_code='R08');` | `0, 0, 0`; the run is `succeeded` |

### TC-059-10 VC-R09 step change

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/validation/test_r09_step_change.py -q` | Passes (14-row table of TRD 14 §4.7.9) |
| 2 | DS-07: `SELECT p.session_id, s.cusum_tally, s.alarm_state FROM scores s JOIN processed_sessions p ON p.id=s.processed_session_id WHERE p.session_id LIKE 'R09-%' ORDER BY p.timestamp_utc;` | 14 rows Oct 17–30; Oct 17–20 `off`; `R09-20261021-01` 5.431965 ±1e-6 `rings` (answer key "RINGS (first crossing)"); later rows `on`; last 26.830256 ±1e-6 |
| 3 | R09 alerts | Exactly 1 |

### TC-059-11 VC-R10 gradual drift and VC-R10-FRZ

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/validation/test_r10_gradual_drift.py -q` and `pytest tests/validation/test_invariance.py -q -k r10_frz` | Both pass |
| 2 | DS-07 R10 scores | 14 rows; first alarm `R10-20261024-01` 5.972050 ±1e-6 `rings`; last 13.418183 ±1e-6 |
| 3 | VC-R10-FRZ | (a) Exp_baselines R10 match; (b) Tier A truncated to R10 days ≤ 2026-10-16 gives identical R10 baselines; (c) Tier B incremental ingestion with the application clock frozen keeps R10 `baselines` values and `frozen_at` unchanged after days 17–30 |

### TC-059-12 Global checks VC-G01..VC-G12

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/validation/test_global_checks.py -q` | All `test_vc_g01`..`test_vc_g12` pass (VC-G11 Tier B only) |
| 2 | DS-07: `SELECT status, count(*) FROM processed_sessions GROUP BY 1;` and `SELECT status, count(*) FROM day_ledger GROUP BY 1;` | usable 267, set_aside 12, quarantined 2, duplicate 2; missing_resident 17, missing_device_gap 2, checked_in 281 (300 ledger rows) |
| 3 | `SELECT count(*), count(*) FILTER (WHERE floor_applied), count(*) FILTER (WHERE floor_applied AND feature_key='number_of_pauses') FROM baselines;` | `180`, `8`, `8` |
| 4 | `SELECT alarm_state, count(*) FROM scores GROUP BY 1;` | 98 total: off 81, on 15, rings 2 |
| 5 | `SELECT count(*) FROM raw_sessions; SELECT count(*) FROM ingest_rejections;` | 283; 0 |
| 6 | `SELECT r.resident_code, c.current_tally, c.alarm_on FROM cusum_state c JOIN residents r ON r.id=c.resident_id WHERE c.alarm_on;` | R09 26.830256, R10 13.418183 (±1e-6); no other `alarm_on` true |

### TC-059-13 Persisted `alerts` after Tier B: exactly R09 and R10 open

| Step | Action | Expected Result |
|---|---|---|
| 1 | DS-07: `SELECT r.resident_code, a.session_id, a.local_date, a.cusum_value, a.status FROM alerts a JOIN residents r ON r.id=a.resident_id ORDER BY 1;` | 2 rows: R09 `R09-20261021-01` 2026-10-21 5.431965 ±1e-6 `open`; R10 `R10-20261024-01` 2026-10-24 5.972050 ±1e-6 `open` |
| 2 | `pytest tests/validation/test_global_checks.py -q -k vc_g10` | Passes |

### TC-059-14 Report shows "Overall: PASS", 22-row summary; JSON `overall` and `supplementary` PASS

| Step | Action | Expected Result |
|---|---|---|
| 1 | After TC-059-01, `head -6 docs/reports/ALGORITHM_VALIDATION_REPORT.md` | Header lines with `Generated:`, `Git SHA:`, `Profile: test_v0_1`, `Config snapshot SHA-256:`, `Input: EchoWell_pipeline_test_input_v0_1.csv (SHA-256 78e77faa…fabe28)`, `Answer key: EchoWell_pipeline_test_v0_1.xlsx (SHA-256 ddbc03ea…482257)`, `Tolerance: abs 1e-6 (float64); strings, integers, booleans exact`, `Overall: PASS` |
| 2 | `grep -n "^## " docs/reports/ALGORITHM_VALIDATION_REPORT.md` | Sections `1. Summary`, `2. Passed cases`, `3. Failed cases`, `4. Root cause analysis`, `5. Recommended fixes`, `6. Supplementary checks`, `7. Informational: false-alarm robustness (not gating)` |
| 3 | Count the summary table rows | 22 rows: VC-R01..VC-R10, VC-G01..VC-G12; VC-G11 Tier A "n/a" |
| 4 | `python -c "import json; d=json.load(open('docs/reports/validation_results.json')); print(d['overall'], d['supplementary'], len(d['cases']))"` | `PASS {'VC-R04-INV': 'PASS', 'VC-R10-FRZ': 'PASS', 'VC-R06-MUT': 'PASS'} 22` |
| 5 | Search both files for names, rooms or secrets | Only study IDs and synthetic values |

### TC-059-15 Every case has `checks` > 0; a 0-check case or a failed case gives FAIL

| Step | Action | Expected Result |
|---|---|---|
| 1 | `python -c "import json; d=json.load(open('docs/reports/validation_results.json')); print(min(c['checks'] for c in d['cases']))"` | A number > 0 (e.g. VC-G09 has 8) |
| 2 | `pytest tests/validation/test_report.py -q` | `test_passing_run`, `test_failing_case_and_zero_checks`, `test_gating_supplementary_check_fails_overall`, `test_only_a_full_session_is_complete` pass |
| 3 | Review `test_failing_case_and_zero_checks` | One failed case gives "Overall: FAIL (1 of 22 cases failed)", a section-3 table for that case (up to 50 mismatches with stage) and JSON matching the §4.10 schema; a case with 0 checks is FAIL |
| 4 | Review `test_gating_supplementary_check_fails_overall` | A failing VC-R04-INV or VC-R10-FRZ makes Overall FAIL |

### TC-059-16 CI uploads both report files even on a forced failure

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -n -A8 "if: always()" .github/workflows/ci.yml` | The upload-artifact step runs with `if: always()` and lists `docs/reports/ALGORITHM_VALIDATION_REPORT.md` and `docs/reports/validation_results.json`; a second `if: always()` step writes the report table to `$GITHUB_STEP_SUMMARY` |
| 2 | On a throw-away branch, make one validation case fail (e.g. change one expected value inside a copy of the test, never the golden file), push and open the CI run | Validation job fails; artifacts still contain both report files; job summary shows the R01–R10 pass/fail table with the failed case |
| 3 | Delete the throw-away branch | No change reaches the main branch |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | Researcher `GET /api/v1/analytics` on DS-07 | `status_totals` 267/12/2/2/17/2; `resident_outcomes` 11 rows; `status_counts` 10 rows |
| 2 | `GET /api/v1/analytics/baselines?limit=1` | `total` 180 |
| 3 | `GET /api/v1/scores?resident_code=R09` | `total` 14 |
| 4 | `GET /api/v1/alerts` | `total` 2 (R09, R10) |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT r.resident_code, count(*) FROM scores s JOIN residents r ON r.id=s.resident_id GROUP BY 1 ORDER BY 1;` | R01 14, R02 8, R03 6, R04 14, R05 12, R06 14, R07 2, R09 14, R10 14 (R08 absent) |
| 2 | `SELECT count(*) FROM baselines b JOIN epochs e ON e.id=b.epoch_id JOIN residents r ON r.id=b.resident_id WHERE r.resident_code='R07' AND e.epoch_number=1;` | `0` |
| 3 | `SELECT count(*) FROM epochs;` | `11` |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | One failed case | "Overall: FAIL (1 of 22 cases failed)" |
| 2 | Case with 0 checks | FAIL |
| 3 | VC-R04-INV or VC-R10-FRZ fails | Overall FAIL |
| 4 | Skip or xfail of a validation test | Session exits non-zero (TC-058-10) |
| 5 | VC-R06-MUT with offsets 0 | R06 loudness baseline comparison fails (expected; not counted in the total) |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-059-AC-01 | `pytest tests/validation -q` exits 0; VC-R01..VC-R10 pass in Tier A and Tier B | TC-059-01, TC-059-02..TC-059-11 |
| FEAT-059-AC-02 | VC-G01..VC-G12 pass: totals 267/12/2/2/17/2, 98 scores, 180 baselines, 2 alerts, 300 ledger rows, 283 raw rows | TC-059-12 |
| FEAT-059-AC-03 | VC-R04-INV and VC-R10-FRZ pass | TC-059-05, TC-059-11 |
| FEAT-059-AC-04 | Report "Overall: PASS" with a 22-row table; JSON `overall` "PASS", `supplementary` VC-R04-INV/VC-R10-FRZ "PASS" | TC-059-14 |
| FEAT-059-AC-05 | `alerts` after Tier B: exactly R09 (R09-20261021-01, 2026-10-21, 5.431965) and R10 (R10-20261024-01, 2026-10-24, 5.972050), both `open` | TC-059-13 |
| FEAT-059-AC-06 | Forced CI failure still uploads both report files | TC-059-16 |
| FEAT-059-AC-07 | Every case and global check has `checks` > 0 | TC-059-15 |

## Test Data Requirements

- DS-01, DS-02 (FEAT-057), registry `database/seeds/test_v0_1/`, DS-07 database for spot checks.
- Environment: `SEED_*` variables, `GIT_SHA`; Docker for Tier B.
- A throw-away Git branch for TC-059-16 only.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-059-FR-01 / TDV-051 | FEAT-059 | TC-059-02 |
| FEAT-059-FR-02 / TDV-052, AGT-046 | FEAT-059 | TC-059-03 |
| FEAT-059-FR-03 / TDV-053, AGT-049 | FEAT-059 | TC-059-04 |
| FEAT-059-FR-04 / TDV-054, FR-031, AGT-043 | FEAT-059 | TC-059-05 |
| FEAT-059-FR-05 / TDV-055, AGT-044 | FEAT-059 | TC-059-06 |
| FEAT-059-FR-06 / TDV-056, AGT-040, AGT-050 | FEAT-059 | TC-059-07 |
| FEAT-059-FR-07 / TDV-057, AGT-045 | FEAT-059 | TC-059-08 |
| FEAT-059-FR-08 / TDV-058 | FEAT-059 | TC-059-09 |
| FEAT-059-FR-09 / TDV-059, CUS-027 | FEAT-059 | TC-059-10 |
| FEAT-059-FR-10 / TDV-060, AGT-051 | FEAT-059 | TC-059-11 |
| FEAT-059-FR-11 / TDV-050, CUS-028, TST-050 | FEAT-059 | TC-059-12, TC-059-13 |
| FEAT-059-FR-12 / TST-082, TDV-070, CIC-100 | FEAT-059 | TC-059-14 |
| FEAT-059-FR-13 / TDV-070, TDV-071 | FEAT-059 | TC-059-14, TC-059-15 |
| FEAT-059-FR-14 / TDV-072 | FEAT-059 | TC-059-14 step 2, TC-059-15 step 3 |
| FEAT-059-FR-15 / CIC-100, CIC-102, TDV-073 | FEAT-059 | TC-059-16 |
| FEAT-059-FR-16 / TST-012 | FEAT-059 | TC-059-01 step 2 |
| VC-R01..VC-R10 | FEAT-059 | TC-059-02..TC-059-11 |
| VC-G01..VC-G12 | FEAT-059 | TC-059-12, TC-059-13 |
| VC-R04-INV, VC-R10-FRZ, VC-R06-MUT | FEAT-059 | TC-059-05, TC-059-11, TC-059-07 |
| AC-TDV-01, AC-TDV-02, AC-TDV-03, AC-TDV-06 | FEAT-059 | TC-059-01, TC-059-12, TC-059-05, TC-059-14 |
| TST-080, TST-083, MVP-01, AGT-023 | FEAT-059 | TC-059-01 |
