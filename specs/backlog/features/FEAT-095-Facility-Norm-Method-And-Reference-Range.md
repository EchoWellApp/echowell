# FEAT-095 Facility norm method and reference-range computation for the new-admission arm

| Field | Value |
|---|---|
| Epic | Analytics Engine |
| Build phase | Future research (TRD 25) |
| Priority | P2 |
| Complexity | High |
| MVP status | Future |
| Dependencies | FEAT-036, FEAT-052, FEAT-073 |
| Status | Not Started |
| Gate | Gated on OQ-08 and OQ-20 |

## Purpose

Give the experimental new-admission arm a facility norm to compare against. A new resident has no own baseline yet, so their first check-ins are compared with the facility's usual range per feature. The TRDs fix where this lives (a separate pure function outside `run_pipeline`, planned module `analytics/facility_norms.py`, writing `facility_reference_ranges` with method, number of residents and computation time) and that it never influences any resident's own baseline, score or alarm. The statistic, the residents included, the minimum N, the own-baseline length for new admissions and any sex-specific F0 ranges are open (OQ-08, OQ-20). Once decided, the `/admissions` page shows "Outside facility range" / "Within facility range" instead of "Facility range not available yet".

## Business Context

- BR-14 (new-admission study arm, experimental): FR-200..FR-206; the page exists in the MVP with comparison status `range_not_available` while no range exists (FR-202, E-22).
- FR-204: facility reference ranges are read from `facility_reference_ranges` with their method, number of residents and computation time; the method is not defined in the MVP (OQ-08).
- RSK-13: between-person comparison is weakly supported by the systematic review; the arm stays labelled "Future / experimental" (TRD 11 UX-181), raises no alerts and never feeds the longitudinal pipeline (D-06, FR-206).

## Referenced TRDs

- TRD 07 ANL-057 (extension point), ANL-006 (fixed stage order of `run_pipeline`), ANL-053, ANL-054 (run logging without feature values).
- TRD 12 SEC-122 (`sex` stored only for F0 ranges).
- TRD 02 FR-200, FR-201, FR-202, FR-203, FR-204, FR-205, FR-206.
- TRD 20 §4.6.21 `facility_reference_ranges` DDL and constraints, indexes `facility_reference_ranges_lookup_idx`, `facility_reference_ranges_run_idx`, grants (app role SELECT/INSERT/UPDATE/DELETE), `residents.sex` (F/M/NULL).
- TRD 06 DB-006 (ranges computable from `raw_sessions`, reference tables and config), §4 layer table ("ranges: per facility run").
- TRD 19 E-22, E-23, E-24 (`AdmissionList`, `AdmissionComparison`, `ReferenceRangeList`, `ComparisonStatus`).
- TRD 05 API-089, API-090 (admission service read paths).
- TRD 11 UX-181, UX-185, UX-186, UX-189..UX-194.
- TRD 13 TST-185, TST-186.
- TRD 24 OQ-08 (gate), OQ-20 (gate), RSK-13, D-06, D-64.

## Scope

Decided by the TRDs:

- A pure function in the planned module `analytics/facility_norms.py` (created only when OQ-08 is resolved), outside `run_pipeline`, that reads adjusted values of usable sessions and produces facility reference ranges per `feature_key` (one of the 19 feature keys) with `low`, `high` (low ≤ high), `method` (1–200 characters), `n_residents` (≥ 1), `sex` (`F`, `M` or NULL) and `computed_at`.
- Persistence: rows in `facility_reference_ranges` linked to `facilities` and to a `pipeline_runs` row (`pipeline_run_id` NOT NULL), unique on (`facility_id`, `feature_key`, `sex`, `pipeline_run_id`), replaced per facility run (TRD 06 layer table).
- Facility F0 ranges computed only per known sex, excluding residents with null sex (OQ-20 interim decision).
- Consumers already exist: E-22 `comparison_status` changes from `range_not_available` to `not_enough_checkins` / `outside_range` / `within_range`; E-23 per-feature `low`, `high`, `resident_value`, `outside_range`; E-24 lists the ranges with method, N and time; `FacilityRangeChart` renders band and dot.
- Isolation: no range ever influences any resident's own baseline, score, CUSUM or alerts; the arm raises no alerts.

Blocked on OQ-08 and OQ-20 (not decided here):

