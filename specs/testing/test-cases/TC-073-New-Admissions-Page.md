# New admissions page (experimental, v0.2 restyle)

## Feature Description

`/admissions` is the experimental page for the new-admission study arm (FEAT-073, TRD 11 UX-181..UX-195, UX-264). It shows the dashed yellow open-question note, the panel with the `<h1>` "New admissions" and its intro, the admissions table (Status · Resident · Admitted · Compared with facility range · Own baseline, plus "Show comparison"), the comparison panel "<R> compared with facility range" with `FacilityRangeChart` (resident value dot against the grey facility band), its table alternative "Show comparison as a table", the transition sentence, the range method line and the empty states. The pipeline test data (DS-07) has no admission arm, so on the seeded stack the reference rendering is the empty state; populated states are verified with the synthetic page-test fixture (A01 `outside_range`, A02 `range_not_available`, TST-186). The page raises no alerts (D-06), uses neutral `RangePill`s "Out of range" / "In range" (D-117) and has no back link (UX-180 retired) and no footer.

## Preconditions

- Local Docker Compose demo profile running (`docker compose --profile demo up -d --build --wait db backend frontend-prod`, `docs/deployment.md`), seeded with `docker compose exec -T backend python -m backend.cli seed test_v0_1 --reset`; frontend at `http://localhost:3001`, API at `http://localhost:8000/api/v1`.
- Seeded users `admin@example.com`, `clinician@example.com`, `researcher@example.com` with the `SEED_*` passwords from `.env` (never written into a test record).
- Browser with developer tools (Elements and Network panels).
- For the populated-state cases: Node 20 and `cd frontend && npm ci` done, so the page test `frontend/tests/pages/admissions.test.tsx` and the component tests can be run with Vitest.
- `psql` access to the local database (read-only `SELECT`).

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-073-01 | DS-07 reference rendering: note, heading, intro, empty texts, no back link | High | Positive |
| TC-073-02 | Experimental note styling and exact wording | Medium | UI |
| TC-073-03 | App bar with "New admissions" current, data bar, no footer | High | UI |
| TC-073-04 | Page reachable from the main navigation for all three roles | Medium | Positive |
| TC-073-05 | Experimental endpoints on DS-07 return the empty list and the experimental header | High | API |
| TC-073-06 | `outside_range` row: neutral "Out of range" pill, "Outside facility range", red "▲" dot | High | Positive |
| TC-073-07 | `range_not_available` row: "○ Learning" and "Facility range not available yet" | High | Positive |
| TC-073-08 | Table columns, "Own baseline" "<n> of <N>", admitted date, scroll container | Medium | UI |
| TC-073-09 | "Show comparison" selects the row and opens the comparison panel with caption and transition sentence | High | Positive |
| TC-073-10 | Comparison table alternative and plain-language measurement labels | Medium | UI |
| TC-073-11 | Range method line shown only when ranges are returned | Medium | Positive |
| TC-073-12 | Empty text depends on `meta.pipeline_profile` (test vs production) | Medium | Positive |
| TC-073-13 | Admissions query error shows the table section error only | High | Negative |
| TC-073-14 | Comparison query error leaves the table usable | Medium | Negative |
| TC-073-15 | Unauthenticated access and expired token redirect to `/login` | High | Security |
| TC-073-16 | No alert, no audio, no forbidden wording on the page | Medium | Negative |

### TC-073-01 DS-07 reference rendering: note, heading, intro, empty texts, no back link

| Step | Action | Expected Result |
|---|---|---|
| 1 | Sign in at `http://localhost:3001/login` as `clinician@example.com` and open `http://localhost:3001/admissions`. | Page loads; browser tab title reads "New admissions – EchoWell". |
| 2 | Read the first element of the main content. | Note reads exactly "Future / experimental. Not in pipeline test v0.1: the test data has no admission group or facility range yet. Open question for Shaba and the PI." |
| 3 | Read the panel heading and the line below it. | `<h1>` "New admissions"; line "New residents don’t have their own baseline yet, so their first check-ins are compared with the facility’s usual range." |
| 4 | Read the table area of the panel. | Text "No new admissions. The pipeline test data v0.1 has no admission group."; no `<table>` element is rendered. |
| 5 | Read the panel below. | Text "Select a resident to see the comparison." |
| 6 | Search the page for a back link (Ctrl+F "←" and "Back"). | No back link and no "← Resident list" link in the main content. |

