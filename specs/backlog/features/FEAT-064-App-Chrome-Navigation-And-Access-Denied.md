# FEAT-064 App chrome: app bar, data bar, navigation and access-denied states

| Field | Value |
|---|---|
| Epic | Frontend |
| Build phase | Phase 8 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-063 |
| Status | Not Started |

## Purpose

Provide the page frame that all dashboard pages share in wireframe v0.2 (SRC-21): the route tree of TRD 24 D-110, the `/` redirect, the dark app bar with the brand "EchoWell", the facility line "<facility name>, Assisted living" and the role-aware main navigation ("Resident list" with a red count badge of change alarms not yet reviewed, "New admissions", "Study team" for researchers and admins, "Admin" for admins, then the display name and "Sign out"), the yellow data bar under the app bar on every page (replacing the v0.1 page footers and sublines), the one-`<h1>` rule, document titles, the skip link, the non-production environment ribbon, and the access-denied states for `/admin` and `/study`. Page content is delivered by the page features.

## Business Context

- BR-12, BR-13: staff move between the resident list, a resident's chart, New admissions and the Study team page with one consistent app bar (SRC-21, TRD 24 D-110).
- BR-01, BR-03 (no audio; test data visible as such): the data bar states on every page, including Login, that no audio is stored or played and, on test data, that no real residents are shown (UX-400, D-OWNER-4).
- BR-16: the Study team and Admin areas are visible and reachable only to the permitted roles.
- D-110: pages Resident list, Resident chart (6 sections), New admissions, Study team, plus Login and Admin (D-111); the v0.1 Alert review (`/alerts`) and Analytics (`/analytics`) routes no longer exist.
- FRs covered (BACKLOG.md): FR-138, FR-218, FR-310, FR-330.

## Referenced TRDs

- TRD 11 (v0.13) — owned by this feature: UX-010 (brand, one `<h1>` per page and its text per route), UX-011, UX-012 (facility line from `meta.facility_name`, never a placeholder facility name), UX-013, UX-014 (navigation order, styles, current page, Admin link), UX-015 (display name and "Sign out"), UX-018 (unreviewed-alarm badge on "Resident list", D-97 fallback, Study team visibility), UX-215 (access denied on `/admin`), UX-229 (`lang` and page titles), UX-400 (data bar). Retired and not built: UX-005 (footers), UX-016 (Devices link), UX-180 (admissions back link), §4.0 screen map for routes.
- TRD 04 (v0.11) FE-020..FE-024 (routes, redirect, protected group, `AppHeader` and `DataBar` on every page, brand and facility line), FE-027, FE-028 (current link, nav order and role rules), FE-029..FE-035 (display name and Sign out, resident code validation and encoding, titles, skip link, access denied, 403 message), FE-036 (`CountBadge` count), FE-037 (`/study` access denied), FE-088 (chrome `meta` from `getUiConfig()`), FE-208 (`DataBar`), §4.3 route table, §4.8 `AppHeader`, `DataBar`, `CountBadge`.
- TRD 12 SEC-043 (role-dependent visibility).
- TRD 21 ENV-032 (staging and local ribbon); TRD 04 FE-172.
- TRD 02 FR-138, FR-218, FR-310, FR-330; TRD 24 D-23 as amended by D-110, D-97, D-108, D-111, D-112, D-113.
- TRD 13 E2E-01, E2E-14, E2E-21; FE-188.

## Scope

- Route files: `app/page.tsx` (redirect), `app/login/page.tsx` (from FEAT-063), `app/(protected)/residents/page.tsx`, `app/(protected)/residents/[residentCode]/` (segment with code validation; the chart layout and its six section routes are FEAT-066), `app/(protected)/admissions/page.tsx`, `app/(protected)/study/page.tsx`, `app/(protected)/admin/page.tsx` shells, `app/not-found.tsx`.
- `AppHeader` (`{ meta, active, variant?: "full" | "brand-only" }`, `role="banner"`): brand, facility line, `<nav aria-label="Main">` with the links and the `CountBadge`, display name, "Sign out"; the brand-only variant is used on `/login` (FEAT-063).
- `DataBar` (`{ meta }`) under the app bar on every page; `CountBadge` (`{ count, label }`, also used by FEAT-066 on "Review and notes").
- Chrome `meta` source: the protected layout reads `meta` from `GET /api/v1/config/ui` (`["config", "ui"]`, available to every role) so that the app bar and the data bar do not depend on the page's own query.
- Badge count from `GET /api/v1/alerts?status=open` (`total`), refreshed with the residents query.
- Document titles "<Page> – EchoWell", root skip link to `<main id="main">`, `<html lang="en">`.
- Environment ribbon when `NEXT_PUBLIC_APP_ENV` ≠ `production`.
- Access-denied state ("You do not have access to this page.", link "← Resident list") for `/admin` (non-admins) and `/study` (clinicians), rendered without calling the page APIs.
- `[residentCode]` validation against `^[A-Z0-9]{1,16}$` and `encodeURIComponent` use.

