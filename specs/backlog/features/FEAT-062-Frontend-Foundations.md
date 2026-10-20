# FEAT-062 Frontend foundations (API client, generated types, query cache, formatting, wording, tokens, section states)

| Field | Value |
|---|---|
| Epic | Frontend |
| Build phase | Phase 8 (TRD 25) |
| Priority | P0 |
| Complexity | High |
| MVP status | Required |
| Dependencies | FEAT-004, FEAT-038, FEAT-060 |
| Status | Not Started |

## Purpose

Build the shared frontend layer every page uses: the single typed API client `frontend/services/api.ts`, the generated contract types `frontend/lib/api-types.ts`, the TanStack Query client and query keys, the facility-time-zone formatters `lib/format.ts`, the wording module `lib/wording.ts` with the PI-confirmation marker, design tokens and base styles, the `SectionState` loading/empty/error component, the error boundaries, and the captured DS-07 test fixtures with MSW handlers. Work starts only after the R01–R10 validation suite passes (AGT-023).

## Business Context

- BR-12, BR-13 (staff read the dashboard correctly): uniform dates in facility time, uniform states and plain-language wording.
- BR-16 (privacy and security): one HTTP module, no third-party scripts, escaped API text, in-memory cache.
- BR-18 (detection, not diagnosis): all clinical wording lives in one PI-reviewed module (D-18, OQ-12).
- BR-15: fixtures are captured from the real pipeline output, never from workbook values (TDV-016).
- FRs covered (BACKLOG.md): none directly (enabling feature).

## Referenced TRDs

- TRD 04 FE-013 (wording only in `lib/wording.ts`), FE-040..FE-045 (client-side fetching, server-capable build, no-store, next.config, standard Next.js only, in-memory cache), FE-062..FE-068 (no dangerous HTML, escaped text, no third-party script, npm audit, form autocomplete attributes, safe error messages, no PII), FE-070..FE-080 (URL building, headers, timeouts, problem+json `ApiError`, network errors, typed functions, `limit=500`, `meta`-only facility values, unknown-field tolerance, form error mapping, query defaults), FE-140..FE-145 (section states, error copy, not-found, empty copy, stale notice, error boundaries), FE-150..FE-154 (format functions), FE-160, FE-161 (tokens, base layout), §4.2 layout, §4.6.2 client functions, §4.6.3 type aliases, §4.7 query keys, §4.11 format table, §4.12 tokens, §4.14 fixtures.
- TRD 11 UX-001..UX-009 (global conventions), UX-160..UX-166 (wording rules), UX-200..UX-207 (states), UX-250, UX-251 (tokens, glyphs only).
- TRD 17 LOG-032 (request ID, "Reference:"), LOG-080..LOG-083 (boundaries, error mapping, no telemetry, per-panel states).
- TRD 12 SEC-076 (API text as text nodes).
- TRD 19 OAS-014; TRD 14 TDV-016; TRD 13 TST-063, TST-094, TST-095, TST-097, TST-142.
- TRD 25 AGT-018, AGT-023; TRD 24 D-18, D-51, D-65.
- TRD 04 FE-090, FE-091 (component props interfaces; presentational components do not fetch).

## Scope

- `frontend/services/api.ts`: one typed function per endpoint of TRD 04 §4.6.2, base URL from `frontend/lib/config.ts`, headers, timeouts, `ApiError`, 401 handling hook (redirect logic wired by FEAT-063), CSV download helpers.
- `npm run gen:api` → `frontend/lib/api-types.ts` (generated, never hand-edited) and the alias module of TRD 04 §4.6.3.
- `frontend/app/providers.tsx` with `QueryClientProvider`; `frontend/lib/queryKeys.ts`.
- `frontend/lib/format.ts` (`formatDateTimeShort`, `formatAsOf`, `formatLocalDate`, `formatLocalDateRange`, `formatTally`, `formatSigned`, `formatCounts30d`).
- `frontend/lib/wording.ts` (status labels via `statusLabel()`, "What this means" templates, `cusumSummary()`, footers, review disclaimer, `CLINICAL_WORDING_APPROVED = false` with marker " [Final clinical wording: confirm with PI]").
- `frontend/lib/deviceGroups.ts` `compressDeviceCodes()` (used by FEAT-065).
- `frontend/styles/tokens.css` and `globals.css`; root layout base styles.
- `components/SectionState/`, `components/Footer/`; `app/(protected)/error.tsx`, `app/global-error.tsx`, `app/not-found.tsx`.
- Test infrastructure: `frontend/tests/fixtures/capture.mjs` (`npm run fixtures:capture` → `frontend/tests/fixtures/ds07/`), `frontend/tests/msw/handlers.ts` with `onUnhandledRequest: "error"`, unit tests in `frontend/tests/unit/`.

