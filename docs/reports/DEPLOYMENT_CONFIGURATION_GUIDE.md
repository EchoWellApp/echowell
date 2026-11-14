# EchoWell Deployment Configuration Guide

Document: docs/reports/DEPLOYMENT_CONFIGURATION_GUIDE.md · Block 3 checkpoint 8 (TRD 25 Phase 9, `Implement_Feature_Batches.md` Phase 14A) · Date: 5 November 2026 · Owner: Team 2 · Feature: FEAT-087

This guide describes the deployment configuration generated in checkpoint 8 and how it is applied in Block 4 (TRD 25 Phase 10). It follows TRD 15 (deployment), TRD 16 (CI/CD), TRD 21 (environment configuration), TRD 22 (hosting), TRD 12 (security) and SRC-01 (`specs/architecture/Deployment_Architecture.md`). **No deployment was performed in checkpoint 8.** The operational runbook is `docs/deployment.md`; the ordered deployment record is `specs/backlog/DEPLOYMENT_CHECKLIST.md`; the validation of the generated files is `docs/reports/CONFIGURATION_VALIDATION_REPORT.md`.

Interim stack (current): Netlify (frontend) + Render (backend web services and nightly cron jobs, Docker from `backend/Dockerfile`, region `ohio`) + Neon (PostgreSQL 16, `aws-us-east-1`), synthetic and team-test data only (D-OWNER-4). Target production: AWS (TRD 15 §4.16), go-live only there.

## 1. Generated configuration files

| File | Purpose | Requirement | Feature |
|---|---|---|---|
| `netlify.toml` | Both Netlify sites: base `frontend/`, `node scripts/check-csp.mjs && npm run build`, Node 20, `@netlify/plugin-nextjs`, ignore command, TRD 12 §4.9 headers | DEP-050..DEP-054, SEC-062, SEC-070 | FEAT-082 |
| `frontend/scripts/check-csp.mjs` | Build-time CSP check (`connect-src` = deployed API origins) | SEC-070 | FEAT-082 |
| `render.yaml` | Render Blueprint: `echowell-api`, `echowell-backend-production`, cron jobs `echowell-nightly-staging` / `echowell-nightly-production` (`0 7,8 * * *` UTC), environment groups; secrets `sync: false` | DEP-040..DEP-048, DEP-044 | FEAT-081 |
| `backend/Dockerfile`, `.dockerignore` | `python:3.12-slim`, non-root UID 10001, copies `backend/`, `analytics/`, `database/`, `alembic.ini` | DEP-020..DEP-022 | FEAT-077 |
| `frontend/Dockerfile`, `frontend/.dockerignore` | `node:20-alpine` multi-stage build for the `demo` profile and E2E only | DEP-023 | FEAT-077 |
| `docker-compose.yml` | `db`, `backend`, `frontend`, `demo` profile `frontend-prod` | DEP-010..DEP-019 | FEAT-077 |
| `.env.example`, `.env.development.example`, `.env.production.example` | TRD 21 §4.6 templates | ENV-005, ENV-041 | FEAT-077 |
| `.github/workflows/ci.yml` | the CIC-070 required checks | CIC-010..CIC-027 | FEAT-078 |
| `.github/workflows/e2e.yml` | `playwright` (required), `performance`, `lighthouse`, `nightly-validation` | CIC-030..CIC-037 | FEAT-080 |
| `.github/workflows/deploy-staging.yml` | staging verification, re-seed, smoke | CIC-040..CIC-043 | FEAT-086 |
| `.github/workflows/deploy-production.yml` | manual approved release | CIC-050..CIC-053 | FEAT-086 |
| `.github/workflows/uptime.yml` | 30-minute uptime check, `incident` issue | CIC-060, CIC-061 | FEAT-085 |
| `.github/dependabot.yml` | dependency updates targeting `main` | TRD 18 | FEAT-078 |
| `tests/smoke/` | post-deploy smoke tests and the deploy wait helper | DEP-080..DEP-082, SEC-066 | FEAT-086, FEAT-083 |
| `tests/performance/` | DS-08 performance budgets | TST-120..TST-126, TST-190 | FEAT-079 |
| `backend/core/monitoring.py` | optional Sentry initialisation (backend only) | LOG-100..LOG-102 | FEAT-084 |

## 2. Local procedure (TRD 15 §4.2, verbatim)

