# Accessibility and responsive conformance

## Feature Description

Every page of the wireframe v0.2 dashboard meets WCAG 2.1 AA in the light and the dark colour scheme and the responsive layout of TRD 11 §4.12 (FEAT-075; TRD 11 UX-220..UX-228, UX-230, UX-240..UX-245; TRD 04 FE-162..FE-165, FE-190, FE-191, FE-211; TRD 03 NFR-060..NFR-070, NFR-140..NFR-142). Status is never shown by colour alone, every chart has a text alternative, all controls are keyboard-operable with a visible 3px focus ring, targets are at least 44 × 44 px, nothing animates, contrast holds in both schemes, headings and labels are correct, status messages use live regions, the chart section navigation becomes a scrolling row below 760px, the layout is one column below 640px and there is no page-level horizontal scroll from 320px. Automated proof: `frontend/tests/e2e/a11y.spec.ts` (axe on the 12-route list in both schemes, keyboard-only run, no-JavaScript message) and `frontend/tests/e2e/responsive.spec.ts`.

## Preconditions

- Local Docker Compose demo profile running and seeded with `test_v0_1` (DS-07): `docker compose --profile demo up -d --build --wait db backend frontend-prod`, frontend at `http://localhost:3001`.
- `.env` from `.env.development.example` with `RATE_LIMIT_LOGIN=60/minute` for the E2E runs (D-74, ENV-054); seeded users with the `SEED_*` passwords exported in the shell running Playwright.
- `cd frontend && npm ci && npx playwright install --with-deps chromium firefox webkit`.
- For manual checks: Chromium-based browser with developer tools (device toolbar, Rendering → "Emulate CSS media feature prefers-color-scheme / prefers-reduced-motion") and the axe DevTools extension (optional).
- The Playwright runs re-seed the database through `global-setup.ts`; run them on the local stack only.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-075-01 | axe: zero serious or critical violations on the 12 routes, light scheme | High | Accessibility |
| TC-075-02 | axe: zero serious or critical violations on the 12 routes, dark scheme | High | Accessibility |
| TC-075-03 | No page-level horizontal scroll at 320, 360, 375 and 390px; chart navigation is one scrolling row | High | UI |
| TC-075-04 | At 375×812 the residents table and change score chart scroll in named, focusable containers; targets ≥ 44px | High | UI |
| TC-075-05 | Keyboard-only run reaches and operates every TST-111 control with a visible 3px focus outline | High | Accessibility |
| TC-075-06 | Colour contrast in both schemes and the token-pair contrast table | High | Accessibility |
| TC-075-07 | Chart text alternatives: R09 change score table caption, Study team chart names and tables | High | Accessibility |
| TC-075-08 | Wide layout at 1280px and narrow layout at 600px | High | UI |
| TC-075-09 | JavaScript disabled shows "This dashboard needs JavaScript enabled." | High | Negative |
| TC-075-10 | Status, alarm and device information never by colour alone | High | Accessibility |
| TC-075-11 | Heading outline, labels and `aria-describedby` on forms | Medium | Accessibility |
| TC-075-12 | Status messages announced through live regions without moving focus | Medium | Accessibility |
| TC-075-13 | No animation under `prefers-reduced-motion: reduce` and no chart animation | Medium | UI |
| TC-075-14 | 200 % zoom: header row and chart banner wrap, page remains usable | Medium | UI |
| TC-075-15 | Loading, empty and error states stated in words | Medium | Negative |
| TC-075-16 | Browser matrix: Firefox and WebKit nightly, tablet ≥ 768px | Medium | Positive |
| TC-075-17 | Forbidden-terms check and plain-language statistical labels | Medium | Negative |

### TC-075-01 axe: zero serious or critical violations on the 12 routes, light scheme

| Step | Action | Expected Result |
|---|---|---|
| 1 | `cd frontend && npx playwright test tests/e2e/a11y.spec.ts --project=chromium -g "light scheme"`. | 12 tests "FE-190 <route> has no serious or critical violations (light)" pass. |
| 2 | Confirm the route list in the output. | `/login`, `/residents`, `/residents/R09`, `/residents/R09/review`, `/residents/R09/trends`, `/residents/R09/baseline`, `/residents/R09/log`, `/residents/R09/device`, `/residents/R08`, `/admissions`, `/study`, `/admin`. |
| 3 | Optional manual: sign in as admin, open `/residents` and run axe DevTools with WCAG 2.1 AA. | 0 serious and 0 critical issues. |
| 4 | Inspect `a11y.spec.ts` for rule exclusions (`disableRules`, `exclude`). | None, or each names the rule and a requirement or OQ ID (TST-153 practice). |

