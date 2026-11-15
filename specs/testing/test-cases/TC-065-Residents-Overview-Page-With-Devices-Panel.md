# Resident list page (filters, residents table, What's happening, status legend, note)

## Feature Description

`/residents` is the home page of the dashboard (wireframe v0.2, SRC-21; TRD 24 D-110): one panel with the `<h1>` "Residents in the study" and the filter buttons "All (<n>)", "Changed (<n>)", "Needs attention (<n>)", "Usual (<n>)" (plus "Learning (<n>)" only when someone is Learning) kept in `?show=`, the four-column residents table (Status · Resident · What's happening · Last check-in) rendering the API rows in API order (`sort=alarm`) with a status pill and a one-line reason, the status legend, and under the panel the note "A status is a prompt to check on someone, not a diagnosis. [Final clinical wording: confirm with PI]". The v0.1 summary tiles, sort select, device and 30-day-count columns and Devices panel are retired (devices moved to the Study team page and each chart's Device section) and are verified as absent (TRD 11 §4.3, §4.13.1, §4.13.2; TRD 04 FE-081..FE-084; TRD 19 E-08).

## Preconditions

- Local Docker Compose demo profile running, seeded with `test_v0_1` and the DS-07 pipeline run (as-of Oct 30, 2026, 3:00 PM CT; `PIPELINE_PROFILE=test_v0_1`, N = 16, h = 5); no alarm reviewed yet.
- Signed in as `clinician@example.com` (password from `SEED_CLINICIAN_PASSWORD`) unless the case says otherwise.
- Browser developer tools (Network panel, Accessibility tree, device toolbar for 375px width).
- For the Learning case: the isolated `echowell_demo` database with the R11 overlay roster (`tests/fixtures/seeds/demo_overlay/`, TRD 13 E2E-15) and one posted R11 record.
- `psql` read access for the database cases.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-065-01 | Header, filter buttons and default "All" with DS-07 | High | Positive |
| TC-065-02 | Ten rows in API order with pills, "What's happening" and last check-in (§4.13.1) | High | Positive |
| TC-065-03 | Filters show the §4.13.2 rows, counts unchanged, URL and announcement | High | Positive |
| TC-065-04 | Filter kept on reload, back navigation and the chart's back link | High | Positive |
| TC-065-05 | Status legend and prompt note | High | UI |
| TC-065-06 | Row click and study-ID link open the chart Summary | High | Positive |
| TC-065-07 | Table structure: headers, caption, row borders, scroll container | Medium | UI |
| TC-065-08 | Narrow screen (375px): table scrolls inside its container | High | UI |
| TC-065-09 | Duplicates never shown (R04) | High | Database |
| TC-065-10 | Learning resident: "Learning (1)" button and template | Medium | Positive |
| TC-065-11 | Reviewed alarm changes "What's happening" to "Reviewed." | Medium | Positive |
| TC-065-12 | Invalid `?show=` value reads as all; no matching rows message | Medium | Negative |
| TC-065-13 | Loading, empty and error states; stale notice on failed refresh | High | Negative |
| TC-065-14 | 5-minute refetch keeps rows visible with `aria-busy` | Low | Positive |
| TC-065-15 | Retired v0.1 elements absent; withdrawn residents and new admissions not listed | Medium | Negative |
| TC-065-16 | Unauthenticated access to the list and the API | High | Security |

### TC-065-01 Header and filter buttons

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `/residents` | `<h1>` "Residents in the study" (22px) on the left of the panel header row |
| 2 | Inspect the filter group | `role="group"` with accessible name "Show"; buttons in order "All (10)", "Changed (2)", "Needs attention (2)", "Usual (6)"; no "Learning" button |
| 3 | Inspect "All (10)" | `aria-pressed="true"`, `--chrome` background and border, `--chrome-ink` text; the others `aria-pressed="false"`, 1px solid `--rule`, radius 999px, 15px |
| 4 | Compare with `GET /api/v1/residents` `summary` | `changed` 2, `needs_attention` 2, `learning` 0, `usual` 6; total 10 |

### TC-065-02 Default rows