1. Install Docker Desktop 4.x (or Docker Engine 24+ with Compose v2), Git, and optionally Node.js 20 LTS and Python 3.12 for running tools outside containers.
2. `git clone https://github.com/EchoWellApp/echowell.git && cd echowell`
3. `cp .env.development.example .env` (values in TRD 21 §4.6). Do not edit `JWT_SECRET` for local use unless sharing the stack on a network.
4. `docker compose up --build -d`
5. Wait until `docker compose ps` shows `db` healthy and `curl -s http://localhost:8000/api/v1/health` returns `"status":"ok"`.
6. `docker compose exec backend python -m backend.cli seed test_v0_1`, then `docker compose exec backend python database/seeds/load_evaluation_ground_truth.py tests/fixtures/answer_key/evaluation_ground_truth_v0_1.csv` (Study team alarm timing check; test_v0_1 only).
7. The seed has created `admin@example.com`, `clinician@example.com` and `researcher@example.com` with the local values of SEED_ADMIN_PASSWORD, SEED_CLINICIAN_PASSWORD and SEED_RESEARCHER_PASSWORD from `.env` (TRD 21; never printed, TRD 06 DB-057).
8. Open `http://localhost:3000`, sign in as `admin@example.com`, confirm the Resident list filters "All (10)", "Changed (2)", "Needs attention (2)", "Usual (6)".
9. Reset: `docker compose down -v` deletes the `pgdata` volume; repeat from step 4.

The `demo` profile adds the production-build frontend on port 3001: `docker compose --profile demo up -d --wait db backend frontend-prod` (DEP-017; E2E and demo fallback).

## 3. Neon procedure (TRD 15 §4.4)

1. Sign in to Neon with the team-owned account (TRD 22, TPS ownership rules).
2. Create project `echowell`, PostgreSQL version **16**, region **AWS US East 1 (N. Virginia)** (`aws-us-east-1`), database name `echowell`.
3. The default database branch is renamed or confirmed as `main` (production). Neon branches are database branches, unrelated to Git branches.
4. As the Neon project owner role (SQL editor, once per branch-tree before any migration), run `CREATE EXTENSION IF NOT EXISTS pgcrypto; CREATE EXTENSION IF NOT EXISTS btree_gist; ALTER DATABASE echowell SET timezone = 'UTC';`, then create the roles `echowell_migrator` (schema owner; DATABASE_MIGRATION_URL only), `echowell_app` (runtime DML) and `echowell_readonly` (SELECT) and their login roles through the console. Grants for `echowell_app` come from the Alembic migrations. `database/roles/provision_login_roles.sql` is never run here.
5. Create child database branch `staging` from `main` immediately after step 4 (empty schema).
6. Copy per branch the **pooled** string for `echowell_app` (host contains `-pooler`) and the **direct** string for `echowell_migrator`, plus for `staging` only the pooled string for `echowell_readonly`; each with `sslmode=require`. Store them only in Render variables (and the staging migrator string as the GitHub secret `STAGING_DATABASE_URL`).
7. Keep compute autosuspend at the plan default (5 min) on both branches and accept cold starts (RSK-07).

Record the results (without connection strings) and the point-in-time restore window in `docs/deployment.md` → "Neon".

## 4. Render procedure (TRD 15 §4.5)

1. Render project `echowell` (team-owned workspace) with environments `staging` and `production`, each with one web service, one cron job and one environment group. The existing web service `echowell-api` (`https://echowell-api.onrender.com`) is the staging web service: keep it, attach it to `staging`, move it from Free to Starter (D-154, D-157). Create `echowell-backend-production` later, when production is needed, in the same region `ohio` (D-156).
2. Create the remaining services from the Blueprint (Dashboard → New → Blueprint, repository `EchoWellApp/echowell`, branch `main`). Every web service: runtime Docker, Dockerfile `./backend/Dockerfile`, context `.`, branch `main`, pre-deploy command `alembic upgrade head`, Docker command `sh -c 'export GIT_SHA="${RENDER_GIT_COMMIT:-unknown}"; exec uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips="*"'`, health check `/api/v1/health`, build filter `backend/**`, `analytics/**`, `database/**`, `alembic.ini`, Starter, 1 instance, region `ohio`. Auto-deploy: staging "After CI checks pass" (`checksPass`), production off.
3. Cron jobs `echowell-nightly-staging` / `echowell-nightly-production`: same image, schedule `0 7,8 * * *` (UTC), command `sh -c 'export GIT_SHA="${RENDER_GIT_COMMIT:-unknown}"; exec python -m backend.jobs.nightly_run'`, no pre-deploy command, no public URL, only the environment group's variables.
4. Variables per §7 of this guide: shared ones in `echowell-staging-shared` / `echowell-production-shared`; web-only ones on the web service. Secrets are entered only in the dashboard. `GIT_SHA` and `PORT` are never set by hand.
5. Deploy and verify `GET https://<backend-domain>/api/v1/health` returns 200 with `version` = deployed commit.
6. Workspace notifications (failed deploys, service failures) to the DevOps owner; record the outbound IP ranges and every dashboard-only setting in `docs/deployment.md` (DEP-044).

