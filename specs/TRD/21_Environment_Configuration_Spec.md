# 21 Environment Configuration Specification

Document ID: ECHOWELL-TRD-21 · Version 0.1 (draft for review) · Date: 18 October 2026 · Owner: Team 2 · Status: Draft

## 1. Purpose

This document is the single authoritative list of EchoWell environment variables: for each variable its meaning,
whether it is required, its default, an example, the environments it applies to, whether it is secret, and how it is
validated at startup. It also defines the content of the environment template files, the boundary between
environment configuration and the algorithm parameters stored in the database (`config_parameters`), the public
frontend variables, and the per-environment value matrix for local, staging, production (current interim stack) and
the AWS target.

## 2. Scope

**In scope**

- Backend variables (contract §13) plus the additional variables defined here (§4.3), validated with pydantic-settings.
- Frontend build-time public variables (`NEXT_PUBLIC_*`).
- Docker Compose-only, CI-only and smoke/E2E-test-only variables.
- Template files `.env.example`, `.env.development.example`, `.env.production.example`.
- Per-environment matrix and where each value is stored (Railway, Netlify, GitHub, AWS Secrets Manager).

**Out of scope**

- Algorithm parameter values (TRD 07/TRD 08/TRD 09; contract §7) — referenced only to define the boundary.
- Secret generation and rotation policy beyond what is needed here (TRD 12).

## 3. References

| ID | Reference |
|---|---|
| SRC-01 | Deployment Architecture ("environment variable management" on Netlify; Railway configuration) |
| SRC-03 | Workbook Parameters sheet (`production` vs `test_v0_1` profile values) |
| D-OWNER-2 | `test_v0_1` profile is for build-out and testing only; refused in production |
| D-OWNER-3 / D-OWNER-4 | Encryption in transit (sslmode=require), AWS target, interim stack synthetic data only |
| TRD 12 | Security (JWT, CORS, rate limits, secrets storage) |
| TRD 15 | Deployment and DevOps (where variables are set, per platform) |
| TRD 16 | CI/CD (CI and smoke-test variables, GitHub secrets/variables) |
| TRD 17 | Logging (LOG_LEVEL, LOG_FORMAT, SENTRY_DSN, GIT_SHA) |
| TRD 22 | Third-party services (Sentry, platforms) |

## 4. Requirements

### 4.1 General rules

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| ENV-001 | All backend configuration shall be read through one `Settings` class (pydantic-settings 2.x `BaseSettings`) in `backend/core/config.py`, instantiated once at startup and injected via a cached `get_settings()` dependency; no other module shall read `os.environ` directly. | Must | TRD 01 | Inspection |
| ENV-002 | Settings validation shall run before the application accepts traffic and before Alembic migrations run; on any validation failure the process shall exit with code 1 and log one CRITICAL `startup_config_invalid` record listing the invalid variable names and the rule violated, never their values (TRD 17 LOG-072). | Must | TRD 17 | Test |
| ENV-003 | Variable names shall be upper-case and exactly as listed in this TRD; unknown variables beginning with `ECHOWELL_` shall be rejected (typo protection) and other unknown variables ignored. | Should | contract §13 | Test |
| ENV-004 | Secret variables (marked "secret" in §4.2) shall be typed `pydantic.SecretStr` so they are masked in `repr()`, logs and error messages. | Must | BR-16, TRD 17 LOG-020 | Test |
| ENV-005 | Secrets shall be stored only in: local `.env` (gitignored, local values only), Railway service variables (interim staging/production), GitHub Actions `staging` environment secrets (TRD 16 §4.9), and AWS Secrets Manager (AWS target). They shall never be set in `netlify.toml`, `railway.toml`, Dockerfiles, `docker-compose.yml` or any committed file. | Must | BR-16, contract §12 | Inspection |
| ENV-006 | A `.env` file shall be loaded only when APP_ENV is `local` or `test`; in `staging` and `production` the backend shall read only real process environment variables. | Must | BR-16 | Test |

### 4.2 Backend variables (contract §13)