## Out of Scope

- Page bodies (FEAT-065..FEAT-074), including the chart's back link "← Resident list", banner and section navigation (FEAT-066) and the Study team header lines (UX-017, FEAT-072).
- Login and session (FEAT-063); API client, tokens and `StatusPill` (FEAT-062).
- The `/study#devices` anchor and its focus handling (FEAT-072).
- The wireframe's "Show wireframe notes" toggle (not a product feature).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-064-FR-01 | The application shall implement exactly the routes `/login`, `/`, `/residents`, `/residents/[residentCode]` with the sections `/review`, `/trends`, `/baseline`, `/log`, `/device`, `/admissions`, `/study`, `/admin`; `/` redirects to `/residents` with `redirect()`; all routes except `/login` and `/` are nested in `app/(protected)/`; there is no `/alerts`, `/analytics` or Devices route. | FE-020, FE-021, FE-022, D-110 |
| FEAT-064-FR-02 | Every signed-in page shall render `AppHeader` (`role="banner"`, `--chrome` background) with the brand "EchoWell" (20px, weight 700, `--chrome-ink`) and next to it the facility line "<meta.facility_name>, Assisted living" (14px, `--chrome-muted`, e.g. "Edgewood, Assisted living"); the facility name is never hard-coded and no other facility name (UX-166) appears. | UX-010, UX-011, UX-012, FE-023, FE-024, FR-330 |
| FEAT-064-FR-03 | The main navigation (`<nav aria-label="Main">`, right-aligned, wrapping) shall contain, in order, "Resident list" (`/residents`), "New admissions" (`/admissions`), "Study team" (`/study`, roles researcher and admin only) and "Admin" (`/admin`, role admin only); each link padding 8px 12px, radius 4px, weight 600, 15px, `--chrome-ink`. | UX-013, UX-014, UX-018, FE-028, FR-218, FR-330, SEC-043 |
| FEAT-064-FR-04 | The link of the current page shall have `aria-current="page"` and a background of white at 16 % opacity; the resident chart and its sections count as "Resident list". | UX-013, FE-027 |
| FEAT-064-FR-05 | When n = `total` of `GET /api/v1/alerts?status=open` (change alarms not yet reviewed; data alerts not counted) is greater than 0, "Resident list" shall be followed by a red count badge (`--red` background, white text, 13px, radius 999px) showing n, and the link's accessible name shall be "Resident list, <n> alarms not reviewed" ("Resident list, 1 alarm not reviewed"); test data: "2", after one review "1". While the count is loading or its request fails, no badge is shown and the link stays usable (D-97). | UX-018, FE-036, FR-330, D-97 |
| FEAT-064-FR-06 | After the navigation the app bar shall show the signed-in user's display name (14px, `--chrome-muted`) and a button "Sign out" (min-height 44px, `--chrome-ink` text, 1px solid `--chrome-muted` border) that calls `signOut` (FEAT-063). | FE-029, UX-015, D-111 |
| FEAT-064-FR-07 | Directly below the app bar every page, including `/login`, shall show `DataBar` (`--yellow-bg` background, `--yellow` text, 14px, weight 600, 1px solid `--yellow-edge` bottom border, padding 6px 20px): with `meta.pipeline_profile` `test_v0_1` "Test data only (<data source label>, <period>). No real residents. No audio is stored or played anywhere in EchoWell." (test data: "Test data only (pipeline test data v0.1, Oct 1–30, 2026). No real residents. No audio is stored or played anywhere in EchoWell."); otherwise, and while `meta` is not yet available, "No audio is stored or played anywhere in EchoWell." | UX-400, FE-208, FE-088, FR-138, BR-01, D-OWNER-4 |
| FEAT-064-FR-08 | Each page shall contain exactly one `<h1>` in its main content: "Residents in the study" on `/residents`, the resident code on the chart, "New admissions" on `/admissions`, "Study team: how the system is working" on `/study`, "Admin" on `/admin`, "EchoWell" on `/login`; the brand in the app bar is not a heading. | UX-010 |
| FEAT-064-FR-09 | Every page shall set the document title "<Page> – EchoWell": "Resident list – EchoWell", "<R> · <Section> – EchoWell" (e.g. "R09 · Summary – EchoWell", "R09 · Review and notes – EchoWell"), "New admissions – EchoWell", "Study team – EchoWell", "Admin – EchoWell", "Sign in – EchoWell"; `<html lang="en">`. | FE-032, UX-229 |
| FEAT-064-FR-10 | The root layout shall render "Skip to main content" as the first focusable element, targeting `<main id="main">`. | FE-033 |
| FEAT-064-FR-11 | A non-admin who opens `/admin` shall see "You do not have access to this page." and the link "← Resident list", with no admin API call and no redirect. | FE-034, UX-215, SEC-043 |
| FEAT-064-FR-12 | A clinician who opens `/study` shall see the same access-denied state and no Study team API call (analytics, data alerts, devices, CSV) shall be made (UX-350 rule, rendered with this state). | FE-037, FR-310, SEC-043 |
| FEAT-064-FR-13 | When any API call returns 403, the affected component shall show "You do not have access to this information." and not retry. | FE-035 |
| FEAT-064-FR-14 | The `[residentCode]` parameter shall be validated against `^[A-Z0-9]{1,16}$` (invalid → resident not-found state without an API call) and passed to the API with `encodeURIComponent`. | FE-030, FE-031 |
| FEAT-064-FR-15 | When `NEXT_PUBLIC_APP_ENV` is not `production`, a non-dismissable ribbon ("STAGING – synthetic data" for staging, "LOCAL" for local) shall render, 12px in `--font-mono`, at the top of `<body>` above the app bar. | ENV-032, FE-172 |

