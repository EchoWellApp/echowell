# Secrets management and transport security

## Feature Description

FEAT-083 defines how every secret is created, stored, separated and rotated and how every network hop is encrypted (TRD 12 SEC-001..SEC-007, SEC-050..SEC-066, SEC-111, SEC-116, §4.12; TRD 21 ENV-004, ENV-005, ENV-041, ENV-051, ENV-052, AC-ENV-02, AC-ENV-03, AC-ENV-09; TRD 15 DEP-006, DEP-008, DEP-009, DEP-033, DEP-034, DEP-045; TRD 16 CIC-090..CIC-092). Secrets live only in local `.env` (gitignored), Render variables and groups (`sync: false`), the GitHub `staging` environment secrets (`STAGING_DATABASE_URL`, four `STAGING_SEED_*`), the two GitHub `production` deploy tokens (`RENDER_API_KEY`, `NETLIFY_AUTH_TOKEN`) and, on AWS, Secrets Manager. Secret settings are `SecretStr` (masked as `**********`). Each environment has its own JWT_SECRET, API keys, users and role passwords. The backend and CLI refuse to start in staging/production with a database URL lacking `sslmode=require` or with `local-dev-only`/`ci-only` values. All external traffic is HTTPS with TLS 1.2+, checked by `tests/smoke/test_tls.py` together with HSTS. The interim stack holds synthetic and test data only, in US East regions.

## Preconditions

- Repository clone; Python 3.12 with `pip install -r backend/requirements.txt -r backend/requirements-dev.txt`; Docker (gitleaks image and backend image `docker build -f backend/Dockerfile -t echowell-backend:qa .`).
- Local Compose stack for the local token in TC-083-08.
- For **Hosted** cases: the team's `<API_BASE_URL>` (origin plus `/api/v1`) and `<FRONTEND_URL>` for staging and production, exported as `SMOKE_API_BASE_URL`, `SMOKE_FRONTEND_URL`, `SMOKE_ENV`; read-only access to GitHub repository settings, Render and Netlify. Never paste a secret value into a command line or this record; hosted cases only read.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-083-01 | APP_ENV=staging with a DATABASE_URL lacking `sslmode=require` exits 1; APP_ENV=local starts | High | Negative |
| TC-083-02 | APP_ENV=production with the development JWT_SECRET exits 1 and does not log the value | High | Security |
| TC-083-03 | `repr(get_settings())` masks the five secret settings with `**********` | High | Security |
| TC-083-04 | Workflows reference only the allowed GitHub secrets | High | Security |
| TC-083-05 | Hosted: `tests/smoke/test_tls.py` passes (TLS 1.1 refused, TLS 1.2 accepted) | High | Hosted |
| TC-083-06 | `docs/deployment.md` secret inventory with store, owner and rotation interval; gitleaks clean | High | Documentation |
| TC-083-07 | No secret in committed files or `NEXT_PUBLIC_*`; gitleaks full history clean | High | Security |
| TC-083-08 | Hosted: a credential from one environment is rejected in another | High | Hosted |
| TC-083-09 | JWT_SECRET generation length; short secrets refused everywhere | Medium | Negative |
| TC-083-10 | `local-dev-only` / `ci-only` values refused by backend and CLI in staging and production | High | Negative |
| TC-083-11 | Rotation recorded as `config.changed` with `{"rotated": true}` and procedures documented | Medium | Database |
| TC-083-12 | Hosted: HTTPS only, HTTP redirected, HSTS on both origins | High | Hosted |
| TC-083-13 | Encryption at rest and US East regions recorded per provider | Medium | Documentation |
| TC-083-14 | Interim stack holds synthetic data only; DATA_SOURCE_LABEL names the source | Medium | Hosted |
| TC-083-15 | GitHub secret scanning with push protection; fork PRs get no secrets | Low | Hosted |

