# Deploy workflows and post-deploy smoke tests

## Feature Description

FEAT-086 (Complete, BACKLOG.md §10) delivers `.github/workflows/deploy-staging.yml`, `.github/workflows/deploy-production.yml` and the smoke suite `tests/smoke/` (`conftest.py`, `support.py`, `test_staging_smoke.py`, `test_production_smoke.py`, `test_tls.py`, `wait_for_deploy.py`). Staging is deployed by the Netlify and Render GitHub integrations on every merge to `main`; `deploy-staging.yml` waits until staging serves the pushed SHA (15 s polling, 15 minutes), re-seeds the staging database with `seed test_v0_1 --reset` and the DS-10 loader when the push changes `backend/alembic/**` or `analytics/**` (or on dispatch with `reseed: true`), runs the authenticated staging smoke tests (DEP-080) and uploads `smoke-report`. Production is deployed only by a manual, reviewer-approved `deploy-production.yml` run for a `main` commit: jobs `verify` → `deploy` (Render API and Netlify CLI, the only two secrets `RENDER_API_KEY` and `NETLIFY_AUTH_TOKEN`) → `wait-for-production` → `smoke` (unauthenticated, read-only, DEP-081) → `release` (tag `vX.Y.Z` and GitHub Release).

Repository and local cases run on the checkout and the Compose demo stack. Cases marked **Hosted** run against the interim deployment (TRD 24 D-180) once the repository variables `STAGING_API_BASE_URL`, `STAGING_FRONTEND_URL`, `PRODUCTION_API_BASE_URL`, `PRODUCTION_FRONTEND_URL` are set (not set on 15 Nov 2026; until then `deploy-staging.yml` stops at "Wait for staging"). No case in this file triggers a push, migration or re-seed only for testing (TRD 24 D-170): hosted cases use the next naturally occurring merge, a `smoke_only` run, or runs that stop in job `verify`.

Note: FEAT-086-AC-05 is aligned to the TRD (TRD 24 D-184): it names DEP-080 (a)–(j) and DEP-081 (a)–(g) as TRD 15 defines them. The cases below test every item of the TRD lists.

## Preconditions

- Local: Docker Compose v2; `cp .env.development.example .env`; `docker compose --profile demo up -d --build --wait db backend frontend-prod`; then `docker compose exec backend python -m backend.cli seed test_v0_1` and `docker compose exec backend python database/seeds/load_evaluation_ground_truth.py tests/fixtures/answer_key/evaluation_ground_truth_v0_1.csv`.
- Local Python 3.12 with `pip install -r backend/requirements.txt -r backend/requirements-dev.txt` to run `pytest` from the host.
- Seed passwords are read from `.env` into the shell (`set -a; . ./.env; set +a`); no password is typed into a test record.
- Login is rate-limited to 5 per minute: run the authenticated suite at most once per minute.
- Hosted: the four repository variables set; GitHub environments `staging` (secrets `STAGING_DATABASE_URL`, `STAGING_SEED_*`) and `production` (secrets `RENDER_API_KEY`, `NETLIFY_AUTH_TOKEN`; variables `NETLIFY_PRODUCTION_SITE_ID`, `RENDER_PRODUCTION_BACKEND_SERVICE_ID`, `RENDER_PRODUCTION_NIGHTLY_SERVICE_ID`; required reviewer) configured by the team; tester has `gh` with repository write access.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-086-01 | Staging smoke suite passes against the local seeded stack | High | Positive |
| TC-086-02 | Production smoke suite (unauthenticated) passes against the local stack | High | Positive |
| TC-086-03 | Smoke configuration errors are reported with the documented messages | Medium | Negative |
| TC-086-04 | Smoke suites cover every DEP-080 and DEP-081 item; no production test is `authenticated` | High | Documentation |
| TC-086-05 | `deploy-production.yml` references exactly the two production secrets in job `deploy` | High | Security |
| TC-086-06 | No other workflow holds a platform token, writes contents or runs migrations against a target | High | Security |
| TC-086-07 | `deploy-staging.yml` triggers, waits, re-seed variables and artifact match the TRD | High | Documentation |
| TC-086-08 | Re-seed decision: `analytics/` change re-seeds, `docs/`-only change does not | High | Positive |
| TC-086-09 | A merge to `main` yields staging version = merge SHA and a green `deploy-staging.yml` | High | Hosted |
| TC-086-10 | Production smoke tests on the hosted origins via `smoke_only` (no deploy, no tag) | High | Hosted |
| TC-086-11 | Approved production release yields version = SHA and tag `vX.Y.Z` | High | Hosted |
| TC-086-12 | Release run for a SHA without a successful staging run deploys nothing | High | Hosted |
| TC-086-13 | Invalid release inputs are refused in job `verify` | Medium | Negative |
| TC-086-14 | A merge to `main` creates no production deploy, tag or release | High | Hosted |
| TC-086-15 | Manual authenticated check is recorded in the GitHub Release notes | Medium | Hosted |
| TC-086-16 | A smoke-test run finishes within 5 minutes | Medium | Performance |