| Variable | Description | Required | Default | Example | Envs | Secret | Validation |
|---|---|---|---|---|---|---|---|
| `APP_ENV` | Deployment environment name | Yes | — | `staging` | all | No | one of `local`, `staging`, `production`, `test` |
| `DATABASE_URL` | Runtime DB connection (role `echowell_app`; Neon pooled endpoint) | Yes | — | `postgresql+psycopg://echowell_app:****@ep-xyz-pooler.us-east-1.aws.neon.tech/echowell?sslmode=require` | all | Yes | scheme `postgres`, `postgresql`, `postgresql+psycopg` (normalised to `postgresql+psycopg`); must contain `sslmode=require` (or `verify-full`) when APP_ENV is `staging` or `production` |
| `JWT_SECRET` | HS256 signing key for access tokens | Yes | — | 64 hex chars from `openssl rand -hex 32` | all | Yes | ≥ 32 bytes; in `staging`/`production` must not equal any value present in a committed template and must contain ≥ 16 distinct characters |
| `JWT_EXPIRES_MINUTES` | Access token lifetime | No | `60` | `60` | all | No | integer 5–1440 |
| `CORS_ORIGINS` | Allowed browser origins, comma-separated | Yes in staging/production | `http://localhost:3000,http://localhost:3001` (local/test only) | `https://echowell-und.netlify.app` | all | No | each item a valid origin without path; `*` forbidden; `http://` allowed only for `localhost` origins and only when APP_ENV is `local` or `test` |
| `FACILITY_NAME` | Facility display name in header subline | Yes in staging/production | `Edgewood` | `Edgewood` | all | No | 1–80 chars; must not contain `Edge4Care` (RSK-10) |
| `FACILITY_TZ` | Facility IANA time zone (bootstrap facility row, scheduler) | No | `America/Chicago` | `America/Chicago` | all | No | valid `zoneinfo.ZoneInfo` key |
| `PIPELINE_PROFILE` | Name of `config_parameters` profile used by pipeline runs | No | `production` | `test_v0_1` | all | No | one of `production`, `test_v0_1`; `test_v0_1` refused when APP_ENV=`production` |
| `NIGHTLY_RUN_HOUR_LOCAL` | Hour (facility local) of the full nightly run | No | `2` | `2` | all | No | integer 0–23 |
| `LOG_LEVEL` | Minimum log level | No | `INFO` | `INFO` | all | No | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `LOG_FORMAT` | Log output format | No | `json` | `json` | all | No | `json` or `console`; `console` refused in `staging`/`production` |
| `SENTRY_DSN` | Sentry project DSN; empty disables Sentry | No | empty | `https://****@o0.ingest.us.sentry.io/0` | staging, production | Yes | empty or https URL |
| `RATE_LIMIT_LOGIN` | Login rate limit per client IP | No | `5/minute` | `5/minute` | all | No | `<int>/<second|minute|hour|day>` |
| `RATE_LIMIT_INGEST` | Ingest rate limit per API key | No | `600/minute` | `600/minute` | all | No | same format |
| `GIT_SHA` | Deployed commit SHA, reported as `version` by health | No | `unknown` | `3f9c2ab…` (40 hex) | all | No | `unknown` or 7–40 hex chars; set by platform (Railway: `${{RAILWAY_GIT_COMMIT_SHA}}`; Compose: `git rev-parse HEAD` via `.env`; App Runner: image build arg) |
| `DATA_SOURCE_LABEL` | Text shown in header "Showing <label> as of …" | No | `pipeline test data v0.1` | `demo data (synthetic)` | all | No | 1–60 chars |

### 4.3 Additional backend variables defined by this TRD

