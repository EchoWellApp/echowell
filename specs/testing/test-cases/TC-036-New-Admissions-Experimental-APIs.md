# New-admissions experimental APIs (GET /admissions, /admissions/{code}/comparison, /facility/reference-ranges)

## Feature Description

Three read-only endpoints serve the experimental New admissions study arm ("Future / experimental study arm"): `GET /api/v1/admissions` (TRD 19 E-22) lists new-admission residents without their own baseline, with `admitted_on`, `checkins_so_far`, `comparison_status` and `own_baseline_progress`; `GET /api/v1/admissions/{resident_code}/comparison` (E-23) compares a new-admission resident's per-feature median with the facility reference ranges; `GET /api/v1/facility/reference-ranges` (E-24) returns the stored ranges with method, number of residents and computation time. Every response carries `X-EchoWell-Experimental: true`, empty lists are not errors, and the arm never creates alerts, scores or CUSUM rows. In v0.1 no ranges exist, so the status is `range_not_available`. Source: FEAT-036; TRD 05 API-089, API-090; TRD 00 VIS-009; TRD 24 D-06, OQ-08, OQ-29 (interim comparison rules).

## Preconditions

1. Local Docker Compose stack running; environment file from `.env.development.example` (`PIPELINE_PROFILE=test_v0_1`, `baseline_n` 16).
2. **DS-07 state:** `docker compose exec backend python -m backend.cli seed test_v0_1` (no new-admission resident, no reference ranges).
3. `API=http://localhost:8000/api/v1`; tokens `ADMIN`, `CLIN`, `RES` from `POST $API/auth/login` with the `SEED_*` passwords; `KEY` = the ingest API key from the environment file.
4. `psql` read access; local development stack with dev requirements for the `pytest` cases that use the fixture new-admission resident N01 (`tests/integration/api/test_admissions.py`).

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-036-01 | DS-07: empty admissions list and empty reference ranges, both with the experimental header and `meta` | High | Positive |
| TC-036-02 | Comparison for longitudinal R09 returns 404 `RESIDENT_NOT_FOUND` | High | Negative |
| TC-036-03 | Fixture N01 with 3 usable sessions and no ranges: `range_not_available`, progress 3 of 16 | High | Positive |
| TC-036-04 | Fixture ranges: `outside_range` when N01's loudness median is below `low`; `within_range` when all inside | High | Analytics |
| TC-036-05 | Calling all three endpoints changes no `alerts`, `scores` or `cusum_state` row | High | Database |
| TC-036-06 | Role access: every user role 200 on all three; API key 401 | High | Security |
| TC-036-07 | Comparison for unknown resident R11 returns 404; experimental header present on 200 responses | Medium | Negative |
| TC-036-08 | Invalid paging returns 422 `INVALID_QUERY_PARAMETER` | Medium | Negative |
| TC-036-09 | Schemas, `meta` and CORS exposure of `X-EchoWell-Experimental` | Medium | API |
| TC-036-10 | New-admission cohort is not listed as longitudinal (`GET /residents?cohort=new_admission`) | Low | Positive |

### TC-036-01 DS-07: empty admissions list and empty reference ranges, both with the experimental header and `meta`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `curl -s -i $API/admissions -H "Authorization: Bearer $CLIN"` | HTTP 200; header `X-EchoWell-Experimental: true`; body `items` [], `total` 0, `limit` 50, `offset` 0, `meta` with seven fields |
| 2 | `curl -s -i $API/facility/reference-ranges -H "Authorization: Bearer $CLIN"` | HTTP 200; header `X-EchoWell-Experimental: true`; `items` []; `total` 0; `meta` present |
| 3 | `SELECT count(*) FROM residents WHERE cohort='new_admission'; SELECT count(*) FROM facility_reference_ranges;` | 0 and 0 |

### TC-036-02 Comparison for longitudinal R09 returns 404 `RESIDENT_NOT_FOUND`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `curl -s -i $API/admissions/R09/comparison -H "Authorization: Bearer $CLIN"` | HTTP 404; `type` "urn:echowell:error:RESIDENT_NOT_FOUND"; `title` "Resident not found" |
| 2 | `pytest tests/integration/api/test_admissions.py::test_comparison_only_for_new_admissions -q` | Passes (longitudinal R01 and unknown R99 both 404 `RESIDENT_NOT_FOUND`) |

