# FEAT-076 End-to-end test suite and database isolation harness

| Field | Value |
|---|---|
| Epic | Testing & Validation |
| Build phase | Phase 8 (TRD 25) |
| Priority | P0 |
| Complexity | High |
| MVP status | Required |
| Dependencies | FEAT-075, FEAT-055, FEAT-057 |
| Status | Not Started |

## Purpose

Implement the Playwright end-to-end suite that proves the whole stack (PostgreSQL, FastAPI backend with the analytics engine, production Next.js build) behaves as wireframe v0.2 (SRC-21) and the answer key require, together with the database isolation harness that makes the suite repeatable: a `globalSetup` that resets and re-seeds the main E2E database before every browser project, per-role sessions stored once, read-only scenarios that always see the pristine `test_v0_1` seed, a serial `@mutating` group that runs last, and a separate `@isolated` run on a second database `echowell_demo` for the scenarios that need their own roster or the current time. Without this harness the E2E assertions on the resident-list filters "All (10)", "Changed (2)", "Needs attention (2)", "Usual (6)", the nav badge "2" and "Not reviewed yet." would depend on test order. The scenarios and expected values follow TRD 13 Table 4.10-A and TRD 11 §4.13, §4.17.5 and §4.18.8 as rewritten for wireframe v0.2 (TRD 24 D-108 to D-114).

## Business Context

- BR-12, BR-13, BR-14 (Resident list, Resident chart with its six sections, New admissions, Study team; SRC-21): every wireframe v0.2 page and section is exercised through the real UI against pipeline output (TST-100, CIC-032).
- BR-15 (reproduce the answer key): the E2E stack is seeded with DS-07 (`seed test_v0_1`, SRC-05 through ingest plus the pipeline at as-of 2026-10-30 15:00 America/Chicago) and the UI must show the answer-key figures.
- BR-16: role restrictions (E2E-14, E2E-21), no third-party requests and no audio elements (FE-192).
- FR-184 (a check-in accepted by `POST /api/v1/sessions` shows on the dashboard): realised by E2E-15 and the latency test TST-187 in the `@isolated` run.

## Referenced TRDs

- TRD 13 TST-004, TST-005, TST-010, TST-100, TST-101, TST-110, TST-187, §4.10 Table 4.10-A (E2E-01..E2E-21), §8 Implementation Notes (E2E procedure).
- TRD 04 (v0.11) FE-185 (`resident-list.spec.ts`), FE-186 (`resident-chart.spec.ts`), FE-187 (E2E-09 step), FE-188 (`auth.spec.ts`), FE-189 (`admissions.spec.ts`), FE-190 (`a11y.spec.ts`), FE-191 (`responsive.spec.ts`), FE-192 (`privacy.spec.ts`), FE-193 (`review.spec.ts`), FE-194 (`study-team.spec.ts`).
- TRD 11 (v0.13) §4.13 (resident list, chart, Study team devices, New admissions), §4.17.5 (review panels and badges), §4.18.8 (Study team); the UX IDs themselves are owned by FEAT-062..FEAT-075 (BACKLOG.md §5.6 coverage table).
- TRD 16 CIC-030, CIC-031, CIC-032, CIC-034 (the workflow that runs the suite is FEAT-080).
- TRD 15 DEP-017, DEP-119 (Compose `demo` profile and read-only fixture mounts used by the seed).
- TRD 21 ENV-054 (RATE_LIMIT_LOGIN `60/minute` allowed only with APP_ENV `local` or `test`).
- TRD 24 D-108 to D-114 (wireframe v0.2), D-73 (main-database isolation, `@mutating` group, scripts), D-74 (logins and login rate limit in tests), D-67 (meaning of "shows on the dashboard"), D-71 (seeded credentials, `seed test_v0_1 --reset`).
- TRD 14 DS-07, DS-10, TDV-061 (as-of set by an explicit pipeline run), Tables 4.9-B..4.9-E (expected UI values).
- TRD 25 §4.6 Phase 8 (commands, pitfalls), AGT-023 (frontend phase starts only after `pytest tests/validation -q` passes).

## Scope