| Variable | Description | Required | Default | Example | Envs | Secret | Validation |
|---|---|---|---|---|---|---|---|
| `DATABASE_MIGRATION_URL` | Connection used by Alembic only (role `echowell_owner`, direct non-pooled endpoint) | No | value of DATABASE_URL | `postgresql+psycopg://echowell_owner:****@ep-xyz.us-east-1.aws.neon.tech/echowell?sslmode=require` | staging, production, AWS | Yes | same rules as DATABASE_URL |
| `CORS_ORIGIN_REGEX` | Additional allowed-origin regex for Netlify deploy previews | No | empty | `^https://deploy-preview-\d+--echowell-und\.netlify\.app$` | staging only | No | must compile; must start with `^https://` and end with `$`; refused (non-empty) when APP_ENV=`production` |
| `PIPELINE_AS_OF` | Fixed "now" for pipeline as-of, day ledger, 30-day windows and header time; empty = current time | No | empty | `2026-10-30T15:00:00-05:00` | local, staging, test | No | ISO 8601 with offset; refused (non-empty) when APP_ENV=`production` |
| `NIGHTLY_SCHEDULER_ENABLED` | Starts the in-process nightly scheduler and 06:00 watchdog (TRD 17 LOG-110/111) | No | `true` (`false` when APP_ENV=`test`) | `false` | all | No | boolean; set `false` on AWS where EventBridge triggers runs (TRD 15 DEP-116) |
| `PORT` | Listening port | No | `8000` | `8000` | all | No | integer 1–65535; injected by Railway/App Runner |

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| ENV-010 | With APP_ENV=`production`, startup shall fail if PIPELINE_PROFILE is `test_v0_1`. | Must | D-OWNER-2, ASM-04 | Test |
| ENV-011 | With APP_ENV=`staging` or `production`, startup shall fail if DATABASE_URL or DATABASE_MIGRATION_URL lacks `sslmode=require` or `sslmode=verify-full`. | Must | D-OWNER-3, TRD 12 | Test |
| ENV-012 | With APP_ENV=`production`, startup shall fail if PIPELINE_AS_OF or CORS_ORIGIN_REGEX is non-empty, if LOG_FORMAT is `console`, or if any CORS origin uses `http://`; when LOG_LEVEL is `DEBUG` in staging or production the backend shall log WARNING `debug_logging_enabled` at startup and every hour (time-boxed use, TRD 17 LOG-012). | Must | BR-16, TRD 17 | Test |
| ENV-013 | JWT_SECRET shall be rejected if shorter than 32 bytes in every environment, including `test`. | Must | contract §12 | Test |
| ENV-014 | DATABASE_URL values starting `postgres://` or `postgresql://` shall be normalised to `postgresql+psycopg://` before engine creation, preserving all query parameters. | Must | TRD 15 | Test |
| ENV-015 | FACILITY_NAME shall be rejected if it contains the string `Edge4Care` (case-insensitive). | Must | RSK-10, contract §2 | Test |
| ENV-016 | The backend shall expose FACILITY_NAME (`meta.facility_name`), FACILITY_TZ (`meta.facility_tz`), DATA_SOURCE_LABEL (`meta.data_source_label`), the effective as-of (`meta.as_of`), `meta.baseline_n`, `meta.cusum_h` and `meta.pipeline_profile` in the `meta` object of every list/detail/analytics response (contract R3, TRD 05), never through frontend build variables. | Must | contract §11 header subline | Test |
| ENV-017 | As-of resolution (contract R11): an explicit `as_of` in `POST /api/v1/pipeline/run` (or the seed command) wins; otherwise PIPELINE_AS_OF when set (local/staging/test only); otherwise the request/run time (always the case in production). With PIPELINE_AS_OF set, nightly and ingest-triggered runs, the day ledger, 30-day windows and `meta.as_of` use it, so the `test_v0_1` seed keeps tiles 2 / 7 / 1 / 19 indefinitely in local and staging. | Must | BR-15, SRC-03, TRD 15 DEP-016 | Test |
| ENV-018 | GIT_SHA shall appear as `version` in `/api/v1/health`, in every log record (TRD 17) and in `pipeline_runs.code_version`. | Must | TRD 17, contract §9 | Test |

### 4.4 Config parameters (database) vs environment