### TC-075-02 axe: zero serious or critical violations on the 12 routes, dark scheme

| Step | Action | Expected Result |
|---|---|---|
| 1 | `npx playwright test tests/e2e/a11y.spec.ts --project=chromium -g "dark scheme"`. | 12 tests "(dark)" pass; each asserts `matchMedia("(prefers-color-scheme: dark)").matches` is `true`. |
| 2 | Manual: emulate `prefers-color-scheme: dark`, open `/admin`. | Selected admin tab text readable (uses `--link`); no in-app theme toggle exists (FE-211). |

### TC-075-03 No page-level horizontal scroll at 320, 360, 375 and 390px; chart navigation is one scrolling row

| Step | Action | Expected Result |
|---|---|---|
| 1 | `npx playwright test tests/e2e/responsive.spec.ts --project=chromium -g "FE-191"`. | All viewport tests 320×568, 360×800, 375×812, 390×844 pass for `/residents`, `/residents/R09`, `/residents/R09/trends`. |
| 2 | Manual: device toolbar 320×568, open each route, run `document.documentElement.scrollWidth <= window.innerWidth` in the console. | `true` on all three routes. |
| 3 | On `/residents/R09` at 320px, inspect the navigation "Resident chart". | One row of links above the content, no wrapping, `overflow-x` `auto` or `scroll`; the banner status pill sits below the facts. |

### TC-075-04 At 375×812 the residents table and change score chart scroll in named, focusable containers; targets ≥ 44px

| Step | Action | Expected Result |
|---|---|---|
| 1 | At 375×812 open `/residents`; inspect the table wrapper. | `role="region"` named "Residents table", `tabindex="0"`; its `scrollWidth` > `clientWidth`; page itself does not scroll horizontally. |
| 2 | Open `/residents/R09/trends`; inspect the chart wrapper. | Region named "Change score chart", `tabindex="0"`, scrolls horizontally inside. |
| 3 | Tab into each container and press ArrowRight. | Container scrolls; focus ring visible. |
| 4 | Run the 44px check of `responsive.spec.ts` (part of `-g "375"`). | Every interactive target in header and main measures ≥ 44 × 44 CSS px except inline links in text. |

### TC-075-05 Keyboard-only run reaches and operates every TST-111 control with a visible 3px focus outline

| Step | Action | Expected Result |
|---|---|---|
| 1 | `npx playwright test tests/e2e/a11y.spec.ts --project=chromium -g "TST-111"`. | Pass (all POSTs are stubbed; nothing is written). |
| 2 | Manual, mouse unplugged: sign in as clinician, on `/residents` press Tab from the address bar. | Order: skip link "Skip to main content", app bar links, then main content top to bottom. |
| 3 | Tab to "Changed (2)" and press Enter; Tab to "All (10)" and press Space. | Filter applies each time; no focus trap. |
| 4 | Tab to "Open chart for R09" and press Enter; Tab through navigation "Resident chart". | Section links reached before section content; "Review this alert" reachable. |
| 5 | Activate "Review this alert"; in region "Review alert: changed since Oct 21" Tab to the checkboxes, the radio group "What did you find?" (arrow keys), the "Note" textbox, "Save review", "Remind me in 24 hours"; in "Staff notes" the combobox "Type of note", textbox "New note", "Add note". Do not submit. | Every control receives focus and responds to Space/Enter/arrows. |
| 6 | Inspect a focused element's computed outline. | `outline: 3px solid` in the `--link` colour with `outline-offset: 2px` (`:focus-visible`). |
| 7 | As admin on `/admin`, Tab to the tabs and use ArrowRight/ArrowLeft. | Tabs operate by keyboard (UX-221). |

### TC-075-06 Colour contrast in both schemes and the token-pair contrast table

