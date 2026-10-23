# EchoWell Frontend Architecture

Document: docs/design/Frontend_Architecture.md · Block 3 checkpoint 1, its own PR: GitHub PR #3 (Implement_Feature_Batches.md Phase 7, TRD 25 Phase 2) · Feature: FEAT-001 · Date: 21 October 2026 · Revised: 23 October 2026 (review round 1)

## 1. Purpose and sources

This document describes the Next.js dashboard that the Phase 3 scaffold (FEAT-004) and the Phase 8 frontend (FEAT-062..FEAT-076) build. It elaborates TRD 04 (FE) and TRD 11 (UX); the screen-level design, component hierarchy and the component → API → database mapping are in docs/design/UI_Architecture.md. API names are those of TRD 19 (TRD 04 §5: a name difference is resolved in favour of TRD 19).

| Topic | Source |
|---|---|
| Stack, layout, routes, rendering, auth, API client, state, components | TRD 04 §4.1–§4.16 (FE-001..FE-205) |
| Screens, copy, accessibility, responsive rules, expected test rendering | TRD 11 (UX-001..UX-384) |
| Endpoint contracts | TRD 19, docs/design/OpenAPI_Spec.md |
| Security headers, CSP | TRD 12 §4.9 |
| Frontend environment variables | TRD 21 §4.5 (ENV-030..ENV-033) |
| Pages decision | TRD 24 D-23 |

## 2. Technology

| Package | Pin | Purpose | Source |
|---|---|---|---|
| Node.js | 20 LTS | runtime | FE-002, AGT-024 |
| next | 14.2.x (App Router) | framework | FE-001, ARC-010 |
| react, react-dom | 18.3.x | UI | FE-003 |
| typescript | 5.x, `strict: true` | types | FE-001 |
| @tanstack/react-query | 5.x | all server state | FE-006 |
| recharts | 2.x | every chart (no other chart library) | FE-005 |
| openapi-typescript | 7.x (dev) | `lib/api-types.ts` from `docs/api_reference/openapi.json` | FE-012, OAS-014 |
| vitest, @vitest/coverage-v8, Testing Library, jsdom, msw | 2.x, 2.x, 16.x/14.x/6.x, 25.x, 2.x (dev) | unit, component, page tests | TRD 04 §4.1 |
| @playwright/test, @axe-core/playwright | 1.48+ / 4.x (dev) | E2E and accessibility | TRD 04 §4.1 |
| eslint (+ next, typescript-eslint, jsx-a11y), prettier | 8.x, 3.x (dev) | lint and format | FE-200, FE-201 |

No UI component library (CSS Modules and custom properties only), fonts self-hosted through `next/font/google` (IBM Plex Sans 400/600, IBM Plex Mono 400), no audio component, no LLM feature (FE-003, FE-004, FE-007, FE-008, AGT-004).

## 3. Source layout

```
frontend/
  app/
    layout.tsx                         root layout, fonts, <Providers>, skip link
    providers.tsx                      QueryClientProvider + AuthProvider
    page.tsx                           redirect "/" → "/residents"
    not-found.tsx, global-error.tsx
    login/page.tsx                     public
    (protected)/
      layout.tsx                       <AuthGuard>
      error.tsx                        route error boundary
      residents/page.tsx               Residents overview + Devices panel (#devices)
      residents/[residentCode]/page.tsx Resident detail
      alerts/page.tsx                  Alert review
      analytics/page.tsx               Analytics (admin, researcher)
      admissions/page.tsx              New admissions (experimental)
      admin/page.tsx                   Admin (admin)
  components/<Name>/<Name>.tsx, .module.css, .test.tsx
  lib/  auth.ts, AuthProvider.tsx, config.ts, format.ts, wording.ts, queryKeys.ts,
        deviceGroups.ts, roles.ts, api-types.ts (generated)
  services/api.ts                      the only HTTP client (existing skeleton file kept)
  styles/tokens.css, globals.css
  middleware.ts                        Cache-Control: private, no-store on protected pages
  tests/unit, tests/pages, tests/fixtures (ds07), tests/msw/handlers.ts, tests/e2e
```

The existing files `frontend/package.json`, `frontend/next.config.js` and `frontend/services/api.ts` are filled in, not replaced (FE-010, AGT-010).

## 4. Routes

Exactly the routes of TRD 04 §4.3 and TRD 24 D-23; no other page exists (FE-020). `/` only redirects.

