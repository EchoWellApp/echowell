# Frontend foundations (API client, generated types, query cache, formatting, wording, v0.2 tokens, status pills, section states)

## Feature Description

The shared frontend layer used by every page: the single typed API client `frontend/services/api.ts` (base URL `${NEXT_PUBLIC_API_BASE_URL}/api/v1`, `Accept`, `Authorization: Bearer`, `X-Request-ID` headers, 15 s timeout / 120 s for CSV upload, problem+json → `ApiError`), the generated contract types `frontend/lib/api-types.ts` (`npm run gen:api`), the TanStack Query client and query keys, the facility-time-zone formatters `lib/format.ts`, the display-status mapping `toDisplayStatus()` (Changed, Needs attention, Learning, Usual), the `StatusPill` component (colour + glyph + label + border), the wording module `lib/wording.ts` (with the marker "[Final clinical wording: confirm with PI]"), the wireframe v0.2 design tokens in `styles/tokens.css` (light and dark scheme) with the self-hosted "Source Sans 3" font, the shared primary/secondary button classes, the `SectionState` loading/empty/error component, the error boundaries, and the captured DS-07 fixtures with MSW handlers (TRD 04 §4.6–§4.14, TRD 11 §4.1, §4.3.4, §4.6, §4.11, §4.15).

## Preconditions

- Local Docker Compose demo profile running (`docs/deployment.md`), seeded with `test_v0_1` and the DS-07 pipeline run (as-of Oct 30, 2026, 3:00 PM CT, `PIPELINE_PROFILE=test_v0_1`, `FACILITY_TZ=America/Chicago`, `DATA_SOURCE_LABEL` "pipeline test data v0.1").
- Seeded users `clinician@example.com`, `researcher@example.com`, `admin@example.com` with the `SEED_*` passwords from the environment file.
- For the unit and static cases: a checkout with `frontend/node_modules` installed (`npm ci` in `frontend/`), Node 20.
- Browser with developer tools (Network panel, request blocking, `prefers-color-scheme` emulation). Chromium is the default.
- `pytest tests/validation -q` passes with zero failures (AGT-023).

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-062-01 | Formatting functions return the TRD 04 §4.11 strings (date-time, tally, threshold) | High | Positive |
| TC-062-02 | `formatLocalDate` is time-zone independent; dates on screen use facility time | High | Positive |
| TC-062-03 | API client headers, base URL and X-Request-ID on every request | High | API |
| TC-062-04 | Problem+json, non-JSON error and timeout become `ApiError` | High | Negative |
| TC-062-05 | Generated types have no drift; typecheck passes; D-114 fields present | High | Positive |
| TC-062-06 | `toDisplayStatus` and `StatusPill` render the four statuses with glyph, label and border | High | UI |
| TC-062-07 | Section error state with "Try again" and "Reference: <id>" | High | Negative |
| TC-062-08 | Section loading and empty states | Medium | UI |
| TC-062-09 | Failed background refresh keeps data and shows "Could not refresh…" | Medium | Negative |
| TC-062-10 | 403 renders "You do not have access to this information." without retry | High | Security |
| TC-062-11 | Error boundary renders "Something went wrong on this page." with "Reload" | Medium | Negative |
| TC-062-12 | Design tokens: no hex literal in component CSS, light and dark schemes | High | UI |
| TC-062-13 | Source Sans 3 served from the app's own origin; no font-service request | High | Security |
| TC-062-14 | Wording rules: PI marker, forbidden words absent, only allowed glyphs | High | UI |
| TC-062-15 | No fetch in components, no fixture/MSW import outside tests, no fixture data in build | High | Security |
| TC-062-16 | Protected pages send `Cache-Control: private, no-store`; no personal data, no audio, no edit controls | High | Security |
| TC-062-17 | Primary and secondary button styles | Medium | UI |
| TC-062-18 | Fixtures re-recorded from DS-07 produce no diff | Medium | Positive |

### TC-062-01 Formatting functions

