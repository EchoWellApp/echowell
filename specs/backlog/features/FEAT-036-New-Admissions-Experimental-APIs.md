# FEAT-036 New-admissions experimental APIs (GET /admissions, /admissions/{code}/comparison, /facility/reference-ranges)

| Field | Value |
|---|---|
| Epic | Backend API |
| Build phase | Phase 5 (TRD 25) |
| Priority | P1 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-021, FEAT-014 |
| Status | Not Started |

## Purpose

Provide the three read-only endpoints of the experimental New admissions study arm (SRC-11): the list of new-admission residents who do not yet have their own baseline, a per-feature comparison of a selected resident with the facility's reference ranges, and the stored reference ranges with their method, number of residents and computation time. The arm is labelled "Future / experimental study arm", never creates alerts and never touches any CUSUM. How the facility ranges are computed is an open question (OQ-08); in v0.1 no ranges exist and the comparison status is "range not available".

## Business Context

- BR-14 (new-admission arm, experimental): list, comparison and ranges for the page.
- BR-11: new-admission comparisons never raise alarms (FR-206).
- BR-09: once the own baseline forms, the resident leaves this list and is compared only with their own baseline (handled by the cohort transition in FEAT-053; this API simply filters by cohort and baseline state).
- FRs covered (BACKLOG.md): FR-201, FR-202, FR-204, FR-206.

## Referenced TRDs

- TRD 05 API-089 (all roles, experimental header, empty items), API-090 (404 for non-new-admission), API-057, API-100.
- TRD 19 §4.3 E-22, E-23, E-24; schemas `AdmissionRow`, `AdmissionList`, `AdmissionComparison`, `ReferenceRange`, `ReferenceRangeList`, `ComparisonStatus`, `BaselineProgress`.
- TRD 00 VIS-009 (experimental labelling); TRD 11 UX-181..UX-195 (page the API serves), §4.13.5.
- TRD 23 §4.2.21 (`facility_reference_ranges`), §4.3.3 (cohort).
- TRD 07 ANL-057 (range computation outside `run_pipeline`, future).
- TRD 13 TST-185, TST-186; TRD 02 AC-FR-10.
- TRD 24 D-06 (experimental, no alerts), OQ-08 (facility norm definition), OQ-20 (sex values).

## Scope

- Router `backend/api/admissions.py` with `GET /api/v1/admissions`, `GET /api/v1/admissions/{resident_code}/comparison`, `GET /api/v1/facility/reference-ranges`, calling `admission_service.list`, `admission_service.comparison`, `admission_service.ranges`.
- Response header `X-EchoWell-Experimental: true` on all three.
- Comparison status values and per-feature comparison rows from stored `facility_reference_ranges`.

## Out of Scope