### TC-083-01 APP_ENV=staging with a DATABASE_URL lacking `sslmode=require` exits 1; APP_ENV=local starts

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest -q tests/unit/backend/core/test_config.py -k sslmode` | `test_staging_requires_sslmode_but_local_does_not` passes. |
| 2 | `docker run --rm --env-file .env.development.example -e APP_ENV=staging -e LOG_FORMAT=json -e JWT_SECRET="$(openssl rand -base64 48)" echowell-backend:qa; echo "exit=$?"` (URLs from the template have no `sslmode`) | `exit=1`; CRITICAL `startup_config_invalid` naming DATABASE_URL (and the other URLs, and the placeholder passwords), never a value. |
| 3 | `docker compose up -d backend` with `.env` from `.env.development.example` (APP_ENV=local, no `sslmode`), then `curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8000/api/v1/health`. | `200` (local starts without `sslmode`). |

### TC-083-02 APP_ENV=production with the development JWT_SECRET exits 1 and does not log the value

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest -q tests/unit/test_env_templates.py -k ac_env_03` and `pytest -q tests/unit/backend/core/test_config.py -k "placeholder or template"` | Pass. |
| 2 | `docker run --rm --env-file .env.development.example -e APP_ENV=production -e PIPELINE_PROFILE=production -e PIPELINE_AS_OF= echowell-backend:qa 2> /tmp/qa-083.log; echo "exit=$?"` | `exit=1`. |
| 3 | `grep -c "JWT_SECRET" /tmp/qa-083.log; grep -c "$(grep '^JWT_SECRET=' .env.development.example | cut -d= -f2)" /tmp/qa-083.log` | First ≥ 1 (variable named); second `0` (value never logged). Delete `/tmp/qa-083.log`. |

### TC-083-03 `repr(get_settings())` masks the five secret settings with `**********`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest -q tests/unit/backend/core/test_config.py -k secrets_masked_in_repr` | Pass. |
| 2 | `set -a; . ./.env.development.example; set +a; SENTRY_DSN=https://k@example.invalid/1 python -c "from backend.core.config import get_settings; print(repr(get_settings()))"` | DATABASE_URL, DATABASE_MIGRATION_URL, DATABASE_READONLY_URL, JWT_SECRET, SENTRY_DSN each shown as `SecretStr('**********')`; no password or DSN text visible. |

### TC-083-04 Workflows reference only the allowed GitHub secrets

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -rn "secrets\." .github/workflows` | Only `secrets.STAGING_DATABASE_URL`, `secrets.STAGING_SEED_ADMIN_PASSWORD`, `secrets.STAGING_SEED_CLINICIAN_PASSWORD`, `secrets.STAGING_SEED_RESEARCHER_PASSWORD`, `secrets.STAGING_SEED_INGEST_API_KEY` (all in `deploy-staging.yml`) and `secrets.RENDER_API_KEY`, `secrets.NETLIFY_AUTH_TOKEN` (in `deploy-production.yml` only). |
| 2 | `grep -rn "github.token\|GITHUB_TOKEN" .github/workflows` | Only the default token (`GH_TOKEN: ${{ github.token }}`) for `gh` calls. |
| 3 | Settings → Environments (read only). | `staging`: the five staging secrets; `production`: `RENDER_API_KEY`, `NETLIFY_AUTH_TOKEN`, required reviewer; no repository-level secrets; no production database URL or JWT secret stored in GitHub. |
| 4 | Inspect how secrets are used in `deploy-staging.yml`. | Passed via `env:`; never `echo`ed. |

### TC-083-05 Hosted: `tests/smoke/test_tls.py` passes (TLS 1.1 refused, TLS 1.2 accepted)

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SMOKE_ENV=staging SMOKE_API_BASE_URL=<API_BASE_URL> SMOKE_FRONTEND_URL=<FRONTEND_URL> pytest -q tests/smoke/test_tls.py` | `test_tls_policy_api` and `test_tls_policy_frontend` pass: TLS 1.1 handshake refused by the server, TLS 1.2 handshake returns `TLSv1.2`. |
| 2 | Repeat with `SMOKE_ENV=production` and the production URLs. | Both pass. |
| 3 | Run against `http://localhost:8000/api/v1` with `SMOKE_ENV=staging`. | Tests skipped with a reason naming SEC-065 (plain HTTP local target). |
| 4 | `openssl s_client -connect <backend host>:443 -tls1_1 < /dev/null` | Handshake fails (cross-check). |

Note: FEAT-083-AC-05 also asks that the test fail when TLS 1.1 is accepted; the repository has no local TLS-1.2-only / TLS-1.1-accepting test endpoint for `tests/smoke/test_tls.py`, so the failing direction can only be checked by code review of `assert_tls_policy` (`tests/smoke/test_tls.py:50`).

