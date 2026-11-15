# End-to-end test suite and database isolation harness

## Feature Description

The Playwright end-to-end suite under `frontend/tests/e2e/` proves the whole stack (PostgreSQL, FastAPI backend with the analytics engine, production Next.js build `frontend-prod` on :3001) against wireframe v0.2 and the answer key (FEAT-076; TRD 13 Table 4.10-A E2E-01..E2E-21, TST-100, TST-187; TRD 04 FE-185..FE-194; TRD 24 D-73, D-74, D-118). The isolation harness makes it repeatable: `global-setup.ts` resets and re-seeds the main database (`seed test_v0_1 --reset` plus the DS-10 loader), restarts the backend, waits for `/api/v1/health` and stores one session per role in `frontend/tests/e2e/.auth/<role>.json`; read-only scenarios always see the pristine seed; the serial `@mutating` group (E2E-18 on R09, FE-193 reminder step on R10, E2E-09/FE-187 on R10) runs last; the `@isolated` scenarios (E2E-15, TST-187, E2E-19) run only through `playwright.isolated.config.ts` on the second database `echowell_demo`. The three npm scripts are `test:e2e:readonly`, `test:e2e:mutating`, `test:e2e:isolated`; there is no bare `test:e2e`.

## Preconditions

- Docker and Docker Compose; repository at the commit under test; `cp .env.development.example .env`, then set `RATE_LIMIT_LOGIN=60/minute` in `.env` (D-74, ENV-054).
- Stack: `docker compose --profile demo up -d --build --wait db backend frontend-prod`; `docker compose exec -T backend python -m backend.cli seed test_v0_1`.
- Shell exports `SEED_ADMIN_PASSWORD`, `SEED_CLINICIAN_PASSWORD`, `SEED_RESEARCHER_PASSWORD`, `SEED_INGEST_API_KEY` with the same values as `.env` (never typed into a test file or this record).
- `cd frontend && npm ci && npx playwright install --with-deps chromium firefox webkit`.
- `pytest tests/validation -q` passes (AGT-023).
- Local stack only; never run against staging or production.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-076-01 | Read-only run in Chromium passes every read-only scenario plus `a11y.spec.ts` | High | Positive |
| TC-076-02 | Mutating run passes E2E-18, FE-193 reminder step, E2E-09/FE-187 in order with one worker | High | Positive |
| TC-076-03 | Read-only run after the mutating run still sees the pristine seed | High | Positive |
| TC-076-04 | Isolated run on `echowell_demo` passes E2E-15, TST-187 (≤ 5 s), E2E-19; main DB keeps 10 residents | High | Positive |
| TC-076-05 | `package.json` has exactly the three D-73 scripts and no bare `test:e2e` | High | Documentation |
| TC-076-06 | Only `auth.spec.ts` submits the login form | High | Security |
| TC-076-07 | `.auth` session files are never tracked | High | Security |
| TC-076-08 | Main run passes in Firefox and WebKit | High | Positive |
| TC-076-09 | Seeded values on the stack match the CIC-032 list (manual walk-through) | High | UI |
| TC-076-10 | "Save review" without a choice saves nothing (E2E-18 first step, manual) | Medium | Negative |
| TC-076-11 | `global-setup.ts` failure stops the invocation without printing a credential | High | Negative |
| TC-076-12 | Retries: 1 in CI, 0 locally; flaky tests reported | Medium | Positive |
| TC-076-13 | Privacy spec: no third-party host, no `<audio>`/`<video>` | High | Security |
| TC-076-14 | Credentials only from `SEED_*`; login limit 60/minute only on the E2E stack | Medium | Security |
| TC-076-15 | Read-only run twice in a row gives identical results | Medium | Positive |
| TC-076-16 | E2E-02 failed login writes an `auth.login.failed` audit row | Medium | Database |

