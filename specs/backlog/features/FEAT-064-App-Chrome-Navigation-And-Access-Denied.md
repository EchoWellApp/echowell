# FEAT-064 App chrome, navigation and access-denied states

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

Provide the page frame that all dashboard pages share: the exact route tree, the `/` redirect, the global `AppHeader` with title, subline and role-aware navigation ("Residents", "Alerts (n)", "Analytics", "New admissions", plus "Admin" for admins), the `BackLink` on pages without global navigation, document titles, the skip link, the non-production environment ribbon, and the access-denied states for `/admin` and `/analytics`. Page content is delivered by the page features.

## Business Context

- BR-12, BR-13: staff move between overview, alerts, analytics and resident detail with consistent chrome (SRC-09, SRC-10, SRC-11, SRC-18, SRC-19, D-31).
- BR-16: admin and analytics areas are visible and reachable only to the permitted roles.
- D-23: exactly five wireframe pages plus `/login` and `/admin`.
- FRs covered (BACKLOG.md): FR-218, FR-310, FR-330, FR-331.

## Referenced TRDs

- TRD 04 FE-020..FE-037 (routes, `/` redirect, protected group, header pages, titles, BackLink pages, `#devices` anchor, active link, Admin and Analytics link rules, display name and Sign out, resident code validation and encoding, document titles, skip link, `/admin` access denied, 403 inline message, "Alerts (n)" count, `/analytics` access denied for clinicians), §4.3 route table and flow, §4.8 `AppHeader`, `BackLink`.
- TRD 11 UX-010..UX-018 (header title, `<h1>` rules, sublines, facility name, nav order and styles, Admin link, user name and Sign out, `#devices` focus, Alerts count and Analytics visibility), UX-215, UX-350.
- TRD 12 SEC-043 (role-dependent visibility).
- TRD 21 ENV-032 (staging and local ribbon); TRD 04 FE-172.
- TRD 02 FR-218, FR-310, FR-330, FR-331; TRD 24 D-23, D-31.
- TRD 13 E2E-01, E2E-14, E2E-21; FE-188.

## Scope

- Route files: `app/page.tsx` (redirect), `app/(protected)/{residents,residents/[residentCode],admissions,alerts,analytics,admin}/page.tsx` shells, `app/login/page.tsx` (from FEAT-063), `app/not-found.tsx`.
- `AppHeader` (`{ meta, active }`) on `/residents`, `/alerts`, `/analytics`, `/admin`: titles, sublines, navigation with active state, "Alerts (n)" from `GET /alerts?status=open`, role-dependent "Analytics" and "Admin", display name, "Sign out".
- `BackLink` (`{ href? }`) "← Back to all residents" on `/residents/[residentCode]` and `/admissions`, preserving the last `?sort=`.
- Document titles "<Page> – EchoWell", root skip link to `<main id="main">`, `<html lang="en">`.
- Environment ribbon when `NEXT_PUBLIC_APP_ENV` ≠ `production`.
- Access-denied state component for `/admin` (non-admins) and `/analytics` (clinicians), rendered without calling the page APIs.
- `[residentCode]` validation against `^[A-Z0-9]{1,16}$` and `encodeURIComponent` use.

## Out of Scope

