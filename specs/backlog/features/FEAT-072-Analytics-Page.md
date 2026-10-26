# FEAT-072 Study team page (KPI tiles, data problems to follow up, check-in charts, alarm timing, Devices, downloads)

| Field | Value |
|---|---|
| Epic | Frontend |
| Build phase | Phase 8 (TRD 25) |
| Priority | P0 |
| Complexity | High |
| MVP status | Required |
| Dependencies | FEAT-064, FEAT-051, FEAT-029, FEAT-032 |
| Status | Not Started |

## Purpose

Implement `/study`, the Study team page that replaces the v0.1 Analytics page (SRC-21, TRD 24 D-110), for the roles researcher and admin: the header panel with the `<h1>` "Study team: how the system is working", "Counts only. No audio, no names." and the period line (answer-key clause only in `test_v0_1`); four KPI tiles; the "Data problems to follow up" list of open data alerts with the tags "Staff can help" and "Study team" (moved from the retired Alert review page); the "Check-ins per day" stacked bar chart; the two columns "Where check-ins are lost" and "Usable check-ins by resident"; the "Alarm timing check" table (`test_v0_1`) or "Alarms and review outcomes" (`production`); the "Devices" section `id="devices"` with tagged rows and the "Show all devices (<n>)" table (moved from the v0.1 overview); the "Downloads" panel (Scores and Baselines CSV, kept, D-111); a text table for every chart; and the empty state when no pipeline run has succeeded yet. With the reference data the page shows 94 %, 89 %, 9 of 10, 2, the four data problems R08, R03, R05, D02, the funnel 300 → 281 → 269 → 267 and the three device rows of TRD 11 §4.13.4.

## Business Context

- BR-15 (numbers match the pipeline answer key), BR-12 (data completeness and device status visible to the study team), BR-03..BR-06 (duplicates, set-aside reasons, held-back check-ins and missed days counted), BR-13 (review outcomes in production).
- VIS-029 (data problems are never presented as health alarms): no "▲" and no red on this page; R05's held-back check-ins and D02's silent day are study-team items and do not change a resident's colour (D-109).
- BR-16 (counts only, no names or audio); VIS-028 (study-team read-outs in the MVP, researcher and admin).
- FRs covered (BACKLOG.md): FR-150, FR-151, FR-152, FR-153, FR-154, FR-155, FR-156, FR-298, FR-310, FR-311, FR-313, FR-314, FR-315, FR-316, FR-317, FR-318, FR-319, FR-320, FR-323.

## Referenced TRDs

- TRD 11 (v0.13) — owned by this feature: UX-017 (header lines), UX-350..UX-355 (roles and header, KPI tiles and notes), UX-306..UX-309 (data problems: rows and tags, order, links, empty text), §4.18.2 row texts, UX-356..UX-361 (check-ins per day), UX-362..UX-366 (where check-ins are lost), UX-367..UX-370 (usable check-ins by resident), UX-371..UX-376 (alarm timing / review outcomes), UX-377 (downloads), §4.18.7 wording, UX-050..UX-058 and §4.4 (Devices section), UX-263 and §4.13.4 (Devices reference rendering), UX-331 (data problems reference rendering), UX-380..UX-384 and §4.18.8 (reference rendering).
- TRD 04 (v0.11) FE-026 (`/study#devices` scroll and focus), FE-037 (clinician access denied, no API call), FE-076 (`limit=500`), FE-102 (`compressDeviceCodes()`), FE-194 (E2E `study-team.spec.ts`), FE-195 (production-profile component test), §4.8 `StudyTeamPage`, `KpiTiles`, `DataProblemsList`, `DailyCheckinsChart`, `LossFunnel`, `UsableByResidentChart`, `AlarmTimingTable`, `ReviewOutcomesTable`, `DevicesSection`, §4.6.2 `getAnalytics`, `getDataAlerts`, `getDevices`, `downloadScoresCsv`, `downloadBaselinesCsv`, §4.12 tokens (`--c-used`, `--c-aside`, `--c-quar`).
- TRD 19 E-18 `GET /api/v1/analytics` (`AnalyticsResponse`), E-30 `GET /api/v1/data-alerts` (`detail` texts of TRD 24 D-114), E-17 `GET /api/v1/devices` (`uploaded_on_as_of_date`), E-12 and E-19 CSV (`Accept: text/csv`).
- TRD 00 VIS-028, VIS-029; TRD 02 FR-150..FR-156, FR-298, FR-310, FR-311, FR-313..FR-320, FR-323, UC-14; TRD 24 D-108..D-114, OQ-24, OQ-31.
- TRD 13 E2E-07, E2E-17 (data problems part), E2E-20, E2E-21 (clinician part), TST-090; TRD 14 Tables 4.9-C, 4.9-D, 4.9-E.

