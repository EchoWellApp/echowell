# Frontend Implementation Report

Checkpoint 7 (Phase 13 Implement Frontend, TRD 25 Phase 8) · Features FEAT-062..FEAT-076 · Branch `feat/cp7-frontend` · 2 November 2026.

Synthetic test data only. No audio, no names, no LLM. The facility is named only from `meta.facility_name`.

## 1. Summary

The dashboard of wireframe v0.2 (SRC-21) is built in `frontend/` on Next.js 14.2 (App Router), React 18, TypeScript strict, TanStack Query 5 and Recharts 2.13. Every page reads the real API through one typed client, with types generated from `docs/api_reference/openapi.json`. With the DS-07 test data every page shows the expected values of TRD 11 §4.13, §4.17.5 and §4.18.8.

| Measure | Value |
|---|---|
| Vitest | 71 files, 429 tests, all pass; line coverage 99.4 %, branches 94.7 % (gate 80 %, FE-180) |
| Playwright, Chromium (local stack) | read-only run 78 passed; `@mutating` group 3 passed; read-only run again after the mutating group passed (reset restores the seed) |
| axe | 12 routes × light and dark: 0 serious or critical violations |
| Responsive | 320, 360, 375, 390 px: no page-level horizontal scroll; chart section navigation is one scrolling row |
| `next build` | passes; first-load JS 88–231 kB per route (budget 300 kB, FE-204) |
| Lint, type-check, Prettier | `next lint --max-warnings 0`, `tsc --noEmit`, `prettier --check .` all clean |

## 2. Structure

| Area | Files |
|---|---|
| Foundations (FEAT-062) | `services/api.ts` (one function per endpoint, `ApiError`, 15 s / 120 s timeouts, `X-Request-ID`, 401 → sign out), `lib/api-types.ts` (generated), `lib/types.ts`, `lib/format.ts`, `lib/status.ts`, `lib/roles.ts`, `lib/queryKeys.ts`, `lib/queryClient.ts`, `lib/deviceGroups.ts`, `lib/hooks.ts`, `lib/wording.ts` + `lib/wording/*.ts` (all copy, FE-013), `styles/tokens.css`, `styles/globals.css`, `middleware.ts` |
| Login and session (FEAT-063) | `lib/auth.ts` (memory + `sessionStorage["echowell.auth"]`), `lib/AuthProvider.tsx`, `components/LoginForm`, `app/login/page.tsx`, the AuthGuard in `app/(protected)/layout.tsx` |
| App chrome (FEAT-064) | `components/AppHeader` (nav, alarm badge), `DataBar`, `CountBadge`, `SectionState`, `AccessDenied`, `BackLink`, `app/not-found.tsx`, `error.tsx`, `global-error.tsx` |
| Resident list (FEAT-065) | `app/(protected)/residents/page.tsx`; `FilterButtons`, `ResidentsTable`, `WhatsHappening`, `StatusLegend`, `StatusPill` |
| Resident chart (FEAT-066..FEAT-071) | `app/(protected)/residents/[residentCode]/` layout + six section routes; `ChartBanner`, `ChartSectionNav`, `SummaryPanel`, `LeaningMost`, `MoreDetailTiles`, `ChangeScoreChart`, `ChangeScoreTable`, `MeasurementCards`, `FeatureCard`, `Sparkline`, `OtherMeasurementsCard`, `BaselinePanel`, `CheckinCounts`, `CheckinLog`, `AlarmReviewPanel`, `AlertReviewForm`, `ReviewHistory`, `StaffNotes`, `NotesList`, `DevicePanel` |
| Study team (FEAT-072) | `app/(protected)/study/page.tsx`; `KpiTiles`, `DataProblemsList`, `DailyCheckinsChart`, `LossFunnel`, `UsableByResidentChart`, `AlarmTimingTable`, `ReviewOutcomesTable`, `DevicesSection` |
| New admissions, Admin (FEAT-073, FEAT-074) | `ExperimentalBanner`, `AdmissionsTable`, `RangePill`, `FacilityRangeChart`, `AdminPanel` (Users, Pipeline runs, Upload data tabs) |
| Tests (FEAT-075, FEAT-076) | `tests/unit`, `tests/pages`, co-located component tests, `tests/msw`, `tests/fixtures/ds07` (captured by `npm run fixtures:capture`), `tests/e2e` (11 specs, global setup, role fixture), `tests/fixtures/seeds/demo_overlay/` |

The v0.1 routes `/alerts` and `/analytics` do not exist (D-110).

## 3. Data and state

- Server state lives only in the in-memory TanStack Query cache (FE-045). Keys follow TRD 04 §4.7, and saves invalidate as FE-085 and FE-086 require. The UI never changes an alarm state locally after a review; it shows what the API returns (FE-134, OQ-05).
- The token is kept in memory and mirrored to `sessionStorage` only. It is never in `localStorage`, cookies or URLs (FE-050, FE-051).
- The resident-list filter is in `?show=`. Filtering happens in the browser in API order, with no request (FE-082, FE-084).
- All dates and times use `meta.facility_tz`. Tests pass under `TZ=Pacific/Kiritimati` and `TZ=America/Los_Angeles` (`npm run test:tz`, FE-153).

## 4. Tests

- **Unit:** format, status (all 6 combinations), roles, device grouping, token store, API client errors and 401 handling, retries, and every wording template.
- **Component and page:** each page is tested with MSW serving the DS-07 fixtures. The TRD 11 expected-rendering rows are asserted with exact strings. Also covered:
  - loading, error with "Reference:" and Try again, 403, empty and stale-data states;
  - role restrictions, with an MSW request spy proving that no admin or study request is made for other roles;
  - the FE-205 fake-timer reminder test.
- **E2E:** `resident-list`, `resident-chart`, `review`, `study-team`, `auth`, `admissions`, `responsive`, `privacy` and `a11y` run read-only. `mutating.spec.ts` runs the D-73/D-118 serial group: E2E-18 on R09, then the FE-193 reminder on R10, then E2E-09/FE-187 on R10. `isolated.spec.ts` covers E2E-15, TST-187 and E2E-19 against `echowell_demo`; it type-checks here, and its CI job is FEAT-080.

## 5. Deviations and additions

| # | Item | Why |
|---|---|---|
| A-1 | Tokens `--badge-ink`, `--nav-active`, `--nav-hover` added to `styles/tokens.css` | White on the dark-mode `--red` (#FF8A80) fails contrast. The two nav tints were literals in the wireframe CSS. |
| A-2 | The count badge draws its digit with CSS (`content: attr(data-count)`) | axe reported `label-content-name-mismatch` (serious) on every page. The link names stay exactly as UX-018 and UX-411 require. |
| A-3 | Selected Admin tab uses `--link` | `--chrome` on `--surface` is 1.02:1 in dark mode. |
| A-4 | `<noscript>` message | NFR-142 / FEAT-075-AC-08 |
| A-5 | Some component props differ from the TRD 04 §4.8 inventory (extra loading, as-of and variant props; `StaffNotes` fetches its own notes) | Needed for per-panel states and time-zone formatting. Listed in the checkpoint report. |
| A-6 | `getHealth` accepts the 503 body; `listPipelineRuns` takes filters; `getCheckins` sends `limit=500` | UX-216 degraded line; UX-219 nightly banner; avoids the API default page of 50. |