| Route | File | Access | Wireframe | Content | Source |
|---|---|---|---|---|---|
| `/login` | `app/login/page.tsx` | public | none | sign-in form | UX-170..UX-176 |
| `/residents` (with `#devices`) | `app/(protected)/residents/page.tsx` | admin, clinician, researcher | SRC-09 (Main) | header, summary tiles, residents table, Devices panel | UX-010..UX-058 |
| `/residents/[residentCode]` | `app/(protected)/residents/[residentCode]/page.tsx` | admin, clinician, researcher | SRC-10 (Resident) | back link, header, What this means, tally chart, 7 measurements, staff review, check-in log | UX-060..UX-150 |
| `/admissions` | `app/(protected)/admissions/page.tsx` | admin, clinician, researcher | SRC-11 (Admission) | experimental banner, admissions table, facility-range comparison | UX-180..UX-195 |
| `/alerts` | `app/(protected)/alerts/page.tsx` | admin, clinician, researcher (review: admin, clinician) | SRC-18 (Alerts) | change-alarm queue, data-alert queue, review panel | UX-300..UX-331 |
| `/analytics` | `app/(protected)/analytics/page.tsx` | admin, researcher | SRC-19 (Analytics) | KPI tiles, daily chart, funnel, by-resident, alarm timing or review outcomes | UX-350..UX-384 |
| `/admin` | `app/(protected)/admin/page.tsx` | admin | none | Users, Pipeline runs, Upload data tabs | UX-210..UX-219 |

### 4.1 Route → endpoint map

Endpoint IDs of TRD 19 §4.3; client functions of TRD 04 §4.6.2. Every route calls at least one endpoint.

| Route | Endpoints called | Client functions | When |
|---|---|---|---|
| `/login` | E-02 POST /auth/login; E-04 GET /auth/me | `login`, `getMe` | sign in; then load the user (FE-054) |
| `/residents` | E-08 GET /residents; E-17 GET /devices; E-13 GET /alerts?status=open (nav count); E-04 GET /auth/me; E-03 POST /auth/logout | `getResidents({sort})`, `getDevices`, `getAlerts({status:"open"})`, `getMe`, `logout` | page load, sort change, 5-minute refresh (FE-081); sign out |
| `/residents/[residentCode]` | E-09 GET /residents/{code}; E-12 GET /scores?resident_code=&epoch=; E-11 GET /residents/{code}/features; E-10 GET /residents/{code}/checkins; E-15 GET /residents/{code}/notes; E-16 POST /residents/{code}/notes; E-13 GET /alerts?resident_code= (open alarm); E-32 GET /config/ui and E-14 POST /alerts/{id}/reviews (review dialog); no E-28 call (no latest-review line, SRC-10 wireframe, D-102) | `getResident`, `getScores`, `getFeatures`, `getCheckins`, `getNotes`, `createNote`, `getAlerts`, `getUiConfig`, `createAlertReview` | five reads in parallel (FE-087); note save; "Mark as reviewed" dialog |
| `/admissions` | E-22 GET /admissions; E-23 GET /admissions/{code}/comparison; E-24 GET /facility/reference-ranges | `getAdmissions`, `getAdmissionComparison`, `getReferenceRanges` | page load; row selection |
| `/alerts` | E-13 GET /alerts; E-30 GET /data-alerts; E-12 GET /scores?resident_code= (mini chart); E-28 GET /alerts/{id}/reviews; E-14 POST /alerts/{id}/reviews; E-29 POST /alerts/{id}/snooze; E-32 GET /config/ui; E-04, E-03 (header) | `getAlerts`, `getDataAlerts`, `getScores`, `getAlertReviews`, `createAlertReview`, `snoozeAlert`, `getUiConfig`, `getMe`, `logout` | page load; card selection (`?alert=<id>`); save review; remind me |
| `/analytics` | E-18 GET /analytics; E-12 GET /scores (`Accept: text/csv`); E-19 GET /analytics/baselines (`Accept: text/csv`); E-13 (nav count); E-04, E-03 | `getAnalytics`, `downloadScoresCsv`, `downloadBaselinesCsv`, `getAlerts`, `getMe`, `logout` | page load; Downloads row |
| `/admin` | E-25 GET /users; E-26 POST /users; E-27 PATCH /users/{id}; E-31 GET /pipeline/runs; E-20 POST /pipeline/run; E-21 GET /pipeline/runs/{id}; E-06 POST /ingest (multipart); E-07 GET /ingest/batches/{id}; E-01 GET /health; E-13 (nav count); E-04, E-03 | `listUsers`, `createUser`, `updateUser`, `listPipelineRuns`, `triggerPipelineRun`, `getPipelineRun`, `uploadIngestCsv`, `getIngestBatch`, `getHealth`, `getAlerts`, `getMe`, `logout` | tabs Users, Pipeline runs (status refreshed every 5 s while running, UX-212), Upload data; "Nightly run missing" banner from E-31 with `trigger=nightly&status=succeeded&limit=1` (UX-219, D-96) |