| Step | Action | Expected Result |
|---|---|---|
| 1 | In `frontend/`, run `npx vitest run tests/unit/format.test.ts` | All tests pass |
| 2 | Confirm the test asserts `formatDateTimeShort("2026-10-30T19:28:04Z", "America/Chicago", "2026-10-30T20:00:00Z")` | Returns "Oct 30, 2:28 PM CT" |
| 3 | Confirm `formatTally(26.830256)` and `formatThreshold(5.0)` / `formatThreshold(4.5)` | "26.8"; "5"; "4.5" |
| 4 | Confirm `formatOpenDays` for 1, 9 and 0 | "1 day"; "9 days"; "opened today" |
| 5 | Confirm `formatSigned` of a negative value | Uses the minus sign U+2212 ("−"), not a hyphen |
| 6 | Sign in as clinician and open `/residents` | R09 row "Last check-in" reads "Oct 30, 2:28 PM CT"; the data bar reads "Test data only (pipeline test data v0.1, Oct 1–30, 2026). No real residents. No audio is stored or played anywhere in EchoWell." |
| 7 | Open `/residents/R09` | "More detail" tile "Voice trends" reads "Change score 26.8" (one decimal) |

### TC-062-02 Local dates independent of the browser time zone

| Step | Action | Expected Result |
|---|---|---|
| 1 | In `frontend/`, run `npm run test:tz` | Both runs (`TZ=Pacific/Kiritimati` and `TZ=America/Los_Angeles`) pass; `formatLocalDate("2026-10-01", …)` returns "Oct 1" in both |
| 2 | In the browser developer tools, emulate the time zone `Pacific/Kiritimati` and reload `/residents` | R09 "Last check-in" still reads "Oct 30, 2:28 PM CT"; "What's happening" still reads "Changed from their usual since Oct 21. Not reviewed yet." |
| 3 | Open `/residents/R09/baseline` with the same emulation | Text reads "First 16 usable check-ins, Oct 1–16, then frozen. Compared with it since Oct 17." |

### TC-062-03 API client headers

| Step | Action | Expected Result |
|---|---|---|
| 1 | Sign in as clinician, open the Network panel and reload `/residents` | The request `GET <NEXT_PUBLIC_API_BASE_URL>/api/v1/residents?…limit=500&offset=0…` is sent (path starts with `/api/v1`) |
| 2 | Inspect its request headers | `Accept: application/json`; `Authorization: Bearer <token>` present; `X-Request-ID` is a UUID |
| 3 | Reload and compare `X-Request-ID` of two consecutive requests | The two values differ (new UUID per request) |
| 4 | Inspect the request for `GET /api/v1/devices` on `/study` (researcher) | Query includes `limit=500&offset=0` |
| 5 | Run `npx vitest run tests/unit/api.test.ts` | All tests pass (headers, 15 s abort, problem+json parsing, non-JSON error → `UNKNOWN`, network error, 401 handler call) |

### TC-062-04 ApiError mapping and timeout

| Step | Action | Expected Result |
|---|---|---|
| 1 | Read the unit test for a mocked 422 problem+json response with `type` `urn:echowell:error:VALIDATION_ERROR` | Client throws `ApiError` with `code` "VALIDATION_ERROR", `requestId` equal to the body's `request_id`, and the body's `errors[]` |
| 2 | Read the unit test for a response that is not JSON | `ApiError.code` is "UNKNOWN"; `errors` defaults to `[]` |
| 3 | Read the unit test for a request exceeding 15 s | `ApiError` with `status` 0 and `title` "Network error" |
| 4 | Open `/residents` with the Network panel set to "Offline" (reload from cache disabled) | The residents panel shows "Could not load residents. Check your connection and try again."; no stack trace, token or raw body appears |

### TC-062-05 Generated types without drift

| Step | Action | Expected Result |
|---|---|---|
| 1 | In `frontend/`, run `npm run gen:api` | Command exits 0 |
| 2 | Run `git diff --stat -- lib/api-types.ts` (read-only check) | No diff |
| 3 | Run `npm run typecheck` | Exits 0 |
| 4 | Search `lib/api-types.ts` for `ResidentOverviewRow` | The schema has `needs_attention`, `attention_reasons` and `alarm_reviewed`; `OverviewSummary` has `changed`, `needs_attention`, `learning`, `usual`; `CheckinEventType` includes `checkins_started`; `Device` has `uploaded_on_as_of_date` |

