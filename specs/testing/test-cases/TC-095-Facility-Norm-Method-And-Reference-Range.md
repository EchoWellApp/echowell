# Facility norm method and reference-range computation for the new-admission arm

## Feature Description

Status: Not Started — these test cases are written from the feature file and run only once the feature is built (BACKLOG.md §10).

FEAT-095 gives the experimental new-admission arm a facility norm. A separate pure function in the planned module `analytics/facility_norms.py` (created only when OQ-08 is resolved), outside `run_pipeline`, reads adjusted values of usable sessions and produces per-feature reference ranges (`low` ≤ `high`, `method`, `n_residents` ≥ 1, `sex` F/M/NULL, `computed_at`). The pipeline service calls it after `run_pipeline` within a full (`scope = all`) run and stores the rows in `facility_reference_ranges` stamped with that run's `pipeline_run_id` (TRD 24 D-76). F0 ranges are computed only per known sex, excluding residents with null sex (OQ-20 interim decision). Ranges never influence any resident's own baseline, score, CUSUM or alerts. Once ranges exist, E-22 `GET /api/v1/admissions` returns `outside_range` / `within_range` / `not_enough_checkins` instead of `range_not_available`, E-23 returns per-feature comparisons, E-24 lists the ranges, and `/admissions` shows "Outside facility range" / "Within facility range" instead of "Facility range not available yet". Gate: OQ-08 (statistic, residents, minimum N, thresholds) and OQ-20 (sex values) answered in TRD 24; method-specific expected values are added from that decision.

Cases run on the local Compose stack with synthetic data (`test_v0_1` plus the fixture new-admission resident N01 of TST-185 and fixture residents with known sex).

Note: FEAT-095-FR-09 quotes the caption as "grey band = usual range across current residents" and the token `--color-range-band`; TRD 11 UX-189/UX-190 specify "Grey band = usual range across current residents" and `--grey-bg` (as rendered by `frontend/lib/wording/admin.ts:50`). These cases follow the TRD.

## Preconditions

- Local Compose stack (`docker compose up -d --build`), seeded with `test_v0_1`; admin, clinician and researcher tokens from `POST /api/v1/auth/login` (passwords from `.env`).
- Synthetic new-admission fixture N01 (cohort `new_admission`, own device) and enough synthetic longitudinal residents with usable sessions to meet the OQ-08 minimum N; some with `sex` F, some M, some NULL.
- OQ-08 and OQ-20 decisions recorded in TRD 24; TRD 07, TRD 02 and TRD 11 updated with the method.
- `psql` read access to the local database.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-095-01 | `run_pipeline` never references `facility_norms` | High | Documentation |
| TC-095-02 | Before ranges exist the arm shows `range_not_available` and "Facility range not available yet" | Medium | UI |
| TC-095-03 | Pipeline output with and without computed ranges is identical | High | Analytics |
| TC-095-04 | Stored range rows meet the DDL constraints and link to a full-run `pipeline_runs` row | High | Database |
| TC-095-05 | No F0 range has `sex` NULL; null-sex residents are not counted in F0 rows | High | Database |
| TC-095-06 | Every row names the OQ-08 method and has `n_residents` ≥ the OQ-08 minimum N | High | Database |
| TC-095-07 | TST-186 passes against ranges produced by the new function | High | API |
| TC-095-08 | E-23 comparison and E-24 range list return the documented fields | High | API |
| TC-095-09 | `/admissions` shows the badges, band-and-dot chart, caption and text table | High | UI |
| TC-095-10 | Note "Future / experimental …" keeps sentences 2–3 until OQ-08 is closed | Medium | UI |
| TC-095-11 | A new admission moves to the Resident list once its own baseline forms (TST-185) | High | Positive |
| TC-095-12 | Too few residents or check-ins give no range / `not_enough_checkins` | Medium | Negative |
| TC-095-13 | R01–R10 validation passes unchanged | High | Analytics |
| TC-095-14 | Admission endpoints keep their roles and expose study IDs only | Medium | Security |