### TC-076-01 Read-only run in Chromium passes every read-only scenario plus `a11y.spec.ts`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `cd frontend && npm run test:e2e:readonly -- --project=chromium`. | `global-setup.ts` prints its steps (reset, seed, DS-10 loader, `docker compose restart backend`, health wait, logins) and no secret value. |
| 2 | Read the result line. | All tests passed, 0 failed, 0 flaky; specs `auth`, `resident-list`, `resident-chart`, `review`, `study-team`, `admissions`, `privacy`, `responsive`, `a11y` ran; no test tagged `@mutating` or `@isolated` ran. |
| 3 | Open `frontend/playwright-report/index.html`. | Every Table 4.10-A scenario except E2E-09, E2E-15, E2E-18, E2E-19 and TST-187 is listed as passed. |

### TC-076-02 Mutating run passes E2E-18, FE-193 reminder step, E2E-09/FE-187 in order with one worker

| Step | Action | Expected Result |
|---|---|---|
| 1 | `npm run test:e2e:mutating -- --project=chromium`. | Command runs `playwright test --grep @mutating --workers=1`; output shows 1 worker. |
| 2 | Read the order of results. | "(1) E2E-18 save review on R09", "(2) FE-193 reminder step on R10", "(3) E2E-09 / FE-187 staff note and review on R10" — all passed, in this order. |
| 3 | `grep -rln "@mutating" tests/e2e`. | Only `tests/e2e/mutating.spec.ts`. |

### TC-076-03 Read-only run after the mutating run still sees the pristine seed

| Step | Action | Expected Result |
|---|---|---|
| 1 | Directly after TC-076-02, sign in as clinician at `http://localhost:3001` and open `/residents`. | R09 shows "Reviewed" text and the nav badge "1" (state left by E2E-18). |
| 2 | `npm run test:e2e:readonly -- --project=chromium`. | All passed (re-seed by `global-setup.ts`). |
| 3 | Reload `/residents` after the run. | Filters "All (10)", "Changed (2)", "Needs attention (2)", "Usual (6)"; nav badge "2"; R09 text "Changed from their usual since Oct 21. Not reviewed yet." |

### TC-076-04 Isolated run on `echowell_demo` passes E2E-15, TST-187 (≤ 5 s), E2E-19; main DB keeps 10 residents

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run the commands of the `e2e.yml` step "Isolated database echowell_demo for E2E-15, E2E-19, TST-187" from the repository root. | `CREATE DATABASE`; provisioning succeeds; backend restarted on `echowell_demo` with `PIPELINE_AS_OF` empty; health 200; `seed test_v0_1 --master-only` and `import-master-data --dir tests/fixtures/seeds/demo_overlay` exit 0. |
| 2 | `cd frontend && npm run test:e2e:isolated`. | Uses `playwright.isolated.config.ts`, Chromium, 1 worker; "E2E-15 new check-in appears", "TST-187 a posted check-in shows within 5 s", "E2E-19 reminder (snooze) without advancing any clock" pass in this order. |
| 3 | `docker compose exec -T db psql -U echowell -d echowell -tA -c "SELECT count(*) FROM residents"`. | `10` (main database untouched). |
| 4 | `docker compose exec -T db psql -U echowell -d echowell_demo -tA -c "SELECT count(*) FROM raw_sessions r JOIN residents s ON s.id = r.resident_id WHERE s.resident_code = 'R11'"`. | ≥ 2 (E2E-15 and TST-187 records for R11). |
| 5 | Inspect `tests/e2e/isolated-setup.ts`. | No reset and no seed call; it only logs in once per role. |

### TC-076-05 `package.json` has exactly the three D-73 scripts and no bare `test:e2e`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -c '"test:e2e"' frontend/package.json`. | `0`. |
| 2 | `grep -n '"test:e2e:' frontend/package.json`. | Exactly three lines: `"test:e2e:readonly": "playwright test --grep-invert \"@isolated|@mutating\""`, `"test:e2e:mutating": "playwright test --grep @mutating --workers=1"`, `"test:e2e:isolated": "playwright test -c playwright.isolated.config.ts --project=chromium --workers=1"`. |

### TC-076-06 Only `auth.spec.ts` submits the login form