| Step | Action | Expected Result |
|---|---|---|
| 1 | Read the table rows top to bottom | Order R09, R10, R03, R08, R01, R02, R04, R05, R06, R07 |
| 2 | Check R09 | "▲ Changed" · "R09" · "Changed from their usual since Oct 21. Not reviewed yet." · "Oct 30, 2:28 PM CT" |
| 3 | Check R10 | "▲ Changed" · "R10" · "Changed from their usual since Oct 24. Not reviewed yet." · "Oct 30, 2:39 PM CT" |
| 4 | Check R03 | "! Needs attention" · "7 check-ins too noisy or too short to use." · "Oct 30, 2:19 PM CT" |
| 5 | Check R08 | "! Needs attention" · "Missing many check-ins. Baseline stuck at 13 of 16." · "Oct 30, 2:28 PM CT" |
| 6 | Check R01, R02, R04, R05, R06 | "● Usual" · "Within their usual range." · last check-ins "Oct 30, 2:07 PM CT", "Oct 30, 2:55 PM CT", "Oct 30, 2:17 PM CT", "Oct 30, 2:40 PM CT", "Oct 30, 2:38 PM CT" |
| 7 | Check R07 | "● Usual" · "Usual. Baseline restarted Oct 13 after a new device." · "Oct 30, 2:52 PM CT" |
| 8 | Compare the order with the API response `items` | Identical; the UI does not re-sort |

### TC-065-03 Filtering

| Step | Action | Expected Result |
|---|---|---|
| 1 | Clear the Network panel; click "Changed (2)" | Rows R09, R10; URL `?show=changed`; no new API request; page not reloaded |
| 2 | Check focus and the live region | Focus stays on "Changed (2)" (`aria-pressed="true"`); polite live region reads "Showing changed residents" |
| 3 | Check all button labels | Still "All (10)", "Changed (2)", "Needs attention (2)", "Usual (6)" |
| 4 | Click "Needs attention (2)" | Rows R03, R08; URL `?show=needs_attention`; announcement "Showing needs attention residents" |
| 5 | Click "Usual (6)" | Rows R01, R02, R04, R05, R06, R07; URL `?show=usual` |
| 6 | Click "All (10)" | Ten rows in the order of TC-065-02; URL `?show=all`; announcement "Showing all residents" |
| 7 | Add the counts 2 + 2 + 0 + 6 | Equals 10, the "All" count |

### TC-065-04 Filter persistence

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `/residents?show=usual` directly (reload) | "Usual (6)" pressed; six Usual rows |
| 2 | Click the "R01" link, then "← Resident list" on the chart | Returns to `/residents?show=usual` with the Usual rows |
| 3 | Click "Changed (2)", open R09, then press the browser Back button | `/residents?show=changed` with R09, R10 |

### TC-065-05 Legend and note

| Step | Action | Expected Result |
|---|---|---|
| 1 | Read the legend under the table | "▲ Changed" + "Their voice has moved away from their own usual. Check on them."; "! Needs attention" + "Not enough good check-ins to judge. Check the device or the routine."; "○ Learning" + "Still collecting the first 16 check-ins to learn their usual."; "● Usual" + "Within their own usual range." (14px, `--muted`, wrapping) |
| 2 | Read the note under the panel | "A status is a prompt to check on someone, not a diagnosis. [Final clinical wording: confirm with PI]" (14px, `--muted`) |
| 3 | Search the page for "depress", "severity", "mood", "patient", "abnormal" | No match |

### TC-065-06 Opening a chart

| Step | Action | Expected Result |
|---|---|---|
| 1 | Inspect the "R09" link | Weight 700, `href="/residents/R09"`, accessible name "Open chart for R09" |
| 2 | Click the "R09" link | `/residents/R09` opens (Summary); title "R09 · Summary – EchoWell" |
| 3 | Go back and click the R09 row's "What's happening" text | `/residents/R09` opens |
| 4 | Tab through the table | Each row has one tab stop (the study-ID link); the row itself is not focusable |

### TC-065-07 Table structure