### TC-086-01 Staging smoke suite passes against the local seeded stack

| Step | Action | Expected Result |
|---|---|---|
| 1 | `curl -s http://localhost:8000/api/v1/health` | 200 with `"status":"ok"` and `"database":"ok"` |
| 2 | Run `set -a; . ./.env; set +a; SMOKE_ENV=staging SMOKE_API_BASE_URL=http://localhost:8000/api/v1 SMOKE_FRONTEND_URL=http://localhost:3001 SMOKE_USER_EMAIL=researcher@example.com SMOKE_USER_PASSWORD="$SEED_RESEARCHER_PASSWORD" pytest -p no:randomly tests/smoke -m smoke -rs` | Session ends with 0 failed |
| 3 | Read the passed tests in `test_staging_smoke.py` | `test_a_health_ok_with_expected_version`, `test_b_frontend_login_page`, `test_c_login_as_seeded_researcher`, `test_d_resident_summary`, `test_e_r09_alarm_since_oct_21`, `test_f_open_alarms_and_data_alerts`, `test_g_analytics_received_and_used`, `test_h_cors_preflight` passed |
| 4 | Read the skip reasons (`-rs`) | `test_i_api_hsts_and_https_redirect`, `test_i_frontend_hsts_and_https_redirect`, `test_tls_policy_api`, `test_tls_policy_frontend` skipped with "SEC-065: plain HTTP on localhost; HSTS, redirect and TLS need HTTPS (TST-135)"; production tests skipped with "TST-152: production suite; this run has SMOKE_ENV=staging" |

Note: `docs/deployment.md` ("Smoke tests") sets `SMOKE_EXPECTED_SHA="$(git rev-parse HEAD)"` for the local run, but the local backend reports `version` `unknown` (`GIT_SHA=unknown` in `.env.development.example:23`, `backend/core/config.py:76`), so `test_a` fails with that variable; leave SMOKE_EXPECTED_SHA unset locally (it is optional, `tests/smoke/conftest.py`).

### TC-086-02 Production smoke suite (unauthenticated) passes against the local stack

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `SMOKE_ENV=production SMOKE_API_BASE_URL=http://localhost:8000/api/v1 SMOKE_FRONTEND_URL=http://localhost:3001 pytest -p no:randomly tests/smoke -m "smoke and not authenticated" -rs` | 0 failed |
| 2 | Read the passed tests of `test_production_smoke.py` | `test_a_health_ok_with_expected_version`, `test_c_residents_without_token_is_401_problem`, `test_d_sessions_without_api_key_is_401`, `test_f_no_audio_route` passed |
| 3 | Read the skipped tests | `test_b_frontend_login_page_over_https`, both `test_e_…` and both TLS tests skipped with the SEC-065 reason (HTTPS-only checks) |
| 4 | Confirm read-only behaviour: `docker compose exec db psql -U echowell -d echowell -c "SELECT count(*) FROM raw_sessions"` before and after step 1 | Count unchanged |