### TC-062-06 Display statuses and StatusPill

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `npx vitest run tests/unit/status-roles-groups.test.ts components/StatusPill` | All tests pass; `toDisplayStatus("alarm_on", true)` returns `changed` (first match) |
| 2 | Sign in as clinician and open `/residents` | R09 pill "▲ Changed"; R03 pill "! Needs attention"; R01 pill "● Usual" |
| 3 | Inspect the R09 pill in the element inspector | Glyph "▲" is in a `<span aria-hidden="true">`; the pill has a 1px solid border, radius 999px, 14px, weight 700; text colour, background and border use `--red` / `--red-bg` / `--red` |
| 4 | Inspect the R03 pill | Glyph "!" `aria-hidden="true"`; colours `--yellow` / `--yellow-bg` / border `--yellow-edge` |
| 5 | Inspect the R01 pill | Glyph "●"; colours `--green` / `--green-bg` / `--green` |
| 6 | Open `/residents/R09` and inspect the banner pill | Large variant: 18px, padding 6px 16px, reads "▲ Changed" |
| 7 | On a stack with the R11 overlay (Learning fixture, `docs/deployment.md` demo overlay) open `/residents` | R11 pill "○ Learning" with `--grey` / `--grey-bg` / `--grey` |
| 8 | Switch the screen to greyscale (developer tools "Emulate vision deficiencies: achromatopsia") | Each status is still identifiable by glyph and label |

### TC-062-07 Section error state

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `npx vitest run components/SectionState` | All tests pass |
| 2 | Sign in as clinician; in the Network panel block the URL pattern `*/api/v1/residents*`; reload `/residents` | The residents panel shows "Could not load residents. Check your connection and try again." and a "Try again" button |
| 3 | Make the API return a 500 problem+json with a `request_id` (for example stop the database container while the backend runs) and reload | Under the message: "Reference: <request_id>" in 12px `--muted`, monospace font |
| 4 | Unblock the URL and click "Try again" | The list loads: filter buttons "All (10)", "Changed (2)", "Needs attention (2)", "Usual (6)" |
| 5 | On `/residents/R09` block only `*/api/v1/residents/R09/checkins*` and open "Check-in log" | Only the log panels show the error state; the banner and section navigation still render (failing panels never blank others) |

### TC-062-08 Loading and empty states

| Step | Action | Expected Result |
|---|---|---|
| 1 | Throttle the network to "Slow 3G" and load `/residents` | While loading, the panel shows "Loading residents…" with `role="status"`; filter buttons show "All (—)" etc. |
| 2 | Load `/residents/R09` with the same throttling | Banner facts show "—" as values until data arrives |
| 3 | Run the residents page test `npx vitest run tests/pages/residents.test.tsx` | Passes, including the empty list text "No residents are enrolled yet." |

### TC-062-09 Failed background refresh with cached data

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `/residents` and wait until the rows render | 10 rows visible |
| 2 | Set the Network panel to "Offline", switch to another tab and back (window focus refetch) | Rows stay visible; at the top of the page the notice "Could not refresh. Showing data as of Oct 30, 3:00 PM CT." appears |
| 3 | Go back online and refocus the window | The notice disappears after the next successful fetch |

### TC-062-10 403 access message

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `npx vitest run components/SectionState` | The test "renders 403 as no access" passes: text "You do not have access to this information." and no button |
| 2 | With the clinician token call `GET /api/v1/analytics` (curl) | 403 problem+json; a 403 is not retried by the query client (retry only for status 0 or ≥ 500, FE-080) |
| 3 | Read `components/SectionState/SectionState.tsx` `QueryState` | A 403 `ApiError` renders the no-access text without the `onRetry` button |

### TC-062-11 Error boundaries

| Step | Action | Expected Result |
|---|---|---|
| 1 | Read `frontend/app/(protected)/error.tsx` and `frontend/app/global-error.tsx` | Both render the `<h1>` "Something went wrong on this page." and a button "Reload"; no error message, stack or digest is rendered |
| 2 | Run `npx vitest run tests/pages/root.test.tsx tests/pages/protected-layout.test.tsx` | Pass |
| 3 | Open an unknown route, e.g. `/does-not-exist` | Page shows "This page was not found." and the link "← Resident list" |