## 5. Netlify procedure (TRD 15 §4.6)

1. "Add new site → Import from Git" → `EchoWellApp/echowell` twice: staging site `echowell-und-staging` and production site `echowell-und` (record actual names if taken).
2. Build settings of both sites come from `/netlify.toml` (base `frontend/`, `node scripts/check-csp.mjs && npm run build`, publish `.next`, Node 20, `@netlify/plugin-nextjs`).
3. Staging site: production branch `main`, auto publishing on, branch deploys off, deploy previews on for PRs.
4. Production site: "Stop builds"; branch deploys and deploy previews off; it is published only by `deploy-production.yml` (`netlify deploy --build --prod`). Record its site ID as the GitHub variable `NETLIFY_PRODUCTION_SITE_ID`.
5. Site variables for all deploy contexts: staging `NEXT_PUBLIC_API_BASE_URL=https://echowell-api.onrender.com`, `NEXT_PUBLIC_APP_ENV=staging`; production `NEXT_PUBLIC_API_BASE_URL=https://echowell-backend-production.onrender.com`, `NEXT_PUBLIC_APP_ENV=production`. `netlify.toml` has no deploy-context environment blocks (D-99).
6. Merge a commit to `main`; confirm the staging login page renders and the network tab shows calls only to the staging backend.

## 6. GitHub configuration

### 6.1 Environments, secrets and variables (TRD 16 §4.9, CIC-090)

| Name | Kind | Scope | Used by |
|---|---|---|---|
| `STAGING_DATABASE_URL` | secret | environment `staging` (deployment branch rule `main`) | `deploy-staging.yml` re-seed |
| `STAGING_SEED_ADMIN_PASSWORD`, `STAGING_SEED_CLINICIAN_PASSWORD`, `STAGING_SEED_RESEARCHER_PASSWORD`, `STAGING_SEED_INGEST_API_KEY` | secrets | environment `staging` | re-seed (as SEED_*); smoke login (researcher) |
| `RENDER_API_KEY`, `NETLIFY_AUTH_TOKEN` | secrets | environment `production` (branch rule `main`, required reviewer from `team2-devops` or the algorithm lead, prevent self-review) | `deploy-production.yml` job `deploy` |
| `RENDER_PRODUCTION_BACKEND_SERVICE_ID`, `RENDER_PRODUCTION_NIGHTLY_SERVICE_ID`, `NETLIFY_PRODUCTION_SITE_ID` | variables | environment `production` | `deploy-production.yml` job `deploy` |
| `STAGING_API_BASE_URL` (`https://echowell-api.onrender.com/api/v1`), `STAGING_FRONTEND_URL` (`https://echowell-und-staging.netlify.app`), `PRODUCTION_API_BASE_URL` (`https://echowell-backend-production.onrender.com/api/v1`), `PRODUCTION_FRONTEND_URL` (`https://echowell-und.netlify.app`) | variables | repository | deploy workflows, `uptime.yml` |
| `GITHUB_TOKEN` | automatic | per job (`${{ github.token }}`) | release, issues, check-run lookup |

No other secret exists in GitHub: no production database URL, JWT secret, API key or user credential (CIC-090).

### 6.2 Branch protection on `main` (CIC-070, CIC-071, AC-CIC-08)

Settings → Branches → rule for `main` (the only long-lived branch):

