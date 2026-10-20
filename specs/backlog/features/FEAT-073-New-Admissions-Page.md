# FEAT-073 New admissions page (experimental)

| Field | Value |
|---|---|
| Epic | Frontend |
| Build phase | Phase 8 (TRD 25) |
| Priority | P1 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-064, FEAT-036 |
| Status | Not Started |

## Purpose

Implement `/admissions` (SRC-11), the experimental page for the new-admission study arm: the "Future / experimental study arm" banner and note, the header and intro, the table of new-admission residents with comparison status and own-baseline progress, the per-resident `FacilityRangeChart` (resident value dot against the grey facility band `--color-range-band`) with its table alternative, the "No new admissions" and "Facility range not available yet" states, and the default footer. The pipeline test data has no admission arm, so the reference rendering is the empty state.

## Business Context

- BR-14 (new residents are compared with the facility's usual range until their own baseline forms, then move to the main list) with VIS-009 (always labelled experimental) and D-06 (no alerts, isolated from the longitudinal pipeline).
- OQ-08 (facility norm method undefined in the MVP): the page renders whatever ranges the API returns and states that the arm is not in pipeline test v0.1.
- FRs covered (BACKLOG.md): FR-200, FR-201, FR-202, FR-203, FR-205, FR-207.

## Referenced TRDs

- TRD 04 FE-100 (`FacilityRangeChart` band, dot, accent and "▲" outside), FE-189 (E2E `admissions.spec.ts`), §4.8 `AdmissionsTable`, `FacilityRangeChart`, `ExperimentalBanner`, `BackLink`, §4.6.2 `getAdmissions`, `getAdmissionComparison`, `getReferenceRanges`, §4.12 `--color-range-band`.
- TRD 11 UX-180..UX-195 (back link, banner, header, table, columns, comparison badges, own-baseline text, selection, cohort transition, comparison chart, caption, labels, transition sentence, table alternative, empty states, range method line), UX-260..UX-264 (reference rendering incl. §4.13.5), UX-243 (760px table container).
- TRD 19 E-22, E-23, E-24 (experimental endpoints, `ComparisonStatus`).
- TRD 00 VIS-009; TRD 02 FR-200..FR-203, FR-205, FR-207; TRD 24 D-06, D-44, OQ-08.
- TRD 13 E2E-13, TST-090, TST-186.

## Scope

- `app/(protected)/admissions/page.tsx`: `BackLink`, `ExperimentalBanner`, header, `AdmissionsTable`, comparison section with `FacilityRangeChart` and its disclosure table, default footer.
- Queries `getAdmissions()` (`limit=500`), `getAdmissionComparison(code)` for the selected resident, `getReferenceRanges()` for the method line.
- Selected resident held in component state.

## Out of Scope

- The experimental endpoints and the cohort transition (FEAT-036, FEAT-053).
- Facility norm computation (FEAT-095, OQ-08/OQ-20).
- Any alerting for new admissions (never, FR-206, D-06).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-073-FR-01 | The page shall start with "← Back to all residents" and directly below a banner (2px dashed accent border, accent text, 600) with line 1 "▲ Future / experimental study arm" and line 2 "Not in pipeline test v0.1 — the test data has no admission arm or facility norm yet. Open question for Shaba and the PI." (kept until OQ-08 closes). | UX-180, UX-181, FR-200, VIS-009, OQ-08 |
| FEAT-073-FR-02 | The header shall show `<h1>` "New admissions" and "New residents don’t have their own baseline yet, so their first check-ins are compared with the facility’s usual range." with a 2px ink bottom border. | UX-182 |
| FEAT-073-FR-03 | The table shall have columns "Resident", "Admitted" ("<Mon D>"), "Check-ins so far" (usable since admission), "Compared with facility range", "Own baseline" ("<n> of <N> usable check-ins", N = `meta.baseline_n`), header background `--color-table-header`, `min-width: 760px` in a horizontally scrolling, keyboard-focusable container. | UX-183, UX-184, UX-186, FR-201, UX-243 |
| FEAT-073-FR-04 | The comparison badge shall read "▲ Outside facility range" (2px accent, accent text, 600) for `outside_range`, "Within facility range" (1px border) for `within_range`, "Not enough check-ins yet" (1px dashed) for `not_enough_checkins`, "Facility range not available yet" (1px dashed) for `range_not_available`. | UX-185, FR-202 |
| FEAT-073-FR-05 | Each row shall have a "Show comparison" button (min-height 44px) selecting the resident; the selected row has `aria-selected="true"` and a 2px ink left border. | UX-187 |
| FEAT-073-FR-06 | The page shall list only new-admission residents without an own formed baseline, as returned by the API; residents whose baseline formed appear on the overview instead. | UX-188, FR-205, UX-046 |
| FEAT-073-FR-07 | The comparison section shall be headed "<R> compared with facility range" and show one row per feature with a band from `low` to `high` (TRD 19 `AdmissionComparison`) in `--color-range-band` (#E2E2DE) and the resident value as an 8px circle — outside the band accent with "▲", inside ink — with the caption "grey band = usual range across current residents". | FE-100, UX-189, UX-190, FR-203, D-44 |
| FEAT-073-FR-08 | Feature rows shall use the TRD 11 §4.5.4 plain-language labels for the 7 scored measurements and the API label otherwise. | UX-191 |
| FEAT-073-FR-09 | Under the chart: "Once <N> usable check-ins are collected, this resident moves to the main list and is compared with their own baseline instead." and, when the API returns them, "Range from <n_residents> current residents, computed <Mon D> (method: <method>)." | UX-192, UX-195 |
| FEAT-073-FR-10 | A disclosure "Show comparison as a table" shall show "Measurement", "Resident value", "Facility range", "Outside range" ("▲ Yes" / "No"). | UX-193, UX-225 |
| FEAT-073-FR-11 | With no new admissions the table area shall read "No new admissions. The pipeline test data v0.1 has no admission arm." when the data source is the test data, otherwise "No new admissions."; the comparison section then reads "Select a resident to see the comparison." | UX-194, UX-264 |
| FEAT-073-FR-12 | The page footer shall read "No audio is stored or played here — only extracted voice measurements." | FR-207, UX-005 |

## Inputs

- `GET /api/v1/admissions?limit=500` → `AdmissionList` (`AdmissionRow`: code, admitted date, check-ins so far, `comparison_status`, baseline progress; `meta`).
- `GET /api/v1/admissions/{code}/comparison` → `AdmissionComparison` (per feature value, `low`, `high`).
- `GET /api/v1/facility/reference-ranges` → `ReferenceRangeList` (method, `n_residents`, `computed_at`).

## Outputs

- Rendered experimental page, table, chart and table alternative.

## Data Flow

`getAdmissions()` (`["admissions"]`) → `AdmissionsTable` → "Show comparison" → selected code → `getAdmissionComparison(code)` (`["admissions", code, "comparison"]`) and `getReferenceRanges()` (`["reference-ranges"]`) → `FacilityRangeChart` + disclosure table + method line.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-064, FEAT-036

- FEAT-064 provides the route shell and `BackLink`.
- FEAT-036 provides the three experimental endpoints.

Features that build directly on this one (BACKLOG.md §4): FEAT-075, FEAT-095.

## Database Impact

None (frontend only).

## API Impact

Endpoints consumed: `GET /api/v1/admissions` (E-22), `GET /api/v1/admissions/{resident_code}/comparison` (E-23), `GET /api/v1/facility/reference-ranges` (E-24); responses carry `X-EchoWell-Experimental: true` (API-089). None exposed.

## Frontend Impact

- Page: `app/(protected)/admissions/page.tsx`.
- Components: `ExperimentalBanner`, `AdmissionsTable`, `FacilityRangeChart`, `BackLink`, `Footer` (default), `SectionState`.

## Analytics Impact

None. Comparison status and ranges come from the API; no client computation.

## Security Requirements

- Study IDs only (UX-001); all roles may view (E-22..E-24: admin, clinician, researcher).
- Outside-range information never conveyed by colour alone ("▲" plus text, UX-004).

## Error Handling

- Admissions query error → table section error; comparison query error → comparison section error only (UX-202).
- `range_not_available` → badge "Facility range not available yet" and no chart band rows (UX-185).

## Logging Requirements

None in the frontend.

## Testing Requirements

- Component (TST-090): `ExperimentalBanner` text, `AdmissionsTable` columns, badges for the four statuses, selection, empty texts (test vs other data source); `FacilityRangeChart` band, inside/outside dot styles, caption, table alternative.
- Page test (`frontend/tests/pages/admissions.test.tsx`): loading, populated (fixture with a synthetic new admission and ranges, as in TST-186), empty DS-07, error, 401 → login (TST-094).
- E2E: `admissions.spec.ts` (FE-189), E2E-13 (banner and empty state on DS-07).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-073-AC-01 | On DS-07, `/admissions` shows "← Back to all residents", the banner lines of UX-181, the table text "No new admissions. The pipeline test data v0.1 has no admission arm." and "Select a resident to see the comparison." | E2E-13; FE-189; AC-UX-07; UX-264 |
| FEAT-073-AC-02 | With a fixture admission whose status is `outside_range`, the badge reads "▲ Outside facility range" and the out-of-range feature dot is accent with "▲". | UX-185; FE-100; TST-186 |
| FEAT-073-AC-03 | With `range_not_available`, the badge reads "Facility range not available yet". Verified by: Page test (`frontend/tests/pages/admissions.test.tsx`; TST-186, TST-094). | UX-185; FR-202 |
| FEAT-073-AC-04 | Selecting "Show comparison" sets `aria-selected="true"` on the row and shows "<R> compared with facility range", the caption "grey band = usual range across current residents" and the transition sentence with N from `meta.baseline_n`. Verified by: Page test (`frontend/tests/pages/admissions.test.tsx`; TST-186, TST-094). | UX-187; UX-189; UX-190; UX-192 |
| FEAT-073-AC-05 | The page footer reads "No audio is stored or played here — only extracted voice measurements." and the page has no global navigation. Verified by: Inspection (the inspection method of FR-207, applied to the condition stated in the criterion). | FR-207; FR-331 |

## Definition of Done

- All FEAT-073 acceptance criteria pass; component, page and E2E tests green.
- Experimental banner present (TRD 25 Phase 8 Outputs).
- Batch report lists IDs (AGT-022).

## Implementation Notes

- Decide the test-data empty text by `meta.data_source_label` / `meta.pipeline_profile` from the API, never by a hard-coded environment check (FE-077).
- The banner second line stays until OQ-08 closes; keep it in `lib/wording.ts`.
- The chart uses `--color-range-band` (D-44); never use accent for the band.