- Computing facility reference ranges (`analytics/facility_norms.py`, future research feature FEAT-095, gated on OQ-08).
- The cohort change from `new_admission` to `longitudinal` (pipeline runner, FEAT-053; TST-185).
- The New admissions page, `ExperimentalBanner`, `AdmissionsTable`, `FacilityRangeChart` (FEAT-073).
- Any alert, CUSUM or score for new admissions (none exists).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-036-FR-01 | All three endpoints shall be available to every user role, shall set response header `X-EchoWell-Experimental: true`, and shall return empty `items` (not an error) when no new-admission residents or reference ranges exist. | API-089, VIS-009, D-06 |
| FEAT-036-FR-02 | `GET /admissions` shall list residents of cohort `new_admission` whose own baseline has not formed, each with `resident_code`, `admitted_on`, `checkins_so_far` (usable check-ins since admission), `comparison_status` and `own_baseline_progress` `{n_usable, n_required}`; paged with `meta`. | FR-201; TRD 19 E-22, `AdmissionRow`; UX-184, UX-186 |
| FEAT-036-FR-03 | `comparison_status` shall be `range_not_available` when no `facility_reference_ranges` row exists; otherwise `not_enough_checkins`, `outside_range` (at least one compared feature value outside its range) or `within_range` (all within). | FR-202; TRD 19 E-22, `ComparisonStatus`; UX-185 |
| FEAT-036-FR-04 | `GET /admissions/{resident_code}/comparison` shall return `AdmissionComparison` `{meta, resident_code, comparison_status, features[]}` with, per feature, `feature_key`, `resident_value` (median of the resident's usable check-ins so far), `low`, `high` and `outside_range`; a resident that is unknown or not of cohort `new_admission` returns 404 `RESIDENT_NOT_FOUND`. | API-090; TRD 19 E-23, `AdmissionComparison` |
| FEAT-036-FR-05 | `GET /facility/reference-ranges` shall return the stored ranges (`feature_key`, `low`, `high`, `method`, `n_residents`, `computed_at`, `pipeline_run_id`) paged with `meta`. | FR-204; TRD 19 E-24, `ReferenceRange` |
| FEAT-036-FR-06 | The endpoints shall be read-only and shall never create alerts, scores or CUSUM rows or change any resident's data. | FR-206, D-06 |

## Inputs

- Bearer JWT (admin, clinician, researcher); path `resident_code`; query `limit`, `offset`.
- Tables `residents` (`cohort`, `admitted_on`, `status`), `processed_sessions`, `raw_sessions` or `processed_sessions.adjusted_features` (values for the median; see Implementation Notes), `epochs`, `baselines`, `facility_reference_ranges`, `config_parameters` (`baseline_n`).

## Outputs

- 200 `AdmissionList`, `AdmissionComparison`, `ReferenceRangeList` with header `X-EchoWell-Experimental: true`; 404 `RESIDENT_NOT_FOUND`.

## Data Flow

1. Auth: any user role.
2. List: select residents with cohort `new_admission` and no frozen baseline in the current epoch; count usable sessions since `admitted_on`; compute progress; determine status from the presence of ranges and the comparison of medians.
3. Comparison: verify cohort (404 otherwise); compute medians of the resident's usable sessions per feature with a stored range; compare with `low`/`high`.
4. Ranges: select stored rows and map them.

## Dependencies

- FEAT-021 (Role-based authorization matrix): all-role access.
- FEAT-014 (Read-model derivations): baseline progress and usable-session counts.
- Downstream: FEAT-038 (OpenAPI), FEAT-073 (page), FEAT-095 (future range computation).

## Database Impact

- Tables read: `residents`, `processed_sessions` (`status`, `local_date`, `adjusted_features`, `resident_id`), `epochs`, `baselines`, `facility_reference_ranges` (all columns of TRD 20 §4.6.21), `config_parameters`.
- Tables written, created or altered: none.

## API Impact

- Exposed: `GET /api/v1/admissions` (E-22), `GET /api/v1/admissions/{resident_code}/comparison` (E-23), `GET /api/v1/facility/reference-ranges` (E-24).
- `X-EchoWell-Experimental` is listed in CORS `expose_headers` (API-101, FEAT-019).

## Frontend Impact

None in this feature. Consumers: `AdmissionsTable` (`getAdmissions()`), `FacilityRangeChart` (`getAdmissionComparison(code)`, `getReferenceRanges()`) and `ExperimentalBanner` on `/admissions` (TRD 04 §4.6.2), delivered by FEAT-073.

## Analytics Impact

No pipeline stage. The only calculation is the median of a new-admission resident's usable check-ins per feature and a range comparison; the facility-norm method itself is undefined (OQ-08) and outside the MVP (ANL-057).

## Security Requirements

- Bearer JWT; all user roles 200; API key and anonymous 401 (TRD 12 §4.6).
- No PII: study IDs only; `sex` is used only for range selection and not returned by these endpoints.

## Error Handling

- Unknown resident or cohort ≠ `new_admission` on the comparison path → 404 `RESIDENT_NOT_FOUND` (API-090).
- No residents or no ranges → 200 with empty `items` and, for a listed resident, `range_not_available`.
- Invalid `limit`/`offset` → 422 `INVALID_QUERY_PARAMETER`.

## Logging Requirements

- Access log per request (LOG-010); no audit rows.

## Testing Requirements

- Integration (`tests/integration/api/test_admissions.py`, marker `integration`): DS-07-like state with no new admissions → three 200 responses with empty `items` and the experimental header (AC-FR-10 API part); comparison for a longitudinal resident → 404; a fixture new-admission resident without ranges → `range_not_available`.
- TST-185 (cohort transition across `/admissions` and `/residents`) runs when FEAT-053 provides the transition; this feature must list and filter correctly for it.
- TST-186 (Should): with fixture ranges for the 7 scored features, `outside_range` when one median is outside its range and `within_range` otherwise; comparison returns `low`, `high`, `resident_value`, `outside_range`.
- Contract: TST-061, TST-064 (`meta` on `AdmissionList`, `AdmissionComparison`, `ReferenceRangeList`).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-036-AC-01 | With DS-07 loaded, `GET /api/v1/admissions` returns 200 `{"items": [], "total": 0, ...}` with `meta` and header `X-EchoWell-Experimental: true`; `GET /facility/reference-ranges` returns 200 with empty `items` and the same header. | API-089, TRD 19 E-22, E-24 |
| FEAT-036-AC-02 | `GET /admissions/R09/comparison` (R09 is longitudinal) returns 404 `RESIDENT_NOT_FOUND`. | API-090 |
| FEAT-036-AC-03 | A fixture new-admission resident N01 with 3 usable sessions and no reference ranges is listed with `comparison_status` `range_not_available` and `own_baseline_progress` 3 of 16 (test_v0_1). | FR-201, FR-202 |
| FEAT-036-AC-04 | With fixture ranges for the 7 scored features and N01's median of `loudness_dbfs` below its `low`, the list shows `outside_range` and the comparison item for `loudness_dbfs` has `outside_range` true; with all medians inside, `within_range`. | TST-186, FR-202 |
| FEAT-036-AC-05 | After calling all three endpoints, the row counts of `alerts`, `scores` and `cusum_state` are unchanged. | FR-206 |
| FEAT-036-AC-06 | Every user role receives 200 on all three endpoints; an API key receives 401. | API-089, TRD 13 Table 4.13-A |

## Definition of Done

- Three endpoints with the experimental header and TRD 19 schemas; integration tests pass; TST-186 passes.
- Requirement markers (TST-013); coverage ≥ 85 %; OpenAPI drift check passes.
- The OQ-08 gaps below are listed in the batch report.

## Implementation Notes

- OQ-08 gaps (do not guess the method): the TRDs do not define the minimum number of check-ins that separates `not_enough_checkins` from a comparison, whether the resident value uses raw or morning-adjusted values, which features are compared (TST-186 uses the 7 scored features; `AdmissionComparison.feature_key` admits all 19), or how a `sex`-specific range is chosen (OQ-20). Implement `range_not_available` (the v0.1 state) fully; for the other statuses implement only what TST-186 fixes (median outside any stored range → `outside_range`, otherwise `within_range`) and raise the remaining points for TRD 24 per AGT-009.
- TRD conflict: TRD 04 FE-100 names the band fields `facility_low` / `facility_high`, while TRD 19 `AdmissionComparison` uses `low` / `high`; the API follows TRD 19 (TRD 05 §1); report it so FEAT-073 maps the generated types.
- Select residents with SQL on cohort and baseline existence; the list is expected to be empty for DS-07 (UX-194).