### TC-083-06 `docs/deployment.md` secret inventory with store, owner and rotation interval; gitleaks clean

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `docs/deployment.md` and find the secret inventory. | One row per TRD 21 §4.2 secret (JWT_SECRET, DATABASE_URL, DATABASE_MIGRATION_URL, DATABASE_READONLY_URL, SENTRY_DSN, SEED_* values, database role passwords, API keys, deploy tokens) with store, owner and rotation interval (JWT 180 days, role passwords 180 days, device API keys 365 days). |
| 2 | `docker run --rm -v "$PWD:/repo" ghcr.io/gitleaks/gitleaks:v8.18.4 detect --no-git --source /repo/docs/deployment.md --redact --no-banner` | "no leaks found". |

Note: `docs/deployment.md` lists the secret stores (lines 16, 100, 121–127) and JWT/role-password rotation steps (lines 279–280), but no inventory table with owner and rotation interval per secret was found; step 1 is expected to fail until it is added.

### TC-083-07 No secret in committed files or `NEXT_PUBLIC_*`; gitleaks full history clean

| Step | Action | Expected Result |
|---|---|---|
| 1 | `docker run --rm -v "$PWD:/repo" ghcr.io/gitleaks/gitleaks:v8.18.4 detect --source /repo --redact --no-banner` | "no leaks found" (allow-list `.gitleaks.toml`). |
| 2 | `grep -nE "PASSWORD|SECRET|://[^:@/]+:[^@/]+@" docker-compose.yml render.yaml netlify.toml backend/Dockerfile frontend/Dockerfile` | Only `local-dev-only-*` placeholders (Compose) and `sync: false` keys (Blueprint). |
| 3 | `grep -rn "NEXT_PUBLIC_" .env*.example frontend/lib/config.ts` | Only `NEXT_PUBLIC_API_BASE_URL` and `NEXT_PUBLIC_APP_ENV`. |
| 4 | `git check-ignore -v .env` | Ignored by `.gitignore`. |

### TC-083-08 Hosted: a credential from one environment is rejected in another

| Step | Action | Expected Result |
|---|---|---|
| 1 | Obtain a local token: `POST http://localhost:8000/api/v1/auth/login` as `researcher@example.com` with `$SEED_RESEARCHER_PASSWORD` (local). | 200 with `access_token`. |
| 2 | `curl -s -o /dev/null -w '%{http_code}\n' <API_BASE_URL>/residents -H "Authorization: Bearer $LOCAL_TOKEN"` (staging, then production). | `401` on both. |
| 3 | `curl -s -o /dev/null -w '%{http_code}\n' -X POST <API_BASE_URL>/auth/login -H 'Content-Type: application/json' -d '{"email":"admin@example.com","password":"'"$SEED_ADMIN_PASSWORD"'"}'` against production with the local value. | `401` (production has no seeded accounts and refuses SEED_*). Do not repeat more than twice (login rate limit 5/minute). |

### TC-083-09 JWT_SECRET generation length; short secrets refused everywhere

| Step | Action | Expected Result |
|---|---|---|
| 1 | `openssl rand -base64 48 | tr -d '\n' | wc -c` | `64`. |
| 2 | `pytest -q tests/unit/backend/core/test_config.py -k short_jwt_secret` | Pass for every APP_ENV. |

### TC-083-10 `local-dev-only` / `ci-only` values refused by backend and CLI in staging and production

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest -q tests/unit/test_env_templates.py -k "env_041 or local_dev_only"` and `pytest -q tests/unit/backend/core/test_config.py -k placeholder` | Pass. |
| 2 | `docker run --rm --env-file .env.development.example -e APP_ENV=staging -e LOG_FORMAT=json echowell-backend:qa python -m backend.cli export-openapi > /dev/null; echo "exit=$?"` | `exit=1`; message names JWT_SECRET and the database URLs (placeholders `local-dev-only`), no value. |
| 3 | Same with `-e APP_ENV=production`. | `exit=1`. |

### TC-083-11 Rotation recorded as `config.changed` with `{"rotated": true}` and procedures documented

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -n "rotated" backend/services/audit_service.py` | `config.changed` details allow the key `rotated`. |
| 2 | Local: after a recorded rotation (or `set-config` change), `SELECT action, details FROM audit_logs WHERE action = 'config.changed' ORDER BY occurred_at DESC LIMIT 5;` | Rows `config.changed`; a secret rotation row has `details` with the secret name and `"rotated": true` and never the value. |
| 3 | Read "Incident containment" in `docs/deployment.md`. | Steps "Rotate JWT_SECRET" (`openssl rand -base64 48`, every token invalid, users sign in again) and "Rotate database role passwords" (all three roles, update Render variables and `STAGING_DATABASE_URL`, redeploy). |
| 4 | Find the device API key rotation (create new, deploy, revoke old) and the rotation intervals (JWT_SECRET and role passwords 180 days, device API keys 365 days). | Documented with `python -m backend.cli create-api-key` and `revoke-api-key --name N` and the intervals. |