- OQ-08: the statistic or percentiles that define `low` and `high`, which residents form the norm (cohorts, minimum days, epochs), the minimum N of residents, how many days or check-ins a new admission needs before comparison (`not_enough_checkins` threshold) and how many for its own baseline (the TRDs show N = `baseline_n` on the page, UX-186, UX-192, but OQ-08 lists the own-baseline length as open), and the rule that sets `outside_range` (FR-202 implies "at least one feature outside", TST-186 tests that rule with fixture ranges).
- OQ-20: which residents' sex values are known and consented; without them no F0 range is computed.
- Trigger and run linkage: the DDL requires `pipeline_run_id`, but the TRDs do not say which run (trigger, scope) computes the ranges or how often. To be settled in TRD 24 with OQ-08.

Trigger for starting: OQ-08 answered in TRD 24 by Shaba Rahavi and the PI (statistic, residents, minimum N, own-baseline length, run linkage), and OQ-20 answered for sex values if F0 ranges are wanted. Until then the banner's second line (UX-181) stays and the page shows "Facility range not available yet".

## Out of Scope

- Any change to the longitudinal pipeline or `run_pipeline` stage order (ANL-006).
- Alerts or CUSUM for new admissions (FR-206).
- The admissions API and page themselves (FEAT-036, FEAT-073) beyond verifying they display computed ranges.
- Recording sex values (consent and data collection, OQ-20).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-095-FR-01 | Facility reference ranges shall be computed by a separate pure function outside `run_pipeline` in the planned module `analytics/facility_norms.py`, created only when OQ-08 is resolved. | ANL-057, OQ-08 |
| FEAT-095-FR-02 | The function shall read adjusted values of usable sessions and shall never influence any resident's own baseline, score or alarm. | ANL-057, FR-205, FR-206 |
| FEAT-095-FR-03 | Each range row shall be stored in `facility_reference_ranges` with `facility_id`, `feature_key` (one of the 19 feature keys), `sex` (F, M or NULL), `low` ≤ `high`, `method` (1–200 characters), `n_residents` ≥ 1, `computed_at` and `pipeline_run_id`. | FR-204, TRD 20 §4.6.21 |
| FEAT-095-FR-04 | Ranges shall be computable solely from `raw_sessions`, the reference tables and the active `config_parameters` profile. | DB-006 |
| FEAT-095-FR-05 | The statistic, residents included, minimum N and the new-admission thresholds shall be those recorded in TRD 24 when OQ-08 closes; the implementer shall not choose them. | OQ-08, AGT-009 |
| FEAT-095-FR-06 | Facility F0 ranges shall be computed only per known sex and exclude residents with null sex. | OQ-20 (interim decision) |
| FEAT-095-FR-07 | `GET /api/v1/admissions` shall return `comparison_status` `outside_range` when at least one feature median is outside its range and `within_range` otherwise once ranges exist, `not_enough_checkins` below the OQ-08 threshold, and `range_not_available` when no range row exists. | FR-202, E-22, TST-186 |
| FEAT-095-FR-08 | `GET /api/v1/admissions/{resident_code}/comparison` shall return per-feature `low`, `high`, `resident_value` and `outside_range`; `GET /api/v1/facility/reference-ranges` shall list method, N and computation time. | FR-203, FR-204, E-23, E-24 |
| FEAT-095-FR-09 | The `/admissions` page shall show the band (`--color-range-band`) and dot per feature with the caption "grey band = usual range across current residents" and the text-table alternative. | FR-203, UX-189, UX-190, UX-193 |
| FEAT-095-FR-10 | A new admission shall move to the Resident list once its own baseline has formed and be compared only with its own baseline from then on. | FR-205, TST-185 |
| FEAT-095-FR-11 | The note "Future / experimental. Not in pipeline test v0.1: …" shall stay; its second and third sentences shall be removed only when OQ-08 is closed. | FR-200, UX-181, D-06 |

## Inputs

- Usable sessions with adjusted values (pipeline output), residents with cohort and `sex`, facility row, active profile.
- The OQ-08 and OQ-20 decisions.

## Outputs

- `analytics/facility_norms.py` with unit tests; backend service code that persists ranges with a `pipeline_runs` row (linkage per the OQ-08 decision).
- `facility_reference_ranges` rows; non-empty E-24 responses; comparison statuses other than `range_not_available`.

## Data Flow

`raw_sessions` → pipeline (unchanged) → usable sessions with adjusted values → facility-norm function (outside `run_pipeline`) → ranges per feature (and sex for F0) → backend persists rows with `pipeline_run_id` → E-22/E-23/E-24 → `/admissions` table badge and `FacilityRangeChart`.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-036, FEAT-052, FEAT-073

- [FEAT-036](FEAT-036-New-Admissions-Experimental-APIs.md) New-admissions experimental APIs (E-22..E-24 read the ranges).
- [FEAT-052](FEAT-052-Pipeline-Orchestrator-Run-Pipeline-Determinism-And.md) Pipeline orchestrator (the norm function stays outside it).
- [FEAT-073](FEAT-073-New-Admissions-Page.md) New admissions page (displays the ranges).

