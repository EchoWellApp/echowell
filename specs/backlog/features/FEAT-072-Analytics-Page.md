# FEAT-072 Analytics page

| Field | Value |
|---|---|
| Epic | Frontend |
| Build phase | Phase 8 (TRD 25) |
| Priority | P0 |
| Complexity | High |
| MVP status | Required |
| Dependencies | FEAT-064, FEAT-051 |
| Status | Not Started |

## Purpose

Implement `/analytics` (SRC-19), the counts page for the study team (roles researcher and admin): the header and subline (answer-key clause only in `test_v0_1`), four KPI tiles, the "Check-ins per day" stacked bar chart, the "Where check-ins are lost" funnel, "Usable check-ins by resident", the "Alarm timing check" table (`test_v0_1`) or "Alarms and review outcomes" (`production`), a text table for every chart, CSV downloads, the footer, and the empty state when no pipeline run has succeeded yet. With the reference data the page shows 94 %, 89 %, 9 of 10, 2 and the funnel 300 → 281 → 269 → 267.

## Business Context

- BR-15 (numbers match the pipeline answer key), BR-12 (data completeness visible), BR-03..BR-06 (duplicates, set-aside reasons, quarantines and missed days counted), BR-13 (review outcomes in production).
- VIS-028 (Analytics page in the MVP, researcher and admin); BR-16 (counts only, no names or audio).
- FRs covered (BACKLOG.md): FR-310, FR-311, FR-313, FR-314, FR-315, FR-316, FR-317, FR-318, FR-319, FR-320, FR-321, FR-323.

## Referenced TRDs

- TRD 04 FE-037 (clinician access denied, no API call), FE-194 (E2E `analytics.spec.ts`), FE-195 (production-profile component test), §4.8 `AnalyticsPage`, `KpiTiles`, `DailyCheckinsChart`, `LossFunnel`, `UsableByResidentChart`, `AlarmTimingTable`, `ReviewOutcomesTable`, §4.6.2 `getAnalytics`, `downloadScoresCsv`, `downloadBaselinesCsv`, §4.12 tokens (`--color-used`, funnel shades).
- TRD 11 UX-350..UX-384 (roles, tiles, percentages, notes, daily chart and legend, x labels, table alternative, accessible names, funnel rows and notes, by-resident rows, alarm timing and review outcomes, caption, test-only labelling, downloads, wording, reference rendering), UX-017 (subline), UX-005 (footer), UX-246 (stacking).
- TRD 19 E-18 `GET /api/v1/analytics` (`AnalyticsResponse`), E-12 and E-19 CSV (`Accept: text/csv`).
- TRD 00 VIS-028; TRD 02 FR-310, FR-311, FR-313..FR-321, FR-323, UC-14.
- TRD 13 E2E-20, E2E-21, TST-090; TRD 14 Table 4.9-E.

## Scope

- `app/(protected)/analytics/page.tsx` (`AnalyticsPage`) with `AppHeader` (title "Analytics", active "analytics"), role check before any data hook, `getAnalytics()` (`["analytics"]`), layout: tiles → daily chart (full width) → two columns funnel | by-resident → timing or review-outcomes section → downloads → footer `analytics`.
- Components `KpiTiles`, `DailyCheckinsChart` (+ "Show daily counts as a table"), `LossFunnel`, `UsableByResidentChart`, `AlarmTimingTable`, `ReviewOutcomesTable`; KPI note and funnel note composition in `lib/wording.ts`.
- "Downloads" row: "Scores (CSV)" and "Baselines (CSV)".
- Empty state "No pipeline run yet" when no succeeded run exists.

## Out of Scope

