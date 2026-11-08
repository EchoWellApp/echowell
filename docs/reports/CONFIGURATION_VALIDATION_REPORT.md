# EchoWell Configuration Validation Report

Document: docs/reports/CONFIGURATION_VALIDATION_REPORT.md · Block 3 checkpoint 8 (TRD 25 Phase 9, `Implement_Feature_Batches.md` Phase 14A) · Date: 5 November 2026 · Owner: Team 2 · Feature: FEAT-087

**No deployment was performed in this checkpoint.** No Render, Netlify, Neon or Sentry account, API or service was called; no secret was created or used; only synthetic data was used locally (TRD 25 §4.6 Phase 9 definition of done, AGT-014).

This report validates every Phase 9 configuration artefact against SRC-01 (`specs/architecture/Deployment_Architecture.md`), TRD 15, TRD 16, TRD 21 and TRD 22 (FEAT-087-FR-05). A row marked FAIL blocks Phase 10 until fixed (AGT-033). Rows marked **RESULT: pending integration** depend on artefacts produced in parallel in this checkpoint and are completed when the checkpoint branch is integrated. Integration pass on 5 November 2026 (branch `feat/cp8-deployment-config`): every such row was re-checked against the integrated files; only P.02 (full stack and full test run) remains pending. Rows that need real accounts or GitHub settings are marked **N/A — Block 4**.

Result values: **PASS** · **FAIL** (with reason) · **RESULT: pending integration** · **N/A** (with reason).

## 1. Summary

| Area | Rows | PASS | FAIL | N/A | Pending integration |
|---|---|---|---|---|---|
| A. Architecture (SRC-01) | 6 | 6 | 0 | 0 | 0 |
| B. Regions and data location (TRD 22, D-54, D-156) | 4 | 4 | 0 | 0 | 0 |
| C. Database URLs and TLS (TRD 21 ENV-011, DEP-034) | 4 | 4 | 0 | 0 | 0 |
| D. Production templates (AGT-015) | 4 | 4 | 0 | 0 | 0 |
| E. Render Blueprint (TRD 15 §4.5) | 10 | 10 | 0 | 0 | 0 |
| F. Netlify (TRD 15 §4.6, TRD 12 §4.9) | 6 | 6 | 0 | 0 | 0 |
| G. Containers and Compose (TRD 15 §4.2–§4.3) | 6 | 6 | 0 | 0 | 0 |
| H. Environment templates and variables (TRD 21) | 5 | 5 | 0 | 0 | 0 |
| I. CI and E2E workflows (TRD 16 §4.2–§4.3, §4.7) | 7 | 7 | 0 | 0 | 0 |
| J. Deploy workflows (TRD 16 §4.4–§4.5, §4.9) | 16 | 16 | 0 | 0 | 0 |
| K. Uptime workflow (TRD 16 §4.6, TRD 17) | 6 | 6 | 0 | 0 | 0 |
| L. Smoke tests (TRD 15 §4.11, TRD 13) | 8 | 8 | 0 | 0 | 0 |
| M. Secrets in GitHub (CIC-090, AC-CIC-06) | 2 | 2 | 0 | 0 | 0 |
| N. Sentry (TRD 17, TRD 22) | 6 | 6 | 0 | 0 | 0 |
| O. Documentation (FEAT-087) | 6 | 6 | 0 | 0 | 0 |
| P. Phase 9 commands | 4 | 4 | 0 | 0 | 0 |
| **Total** | **96** | **96** | **0** | **0** | **0** |

No open FAIL (B.02 is documented in the guide, not the TRD-verbatim template; §4 item 7). Checks whose final evidence needs real accounts or GitHub (the `sslmode` content of the `STAGING_DATABASE_URL` secret in C.04, branch protection in O.05, the first CI run confirming the action tags in I.07) are verified here on the committed configuration only and repeated in Phase 10 / Block 4.

## 2. Results

### A. Architecture (SRC-01)

| ID | Check | Artefact | Source | Method | Result |
|---|---|---|---|---|---|
| A.01 | Frontend hosted on Netlify, built from `frontend/` (GitHub → Netlify) | `netlify.toml` | SRC-01 "Deployment Strategy", DEP-050 | Inspection | **PASS**: `[build] base = "frontend"`, `@netlify/plugin-nextjs`; sites build from GitHub `main` (header comment, D-99) |
| A.02 | Backend hosted on Render as a Docker web service from `backend/Dockerfile` plus a nightly cron job (GitHub → Render) | `render.yaml` | SRC-01 "Backend Hosting", D-153, DEP-046 | Inspection | **PASS**: two `type: web` services with `runtime: docker`, `dockerfilePath: ./backend/Dockerfile`, and two `type: cron` nightly jobs, all from `repo: https://github.com/EchoWellApp/echowell` |
| A.03 | PostgreSQL on Neon (Render Postgres only as contingency) | `render.yaml` (no database service), `.env.production.example` | SRC-01 "Database Hosting", TPS-030 | Inspection | **PASS**: `render.yaml` has no `databases:` key and no Render Postgres service; `.env.production.example` names Neon pooled/direct URLs for all three database variables |
| A.04 | CI on GitHub Actions runs unit, integration and validation tests and the frontend build on every PR and merge | `.github/workflows/ci.yml` | SRC-01 "CI/CD", CIC-010, CIC-013, CIC-017 | Inspection | **PASS**: triggers `pull_request`, `push` to `main`, `workflow_dispatch`; `backend-test` runs `tests/unit tests/integration tests/contract tests/security tests/validation` in one invocation; job `frontend` runs `npm run build` |
| A.05 | No platform SDK in application code; platform specifics only in `netlify.toml`, `render.yaml`, env vars (AWS portability) | `backend/`, `analytics/`, `frontend/` | SRC-01 "Future AWS Migration", DEP-110, TPS-020 | `grep -rniE "render\.com\|netlify\|neon" backend analytics frontend/app frontend/lib` | **PASS**: the only matches are the words `neon` and `oneone` in `backend/core/common_passwords.txt` (password deny-list data, not platform code); `backend/requirements.txt` holds no Render/Netlify/Neon SDK |
| A.06 | Deploy verification and release use only public HTTPS endpoints and the two platform deploy APIs; staging deploys via integrations, production via the approved release workflow | `deploy-staging.yml`, `deploy-production.yml` | SRC-01, TRD 16 §4.1, D-99 | Inspection | PASS: staging workflow holds no platform token; production uses the Render API and Netlify CLI only in job `deploy` (environment `production`) |

