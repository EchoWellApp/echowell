# Study team page (KPI tiles, data problems to follow up, check-in charts, alarm timing, Devices, downloads)

## Feature Description

`/study`, the Study team page that replaces the v0.1 Analytics page (SRC-21, D-110), for the roles researcher and admin: the header panel with the `<h1>` "Study team: how the system is working", "Counts only. No audio, no names." and the period line; four KPI tiles; "Data problems to follow up" (open data alerts tagged "Staff can help" or "Study team"); the "Check-ins per day" stacked bar chart with its table; "Where check-ins are lost" and "Usable check-ins by resident"; "Alarm timing check" (`test_v0_1`) or "Alarms and review outcomes" (`production`); the "Devices" section (`id="devices"`) with tagged rows and "Show all devices (<n>)"; the "Downloads" panel ("Scores (CSV)", "Baselines (CSV)"); and the empty state when no pipeline run has succeeded. Clinicians get the access-denied state (TRD 11 §4.4, §4.13.4, §4.18; TRD 04 FE-026, FE-037, FE-076, FE-102, FE-194, FE-195; TRD 19 E-12, E-17, E-18, E-19, E-30).

## Preconditions

- Local Docker Compose demo profile running, freshly seeded with `test_v0_1`, the DS-07 pipeline run (as-of Oct 30, 2026, 3:00 PM CT) and the DS-10 evaluation ground truth (`python database/seeds/load_evaluation_ground_truth.py tests/fixtures/answer_key/evaluation_ground_truth_v0_1.csv`); no reviews saved.
- Signed in as `researcher@example.com` (`SEED_RESEARCHER_PASSWORD`) unless the case says otherwise; `clinician@example.com` and `admin@example.com` for the role cases.
- For the empty-state case: the isolated `echowell_demo` database seeded with `seed test_v0_1 --master-only` (and optionally the R11 overlay) before any record is posted, so no pipeline run exists.
- Browser developer tools (Network panel, Accessibility tree); a file manager to open downloaded CSV files; `psql` read access.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-072-01 | Header panel and KPI tiles with DS-07 | High | Positive |
| TC-072-02 | Data problems to follow up: four rows, tags, order, links, no "▲"/red | High | Positive |
| TC-072-03 | Check-ins per day: legend, bars, x labels, tooltips, table, accessible name | High | Positive |
| TC-072-04 | Where check-ins are lost: four rows with notes and meter widths | High | Positive |
| TC-072-05 | Usable check-ins by resident: order, percentages, links, accessible names | High | Positive |
| TC-072-06 | Alarm timing check table and caption | High | Positive |
| TC-072-07 | Devices section via `/study#devices`: rows, tags, scroll and focus | High | Positive |
| TC-072-08 | "Show all devices (10)" table | High | Positive |
| TC-072-09 | Downloads: Scores and Baselines CSV | Medium | Positive |
| TC-072-10 | KPI note after reviews ("R10 …", "both reviewed") | Medium | Positive |
| TC-072-11 | Production profile: "Alarms and review outcomes", no answer-key clause | High | Positive |
| TC-072-12 | Clinician: access denied, no Study team request | High | Security |
| TC-072-13 | Admin can open the page; unauthenticated redirect | Medium | Security |
| TC-072-14 | Empty state "No pipeline run yet." and empty sub-panels | Medium | Negative |
| TC-072-15 | Per-panel errors are independent; CSV download failure | High | Negative |
| TC-072-16 | Wording and privacy rules; narrow-screen layout | Medium | UI |

### TC-072-01 Header and KPI tiles

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `/study` | Title "Study team – EchoWell"; "Study team" nav link `aria-current="page"` |
| 2 | Read the header panel | `<h1>` "Study team: how the system is working"; "Counts only. No audio, no names." (14px, `--muted`); "pipeline test data v0.1, Oct 1–30, 2026 · numbers match the pipeline answer key" |
| 3 | Read the four tiles in order | "Check-ins received" "94%" / "281 of 300 expected"; "Used for scoring" "89%" / "267 of 300 expected"; "Baselines formed" "9 of 10" / "R08 still forming; R07 restarted once"; "Alarms raised" "2" / "R09, R10; neither reviewed yet" |
| 4 | Inspect a tile | Label 13px `--muted`, value 18px weight 700, note 14px `--muted`; tiles min width 200px, gap 12px |

### TC-072-02 Data problems to follow up

