# FEAT-065 Resident list page (filters, residents table, What's happening, status legend, note)

| Field | Value |
|---|---|
| Epic | Frontend |
| Build phase | Phase 8 (TRD 25) |
| Priority | P0 |
| Complexity | High |
| MVP status | Required |
| Dependencies | FEAT-064, FEAT-027 |
| Status | Not Started |

## Purpose

Implement `/residents`, the home page of the dashboard as wireframe v0.2 draws it (SRC-21, TRD 24 D-110): one panel with the `<h1>` "Residents in the study" and the filter buttons "All (<n>)", "Changed (<n>)", "Needs attention (<n>)", "Usual (<n>)" (plus "Learning (<n>)" only when someone is Learning) kept in `?show=`, the four-column residents table (Status · Resident · What's happening · Last check-in) rendering the API rows in API order with a status pill and a one-line reason, the status legend, and under the panel the prompt note "A status is a prompt to check on someone, not a diagnosis. [Final clinical wording: confirm with PI]". With the reference data the page shows "All (10)", "Changed (2)", "Needs attention (2)", "Usual (6)" and the ten rows of TRD 11 §4.13.1, Changed first. The v0.1 summary tiles, sort select, device and 30-day-count columns and the Devices panel are not built (TRD 11 UX-020..UX-024, UX-030..UX-033, UX-035, UX-039 retired); devices move to the Study team page (FEAT-072) and each chart's Device section (FEAT-070).

## Business Context

- BR-12 (staff see at a glance who has changed from their own usual, who needs attention because check-ins are missing or unusable, who is still learning and who is usual) with the four display statuses of TRD 24 D-109.
- BR-18 (detection, not diagnosis): every status is a prompt to check on someone (UX-407).
- BR-03, BR-06: duplicates never shown; missing check-ins explained in plain words.
- BR-15: the page equals the answer-key-derived DS-07 values.
- The alarm queue of the retired Alert review page is replaced by this list (Changed residents sort first) and the nav badge (TRD 11 §4.17).
- FRs covered (BACKLOG.md): FR-130, FR-131, FR-132, FR-133, FR-134, FR-137, FR-140.

## Referenced TRDs

- TRD 11 (v0.13) — owned by this feature: UX-034, UX-036, UX-037, UX-038, UX-040..UX-046 (table, status cell, study-ID link, last check-in, row click, truncation line, scroll container, caption, duplicates, withdrawn, new admissions), UX-401..UX-405, UX-408 (filter buttons, filtering, announcement, `?show=`, API order, "What's happening" cell), UX-406 (legend), UX-407 (note), §4.3.6 templates, UX-260, UX-261 (reference rendering §4.13.1, §4.13.2). Uses `StatusPill` (§4.3.4, FEAT-062). Retired, not built: UX-020..UX-024, UX-030..UX-033, UX-035, UX-039.
- TRD 04 (v0.11) FE-081 (5-minute refetch), FE-082 (`?show=` filter), FE-083 (keep previous rows, `aria-busy`), FE-084 (API order, no re-sort), FE-025 (last filter for the back link), FE-181, FE-182 (component tests), FE-185 (E2E `resident-list.spec.ts`), §4.8 `FilterButtons`, `ResidentsTable`, `WhatsHappening`, `StatusLegend`.
- TRD 19 E-08 `GET /api/v1/residents` (`OverviewSummary` `{changed, needs_attention, learning, usual}`, rows with `needs_attention`, `attention_reasons`, `alarm_reviewed`; `sort=alarm` redefined; TRD 24 D-109, D-114).
- TRD 13 TST-090, TST-091, TST-092 (as updated for v0.2); E2E-03..E2E-06.
- TRD 02 FR-130..FR-134, FR-137, FR-140; TRD 24 D-108, D-109, D-110, D-113, D-114, OQ-12, OQ-31, OQ-32.

## Scope

- `app/(protected)/residents/page.tsx`: query `getResidents({ sort: "alarm" })` (`limit=500`, longitudinal cohort, no withdrawn); one panel with header row (`<h1>` and `FilterButtons`), `ResidentsTable`, `StatusLegend`; the prompt note under the panel.
- Components: `FilterButtons` (`{ summary, total, value, onChange }`), `ResidentsTable` (`{ rows, meta, filter, isFetching }`), `WhatsHappening` (`{ row, meta }`), `StatusLegend` (`{ meta }`); wording templates of §4.3.6 (`whatsHappening()`) in `lib/wording.ts`.
- Client-side filtering of the already loaded rows; `?show=` URL state with `router.replace`; the last value is also written to `sessionStorage["echowell.residentList.show"]` (in `try/catch`, default `all`; FE-025) for the chart's back link (FEAT-066).
- Per-panel `SectionState` (loading, empty, error) from FEAT-062.
- Component and page tests with DS-07 fixtures; the resident-list E2E specs.

## Out of Scope

- Display status inputs, attention flag, summary counts and the `sort=alarm` order (backend FEAT-027; the UI never re-sorts and computes no data-alert rule).
- The Devices section and the data-problem list (FEAT-072); the resident chart (FEAT-066..FEAT-071); New admissions (FEAT-073).
- Room numbers or sorting by room (OQ-32; no room data is shown, UX-001).
- Responsive and accessibility audit across pages (FEAT-075), beyond the structural requirements listed here.

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-065-FR-01 | The page shall show one panel whose header row contains the `<h1>` "Residents in the study" (22px) on the left and, on the right, a group (`role="group"`, accessible name "Show") of toggle buttons (15px, padding 6px 12px, radius 999px, 1px solid `--rule`; pressed: `--chrome` background and border, `--chrome-ink` text, `aria-pressed="true"`) in the order "All (<n>)", "Changed (<n>)", "Needs attention (<n>)", "Learning (<n>)", "Usual (<n>)", where "Learning (<n>)" is shown only when `summary.learning` > 0 and the counts come from the API `summary`; "All" is pressed by default. | UX-401, D-109 |
| FEAT-065-FR-02 | Pressing a filter shall show only the rows of that display status (via `toDisplayStatus()`), keep their API order and leave all counts unchanged; the status counts sum to the "All" count; with no matching rows the table shows one row "No residents with this status." | UX-402, FR-133 |
| FEAT-065-FR-03 | Changing the filter shall not reload the page or send a request, keep focus on the pressed button, announce "Showing <label> residents" ("Showing all residents") in a polite live region, and write `?show=` (`all`, `changed`, `needs_attention`, `learning`, `usual`; default `all`, invalid values read as `all`) with `router.replace`, so that reload, back navigation and the chart's back link show the same filter. | UX-403, UX-404, UX-201, FE-082 |
| FEAT-065-FR-04 | Rows shall render in exactly the API order of `sort=alarm` (Changed by alarm date oldest first then natural code, then Needs attention, Learning, Usual by natural code); the frontend shall not re-sort. | UX-408, FE-084, FR-133 |
| FEAT-065-FR-05 | The table shall have the columns "Status", "Resident", "What's happening", "Last check-in" with header cells 14px, weight 600, `--muted`, background `--surface-2`, `scope="col"`, a visually hidden `<caption>` "Residents in the study, <filter label>" (e.g. "Residents in the study, all"), body cells padding 12px 18px with a 1px solid `--rule` bottom border; a Changed row has a 5px `--red` left border on its first cell and a Needs-attention row a 5px `--yellow-edge` left border. | UX-034, UX-043 |
| FEAT-065-FR-06 | The table shall sit in a container with `overflow-x: auto`, `tabindex="0"` and the accessible name "Residents table"; the table has `min-width: 640px`. | UX-042 |
| FEAT-065-FR-07 | The Status cell shall show `StatusPill` with the row's display status. | UX-036, FR-131 |
| FEAT-065-FR-08 | The Resident cell shall show the study ID in weight 700 as a link to `/residents/<R>` (chart Summary) with the accessible name "Open chart for <R>"; a click anywhere on the row opens the same page (pointer convenience; the row is not a separate tab stop). | UX-037, UX-040, FR-140 |
| FEAT-065-FR-09 | The "What's happening" cell shall show one sentence from `lib/wording.ts` per TRD 11 §4.3.6: Changed "Changed from their usual since <Mon D>. Not reviewed yet." / "… Reviewed." (by `alarm_reviewed`); Needs attention `baseline_stalled` "Missing many check-ins. Baseline stuck at <n> of <N>.", `high_set_aside` "<k> check-ins too noisy or too short to use." (both: `baseline_stalled` sentence first, one space); Learning "Learning their usual: <n> of <N> check-ins so far."; Usual "Within their usual range." or, with current epoch > 1, "Usual. Baseline restarted <Mon D> after a new device." (firmware: "… after a firmware change."; software: "… after a software change."). | UX-405, FR-131, FR-132, D-109 |
| FEAT-065-FR-10 | The "Last check-in" cell (`--muted`) shall show `last_checkin_at` formatted "Oct 30, 2:28 PM CT" in `meta.facility_tz` (most recent non-duplicate record of any status), or "No check-ins yet". | UX-038 |
| FEAT-065-FR-11 | Under the table the panel shall show the status legend: for each of the four statuses its pill followed by its meaning text — "Their voice has moved away from their own usual. Check on them.", "Not enough good check-ins to judge. Check the device or the routine.", "Still collecting the first <N> check-ins to learn their usual.", "Within their own usual range." — 14px, `--muted`, wrapping. | UX-406 |
| FEAT-065-FR-12 | Under the panel the note "A status is a prompt to check on someone, not a diagnosis. [Final clinical wording: confirm with PI]" (14px, `--muted`) shall appear; the bracketed part stays while `CLINICAL_WORDING_APPROVED` is false (OQ-12). | UX-407, UX-162, UX-164 |
| FEAT-065-FR-13 | When `total` exceeds the returned items, the line "Showing <returned> of <total> residents." shall appear under the table; the list is requested with `limit=500`. | UX-041, FE-076 |
| FEAT-065-FR-14 | Only enrolled, non-withdrawn residents of the longitudinal cohort returned by the API are listed; new admissions appear only after their own baseline has formed; duplicates never appear in any count or row. | UX-044, UX-045, UX-046, FR-130 |
| FEAT-065-FR-15 | The residents query shall refetch every 5 minutes while the document is visible; previous rows stay visible during a refresh with `aria-busy="true"` on the table. | FE-081, FE-083, UX-201 |
| FEAT-065-FR-16 | With the reference data the page shall render exactly the filters and rows of TRD 11 §4.13.1 and, per filter, the rows of §4.13.2. | UX-260, UX-261, FR-137 |
| FEAT-065-FR-17 | Empty and loading states: no residents "No residents are enrolled yet."; while loading the filter counts show "—". | UX-204, UX-200 |

## Inputs

- `GET /api/v1/residents?sort=alarm&cohort=longitudinal&include_withdrawn=false&limit=500` → `ResidentsOverviewResponse` (`meta`, `window`, `summary` `{changed, needs_attention, learning, usual}`, `items` with `status`, `needs_attention`, `attention_reasons`, `alarm_reviewed`, alarm date, baseline progress, current epoch start and restart cause, `last_30_days`, `last_checkin_at`; `total`).
- `?show=` URL parameter.

## Outputs

- Rendered `/residents` page; URL updates on filter change; the last filter value for the chart's back link.

## Data Flow

`getResidents({sort: "alarm"})` (`["residents", {sort: "alarm"}]`) → `FilterButtons` (summary counts) and `ResidentsTable` (items in API order → `toDisplayStatus()` → `StatusPill`; `WhatsHappening` (`whatsHappening(row, meta)`); `formatDateTimeShort`) filtered by `?show=` in the browser → `StatusLegend` (meta.baseline_n) → note. The app bar and data bar come from FEAT-064.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-064, FEAT-027

- FEAT-064 provides the route shell, app bar, data bar and navigation.
- FEAT-027 provides `GET /api/v1/residents` with the display-status inputs, the attention flag, the summary counts and the `sort=alarm` order (TRD 24 D-109, D-114).

Features that build directly on this one (BACKLOG.md §4): FEAT-075.

## Database Impact

None (frontend only).

## API Impact

Endpoint consumed: `GET /api/v1/residents` (E-08); the app bar's `GET /api/v1/alerts?status=open` (E-13) comes from FEAT-064. None exposed. The page no longer calls `GET /api/v1/devices`.

## Frontend Impact

- Page: `app/(protected)/residents/page.tsx`.
- Components: `FilterButtons`, `ResidentsTable`, `WhatsHappening`, `StatusLegend`, `StatusPill` (FEAT-062), `SectionState`.

## Analytics Impact

None. Statuses, attention flag, counts and order are rendered as returned by the API.

## Security Requirements

- Residents shown by study ID only; no name, photo or room (UX-001, OQ-32).
- Data fetched client-side with the Bearer token; no server-side rendering of resident data (FE-040).

## Error Handling

- Residents query error → error state inside the panel; the app bar and data bar stay (UX-202, LOG-083).
- Refetch failure with cached data → stale notice (FE-144).
- 401 → login redirect (FEAT-063); 403 → access message (FE-035).

## Logging Requirements

None in the frontend.

## Testing Requirements

- Component (co-located, TST-090): `FilterButtons` asserts "All (10)", "Changed (2)", "Needs attention (2)", "Usual (6)" in order, no Learning button on DS-07 and "Learning (1)" on a fixture with a Learning row, `aria-pressed`, counts unchanged after filtering; `ResidentsTable` asserts for R01–R10 the pill, "What's happening" text and last check-in of §4.13.1 in API order (FE-182), the row borders, the caption per filter, the study-ID link names and "No residents with this status."; `StatusLegend` asserts the four meanings with N from `meta`; all "What's happening" templates incl. reviewed, both-reasons and firmware/software restart variants.
- Page test (`frontend/tests/pages/residents.test.tsx`, MSW): loading, populated, empty, error with reference, `?show=changed` on load, filter change without request, live-region text, 401 → login (TST-094).
- E2E (`resident-list.spec.ts`, FE-185): E2E-03 (filters, legend and note), E2E-04 (default rows of §4.13.1), E2E-05 (Changed and Needs attention filters, `?show=`, announcement), E2E-06 (filter kept on reload and after the chart's back link) of TRD 13 Table 4.10-A.

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-065-AC-01 | With DS-07, `/residents` shows "Residents in the study", the filters "All (10)", "Changed (2)", "Needs attention (2)", "Usual (6)" (no Learning button) and "All" pressed. | E2E-03; AC-UX-01; UX-401 |
| FEAT-065-AC-02 | The rows are R09, R10, R03, R08, R01, R02, R04, R05, R06, R07 with the pills, "What's happening" texts and last check-ins of TRD 11 §4.13.1 (e.g. R09 "▲ Changed", "Changed from their usual since Oct 21. Not reviewed yet.", "Oct 30, 2:28 PM CT"; R08 "! Needs attention", "Missing many check-ins. Baseline stuck at 13 of 16."; R07 "● Usual", "Usual. Baseline restarted Oct 13 after a new device."). | E2E-04; FE-182; UX-260 |
| FEAT-065-AC-03 | Pressing "Changed" shows R09, R10; "Needs attention" R03, R08; "Usual" R01, R02, R04, R05, R06, R07; "All" the ten rows; the URL contains the matching `?show=` value, the counts do not change and "Showing changed residents" is announced; after a reload with `?show=usual`, and after opening R01 and following "← Resident list", the Usual rows are shown again. | E2E-05; E2E-06; AC-UX-02; UX-261 |
| FEAT-065-AC-04 | The status legend lists the four pills with their meaning texts ("Still collecting the first 16 check-ins to learn their usual." on DS-07) and the note "A status is a prompt to check on someone, not a diagnosis. [Final clinical wording: confirm with PI]" appears under the panel. Verified by: Component (TST-090). | UX-406; UX-407 |
| FEAT-065-AC-05 | Clicking the R09 row or its "R09" link (accessible name "Open chart for R09") opens `/residents/R09`. Verified by: Page test (TST-094). | UX-037; UX-040; FR-140 |
| FEAT-065-AC-06 | No row, count or text on the page reflects R04's two duplicate arrivals. Verified by: Page test (`frontend/tests/pages/residents.test.tsx`; TST-094). | UX-044; AGT-053 |
| FEAT-065-AC-07 | At 375px width the table scrolls inside its focusable container "Residents table" while the page does not. Verified by: E2E (`responsive.spec.ts`, FEAT-075). | UX-042 |

## Definition of Done

- All FEAT-065 acceptance criteria pass; component, page and E2E tests green in Chromium.
- Resident list reads "All (10)", "Changed (2)", "Needs attention (2)", "Usual (6)" with test data and lists R09 and R10 first (TRD 25 Phase 8 DoD, as updated for v0.2).
- Batch report lists IDs (AGT-022).

## Implementation Notes

- Do not compute the list order client-side; the `sort=alarm` order is defined by the API (D-109 amends D-17). The `resident_id` and `last_checkin` sorts stay in the API but are not offered in the UI.
- Which data alerts turn a resident yellow was OQ-31, answered by TRD 24 D-115; the UI renders the API flag and the reasons it lists (`baseline_stalled`, `high_set_aside`) and never derives them.
- R05 (held-back check-ins) and D02 (silent day) are study-team data problems and do not change a resident's colour (D-109); they appear on the Study team page (FEAT-072).
- The "Learning (<n>)" button appears only when someone is Learning (question 2 of the v0.2 review for the algorithm lead).
- "Last check-in" counts set-aside and held-back records but never duplicates (TRD 11 §8).
- The file name keeps the v0.1 title (feature IDs and file names are never renamed, TRD 25 §4.2).