### TC-036-03 Fixture N01 with 3 usable sessions and no ranges: `range_not_available`, progress 3 of 16

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/integration/api/test_admissions.py::test_range_not_available -q` | Passes. The fixture adds new-admission resident N01 (sex F, admitted 2026-10-20) with 3 usable check-ins on D01 and no `facility_reference_ranges` rows; the test asserts the list contains N01 with `admitted_on` "2026-10-20", `checkins_so_far` 3, `comparison_status` "range_not_available", `own_baseline_progress` `{"n_usable": 3, "n_required": 16}` |
| 2 | Read the test's comparison assertions | `GET /admissions/N01/comparison` returns 200 with the experimental header, `comparison_status` "range_not_available" and 7 `features` in contract order (loudness_dbfs … voiced_fraction), each with `resident_value` set and `low`, `high`, `outside_range` null; row counts of `alerts`, `scores`, `cusum_state` unchanged |

### TC-036-04 Fixture ranges: `outside_range` when N01's loudness median is below `low`; `within_range` when all inside

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/integration/api/test_admissions.py::test_comparison_with_ranges -q` | Passes (TST-186). With fixture ranges for the 7 scored features and N01's `loudness_dbfs` median below its `low`: list `comparison_status` "outside_range"; comparison item `loudness_dbfs` has `outside_range` true with `resident_value`, `low`, `high`; with all medians inside their ranges: `within_range` |
| 2 | Confirm the interim rule (OQ-29) in the code: `grep -n "MIN_CHECKINS" backend/services/admission_service.py` | `MIN_CHECKINS = 5`: fewer than 5 usable check-ins with ranges present gives `not_enough_checkins` |

### TC-036-05 Calling all three endpoints changes no `alerts`, `scores` or `cusum_state` row

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT (SELECT count(*) FROM alerts), (SELECT count(*) FROM scores), (SELECT count(*) FROM cusum_state);` | DS-07: 2, 98, and the `cusum_state` count noted |
| 2 | Call `GET /admissions`, `GET /admissions/R09/comparison`, `GET /facility/reference-ranges` three times each as admin | 200, 404, 200 |
| 3 | Repeat the count query | Identical counts |
| 4 | `pytest tests/integration/api/test_admissions.py::test_range_not_available -q` | Passes (also asserts the counts with a new-admission resident present) |

### TC-036-06 Role access: every user role 200 on all three; API key 401

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET /admissions` and `GET /facility/reference-ranges` with each of `$ADMIN`, `$CLIN`, `$RES` | 200 for all six |
| 2 | `GET /admissions/R09/comparison` with each role | 404 `RESIDENT_NOT_FOUND` (authorised; resident not eligible) |
| 3 | All three paths with `X-API-Key: $KEY` | 401 `NOT_AUTHENTICATED` |
| 4 | `pytest tests/integration/api/test_admissions.py::test_empty_state -q` | Passes (admin, clinician and researcher each get 200 with the experimental header on `/admissions` and `/facility/reference-ranges`) |

### TC-036-07 Comparison for unknown resident R11 returns 404; experimental header present on 200 responses

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET $API/admissions/R11/comparison` | HTTP 404 `RESIDENT_NOT_FOUND` |
| 2 | Re-check the headers of TC-036-01 steps 1–2 | `X-EchoWell-Experimental: true` on both 200 responses |

### TC-036-08 Invalid paging returns 422 `INVALID_QUERY_PARAMETER`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET $API/admissions?limit=0`, `GET $API/admissions?offset=-1`, `GET $API/facility/reference-ranges?limit=501` | 422 `INVALID_QUERY_PARAMETER` each |

### TC-036-09 Schemas, `meta` and CORS exposure of `X-EchoWell-Experimental`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Validate the bodies of TC-036-01 against `AdmissionList` and `ReferenceRangeList` from `GET $API/openapi.json` | Valid; `meta` present |
| 2 | `curl -s -i $API/admissions -H "Origin: http://localhost:3000" -H "Authorization: Bearer $CLIN"` | `Access-Control-Expose-Headers` includes `X-EchoWell-Experimental` |
| 3 | Inspect `AdmissionRow` and `ReferenceRange` schemas | No `sex` or other demographic field returned; residents only by `resident_code` |