| Step | Action | Expected Result |
|---|---|---|
| 1 | Read the panel after the tiles | Heading "Data problems to follow up"; four rows in order |
| 2 | Row 1 | Tag "Staff can help" (`--yellow`, 14px, weight 700); text "**R08:** baseline stuck at 13 of 16. 12 missed and 5 set aside in 30 days." |
| 3 | Row 2 | "Staff can help" — "**R03:** 7 of 29 received check-ins set aside (noise, quality flag, too short)." |
| 4 | Row 3 | Tag "Study team" (`--muted`) — "**R05:** 2 check-ins held back as possible other voice (Oct 8, Oct 22)." |
| 5 | Row 4 | "Study team" — "**D02:** silent all day Oct 12. Affected R02 and R03." |
| 6 | Inspect the links | "R08" → `/residents/R08/log`, accessible name "R08 · baseline stuck at 13 of 16"; "R03" → `/residents/R03/log`; "R05" → `/residents/R05/log`; "D02" → `/study#devices` |
| 7 | Inspect colours and glyphs | No "▲" and no red in the panel; R08 has no separate high_set_aside row |
| 8 | Click "R08" | `/residents/R08/log` opens |

### TC-072-03 Check-ins per day

| Step | Action | Expected Result |
|---|---|---|
| 1 | Read the legend under "Check-ins per day" | In order: "Used" (`--c-used` swatch), "Set aside" (`--c-aside`), "Held back (other voice)" (`--c-quar`), "Missed" (dashed outline); 12px swatches, 14px `--muted` labels |
| 2 | Count the bars | 30 bars, Oct 1–30, each totalling 10 residents; stacked bottom to top Used, Set aside, Held back, Missed |
| 3 | Read the x axis | "Oct 1", "Oct 12: D02 silent", "Oct 30" |
| 4 | Hover Oct 8 | Tooltip "Oct 8: 8 used, 0 set aside, 1 held back, 1 missed" |
| 5 | Inspect the chart's accessible name | "Check-ins per day, Oct 1–30, 2026: 267 used, 12 set aside, 2 held back, 19 missed." (period as rendered on the page) |
| 6 | Open "Show daily counts as a table" | Columns "Date", "Used", "Set aside", "Held back", "Missed", "Note"; Oct 1 10/0/0/0; Oct 12 8/0/0/2 with note "D02 silent"; Oct 22 8/1/1/0 |
| 7 | Check for "▲" in the chart | None |

### TC-072-04 Where check-ins are lost

| Step | Action | Expected Result |
|---|---|---|
| 1 | Read the panel rows | "Expected" 300 "10 residents × 30 days"; "Received" 281 "19 missed; 2 duplicate copies removed"; "Passed quality checks" 269 "12 set aside: quality flag 5, noise 5, too short 3 (1 had two reasons)"; "Same speaker, used" 267 "2 held back as possible other voice" |
| 2 | Inspect meter widths | 100%, 93.7%, 89.7%, 89.0% of the track (14px high) |
| 3 | Inspect layout | 170px label column, meter, 44px right-aligned bold value |

### TC-072-05 Usable check-ins by resident

| Step | Action | Expected Result |
|---|---|---|
| 1 | Read the subtitle | "Share of 30 days, lowest first" |
| 2 | Read the rows top to bottom | R08 43%, R03 73%, R02 80%, R05 93%, R01 100%, R04 100%, R06 100%, R07 100%, R09 100%, R10 100% |
| 3 | Inspect the R08 row's accessible name | "R08: 13 of 30 days usable (43%); 5 set aside; 0 held back; 12 missed." |
| 4 | Click "R05" | `/residents/R05/log` opens |
| 5 | Inspect a meter | Filled with `--c-used` in proportion to the percentage |

### TC-072-06 Alarm timing check

| Step | Action | Expected Result |
|---|---|---|
| 1 | Read the panel | Heading "Alarm timing check"; line "Test data only, where the true change date is known." |
| 2 | Read the table | Columns "Resident", "Planted change", "Change began", "Alarm rang", "Delay"; rows "R09 · Sudden step · Oct 21 · Oct 21 · 0 days", "R10 · Slow drift · Oct 17 · Oct 24 · 7 days", "Other 8 · None · None · No alarm · Correct" |
| 3 | Read the caption | "With real residents the true change date is unknown, so this panel becomes: alarms raised, alarms reviewed, and review outcomes." (12px, `--muted`) |
| 4 | Inspect the container | Scrolling container, keyboard-focusable, accessible name "Alarm timing table" |