Note: `docs/deployment.md` documents the rotation steps (lines 214, 279–280) but states no 180-day or 365-day interval (SEC-055..SEC-057); step 4 is expected to fail on the intervals until they are added.

### TC-083-12 Hosted: HTTPS only, HTTP redirected, HSTS on both origins

| Step | Action | Expected Result |
|---|---|---|
| 1 | `curl -sI <API_BASE_URL>/health` (staging, production). | `strict-transport-security: max-age=31536000; includeSubDomains`. |
| 2 | `curl -sI <FRONTEND_URL>/login` (staging, production). | Same HSTS header. |
| 3 | `curl -s -o /dev/null -w '%{http_code} %{redirect_url}\n' http://<frontend host>/login` and the same for the backend host. | Redirect to `https://` (301/308); no 200 over HTTP. |
| 4 | `SMOKE_ENV=staging SMOKE_API_BASE_URL=<API_BASE_URL> SMOKE_FRONTEND_URL=<FRONTEND_URL> pytest -q tests/smoke -k hsts_and_https_redirect` | HSTS / HTTPS smoke checks pass. |

### TC-083-13 Encryption at rest and US East regions recorded per provider

| Step | Action | Expected Result |
|---|---|---|
| 1 | Read `docs/deployment.md` line 75 and the Neon and Render sections. | Neon `aws-us-east-1`, Render `ohio` (US East), AWS `us-east-1`; Netlify stores no data. |
| 2 | Find the encryption-at-rest record per provider. | Neon provider-managed encryption (and Render Postgres if used; Render services keep no data); KMS on AWS. |
| 3 | Hosted (read only): Render service settings → Region; Neon project settings → Region. | Ohio; `aws-us-east-1`. |

Note: no per-provider encryption-at-rest statement (SEC-063, DB-052) was found in `docs/deployment.md`; only the backup dump is described as "encrypted at rest" (line 221). Step 2 is expected to fail until it is added.

### TC-083-14 Interim stack holds synthetic data only; DATA_SOURCE_LABEL names the source

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -n "DATA_SOURCE_LABEL" render.yaml .env.production.example` | Staging `pipeline test data v0.1`; production `demo data (synthetic)`. |
| 2 | Open staging `<FRONTEND_URL>`, sign in with the staging researcher account held by the team. | Data bar "Test data only (pipeline test data v0.1, Oct 1–30, 2026). No real residents. No audio is stored or played anywhere in EchoWell."; residents are R01–R10 only. |
| 3 | Read "Hard rules" in `docs/deployment.md`. | First row: the interim Netlify / Render / Neon stack, including `production`, holds synthetic and team-test data only; no real resident data is ever loaded, ingested or connected; go-live only on AWS. Interim API keys are issued only to test devices or harnesses (SEC-004). |

### TC-083-15 GitHub secret scanning with push protection; fork PRs get no secrets

| Step | Action | Expected Result |
|---|---|---|
| 1 | Settings → Code security (read only). | Secret scanning and push protection enabled (where the plan allows). |
| 2 | Inspect `deploy-staging.yml` and `deploy-production.yml` triggers. | No `pull_request_target`; secrets used only in `push`/`workflow_dispatch` jobs on `main`, so fork PRs receive none. |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | Hosted `GET <API_BASE_URL>/residents` with a local token | 401 |
| 2 | Hosted `GET <API_BASE_URL>/health` | 200 with HSTS header |
| 3 | Local `GET http://localhost:8000/api/v1/health` with APP_ENV=local, no `sslmode` | 200 |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT action, details FROM audit_logs WHERE action = 'config.changed';` (local) | Rotation rows carry the secret name and `"rotated": true`, never a value |
| 2 | Local `.env.development.example` URLs vs hosted rule | Local URLs have no `sslmode`; startup accepted only for APP_ENV `local`/`test` |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Staging without `sslmode=require` (TC-083-01) | Exit 1, `startup_config_invalid` |
| 2 | Production with development JWT_SECRET (TC-083-02) | Exit 1, value not logged |
| 3 | CLI with placeholders in staging/production (TC-083-10) | Exit 1 |
| 4 | Local token on hosted API (TC-083-08) | 401 |
| 5 | Plain HTTP (TC-083-12) | Redirect to HTTPS |
| 6 | TLS 1.1 handshake (TC-083-05) | Refused |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-083-AC-01 | APP_ENV=staging with a DATABASE_URL without `sslmode=require` exits 1; APP_ENV=local starts | TC-083-01 |
| FEAT-083-AC-02 | APP_ENV=production with the `.env.development.example` JWT_SECRET exits 1 and the log does not contain the value | TC-083-02 |
| FEAT-083-AC-03 | `repr(get_settings())` shows `**********` for the five secret settings | TC-083-03 |
| FEAT-083-AC-04 | `grep -r "secrets\." .github/workflows` lists only the seven allowed secrets in the named files (plus `GITHUB_TOKEN`) | TC-083-04 |
| FEAT-083-AC-05 | `tests/smoke/test_tls.py` passes against a TLS 1.2-only endpoint and fails when TLS 1.1 is accepted | TC-083-05 |
| FEAT-083-AC-06 | `docs/deployment.md` has the secret inventory with store, owner, rotation interval for every TRD 21 §4.2 secret and no secret value | TC-083-06 |