| Setting | Value |
|---|---|
| Require a pull request before merging | on; at least 1 approval (the algorithm lead approves checkpoint PRs, AGT-013) |
| Require status checks to pass before merging | on, with exactly these eight checks: `repo-hygiene`, `backend-lint`, `backend-test`, `openapi-contract`, `frontend`, `security-audit`, `docker-build`, `playwright` |
| Require branches to be up to date before merging | on (CIC-071) |
| Not required | `e2e.yml` jobs `performance`, `lighthouse`, `nightly-validation`; `deploy-staging.yml`, `deploy-production.yml`, `uptime.yml` |
| Pushes | no direct pushes to `main`; no force pushes; no deletion |

The check names are the job ids of `ci.yml` and `e2e.yml` (TRD 16 §8); `deploy-production.yml` job `verify` checks the same eight names on the released commit (CIC-053).

### 6.3 Workflow set (CIC-002)

`ci.yml`, `e2e.yml`, `deploy-staging.yml`, `deploy-production.yml`, `uptime.yml`; no other workflow. All use `ubuntu-24.04`, `permissions: contents: read` by default (only `deploy-production.yml` job `release` has `contents: write`; `uptime.yml` has `issues: write`), actions from `actions/*` pinned to a major tag, and `timeout-minutes` ≤ 20 per job (CIC-024, CIC-025, CIC-027, CIC-111).

## 7. Environment-variable matrix (TRD 21 §4.2, §4.3, §4.5, §4.7)

Value sources: **tmpl** = committed template (`.env.development.example` for local), **CI** = workflow env, **RG** = Render environment group (web service and cron job), **RW** = Render web service only, **NS** = Netlify site variable, **GH** = GitHub secret or variable, **SM** = AWS Secrets Manager. "—" = not set.

### 7.1 Backend variables (§4.2, §4.3)

| Variable | Secret | local | test (CI) | staging | production (interim) | AWS target |
|---|---|---|---|---|---|---|
| `APP_ENV` | no | `local` (tmpl) | `test` (CI) | `staging` (RG) | `production` (RG) | `production` |
| `DATABASE_URL` | yes | Compose `db`, `echowell_app_login` (tmpl) | CI service `echowell_test`, `echowell_app_login` | Neon `staging` pooled, app role, `sslmode=require` (RG) | Neon `main` pooled, app role, `sslmode=require` (RG) | RDS, app role, `sslmode=require` (SM) |
| `DATABASE_MIGRATION_URL` | yes | Compose `db`, `echowell_migrator_login` (tmpl) | CI service, `echowell_migrator_login` | Neon `staging` direct, migrator role (RW only); re-seed: GH `STAGING_DATABASE_URL` | Neon `main` direct, migrator role (RW only) | RDS migrator role, migration task only (SM) |
| `DATABASE_READONLY_URL` | yes | Compose `db`, `echowell_readonly_login` (tmpl) | CI service, `echowell_readonly_login` | Neon `staging` pooled, readonly role (RW) | not set (SEC-116) | not set |
| `JWT_SECRET` | yes | local-dev-only value (tmpl) | `openssl rand -hex 32` per run (CI) | unique secret (RW) | unique secret, different from staging (RW) | unique secret (SM) |
| `JWT_EXPIRES_MINUTES` | no | `60` (default) | `60` | `60` (RW) | `60` (RW) | `60` |
| `CORS_ORIGINS` | no | `http://localhost:3000,http://localhost:3001` | `http://localhost:3000` | `https://echowell-und-staging.netlify.app` (RW) | `https://echowell-und.netlify.app` (RW) | Amplify production domain |
| `CORS_ORIGIN_REGEX` | no | empty | empty | `^https://deploy-preview-\d+--echowell-und-staging\.netlify\.app$` (RW) | empty | empty |
| `FACILITY_NAME` | no | `Edgewood` | `Edgewood` | `Edgewood` (RG) | `Edgewood` (RG) | `Edgewood` |
| `FACILITY_TZ` | no | `America/Chicago` | `America/Chicago` | `America/Chicago` (RG) | `America/Chicago` (RG) | `America/Chicago` |
| `PIPELINE_PROFILE` | no | `test_v0_1` | `test_v0_1` | `test_v0_1` (RG) | `production` (RG) | `production` |
| `PIPELINE_AS_OF` | no | `2026-10-30T15:00:00-05:00` | set per test | `2026-10-30T15:00:00-05:00` (RG) | empty (refused when set) | empty |
| `NIGHTLY_RUN_HOUR_LOCAL` | no | `2` | `2` | `2` (RG) | `2` (RG) | `2` (EventBridge 02:00) |
| `LOG_LEVEL` | no | `INFO` | `INFO` | `INFO` (RG) | `INFO` (RG) | `INFO` |
| `LOG_FORMAT` | no | `console` | `json` | `json` (RG) | `json` (RG) | `json` |
| `SENTRY_DSN` | yes | empty | empty | optional (RG) | optional, synthetic data only (RG) | empty unless re-approved (TPS-061) |
| `RATE_LIMIT_LOGIN` | no | `5/minute` (E2E stack `60/minute`) | `5/minute` | `5/minute` (RW) | `5/minute` (RW) | `5/minute` |
| `RATE_LIMIT_INGEST` | no | `600/minute` | `600/minute` | `600/minute` (RW) | `600/minute` (RW) | `600/minute` |
| `GIT_SHA` | no | `unknown` or `git rev-parse HEAD` | `${{ github.sha }}` | exported from `RENDER_GIT_COMMIT` by the Docker command | same; = released SHA | image build argument |
| `DATA_SOURCE_LABEL` | no | `pipeline test data v0.1` | `pipeline test data v0.1` | `pipeline test data v0.1` (RW) | `demo data (synthetic)` (RW) | `Edgewood check-ins` |
| `SEED_ADMIN_PASSWORD`, `SEED_CLINICIAN_PASSWORD`, `SEED_RESEARCHER_PASSWORD`, `SEED_INGEST_API_KEY` | yes | `local-dev-only-*` placeholders (tmpl) | generated per job, masked (`e2e.yml`) | only in the re-seed step, from GH `STAGING_SEED_*` | never (startup refuses) | never |
| `PORT` | no | `8000` | `8000` | injected by Render | injected by Render | App Runner `8000` |