### TC-072-07 Devices section

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `/study#devices` directly | Page scrolls to the section with `id="devices"`; focus is on its heading "Devices" |
| 2 | Read the rows in order | "● Online" — "**D01, D04 to D06, D08 to D10:** all uploaded Oct 30. Firmware fw-1.0.0."; "● Online" — "**D02** (shared by R02 and R03): last upload Oct 30, 2:55 PM CT. Silent all day Oct 12."; "● Online" — "**D07B** (R07): in use since Oct 13, replacing D07. Last upload Oct 30, 2:52 PM CT." |
| 3 | Inspect the tags | "● Online" in `--green`, 14px, weight 700 |
| 4 | Check for a row for D07 | None (retired device has no row) |
| 5 | Click "D02" in the data problems panel | Scrolls to the Devices section |

### TC-072-08 Show all devices

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open the disclosure "Show all devices (10)" | Table columns "Device", "Residents", "In use", "Last upload", "Firmware", "Days with no device activity (last 30 days)", "Silent days (shared device)" |
| 2 | Count rows | 10: D01, D02, D04, D05, D06, D07, D07B, D08, D09, D10 |
| 3 | Check D02 | Residents "R02, R03"; no activity "1 (Oct 12)"; silent days "1 (Oct 12)" |
| 4 | Check D07 | Residents "R07"; In use "Oct 1–12 · replaced by D07B"; last upload "Oct 12, 2:14 PM CT" |
| 5 | Check D07B and D08 | D07B "Since Oct 13"; D08 days with no device activity "12" |
| 6 | Check the remaining rows | Firmware "fw-1.0.0" everywhere; other activity and silent counts "0" |

### TC-072-09 Downloads

| Step | Action | Expected Result |
|---|---|---|
| 1 | Read the last panel | Heading "Downloads"; buttons "Scores (CSV)" and "Baselines (CSV)" |
| 2 | Click "Scores (CSV)" | `GET /api/v1/scores` with `Accept: text/csv` returns 200 `text/csv`; a CSV file is saved |
| 3 | Open the file | Header row and one row per scored session; rows for R09 include 2026-10-21 with alarm state "rings" |
| 4 | Click "Baselines (CSV)" | `GET /api/v1/analytics/baselines` with `Accept: text/csv` returns 200; file saved with baseline rows per resident and measurement |

### TC-072-10 Alarms raised note after reviews

| Step | Action | Expected Result |
|---|---|---|
| 1 | As clinician review R09 ("Checked on resident, no concern"); as researcher reload `/study` | "Alarms raised" "2" / "R09, R10; 1 not reviewed yet" |
| 2 | Review R10 too and reload | Note "R09, R10; both reviewed" |
| 3 | Re-seed afterwards | Note "R09, R10; neither reviewed yet" |

### TC-072-11 Production profile

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `npx vitest run tests/pages/study.test.tsx components/ReviewOutcomesTable components/AlarmTimingTable` in `frontend/` | Passes FE-195: with `meta.pipeline_profile` "production" the page renders "Alarms and review outcomes" with columns "" and "Count" and rows "Alarms raised", "Reviewed", "Checked on resident, no concern", "Explained by a known cause", "Referred to nurse or provider", "Looks like a data problem: send to study team"; no "Alarm timing check" |
| 2 | Check the period line in that test | No " · numbers match the pipeline answer key" |

### TC-072-12 Clinician denied

| Step | Action | Expected Result |
|---|---|---|
| 1 | Sign in as clinician; clear the Network panel; open `/study` | "You do not have access to this page." and "← Resident list" |
| 2 | Check the Network panel | No request to `/api/v1/analytics`, `/api/v1/data-alerts`, `/api/v1/devices`, `/api/v1/scores` or `/api/v1/analytics/baselines` |
| 3 | `curl` `GET /api/v1/analytics` with the clinician token | 403 `FORBIDDEN` |

### TC-072-13 Admin and unauthenticated

| Step | Action | Expected Result |
|---|---|---|
| 1 | Sign in as admin; open `/study` | Same content as for the researcher (TC-072-01) |
| 2 | In a private window open `/study` | Redirected to `/login?next=%2Fstudy` |

### TC-072-14 Empty states

| Step | Action | Expected Result |
|---|---|---|
| 1 | On the isolated `echowell_demo` database with only the master data (no pipeline run), sign in as researcher and open `/study` | Empty state "No pipeline run yet." |
| 2 | Run `npx vitest run tests/pages/study.test.tsx components/DataProblemsList components/DevicesSection` | Pass: no open data alert → "No data problems in the last 30 days."; no devices → "No devices are registered yet." |

Note: FEAT-072-FR-17 and TRD 02 UC-14 write "No pipeline run yet" without a final period; the code shows "No pipeline run yet." (frontend/lib/wording/study.ts:10).

### TC-072-15 Panel errors

