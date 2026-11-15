# Voice trends: change score chart and the 7 voice measurements

## Feature Description

The "Voice trends" section of the resident chart (`/residents/[residentCode]/trends`, SRC-21): the "Change score" panel (the CUSUM tally, called "change score" in the UI, D-113) with its intro line, `ChangeScoreChart` (one bar per scored session of the displayed epoch; `--c-aside` while the alarm is off, `--red` from the first crossing on; leading grey baseline slot; dashed red "Alarm line: <h>"; "▲" marker and "<Mon D> · alarm" tick; zero-value stubs; no animation), the data table behind "Show change score as a table", the forming and device-period texts and the "Device period" selector; and the panel "The 7 voice measurements behind the score" with seven cards (plain-language label, technical name, signed sparkline), the eighth card "12 other measurements (pitch, jitter, MFCCs and others)" / "Stored, not scored", and the placeholder caption (TRD 11 §4.5.3, §4.5.4, §4.13.3; TRD 04 FE-093..FE-099; TRD 19 E-11, E-12).

## Preconditions

- Local Docker Compose demo profile running, seeded with `test_v0_1` and the DS-07 pipeline run (as-of Oct 30, 2026, 3:00 PM CT; N = 16, h = 5.0).
- Signed in as `clinician@example.com` (`SEED_CLINICIAN_PASSWORD`).
- Browser developer tools (element inspector, Accessibility tree, Network panel); a screen reader (NVDA, VoiceOver or Orca) for the table case; axe DevTools or `npx playwright test tests/e2e/a11y.spec.ts` for the accessibility case.
- `psql` read access.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-067-01 | R09 Change score panel heading and intro line | High | UI |
| TC-067-02 | R09 chart: 14 bars, colours by alarm state, baseline slot, alarm line, marker, tick | High | Positive |
| TC-067-03 | R09 data table values and alarm column | High | Positive |
| TC-067-04 | R09 chart accessible name, tooltips, y axis | High | UI |
| TC-067-05 | R10 colouring: alarm rings on Oct 24 | High | Positive |
| TC-067-06 | R07 device period line, "Baseline Oct 13–28", two stubs | High | Positive |
| TC-067-07 | R07 "Device period" selector loads epoch 1 with no bars | Medium | Positive |
| TC-067-08 | R08 forming text and "Not scored yet" on all 7 cards | High | Positive |
| TC-067-09 | Seven measurement cards: order, labels, sparklines, accessible names | High | UI |
| TC-067-10 | Eighth card and placeholder caption; stored measurements not shown | High | UI |
| TC-067-11 | No per-measurement alarm, threshold, "abnormal" or red on cards | Medium | Negative |
| TC-067-12 | Accessibility: axe, table with caption, keyboard scroll container, no animation | High | Accessibility |
| TC-067-13 | Panel errors are independent (scores vs. features) | High | Negative |
| TC-067-14 | Single-epoch resident has no "Device period" selector; read-only section | Medium | Negative |

### TC-067-01 Change score panel intro

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `/residents/R09/trends` | Title "R09 · Voice trends – EchoWell"; "Voice trends" link current in the section navigation |
| 2 | Read the first panel | `<h2>` "Change score"; line "Goes up when check-ins keep leaning away from R09’s usual. The alarm turns on at 5. Missed, set-aside and held-back check-ins leave it unchanged." (14px, `--muted`) |

### TC-067-02 R09 chart

| Step | Action | Expected Result |
|---|---|---|
| 1 | Count the bars | 14 bars, Oct 17 to Oct 30 in time order |
| 2 | Inspect the fills of Oct 17–20 | `--c-aside` fill with a 1px `--muted` outline |
| 3 | Inspect the fills of Oct 21–30 | `--red` fill |
| 4 | Inspect the leading slot | Grey `--grey-bg` area of full plot height before the first bar, labelled "Baseline Oct 1–16" |
| 5 | Inspect the horizontal line | Dashed (2px, dash 6/4) `--red` line at y = 5, label "Alarm line: 5" (12px, `--red`) at its left end above the line |
| 6 | Inspect the Oct 21 bar | "▲" above it; x tick "Oct 21 · alarm" |
| 7 | Read the x axis | Labels include "Oct 17", "Oct 21 · alarm", "Oct 30" (12px, `--muted`); labels at least 48px apart |

