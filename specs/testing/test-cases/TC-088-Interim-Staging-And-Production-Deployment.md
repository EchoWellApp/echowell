# Interim staging and production deployment (synthetic and test data only)

## Feature Description

FEAT-088 (Complete, BACKLOG.md §10) is the Phase 10 deployment of EchoWell on the interim stack: Neon (project `echowell`, PostgreSQL 16, `aws-us-east-1`, database branches `main` = production and `staging`), Render (project `echowell`, region `ohio`, Starter instances; staging web service `echowell-api` per TRD 24 D-154 and cron job `echowell-nightly-staging`; production web service `echowell-backend-production` and cron job `echowell-nightly-production`) and Netlify (staging site `echowell-und-staging`, production site `echowell-und`). Staging runs profile `test_v0_1` with PIPELINE_AS_OF 2026-10-30T15:00:00-05:00 and the answer-key data; interim production runs profile `production`, is bootstrapped, has an interactively created first admin and a roster of `T`-prefixed demo study IDs, and never holds `test_v0_1` seed data. The team performed the deployment itself (TRD 24 D-180); the hosted verification items are carried out as Block 5 validation activities.

These test cases are the verification runbook for the deployed state. They read and check; they do not redeploy, migrate, re-seed or change any Render, Netlify or Neon setting (TRD 24 D-170). Hosted URLs are written as placeholders: `<STAGING_API_BASE_URL>` and `<PRODUCTION_API_BASE_URL>` (each including `/api/v1`, so `<…_API_BASE_URL>/health` equals `$BACKEND_URL/api/v1/health` of the acceptance criteria), `<STAGING_FRONTEND_URL>`, `<PRODUCTION_FRONTEND_URL>`.

Note: FEAT-088 is aligned to the TRD (TRD 24 D-184): the staging web service is `echowell-api` (TRD 15, `docs/deployment.md`, TRD 24 D-154). These cases follow the TRD.

## Preconditions

- Hosted origins known to the tester (held by the team; never written into the test record).
- Read-only database access from an operator workstation: `psql` 16 with the production and staging connection strings taken from the Render dashboard (app role, `sslmode=require`); only `SELECT` statements are run. The strings are never pasted into a file, issue or chat.
- View access to the Render, Netlify and Neon dashboards (DevOps owner or an administrator), and to GitHub Actions.
- A staging account: `researcher@example.com` with the staging seed password from the `STAGING_SEED_RESEARCHER_PASSWORD` store (entered at the prompt, never typed into the record). A production admin account created per FEAT-088-FR-06.
- Local: Compose stack available for TC-088-05.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-088-01 | Health reports `ok`, database `ok` and the deployed SHA in staging and production | High | Hosted |
| TC-088-02 | Frontend `/residents` is served over HTTPS in both environments | High | Hosted |
| TC-088-03 | `deploy-staging.yml` and `deploy-production.yml` are green on the deployed commits | High | Hosted |
| TC-088-04 | Production has zero `raw_sessions` rows from `ingest_batches.source = 'seed'` | High | Hosted |
| TC-088-05 | Production configuration with `PIPELINE_PROFILE=test_v0_1` is refused; seeding is refused in production | High | Negative |
| TC-088-06 | Interim Neon project holds only R01–R10 (staging) and `T`-prefixed demo IDs | High | Hosted |
| TC-088-07 | `docs/reports/DEPLOYMENT_REPORT.md` exists with the required sentences and final line | High | Documentation |
| TC-088-08 | A staging JWT and a staging API key are rejected by production | High | Hosted |
| TC-088-09 | Staging dashboard shows the answer-key list and the staging data label | High | Hosted |
| TC-088-10 | Production dashboard shows the synthetic label and a `T`-prefixed demo resident | Medium | Hosted |
| TC-088-11 | Production and staging variables match the TRD 21 §4.7 matrix; deviations are recorded | Medium | Hosted |
| TC-088-12 | Regions are Neon `aws-us-east-1` and Render `ohio`; instances are Starter | Medium | Hosted |
| TC-088-13 | Migrations run only as the Render pre-deploy command; both branches are at head `0004` | Medium | Hosted |
| TC-088-14 | Production bootstrap, first admin and roster are audited; no default credential exists | Medium | Hosted |
| TC-088-15 | R01–R10 validation passes in CI on the deployed commit | High | Positive |
| TC-088-16 | GitHub organisation requires two-factor authentication | Medium | Security |

