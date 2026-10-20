# FEAT-081 Railway backend and nightly cron services, Neon database configuration

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

Write the backend hosting configuration for the interim stack as code and as a runbook, without deploying: `railway.toml` for the `backend` service (pre-deploy `alembic upgrade head`, uvicorn start command, healthcheck `/api/v1/health`, one replica, "Wait for CI"), `railway.nightly.toml` for the separate `nightly` Railway Cron Job service (`0 7,8 * * *` UTC, `python -m backend.jobs.nightly_run`), and the Neon setup procedure (project `echowell` in `aws-us-east-1`, branches `main` and `staging`, extensions and timezone set by the owner role, pooled endpoint for the app role, direct endpoint for the migrator). Phase 10 (FEAT-088) executes these procedures.

## Business Context

- BR-17 and SRC-01: FastAPI with the analytics engine on Railway, PostgreSQL 16 on Neon (DEP-003, DEP-005, VIS-016).
- BR-16: least-privilege database roles, TLS to the database, migrator credential kept off the cron service (DEP-032, DEP-034, SEC-111).
- BR-06, BR-11: the nightly run extends the day ledger and keeps alarms current even without new records (DEP-046, DEP-047).

## Referenced TRDs

- TRD 15 DEP-001, DEP-003, DEP-004, DEP-005, DEP-030..DEP-035, DEP-040..DEP-048, DEP-060..DEP-065, §4.4 Neon procedure, §4.5 Railway procedure and outlines, §8 Implementation Notes.
- TRD 22 TPS-020, TPS-021, TPS-030, TPS-031, TPS-032, TPS-004, TPS-005, TPS-006, TPS-007.
- TRD 17 LOG-110, LOG-111, LOG-071.
- TRD 12 SEC-007, SEC-061, SEC-111, SEC-116.
- TRD 21 ENV-050, ENV-053, §4.7 matrix.
- TRD 06 DB-021 (nightly advisory lock), DB-053.
- TRD 24 D-47, D-54, D-58, D-62, D-72, RSK-15.
- TRD 25 §4.6 Phase 9 (no deployment performed), AGT-014, AGT-059.

## Scope

- `/railway.toml` exactly per the TRD 15 §4.5 outline: builder `DOCKERFILE`, `dockerfilePath = "backend/Dockerfile"`, `watchPatterns = ["backend/**", "analytics/**", "alembic.ini", "railway.toml"]`, `preDeployCommand = ["alembic upgrade head"]`, `startCommand = "sh -c 'uvicorn backend.main:app --host 0.0.0.0 --port $PORT'"`, `healthcheckPath = "/api/v1/health"`, `healthcheckTimeout = 120`, `restartPolicyType = "ON_FAILURE"`, `restartPolicyMaxRetries = 3`, `numReplicas = 1`.
- `/railway.nightly.toml` per the outline: builder `DOCKERFILE`, `dockerfilePath = "backend/Dockerfile"`, `watchPatterns = ["backend/**", "analytics/**"]`, `startCommand = "python -m backend.jobs.nightly_run"`, `cronSchedule = "0 7,8 * * *"`, `restartPolicyType = "NEVER"`.
- Runbook sections in `docs/deployment.md`: Railway project `echowell` with environments `production` and `staging`; dashboard-only settings (source branch `main`/`staging`, root `/`, Wait for CI on, region US East (Virginia), app sleeping allowed except demo days, public domains `echowell-backend-production.up.railway.app` / `echowell-backend-staging.up.railway.app` or the recorded generated names, `GIT_SHA=${{RAILWAY_GIT_COMMIT_SHA}}`); the `nightly` service variable allow-list; the usage hard limit (USD 20, alert at USD 10).
- Neon runbook: project `echowell`, PostgreSQL 16, region `aws-us-east-1`, database `echowell`, default branch `main`; owner-role SQL `CREATE EXTENSION IF NOT EXISTS pgcrypto; CREATE EXTENSION IF NOT EXISTS btree_gist; ALTER DATABASE echowell SET timezone = 'UTC';`; group and login roles with generated passwords; child branch `staging`; pooled URL for `echowell_app` and `echowell_readonly` (staging only), direct URL for `echowell_migrator`; autosuspend default; temporary `pre-<sha>` and `restore-drill` branches deleted within 7 days.
- The Railway PostgreSQL fallback procedure (DEP-035, TPS-030).
- An import-boundary test asserting that only `backend/alembic/env.py` and the TRD 20 §4.3 closed list read DATABASE_MIGRATION_URL.