## Out of Scope

- Login, `AuthProvider`, `AuthGuard`, `lib/auth.ts`, `lib/roles.ts` (FEAT-063).
- `AppHeader`, `BackLink`, route tree, access-denied states (FEAT-064).
- Page and feature components (FEAT-065..FEAT-074); accessibility audit across pages (FEAT-075).
- Next.js scaffold, ESLint/Prettier/Vitest/Playwright setup and build-time env check (FEAT-004).
- CSP and security headers (owned by TRD 12 §4.9, deployment features).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-062-FR-01 | Every backend HTTP request shall go through `frontend/services/api.ts`, built as `${apiBaseUrl}/api/v1<path>` with `apiBaseUrl` = `NEXT_PUBLIC_API_BASE_URL` read in `frontend/lib/config.ts` (origin only, no trailing slash); no component calls `fetch`. | FE-011, FE-070, D-65 |
| FEAT-062-FR-02 | Every request shall send `Accept: application/json`, `Authorization: Bearer <token>` when a token exists, and a new `X-Request-ID: crypto.randomUUID()`. | FE-071, LOG-032 |
| FEAT-062-FR-03 | Requests shall abort after 15 s (`AbortController`), CSV upload after 120 s; network failures and timeouts become `ApiError {status: 0, title: "Network error"}`. | FE-072, FE-074 |
| FEAT-062-FR-04 | Non-2xx `application/problem+json` responses shall be thrown as `ApiError` with `status`, `code` (suffix of `urn:echowell:error:<CODE>` or "UNKNOWN"), `title`, `detail`, `requestId` (body or `X-Request-ID` header) and `errors` (default `[]`); UI logic branches on `code` only. | FE-073, FE-079 |
| FEAT-062-FR-05 | `api.ts` shall expose exactly the typed functions of TRD 04 §4.6.2 (login … getHealth) with parameter and return types from `lib/api-types.ts`; list calls for overview, devices and admissions use `limit=500&offset=0`. | FE-075, FE-076 |
| FEAT-062-FR-06 | `lib/api-types.ts` shall be generated by `npm run gen:api` (`openapi-typescript ../docs/api_reference/openapi.json -o lib/api-types.ts`) and never edited by hand; regeneration in CI must produce no diff and `tsc --noEmit` must pass. | FE-012, OAS-014, TST-063, D-51 |
| FEAT-062-FR-07 | Facility name, time zone, data source label, as-of, `baseline_n`, `cusum_h` and `pipeline_profile` shall be read only from the API `meta` block; components shall not hard-code `America/Chicago`, 16, 30, 5.0 or a profile. | FE-077, UX-007 |
| FEAT-062-FR-08 | Unknown response fields shall be ignored; a missing required field shall render the section error state instead of partial data. | FE-078 |
| FEAT-062-FR-09 | The `QueryClient` shall use `staleTime 60_000`, `gcTime 300_000`, `refetchOnWindowFocus true`, and retry at most 2 times only for `ApiError.status` 0 or ≥ 500 with 1 s then 2 s delay; the cache stays in memory only; query keys follow TRD 04 §4.7. | FE-080, FE-045 |
| FEAT-062-FR-10 | All protected data shall be fetched in client components via TanStack Query; none in server components, route handlers or at build time; protected pages carry `Cache-Control: private, no-store` (set in `middleware.ts`). | FE-040, FE-042 |
| FEAT-062-FR-11 | `lib/format.ts` shall implement the TRD 04 §4.11 functions with `Intl.DateTimeFormat("en-US", {timeZone: meta.facility_tz})`; `formatDateTimeShort("2026-10-30T19:28:04Z", "America/Chicago", "2026-10-30T20:00:00Z")` = "Oct 30, 2:28 PM"; `formatAsOf("2026-10-30T20:00:00Z", "America/Chicago")` = "Oct 30, 2026, 3:00 PM CT" (fallback to `short`); `formatLocalDate("2026-10-01", …)` = "Oct 1" under any `TZ`; tallies one decimal, half away from zero; signed values with U+2212. | FE-150..FE-154, UX-002, UX-003, UX-008 |
| FEAT-062-FR-12 | All clinical and plain-language templates shall exist only in `lib/wording.ts`; with `CLINICAL_WORDING_APPROVED = false` the "What this means" note ends with " [Final clinical wording: confirm with PI]". | FE-013, UX-073, UX-074, UX-164, D-18 |
| FEAT-062-FR-13 | Wording shall follow detection-not-diagnosis rules: no "diagnos" (except "not a diagnosis"), "depress", "severity", "severe", "disorder", "illness", "abnormal", "risk score", "mood", "patient"; no "Edge4Care" or "[Facility name]"; sentence case, no exclamation marks. | UX-160..UX-166, AGT-018 |
| FEAT-062-FR-14 | `SectionState` shall render loading ("Loading <section name>…", `role="status"`, ±20 % stable size), error ("Could not load <section name>. Check your connection and try again.", "Try again" calling `refetch()`, "Reference: <request_id>" in IBM Plex Mono 12px) and empty states with the copy of TRD 11 UX-204; failing sections never blank other sections. | FE-140, FE-141, FE-143, UX-200, UX-202, UX-203, UX-204, LOG-083 |
| FEAT-062-FR-15 | A failed background refetch with cached data shall keep the data and show "Could not refresh. Showing data as of <as-of>." | FE-144, UX-206 |
| FEAT-062-FR-16 | `app/(protected)/error.tsx` and `app/global-error.tsx` shall render "Something went wrong on this page." with "Reload" and no technical details; the client maps 403 to "You do not have access to this information." (no retry), 429 to "Too many attempts. Wait a minute and try again.", 503 to "The service is temporarily unavailable. Try again in a minute." | FE-145, FE-035, LOG-080, LOG-081 |
| FEAT-062-FR-17 | Field-level `errors[]` shall be shown under the matching form field (linked by `aria-describedby`), other errors above the submit button; user-facing errors never contain stack traces, tokens or raw bodies, only an optional "Reference: <id>". | FE-079, FE-067, UX-207 |
| FEAT-062-FR-18 | API strings shall be rendered as React text only; `dangerouslySetInnerHTML`, `eval`, `new Function` and `innerHTML` are banned (`react/no-danger: error`); no third-party script, telemetry or analytics. | FE-062, FE-063, FE-064, SEC-076, LOG-082 |
| FEAT-062-FR-19 | `styles/tokens.css` shall define exactly the TRD 04 §4.12 custom properties; component CSS uses only these tokens (a Vitest scan fails on hex literals in `components/**/*.module.css`); `body` uses `--font-sans`, ink on page background, centred `max-width: var(--content-max)`; the only glyphs are "▲" and "←". | FE-160, FE-161, UX-250, UX-251 |
| FEAT-062-FR-20 | The UI shall identify residents only by study ID, show no PII, no audio element, and offer no control to edit, recompute or delete baselines, scores, tallies, alarms or records. | UX-001, UX-006, UX-009, FE-068 |
| FEAT-062-FR-21 | `Footer` shall render, in IBM Plex Mono 13px secondary, the UX-005 text for variants `overview`, `default`, `alerts`, `analytics`. | FE-103, UX-005 |
| FEAT-062-FR-22 | Frontend fixtures shall be captured from the DS-07 API by `npm run fixtures:capture` into `frontend/tests/fixtures/ds07/` (one capture per sort value) and committed; a test re-records and diffs them; MSW handlers and fixture JSON are imported only from `frontend/tests/`. | TDV-016, TST-095, TRD 04 §4.14 |
| FEAT-062-FR-23 | Frontend work shall start only after `pytest tests/validation -q` passes with zero failures. | AGT-023 |
| FEAT-062-FR-24 | Each component of TRD 04 §4.8 shall export its listed props interface from its module, and presentational components shall receive their data as props only: they shall not call the API client or a query hook (data is fetched by the page components). | FE-090, FE-091 |