| Concern | Where | Changed by |
|---|---|---|
| Which parameter profile is active | env `PIPELINE_PROFILE` | deployment (Railway variable / `.env`) |
| Algorithm and alerting parameter values (`baseline_n`, `noise_limit_dbfs`, `cusum_k`, `cusum_h`, `morning_offsets`, `facility_tz`, `data_alert_set_aside_fraction`, `data_alert_device_silent_days`, `data_alert_baseline_stalled_enabled`, `alert_snooze_hours`, `review_explanations`, …) | table `config_parameters` (profile, key) | admin via config change (audited, TRD 12); initial rows by `backend.cli bootstrap` (TRD 15 §4.8) |
| Parameter snapshot used by a run | `pipeline_runs.config_snapshot` | pipeline (immutable record) |
| Facility name, time zone for scheduler | env `FACILITY_NAME`, `FACILITY_TZ` | deployment |
| Secrets, URLs, logging, rate limits | env | deployment |

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| ENV-020 | Algorithm, data-alert and review parameters (including the contract §19 keys `data_alert_*`, `alert_snooze_hours`, `review_explanations`) shall never be read from environment variables; the only algorithm-related environment variables are PIPELINE_PROFILE and PIPELINE_AS_OF (test as-of). | Must | contract §7, BR-15 | Inspection |
| ENV-021 | At startup the backend shall verify that the profile named by PIPELINE_PROFILE exists in `config_parameters` with all keys of contract §7; if not, `/api/v1/health` shall still return 200 but every pipeline run shall fail with `pipeline_config_invalid` (TRD 17) until `bootstrap` is run. | Must | TRD 17 | Test |
| ENV-022 | If FACILITY_TZ differs from the active profile's `facility_tz`, the backend shall log WARNING `config_mismatch` at startup and add a `config_mismatch` warning to each pipeline run; the pipeline shall use the profile value. | Must | ASM-01, TRD 17 LOG-064 | Test |

### 4.5 Frontend, Compose, CI and test-harness variables

Frontend variables are inlined at build time by Next.js and are therefore **public**: never put a secret in a `NEXT_PUBLIC_*` variable.

| Variable | Description | Required | Default | Example | Envs | Secret | Validation |
|---|---|---|---|---|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | Backend base URL including `/api/v1` | Yes | — | `https://echowell-backend-production.up.railway.app/api/v1` | all | No | absolute URL ending in `/api/v1`; `https://` required unless host is `localhost` |
| `NEXT_PUBLIC_APP_ENV` | Environment label (shows a "STAGING" / "LOCAL" ribbon when not `production`) | Yes | — | `production` | all | No | `local`, `staging`, `production` |
| `NEXT_PUBLIC_GIT_SHA` | Build commit, rendered as `<meta name="echowell-build">` (TRD 16 §4.4) | No (derived) | `process.env.COMMIT_REF` (Netlify) or `process.env.GIT_SHA` or `unknown`, computed in `next.config.js` | `3f9c2ab…` | all | No | never set manually |
| `NEXT_TELEMETRY_DISABLED` | Disable Next.js telemetry | No | `1` | `1` | all | No | — |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Compose `db` container init | Compose only | `echowell` / `echowell` / `echowell` | — | local | local-only | — |
| `SMOKE_API_BASE_URL`, `SMOKE_FRONTEND_URL`, `SMOKE_EXPECTED_SHA`, `SMOKE_ENV` | Smoke test targets (TRD 15 §4.11) | smoke runs | — | `https://…/api/v1` | CI | No | `SMOKE_ENV` ∈ `staging`, `production` |
| `SMOKE_USER_EMAIL`, `SMOKE_USER_PASSWORD` | Staging smoke user | staging smoke | — | — | CI (staging) | Yes | never set for production |
| `E2E_BASE_URL`, `E2E_USER_EMAIL`, `E2E_USER_PASSWORD` | Playwright targets (TRD 16 §4.3) | E2E runs | `http://localhost:3001` | — | CI, local | ephemeral | — |

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| ENV-030 | The frontend shall read NEXT_PUBLIC_API_BASE_URL and NEXT_PUBLIC_APP_ENV only in `frontend/lib/config.ts`, which shall throw at build time if either is missing or invalid. | Must | TRD 04 | Test |
| ENV-031 | No `NEXT_PUBLIC_*` variable shall contain a secret, a database URL or a facility-specific value other than the API URL. | Must | BR-16 | Inspection |
| ENV-032 | The frontend shall show a non-dismissable ribbon "STAGING – synthetic data" when NEXT_PUBLIC_APP_ENV=`staging` and "LOCAL" when `local`. | Should | BR-16, D-OWNER-4 | Test |
| ENV-033 | `next.config.js` shall set `env.NEXT_PUBLIC_GIT_SHA` from `COMMIT_REF` (Netlify), else `GIT_SHA`, else `unknown`. | Must | TRD 16 | Test |

