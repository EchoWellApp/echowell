# App chrome: app bar, data bar, navigation and access-denied states

## Feature Description

The page frame shared by every dashboard page (wireframe v0.2, SRC-21): the route tree (`/login`, `/`, `/residents`, `/residents/[residentCode]` with `/review`, `/trends`, `/baseline`, `/log`, `/device`, `/admissions`, `/study`, `/admin`; no `/alerts`, `/analytics` or Devices route), the `/` redirect to `/residents`, the dark app bar with the brand "EchoWell", the facility line "<facility name>, Assisted living", the role-aware main navigation ("Resident list" with a red count badge of change alarms not yet reviewed, "New admissions", "Study team" for researcher and admin, "Admin" for admin), the display name and "Sign out", the yellow data bar on every page, one `<h1>` per page, document titles "<Page> – EchoWell", the skip link, the non-production environment ribbon, the resident-code validation and the access-denied states for `/admin` and `/study` (TRD 11 UX-010..UX-015, UX-018, UX-215, UX-229, UX-400; TRD 04 FE-020..FE-037, FE-088, FE-172, FE-208).

## Preconditions

- Local Docker Compose demo profile running, seeded with `test_v0_1` and the DS-07 pipeline run (as-of Oct 30, 2026, 3:00 PM CT; `FACILITY_NAME` Edgewood; `DATA_SOURCE_LABEL` "pipeline test data v0.1"; `PIPELINE_PROFILE=test_v0_1`); no alarm reviewed yet (fresh seed: 2 open change alarms R09, R10).
- Seeded users `clinician@example.com`, `researcher@example.com`, `admin@example.com` with the `SEED_*` passwords.
- Frontend built with `NEXT_PUBLIC_APP_ENV=local` (default for the local stack) unless the case says otherwise.
- Browser developer tools (Network panel, Accessibility tree, element inspector).

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-064-01 | `/` redirects to `/residents`; route tree has no retired routes | High | Positive |
| TC-064-02 | App bar brand and facility line from `meta.facility_name` | High | UI |
| TC-064-03 | Clinician navigation: Resident list (badge 2) and New admissions only | High | Positive |
| TC-064-04 | Researcher and admin navigation | High | Positive |
| TC-064-05 | Current link `aria-current="page"`, chart counts as Resident list | High | UI |
| TC-064-06 | Unreviewed-alarm badge: accessible name, singular form after one review | High | Positive |
| TC-064-07 | Badge hidden while loading or on error; link stays usable | Medium | Negative |
| TC-064-08 | Display name and "Sign out" button | Medium | UI |
| TC-064-09 | Data bar text on every page, including `/login` | High | UI |
| TC-064-10 | Production-profile `meta` and `config/ui` failure: data bar shows only the no-audio sentence | High | Negative |
| TC-064-11 | One `<h1>` per page, document titles, `lang="en"`, skip link | High | UI |
| TC-064-12 | Clinician and researcher on `/admin`: access denied, no admin API call | High | Security |
| TC-064-13 | Clinician on `/study`: access denied, no Study team API call | High | Security |
| TC-064-14 | Invalid resident code renders not-found state without API call | High | Negative |
| TC-064-15 | Environment ribbon for local, staging and production builds | Medium | UI |
| TC-064-16 | 403 from an API call shows the inline no-access message | Medium | Security |

### TC-064-01 Redirect and routes

| Step | Action | Expected Result |
|---|---|---|
| 1 | Signed in as clinician, open `/` | URL becomes `/residents`; `<h1>` "Residents in the study" |
| 2 | Open `/alerts` | "This page was not found." with the link "← Resident list" |
| 3 | Open `/analytics` and `/devices` | Same not-found page for each |
| 4 | Open `/residents/R09/review`, `/trends`, `/baseline`, `/log`, `/device` | Each loads the matching R09 chart section |