Endpoints with no browser caller: E-05 POST /sessions (devices only).

### 4.2 Page hierarchy

```mermaid
flowchart TB
  ROOT["/ (redirect)"] --> RES
  LOGIN["/login (public)"] -->|"sign-in, valid next or /residents"| RES
  subgraph PROTECTED["app/(protected) — AuthGuard"]
    RES["/residents<br/>Residents overview"] --> DEV["#devices<br/>Devices panel (same page)"]
    RES -->|"Open"| DET["/residents/[residentCode]<br/>Resident detail"]
    DET -->|"← Back to all residents"| RES
    RES -->|"nav New admissions"| ADM["/admissions<br/>New admissions (experimental)"]
    ADM -->|"← Back to all residents"| RES
    RES -->|"nav Alerts (n)"| AL["/alerts<br/>Alert review"]
    AL -->|"Open full resident view →"| DET
    AL -->|"device data alert"| DEV
    RES -->|"nav Analytics (admin, researcher)"| AN["/analytics<br/>Analytics"]
    RES -->|"nav Admin (admin)"| ADMIN["/admin<br/>Admin"]
    DET -->|"Mark as reviewed"| DLG["ReviewDialog (modal, same form as /alerts)"]
  end
  PROTECTED -. "no or expired token" .-> LOGIN
```

## 5. Rendering, authentication and authorisation

| Rule | Design | Source |
|---|---|---|
| Client-side data | protected pages are client components fetching with TanStack Query; no protected data in server components, route handlers or at build time | FE-040 |
| Server-capable build | Netlify Next.js runtime (interim), Amplify SSR (target); no `output: "export"`; no Netlify-specific APIs | FE-041, FE-044, ARC-093 |
| No caching of protected pages | `Cache-Control: private, no-store` via `middleware.ts`; query cache in memory only | FE-042, FE-045 |
| Token storage | memory + `sessionStorage["echowell.auth"]`; never `localStorage`, cookies, URLs, logs | FE-050, FE-051 |
| Session expiry | sign-out at `exp`; any 401 clears token and cache and redirects to `/login?reason=expired&next=…` | FE-052, FE-056 |
| Open-redirect guard | `next` must start with a single `/` | FE-057 |
| Role helpers | `canWriteNotes`, `canReviewAlarms` (admin, clinician); `isAdmin`; `canSeeAnalytics` (admin, researcher) in `lib/roles.ts` | FE-059, SEC-043 |
| Access denied | non-admin on `/admin` and clinician on `/analytics` see "You do not have access to this page." without calling the API; any 403 renders "You do not have access to this information." | FE-034, FE-035, FE-037 |
| Browser hardening | CSP of TRD 12 §4.9 set by `netlify.toml` (not in `middleware.ts`); no `dangerouslySetInnerHTML`; no third-party scripts | FE-060..FE-064 |

```mermaid
sequenceDiagram
  participant U as User
  participant FE as Next.js (browser)
  participant API as FastAPI /api/v1
  U->>FE: email + password on /login
  FE->>API: POST /auth/login (E-02)
  API-->>FE: 200 Token {access_token, expires_in, user}
  FE->>FE: store token (memory + sessionStorage), schedule sign-out at exp
  FE->>API: GET /auth/me (E-04)
  FE->>U: navigate to next or /residents
  API-->>FE: 401 on any later call
  FE->>FE: clear token, cancel queries, clear cache
  FE->>U: /login?reason=expired&next=<path>
```

## 6. API client (`frontend/services/api.ts`)