## Inputs

- `docs/api_reference/openapi.json` (FEAT-038); `NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_APP_ENV` (TRD 21).
- DS-07 backend stack (FEAT-060 conditions) for fixture capture.
- TRD 11 copy strings (exact, including U+00B7 "·", "▲", "–", "’").

## Outputs

- `frontend/services/api.ts`, `frontend/lib/{config,api-types,queryKeys,format,wording,deviceGroups}.ts`, `frontend/app/providers.tsx`, error boundaries, `frontend/styles/{tokens,globals}.css`, `components/SectionState`, `components/Footer`.
- `frontend/tests/fixtures/ds07/*.json`, `frontend/tests/fixtures/capture.mjs`, `frontend/tests/msw/handlers.ts`, unit tests.

## Data Flow

Component → TanStack Query hook → `api.ts` function → `fetch` with headers and timeout → backend → JSON or problem+json → typed data or `ApiError` → hook state → component renders data or `SectionState`; dates/numbers formatted by `format.ts` with `meta.facility_tz`; copy from `wording.ts`.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-004, FEAT-038, FEAT-060

- FEAT-004 provides the Next.js 14.2 scaffold and tooling.
- FEAT-038 provides the committed OpenAPI contract for `gen:api`.
- FEAT-060 proves the DS-07 API values the fixtures capture (and the validation gate of AGT-023 has passed).

