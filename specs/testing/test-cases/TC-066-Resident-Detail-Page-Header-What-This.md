# Resident chart frame and Summary (back link, banner, section navigation, Right now, Leaning most, More detail)

## Feature Description

The frame of the resident chart `/residents/[residentCode]` (wireframe v0.2, SRC-21) and its first section, Summary: the back link "← Resident list" (keeping the list's filter), the banner with the resident code as `<h1>`, the facts "Device", "Last check-in", "Usable check-ins, last 30 days" and "Baseline" and the large status pill, the section navigation with six links (Summary, Review and notes with an unreviewed-alarm badge, Voice trends, Baseline, Check-in log, Device; each its own URL), the "Right now" panel (lead sentence per situation, alarm facts, "Leaning most", action buttons, the "not a diagnosis" note with the PI-confirmation marker), the "More detail" tiles, and the "Resident <code> was not found." state (TRD 11 §4.5.1, §4.5.2, §4.5.2.1, UX-312, §4.13.3; TRD 04 FE-025, FE-087, FE-142, FE-206, FE-210; TRD 19 E-09, E-13, E-17).

## Preconditions

- Local Docker Compose demo profile running, seeded with `test_v0_1` and the DS-07 pipeline run (as-of Oct 30, 2026, 3:00 PM CT; N = 16, h = 5); no alarm reviewed yet.
- Signed in as `clinician@example.com` (`SEED_CLINICIAN_PASSWORD`) unless the case says otherwise.
- Browser developer tools (Network panel with request blocking, Accessibility tree).
- `psql` read access for the database cases.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-066-01 | R09 banner and lead (Changed, change score above the line) | High | Positive |
| TC-066-02 | R09 alarm facts, Leaning most, buttons and More detail tiles | High | Positive |
| TC-066-03 | R10 facts, Leaning most and change score tile | High | Positive |
| TC-066-04 | Summary note "not a diagnosis" with the PI marker; no clinical wording | High | UI |
| TC-066-05 | R08 Needs attention (baseline stalled): banner, lead, buttons, tiles | High | Positive |
| TC-066-06 | R07 device replacement: banner device text and restart sentence | High | Positive |
| TC-066-07 | R03 shared device and Needs attention (high set-aside) | High | Positive |
| TC-066-08 | Usual resident with scored sessions (R01) | Medium | Positive |
| TC-066-09 | Section navigation: order, current link, own URLs, back button | High | UI |
| TC-066-10 | Review-and-notes badge on R09/R10 only; disappears after review | High | Positive |
| TC-066-11 | Back link keeps the list's `?show=` filter | Medium | Positive |
| TC-066-12 | Unknown resident (R11 on DS-07) shows the not-found state | High | Negative |
| TC-066-13 | Panel error isolation when alerts or devices fail | High | Negative |
| TC-066-14 | Loading state shows "—" in banner facts | Medium | UI |
| TC-066-15 | N and h come from the API (production-profile fixture shows "of 30") | Medium | Positive |
| TC-066-16 | Learning resident Summary (R11 overlay) | Medium | Positive |
| TC-066-17 | Unauthenticated chart access | High | Security |

### TC-066-01 R09 banner and lead

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `/residents/R09` | First element in the content: link "← Resident list" (weight 600, no underline, min-height 44px); title "R09 · Summary – EchoWell" |
| 2 | Inspect the banner | `<section aria-label="Resident">`; `<h1>` "R09" (26px, weight 700); large pill "▲ Changed" (18px, padding 6px 16px) at its right end |
| 3 | Read the facts `<dl>` | "Device" "D09"; "Last check-in" "Oct 30, 2:28 PM CT"; "Usable check-ins, last 30 days" "30 of 30"; "Baseline" "Complete" (terms 13px `--muted`, values weight 600) |
| 4 | Read the "Right now" panel | Heading "Right now"; 6px `--red` left border; lead "R09’s voice has moved away from their own usual pattern, steadily and long enough to set off the alarm on Oct 21. It is still changed." (20px, weight 600) |

### TC-066-02 R09 facts, Leaning most, buttons, tiles

| Step | Action | Expected Result |
|---|---|---|
| 1 | Read the three facts in "Right now" | "Oct 21" / "Alarm started"; "9 days" / "Open"; "Not reviewed" / "Review status" (value 18px weight 700, label 13px `--muted`) |
| 2 | Read the next line | "Leaning most: more pauses, quieter, less voiced sound" |
| 3 | Check the buttons | Primary "Review this alert" linking to `/residents/R09/review`; secondary "See what changed" linking to `/residents/R09/trends` |
| 4 | Read the "More detail" heading and tiles | `<h2>` "More detail"; tiles "Voice trends" "Change score 26.8"; "Baseline" "16 of 16 check-ins"; "Check-ins, last 30 days" "30 used, 0 missed"; "Device" "D09 online"; each with "Open" |
| 5 | Click each tile | Opens `/residents/R09/trends`, `/baseline`, `/log`, `/device` respectively |

### TC-066-03 R10 Summary

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `/residents/R10` | Banner "D10" · "Oct 30, 2:39 PM CT" · "30 of 30" · "Complete" · "▲ Changed" |
| 2 | Read lead and facts | Lead "R10’s voice has moved away from their own usual pattern, steadily and long enough to set off the alarm on Oct 24. It is still changed."; facts "Oct 24" Alarm started, "6 days" Open, "Not reviewed" |
| 3 | Read Leaning most and tile | "Leaning most: more pauses, slower while talking, fewer syllables per second"; tile "Change score 13.4" |

### TC-066-04 Summary note and wording rules

| Step | Action | Expected Result |
|---|---|---|
| 1 | On `/residents/R09` read the last paragraph of "Right now" | "This compares R09 only with R09. It is a prompt to check in, not a diagnosis. [Final clinical wording: confirm with PI]" (14px, `--muted`) |
| 2 | Repeat on R08, R07, R01 | Same pattern with the resident's code, ending with "[Final clinical wording: confirm with PI]" |
| 3 | Search the Summary for "diagnos" | Only inside "not a diagnosis"; no "depress", "severity", "severe", "disorder", "illness", "abnormal", "risk score", "mood", "patient" |
| 4 | Run `npx vitest run components/SummaryPanel` in `frontend/` | Passes (TST-096 marker, TST-097 phrase) |

### TC-066-05 R08 Needs attention

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `/residents/R08` | Banner "D08" · "Oct 30, 2:28 PM CT" · "13 of 30" · "13 of 16" · "! Needs attention" |
| 2 | Read the "Right now" panel | 6px `--yellow-edge` left border; lead "Missing many check-ins. Baseline stuck at 13 of 16. EchoWell can’t judge their voice well until more good check-ins come in." |
| 3 | Check the buttons | Secondary "See missed and set-aside check-ins" (to `/residents/R08/log`) and "Check the device" (to `/residents/R08/device`); no "Review this alert", no alarm facts, no "Leaning most" |
| 4 | Read the tiles | "Not scored yet"; "13 of 16 check-ins"; "13 used, 12 missed"; "D08 online" |
| 5 | Check for error banners | None |

### TC-066-06 R07 device replacement

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `/residents/R07` | Banner Device "D07B (replaced D07)" · "Oct 30, 2:52 PM CT" · "30 of 30" · "Complete" · "● Usual" |
| 2 | Read the lead | "R07’s voice is within their own usual range. Nothing to do. The baseline restarted on Oct 13 because the device changed (D07B, was D07); R07 is now compared only with the new baseline." |
| 3 | Open "Voice trends" and "Baseline" | Voice trends line "Showing the current device period since Oct 13. Earlier periods are not scored against this baseline."; Baseline text starts "Restarted Oct 13 when the device was replaced (D07 to D07B), …" (UX-065) |
| 4 | Read the green border | "Right now" has a 6px `--green` left border |

### TC-066-07 R03 shared device

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `/residents/R03` | Banner Device "D02 (shared with R02)" · "Oct 30, 2:19 PM CT" · "22 of 30" · "Complete" · "! Needs attention" |
| 2 | Read the lead | "7 check-ins too noisy or too short to use. EchoWell can’t judge their voice well until more good check-ins come in." |
| 3 | Read the tiles | "No change"; "16 of 16 check-ins"; "22 used, 1 missed"; "D02 online" |
| 4 | Open `/residents/R02` | Device "D02 (shared with R03)" |

### TC-066-08 Usual resident

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `/residents/R01` | Banner "● Usual", "30 of 30", "Complete" |
| 2 | Read the lead | "R01’s voice is within their own usual range. Nothing to do." |
| 3 | Check buttons | No action buttons in "Right now" |
| 4 | Read the tiles | "No change"; "16 of 16 check-ins"; "30 used, 0 missed"; "D01 online" |

### TC-066-09 Section navigation

| Step | Action | Expected Result |
|---|---|---|
| 1 | On `/residents/R09` inspect `<nav aria-label="Resident chart">` | Links in order "Summary", "Review and notes", "Voice trends", "Baseline", "Check-in log", "Device"; weight 600, padding 10px 12px, min-height 44px |
| 2 | Check the current link | "Summary" has `aria-current="page"`, `--chrome` background, `--chrome-ink` text |
| 3 | Click each link | URLs `/residents/R09/review`, `/trends`, `/baseline`, `/log`, `/device`; titles "R09 · Review and notes – EchoWell", "R09 · Voice trends – EchoWell", "R09 · Baseline – EchoWell", "R09 · Check-in log – EchoWell", "R09 · Device – EchoWell" |
| 4 | Press the browser Back button | Returns to the previous section |
| 5 | Open `/residents/R09/log` directly (bookmark) | Check-in log section opens with "Check-in log" current |
| 6 | At ≥ 1024px check layout; then at 700px | 200px navigation column beside content; below 760px the navigation becomes one horizontally scrolling row above the content |

### TC-066-10 Review-and-notes badge

| Step | Action | Expected Result |
|---|---|---|
| 1 | On `/residents/R09` inspect "Review and notes" | Ends with a red badge "1"; accessible name "Review and notes, alarm not reviewed" |
| 2 | Open `/residents/R10` | Same badge "1" |
| 3 | Open `/residents/R01` and `/residents/R08` | No badge; accessible name "Review and notes" |
| 4 | Save a review for R09 (outcome "Checked on resident, no concern") and return to Summary | Badge gone; "Review status" reads "Reviewed"; pill still "▲ Changed"; tile still "Change score 26.8" |
| 5 | Re-seed afterwards (`python -m backend.cli seed test_v0_1 --reset` plus the DS-07 pipeline run) | Badge "1" back |

### TC-066-11 Back link and filter

| Step | Action | Expected Result |
|---|---|---|
| 1 | On `/residents` click "Needs attention (2)", then "R08" | Chart of R08 |
| 2 | Click "← Resident list" | `/residents?show=needs_attention` with R03, R08 |
| 3 | Open `/residents/R09` in a new tab directly and click "← Resident list" | `/residents?show=all` (default) |

### TC-066-12 Unknown resident

| Step | Action | Expected Result |
|---|---|---|
| 1 | On DS-07 open `/residents/R11` | `GET /api/v1/residents/R11` returns 404; page shows "← Resident list" and "Resident R11 was not found." |
| 2 | Check the page | No banner, no section navigation, no section panels |
| 3 | Open `/residents/R11/log` | Same not-found state |

### TC-066-13 Panel error isolation

| Step | Action | Expected Result |
|---|---|---|
| 1 | Block `*/api/v1/alerts*` and open `/residents/R09` | Banner and lead render from the resident detail; the alarm facts / "Leaning most" area shows "Could not load alarm details. Check your connection and try again." with "Try again" |
| 2 | Unblock alerts, block `*/api/v1/devices*` and reload | Only the parts needing device data show an error state; banner, lead and other tiles render |
| 3 | Block `*/api/v1/residents/R09` (detail) and reload | "Could not load resident. Check your connection and try again." with "Try again" and, when available, "Reference: <request_id>" |

### TC-066-14 Loading state

| Step | Action | Expected Result |
|---|---|---|
| 1 | Throttle to "Slow 3G" and open `/residents/R10` | Banner facts show "—" until data arrive; loading text "Loading resident…" with `role="status"` |

### TC-066-15 API-driven N and h

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `npx vitest run components/ChartBanner components/SummaryPanel components/MoreDetailTiles` | Passes, including the production-profile fixture showing "of 30" in Baseline facts and Learning texts |
| 2 | Run `grep -rnE "\\b(16|30)\\b" frontend/components/ChartBanner/ChartBanner.tsx frontend/components/SummaryPanel/SummaryPanel.tsx` | No hard-coded baseline length or window used as a value |

### TC-066-16 Learning resident

| Step | Action | Expected Result |
|---|---|---|
| 1 | On the isolated `echowell_demo` stack with R11 and one posted record, open `/residents/R11` | Banner "D11", "○ Learning", Baseline "1 of 16" |
| 2 | Read the lead and note | "EchoWell is still learning R11’s usual pattern: 1 of 16 usable check-ins so far. Nothing is scored and no alarm can ring until the baseline is complete."; note "Once the baseline is complete, R11 will be compared only with R11. A change is a prompt to check in, not a diagnosis. [Final clinical wording: confirm with PI]" |
| 3 | Check the panel border and tiles | 6px `--grey` left border; "Voice trends" tile "Not scored yet"; "Baseline" "1 of 16 check-ins" |

### TC-066-17 Unauthenticated access

| Step | Action | Expected Result |
|---|---|---|
| 1 | In a new private window open `/residents/R09` | Redirected to `/login?next=%2Fresidents%2FR09` |
| 2 | `curl -i <api>/api/v1/residents/R09` without token | 401 |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/residents/R09` | 200 `ResidentDetail`: `status` "alarm_on", `needs_attention` false, `alarm_reviewed` false, `baseline.state` "frozen", `device.device_code` "D09", `last_30_days.used` 30 |
| 2 | `GET /api/v1/alerts?resident_code=R09` | 200; one open alert, `local_date` 2026-10-21, `open_days` 9, `leaning_most` with 3 measurement keys in the order more pauses, quieter, less voiced sound |
| 3 | `GET /api/v1/residents/R07` | `device.device_code` "D07B", `previous_device_code` "D07", `current_epoch.epoch_number` 2, `restart_cause` "device" |
| 4 | `GET /api/v1/residents/R03` | `device.shared` true, `shared_with` ["R02"], `attention_reasons` ["high_set_aside"] |
| 5 | `GET /api/v1/devices` | `uploaded_on_as_of_date` true for D01–D06, D07B, D08–D10 and false for D07 |
| 6 | `GET /api/v1/residents/R11` on DS-07 | 404 `RESIDENT_NOT_FOUND` |
| 7 | The three layout requests (resident, alerts, devices) in the Network panel | Sent in parallel (overlapping timings) |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT a.status, a.local_date FROM alerts a JOIN residents r ON r.id = a.resident_id WHERE r.resident_code = 'R09';` | `open`, 2026-10-21 (Alarm started "Oct 21") |
| 2 | `SELECT count(*) FROM alert_reviews ar JOIN alerts a ON a.id = ar.alert_id JOIN residents r ON r.id = a.resident_id WHERE r.resident_code = 'R09';` | 0 on a fresh seed ("Not reviewed"); 1 after TC-066-10 step 4 |
| 3 | `SELECT e.epoch_number, e.started_on FROM epochs e JOIN residents r ON r.id = e.resident_id WHERE r.resident_code = 'R07' ORDER BY e.epoch_number;` | Epoch 2 started 2026-10-13 (restart sentence date) |
| 4 | After TC-066-10 step 4: `SELECT status FROM alerts a JOIN residents r ON r.id = a.resident_id WHERE r.resident_code = 'R09';` | Still `open` (review does not close the alarm, OQ-05) |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Unknown resident R11 on DS-07 | "Resident R11 was not found.", no banner or sections (TC-066-12) |
| 2 | Invalid code `/residents/r09!` | Not-found state without API call (see TC-064-14) |
| 3 | Alerts or devices request fails | Error only in dependent panels; lead still renders (TC-066-13) |
| 4 | Resident detail request fails | "Could not load resident. Check your connection and try again." (TC-066-13) |
| 5 | No token | Redirect to login; API 401 (TC-066-17) |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-066-AC-01 | R09: back link, `<h1>` "R09", "D09", "Oct 30, 2:28 PM CT", "30 of 30", "Complete", "▲ Changed", lead text | TC-066-01 |
| FEAT-066-AC-02 | R09 facts "Oct 21"/"9 days"/"Not reviewed", Leaning most, buttons, tiles; R10 "6 days", its Leaning most, "Change score 13.4" | TC-066-02, TC-066-03 |
| FEAT-066-AC-03 | Note contains "It is a prompt to check in, not a diagnosis." and ends with "[Final clinical wording: confirm with PI]" | TC-066-04 |
| FEAT-066-AC-04 | R08: "! Needs attention", "13 of 30", "13 of 16", lead, two buttons, tiles, no error banner | TC-066-05 |
| FEAT-066-AC-05 | R07 "D07B (replaced D07)", "● Usual", restart lead; R03 "D02 (shared with R02)", "22 of 30", "! Needs attention" | TC-066-06, TC-066-07 |
| FEAT-066-AC-06 | Six links in order; badge "1" with "Review and notes, alarm not reviewed" on R09/R10, none on R01; own URLs | TC-066-09, TC-066-10 |
| FEAT-066-AC-07 | `/residents/R11` (unknown) shows "Resident R11 was not found." with back link, nothing else | TC-066-12 |
| FEAT-066-AC-08 | Production profile shows "of 30" without frontend change | TC-066-15 |

## Test Data Requirements

- DS-07 `test_v0_1` (R01–R10), as-of Oct 30, 2026, 3:00 PM CT; R09/R10 open alarms; R07 device replacement D07 → D07B on Oct 13; D02 shared by R02 and R03.
- R11 is unknown on DS-07 (not-found case) and exists only on the isolated `echowell_demo` overlay (Learning case).
- Production-profile fixture of the component tests (N = 30).
- Seeded clinician with `SEED_CLINICIAN_PASSWORD`; re-seed command for TC-066-10.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-066-FR-01 | FEAT-066 | TC-066-01, TC-066-11 |
| FEAT-066-FR-02, FR-03 | FEAT-066 | TC-066-01, TC-066-05, TC-066-06, TC-066-07 |
| FEAT-066-FR-04 | FEAT-066 | TC-066-09 |
| FEAT-066-FR-05 | FEAT-066 | TC-066-10 |
| FEAT-066-FR-06 | FEAT-066 | TC-066-01, TC-066-05, TC-066-06, TC-066-08, TC-066-16 |
| FEAT-066-FR-07, FR-08 | FEAT-066 | TC-066-02, TC-066-03 |
| FEAT-066-FR-09 | FEAT-066 | TC-066-05 |
| FEAT-066-FR-10 | FEAT-066 | TC-066-04, TC-066-16 |
| FEAT-066-FR-11 | FEAT-066 | TC-066-02, TC-066-05, TC-066-07, TC-066-08 |
| FEAT-066-FR-12 | FEAT-066 | TC-066-13 |
| FEAT-066-FR-13 | FEAT-066 | TC-066-12 |
| FEAT-066-FR-14 | FEAT-066 | TC-066-01 to TC-066-08 |
| UX-060 | FEAT-066 | TC-066-01, TC-066-11 |
| UX-061, UX-062, UX-063 | FEAT-066 | TC-066-01, TC-066-05, TC-066-06, TC-066-07 |
| UX-065 | FEAT-066 | TC-066-06 |
| UX-070..UX-073, UX-075 | FEAT-066 | TC-066-01, TC-066-04, TC-066-05, TC-066-16 |
| UX-076, UX-312 | FEAT-066 | TC-066-02, TC-066-03 |
| UX-077 | FEAT-066 | TC-066-05 |
| UX-078 | FEAT-066 | TC-066-02, TC-066-05, TC-066-07, TC-066-08 |
| UX-007 | FEAT-066 | TC-066-15 |
| UX-410 | FEAT-066 | TC-066-09 |
| UX-411 | FEAT-066 | TC-066-10 |
| UX-412 | FEAT-066 | TC-066-12 |
| UX-262 | FEAT-066 | TC-066-01 to TC-066-08 |
| FE-025 | FEAT-066 | TC-066-11 |
| FE-087 | FEAT-066 | TC-066-13 |
| FE-142 | FEAT-066 | TC-066-12 |
| FE-206 | FEAT-066 | TC-066-09 |
| FE-210 | FEAT-066 | TC-066-10 |
| FE-186, FE-193 | FEAT-066 | TC-066-01, TC-066-02, TC-066-10 |
| E2E-08 | FEAT-066 | TC-066-01, TC-066-02 |
| E2E-10 | FEAT-066 | TC-066-06 |
| E2E-11 | FEAT-066 | TC-066-05 |
| E2E-12 | FEAT-066 | TC-066-07 |
| TST-090, TST-096, TST-097 | FEAT-066 | TC-066-04, TC-066-15 |