### TC-086-03 Smoke configuration errors are reported with the documented messages

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `pytest -p no:randomly tests/smoke -m smoke -rs` with no SMOKE_* variable | All smoke tests skipped with "TST-152: SMOKE_API_BASE_URL is not set (smoke tests run after a deploy)"; exit 0 |
| 2 | Run with `SMOKE_ENV=qa SMOKE_API_BASE_URL=http://localhost:8000/api/v1` | Usage error "SMOKE_ENV must be staging or production (TRD 21 §4.5)"; no test passes |
| 3 | Run with `SMOKE_ENV=production SMOKE_API_BASE_URL=http://localhost:8000/api/v1 SMOKE_USER_EMAIL=researcher@example.com` | Usage error "SMOKE_USER_* is never set for production (TRD 21, TST-152)" |
| 4 | Run the staging suite as in TC-086-01 but without SMOKE_USER_PASSWORD | `test_c`..`test_g` fail with "SMOKE_USER_EMAIL and SMOKE_USER_PASSWORD are required for staging (DEP-080)" |
| 5 | Run the staging suite with `SMOKE_USER_PASSWORD=wrong-value` | `test_c`..`test_g` fail on the login assertion (status 401 instead of 200) |

### TC-086-04 Smoke suites cover every DEP-080 and DEP-081 item; no production test is `authenticated`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -n "^def test_" tests/smoke/test_staging_smoke.py` | Tests `test_a_…` through `test_h_…` and two `test_i_…` (API and frontend HSTS and redirect) |
| 2 | `grep -n "^def test_" tests/smoke/test_tls.py` | `test_tls_policy_api`, `test_tls_policy_frontend` (DEP-080 (j), DEP-081 (g), SEC-066) |
| 3 | `grep -n "^def test_" tests/smoke/test_production_smoke.py` | `test_a_…`, `test_b_…`, `test_c_…`, `test_d_…`, two `test_e_…`, `test_f_no_audio_route` |
| 4 | `grep -n "mark.authenticated" tests/smoke/test_production_smoke.py; echo "exit=$?"` | No match; `exit=1` |
| 5 | `grep -c "mark.authenticated" tests/smoke/test_staging_smoke.py` | `5` (tests c–g, the ones that log in) |
| 6 | Read `test_d_resident_summary` and `test_f_open_alarms_and_data_alerts` | Asserts summary `{"changed": 2, "needs_attention": 2, "learning": 0, "usual": 6}`, total 10; open alarms `["R09", "R10"]`; data alerts exactly `baseline_stalled` R08, `device_silent` D02 (detail contains "Oct 12"), `high_set_aside` R03, `possible_other_speaker` R05 |
| 7 | Read `test_g_analytics_received_and_used` and `test_h_cors_preflight` | Asserts 281 of 300 received and 267 of 300 used; preflight allowed for the frontend origin and no `access-control-allow-origin` for `https://example.org` |

### TC-086-05 `deploy-production.yml` references exactly the two production secrets in job `deploy`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -n "secrets\." .github/workflows/deploy-production.yml` | Exactly two lines: `RENDER_API_KEY: ${{ secrets.RENDER_API_KEY }}` and `NETLIFY_AUTH_TOKEN: ${{ secrets.NETLIFY_AUTH_TOKEN }}` |
| 2 | Find the job that contains both lines | Both are in job `deploy`, which has `environment: production` |
| 3 | Search the file for `DATABASE_URL`, `JWT_SECRET`, `SEED_` | No match (no production database URL or application credential, CIC-050) |
| 4 | Read how the Render key is used | Written to a header file under `$RUNNER_TEMP` with `umask 077` and passed as `-H @"$header"`, never on the command line or echoed (CIC-092) |