### TC-062-12 Design tokens and schemes

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `npx vitest run tests/unit/tokens.test.ts` | Passes: no hex colour literal in `components/**/*.module.css` |
| 2 | Open `frontend/styles/tokens.css` | Every §4.15 token (`--chrome`, `--chrome-ink`, `--chrome-muted`, `--canvas`, `--surface`, `--surface-2`, `--ink`, `--muted`, `--rule`, `--link`, `--red`, `--red-bg`, `--yellow`, `--yellow-bg`, `--yellow-edge`, `--green`, `--green-bg`, `--grey`, `--grey-bg`, `--c-used`, `--c-aside`, `--c-quar`, `--badge-ink`) is defined once on `:root` and once under `@media (prefers-color-scheme: dark)` |
| 3 | In the browser, emulate `prefers-color-scheme: light` and inspect `body` on `/residents` | Background `#EDF1F4` (`--canvas`), text `#17232E` (`--ink`); app bar `#1F3A52`; content max width 1240px, page padding 20px, base font 16px, line-height 1.45 |
| 4 | Emulate `prefers-color-scheme: dark` | Background `#121A21`, text `#E6EDF3`, app bar `#0F2233`; Changed pill text `#FF8A80` |

### TC-062-13 Self-hosted font

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `/login` with the Network panel filtered to "Font" | The only font request is a `.woff2` served from the application's own origin (`/_next/static/media/…`) |
| 2 | Filter the Network panel for `fonts.googleapis.com` and `fonts.gstatic.com` while visiting `/residents`, `/residents/R09` and `/study` | No request to either host |
| 3 | Inspect the computed `font-family` of `body` | Starts with the Source Sans 3 variable family, fallback "Segoe UI", Helvetica, Arial, sans-serif |
| 4 | In a production build (`npm run build`), search `.next/static` for "IBM Plex" and for font-service host names | No match |

### TC-062-14 Wording rules

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `/residents` | Under the panel: "A status is a prompt to check on someone, not a diagnosis. [Final clinical wording: confirm with PI]" |
| 2 | Open `/residents/R09` | The "Right now" note reads "This compares R09 only with R09. It is a prompt to check in, not a diagnosis. [Final clinical wording: confirm with PI]" |
| 3 | On each page (`/residents`, every R09 section, `/admissions`, `/study`, `/admin`, `/login`) use the browser's find function for "depress", "severity", "severe", "disorder", "illness", "abnormal", "risk score", "mood", "patient", "[Facility name]" | No match; "diagnos" only inside "not a diagnosis" |
| 4 | Search the pages for "!" used as punctuation | None; "!" appears only as the Needs attention pill glyph |
| 5 | Inspect glyphs used across the pages | Only "▲", "!", "●", "○", "←"; no icon images or icon fonts |
| 6 | Run `npx vitest run tests/unit/wording-*.test.ts` | All pass (exact TRD 11 strings; marker present while `CLINICAL_WORDING_APPROVED = false`) |
| 7 | Check the app bar facility line | Reads "Demo Facility, Assisted living" (from `meta.facility_name`); the old facility name of AGT-019 never appears |

### TC-062-15 Single HTTP module and test-only fixtures

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `grep -rn "fetch(" frontend/app frontend/components` | No output |
| 2 | Run `grep -rln "tests/msw\|tests/fixtures\|from \"msw" frontend/app frontend/components frontend/lib frontend/services` | No output |
| 3 | Run `grep -rn "dangerouslySetInnerHTML\|innerHTML\|new Function\|eval(" frontend/app frontend/components frontend/lib` | No output |
| 4 | After `npm run build`, search `.next/static` for a DS-07 fixture marker string (e.g. a captured `request_id` from `tests/fixtures/ds07/residents.json`) | No match |
| 5 | Check the Network panel on every page | No third-party script, telemetry or analytics request |

### TC-062-16 Cache headers, privacy and read-only data

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `/residents` and inspect the document response headers | `Cache-Control: private, no-store` |
| 2 | Repeat for `/residents/R09`, `/admissions`, `/study`, `/admin`, `/login` | Same header on each |
| 3 | Review every page | Residents are shown only by study ID (R01–R10); no name, photo or room; no `<audio>` element (verify with `document.querySelectorAll("audio").length` = 0) |
| 4 | Look for edit, recompute, reset or delete controls for baselines, scores, change scores, alarms or records | None exist |
| 5 | Open Application/Storage in developer tools after browsing | No query data in `localStorage`, `sessionStorage` or IndexedDB (cache is in memory only) |

### TC-062-17 Button classes

| Step | Action | Expected Result |
|---|---|---|
| 1 | On `/login` inspect the "Sign in" button | min-height 44px, padding 0 20px, weight 700, radius 4px, background and border `--chrome`, text `--chrome-ink` |
| 2 | On `/residents/R09` inspect "Review this alert" | Same primary style |
| 3 | Inspect "See what changed" on `/residents/R09` and "Add note" on `/residents/R09/review` | min-height 44px, background `--surface`, ink text, 1px solid `--rule` border |