### TC-064-02 Brand and facility line

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `/residents` and inspect the app bar | `role="banner"`, background `--chrome` (#1F3A52 light); "EchoWell" 20px weight 700 in `--chrome-ink`; the brand is not a heading element |
| 2 | Read the facility line next to the brand | "Edgewood, Assisted living" (14px, `--chrome-muted`) |
| 3 | Compare with `GET /api/v1/config/ui` `meta.facility_name` | Same value "Edgewood" |
| 4 | Search every page for "[Facility name]" and for the old facility name of AGT-019 | No match |

### TC-064-03 Clinician navigation

| Step | Action | Expected Result |
|---|---|---|
| 1 | Sign in as clinician and inspect `<nav aria-label="Main">` | Links in order: "Resident list" (`/residents`) with badge "2", "New admissions" (`/admissions`) |
| 2 | Look for "Study team" and "Admin" | Neither link is present |
| 3 | Inspect a link's style | padding 8px 12px, radius 4px, weight 600, 15px, `--chrome-ink` |

### TC-064-04 Researcher and admin navigation

| Step | Action | Expected Result |
|---|---|---|
| 1 | Sign in as researcher | Links: "Resident list" (badge "2"), "New admissions", "Study team" (`/study`); no "Admin" |
| 2 | Sign in as admin | Links: "Resident list" (badge "2"), "New admissions", "Study team", "Admin" (`/admin`) in that order |
| 3 | Narrow the window to 375px | The navigation wraps below the brand; no horizontal page scroll |

### TC-064-05 Current page indicator

| Step | Action | Expected Result |
|---|---|---|
| 1 | On `/residents` inspect "Resident list" | `aria-current="page"`; background white at 16% opacity |
| 2 | Open `/residents/R09/trends` | "Resident list" still carries `aria-current="page"` |
| 3 | Open `/admissions` | "New admissions" has `aria-current="page"`; "Resident list" does not |
| 4 | As admin open `/study` and `/admin` | "Study team" then "Admin" carries `aria-current="page"` |

### TC-064-06 Unreviewed-alarm badge

| Step | Action | Expected Result |
|---|---|---|
| 1 | On `/residents` inspect the badge | Text "2"; `--red` background, white digit (`--badge-ink`), 13px, radius 999px |
| 2 | Check the link's accessible name in the Accessibility tree | "Resident list, 2 alarms not reviewed" |
| 3 | Compare with `GET /api/v1/alerts?status=open` | `total` = 2 (data alerts are not counted) |
| 4 | As clinician, save a review for R09 on `/residents/R09/review` (outcome "Checked on resident, no concern") | Badge changes to "1"; accessible name "Resident list, 1 alarm not reviewed" |
| 5 | Reset the data afterwards (`python -m backend.cli seed test_v0_1 --reset` in the backend container plus the DS-07 pipeline run) | Badge back to "2" |

### TC-064-07 Badge loading and failure

| Step | Action | Expected Result |
|---|---|---|
| 1 | Block `*/api/v1/alerts*` in the Network panel and reload `/residents` | "Resident list" shows no badge; accessible name "Resident list"; clicking it opens `/residents` |
| 2 | Throttle to "Slow 3G" with the URL unblocked and reload | No badge until the count arrives, then "2" |
| 3 | Check the rest of the page with the alerts request blocked | Resident table still renders 10 rows |

### TC-064-08 Display name and Sign out

| Step | Action | Expected Result |
|---|---|---|
| 1 | Signed in as clinician, inspect the right end of the app bar | Display name "Clinician" (14px, `--chrome-muted`) followed by the button "Sign out" (min-height 44px, `--chrome-ink` text, 1px solid `--chrome-muted` border) |
| 2 | Click "Sign out" | `POST /api/v1/auth/logout` sent; URL `/login` |

### TC-064-09 Data bar on every page

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `/residents`, `/residents/R09`, `/admissions`, `/study` (researcher) and `/admin` (admin) | Directly below the app bar each page shows "Test data only (pipeline test data v0.1, Oct 1–30, 2026). No real residents. No audio is stored or played anywhere in EchoWell." |
| 2 | Inspect the bar | `--yellow-bg` background, `--yellow` text, 14px, weight 600, 1px solid `--yellow-edge` bottom border, padding 6px 20px |
| 3 | Sign out and open `/login` | Data bar reads "No audio is stored or played anywhere in EchoWell." |
| 4 | Check that no page has a v0.1 footer | No footer text "Duplicate records are removed quietly and not shown." at page bottom outside the check-in log |

### TC-064-10 Production profile and config failure

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `npx vitest run components/DataBar` in `frontend/` | Passes: production-profile `meta` → "No audio is stored or played anywhere in EchoWell." only |
| 2 | On the local stack, block `*/api/v1/config/ui*` and reload `/residents` | Data bar reads "No audio is stored or played anywhere in EchoWell."; the facility line is omitted; the residents panel still loads |

### TC-064-11 Headings, titles, skip link

| Step | Action | Expected Result |
|---|---|---|
| 1 | On each route count `document.querySelectorAll("h1").length` | 1 on every route |
| 2 | Read the `<h1>` text per route | `/residents` "Residents in the study"; `/residents/R09` "R09"; `/admissions` "New admissions"; `/study` "Study team: how the system is working"; `/admin` "Admin"; `/login` "EchoWell" |
| 3 | Read the document titles | "Resident list – EchoWell"; "R09 · Summary – EchoWell"; "R09 · Review and notes – EchoWell" on `/residents/R09/review`; "New admissions – EchoWell"; "Study team – EchoWell"; "Admin – EchoWell"; "Sign in – EchoWell" |
| 4 | Inspect `<html>` | `lang="en"` |
| 5 | Load `/residents` and press Tab once | First focused element is "Skip to main content"; pressing Enter moves focus to `<main id="main">` |

### TC-064-12 /admin access denied

| Step | Action | Expected Result |
|---|---|---|
| 1 | Sign in as clinician; clear the Network panel; open `/admin` | `<h1>` "You do not have access to this page." and the link "← Resident list"; URL stays `/admin` (no redirect) |
| 2 | Check the Network panel | No request to `/api/v1/users`, `/api/v1/pipeline/runs`, `/api/v1/health` or any other admin endpoint |
| 3 | Click "← Resident list" | Opens `/residents` |
| 4 | Repeat steps 1–2 as researcher | Same access-denied state, no admin request |

### TC-064-13 /study access denied for clinician

| Step | Action | Expected Result |
|---|---|---|
| 1 | Sign in as clinician; clear the Network panel; open `/study` | "You do not have access to this page." and "← Resident list" |
| 2 | Check the Network panel | No request to `/api/v1/analytics`, `/api/v1/analytics/baselines`, CSV exports (`Accept: text/csv` on `/api/v1/scores`), `/api/v1/data-alerts`, `/api/v1/devices` or any CSV export |
| 3 | Check the nav | No "Study team" link |

### TC-064-14 Invalid resident code

| Step | Action | Expected Result |
|---|---|---|
| 1 | Clear the Network panel; open `/residents/r09!` | Page shows "← Resident list" and "Resident r09! was not found."; no banner, no section navigation |
| 2 | Check the Network panel | No `GET /api/v1/residents/…` request |
| 3 | Open `/residents/R99` (valid pattern, unknown) | `GET /api/v1/residents/R99` returns 404; page shows "Resident R99 was not found." with the back link and no other panels |

### TC-064-15 Environment ribbon

| Step | Action | Expected Result |
|---|---|---|
| 1 | On the local stack (`NEXT_PUBLIC_APP_ENV=local`) open any page | Ribbon "LOCAL" at the top of `<body>` above the app bar, 12px, `--font-mono`; no close control |
| 2 | Run `npx vitest run components/AppHeader components/EnvironmentRibbon` | Passes: `staging` → "STAGING – synthetic data"; `production` → no ribbon |
| 3 | **Hosted**: open the staging site | Ribbon "STAGING – synthetic data" visible on every page |
| 4 | **Hosted**: open the production site | No ribbon |

### TC-064-16 Inline 403 message

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `npx vitest run components/SectionState` | 403 case renders "You do not have access to this information." with no "Try again" button |
| 2 | As researcher, call `POST /api/v1/residents/R09/notes` with the researcher token (curl) | 403 problem+json (role not allowed); the UI never offers that control to a researcher (TC-063-12) |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/config/ui` (clinician token) | 200; `meta.facility_name` "Edgewood", `meta.pipeline_profile` "test_v0_1", `meta.data_source_label` "pipeline test data v0.1" |
| 2 | `GET /api/v1/alerts?status=open` | 200; `total` 2 (R09, R10) |
| 3 | `GET /api/v1/users` with the clinician token | 403 (admin only) |
| 4 | `GET /api/v1/analytics` with the clinician token | 403 |
| 5 | `GET /api/v1/residents/R99` | 404 problem+json |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT name FROM facilities;` | "Edgewood", the same value shown in the facility line |
| 2 | `SELECT count(*) FROM alerts WHERE status = 'open';` | 2 on a fresh seed, matching the badge |
| 3 | After TC-064-06 step 4: same query | 1 |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Alert count request fails | No badge, link usable (TC-064-07) |
| 2 | `config/ui` fails | Data bar "No audio is stored or played anywhere in EchoWell.", no facility line (TC-064-10) |
| 3 | Clinician/researcher opens `/admin` | "You do not have access to this page.", no admin API call (TC-064-12) |
| 4 | Clinician opens `/study` | Access denied, no Study team API call (TC-064-13) |
| 5 | Resident code `r09!` | Not-found state, no API call (TC-064-14) |
| 6 | Retired routes `/alerts`, `/analytics` | "This page was not found." (TC-064-01) |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-064-AC-01 | Clinician `/admin`: "You do not have access to this page." with "← Resident list", no admin request, no "Admin" link | TC-064-12, TC-064-03 |
| FEAT-064-AC-02 | Clinician: no "Study team" link; `/study` access denied with no `GET /api/v1/analytics` request | TC-064-13 |
| FEAT-064-AC-03 | App bar "EchoWell" / "Edgewood, Assisted living", nav per role with badge "2", data bar test-data sentence | TC-064-02, TC-064-03, TC-064-04, TC-064-09 |
| FEAT-064-AC-04 | `/` → `/residents`; "Resident list" `aria-current="page"` on `/residents/R09/trends` | TC-064-01, TC-064-05 |
| FEAT-064-AC-05 | Titles per FR-09, one `<h1>` per route with UX-010 text, skip link first focusable | TC-064-11 |
| FEAT-064-AC-06 | `/residents/r09!` renders not-found without API request | TC-064-14 |
| FEAT-064-AC-07 | `staging` → "STAGING – synthetic data"; `production` → no ribbon | TC-064-15 |
| FEAT-064-AC-08 | Production-profile `meta` → data bar only "No audio is stored or played anywhere in EchoWell." | TC-064-10 |

## Test Data Requirements

- DS-07 (`test_v0_1`, R01–R10, open change alarms R09 and R10), `FACILITY_NAME` Edgewood, `DATA_SOURCE_LABEL` "pipeline test data v0.1".
- Seeded users and `SEED_*` passwords; display name "Clinician" for the clinician.
- `NEXT_PUBLIC_APP_ENV` values `local`, `staging`, `production` (staging/production only on the hosted sites).
- Re-seed command for resetting the review made in TC-064-06.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-064-FR-01 | FEAT-064 | TC-064-01 |
| FEAT-064-FR-02 | FEAT-064 | TC-064-02 |
| FEAT-064-FR-03 | FEAT-064 | TC-064-03, TC-064-04 |
| FEAT-064-FR-04 | FEAT-064 | TC-064-05 |
| FEAT-064-FR-05 | FEAT-064 | TC-064-06, TC-064-07 |
| FEAT-064-FR-06 | FEAT-064 | TC-064-08 |
| FEAT-064-FR-07 | FEAT-064 | TC-064-09, TC-064-10 |
| FEAT-064-FR-08, FR-09, FR-10 | FEAT-064 | TC-064-11 |
| FEAT-064-FR-11 | FEAT-064 | TC-064-12 |
| FEAT-064-FR-12 | FEAT-064 | TC-064-13 |
| FEAT-064-FR-13 | FEAT-064 | TC-064-16 |
| FEAT-064-FR-14 | FEAT-064 | TC-064-14 |
| FEAT-064-FR-15 | FEAT-064 | TC-064-15 |
| UX-010 | FEAT-064 | TC-064-02, TC-064-11 |
| UX-011, UX-012 | FEAT-064 | TC-064-02 |
| UX-013, UX-014 | FEAT-064 | TC-064-03, TC-064-04, TC-064-05 |
| UX-015 | FEAT-064 | TC-064-08 |
| UX-018 | FEAT-064 | TC-064-06, TC-064-07 |
| UX-215 | FEAT-064 | TC-064-12 |
| UX-229 | FEAT-064 | TC-064-11 |
| UX-400 | FEAT-064 | TC-064-09, TC-064-10 |
| FE-020, FE-021, FE-022 | FEAT-064 | TC-064-01 |
| FE-023, FE-024, FE-088 | FEAT-064 | TC-064-02, TC-064-10 |
| FE-027, FE-028 | FEAT-064 | TC-064-03, TC-064-04, TC-064-05 |
| FE-029 | FEAT-064 | TC-064-08 |
| FE-030, FE-031 | FEAT-064 | TC-064-14 |
| FE-032, FE-033 | FEAT-064 | TC-064-11 |
| FE-034 | FEAT-064 | TC-064-12 |
| FE-035 | FEAT-064 | TC-064-16 |
| FE-036 | FEAT-064 | TC-064-06, TC-064-07 |
| FE-037 | FEAT-064 | TC-064-13 |
| FE-172 | FEAT-064 | TC-064-15 |
| FE-208 | FEAT-064 | TC-064-09, TC-064-10 |
| E2E-01 | FEAT-064 | TC-064-03, TC-064-09 |
| E2E-14 | FEAT-064 | TC-064-12 |
| E2E-21 | FEAT-064 | TC-064-13 |
| FE-188 | FEAT-064 | TC-064-12 |