### TC-036-10 New-admission cohort is not listed as longitudinal (`GET /residents?cohort=new_admission`)

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET $API/residents?cohort=new_admission` (DS-07) | 200; `items` []; matches the empty admissions list |
| 2 | `GET $API/residents` | 10 longitudinal residents, none listed on `/admissions` |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/admissions` | 200 `AdmissionList`; `X-EchoWell-Experimental: true` |
| 2 | `GET /api/v1/admissions/{code}/comparison` | 200 `AdmissionComparison` `{meta, resident_code, comparison_status, features[]}` (`feature_key`, `resident_value`, `low`, `high`, `outside_range`); 404 `RESIDENT_NOT_FOUND` for unknown or non-new-admission resident |
| 3 | `GET /api/v1/facility/reference-ranges` | 200 `ReferenceRangeList` (`feature_key`, `low`, `high`, `method`, `n_residents`, `computed_at`, `pipeline_run_id`) |
| 4 | `comparison_status` values | `range_not_available`, `not_enough_checkins`, `outside_range`, `within_range` |
| 5 | Auth | All user roles 200; API key / anonymous 401 |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT count(*) FROM residents WHERE cohort='new_admission';` | 0 for DS-07 (empty list expected) |
| 2 | `SELECT count(*) FROM facility_reference_ranges;` | 0 for DS-07 (`range_not_available` state) |
| 3 | `alerts`, `scores`, `cusum_state` counts | Unchanged by any call |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Comparison for longitudinal R09 / unknown R11 | 404 `RESIDENT_NOT_FOUND` |
| 2 | Invalid paging | 422 `INVALID_QUERY_PARAMETER` |
| 3 | API key / anonymous | 401 |
| 4 | `docker compose stop db`, then `GET /admissions` | 503 `SERVICE_UNAVAILABLE`; `docker compose start db` afterwards |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-036-AC-01 | DS-07 `GET /admissions` 200 `{"items": [], "total": 0, ...}` with `meta` and `X-EchoWell-Experimental: true`; `GET /facility/reference-ranges` 200, empty `items`, same header | TC-036-01 |
| FEAT-036-AC-02 | `GET /admissions/R09/comparison` returns 404 `RESIDENT_NOT_FOUND` | TC-036-02 |
| FEAT-036-AC-03 | Fixture N01 with 3 usable sessions and no ranges: `range_not_available`, `own_baseline_progress` 3 of 16 | TC-036-03 |
| FEAT-036-AC-04 | Fixture ranges with N01 loudness median below `low`: list `outside_range`, comparison `loudness_dbfs` `outside_range` true; all inside: `within_range` | TC-036-04 |
| FEAT-036-AC-05 | Counts of `alerts`, `scores`, `cusum_state` unchanged after calling all three endpoints | TC-036-05 |
| FEAT-036-AC-06 | Every user role 200 on all three endpoints; API key 401 | TC-036-06 |

## Test Data Requirements

- DS-07 (`seed test_v0_1`): no new-admission residents, no reference ranges (TRD 11 §4.13.5).
- Synthetic fixture N01 (new admission, sex F, admitted 2026-10-20, usable check-ins on D01) and fixture reference ranges for the 7 scored features, created by `tests/integration/api/test_admissions.py`.
- Synthetic codes R09 (longitudinal) and R11 (not enrolled).
- Environment: `SEED_*` passwords and `SEED_INGEST_API_KEY` from the environment file.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-036-FR-01 (API-089, VIS-009, D-06) | FEAT-036 | TC-036-01, TC-036-06, TC-036-07 |
| FEAT-036-FR-02 (FR-201; UX-184, UX-186) | FEAT-036 | TC-036-03, TC-036-10 |
| FEAT-036-FR-03 (FR-202; UX-185) | FEAT-036 | TC-036-03, TC-036-04 |
| FEAT-036-FR-04 (API-090) | FEAT-036 | TC-036-02, TC-036-04, TC-036-07 |
| FEAT-036-FR-05 (FR-204) | FEAT-036 | TC-036-01, TC-036-09 |
| FEAT-036-FR-06 (FR-206, D-06) | FEAT-036 | TC-036-05 |
| TST-185 | FEAT-036 | TC-036-10 (listing and filtering by cohort) |
| TST-186 | FEAT-036 | TC-036-04 |
| AC-FR-10 (API part) | FEAT-036 | TC-036-01 |
| TST-061, TST-064 | FEAT-036 | TC-036-09 |
| TRD 13 Table 4.13-A (admissions rows) | FEAT-036 | TC-036-06 |