### 4.6 Template files

Three committed templates; real `.env` files are gitignored (TRD 18 §4.11).

| File | Purpose |
|---|---|
| `.env.example` | Complete reference: every variable of §4.2, §4.3 and the frontend variables, each with a one-line comment; secrets empty. |
| `.env.development.example` | Ready-to-copy local values for Docker Compose (`cp .env.development.example .env`). |
| `.env.production.example` | Checklist of keys to set in Railway / Netlify / AWS for staging and production; secrets empty; comments state where each value comes from. Never filled in the repository. |

`.env.development.example` content:

```dotenv
# Local development (docker compose). Copy to .env. Local-only values; never reuse elsewhere.
APP_ENV=local
DATABASE_URL=postgresql+psycopg://echowell:echowell@db:5432/echowell
JWT_SECRET=local-dev-only-0123456789abcdef0123456789abcdef
JWT_EXPIRES_MINUTES=60
CORS_ORIGINS=http://localhost:3000,http://localhost:3001
FACILITY_NAME=Edgewood
FACILITY_TZ=America/Chicago
PIPELINE_PROFILE=test_v0_1
PIPELINE_AS_OF=2026-10-30T15:00:00-05:00
NIGHTLY_RUN_HOUR_LOCAL=2
NIGHTLY_SCHEDULER_ENABLED=true
LOG_LEVEL=INFO
LOG_FORMAT=console
SENTRY_DSN=
RATE_LIMIT_LOGIN=5/minute
RATE_LIMIT_INGEST=600/minute
GIT_SHA=unknown
DATA_SOURCE_LABEL=pipeline test data v0.1
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_APP_ENV=local
NEXT_TELEMETRY_DISABLED=1
```

`.env.production.example` content:

```dotenv
# Staging/production keys. Set values in Railway (backend) and Netlify (frontend) UIs,
# or AWS Secrets Manager / App Runner / Amplify on the AWS target. NEVER commit values.
# --- Backend (Railway service variables) ---
APP_ENV=production                 # staging for the staging environment
DATABASE_URL=                      # secret: Neon pooled URL, role echowell_app, must include sslmode=require
DATABASE_MIGRATION_URL=            # secret: Neon direct URL, role echowell_owner, must include sslmode=require
JWT_SECRET=                        # secret: openssl rand -hex 32 (different per environment)
JWT_EXPIRES_MINUTES=60
CORS_ORIGINS=                      # e.g. https://echowell-und.netlify.app (staging: https://staging--echowell-und.netlify.app)
CORS_ORIGIN_REGEX=                 # staging only: ^https://deploy-preview-\d+--echowell-und\.netlify\.app$ ; empty in production
FACILITY_NAME=Edgewood
FACILITY_TZ=America/Chicago
PIPELINE_PROFILE=production        # staging: test_v0_1 ; production: production (test_v0_1 refused)
PIPELINE_AS_OF=                    # staging: 2026-10-30T15:00:00-05:00 ; production: must be empty
NIGHTLY_RUN_HOUR_LOCAL=2
NIGHTLY_SCHEDULER_ENABLED=true     # false on AWS App Runner
LOG_LEVEL=INFO
LOG_FORMAT=json
SENTRY_DSN=                        # optional secret; empty disables Sentry
RATE_LIMIT_LOGIN=5/minute
RATE_LIMIT_INGEST=600/minute
GIT_SHA=${{RAILWAY_GIT_COMMIT_SHA}} # Railway reference variable
DATA_SOURCE_LABEL=demo data (synthetic)
# --- Frontend (Netlify environment variables, per deploy context) ---
NEXT_PUBLIC_API_BASE_URL=          # production: https://<railway production domain>/api/v1
NEXT_PUBLIC_APP_ENV=production
```

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| ENV-040 | The three template files shall exist at the repository root with the content above (`.env.example` being the union of all variables with comments) and shall be kept in sync with this TRD; a unit test shall assert that every field of `Settings` appears in `.env.example`. | Must | SRC-17 Phase 14A | Test |
| ENV-041 | `JWT_SECRET` in `.env.development.example` shall contain the substring `local-dev-only` and the backend shall refuse any JWT_SECRET containing `local-dev-only` when APP_ENV is `staging` or `production`. | Must | BR-16 | Test |