### B. Regions and data location (D-54, D-156, TPS-004)

| ID | Check | Artefact | Source | Method | Result |
|---|---|---|---|---|---|
| B.01 | Render services and cron jobs in region `ohio` (US East), the region of `echowell-api` | `render.yaml` | D-156, TPS-004, DEP-031 | Inspection | **PASS**: `region: ohio` on all four services (web `echowell-api`, `echowell-backend-production`; cron `echowell-nightly-staging`, `echowell-nightly-production`) |
| B.02 | Neon project `aws-us-east-1` documented as the only database region | `docs/reports/DEPLOYMENT_CONFIGURATION_GUIDE.md` §3, `docs/deployment.md` | D-54, DEP-031 | Inspection | **PASS**: guide §3 step 2 and `docs/deployment.md` name `aws-us-east-1` as the only database region. `.env.production.example` stays byte-identical to TRD 21 §4.6 (`test_env_040_templates_match_trd21`), which has no region comment, so the region is documented in the guide rather than in the template (§4 item 7) |
| B.03 | No hostname containing `neon.tech` and no production secret in committed configuration | `netlify.toml`, `render.yaml`, `docker-compose.yml`, Dockerfiles | AC-DEP-10 | `grep -rn "neon.tech" netlify.toml render.yaml docker-compose.yml backend/Dockerfile frontend/Dockerfile` | **PASS**: grep returns nothing (exit 1); the only credentials in these files are the `local-dev-only-*` placeholders of `docker-compose.yml`; `render.yaml` declares every secret `sync: false` without a value |
| B.04 | Netlify stores no data; SSR in the default US region | `netlify.toml` | TPS-004, TRD 22 §4.2 | Inspection | **PASS**: `netlify.toml` has no data store, no Blobs/Forms and no region override (default US region for SSR); `frontend/middleware.ts` (headers only, stores nothing) is deployed by the plugin as an edge function, see §4 item 8 |

### C. Database URLs and TLS (TRD 21 ENV-011, DEP-034)

| ID | Check | Artefact | Source | Method | Result |
|---|---|---|---|---|---|
| C.01 | `DATABASE_URL` (app role) template value contains `sslmode=require` for staging and production | `.env.production.example`, `.env.example` | ENV-011, DEP-034, TRD 25 Phase 9 DoD | Inspection | **PASS**: both values are empty (secrets); `.env.example` comment "sslmode=require in staging/production", `.env.production.example` comment "must include sslmode=require"; enforced at startup (C.03) |
| C.02 | `DATABASE_MIGRATION_URL` (migrator role) template value contains `sslmode=require` | `.env.production.example` | ENV-011, DEP-034 | Inspection | **PASS**: `DATABASE_MIGRATION_URL=` empty with comment "Neon direct URL, role echowell_migrator, must include sslmode=require" |
| C.03 | Backend refuses to start in staging or production without `sslmode=require` on any of the three URLs | `backend/core/config.py` | ENV-011, AC-ENV-02 | `pytest tests/unit/backend/core/test_config.py -q` | PASS (guard present in `startup_violations`; test suite of FEAT-083/FEAT-006) |
| C.04 | Staging re-seed uses the migrator direct URL from `STAGING_DATABASE_URL` for both URLs; the production URL is never in GitHub | `deploy-staging.yml`, `deploy-production.yml` | DEP-033, CIC-050, TRD 16 §4.4 step 4 | Inspection | **PASS**: `deploy-staging.yml` sets `DATABASE_URL` and `DATABASE_MIGRATION_URL` both from `secrets.STAGING_DATABASE_URL` (lines 93–94); `deploy-production.yml` reads only `RENDER_API_KEY` and `NETLIFY_AUTH_TOKEN`. The `sslmode` content of the secret itself is checked in Phase 10 (checklist E.01) |

### D. Production templates (AGT-015, ENV-010, ENV-012)

| ID | Check | Artefact | Source | Method | Result |
|---|---|---|---|---|---|
| D.01 | Production template sets `PIPELINE_PROFILE=production` | `.env.production.example`, `render.yaml` production group | AGT-015, TRD 25 Phase 9 DoD | Inspection | **PASS**: `.env.production.example` `PIPELINE_PROFILE=production`; group `echowell-production-shared` `PIPELINE_PROFILE: production` (`test_render_blueprint.py`, `test_env_templates.py`) |
| D.02 | Production template has no `PIPELINE_AS_OF` value | `.env.production.example`, `render.yaml` production group | ENV-012 | Inspection | **PASS**: template `PIPELINE_AS_OF=` empty ("production: must be empty"); `echowell-production-shared` has no `PIPELINE_AS_OF` key |
| D.03 | Production has no `DATABASE_READONLY_URL`, no `CORS_ORIGIN_REGEX`, no `SEED_*` | `render.yaml`, `.env.production.example` | SEC-116, ENV-012 | Inspection | **PASS**: production group and `echowell-backend-production` have no `DATABASE_READONLY_URL`, `CORS_ORIGIN_REGEX` or `SEED_*`; the shared staging/production template keeps both keys empty with "must be empty in production" / "empty in production" and lists SEED_* only in a comment ("never set here") |
| D.04 | Startup guard refuses `test_v0_1` and `PIPELINE_AS_OF` in production | `backend/core/config.py` | AC-ENV-01, AC-ENV-06, CFG-06 | `pytest tests/unit/backend/core/test_config.py -q` | PASS (guard present; FEAT-006 tests) |

### E. Render Blueprint (TRD 15 §4.5, DEP-040..DEP-048)