| Step | Action | Expected Result |
|---|---|---|
| 1 | Inspect the header row | Cells "Status", "Resident", "What's happening", "Last check-in" with `scope="col"`, 14px, weight 600, `--muted`, background `--surface-2` |
| 2 | Inspect the caption | Visually hidden `<caption>` "Residents in the study, all"; after clicking "Changed" it reads "Residents in the study, changed" |
| 3 | Inspect R09's first cell | 5px solid `--red` left border |
| 4 | Inspect R03's first cell | 5px solid `--yellow-edge` left border |
| 5 | Inspect R01's first cell and a body cell | No coloured left border; padding 12px 18px; 1px solid `--rule` bottom border |
| 6 | Inspect the table container | `overflow-x: auto`, `tabindex="0"`, accessible name "Residents table"; table `min-width: 640px` |

### TC-065-08 Narrow screen

| Step | Action | Expected Result |
|---|---|---|
| 1 | Set the viewport to 375 × 812 and open `/residents` | The page has no horizontal scrollbar (`document.documentElement.scrollWidth` ≤ 375) |
| 2 | Tab to the "Residents table" container and press the Right arrow key | The table scrolls horizontally inside its container |
| 3 | Check the header row | Filter buttons wrap below the heading |

### TC-065-09 Duplicates never shown

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run Database Validation step 2 | R04 has 2 `duplicate` processed sessions and 30 `usable` |
| 2 | Check R04's row | "● Usual" · "Within their usual range." · "Oct 30, 2:17 PM CT"; no count, row or text mentions duplicates |
| 3 | Open `/residents/R04` and check the banner | "Usable check-ins, last 30 days" reads "30 of 30" |
| 4 | Check the summary counts | Still 10 residents (no extra row from duplicates) |

### TC-065-10 Learning resident

| Step | Action | Expected Result |
|---|---|---|
| 1 | On the isolated `echowell_demo` stack with R11 and one posted R11 record (E2E-15 set-up), open `/residents` | A button "Learning (1)" appears between "Needs attention (<n>)" and "Usual (<n>)" |
| 2 | Check R11's row | "○ Learning" · "Learning their usual: 1 of 16 check-ins so far." · last check-in = facility-local time of the posted record |
| 3 | Click "Learning (1)" | Only R11; URL `?show=learning` |

### TC-065-11 Reviewed alarm text

| Step | Action | Expected Result |
|---|---|---|
| 1 | As clinician, save a review for R09 on `/residents/R09/review` (outcome "Checked on resident, no concern") | "Review saved." announced |
| 2 | Open `/residents` | R09 row still "▲ Changed", text "Changed from their usual since Oct 21. Reviewed."; filters unchanged "Changed (2)" |
| 3 | Re-seed (`python -m backend.cli seed test_v0_1 --reset` plus the DS-07 pipeline run) | R09 back to "Not reviewed yet." |

### TC-065-12 Invalid filter and no matching rows

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `/residents?show=bogus` | "All (10)" pressed; ten rows |
| 2 | Open `/residents?show=learning` on DS-07 (no Learning resident) | Table shows one row "No residents with this status."; counts unchanged |

### TC-065-13 Loading, empty, error and stale states

| Step | Action | Expected Result |
|---|---|---|
| 1 | Throttle to "Slow 3G" and reload | Panel shows "Loading residents…" (`role="status"`); buttons read "All (—)", "Changed (—)", "Needs attention (—)", "Usual (—)" |
| 2 | Block `*/api/v1/residents*` and reload | Panel shows "Could not load residents. Check your connection and try again." and "Try again"; app bar and data bar still render |
| 3 | With a 500 response carrying a request ID | "Reference: <request_id>" under the message |
| 4 | Unblock and click "Try again" | Rows load |
| 5 | With rows loaded, go offline and refocus the window | Rows stay; notice "Could not refresh. Showing data as of Oct 30, 3:00 PM CT." at the top |
| 6 | Run `npx vitest run tests/pages/residents.test.tsx` in `frontend/` | Passes, including the empty state "No residents are enrolled yet." and the truncation line "Showing 10 of 612 residents." under the table when `total` exceeds the returned rows |
| 7 | On DS-07 check under the table | No "Showing … of … residents." line (10 of 10 returned) |