## Scope

- `app/(protected)/study/page.tsx` (`StudyTeamPage`) with the role check before any data hook, queries `getAnalytics()` (`["analytics"]`), `getDataAlerts({ status: "open" })` (`["data-alerts", {status: "open"}]`) and `getDevices()` (`["devices"]`), layout: header panel → `KpiTiles` → `DataProblemsList` → `DailyCheckinsChart` (full width) → two columns `LossFunnel` | `UsableByResidentChart` → `AlarmTimingTable` or `ReviewOutcomesTable` → `DevicesSection` → Downloads.
- KPI note, data-problem row and device row composition in `lib/wording.ts`; `compressDeviceCodes()` from FEAT-062.
- `/study#devices` anchor: scroll to the section and move focus to its heading.
- Empty state "No pipeline run yet" when no succeeded run exists.

## Out of Scope

- The endpoints and aggregates (FEAT-035, FEAT-051), data alerts and their `detail` texts (FEAT-050, FEAT-032), device read-model (FEAT-029, FEAT-014).
- Access-denied state and navigation visibility (FEAT-064; this page uses them).
- Any rule that turns a resident Needs attention because of a data problem (backend, OQ-31).
- Responsive and axe audit across pages (FEAT-075).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-072-FR-01 | The page shall be available only to researcher and admin; a clinician sees the access-denied state "You do not have access to this page." with "← Resident list" and no Study team API request is made. | UX-350, FE-037, FR-310 |
| FEAT-072-FR-02 | The header panel shall show the `<h1>` "Study team: how the system is working", the line "Counts only. No audio, no names." (14px, `--muted`) and the period line "<data source label>, <period> · numbers match the pipeline answer key", where the clause " · numbers match the pipeline answer key" appears only when `meta.pipeline_profile` is `test_v0_1` and the period is the 30-day window with year (test data "pipeline test data v0.1, Oct 1–30, 2026 · numbers match the pipeline answer key"). | UX-017, UX-350, FR-311 |
| FEAT-072-FR-03 | Four tiles (grid, min width 200px, gap 12px; label 13px `--muted`, value 18px weight 700, note 14px `--muted`) shall appear in the order "Check-ins received" ("<p>%" and "<received> of <expected> expected"), "Used for scoring" ("<p>%" and "<usable> of <expected> expected"), "Baselines formed" ("<formed> of <active residents>" and the note of forming residents and restarts, e.g. "R08 still forming; R07 restarted once", or "All baselines formed"), "Alarms raised" (count and note "<codes>; <review state>" with "not reviewed yet" (1), "neither reviewed yet" (2), "none reviewed yet" (≥ 3), "<k> not reviewed yet" (some), "reviewed" / "both reviewed" / "all reviewed"; with 0 alarms "none in this period"); percentages are the API's half-up integers. | UX-351..UX-355, FR-313, FR-314 |
| FEAT-072-FR-04 | After the tiles a panel "Data problems to follow up" shall list one row per open data alert (grid: 110px tag column, text column; 1px `--rule` separators): tag "Staff can help" (`--yellow`, 14px, weight 700) for `baseline_stalled` and `high_set_aside`, "Study team" (`--muted`) for `possible_other_speaker`, `device_silent` and `review_flagged_data_problem`, then "**<code>:** <detail>" with the API `detail` text; never "▲" or red. | UX-306, FR-298, VIS-029, D-114 |
| FEAT-072-FR-05 | Data-problem rows shall be ordered by kind (baseline_stalled, high_set_aside, possible_other_speaker, device_silent, review_flagged_data_problem), then by resident or device code; the bold code is a link — a resident code to `/residents/<R>/log`, a device code to `/study#devices` — whose accessible name is the API `title` (e.g. "R08 · baseline stuck at 13 of 16"); with no open data alert the panel reads "No data problems in the last 30 days." | UX-307, UX-308, UX-309 |
| FEAT-072-FR-06 | "Check-ins per day" shall show a legend in the order Used (`--c-used`), Set aside (`--c-aside`), Held back (other voice) (`--c-quar`), Missed (dashed outline), each a 12px swatch with its label (14px, `--muted`), and one stacked bar per local day (plot height about 160px, min width 560px in a keyboard-focusable scrolling container), stacked bottom to top Used, Set aside, Held back, Missed; duplicates excluded. | UX-356, UX-357, FR-315 |
| FEAT-072-FR-07 | The x axis shall label the first day, every day with a device-silent gap as "<Mon D>: <D> silent" (several: "<Mon D>: D02, D05 silent") from `silent_device_codes`, and the last day; each bar has the tooltip "<Mon D>: <u> used, <a> set aside, <q> held back, <m> missed"; no "▲" in Study team charts. | UX-358, UX-361, FR-315 |
| FEAT-072-FR-08 | A disclosure "Show daily counts as a table" shall show the columns "Date", "Used", "Set aside", "Held back", "Missed", "Note"; the chart's accessible name is "Check-ins per day, <period>: <used> used, <set aside> set aside, <held back> held back, <missed> missed." | UX-359, UX-360, FR-320 |
| FEAT-072-FR-09 | "Where check-ins are lost" shall show four rows (grid: 170px label, meter, 44px right-aligned bold value; meter 14px high, filled width proportional to Expected) "Expected", "Received", "Passed quality checks", "Same speaker, used" with the notes "<residents> residents × <days> days" (or "sum of days enrolled across <residents> residents"), "<missed> missed; <duplicates> duplicate copies removed" ("1 duplicate copy removed"), "<set aside> set aside: quality flag <a>, noise <b>, too short <c>" plus " (<k> had two reasons)" or " (<k> had more than one reason)", "<held back> held back as possible other voice". | UX-362..UX-366, FR-316 |
| FEAT-072-FR-10 | "Usable check-ins by resident" shall show the subtitle "Share of <days> days, lowest first" and one row per active resident in API order (percentage ascending, natural code ties): 44px bold code linking to `/residents/<R>/log`, a `--c-used` meter of the used share, 48px right-aligned percentage; each row's accessible name "<R>: <used> of <days> days usable (<p>%); <set aside> set aside; <held back> held back; <missed> missed." | UX-367..UX-370, FR-317, FR-320 |
| FEAT-072-FR-11 | With `test_v0_1` the panel "Alarm timing check" with the line "Test data only, where the true change date is known." shall show a table (in a scrolling container) "Resident", "Planted change", "Change began", "Alarm rang", "Delay": one row per resident with a planted change, then "Other <k>" / "None" / "None" / "No alarm" / "Correct" when none of them alarmed (otherwise "<n> alarms" / "<n> false alarms"); "Delay" "<d> days" ("1 day"); planted change without alarm "No alarm" / "Missed"; an alarm before the change began "False alarm"; caption "With real residents the true change date is unknown, so this panel becomes: alarms raised, alarms reviewed, and review outcomes." | UX-371..UX-374, UX-376, FR-318 |
| FEAT-072-FR-12 | With `production` the panel shall be "Alarms and review outcomes" with a two-column table ("", "Count") and rows "Alarms raised", "Reviewed", "Checked on resident, no concern", "Explained by a known cause", "Referred to nurse or provider", "Looks like a data problem: send to study team"; the timing data never shows in production. | UX-375, UX-376, FR-319 |
| FEAT-072-FR-13 | After the timing panel a section with `id="devices"` and heading "Devices" shall show rows (status tag column "● Online" in `--green` when `uploaded_on_as_of_date` is true for the row's devices, otherwise "○ No upload today" in `--muted`; 14px, weight 700; text column) in the order grouped, shared, replacement, needing attention, natural device order within a kind: shared "**<D>** (shared by <R> and <R>): last upload <date-time>." + silent text; replacement "**<D>** (<R>): in use since <Mon D>, replacing <old D>. Last upload <date-time>." (the retired device gets no row); needing attention "**<D>** (<R list>): last upload <date-time>." + silent text + " Firmware <version>." when it differs from the most common one; grouped "**<compressed list>:** all uploaded <as-of Mon D>. Firmware <version>." with runs of 3 or more joined by " to "; silent text none / " Silent all day <Mon D>[, <Mon D>…]." (1–3 days) / " Silent all day on <k> days (latest <Mon D>)." | UX-050..UX-054, §4.4, FE-102, FR-150, FR-151, FR-152, FR-153, FR-155, FR-156 |
| FEAT-072-FR-14 | Below the rows a disclosure "Show all devices (<count>)" shall reveal a table "Device", "Residents", "In use" ("Since <Mon D>" or "<Mon D>–<Mon D> · replaced by <D>"), "Last upload", "Firmware", "Days with no device activity (last 30 days)" (`silent_days_last_30`, count plus up to 3 dates, e.g. "1 (Oct 12)" or "0"), "Silent days (shared device)" (`device_gap_days_last_30`), one row per device including inactive ones; loading `/study#devices` scrolls to the section and moves focus to its heading. | UX-055..UX-057, FE-026, FR-154 |
| FEAT-072-FR-15 | A "Downloads" panel at the end of the page shall offer "Scores (CSV)" and "Baselines (CSV)" calling `GET /scores` and `GET /analytics/baselines` with `Accept: text/csv`. | UX-377 |
| FEAT-072-FR-16 | The page shall use no alarm wording other than "Alarms raised", "Alarm timing check" and "Alarm rang", shall not rank residents by health state, and shall show no resident name, note or audio. | §4.18.7, UX-001 |
| FEAT-072-FR-17 | With no succeeded pipeline run the page shall show the empty state "No pipeline run yet"; with no devices the Devices section reads "No devices are registered yet."; each panel renders its own loading, empty and error state. | UC-14, UX-204, UX-202, LOG-083 |
| FEAT-072-FR-18 | With the reference data the page shall render TRD 11 §4.18.8 and §4.13.4: tiles 94 % / "281 of 300 expected", 89 % / "267 of 300 expected", "9 of 10" / "R08 still forming; R07 restarted once", 2 / "R09, R10; neither reviewed yet"; data problems "Staff can help — **R08:** baseline stuck at 13 of 16. 12 missed and 5 set aside in 30 days.", "Staff can help — **R03:** 7 of 29 received check-ins set aside (noise, quality flag, too short).", "Study team — **R05:** 2 check-ins held back as possible other voice (Oct 8, Oct 22).", "Study team — **D02:** silent all day Oct 12. Affected R02 and R03."; x labels "Oct 1", "Oct 12: D02 silent", "Oct 30"; funnel 300/281/269/267 with the notes; by resident R08 43 %, R03 73 %, R02 80 %, R05 93 %, others 100 %; timing R09 · Sudden step · Oct 21 · Oct 21 · 0 days, R10 · Slow drift · Oct 17 · Oct 24 · 7 days, Other 8 · None · None · No alarm · Correct; Devices "● Online" rows "**D01, D04 to D06, D08 to D10:** all uploaded Oct 30. Firmware fw-1.0.0.", "**D02** (shared by R02 and R03): last upload Oct 30, 2:55 PM. Silent all day Oct 12.", "**D07B** (R07): in use since Oct 13, replacing D07. Last upload Oct 30, 2:52 PM." and "Show all devices (10)". | UX-380..UX-384, UX-331, UX-058, UX-263, FR-323 |

## Inputs

- `GET /api/v1/analytics` → `AnalyticsResponse` (`meta`, `period`, `kpis`, `daily_series`, `funnel`, `by_resident`, `alarm_timing` or `review_outcomes`, `status_totals`, `pipeline_run`).
- `GET /api/v1/data-alerts?status=open` → `DataAlertList` (`kind`, `resident_code` or `device_code`, `title`, `detail`).
- `GET /api/v1/devices?limit=500` → `DeviceList` (`uploaded_on_as_of_date`, assigned residents, last upload, firmware, `in_use_since`, `in_use_until`, `replaces_device_code`, `replaced_by_device_code`, `silent_days_last_30`, `device_gap_days_last_30`).
- Role from `useAuth()`; `meta.pipeline_profile`, `meta.data_source_label`, `meta.facility_tz`.

## Outputs

- Rendered page; CSV file downloads via the browser.

## Data Flow

Role check → parallel `getAnalytics()`, `getDataAlerts({status: "open"})`, `getDevices()` → `KpiTiles(kpis)` (notes composed in `wording.ts`), `DataProblemsList(alerts)`, `DailyCheckinsChart(daily_series, meta)`, `LossFunnel(funnel)`, `UsableByResidentChart(by_resident)`, `AlarmTimingTable` (planted rows + grouped "Other <k>") or `ReviewOutcomesTable(review_outcomes)`, `DevicesSection(devices, meta)` → Downloads → `downloadScoresCsv`, `downloadBaselinesCsv`.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-064, FEAT-051, FEAT-029, FEAT-032

- FEAT-064 provides the app bar, nav visibility and access-denied state.
- FEAT-051 provides the `kpis`, `daily_series`, `funnel`, `by_resident` blocks (FEAT-035, through FEAT-051, provides the rest of E-18).
- FEAT-029 provides `GET /devices` (with `uploaded_on_as_of_date`, D-114); FEAT-032 provides `GET /data-alerts`.

Features that build directly on this one (BACKLOG.md §4): FEAT-075.

## Database Impact

None (frontend only).

## API Impact

Endpoints consumed: `GET /api/v1/analytics` (E-18), `GET /api/v1/data-alerts` (E-30), `GET /api/v1/devices` (E-17), `GET /api/v1/scores` (E-12, CSV), `GET /api/v1/analytics/baselines` (E-19, CSV). None exposed.

## Frontend Impact

- Page: `app/(protected)/study/page.tsx`.
- Components: `StudyTeamPage`, `KpiTiles`, `DataProblemsList`, `DailyCheckinsChart`, `LossFunnel`, `UsableByResidentChart`, `AlarmTimingTable`, `ReviewOutcomesTable`, `DevicesSection`, `SectionState`.

## Analytics Impact

None. All counts, percentages, data-alert texts and device states come from the API; the UI only groups the "Other <k>" timing row and the device rows and composes note strings (UX-354, UX-355, UX-372, §4.4).

## Security Requirements

- Clinicians never trigger a Study team request (FE-037); the backend returns 403 to them for analytics (FR-310).
- No resident names, notes or audio on the page (UX-001, FR-311); CSV downloads only for researcher and admin (OAS-018).

## Error Handling

- 403 → access message (FE-035); per-panel errors independent (LOG-083); no succeeded run → "No pipeline run yet".
- CSV download 413 → error message with reference (FEAT-062 error mapping).

## Logging Requirements

None in the frontend; the backend writes `export.csv` audit rows for CSV downloads (TRD 12 §4.12).

## Testing Requirements

- Component (TST-090): `KpiTiles` (values and all note variants incl. every UX-355 review state), `DataProblemsList` (four DS-07 rows in order, tags, link targets and accessible names, no "▲", empty text), `DailyCheckinsChart` (legend order, x labels, table rows for Oct 1, Oct 12, Oct 22, accessible name), `LossFunnel` (notes incl. singular/plural), `UsableByResidentChart` (order, widths, links, accessible names), `AlarmTimingTable` (grouped Other row, delays, false alarm), `ReviewOutcomesTable`, `DevicesSection` (row kinds and order, tags, grouped list "D01, D04 to D06, D08 to D10", silent text variants, "Show all devices (10)" table with D08 "12" days with no device activity and D07 "Oct 1–12 · replaced by D07B").
- FE-195: `StudyTeamPage` with `meta.pipeline_profile` = `production` renders `ReviewOutcomesTable` instead of `AlarmTimingTable` and the period line omits the answer-key clause.
- Page test (`frontend/tests/pages/study.test.tsx`): loading, populated, empty ("No pipeline run yet"), error, 401 → login, clinician access-denied with no request, `#devices` focus (TST-094).
- E2E (`study-team.spec.ts`, FE-194): E2E-07 (Study team devices), E2E-17 (data problems part), E2E-20 (researcher values), E2E-21 (clinician refused).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-072-AC-01 | As researcher on DS-07, `/study` shows "Study team: how the system is working", "Counts only. No audio, no names.", "pipeline test data v0.1, Oct 1–30, 2026 · numbers match the pipeline answer key" and the tiles 94 % "281 of 300 expected", 89 % "267 of 300 expected", "9 of 10" "R08 still forming; R07 restarted once", 2 "R09, R10; neither reviewed yet". | E2E-20; FE-194; UX-380 |
| FEAT-072-AC-02 | "Data problems to follow up" shows exactly R08 (Staff can help), R03 (Staff can help), R05 (Study team), D02 (Study team) in that order with the texts of FEAT-072-FR-18; "R08" links to `/residents/R08/log` and "D02" to `/study#devices`; no "▲" and no red. | E2E-17; E2E-20; UX-331; TDV-068 |
| FEAT-072-AC-03 | The funnel shows 300 "10 residents × 30 days" → 281 "19 missed; 2 duplicate copies removed" → 269 "12 set aside: quality flag 5, noise 5, too short 3 (1 had two reasons)" → 267 "2 held back as possible other voice"; by-resident rows read R08 43 %, R03 73 %, R02 80 %, R05 93 %, R01, R04, R06, R07, R09, R10 100 % in that order. | E2E-20; UX-382; UX-383 |
| FEAT-072-AC-04 | The daily table shows Oct 1 10/0/0/0, Oct 12 8/0/0/2 with note "D02 silent" and Oct 22 8/1/1/0, the legend reads Used, Set aside, Held back (other voice), Missed, and the x axis labels "Oct 1", "Oct 12: D02 silent", "Oct 30". | FE-194; UX-381 |
| FEAT-072-AC-05 | The alarm timing table shows R09 · Sudden step · Oct 21 · Oct 21 · 0 days, R10 · Slow drift · Oct 17 · Oct 24 · 7 days, Other 8 · None · None · No alarm · Correct, with the line "Test data only, where the true change date is known." | E2E-20; UX-384 |
| FEAT-072-AC-06 | `/study#devices` scrolls the Devices section into view and focuses its heading; it shows the three "● Online" rows of TRD 11 §4.13.4 in order, and "Show all devices (10)" lists 10 devices, D08 with 12 days with no device activity, D07 "Oct 1–12 · replaced by D07B". | E2E-07; AC-UX-03; UX-058; UX-263 |
| FEAT-072-AC-07 | With a `production` fixture the "Alarms and review outcomes" table replaces the timing table and the period line has no "numbers match the pipeline answer key". | FE-195; AC-UX-12 |
| FEAT-072-AC-08 | As clinician, `/study` shows the access-denied state and no Study team request is sent. | E2E-21; FE-037 |

## Definition of Done

- All FEAT-072 acceptance criteria pass; component, page and E2E tests green.
- Study team shows 281 of 300 (94 %), 267 of 300 (89 %), 9 of 10, 2, the four data problems, the timing table and the three device rows (TRD 25 Phase 8 DoD, as updated for v0.2).
- The batch report lists the implemented requirement IDs (AGT-022).

## Implementation Notes

- The data-problem text is the API `detail` (produced by the backend with the v0.2 wording, D-114); the UI renders "<code>: <detail>" with the code in bold and never rewrites it.
- R03 is listed as `high_set_aside` and R08 is not, because `baseline_stalled` suppresses `high_set_aside` for the same resident (FR-295, UX-331).
- The E-18 DTO carries counts and codes but no note strings; compose KPI notes in `lib/wording.ts` per UX-354 and UX-355.
- The "Other <k>" row groups `alarm_timing` items with `planted_change` "None" (`result` `correct_no_alarm`); show them individually only when one of them alarmed (UX-372).
- Do not show R07's retired device D07 as a device row; do show it in the "Show all devices" table (TRD 11 §8).
- All Recharts components set `isAnimationActive={false}` (FE-099).
- The file name keeps the v0.1 title (feature IDs and file names are never renamed, TRD 25 §4.2).