| Step | Action | Expected Result |
|---|---|---|
| 1 | Check the TC-075-01 and TC-075-02 runs for `color-contrast`. | No `color-contrast` violation on any route in either scheme. |
| 2 | Open `docs/reports/FRONTEND_IMPLEMENTATION_REPORT.md` and find the TRD 11 §4.15 token-pair contrast table. | Table lists every token pair for light and dark with ratio; every text pair ≥ 4.5:1 and every non-text pair (chart graphics, borders) ≥ 3:1. |
| 3 | Spot-check `--c-aside` and `--c-quar` bar colours against `--surface` in the light scheme with a contrast checker. | Each ≥ 3:1. |

Note: no §4.15 token-pair table was found in `docs/reports/FRONTEND_IMPLEMENTATION_REPORT.md`, and `docs/reports/TRD_Implementation_Audit.md:106` records light `--c-aside` 2.23:1 and `--c-quar` 2.94:1 on `--surface` (`frontend/styles/tokens.css:28-29`); steps 2–3 are expected to fail until fixed.

### TC-075-07 Chart text alternatives: R09 change score table caption, Study team chart names and tables

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `/residents/R09/trends`; open the change score table alternative. | Element with role `table` and caption "Change score for R09, by scored check-in"; reachable by keyboard (TST-112). |
| 2 | Inspect the change score chart, sparklines and measurement cards. | Each chart has an accessible name. |
| 3 | Open `/study`; inspect "Check-ins per day". | Accessible name starting "Check-ins per day, <period>: <n> used, <n> set aside, <n> held back, <n> missed."; disclosure "Show daily counts as a table" with columns "Date", "Used", "Set aside", "Held back", "Missed", "Note". |
| 4 | Inspect "Usable check-ins by resident". | Each bar row has an accessible name with the resident ID and value. |
| 5 | Inspect `/admissions` facility range chart (component test, TC-073-10). | Named chart and "Show comparison as a table". |

### TC-075-08 Wide layout at 1280px and narrow layout at 600px

| Step | Action | Expected Result |
|---|---|---|
| 1 | `npx playwright test tests/e2e/responsive.spec.ts --project=chromium -g "FEAT-075-AC-07"`. | Both tests ("200px section navigation beside the content, tiles in one row" and "tiles stack in one column and page padding is 12px") pass. |
| 2 | Manual at 1280px: `/residents/R09`. | Section navigation is a 200px left column beside region "Right now"; the four "More detail" tile links are in one row. |
| 3 | At 1280px: `/residents/R09/trends` and `/study`. | Measurement cards in two columns; "Where check-ins are lost" and "Usable check-ins by resident" side by side. |
| 4 | At 600px: `/residents/R09`. | "More detail" tiles stack in one column; main padding computes to 12px; app bar navigation wraps below the brand. |

### TC-075-09 JavaScript disabled shows "This dashboard needs JavaScript enabled."

| Step | Action | Expected Result |
|---|---|---|
| 1 | `npx playwright test tests/e2e/a11y.spec.ts --project=chromium -g "NFR-142"`. | Pass. |
| 2 | Manual: disable JavaScript in developer tools settings and open `http://localhost:3001/login`. | Text exactly "This dashboard needs JavaScript enabled." is visible. |

### TC-075-10 Status, alarm and device information never by colour alone

| Step | Action | Expected Result |
|---|---|---|
| 1 | On `/residents`, read the status pills of R09, R08, R01. | "▲ Changed", "! Needs attention", "● Usual" with glyph, label and border. |
| 2 | Emulate achromatopsia (Rendering → Emulate vision deficiencies) and re-read. | All statuses still distinguishable by glyph and word. |
| 3 | On `/residents/R09/trends`, inspect alarm bars. | "▲" marker on alarm bars, the "Alarm line: 5" label and the data table present. |
| 4 | On `/residents/R09/device` and `/study`, read device status. | "●"/"○" plus words. |

### TC-075-11 Heading outline, labels and `aria-describedby` on forms

| Step | Action | Expected Result |
|---|---|---|
| 1 | On each of the 12 routes run `document.querySelectorAll('h1').length` in the console. | `1` on every route. |
| 2 | Check the heading levels of panels and sub-lists (HeadingsMap or console). | Panels `<h2>`, sub-lists `<h3>`; no skipped level. |
| 3 | On `/login`, `/residents/R09/review` and `/admin` (Users form), inspect inputs. | Each field has a visible `<label for>` or `<legend>`; error/help texts referenced by `aria-describedby`. |