### TC-062-18 Fixture re-recording

| Step | Action | Expected Result |
|---|---|---|
| 1 | With the DS-07 stack running, run `npm run fixtures:capture` in `frontend/` | Exits 0; writes `tests/fixtures/ds07/*.json` |
| 2 | Check `git status --porcelain frontend/tests/fixtures/ds07` | No modified file except values the capture script documents as volatile (none expected) |
| 3 | Open `tests/fixtures/ds07/residents.json` | Rows in API order R09, R10, R03, R08, R01, R02, R04, R05, R06, R07 (not reordered) |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | Observe `GET /api/v1/residents` from `/residents` | 200; response has `items`, `total`, `summary` `{changed: 2, needs_attention: 2, learning: 0, usual: 6}` and `meta` with `facility_name`, `facility_tz` "America/Chicago", `data_source_label`, `as_of`, `baseline_n` 16, `cusum_h` 5.0, `pipeline_profile` "test_v0_1" |
| 2 | Request headers of any call | `Accept: application/json`, `Authorization: Bearer …`, unique `X-Request-ID` |
| 3 | Force a 500 / 422 response | Body is `application/problem+json` with `type` `urn:echowell:error:<CODE>` and `request_id`; the UI shows only the friendly message and "Reference: <request_id>" |
| 4 | Call any protected endpoint without a token (e.g. `curl <api>/api/v1/residents`) | 401 problem+json; in the UI a 401 clears the session and redirects to `/login?reason=expired&next=<path>` (wired by FEAT-063) |

## Database Validation

Not applicable: the frontend never accesses the database (FEAT-062 Database Impact: none).

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Block `*/api/v1/residents*` | "Could not load residents. Check your connection and try again." with "Try again"; app bar and data bar still render (TC-062-07) |
| 2 | Go offline during a background refresh | Cached rows kept; "Could not refresh. Showing data as of Oct 30, 3:00 PM CT." (TC-062-09) |
| 3 | Endpoint answers 403 | "You do not have access to this information.", no retry (TC-062-10) |
| 4 | 429 or 503 outside the login form | The affected section's error state ("Could not load <panel name>. …") or the error boundary when the whole page fails (TRD 17 LOG-081, D-179); e.g. on `/residents` "Could not load residents. Check your connection and try again." |
| 5 | Request exceeds 15 s | `ApiError` status 0 "Network error" (TC-062-04) |
| 6 | Render error inside a protected page | "Something went wrong on this page." with "Reload", no details (TC-062-11) |
| 7 | Unknown route | "This page was not found." with "← Resident list" (TC-062-11) |

Note: FEAT-062-FR-18 and FR-22 are aligned to the TRD (TRD 24 D-184): 429 and 503 outside the login form go to the section error state (TRD 17 LOG-081, D-179; frontend/lib/wording/common.ts:75-83), and the font is loaded with `next/font/local`.

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-062-AC-01 | `formatDateTimeShort(...)` = "Oct 30, 2:28 PM CT", `formatTally(26.830256)` = "26.8", `formatThreshold(5.0)` = "5" | TC-062-01 |
| FEAT-062-AC-02 | `formatLocalDate("2026-10-01", …)` = "Oct 1" under `TZ=Pacific/Kiritimati` and `TZ=America/Los_Angeles` | TC-062-02 |
| FEAT-062-AC-03 | 422 problem+json → `ApiError` code "VALIDATION_ERROR" with `request_id` and `errors[]`; 15 s timeout → status 0 "Network error" | TC-062-04 |
| FEAT-062-AC-04 | `npm run gen:api` no diff, `npm run typecheck` passes, `ResidentOverviewRow` has the D-114 fields | TC-062-05 |
| FEAT-062-AC-05 | No hex literal in component CSS; every token once on `:root` and once under dark; forbidden-words test passes | TC-062-12, TC-062-14 |
| FEAT-062-AC-06 | R09/R03/forming/R01 → Changed/Needs attention/Learning/Usual; pills "▲ Changed", "! Needs attention", "○ Learning", "● Usual" with hidden glyph and visible border | TC-062-06 |
| FEAT-062-AC-07 | Error state renders "Could not load <name>. Check your connection and try again.", "Try again" calling retry, "Reference: <id>" | TC-062-07 |
| FEAT-062-AC-08 | Source Sans 3 from own origin; no IBM Plex file; no font-service request | TC-062-13 |
| FEAT-062-AC-09 | No MSW/fixture import outside `frontend/tests/`, no fixture data in build, no `fetch(` in `frontend/app` and `frontend/components` | TC-062-15 |

