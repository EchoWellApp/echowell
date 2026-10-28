# FEAT-062 Frontend foundations (API client, generated types, query cache, formatting, wording, v0.2 tokens, status pills, section states)

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

Build the shared frontend layer every page uses: the single typed API client `frontend/services/api.ts`, the generated contract types `frontend/lib/api-types.ts`, the TanStack Query client and query keys, the facility-time-zone formatters `lib/format.ts`, the display-status mapping `lib/status.ts` `toDisplayStatus()` (API `status` + `needs_attention` → Changed, Needs attention, Learning, Usual; TRD 24 D-109), the `StatusPill` component with its four colours and glyphs, the wording module `lib/wording.ts` with every v0.2 copy template and the PI-confirmation marker, the wireframe v0.2 design tokens (SRC-21, TRD 24 D-112) in a light and a dark scheme with the self-hosted "Source Sans 3" font, the `SectionState` loading/empty/error component, the error boundaries, and the captured DS-07 test fixtures with MSW handlers. The checkpoint 2 skeleton (`frontend/app/layout.tsx`, FEAT-004) still loads IBM Plex Sans and Mono; this feature replaces them with Source Sans 3. Work starts only after the R01–R10 validation suite passes (AGT-023).

## Business Context

- BR-12, BR-13 (staff read the dashboard correctly): uniform dates in facility time, one status vocabulary with four display statuses that are never conveyed by colour alone, uniform states and plain-language wording.
- BR-16 (privacy and security): one HTTP module, no third-party scripts or runtime font requests, escaped API text, in-memory cache.
- BR-18 (detection, not diagnosis): all clinical wording lives in one PI-reviewed module (D-18, OQ-12).
- BR-15: fixtures are captured from the real pipeline output, never from workbook values (TDV-016).
- Wireframe v0.2 (SRC-21) replaces the five v0.1 wireframes (TRD 24 D-108); its visual tokens and wording changes are D-112 and D-113.
- FRs covered (BACKLOG.md): none directly (enabling feature).

## Referenced TRDs

- TRD 11 (v0.13) — owned by this feature: UX-001..UX-004, UX-006..UX-009 (global conventions; UX-004 pill = colour + glyph + label + border), §4.3.4 display statuses and pill styling, UX-074 (single wording configuration), UX-122 (primary and secondary button styles, shared classes in `styles/globals.css`), UX-160..UX-167 (wording rules, incl. UX-167 v0.2 word changes), UX-200..UX-207 (loading, empty and error states), UX-250..UX-253 (tokens of §4.15, glyphs, self-hosted font, light and dark scheme). UX-005 is retired (D-110); its texts move to the data bar (UX-400, FEAT-064) and the check-in log caption (UX-148, FEAT-068).
- TRD 04 FE-013 (wording only in `lib/wording.ts`), FE-040..FE-045, FE-062..FE-068, FE-070..FE-080, FE-140..FE-145, FE-150..FE-154, FE-160, FE-161, FE-211, FE-004 (font), FE-092 (`StatusPill`), FE-207 (`toDisplayStatus`), FE-090, FE-091, §4.2 layout, §4.6.2 client functions, §4.6.3 type aliases, §4.7 query keys, §4.11 format table, §4.12 tokens, §4.14 fixtures (as updated for wireframe v0.2).
- TRD 17 LOG-032 (request ID, "Reference:"), LOG-080..LOG-083.
- TRD 12 SEC-076 (API text as text nodes).
- TRD 19 OAS-014 (generated types; `ResidentOverviewRow`, `ResidentDetail` with `needs_attention`, `attention_reasons`, `alarm_reviewed`; `OverviewSummary` `{changed, needs_attention, learning, usual}`; `CheckinEventType` `checkins_started`; `Device.uploaded_on_as_of_date`; TRD 24 D-114); TRD 14 TDV-016; TRD 13 TST-063, TST-094, TST-095, TST-097, TST-142.
- TRD 25 AGT-018, AGT-023; TRD 24 D-18, D-51, D-65, D-108, D-109, D-112, D-113, D-114; SRC-21.