### 7.2 Frontend, Compose, CI and test-harness variables (§4.5)

| Variable | Secret | local | test / CI | staging | production | Source |
|---|---|---|---|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | no (public) | `http://localhost:8000` | `http://localhost:8000` | `https://echowell-api.onrender.com` | `https://echowell-backend-production.onrender.com` | tmpl; Compose build arg; NS |
| `NEXT_PUBLIC_APP_ENV` | no | `local` | `local` | `staging` | `production` | tmpl; NS |
| `NEXT_PUBLIC_GIT_SHA` | no | derived (`unknown`) | derived | `COMMIT_REF` (Netlify Git build) | `GIT_SHA` set by `deploy-production.yml` | `next.config.js` (ENV-033) |
| `NEXT_TELEMETRY_DISABLED` | no | `1` | `1` | `1` | `1` | `netlify.toml`, Dockerfile |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | placeholders | `echowell` / `local-dev-only-postgres` / `echowell` | `echowell` / `ci-only-postgres` / `echowell_test` | — | — | Compose `db`, CI service |
| `ECHOWELL_MIGRATOR_DB_PASSWORD`, `ECHOWELL_APP_DB_PASSWORD`, `ECHOWELL_READONLY_DB_PASSWORD` | placeholders | `local-dev-only-*` | `ci-only-*` | never | never | Compose, CI |
| `SMOKE_API_BASE_URL`, `SMOKE_FRONTEND_URL`, `SMOKE_EXPECTED_SHA`, `SMOKE_ENV` | no | optional local run | — | from GH variables, pushed SHA, `staging` | from GH variables, released SHA, `production` | deploy workflows |
| `SMOKE_USER_EMAIL`, `SMOKE_USER_PASSWORD` | yes | optional local run | — | `researcher@example.com` / GH `STAGING_SEED_RESEARCHER_PASSWORD` | never set | `deploy-staging.yml` |
| `E2E_BASE_URL` | no | `http://localhost:3001` | `http://localhost:3001` | — | — | `e2e.yml` |
| `STAGING_DATABASE_URL`, `STAGING_SEED_*` (4), `RENDER_API_KEY`, `NETLIFY_AUTH_TOKEN` | yes | — | — | GH environment `staging` | GH environment `production` | §6.1 |
| `STAGING_API_BASE_URL`, `STAGING_FRONTEND_URL`, `PRODUCTION_API_BASE_URL`, `PRODUCTION_FRONTEND_URL`, `NETLIFY_PRODUCTION_SITE_ID`, `RENDER_PRODUCTION_BACKEND_SERVICE_ID`, `RENDER_PRODUCTION_NIGHTLY_SERVICE_ID` | no | — | — | GH variables | GH variables | §6.1 |
| `PYTHON_VERSION`, `NODE_VERSION` | no | — | workflow env `3.12`, `20` | workflow env | workflow env | workflows; `NODE_VERSION` also in `netlify.toml` |

