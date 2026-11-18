# Render backend and nightly cron services, Neon database configuration

## Feature Description

FEAT-081 defines the interim backend hosting as code and runbook (retargeted from Railway to Render, TRD 24 D-153; TRD 15 DEP-030..DEP-048, DEP-060..DEP-065, §4.4, §4.5; TRD 22 TPS-020, TPS-021, TPS-030..TPS-032; TRD 12 SEC-061, SEC-111, SEC-116). The Blueprint `render.yaml` defines four services and two environment groups: per environment a web service (staging `echowell-api`, D-154; production `echowell-backend-production`) built from `backend/Dockerfile` with pre-deploy command `alembic upgrade head`, a uvicorn Docker command that exports `GIT_SHA` from `RENDER_GIT_COMMIT`, health check `/api/v1/health`, one Starter instance, auto-deploy "After CI checks pass" (`checksPass`) in staging and off in production; a cron job `echowell-nightly-<env>` running `python -m backend.jobs.nightly_run` on `0 7,8 * * *` UTC with only its environment group's variables; and the groups `echowell-staging-shared` and `echowell-production-shared`. Secrets are `sync: false`. `docs/deployment.md` holds the Neon procedure (project `echowell`, PostgreSQL 16, `aws-us-east-1`, branches `main` and `staging`, owner-role extensions and timezone, pooled endpoint for the app role, direct for the migrator, `sslmode=require`) and the dashboard-only settings. The interim deployment is live (TRD 24 D-180); hosted checks here are read-only and never change the Render, Netlify or Neon deployments (D-170).

## Preconditions

- Repository clone; Python 3.12 with `pip install -r backend/requirements.txt -r backend/requirements-dev.txt`; Docker for the local migration check.
- For the cases marked **Hosted**: the team's `<API_BASE_URL>` (backend origin plus `/api/v1`) for staging and production, and read-only (viewer) access to the Render workspace and the Neon project. No URL, password or connection string is written into the test record.
- No deploy, re-seed, migration, branch creation or setting change is performed on any hosted service while running these cases.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-081-01 | Web services: pre-deploy migration, Docker command without `alembic`, health path, one paid instance | High | Positive |
| TC-081-02 | Cron jobs: nightly command, `0 7,8 * * *`, no pre-deploy, only `fromGroup`, no `alembic` | High | Positive |
| TC-081-03 | Import-boundary test for DATABASE_MIGRATION_URL passes and catches application code | High | Security |
| TC-081-04 | `docs/deployment.md` lists every dashboard-only setting and the cron variable allow-list, no secret | High | Documentation |
| TC-081-05 | Neon runbook: `aws-us-east-1`, PostgreSQL 16, branches `main`/`staging`, owner-role SQL, `sslmode=require` | High | Documentation |
| TC-081-06 | `render.yaml` has no `neon.tech` and every secret key is `sync: false` | High | Security |
| TC-081-07 | DATABASE_MIGRATION_URL and DATABASE_READONLY_URL only on the right web service | High | Security |
| TC-081-08 | Auto-deploy: staging `checksPass`, production `"off"` | Medium | Positive |
| TC-081-09 | Nightly job refuses to run on a schema revision mismatch | Medium | Negative |
| TC-081-10 | Failing `alembic upgrade head` exits non-zero (previous deploy stays live) | Medium | Negative |
| TC-081-11 | Hosted: health check and HSTS on staging and production backends | High | Hosted |
| TC-081-12 | Hosted: Render dashboard matches the Blueprint (read-only inspection) | Medium | Hosted |
| TC-081-13 | Hosted: nightly cron runs visible and single run per night | Medium | Hosted |
| TC-081-14 | No Render- or Neon-specific API or SDK in application code | Medium | Negative |
| TC-081-15 | Render Postgres fallback procedure documented | Low | Documentation |