## Scope

- `frontend/services/api.ts`: one typed function per endpoint of TRD 04 §4.6.2, base URL from `frontend/lib/config.ts`, headers, timeouts, `ApiError`, 401 handling hook (redirect logic wired by FEAT-063), CSV download helpers.
- `npm run gen:api` → `frontend/lib/api-types.ts` (generated, never hand-edited, including the D-114 additions) and the alias module of TRD 04 §4.6.3.
- `frontend/app/providers.tsx` with `QueryClientProvider`; `frontend/lib/queryKeys.ts`.
- `frontend/lib/format.ts` (`formatDateTimeShort`, `formatAsOf`, `formatLocalDate`, `formatLocalDateRange` (with year where UX-003 requires it), `formatTally` (one decimal), `formatThreshold` (h without trailing zeros: "5", "4.5"), `formatSigned`, `formatOpenDays` ("1 day", "<d> days", "opened today")).
- `frontend/lib/status.ts`: `toDisplayStatus(status, needsAttention)` → `UiStatus` `changed` | `needs_attention` | `learning` | `usual` (first match per TRD 11 §4.3.4, FE-207); presentation only, the browser computes no data-alert rule.
- `components/StatusPill/` (`{ status: UiStatus; size?: "sm" | "lg" }`): label from `statusLabel()`, decorative glyph (`aria-hidden="true"`), colours and border of §4.3.4, large variant for the chart banner.
- `frontend/lib/wording.ts`: pill labels and legend meanings, "What's happening" templates (§4.3.6), Summary lead and note templates (§4.5.2.1), baseline templates (§4.5.7.1), check-in log and device history lines (§4.5.6, UX-431), review and note messages, Study team note and data-problem helpers, data bar sentences; `CLINICAL_WORDING_APPROVED = false` with the marker " [Final clinical wording: confirm with PI]". Feature pages add their templates here, never in components.
- `frontend/lib/deviceGroups.ts` `compressDeviceCodes()` (runs of 3 or more joined with " to ", UX-054; used by FEAT-072).
- `frontend/styles/tokens.css` (the TRD 11 §4.15 tokens as CSS custom properties, light values on `:root`, dark values under `@media (prefers-color-scheme: dark)`) and `globals.css`; root layout base styles; `next/font/google` `Source_Sans_3` (weights 400, 600, 700, `display: "swap"`, self-hosted at build time) replacing the IBM Plex fonts of the checkpoint 2 skeleton.
- Primary and secondary button classes of UX-122 in `styles/globals.css` (used by every feature); `components/SectionState/`; `app/(protected)/error.tsx`, `app/global-error.tsx`, `app/not-found.tsx`.
- Test infrastructure: `frontend/tests/fixtures/capture.mjs` (`npm run fixtures:capture` → `frontend/tests/fixtures/ds07/`), `frontend/tests/msw/handlers.ts` with `onUnhandledRequest: "error"`, unit tests in `frontend/tests/unit/`.

## Out of Scope

