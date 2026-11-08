# Deployment and operations runbook

Operational guide (TRD 18 GIT-054) for the three environments `local`, `staging` and `production`. Requirements: TRD 15 (deployment), TRD 16 (CI/CD), TRD 21 (configuration), TRD 22 (hosting), TRD 12 (security), TRD 17 (monitoring). The configuration reference with the full variable matrix is `docs/reports/DEPLOYMENT_CONFIGURATION_GUIDE.md`; the step-by-step deployment record is `specs/backlog/DEPLOYMENT_CHECKLIST.md`.

Written in Block 3 checkpoint 8 (Phase 14A, FEAT-084..FEAT-087). **No deployment was performed in that checkpoint**; the values marked "recorded in Phase 10" are filled in by the Block 4 deployment PR (FEAT-088) and never contain credentials.

## Hard rules

| Rule | Source |
|---|---|
| The interim Netlify / Render / Neon stack, including the environment named `production`, holds synthetic and team-test data only. No real resident data is ever loaded, ingested or connected there; go-live happens only on AWS. | DEP-008, DEP-118, TPS-002, TPS-003, D-OWNER-4 |
| Production never runs `PIPELINE_PROFILE=test_v0_1`, never sets `PIPELINE_AS_OF` and is never seeded. | DEP-007, DEP-070, ENV-010, ENV-012 |
| Schema changes reach staging and production only through the Render pre-deploy command `alembic upgrade head`; no workflow runs migrations against production; no `alembic downgrade` in production. | DEP-040, DEP-060, DEP-086, CIC-003 |
| Secrets live only in Render environment variables and environment groups, the five GitHub `staging` environment secrets, the two GitHub `production` deploy tokens and (AWS) Secrets Manager. | ENV-005, DEP-033, CIC-090 |
| Branching: `main` plus short-lived feature branches. Every merge to `main` deploys staging; production changes only through an approved manual run of `deploy-production.yml`. There is no `staging` Git branch. | D-99, DEP-002..DEP-004, GIT-012 |

## Environments

| Aspect | local | staging | production |
|---|---|---|---|
| Git source | working tree | `main`, every merge (platform integrations) | a `main` commit released by `deploy-production.yml` (manual, approved, tag `vX.Y.Z`) |
| Frontend | `next dev` :3000 (Compose); `frontend-prod` :3001 (`demo` profile) | Netlify site `echowell-und-staging` (production branch `main`, auto publish, deploy previews) | Netlify site `echowell-und` (builds stopped; published only by `deploy-production.yml`) |
| Backend | uvicorn :8000 (Compose) | Render project `echowell`, environment `staging`: web service `echowell-api` (existing, `https://echowell-api.onrender.com`) and cron job `echowell-nightly-staging`; auto-deploy "After CI checks pass" | Render environment `production`: web service `echowell-backend-production` and cron job `echowell-nightly-production`; auto-deploy off |
| Database | `postgres:16-alpine`, volume `pgdata` | Neon project `echowell`, database branch `staging` | Neon project `echowell`, database branch `main` |
| APP_ENV / PIPELINE_PROFILE | `local` / `test_v0_1` | `staging` / `test_v0_1` | `production` / `production` |
| Region | — | Render `ohio` (US East, D-156), Neon `aws-us-east-1` | same |

The production Render services are created when production is needed (TRD 24 D-154), in the region of `echowell-api`. Render is a temporary staging and prototyping platform until the AWS move (D-157).

## Local environment (Docker Compose)

The local setup procedure of TRD 15 §4.2, reproduced verbatim:

1. Install Docker Desktop 4.x (or Docker Engine 24+ with Compose v2), Git, and optionally Node.js 20 LTS and Python 3.12 for running tools outside containers.
2. `git clone https://github.com/EchoWellApp/echowell.git && cd echowell`
3. `cp .env.development.example .env` (values in TRD 21 §4.6). Do not edit `JWT_SECRET` for local use unless sharing the stack on a network.
4. `docker compose up --build -d`
5. Wait until `docker compose ps` shows `db` healthy and `curl -s http://localhost:8000/api/v1/health` returns `"status":"ok"`.
6. `docker compose exec backend python -m backend.cli seed test_v0_1`, then `docker compose exec backend python database/seeds/load_evaluation_ground_truth.py tests/fixtures/answer_key/evaluation_ground_truth_v0_1.csv` (Study team alarm timing check; test_v0_1 only).
7. The seed has created `admin@example.com`, `clinician@example.com` and `researcher@example.com` with the local values of SEED_ADMIN_PASSWORD, SEED_CLINICIAN_PASSWORD and SEED_RESEARCHER_PASSWORD from `.env` (TRD 21; never printed, TRD 06 DB-057).
8. Open `http://localhost:3000`, sign in as `admin@example.com`, confirm the Resident list filters "All (10)", "Changed (2)", "Needs attention (2)", "Usual (6)".
9. Reset: `docker compose down -v` deletes the `pgdata` volume; repeat from step 4.