### TC-081-01 Web services: pre-deploy migration, Docker command without `alembic`, health path, one paid instance

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest -q tests/unit/test_render_blueprint.py -k "web_service or four_services or field_by_field"` | All pass (staging and production). |
| 2 | `python -c "import yaml;[print(s['name'],s['plan'],s.get('numInstances'),s['preDeployCommand'],s['healthCheckPath']) for s in yaml.safe_load(open('render.yaml'))['services'] if s['type']=='web']"` | `echowell-api starter 1 alembic upgrade head /api/v1/health` and `echowell-backend-production starter 1 alembic upgrade head /api/v1/health`. |
| 3 | `grep -n "dockerCommand" render.yaml` | Web services: `sh -c 'export GIT_SHA="${RENDER_GIT_COMMIT:-unknown}"; exec uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips="*"'`; no `alembic` in any `dockerCommand`. |
| 4 | `grep -n "plan:" render.yaml` | Every service `plan: starter`; no `free`. |

### TC-081-02 Cron jobs: nightly command, `0 7,8 * * *`, no pre-deploy, only `fromGroup`, no `alembic`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest -q tests/unit/test_render_blueprint.py -k cron_job` | Pass for staging and production. |
| 2 | Read the two `type: cron` entries of `render.yaml`. | Names `echowell-nightly-staging`, `echowell-nightly-production`; `schedule: "0 7,8 * * *"`; `dockerCommand: sh -c 'export GIT_SHA="${RENDER_GIT_COMMIT:-unknown}"; exec python -m backend.jobs.nightly_run'`; no `preDeployCommand`, no `healthCheckPath`; `envVars` is only `- fromGroup: echowell-<env>-shared`. |
| 3 | Read the two `envVarGroups`. | Keys limited to APP_ENV, PIPELINE_PROFILE, PIPELINE_AS_OF (staging only), FACILITY_NAME, FACILITY_TZ, NIGHTLY_RUN_HOUR_LOCAL, LOG_LEVEL, LOG_FORMAT, DATABASE_URL (`sync: false`), SENTRY_DSN (`sync: false`). |

### TC-081-03 Import-boundary test for DATABASE_MIGRATION_URL passes and catches application code

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest -q tests/unit/test_render_blueprint.py -k "closed_list or boundary_check"` | `test_only_the_closed_list_reads_database_migration_url` and `test_boundary_check_catches_application_code[api|services|jobs]` pass. |
| 2 | Locally create `backend/services/qa_leak.py` with `import os` and `URL = os.environ["DATABASE_MIGRATION_URL"]`; rerun step 1. | `test_only_the_closed_list_reads_database_migration_url` fails. |
| 3 | Delete `backend/services/qa_leak.py`; rerun. | Pass. |

### TC-081-04 `docs/deployment.md` lists every dashboard-only setting and the cron variable allow-list, no secret

| Step | Action | Expected Result |
|---|---|---|
| 1 | Read "## Render (backend web services and nightly cron jobs)" in `docs/deployment.md`. | Table of dashboard-only settings: project and environments, existing staging web service, secret values (names only), auto-deploy, notifications, outbound IP ranges, custom domain (none), Blueprint sync, assigned production domain. |
| 2 | Read the paragraph after the table. | Cron jobs run `python -m backend.jobs.nightly_run` on `0 7,8 * * *` UTC and receive only the group variables, never DATABASE_MIGRATION_URL, DATABASE_READONLY_URL, JWT_SECRET or CORS settings; `GIT_SHA` exported from `RENDER_GIT_COMMIT`. |
| 3 | `docker run --rm -v "$PWD:/repo" ghcr.io/gitleaks/gitleaks:v8.18.4 detect --no-git --source /repo/docs/deployment.md --redact --no-banner` | "no leaks found". |
| 4 | `pytest -q tests/integration/pipeline/test_nightly_run.py -k across_dst -p no:randomly` (TST-052, named as the AC's verification) | `test_one_run_per_local_night_across_dst` passes. |

### TC-081-05 Neon runbook: `aws-us-east-1`, PostgreSQL 16, branches `main`/`staging`, owner-role SQL, `sslmode=require`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Read "## Neon (database)" in `docs/deployment.md`. | Project `echowell`, PostgreSQL 16, region `aws-us-east-1`; branches `main` (production) and `staging`; temporary `pre-<short-sha>` and `restore-drill` branches deleted within 7 days. |
| 2 | Find the owner-role SQL (lines 47–48 and §4.4 reference). | `CREATE EXTENSION IF NOT EXISTS pgcrypto;`, `CREATE EXTENSION IF NOT EXISTS btree_gist;` and `ALTER DATABASE … SET timezone = 'UTC'`, run by the owner role before any migration; migrations never create extensions. |
| 3 | Read the connection-string row. | Pooled endpoint for app and readonly roles, direct for the migrator, all with `sslmode=require`; stored only in Render and the GitHub secret `STAGING_DATABASE_URL`. |
| 4 | Read "## Production release". | Step 2: create Neon branch `pre-<short-sha>` from `main` when the release contains a migration (DEP-063). |

### TC-081-06 `render.yaml` has no `neon.tech` and every secret key is `sync: false`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep "neon.tech" render.yaml` | No output. |
| 2 | `grep -nE "DATABASE_URL|DATABASE_MIGRATION_URL|DATABASE_READONLY_URL|JWT_SECRET|SENTRY_DSN" render.yaml` | Every match is `{ key: <NAME>, sync: false }`; none has a `value`. |
| 3 | `pytest -q tests/unit/test_render_blueprint.py -k "sync_false or no_hostnames"` | Pass. |

