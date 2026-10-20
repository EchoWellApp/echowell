# FEAT-065 Residents overview page with Devices panel

| Field | Value |
|---|---|
| Epic | Frontend |
| Build phase | Phase 8 (TRD 25) |
| Priority | P0 |
| Complexity | High |
| MVP status | Required |
| Dependencies | FEAT-064, FEAT-027, FEAT-029 |
| Status | Not Started |

## Purpose

Implement `/residents`, the home page of the dashboard (SRC-09): the four summary tiles, the sort control kept in the URL, the residents table rendering the API rows in API order with status badges, device text, last check-in, last-30-days counts and "Open" links, the Devices panel `#devices` (shared, replacement, needing-attention and grouped device cards plus the "Show all devices" table) and the overview footer. With the reference data the page shows tiles 2 / 7 / 1 / 19 and the ten rows of TRD 11 §4.13.1.

## Business Context

- BR-12 (staff see at a glance who has an alarm, who is being watched, whose baseline is forming, and missed or set-aside check-ins).
- BR-06, BR-08, BR-03: missed days, device sharing/replacement and duplicates are shown or hidden exactly as the pipeline defines them.
- BR-15: the page equals the answer-key-derived DS-07 values.
- FRs covered (BACKLOG.md): FR-130, FR-131, FR-132, FR-133, FR-134, FR-135, FR-136, FR-137, FR-138, FR-139, FR-140, FR-150, FR-151, FR-152, FR-153, FR-154, FR-155, FR-156.

## Referenced TRDs

- TRD 04 FE-081 (5-minute refetch), FE-082 (sort in URL), FE-083 (keep previous rows, `aria-busy`), FE-084 (API order, no re-sort), FE-088 (subline from `meta`), FE-102 (`compressDeviceCodes`), FE-103 (footer), FE-181, FE-182 (component tests), FE-185 (E2E `overview.spec.ts`), §4.8 `SummaryTiles`, `SortSelect`, `ResidentsTable`, `StatusBadge`, `DeviceCell`, `DevicePanel`.
- TRD 11 UX-020..UX-024 (tiles), UX-030..UX-033 (sort), UX-034..UX-048 (table, device cell, badge, last check-in, counts, Open link, truncation line, scroll container, caption, duplicates, withdrawn, new admissions), §4.3.4 badges, §4.3.5 count semantics, UX-050..UX-058 (Devices panel), §4.13.1, §4.13.2, §4.13.4.
- TRD 13 TST-091 (StatusBadge), TST-092 (sort orders), TST-090; E2E-03..E2E-07.
- TRD 19 E-08 `GET /api/v1/residents`, E-17 `GET /api/v1/devices`.
- TRD 02 FR-130..FR-140, FR-150..FR-156.

## Scope

- `app/(protected)/residents/page.tsx`: queries `getResidents({sort})` and `getDevices()`; header via `AppHeader` (FEAT-064); tiles, residents section, devices section, footer variant `overview`.
- Components: `SummaryTiles`, `SortSelect`, `ResidentsTable`, `StatusBadge`, `DeviceCell`, `DevicePanel` (cards + "Show all devices (<count>)" disclosure table).
- Per-section `SectionState` (loading, empty, error) from FEAT-062.
- Component tests with DS-07 fixtures and the `overview.spec.ts` E2E.

## Out of Scope