Database login roles (local and CI): `database/roles/provision_login_roles.sql` runs as the PostgreSQL superuser right after the
server starts (Compose: `/docker-entrypoint-initdb.d`; CI: TRD 16). It first runs `CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS btree_gist;` and sets the current database's `timezone` to `UTC` (`ALTER DATABASE … SET timezone = 'UTC'`, TRD 20 PGS-001; extensions are created only by provisioning, never by Alembic; TRD 20 §4.2,
TRD 24 D-72), then idempotently creates the group roles `echowell_migrator`,
`echowell_app`, `echowell_readonly` (NOLOGIN), makes `echowell_migrator` owner of schema `public`, and creates the login roles
`echowell_migrator_login`, `echowell_app_login`, `echowell_readonly_login` (TRD 20 §4.3) with passwords read via psql `\getenv` from
`ECHOWELL_MIGRATOR_DB_PASSWORD`, `ECHOWELL_APP_DB_PASSWORD`, `ECHOWELL_READONLY_DB_PASSWORD` (local/CI only, TRD 21). Staging,
production and AWS create the login roles through the provider console with generated secrets; the script is never run there.
The backend then connects as `echowell_app_login` (DATABASE_URL), Alembic as `echowell_migrator_login` (DATABASE_MIGRATION_URL) and
`analytics_summary.py` as `echowell_readonly_login` (DATABASE_READONLY_URL).

The local Compose command runs uvicorn without `--proxy-headers`, so the client IP is the socket peer (TRD 05 API-103); the image default command and the Render start (Docker) command in `render.yaml` add `--proxy-headers --forwarded-allow-ips="*"` (TRD 15 DEP-022, DEP-040).

The `demo` profile (`docker compose --profile demo up -d --wait db backend frontend-prod`) adds the production-build frontend on `http://localhost:3001` for E2E tests and the demo fallback (DEP-017, DEP-090).

## Service accounts

TRD 22 TPS-005..TPS-007, TPS-021 and AC-TPS-01. One row per service in use; never passwords or tokens. Plan limits are indicative (October 2026) until verified on the provider's pricing page at account creation (TPS-007); the "Verified on" column and the actual limits are recorded in Phase 10 (FEAT-088).

| Service | Owner account | Administrators (≥ 2, MFA) | Plan | Region | Limits to verify | Verified on |
|---|---|---|---|---|---|---|
| GitHub organisation `EchoWellApp` | project-owned organisation, 2FA required for all members (TPS-040) | DevOps owner, algorithm lead | Free (public repository) | — | Actions minutes (free for public repositories) | recorded in Phase 10 |
| Netlify team "EchoWell" | project mailbox (TPS-005) | DevOps owner + 1 | Free (Starter) | global edge; SSR in Netlify's default US region | monthly build minutes / credits, bandwidth, 1 concurrent build | recorded in Phase 10 |
| Render workspace | project mailbox | DevOps owner + 1; the deploy account owning `RENDER_API_KEY` is a member of this workspace only | Hobby workspace; two Starter web services (about USD 7 per month each) and two cron jobs (per running second, minimum about USD 1 per month each); no autoscaling | `ohio` (US East) | instance prices, build minutes, outbound bandwidth; Render has no hard spending cap | recorded in Phase 10 |
| Neon organisation | project mailbox | DevOps owner + 1 | Free | `aws-us-east-1` | storage (about 0.5 GB), monthly compute hours, branch count, point-in-time restore window | recorded in Phase 10 |
| Sentry (optional, FEAT-084) | project mailbox | DevOps owner | Developer (free) | US data region | monthly error-event quota, about 30 days retention | recorded in Phase 10 if enabled |