## Out of Scope

- Executing any deployment, creating accounts or setting real variables (Phase 10, FEAT-088; TRD 25 §4.6 Phase 9 "no deployment performed").
- `backend/jobs/nightly_run.py` logic (FEAT-054) and the missing-run detection (FEAT-056).
- Netlify configuration (FEAT-082), secrets policy and rotation (FEAT-083), deploy verification workflows (FEAT-086).
- AWS EventBridge scheduling (FEAT-092).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-081-FR-01 | The Railway `backend` service shall run migrations only as its pre-deploy command `alembic upgrade head`, and its start command shall be `uvicorn backend.main:app --host 0.0.0.0 --port $PORT` wrapped in `sh -c`. | DEP-040, D-58 |
| FEAT-081-FR-02 | DATABASE_MIGRATION_URL shall be a variable of the `backend` service only; application request, pipeline and job code shall never read it (import-boundary test). | DEP-040, SEC-111, RSK-15 |
| FEAT-081-FR-03 | The healthcheck path shall be `/api/v1/health` with timeout 120 s; a deployment whose healthcheck fails shall not receive traffic. | DEP-041, LOG-071 |
| FEAT-081-FR-04 | The backend service shall run exactly one replica in staging and production; app sleeping may be enabled except on demo days. | DEP-042 |
| FEAT-081-FR-05 | Railway "Wait for CI" shall be enabled so a commit deploys only after its required checks pass. | DEP-043 |
| FEAT-081-FR-06 | Railway configuration shall be stored in `/railway.toml` and `/railway.nightly.toml`; every dashboard-only setting shall be listed in `docs/deployment.md`. | DEP-044 |
| FEAT-081-FR-07 | The backend shall send `Strict-Transport-Security: max-age=31536000; includeSubDomains` in staging and production and be reachable only over HTTPS through the Railway edge. | DEP-045, SEC-062 |
| FEAT-081-FR-08 | The nightly run shall be a separate Railway Cron Job service `nightly` running `python -m backend.jobs.nightly_run` on `0 7,8 * * *` UTC with restart policy never, no public domain, no healthcheck, and only the variables DATABASE_URL, APP_ENV, PIPELINE_PROFILE, PIPELINE_AS_OF (non-production only), FACILITY_NAME, FACILITY_TZ, NIGHTLY_RUN_HOUR_LOCAL, LOG_LEVEL, LOG_FORMAT, GIT_SHA and optional SENTRY_DSN. | DEP-046, LOG-110, D-47, SEC-111 |
| FEAT-081-FR-09 | The `nightly` service shall never run `alembic upgrade` and shall exit non-zero when the database schema revision differs from the revision bundled in its image. | DEP-048 |
| FEAT-081-FR-10 | Neon project `echowell` shall run PostgreSQL 16 in `aws-us-east-1` with branches `main` (production) and `staging` only, plus temporary `pre-<sha>` and `restore-drill` branches deleted within 7 days. | DEP-030, DEP-031, DEP-005, TPS-031, D-54 |
| FEAT-081-FR-11 | Extensions `pgcrypto` and `btree_gist` and the database `timezone` `UTC` shall be set by the Neon owner role before any migration; migrations never create extensions. | TRD 15 §4.4 step 4, D-72 |
| FEAT-081-FR-12 | The runtime backend shall connect as `echowell_app` through the pooled endpoint and Alembic as `echowell_migrator` through the direct endpoint; DATABASE_READONLY_URL (pooled, readonly role) shall be set only on staging. | DEP-032, SEC-116 |
| FEAT-081-FR-13 | Every Neon connection string shall include `sslmode=require`; connection strings shall be stored only in Railway variables and, for staging re-seeding, in the GitHub environment secret `STAGING_DATABASE_URL`. | DEP-033, DEP-034, SEC-061, DB-053 |
| FEAT-081-FR-14 | Schema changes shall be applied only by `alembic upgrade head` as the pre-deploy command; migrations shall be backward compatible (expand/contract), applied on staging first, take advisory lock `0x45434857`, and a failing upgrade shall exit non-zero so the previous deployment stays live. | DEP-060, DEP-061, DEP-062, DEP-064, DEP-065 |
| FEAT-081-FR-15 | Before a release with a migration is merged to `main`, the runbook shall instruct creating Neon branch `pre-<short-sha>` from `main`, deleted after 7 days if unused. | DEP-063 |
| FEAT-081-FR-16 | No application code shall use Railway- or Neon-specific APIs or SDKs; only `railway.toml`, environment variables and the PORT convention couple the code to Railway. | TPS-020, TPS-032, DEP-110 |
| FEAT-081-FR-17 | The Railway workspace shall have a usage hard limit of USD 20 per month with an e-mail alert at USD 10. | TPS-021 |
| FEAT-081-FR-18 | The Railway PostgreSQL fallback shall require only the D-72 provisioning as the Railway `postgres` superuser, a change of the three database URLs and a `pg_dump`/`pg_restore` (restored as `echowell_migrator`, `--no-owner`). | DEP-035, TPS-030 |