### TC-073-02 Experimental note styling and exact wording

| Step | Action | Expected Result |
|---|---|---|
| 1 | On `/admissions`, inspect the note element in developer tools (Computed tab). | Border 1px dashed in the `--yellow-edge` colour; background `--yellow-bg`; text colour `--yellow`; font-size 14px; padding 8px 12px; border-radius 6px. |
| 2 | Compare the note text character by character with UX-181. | Identical, including "Future / experimental." and both open-question sentences (kept until OQ-08 closes). |
| 3 | Switch the OS/browser to dark colour scheme and reload. | Note stays visible with the dark-scheme yellow tokens; text remains readable (no colour-only meaning). |

### TC-073-03 App bar with "New admissions" current, data bar, no footer

| Step | Action | Expected Result |
|---|---|---|
| 1 | On `/admissions`, inspect the main navigation links. | Links "Resident list", "New admissions", "Study team" (and "Admin" for admin only); the "New admissions" link has `aria-current="page"`. |
| 2 | Read the data bar under the app bar. | "Test data only (pipeline test data v0.1, Oct 1–30, 2026). No real residents. No audio is stored or played anywhere in EchoWell." |
| 3 | Scroll to the end of the page and inspect the DOM for `<footer>`. | No page footer element; the no-audio statement appears only in the data bar. |

### TC-073-04 Page reachable from the main navigation for all three roles

| Step | Action | Expected Result |
|---|---|---|
| 1 | Sign in as `admin@example.com`; click "New admissions" in the app bar. | URL `/admissions`; `<h1>` "New admissions". |
| 2 | Repeat as `clinician@example.com`. | Same page, no access-denied text. |
| 3 | Repeat as `researcher@example.com`. | Same page, no access-denied text (E-22..E-24 allow admin, clinician, researcher). |

### TC-073-05 Experimental endpoints on DS-07 return the empty list and the experimental header

| Step | Action | Expected Result |
|---|---|---|
| 1 | `curl -s -X POST http://localhost:8000/api/v1/auth/login -H 'Content-Type: application/json' -d '{"email":"clinician@example.com","password":"'"$SEED_CLINICIAN_PASSWORD"'"}'`; keep `access_token` as `$TOKEN`. | HTTP 200 with a bearer token. |
| 2 | `curl -si "http://localhost:8000/api/v1/admissions?limit=500" -H "Authorization: Bearer $TOKEN"`. | HTTP 200; header `X-EchoWell-Experimental: true`; body `items` is `[]`; `meta.pipeline_profile` is `test_v0_1`; `meta.baseline_n` is `16`. |
| 3 | `curl -si http://localhost:8000/api/v1/facility/reference-ranges -H "Authorization: Bearer $TOKEN"`. | HTTP 200; header `X-EchoWell-Experimental: true`; response has `items` and `meta`. |
| 4 | In the browser Network panel on `/admissions`, list API calls. | `GET /api/v1/admissions?limit=500` is called; no call to `/admissions/{code}/comparison` is made while no resident is selected. |

### TC-073-06 `outside_range` row: neutral "Out of range" pill, "Outside facility range", red "▲" dot

| Step | Action | Expected Result |
|---|---|---|
| 1 | `cd frontend && npx vitest run tests/pages/admissions.test.tsx components/AdmissionsTable components/FacilityRangeChart`. | All tests pass (0 failed). |
| 2 | Review the test "shows rows and the comparison of the selected resident (FEAT-073-AC-02..AC-04)" for fixture row A01 (`comparison_status` `outside_range`). | A01 row Status cell text "Out of range" with no "▲" glyph and no red/green status class; "Compared with facility range" cell "Outside facility range". |
| 3 | In the same test, check the comparison chart of A01. | Each out-of-range measurement dot has `data-outside="true"`, the `--red` colour class and an aria-hidden "▲"; in-range dots use ink; band elements use `--grey-bg` (never red). |
| 4 | Check the `within_range` component case (A02 in `AdmissionsTable.test.tsx`). | Pill "In range" (neutral) and text "Within facility range". |