Render runs only the two Starter web services and the two cron jobs above (no other paid service, no autoscaling); any instance-type change or added service needs approval under OQ-07. Render billing e-mail notifications go to the project mailbox (TPS-021).

Rules recorded for every third-party service (TPS-001..TPS-004): only the services of TRD 22 §4.1 are used (GitHub, Netlify, Render, Neon, Render Postgres as contingency, Google Fonts at build time, optional Sentry, and AWS as the target); no real resident data is stored on or sent through Netlify, Render, Neon or Sentry; go-live happens only on AWS; every service that stores EchoWell data is in the United States (Neon `aws-us-east-1`, Render `ohio`, AWS `us-east-1`; Netlify stores no data).

## Neon (database)

Procedure: TRD 15 §4.4 steps 1–7, executed in Phase 10 (checklist section B). Recorded here after execution, without connection strings:

| Item | Value |
|---|---|
| Project / PostgreSQL version / region | `echowell` / 16 / `aws-us-east-1` |
| Database branches | `main` (production), `staging` (child of `main`); temporary `pre-<short-sha>` and `restore-drill` branches are deleted within 7 days (TPS-031) |
| Roles | `echowell_migrator` (schema owner, DATABASE_MIGRATION_URL only), `echowell_app` (runtime), `echowell_readonly` (staging DATABASE_READONLY_URL; never set in production) |
| Connection strings | pooled (`-pooler`) for the app and readonly roles, direct for the migrator role, all with `sslmode=require`; stored only in Render variables and, for staging re-seeding, the GitHub secret `STAGING_DATABASE_URL` |
| Point-in-time restore window in force (DEP-095) | recorded in Phase 10 from the Neon plan |
| Compute autosuspend | plan default (5 min) on both branches; cold starts accepted (RSK-07) |

## Render (backend web services and nightly cron jobs)

Configuration as code: the Blueprint `render.yaml` (DEP-044) defines `echowell-api`, `echowell-nightly-staging`, `echowell-backend-production`, `echowell-nightly-production` and the environment groups `echowell-staging-shared` and `echowell-production-shared`; secrets are declared `sync: false` and entered only in the dashboard.

Dashboard-only settings (DEP-044), set and recorded in Phase 10:

| Setting | Where | Value |
|---|---|---|
| Project and environments | Render → Projects | project `echowell`, environments `staging` and `production`; each service assigned to its environment |
| Existing staging web service | `echowell-api` | kept, not recreated (D-154); moved from Free to Starter (D-157); its origin `https://echowell-api.onrender.com` is the staging API origin in the GitHub variables and the CSP |
| Secret values | each environment group / web service | DATABASE_URL, SENTRY_DSN (group); DATABASE_MIGRATION_URL, DATABASE_READONLY_URL (staging only), JWT_SECRET (web service) |
| Auto-deploy | staging services | "After CI checks pass"; production services: off |
| Notifications | Workspace → Notifications | e-mail on failed deploys and service failures to the DevOps owner |
| Outbound IP ranges | service → Connect → Outbound | recorded in Phase 10 (not used for allow-listing on Neon Free) |
| Custom domain | — | none (OQ-07); platform default domains only |
| Blueprint sync | Blueprint page | recorded in Phase 10 |
| Assigned production domain | `echowell-backend-production` | `echowell-backend-production.onrender.com`, or the name Render assigned (then also update the GitHub variable and the CSP) |

The cron jobs run `python -m backend.jobs.nightly_run` on `0 7,8 * * *` UTC and receive only the environment group's variables (never DATABASE_MIGRATION_URL, DATABASE_READONLY_URL, JWT_SECRET or CORS settings). `GIT_SHA` is never a Render variable: the Docker commands export it from `RENDER_GIT_COMMIT`.

## Netlify (frontend)

Both sites are built from `/netlify.toml` (base `frontend/`, command `node scripts/check-csp.mjs && npm run build`, Node 20, `@netlify/plugin-nextjs`, security headers of TRD 12 §4.9). `netlify.toml` has no deploy-context environment blocks: both sites build `main`, so the API origin is a per-site variable (TRD 15 §4.6).