- Login, `AuthProvider`, `AuthGuard`, `lib/auth.ts`, `lib/roles.ts` (FEAT-063).
- App bar, data bar, route tree, access-denied states (FEAT-064). The v0.1 `Footer` component is not built (UX-005 retired).
- Page and section components (FEAT-065..FEAT-074); accessibility and responsive audit across pages, including the contrast check of the token pairs in both schemes (FEAT-075).
- Next.js scaffold, ESLint/Prettier/Vitest/Playwright setup and build-time env check (FEAT-004).
- CSP and security headers (TRD 12 §4.9, deployment features).
- The wireframe's "Show wireframe notes" toggle (a wireframe tool, not a product feature; TRD 11 §2).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-062-FR-01 | Every backend HTTP request shall go through `frontend/services/api.ts`, built as `${apiBaseUrl}/api/v1<path>` with `apiBaseUrl` = `NEXT_PUBLIC_API_BASE_URL` read in `frontend/lib/config.ts` (origin only, no trailing slash); no component calls `fetch`. | FE-011, FE-070, D-65 |
| FEAT-062-FR-02 | Every request shall send `Accept: application/json`, `Authorization: Bearer <token>` when a token exists, and a new `X-Request-ID: crypto.randomUUID()`. | FE-071, LOG-032 |
| FEAT-062-FR-03 | Requests shall abort after 15 s (`AbortController`), CSV upload after 120 s; network failures and timeouts become `ApiError {status: 0, title: "Network error"}`. | FE-072, FE-074 |
| FEAT-062-FR-04 | Non-2xx `application/problem+json` responses shall be thrown as `ApiError` with `status`, `code` (suffix of `urn:echowell:error:<CODE>` or "UNKNOWN"), `title`, `detail`, `requestId` (body or `X-Request-ID` header) and `errors` (default `[]`); UI logic branches on `code` only. | FE-073, FE-079 |
| FEAT-062-FR-05 | `api.ts` shall expose exactly the typed functions of TRD 04 §4.6.2 with parameter and return types from `lib/api-types.ts`; list calls for residents, devices and admissions use `limit=500&offset=0`. | FE-075, FE-076 |
| FEAT-062-FR-06 | `lib/api-types.ts` shall be generated by `npm run gen:api` (`openapi-typescript ../docs/api_reference/openapi.json -o lib/api-types.ts`) and never edited by hand; regeneration in CI must produce no diff and `tsc --noEmit` must pass. | FE-012, OAS-014, TST-063, D-51 |
| FEAT-062-FR-07 | Facility name, time zone, data source label, as-of, `baseline_n`, `cusum_h` and `pipeline_profile` shall be read only from the API `meta` block; components shall not hard-code `America/Chicago`, 16, 30, 5.0 or a profile. | FE-077, UX-007 |
| FEAT-062-FR-08 | Unknown response fields shall be ignored; a missing required field shall render the section error state instead of partial data. | FE-078 |
| FEAT-062-FR-09 | The `QueryClient` shall use `staleTime 60_000`, `gcTime 300_000`, `refetchOnWindowFocus true`, and retry at most 2 times only for `ApiError.status` 0 or ≥ 500 with 1 s then 2 s delay; the cache stays in memory only; query keys follow TRD 04 §4.7. | FE-080, FE-045 |
| FEAT-062-FR-10 | All protected data shall be fetched in client components via TanStack Query; none in server components, route handlers or at build time; protected pages carry `Cache-Control: private, no-store` (set in `middleware.ts`). | FE-040, FE-042 |
| FEAT-062-FR-11 | `lib/format.ts` shall implement the TRD 04 §4.11 functions with `Intl.DateTimeFormat("en-US", {timeZone: meta.facility_tz})`: `formatDateTimeShort("2026-10-30T19:28:04Z", "America/Chicago", "2026-10-30T20:00:00Z")` = "Oct 30, 2:28 PM CT"; `formatLocalDate("2026-10-01", …)` = "Oct 1" under any `TZ`; date ranges "Oct 1–16", with the year only when it differs from the as-of year, except the data bar and Study team period ("Oct 1–30, 2026"); change score values one decimal ("5.4", "26.8"); the alarm line h without trailing zeros ("5"); signed values with U+2212. | FE-150..FE-154, UX-002, UX-003, UX-008 |
| FEAT-062-FR-12 | `toDisplayStatus()` shall map, first match: `status` `alarm_on` → Changed; `needs_attention` true → Needs attention; `status` `baseline_forming` → Learning; `status` `no_alarm` → Usual; it uses only API values. | FE-207, TRD 11 §4.3.4, D-109 |
| FEAT-062-FR-13 | `StatusPill` shall render inline-flex, gap 6px, padding 3px 10px, radius 999px, 14px, weight 700, 1px border, a 12px glyph before the label with `aria-hidden="true"` — Changed "▲" (`--red` / `--red-bg` / `--red`), Needs attention "!" (`--yellow` / `--yellow-bg` / `--yellow-edge`), Learning "○" (`--grey` / `--grey-bg` / `--grey`), Usual "●" (`--green` / `--green-bg` / `--green`); the large variant is 18px with padding 6px 16px. Status is never shown by colour alone. | UX-004, TRD 11 §4.3.4 |
| FEAT-062-FR-14 | All clinical and plain-language templates shall exist only in `lib/wording.ts`; with `CLINICAL_WORDING_APPROVED = false` the Summary note and the resident-list note end with " [Final clinical wording: confirm with PI]". | FE-013, UX-074, UX-164, D-18 |
| FEAT-062-FR-15 | Wording shall follow detection-not-diagnosis rules: no "diagnos" (except "not a diagnosis"), "depress", "severity", "severe", "disorder", "illness", "abnormal", "risk score", "mood", "patient"; no facility name other than `meta.facility_name` and no "[Facility name]" placeholder (UX-166); sentence case, no exclamation marks (the "!" pill glyph is a shape, not punctuation); UI words per D-113: "held back (possible other voice)" for `quarantined`, "change score" for the CUSUM tally, "Comparing with baseline started" / "compared with it since", "What did you find?", "Changed", "Needs attention", "Learning", "Usual". | UX-160..UX-167, AGT-018, D-113 |
| FEAT-062-FR-16 | `SectionState` shall render loading ("Loading <panel name>…", `role="status"`, stable size; tiles and banner facts show "—"), error ("Could not load <panel name>. Check your connection and try again.", "Try again" calling `refetch()`, "Reference: <request_id>" 12px `--muted` in `--font-mono`) and empty states with the copy of TRD 11 UX-204; failing panels never blank other panels. | FE-140, FE-141, FE-143, UX-200, UX-202, UX-203, UX-204, LOG-083 |
| FEAT-062-FR-17 | A failed background refetch with cached data shall keep the data and show "Could not refresh. Showing data as of <as-of>." | FE-144, UX-206 |
| FEAT-062-FR-18 | `app/(protected)/error.tsx` and `app/global-error.tsx` shall render "Something went wrong on this page." with "Reload" and no technical details; the client maps 403 to "You do not have access to this information." (no retry), 429 to "Too many attempts. Wait a minute and try again.", 503 to "The service is temporarily unavailable. Try again in a minute." | FE-145, FE-035, LOG-080, LOG-081 |
| FEAT-062-FR-19 | Field-level `errors[]` shall be shown under the matching form field (linked by `aria-describedby`), other errors above the submit button; user-facing errors never contain stack traces, tokens or raw bodies, only an optional "Reference: <id>". | FE-079, FE-067, UX-207 |
| FEAT-062-FR-20 | API strings shall be rendered as React text only; `dangerouslySetInnerHTML`, `eval`, `new Function` and `innerHTML` are banned (`react/no-danger: error`); no third-party script, telemetry or analytics. | FE-062, FE-063, FE-064, SEC-076, LOG-082 |
| FEAT-062-FR-21 | `styles/tokens.css` shall define exactly the TRD 11 §4.15 / TRD 04 §4.12 custom properties (`--chrome`, `--chrome-ink`, `--chrome-muted`, `--canvas`, `--surface`, `--surface-2`, `--ink`, `--muted`, `--rule`, `--link`, `--red`/`--red-bg`, `--yellow`/`--yellow-bg`/`--yellow-edge`, `--green`/`--green-bg`, `--grey`/`--grey-bg`, `--c-used`, `--c-aside`, `--c-quar`, sizes and spacing) with the light values on `:root` and the dark values under `@media (prefers-color-scheme: dark)`; component CSS uses only these tokens (a Vitest scan fails on hex literals in `components/**/*.module.css`); `body` uses the font token, `--ink` on `--canvas`, max width 1240px, page padding 20px, base 16px, line-height 1.45, tabular numerals. | FE-160, FE-161, FE-211, UX-250, UX-253, D-112 |
| FEAT-062-FR-22 | The font shall be "Source Sans 3" 400/600/700 loaded with `next/font/google` (downloaded at build time and served from the application's origin, fallback Segoe UI, Helvetica, Arial, sans-serif); the IBM Plex Sans and Mono imports of `frontend/app/layout.tsx` shall be removed; no request to a font service is made at runtime. | FE-004, UX-252, D-112, BR-16 |
| FEAT-062-FR-23 | The only glyphs in the UI shall be "▲", "!", "●", "○" and "←"; no icon library is installed. | UX-251 |
| FEAT-062-FR-24 | The UI shall identify residents only by study ID, show no name, photo, room or other personal data, no audio element, and offer no control to edit, recompute, reset or delete baselines, scores, change scores, alarms or records. | UX-001, UX-006, UX-009, FE-068 |
| FEAT-062-FR-25 | Frontend fixtures shall be captured from the DS-07 API by `npm run fixtures:capture` into `frontend/tests/fixtures/ds07/` and committed (residents list with `sort=alarm`, each resident detail, scores, check-ins, features, notes, alerts, data alerts, devices, analytics, config); a test re-records and diffs them; MSW handlers and fixture JSON are imported only from `frontend/tests/`. | TDV-016, TST-095, TRD 04 §4.14 |
| FEAT-062-FR-26 | Frontend work shall start only after `pytest tests/validation -q` passes with zero failures. | AGT-023 |
| FEAT-062-FR-27 | Each component of TRD 04 §4.8 shall export its listed props interface from its module, and presentational components shall receive their data as props only: they shall not call the API client or a query hook (data is fetched by the page and section components). | FE-090, FE-091 |
| FEAT-062-FR-28 | The shared button classes shall provide the primary variant (min-height 44px, padding 0 20px, weight 700, radius 4px, `--chrome` background and border, `--chrome-ink` text; e.g. "Review this alert", "Save review", "Sign in") and the secondary variant (min-height 44px, `--surface` background, ink text, 1px solid `--rule` border; e.g. "Add note", "Remind me in <h> hours", "See what changed"); link-styled buttons use the same classes. | UX-122 |

## Inputs

- `docs/api_reference/openapi.json` (FEAT-038, including the D-114 additions delivered in checkpoint 4); `NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_APP_ENV` (TRD 21).
- DS-07 backend stack (FEAT-060 conditions) for fixture capture.
- TRD 11 v0.13 copy strings (exact, including "·" U+00B7, "▲", "●", "○", "←", "–", "’", "“ ”") and the §4.15 token table.

## Outputs

- `frontend/services/api.ts`, `frontend/lib/{config,api-types,queryKeys,format,status,wording,deviceGroups}.ts`, `frontend/app/providers.tsx`, error boundaries, `frontend/styles/{tokens,globals}.css`, the Source Sans 3 font setup in `frontend/app/layout.tsx`, `components/StatusPill`, `components/SectionState`, button classes in `styles/globals.css`.
- `frontend/tests/fixtures/ds07/*.json`, `frontend/tests/fixtures/capture.mjs`, `frontend/tests/msw/handlers.ts`, unit tests.

## Data Flow

Component → TanStack Query hook → `api.ts` function → `fetch` with headers and timeout → backend → JSON or problem+json → typed data or `ApiError` → hook state → component renders data or `SectionState`; `status` + `needs_attention` → `toDisplayStatus()` → `StatusPill`; dates/numbers formatted by `format.ts` with `meta.facility_tz`; copy from `wording.ts`; colours from `tokens.css` (light or dark by the operating-system preference).

## Dependencies

Required before implementation (BACKLOG.md): FEAT-004, FEAT-038, FEAT-060

- FEAT-004 provides the Next.js 14.2 scaffold and tooling (its root layout still loads IBM Plex; this feature switches it).
- FEAT-038 provides the committed OpenAPI contract for `gen:api`.
- FEAT-060 proves the DS-07 API values the fixtures capture (and the validation gate of AGT-023 has passed).

Features that build directly on this one (BACKLOG.md §4): FEAT-063, FEAT-077.

## Database Impact

None. The frontend never accesses the database.

## API Impact

Endpoints consumed: all client functions of TRD 04 §4.6.2 (E-01..E-32 as used by pages). None exposed. The 401 path calls the sign-out/redirect handler that FEAT-063 registers.

## Frontend Impact

- Files: `frontend/services/api.ts`, `frontend/lib/config.ts`, `frontend/lib/api-types.ts`, `frontend/lib/queryKeys.ts`, `frontend/lib/format.ts`, `frontend/lib/status.ts`, `frontend/lib/wording.ts`, `frontend/lib/deviceGroups.ts`, `frontend/app/providers.tsx`, `frontend/app/layout.tsx` (font switch), `frontend/app/(protected)/error.tsx`, `frontend/app/global-error.tsx`, `frontend/app/not-found.tsx`, `frontend/middleware.ts`, `frontend/styles/tokens.css`, `frontend/styles/globals.css`.
- Components: `StatusPill`, `SectionState` (TRD 04 §4.8); shared button classes in `styles/globals.css`.

## Analytics Impact

None. The frontend computes no analytics; it renders API values, maps status plus attention flag to a display status and rounds only for display (NFR-037).

## Security Requirements

- No token or secret in any `NEXT_PUBLIC_*` variable or code (FE-173); the token is attached only by `api.ts` and never logged (FE-051).
- No third-party scripts, telemetry or runtime font requests (FE-064, LOG-082, UX-252); API text never rendered as HTML (SEC-076).
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

- Unit (Vitest, `frontend/tests/unit/`): `format.ts` (FE-151..FE-153 with `TZ=Pacific/Kiritimati` and `TZ=America/Los_Angeles`, `formatTally`, `formatThreshold` "5" and "4.5", `formatSigned`, `formatOpenDays` "1 day" / "9 days" / "opened today", date range with year), `status.ts` (`toDisplayStatus`, all four results and the first-match order, e.g. `alarm_on` with `needs_attention` true → Changed), `wording.ts` (exact strings of TRD 11 §4.3.6, §4.5.2.1, §4.5.6, §4.5.7.1; marker present while unapproved — TST-096 logic), `deviceGroups.ts` ("D01, D04 to D06, D08 to D10"), `api.ts` (headers, 15 s abort, problem+json parsing to `ApiError`, non-JSON error → `UNKNOWN`, network error, 401 handler call).
- Component: `StatusPill` (four labels, glyphs hidden from assistive technology, border present, large variant), `SectionState` loading/empty/error (TST-090).
- Static: token hex-literal scan (FE-160); forbidden-words text test (TST-097); no MSW/fixture import outside `frontend/tests/` (TST-095); `gen:api` drift and `tsc --noEmit` (TST-063); no `IBM Plex` and no `fonts.googleapis.com` / `fonts.gstatic.com` reference in the built output.
- Fixtures: re-record and diff `tests/fixtures/ds07/` (TDV-016).
- Coverage contributes to frontend ≥ 80 % lines (TST-142, FE-180).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-062-AC-01 | `formatDateTimeShort("2026-10-30T19:28:04Z", "America/Chicago", "2026-10-30T20:00:00Z")` returns "Oct 30, 2:28 PM CT", `formatTally(26.830256)` returns "26.8" and `formatThreshold(5.0)` returns "5". Verified by: Unit (`frontend/tests/unit/`; TST-096). | FE-151; UX-003; UX-008 |
| FEAT-062-AC-02 | `formatLocalDate("2026-10-01", …)` returns "Oct 1" with `TZ=Pacific/Kiritimati` and with `TZ=America/Los_Angeles`. Verified by: Unit (`frontend/tests/unit/`; TST-096). | FE-153 |
| FEAT-062-AC-03 | A mocked 422 problem+json response makes the client throw `ApiError` with `code` "VALIDATION_ERROR", the body's `request_id` and its `errors[]`; a timeout after 15 s throws `ApiError` with status 0 and title "Network error". Verified by: Unit (`frontend/tests/unit/`; TST-096). | FE-072; FE-073; FE-074 |
| FEAT-062-AC-04 | Running `npm run gen:api` on the committed contract produces no diff and `npm run typecheck` passes; `ResidentOverviewRow` has `needs_attention`, `attention_reasons` and `alarm_reviewed`. | TST-063; FE-012; D-114 |
| FEAT-062-AC-05 | The Vitest scan finds no hex colour literal in `components/**/*.module.css`; `tokens.css` defines every §4.15 token once on `:root` and once under `prefers-color-scheme: dark`; the forbidden-words test passes on rendered pages. | FE-160; UX-250; UX-253; TST-097 |
| FEAT-062-AC-06 | `toDisplayStatus` returns Changed, Needs attention, Learning and Usual for the DS-07 rows of R09, R03, a forming fixture and R01; `StatusPill` renders "▲ Changed", "! Needs attention", "○ Learning", "● Usual" with the glyph `aria-hidden` and a visible border. Verified by: Unit and Component (TST-090). | UX-004; D-109 |
| FEAT-062-AC-07 | `SectionState` with `state="error"` and a request id renders "Could not load <name>. Check your connection and try again.", a "Try again" button calling `onRetry`, and "Reference: <id>". Verified by: Component (TST-090). | FE-141; UX-203 |
| FEAT-062-AC-08 | The production build serves Source Sans 3 from the application's own origin; the built output contains no IBM Plex font file and no request to a font service. Verified by: Inspection of `.next/static` and the E2E request log (FE-192). | UX-252; D-112 |
| FEAT-062-AC-09 | No file outside `frontend/tests/` imports MSW handlers or fixture JSON, the production build contains no fixture data, and `grep -rn "fetch(" frontend/app frontend/components` returns no match. Verified by: Inspection (run the command and check its output). | TST-095; FE-011 |

## Definition of Done

- All FEAT-062 acceptance criteria pass; `npm run lint && npm run typecheck && npm run test` exit 0.
- Fixtures captured and committed from DS-07; `docs/reports/FRONTEND_IMPLEMENTATION_REPORT.md` section for foundations written (TRD 25 Phase 8 Outputs), noting the font switch from IBM Plex to Source Sans 3 (D-112).
- Batch report lists IDs (AGT-022).

## Implementation Notes

- Never parse a local date with `new Date("YYYY-MM-DD")`; split the string (TRD 04 §8).
- MSW: register handlers for every §4.6.2 endpoint and set `onUnhandledRequest: "error"`; the resident list order comes from the API (`sort=alarm`, D-109), so fixtures are captured, not reordered.
- Copy strings verbatim from TRD 11 into `wording.ts` and test them with exact matches (TRD 11 §8).
- The four display statuses are a presentation mapping (TRD 11 §8); the attention flag itself is computed by the API from open data alerts (OQ-31).
- Contrast of every token pair in both schemes is checked by FEAT-075 (UX-224); a pair below the limit is adjusted in `tokens.css` before checkpoint 7 is approved and reported to the algorithm lead.
- Dark mode is a Should (UX-253); keep it in `tokens.css` only, with no per-component dark rules.
- The route boundary is `app/(protected)/error.tsx` (TRD 04 §4.2, FE-145), with `app/global-error.tsx` for the root.
- Component names follow TRD 04 v0.11 §4.8 (binding, FE-090); the v0.1 components `SummaryTiles`, `SortSelect`, `DeviceCell`, `Footer`, `AlertsPage`, `AlertQueue`, `AlertCard`, `MiniTallyChart` and `ReviewDialog` are not built.