### 4.7 Per-environment matrix

| Variable | local (Compose) | test (CI) | staging (Railway/Netlify) | production — current interim (Railway/Netlify) | production — AWS target |
|---|---|---|---|---|---|
| APP_ENV | `local` | `test` | `staging` | `production` | `production` |
| DATABASE_URL | Compose `db` | CI service `localhost:5432/echowell_test` | Neon `staging` pooled, app role | Neon `main` pooled, app role | RDS endpoint, app role, `sslmode=require` (Secrets Manager) |
| DATABASE_MIGRATION_URL | unset (= DATABASE_URL) | unset | Neon `staging` direct, owner role | Neon `main` direct, owner role | RDS, owner role (Secrets Manager) |
| JWT_SECRET | local-dev-only value | generated per run | unique secret | unique secret | unique secret (Secrets Manager) |
| CORS_ORIGINS | `http://localhost:3000,http://localhost:3001` | `http://localhost:3000` | `https://staging--echowell-und.netlify.app` | `https://echowell-und.netlify.app` | Amplify production domain |
| CORS_ORIGIN_REGEX | empty | empty | deploy-preview regex | empty | empty |
| FACILITY_NAME | `Edgewood` | `Edgewood` | `Edgewood` | `Edgewood` | `Edgewood` |
| FACILITY_TZ | `America/Chicago` | `America/Chicago` | `America/Chicago` | `America/Chicago` | `America/Chicago` |
| PIPELINE_PROFILE | `test_v0_1` | `test_v0_1` | `test_v0_1` | `production` | `production` |
| PIPELINE_AS_OF | `2026-10-30T15:00:00-05:00` | set per test | `2026-10-30T15:00:00-05:00` | empty | empty |
| NIGHTLY_SCHEDULER_ENABLED | `true` | `false` | `true` | `true` | `false` |
| LOG_FORMAT / LOG_LEVEL | `console` / `INFO` | `json` / `INFO` | `json` / `INFO` | `json` / `INFO` | `json` / `INFO` |
| SENTRY_DSN | empty | empty | optional | optional (synthetic data only) | optional, re-approved (TRD 22) |
| GIT_SHA | `unknown` | `${{ github.sha }}` | Railway reference | Railway reference | image build arg |
| DATA_SOURCE_LABEL | `pipeline test data v0.1` | `pipeline test data v0.1` | `pipeline test data v0.1` | `demo data (synthetic)` | `Edgewood check-ins` |
| NEXT_PUBLIC_API_BASE_URL | `http://localhost:8000/api/v1` | `http://localhost:8000/api/v1` | staging backend | production backend | App Runner domain |
| NEXT_PUBLIC_APP_ENV | `local` | `local` | `staging` | `production` | `production` |

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| ENV-050 | Each environment shall be configured exactly per the matrix in §4.7; deviations shall be recorded in `docs/deployment.md` with a reason. | Must | TRD 15 | Inspection |
| ENV-051 | JWT_SECRET and API keys shall differ between every pair of environments (TRD 15 DEP-006). | Must | BR-16 | Test |
| ENV-052 | Rotating JWT_SECRET shall be possible by changing the variable and redeploying; all existing tokens become invalid and users re-login (no refresh tokens, contract §12). | Must | TRD 12 | Demo |

## 5. Assumptions

- ASM-01 Facility timezone America/Chicago (default FACILITY_TZ).
- ASM-03 Single facility (Edgewood): one FACILITY_NAME per deployment.
- ASM-04 Test profile baseline_n=16, production 30 — selected via PIPELINE_PROFILE.
- D-OWNER-4 Interim production holds synthetic/test data only; hence DATA_SOURCE_LABEL `demo data (synthetic)` until AWS go-live.