### TC-095-01 `run_pipeline` never references `facility_norms`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -n "facility_norms" analytics/pipeline.py; echo "exit=$?"` | No output; `exit=1` |
| 2 | `grep -rn "facility_norms" analytics backend` | The module itself and the pipeline service call after `run_pipeline` (scope `all`) only |
| 3 | Before OQ-08 is resolved: `ls analytics/facility_norms.py` | File does not exist |

### TC-095-02 Before ranges exist the arm shows `range_not_available` and "Facility range not available yet"

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT count(*) FROM facility_reference_ranges;` | `0` |
| 2 | `GET /api/v1/admissions` (clinician) | Every item `comparison_status` `range_not_available` |
| 3 | `GET /api/v1/facility/reference-ranges` | 200 with an empty list |
| 4 | Open `/admissions` | Badge text "Facility range not available yet" for each admission (or empty state "No new admissions. The pipeline test data v0.1 has no admission group." when none) |

### TC-095-03 Pipeline output with and without computed ranges is identical

| Step | Action | Expected Result |
|---|---|---|
| 1 | Local: run a full pipeline without the norm step (ranges table empty); record `SELECT md5(string_agg(t::text, '' ORDER BY t::text)) FROM (SELECT resident_id, epoch_id, feature_key, median, robust_spread FROM baselines) t;` and the same for `scores` (`processed_session_id, z, composite_z, cusum_tally, alarm_state`), `cusum_state` and `alerts` (`resident_id, epoch_id, session_id, local_date, cusum_value, status`) | Four hashes recorded |
| 2 | Run a full (`scope = all`) run that computes ranges | `facility_reference_ranges` has rows |
| 3 | Recompute the four hashes | Identical to step 1 |
| 4 | Run the unit tests of the norm function (purity, determinism, never touching baselines or scores) | All pass |

### TC-095-04 Stored range rows meet the DDL constraints and link to a full-run `pipeline_runs` row

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT count(*) FROM facility_reference_ranges WHERE low > high OR n_residents < 1 OR length(method) NOT BETWEEN 1 AND 200 OR pipeline_run_id IS NULL;` | `0` |
| 2 | `SELECT DISTINCT feature_key FROM facility_reference_ranges;` | Only keys from the 19 feature keys |
| 3 | `SELECT DISTINCT p.scope, p.status FROM facility_reference_ranges f JOIN pipeline_runs p ON p.id = f.pipeline_run_id;` | `all`, `succeeded` |
| 4 | Run another full run; `SELECT count(DISTINCT pipeline_run_id) FROM facility_reference_ranges;` | Rows replaced per facility run (one current run's rows, per TRD 06 layer table) |
| 5 | Try `INSERT` of a row with `low` > `high` as the app role | Rejected by the CHECK constraint |

### TC-095-05 No F0 range has `sex` NULL; null-sex residents are not counted in F0 rows

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT count(*) FROM facility_reference_ranges WHERE feature_key = 'mean_f0_hz' AND sex IS NULL;` | `0` |
| 2 | `SELECT sex, n_residents FROM facility_reference_ranges WHERE feature_key = 'mean_f0_hz' ORDER BY sex;` | Rows for `F` and `M` only |
| 3 | Compare with `SELECT sex, count(*) FROM residents WHERE cohort = 'longitudinal' AND <OQ-08 inclusion rule> GROUP BY sex;` | Each F0 `n_residents` ≤ the count of that sex; null-sex residents excluded |
| 4 | Set a fixture resident's `sex` to NULL, rerun a full run | F0 `n_residents` for its former sex decreases by 1; no NULL-sex F0 row appears |

### TC-095-06 Every row names the OQ-08 method and has `n_residents` ≥ the OQ-08 minimum N

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT DISTINCT method FROM facility_reference_ranges;` | One non-empty value naming the OQ-08 method as recorded in TRD 24 |
| 2 | `SELECT min(n_residents) FROM facility_reference_ranges;` | ≥ the OQ-08 minimum N |
| 3 | Compare `low`/`high` of 2 features with a hand calculation of the OQ-08 statistic on the fixture residents' adjusted usable values | Equal within float64 precision |

### TC-095-07 TST-186 passes against ranges produced by the new function

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/integration/api/test_admissions.py -q -k "comparison_with_ranges or range_not_available"` | Pass |
| 2 | With ranges from the new function, a new admission whose median of at least one feature is outside its range: `GET /api/v1/admissions` | That item `comparison_status` `outside_range` |
| 3 | Same with all medians inside | `within_range` |
| 4 | Frontend test of `FacilityRangeChart` (`npm run test -- FacilityRangeChart`) | Pass: band and dot rendered per feature |

### TC-095-08 E-23 comparison and E-24 range list return the documented fields

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/admissions/N01/comparison` (clinician) | 200; per feature `feature_key`, `low`, `high`, `resident_value`, `outside_range` (boolean) |
| 2 | `GET /api/v1/admissions/R01/comparison` (a longitudinal resident) | 404 with `type` `urn:echowell:error:RESIDENT_NOT_FOUND` (comparison only for new admissions) |
| 3 | `GET /api/v1/facility/reference-ranges` | 200; each item has `feature_key`, `sex`, `low`, `high`, `method`, `n_residents`, `computed_at` |

### TC-095-09 `/admissions` shows the badges, band-and-dot chart, caption and text table

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `/admissions` as clinician | Table badge "Outside facility range" or "Within facility range" (or "Not enough check-ins yet") per admission |
| 2 | Select N01 | Heading "N01 compared with facility range"; one row per measurement with a grey band from low to high and a dot; a dot outside the band is red with "▲" |
| 3 | Read the caption | "Grey band = usual range across current residents" |
| 4 | Open disclosure "Show comparison as a table" | Columns "Measurement", "Resident value", "Facility range", "Outside range" with "▲ Yes" / "No" |
| 5 | Run the axe check on `/admissions` (`npm run test:e2e:readonly -- --grep admissions`) | 0 serious or critical violations |

### TC-095-10 Note "Future / experimental …" keeps sentences 2–3 until OQ-08 is closed

| Step | Action | Expected Result |
|---|---|---|
| 1 | With OQ-08 Open, open `/admissions` | Note begins "Future / experimental. Not in pipeline test v0.1: the test data has no admission group or facility range yet." followed by the third UX-181 sentence |
| 2 | After OQ-08 is closed and TRD 11 updated | The note reads "Future / experimental." without the second and third sentences |

### TC-095-11 A new admission moves to the Resident list once its own baseline forms (TST-185)

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/integration/api/test_admissions.py -q -k "moves_to_the_resident_list or cohort_change_shares_the_pipeline_transaction"` | Pass |
| 2 | Local: N01 with 15 usable records; post the 16th usable record | `residents.cohort` becomes `longitudinal`; one `audit_logs` row `resident.cohort_changed` |
| 3 | `GET /api/v1/admissions`; `GET /api/v1/residents` | N01 absent from admissions; present in residents with pill "● Usual" |

### TC-095-12 Too few residents or check-ins give no range / `not_enough_checkins`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Use a fixture with fewer residents than the OQ-08 minimum N for one feature; full run | No row for that feature; comparisons needing it stay `range_not_available` |
| 2 | A new admission with fewer usable check-ins than the OQ-08 threshold | `comparison_status` `not_enough_checkins`; badge "Not enough check-ins yet" |
| 3 | `SELECT count(*) FROM alerts a JOIN residents r ON r.id = a.resident_id WHERE r.cohort = 'new_admission';` | `0` (the arm raises no alerts) |

### TC-095-13 R01–R10 validation passes unchanged

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/validation -q` | All pass, 0 failed |

### TC-095-14 Admission endpoints keep their roles and expose study IDs only

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/admissions` without token | 401 |
| 2 | Same with admin, clinician, researcher tokens | 200 each |
| 3 | Inspect E-22..E-24 responses | Study IDs only; `sex` only as F, M or null; no name, room or PII |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/admissions` | 200; `comparison_status` one of `range_not_available`, `not_enough_checkins`, `outside_range`, `within_range` |
| 2 | `GET /api/v1/admissions/{resident_code}/comparison` | 200 with per-feature `low`, `high`, `resident_value`, `outside_range` |
| 3 | `GET /api/v1/facility/reference-ranges` | 200 with `method`, `n_residents`, `computed_at` per row |
| 4 | Any of the three without token | 401 |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | Constraint check query (TC-095-04) | 0 violating rows |
| 2 | F0 NULL-sex rows (TC-095-05) | 0 |
| 3 | `pipeline_run_id` linkage to `scope = all` runs (TC-095-04) | All rows linked |
| 4 | Baseline/score/CUSUM/alert hashes with and without ranges (TC-095-03) | Identical |
| 5 | Alerts for new admissions (TC-095-12) | 0 |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Insert a row with `low` > `high` (TC-095-04) | Rejected by CHECK |
| 2 | Below minimum N (TC-095-12) | No range row; `range_not_available` |
| 3 | Below the check-in threshold (TC-095-12) | `not_enough_checkins` |
| 4 | Comparison for a longitudinal resident (TC-095-08) | 404 `RESIDENT_NOT_FOUND` |
| 5 | Unauthenticated request (TC-095-14) | 401 |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-095-AC-01 | `grep -n "facility_norms" analytics/pipeline.py` returns nothing | TC-095-01 |
| FEAT-095-AC-02 | Pipeline with and without computed ranges yields identical `baselines`, `scores`, `cusum_state` and `alerts` | TC-095-03, TC-095-12 |
| FEAT-095-AC-03 | TST-186 passes against ranges produced by the new function | TC-095-07, TC-095-08, TC-095-09 |
| FEAT-095-AC-04 | No `mean_f0_hz` row has `sex` NULL; null-sex residents not counted in F0 `n_residents` | TC-095-05 |
| FEAT-095-AC-05 | Every row has a non-empty `method` naming the OQ-08 method and `n_residents` ≥ the OQ-08 minimum N | TC-095-06, TC-095-04 |
| FEAT-095-AC-06 | `pytest tests/validation -q` passes unchanged | TC-095-13 |

## Test Data Requirements

- `test_v0_1` seed (R01–R10 contain no new admissions).
- Synthetic new-admission resident N01 (TST-185 fixture) and synthetic longitudinal residents with `sex` F, M and NULL and enough usable sessions for the OQ-08 minimum N.
- Fixture `facility_reference_ranges` rows for the 7 scored features (TST-186) and ranges produced by the new function.
- Study IDs only; no real sex values (OQ-20 consent applies to real residents only).

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| ANL-057, ANL-006 | FEAT-095 | TC-095-01, TC-095-03 |
| FR-205, FR-206 | FEAT-095 | TC-095-03, TC-095-11, TC-095-12 |
| FR-204, TRD 20 §4.6.21, D-76 | FEAT-095 | TC-095-04, TC-095-06, TC-095-08 |
| DB-006 | FEAT-095 | TC-095-03, TC-095-06 |
| OQ-08, AGT-009 | FEAT-095 | TC-095-06, TC-095-12 |
| OQ-20, SEC-122 | FEAT-095 | TC-095-05, TC-095-14 |
| FR-202, E-22, TST-186 | FEAT-095 | TC-095-02, TC-095-07 |
| FR-203, E-23, E-24 | FEAT-095 | TC-095-08 |
| UX-185, UX-189, UX-190, UX-193 | FEAT-095 | TC-095-09 |
| FR-200, UX-181, D-06 | FEAT-095 | TC-095-10 |
| TST-185 | FEAT-095 | TC-095-11 |
| AGT-008 | FEAT-095 | TC-095-13 |
| FEAT-095-FR-01..FEAT-095-FR-11 | FEAT-095 | TC-095-01..TC-095-14 |