| ID | Check | Artefact | Source | Method | Result |
|---|---|---|---|---|---|
| E.01 | Four services: web `echowell-api`, `echowell-backend-production`; cron `echowell-nightly-staging`, `echowell-nightly-production`; two environment groups | `render.yaml` | DEP-044 | Inspection; `tests/unit/test_render_blueprint.py` | **PASS**: services `echowell-api` (web), `echowell-nightly-staging` (cron), `echowell-backend-production` (web), `echowell-nightly-production` (cron); groups `echowell-staging-shared`, `echowell-production-shared`; `pytest tests/unit/test_render_blueprint.py -q` → 16 passed |
| E.02 | Runtime Docker, `dockerfilePath: ./backend/Dockerfile`, `dockerContext: .` | `render.yaml` | DEP-020, §4.5 step 2 | Inspection | **PASS**: all four services `runtime: docker`, `dockerfilePath: ./backend/Dockerfile`, `dockerContext: .` |
| E.03 | Pre-deploy `alembic upgrade head` on web services only; none on cron jobs | `render.yaml` | DEP-040, DEP-048 | Inspection | **PASS**: `preDeployCommand: alembic upgrade head` on both web services; neither cron job has a `preDeployCommand` |
| E.04 | Docker command exports `GIT_SHA` from `RENDER_GIT_COMMIT`, uvicorn with `--proxy-headers --forwarded-allow-ips="*"` | `render.yaml` | DEP-040, API-103 | Inspection | **PASS**: web `dockerCommand: sh -c 'export GIT_SHA="${RENDER_GIT_COMMIT:-unknown}"; exec uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8000}" --proxy-headers --forwarded-allow-ips="*"'`; cron commands export `GIT_SHA` the same way |
| E.05 | `healthCheckPath: /api/v1/health`; build filter `backend/**`, `analytics/**`, `database/**`, `alembic.ini` | `render.yaml` | DEP-041, §4.5 step 2 | Inspection | **PASS**: `healthCheckPath: /api/v1/health` on both web services; `buildFilter.paths` = `backend/**`, `analytics/**`, `database/**`, `alembic.ini` on all four services |
| E.06 | Starter plan, 1 instance, no autoscaling | `render.yaml` | DEP-042, TPS-021 | Inspection | **PASS**: `plan: starter` on all four services, `numInstances: 1` on both web services, no `scaling` key |
| E.07 | Auto-deploy `checksPass` in staging, `off` in production | `render.yaml` | DEP-043, DEP-003, D-99 | Inspection | **PASS**: `autoDeployTrigger: checksPass` on `echowell-api` and `echowell-nightly-staging`; `"off"` on both production services |
| E.08 | Cron schedule `0 7,8 * * *`, command `python -m backend.jobs.nightly_run` | `render.yaml` | DEP-046, D-47 | Inspection | **PASS**: both cron jobs `schedule: "0 7,8 * * *"`, command `python -m backend.jobs.nightly_run` (wrapped in `sh -c` to export `GIT_SHA`) |
| E.09 | Every secret `sync: false`; DATABASE_MIGRATION_URL, DATABASE_READONLY_URL, JWT_SECRET and CORS only on web services, never in the group or cron job | `render.yaml` | DEP-033, DEP-040, SEC-111, ENV-053 | Inspection | **PASS**: `DATABASE_URL`, `SENTRY_DSN`, `DATABASE_MIGRATION_URL`, `DATABASE_READONLY_URL`, `JWT_SECRET` are `sync: false` without value; `DATABASE_MIGRATION_URL`, `DATABASE_READONLY_URL` (staging only), `JWT_SECRET`, `CORS_ORIGINS`, `CORS_ORIGIN_REGEX` (staging only) appear only under the web services; cron jobs use `fromGroup` only |
| E.10 | Variable values per the TRD 21 §4.7 matrix (staging and production columns) | `render.yaml` | ENV-050 | Inspection against guide §7.1 | **PASS**: every key and value of both groups and both web services equals the staging and production columns of guide §7.1 (APP_ENV, PIPELINE_PROFILE, PIPELINE_AS_OF, FACILITY_*, NIGHTLY_RUN_HOUR_LOCAL, LOG_*, JWT_EXPIRES_MINUTES 60, CORS origins, RATE_LIMIT_* 5/minute and 600/minute, DATA_SOURCE_LABEL); asserted by `test_variables_follow_the_trd21_matrix_and_secrets_are_sync_false` |

### F. Netlify (TRD 15 §4.6, TRD 12 §4.9)

| ID | Check | Artefact | Source | Method | Result |
|---|---|---|---|---|---|
| F.01 | base `frontend`, command `node scripts/check-csp.mjs && npm run build`, publish `.next`, Node 20, plugin `@netlify/plugin-nextjs` | `netlify.toml` | DEP-050 | Inspection; `tests/unit/test_netlify_config.py` | **PASS**: `base = "frontend"`, `command = "node scripts/check-csp.mjs && npm run build"`, `publish = ".next"`, `NODE_VERSION = "20"`, plugin `@netlify/plugin-nextjs` (parsed with `tomllib`); `pytest tests/unit/test_netlify_config.py -q` → 14 passed |
| F.02 | Ignore command skips builds without changes under `frontend/` or to `netlify.toml` | `netlify.toml` | DEP-052 | Inspection | **PASS**: `ignore = "git diff --quiet $CACHED_COMMIT_REF $COMMIT_REF -- . ../netlify.toml"` (run from `frontend/`); simulated on this branch: commit `bd60142` (no frontend change) exit 0 = skip, `5575d25` and `4e16094` (frontend changes) exit 1 = build |
| F.03 | No deploy-context environment blocks; no `NEXT_PUBLIC_API_BASE_URL` in the file | `netlify.toml` | TRD 15 §4.6, DEP-054, D-99 | Inspection | **PASS**: no `[context.*]` table and no `NEXT_PUBLIC_API_BASE_URL` string in the file |
| F.04 | Security headers equal TRD 12 §4.9 verbatim (HSTS, nosniff, DENY, no-referrer, Permissions-Policy, CSP with both Render origins) | `netlify.toml` | DEP-053, SEC-062, SEC-070 | Inspection; `node frontend/scripts/check-csp.mjs` | **PASS**: `[[headers]]` block byte-identical to TRD 12 §4.9 (`diff` with lines 219–227 of TRD 12: no difference); `NEXT_PUBLIC_API_BASE_URL=https://echowell-api.onrender.com node frontend/scripts/check-csp.mjs` and `…=https://echowell-backend-production.onrender.com` → exit 0; an unlisted origin, an origin with `/api/v1` and an unset variable → exit 1 |
| F.05 | Build meta `<meta name="echowell-build">` from `COMMIT_REF`/`GIT_SHA` | `frontend/next.config.js`, `frontend/app/layout.tsx` | ENV-033, TRD 16 §4.4 step 3 | Inspection; local run (§3) | **PASS**: `next.config.js` sets `NEXT_PUBLIC_GIT_SHA` from `COMMIT_REF`, else `GIT_SHA`, else `"unknown"`; `app/layout.tsx` renders `other: { "echowell-build": config.gitSha }`; the local wait helper read it (§3) |
| F.06 | No Netlify Functions, Forms, Identity, Blobs, Analytics or Edge Functions | `netlify.toml`, `frontend/` | TPS-010 | Inspection | **PASS**: no `[functions]`, `[[edge_functions]]`, `[[redirects]]` to functions, Forms, Identity, Blobs or Analytics in `netlify.toml`; no `netlify/` directory and no `@netlify/*` runtime dependency in `frontend/` (only the build plugin in devDependencies); `frontend/middleware.ts` is standard Next.js, which TPS-010 allows ("beyond what `@netlify/plugin-nextjs` generates") |