| Step | Action | Expected Result |
|---|---|---|
| 1 | Block `*/api/v1/data-alerts*` and open `/study` | "Data problems to follow up" shows "Could not load data problems to follow up. Check your connection and try again." with "Try again"; tiles, charts and Devices render |
| 2 | Block `*/api/v1/devices*` only | Only the Devices section shows "Could not load devices. Check your connection and try again." |
| 3 | Block `*/api/v1/analytics` only | Tiles and chart panels show "Could not load study team counts. Check your connection and try again."; data problems and Devices render |
| 4 | Block `*/api/v1/scores*` and click "Scores (CSV)" | Error message with "Reference: <request_id>" when available; page stays usable |

### TC-072-16 Wording, privacy, layout

| Step | Action | Expected Result |
|---|---|---|
| 1 | Search the page for "alarm" | Only "Alarms raised", "Alarm timing check", "Alarm rang" (and the production rows) |
| 2 | Search for names, notes text, "depress", "severity", "mood", "patient" | None; residents only by study ID |
| 3 | Check for `<audio>` | None |
| 4 | At ≥ 1024px | "Where check-ins are lost" and "Usable check-ins by resident" side by side |
| 5 | At 375px | Columns stack; the daily chart (min width 560px) and the timing table scroll inside their focusable containers; the page does not scroll horizontally |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/analytics` (researcher) | 200; `period` 2026-10-01..2026-10-30, 30 days; `kpis.checkins_received` 281/300/94; `used_for_scoring` 267/300/89; `baselines_formed` 9 of 10, forming ["R08"], restarts R07 ×1; `alarms_raised` 2, ["R09","R10"], `not_reviewed_count` 2 |
| 2 | Same response | `funnel` expected 300, received 281, missed 19, duplicates_removed 2, passed_quality 269, set_aside 12 (quality 5, noise 5, too short 3, multi 1), quarantined 2, used 267; `by_resident` R08 43 … R10 100; `alarm_timing` non-null, `review_outcomes` null |
| 3 | `GET /api/v1/data-alerts?status=open` | Four items: R08 baseline_stalled, R03 high_set_aside, R05 possible_other_speaker, D02 device_silent, with the `title` and `detail` texts shown on the page |
| 4 | `GET /api/v1/devices?limit=500&offset=0` | 10 devices; D07 `uploaded_on_as_of_date` false, all others true |
| 5 | `GET /api/v1/scores` with `Accept: text/csv` (researcher) | 200 `text/csv`; same call with the clinician token: 403 (CSV for A, Rs only) |
| 6 | `GET /api/v1/analytics/baselines` with `Accept: text/csv` | 200 `text/csv` |
| 7 | `GET /api/v1/analytics` with the clinician token / without token | 403 / 401 |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT kind, coalesce(r.resident_code, d.device_code) FROM data_alerts da LEFT JOIN residents r ON r.id = da.resident_id LEFT JOIN devices d ON d.id = da.device_id WHERE da.status = 'open' ORDER BY kind;` | baseline_stalled R08; possible_other_speaker R05; high_set_aside R03; device_silent D02 (no high_set_aside row for R08) |
| 2 | `SELECT status, count(*) FROM processed_sessions WHERE local_date BETWEEN '2026-10-01' AND '2026-10-30' GROUP BY status;` | usable 267, set_aside 12, quarantined 2, duplicate 2 (received = 281 non-duplicates) |
| 3 | `SELECT status, count(*) FROM day_ledger WHERE local_date BETWEEN '2026-10-01' AND '2026-10-30' AND status <> 'checked_in' GROUP BY status;` | missing_resident + missing_device_gap = 19 |
| 4 | `SELECT count(*) FROM evaluation_ground_truth;` | Rows loaded (source of the alarm timing table; never read by the pipeline) |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Clinician opens `/study` | Access denied, no request (TC-072-12) |
| 2 | No pipeline run | "No pipeline run yet." (TC-072-14) |
| 3 | One endpoint fails | Only its panels show the error state (TC-072-15) |
| 4 | CSV download fails | Error with reference, page usable (TC-072-15) |
| 5 | No token | Redirect to login; API 401 (TC-072-13) |
| 6 | Production profile | Timing data never shown (TC-072-11) |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-072-AC-01 | Header lines and tiles 94% / 89% / "9 of 10" / 2 with their notes | TC-072-01 |
| FEAT-072-AC-02 | Data problems R08, R03, R05, D02 in order with texts, tags and links; no "▲" or red | TC-072-02 |
| FEAT-072-AC-03 | Funnel 300 → 281 → 269 → 267 with notes; by-resident order and percentages | TC-072-04, TC-072-05 |
| FEAT-072-AC-04 | Daily table Oct 1 10/0/0/0, Oct 12 8/0/0/2 "D02 silent", Oct 22 8/1/1/0; legend order; x labels | TC-072-03 |
| FEAT-072-AC-05 | Timing rows R09, R10, Other 8 and the "Test data only…" line | TC-072-06 |
| FEAT-072-AC-06 | `/study#devices` scroll and focus; three "● Online" rows; "Show all devices (10)" with D08 "12", D07 "Oct 1–12 · replaced by D07B" | TC-072-07, TC-072-08 |
| FEAT-072-AC-07 | Production fixture: "Alarms and review outcomes", no answer-key clause | TC-072-11 |
| FEAT-072-AC-08 | Clinician: access denied, no Study team request | TC-072-12 |