### TC-065-14 Periodic refetch

| Step | Action | Expected Result |
|---|---|---|
| 1 | Keep `/residents` visible for 5 minutes with the Network panel open | A new `GET /api/v1/residents` is sent after about 5 minutes |
| 2 | During that request inspect the table | Previous rows remain visible; table has `aria-busy="true"` until the response arrives |

### TC-065-15 Retired elements and excluded residents

| Step | Action | Expected Result |
|---|---|---|
| 1 | Inspect the page | No summary tiles, no "Sort by" select, no device column, no 30-day count columns, no Devices panel |
| 2 | Open `/admissions` | Its empty state reads "No new admissions. The pipeline test data v0.1 has no admission group."; no admission resident is on `/residents` |
| 3 | Run Database Validation step 3 | No withdrawn resident exists in DS-07; every listed code has `status` active and `cohort` longitudinal |

### TC-065-16 Unauthenticated access

| Step | Action | Expected Result |
|---|---|---|
| 1 | In a new private window open `/residents` | Redirected to `/login?next=%2Fresidents`; no row visible |
| 2 | `curl -i <api>/api/v1/residents` without a token | 401 problem+json |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | Observe the page request `GET /api/v1/residents?limit=500&offset=0` (default `sort=alarm`) | 200; `total` 10; `items` in order R09, R10, R03, R08, R01, R02, R04, R05, R06, R07 |
| 2 | Check `summary` | `{changed: 2, needs_attention: 2, learning: 0, usual: 6}` |
| 3 | Check row fields | `needs_attention` true only for R03 (`attention_reasons` ["high_set_aside"]) and R08 (["baseline_stalled"]); `alarm_reviewed` false for R09, R10 and null for the others; R08 `baseline_progress` 13 of 16; R07 `restart_cause` "device" |
| 4 | Check `last_checkin_at` of R09 | "2026-10-30T19:28:…Z" (2:28 PM CT) |
| 5 | `GET /api/v1/residents?sort=bogus` | 422 `INVALID_QUERY_PARAMETER` |
| 6 | Without token | 401 |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT r.resident_code, a.status, a.local_date FROM alerts a JOIN residents r ON r.id = a.resident_id ORDER BY a.local_date;` | R09 open 2026-10-21; R10 open 2026-10-24 (matches the Changed rows and dates) |
| 2 | `SELECT ps.status, count(*) FROM processed_sessions ps JOIN residents r ON r.id = ps.resident_id WHERE r.resident_code = 'R04' GROUP BY ps.status;` | `usable` 30, `duplicate` 2 |
| 3 | `SELECT resident_code, status, cohort FROM residents ORDER BY resident_code;` | R01–R10, all `active`, `longitudinal` |
| 4 | `SELECT r.resident_code, d.kind FROM data_alerts d JOIN residents r ON r.id = d.resident_id WHERE d.status = 'open' AND d.kind IN ('baseline_stalled','high_set_aside');` | R03 high_set_aside; R08 baseline_stalled (the two Needs attention rows) |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Residents request fails | "Could not load residents. Check your connection and try again." + "Try again" (TC-065-13) |
| 2 | Refresh fails with cached data | "Could not refresh. Showing data as of Oct 30, 3:00 PM CT." (TC-065-13) |
| 3 | `?show=bogus` | Treated as all (TC-065-12) |
| 4 | Filter with no rows | "No residents with this status." (TC-065-12) |
| 5 | No token | Redirect to `/login?next=%2Fresidents`; API 401 (TC-065-16) |
| 6 | Duplicate records | Never counted or listed (TC-065-09) |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-065-AC-01 | "Residents in the study", "All (10)", "Changed (2)", "Needs attention (2)", "Usual (6)", no Learning, "All" pressed | TC-065-01 |
| FEAT-065-AC-02 | Rows R09…R07 with the §4.13.1 pills, texts and last check-ins | TC-065-02 |
| FEAT-065-AC-03 | Filters show the §4.13.2 rows, `?show=` set, counts unchanged, "Showing changed residents"; kept after reload and back link | TC-065-03, TC-065-04 |
| FEAT-065-AC-04 | Legend with the four meanings ("Still collecting the first 16 check-ins to learn their usual.") and the prompt note with the PI marker | TC-065-05 |
| FEAT-065-AC-05 | R09 row or "R09" link ("Open chart for R09") opens `/residents/R09` | TC-065-06 |
| FEAT-065-AC-06 | Nothing reflects R04's two duplicate arrivals | TC-065-09 |
| FEAT-065-AC-07 | At 375px the table scrolls inside "Residents table", the page does not | TC-065-08 |

## Test Data Requirements

- DS-07: `test_v0_1` R01–R10, as-of Oct 30, 2026, 3:00 PM CT; R04 with two duplicate arrivals; open alerts R09 (Oct 21) and R10 (Oct 24); open data alerts R03 high_set_aside and R08 baseline_stalled.
- Learning fixture R11 (overlay roster, isolated `echowell_demo`) for TC-065-10.
- Seeded clinician with `SEED_CLINICIAN_PASSWORD`; re-seed command for TC-065-11.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-065-FR-01 | FEAT-065 | TC-065-01, TC-065-10 |
| FEAT-065-FR-02 | FEAT-065 | TC-065-03, TC-065-12 |
| FEAT-065-FR-03 | FEAT-065 | TC-065-03, TC-065-04, TC-065-12 |
| FEAT-065-FR-04 | FEAT-065 | TC-065-02 |
| FEAT-065-FR-05, FR-06 | FEAT-065 | TC-065-07, TC-065-08 |
| FEAT-065-FR-07, FR-09 | FEAT-065 | TC-065-02, TC-065-10, TC-065-11 |
| FEAT-065-FR-08 | FEAT-065 | TC-065-06 |
| FEAT-065-FR-10 | FEAT-065 | TC-065-02 |
| FEAT-065-FR-11, FR-12 | FEAT-065 | TC-065-05 |
| FEAT-065-FR-13 | FEAT-065 | TC-065-13; API Validation step 1 (`limit=500`) |
| FEAT-065-FR-14 | FEAT-065 | TC-065-09, TC-065-15 |
| FEAT-065-FR-15 | FEAT-065 | TC-065-14 |
| FEAT-065-FR-16 | FEAT-065 | TC-065-02, TC-065-03 |
| FEAT-065-FR-17 | FEAT-065 | TC-065-13 |
| UX-034, UX-036, UX-043 | FEAT-065 | TC-065-02, TC-065-07 |
| UX-037, UX-040 | FEAT-065 | TC-065-06 |
| UX-038 | FEAT-065 | TC-065-02 |
| UX-041 | FEAT-065 | TC-065-13 |
| UX-042 | FEAT-065 | TC-065-07, TC-065-08 |
| UX-044, UX-045, UX-046 | FEAT-065 | TC-065-09, TC-065-15 |
| UX-401, UX-402, UX-403, UX-404 | FEAT-065 | TC-065-01, TC-065-03, TC-065-04, TC-065-12 |
| UX-405 | FEAT-065 | TC-065-02, TC-065-10, TC-065-11 |
| UX-406, UX-407 | FEAT-065 | TC-065-05 |
| UX-408 | FEAT-065 | TC-065-02 |
| UX-260, UX-261 | FEAT-065 | TC-065-02, TC-065-03 |
| UX-200, UX-204 | FEAT-065 | TC-065-13 |
| FE-025 | FEAT-065 | TC-065-04 |
| FE-081, FE-083 | FEAT-065 | TC-065-14 |
| FE-082 | FEAT-065 | TC-065-03, TC-065-12 |
| FE-084 | FEAT-065 | TC-065-02 |
| FE-182, FE-185 | FEAT-065 | TC-065-02, TC-065-03 |
| E2E-03 | FEAT-065 | TC-065-01, TC-065-05 |
| E2E-04 | FEAT-065 | TC-065-02 |
| E2E-05 | FEAT-065 | TC-065-03 |
| E2E-06 | FEAT-065 | TC-065-04 |
| TST-090, TST-094 | FEAT-065 | TC-065-05, TC-065-06, TC-065-09, TC-065-13 |