### TC-075-12 Status messages announced through live regions without moving focus

| Step | Action | Expected Result |
|---|---|---|
| 1 | On `/residents` click "Changed (2)" with a screen reader (or inspect the DOM). | Filter result message is inside an `aria-live` region; focus stays on the button. |
| 2 | On `/admin`, add a user (TC-074-05) and check the confirmation message. | "<email> was added." announced through a live region; focus not moved. |
| 3 | Run `npx vitest run components` and check the live-region tests for filtering and saving. | Pass. |

### TC-075-13 No animation under `prefers-reduced-motion: reduce` and no chart animation

| Step | Action | Expected Result |
|---|---|---|
| 1 | Emulate `prefers-reduced-motion: reduce`; open `/residents/R09/trends` and `/study`. | Charts render in their final state at once; no transition. |
| 2 | In the console run `document.getAnimations().length` after load. | `0`. |
| 3 | Without the emulation, reload `/residents/R09/trends`. | Charts still render without animation (UX-230). |

### TC-075-14 200 % zoom: header row and chart banner wrap, page remains usable

| Step | Action | Expected Result |
|---|---|---|
| 1 | Desktop window 1280px wide, browser zoom 200 %, open `/residents`. | Text readable; filter buttons move below the heading; no page-level horizontal scroll. |
| 2 | Open `/residents/R09`. | Chart banner wraps; status pill moves below the heading; all controls reachable. |

### TC-075-15 Loading, empty and error states stated in words

| Step | Action | Expected Result |
|---|---|---|
| 1 | On `/residents`, block `*/api/v1/residents*` in developer tools and reload. | "Could not load <panel>. Check your connection and try again." with "Try again", inside `role="alert"`. |
| 2 | Throttle to "Slow 3G" and reload `/study`. | "Loading <panel>…" in a `role="status"` element before data. |
| 3 | Open `/admissions` on DS-07. | Empty state in words "No new admissions. The pipeline test data v0.1 has no admission group." |

### TC-075-16 Browser matrix: Firefox and WebKit nightly, tablet ≥ 768px

| Step | Action | Expected Result |
|---|---|---|
| 1 | `npx playwright test tests/e2e/a11y.spec.ts tests/e2e/responsive.spec.ts --project=firefox` then `--project=webkit`. | All tests pass in both projects. |
| 2 | Device toolbar 768×1024 (tablet), sign in and visit `/residents`, `/residents/R09`, `/study`. | Pages usable; no page-level horizontal scroll. |
| 3 | Check the latest scheduled `e2e.yml` run in GitHub Actions. | Main run passed for `chromium firefox webkit`. |

### TC-075-17 Forbidden-terms check and plain-language statistical labels

| Step | Action | Expected Result |
|---|---|---|
| 1 | `git grep -n -I -w -i -E "diagnoses|severity" -- frontend/app frontend/components frontend/lib/wording.ts`. | No output (same check as the `repo-hygiene` job). |
| 2 | Read the labels on `/residents/R09/trends` and `/study`. | Plain-language "change score" and "held back" used; no statistical jargon such as "CUSUM" or "quarantine" in UI copy. |

## API Validation

Not applicable: FEAT-075 adds no API; the tests read the DS-07 API only through the pages.

## Database Validation

