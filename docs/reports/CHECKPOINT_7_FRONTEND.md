# Checkpoint 7 Report — Phase 13 Implement Frontend

Block 3 "Implement Features", checkpoint 7 of 9, its own PR (branch `feat/cp7-frontend`, created from `main` at 753d32a after GitHub PR #22 was merged on 2 November 2026) · Prompt: `specs/prompts/Implement_Feature_Batches.md` "Phase 13: Implement Frontend" · TRD 25 Phase 8 · Features: FEAT-062..FEAT-076 · Date: 2 November 2026 · Status: in review (GitHub PR #28); review round 1 answered and applied, section 10.

Build order followed roadmap §5.7: [FEAT-062, FEAT-063, FEAT-064] → [FEAT-065] → [FEAT-066, FEAT-067, FEAT-068] → [FEAT-069, FEAT-070, FEAT-071] → [FEAT-072, FEAT-073, FEAT-074] → [FEAT-075, FEAT-076]. Specs read: TRD 04, TRD 11, TRD 19 (through the generated types), TRD 13 §4.10, TRD 24 D-73, D-74 and D-108..D-119, and the wireframe v0.2 with `WIREFRAMES.md`. The pipeline-validation gate passed on `main` before work started (AGT-023, CI green on 753d32a).

Everything runs on synthetic test data (DS-07). No audio, no names, no LLM.

## 1. Result

The whole dashboard of wireframe v0.2 is built. With the test data it shows every value TRD 11 expects. Details are in `docs/reports/FRONTEND_IMPLEMENTATION_REPORT.md`.

| Measure | Value |
|---|---|
| Vitest (unit, component, page) | 429 passed; line coverage 99.4 % (gate 80 %) |
| Playwright, Chromium, local stack | read-only 78 passed; `@mutating` 3 passed; read-only again afterwards passed |
| axe, light and dark | 0 serious or critical violations on the 12 routes of FE-190 |
| Phone widths 320–390 px | no page-level horizontal scroll |
| `next build` | passes; largest first-load JS 231 kB (`/study`), budget 300 kB |
| DS-07 fixture vs TRD 11 expected values | no mismatch except the D07 resident (Q-6) |

## 2. What was built

| Group | Features | Delivered |
|---|---|---|
| 1 | FEAT-062..FEAT-064 | API client and generated types, query cache, formatting, wording, v0.2 tokens (Source Sans 3, light and dark), status pills, panel states, login and session handling, route guard, app bar with alarm badge, data bar, access-denied and error pages, DS-07 fixture capture (`npm run fixtures:capture`), MSW test harness |
| 2 | FEAT-065 | Resident list: filters in `?show=`, table in API order, What's happening, legend, PI note |
| 3 | FEAT-066..FEAT-068 | Chart layout (back link, banner, six-section navigation with review badge, not-found), Summary, Voice trends (change score chart and table, 7 measurement cards), Baseline, Check-in log |
| 4 | FEAT-069..FEAT-071 | Alarm review panel (checklist, outcome, note, reminder, previous reviews), staff notes, Device section |
| 5 | FEAT-072..FEAT-074 | Study team (tiles, data problems, charts, alarm timing or review outcomes, Devices `#devices`, CSV downloads), New admissions (experimental), Admin (users, pipeline runs, upload) |
| 6 | FEAT-075, FEAT-076 | Accessibility and responsive checks; Playwright suite with global reset, per-role sessions, the `@mutating` serial group and the `@isolated` specs; demo overlay roster |

## 3. Defects found and fixed during the checkpoint

| # | Found by | Problem | Fix |
|---|---|---|---|
| F-1 | `next build` | A layout exported a helper function, which Next.js rejects | Moved to `components/AppHeader` |
| F-2 | E2E (FE-058) | Sign out went to `/login?next=…` | The guard skips its redirect after a user sign-out |
| F-3 | axe | Count badge digit not in the link's accessible name | Digit drawn by CSS (A-2 of the implementation report) |
| F-4 | axe, dark | Selected Admin tab contrast 1.02:1 | Uses `--link` |

No backend or analytics code was changed.

## 4. Files

- **Created:** about 300 files under `frontend/`. These are the pages, 46 components (each with CSS module and test), `lib/`, `styles/`, `middleware.ts`, `tests/` (unit, pages, MSW, DS-07 fixtures, 11 E2E specs with setup and fixture), plus `tests/fixtures/seeds/demo_overlay/`, `docs/reports/FRONTEND_IMPLEMENTATION_REPORT.md` and this report.
- **Changed:** `frontend/app/layout.tsx`, `app/login/page.tsx`, `services/api.ts`, `package.json` (scripts `fixtures:capture`, `test:tz`), `playwright.config.ts` (retries 1 in CI), `vitest.setup.ts`, the two existing tests, `.prettierignore`. Tracking: `specs/backlog/BACKLOG.md` §10, the FEAT-062..FEAT-076 Status fields and roadmap §2.1.
- **Size:** about 45,500 added lines.
  - About 25,300 are generated: the DS-07 JSON fixtures and `lib/api-types.ts`.
  - About 10,400 are tests.
  - About 9,800 are application code and CSS.

## 5. Commands run and results

| # | Command (in `frontend/`) | Result |
|---|---|---|
| 1 | `npm run lint`; `npm run typecheck`; `npm run format:check` | clean |
| 2 | `npm run test:coverage` | 71 files, 429 passed; lines 99.41 %, branches 94.73 % |
| 3 | `npm run test:tz` | format tests pass in Pacific/Kiritimati and America/Los_Angeles |
| 4 | `npm run build` | passes; first-load JS 88–231 kB |
| 5 | `npm run test:e2e:readonly -- --project=chromium` (local DS-07 stack, `E2E_RESET_COMMAND`) | 78 passed |
| 6 | `npm run test:e2e:mutating -- --project=chromium` | 3 passed |
| 7 | `npm run gen:api` | `lib/api-types.ts` identical to the committed file |

The local stack used here: PostgreSQL 16 with DS-07 (`seed test_v0_1` plus the DS-10 loader), uvicorn on :8000, and `next start` on :3001. Docker is not available in this container, so `global-setup.ts` ran the reset through `E2E_RESET_COMMAND`; CI uses the `docker compose` steps.

## 6. Exit criteria (roadmap §5.7)

| Criterion | Evidence | Result |
|---|---|---|
| Data bar "Test data only (pipeline test data v0.1, Oct 1–30, 2026). No real residents. No audio is stored or played anywhere in EchoWell." and nav badge "2" | `DataBar.test`, `AppHeader.test`, E2E-01, FE-185 | PASS |
| Filters "All (10)", "Changed (2)", "Needs attention (2)", "Usual (6)", rows R09, R10, R03, R08, R01, R02, R04, R05, R06, R07 | `FilterButtons.test`, `ResidentsTable.test`, E2E-03..E2E-06 | PASS |
| R09 Summary and chart values (Oct 21, 9 days, Not reviewed, Leaning most, 14 bars, "Alarm line: 5", "Oct 21 · alarm", table 3.2 … 26.8) | `resident-summary`, `ChangeScoreChart.test`, `ChangeScoreTable.test`, E2E-08 | PASS |
| Study team values (94 %, 89 %, 9 of 10, 2; funnel 300/281/269/267; by-resident; timing 0 and 7 days) | `study.test`, E2E-20 | PASS |
| Review saved keeps the alarm on; badge drops to 1 | `mutating.spec.ts` E2E-18, E2E-09 | PASS |
| Frontend line coverage ≥ 80 % | item 2 | PASS |
| No `/alerts` or `/analytics` route | route tree; `next build` route list | PASS |
| WCAG 2.1 AA in light and dark (axe) | `a11y.spec.ts` | PASS |
| E2E in Firefox and WebKit; `@isolated` run on `echowell_demo` | only Chromium is installed here; `e2e.yml` is FEAT-080 (checkpoint 8) | PENDING |
| Algorithm lead approves and merges (D-101) | review | PENDING |

## 7. New OQ and D IDs

None. Decisions from this review will be recorded in TRD 24 from D-141 (D-140 is the OpenAPI server fix, GitHub PR #29).

## 8. Notes

| # | Note |
|---|---|
| N-1 | The six screen groups were built in parallel, each owning its own files; I integrated them and ran every check on the combined tree. |
| N-2 | New E2E environment variables: `E2E_RESET_COMMAND` (replaces the `docker compose` reset when set), `E2E_SKIP_RESET`, `E2E_PSQL_COMMAND` (audit-row check of E2E-02; default `docker compose exec -T db psql …`), `E2E_API_BASE_URL`. `e2e.yml` (FEAT-080) will need to set the SEED_* passwords and `SEED_INGEST_API_KEY`. |
| N-3 | The container has Node 22; `package.json` asks for Node 20 and CI uses Node 20. Nothing failed on 22. |
| N-4 | `main` received two direct commits by team members during checkpoint 6 ("Fix Netlify deploy", "Fix Render deployment error"). Render is not in the deployment plan (Netlify, Railway, Neon; Block 4). I did not touch either. |

## 9. Questions for the reviewer

| ID | Question |
|---|---|
| Q-1 | The UI uses some short texts that no spec defines. Examples: "Period 1" / "Period 2 (current)" for the device-period choice; "The latest pipeline run failed (started <date-time>)."; "Could not save the review. Your choices are kept — try again."; "No device is assigned to <R>."; "Changed from their usual. Not reviewed yet." when a Changed resident has no alarm date. Accept them, or should the PI/lead supply the wording? |
| Q-2 | A-1: I added three tokens (`--badge-ink`, a dark text on the red badge in dark mode, plus the two nav tints). Add them to TRD 04 §4.12 and TRD 11 §4.15? |
| Q-3 | A-2: the badge digit is drawn by CSS so that the link name is exactly "Resident list, 2 alarms not reviewed" and axe passes. Agree? |
| Q-4 | The "Review and notes" badge follows `alarm_reviewed === false` (FE-210, FEAT-066-FR-05), not "alert status open" as UX-411 says. These agree on the test data. Align UX-411 with FE-210? |
| Q-5 | `device_silent` check-in events come from the API with `device_code: null`, so the log line takes the device code from the detail text. Should the API fill `device_code` on these events (an additive TRD 19 change)? |
| Q-6 | TRD 11 §4.13.4 shows "D07 R07" in the all-devices table, but the API returns no residents for the retired D07. The UI now shows the residents of its replacement (D07B). Keep that, or should the API return R07 for D07? |
| Q-7 | UX-056 "followed by up to 3 dates": I show the latest three (D08: "12 (latest Oct 21, Oct 24, Oct 27)"). Agree? |
| Q-8 | TRD 13 TST-100 lists the `@mutating` order as E2E-18, E2E-09, then the reminder. D-73/D-118, FE-187 and FE-193 say E2E-18, the reminder, then E2E-09. I followed D-118. Correct TST-100? |
| Q-9 | Feature-file wording that TRD 11 v0.2 superseded: FEAT-068-AC-07 (Baseline sentence without "in the last 30 days") and FEAT-073 (Changed/Usual pills for admissions; D-117 says neutral pills). I followed TRD 11. Update the feature files? |
| Q-10 | Some component props differ from the TRD 04 §4.8 inventory: extra loading and as-of props, and `StaffNotes` fetches its own notes. Update §4.8 to match, or change the code? |
| Q-11 | Firefox, WebKit and the `@isolated` run were not run here. They will run in `e2e.yml` (FEAT-080, checkpoint 8). Agree? |
| Q-12 | Size: about 45,500 added lines, of which about 25,300 are generated fixtures and types and about 10,400 are tests, for 15 features. Accept as one PR? |
| Q-13 | N-4: someone deployed to Render from `main`. Is that intended, and should Block 4 plan for it? |

## 10. Review round 1 resolutions (4 November 2026)

Shaba (algorithm lead) answered all 13 questions in her review of GitHub PR #28, requesting changes. The decisions are recorded in TRD 24 as D-141..D-151, plus D-153 for Q-13.

| Q | Answer | Change made |
|---|---|---|
| Q-1 | Accept the texts that no spec defined; a PI/lead review can come later | D-141; no code change |
| Q-2 | Add the three tokens to the specs | TRD 04 §4.12 and TRD 11 §4.15 list `--badge-ink`, `--nav-active`, `--nav-hover` (D-142) |
| Q-3 | Agree with the CSS-drawn badge digit | D-143; no code change |
| Q-4 | Align UX-411 with FE-210 | UX-411 now names `alarm_reviewed === false` as the source of truth (D-144) |
| Q-5 | The API should fill `device_code` on `device_silent` events | `backend/services/checkin_service.py` sets it from the day-ledger device; the schema description, `docs/api_reference/openapi.json`, TRD 19 and the skeleton fixture, `lib/api-types.ts` and the R02/R03 DS-07 fixtures are updated; the integration test now expects `device_code: "D02"`; the check-in log uses the field and no longer reads the code from the detail text (D-145) |
| Q-6 | Keep showing the replacement device's resident for D07 | TRD 11 §4.13.4 notes the rule (D-146) |
| Q-7 | Agree: the three most recent dates | UX-056 wording and example (D-147) |
| Q-8 | Correct TST-100 | TRD 13 TST-100 and §8, and TRD 16 CIC-030, now give the D-118 order (D-148) |
| Q-9 | Update the feature files | FEAT-068-AC-07 (Baseline sentence) and FEAT-073 (neutral pills) (D-149) |
| Q-10 | Update TRD 04 §4.8 to the implemented props | 19 component rows updated from the code; `StaffNotes` noted as fetching its own notes (D-150) |
| Q-11 | Firefox, WebKit and `@isolated` in `e2e.yml` satisfy the requirement | D-151 |
| Q-12 | Accept as one PR | D-151 |
| Q-13 | Render (not Railway) is the intended backend host; update all deployment documentation and Block 4 planning | Done in its own documentation PR, GitHub PR #30 (D-153), because it touches about 60 deployment documents and none of the frontend code |

Checks after the changes: Vitest 429 passed; contract tests, `test_residents.py` and the DS-07 UI fixture checks passed (54); `ruff check` and `ruff format --check` clean; the live API returns `device_code: "D02"` for R03's Oct 12 `device_silent` event.