- Page bodies (FEAT-065..FEAT-074).
- Login and session (FEAT-063); API client (FEAT-062).
- The subline content specific to a page beyond the templates here is built from `meta` by this component; data loading for the page bodies is owned by the page features.

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-064-FR-01 | The application shall implement exactly the routes `/login`, `/`, `/residents` (with `#devices`), `/residents/[residentCode]`, `/admissions`, `/admin`, `/alerts`, `/analytics`; `/` redirects to `/residents` with `redirect()`; all routes except `/login` and `/` are nested in `app/(protected)/`. | FE-020, FE-021, FE-022, D-23 |
| FEAT-064-FR-02 | `/residents`, `/alerts`, `/analytics` and `/admin` shall render `AppHeader` with title "EchoWell", "Alert review", "Analytics", "Admin" respectively (28px, 600); on `/residents` the `<h1>` is the visually hidden text "Residents", elsewhere the title is the `<h1>`. | FE-023, FE-024, UX-010, FR-330, D-31 |
| FEAT-064-FR-03 | Sublines: `/residents` "Voice check-ins · <facility_name> · Showing <data_source_label> as of <Mon D, YYYY, h:mm AM/PM TZ>"; `/alerts` "For the charge nurse or clinical lead · <data_source_label> as of <Mon D, YYYY>"; `/analytics` "For the study team · <data_source_label>, <period> · numbers match the pipeline answer key" with the last clause only when `meta.pipeline_profile` is `test_v0_1`; values from `meta` only, facility never hard-coded. | UX-011, UX-012, UX-017, FE-088 |
| FEAT-064-FR-04 | The navigation shall contain, in order, "Residents", "Alerts (<n>)", "Analytics", "New admissions", plus "Admin" after "New admissions" for role admin; "Analytics" renders only for admin and researcher. | FE-023, FE-028, UX-013, UX-014, UX-018, FR-218, SEC-043 |
| FEAT-064-FR-05 | The current route's link shall carry `aria-current="page"` with a 2px solid ink border and weight 600; others a 1px solid `--color-border` border; padding 12px 16px on white. | FE-027, UX-013 |
| FEAT-064-FR-06 | n in "Alerts (<n>)" shall be `total` of `GET /api/v1/alerts?status=open` (change alarms not yet reviewed; data alerts not counted), refreshed with the residents query (test data: 2; after one review: 1). | FE-036, UX-018, FR-330 |
| FEAT-064-FR-07 | The header shall show the signed-in user's display name (14px secondary) and a "Sign out" button (min-height 44px) that calls `signOut` (FEAT-063). | FE-029, UX-015 |
| FEAT-064-FR-08 | `/residents/[residentCode]` and `/admissions` shall start with `BackLink` "← Back to all residents" to `/residents` (keeping the last `?sort=`) and shall not render `AppHeader`. | FE-025, UX-060, UX-180, FR-331 |
| FEAT-064-FR-09 | Loading `/residents#devices` shall scroll to `<section id="devices">` and move focus to its heading "Devices"; there is no "Devices" navigation link. | FE-026, UX-016 |
| FEAT-064-FR-10 | Every page shall set the document title "Residents – EchoWell", "R09 – EchoWell" (resident code), "Alert review – EchoWell", "Analytics – EchoWell", "New admissions – EchoWell", "Admin – EchoWell", "Sign in – EchoWell". | FE-032, UX-229 |
| FEAT-064-FR-11 | The root layout shall render "Skip to main content" as the first focusable element, targeting `<main id="main">`, and declare `lang="en"`. | FE-033, UX-229 |
| FEAT-064-FR-12 | A non-admin who opens `/admin` shall see "You do not have access to this page." and the link "Back to all residents", with no admin API call and no redirect. | FE-034, UX-215, SEC-043 |
| FEAT-064-FR-13 | A clinician who opens `/analytics` shall see the same access-denied state and no analytics API call shall be made. | FE-037, UX-350, FR-310 |
| FEAT-064-FR-14 | When any API call returns 403, the affected component shall show "You do not have access to this information." and not retry. | FE-035 |
| FEAT-064-FR-15 | The `[residentCode]` parameter shall be validated against `^[A-Z0-9]{1,16}$` (invalid → resident not-found state without an API call) and passed to the API with `encodeURIComponent`. | FE-030, FE-031 |
| FEAT-064-FR-16 | When `NEXT_PUBLIC_APP_ENV` is not `production`, a non-dismissable ribbon ("STAGING – synthetic data" for staging, "LOCAL" for local) shall render in IBM Plex Mono 12px at the top of `<body>`. | ENV-032, FE-172 |

## Inputs

- `useAuth()` role and display name (FEAT-063); `meta` from the page's main query; `GET /api/v1/alerts?status=open` total; `NEXT_PUBLIC_APP_ENV` via `lib/config.ts`.

## Outputs

- Route tree, `AppHeader`, `BackLink`, access-denied component, ribbon, skip link, document titles.

## Data Flow

Protected page renders → `AppHeader` reads role (useAuth), `meta` (page query) and open-alarm total (`["alerts", {status: "open"}]` query) → renders title, subline, nav. `/admin` or `/analytics` → role check before any data hook → access-denied state.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-063

- FEAT-063 provides `useAuth()`, `signOut`, `AuthGuard` and `lib/roles.ts`; FEAT-062 (through FEAT-063) provides the API client and formatters.

## Database Impact

None.

## API Impact