### TC-086-06 No other workflow holds a platform token, writes contents or runs migrations against a target

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -rln "RENDER_API_KEY\|NETLIFY_AUTH_TOKEN" .github/workflows/` | Only `.github/workflows/deploy-production.yml` |
| 2 | `grep -rn "contents: write" .github/workflows/` | One match, in job `release` of `deploy-production.yml` |
| 3 | `grep -n "alembic" .github/workflows/deploy-staging.yml .github/workflows/deploy-production.yml` | No `alembic upgrade` command; migrations run only as the Render pre-deploy command (staging re-seed uses `seed test_v0_1 --reset`, D-71) |
| 4 | `grep -rn 'run:.*\${{ *secrets\.' .github/workflows/` | No match: secrets are passed only through `env:` |
| 5 | `ls .github/workflows/` | Exactly `ci.yml`, `deploy-production.yml`, `deploy-staging.yml`, `e2e.yml`, `uptime.yml` (CIC-002) |

### TC-086-07 `deploy-staging.yml` triggers, waits, re-seed variables and artifact match the TRD

| Step | Action | Expected Result |
|---|---|---|
| 1 | Read `on:` | `push` to `branches: [main]` and `workflow_dispatch` with boolean input `reseed` (default `false`) |
| 2 | Read job `wait-for-staging`, step "Wait for staging backend and frontend to serve the pushed commit" | Calls `tests/smoke/wait_for_deploy.py` with `--interval 15 --timeout 900` and `--frontend-sha` from `git log -1 --format=%H "$EXPECTED_SHA" -- frontend netlify.toml` |
| 3 | Read job `reseed-and-smoke` | `environment: staging`; `timeout-minutes: 20` |
| 4 | Read step "Re-seed staging (seed test_v0_1 --reset, then the DS-10 loader)" `env:` | `DATABASE_URL` and `DATABASE_MIGRATION_URL` both `${{ secrets.STAGING_DATABASE_URL }}`, `APP_ENV: staging`, `PIPELINE_PROFILE: test_v0_1`, `PIPELINE_AS_OF: "2026-10-30T15:00:00-05:00"`, `FACILITY_TZ: America/Chicago`, four `SEED_*` from `STAGING_SEED_*`; no `JWT_SECRET` and no `CORS_*` variable |
| 5 | Read the commands of that step | `python -m backend.cli seed test_v0_1 --reset` then `python database/seeds/load_evaluation_ground_truth.py tests/fixtures/answer_key/evaluation_ground_truth_v0_1.csv` |
| 6 | Read step "Staging smoke tests (DEP-080)" and the upload step | `pytest -p no:randomly tests/smoke -m smoke --junitxml=build/smoke-junit.xml` with `SMOKE_ENV: staging`, `SMOKE_USER_EMAIL: researcher@example.com`; artifact `smoke-report`, `retention-days: 30`, uploaded `if: always()` |

### TC-086-08 Re-seed decision: `analytics/` change re-seeds, `docs/`-only change does not

| Step | Action | Expected Result |
|---|---|---|
| 1 | `gh run list --workflow deploy-staging.yml --limit 50 --json databaseId,headSha,event` and pick one push run whose commit range changed a file under `analytics/` (check with `git diff --name-only <before> <after> -- analytics backend/alembic`) | At least one such run exists in history |
| 2 | Open its log, step "Decide whether to re-seed (CIC-041)" | Line `re-seed staging: true` |
| 3 | Pick a push run whose commit range changed only files under `docs/` | Step prints `re-seed staging: false` |
| 4 | For a run after the variables are set, read job `reseed-and-smoke` | Step "Re-seed staging …" ran for the `analytics/` push and was skipped for the `docs/`-only push |
| 5 | Locally, run the decision rule on two commits: `git diff --name-only <commit>^ <commit> -- backend/alembic analytics \| grep -q . && echo true \|\| echo false` | `true` for an `analytics/` commit, `false` for a `docs/`-only commit |

Note: do not create a push only to trigger a re-seed (D-170); use existing or naturally occurring pushes.

### TC-086-09 A merge to `main` yields staging version = merge SHA and a green `deploy-staging.yml`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Before the next planned merge, record `curl -s "<PRODUCTION_API_BASE_URL>/health"` `version` | Value P recorded |
| 2 | After the merge (SHA M), open Actions → Deploy staging for the push run | Run for `headSha` M |
| 3 | Read job `wait-for-staging` | Polling lines show the observed `version` until it equals M (≤ 15 minutes); job `success` |
| 4 | Read job `reseed-and-smoke` | Smoke step passes DEP-080 (a)–(i) and both TLS tests; job `success`; artifact `smoke-report` present |
| 5 | `curl -s "<STAGING_API_BASE_URL>/health"` | `"status":"ok"`, `"database":"ok"`, `"version":"M"` |
| 6 | View source of `<STAGING_FRONTEND_URL>/login` | `<meta name="echowell-build" content="…">` equals M, or the latest commit touching `frontend/` or `netlify.toml` |
| 7 | `curl -s "<PRODUCTION_API_BASE_URL>/health"` | `version` still equals P (production unchanged) |

### TC-086-10 Production smoke tests on the hosted origins via `smoke_only` (no deploy, no tag)

| Step | Action | Expected Result |
|---|---|---|
| 1 | Read the deployed SHA: `curl -s "<PRODUCTION_API_BASE_URL>/health"` | `version` S (40 hex characters) |
| 2 | Actions → Deploy production → Run workflow on `main` with `sha` = S, `version` empty, `smoke_only` ticked | Run starts |
| 3 | Read job `verify` | "Commit is on main and version is new" passes and prints `release S (smoke only)`; the required-checks step is skipped |
| 4 | Read job `deploy` | Skipped (no reviewer request, no Render or Netlify call) |
| 5 | Read job `wait-for-production` | Health `version` and build meta equal S; `success` |
| 6 | Read job `smoke` | DEP-081 tests a, b, c, d, e (API and frontend), f and both TLS tests passed; `smoke-report` uploaded |
| 7 | Read job `release` and run `git ls-remote --tags origin` | `release` skipped; no new tag |

### TC-086-11 Approved production release yields version = SHA and tag `vX.Y.Z`

Run only when the team decides to make a production release; no release is made only for this test case.

| Step | Action | Expected Result |
|---|---|---|
| 1 | Choose SHA R on `main` whose eight CIC-070 checks and `deploy-staging.yml` run succeeded, and a new version `vX.Y.Z`; if R contains a migration, follow TC-089 pre-release steps first | Inputs recorded |
| 2 | Dispatch Deploy production with `sha` = R, `version` = `vX.Y.Z`, `smoke_only` unticked | Job `verify` prints each check name with `success` and `successful deploy-staging.yml runs for R: ≥1` |
| 3 | Observe job `deploy` | Waits for review; a required reviewer (not the dispatcher) approves |
| 4 | Read the Render step log | Both production services print `deploy … of R triggered` and reach `live` |
| 5 | Read the Netlify step | `netlify-cli@17 deploy --build --prod` completes |
| 6 | Read jobs `wait-for-production` and `smoke` | Health `version` = R; DEP-081 tests pass |
| 7 | Read job `release`; open Releases | Tag `vX.Y.Z` on R; Release notes contain "Released commit R by deploy-production.yml; production smoke tests (DEP-081) passed." and "Manual authenticated check (TRD 15 DEP-083): pending." |

### TC-086-12 Release run for a SHA without a successful staging run deploys nothing

| Step | Action | Expected Result |
|---|---|---|
| 1 | Find a SHA N on `main` with no successful `deploy-staging.yml` run: `gh run list --workflow deploy-staging.yml --commit N --json conclusion` | No entry with `success` |
| 2 | Dispatch Deploy production with `sha` = N and an unused version `vX.Y.Z` | Run starts |
| 3 | Read job `verify`, step "Required checks and staging run succeeded (CIC-053)" | Prints `successful deploy-staging.yml runs for N: 0` and fails with "::error::N has not passed every required check and its staging run" |
| 4 | Read jobs `deploy`, `wait-for-production`, `smoke`, `release` | All skipped; no reviewer approval was requested |
| 5 | `git ls-remote --tags origin vX.Y.Z` and production health `version` | No tag; version unchanged |

If a reviewer request appears, the reviewer rejects it and the case is recorded as FAIL.

### TC-086-13 Invalid release inputs are refused in job `verify`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Dispatch Deploy production with `sha` = `abc123` | `verify` fails with "::error::sha must be a full 40-character commit SHA" |
| 2 | Dispatch with a valid `main` SHA and `version` = `1.2` | Fails with "::error::version must match vX.Y.Z" |
| 3 | Dispatch with a valid SHA and an existing tag as `version` (if any tag exists) | Fails with "::error::tag vX.Y.Z already exists" |
| 4 | Dispatch with a 40-character SHA that is not on `main` | Fails with "::error::<sha> is not on main" |
| 5 | For each run, check the later jobs | `deploy`, `wait-for-production`, `smoke`, `release` skipped |

### TC-086-14 A merge to `main` creates no production deploy, tag or release

| Step | Action | Expected Result |
|---|---|---|
| 1 | Record production health `version`, `git ls-remote --tags origin` and the Releases list before a merge | Baseline recorded |
| 2 | After the merge, `gh run list --workflow deploy-production.yml --event push` | Empty: the workflow has no push trigger |
| 3 | Repeat step 1 readings | `version`, tags and Releases unchanged |
| 4 | Netlify production site `echowell-und` deploy list | No new deploy (builds stopped) |

### TC-086-15 Manual authenticated check is recorded in the GitHub Release notes

| Step | Action | Expected Result |
|---|---|---|
| 1 | After TC-086-11, open `<PRODUCTION_FRONTEND_URL>/login` and sign in as the production admin created in FEAT-088 | Resident list opens; header shows "demo data (synthetic)" |
| 2 | Open Residents, open one `T`-prefixed resident, sign out | Each page loads; sign-out returns to `/login` |
| 3 | Edit Release `vX.Y.Z` | The "pending" line is replaced with result, date and role used; no name or credential |

### TC-086-16 A smoke-test run finishes within 5 minutes

| Step | Action | Expected Result |
|---|---|---|
| 1 | In the runs of TC-086-09 and TC-086-10, read the duration of steps "Staging smoke tests (DEP-080)" and "Production smoke tests (DEP-081)" | Each ≤ 5 minutes (the wait job is counted separately, DEP-082) |
| 2 | Locally, time TC-086-01 step 2 | Completes in under 5 minutes |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/health` (local or hosted) | 200; `status` `ok`, `database` `ok`, `version` = expected SHA (hosted) |
| 2 | `POST /api/v1/auth/login` as `researcher@example.com` (staging or local) | 200 with `access_token` |
| 3 | `GET /api/v1/residents` with Bearer token (staging/local) | 200; `summary` = `{"changed":2,"needs_attention":2,"learning":0,"usual":6}`; `total` 10 |
| 4 | `GET /api/v1/residents/R09` | 200; `status` `alarm_on`; `alarm_since` `2026-10-21` |
| 5 | `GET /api/v1/alerts?status=open`; `GET /api/v1/data-alerts?status=open` | Alarms R09, R10; data alerts R08 `baseline_stalled`, D02 `device_silent` ("Oct 12"), R03 `high_set_aside`, R05 `possible_other_speaker` |
| 6 | `GET /api/v1/analytics` | `kpis.checkins_received` 281 of 300; `kpis.used_for_scoring` 267 of 300 |
| 7 | `OPTIONS /api/v1/residents` with `Origin: https://example.org` | No `access-control-allow-origin` header |
| 8 | `GET /api/v1/residents` without token (production) | 401, `content-type` `application/problem+json`, body has `status` 401, `type`, `title` |
| 9 | `POST /api/v1/sessions` with `{}` and no `X-API-Key` (production) | 401; nothing written |
| 10 | `GET /api/v1/audio` | 404 |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | Local, after `docker compose exec backend python -m backend.cli seed test_v0_1 --reset`: `SELECT action, occurred_at FROM audit_logs WHERE action = 'seed.reset' ORDER BY occurred_at DESC LIMIT 1;` | One row with `action` `seed.reset` and the time of the reset |
| 2 | Local: `SELECT count(*) FROM residents WHERE resident_code LIKE 'R%';` | 10 |
| 3 | Hosted staging, after a re-seeding run (operator psql with the staging URL, read-only): same query as step 1 | Latest `seed.reset` row matches the run time |
| 4 | Hosted production (operator, read-only): `SELECT count(*) FROM audit_logs WHERE action = 'seed.reset';` | 0 (re-seeding never runs against production) |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Smoke run without SMOKE_API_BASE_URL (TC-086-03) | All skipped with the TST-152 reason |
| 2 | Invalid SMOKE_ENV; SMOKE_USER_* set for production (TC-086-03) | Usage errors with the exact messages |
| 3 | Wrong researcher password (TC-086-03) | Login assertion fails (401) |
| 4 | Release for a SHA without staging success (TC-086-12) | `verify` fails; nothing deployed; no tag |
| 5 | Malformed `sha` / `version`, existing tag, SHA not on `main` (TC-086-13) | `verify` fails with the exact `::error::` messages |
| 6 | Merge to `main` (TC-086-14) | No production deploy, tag or release |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-086-AC-01 | Merge to `main` → staging health `version` = merge SHA, Netlify staging deploy, green `deploy-staging.yml`, production unchanged | TC-086-09, TC-086-14 |
| FEAT-086-AC-02 | Approved manual run for a `main` commit and `vX.Y.Z` → production `version` = SHA, green run, tag `vX.Y.Z` | TC-086-11, TC-086-10 |
| FEAT-086-AC-03 | `grep -n "secrets\." deploy-production.yml` returns exactly `secrets.RENDER_API_KEY` and `secrets.NETLIFY_AUTH_TOKEN`, both in job `deploy` with environment `production` | TC-086-05 |
| FEAT-086-AC-04 | An `analytics/` push triggers the re-seed step; a `docs/`-only push does not | TC-086-08 |
| FEAT-086-AC-05 | Staging suite covers each DEP-080 item and production suite each DEP-081 item; production tests carry no `authenticated` marker | TC-086-04, TC-086-01, TC-086-02 |
| FEAT-086-AC-06 | A merge produces no production deploy, tag or release; a run for a SHA whose checks or staging run did not succeed deploys nothing | TC-086-14, TC-086-12, TC-086-13 |