- `frontend/playwright.config.ts` (main run: `globalSetup` `frontend/tests/e2e/global-setup.ts`, `grepInvert: /@isolated/`, `retries: 1` in CI and `0` locally, projects `chromium`, `firefox`, `webkit`, `baseURL` from `E2E_BASE_URL`).
- `frontend/playwright.isolated.config.ts` (`globalSetup` `frontend/tests/e2e/isolated-setup.ts`, `grep: /@isolated/`, `workers: 1`, `fullyParallel: false`, single file `frontend/tests/e2e/isolated.spec.ts`).
- `frontend/tests/e2e/global-setup.ts`: `docker compose exec -T backend python -m backend.cli seed test_v0_1 --reset`, then `docker compose exec -T backend python database/seeds/load_evaluation_ground_truth.py tests/fixtures/answer_key/evaluation_ground_truth_v0_1.csv`, then `docker compose restart backend` and a wait for `/api/v1/health`, then one `POST /api/v1/auth/login` per role (admin, clinician, researcher) stored as `frontend/tests/e2e/.auth/<role>.json` (git-ignored).
- `frontend/tests/e2e/isolated-setup.ts`: no reset and no seed; one login per role against the `echowell_demo` backend into `frontend/tests/e2e/.auth/isolated-<role>.json`.
- A role fixture that writes the stored token into `sessionStorage` with `page.addInitScript` before the first navigation (D-74; the token lives in `sessionStorage`, TRD 12 SEC-037).
- Scenario files under `frontend/tests/e2e/`: `resident-list.spec.ts` (FE-185, E2E-03..E2E-06), `resident-chart.spec.ts` (FE-186, E2E-08, E2E-10..E2E-12), `review.spec.ts` (FE-193 read-only part, E2E-17), `study-team.spec.ts` (FE-194, E2E-07, E2E-20, E2E-21), `auth.spec.ts` (FE-188, E2E-01, E2E-02, E2E-14), `admissions.spec.ts` (FE-189, E2E-13), `responsive.spec.ts` (FE-191, E2E-16), `privacy.spec.ts` (FE-192), `mutating.spec.ts` (D-73 group: E2E-18, then E2E-09 implemented by FE-187, then the FE-193 reminder step on R10), `isolated.spec.ts` (E2E-15, TST-187, E2E-19 in this order).
- `frontend/package.json` scripts exactly `test:e2e:readonly` (`playwright test --grep-invert "@isolated|@mutating"`), `test:e2e:mutating` (`playwright test --grep @mutating --workers=1`), `test:e2e:isolated` (`playwright test -c playwright.isolated.config.ts --project=chromium --workers=1`); no bare `test:e2e` script.
- The demo-overlay roster `tests/fixtures/seeds/demo_overlay/` (`facilities.csv` Edgewood, `residents.csv` R11 F longitudinal enrolled 2026-10-01, `devices.csv` D11 fw-1.0.0, `device_assignments.csv` R11–D11 from 2026-10-01) in the TRD 06 DB-060 format.
- Running `a11y.spec.ts` inside the read-only run (its route list and assertions are owned by FEAT-075).

## Out of Scope