Endpoints consumed: `GET /api/v1/alerts?status=open` (E-13) for the count; `POST /api/v1/auth/logout` (E-03) via `signOut`. None exposed.

## Frontend Impact

- Pages: route shells for all seven routes, `app/page.tsx`, `app/layout.tsx` (skip link, ribbon, `lang`).
- Components: `AppHeader`, `BackLink`, access-denied view (used by `/admin` and `/analytics`).

## Analytics Impact

None.

## Security Requirements

- Admin link and `/admin` content only for admins; Analytics link and page only for admin and researcher (SEC-043, FR-218). The backend enforces the same rules (403); the UI never relies on hiding alone.
- No admin or analytics API request is issued for a user without the role (FE-034, FE-037).
- Resident code validated before use in a URL (FE-030, FE-031).

## Error Handling

- Count query failure: the TRDs do not define the link text for this case; keep the last known count from the cache (FE-144 pattern) and let the page sections show their own errors (see Implementation Notes).
- 403 → inline "You do not have access to this information." (FE-035).
- Invalid resident code → not-found state (FE-030, UX-205).

## Logging Requirements

None in the frontend (LOG-082). Backend writes `access.denied` audit rows for 403s it returns (TRD 12 §4.12).

## Testing Requirements

- Component (`components/AppHeader/AppHeader.test.tsx`): titles per page, sublines with the DS-07 `meta` ("Voice check-ins · Edgewood · Showing pipeline test data v0.1 as of Oct 30, 2026, 3:00 PM CT"; analytics clause only for `test_v0_1`), nav order, `aria-current`, Admin only for admin, Analytics hidden for clinician, "Alerts (2)" (TST-090).
- Page tests: `/admin` as clinician and researcher, `/analytics` as clinician → access-denied, no MSW request to admin/analytics endpoints (TST-094).
- E2E: E2E-14 (`/admin` as clinician), E2E-21 clinician part (`/analytics` refused, nav item hidden), FE-188 researcher `/admin` access denied.

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-064-AC-01 | As clinician, `/admin` shows "You do not have access to this page." with "Back to all residents", no admin API request is made, and the nav has no "Admin" link. | E2E-14; FE-034; UX-215 |
| FEAT-064-AC-02 | As clinician, the nav has no "Analytics" link and `/analytics` shows the access-denied state with no `GET /api/v1/analytics` request. | E2E-21; FE-037; FR-218 |
| FEAT-064-AC-03 | With DS-07, the `/residents` header shows "EchoWell", the subline "Voice check-ins · Edgewood · Showing pipeline test data v0.1 as of Oct 30, 2026, 3:00 PM CT" and the nav "Residents", "Alerts (2)", "New admissions" for a clinician, plus "Analytics" for a researcher and "Analytics" and "Admin" for an admin. | UX-011; UX-013; UX-014; FE-036 |
| FEAT-064-AC-04 | `/` redirects to `/residents`; `/residents/R09` and `/admissions` show "← Back to all residents" and no global nav. | FE-021; FE-025; FR-331 |
| FEAT-064-AC-05 | Document titles equal FE-032 on each route and "Skip to main content" is the first focusable element. | FE-032; FE-033 |
| FEAT-064-AC-06 | `/residents/r09!` renders the resident not-found state without any API request. | FE-030 |
| FEAT-064-AC-07 | With `NEXT_PUBLIC_APP_ENV=staging` the ribbon "STAGING – synthetic data" is visible; with `production` no ribbon renders. | ENV-032; FE-172 |

## Definition of Done

- All FEAT-064 acceptance criteria pass; component, page and E2E tests listed above green.
- Batch report lists IDs and the TRD conflicts below (AGT-022).

## Implementation Notes

- TRD conflict: TRD 13 E2E-01 expects a clinician's nav to include "Analytics", while FR-218, FE-028, UX-018, SEC-043 and E2E-21 hide it for clinicians. Implement the role rule (four requirements agree) and report E2E-01 for correction.
- TRD conflict: TRD 02 FR-150 still mentions a header nav "Devices", retired by contract §20 R2 (FE-026, UX-016); do not render a Devices link.
- The header error case for a failed count query is not defined by the TRDs; keep the last value or render "Alerts" and raise an OQ (AGT-009) if reviewers need a defined text.
- Use `next/navigation` `redirect()` in `app/page.tsx` (FE-021).