## Test Data Requirements

- DS-07 `test_v0_1` (R01–R10) with the §4.18.8 values; DS-10 evaluation ground truth for the alarm timing table.
- Isolated `echowell_demo` database with master data only (empty state).
- Production-profile fixture of the component and page tests (FE-195).
- Seeded researcher, clinician and admin with the `SEED_*` passwords; re-seed command after TC-072-10.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-072-FR-01 | FEAT-072 | TC-072-12, TC-072-13 |
| FEAT-072-FR-02 | FEAT-072 | TC-072-01, TC-072-11 |
| FEAT-072-FR-03 | FEAT-072 | TC-072-01, TC-072-10 |
| FEAT-072-FR-04, FR-05 | FEAT-072 | TC-072-02, TC-072-14 |
| FEAT-072-FR-06, FR-07, FR-08 | FEAT-072 | TC-072-03 |
| FEAT-072-FR-09 | FEAT-072 | TC-072-04 |
| FEAT-072-FR-10 | FEAT-072 | TC-072-05 |
| FEAT-072-FR-11 | FEAT-072 | TC-072-06 |
| FEAT-072-FR-12 | FEAT-072 | TC-072-11 |
| FEAT-072-FR-13 | FEAT-072 | TC-072-07 |
| FEAT-072-FR-14 | FEAT-072 | TC-072-07, TC-072-08 |
| FEAT-072-FR-15 | FEAT-072 | TC-072-09, TC-072-15 |
| FEAT-072-FR-16 | FEAT-072 | TC-072-16 |
| FEAT-072-FR-17 | FEAT-072 | TC-072-14, TC-072-15 |
| FEAT-072-FR-18 | FEAT-072 | TC-072-01 to TC-072-08 |
| UX-017, UX-350 | FEAT-072 | TC-072-01, TC-072-12 |
| UX-351..UX-355 | FEAT-072 | TC-072-01, TC-072-10 |
| UX-306..UX-309 | FEAT-072 | TC-072-02, TC-072-14 |
| UX-356..UX-361 | FEAT-072 | TC-072-03 |
| UX-362..UX-366 | FEAT-072 | TC-072-04 |
| UX-367..UX-370 | FEAT-072 | TC-072-05 |
| UX-371..UX-374, UX-376 | FEAT-072 | TC-072-06 |
| UX-375 | FEAT-072 | TC-072-11 |
| UX-377 | FEAT-072 | TC-072-09 |
| UX-050..UX-054 | FEAT-072 | TC-072-07 |
| UX-055..UX-057 | FEAT-072 | TC-072-08 |
| UX-058, UX-263 | FEAT-072 | TC-072-07, TC-072-08 |
| UX-331 | FEAT-072 | TC-072-02 |
| UX-380..UX-384 | FEAT-072 | TC-072-01, TC-072-03, TC-072-04, TC-072-05, TC-072-06 |
| UX-204, UX-202 | FEAT-072 | TC-072-14, TC-072-15 |
| UX-240, UX-242, UX-243 | FEAT-072 | TC-072-16 |
| FE-026 | FEAT-072 | TC-072-07 |
| FE-037 | FEAT-072 | TC-072-12 |
| FE-076 | FEAT-072 | API Validation step 4 |
| FE-102 | FEAT-072 | TC-072-07 |
| FE-194 | FEAT-072 | TC-072-01 to TC-072-08 |
| FE-195 | FEAT-072 | TC-072-11 |
| E2E-07 | FEAT-072 | TC-072-07, TC-072-08 |
| E2E-17 | FEAT-072 | TC-072-02 |
| E2E-20 | FEAT-072 | TC-072-01 to TC-072-06 |
| E2E-21 | FEAT-072 | TC-072-12 |
| TST-090, TST-094 | FEAT-072 | TC-072-11, TC-072-14 |