### G. Containers and Compose (TRD 15 §4.2–§4.3)

| ID | Check | Artefact | Source | Method | Result |
|---|---|---|---|---|---|
| G.01 | `backend/Dockerfile` from `python:3.12-slim`, copies `backend/`, `analytics/`, `database/`, `alembic.ini`; installs only `backend/requirements.txt` | `backend/Dockerfile` | DEP-020 | Inspection | **PASS**: `FROM python:3.12-slim`; `COPY alembic.ini`, `analytics/`, `backend/`, `database/`; `pip install -r backend/requirements.txt` only |
| G.02 | Non-root UID 10001; no `.env`, `tests/`, `specs/`, `frontend/` in the image | `backend/Dockerfile`, `.dockerignore` | DEP-021, CIC-023 | `docker-build` job | **PASS**: `USER 10001:10001`; `.dockerignore` excludes `.env`, `.env.*`, `tests`, `specs`, `docs`, `frontend`; the `docker-build` checks run on a local image of this Dockerfile (proxy CA added for the sandbox build only): `id -u` = 10001, `ls -a /app` = `alembic.ini analytics backend database` |
| G.03 | Image default command uvicorn with proxy flags, no migration | `backend/Dockerfile` | DEP-022 | Inspection | **PASS**: `CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]`; no `alembic` in the image command |
| G.04 | `frontend/Dockerfile` multi-stage `node:20-alpine`, build args `NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_APP_ENV` | `frontend/Dockerfile` | DEP-023 | Inspection | **PASS**: stages `deps`, `build`, `runtime`, all `node:20-alpine`; `ARG NEXT_PUBLIC_API_BASE_URL`, `ARG NEXT_PUBLIC_APP_ENV` (plus `GIT_SHA`); runtime runs as `node` |
| G.05 | Compose: `db` `postgres:16-alpine`, `pgdata`, 127.0.0.1 ports, healthcheck; backend after healthy db, `alembic upgrade head` then uvicorn `--reload`; bind mounts incl. `database/` and `tests/fixtures/` read-only; no top-level `version` | `docker-compose.yml` | DEP-010..DEP-013, DEP-019, DEP-119, D-55 | `docker compose config` | **PASS**: `docker compose config -q` exit 0 (with `.env` copied from `.env.development.example`, removed afterwards); `db` `postgres:16-alpine`, volume `pgdata`, ports `127.0.0.1:5432`, `pg_isready` healthcheck; backend `depends_on: db: service_healthy`, `alembic upgrade head && uvicorn … --reload`; `./database` and `./tests/fixtures` mounted `:ro`; no top-level `version` |
| G.06 | `demo` profile `frontend-prod` on 127.0.0.1:3001; only `local-dev-only-*` placeholder secrets | `docker-compose.yml` | DEP-017, DEP-018 | Inspection | **PASS**: `frontend-prod` has `profiles: ["demo"]`, ports `127.0.0.1:3001:3000`; `docker compose --profile demo config --services` lists it; the only credentials are `local-dev-only-*` (`POSTGRES_PASSWORD`, the three role passwords and the three URLs) |

### H. Environment templates and variables (TRD 21)

| ID | Check | Artefact | Source | Method | Result |
|---|---|---|---|---|---|
| H.01 | Three templates exist; real `.env` files untracked | `.env.example`, `.env.development.example`, `.env.production.example` | TRD 21 §4.6, CIC-021 | `git ls-files '.env*'` | **PASS**: `git ls-files '.env*'` → exactly the three templates; `.gitignore` lines 25–26 ignore `.env` and `.env.*` (`git check-ignore -v .env frontend/.env.local`) |
| H.02 | `.env.example` lists every variable of §4.2, §4.3 and the frontend variables; secrets empty | `.env.example` | TRD 21 §4.6, AC-ENV-08 | `tests/unit/backend/core/test_env_templates.py` | **PASS**: `pytest tests/unit/backend/core/test_env_templates.py -q` → 4 passed (every `Settings` field in `.env.example`, templates equal TRD 21); `tests/unit/test_env_templates.py` → 26 passed (secrets empty and commented); frontend variables present |
| H.03 | `.env.development.example` matches TRD 21 §4.6 local values (`local-dev-only-*` placeholders) | `.env.development.example` | ENV-041 | Inspection | **PASS**: `diff` against the TRD 21 §4.6 block: identical; all secrets `local-dev-only-*` |
| H.04 | `.env.production.example`: secrets empty, comments name the source of each value | `.env.production.example` | TRD 21 §4.6 | Inspection | **PASS**: identical to the TRD 21 §4.6 block; every secret value empty; header comments name Render group / web service / Netlify site, per-line comments give staging and production values |
| H.05 | Every TRD 21 variable documented with its per-environment value source | `docs/reports/DEPLOYMENT_CONFIGURATION_GUIDE.md` §7 | TRD 25 Phase 9 DoD, FEAT-087-AC-03 | Script: every variable name of TRD 21 §4.2, §4.3, §4.5 found in the guide | PASS (58 of 58 names found) |