## Test Data Requirements

- DS-07: `test_v0_1` seed (R01–R10) and pipeline run as-of 2026-10-30 15:00 America/Chicago; `FACILITY_NAME` Demo Facility; `DATA_SOURCE_LABEL` "pipeline test data v0.1".
- Learning fixture: R11 from `tests/fixtures/seeds/demo_overlay/` (isolated `echowell_demo` database) for the "○ Learning" pill.
- Seeded users and `SEED_*` passwords from the environment file; `NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_APP_ENV`.
- Captured fixtures `frontend/tests/fixtures/ds07/`; no audio, no real person.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-062-FR-01, FR-02, FR-05 | FEAT-062 | TC-062-03, TC-062-15 |
| FEAT-062-FR-03, FR-04 | FEAT-062 | TC-062-04 |
| FEAT-062-FR-06 | FEAT-062 | TC-062-05 |
| FEAT-062-FR-07, FR-11 | FEAT-062 | TC-062-01, TC-062-02 |
| FEAT-062-FR-08, FR-16 | FEAT-062 | TC-062-07, TC-062-08 |
| FEAT-062-FR-09, FR-17 | FEAT-062 | TC-062-09 |
| FEAT-062-FR-10 | FEAT-062 | TC-062-16 |
| FEAT-062-FR-12, FR-13 | FEAT-062 | TC-062-06 |
| FEAT-062-FR-14, FR-15, FR-23 | FEAT-062 | TC-062-14 |
| FEAT-062-FR-18 | FEAT-062 | TC-062-10, TC-062-11 |
| FEAT-062-FR-19 | FEAT-062 | TC-062-04 |
| FEAT-062-FR-20 | FEAT-062 | TC-062-15 |
| FEAT-062-FR-21 | FEAT-062 | TC-062-12 |
| FEAT-062-FR-22 | FEAT-062 | TC-062-13 |
| FEAT-062-FR-24 | FEAT-062 | TC-062-16 |
| FEAT-062-FR-25 | FEAT-062 | TC-062-18 |
| FEAT-062-FR-26 | FEAT-062 | Preconditions (validation gate) |
| FEAT-062-FR-27 | FEAT-062 | TC-062-15 |
| FEAT-062-FR-28 | FEAT-062 | TC-062-17 |
| UX-001, UX-006, UX-009 | FEAT-062 | TC-062-16 |
| UX-002, UX-003, UX-008 | FEAT-062 | TC-062-01, TC-062-02 |
| UX-004 | FEAT-062 | TC-062-06 |
| UX-122 | FEAT-062 | TC-062-17 |
| UX-160..UX-167 | FEAT-062 | TC-062-14 |
| UX-200..UX-206 | FEAT-062 | TC-062-07, TC-062-08, TC-062-09 |
| UX-250, UX-253 | FEAT-062 | TC-062-12 |
| UX-251 | FEAT-062 | TC-062-14 |
| UX-252 | FEAT-062 | TC-062-13 |
| FE-004 | FEAT-062 | TC-062-13 |
| FE-011, FE-062..FE-064 | FEAT-062 | TC-062-15 |
| FE-012 | FEAT-062 | TC-062-05 |
| FE-035 | FEAT-062 | TC-062-10 |
| FE-042, FE-045 | FEAT-062 | TC-062-16 |
| FE-070..FE-080 | FEAT-062 | TC-062-03, TC-062-04, TC-062-09 |
| FE-140..FE-145 | FEAT-062 | TC-062-07, TC-062-08, TC-062-09, TC-062-11 |
| FE-150..FE-154 | FEAT-062 | TC-062-01, TC-062-02 |
| FE-160, FE-161, FE-211 | FEAT-062 | TC-062-12 |
| FE-092, FE-207 | FEAT-062 | TC-062-06 |
| TST-063 | FEAT-062 | TC-062-05 |
| TST-090 | FEAT-062 | TC-062-06, TC-062-07 |
| TST-095 | FEAT-062 | TC-062-15, TC-062-18 |
| TST-097 | FEAT-062 | TC-062-14 |
| TST-096 | FEAT-062 | TC-062-01, TC-062-02, TC-062-04 |