Note: populated admissions cannot be produced on the seeded stack (DS-07 has no admission arm); this case runs the synthetic MSW fixture of TST-186.

### TC-073-07 `range_not_available` row: "○ Learning" and "Facility range not available yet"

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `cd frontend && npx vitest run tests/pages/admissions.test.tsx`. | Pass. |
| 2 | Check fixture row A02 (`range_not_available`) assertions. | Status cell "○ Learning" (`StatusPill` learning); "Compared with facility range" cell "Facility range not available yet". |
| 3 | Check `AdmissionsTable.test.tsx` row A03 (`not_enough_checkins`). | "○ Learning" and "Not enough check-ins yet". |
| 4 | Check `FacilityRangeChart` with no banded features. | Text "Facility range not available yet"; no band rows (`data-testid="range-row"` count 0) and no "Show comparison as a table" disclosure. |

### TC-073-08 Table columns, "Own baseline" "<n> of <N>", admitted date, scroll container

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `npx vitest run components/AdmissionsTable` and read the first test. | Column headers in order "Status", "Resident", "Admitted", "Compared with facility range", "Own baseline", "Actions" ("Actions" visually hidden). |
| 2 | Check row A01 values. | "A01" (weight 700), "Oct 21", "Outside facility range", "6 of 16" (N from `meta.baseline_n` = 16). |
| 3 | Check row A04 with `admitted_on` null. | Admitted cell shows "—". |
| 4 | Check the table container. | `role="region"` named "New admissions table" with `tabindex="0"`; table `min-width: 640px` scrolls inside it. |

### TC-073-09 "Show comparison" selects the row and opens the comparison panel with caption and transition sentence

| Step | Action | Expected Result |
|---|---|---|
| 1 | In `tests/pages/admissions.test.tsx`, follow the click on the button named "Show comparison for A01". | Button is a secondary button with min-height 44px. |
| 2 | Check the A01 row after the click. | Row has `aria-selected="true"`; its first cell has a 5px `--chrome` left border; exactly one row is selected. |
| 3 | Check the comparison panel. | `<h2>` "A01 compared with facility range"; caption "Grey band = usual range across current residents" (12px, `--muted`). |
| 4 | Check the sentence under the chart. | "After 16 usable check-ins, the resident moves to the resident list and is compared with their own baseline instead." (N = `meta.baseline_n`). |

### TC-073-10 Comparison table alternative and plain-language measurement labels

| Step | Action | Expected Result |
|---|---|---|
| 1 | In the comparison panel of the fixture, open the disclosure "Show comparison as a table". | Table with columns "Measurement", "Resident value", "Facility range", "Outside range". |
| 2 | Check an out-of-range row and an in-range row. | "Outside range" reads "▲ Yes" and "No" respectively; "Facility range" reads "<low>–<high>" with at most 2 decimals and U+2212 for negatives. |
| 3 | Check the measurement labels. | Scored keys use the TRD 11 §4.5.4 labels: `loudness_dbfs` "Quieter", `total_phrase_duration_s` "Slower to say the phrase", `speech_rate_syl_per_s` "Fewer syllables per second", `articulation_rate_syl_per_s` "Slower while talking", `number_of_pauses` "More pauses", `pause_fraction` "More time in pauses", `voiced_fraction` "Less voiced sound"; any other key shows the API label. |
| 4 | Check the chart accessible name. | `role="img"` named "A01 compared with facility range: <k> of <n> measurements outside the range". |

### TC-073-11 Range method line shown only when ranges are returned

| Step | Action | Expected Result |
|---|---|---|
| 1 | In the page test with reference ranges returned, read the line under the transition sentence. | "Range from <n_residents> current residents, computed <Mon D> (method: <method>)." with the values of the fixture. |
| 2 | Run the test "omits the method line when no ranges are returned". | No line starting "Range from" is rendered. |