### TC-067-03 R09 data table

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open the disclosure "Show change score as a table" | Table with columns "Date", "Change score", "Alarm" and a caption naming R09 ("Change score for R09, by scored check-in") |
| 2 | Read the "Change score" column top to bottom | 3.2, 2.6, 1.8, 1.6, 5.4, 8.0, 8.3, 10.7, 12.4, 15.3, 16.7, 18.8, 23.1, 26.8 (14 rows, one decimal) |
| 3 | Read the "Alarm" column | "—" for Oct 17–20; "▲ Alarm rings (first crossing)" for Oct 21; "▲ Alarm on" for Oct 22–30 |

### TC-067-04 Accessible name, tooltips, y axis

| Step | Action | Expected Result |
|---|---|---|
| 1 | Inspect the chart element in the Accessibility tree | `role="img"` with name "Change score for R09 from Oct 17 to Oct 30. Baseline Oct 1–16. Alarm line 5. Crossed the alarm line on Oct 21; now 26.8." |
| 2 | Hover the Oct 21 bar and the Oct 30 bar | Tooltips "Oct 21: 5.4" and "Oct 30: 26.8" |
| 3 | Read the y axis | Starts at 0; ticks every 10 (0, 10, 20, …); maximum ≥ 1.05 × 26.8 |

### TC-067-05 R10 colouring

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `/residents/R10/trends` | 14 bars Oct 17–30 |
| 2 | Inspect Oct 17–23 | `--c-aside` (values 0.2, 0.6, 1.0, 1.4, 2.4, 3.8, 4.4 in the table, alarm "—") |
| 3 | Inspect Oct 24 | `--red`, "▲", tick "Oct 24 · alarm", value 6.0, table "▲ Alarm rings (first crossing)" |
| 4 | Inspect Oct 25–30 | `--red`; values 6.5, 7.0, 9.1, 10.8, 12.6, 13.4; "▲ Alarm on" |
| 5 | Read the accessible name | "Change score for R10 from Oct 17 to Oct 30. Baseline Oct 1–16. Alarm line 5. Crossed the alarm line on Oct 24; now 13.4." |

### TC-067-06 R07 current device period

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `/residents/R07/trends` | Line above the chart (14px, `--muted`): "Showing the current device period since Oct 13. Earlier periods are not scored against this baseline." |
| 2 | Inspect the chart | Baseline slot "Baseline Oct 13–28"; two bars (Oct 29, Oct 30) with value 0.0 drawn as 2px stubs in `--rule` |
| 3 | Open the table | Two rows "0.0" with alarm "—" |
| 4 | Read the accessible name | Contains "Baseline Oct 13–28. Alarm line 5. Below the alarm line throughout; now 0.0." |

### TC-067-07 Device period selector

| Step | Action | Expected Result |
|---|---|---|
| 1 | On `/residents/R07/trends` find the labelled `<select>` "Device period" | Options "Period 1" and "Period 2 (current)"; "Period 2 (current)" selected |
| 2 | Clear the Network panel and choose epoch 1 | `GET /api/v1/scores?resident_code=R07&epoch=1` is sent |
| 3 | Inspect the chart area | No bars (epoch 1 never formed a baseline) |

Note: for an epoch without baseline and scores the code shows "No check-ins were scored in this device period." (frontend/lib/wording/trends.ts:23); TRD 11 does not define this text, FEAT-067-AC-07 only requires that no bars render.

### TC-067-08 R08 forming

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `/residents/R08/trends` | Change score panel shows "No change score yet. Scoring starts after the baseline is complete (13 of 16 usable check-ins so far)." and no chart, no bars |
| 2 | Read the measurement panel | All 7 cards show "Not scored yet" (12px, `--muted`) with a 1px dashed `--rule` border; no sparkline |

### TC-067-09 Seven measurement cards

| Step | Action | Expected Result |
|---|---|---|
| 1 | On `/residents/R09/trends` read the second panel | `<h2>` "The 7 voice measurements behind the score"; intro "Each is compared with R09’s own baseline. The score rises when the voice is:" |
| 2 | Read the cards in order | "Quieter (loudness)", "Slower to say the phrase (phrase duration)", "Fewer syllables per second (speech rate)", "Slower while talking (articulation rate)", "More pauses (number of pauses)", "More time in pauses (pause fraction)", "Less voiced sound (voiced fraction)"; technical name 14px `--muted` |
| 3 | Inspect a card | Padding 10px 12px, 1px solid `--rule` border, label left, 110 × 28px sparkline right with a dashed zero line, no axes, grid or tooltip |
| 4 | Read the accessible name of the "Quieter" sparkline | "Quieter (loudness): latest <signed value> compared with own baseline over 14 scored check-ins" (signed value with "+" or "−") |
| 5 | At ≥ 1024px count the columns | Cards in two columns; below 640px one column |