| Rule | Source |
|---|---|
| URL = `${NEXT_PUBLIC_API_BASE_URL}/api/v1<path>`, base read only in `lib/config.ts` | FE-070, ENV-030 |
| Headers: `Accept: application/json`, `Authorization: Bearer <token>`, `X-Request-ID: crypto.randomUUID()` | FE-071 |
| Timeouts 15 s (CSV upload 120 s) | FE-072 |
| Problem documents become `ApiError {status, code, title, detail, requestId, errors}`; network failure `status: 0` | FE-073, FE-074 |
| Forms map `errors[].field` to controls; logic branches on `code` only | FE-079, UX-207 |
| One typed function per endpoint, types from `lib/api-types.ts` | FE-075, FE-011 |
| Lists for overview, devices and admissions request `limit=500&offset=0` and show "Showing <n> of <total> residents." when truncated | FE-076, UX-041 |
| `meta` is the only source of facility name, time zone, data source label, as-of, `baseline_n`, `cusum_h`, profile; nothing hard-coded | FE-077, UX-007, UX-012 |

| Client function | Endpoint |
|---|---|
| `login`, `logout`, `getMe` | E-02, E-03, E-04 |
| `getUiConfig` | E-32 |
| `getResidents`, `getResident`, `getCheckins`, `getFeatures` | E-08, E-09, E-10, E-11 |
| `getScores`, `downloadScoresCsv` | E-12 |
| `getAlerts`, `getAlertReviews`, `createAlertReview`, `snoozeAlert` | E-13, E-28, E-14, E-29 |
| `getDataAlerts` | E-30 |
| `getNotes`, `createNote` | E-15, E-16 |
| `getDevices` | E-17 |
| `getAnalytics`, `downloadBaselinesCsv` | E-18, E-19 |
| `triggerPipelineRun`, `getPipelineRun`, `listPipelineRuns` | E-20, E-21, E-31 |
| `getAdmissions`, `getAdmissionComparison`, `getReferenceRanges` | E-22, E-23, E-24 |
| `listUsers`, `createUser`, `updateUser` | E-25, E-26, E-27 |
| `uploadIngestCsv`, `getIngestBatch` | E-06, E-07 |
| `getHealth` | E-01 |

## 7. State management

| Kind | Holder | Examples | Source |
|---|---|---|---|
| Server state | TanStack Query cache (memory only) | residents, resident detail, scores, features, check-ins, notes, devices, alerts, data alerts, analytics, admissions, admin lists | FE-006, FE-045 |
| Auth state | `AuthProvider` context + `lib/auth.ts` | token, user, role | FE-050..FE-054 |
| URL state | `useSearchParams` | `?sort=` on `/residents`, `?alert=` on `/alerts`, `?tab=` on `/admin` | FE-082, FE-139, UX-210 |
| Local UI state | `useState` | note draft and type, review form, disclosures, dialog open | FE-089 |

No Redux or Zustand. QueryClient defaults: `staleTime` 60 s, `gcTime` 300 s, refetch on focus, retry at most 2 times only for status 0 or ≥ 500 (FE-080); overview, devices and detail refetch every 5 minutes while visible (FE-081).

```mermaid
flowchart LR
  subgraph Keys["lib/queryKeys.ts"]
    K1["['residents', {sort}]"]
    K2["['resident', code] plus 'checkins', 'features', ('scores', epoch) or 'notes'"]
    K3["['alerts', {status, residentCode}] and ['alerts', id, 'reviews']"]
    K4["['data-alerts', {status}]"]
    K5["['analytics']"]
    K6["['devices'], ['admissions'], ['reference-ranges'], ['admin', ...], ['me']"]
  end
  NOTE["createNote success"] -->|"invalidate"| K2
  NOTE -->|"invalidate"| K1
  NOTE -->|"invalidate"| K3
  REV["createAlertReview / snoozeAlert success"] -->|"invalidate"| K3
  REV -->|"invalidate"| K4
  REV -->|"invalidate"| K2
  REV -->|"invalidate"| K1
  REV -->|"invalidate"| K5
```

Invalidation rules: FE-085 (after a note) and FE-086 (after a review or snooze). After a review the UI renders the state returned by the API on refetch; it never changes the badge, tally or chart itself (FE-134, OQ-05).

## 8. Shared libraries