Features that build directly on this one (BACKLOG.md §4): FEAT-063, FEAT-077.

## Database Impact

None. The frontend never accesses the database.

## API Impact

Endpoints consumed: all client functions of TRD 04 §4.6.2 (E-01..E-32 as used by pages). None exposed. The 401 path calls the sign-out/redirect handler that FEAT-063 registers.

## Frontend Impact

- Files: `frontend/services/api.ts`, `frontend/lib/config.ts`, `frontend/lib/api-types.ts`, `frontend/lib/queryKeys.ts`, `frontend/lib/format.ts`, `frontend/lib/wording.ts`, `frontend/lib/deviceGroups.ts`, `frontend/app/providers.tsx`, `frontend/app/(protected)/error.tsx`, `frontend/app/global-error.tsx`, `frontend/app/not-found.tsx`, `frontend/middleware.ts`, `frontend/styles/tokens.css`, `frontend/styles/globals.css`.
- Components: `SectionState`, `Footer` (TRD 04 §4.8).

## Analytics Impact

None. The frontend computes no analytics; it renders API values and rounds only for display (NFR-037).

## Security Requirements

- No token or secret in any `NEXT_PUBLIC_*` variable or code (FE-173); the token is attached only by `api.ts` and never logged (FE-051).
- No third-party scripts or telemetry (FE-064, LOG-082); API text never rendered as HTML (SEC-076).
- Query cache in memory only (FE-045); protected pages `Cache-Control: private, no-store` (FE-042).

## Error Handling

- `ApiError` for all non-2xx and network failures; retries only for status 0 or ≥ 500 (FE-080).
- 401 → token cleared, queries cancelled, cache cleared, redirect to `/login?reason=expired&next=<path>` (FE-056, wired with FEAT-063).
- 403 → inline access message without retry (FE-035); 404 from `getResident` → whole-page not-found (FE-142, used by FEAT-066).
- Unhandled render errors → error boundaries (FE-145).

## Logging Requirements

- No browser telemetry; production console limited to `console.error` for caught errors without response bodies (LOG-082).
- Displayed errors show "Reference: <request_id>" (LOG-032, FE-067). No audit records originate in the frontend.

## Testing Requirements