### TC-081-07 DATABASE_MIGRATION_URL and DATABASE_READONLY_URL only on the right web service

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest -q tests/unit/test_render_blueprint.py -k migration_and_readonly` | Pass. |
| 2 | Inspect `render.yaml`. | DATABASE_MIGRATION_URL on both web services only (not in a group, not on a cron job); DATABASE_READONLY_URL only on `echowell-api` (staging); absent from production. |

### TC-081-08 Auto-deploy: staging `checksPass`, production `"off"`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -n "autoDeployTrigger" render.yaml` | `echowell-api` and `echowell-nightly-staging`: `checksPass`; `echowell-backend-production` and `echowell-nightly-production`: `"off"`. |
| 2 | Read `.github/workflows/deploy-production.yml` triggers. | Production is deployed only by this workflow (manual, `production` environment). |

### TC-081-09 Nightly job refuses to run on a schema revision mismatch

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest -q tests/integration/pipeline/test_nightly_run.py -k schema_mismatch -p no:randomly` | `test_schema_mismatch_refuses` passes: exit code 1 and no `pipeline_runs` row when the database revision differs from the bundled one. |
| 2 | `grep -n "alembic" backend/jobs/nightly_run.py | grep -i upgrade` | No `alembic upgrade` call in the nightly job. |

### TC-081-10 Failing `alembic upgrade head` exits non-zero (previous deploy stays live)

| Step | Action | Expected Result |
|---|---|---|
| 1 | `docker build -f backend/Dockerfile -t echowell-backend:qa .` then `docker run --rm -e APP_ENV=local --env-file .env.development.example -e DATABASE_MIGRATION_URL=postgresql+psycopg://nobody:x@127.0.0.1:1/nodb echowell-backend:qa alembic upgrade head; echo "exit=$?"` | Connection error; `exit` non-zero (Render marks such a pre-deploy as failed and keeps the previous deploy live, DEP-065). |
| 2 | Hosted (read-only): Render → `echowell-api` → Events. | Any past "pre-deploy failed" event is followed by the previous deploy remaining live; no action taken. |

### TC-081-11 Hosted: health check and HSTS on staging and production backends