### I. CI and E2E workflows (TRD 16 §4.2, §4.3, §4.7)

| ID | Check | Artefact | Source | Method | Result |
|---|---|---|---|---|---|
| I.01 | `ci.yml` triggers: pull requests, push to `main`, manual dispatch | `ci.yml` | CIC-010 | Inspection | **PASS**: `on: pull_request, push: branches [main], workflow_dispatch` |
| I.02 | Job ids equal the CIC-070 check names `repo-hygiene`, `backend-lint`, `backend-test`, `openapi-contract`, `frontend`, `security-audit`, `docker-build` (`ci.yml`) and `playwright` (`e2e.yml`) | `ci.yml`, `e2e.yml` | CIC-070, TRD 16 §8 | Inspection; must match `REQUIRED_CHECKS` of `deploy-production.yml` | **PASS**: `ci.yml` job ids `repo-hygiene`, `backend-lint`, `backend-test`, `openapi-contract`, `frontend`, `security-audit`, `docker-build`; `e2e.yml` job `playwright`; equal to `REQUIRED_CHECKS` in `deploy-production.yml` (line 76–78). `security-audit` runs `scripts/ci/audit_gate.py pip` and `… npm` with the time-boxed `SECURITY_EXCEPTIONS.md` waivers (D-105, RSK-16) |
| I.03 | **OpenAPI drift check:** `openapi-contract` fails when `python -m backend.cli export-openapi` differs from `docs/api_reference/openapi.json` or `frontend/lib/api-types.ts` is stale | `ci.yml` | CIC-018, D-51, TRD 25 Phase 9 DoD | Inspection | **PASS**: job exports with `python -m backend.cli export-openapi`, fails on `diff -u docs/api_reference/openapi.json`, regenerates `frontend/lib/api-types.ts` with `openapi-typescript@7` and fails on `git diff --exit-code` |
| I.04 | `backend-test` runs unit, integration and validation suites on `postgres:16-alpine` with the coverage gates | `ci.yml` | CIC-012..CIC-016 | Inspection | **PASS**: service `postgres:16-alpine`; provisioning, `alembic upgrade head`, downgrade/upgrade, `alembic check`; one pytest invocation over unit, integration, contract, security, validation; `coverage report --fail-under=95` (`analytics/*`) and `--fail-under=85` (`backend/*`) |
| I.05 | No repository secret in `ci.yml`; JWT secret generated per run | `ci.yml` | CIC-026 | `grep -n "secrets\." .github/workflows/ci.yml` | **PASS**: `grep -n "secrets\." .github/workflows/ci.yml` → nothing; `JWT_SECRET=$(openssl rand -hex 32)` per run |
| I.06 | `e2e.yml` jobs `playwright`, `performance`, `lighthouse`, `nightly-validation`; triggers PR, push `main`, 08:00 UTC nightly, dispatch | `e2e.yml` | CIC-030..CIC-037 | Inspection | **PASS**: jobs `playwright`, `performance`, `nightly-validation`, `lighthouse` (plus `ci-failure-issue`); `on: pull_request (main), push (main), schedule "0 8 * * *", workflow_dispatch`; `performance` and `nightly-validation` only on schedule/dispatch |
| I.07 | All workflows: `ubuntu-24.04`, default `contents: read`, actions pinned per CIC-025, `timeout-minutes` ≤ 20, only the five CIC-002 workflow files | `.github/workflows/*.yml` | CIC-002, CIC-024, CIC-025, CIC-027, CIC-111 | `ls .github/workflows`; inspection | **PASS**: `ls .github/workflows` = the five CIC-002 files; every job `runs-on: ubuntu-24.04` and `timeout-minutes` ≤ 20 (max 20); every workflow `permissions: contents: read` at top level; `uses:` only `actions/*@vN` and `docker/*@vN`. `actionlint` 1.7.12 on all five files: 0 errors; 6 shellcheck SC2086 *info* notes in `e2e.yml` (intended word splitting of `$BROWSERS` and `$DEMO`). That the major tags exist on GitHub is confirmed by the first CI run (Block 4) |

### J. Deploy workflows (TRD 16 §4.4, §4.5, §4.9)