## 6. Dependencies

- pydantic 2.x and pydantic-settings 2.x (`backend/requirements.txt`).
- `config_parameters` table and `backend.cli bootstrap` (TRD 06, TRD 15).
- Platform variable stores: Railway, Netlify, GitHub Actions environments, AWS Secrets Manager (TRD 22).
- API field(s) delivering facility name, data source label and as-of to the frontend (TRD 05 / TRD 19).

## 7. Acceptance Criteria

- AC-ENV-01 Starting the backend with APP_ENV=production and PIPELINE_PROFILE=test_v0_1 exits with code 1 and a CRITICAL log naming PIPELINE_PROFILE.
- AC-ENV-02 Starting with APP_ENV=staging and a DATABASE_URL without `sslmode=require` exits with code 1; with APP_ENV=local it starts.
- AC-ENV-03 Starting with APP_ENV=production and JWT_SECRET from `.env.development.example` exits with code 1; the log does not contain the secret value.
- AC-ENV-04 A JWT_SECRET of 31 bytes is rejected in every APP_ENV.
- AC-ENV-05 `DATABASE_URL=postgres://u:p@h/db?sslmode=require` yields an engine URL `postgresql+psycopg://u:p@h/db?sslmode=require`.
- AC-ENV-06 With APP_ENV=production and PIPELINE_AS_OF set, startup fails; with APP_ENV=staging and PIPELINE_AS_OF=2026-10-30T15:00:00-05:00 the residents summary returns tiles 2 / 7 / 1 / 19 on any calendar date.
- AC-ENV-07 FACILITY_NAME=`Edge4Care` is rejected.
- AC-ENV-08 The unit test comparing `Settings` fields with `.env.example` passes; `frontend` build fails when NEXT_PUBLIC_API_BASE_URL is unset.
- AC-ENV-09 `repr(get_settings())` shows `**********` for DATABASE_URL, DATABASE_MIGRATION_URL, JWT_SECRET and SENTRY_DSN.

## 8. Implementation Notes

- `Settings` uses `model_config = SettingsConfigDict(env_file=".env" if APP_ENV in {"local","test"} else None, extra="ignore", case_sensitive=True)`; read APP_ENV first from `os.environ` in the factory to decide on `env_file` (the single allowed direct read, inside `backend/core/config.py`).
- Implement cross-field rules (ENV-010 to ENV-012, ENV-041) in a `@model_validator(mode="after")`.
- Parse `CORS_ORIGINS` with a `field_validator(mode="before")` splitting on commas and stripping spaces; pydantic-settings otherwise expects JSON for list types.
- Alembic `env.py` must import `get_settings()` and use `DATABASE_MIGRATION_URL or DATABASE_URL`, so the same validation applies to migrations.
- For psycopg 3 behind the Neon pooler pass `connect_args={"prepare_threshold": None}` (TRD 15 Implementation Notes).
- Do not log the `Settings` object; log only a startup summary (`env`, `version`, `pipeline_profile`, `facility_tz`, `sentry_enabled` boolean, `as_of_fixed` boolean).
- Next.js inlines `NEXT_PUBLIC_*` at build time: changing them on Netlify requires a rebuild ("Clear cache and deploy").

## 9. Open Questions

- OQ-07 AWS budget approval timing and account ownership — determines when the AWS column of §4.7 becomes active.
- OQ-13 Alarm-limit calibration — future changes to `cusum_h`/`cusum_k` are `config_parameters` changes, never environment changes.
- OQ-12 Final clinical wording — wording strings live in `frontend/lib/wording.ts` with `CLINICAL_WORDING_APPROVED=false` (a source constant, contract R14), not an environment variable.
- OQ-24 / OQ-25 Data-alert thresholds and review explanation list — `config_parameters` values, changed without redeploy.

## Revision History

| Version | Date | Description | Author |
|---|---|---|---|
| 0.1 | 18 Oct 2026 | Initial generation from TRD_Generation_Prompt.md | — |