- Unit (Vitest, `frontend/tests/unit/`): `format.ts` (FE-151..FE-153 with `TZ=Pacific/Kiritimati` and `TZ=America/Los_Angeles`, `formatTally`, `formatSigned`, `formatCounts30d`), `wording.ts` (exact strings, marker present while unapproved — TST-096 logic), `deviceGroups.ts` ("D01, D04–D06, D08–D10"), `api.ts` (headers, 15 s abort, problem+json parsing to `ApiError`, non-JSON error → `UNKNOWN`, network error, 401 handler call).
- Component: `SectionState` loading/empty/error (TST-090), `Footer` variants.
- Static: token hex-literal scan (FE-160); forbidden-words text test (TST-097); no MSW/fixture import outside `frontend/tests/` (TST-095); `gen:api` drift and `tsc --noEmit` (TST-063).
- Fixtures: re-record and diff `tests/fixtures/ds07/` (TDV-016).
- Coverage contributes to frontend ≥ 80 % lines (TST-142, FE-180).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-062-AC-01 | `formatDateTimeShort("2026-10-30T19:28:04Z", "America/Chicago", "2026-10-30T20:00:00Z")` returns "Oct 30, 2:28 PM" and `formatAsOf("2026-10-30T20:00:00Z", "America/Chicago")` returns "Oct 30, 2026, 3:00 PM CT". Verified by: Unit (`frontend/tests/unit/`; TST-096). | FE-151; FE-152 |
| FEAT-062-AC-02 | `formatLocalDate("2026-10-01", …)` returns "Oct 1" with `TZ=Pacific/Kiritimati` and with `TZ=America/Los_Angeles`. Verified by: Unit (`frontend/tests/unit/`; TST-096). | FE-153 |
| FEAT-062-AC-03 | A mocked 422 problem+json response makes the client throw `ApiError` with `code` "VALIDATION_ERROR", the body's `request_id` and its `errors[]`; a timeout after 15 s throws `ApiError` with status 0 and title "Network error". Verified by: Unit (`frontend/tests/unit/`; TST-096). | FE-072; FE-073; FE-074 |
| FEAT-062-AC-04 | Running `npm run gen:api` on the committed contract produces no diff and `npm run typecheck` passes. | TST-063; FE-012 |
| FEAT-062-AC-05 | The Vitest scan finds no hex colour literal in `components/**/*.module.css`, and the forbidden-words test passes on rendered pages. | FE-160; TST-097 |
| FEAT-062-AC-06 | `SectionState` with `state="error"` and a request id renders "Could not load <name>. Check your connection and try again.", a "Try again" button calling `onRetry`, and "Reference: <id>". Verified by: Component (TST-090). | FE-141; UX-203 |
| FEAT-062-AC-07 | No file outside `frontend/tests/` imports MSW handlers or fixture JSON, and the production build contains no fixture data. | TST-095 |
| FEAT-062-AC-08 | `grep -rn "fetch(" frontend/app frontend/components` returns no match. Verified by: Inspection (run the command in the criterion and check its output). | FE-011 |

## Definition of Done

- All FEAT-062 acceptance criteria pass; `npm run lint && npm run typecheck && npm run test` exit 0.
- Fixtures captured and committed from DS-07; `docs/reports/FRONTEND_IMPLEMENTATION_REPORT.md` section for foundations written (TRD 25 Phase 8 Outputs).
- Batch report lists IDs (AGT-022).

## Implementation Notes

- Never parse a local date with `new Date("YYYY-MM-DD")`; split the string (TRD 04 §8).
- Implement and test the `shortGeneric` → `short` fallback by stubbing the formatter (TRD 04 §8).
- MSW: register handlers for every §4.6.2 endpoint and set `onUnhandledRequest: "error"`; capture fixtures per sort value because the order comes from the API (FE-084).
- Copy strings verbatim from TRD 11 into `wording.ts` and test them with exact matches (TRD 11 §8).
- The route boundary is `app/(protected)/error.tsx` (TRD 04 §4.2, FE-145; TRD 17 LOG-080 aligned in the PR #2 consistency fixes), with `app/global-error.tsx` for the root.