| Step | Action | Expected Result |
|---|---|---|
| 1 | `git grep -n "fill(.*password" frontend/tests/e2e`. | Matches only in `frontend/tests/e2e/auth.spec.ts`. |
| 2 | Open `frontend/tests/e2e/fixtures.ts`. | Role sessions are injected into `sessionStorage` through `page.addInitScript`; no form login. |

### TC-076-07 `.auth` session files are never tracked

| Step | Action | Expected Result |
|---|---|---|
| 1 | After TC-076-01, `ls frontend/tests/e2e/.auth`. | `admin.json`, `clinician.json`, `researcher.json` exist locally. |
| 2 | `git ls-files frontend/tests/e2e/.auth`. | No output. |
| 3 | `git check-ignore -v frontend/tests/e2e/.auth/admin.json`. | Matched by `.gitignore` entry `frontend/tests/e2e/.auth/`. |

### TC-076-08 Main run passes in Firefox and WebKit

| Step | Action | Expected Result |
|---|---|---|
| 1 | `npm run test:e2e:readonly -- --project=firefox && npm run test:e2e:mutating -- --project=firefox`. | All passed. |
| 2 | Same with `--project=webkit`. | All passed. |

### TC-076-09 Seeded values on the stack match the CIC-032 list (manual walk-through)

| Step | Action | Expected Result |
|---|---|---|
| 1 | After a re-seed (`seed test_v0_1 --reset`, DS-10 loader, `docker compose restart backend`), open `http://localhost:3001/login`. | Data bar "Test data only (pipeline test data v0.1, Oct 1–30, 2026). No real residents. No audio is stored or played anywhere in EchoWell." |
| 2 | Sign in as clinician; read `/residents`. | Nav "Resident list" badge "2"; filters "All (10)", "Changed (2)", "Needs attention (2)", "Usual (6)"; order R09, R10, R03, R08, R01, R02, R04, R05, R06, R07. |
| 3 | Open `/residents/R09`. | "Oct 21", "9 days", "Not reviewed"; "Leaning most: more pauses, quieter, less voiced sound"; tile "Change score 26.8". |
| 4 | Open `/residents/R10`. | "6 days", "Change score 13.4". |
| 5 | Open `/residents/R09/trends`. | "Alarm line: 5", "Baseline Oct 1–16", 7 measurement cards. |
| 6 | Open `/residents/R08`. | "! Needs attention" and "Not scored yet". |
| 7 | Sign in as researcher; open `/study`. | Data problems for R08, R03, R05, D02; "281 of 300 expected" and "267 of 300 expected"; alarm timing table; three device rows. |
| 8 | Sign in as clinician; open `/study`. | Access refused ("You do not have access to this page."). |
| 9 | Open `/admissions`. | The New admissions note of E2E-13. |

### TC-076-10 "Save review" without a choice saves nothing (E2E-18 first step, manual)

| Step | Action | Expected Result |
|---|---|---|
| 1 | On a fresh seed, sign in as clinician, open `/residents/R09/review`, click "Save review" without selecting a finding. | Message "Choose what you found."; no `POST` to the review endpoint succeeds. |
| 2 | `SELECT count(*) FROM alert_reviews;` before and after. | Count unchanged. |
| 3 | Re-seed (`seed test_v0_1 --reset`, `docker compose restart backend`). | Pristine seed restored. |

### TC-076-11 `global-setup.ts` failure stops the invocation without printing a credential

| Step | Action | Expected Result |
|---|---|---|
| 1 | `docker compose stop backend`; then `npm run test:e2e:readonly -- --project=chromium`. | Invocation exits non-zero; the failing step is printed; no scenario runs. |
| 2 | Search the console output for the values of `SEED_ADMIN_PASSWORD` and `SEED_INGEST_API_KEY`. | Not present. |
| 3 | `unset SEED_ADMIN_PASSWORD`, `docker compose start backend`, run again. | Invocation fails at the admin login step; no scenario runs. |