### TC-088-01 Health reports `ok`, database `ok` and the deployed SHA in staging and production

| Step | Action | Expected Result |
|---|---|---|
| 1 | `curl -fsS "<STAGING_API_BASE_URL>/health"` | Exit 0; JSON `"status":"ok"`, `"database":"ok"`, `"version":"<40-hex SHA>"` |
| 2 | Render → `echowell-api` → Events: read the commit of the live deploy | Equals the `version` of step 1 |
| 3 | `curl -fsS "<PRODUCTION_API_BASE_URL>/health"` | Exit 0; `"status":"ok"`, `"database":"ok"`, `version` = SHA of the live deploy of `echowell-backend-production` |
| 4 | `git branch -r --contains <production version>` | Lists `origin/main` (production runs a `main` commit) |
| 5 | Repeat steps 1 and 3 once after the Neon compute has been idle more than 5 minutes | Both still return 200 within 30 s (cold start accepted, RSK-07) |

### TC-088-02 Frontend `/residents` is served over HTTPS in both environments

| Step | Action | Expected Result |
|---|---|---|
| 1 | `curl -fsSI "<STAGING_FRONTEND_URL>/residents"` | Exit 0; status line `200`; header `strict-transport-security: max-age=31536000; includeSubDomains` |
| 2 | `curl -fsSI "<PRODUCTION_FRONTEND_URL>/residents"` | Exit 0; status `200`; same HSTS header |
| 3 | `curl -sSI "http://<production frontend host>/residents"` | `301` or `308` with `location: https://<production frontend host>/residents` |
| 4 | Open `<PRODUCTION_FRONTEND_URL>/login` in a browser | Padlock shown; certificate valid; login form "Sign in" displayed |

### TC-088-03 `deploy-staging.yml` and `deploy-production.yml` are green on the deployed commits

| Step | Action | Expected Result |
|---|---|---|
| 1 | Take the staging `version` S from TC-088-01; run `gh run list --workflow deploy-staging.yml --commit S --json conclusion,databaseId` | At least one run with conclusion `success` |
| 2 | Take the production `version` P; run `gh run list --workflow deploy-production.yml --json conclusion,displayTitle,databaseId` and open the runs | A run with input `sha` = P and conclusion `success` |
| 3 | Record which kind of production run it is (full release with tag, or `smoke_only`, TC-086-10) | Kind recorded in `DEPLOYMENT_CHECKLIST.md` G.05 evidence |

Note: on 15 Nov 2026 the repository variables with the hosted URLs are not set, so `deploy-staging.yml` stops at "Wait for staging" (`docs/deployment.md`, "Deployment status"); this case passes only after the variables are set and a run completes.

### TC-088-04 Production has zero `raw_sessions` rows from `ingest_batches.source = 'seed'`

| Step | Action | Expected Result |
|---|---|---|
| 1 | On the production database (read-only): `SELECT count(*) FROM raw_sessions r JOIN ingest_batches b ON r.ingest_batch_id = b.id WHERE b.source = 'seed';` | `0` |
| 2 | `SELECT count(*) FROM ingest_batches WHERE source = 'seed';` | `0` |
| 3 | `SELECT count(*) FROM evaluation_ground_truth;` | `0` (answer key only where the profile is `test_v0_1`) |
| 4 | Record the query output in `DEPLOYMENT_CHECKLIST.md` G.10 | Evidence filled |