## Inputs

- `useAuth()` role and display name (FEAT-063); `meta` from `GET /api/v1/config/ui`; `GET /api/v1/alerts?status=open` total; `NEXT_PUBLIC_APP_ENV` via `lib/config.ts`.

## Outputs

- Route tree, `AppHeader`, `DataBar`, `CountBadge`, access-denied state, ribbon, skip link, document titles.

## Data Flow

Protected layout renders → `["config", "ui"]` query → `meta` → `AppHeader` (facility line) and `DataBar` (profile, data source label, period); `AppHeader` reads role and display name (`useAuth`) and the open-alarm total (`["alerts", {status: "open"}]`) → badge. `/admin` or `/study` → role check before any data hook → access-denied state.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-063

- FEAT-063 provides `useAuth()`, `signOut`, `AuthGuard` and `lib/roles.ts`; FEAT-062 (through FEAT-063) provides the API client, formatters, tokens and wording.

Features that build directly on this one (BACKLOG.md §4): FEAT-065, FEAT-066, FEAT-072, FEAT-073, FEAT-074.

## Database Impact

None.

## API Impact

Endpoints consumed: `GET /api/v1/config/ui` (E-32) for `meta`, `GET /api/v1/alerts?status=open` (E-13) for the badge; `POST /api/v1/auth/logout` (E-03) via `signOut`. None exposed.

## Frontend Impact

- Pages: route shells for `/residents`, `/residents/[residentCode]`, `/admissions`, `/study`, `/admin`; `app/page.tsx`; `app/layout.tsx` (skip link, ribbon, `lang`); `app/(protected)/layout.tsx` (app bar and data bar around the page).
- Components: `AppHeader`, `DataBar`, `CountBadge`; access-denied state.

## Analytics Impact

None.

## Security Requirements

- Admin link and `/admin` content only for admins; Study team link and page only for admin and researcher (SEC-043, FR-218). The backend enforces the same rules (403); the UI never relies on hiding alone.
- No admin or Study team API request is issued for a user without the role (FE-034, FR-310).
- Resident code validated before use in a URL (FE-030, FE-031).

## Error Handling

- Badge count loading or failure: no badge, link usable (UX-018, D-97).
- `config/ui` failure: the data bar shows "No audio is stored or played anywhere in EchoWell." and the facility line is omitted; page panels show their own errors (UX-202).
- 403 → inline "You do not have access to this information." (FE-035).
- Invalid resident code → not-found state (FE-030, UX-205).