| Module | Responsibility | Source |
|---|---|---|
| `lib/format.ts` | every date, time and number in `meta.facility_tz` (`formatDateTimeShort`, `formatAsOf`, `formatLocalDate`, `formatLocalDateRange`, `formatTally`, `formatSigned`, `formatCounts30d`); local dates never parsed with `new Date("YYYY-MM-DD")` | FE-150..FE-154, ARC-055 |
| `lib/wording.ts` | every clinical or plain-language template (status labels, What this means, chart summaries); `CLINICAL_WORDING_APPROVED = false` appends "[Final clinical wording: confirm with PI]" | FE-013, UX-073, OQ-12, D-18 |
| `lib/deviceGroups.ts` | `compressDeviceCodes()` natural sort and en-dash runs ("D01, D04–D06, D08–D10") | FE-102 |
| `lib/roles.ts` | role helpers | FE-059 |
| `lib/config.ts` | the only reader of `NEXT_PUBLIC_*` variables; build fails on a missing or non-HTTPS staging/production API URL | ENV-030, FE-171 |
| `styles/tokens.css` | colour, font and spacing tokens; no hex literals in component CSS | FE-160 |

## 9. Loading, empty and error states

Each data section renders `SectionState` (loading with `role="status"`, error with "Try again" and "Reference: <request_id>", empty copy of TRD 11 UX-204); a failing section never blanks the others; a 404 resident renders only the not-found state; cached data after a failed refresh shows "Could not refresh. Showing data as of <as-of>." (FE-140..FE-145, UX-200..UX-206).

## 10. Environment variables

| Variable | Use | Source |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | API origin (no path); also in CSP `connect-src` | FE-170, ENV-030 |
| `NEXT_PUBLIC_APP_ENV` | `local`, `staging`, `production`, `test`; ribbon "STAGING – synthetic data" or "LOCAL" outside production | FE-172, ENV-032 |
| `NEXT_PUBLIC_GIT_SHA` | derived in `next.config.js` from `COMMIT_REF` or `GIT_SHA` | ENV-033 |

No secret is referenced from frontend code (FE-173, ENV-031).

## 11. Build, lint and test

| Script | Command | Source |
|---|---|---|
| `lint` | `next lint --max-warnings 0` | FE-200, CIC-017 |
| `typecheck` | `tsc --noEmit` | FE-202 |
| `format:check` | `prettier --check .` | FE-201 |
| `test`, `test:coverage` | `vitest run` with line coverage ≥ 80 % | FE-180, TST-142, D-39 |
| `build` | `next build`; first-load JS ≤ 300 kB per route | FE-203, FE-204 |
| `test:e2e:readonly`, `test:e2e:mutating`, `test:e2e:isolated` | Playwright groups (D-73) | TRD 04 §4.15, TST-100 |
| `gen:api` | `openapi-typescript ../docs/api_reference/openapi.json -o lib/api-types.ts` | FE-012 |
| `fixtures:capture` | DS-07 JSON fixtures from the local stack | TRD 04 §4.14 |

Test levels and the E2E scenario list are in docs/design/Testing_Architecture.md.

## 12. Privacy and safety rules in the UI

- Residents are study IDs only; no names, photos or rooms (UX-001, FE-068, AGT-017).
- No audio player, waveform or audio link on any page; footer "No audio is stored or played here — only extracted voice measurements." (UX-005, UX-006, FE-007).
- Wording says "detects a change" and "a prompt to check in, not a diagnosis"; forbidden stems of UX-161 never appear (AGT-018, UX-160..UX-166).
- Facility named only from `meta.facility_name`; "Edge4Care" never appears (UX-012, AGT-019).
- No EWMA chart (OQ-18); no control to edit, reset or delete baselines, scores, tallies, alarms or records (UX-009).
- No request to any host other than the frontend origin and the API origin (FE-192).

## 13. Open questions affecting the frontend

| ID | Effect |
|---|---|
| OQ-05 | Review marks "Reviewed" only; badge, tally and chart unchanged; note shown on detail and alerts pages. |
| OQ-08, OQ-29 | `/admissions` stays experimental; v0.1 renders the empty state. |
| OQ-12 | Wording behind `CLINICAL_WORDING_APPROVED`. |
| OQ-13 | Alarm line value rendered from `meta.cusum_h`. |
| OQ-18 | No EWMA display. |
| OQ-25 | Explanation checklist from E-32. |
| OQ-28 | Earlier-epoch view: interim "Device period" select above the tally chart (TRD 24 OQ-28 interim decision, FEAT-067). |