| ID | Check | Artefact | Source | Method | Result |
|---|---|---|---|---|---|
| J.01 | Staging triggers: `push` to `main` and `workflow_dispatch` with boolean `reseed`; concurrency `deploy-staging`, not cancelled | `deploy-staging.yml` | TRD 16 §4.4 | Inspection | PASS |
| J.02 | Polls staging health every 15 s up to 15 min until `version` = pushed SHA; fails otherwise | `deploy-staging.yml`, `tests/smoke/wait_for_deploy.py` | CIC-040, DEP-082, FEAT-086-FR-02 | Inspection; `tests/unit/test_deploy_wait.py`; local run (§3) | PASS |
| J.03 | Waits for `echowell-build` meta, accepting `git log -1 --format=%H -- frontend netlify.toml` when Netlify skipped the build | `deploy-staging.yml`, `wait_for_deploy.py` | TRD 16 §4.4 step 3, §8, FEAT-086-FR-03 | Unit tests; local run against `next dev` | PASS |
| J.04 | Re-seed only when the push changes `backend/alembic/` or `analytics/` or on `reseed: true`; `seed test_v0_1 --reset` then the DS-10 loader | `deploy-staging.yml` | CIC-041, DEP-074, FEAT-086-FR-04, AC-04 | Inspection (`git diff --name-only <before> <sha> -- backend/alembic analytics`) | PASS |
| J.05 | Re-seed variables exactly the ENV-053 operator set (both URLs = `STAGING_DATABASE_URL`, APP_ENV, PIPELINE_PROFILE, PIPELINE_AS_OF, FACILITY_*, SEED_* from `STAGING_SEED_*`); no JWT_SECRET or CORS | `deploy-staging.yml` | ENV-053, FEAT-086-FR-04 | Inspection | PASS |
| J.06 | Smoke step `pytest tests/smoke -m smoke` with SMOKE_ENV=staging and the researcher credentials; job in environment `staging` | `deploy-staging.yml` | CIC-042, CIC-043, FEAT-086-FR-05 | Inspection | PASS |
| J.07 | `smoke-report` artifact (`build/smoke-junit.xml`, 30 days) in both deploy workflows | both | TRD 16 §4.10, FEAT-086-FR-14 | Inspection | PASS |
| J.08 | Production trigger `workflow_dispatch` only, inputs `sha`, `version`, `smoke_only`; concurrency `deploy-production` | `deploy-production.yml` | CIC-053, TRD 16 §4.5 | Inspection | PASS |
| J.09 | Verifies SHA is an ancestor of `origin/main`, version `^v\d+\.\d+\.\d+$`, tag absent | `deploy-production.yml` job `verify` | TRD 16 §4.5 step 1 | Inspection | PASS |
| J.10 | "Wait for CI": all eight CIC-070 check-runs `success` on the SHA and a successful `deploy-staging.yml` run for it; otherwise nothing is deployed | job `verify` (gates `deploy`) | CIC-053, DEP-062, FEAT-086-FR-16, AC-06 | Inspection; jq selection tested on sample data | PASS |
| J.11 | Render API deploy of the SHA for both production service IDs (`POST /v1/services/{id}/deploys`, `commitId`), polled every 15 s until `live`, failing on failure states or 20 min | job `deploy` | TRD 16 §4.5 step 3, DEP-003 | Inspection | PASS |
| J.12 | Netlify CLI `npx netlify-cli@17 deploy --build --prod --site <NETLIFY_PRODUCTION_SITE_ID>` in `frontend/` with `GIT_SHA` | job `deploy` | TRD 16 §4.5 step 4, DEP-002 | Inspection | PASS |
| J.13 | Waits for production `version` and build meta = SHA (15 min); smoke `-m "smoke and not authenticated"` with SMOKE_ENV=production | jobs `wait-for-production`, `smoke` | CIC-051, DEP-081, FEAT-086-FR-08 | Inspection | PASS |
| J.14 | Tag and GitHub Release (`gh release create vX.Y.Z --generate-notes --target $SHA`) only after green smoke tests, only in this workflow; only job with `contents: write` | job `release` | CIC-052, CIC-024, FEAT-086-FR-10, FR-13 | Inspection; `grep -rn "contents: write" .github/workflows` | PASS (full-repository grep: `contents: write` only in `deploy-production.yml` job `release`, line 227) |
| J.15 | Only `RENDER_API_KEY` and `NETLIFY_AUTH_TOKEN` in the production workflow, via `env:`; the Render key reaches `curl` through a header file, never argv; nothing echoed | `deploy-production.yml` | CIC-050, CIC-092, FEAT-086-FR-07 | `grep -n "secrets\." .github/workflows/deploy-production.yml` → 2 lines (see §4, item 1) | PASS |
| J.16 | Lint: `actionlint` 1.7.12 with `shellcheck` | three workflow files | TRD 16 | `actionlint .github/workflows/{uptime,deploy-staging,deploy-production}.yml` | PASS (0 findings) |

### K. Uptime workflow (TRD 16 §4.6, TRD 17 §4.8–§4.9)

| ID | Check | Artefact | Source | Method | Result |
|---|---|---|---|---|---|
| K.01 | `schedule` `*/30 * * * *` and `workflow_dispatch`; no shorter interval | `uptime.yml` | CIC-060, CIC-061, FEAT-085-AC-01 | Inspection | PASS |
| K.02 | `curl --fail --max-time 30` on production and staging `/api/v1/health` and production `/login` | `uptime.yml` | LOG-103, FEAT-085-FR-01, FR-02 | Inspection; local simulation | PASS |
| K.03 | One retry after 60 s; second failure opens or comments on "Uptime check failing" with label `incident` | `uptime.yml` | CIC-060, FEAT-085-FR-03 | Local simulation of the check step (one OK, one twice-failing URL, one unset variable): exit 1, failure list emitted | PASS (issue step itself: Phase 10 negative test, FEAT-085-AC-02) |
| K.04 | No `secrets.`; `contents: read`, `issues: write` only on the job; `timeout-minutes` 10 | `uptime.yml` | CIC-024, CIC-090, FEAT-085-FR-05, AC-03 | `grep -n "secrets\." .github/workflows/uptime.yml` → nothing | PASS |
| K.05 | Issue text has URLs, status codes and timestamps only | `uptime.yml` | TPS-041 | Inspection | PASS |
| K.06 | A URL variable not yet configured is reported as a notice, not as an outage (production created later, D-154) | `uptime.yml` | D-154, RSK-05 | Local simulation | PASS |

### L. Smoke tests (TRD 15 §4.11, TRD 13 TST-006, TST-134, TST-135, TST-152, TST-153)

| ID | Check | Artefact | Source | Method | Result |
|---|---|---|---|---|---|
| L.01 | Staging suite covers DEP-080 (a)–(i); TLS (j) in `test_tls.py` | `tests/smoke/test_staging_smoke.py`, `test_tls.py` | DEP-080, FEAT-086-AC-05 | Inspection | PASS |
| L.02 | Production suite covers DEP-081 (a)–(f); TLS (g) in `test_tls.py`; no `authenticated` marker; read-only | `tests/smoke/test_production_smoke.py` | DEP-081, TST-152, FEAT-086-AC-05 | `grep -n authenticated tests/smoke/test_production_smoke.py` → nothing | PASS |
| L.03 | Every module carries exactly the `smoke` level marker; login tests carry `authenticated` | `tests/smoke/` | TST-006 | `pytest tests/unit/test_markers.py` | PASS |
| L.04 | Skips name a requirement ID (SEC-065, TST-152, DEP-080) | `tests/smoke/` | TST-153 | Inspection; collection hook | PASS |
| L.05 | Local staging-equivalent run against the seeded backend :8000 and `next dev` :3000 | `tests/smoke/` | FEAT-086 Testing Requirements | see §3 | PASS (8 passed, 11 skipped) |
| L.06 | Local production-equivalent run, `-m "smoke and not authenticated"` | `tests/smoke/` | DEP-081 | see §3 | PASS (4 passed, 10 skipped, 5 deselected) |
| L.07 | TLS check refuses TLS 1.1 only when the server refuses it (client offers TLS 1.1 at security level 0; a client unable to offer it fails the test) | `tests/smoke/test_tls.py` | SEC-066 | local TLS servers (TLS 1.2-only refused 1.1; 1.1-capable accepted it) | PASS |
| L.08 | Without `SMOKE_API_BASE_URL` all smoke tests skip, so `pytest -q` stays offline | `tests/smoke/conftest.py` | TST-153 | `pytest tests/smoke -q` → 19 skipped | PASS |

