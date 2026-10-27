# FEAT-073 New admissions page (experimental, v0.2 restyle)

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

Implement `/admissions`, the experimental page for the new-admission study arm, restyled for wireframe v0.2 (SRC-21, TRD 24 D-110): the open-question note at the top ("Future / experimental. Not in pipeline test v0.1: …"), the panel with the `<h1>` "New admissions" and its intro, the admissions table (Status · Resident · Admitted · Compared with facility range · Own baseline, plus "Show comparison"), the comparison panel "<R> compared with facility range" with `FacilityRangeChart` (resident value dot against the grey facility band) and its table alternative, the transition sentence, and the empty states. The page is reached from the main navigation and has no back link (UX-180 retired); the no-audio statement is the data bar (FEAT-064), not a footer. The pipeline test data has no admission arm, so the reference rendering is the empty state.

## Business Context

- BR-14 (new residents are compared with the facility's usual range until their own baseline forms, then move to the resident list) with VIS-009 (always labelled experimental) and D-06 (no alerts, isolated from the longitudinal pipeline).
- OQ-08 (facility norm method undefined in the MVP): the page renders whatever ranges the API returns and states that the arm is not in pipeline test v0.1.
- D-109 and question 4 of the v0.2 review: the comparison status uses the v0.2 pills (outside range "Changed", within range "Usual", otherwise "Learning") until the algorithm lead decides otherwise.
- FRs covered (BACKLOG.md): FR-200, FR-201, FR-202, FR-203, FR-205.

## Referenced TRDs

- TRD 11 (v0.13) — owned by this feature: UX-181..UX-195 (open-question note, header and intro, table and columns, study ID and admitted date, status pill and comparison text, own-baseline text, "Show comparison" and selection, cohort transition, comparison chart, caption, labels, transition sentence, table alternative, empty states, range method line), UX-264 and §4.13.5 (reference rendering). Retired, not built: UX-180 (back link). Uses `StatusPill` (FEAT-062) and the data bar (UX-400, FEAT-064).
- TRD 04 (v0.11) FE-092 (`StatusPill` used for the comparison status), FE-100 (`FacilityRangeChart` band `--grey-bg`, dot, `--red` and "▲" outside), FE-189 (E2E `admissions.spec.ts`), §4.8 `AdmissionsTable`, `FacilityRangeChart`, `ExperimentalBanner`, §4.6.2 `getAdmissions`, `getAdmissionComparison`, `getReferenceRanges`.
- TRD 19 E-22, E-23, E-24 (experimental endpoints, `ComparisonStatus`).
- TRD 00 VIS-009; TRD 02 FR-200..FR-203, FR-205; TRD 24 D-06, D-44, D-109, D-110, D-112, OQ-08.
- TRD 13 E2E-13, TST-090, TST-186.

## Scope

- `app/(protected)/admissions/page.tsx`: `ExperimentalBanner` (open-question note), panel with header, intro and `AdmissionsTable`, comparison panel with `FacilityRangeChart`, its disclosure table, transition sentence and method line.
- Queries `getAdmissions()` (`limit=500`), `getAdmissionComparison(code)` for the selected resident, `getReferenceRanges()` for the method line.
- Selected resident held in component state.

## Out of Scope

- The experimental endpoints and the cohort transition (FEAT-036, FEAT-053).
- Facility norm computation (FEAT-095, OQ-08/OQ-20).
- Any alerting for new admissions (never, FR-206, D-06).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-073-FR-01 | The page shall start with the note `ExperimentalBanner` (1px dashed `--yellow-edge` border, `--yellow-bg` background, `--yellow` text, 14px, padding 8px 12px, radius 6px) reading "Future / experimental. Not in pipeline test v0.1: the test data has no admission group or facility range yet. Open question for Shaba and the PI."; the second and third sentences stay until OQ-08 is closed. | UX-181, FR-200, VIS-009, OQ-08, RAQ-018 |
| FEAT-073-FR-02 | The panel shall start with the `<h1>` "New admissions" (22px) and the line "New residents don’t have their own baseline yet, so their first check-ins are compared with the facility’s usual range." (`--muted`). | UX-182 |
| FEAT-073-FR-03 | The table shall have the columns "Status", "Resident", "Admitted", "Compared with facility range", "Own baseline" and an action column (visually hidden header "Actions"), header styles of UX-034, `min-width: 640px` inside a horizontally scrolling, keyboard-focusable container with an accessible name. | UX-183, UX-243, FR-201 |
| FEAT-073-FR-04 | "Resident" shall show the study ID (weight 700); "Admitted" the admission date "<Mon D>"; "Own baseline" "<n> of <N>" (usable check-ins towards the own baseline, N = `meta.baseline_n`). | UX-184, UX-186, FR-201 |
| FEAT-073-FR-05 | "Status" shall show a pill and "Compared with facility range" the matching text: `outside_range` → neutral `RangePill` "Out of range" and "Outside facility range"; `within_range` → neutral `RangePill` "In range" and "Within facility range" (no status colour, no glyph; TRD 24 D-117); `not_enough_checkins` → "○ Learning" and "Not enough check-ins yet"; `range_not_available` → "○ Learning" and "Facility range not available yet". | UX-185, FR-202, UX-004, D-117 |
| FEAT-073-FR-06 | Each row shall have a secondary button "Show comparison" (min-height 44px) selecting the resident; the selected row has `aria-selected="true"` and a 5px `--chrome` left border on its first cell. | UX-187 |
| FEAT-073-FR-07 | The page shall list only new-admission residents without an own formed baseline, as returned by the API; residents whose baseline formed appear on the resident list instead. | UX-188, FR-205, UX-046 |
| FEAT-073-FR-08 | The comparison panel shall be headed "<R> compared with facility range" (h2) and show one row per measurement with a band from `low` to `high` (TRD 19 `AdmissionComparison`) in `--grey-bg` and the resident value as an 8px dot — outside the band `--red` with "▲", inside ink — with the caption "Grey band = usual range across current residents" (12px, `--muted`). | FE-100, UX-189, UX-190, FR-203, D-44 |
| FEAT-073-FR-09 | Measurement rows shall use the TRD 11 §4.5.4 plain-language labels for the 7 scored measurements and the API label otherwise. | UX-191 |
| FEAT-073-FR-10 | Under the chart: "After <N> usable check-ins, the resident moves to the resident list and is compared with their own baseline instead." (14px, `--muted`) and, when the API returns them, "Range from <n_residents> current residents, computed <Mon D> (method: <method>)." | UX-192, UX-195 |
| FEAT-073-FR-11 | A disclosure "Show comparison as a table" shall show "Measurement", "Resident value", "Facility range", "Outside range" ("▲ Yes" / "No"). | UX-193, UX-225 |
| FEAT-073-FR-12 | With no new admissions the table area shall read "No new admissions. The pipeline test data v0.1 has no admission group." when `meta.pipeline_profile` is `test_v0_1`, otherwise "No new admissions."; the comparison panel then reads "Select a resident to see the comparison." | UX-194, UX-264 |
| FEAT-073-FR-13 | The page shall show the app bar and the data bar of FEAT-064 (no page footer, no back link). | UX-400, UX-180 retired |

## Inputs

- `GET /api/v1/admissions?limit=500` → `AdmissionList` (`AdmissionRow`: code, admitted date, `comparison_status`, own-baseline progress; `meta`).
- `GET /api/v1/admissions/{code}/comparison` → `AdmissionComparison` (per feature value, `low`, `high`).
- `GET /api/v1/facility/reference-ranges` → `ReferenceRangeList` (method, `n_residents`, `computed_at`).

## Outputs

- Rendered experimental page, table, chart and table alternative.

## Data Flow

`getAdmissions()` (`["admissions"]`) → `AdmissionsTable` → "Show comparison" → selected code → `getAdmissionComparison(code)` (`["admissions", code, "comparison"]`) and `getReferenceRanges()` (`["reference-ranges"]`) → `FacilityRangeChart` + disclosure table + method line.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-064, FEAT-036

- FEAT-064 provides the route shell, the app bar and the data bar.
- FEAT-036 provides the three experimental endpoints.

Features that build directly on this one (BACKLOG.md §4): FEAT-075, FEAT-095.

## Database Impact

None (frontend only).

## API Impact

Endpoints consumed: `GET /api/v1/admissions` (E-22), `GET /api/v1/admissions/{resident_code}/comparison` (E-23), `GET /api/v1/facility/reference-ranges` (E-24); responses carry `X-EchoWell-Experimental: true` (API-089). None exposed.

## Frontend Impact

- Page: `app/(protected)/admissions/page.tsx`.
- Components: `ExperimentalBanner`, `AdmissionsTable`, `FacilityRangeChart`, `StatusPill`, `SectionState`.

## Analytics Impact

None. Comparison status and ranges come from the API; no client computation.

## Security Requirements

- Study IDs only (UX-001); all roles may view (E-22..E-24: admin, clinician, researcher).
- Outside-range information never conveyed by colour alone (pill glyph and label, "▲" on the dot, text, UX-004).

## Error Handling

- Admissions query error → table section error; comparison query error → comparison section error only (UX-202).
- `range_not_available` → "○ Learning" pill, "Facility range not available yet" and no chart band rows (UX-185).

## Logging Requirements

None in the frontend.

## Testing Requirements

- Component (TST-090): `ExperimentalBanner` text, `AdmissionsTable` columns, pills and texts for the four statuses, selection border and `aria-selected`, empty texts (test vs production profile); `FacilityRangeChart` band, inside/outside dot styles, caption, table alternative.
- Page test (`frontend/tests/pages/admissions.test.tsx`): loading, populated (fixture with a synthetic new admission and ranges, as in TST-186), empty DS-07, error, 401 → login (TST-094).
- E2E: `admissions.spec.ts` (FE-189), E2E-13 (note and empty state on DS-07).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-073-AC-01 | On DS-07, `/admissions` shows the note "Future / experimental. Not in pipeline test v0.1: the test data has no admission group or facility range yet. Open question for Shaba and the PI.", the `<h1>` "New admissions", the table text "No new admissions. The pipeline test data v0.1 has no admission group." and "Select a resident to see the comparison.", and no back link. | E2E-13; FE-189; AC-UX-07; UX-264 |
| FEAT-073-AC-02 | With a fixture admission whose status is `outside_range`, the row shows the neutral pill "Out of range" (no "▲", no red) and "Outside facility range" and the out-of-range dot is `--red` with "▲". Verified by: Page test (TST-186). | UX-185; FE-100 |
| FEAT-073-AC-03 | With `range_not_available`, the row shows "○ Learning" and "Facility range not available yet". Verified by: Page test (`frontend/tests/pages/admissions.test.tsx`; TST-186, TST-094). | UX-185; FR-202 |
| FEAT-073-AC-04 | Selecting "Show comparison" sets `aria-selected="true"` on the row and shows "<R> compared with facility range", the caption "Grey band = usual range across current residents" and the sentence "After 16 usable check-ins, the resident moves to the resident list and is compared with their own baseline instead." with N from `meta.baseline_n`. Verified by: Page test (TST-094). | UX-187; UX-189; UX-190; UX-192 |
| FEAT-073-AC-05 | The page shows the app bar with "New admissions" current and the data bar; it has no footer. Verified by: Page test (TST-094). | UX-400; FR-138 |

## Definition of Done

- All FEAT-073 acceptance criteria pass; component, page and E2E tests green.
- Experimental banner present (TRD 25 Phase 8 Outputs).
- Batch report lists IDs (AGT-022).

## Implementation Notes

- Decide the test-data empty text by `meta.pipeline_profile` from the API, never by a hard-coded environment check (FE-077).
- The note's second and third sentences stay until OQ-08 closes; keep them in `lib/wording.ts`.
- The pill mapping (outside range "Changed", within range "Usual") is question 4 of the v0.2 review for the algorithm lead; keep the mapping in one function so a switch to neutral pills is a one-line change.
- The chart band uses `--grey-bg` (D-44, D-112); never use red for the band.