### TC-076-12 Retries: 1 in CI, 0 locally; flaky tests reported

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -n "retries" frontend/playwright.config.ts`. | `retries: process.env.CI ? 1 : 0`. |
| 2 | Open the latest `e2e.yml` run report (artifact `playwright-report`). | Any test passing only on retry is marked "flaky" in the report. |

### TC-076-13 Privacy spec: no third-party host, no `<audio>`/`<video>`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `npx playwright test tests/e2e/privacy.spec.ts --project=chromium`. | "FE-192 only the frontend origin and the API origin are contacted; no audio or video" passes. |
| 2 | Manual: Network panel on `/login`, `/residents`, `/residents/R09`, `/study`. | Requests only to `http://localhost:3001` and `NEXT_PUBLIC_API_BASE_URL` (`http://localhost:8000`); no font service host. |
| 3 | `document.querySelectorAll('audio, video').length` on each route. | `0`. |

### TC-076-14 Credentials only from `SEED_*`; login limit 60/minute only on the E2E stack

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -rn "SEED_" frontend/tests/e2e/*.ts`. | Passwords read from `process.env[\`SEED_${role}_PASSWORD\`]` and `process.env.SEED_INGEST_API_KEY`; no literal password. |
| 2 | `docker compose exec -T backend env | grep -E "^(APP_ENV|RATE_LIMIT_LOGIN)="`. | `APP_ENV=local`, `RATE_LIMIT_LOGIN=60/minute`. |
| 3 | `grep -n "^RATE_LIMIT_LOGIN" .env.development.example .env.production.example`. | Both `5/minute` (60/minute only by the E2E `.env` edit). |

### TC-076-15 Read-only run twice in a row gives identical results

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `npm run test:e2e:readonly -- --project=chromium` twice. | Both runs pass with the same number of passed tests and 0 failed. |

### TC-076-16 E2E-02 failed login writes an `auth.login.failed` audit row

| Step | Action | Expected Result |
|---|---|---|
| 1 | `npx playwright test tests/e2e/auth.spec.ts --project=chromium`. | E2E-01, E2E-02, FE-188 pass. |
| 2 | `docker compose exec -T db psql -U echowell -d echowell -tA -c "SELECT count(*) FROM audit_logs WHERE action='auth.login.failed'"`. | ≥ 1. |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `GET http://localhost:8000/api/v1/health` after `global-setup.ts` | 200 |
| 2 | `POST /api/v1/auth/login` per role with `SEED_*` values (as `global-setup.ts`) | 200 with a token for each role |
| 3 | `POST /api/v1/sessions` with `X-API-Key: $SEED_INGEST_API_KEY` and an R11 record (E2E-15, isolated DB) | 201 |
| 4 | `GET /api/v1/alerts` after E2E-19 | R10 alert `snoozed_until` = click time + 24 h ± 2 min |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT count(*) FROM residents;` on `echowell` after the isolated run | 10 |
| 2 | R11 records in `echowell_demo` (TC-076-04 step 4) | ≥ 2 |
| 3 | `SELECT count(*) FROM audit_logs WHERE action='auth.login.failed';` after E2E-02 | ≥ 1 |
| 4 | After a read-only run, the R09 alert has no review row | Pristine seed (no review saved) |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Backend stopped before a run (TC-076-11) | Invocation fails, no scenario runs, no credential printed |
| 2 | `SEED_ADMIN_PASSWORD` missing (TC-076-11) | Fails at the admin login |
| 3 | "Save review" without a choice (TC-076-10) | "Choose what you found."; nothing saved |
| 4 | Run `npx playwright test` with the main config and `--grep @isolated` | No test runs (main config has `grepInvert: /@isolated/`) |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-076-AC-01 | `npm run test:e2e:readonly -- --project=chromium` passes every read-only Table 4.10-A scenario plus `a11y.spec.ts` | TC-076-01, TC-076-09 |
| FEAT-076-AC-02 | `npm run test:e2e:mutating -- --project=chromium` passes E2E-18, FE-193 step, E2E-09/FE-187 in order with `--workers=1` | TC-076-02 |
| FEAT-076-AC-03 | Mutating then read-only still yields "Changed (2)", badge "2" and R09 "Changed from their usual since Oct 21. Not reviewed yet." | TC-076-03 |
| FEAT-076-AC-04 | `npm run test:e2e:isolated` passes E2E-15, TST-187 (≤ 5 s), E2E-19 on `echowell_demo`; main DB holds 10 residents | TC-076-04 |
| FEAT-076-AC-05 | `grep -c '"test:e2e"' frontend/package.json` returns 0; three D-73 scripts present | TC-076-05 |
| FEAT-076-AC-06 | `git grep -n "fill(.*password" frontend/tests/e2e` lists only `auth.spec.ts` | TC-076-06 |
| FEAT-076-AC-07 | `git ls-files frontend/tests/e2e/.auth` returns nothing | TC-076-07 |
| FEAT-076-AC-08 | Main run passes in Firefox and WebKit | TC-076-08 |

## Test Data Requirements

- `test_v0_1` seed (R01–R10, SRC-05, pipeline run at as-of 2026-10-30T15:00:00-05:00) and DS-10 (`tests/fixtures/answer_key/evaluation_ground_truth_v0_1.csv` via `database/seeds/load_evaluation_ground_truth.py`).
- `echowell_demo`: `seed test_v0_1 --master-only` plus `tests/fixtures/seeds/demo_overlay` (R11, N01), `PIPELINE_AS_OF` empty.
- Environment: `SEED_ADMIN_PASSWORD`, `SEED_CLINICIAN_PASSWORD`, `SEED_RESEARCHER_PASSWORD`, `SEED_INGEST_API_KEY`, `RATE_LIMIT_LOGIN=60/minute`, optional `E2E_BASE_URL`, `E2E_API_BASE_URL`, `FACILITY_TZ`.
- Note text for E2E-09: "Resident has a cold; nurse notified." (synthetic).

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-076-FR-01 / TST-004, DEP-017, CIC-030 | FEAT-076 | TC-076-01 |
| FEAT-076-FR-02 / D-73, D-74 (a) | FEAT-076 | TC-076-01, TC-076-11 |
| FEAT-076-FR-03 / D-74 (a) | FEAT-076 | TC-076-06 |
| FEAT-076-FR-04 / TST-100, CIC-032, E2E-01..E2E-21 | FEAT-076 | TC-076-01, TC-076-09 |
| FEAT-076-FR-05 / D-73, D-118 | FEAT-076 | TC-076-02 |
| FEAT-076-FR-06 / E2E-18 | FEAT-076 | TC-076-02, TC-076-10 |
| FEAT-076-FR-07 / E2E-09, FE-187 | FEAT-076 | TC-076-02 |
| FEAT-076-FR-08 / CIC-030, D-73 | FEAT-076 | TC-076-04 |
| FEAT-076-FR-09 / E2E-15, D-169 | FEAT-076 | TC-076-04 |
| FEAT-076-FR-10 / TST-187, NFR-011 | FEAT-076 | TC-076-04 |
| FEAT-076-FR-11 / E2E-19, TST-065 | FEAT-076 | TC-076-04 |
| FEAT-076-FR-12 / D-73 | FEAT-076 | TC-076-05 |
| FEAT-076-FR-13 / TST-101, TST-161 | FEAT-076 | TC-076-12 |
| FEAT-076-FR-14 / FE-192, TPS-050, TPS-081 | FEAT-076 | TC-076-13 |
| FEAT-076-FR-15 / FE-191, E2E-16, D-78 | FEAT-076 | TC-076-01 |
| FEAT-076-FR-16 / D-74 (b), ENV-054, CIC-034 | FEAT-076 | TC-076-14 |
| FEAT-076-FR-17 / TST-005 | FEAT-076 | TC-076-03, TC-076-15 |
| E2E-02, TST-053 | FEAT-076 | TC-076-16 |
| TST-151 (Firefox, WebKit) | FEAT-076 | TC-076-08 |