### M. Secrets in GitHub (CIC-090, AC-CIC-06)

| ID | Check | Artefact | Source | Method | Result |
|---|---|---|---|---|---|
| M.01 | `grep -r "secrets\." .github/workflows` lists only the five `STAGING_*` secrets (in `deploy-staging.yml`) and `RENDER_API_KEY`, `NETLIFY_AUTH_TOKEN` (in `deploy-production.yml`) | all workflows | AC-CIC-06, CIC-090 | grep | **PASS**: grep lists exactly `STAGING_DATABASE_URL`, `STAGING_SEED_ADMIN_PASSWORD`, `STAGING_SEED_CLINICIAN_PASSWORD`, `STAGING_SEED_RESEARCHER_PASSWORD`, `STAGING_SEED_INGEST_API_KEY` (`deploy-staging.yml`) and `RENDER_API_KEY`, `NETLIFY_AUTH_TOKEN` (`deploy-production.yml`); none in `ci.yml`, `e2e.yml`, `uptime.yml` (`GITHUB_TOKEN` as `${{ github.token }}`) |
| M.02 | No `pull_request_target` | all workflows | CIC-091 | `grep -rn pull_request_target .github/workflows` | PASS (all five workflow files: no output) |

### N. Sentry (TRD 17 LOG-070, LOG-100..LOG-102, LOG-111; TRD 22 TPS-060, TPS-061)

| ID | Check | Artefact | Source | Method | Result |
|---|---|---|---|---|---|
| N.01 | Empty DSN: no SDK initialisation, zero transport calls on an unhandled exception, ERROR log written | `backend/core/monitoring.py` | LOG-101, FEAT-084-AC-01 | `tests/unit/backend/core/test_monitoring.py` | PASS |
| N.02 | Init options: environment = APP_ENV, release = GIT_SHA, `send_default_pii=False`, `traces_sample_rate=0`, `max_request_body_size="never"`, `before_send` | same | LOG-100, FEAT-084-FR-01 | unit test | PASS |
| N.03 | Captured event has no request body, headers, cookies, query string; `password` and `postgresql://u:p@h/db` credentials redacted | same | LOG-100, SEC-127, FEAT-084-AC-02 | unit test with a captured transport | PASS |
| N.04 | `unhandled_exception` and `nightly_run_missing` reported when enabled; INFO records not reported | same | LOG-070, LOG-111 | unit tests | PASS (wiring into the app lifespan and the nightly job: see §4 item 6) |
| N.05 | Backend only: `@sentry` absent from `frontend/package.json`; enabled only in staging and production | `frontend/package.json`, monitoring module | TPS-060, LOG-102, FEAT-084-AC-03 | `grep -rn "@sentry" frontend/package.json` → nothing; unit test | PASS |
| N.06 | `sentry-sdk` pinned `==` in `backend/requirements.txt`; runbook states the go-live rule and the empty local/test values | `backend/requirements.txt`, `docs/deployment.md` | GIT-112, TPS-061, FEAT-084-AC-04 | Inspection | PASS (`sentry-sdk==2.74.0`) |

### O. Documentation (FEAT-087)

| ID | Check | Artefact | Source | Method | Result |
|---|---|---|---|---|---|
| O.01 | The four FEAT-087 files exist | checklists, guide, this report | AC-AGT-07, FEAT-087-AC-01 | `ls` | PASS |
| O.02 | Guide reproduces TRD 15 §4.2 steps 1–9 and §4.9/§4.10 steps verbatim | guide §2, §8, §9 | FEAT-087-FR-03 | text comparison with TRD 15 | PASS |
| O.03 | `docs/deployment.md`: the five SEC-170 containment actions, 24-hour reporting, SEC-172/SEC-173, SEC-180..SEC-184 | `docs/deployment.md` | FEAT-087-AC-05 | Inspection | PASS |
| O.04 | `docs/deployment.md`: owner, admins, plan, limits and verification date per service; Render instance types and billing recipient; weekly usage check; DEP-102 fallback order; two `incident` watchers | `docs/deployment.md` | FEAT-085-AC-04, AC-05, TPS-006 | Inspection | PASS (values marked "recorded in Phase 10" are filled by FEAT-088) |
| O.05 | Branch-protection settings with the CIC-070 required checks in the guide | guide §6.2 | CIC-070, AC-CIC-08 | Inspection | PASS |
| O.06 | Placeholder grep returns nothing | `specs/backlog`, guide, this report | FEAT-087-AC-06 | `grep -rnE "T[B]D\|T[O]DO\|\[p[l]aceholder\]" specs/backlog docs/reports/DEPLOYMENT_CONFIGURATION_GUIDE.md docs/reports/CONFIGURATION_VALIDATION_REPORT.md` | PASS (no output) |

### P. Phase 9 commands (TRD 25 §4.6 Phase 9)

| ID | Command | Result |
|---|---|---|
| P.01 | `docker compose config` | **PASS**: `cp .env.development.example .env && docker compose config -q` → exit 0; `--profile demo config --services` → `db backend frontend frontend-prod`; `.env` deleted afterwards |
| P.02 | `docker compose up -d && pytest -q` | **PASS**: the Compose `db` and `backend` services came up healthy (and the `demo` profile with `frontend-prod`, P.03); `pytest -q -p randomly` on this branch: 757 passed, 19 skipped (smoke tests need a deployed URL), 16 deselected (performance), 5 Nov 2026 |
| P.03 | `ruff check . && ruff format --check .` and `mypy analytics backend` on the files of FEAT-084..FEAT-087 | PASS |
| P.04 | `pytest tests/unit/backend/core/test_monitoring.py tests/unit/test_deploy_wait.py tests/unit/test_markers.py -q` | PASS (17 passed) |