### TC-088-05 Production configuration with `PIPELINE_PROFILE=test_v0_1` is refused; seeding is refused in production

Run locally (a throwaway configuration with the production variables), never on the hosted services.

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/unit/backend/core/test_config.py -q -k "cfg_06 or tst_038"` | All selected tests pass (`test_cfg_06_production_refuses_test_profile`, `test_cfg_06_process_exits_1_with_critical_log`, `test_tst_038_production_refuses_pipeline_as_of`) |
| 2 | `docker compose run --rm -e APP_ENV=production -e PIPELINE_PROFILE=test_v0_1 backend; echo "exit=$?"` | Process exits with `exit=1`; the log contains `startup_config_invalid` and the item `PIPELINE_PROFILE` "test_v0_1 is refused when APP_ENV=production" (other production violations of the local file may also be listed); no secret value is printed |
| 3 | `docker compose run --rm -e APP_ENV=production -e PIPELINE_PROFILE=production -e PIPELINE_AS_OF=2026-10-30T15:00:00-05:00 backend; echo "exit=$?"` | `exit=1`; log lists `PIPELINE_AS_OF` "must be empty when APP_ENV=production" |
| 4 | `docker compose exec -e APP_ENV=production backend python -m backend.cli seed test_v0_1; echo "exit=$?"` | `exit=2`; message "seeding is not allowed in production"; `SELECT count(*) FROM audit_logs WHERE action = 'seed.reset'` unchanged |

### TC-088-06 Interim Neon project holds only R01–R10 (staging) and `T`-prefixed demo IDs

| Step | Action | Expected Result |
|---|---|---|
| 1 | Production (read-only): `SELECT resident_code FROM residents WHERE resident_code !~ '^T';` | 0 rows |
| 2 | Production: `SELECT resident_code, status FROM residents ORDER BY resident_code;` | Only `T`-prefixed codes (e.g. `T01`) |
| 3 | Staging (read-only): `SELECT resident_code FROM residents WHERE resident_code !~ '^(R0[1-9]\|R10\|T.*)$';` | 0 rows |
| 4 | Staging: `SELECT count(*) FROM residents WHERE resident_code ~ '^R(0[1-9]\|10)$';` | `10` |
| 5 | Neon console → project `echowell` → Branches | Only `main`, `staging` and, if present, temporary `pre-<short-sha>` / `restore-drill` branches younger than 7 days |

### TC-088-07 `docs/reports/DEPLOYMENT_REPORT.md` exists with the required sentences and final line

| Step | Action | Expected Result |
|---|---|---|
| 1 | `test -f docs/reports/DEPLOYMENT_REPORT.md; echo "exit=$?"` | `exit=0` |
| 2 | `grep -v '^\s*$' docs/reports/DEPLOYMENT_REPORT.md \| tail -n 1` | Exactly `DEPLOYMENT SUCCESSFUL` or `DEPLOYMENT FAILED` (the evidence precedes it) |
| 3 | `grep -n "synthetic-data interim deployment" docs/reports/DEPLOYMENT_REPORT.md` | At least one line stating the deployment is a synthetic-data interim deployment |
| 4 | `grep -n "not a go-live" docs/reports/DEPLOYMENT_REPORT.md` | At least one line |
| 5 | `grep -ni "no real resident data was loaded" docs/reports/DEPLOYMENT_REPORT.md` | At least one line |
| 6 | Read the report body | Lists environments, services, URL placeholders or platform domains (no credentials), validation results of TC-088-01..TC-088-16, issues and remediation |

Note: on 15 Nov 2026 `docs/reports/DEPLOYMENT_REPORT.md` does not exist (`MVP_READINESS_CHECKLIST.md` D.02); the case fails until the team writes it.

### TC-088-08 A staging JWT and a staging API key are rejected by production

| Step | Action | Expected Result |
|---|---|---|
| 1 | `curl -sS -X POST "<STAGING_API_BASE_URL>/auth/login" -H 'Content-Type: application/json' -d '{"email":"researcher@example.com","password":"<entered at prompt>"}'` | 200 with `access_token` T (staging) |
| 2 | `curl -sS -o /dev/null -w '%{http_code}\n' "<STAGING_API_BASE_URL>/auth/me" -H "Authorization: Bearer T"` | `200` (token valid where issued) |
| 3 | `curl -sS -i "<PRODUCTION_API_BASE_URL>/auth/me" -H "Authorization: Bearer T"` | `401`; `content-type: application/problem+json` |
| 4 | `curl -sS -o /dev/null -w '%{http_code}\n' -X POST "<PRODUCTION_API_BASE_URL>/sessions" -H "X-API-Key: <staging test-ingest key from the secret store>" -H 'Content-Type: application/json' -d '{}'` | `401`; no row written in production |
| 5 | `curl -sS -X POST "<STAGING_API_BASE_URL>/auth/logout" -H "Authorization: Bearer T"` | Token revoked |

### TC-088-09 Staging dashboard shows the answer-key list and the staging data label

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `<STAGING_FRONTEND_URL>/login`, sign in as `researcher@example.com` | Resident list opens |
| 2 | Read the header | Data label "pipeline test data v0.1" |
| 3 | Read the filter buttons | "All (10)", "Changed (2)", "Needs attention (2)", "Usual (6)" |
| 4 | Read the row order | R09, R10, R03, R08, R01, R02, R04, R05, R06, R07 |
| 5 | Open R09 | Pill "▲ Changed"; change score chart with "Alarm line: 5" |

### TC-088-10 Production dashboard shows the synthetic label and a `T`-prefixed demo resident

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `<PRODUCTION_FRONTEND_URL>/login`, sign in as the production admin | Resident list opens |
| 2 | Read the header | Data label "demo data (synthetic)" on every page visited (Residents, one resident, Admin) |
| 3 | Read the resident rows | Only `T`-prefixed study IDs; no R01–R10 |
| 4 | Sign out | Returns to `/login` |

### TC-088-11 Production and staging variables match the TRD 21 §4.7 matrix; deviations are recorded

| Step | Action | Expected Result |
|---|---|---|
| 1 | Render → environment group `echowell-production-shared` (view only) | `APP_ENV=production`, `PIPELINE_PROFILE=production`, no `PIPELINE_AS_OF`, `DATA_SOURCE_LABEL=demo data (synthetic)` |
| 2 | Render → `echowell-backend-production` → Environment (view only) | No `DATABASE_READONLY_URL`; `JWT_SECRET` set (value not displayed) |
| 3 | Render → `echowell-staging-shared` | `APP_ENV=staging`, `PIPELINE_PROFILE=test_v0_1`, `PIPELINE_AS_OF=2026-10-30T15:00:00-05:00`, `DATA_SOURCE_LABEL=pipeline test data v0.1` |
| 4 | Netlify → each site → Environment variables | `echowell-und-staging`: `NEXT_PUBLIC_APP_ENV=staging`; `echowell-und`: `NEXT_PUBLIC_APP_ENV=production`; only `NEXT_PUBLIC_*`, `NODE_VERSION`, `NEXT_TELEMETRY_DISABLED` |
| 5 | Compare any difference with `docs/deployment.md` "Configuration deviations from the TRD 21 §4.7 matrix" | Every difference has a row with a reason |

### TC-088-12 Regions are Neon `aws-us-east-1` and Render `ohio`; instances are Starter

| Step | Action | Expected Result |
|---|---|---|
| 1 | Neon → project `echowell` → Settings | Region AWS US East (`aws-us-east-1`); PostgreSQL 16 |
| 2 | Render → each of the two web services and two cron jobs → Settings | Region Ohio; web services on instance type Starter (not Free) |
| 3 | `grep -c "region: ohio" render.yaml` | `4` |

### TC-088-13 Migrations run only as the Render pre-deploy command; both branches are at head `0004`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Render → `echowell-api` and `echowell-backend-production` → Settings → Pre-Deploy Command (view only) | `alembic upgrade head` |
| 2 | Production and staging (read-only): `SELECT version_num FROM alembic_version;` | `0004` on both (equals `revision = "0004"` in `backend/alembic/versions/0004_schema_check_grant_data_alert_days.py`) |
| 3 | `grep -rn "alembic upgrade" .github/workflows/deploy-*.yml; echo "exit=$?"` | No match; `exit=1` |

### TC-088-14 Production bootstrap, first admin and roster are audited; no default credential exists

| Step | Action | Expected Result |
|---|---|---|
| 1 | Production (read-only): `SELECT count(*) FROM facilities;` | `1` |
| 2 | `SELECT profile, count(*) FROM config_parameters GROUP BY profile ORDER BY profile;` | Rows for `production` and `test_v0_1` (bootstrap verifies both profiles exist; production never runs `test_v0_1`) |
| 3 | `SELECT action, count(*) FROM audit_logs WHERE action IN ('user.created','api_key.created','roster.loaded') GROUP BY action;` | Each action present at least once |
| 4 | `SELECT email, role FROM users ORDER BY created_at;` | No `admin@example.com`, `clinician@example.com` or `researcher@example.com` (seed users exist only where seeded) |
| 5 | `SELECT name, active FROM api_keys;` | Only keys for test devices or harnesses; no key named `test-ingest` |

### TC-088-15 R01–R10 validation passes in CI on the deployed commit

| Step | Action | Expected Result |
|---|---|---|
| 1 | For SHA P (production) and S (staging), open the `ci.yml` run on that commit | Job `backend-test` conclusion `success` |
| 2 | Download artifact `backend-reports` and open `ALGORITHM_VALIDATION_REPORT.md` | "Overall: PASS"; the Git SHA in the report equals the deployed SHA |
| 3 | Locally on SHA P: `pytest tests/validation -q` | All tests pass, 0 failed |

### TC-088-16 GitHub organisation requires two-factor authentication

| Step | Action | Expected Result |
|---|---|---|
| 1 | GitHub → organisation `EchoWellApp` → Settings → Authentication security (owner view) | "Require two-factor authentication for everyone" is enabled |
| 2 | Open `DEPLOYMENT_CHECKLIST.md` row A.04 | Evidence column records the verification date |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `GET <STAGING_API_BASE_URL>/health`, `GET <PRODUCTION_API_BASE_URL>/health` | 200; `status` `ok`; `database` `ok`; `version` = deployed SHA |
| 2 | `POST <STAGING_API_BASE_URL>/auth/login` (researcher) | 200 with `access_token` |
| 3 | `GET <PRODUCTION_API_BASE_URL>/auth/me` with the staging token | 401, RFC 7807 body |
| 4 | `GET <PRODUCTION_API_BASE_URL>/residents` without token | 401 |
| 5 | `GET <PRODUCTION_API_BASE_URL>/audio` | 404 |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | Production: seed-linked `raw_sessions` count (TC-088-04) | 0 |
| 2 | Production: resident codes not starting with `T` (TC-088-06) | 0 rows |
| 3 | Staging: resident codes outside R01–R10 and `T`-prefixed (TC-088-06) | 0 rows |
| 4 | Both: `alembic_version.version_num` (TC-088-13) | `0004` |
| 5 | Production: audit rows `user.created`, `api_key.created`, `roster.loaded` (TC-088-14) | Present |
| 6 | Production: `SELECT count(*) FROM evaluation_ground_truth;` | 0 |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Start a production configuration with `PIPELINE_PROFILE=test_v0_1` (TC-088-05) | Exit 1, `startup_config_invalid`, `PIPELINE_PROFILE` named |
| 2 | Production configuration with `PIPELINE_AS_OF` set (TC-088-05) | Exit 1, `PIPELINE_AS_OF` named |
| 3 | `seed test_v0_1` with `APP_ENV=production` (TC-088-05) | Exit 2, "seeding is not allowed in production" |
| 4 | Staging JWT on production `/auth/me`; staging API key on production `/sessions` (TC-088-08) | 401 each |
| 5 | `http://` request to the production frontend (TC-088-02) | Redirect to `https://` |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-088-AC-01 | Health returns `status` ok, `database` ok and `version` = deployed SHA for staging and production | TC-088-01 |
| FEAT-088-AC-02 | `curl -fsSI "$FRONTEND_URL/residents"` succeeds over HTTPS for both environments | TC-088-02 |
| FEAT-088-AC-03 | `deploy-staging.yml` and `deploy-production.yml` are green on the deployed commits | TC-088-03 |
| FEAT-088-AC-04 | Production `raw_sessions` has zero rows linked to `ingest_batches.source = 'seed'` | TC-088-04 |
| FEAT-088-AC-05 | Starting production with `PIPELINE_PROFILE=test_v0_1` is refused | TC-088-05 |
| FEAT-088-AC-06 | No resident_code outside R01–R10 (staging) and `T`-prefixed demo IDs | TC-088-06 |
| FEAT-088-AC-07 | `DEPLOYMENT_REPORT.md` exists, ends with the verdict line, states synthetic-data interim, not a go-live, no real resident data loaded | TC-088-07 |
| FEAT-088-AC-08 | A staging JWT is rejected (401) by production | TC-088-08 |