Deviations from the TRD 21 §4.7 matrix are recorded in `docs/deployment.md` → "Configuration deviations" (ENV-050).

## 8. Staging deploy (automatic from `main`, D-99; TRD 15 §4.9 verbatim)

1. Open a PR from a short-lived `feat/...`, `fix/...`, `docs/...` or `chore/...` branch directly to `main` (TRD 18 GIT-012); CI (TRD 16) must be green and the PR approved; Netlify posts a deploy preview of the staging site pointing to the staging backend.
2. Merge the PR into `main`.
3. Render `staging` waits until the commit's GitHub checks pass ("After CI checks pass"), builds `backend/Dockerfile` for the web service and the cron job, runs the pre-deploy command `alembic upgrade head`, starts uvicorn and switches traffic once the health check passes.
4. Netlify builds and publishes the staging site `echowell-und-staging` from `main`.
5. GitHub Actions `deploy-staging.yml` (TRD 16 §4.4, triggered by the push to `main`) waits until `GET /api/v1/health` reports `version` = merged SHA, re-seeds the staging database if DEP-074 applies, and runs the staging smoke tests (DEP-080).
6. The algorithm lead reviews the staging dashboard (Resident list filters 10 / 2 / 2 / 6, R09 chart with the alarm) before that commit is chosen for a production release.

Production is not touched by any of these steps. Staging setup: the staging environment is deployed from `main` only; there is no `staging` Git branch and no promotion PR.

`deploy-staging.yml` (TRD 16 §4.4): trigger `push` to `main` and `workflow_dispatch` (`reseed`); concurrency `deploy-staging` (queued). Job `wait-for-staging` (≤ 18 min): decides on re-seeding (push changing `backend/alembic/` or `analytics/`, or `reseed: true`; unknown previous commit re-seeds), polls health `version` and the `echowell-build` meta every 15 s for 15 min with `tests/smoke/wait_for_deploy.py`, accepting `git log -1 --format=%H -- frontend netlify.toml` when Netlify skipped the build. Job `reseed-and-smoke` (environment `staging`, ≤ 20 min): `python -m backend.cli seed test_v0_1 --reset` and `python database/seeds/load_evaluation_ground_truth.py tests/fixtures/answer_key/evaluation_ground_truth_v0_1.csv` with the ENV-053 variable set (both database URLs = `STAGING_DATABASE_URL`), then `pytest tests/smoke -m smoke` with `SMOKE_ENV=staging`, artifact `smoke-report` (30 days).

## 9. Production release (manual, D-99; TRD 15 §4.10 verbatim)

1. Choose a `main` commit whose required checks passed and whose `deploy-staging.yml` run succeeded (step 4.9.5), and the version `vX.Y.Z` (TRD 18 §4.7).
2. If the release contains a migration, create Neon restore database branch `pre-<short-sha>` from `main` (DEP-063) and take the DEP-096 dump.
3. Run the GitHub Actions workflow `deploy-production.yml` manually (`workflow_dispatch`, inputs `sha` and `version`; TRD 16 §4.5). The workflow first verifies, before any approval is asked for, that the commit is on `main`, its required checks passed and its staging deploy succeeded (job `verify`, "Wait for CI" semantics, TRD 16 CIC-053; TRD 24 D-165); if a check fails the run stops and no reviewer is asked. Only the following `deploy` job uses the GitHub environment `production`, so it then waits until a required reviewer approves.
4. After approval the workflow triggers a Render deploy of that commit for the production web service and cron job through the Render API (`commitId` = SHA; pre-deploy `alembic upgrade head`, health check; `GIT_SHA` comes from `RENDER_GIT_COMMIT`) and waits until both deploys are `live`; publishes the Netlify production site with `netlify deploy --build --prod` from the same commit; waits for `version` = released SHA; runs the production smoke tests (DEP-081); then creates the Git tag `vX.Y.Z` and a GitHub Release.
5. If smoke tests fail, follow the rollback procedure (4.12) within 30 minutes; no tag is created.