## Logging Requirements

None in the frontend (LOG-082). The backend writes `access.denied` audit rows for 403s it returns (TRD 12 §4.12).

## Testing Requirements

- Component (`components/AppHeader/AppHeader.test.tsx`, TST-090): brand, facility line "Edgewood, Assisted living" from the DS-07 `meta`, nav order per role (clinician: Resident list, New admissions; researcher: + Study team; admin: + Study team, Admin), `aria-current` on the chart route, badge "2" with accessible name "Resident list, 2 alarms not reviewed", singular form for 1, no badge while loading or on error, Sign out.
- Component (`components/DataBar/DataBar.test.tsx`): test-data sentence with the DS-07 `meta`, production sentence, sentence without `meta`.
- Page tests: `/admin` as clinician and researcher, `/study` as clinician → access-denied with "← Resident list", no MSW request to admin or Study team endpoints (TST-094); one `<h1>` per route; document titles.
- E2E: E2E-01 (nav and data bar after login), E2E-14 (`/admin` as clinician), E2E-21 clinician part (`/study` refused, nav item hidden), FE-188 researcher `/admin` access denied.

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-064-AC-01 | As clinician, `/admin` shows "You do not have access to this page." with "← Resident list", no admin API request is made, and the nav has no "Admin" link. | E2E-14; FE-034; UX-215 |
| FEAT-064-AC-02 | As clinician, the nav has no "Study team" link and `/study` shows the access-denied state with no `GET /api/v1/analytics` request. | E2E-21; FR-218; FR-310 |
| FEAT-064-AC-03 | With DS-07, every signed-in page shows the app bar "EchoWell" / "Edgewood, Assisted living", the nav "Resident list" with badge "2", "New admissions" for a clinician, plus "Study team" for a researcher and "Study team" and "Admin" for an admin, and the data bar "Test data only (pipeline test data v0.1, Oct 1–30, 2026). No real residents. No audio is stored or played anywhere in EchoWell." Verified by: Component (`AppHeader.test.tsx`, `DataBar.test.tsx`) and E2E-01. | UX-011; UX-013; UX-014; UX-018; UX-400 |
| FEAT-064-AC-04 | `/` redirects to `/residents`; on `/residents/R09/trends` the "Resident list" link carries `aria-current="page"`. Verified by: Page test (TST-094). | FE-021; UX-013 |
| FEAT-064-AC-05 | Document titles equal FEAT-064-FR-09 on each route, each route has exactly one `<h1>` with the UX-010 text, and "Skip to main content" is the first focusable element. Verified by: Page test (TST-094). | UX-010; UX-229; FE-033 |
| FEAT-064-AC-06 | `/residents/r09!` renders the resident not-found state without any API request. Verified by: Page test (TST-094). | FE-030 |
| FEAT-064-AC-07 | With `NEXT_PUBLIC_APP_ENV=staging` the ribbon "STAGING – synthetic data" is visible; with `production` no ribbon renders. Verified by: Component (`AppHeader.test.tsx`; TST-090). | ENV-032; FE-172 |
| FEAT-064-AC-08 | With a production-profile `meta` the data bar reads only "No audio is stored or played anywhere in EchoWell." Verified by: Component (`DataBar.test.tsx`). | UX-400; AC-UX-10 |

## Definition of Done

- All FEAT-064 acceptance criteria pass; component, page and E2E tests listed above green.
- The batch report lists the implemented requirement IDs (AGT-022).

## Implementation Notes

- A clinician's nav has no "Study team" link (FR-218, UX-018, SEC-043, E2E-21).
- There is no "Devices" navigation link (UX-016 retired); devices are on the Study team page (`/study#devices`, FEAT-072) and in each chart's Device section (FEAT-070).
- The v0.1 `AppHeader` titles and sublines ("Alert review", "Analytics", "Voice check-ins · …") and the v0.1 `BackLink` "← Back to all residents" are not built (UX-005, UX-180 retired; D-110).
- Data-bar period: the 30 facility-local days ending on the as-of date, formatted with the year ("Oct 1–30, 2026", UX-003); use the window value TRD 04 §4.11 names for it.
- Use `next/navigation` `redirect()` in `app/page.tsx` (FE-021).
