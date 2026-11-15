# Check-in log and Baseline sections of the resident chart

## Feature Description

Two sections of the resident chart (wireframe v0.2, SRC-21). "Check-in log" (`/residents/[residentCode]/log`): the panel "Check-ins, last 30 days" with the four counts "Used", "Set aside (noise, poor quality or too short)", "Held back (possible other voice)" and "Missed", and the panel "Events" with one row per event, newest first (alarm on, comparing with baseline started, baseline complete, baseline restarted by cause, check-in set aside with the pipeline's reasons, check-in held back, check-in missed, shared device silent, check-ins started), paging with "Show earlier entries", never a duplicate or an ordinary usable check-in, the caption "Duplicate records are removed quietly and not shown." and the empty state "Nothing to report yet.". "Baseline" (`/residents/[residentCode]/baseline`): the panel "Baseline: <R>’s usual" with the frozen, forming or restarted baseline text, the `<progress>` meter and the explanation (TRD 11 §4.3.5, §4.5.6, §4.5.7, §4.13.3; TRD 04 FE-101; TRD 19 E-09, E-10).

## Preconditions

- Local Docker Compose demo profile running, seeded with `test_v0_1` and the DS-07 pipeline run (as-of Oct 30, 2026, 3:00 PM CT; N = 16, h = 5).
- Signed in as `clinician@example.com` (`SEED_CLINICIAN_PASSWORD`).
- For the paging case: the isolated `echowell_demo` database with the R11 overlay (enrolled 2026-10-01, `PIPELINE_AS_OF` empty so as-of = current time) and one posted R11 record (TRD 13 E2E-15 set-up).
- Browser developer tools (Network panel with request blocking, Accessibility tree); `psql` read access.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-068-01 | R09 counts and event lines (alarm, comparing started, baseline complete, check-ins started) | High | Positive |
| TC-068-02 | R07 restart lines and "Check-ins started on D07." | High | Positive |
| TC-068-03 | R08 counts 13 / 5 / 0 / 12 with missed and set-aside lines | High | Positive |
| TC-068-04 | R03 set-aside reasons and shared-device silent day; R05 held-back lines | High | Positive |
| TC-068-05 | No usable or duplicate lines (R04); caption under events | High | Negative |
| TC-068-06 | Event layout, same-date ordering and no colour reliance | Medium | UI |
| TC-068-07 | "Show earlier entries" paging (R11) and absence on DS-07 | Medium | Positive |
| TC-068-08 | Empty events state "Nothing to report yet." | Medium | Negative |
| TC-068-09 | R09 Baseline section: frozen text, meter, explanation | High | Positive |
| TC-068-10 | R08 forming Baseline text and meter | High | Positive |
| TC-068-11 | R07 restarted Baseline text | High | Positive |
| TC-068-12 | Baseline dates stable after freeze across reloads | Medium | Positive |
| TC-068-13 | Events panel error does not blank the counts; paging failure keeps shown events | High | Negative |
| TC-068-14 | Counts and missed days equal the API and the day ledger | High | Database |

### TC-068-01 R09 log

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `/residents/R09/log` | Title "R09 · Check-in log – EchoWell"; panel "Check-ins, last 30 days" |
| 2 | Read the count tiles | "30" Used; "0" Set aside (noise, poor quality or too short); "0" Held back (possible other voice); "0" Missed (number 24px weight 700 above its label) |
| 3 | Read the first three event rows of the "Events" panel | "Oct 21" "Alarm on. Change score crossed 5."; "Oct 17" "Comparing with baseline started."; "Oct 16" "Baseline complete (16 of 16)." |
| 4 | Read the last event row | "Oct 1" "Check-ins started." |
| 5 | Count all rows | 4 rows (no line for the usable check-ins) |

### TC-068-02 R07 log

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `/residents/R07/log` | Rows include, newest first: "Oct 29" "Comparing with baseline started."; "Oct 28" "Baseline complete (16 of 16)."; "Oct 13" "New device D07B. Baseline restarted." |
| 2 | Read the last row | "Oct 1" "Check-ins started on D07." |
| 3 | Read the counts | 30 / 0 / 0 / 0 |

### TC-068-03 R08 log

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `/residents/R08/log` | Counts: Used "13", Set aside "5", Held back "0", Missed "12" |
| 2 | Read the first three rows | "Oct 29" "Check-in set aside: speech too short."; "Oct 27" "Check-in missed."; "Oct 25" "Check-in set aside: quality flag poor." |
| 3 | Count lines by text | Exactly 12 "Check-in missed." lines and 5 "Check-in set aside: …" lines |
| 4 | Check for alarm or baseline-complete lines | None (baseline still forming) |
| 5 | Read the last row | "Oct 1" "Check-ins started." |

### TC-068-04 R03 and R05 lines

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `/residents/R03/log` | Contains "Oct 26" "Check-in set aside: speech too short.", "Oct 24" "Comparing with baseline started.", "Oct 23" "Baseline complete (16 of 16).", "Oct 18" "Check-in set aside: quality flag poor; noise above limit.", "Oct 12" "Shared device D02 silent all day. Check-in missed." |
| 2 | Read R03 counts | 22 / 7 / 0 / 1 |
| 3 | Open `/residents/R02/log` | Contains "Oct 23" "Check-in missed." and "Oct 12" "Shared device D02 silent all day. Check-in missed."; counts 24 / 0 / 0 / 6 |
| 4 | Open `/residents/R05/log` | Contains "Oct 22" "Check-in held back: possible other voice." and "Oct 8" "Check-in held back: possible other voice."; counts 28 / 0 / 2 / 0 |
| 5 | Inspect the held-back lines | Only "possible other voice"; no F0 z value, feature counts or other screen statistics |

### TC-068-05 No usable or duplicate lines

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `/residents/R04/log` | Counts 30 / 0 / 0 / 0; rows only "Oct 17" "Comparing with baseline started.", "Oct 16" "Baseline complete (16 of 16).", "Oct 1" "Check-ins started." |
| 2 | Search the page for "duplicate" | Only in the caption "Duplicate records are removed quietly and not shown." (14px, `--muted`) below the events |
| 3 | Check R04's two duplicate arrivals | No row refers to them; Used stays 30 |

### TC-068-06 Layout, ordering, colour

| Step | Action | Expected Result |
|---|---|---|
| 1 | Inspect an event row on R03 | Grid with an 80px `--muted` date column and a text column; 1px solid `--rule` bottom border; padding 10px 0 |
| 2 | Compare the row order with `GET /api/v1/residents/R03/checkins` | Identical (UI does not re-sort); newest date first |
| 3 | Inspect row colours | All rows use the same text colours; each line's text names its type (no coloured icons) |
| 4 | Inspect the count tiles at ≥ 1024px and at 375px | Tiles in a grid (min width 150px); stack in one column below 640px |

### TC-068-07 Show earlier entries

| Step | Action | Expected Result |
|---|---|---|
| 1 | On DS-07 open `/residents/R09/log` | No "Show earlier entries" button (all events lie in the Oct 1–30 window) |
| 2 | On the isolated `echowell_demo` stack (R11, as-of = current time) open `/residents/R11/log` | Events of the last 30 days ending on the current date; newest line "<Mon D> Check-ins started." (dated by the posted record); earlier lines "Check-in missed."; button "Show earlier entries" at the end |
| 3 | Clear the Network panel and click "Show earlier entries" | `GET /api/v1/residents/R11/checkins?from=<date>&to=<date>` for the previous 30 days; older "Check-in missed." lines are appended; shown lines stay |
| 4 | Repeat until no earlier events exist | Button disappears once the window reaches the enrolment date (Oct 1) |

### TC-068-08 Empty events

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `npx vitest run components/CheckinLog` in `frontend/` | Passes, including the fixture with no events: "Nothing to report yet." followed by "Duplicate records are removed quietly and not shown." |

### TC-068-09 R09 Baseline

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `/residents/R09/baseline` | `<h2>` "Baseline: R09’s usual"; title "R09 · Baseline – EchoWell" |
| 2 | Read the first paragraph | "First 16 usable check-ins, Oct 1–16, then frozen. Compared with it since Oct 17." |
| 3 | Inspect the meter | Native `<progress>` max 16, value 16, height 14px, full width, accessible name "16 of 16 usable check-ins"; caption "16 of 16 usable check-ins" (14px, `--muted`) |
| 4 | Read the last paragraph | "The baseline is built from the first 16 usable check-ins, then frozen so slow changes still show up. It restarts if the resident gets a new device or the device or extraction software changes." |
| 5 | Open `/residents/R05/baseline`, `/residents/R03/baseline`, `/residents/R02/baseline` | "… Oct 1–17, then frozen. Compared with it since Oct 18."; "… Oct 1–23, then frozen. Compared with it since Oct 24."; "… Oct 1–21, then frozen. Compared with it since Oct 22." |

### TC-068-10 R08 forming Baseline

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `/residents/R08/baseline` | Paragraph "Still forming: 13 of 16 usable check-ins so far. 12 missed and 5 set-aside check-ins in the last 30 days have slowed it down." |
| 2 | Inspect the meter | `<progress>` max 16, value 13, accessible name "13 of 16 usable check-ins"; caption "13 of 16 usable check-ins" |

Note: FEAT-068-FR-13 words the clause " <m> missed and <s> set-aside check-ins have slowed it down." without "in the last 30 days"; TRD 11 §4.5.7.1 (D-149), FEAT-068-AC-07 and the code (frontend/lib/wording/chart.ts:257) include it. The case follows the TRD.

### TC-068-11 R07 restarted Baseline

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `/residents/R07/baseline` | Paragraph "Restarted Oct 13 when the device was replaced (D07 to D07B), so readings from the old device are not mixed in. First 16 usable check-ins, Oct 13–28, then frozen. Compared with it since Oct 29." |
| 2 | Inspect the meter | 16 of 16 |

### TC-068-12 Baseline stability

| Step | Action | Expected Result |
|---|---|---|
| 1 | Note the R09 Baseline paragraph, reload the page 3 times | Text unchanged: "First 16 usable check-ins, Oct 1–16, then frozen. Compared with it since Oct 17." |
| 2 | As admin, trigger `POST /api/v1/pipeline/run` with the same `as_of` 2026-10-30T15:00:00-05:00 and profile `test_v0_1`; reload | Same text and meter |
| 3 | Look for controls to edit, reset or recompute the baseline | None |

### TC-068-13 Error isolation

| Step | Action | Expected Result |
|---|---|---|
| 1 | Block `*/api/v1/residents/R09/checkins*` and open `/residents/R09/log` | "Events" panel shows "Could not load check-in events. Check your connection and try again." with "Try again"; the counts panel still shows 30 / 0 / 0 / 0 |
| 2 | Unblock and click "Try again" | Events load |
| 3 | On the R11 stack, load the log, block `*/checkins*`, click "Show earlier entries" | Error "Could not load earlier entries. Check your connection and try again." with "Try again"; already shown events remain |
| 4 | Block `*/api/v1/residents/R09` and open `/residents/R09/baseline` | "Could not load resident. Check your connection and try again." (no partial baseline text) |

### TC-068-14 Counts vs. API and ledger

| Step | Action | Expected Result |
|---|---|---|
| 1 | Compare R08 tiles with `GET /api/v1/residents/R08` `last_30_days` | `used` 13, `set_aside` 5, `quarantined` 0, `missed` 12 |
| 2 | Run Database Validation steps 1–2 for R08 | Ledger missed days 12; processed usable 13, set aside 5 |
| 3 | Compare each "Check-in missed." date on R08 with the ledger dates | Identical sets; no missed day shown as a check-in or filled with a value |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/residents/R09/checkins` | 200; events newest first: `alarm_on` 2026-10-21, `watching_started` 2026-10-17, `baseline_complete` 2026-10-16, `checkins_started` 2026-10-01 |
| 2 | `GET /api/v1/residents/R07/checkins` | `baseline_restarted` 2026-10-13 with `restart_cause` "device", `previous_device_code` "D07", `device_code` "D07B"; `checkins_started` 2026-10-01 with `device_code` "D07" |
| 3 | `GET /api/v1/residents/R03/checkins` | `set_aside` 2026-10-18 with `detail` "quality flag poor; noise above limit"; `device_silent` 2026-10-12 |
| 4 | `GET /api/v1/residents/R09/checkins?from=2026-09-01&to=2026-09-30` | 200 with no events |
| 5 | `GET /api/v1/residents/R09/checkins?from=bad` | 422 |
| 6 | `GET /api/v1/residents/R99/checkins` | 404 |
| 7 | `GET /api/v1/residents/R08` | `last_30_days` `{used: 13, set_aside: 5, quarantined: 0, missed: 12}`; `baseline.state` "forming", `n_usable` 13, `n_required` 16 |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT dl.status, count(*) FROM day_ledger dl JOIN residents r ON r.id = dl.resident_id WHERE r.resident_code = 'R08' AND dl.local_date BETWEEN '2026-10-01' AND '2026-10-30' GROUP BY dl.status;` | `missing_resident` + `missing_device_gap` = 12 |
| 2 | `SELECT ps.status, count(*) FROM processed_sessions ps JOIN residents r ON r.id = ps.resident_id WHERE r.resident_code = 'R08' GROUP BY ps.status;` | `usable` 13, `set_aside` 5 |
| 3 | `SELECT dl.local_date, dl.status FROM day_ledger dl JOIN residents r ON r.id = dl.resident_id WHERE r.resident_code = 'R03' AND dl.status = 'missing_device_gap';` | 2026-10-12 (the D02 silent day) |
| 4 | `SELECT ps.local_date, ps.reason_text FROM processed_sessions ps JOIN residents r ON r.id = ps.resident_id WHERE r.resident_code = 'R03' AND ps.local_date = '2026-10-18';` | `reason_text` "quality flag poor; noise above limit" |
| 5 | `SELECT count(*) FROM processed_sessions ps JOIN residents r ON r.id = ps.resident_id WHERE r.resident_code = 'R04' AND ps.status = 'duplicate';` | 2 (exist in the database, never shown) |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Check-ins request fails | Events panel error with "Try again"; counts stay (TC-068-13) |
| 2 | "Show earlier entries" fails | "Could not load earlier entries. …"; shown events kept (TC-068-13) |
| 3 | Resident with no events | "Nothing to report yet." + caption (TC-068-08) |
| 4 | Duplicate and usable records | Never shown as lines (TC-068-05) |
| 5 | Invalid query to the API | 422 / 404 (API Validation 5–6) |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-068-AC-01 | R09 counts 30/0/0/0; first lines alarm on, comparing started, baseline complete; last "Oct 1 Check-ins started." | TC-068-01 |
| FEAT-068-AC-02 | R07 lines Oct 29, Oct 28, Oct 13 restart, "Oct 1 Check-ins started on D07." | TC-068-02 |
| FEAT-068-AC-03 | R08 counts 13/5/0/12, 12 missed and 5 set-aside lines, first "Oct 29 Check-in set aside: speech too short." | TC-068-03, TC-068-14 |
| FEAT-068-AC-04 | R03 set-aside reasons and D02 silent line; R05 held-back line | TC-068-04 |
| FEAT-068-AC-05 | No usable or duplicate lines (R04); caption under events | TC-068-05 |
| FEAT-068-AC-06 | R09 Baseline heading, frozen text, meter 16 of 16, caption, explanation | TC-068-09 |
| FEAT-068-AC-07 | R08 forming text with "in the last 30 days have slowed it down." and `<progress>` 13/16; R07 restart text | TC-068-10, TC-068-11 |
| FEAT-068-AC-08 | Fixture with no events shows "Nothing to report yet." + caption | TC-068-08 |

## Test Data Requirements

- DS-07 `test_v0_1` (R01–R10) with the §4.13.3 counts: R08 13/5/0/12, R03 22/7/0/1, R05 28/0/2/0, R02 24/0/0/6, others 30/0/0/0; R04 duplicates; D02 silent Oct 12; R07 device change D07 → D07B Oct 13.
- R11 overlay on `echowell_demo` (paging case).
- Seeded clinician (`SEED_CLINICIAN_PASSWORD`); admin (`SEED_ADMIN_PASSWORD`) for the pipeline re-run in TC-068-12.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-068-FR-01 | FEAT-068 | TC-068-01, TC-068-03, TC-068-14 |
| FEAT-068-FR-02, FR-03 | FEAT-068 | TC-068-06 |
| FEAT-068-FR-04 | FEAT-068 | TC-068-01, TC-068-02, TC-068-03, TC-068-04 |
| FEAT-068-FR-05 | FEAT-068 | TC-068-04 |
| FEAT-068-FR-06 | FEAT-068 | TC-068-04 |
| FEAT-068-FR-07 | FEAT-068 | TC-068-05 |
| FEAT-068-FR-08 | FEAT-068 | TC-068-07 |
| FEAT-068-FR-09 | FEAT-068 | TC-068-06 |
| FEAT-068-FR-10 | FEAT-068 | TC-068-05, TC-068-08 |
| FEAT-068-FR-11 | FEAT-068 | TC-068-14 |
| FEAT-068-FR-12 | FEAT-068 | TC-068-01 |
| FEAT-068-FR-13 | FEAT-068 | TC-068-09, TC-068-10, TC-068-11 |
| FEAT-068-FR-14, FR-15 | FEAT-068 | TC-068-09, TC-068-10 |
| FEAT-068-FR-16 | FEAT-068 | TC-068-12 |
| FEAT-068-FR-17 | FEAT-068 | TC-068-01 to TC-068-11 |
| UX-047, UX-048, UX-150 | FEAT-068 | TC-068-14 |
| UX-140, UX-141 | FEAT-068 | TC-068-01, TC-068-06 |
| UX-142, UX-143 | FEAT-068 | TC-068-01 to TC-068-04 |
| UX-144, UX-148 | FEAT-068 | TC-068-05 |
| UX-145 | FEAT-068 | TC-068-04 |
| UX-146 | FEAT-068 | TC-068-07 |
| UX-147 | FEAT-068 | TC-068-06 |
| UX-149 | FEAT-068 | TC-068-08 |
| UX-066 | FEAT-068 | TC-068-12 |
| UX-420..UX-423 | FEAT-068 | TC-068-09, TC-068-10, TC-068-11 |
| UX-202 | FEAT-068 | TC-068-13 |
| FE-101 | FEAT-068 | TC-068-06 |
| FE-186 | FEAT-068 | TC-068-01, TC-068-02, TC-068-03, TC-068-04 |
| E2E-08 | FEAT-068 | TC-068-01, TC-068-09 |
| E2E-10 | FEAT-068 | TC-068-02, TC-068-11 |
| E2E-11 | FEAT-068 | TC-068-03, TC-068-10 |
| E2E-12 | FEAT-068 | TC-068-04 |
| TST-090 | FEAT-068 | TC-068-08 |