### TC-067-10 Eighth card and caption

| Step | Action | Expected Result |
|---|---|---|
| 1 | Read the card after the seven | Background `--surface-2`; left "12 other measurements (pitch, jitter, MFCCs and others)"; right "Stored, not scored" (14px, `--muted`) |
| 2 | Compare with `GET /api/v1/residents/R09/features` | `stored_feature_keys` has 12 entries; none of them is listed, plotted or summarised on the page |
| 3 | Read the caption under the cards | "Measurement names are placeholders until Team 1 confirms the openSMILE output names. Morning check-ins are adjusted before comparing." (12px, `--muted`) |

### TC-067-11 No per-measurement alarm

| Step | Action | Expected Result |
|---|---|---|
| 1 | Inspect every card on R09 and R10 | No threshold line, no "▲", no red colour, no "abnormal" text, no per-measurement alarm |
| 2 | Search the section for z-score numbers outside the table and the sparkline names | None shown as visible text |

### TC-067-12 Accessibility

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run axe on `/residents/R09/trends` | No serious or critical violation |
| 2 | With a screen reader, open the disclosure and navigate by table | Table announced with role `table` and caption "Change score for R09, by scored check-in"; header cells read "Date", "Change score", "Alarm" |
| 3 | Tab to the chart container | Keyboard-focusable (`tabindex="0"`) with accessible name "Change score chart"; at 375px the chart (min width 520px) scrolls inside the container, the page does not |
| 4 | Reload and watch the chart and sparklines | Render without animation |

### TC-067-13 Independent panel errors

| Step | Action | Expected Result |
|---|---|---|
| 1 | Block `*/api/v1/scores*` and open `/residents/R09/trends` | Change score panel shows "Could not load the change score. Check your connection and try again." with "Try again"; the 7 cards still render |
| 2 | Unblock scores, block `*/api/v1/residents/R09/features*`, reload | Measurement panel shows "Could not load the voice measurements. Check your connection and try again."; the chart still renders |
| 3 | Unblock and click "Try again" | Panel loads |

### TC-067-14 Single epoch and read-only

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `/residents/R09/trends` | No "Device period" selector (one epoch) |
| 2 | Look for edit, reset or recompute controls | None |
| 3 | Try `/residents/R99/trends` | "Resident R99 was not found." with back link |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/scores?resident_code=R09` | 200; 14 `items` with `local_date` 2026-10-17..2026-10-30, `cusum_tally` matching TC-067-03 (rounded), `alarm_state` off ×4, rings ×1 (2026-10-21), on ×9; `baseline_periods` first 2026-10-01, frozen after 2026-10-16 |
| 2 | `GET /api/v1/scores?resident_code=R07` | Current epoch 2 items for 2026-10-29 and 2026-10-30, `cusum_tally` 0.0 |
| 3 | `GET /api/v1/scores?resident_code=R07&epoch=1` | 200 with no items |
| 4 | `GET /api/v1/residents/R09/features` | 200; scored deviations for the 7 measurements; `stored_feature_keys` length 12 |
| 5 | `GET /api/v1/scores?resident_code=R99` | 404 |
| 6 | `GET /api/v1/scores?resident_code=R09&epoch=0` | 422 |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT s.local_date, round(s.cusum_tally::numeric, 1), s.alarm_state FROM scores s JOIN residents r ON r.id = s.resident_id WHERE r.resident_code = 'R09' ORDER BY s.local_date;` | 14 rows matching the chart values and colours |
| 2 | `SELECT b.n_sessions, b.first_session_id, b.frozen_after_session_id FROM baselines b JOIN epochs e ON e.id = b.epoch_id JOIN residents r ON r.id = b.resident_id WHERE r.resident_code = 'R07' AND e.epoch_number = 2 AND b.feature_key = 'loudness_dbfs';` | `n_sessions` 16; `first_session_id` starts with "R07-20261013"; `frozen_after_session_id` starts with "R07-20261028" (slot "Baseline Oct 13–28") |
| 3 | `SELECT count(*) FROM scores s JOIN residents r ON r.id = s.resident_id WHERE r.resident_code = 'R08';` | 0 (forming; no bars) |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Scores request fails | Error state only in the Change score panel (TC-067-13) |
| 2 | Features request fails | Error state only in the measurement panel (TC-067-13) |
| 3 | Forming baseline | Forming text, no bars, "Not scored yet" cards (TC-067-08) |
| 4 | Earlier epoch without baseline | No bars (TC-067-07) |
| 5 | Unknown resident | "Resident R99 was not found." (TC-067-14) |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-067-AC-01 | R09: 14 bars, Oct 17–20 `--c-aside`, Oct 21–30 `--red`, "Alarm line: 5", "Baseline Oct 1–16", "▲" and "Oct 21 · alarm" | TC-067-02 |
| FEAT-067-AC-02 | R09 table: the 14 values and Oct 21 "▲ Alarm rings (first crossing)" | TC-067-03 |
| FEAT-067-AC-03 | R09 accessible name text exactly as specified | TC-067-04 |
| FEAT-067-AC-04 | R07 device-period line, "Baseline Oct 13–28", 2 stubs | TC-067-06 |
| FEAT-067-AC-05 | R08 forming text, no bars, "Not scored yet" on all 7 cards | TC-067-08 |
| FEAT-067-AC-06 | R09: 7 cards in order, eighth card, placeholder caption | TC-067-09, TC-067-10 |
| FEAT-067-AC-07 | R07 epoch 1 requests `…&epoch=1` and renders no bars | TC-067-07 |
| FEAT-067-AC-08 | axe no serious/critical; table role `table` with caption naming R09 | TC-067-12 |