### TC-073-12 Empty text depends on `meta.pipeline_profile` (test vs production)

| Step | Action | Expected Result |
|---|---|---|
| 1 | On the seeded stack (`meta.pipeline_profile` = `test_v0_1`) open `/admissions`. | "No new admissions. The pipeline test data v0.1 has no admission group." |
| 2 | Run `npx vitest run components/AdmissionsTable -t "empty text by profile"`. | With `pipeline_profile` `production` the text is exactly "No new admissions."; with `test_v0_1` the longer text. |
| 3 | Search the frontend source for an environment check deciding this text: `grep -n "admissionsEmpty" -r frontend/components frontend/lib`. | The text is chosen only from `meta.pipeline_profile` (FE-077), not from `NEXT_PUBLIC_APP_ENV`. |

### TC-073-13 Admissions query error shows the table section error only

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run the page test "shows the admissions error only in the table panel". | Pass. |
| 2 | Manual: on the demo stack open `/admissions`, then in developer tools block the request URL pattern `*/api/v1/admissions*` and reload. | Table area shows "Could not load new admissions. Check your connection and try again." with a "Try again" button (and "Reference: <request id>" when the API returned one); the note and `<h1>` stay visible. |
| 3 | Unblock the URL and click "Try again". | Empty-state text of TC-073-01 step 4 appears; the error disappears. |

### TC-073-14 Comparison query error leaves the table usable

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run the page test "keeps the table when the comparison fails (UX-202)". | Pass. |
| 2 | Check its assertions. | Comparison panel shows "Could not load the comparison. Check your connection and try again." with "Try again"; the admissions table rows (A01, A02) stay visible. |

### TC-073-15 Unauthenticated access and expired token redirect to `/login`

| Step | Action | Expected Result |
|---|---|---|
| 1 | In a private window, open `http://localhost:3001/admissions` without signing in. | Redirect to `/login`; no admissions data shown. |
| 2 | `curl -s -o /dev/null -w '%{http_code}' "http://localhost:8000/api/v1/admissions?limit=500"` (no token). | `401`. |
| 3 | Run the page test 401 case in `tests/pages/admissions.test.tsx`. | Redirect to `/login` is asserted (TST-094). |

### TC-073-16 No alert, no audio, no forbidden wording on the page

| Step | Action | Expected Result |
|---|---|---|
| 1 | On `/admissions` inspect the DOM for `<audio>` and `<video>`. | None present. |
| 2 | Search the page text for "diagnosis", "diagnoses", "severity", "alarm". | None found. |
| 3 | `SELECT count(*) FROM alerts;` before and after opening `/admissions` and selecting nothing. | Count unchanged (the page creates no alert, D-06). |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/admissions?limit=500` with a clinician Bearer token | 200; `X-EchoWell-Experimental: true`; DS-07 `items` `[]`; `meta.pipeline_profile` `test_v0_1`; `meta.baseline_n` 16 |
| 2 | `GET /api/v1/admissions/R01/comparison` with a Bearer token | 404 RFC 7807 body (R01 is not in the new-admission cohort, API-090); the page never requests it because no row exists |
| 3 | `GET /api/v1/facility/reference-ranges` with a Bearer token | 200; `X-EchoWell-Experimental: true`; `items` and `meta` present |
| 4 | Any of the three endpoints without a token | 401 |
| 5 | Verify the response schemas against `/api/v1/docs` (`AdmissionList`, `AdmissionComparison`, `ReferenceRangeList`) | Field names match: `resident_code`, `admitted_on`, `comparison_status`, `own_baseline_progress`, `features[].low/high/resident_value/outside_range`, `n_residents`, `computed_at`, `method` |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT count(*) FROM residents;` and `SELECT count(*) FROM residents WHERE cohort = 'new_admission';` on the seeded database | 10 (R01–R10) and 0; no new-admission resident exists, which is why the page shows the empty state |
| 2 | `SELECT count(*) FROM alerts;` before and after using the page | Unchanged (frontend only, no writes; FEAT-073 Database Impact: none) |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Block `*/api/v1/admissions*` in developer tools and reload (TC-073-13) | Table error "Could not load new admissions. Check your connection and try again." with "Try again" |
| 2 | Comparison request fails (TC-073-14) | Comparison error only; table stays usable |
| 3 | Open `/admissions` without a session (TC-073-15) | Redirect to `/login`; API returns 401 |
| 4 | Comparison with no ranges (`range_not_available`, TC-073-07) | "○ Learning", "Facility range not available yet", no band rows |
| 5 | Look for alerts, audio or forbidden words (TC-073-16) | None |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-073-AC-01 | On DS-07 the exact note, `<h1>` "New admissions", "No new admissions. The pipeline test data v0.1 has no admission group.", "Select a resident to see the comparison." are shown and no back link exists | TC-073-01, TC-073-02 |
| FEAT-073-AC-02 | `outside_range` row shows neutral "Out of range" (no "▲", no red) and "Outside facility range"; out-of-range dot is `--red` with "▲" | TC-073-06 |
| FEAT-073-AC-03 | `range_not_available` row shows "○ Learning" and "Facility range not available yet" | TC-073-07 |
| FEAT-073-AC-04 | "Show comparison" sets `aria-selected="true"`, shows "<R> compared with facility range", the caption and "After 16 usable check-ins, …" with N from `meta.baseline_n` | TC-073-09 |
| FEAT-073-AC-05 | App bar with "New admissions" current, the data bar, no footer | TC-073-03 |