| Step | Action | Expected Result |
|---|---|---|
| 1 | `curl -s -D - <API_BASE_URL>/health` for staging. | HTTP 200; JSON `status` `ok`, `database` `ok`, `version` equal to the deployed commit SHA; header `strict-transport-security: max-age=31536000; includeSubDomains`. |
| 2 | Repeat for production `<API_BASE_URL>`. | Same result. |
| 3 | `curl -s -o /dev/null -w '%{http_code} %{redirect_url}\n' http://<backend host>/api/v1/health` | Redirect to `https://` (or connection refused); never a 200 over plain HTTP. |

### TC-081-12 Hosted: Render dashboard matches the Blueprint (read-only inspection)

| Step | Action | Expected Result |
|---|---|---|
| 1 | Render → project `echowell` → environments. | Environments `staging` and `production`; services `echowell-api`, `echowell-nightly-staging`, `echowell-backend-production`, `echowell-nightly-production`; groups `echowell-staging-shared`, `echowell-production-shared`. |
| 2 | Open each web service → Settings. | Instance type Starter; 1 instance; pre-deploy command `alembic upgrade head`; health check path `/api/v1/health`; region Ohio; auto-deploy "After CI checks pass" (staging) / off (production). |
| 3 | Open each cron job → Environment. | Only the linked group; no DATABASE_MIGRATION_URL, DATABASE_READONLY_URL or JWT_SECRET. |
| 4 | Workspace → Billing (read only). | Two Starter web services and two cron jobs; no autoscaling. |

### TC-081-13 Hosted: nightly cron runs visible and single run per night

| Step | Action | Expected Result |
|---|---|---|
| 1 | Render → `echowell-nightly-staging` → Logs for the last 3 days. | Two firings per day (07:00 and 08:00 UTC); one proceeds at facility-local 02:xx, the other exits without a second run (advisory lock / hour check). |
| 2 | As admin on the staging frontend, `/admin?tab=runs`. | One "Nightly" run per night with status "Succeeded"; no "Nightly run missing for <date>" banner. |

### TC-081-14 No Render- or Neon-specific API or SDK in application code

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -rniE "render\.com|onrender|neon\.tech|neondatabase|RENDER_" backend analytics --include=*.py` | No match (only `render.yaml` uses `RENDER_GIT_COMMIT`). |
| 2 | `grep -niE "render|neon" backend/requirements.txt` | No match. |

### TC-081-15 Render Postgres fallback procedure documented

| Step | Action | Expected Result |
|---|---|---|
| 1 | Search `docs/deployment.md` for the Render Postgres fallback. | Procedure states: D-72 provisioning as the database admin user (verified able to create `pgcrypto`, `btree_gist` and the roles), change of DATABASE_URL, DATABASE_MIGRATION_URL and DATABASE_READONLY_URL, and `pg_dump`/`pg_restore` restored as `echowell_migrator` with `--no-owner`. |

Note: `docs/deployment.md` names Render Postgres only as a contingency (line 75) and documents `pg_dump --format=custom --no-owner` for backups (line 221); no Render Postgres fallback procedure (DEP-035, TPS-030) was found, so this case is expected to fail until it is added.

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | Hosted `GET <API_BASE_URL>/health` (staging, production) | 200; `database` `ok`; HSTS header present |
| 2 | Local `GET http://localhost:8000/api/v1/health` with the image started by the Render-style command (`PORT` set) | 200 |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | Local: after `docker compose up`, `SELECT version_num FROM alembic_version;` | Equals the head revision bundled in the image (the value the nightly job compares, DEP-048) |
| 2 | Hosted (read-only, Neon console SQL editor on `staging` as a read-only role): `SHOW timezone;` and `SELECT extname FROM pg_extension;` | `UTC`; `pgcrypto`, `btree_gist` present |
| 3 | Integration test of TC-081-09 | No `pipeline_runs` row on a revision mismatch |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Application module reads DATABASE_MIGRATION_URL (TC-081-03) | Boundary test fails |
| 2 | Schema revision mismatch (TC-081-09) | Nightly job exits 1, writes no run |
| 3 | Unreachable migration database (TC-081-10) | `alembic upgrade head` exits non-zero |
| 4 | Plain HTTP to the backend (TC-081-11 step 3) | No 200 over HTTP |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-081-AC-01 | Each web service has `preDeployCommand: alembic upgrade head`, a `dockerCommand` without `alembic`, `healthCheckPath: /api/v1/health`, `numInstances: 1`, a paid plan | TC-081-01, TC-081-12 |
| FEAT-081-AC-02 | Each cron job runs `python -m backend.jobs.nightly_run`, `schedule: "0 7,8 * * *"`, no `preDeployCommand`, only `fromGroup`, no `alembic` | TC-081-02 |
| FEAT-081-AC-03 | Import-boundary test passes and fails when `backend/api/`, `backend/services/` or `backend/jobs/` references DATABASE_MIGRATION_URL | TC-081-03 |
| FEAT-081-AC-04 | `docs/deployment.md` lists every DEP-044 dashboard-only setting and the cron allow-list, no secret | TC-081-04 |
| FEAT-081-AC-05 | Neon runbook names `aws-us-east-1`, PostgreSQL 16, branches `main` and `staging`, owner-role extension and timezone SQL, `sslmode=require` | TC-081-05 |
| FEAT-081-AC-06 | `grep "neon.tech" render.yaml` returns nothing; every secret key is `sync: false` | TC-081-06 |