## Inputs

- Backend image definition (FEAT-077), `backend.jobs.nightly_run` (FEAT-054), `alembic.ini` at the repository root.
- TRD 21 §4.7 variable matrix; TRD 15 §4.4/§4.5 procedures.

## Outputs

- `/railway.toml`, `/railway.nightly.toml`.
- `docs/deployment.md` sections "Railway backend", "Railway nightly cron service", "Neon database", "Railway PostgreSQL fallback" (values and names, never secrets).
- `tests/unit/backend/core/test_migration_url_boundary.py` (import-boundary test).

## Data Flow

Merge to `staging`/`main` → Railway waits for CI → builds `backend/Dockerfile` → pre-deploy container runs `alembic upgrade head` (migrator role, direct Neon endpoint) → new container starts uvicorn (app role, pooled endpoint) → healthcheck `/api/v1/health` → traffic switched. Cron 07:00 and 08:00 UTC → `nightly` container → `backend.jobs.nightly_run` checks facility-local 02:xx and the per-date dedupe under the nightly advisory lock → full run or exit 0 after the missing-run check.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-077, FEAT-054

- [FEAT-077](FEAT-077-Production-Container-Images-Compose-Demo-Profile.md) Production container images (the image Railway builds).
- [FEAT-054](FEAT-054-Ingest-Triggered-And-Nightly-Pipeline-Runs.md) Ingest-triggered and nightly pipeline runs (`backend/jobs/nightly_run.py`).

## Database Impact

- No table is created or altered by this feature. The runbook provisions the Neon project, branches, extensions, timezone and roles (`echowell_migrator`, `echowell_app`, `echowell_readonly` and their login roles); the tables come from Alembic migrations (TRD 20).
- Tables read at runtime by the configured services: all application tables through `echowell_app`; `alembic_version` by the nightly schema-revision check (DEP-048).

## API Impact

- `GET /api/v1/health` is the Railway healthcheck (must return 200 with `version` = deployed SHA).
- No endpoint is added or changed.

## Frontend Impact

None. The frontend reaches the backend at the Railway public domain configured in Netlify (FEAT-082).

## Analytics Impact

None in code. The nightly service runs the unchanged pipeline with trigger `nightly` (D-47).

## Security Requirements