- The display-status and sort computation (backend FEAT-027; the UI never re-sorts).
- Device data derivation (`silent_days_last_30`, `device_gap_days_last_30`, `in_use_until`, FEAT-029 / FEAT-014).
- Resident detail page (FEAT-066) and New admissions page (FEAT-073).
- Responsive and accessibility audit across pages (FEAT-075), beyond the structural requirements listed here.

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-065-FR-01 | Four tiles shall appear in the order "Alarm on" (`summary.alarm_on`), "Being watched, no alarm" (`summary.no_alarm`), "Baseline still forming" (`summary.baseline_forming`), "Missed check-ins, last 30 days" (`summary.missed_last_30_days`) as static text; the "Alarm on" tile has a 2px accent border and accent value when > 0, else 1px border and ink; tiles 2–4 1px border, ink. | UX-020..UX-024, FR-136 |
| FEAT-065-FR-02 | The Residents section header shall show "Residents" and the label "Sort by" bound to a native `<select id="sort">` with exactly "Alarms first" (default, `alarm`), "Resident ID" (`resident_id`), "Last check-in" (`last_checkin`). | UX-030, UX-031, FR-133 |
| FEAT-065-FR-03 | The sort shall be kept in `?sort=` (default `alarm` when absent or invalid) and changed with `router.replace` without scrolling; focus stays on the select; "Sorted by <option label>" is announced in a polite live region; previous rows stay visible with `aria-busy="true"` until the new response arrives. | FE-082, FE-083, UX-032, UX-033, UX-201 |
| FEAT-065-FR-04 | Rows shall render in exactly the API `items` order for the selected sort; the frontend shall not re-sort. | FE-084, FR-133 |
| FEAT-065-FR-05 | The table shall have the columns "Resident", "Device", "Status", "Last check-in (local)", "Last 30 days: used · set aside · quarantined · missed" and an action column (visually hidden header "Actions"), a visually hidden caption "Residents, sorted by <option label>", `scope="col"` headers, and sit in an `overflow-x: auto` container with `min-width: 900px`. | UX-034, UX-042, UX-043 |
| FEAT-065-FR-06 | The Device cell shall show the device code, " (shared)" when `device_shared`, and " (was <previous_device_code>)" when present, the appended text in secondary colour (e.g. "D02 (shared)", "D07B (was D07)"). | UX-035, FR-134 |
| FEAT-065-FR-07 | The Status cell shall show `StatusBadge` with the TRD 11 §4.3.4 text and style: "▲ Alarm since <Mon D>" (2px accent, accent text, 600), "No alarm", "No alarm · baseline restarted <Mon D>" (epoch > 1), "Baseline forming · <n> of <N> sessions" (1px dashed), "Baseline forming · <n> of <N> sessions · restarted <Mon D>"; text from `lib/wording.ts` `statusLabel()`; the alarm variant always includes "▲". The resident cell of an `alarm_on` row is weight 600. | UX-036, UX-037, FE-092, FR-131, FR-132 |
| FEAT-065-FR-08 | "Last check-in (local)" shall show `last_checkin_at` formatted "Oct 30, 2:28 PM" in `meta.facility_tz`, or "No check-ins yet". | UX-038, FR-134 |
| FEAT-065-FR-09 | The last-30-days cell shall show `used · set_aside · quarantined · missed` from `last_30_days` (e.g. "13 · 5 · 0 · 12"); duplicates never appear in any count, row or log. | UX-039, UX-044, UX-047, UX-048, FR-135 |
| FEAT-065-FR-10 | The action cell shall contain an "Open" link (min-height 44px) to `/residents/<R>` with accessible name "Open <R>". | UX-040, FR-140 |
| FEAT-065-FR-11 | When `total` exceeds the returned items, the line "Showing <returned> of <total> residents." shall appear under the table; the list is requested with `limit=500`. | UX-041, FE-076 |
| FEAT-065-FR-12 | Only active longitudinal residents returned by the API are listed (withdrawn hidden; new admissions only after their baseline formed). | UX-045, UX-046, FR-130 |
| FEAT-065-FR-13 | The Devices section (`id="devices"`, heading "Devices") shall follow the table and show cards in the order shared, replacement, needing attention, grouped (natural device order within a kind) with the line texts of TRD 11 §4.4, including the silent text rule over `device_gap_days_last_30` ("silent all day Oct 12"; > 3 days "silent all day on <k> days (latest <Mon D>)"). | UX-050, UX-051, UX-052, FR-150, FR-151, FR-152, FR-153 |
| FEAT-065-FR-14 | A replacement card shall read "<D> · <R>" / "In use since <Mon D> (replaced <old D>) · last upload <date-time>"; the retired device gets no card. | UX-053, FR-155 |
| FEAT-065-FR-15 | Remaining active devices (uploaded on the as-of date, not shared, not replaced, no device-gap days) shall be grouped in one dashed card per firmware version titled with `compressDeviceCodes()` (e.g. "D01, D04–D06, D08–D10") and "All uploaded on <as-of Mon D> · firmware <version>". | UX-054, FE-102, FR-156 |
| FEAT-065-FR-16 | A disclosure "Show all devices (<count>)" shall reveal a table with columns "Device", "Residents", "In use", "Last upload", "Firmware", "Days with no device activity (last 30 days)" (from `silent_days_last_30`, count plus up to 3 dates, e.g. "1 (Oct 12)" or "0"), "Silent days (shared device)" (from `device_gap_days_last_30`), one row per device including inactive ones; "In use" reads "Since <Mon D>" or "<Mon D>–<Mon D> · replaced by <D>". | UX-055, UX-056, UX-057, FR-154 |
| FEAT-065-FR-17 | The header subline shall be built from the `meta` block of `getResidents`; the footer shall read "No audio is stored or played here — only extracted voice measurements. Duplicate records are removed quietly and not shown." | FE-088, FE-103, FR-138, FR-139 |
| FEAT-065-FR-18 | The residents and devices queries shall refetch every 5 minutes while the document is visible. | FE-081 |
| FEAT-065-FR-19 | With the reference data the page shall render exactly the tiles, rows, sort orders and device cards of TRD 11 §4.13.1, §4.13.2 and §4.13.4. | UX-058, FR-137 |
| FEAT-065-FR-20 | Empty states: table "No residents are enrolled yet."; devices "No devices are registered yet."; while loading tiles show "—". | UX-204, UX-200 |