- The endpoint and aggregates (FEAT-035, FEAT-051); alarm-timing and review-outcome computation (FEAT-035).
- Access-denied component and navigation visibility (FEAT-064; this page uses it).
- Responsive/axe audit across pages (FEAT-075).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-072-FR-01 | The page shall be available only to researcher and admin; a clinician sees the access-denied state and no `GET /api/v1/analytics` request is made. | FR-310, FE-037, UX-350 |
| FEAT-072-FR-02 | The subline shall read "For the study team · <data_source_label>, <period> · numbers match the pipeline answer key", where the last clause appears only when `meta.pipeline_profile` is `test_v0_1` and `<period>` is the 30-day window with year (test data "For the study team · pipeline test data v0.1, Oct 1–30, 2026 · numbers match the pipeline answer key"). | FR-311, UX-017 |
| FEAT-072-FR-03 | Four tiles in the order "Check-ins received" ("<p>%" and "<received> of <expected> expected"), "Used for scoring" ("<p>%" and "<usable> of <expected> expected"), "Baselines formed" ("<formed> of <residents>" and the note of forming residents and restarts: "R08 still forming; R07 restarted once", "twice", "<k> times", or "All baselines formed"), "Alarms raised" (count and note "<codes> · <review state>" per UX-355 or "none in this period"); percentages are the API's half-up integers. | FR-313, FR-314, UX-351..UX-355 |
| FEAT-072-FR-04 | "Check-ins per day" shall show a legend Used (#4A4A47), Set aside (#BDBDB8), Quarantined (#9A4508), Missed (white with 1px dashed #8A8A85) and one stacked bar per local day (plot height 160px, gap 4px, min width 760px in a scrolling container), stacked bottom to top Used, Set aside, Quarantined, Missed; duplicates excluded. | FR-315, UX-356, UX-357 |
| FEAT-072-FR-05 | The x axis shall label the first day, each day with silent devices as "<Mon D> · <D> silent" (several: "<Mon D> · D02, D05 silent") from `silent_device_codes`, and the last day; no "▲" in analytics charts. | FR-315, UX-358, UX-361 |
| FEAT-072-FR-06 | A disclosure "Show daily counts as a table" shall show columns "Date", "Used", "Set aside", "Quarantined", "Missed", "Note"; the chart's accessible name is "Check-ins per day, <period>: <used> used, <set aside> set aside, <quarantined> quarantined, <missed> missed." | FR-320, UX-359, UX-360 |
| FEAT-072-FR-07 | The funnel "Where check-ins are lost" shall show four rows "Expected check-ins", "Received", "Passed quality checks", "Same speaker, used" (bar width proportional to Expected; colours #8A8A85, #6E6E6A, #5A5A57, #4A4A47) with notes "<residents> residents × <days> days" (or "sum of days enrolled across <residents> residents"), "<missed> missed · <duplicates> duplicate copies removed" ("1 duplicate copy removed"), "<set aside> set aside: quality flag <a>, noise <b>, too short <c>" plus " (<k> had two reasons)" or " (<k> had more than one reason)", "<quarantined> quarantined as possible other speaker". | FR-316, UX-362..UX-366 |
| FEAT-072-FR-08 | "Usable check-ins by resident" shall show the subtitle "Share of <days> days, lowest first" and one row per resident in API order (percentage ascending, natural code ties): 48px bold code, a 20px bar stacked used / set aside / quarantined with missed unfilled, 56px percentage; each row's accessible name "<R>: <used> of <days> days usable (<p>%); <set aside> set aside; <quarantined> quarantined; <missed> missed." | FR-317, FR-320, UX-367..UX-370 |
| FEAT-072-FR-09 | With `meta.pipeline_profile` = `test_v0_1` the section "Alarm timing check" with inline "· test data only, where the true change date is known" shall show a table (min width 640px) "Resident", "Planted change", "Change began", "Alarm rang", "Delay": one row per resident with a planted change, then "Other <k>" / "None" / "—" / "No alarm" / "Correct" when none of them alarmed (otherwise "<n> alarms" / "<n> false alarms"); "Delay" "<d> days" ("1 day"); planted change without alarm "No alarm" and "Missed"; caption "With real residents the true change date is unknown, so this panel becomes: alarms raised, reviewed, and the review outcomes." | FR-318, UX-371..UX-374, UX-376 |
| FEAT-072-FR-10 | With `production` the section shall be "Alarms and review outcomes" with a two-column table ("", "Count") and rows "Alarms raised", "Reviewed", "Checked on resident, no concern", "Explained by a known cause", "Referred to nurse or provider", "Looks like a data problem: send to study team" from `review_outcomes`; the timing data never shows in production. | FR-319, UX-375, UX-376 |
| FEAT-072-FR-11 | A "Downloads" row shall offer "Scores (CSV)" and "Baselines (CSV)" calling `GET /scores` and `GET /analytics/baselines` with `Accept: text/csv`. | UX-377 |
| FEAT-072-FR-12 | The footer shall read "Counts only — no audio, no resident names."; the page uses no alarm wording other than "Alarms raised" and does not rank residents by health. | FR-321, UX-005, TRD 11 §4.18.6 |
| FEAT-072-FR-13 | With no succeeded pipeline run the page shall show the empty state "No pipeline run yet". | TRD 02 UC-14 |
| FEAT-072-FR-14 | With the reference data the page shall render TRD 11 §4.18.7 (tiles 94 % / "281 of 300 expected", 89 % / "267 of 300 expected", "9 of 10" / "R08 still forming; R07 restarted once", 2 / "R09, R10 · both not yet reviewed"; x labels "Oct 1", "Oct 12 · D02 silent", "Oct 30"; funnel 300/281/269/267 with the notes; by-resident R08 43 %, R03 73 %, R02 80 %, R05 93 %, others 100 %; timing R09 · Sudden step · Oct 21 · Oct 21 · 0 days, R10 · Slow drift · Oct 17 · Oct 24 · 7 days, Other 8 · None · — · No alarm · Correct). | FR-323, UX-380..UX-384 |
| FEAT-072-FR-15 | Each panel (tiles, daily chart, funnel, by-resident, timing/outcomes) shall render its own loading, empty and error state. | LOG-083, UX-202 |

## Inputs

- `GET /api/v1/analytics` → `AnalyticsResponse` (`meta`, `period`, `kpis`, `daily_series`, `funnel`, `by_resident`, `alarm_timing` or `review_outcomes`, `status_totals`, `pipeline_run`).
- Role from `useAuth()`; `meta.pipeline_profile`, `meta.data_source_label`, `meta.facility_tz`.

## Outputs

- Rendered page; CSV file downloads via the browser.

## Data Flow

Role check → `getAnalytics()` → `KpiTiles(kpis)` (notes composed in `wording.ts` from counts and codes), `DailyCheckinsChart(daily_series, meta)`, `LossFunnel(funnel)`, `UsableByResidentChart(by_resident)`, `AlarmTimingTable` rows built from `alarm_timing` (planted rows + grouped "Other <k>") or `ReviewOutcomesTable(review_outcomes)` → footer. Downloads → `downloadScoresCsv`, `downloadBaselinesCsv`.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-064, FEAT-051

- FEAT-064 provides the header, nav visibility and access-denied state.
- FEAT-051 provides the `kpis`, `daily_series`, `funnel`, `by_resident` blocks (FEAT-035, through FEAT-051, provides the rest of E-18).

## Database Impact

None (frontend only).

## API Impact

Endpoints consumed: `GET /api/v1/analytics` (E-18), `GET /api/v1/scores` (E-12, CSV), `GET /api/v1/analytics/baselines` (E-19, CSV), `GET /api/v1/alerts?status=open` (E-13, nav count). None exposed.

## Frontend Impact

- Page: `app/(protected)/analytics/page.tsx`.
- Components: `AnalyticsPage`, `KpiTiles`, `DailyCheckinsChart`, `LossFunnel`, `UsableByResidentChart`, `AlarmTimingTable`, `ReviewOutcomesTable`, `Footer` (analytics), `SectionState`.

## Analytics Impact

None. All counts and percentages come from the API; the UI only groups the "Other <k>" timing row and composes note strings (UX-372, UX-354, UX-355).

## Security Requirements

- Clinicians never trigger the analytics request (FE-037); the backend returns 403 to them (FR-310).
- No resident names, notes or audio on the page (UX-001, FR-321); CSV downloads only for researcher and admin (OAS-018).

## Error Handling

- 403 → access message (FE-035); per-panel errors independent (LOG-083); no succeeded run → "No pipeline run yet".
- CSV download 413 → error message with reference (FEAT-062 error mapping).

## Logging Requirements

None in the frontend; the backend writes `export.csv` audit rows for CSV downloads (TRD 12 §4.12).

## Testing Requirements

- Component (TST-090): `KpiTiles` (values and all note variants incl. UX-355 states), `DailyCheckinsChart` (legend order, x labels, table rows for Oct 1, Oct 12, Oct 22, accessible name), `LossFunnel` (notes incl. singular/plural), `UsableByResidentChart` (order, widths, accessible names), `AlarmTimingTable` (grouped Other row, delays), `ReviewOutcomesTable`.
- FE-195: `AnalyticsPage` with `meta.pipeline_profile` = `production` renders `ReviewOutcomesTable` instead of `AlarmTimingTable` and the subline omits the answer-key clause.
- Page test (`frontend/tests/pages/analytics.test.tsx`): loading, populated, empty ("No pipeline run yet"), error, 401 → login, clinician access-denied with no request (TST-094).
- E2E: `analytics.spec.ts` (FE-194), E2E-20 (researcher values), E2E-21 (clinician refused).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-072-AC-01 | As researcher on DS-07, tiles show 94 % "281 of 300 expected", 89 % "267 of 300 expected", "9 of 10" "R08 still forming; R07 restarted once", 2 "R09, R10 · both not yet reviewed". | E2E-20; FE-194; UX-380 |
| FEAT-072-AC-02 | The funnel shows 300 "10 residents × 30 days" → 281 "19 missed · 2 duplicate copies removed" → 269 "12 set aside: quality flag 5, noise 5, too short 3 (1 had two reasons)" → 267 "2 quarantined as possible other speaker". | E2E-20; UX-382 |
| FEAT-072-AC-03 | By-resident rows read R08 43 %, R03 73 %, R02 80 %, R05 93 %, R01, R04, R06, R07, R09, R10 100 % in that order. | E2E-20; UX-383 |
| FEAT-072-AC-04 | The daily table shows Oct 1 10/0/0/0, Oct 12 8/0/0/2 with note "D02 silent" and Oct 22 8/1/1/0, and the x axis labels "Oct 1", "Oct 12 · D02 silent", "Oct 30". | FE-194; UX-381 |
| FEAT-072-AC-05 | The alarm timing table shows R09 · Sudden step · Oct 21 · Oct 21 · 0 days, R10 · Slow drift · Oct 17 · Oct 24 · 7 days, Other 8 · None · — · No alarm · Correct, and the footer reads "Counts only — no audio, no resident names." | E2E-20; UX-384; FR-321 |
| FEAT-072-AC-06 | With a `production` fixture the "Alarms and review outcomes" table replaces the timing table and the subline has no "numbers match the pipeline answer key". | FE-195; AC-UX-12 |
| FEAT-072-AC-07 | As clinician, `/analytics` shows the access-denied state and no analytics request is sent. | E2E-21; FE-037 |

## Definition of Done

- All FEAT-072 acceptance criteria pass; component, page and E2E tests green.
- Analytics shows 281 of 300 (94 %), 267 of 300 (89 %), 9 of 10, 2 and the timing table (TRD 25 Phase 8 DoD).
- Batch report lists IDs and the conflict below (AGT-022).

## Implementation Notes

- A clinician gets the access-denied state "You do not have access to this page." with "Back to all residents" (FE-034/FE-037, UX-350; shared component, FEAT-064); TRD 02 FR-310 and UC-14 were aligned in the PR #2 consistency fixes.
- The E-18 DTO carries counts and codes but no note strings (TRD 07 §4.13 notes are internal); compose notes in `lib/wording.ts` per UX-354 and UX-355.
- The "Other <k>" row groups `alarm_timing` items with `planted_change` "None" (`result` `correct_no_alarm`); show them individually as false alarms only when one of them alarmed (UX-372).
- All Recharts components set `isAnimationActive={false}` (FE-099).