Gate: OQ-08 (facility norm definition) and OQ-20 (sex values).

Features that build directly on this one (BACKLOG.md §4): none.

## Database Impact

- Tables written: `facility_reference_ranges` (INSERT; replaced per facility run), `pipeline_runs` (the linked run row).
- Tables read: `processed_sessions` (adjusted features, status), `residents` (cohort, sex), `facilities`, `config_parameters`.
- Tables created or altered: none (the table exists, TRD 20 §4.6.21); a schema change would only follow an OQ-08 decision that the DDL cannot hold.

## API Impact

- Endpoints consumed or exposed: E-22 `GET /api/v1/admissions`, E-23 `GET /api/v1/admissions/{resident_code}/comparison`, E-24 `GET /api/v1/facility/reference-ranges`; behaviour changes only through data (ranges present). No new endpoint.

## Frontend Impact

- `/admissions`: `AdmissionsTable` badges and `FacilityRangeChart` show real ranges (UX-185, UX-189..UX-193); banner line 2 removed when OQ-08 closes (UX-181). No new component.

## Analytics Impact

- New pure function (statistic per OQ-08) computing per-feature `low`/`high` over adjusted values of the selected residents' usable sessions; per-sex F0 ranges (OQ-20).
- No change to baseline, scoring, CUSUM or alerts (ANL-057).

## Security Requirements

- Read endpoints keep their roles (admin, clinician, researcher, E-22..E-24).
- `sex` is stored only as F, M or NULL and only where consented (SEC-122, OQ-20).
- Study IDs only; no PII (AGT-017).

## Error Handling

- Too few residents for the OQ-08 minimum N → no row for that feature (status stays `range_not_available` for comparisons needing it); exact handling per OQ-08.
- DDL constraint violations (low > high, n < 1, invalid feature key) are defects caught by tests.

## Logging Requirements

- `analytics/` does not log; the backend logs the run with `pipeline_run_id` and counts, without feature values (ANL-053, ANL-054).

## Testing Requirements

- Unit tests of the norm function (purity, determinism, exclusion of null-sex residents from F0 ranges, never touching baselines or scores).
- Integration: TST-186 (fixture ranges → `outside_range` / `within_range`, comparison fields, `FacilityRangeChart` rendering); TST-185 (cohort transition) still passes.
- Regression: `pytest tests/validation -q` unchanged (R01–R10 contain no new admissions).
- Method-specific expected values are written from the OQ-08 decision.

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-095-AC-01 | `grep -n "facility_norms" analytics/pipeline.py` returns nothing. Verified by: Inspection (run the command in the criterion and check its output). | ANL-057 |
| FEAT-095-AC-02 | Running the pipeline with and without computed ranges yields identical `baselines`, `scores`, `cusum_state` and `alerts`. Verified by: Test (Unit tests of the norm function (purity, determinism, exclusion of null-sex residents from F0 ranges, never touching baselines or scores)). | ANL-057, FR-206 |
| FEAT-095-AC-03 | TST-186 passes against ranges produced by the new function. | TST-186, FR-202, FR-203 |
| FEAT-095-AC-04 | No `facility_reference_ranges` row for `mean_f0_hz` has `sex` NULL, and residents with null sex are not counted in any F0 row's `n_residents`. Verified by: Integration (TST-186). | OQ-20 interim decision |
| FEAT-095-AC-05 | Every stored row has a non-empty `method` naming the OQ-08 method and `n_residents` ≥ the OQ-08 minimum N. Verified by: Test (Method-specific expected values are written from the OQ-08 decision). | FR-204, OQ-08 |
| FEAT-095-AC-06 | `pytest tests/validation -q` passes unchanged. | AGT-008 |

## Definition of Done

- All FEAT-095 acceptance criteria pass.
- Gates satisfied (OQ-08 answered, OQ-20 answered where F0 ranges are used); all FEAT-095 acceptance criteria pass; TRD 07/TRD 02/TRD 11 updated through a TRD change with the decided method before code merges.

## Implementation Notes

- The function's signature should follow the other stage contracts (frozen dataclasses in, frozen dataclasses out, config passed explicitly) so it stays pure and testable.
- `UNIQUE NULLS NOT DISTINCT` requires PostgreSQL ≥ 15 (TRD 20 Implementation Notes); keep PostgreSQL 16.
- Resolved (TRD 24 D-76, TRD 07 ANL-057): the pipeline service calls the facility-norm function after `run_pipeline` within a full (`scope = all`) run and stamps every range row with that run's `pipeline_run_id` (NOT NULL in TRD 20); the computation method itself stays with OQ-08.