## Inputs

- `GET /api/v1/residents?sort=<s>&cohort=longitudinal&include_withdrawn=false&limit=500` → `ResidentsOverviewResponse` (`meta`, `window`, `summary`, `items`, `total`).
- `GET /api/v1/devices?limit=500` → `DeviceList`.
- `?sort=` URL parameter.

## Outputs

- Rendered `/residents` page and `#devices` section; URL updates on sort change.

## Data Flow

URL `?sort` → `getResidents({sort})` (`["residents", {sort}]`) and `getDevices()` (`["devices"]`) → `SummaryTiles` (summary), `ResidentsTable` (items in API order, meta for formatting), `DevicePanel` (devices, meta) → per-section states; `AppHeader` subline from `meta`.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-064, FEAT-027, FEAT-029

- FEAT-064 provides the route shell, `AppHeader` and navigation.
- FEAT-027 provides `GET /api/v1/residents` with display status and sorts.
- FEAT-029 provides `GET /api/v1/devices`.

## Database Impact

None (frontend only).

## API Impact

Endpoints consumed: `GET /api/v1/residents` (E-08), `GET /api/v1/devices` (E-17), `GET /api/v1/alerts?status=open` (E-13, via `AppHeader`). None exposed.

## Frontend Impact

- Page: `app/(protected)/residents/page.tsx`.
- Components: `SummaryTiles`, `SortSelect`, `ResidentsTable`, `StatusBadge`, `DeviceCell`, `DevicePanel`, `Footer` (overview), `SectionState`.

## Analytics Impact

None. Counts, statuses and order are rendered as returned by the API.

## Security Requirements

- Residents shown by study ID only; no PII (UX-001).
- Data fetched client-side with the Bearer token; no server-side rendering of resident data (FE-040).

## Error Handling

- Residents query error → error state in the residents section only; devices section unaffected, and vice versa (UX-202, LOG-083).
- Refetch failure with cached data → stale notice (FE-144).
- 401 → login redirect (FEAT-063); 403 → access message (FE-035).

## Logging Requirements

None in the frontend.

## Testing Requirements