## Test Data Requirements

- `test_v0_1` seed (R01–R10, DS-07 values); no new-admission resident exists, so the seeded stack renders the empty state.
- Synthetic MSW fixture of `frontend/tests/pages/admissions.test.tsx` and component tests: study IDs A01 (`outside_range`), A02 (`within_range` in the component test, `range_not_available` in the page test), A03 (`not_enough_checkins`), A04 (`range_not_available`, `admitted_on` null); `meta.baseline_n` 16.
- Environment: `.env` from `.env.development.example` (`PIPELINE_PROFILE=test_v0_1`, `SEED_*` values), `NEXT_PUBLIC_API_BASE_URL` (frontend build argument).
- No audio, no real names or rooms.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-073-FR-01 / UX-181, FR-200, VIS-009, OQ-08 | FEAT-073 | TC-073-01, TC-073-02 |
| FEAT-073-FR-02 / UX-182 | FEAT-073 | TC-073-01 |
| FEAT-073-FR-03 / UX-183, UX-243, FR-201 | FEAT-073 | TC-073-08 |
| FEAT-073-FR-04 / UX-184, UX-186 | FEAT-073 | TC-073-08 |
| FEAT-073-FR-05 / UX-185, FR-202, UX-004, D-117, FE-092 | FEAT-073 | TC-073-06, TC-073-07 |
| FEAT-073-FR-06 / UX-187 | FEAT-073 | TC-073-09 |
| FEAT-073-FR-07 / UX-188, FR-205 | FEAT-073 | TC-073-05, TC-073-01 |
| FEAT-073-FR-08 / FE-100, UX-189, UX-190, FR-203, D-44 | FEAT-073 | TC-073-06, TC-073-09 |
| FEAT-073-FR-09 / UX-191 | FEAT-073 | TC-073-10 |
| FEAT-073-FR-10 / UX-192, UX-195 | FEAT-073 | TC-073-09, TC-073-11 |
| FEAT-073-FR-11 / UX-193, UX-225 | FEAT-073 | TC-073-10 |
| FEAT-073-FR-12 / UX-194, UX-264 | FEAT-073 | TC-073-01, TC-073-12 |
| FEAT-073-FR-13 / UX-400, UX-180 retired | FEAT-073 | TC-073-03 |
| UX-202 (section errors) | FEAT-073 | TC-073-13, TC-073-14 |
| E-22, E-23, E-24, API-089 | FEAT-073 | TC-073-05 |
| TST-094, TST-090, TST-186 | FEAT-073 | TC-073-06, TC-073-07, TC-073-15 |
| E2E-13, FE-189, D-06 | FEAT-073 | TC-073-01, TC-073-16 |