- Least privilege: app role for the web and nightly services; migrator credential only on `backend`; readonly URL only on staging (SEC-111, SEC-116).
- TLS to Neon with `sslmode=require`; HSTS on responses (DEP-034, DEP-045).
- US East regions only (SEC-007, TPS-004); team-owned accounts with ≥ 2 MFA admins (TPS-005).
- Interim stack holds synthetic and test data only (AGT-014, DEP-008).

## Error Handling

- Failing pre-deploy migration → deployment aborted, previous deployment stays live (DEP-065).
- Failing healthcheck within 120 s → no traffic switch (DEP-041).
- Backend crash → restart on failure, max 3 retries.
- Nightly schema mismatch → non-zero exit, visible in Railway logs (DEP-048); missed night → `nightly_run_missing` ERROR (LOG-111, FEAT-056).

## Logging Requirements

- Services log JSON to stdout (LOG_FORMAT `json`), retained by Railway at platform default; no export to other log stores (LOG-120).
- The runbook records account owner, admins, plan and the date limits were verified, without credentials (TPS-006, TPS-007).

## Testing Requirements

- Unit: import-boundary test for DATABASE_MIGRATION_URL (DEP-040 verification); `test_nightly_schema_revision_mismatch_exits_nonzero` (DEP-048) if not already delivered by FEAT-054.
- Integration: TST-052 (nightly dedupe across the DST change) remains green.
- Inspection: TOML files compared field by field with the TRD 15 outlines; CI dry run (TRD 25 §4.6 Phase 9).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-081-AC-01 | `/railway.toml` contains `preDeployCommand = ["alembic upgrade head"]`, a start command without `alembic`, `healthcheckPath = "/api/v1/health"`, `healthcheckTimeout = 120` and `numReplicas = 1`. | DEP-040, DEP-041, DEP-042 |
| FEAT-081-AC-02 | `/railway.nightly.toml` contains `startCommand = "python -m backend.jobs.nightly_run"`, `cronSchedule = "0 7,8 * * *"` and `restartPolicyType = "NEVER"`, and no `alembic`. | DEP-046, DEP-048 |
| FEAT-081-AC-03 | The import-boundary test passes and fails when a module under `backend/api/`, `backend/services/` or `backend/jobs/` references `DATABASE_MIGRATION_URL`. | DEP-040, SEC-111 |
| FEAT-081-AC-04 | `docs/deployment.md` lists every dashboard-only setting of DEP-044 and the `nightly` variable allow-list, with no secret value. | DEP-044, ENV-005 |
| FEAT-081-AC-05 | The Neon runbook names region `aws-us-east-1`, PostgreSQL 16, branches `main` and `staging`, the owner-role extension and timezone SQL, and `sslmode=require` on every URL. | DEP-030, DEP-031, DEP-034, D-72 |
| FEAT-081-AC-06 | `grep -r "neon.tech" railway.toml railway.nightly.toml` returns nothing. | AC-DEP-10 |

## Definition of Done

- All FEAT-081 acceptance criteria pass; no deployment performed (TRD 25 §4.6 Phase 9).
- `CONFIGURATION_VALIDATION_REPORT.md` (FEAT-087) records the comparison with SRC-01 and TRD 22.
- Batch report entry (AGT-022).

## Implementation Notes

- Keep the `sh -c '...'` wrapper so `$PORT` expands (TRD 15 §8).
- `backend/jobs/nightly_run.py` takes the transaction-scoped nightly advisory lock (TRD 06 DB-021 (d)) before inserting the nightly `pipeline_runs` row; both cron firings may start, only one proceeds (TRD 15 §8).
- Neon hands out `postgres://` URLs; settings normalise them to `postgresql+psycopg://` (TRD 15 §8).
- The engine factory disables server-side prepared statements (`prepare_threshold: None`) for the pooled endpoint (API-125).
- Avoid production deploys in the 08:00–20:00 facility-local window while OQ-15 is open (TRD 15 §9).