## Test Data Requirements

- No resident data; local checks use `.env.development.example` values and a throwaway image tag `echowell-backend:qa`.
- Hosted placeholders: `<API_BASE_URL>` (staging, production), `<backend host>`; viewer access to Render and Neon held by the team.
- Variable names only: DATABASE_URL, DATABASE_MIGRATION_URL, DATABASE_READONLY_URL, JWT_SECRET, SENTRY_DSN, RENDER_GIT_COMMIT, STAGING_DATABASE_URL.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-081-FR-01 / DEP-040, D-58 | FEAT-081 | TC-081-01 |
| FEAT-081-FR-02 / DEP-040, SEC-111, RSK-15 | FEAT-081 | TC-081-03, TC-081-07 |
| FEAT-081-FR-03 / DEP-041, LOG-071 | FEAT-081 | TC-081-01, TC-081-11 |
| FEAT-081-FR-04 / DEP-042 | FEAT-081 | TC-081-01, TC-081-12 |
| FEAT-081-FR-05 / DEP-043, DEP-003 | FEAT-081 | TC-081-08 |
| FEAT-081-FR-06 / DEP-044 | FEAT-081 | TC-081-04, TC-081-06 |
| FEAT-081-FR-07 / DEP-045, SEC-062 | FEAT-081 | TC-081-11 |
| FEAT-081-FR-08 / DEP-046, LOG-110, D-47, SEC-111 | FEAT-081 | TC-081-02, TC-081-13 |
| FEAT-081-FR-09 / DEP-048 | FEAT-081 | TC-081-09 |
| FEAT-081-FR-10 / DEP-030, DEP-031, DEP-005, TPS-031 | FEAT-081 | TC-081-05 |
| FEAT-081-FR-11 / TRD 15 §4.4 step 4, D-72 | FEAT-081 | TC-081-05 |
| FEAT-081-FR-12 / DEP-032, SEC-116 | FEAT-081 | TC-081-05, TC-081-07 |
| FEAT-081-FR-13 / DEP-033, DEP-034, SEC-061, DB-053 | FEAT-081 | TC-081-05, TC-081-06 |
| FEAT-081-FR-14 / DEP-060..DEP-062, DEP-064, DEP-065 | FEAT-081 | TC-081-10 |
| FEAT-081-FR-15 / DEP-063 | FEAT-081 | TC-081-05 |
| FEAT-081-FR-16 / TPS-020, TPS-032, DEP-110 | FEAT-081 | TC-081-14 |
| FEAT-081-FR-17 / TPS-021 | FEAT-081 | TC-081-12 |
| FEAT-081-FR-18 / DEP-035, TPS-030 | FEAT-081 | TC-081-15 |