## Test Data Requirements

- DS-07 `test_v0_1`: R09 (alarm Oct 21, tally 26.8), R10 (alarm Oct 24, tally 13.4), R07 (epoch 2 from Oct 13, baseline Oct 13–28, two 0.0 scores), R08 (forming, 13 of 16).
- TRD 11 §4.13.3 Voice trends values (binding, from SRC-03).
- Seeded clinician with `SEED_CLINICIAN_PASSWORD`.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-067-FR-01 | FEAT-067 | TC-067-01 |
| FEAT-067-FR-02, FR-03 | FEAT-067 | TC-067-02, TC-067-05 |
| FEAT-067-FR-04, FR-05 | FEAT-067 | TC-067-02, TC-067-06 |
| FEAT-067-FR-06 | FEAT-067 | TC-067-02, TC-067-04 |
| FEAT-067-FR-07 | FEAT-067 | TC-067-06 |
| FEAT-067-FR-08 | FEAT-067 | TC-067-04 |
| FEAT-067-FR-09 | FEAT-067 | TC-067-12 |
| FEAT-067-FR-10 | FEAT-067 | TC-067-04, TC-067-05 |
| FEAT-067-FR-11 | FEAT-067 | TC-067-03, TC-067-12 |
| FEAT-067-FR-12 | FEAT-067 | TC-067-08 |
| FEAT-067-FR-13 | FEAT-067 | TC-067-06 |
| FEAT-067-FR-14 | FEAT-067 | TC-067-07, TC-067-14 |
| FEAT-067-FR-15, FR-16, FR-17 | FEAT-067 | TC-067-09 |
| FEAT-067-FR-18 | FEAT-067 | TC-067-08, TC-067-11 |
| FEAT-067-FR-19, FR-20 | FEAT-067 | TC-067-10 |
| FEAT-067-FR-21 | FEAT-067 | TC-067-02, TC-067-05, TC-067-06, TC-067-08 |
| UX-080 | FEAT-067 | TC-067-01 |
| UX-081..UX-087 | FEAT-067 | TC-067-02, TC-067-04, TC-067-05, TC-067-06 |
| UX-089 | FEAT-067 | TC-067-08 |
| UX-090, UX-091 | FEAT-067 | TC-067-03, TC-067-04 |
| UX-092 | FEAT-067 | TC-067-06 |
| UX-100..UX-104 | FEAT-067 | TC-067-08, TC-067-09 |
| UX-105 | FEAT-067 | TC-067-11 |
| UX-106..UX-108 | FEAT-067 | TC-067-10 |
| UX-230, UX-243 | FEAT-067 | TC-067-12 |
| FE-093..FE-099 | FEAT-067 | TC-067-02, TC-067-04, TC-067-06, TC-067-09, TC-067-12 |
| FE-154 | FEAT-067 | TC-067-01, TC-067-03 |
| FE-183 | FEAT-067 | TC-067-02 |
| FE-184 | FEAT-067 | TC-067-03 |
| FE-186 | FEAT-067 | TC-067-02, TC-067-06, TC-067-08 |
| TST-093 | FEAT-067 | TC-067-02, TC-067-04 |
| TST-110, TST-112 | FEAT-067 | TC-067-12 |
| E2E-08 | FEAT-067 | TC-067-02, TC-067-09, TC-067-10 |
| E2E-10 | FEAT-067 | TC-067-06 |
| E2E-11 | FEAT-067 | TC-067-08 |