## Test Data Requirements

- Local `.env.development.example` (placeholders `local-dev-only-*`), local seed users with `SEED_*` passwords for TC-083-08.
- Hosted placeholders `<API_BASE_URL>`, `<FRONTEND_URL>`, `<backend host>`, `<frontend host>`; smoke variables `SMOKE_API_BASE_URL`, `SMOKE_FRONTEND_URL`, `SMOKE_ENV` (and for staging `SMOKE_USER_EMAIL`/`SMOKE_USER_PASSWORD`, held by the team).
- Dummy DSN `https://k@example.invalid/1` (not a real project).
- Secret names only: JWT_SECRET, DATABASE_URL, DATABASE_MIGRATION_URL, DATABASE_READONLY_URL, SENTRY_DSN, STAGING_DATABASE_URL, STAGING_SEED_*, RENDER_API_KEY, NETLIFY_AUTH_TOKEN.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-083-FR-01 / SEC-050, ENV-005, AGT-016 | FEAT-083 | TC-083-07, TC-083-04 |
| FEAT-083-FR-02 / ENV-004, AC-ENV-09 | FEAT-083 | TC-083-03 |
| FEAT-083-FR-03 / SEC-054 | FEAT-083 | TC-083-07 |
| FEAT-083-FR-04 / DEP-006, ENV-051, SEC-056 | FEAT-083 | TC-083-08 |
| FEAT-083-FR-05 / SEC-055, ENV-052 | FEAT-083 | TC-083-09, TC-083-11 |
| FEAT-083-FR-06 / SEC-056, RSK-15 | FEAT-083 | TC-083-11 |
| FEAT-083-FR-07 / SEC-057 | FEAT-083 | TC-083-11 |
| FEAT-083-FR-08 / SEC-058, TRD 12 §4.12 | FEAT-083 | TC-083-11 |
| FEAT-083-FR-09 / CIC-090, CIC-091, CIC-092, DEP-033 | FEAT-083 | TC-083-04, TC-083-15 |
| FEAT-083-FR-10 / SEC-060, SEC-064, DEP-009 | FEAT-083 | TC-083-12 |
| FEAT-083-FR-11 / SEC-061, DEP-034, DB-053, AC-ENV-02 | FEAT-083 | TC-083-01 |
| FEAT-083-FR-12 / ENV-041, AC-ENV-03 | FEAT-083 | TC-083-02, TC-083-10 |
| FEAT-083-FR-13 / SEC-066, SEC-062, DEP-045 | FEAT-083 | TC-083-05, TC-083-12 |
| FEAT-083-FR-14 / SEC-063, DB-052, PGS-039 | FEAT-083 | TC-083-13 |
| FEAT-083-FR-15 / SEC-001, SEC-003, SEC-004, DEP-008, AGT-014 | FEAT-083 | TC-083-14 |
| FEAT-083-FR-16 / SEC-007 | FEAT-083 | TC-083-13 |
| FEAT-083-FR-17 / SEC-053 | FEAT-083 | TC-083-15 |