## Test Data Requirements

- Local: `test_v0_1` seed (R01–R10, devices incl. D02, `researcher@example.com`), DS-10 answer-key loader, Compose `demo` profile.
- Staging: the same `test_v0_1` data re-seeded by the workflow (PIPELINE_AS_OF 2026-10-30T15:00:00-05:00).
- Production: no test data is written; smoke checks are unauthenticated and read-only.
- Environment variables: SMOKE_ENV, SMOKE_API_BASE_URL, SMOKE_FRONTEND_URL, SMOKE_EXPECTED_SHA (hosted), SMOKE_USER_EMAIL / SMOKE_USER_PASSWORD (staging and local only, from `.env`).
- Placeholders: `<STAGING_API_BASE_URL>`, `<STAGING_FRONTEND_URL>`, `<PRODUCTION_API_BASE_URL>`, `<PRODUCTION_FRONTEND_URL>`.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| CIC-001, CIC-003, DEP-060 | FEAT-086 | TC-086-06, TC-086-14 |
| CIC-040, DEP-082 | FEAT-086 | TC-086-07, TC-086-09, TC-086-16 |
| CIC-041, DEP-074, D-71 | FEAT-086 | TC-086-07, TC-086-08 |
| CIC-042, CIC-043, DEP-080, TST-152, TST-134 | FEAT-086 | TC-086-01, TC-086-04, TC-086-09 |
| CIC-050, CIC-090, CIC-092 | FEAT-086 | TC-086-05, TC-086-06 |
| CIC-051, DEP-081 | FEAT-086 | TC-086-02, TC-086-10, TC-086-11 |
| CIC-052, CIC-053 | FEAT-086 | TC-086-11, TC-086-12, TC-086-13, TC-086-14 |
| TST-135, SEC-062, SEC-066 | FEAT-086 | TC-086-01, TC-086-04, TC-086-10 |
| TST-006 | FEAT-086 | TC-086-04 |
| TRD 16 §4.10 `smoke-report` | FEAT-086 | TC-086-07, TC-086-10 |
| DEP-083 | FEAT-086 | TC-086-15 |
| FEAT-086-FR-01..FEAT-086-FR-16 | FEAT-086 | TC-086-01..TC-086-16 |