| Site | Builds | Site variables (all deploy contexts) |
|---|---|---|
| `echowell-und-staging` | production branch `main`, auto publishing on; branch deploys off; deploy previews on for PRs; the ignore command skips builds without changes under `frontend/` or to `netlify.toml` | `NEXT_PUBLIC_API_BASE_URL=https://echowell-api.onrender.com`, `NEXT_PUBLIC_APP_ENV=staging` |
| `echowell-und` | **builds stopped**; branch deploys and deploy previews off; published only by `deploy-production.yml` (`netlify deploy --build --prod`); its site ID is the GitHub variable `NETLIFY_PRODUCTION_SITE_ID` | `NEXT_PUBLIC_API_BASE_URL=https://echowell-backend-production.onrender.com`, `NEXT_PUBLIC_APP_ENV=production` |

If a site name is taken, the actual name is recorded here and in the GitHub variables. Netlify variables hold only `NEXT_PUBLIC_*`, `NODE_VERSION` and `NEXT_TELEMETRY_DISABLED` (TPS-011); deploy previews never get the production backend URL (DEP-054).

## GitHub environments, secrets, variables and branch protection

| Name | Kind | Scope | Used by |
|---|---|---|---|
| `STAGING_DATABASE_URL` | secret | environment `staging` (branch rule `main`) | `deploy-staging.yml` re-seed (Neon `staging` direct URL, migrator role) |
| `STAGING_SEED_ADMIN_PASSWORD`, `STAGING_SEED_CLINICIAN_PASSWORD`, `STAGING_SEED_RESEARCHER_PASSWORD`, `STAGING_SEED_INGEST_API_KEY` | secrets | environment `staging` | `deploy-staging.yml` re-seed; the researcher password also logs the smoke tests in |
| `RENDER_API_KEY`, `NETLIFY_AUTH_TOKEN` | secrets | environment `production` (branch rule `main`, required reviewer from `team2-devops` or the algorithm lead, self-review prevented) | `deploy-production.yml` job `deploy` only |
| `RENDER_PRODUCTION_BACKEND_SERVICE_ID`, `RENDER_PRODUCTION_NIGHTLY_SERVICE_ID`, `NETLIFY_PRODUCTION_SITE_ID` | variables | environment `production` | `deploy-production.yml` job `deploy` |
| `STAGING_API_BASE_URL`, `STAGING_FRONTEND_URL`, `PRODUCTION_API_BASE_URL`, `PRODUCTION_FRONTEND_URL` | variables | repository | deploy workflows, `uptime.yml`; the API variables include `/api/v1` |

Branch protection on `main` requires exactly the eight checks of CIC-070: `repo-hygiene`, `backend-lint`, `backend-test`, `openapi-contract`, `frontend`, `security-audit`, `docker-build`, `playwright`, with "Require branches to be up to date before merging" (CIC-071).

## Configuration deviations from the TRD 21 §4.7 matrix

ENV-050: each environment is configured exactly per the matrix; any deviation is recorded here with its reason.

| Variable | Environment | Deviation | Reason |
|---|---|---|---|
| SENTRY_DSN | local, test | a non-empty value is ignored with a WARNING `sentry_dsn_ignored` (the matrix says empty) | defensive: Sentry is enabled only in staging and production (LOG-102); the matrix value itself is unchanged |

No other deviation is recorded at checkpoint 8. Phase 10 adds a row for any value that differs when the platforms are configured (for example a Render- or Netlify-assigned name).

## Staging deploy (automatic on every merge to `main`)

TRD 15 §4.9, reproduced verbatim:

1. Open a PR from a short-lived `feat/...`, `fix/...`, `docs/...` or `chore/...` branch directly to `main` (TRD 18 GIT-012); CI (TRD 16) must be green and the PR approved; Netlify posts a deploy preview of the staging site pointing to the staging backend.
2. Merge the PR into `main`.
3. Render `staging` waits until the commit's GitHub checks pass ("After CI checks pass"), builds `backend/Dockerfile` for the web service and the cron job, runs the pre-deploy command `alembic upgrade head`, starts uvicorn and switches traffic once the health check passes.
4. Netlify builds and publishes the staging site `echowell-und-staging` from `main`.
5. GitHub Actions `deploy-staging.yml` (TRD 16 §4.4, triggered by the push to `main`) waits until `GET /api/v1/health` reports `version` = merged SHA, re-seeds the staging database if DEP-074 applies, and runs the staging smoke tests (DEP-080).
6. The algorithm lead reviews the staging dashboard (Resident list filters 10 / 2 / 2 / 6, R09 chart with the alarm) before that commit is chosen for a production release.