- The `e2e.yml` workflow, the nightly three-browser schedule, the `performance`, `lighthouse` and `nightly-validation` jobs (FEAT-080).
- Content of `a11y.spec.ts` and the keyboard-only test (FEAT-075, TST-110, TST-111).
- Component and page tests with Vitest/MSW (delivered with each page feature, TST-090..TST-097), including FE-205 snooze expiry with fake timers.
- Post-deploy smoke tests (FEAT-086).
- Any change to expected values of the answer key (AGT-008); any test-only API endpoint (D-73: no test-hook endpoint exists).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-076-FR-01 | E2E tests shall live under `frontend/tests/e2e/` with `frontend/playwright.config.ts` and run against the Compose `demo` profile stack (db, backend :8000, `frontend-prod` :3001). | TST-004, DEP-017, CIC-030 |
| FEAT-076-FR-02 | `global-setup.ts` shall, at the start of every main-run invocation (one per browser project and group), reset and re-seed the main E2E database with `seed test_v0_1 --reset` plus the DS-10 loader, restart the backend container and wait for `/api/v1/health`, then log in once per role through `POST /api/v1/auth/login` and store each session in `frontend/tests/e2e/.auth/<role>.json`. | D-73, D-74 (a), CIC-030 |
| FEAT-076-FR-03 | Scenarios other than E2E-01, E2E-02 and FE-188 shall not submit the login form; they shall reuse the stored per-role session through a fixture that writes the token into `sessionStorage` via `page.addInitScript`. | D-74 (a), TRD 13 §4.10 |
| FEAT-076-FR-04 | Every scenario of Table 4.10-A shall be implemented with the expected values of that table, of TRD 14 Tables 4.9-B..4.9-E and of TRD 11 §4.13, §4.17.5 and §4.18.8, asserting at minimum the CIC-032 list as updated for v0.2: login and data bar "Test data only (pipeline test data v0.1, Oct 1–30, 2026). No real residents. No audio is stored or played anywhere in EchoWell."; nav "Resident list" badge "2"; filters "All (10)", "Changed (2)", "Needs attention (2)", "Usual (6)"; default order R09, R10, R03, R08, R01, R02, R04, R05, R06, R07 with their pills and "What's happening" texts; R09 Summary "Oct 21" / "9 days" / "Not reviewed", "Leaning most: more pauses, quieter, less voiced sound", tile "Change score 26.8"; R10 "6 days", "Change score 13.4"; R09 Voice trends "Alarm line: 5", "Baseline Oct 1–16", 7 measurement cards; R08 "! Needs attention" and "Not scored yet"; R07 restart texts; `/study` data problems R08, R03, R05, D02, "281 of 300 expected", "267 of 300 expected", the alarm timing table and the three device rows; clinician refused `/study`; New admissions note. | TST-100, CIC-032, E2E-01..E2E-21 |
| FEAT-076-FR-05 | Scenarios that save a review, a note or a snooze shall be tagged `@mutating` and live only in `frontend/tests/e2e/mutating.spec.ts`, run serially in the order E2E-18 (R09); the FE-193 snooze step on R10; E2E-09 (implemented by FE-187, on R10), after all read-only scenarios of the same project. | D-73, D-118, TST-100, FE-187, FE-193 |
| FEAT-076-FR-06 | E2E-18 shall, on `/residents/R09/review`, first click "Save review" without a choice ("Choose what you found.", nothing saved), then save "Checked on resident, no concern" and assert "Review saved.", the review in "Previous reviews", R09 Summary "Reviewed", the list text "Changed from their usual since Oct 21. Reviewed.", nav badge "1", R09's "Review and notes" badge gone, pill "▲ Changed" and change score 26.8 unchanged. | E2E-18, OQ-05 |
| FEAT-076-FR-07 | E2E-09/FE-187 shall, on `/residents/R10/review` (independent of E2E-18, D-118), add the "Observation" note "Resident has a cold; nurse notified." ("Note saved.", note listed with time, type and author), then save a review with "Cold, cough or sore throat" and "Explained by a known cause", and assert the review in "Previous reviews", R10 "Reviewed", the pill still "▲ Changed" and the change score 13.4 unchanged. | E2E-09, FE-187, OQ-05, D-118 |
| FEAT-076-FR-08 | The `@isolated` scenarios shall run only through `playwright.isolated.config.ts`, serially in Chromium, against the database `echowell_demo` (seeded with `seed test_v0_1 --master-only` and `import-master-data --dir tests/fixtures/seeds/demo_overlay`, PIPELINE_AS_OF empty), in the order E2E-15, TST-187, E2E-19; `isolated-setup.ts` shall never reset or seed. | TST-004, CIC-030, D-73, D-74 |
| FEAT-076-FR-09 | E2E-15 shall POST one valid record for R11 with `timestamp_utc` = current UTC time and session ID `R11-<facility-local YYYYMMDD>-01` using the seeded API key, reload `/residents` and assert the R11 row (last check-in = facility-local time of the record, pill "○ Learning", "Learning their usual: 1 of 16 check-ins so far."), in R11's chart the 30-day used count 1, no change score bar and a check-in log with only "<Mon D> Check-ins started." (no event for the usable check-in), and R01–R10 rows unchanged. | E2E-15, FR-184, D-67, UX-144 |
| FEAT-076-FR-10 | TST-187 shall POST a further R11 record (`R11-<facility-local date>-02`) and fail when more than 5 s pass between the 201 response and a reload of `/residents` showing the new "Last check-in" on the R11 row (and the increased 30-day used count in R11's chart). | TST-187, NFR-011, SC-03 |
| FEAT-076-FR-11 | E2E-19 shall, as admin, upload the SRC-05 CSV to `POST /api/v1/ingest`, wait for the batch, run `POST /api/v1/pipeline/run` with `as_of` 2026-10-30T15:00:00-05:00, click "Remind me in 24 hours" on `/residents/R10/review` without advancing any clock, and assert "Reminder set for <Mon D, h:mm AM/PM CT>. The alarm stays on.", the reminder line, review status "Not reviewed", unchanged status and `snoozed_until` = click time + 24 h ± 2 min from `GET /api/v1/alerts`. | E2E-19, TST-065, D-73 |
| FEAT-076-FR-12 | `frontend/package.json` shall define exactly the scripts `test:e2e:readonly`, `test:e2e:mutating` and `test:e2e:isolated` with the commands of D-73 and no bare `test:e2e`. | D-73, TST-004 |
| FEAT-076-FR-13 | Playwright shall run with `retries: 1` in CI and `retries: 0` locally; a scenario that passes only on retry shall be reported as flaky. | TST-101, TST-161 |
| FEAT-076-FR-14 | `privacy.spec.ts` shall assert that no request targets a host other than the frontend origin and `NEXT_PUBLIC_API_BASE_URL` (in particular no font service) and that no `<audio>` or `<video>` element exists on any route. | FE-192, TPS-050, TPS-081 |
| FEAT-076-FR-15 | `responsive.spec.ts` shall load `/residents`, `/residents/R09` and `/residents/R09/trends` at 320×568, 360×800, 375×812 and 390×844 and assert `document.documentElement.scrollWidth <= window.innerWidth` and the scrolling chart navigation row; E2E-16 shall assert the same at those widths plus table and chart scrolling within their containers and touch targets ≥ 44 px. | FE-191, E2E-16, D-78 |
| FEAT-076-FR-16 | The E2E stack shall use RATE_LIMIT_LOGIN=`60/minute` (APP_ENV `local`), and E2E credentials shall be the SEED_* values supplied by the environment, never literals in test code. | D-74 (b), ENV-054, CIC-034 |
| FEAT-076-FR-17 | E2E scenarios shall depend on the current time only where stated (E2E-15, TST-187, E2E-19) and otherwise on the documented D-73 order. | TST-005 |

## Inputs

- The running Compose `demo` stack (FEAT-077) with `.env` from `.env.development.example` and per-job SEED_ADMIN_PASSWORD, SEED_CLINICIAN_PASSWORD, SEED_RESEARCHER_PASSWORD, SEED_INGEST_API_KEY.
- DS-07 produced by `python -m backend.cli seed test_v0_1` (roster `database/seeds/test_v0_1/`, SRC-05 copy `tests/fixtures/pipeline_input/EchoWell_pipeline_test_input_v0_1.csv`; FEAT-055) and DS-10 `tests/fixtures/answer_key/evaluation_ground_truth_v0_1.csv` (FEAT-057).
- The demo-overlay roster `tests/fixtures/seeds/demo_overlay/` (this feature).
- Environment variable `E2E_BASE_URL` (`http://localhost:3001`).

## Outputs

- Playwright specs, two configs, two setup scripts and the role fixture under `frontend/`.
- `frontend/tests/e2e/.auth/<role>.json` and `.auth/isolated-<role>.json` at run time (git-ignored, never committed).
- `frontend/playwright-report/` (HTML report, traces of failures), uploaded as a CI artifact by FEAT-080, never committed (TRD 13 §8).
- New rows created by the `@mutating` and `@isolated` scenarios (one `alert_reviews` row, one `staff_notes` row, an alert snooze, two R11 records) on databases that are reset before the next invocation.

## Data Flow

1. `global-setup.ts` → `seed test_v0_1 --reset` (D-71: `alembic downgrade base`, `alembic upgrade head`, roster, users, API key, SRC-05 ingest, pipeline at as-of 2026-10-30 15:00 CT) → DS-10 loader → backend restart (empty pool and login limiter) → three logins → storage-state files.
2. `test:e2e:readonly` → read-only scenarios read `/residents`, `/residents/[residentCode]` and its sections, `/admissions`, `/study`, `/admin` through the backend API.
3. `test:e2e:mutating` → a new `global-setup.ts` invocation re-seeds, then `mutating.spec.ts` posts a review on R09, then a snooze, a note and a review on R10 through the UI (D-118) (`POST /api/v1/alerts/{id}/reviews`, `POST /api/v1/residents/{code}/notes`, `POST /api/v1/alerts/{id}/snooze`).
4. `e2e.yml` (FEAT-080) creates and seeds `echowell_demo` and restarts the backend on it → `test:e2e:isolated` → `isolated-setup.ts` logs in → `isolated.spec.ts` posts R11 records to `POST /api/v1/sessions` (API key), ingests SRC-05 and runs the pipeline for E2E-19.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-075, FEAT-055, FEAT-057

- [FEAT-075](FEAT-075-Accessibility-And-Responsive-Conformance.md) Accessibility and responsive conformance: all pages and `a11y.spec.ts` exist, so the suite runs against finished pages.
- [FEAT-055](FEAT-055-Pipeline-Operator-CLI-And-Full-Test.md) Pipeline operator CLI and full `test_v0_1` seed: `seed test_v0_1 [--reset] [--master-only]` used by `global-setup.ts` and `e2e.yml`.
- [FEAT-057](FEAT-057-Golden-Fixtures-Answer-Key-Integrity-And.md) Golden fixtures and the DS-10 ground-truth loader used for E2E-20.

The Compose `demo` profile is completed by FEAT-077 and the workflow by FEAT-080; locally the suite runs against `docker compose --profile demo up -d db backend frontend-prod`.

Features that build directly on this one (BACKLOG.md §4): FEAT-080, FEAT-090.

## Database Impact

- Tables used (through the API only): `residents`, `devices`, `device_assignments`, `raw_sessions`, `processed_sessions`, `day_ledger`, `baselines`, `scores`, `cusum_state`, `alerts`, `alert_reviews`, `staff_notes`, `data_alerts`, `pipeline_runs`, `evaluation_ground_truth`, `users`, `api_keys`, `audit_logs` (TRD 20 §4.6).
- Tables created: none. Databases: `echowell_demo` is created by the workflow step of FEAT-080; the main E2E database is recreated by `seed test_v0_1 --reset` (`reset-test-db`, D-71).
- Tables modified: none structurally; rows are written only by normal API calls on test databases.

## API Impact

- Consumed: `POST /api/v1/auth/login`, `GET /api/v1/health`, `GET /api/v1/residents`, `GET /api/v1/residents/{resident_code}` and its `/checkins`, `/features`, `/notes`, `GET /api/v1/scores`, `GET /api/v1/devices`, `GET /api/v1/alerts`, `GET /api/v1/data-alerts`, `POST /api/v1/alerts/{id}/reviews`, `POST /api/v1/alerts/{id}/snooze`, `POST /api/v1/residents/{resident_code}/notes`, `GET /api/v1/analytics`, `GET /api/v1/admissions`, `POST /api/v1/sessions`, `POST /api/v1/ingest`, `GET /api/v1/ingest/batches/{id}`, `POST /api/v1/pipeline/run` (TRD 19).
- Exposed: none (no test-hook endpoint, D-73).

## Frontend Impact

- Pages exercised: `/login`, `/residents`, `/residents/[residentCode]` with `/review`, `/trends`, `/baseline`, `/log`, `/device`, `/admissions`, `/study` (with `#devices`), `/admin` (D-23 as amended by D-110).
- Files added: `frontend/playwright.config.ts`, `frontend/playwright.isolated.config.ts`, `frontend/tests/e2e/*.spec.ts`, `global-setup.ts`, `isolated-setup.ts`, the role fixture; `frontend/package.json` scripts; `.gitignore` entry for `frontend/tests/e2e/.auth/`.
- No production component is changed; components are located by accessible names and texts of TRD 11.

## Analytics Impact

None directly. The suite asserts outputs of the pipeline (display statuses and filter counts, change score bars, tallies 26.830256 / 13.418183 shown as 26.8 / 13.4, data problems, Study team KPIs) produced by FEAT-040..FEAT-052 but computes nothing.

## Security Requirements

- Logins use the seeded users `admin@example.com`, `clinician@example.com`, `researcher@example.com` with per-job SEED_* passwords; no credential literal is committed (CIC-034, D-71).
- Storage-state files are git-ignored and never uploaded as artifacts.
- Role checks: E2E-14 (clinician on `/admin` sees "You do not have access to this page."), E2E-21 (clinician refused `/study`; researcher sees the read-only review and note texts and a direct `POST /alerts/{id}/reviews` returns 403).
- Only synthetic data (SRC-05, R11 overlay) is used (AGT-014, AGT-017).

## Error Handling

- `global-setup.ts` fails the invocation (non-zero exit, no scenario runs) when the reset, seed, loader, restart, health wait or any role login fails, printing the failing step but never a credential.
- Retries: one retry in CI (TST-101); a test passing only on retry is reported flaky and handled as an S3 defect when repeated (TST-161).
- On failure, traces and screenshots go to `frontend/playwright-report/`; Compose logs are collected by FEAT-080.

## Logging Requirements

- No application logging is added. The suite relies on the backend's `request_completed` lines and audit rows; E2E-02 asserts an audit row "failed login" (action `auth.login.failed`, TRD 12 §4.12, TST-053).
- Setup scripts log step names and durations to stdout without secrets (masked by the workflow, CIC-034).

## Testing Requirements

- E2E scenarios: E2E-01..E2E-21 (Table 4.10-A), FE-185..FE-193, TST-187; accessibility `a11y.spec.ts` (TST-110, run here, owned by FEAT-075).
- Commands (TRD 25 §4.6 Phase 8): `cd frontend && npm run test:e2e:readonly -- --project=chromium && npm run test:e2e:mutating -- --project=chromium`; `npm run test:e2e:isolated` after the `echowell_demo` preparation of CIC-030.
- Regression: the read-only run executed twice in a row against the same stack produces identical results (pristine seed per invocation, D-73).
- Algorithm validation: not in this feature (FEAT-059); E2E asserts the UI view of the same figures.

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-076-AC-01 | `npm run test:e2e:readonly -- --project=chromium` passes every read-only scenario of Table 4.10-A (all except E2E-09, E2E-15, E2E-18, E2E-19 and TST-187) plus `a11y.spec.ts`. | TST-100, AC-TST-07, CIC-032 |
| FEAT-076-AC-02 | `npm run test:e2e:mutating -- --project=chromium` passes E2E-18, the FE-193 reminder step and E2E-09/FE-187, in that order, with `--workers=1`. | D-73, D-118, FE-187, FE-193 |
| FEAT-076-AC-03 | Running `test:e2e:mutating` and then `test:e2e:readonly` again on the same stack still yields "Changed (2)", the nav badge "2" and R09 "Changed from their usual since Oct 21. Not reviewed yet." (the re-seed restores the pristine seed). | D-73, E2E-03, E2E-17 |
| FEAT-076-AC-04 | `npm run test:e2e:isolated` passes E2E-15, TST-187 (≤ 5 s) and E2E-19 against `echowell_demo`, and the main database still holds exactly 10 residents afterwards. | TST-187, NFR-011, CIC-030 |
| FEAT-076-AC-05 | `grep -c '"test:e2e"' frontend/package.json` returns 0 and the three scripts of D-73 are present with the documented commands. Verified by: Inspection (run the command in the criterion and check its output). | D-73 |
| FEAT-076-AC-06 | Only `auth.spec.ts` (E2E-01, E2E-02, FE-188) contains form logins; `git grep -n "fill(.*password" frontend/tests/e2e` lists only that file. | D-74 (a) |
| FEAT-076-AC-07 | `git ls-files frontend/tests/e2e/.auth` returns nothing. | CIC-034, SEC-050 |
| FEAT-076-AC-08 | With the main run in Firefox and WebKit (`--project=firefox`, `--project=webkit`) every main-run scenario passes. | TST-100, TST-151 |

## Definition of Done

- All FEAT-076 acceptance criteria pass locally on the Compose `demo` stack.
- Requirement IDs appear in test titles or `// req: <ID>` comments (TST-012, TST-013).
- No mock data imported by production code (TST-095 still passes); frontend coverage gate unaffected.
- Batch report lists scenario IDs, commands and results (AGT-022); PR approved by the algorithm lead (AGT-013).

## Implementation Notes

- Playwright `storageState` does not capture `sessionStorage`; use the role fixture with `page.addInitScript` (D-74).
- Restart the backend after every reset: psycopg prepared statements are disabled by API-125, but the in-memory login limiter and pool must start empty (D-73).
- Dates on screen are facility-local (America/Chicago); compute E2E-15 expectations with the facility time zone, not the runner's.
- Locate elements by role and accessible name (TRD 11 texts) rather than CSS classes so the tests double as accessibility checks.
- Keep `mutating.spec.ts` as the single definition of the D-73 group; do not tag scenarios `@mutating` in other files.
- `E2E-19` must not advance any clock; reminder expiry is TST-065 and FE-205.
- The v0.1 spec files `overview.spec.ts`, `resident-detail.spec.ts`, `alerts.spec.ts` and the analytics spec are renamed `resident-list.spec.ts`, `resident-chart.spec.ts`, `review.spec.ts` and `study-team.spec.ts` (TRD 04 v0.11).