## Test Data Requirements

- Staging: `test_v0_1` (R01–R10, devices D01–D…, seed users, API key `test-ingest`, DS-10 answer key), PIPELINE_AS_OF 2026-10-30T15:00:00-05:00.
- Production: `T`-prefixed demo residents and test devices only; the production admin created interactively; no seed data.
- Local: Compose stack for TC-088-05 (`.env.development.example`).
- Placeholders `<STAGING_API_BASE_URL>`, `<PRODUCTION_API_BASE_URL>`, `<STAGING_FRONTEND_URL>`, `<PRODUCTION_FRONTEND_URL>`; passwords and keys entered at prompts only.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| DEP-001, DEP-004, DEP-005, ARC-080 | FEAT-088 | TC-088-01, TC-088-11 |
| DEP-002, DEP-003 | FEAT-088 | TC-088-03 |
| D-59, DEP-074 | FEAT-088 | TC-088-09, TC-088-11 |
| AGT-015, SEC-116, SEC-004 | FEAT-088 | TC-088-05, TC-088-10, TC-088-11 |
| DEP-007, DEP-008, DEP-073, DEP-093 | FEAT-088 | TC-088-04, TC-088-06 |
| DEP-070, DEP-072, DEP-075, SEC-017 | FEAT-088 | TC-088-05, TC-088-14 |
| DEP-006, ENV-051 | FEAT-088 | TC-088-08 |
| SEC-003, AGT-014 | FEAT-088 | TC-088-14 |
| DEP-060, ARC-082 | FEAT-088 | TC-088-13 |
| ARC-083, DEP-080, DEP-081, TST-152 | FEAT-088 | TC-088-01, TC-088-02, TC-088-03 |
| AC-AGT-04 | FEAT-088 | TC-088-15 |
| ARC-084, D-54, D-156 | FEAT-088 | TC-088-12 |
| AC-AGT-10, VIS-024 | FEAT-088 | TC-088-07 |
| ENV-050 | FEAT-088 | TC-088-11 |
| TPS-040 | FEAT-088 | TC-088-16 |
| FEAT-088-FR-01..FEAT-088-FR-15 | FEAT-088 | TC-088-01..TC-088-16 |
