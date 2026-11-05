# FEAT-081 Render backend and nightly cron services, Neon database configuration

> Retargeted from Railway to Render on 4 Nov 2026 (TRD 24 D-153, checkpoint 7 review of GitHub PR #28, Q-13). Requirement IDs are unchanged; the deliverable `railway.toml` / `railway.nightly.toml` is replaced by the Blueprint `render.yaml`.

| Field | Value |
|---|---|
| Epic | DevOps & Deployment |
| Build phase | Phase 9 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-077, FEAT-054 |
| Status | Not Started |

## Purpose

Write the backend hosting configuration for the interim stack as code and as a runbook, without deploying: the Render Blueprint `render.yaml` with, per environment, the web service `echowell-backend-<env>` (Docker runtime from `backend/Dockerfile`, pre-deploy command `alembic upgrade head`, uvicorn Docker command that exports `GIT_SHA` from `RENDER_GIT_COMMIT`, health check `/api/v1/health`, one Starter instance, auto-deploy from `main` "After CI checks pass" in staging and off in production), the separate cron job `echowell-nightly-<env>` (`0 7,8 * * *` UTC, `python -m backend.jobs.nightly_run`) and the environment group `echowell-<env>-shared`, and the Neon setup procedure (project `echowell` in `aws-us-east-1`, database branches `main` and `staging`, extensions and timezone set by the owner role, pooled endpoint for the app role, direct endpoint for the migrator). Phase 10 (FEAT-088) executes these procedures.

## Business Context

- BR-17 and SRC-01: FastAPI with the analytics engine on Render (D-153), PostgreSQL 16 on Neon (DEP-003, DEP-005, VIS-016).
- BR-16: least-privilege database roles, TLS to the database, migrator credential kept off the cron service (DEP-032, DEP-034, SEC-111).
- BR-06, BR-11: the nightly run extends the day ledger and keeps alarms current even without new records (DEP-046, DEP-047).

## Referenced TRDs

- TRD 15 DEP-001, DEP-003, DEP-004, DEP-005, DEP-030..DEP-035, DEP-040..DEP-048, DEP-060..DEP-065, §4.4 Neon procedure, §4.5 Render procedure and `render.yaml` outline, §4.12 rollback, §8 Implementation Notes.
- TRD 22 TPS-020, TPS-021, TPS-030, TPS-031, TPS-032, TPS-004, TPS-005, TPS-006, TPS-007.
- TRD 17 LOG-110, LOG-111, LOG-071.
- TRD 12 SEC-007, SEC-061, SEC-111, SEC-116.
- TRD 21 ENV-050, ENV-053, §4.7 matrix.
- TRD 06 DB-021 (nightly advisory lock), DB-053.
- TRD 24 D-47, D-54, D-58, D-62, D-72, D-153, RSK-15.
- TRD 25 §4.6 Phase 9 (no deployment performed), AGT-014, AGT-059.

## Scope

- `/render.yaml` exactly per the TRD 15 §4.5 outline, for both environments: environment groups `echowell-staging-shared` and `echowell-production-shared` (the variables shared by web service and cron job; secrets `sync: false`); web services `echowell-api` and `echowell-backend-production` with `runtime: docker`, `dockerfilePath: ./backend/Dockerfile`, `dockerContext: .`, `branch: main`, `region: ohio` (`ohio` (the region of `echowell-api`), D-156), `plan: starter`, `numInstances: 1`, `preDeployCommand: alembic upgrade head`, `dockerCommand: sh -c 'export GIT_SHA="${RENDER_GIT_COMMIT:-unknown}"; exec uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips="*"'`, `healthCheckPath: /api/v1/health`, `buildFilter.paths: ["backend/**", "analytics/**", "database/**", "alembic.ini"]`, `autoDeployTrigger: checksPass` (staging) / `off` (production), and the web-only variables.
- Cron jobs `echowell-nightly-staging` and `echowell-nightly-production` in the same `render.yaml`: `type: cron`, `runtime: docker`, same Dockerfile, context, branch, region and build filter, `schedule: "0 7,8 * * *"`, `dockerCommand: sh -c 'export GIT_SHA="${RENDER_GIT_COMMIT:-unknown}"; exec python -m backend.jobs.nightly_run'`, no pre-deploy command, `autoDeployTrigger` as the web service of its environment, variables only `fromGroup` of its environment.
- Runbook sections in `docs/deployment.md`: Render project `echowell` with environments `production` and `staging`; creating the services from the Blueprint (Dashboard → New → Blueprint) and the dashboard-only settings (secret values, workspace notifications for failed deploys, Blueprint sync, project/environment assignment; staging auto-deploy "After CI checks pass"; production auto-deploy off, deployed only by `deploy-production.yml` through the Render API, D-99); `ohio` (the region of `echowell-api`) (US East); Starter instances (no Free instance type: spin-down and no pre-deploy command); default domains `echowell-api.onrender.com` / `echowell-backend-production.onrender.com` or the recorded assigned names (the pre-D-153 service `echowell-api.onrender.com` is either recreated or recorded, TRD 15 §4.5 step 3); `GIT_SHA` from `RENDER_GIT_COMMIT` in both environments; the outbound IP ranges; the cron job variable allow-list (environment group only); the weekly cost check (TPS-021).
- Rollback runbook: Render dashboard → service → Events → last good deploy → "Rollback" for the web service and the cron job; re-enable auto-deploy on the staging services after the revert is merged (Render turns it off on rollback); the post-migration caveat of TRD 15 §4.12.
- Neon runbook: project `echowell`, PostgreSQL 16, region `aws-us-east-1`, database `echowell`, default database branch `main`; owner-role SQL `CREATE EXTENSION IF NOT EXISTS pgcrypto; CREATE EXTENSION IF NOT EXISTS btree_gist; ALTER DATABASE echowell SET timezone = 'UTC';`; group and login roles with generated passwords; child database branch `staging`; pooled URL for `echowell_app` and `echowell_readonly` (staging only), direct URL for `echowell_migrator`; autosuspend default; temporary `pre-<sha>` and `restore-drill` branches deleted within 7 days.
- The Render Postgres fallback procedure (DEP-035, TPS-030).
- An import-boundary test asserting that only `backend/alembic/env.py` and the TRD 20 §4.3 closed list read DATABASE_MIGRATION_URL.

## Out of Scope

- Executing any deployment, creating accounts or setting real variables (Phase 10, FEAT-088; TRD 25 §4.6 Phase 9 "no deployment performed").
- `backend/jobs/nightly_run.py` logic (FEAT-054) and the missing-run detection (FEAT-056).
- Netlify configuration (FEAT-082), secrets policy and rotation (FEAT-083), deploy verification workflows (FEAT-086).
- AWS EventBridge scheduling (FEAT-092).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-081-FR-01 | The Render web service shall run migrations only as its pre-deploy command `alembic upgrade head`, and its Docker command shall be `uvicorn backend.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips="*"` wrapped in `sh -c`, preceded only by `export GIT_SHA="${RENDER_GIT_COMMIT:-unknown}"` (API-103). | DEP-040, D-58 |
| FEAT-081-FR-02 | DATABASE_MIGRATION_URL shall be an environment variable of the web service only (never of the environment group or the cron job); application request, pipeline and job code shall never read it (import-boundary test). | DEP-040, SEC-111, RSK-15 |
| FEAT-081-FR-03 | The health check path shall be `/api/v1/health`; a deploy whose health check does not pass shall not receive traffic (Render keeps the previous deploy). | DEP-041, LOG-071 |
| FEAT-081-FR-04 | The backend web service shall run exactly one instance in staging and production on the Starter instance type; the Free instance type (spin-down, no pre-deploy command) shall not be used. | DEP-042 |
| FEAT-081-FR-05 | Render auto-deploy "After CI checks pass" (`autoDeployTrigger: checksPass`) shall be set on the `staging` services so a commit deploys only after its checks pass; the `production` services shall have auto-deploy off and be deployed only by `deploy-production.yml`. | DEP-043, DEP-003 |
| FEAT-081-FR-06 | Render configuration of the four services and two environment groups shall be stored in `/render.yaml` (secret values never, `sync: false`); every dashboard-only setting shall be listed in `docs/deployment.md`. | DEP-044 |
| FEAT-081-FR-07 | The backend shall send `Strict-Transport-Security: max-age=31536000; includeSubDomains` in staging and production and be reachable only over HTTPS through the Render edge (automatic TLS). | DEP-045, SEC-062 |
| FEAT-081-FR-08 | The nightly run shall be a separate Render cron job `echowell-nightly-<env>` running `python -m backend.jobs.nightly_run` on `0 7,8 * * *` UTC with no public URL, no health check, no pre-deploy command, and only the variables of its environment group: DATABASE_URL, APP_ENV, PIPELINE_PROFILE, PIPELINE_AS_OF (non-production only), FACILITY_NAME, FACILITY_TZ, NIGHTLY_RUN_HOUR_LOCAL, LOG_LEVEL, LOG_FORMAT and optional SENTRY_DSN (GIT_SHA comes from `RENDER_GIT_COMMIT`). | DEP-046, LOG-110, D-47, SEC-111 |
| FEAT-081-FR-09 | The nightly cron job shall never run `alembic upgrade` and shall exit non-zero when the database schema revision differs from the revision bundled in its image. | DEP-048 |
| FEAT-081-FR-10 | Neon project `echowell` shall run PostgreSQL 16 in `aws-us-east-1` with database branches `main` (production) and `staging` only, plus temporary `pre-<sha>` and `restore-drill` branches deleted within 7 days. | DEP-030, DEP-031, DEP-005, TPS-031, D-54 |
| FEAT-081-FR-11 | Extensions `pgcrypto` and `btree_gist` and the database `timezone` `UTC` shall be set by the Neon owner role before any migration; migrations never create extensions. | TRD 15 §4.4 step 4, D-72 |
| FEAT-081-FR-12 | The runtime backend shall connect as `echowell_app` through the pooled endpoint and Alembic as `echowell_migrator` through the direct endpoint; DATABASE_READONLY_URL (pooled, readonly role) shall be set only on staging. | DEP-032, SEC-116 |
| FEAT-081-FR-13 | Every Neon connection string shall include `sslmode=require`; connection strings shall be stored only in Render environment variables / environment groups and, for staging re-seeding, in the GitHub environment secret `STAGING_DATABASE_URL`. | DEP-033, DEP-034, SEC-061, DB-053 |
| FEAT-081-FR-14 | Schema changes shall be applied only by `alembic upgrade head` as the pre-deploy command; migrations shall be backward compatible (expand/contract), applied on staging first, take advisory lock `0x45434857`, and a failing upgrade shall exit non-zero so the previous deployment stays live. | DEP-060, DEP-061, DEP-062, DEP-064, DEP-065 |
| FEAT-081-FR-15 | Before a release with a migration is deployed to production, the runbook shall instruct creating Neon branch `pre-<short-sha>` from `main`, deleted after 7 days if unused. | DEP-063 |
| FEAT-081-FR-16 | No application code shall use Render- or Neon-specific APIs or SDKs; only `render.yaml`, environment variables, the PORT convention and the `RENDER_GIT_COMMIT` export in the `render.yaml` commands couple the deployment to Render. | TPS-020, TPS-032, DEP-110 |
| FEAT-081-FR-17 | Render costs shall be bounded by the configured instance types (two Starter web services, two cron jobs, no autoscaling); the runbook records the weekly month-to-date cost check and billing e-mails to the project mailbox (Render has no hard spending cap). | TPS-021 |
| FEAT-081-FR-18 | The Render Postgres fallback shall require only the D-72 provisioning as the database's admin user (verified able to create the extensions and roles), a change of the three database URLs and a `pg_dump`/`pg_restore` (restored as `echowell_migrator`, `--no-owner`). | DEP-035, TPS-030 |

## Inputs

- Backend image definition (FEAT-077), `backend.jobs.nightly_run` (FEAT-054), `alembic.ini` at the repository root.
- TRD 21 §4.7 variable matrix; TRD 15 §4.4/§4.5 procedures.

## Outputs

- `/render.yaml` (Blueprint: two web services, two cron jobs, two environment groups).
- `docs/deployment.md` sections "Render backend", "Render nightly cron job", "Render rollback", "Neon database", "Render Postgres fallback" (values and names, never secrets).
- `tests/unit/backend/core/test_migration_url_boundary.py` (import-boundary test).

## Data Flow

Merge to `main` → Render `staging` waits until the commit's checks pass (production: approved `deploy-production.yml` run → Render API deploy with `commitId`) → builds `backend/Dockerfile` → pre-deploy instance runs `alembic upgrade head` (migrator role, direct Neon endpoint) → new instance starts uvicorn (app role, pooled endpoint, `GIT_SHA` = `RENDER_GIT_COMMIT`) → health check `/api/v1/health` → traffic switched. Cron 07:00 and 08:00 UTC → `echowell-nightly-<env>` run → `backend.jobs.nightly_run` checks facility-local 02:xx and the per-date dedupe under the nightly advisory lock → full run or exit 0 after the missing-run check.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-077, FEAT-054

- [FEAT-077](FEAT-077-Production-Container-Images-Compose-Demo-Profile.md) Production container images (the image Render builds).
- [FEAT-054](FEAT-054-Ingest-Triggered-And-Nightly-Pipeline-Runs.md) Ingest-triggered and nightly pipeline runs (`backend/jobs/nightly_run.py`).

Features that build directly on this one (BACKLOG.md §4): FEAT-083, FEAT-084, FEAT-085, FEAT-086.

## Database Impact

- No table is created or altered by this feature. The runbook provisions the Neon project, branches, extensions, timezone and roles (`echowell_migrator`, `echowell_app`, `echowell_readonly` and their login roles); the tables come from Alembic migrations (TRD 20).
- Tables read at runtime by the configured services: all application tables through `echowell_app`; `alembic_version` by the nightly schema-revision check (DEP-048).

## API Impact

- `GET /api/v1/health` is the Render health check (must return 200 with `version` = deployed SHA).
- No endpoint is added or changed.

## Frontend Impact

None. The frontend reaches the backend at the Render `onrender.com` domain configured in Netlify (FEAT-082).

## Analytics Impact

None in code. The nightly cron job runs the unchanged pipeline with trigger `nightly` (D-47).

## Security Requirements

- Least privilege: app role for the web service and the cron job; migrator credential only on the web service; readonly URL only on staging (SEC-111, SEC-116).
- TLS to Neon with `sslmode=require`; HSTS on responses (DEP-034, DEP-045).
- US East regions only (SEC-007, TPS-004); team-owned accounts with ≥ 2 MFA admins (TPS-005).
- Interim stack holds synthetic and test data only (AGT-014, DEP-008).

## Error Handling

- Failing pre-deploy migration → deploy fails ("pre-deploy failed"), previous deploy stays live (DEP-065); Render notification e-mail.
- Failing health check → no traffic switch; Render marks the deploy failed (DEP-041).
- Backend crash → Render restarts the instance automatically.
- Nightly schema mismatch → non-zero exit, the cron run is marked failed and visible in the cron job's Logs (DEP-048); missed night → `nightly_run_missing` ERROR (LOG-111, FEAT-056).

## Logging Requirements

- Services log JSON to stdout (LOG_FORMAT `json`), retained by Render at the workspace plan's default; no export to other log stores (LOG-120).
- The runbook records account owner, admins, plan and the date limits were verified, without credentials (TPS-006, TPS-007).

## Testing Requirements

- Unit: import-boundary test for DATABASE_MIGRATION_URL (DEP-040 verification); `test_nightly_schema_revision_mismatch_exits_nonzero` (DEP-048) if not already delivered by FEAT-054.
- Integration: TST-052 (nightly dedupe across the DST change) remains green.
- Inspection: `render.yaml` compared field by field with the TRD 15 outline (and validated by the Blueprint preview in the Render dashboard before sync); CI dry run (TRD 25 §4.6 Phase 9).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-081-AC-01 | Each web service in `/render.yaml` has `preDeployCommand: alembic upgrade head`, a `dockerCommand` without `alembic`, `healthCheckPath: /api/v1/health`, `numInstances: 1` and a paid `plan` (not `free`). Verified by: Test (run the command in the criterion against the stated environment and check the stated result). | DEP-040, DEP-041, DEP-042 |
| FEAT-081-AC-02 | Each cron job in `/render.yaml` has a `dockerCommand` running `python -m backend.jobs.nightly_run`, `schedule: "0 7,8 * * *"`, no `preDeployCommand`, only `fromGroup` variables, and no `alembic`. Verified by: Test (run the command in the criterion against the stated environment and check the stated result). | DEP-046, DEP-048 |
| FEAT-081-AC-03 | The import-boundary test passes and fails when a module under `backend/api/`, `backend/services/` or `backend/jobs/` references `DATABASE_MIGRATION_URL`. Verified by: Unit (import-boundary test for DATABASE_MIGRATION_URL (DEP-040 verification)). | DEP-040, SEC-111 |
| FEAT-081-AC-04 | `docs/deployment.md` lists every dashboard-only setting of DEP-044 and the cron job variable allow-list, with no secret value. Verified by: Integration (TST-052). | DEP-044, ENV-005 |
| FEAT-081-AC-05 | The Neon runbook names region `aws-us-east-1`, PostgreSQL 16, database branches `main` and `staging`, the owner-role extension and timezone SQL, and `sslmode=require` on every URL. Verified by: Inspection (the inspection method of DEP-030, applied to the condition stated in the criterion). | DEP-030, DEP-031, DEP-034, D-72 |
| FEAT-081-AC-06 | `grep "neon.tech" render.yaml` returns nothing and every secret key in it is `sync: false`. Verified by: Inspection (run the command in the criterion and check its output). | AC-DEP-10 |

## Definition of Done

- All FEAT-081 acceptance criteria pass; no deployment performed (TRD 25 §4.6 Phase 9).
- `CONFIGURATION_VALIDATION_REPORT.md` (FEAT-087) records the comparison with SRC-01 and TRD 22.
- Batch report entry (AGT-022).

## Implementation Notes

- Keep the `sh -c '...'` wrapper so `$PORT` and `RENDER_GIT_COMMIT` expand (TRD 15 §8).
- Render cron schedules are UTC only; Render runs at most one run of a cron job at a time and does not retry a failed run.
- A service's region cannot be changed after creation; the existing `echowell-api` service is in `ohio`; create the production service in the same region (D-156).
- `backend/jobs/nightly_run.py` takes the transaction-scoped nightly advisory lock (TRD 06 DB-021 (d)) before inserting the nightly `pipeline_runs` row; both cron firings may start, only one proceeds (TRD 15 §8).
- Neon hands out `postgres://` URLs; settings normalise them to `postgresql+psycopg://` (TRD 15 §8).
- The engine factory disables server-side prepared statements (`prepare_threshold: None`) for the pooled endpoint (API-125).
- Avoid production deploys in the 08:00–20:00 facility-local window while OQ-15 is open (TRD 15 §9).