Production is not touched by any of these steps.

`deploy-staging.yml` in detail: job `wait-for-staging` decides whether to re-seed (push touching `backend/alembic/` or `analytics/`, or dispatch with `reseed: true`) and polls the staging health `version` and the `echowell-build` meta of `/login` every 15 s for up to 15 minutes (accepting the previous frontend build when the commit changed nothing under `frontend/` or `netlify.toml`); job `reseed-and-smoke` runs in the GitHub environment `staging`, re-seeds with `python -m backend.cli seed test_v0_1 --reset` and the DS-10 loader when needed, runs `pytest tests/smoke -m smoke` and uploads `smoke-report`. To re-seed staging by hand: Actions → Deploy staging → Run workflow on `main` with `reseed` ticked.

## Production release (manual, deliberate)

TRD 15 §4.10, reproduced verbatim:

1. Choose a `main` commit whose required checks passed and whose `deploy-staging.yml` run succeeded (step 4.9.5), and the version `vX.Y.Z` (TRD 18 §4.7).
2. If the release contains a migration, create Neon restore database branch `pre-<short-sha>` from `main` (DEP-063) and take the DEP-096 dump.
3. Run the GitHub Actions workflow `deploy-production.yml` manually (`workflow_dispatch`, inputs `sha` and `version`; TRD 16 §4.5). The workflow first verifies, before any approval is asked for, that the commit is on `main`, its required checks passed and its staging deploy succeeded (job `verify`, "Wait for CI" semantics, TRD 16 CIC-053; TRD 24 D-165); if a check fails the run stops and no reviewer is asked. Only the following `deploy` job uses the GitHub environment `production`, so it then waits until a required reviewer approves.
4. After approval the workflow triggers a Render deploy of that commit for the production web service and cron job through the Render API (`commitId` = SHA; pre-deploy `alembic upgrade head`, health check; `GIT_SHA` comes from `RENDER_GIT_COMMIT`) and waits until both deploys are `live`; publishes the Netlify production site with `netlify deploy --build --prod` from the same commit; waits for `version` = released SHA; runs the production smoke tests (DEP-081); then creates the Git tag `vX.Y.Z` and a GitHub Release.
5. If smoke tests fail, follow the rollback procedure (4.12) within 30 minutes; no tag is created.

`deploy-production.yml` jobs: `verify` (full 40-character SHA on `main`, version format, tag not yet present, the eight CIC-070 checks `success` on that SHA, a successful `deploy-staging.yml` run for it) → `deploy` (environment `production`, waits for the reviewer; Render API deploys of both production services polled every 15 s until `live`, then the Netlify CLI publish with `GIT_SHA` set to the SHA) → `wait-for-production` (health `version` and build meta = SHA, 15 minutes) → `smoke` (`pytest tests/smoke -m "smoke and not authenticated"`, `smoke-report`) → `release` (`gh release create vX.Y.Z --generate-notes --target <sha>`, the only job with `contents: write`). Dispatch with `smoke_only: true` re-runs the production smoke tests for the deployed SHA without deploying or tagging. Prefer a window outside 08:00–20:00 facility-local time while OQ-15 is open.

First production deploy only (checklist G.06–G.08): in the Render Shell of `echowell-backend-production`, run `python -m backend.cli bootstrap`, then create the first admin with `python -m backend.cli create-user --email <admin email> --display-name <name> --role admin` (password typed interactively, never written down; DEP-075), and register only `T`-prefixed demo residents and test devices.

## Smoke tests

`tests/smoke/` (marker `smoke`; tests that log in also carry `authenticated`), configured only by environment variables (TRD 21 §4.5):

| Variable | staging run | production run |
|---|---|---|
| SMOKE_ENV | `staging` | `production` |
| SMOKE_API_BASE_URL | `${{ vars.STAGING_API_BASE_URL }}` | `${{ vars.PRODUCTION_API_BASE_URL }}` |
| SMOKE_FRONTEND_URL | `${{ vars.STAGING_FRONTEND_URL }}` | `${{ vars.PRODUCTION_FRONTEND_URL }}` |
| SMOKE_EXPECTED_SHA | pushed SHA | released SHA |
| SMOKE_USER_EMAIL / SMOKE_USER_PASSWORD | `researcher@example.com` / `STAGING_SEED_RESEARCHER_PASSWORD` | never set |