Not applicable: FEAT-075 has no database impact (Database Impact: None).

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Disable JavaScript (TC-075-09) | "This dashboard needs JavaScript enabled." |
| 2 | Block a data request (TC-075-15) | Error stated in words with "Try again" |
| 3 | Introduce a serious axe violation on a throwaway branch (e.g. remove the `aria-label` of the "Residents table" region) and run `a11y.spec.ts` | Test for `/residents` fails listing `scrollable-region-focusable` |
| 4 | Remove `overflow-x` from the residents table wrapper on a throwaway branch and run `responsive.spec.ts` | Viewport tests fail (`scrollWidth` > `innerWidth`) |
| 5 | Emulate a colour-vision deficiency (TC-075-10) | Status still readable from glyph and word |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-075-AC-01 | `a11y.spec.ts` reports zero serious or critical axe violations on `/login`, `/residents`, the six R09 chart sections, `/residents/R08`, `/admissions`, `/study`, `/admin` in light and dark | TC-075-01, TC-075-02 |
| FEAT-075-AC-02 | At 320×568, 360×800, 375×812, 390×844 `scrollWidth <= innerWidth` on the three routes and the chart navigation is one scrolling row | TC-075-03 |
| FEAT-075-AC-03 | At 375×812 residents table and change score chart scroll in named, focusable containers; every target ≥ 44px | TC-075-04 |
| FEAT-075-AC-04 | Keyboard-only run reaches and operates every TST-111 control with a visible 3px focus outline | TC-075-05 |
| FEAT-075-AC-05 | axe colour-contrast passes in both schemes; token-pair table shows text ≥ 4.5:1 and non-text ≥ 3:1 in light and dark | TC-075-06 |
| FEAT-075-AC-06 | R09 change score table has role `table` with a caption naming R09; every Study team chart has a disclosure table or row accessible names | TC-075-07 |
| FEAT-075-AC-07 | At 1280px 200px section navigation beside content and four tiles in one row; at 600px tiles in one column and 12px padding | TC-075-08 |
| FEAT-075-AC-08 | With JavaScript disabled the page shows "This dashboard needs JavaScript enabled." | TC-075-09 |

## Test Data Requirements

- `test_v0_1` seed with DS-07 values (R01–R10; R09 and R10 changed, R08 needs attention); DS-10 ground truth loaded by `global-setup.ts`.
- Environment: `SEED_ADMIN_PASSWORD`, `SEED_CLINICIAN_PASSWORD`, `SEED_RESEARCHER_PASSWORD` exported for Playwright; `RATE_LIMIT_LOGIN=60/minute`; `E2E_BASE_URL` (default `http://localhost:3001`).
- Viewports 320×568, 360×800, 375×812, 390×844, 600px, 768×1024, 1280px.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-075-FR-01 / UX-220, NFR-060, TST-110, FE-190 | FEAT-075 | TC-075-01, TC-075-02 |
| FEAT-075-FR-02 / UX-004, NFR-061 | FEAT-075 | TC-075-10 |
| FEAT-075-FR-03 / UX-221, NFR-065, TST-111 | FEAT-075 | TC-075-05 |
| FEAT-075-FR-04 / UX-222, FE-163 | FEAT-075 | TC-075-05 |
| FEAT-075-FR-05 / UX-223, FE-162, NFR-064 | FEAT-075 | TC-075-04 |
| FEAT-075-FR-06 / UX-224, FE-211, NFR-062, NFR-063, TST-113 | FEAT-075 | TC-075-06 |
| FEAT-075-FR-07 / UX-225, FR-168, FR-320, TST-112 | FEAT-075 | TC-075-07 |
| FEAT-075-FR-08 / UX-226, UX-227 | FEAT-075 | TC-075-11 |
| FEAT-075-FR-09 / UX-228 | FEAT-075 | TC-075-12 |
| FEAT-075-FR-10 / UX-230, FE-164, FE-099 | FEAT-075 | TC-075-13 |
| FEAT-075-FR-11 / UX-240, FE-165 | FEAT-075 | TC-075-08 |
| FEAT-075-FR-12 / UX-241 | FEAT-075 | TC-075-03 |
| FEAT-075-FR-13 / UX-242 | FEAT-075 | TC-075-08 |
| FEAT-075-FR-14 / UX-243, NFR-068 | FEAT-075 | TC-075-03, TC-075-04 |
| FEAT-075-FR-15 / UX-244, UX-245 | FEAT-075 | TC-075-14 |
| FEAT-075-FR-16 / NFR-070 | FEAT-075 | TC-075-15 |
| FEAT-075-FR-17 / NFR-140, NFR-141, NFR-142 | FEAT-075 | TC-075-09, TC-075-16 |
| FEAT-075-FR-18 / NFR-066, NFR-067, UX-167 | FEAT-075 | TC-075-17 |
| FE-191, E2E-16, D-78 | FEAT-075 | TC-075-03, TC-075-04 |