## 3. Local smoke-test evidence

Run on 5 November 2026 against a local backend (`uvicorn backend.main:app` on `http://localhost:8000`, APP_ENV=local, its own database seeded with `python -m backend.cli seed test_v0_1` and the DS-10 loader, `GIT_SHA` = checkpoint base commit) and `next dev` on `http://localhost:3000`:

| Step | Command | Result |
|---|---|---|
| Wait helper | `python tests/smoke/wait_for_deploy.py --sha <sha> --api-base-url http://localhost:8000/api/v1 --frontend-url http://127.0.0.1:3000 --frontend-sha <sha>` | backend `version` and `echowell-build` meta both = SHA after 2 attempts; exit 0 |
| Staging-equivalent | `SMOKE_ENV=staging SMOKE_API_BASE_URL=http://localhost:8000/api/v1 SMOKE_FRONTEND_URL=http://localhost:3000 SMOKE_EXPECTED_SHA=<sha> SMOKE_USER_EMAIL=researcher@example.com SMOKE_USER_PASSWORD=<local seed value> pytest tests/smoke -m smoke` | 8 passed (DEP-080 a–h), 11 skipped (7 production-suite tests; HSTS, redirect and TLS on `http://`, SEC-065) |
| Production-equivalent | `SMOKE_ENV=production … pytest tests/smoke -m "smoke and not authenticated"` | 4 passed (DEP-081 a, c, d, f), 10 skipped, 5 deselected |
| Offline | `pytest tests/smoke -q` without SMOKE_* | 19 skipped |

The HTTPS-only checks (DEP-080 i–j, DEP-081 b, e, g) run for the first time against the hosted origins in Phase 10 (FEAT-088).

## 4. Findings and TRD contradictions for TRD 24 (AGT-009)

Listed, not resolved in the TRDs (FEAT-087 Out of Scope).

Update 7 Nov 2026 (checkpoint 8 review, GitHub PR #31): findings 1 and 4 are resolved in the TRDs by TRD 24 D-164 and D-166; the approval order behind finding 3 is documented by D-165. See `CHECKPOINT_8_DEPLOYMENT_CONFIG.md` §10.

1. **FEAT-086-AC-03 vs CIC-050 / AC-CIC-06.** FEAT-086-AC-03 says "`grep -n "secrets\." .github/workflows/deploy-production.yml` returns nothing", but TRD 16 §4.5 steps 3–4, CIC-050 and AC-CIC-06 require `deploy-production.yml` to read `secrets.RENDER_API_KEY` and `secrets.NETLIFY_AUTH_TOKEN`. The workflow follows TRD 16 (exactly those two lines); the acceptance criterion should read "lists only `RENDER_API_KEY` and `NETLIFY_AUTH_TOKEN`".
2. **CIC-111 vs TRD 16 §4.5 / §4.4 timeouts.** CIC-111 limits every job to 20 minutes, while §4.5 allows a 20-minute Render poll followed by a Netlify build and two 15-minute waits, and §4.4 allows two 15-minute waits plus re-seed and smoke. Implemented by splitting the work into jobs (`verify`, `deploy`, `wait-for-production`, `smoke`, `release`; `wait-for-staging`, `reseed-and-smoke`) and polling backend and frontend in one loop, so every job is ≤ 20 minutes and every TRD wait keeps its limit (the Render poll's 20 minutes coincide with the `deploy` job limit).
3. **Approval per job.** GitHub asks the `production` reviewer once per job that references the environment; to keep one approval per release, the Render and Netlify steps share the single job `deploy`, and the verification job runs before approval (it holds no secret), so the reviewer sees the CIC-053 result before approving. TRD 15 §4.10 step 4 says the verification happens "after approval"; the order is stricter, not weaker.
4. **Stale tile counts.** TRD 21 ENV-017 and TRD 15 §5 ("Note for lead") still say the seed keeps "tiles 2 / 7 / 1 / 19"; DEP-080 (d) and D-114 use the summary changed 2 / needs_attention 2 / learning 0 / usual 6, which the smoke test asserts and the local run confirmed.
5. **TRD 16 §4.4 step 3 vs §8.** Step 3 says "accept the previous build" when `frontend/` did not change; §8 says compare with the latest commit touching `frontend/` or `netlify.toml`. The wait helper accepts either the pushed SHA or that commit, which satisfies both.
6. **Sentry wiring outside this feature's files.** `init_sentry(settings)` must be called in the app lifespan (`backend/main.py`) and in `backend/jobs/nightly_run.py` `main()` (FEAT-084 Implementation Notes); those files were not changed in this feature's work, so until the two calls are added Sentry stays off everywhere (safe default, LOG-101).
7. **B.02 vs TRD 21 §4.6 / ENV-040.** Check B.02 expects `.env.production.example` to document Neon `aws-us-east-1` as the only database region, but the file is byte-identical to the `.env.production.example` content of TRD 21 §4.6, which names no region, and ENV-040 plus `tests/unit/backend/core/test_env_templates.py` (`test_env_040_templates_match_trd21`) require that identity. Adding a region comment to the template alone would fail that test; either TRD 21 §4.6 and the template gain the comment together, or B.02's artefact column is reduced to the guide §3 and `docs/deployment.md` (both already name `aws-us-east-1`).
8. **TPS-010 / FE-044 vs `@netlify/plugin-nextjs` middleware handling.** `frontend/middleware.ts` (TRD 04 FE-042, sets `Cache-Control` only) is deployed by the Netlify Next.js runtime as an edge function, which may execute outside the US region. TPS-010 permits what the plugin generates and the middleware stores and forwards no data, so B.04 and F.06 pass; TRD 22 §4.2 ("SSR in the default US region") does not mention the edge execution of middleware and could say so.

## 5. Statement

No deployment was performed. No real data source, real-device API key or secret was configured. All checks above used repository files, local processes and synthetic data only.