- Component (co-located): `SummaryTiles` asserts 2, 7, 1, 19 in order (FE-181); `ResidentsTable` asserts device cell, badge text, last check-in and counts for R01–R10 (FE-182) and the three sort orders on DS-07 fixtures (TST-092); `StatusBadge` asserts "▲ Alarm since Oct 21", "No alarm · baseline restarted Oct 13", "Baseline forming · 13 of 16 sessions" and non-colour cues (TST-091); `DevicePanel` asserts the §4.13.4 cards and "Show all devices (10)" table (D08 "12" days with no activity).
- Page test (`frontend/tests/pages/residents.test.tsx`, MSW): loading, populated, empty, error with reference, 401 → login (TST-094).
- E2E (`overview.spec.ts`, FE-185): E2E-03 tiles, E2E-04 default rows, E2E-05 Resident ID sort, E2E-06 Last check-in sort, E2E-07 devices panel via `#devices`.

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-065-AC-01 | With DS-07, `/residents` shows tiles "Alarm on" 2, "Being watched, no alarm" 7, "Baseline still forming" 1, "Missed check-ins, last 30 days" 19. | E2E-03; FE-181; AC-UX-01 |
| FEAT-065-AC-02 | The default rows are R09, R10, R08, R07, R03, R02, R05, R01, R04, R06 with the device, badge, last check-in and count texts of TRD 11 §4.13.1 (e.g. R08 "Baseline forming · 13 of 16 sessions", "Oct 30, 2:28 PM", "13 · 5 · 0 · 12"; R07 "D07B (was D07)", "No alarm · baseline restarted Oct 13"). | E2E-04; FE-182; AC-FE-02 |
| FEAT-065-AC-03 | Choosing "Resident ID" yields R01…R10 and "Last check-in" yields R02, R07, R05, R10, R06, R08, R09, R03, R04, R01, and the URL contains the matching `?sort=` value. | E2E-05; E2E-06; AC-UX-02; TST-092 |
| FEAT-065-AC-04 | `/residents#devices` scrolls the Devices panel into view with cards "D02 · shared by R02, R03" / "Last upload Oct 30, 2:55 PM · silent all day Oct 12", "D07B · R07" / "In use since Oct 13 (replaced D07) · last upload Oct 30, 2:52 PM", and the dashed "D01, D04–D06, D08–D10" / "All uploaded on Oct 30 · firmware fw-1.0.0". | E2E-07; AC-UX-03; UX-058 |
| FEAT-065-AC-05 | "Show all devices (10)" lists 10 devices, D08 shows 12 days with no device activity, D07 shows "Oct 1–12 · replaced by D07B". | AC-UX-03; UX-055..UX-057 |
| FEAT-065-AC-06 | R04's row shows "30 · 0 · 0 · 0" (its two duplicates are not counted anywhere on the page). | UX-044; AGT-053 |
| FEAT-065-AC-07 | `StatusBadge` component tests assert the three TST-091 texts and that the alarm badge contains "▲". | TST-091; FE-092 |

## Definition of Done

- All FEAT-065 acceptance criteria pass; component, page and E2E tests green in Chromium.
- Overview tiles read 2 / 7 / 1 / 19 with test data (TRD 25 Phase 8 DoD).
- Batch report lists IDs (AGT-022).

## Implementation Notes

- Do not compute the overview order client-side; capture fixtures per sort value (TRD 04 §8).
- Natural sort of device codes inside `compressDeviceCodes()` (D07 before D07B; runs only for codes without suffix) (FE-102, AGT-052).
- TRD conflict: FR-150 says the Devices panel has a header nav "Devices"; the navigation link is retired (FE-026, UX-016, contract §20 R2). Keep only the `#devices` anchor.
- FR-134 states "(was <old>)" applies after a device change in the current epoch, while TRD 11 §5 notes it applies when the replacement happened within the last 30 days; render "(was …)" whenever the API returns `previous_device_code` so the rule lives in the backend (FEAT-027).
- "Last check-in" counts set-aside and quarantined records but never duplicates (TRD 11 §8).