| File | Checks |
|---|---|
| `test_staging_smoke.py` | DEP-080 (a) health and version, (b) `/login`, (c) researcher login, (d) summary 2 / 2 / 0 / 6, (e) R09 `alarm_on` since 2026-10-21, (f) open alarms R09 and R10 and exactly the four data alerts, (g) 281 of 300 received and 267 of 300 used, (h) CORS preflight allowed for the staging origin and refused for `https://example.org`, (i) HSTS and http→https redirect on API and frontend |
| `test_production_smoke.py` | DEP-081 (a) health and version, (b) `/login` over HTTPS, (c) `/residents` 401 with an RFC 7807 body, (d) `POST /sessions` 401 without key, (e) HSTS and redirect on both origins, (f) `/audio` 404; unauthenticated and read-only |
| `test_tls.py` | DEP-080 (j) / DEP-081 (g), SEC-066: TLS 1.1 refused and TLS 1.2 accepted on both origins |

`tests/smoke/wait_for_deploy.py` is the polling helper used by both deploy workflows. Without `SMOKE_API_BASE_URL` every smoke test is skipped, so `pytest -q` stays offline. Against `http://` targets the HSTS, redirect and TLS checks are skipped with reason SEC-065.

Run locally against the seeded local backend (staging-equivalent, TRD 15 §4.11; the expected SHA is optional):

```sh
SMOKE_ENV=staging SMOKE_API_BASE_URL=http://localhost:8000/api/v1 SMOKE_FRONTEND_URL=http://localhost:3000 \
SMOKE_EXPECTED_SHA="$(git rev-parse HEAD)" SMOKE_USER_EMAIL=researcher@example.com \
SMOKE_USER_PASSWORD="<local SEED_RESEARCHER_PASSWORD>" pytest tests/smoke -m smoke
```

## Manual authenticated check (DEP-083)

After every production release a team member logs in on the production site, opens Residents, opens one resident and signs out, then edits the GitHub Release `vX.Y.Z` and replaces the "pending" line of the release notes with the result, the date and the role used (no names, no credentials).

## Rollback

TRD 15 §4.12:

| Failure | Action | Time target |
|---|---|---|
| Frontend broken, backend fine | Netlify → Deploys → select last good deploy → "Publish deploy". Then revert the commit on `main` by PR. | 5 min |
| Backend fails health check or pre-deploy | Nothing to do immediately; Render keeps the previous deploy serving and reports the failed deploy (notification e-mail). Fix forward by PR. | 0 min |
| Backend healthy but functionally broken, no migration | Render dashboard → web service → Events → last good deploy → "Rollback" (re-runs that deploy's image without a rebuild; current environment variables apply), and the same for the cron job. Render then turns auto-deploy off on the rolled-back service: re-enable it in `staging` after the revert is merged. Revert the commit on `main` by PR; for production, run `deploy-production.yml` for the fixed commit. | 10 min |
| Backend broken after an additive migration | Roll back as above (schema is backward compatible, DEP-061). A rollback does not re-run the pre-deploy command or any other operational command (migrations, seeding, bootstrap); run them by hand if needed (confirmed by the algorithm lead, TRD 24 D-158). If the older image cannot work with the newer database revision, revert on `main` by PR and deploy forward instead. Do not run `alembic downgrade` in production. | 10 min |
| Data damaged by a migration or bug | Stop ingestion (deactivate API keys with `python -m backend.cli revoke-api-key --name N`, §4.8), restore Neon `main` from `pre-<short-sha>` branch or PITR timestamp (4.13), redeploy the matching backend, re-run `run-pipeline --scope all`, then issue new device keys with `python -m backend.cli create-api-key` (revoked keys stay revoked; there is no re-activate command) and give them to Team 1. Record incident in GitHub issue labelled `incident`. | 60 min |

Rollback rehearsal (DEP-085, AC-DEP-07): once before 15 Nov 2026; record date, duration and result here in Phase 10.

## Backups and restore

- Neon point-in-time restore on `main` for the window of the plan in force (recorded under "Neon"), under the interim waiver of NFR-024 (DEP-095, D-60).
- Weekly (Mondays) and before every release with a migration: `pg_dump --format=custom --no-owner` of production by the data steward from a UND-managed workstation, encrypted at rest, stored only on the storage designated by the PI (DEP-096, OQ-01). Dumps are never committed or uploaded as Actions artifacts (DEP-098).
- PITR restore: Neon console → project `echowell` → branch `main` → "Restore" → timestamp (UTC) → verify with `SELECT max(received_at) FROM raw_sessions` → redeploy the matching backend → `python -m backend.cli run-pipeline --scope all` (DEP-087).
- Restore drill (DEP-097): once before 15 Nov 2026 into Neon branch `restore-drill`; record the result (row counts of `raw_sessions`, `audit_logs`, `alerts`, schema diff, `pytest tests/validation -q`) here in Phase 10.

## Demo fallback (RSK-12)

If production does not pass DEP-081 by 5 Nov 2026, the demo runs on a team laptop with the commit on `main`:

1. `cp .env.development.example .env`; `docker compose --profile demo up -d --wait db backend frontend-prod`.
2. `docker compose exec backend python -m backend.cli seed test_v0_1` and the DS-10 loader (step 6 of the local procedure).
3. Dashboard at `http://localhost:3001`. For device posts, bind the backend port to the laptop's LAN address for the duration of the demo only and give Team 1 `http://<laptop LAN IP>:8000/api/v1/sessions` with a test API key from `python -m backend.cli create-api-key --name <name> --device <device>`.
4. Post one record (device or `curl`), reload `/residents`, confirm it appears after processing; rebind the port to 127.0.0.1 afterwards.

Rehearsal (DEP-092, AC-DEP-09): once before 15 Nov 2026; record date and result here in Phase 10.

## Monitoring and alerts

| Signal | Source | Who looks | Frequency |
|---|---|---|---|
| Uptime | `uptime.yml` every 30 min: production and staging `/api/v1/health`, production `/login`; one retry after 60 s; two failures open or update the issue "Uptime check failing" labelled `incident` | `incident` watchers | continuous |
| Deploy failures | Render notification e-mail; Netlify deploy view; failing `deploy-*.yml` run | DevOps owner | per deploy |
| Application logs | Render Logs tab (search `"level": "ERROR"`, `pipeline_run_failed`, `nightly_run_missing`) | DevOps owner | daily |
| Exceptions (optional) | Sentry project `echowell-backend` | DevOps owner | e-mail per new issue |
| Pipeline health | `/admin` pipeline runs and the missing-nightly banner | admin | daily |

**Incident watchers (LOG-114, FEAT-085-FR-06).** The DevOps owner and the algorithm lead watch the repository's issues with label `incident` (GitHub → Watch → Custom → Issues, plus a saved filter `label:incident`), so every uptime incident reaches at least two team members. Both roles are confirmed in Phase 10 and listed in the weekly team status. The `incident` label is created by `uptime.yml` on its first failure if it does not exist yet.

**Uptime report (NFR-020).** Production availability of `GET /api/v1/health` during 16 Nov – 8 Dec 2026 is computed from the `uptime.yml` run history (Actions → Uptime, filter by date): availability = 1 − (number of 30-minute checks whose production API check failed twice ÷ number of checks run), target ≥ 99.0 %. Runs where the variable was not configured are excluded and stated. The figure goes into the readiness evidence (MVP checklist) with the run-history link.

## Usage monitoring

Weekly, the DevOps owner reads the usage pages and records the figures in the weekly team status (DEP-101, TRD 17 §4.8):

| Platform | Figure | Where |
|---|---|---|
| Netlify | build minutes used this month (both sites) | Team → Usage |
| Render | month-to-date charges of the workspace (two Starter web services, two cron jobs; no hard spending cap) | Workspace → Billing |
| Neon | compute hours used this month and storage per branch | Project → Usage |

Fallback order when a limit approaches (DEP-102, FEAT-085-FR-08): if Neon Free compute hours would be exhausted before month end, **first** relax the uptime interval (edit the `uptime.yml` schedule to a longer interval, never shorter than 30 minutes), **second** suspend staging compute (Neon `staging` branch compute and, if needed, the Render staging services), and only then consider any production setting. Any Render instance-type change or new service needs approval under OQ-07.

## Error monitoring with Sentry (optional, FEAT-084)

- Backend only (`backend/core/monitoring.py`); no browser SDK (TPS-060, LOG-082). Initialised by the web application's startup and the nightly job only when `SENTRY_DSN` is set and APP_ENV is `staging` or `production`; with an empty DSN the SDK is not even imported (LOG-101).
- Events: every ERROR log record (`unhandled_exception`, `nightly_run_missing`, `pipeline_run_failed`), after the log redaction is applied again and request headers, cookies, query strings and bodies are dropped; `send_default_pii=False`, no tracing (LOG-100).
- Project `echowell-backend` in the Sentry organisation owned by the project mailbox; alert rule "e-mail per new issue" to the DevOps owner.
- `SENTRY_DSN` is a secret (`SecretStr`), set only in the Render environment groups; values per TRD 21 §4.7: **local empty, test empty**, staging optional, interim production optional (synthetic data only).
- **Go-live rule (TPS-061, LOG-102): before AWS go-live, `SENTRY_DSN` is empty in production unless the project coordinator and UND IT approve Sentry for PHI-derived data under an appropriate agreement; CloudWatch is the default on AWS.** The decision is recorded in checklist row N.11.
- Decision for the interim stack: recorded in Phase 10 (checklist C.12).

## Incident containment, reporting and investigation

Containment actions, executable within 1 hour by the on-duty Team 2 DevOps lead (SEC-170):

| # | Action | How |
|---|---|---|
| 1 | Revoke API keys | Render Shell of the affected web service: `python -m backend.cli revoke-api-key --name <key name>` (audited; revoked keys stay revoked) |
| 2 | Deactivate users | As an admin: `PATCH /api/v1/users/{id}` with body `{"active": false}` (TRD 19 E-27), or the Admin page |
| 3 | Rotate JWT_SECRET | Generate `openssl rand -base64 48`, replace JWT_SECRET on the Render web service, redeploy; every issued token becomes invalid and users sign in again (SEC-035, ENV-052) |
| 4 | Rotate database role passwords | Neon console → Roles → reset the password of `echowell_app`, `echowell_migrator`, `echowell_readonly` login roles; update DATABASE_URL, DATABASE_MIGRATION_URL, DATABASE_READONLY_URL in Render (and `STAGING_DATABASE_URL` for staging); redeploy |
| 5 | Suspend the service | Render dashboard → web service → Settings → Suspend, and the same for the cron job (on AWS: scale App Runner to zero) |

Reporting (SEC-171): a suspected security incident is reported to the PI and the Team 2 lead within 24 hours of discovery; the PI decides on reporting to UND IT security and the IRB under UND policy.

Investigation (SEC-172): correlate `audit_logs` (actor, action, `request_id`, ip) with the application logs by `request_id` (every log record and every error response carries it).

Post-incident note (SEC-173): timeline, cause, data affected and corrective actions, kept in the team's private project space, **not** in this public repository; the public `incident` issue holds only URLs, status codes and timestamps.

## Research-data governance

- EchoWell data is research data of the UND Speech Study, owned by the faculty PI and governed by the IRB-approved protocol; Team 2 acts as system operator only (SEC-180).
- No retention-based deletion job runs in the MVP; retention periods and storage locations are decided under OQ-01 (SEC-181).
- Data exports outside EchoWell are made only via the `echowell_readonly` role by personnel listed on the IRB protocol, and only from the approved AWS platform once live data exists (SEC-182).
- Public development datasets (DAIC-WOZ, E-DAIC) are used only under their licence terms, only for development and pipeline validation, and never loaded into an environment that also holds live study data (SEC-183).
- Third-party-licensed documents are referenced by link, never committed (SEC-184).

## AWS target (go-live)

TRD 15 §4.16 and checklist section N: Amplify, App Runner (same `backend/Dockerfile` image), RDS PostgreSQL 16 with KMS, Secrets Manager, CloudWatch, EventBridge Scheduler, under the AWS BAA, after OQ-07. Go-live requires the signed item "hosting approved for PHI-derived data (AWS)" by the PI and UND IT (SEC-005) before any live device is pointed at the API.