`deploy-production.yml` (TRD 16 §4.5): trigger `workflow_dispatch` only (inputs `sha`, `version`, `smoke_only`); concurrency `deploy-production`. Jobs: `verify` (≤ 10 min; `contents/checks/actions: read`) → `deploy` (environment `production`, ≤ 20 min; Render `POST /v1/services/{id}/deploys` with `{"commitId": "<sha>"}` for both service IDs, polled every 15 s until `live`, failing on `build_failed`, `pre_deploy_failed`, `update_failed`, `canceled`, `deactivated` or 20 min; then `npx netlify-cli@17 deploy --build --prod --site <NETLIFY_PRODUCTION_SITE_ID>` in `frontend/` with `GIT_SHA`) → `wait-for-production` (≤ 18 min) → `smoke` (`pytest tests/smoke -m "smoke and not authenticated"`, `smoke-report`) → `release` (`gh release create vX.Y.Z --generate-notes --target <sha>`, notes carry the DEP-083 manual-check line). The Render key is passed to `curl` through a header file, never on the command line (CIC-092).

## 10. Post-deploy smoke tests (TRD 15 §4.11)

| Suite | Marker | Checks |
|---|---|---|
| `tests/smoke/test_staging_smoke.py` | `smoke` (+ `authenticated` for login tests) | DEP-080 (a)–(i) |
| `tests/smoke/test_production_smoke.py` | `smoke` only | DEP-081 (a)–(f), unauthenticated and read-only |
| `tests/smoke/test_tls.py` | `smoke` | DEP-080 (j), DEP-081 (g), SEC-066 (TLS 1.1 refused, TLS 1.2 accepted, both origins) |

Targets come from `SMOKE_*` (§7.2). A run finishes in well under 5 minutes excluding the wait (DEP-082); locally it ran in under 1 s against the seeded backend (see `CONFIGURATION_VALIDATION_REPORT.md`). Commands and the local invocation are in `docs/deployment.md` → "Smoke tests".

## 11. Rollback (TRD 15 §4.12)

| Failure | Action | Time target |
|---|---|---|
| Frontend broken, backend fine | Netlify → Deploys → last good deploy → "Publish deploy"; revert on `main` by PR | 5 min |
| Backend fails health check or pre-deploy | nothing immediately: Render keeps the previous deploy; fix forward by PR | 0 min |
| Backend healthy but broken, no migration | Render → service → Events → last good deploy → "Rollback" (web service and cron job); re-enable staging auto-deploy after the revert; production: `deploy-production.yml` for the fixed commit | 10 min |
| Backend broken after an additive migration | roll back as above; a rollback never re-runs the pre-deploy command or other operational commands (D-158); if the older image cannot run on the newer revision, revert and deploy forward; never `alembic downgrade` in production | 10 min |
| Data damaged | revoke API keys, restore Neon from `pre-<short-sha>` or PITR, redeploy, `run-pipeline --scope all`, issue new device keys, `incident` issue | 60 min |

## 12. Backup and restore (TRD 15 §4.13)

Neon PITR (window recorded in `docs/deployment.md`), weekly and pre-migration `pg_dump --format=custom --no-owner` by the data steward to PI-designated storage (never committed, never an artifact), restore drill into branch `restore-drill` once before 15 Nov 2026 (DEP-095..DEP-098). On AWS: RDS automated backups (14 days) and KMS-encrypted snapshots.

## 13. Demo fallback (TRD 15 §4.14)

If production does not pass DEP-081 by 5 Nov 2026: `docker compose --profile demo up -d db backend frontend-prod` on a team laptop with the commit on `main`, dashboard `http://localhost:3001`, device posts to `http://<laptop LAN IP>:8000/api/v1/sessions` with the backend bound to the LAN only during the demo; rehearsed once before 15 Nov 2026 (DEP-090..DEP-093). Steps in `docs/deployment.md` → "Demo fallback".

## 14. Monitoring

`uptime.yml` every 30 minutes (never shorter) with one 60 s retry and the `incident` issue (CIC-060, CIC-061, LOG-103); watchers DevOps owner and algorithm lead (LOG-114); weekly usage check and the DEP-102 fallback order; optional backend-only Sentry with the TPS-061 go-live rule. Details in `docs/deployment.md` → "Monitoring and alerts", "Usage monitoring", "Error monitoring with Sentry".
