# 12 Security and Authentication Spec

Document ID: ECHOWELL-TRD-12 · Version 0.1 (draft for review) · Date: 18 October 2026 · Owner: Team 2 · Status: Draft

## 1. Purpose

This document specifies how EchoWell protects research data and controls access: threat model,
authentication of dashboard users (JWT) and devices (API keys), role-based authorisation for every endpoint,
password policy, session expiry, secrets management, transport and storage encryption, browser security
headers, input validation, rate limiting, audit logging, database least privilege, privacy and data
minimisation, dependency scanning, backups, incident response and research data governance.

EchoWell handles acoustic feature values extracted from residents' speech. Live feature data is treated as
sensitive and potentially PHI-derived (owner decision D-OWNER-3). EchoWell never receives audio and stores
no personally identifying information about residents: residents are known only by study IDs.

## 2. Scope

In scope: the FastAPI backend (Railway now, AWS App Runner target), the Next.js frontend (Netlify now, AWS
Amplify target), the PostgreSQL database (Neon now, AWS RDS target), GitHub repository and Actions, the admin
CLI, and operational security procedures run by Team 2.

Out of scope: device hardware security, on-device audio handling, wake word and device-to-cloud transport
security beyond the API contract (Team 1; ASM-05, OQ-16); UND institutional policies themselves (referenced,
not defined); the offline mixed-effects research analysis environment (governed by the IRB protocol).

## 3. References

| ID | Document |
|---|---|
| SRC-01 | Deployment Architecture (Netlify, Railway, Neon/Railway PostgreSQL, GitHub Actions, future AWS) |
| SRC-02 | Storage flowchart (raw store kept as received; every other table rebuildable) |
| SRC-05 | Pipeline test input CSV (synthetic data permitted on the interim stack) |
| SRC-07 | Preprint (https://preprints.jmir.org/preprint/113062): device captures a short fixed phrase; features only |
| SRC-14 | Team 2 PRD Guide Part B (raw audio never leaves the room; no LLMs) |
| Contract §12, §18–§21 | Security baseline; owner decisions D-OWNER-1..4; wireframe additions (SRC-18 Alert review, SRC-19 Analytics); reconciliation R1–R26 |
| TRD 05 | Backend API (dependencies, error codes, rate limits, middleware) |
| TRD 06 / TRD 20 | Database design and DDL (roles, triggers) |
| TRD 15 / TRD 16 | Deployment and CI/CD (secrets, scanning jobs) |
| TRD 17 | Logging, monitoring and error handling |
| TRD 19 | API contracts (security schemes) |
| TRD 21 / TRD 22 | Environment configuration; third-party services and hosting |
| TRD 24 | Risks, assumptions and open questions |

## 4. Requirements

### 4.1 Threat model (STRIDE)

Assets: A1 feature records and derived scores/alerts (sensitive, potentially PHI-derived); A2 staff notes;
A3 user credentials and JWT secret; A4 device API keys; A5 audit trail; A6 database credentials; A7 the
integrity of the frozen baselines and alarm results (research validity).

Trust boundaries: B1 device → API (internet); B2 browser → Netlify frontend; B3 browser → API (CORS);
B4 API → PostgreSQL; B5 GitHub Actions → hosting platforms; B6 admin workstation (CLI, read-only analysis role) → database.

| # | STRIDE | Threat | Boundary/asset | Mitigation (requirement IDs) |
|---|---|---|---|---|
| T-01 | Spoofing | Attacker posts fabricated records with a stolen or guessed API key | B1 / A1, A7 | Per-device keys with 256-bit entropy, SHA-256 storage, device binding, revocation, rate limit (SEC-020..SEC-027, SEC-090) |
| T-02 | Spoofing | Credential stuffing / brute force against login | B3 / A3 | argon2id, 5/min/IP rate limit, temporary lockout, uniform error (SEC-010..SEC-016, SEC-091) |
| T-03 | Spoofing | Forged JWT | B3 / A3 | HS256 with ≥ 32-byte secret, `alg` pinned, `iss`/`aud`/`exp` verified, user re-loaded per request (SEC-030..SEC-036) |
| T-04 | Tampering | Modification or deletion of raw records to alter results | B4 / A1, A7 | Immutable `raw_sessions` (trigger + grants), app role without UPDATE/DELETE (SEC-110..SEC-114) |
| T-05 | Tampering | Data altered in transit | B1–B4 | TLS 1.2+ everywhere incl. `sslmode=require`, HSTS (SEC-060..SEC-066) |
| T-06 | Tampering | Malicious dependency or CI workflow change | B5 | Dependabot, pip-audit, npm audit, pinned actions, protected `main` (SEC-150..SEC-156) |
| T-07 | Repudiation | Staff deny reviewing an alarm or writing a note | A5 | Append-only audit log with actor, request ID, IP (SEC-100..SEC-108) |
| T-08 | Information disclosure | Resident data exposed to unauthorised users | B3 / A1, A2 | Authentication on every data endpoint, role matrix, CORS allow-list, no PII (SEC-040..SEC-046, SEC-120..SEC-127) |
| T-09 | Information disclosure | Secrets committed to the repository or printed in logs | A3, A4, A6 | Platform secret stores, gitignored `.env`, secret scanning, log redaction (SEC-050..SEC-058, SEC-107) |
| T-10 | Information disclosure | Verbose errors reveal internals | B3 | Problem responses without stack traces (SEC-085) |
| T-11 | Information disclosure | Real resident data stored on a stack not approved for PHI-derived data | A1 | Interim stack = synthetic/test data only; go-live on AWS only (SEC-001..SEC-005) |
| T-12 | Information disclosure | XSS steals the bearer token from the browser | B2 | CSP, React escaping, no `dangerouslySetInnerHTML`, sessionStorage only (SEC-070..SEC-076, SEC-037) |
| T-13 | Denial of service | Request floods or oversized bodies exhaust free-tier resources (RSK-07) | B1, B3 | Rate limits, body-size limits, batch limits (SEC-090..SEC-094) |
| T-14 | Elevation of privilege | Clinician/researcher calls admin endpoints, or API key reads data | B3 | Server-side role checks from DB, API keys limited to `ingest:write` (SEC-040..SEC-046) |
| T-15 | Elevation of privilege | SQL injection | B4 | SQLAlchemy bound parameters only; no string-built SQL (SEC-083) |
| T-17 | Tampering | Pipeline tuned against the answer key (evaluation data leaks into the analytics) | A7 | `evaluation_ground_truth` not readable by `echowell_app`; only `analytics_summary.py` reads it, through a separate DATABASE_READONLY_URL engine, in test_v0_1 (SEC-114, SEC-116) |
| T-16 | Information disclosure | Audio smuggled into the cloud via extra fields | B1 | `extra="forbid"`, 64 KB body limit, no audio media types, no audio endpoints (SEC-080..SEC-082, SEC-121) |

### 4.2 Data classification and hosting (owner decisions D-OWNER-3, D-OWNER-4)

| Class | Examples | Allowed where |
|---|---|---|
| Synthetic / test | SRC-05 CSV, SRC-06 legacy mock, generated datasets, public development datasets' derived features (DAIC-WOZ, E-DAIC) | local, interim stack (Netlify/Railway/Neon), AWS |
| Live research data (potentially PHI-derived) | features from Team 1 devices at Edgewood, staff notes about real residents, derived scores and alerts | AWS target platform only, after approval |

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| SEC-001 | The interim stack (Netlify + Railway + Neon, all environments including the one named `production`) shall hold synthetic and test data only; no real resident data shall be loaded, ingested or entered into it. | Must | D-OWNER-4, BR-16 | Inspection |
| SEC-002 | EchoWell shall not go live with real resident data until the AWS target platform is approved; go-live shall happen on AWS only. | Must | D-OWNER-4, D-OWNER-3 | Inspection |
| SEC-003 | Team 2 shall not issue interim-stack API keys to devices deployed at Edgewood; interim-stack API keys shall be bound to test devices or used only by test harnesses. | Must | D-OWNER-4 | Inspection |
| SEC-004 | On the interim stack, DATA_SOURCE_LABEL shall name the synthetic/test source (for example "pipeline test data v0.1") and the frontend header shall display it on every page. | Must | D-OWNER-4, contract §11 | Demo |
| SEC-005 | The go-live checklist (TRD 15) shall include a signed-off item "hosting approved for PHI-derived data (AWS)" by the PI and UND IT before any live device is pointed at the API. | Must | D-OWNER-3, D-OWNER-4 | Inspection |
| SEC-007 | All hosted data shall reside in US East regions: Neon `aws-us-east-1`, Railway US East, AWS target `us-east-1`. | Must | contract §21 R25, D-OWNER-3 | Inspection |
| SEC-006 | Application code shall remain portable to AWS (App Runner, Amplify, RDS PostgreSQL, KMS, Secrets Manager, CloudWatch) with configuration changes only: no Railway-, Netlify- or Neon-specific SDKs in application code. | Must | D-OWNER-3, SRC-01 | Inspection |

### 4.3 Authentication: dashboard users

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| SEC-010 | Passwords shall be hashed with argon2id via argon2-cffi 23.x using time_cost=3, memory_cost=65536 KiB, parallelism=4, hash_len=32, salt_len=16; plaintext passwords shall never be stored or logged. | Must | contract §12 | Test |
| SEC-011 | On successful login, if the stored hash parameters differ from SEC-010, the hash shall be recomputed and stored (rehash on login). | Should | contract §12 | Test |
| SEC-012 | Passwords shall be 12..128 characters, shall not equal the user's email (case-insensitive) and shall not appear in the bundled list `backend/core/common_passwords.txt` (top 10,000 common passwords); violations return 422 `PASSWORD_POLICY_VIOLATION`. No composition rules (upper/lower/digit) and no periodic forced change shall be imposed (NIST SP 800-63B). | Must | contract §12 | Test |
| SEC-013 | Login with an unknown email shall still perform one argon2id verification against a fixed dummy hash so that response time does not reveal whether the email exists. | Must | T-02 | Test |
| SEC-014 | Unknown email, wrong password and inactive user shall all return 401 `INVALID_CREDENTIALS` with identical body. | Must | T-02 | Test |
| SEC-015 | After 10 failed logins for the same email within 15 minutes (counted from `audit_logs` action `auth.login.failed`), further attempts for that email shall return 429 `ACCOUNT_TEMPORARILY_LOCKED` until 15 minutes after the last failure. | Should | T-02 | Test |
| SEC-016 | Emails shall be normalised to lower case and trimmed before lookup and storage. | Must | — | Test |
| SEC-017 | The first admin account shall be created only by the CLI `python -m backend.cli create-user --role admin` run by a team member with database access; there shall be no self-registration endpoint and no default credentials. | Must | BR-16 | Inspection |

### 4.4 Authentication: devices (API keys)

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| SEC-020 | API keys shall be generated as `ewk_` + `secrets.token_urlsafe(32)` (256 bits of entropy) by `python -m backend.cli create-api-key --name <name> --scope <ingest:write|pipeline:run> [--device <device_code>]`. | Must | contract §12, §21 R18 | Test |
| SEC-021 | Only the SHA-256 hex digest of the key shall be stored (`api_keys.key_hash`, unique); the plaintext key shall be printed once by the CLI and never stored, logged or retrievable. | Must | contract §12 | Test |
| SEC-022 | Every API key shall carry exactly one scope: `ingest:write` (devices, test harnesses) or `pipeline:run` (the AWS EventBridge scheduler calling `POST /pipeline/run`); a key used on an endpoint outside its scope receives 403 `FORBIDDEN`. No other scopes exist in the MVP. | Must | contract §9, §21 R18 | Test |
| SEC-023 | A key used by a device in a deployment shall be bound to that device (`api_keys.device_id`), and a record from another device shall be refused with 403 `DEVICE_KEY_MISMATCH` (TRD 05 API-040). Unbound keys are permitted only for test harnesses and the seed/CI pipeline. | Must | T-01 | Test |
| SEC-024 | `python -m backend.cli revoke-api-key --name <name>` shall set `active=false`; revoked keys shall be rejected with 401 `API_KEY_INVALID` on the next request. | Must | T-01 | Test |
| SEC-025 | `api_keys.last_used_at` shall be updated at most once per minute per key. | Should | TRD 17 | Test |
| SEC-026 | API keys shall be accepted only in the `X-API-Key` header, never in query strings or bodies. | Must | T-09 | Test |
| SEC-027 | API keys shall be rejected (401) on every endpoint except `POST /api/v1/sessions`, `POST /api/v1/ingest` (scope `ingest:write`) and `POST /api/v1/pipeline/run` (scope `pipeline:run`). | Must | T-14, contract §21 R18 | Test |

### 4.5 Tokens and session expiry

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| SEC-030 | Access tokens shall be JWTs signed with HS256 using JWT_SECRET via PyJWT 2.x; decoding shall pass `algorithms=["HS256"]` explicitly so `none` and other algorithms are rejected. | Must | contract §12 | Test |
| SEC-031 | Token claims shall be `sub` (user UUID), `role`, `iat`, `exp`, `jti` (UUID4), `iss`="echowell-api", `aud`="echowell-dashboard"; `iss`, `aud`, `exp` shall be verified on every request. | Must | T-03 | Test |
| SEC-032 | Token lifetime shall be JWT_EXPIRES_MINUTES (default 60, maximum 60 in staging and production); there shall be no refresh tokens in the MVP; after expiry the user logs in again. | Must | contract §12, §13 | Test |
| SEC-033 | The backend shall refuse to start when APP_ENV is `staging` or `production` and JWT_SECRET is shorter than 32 bytes or equals any value found in the repository (e.g. `.env.example`), and when APP_ENV is `production` and PIPELINE_PROFILE is `test_v0_1` or PIPELINE_AS_OF is set. | Must | T-03, D-OWNER-2, contract §21 R21 | Test |
| SEC-034 | Authorisation decisions shall use the role and `active` flag read from the `users` table on each request, so role changes and deactivation take effect on the next request; the `role` claim is informational only. | Must | T-14 | Test |
| SEC-035 | Rotating JWT_SECRET shall invalidate all issued tokens; this is the emergency revocation mechanism (SEC-170). | Must | T-03 | Test |
| SEC-036 | `POST /auth/logout` shall be audited; the frontend shall delete the token on logout and on any 401 response. | Must | contract §12 | Test |
| SEC-037 | The frontend shall keep the token in memory and in `sessionStorage` only (cleared when the tab closes); it shall not use `localStorage` or cookies for the token. Because no cookies carry credentials, CSRF protection is not required. | Must | T-12 | Inspection |
| SEC-038 | The frontend shall redirect to `/login` when a token is absent or expired and shall show the expiry time-out message "Your session has ended. Please sign in again." | Should | TRD 04 | Test |

### 4.6 Authorisation (role matrix)

Roles: admin (system and user management, all data), clinician (care staff: view and review), researcher
(view and analytics, no review actions). API key: ingest only.

Legend: Y = allowed; — = refused (401 for wrong credential type, 403 `FORBIDDEN` for wrong role).

| Endpoint (`/api/v1`) | Anonymous | admin | clinician | researcher | API key |
|---|---|---|---|---|---|
| GET /health | Y | Y | Y | Y | Y |
| POST /auth/login | Y | Y | Y | Y | — |
| POST /auth/logout | — | Y | Y | Y | — |
| GET /auth/me | — | Y | Y | Y | — |
| POST /sessions | — | — | — | — | Y (scope `ingest:write`) |
| POST /ingest | — | Y | — | — | Y (scope `ingest:write`) |
| GET /ingest/batches/{id} | — | Y | — | Y | — |
| GET /residents | — | Y | Y | Y | — |
| GET /residents/{resident_code} | — | Y | Y | Y | — |
| GET /residents/{resident_code}/checkins | — | Y | Y | Y | — |
| GET /residents/{resident_code}/features | — | Y | Y | Y | — |
| GET /scores (JSON) | — | Y | Y | Y | — |
| GET /scores (`Accept: text/csv`) | — | Y | — | Y | — |
| GET /alerts | — | Y | Y | Y | — |
| POST /alerts/{id}/reviews | — | Y | Y | — | — |
| GET /alerts/{id}/reviews | — | Y | Y | Y | — |
| POST /alerts/{id}/snooze | — | Y | Y | — | — |
| GET /data-alerts | — | Y | Y | Y | — |
| GET /residents/{resident_code}/notes | — | Y | Y | Y | — |
| POST /residents/{resident_code}/notes | — | Y | Y | — | — |
| GET /devices | — | Y | Y | Y | — |
| GET /analytics | — | Y | — | Y | — |
| GET /analytics/baselines (JSON or `Accept: text/csv`) | — | Y | — | Y | — |
| POST /pipeline/run | — | Y | — | — | Y (scope `pipeline:run` only) |
| GET /pipeline/runs | — | Y | — | Y | — |
| GET /pipeline/runs/{id} | — | Y | — | Y | — |
| GET /admissions | — | Y | Y | Y | — |
| GET /admissions/{resident_code}/comparison | — | Y | Y | Y | — |
| GET /facility/reference-ranges | — | Y | Y | Y | — |
| GET /users | — | Y | — | — | — |
| POST /users | — | Y | — | — | — |
| PATCH /users/{id} | — | Y | — | — | — |
| GET /openapi.json | Y | Y | Y | Y | Y |

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| SEC-040 | Every endpoint shall enforce the role matrix above on the server through the TRD 05 dependencies; frontend hiding of controls is a convenience, not a control. | Must | BR-16, T-14 | Test |
| SEC-041 | An automated test shall exercise every (endpoint × credential type) cell of the matrix and assert the allowed status or 401/403. | Must | BR-16 | Test |
| SEC-042 | A route without an explicit auth dependency shall fail the test `tests/integration/test_auth_coverage.py`, which enumerates `app.routes` and allows only `/health`, `/auth/login` and `/openapi.json` (plus `/docs` outside production) to be anonymous. | Must | T-14 | Test |
| SEC-043 | The frontend shall show the `/admin` route only to admins, the "Analytics" navigation and `/analytics` page only to researchers and admins, and the alarm review form ("Save review", "Remind me in 24 h", Resident detail "Mark as reviewed") and the staff-note form only to clinicians and admins. | Must | TRD 04, SRC-18, SRC-19 | Test |
| SEC-044 | Users shall not be able to change their own role or deactivate themselves via `PATCH /users/{id}`; the request returns 403 `FORBIDDEN`. | Must | T-14 | Test |
| SEC-045 | Researchers shall have read-only access in the API (including CSV export); no researcher action shall create, update, review or snooze any record. | Must | BR-16 | Test |
| SEC-046 | Accounts shall be granted only to personnel listed on the IRB-approved protocol (verified by the admin before `POST /users`), and accounts of people leaving the study shall be deactivated within 1 working day of notice. | Must | BR-16, OQ-11 | Inspection |

### 4.7 Secrets management

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| SEC-050 | Secrets (JWT_SECRET, DATABASE_URL, DATABASE_MIGRATION_URL, DATABASE_READONLY_URL, SENTRY_DSN, database role passwords, platform deploy tokens) shall be stored only in Railway service variables, Netlify environment variables, Neon project settings and GitHub Actions encrypted secrets; on AWS in AWS Secrets Manager. | Must | contract §12, D-OWNER-3 | Inspection |
| SEC-051 | `.env`, `.env.*` (except `.env.example`) shall be listed in `.gitignore`; `.env.example` shall contain variable names with non-secret dummy values only. | Must | contract §12 | Inspection |
| SEC-052 | CI shall run `gitleaks detect` (CLI 8.x) on every pull request and fail on any finding. | Must | T-09 | Test |
| SEC-053 | GitHub secret scanning with push protection shall be enabled on the repository where the plan allows it. | Should | T-09 | Inspection |
| SEC-054 | `NEXT_PUBLIC_*` variables shall contain no secrets (they are embedded in the browser bundle). | Must | T-09 | Inspection |
| SEC-055 | JWT_SECRET shall be generated with `python -c "import secrets; print(secrets.token_urlsafe(48))"`, differ per environment, and be rotated every 180 days and immediately on suspected exposure or departure of a team member with access. | Must | T-03 | Inspection |
| SEC-056 | Database role passwords shall differ per environment and per role, be at least 32 random characters, and be rotated every 180 days and on team-member departure. | Must | T-09 | Inspection |
| SEC-057 | Device API keys shall be rotated every 365 days, on device replacement and on suspected exposure (create new key, deploy to device, revoke old key). | Must | T-01 | Inspection |
| SEC-058 | Each rotation shall be recorded as an audit row (`config.changed` with the secret name, never its value) or, for platform-side secrets, in the operations log in `docs/deployment.md`. | Should | T-07 | Inspection |

### 4.8 Transport and storage encryption

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| SEC-060 | All external traffic shall use HTTPS with TLS 1.2 or higher (Netlify and Railway edges now; AWS ALB/App Runner/CloudFront with a TLS 1.2+ security policy on AWS); TLS 1.0/1.1 and plain HTTP shall not serve data (HTTP redirects to HTTPS). | Must | contract §12, D-OWNER-3 | Test |
| SEC-061 | The backend shall connect to PostgreSQL with `sslmode=require` (or `verify-full`) in staging and production and refuse to start otherwise (TRD 05 API-059); on AWS, RDS shall set `rds.force_ssl=1`. | Must | D-OWNER-3 | Test |
| SEC-062 | `Strict-Transport-Security: max-age=31536000; includeSubDomains` shall be sent by the backend (TRD 05 API-106) and by Netlify (netlify.toml) in staging and production. | Must | contract §12 | Test |
| SEC-063 | Data at rest shall be encrypted with provider-managed encryption on the interim stack (Neon storage encryption; Railway volumes) and, on AWS, with RDS storage encryption using a customer-managed KMS key, encrypted automated backups and snapshots, and encrypted S3 buckets if any are used. | Must | D-OWNER-3 | Inspection |
| SEC-064 | Device-to-API traffic shall use HTTPS only; the API shall not offer any unencrypted ingest path. | Must | BR-01, OQ-07 | Test |
| SEC-065 | Local development (`docker-compose`) may use plain HTTP on localhost with synthetic data only. | May | — | Inspection |
| SEC-066 | A TLS check (e.g. `curl --tlsv1.1 --tls-max 1.1` must fail; `--tlsv1.2` must succeed) shall be part of the post-deploy smoke test for staging and production. | Should | TRD 15 | Test |

### 4.9 Browser security (frontend)

`netlify.toml` at the repository root (TRD 15; excerpt, binding):

```toml
[[headers]]
  for = "/*"
  [headers.values]
    Strict-Transport-Security = "max-age=31536000; includeSubDomains"
    X-Content-Type-Options = "nosniff"
    X-Frame-Options = "DENY"
    Referrer-Policy = "no-referrer"
    Permissions-Policy = "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
    Content-Security-Policy = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self' https://echowell-api-staging.up.railway.app https://echowell-api.up.railway.app; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'; upgrade-insecure-requests"
```

The `connect-src` origins are the Railway public domains of the staging and production API services, which
shall be configured as `echowell-api-staging.up.railway.app` and `echowell-api.up.railway.app` (Railway service
settings → Networking → generate domain with these names). Local development (`next dev` on :3000 against
:8000) is not served through Netlify and therefore not subject to this header. When the API moves to AWS, the
AWS API origin replaces these entries in the same change that switches NEXT_PUBLIC_API_BASE_URL.

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| SEC-070 | The frontend shall be served with the headers in the netlify.toml excerpt above; `connect-src` shall list exactly the API origins of the deployed environments and no wildcard, and the Netlify build command shall run `node scripts/check-csp.mjs`, which fails the build when the origin of NEXT_PUBLIC_API_BASE_URL is not listed in `connect-src`. | Must | T-12 | Test |
| SEC-071 | `Permissions-Policy` shall deny `microphone` and `camera`: the dashboard never accesses audio or video devices. | Must | BR-01, T-16 | Test |
| SEC-072 | IBM Plex Sans and IBM Plex Mono shall be self-hosted via `next/font` so that no third-party font or script origin is required by the CSP. | Must | T-12, contract §11 | Inspection |
| SEC-073 | The frontend shall load no third-party scripts, analytics, trackers or tag managers. | Must | BR-16 | Inspection |
| SEC-074 | React components shall not use `dangerouslySetInnerHTML`; an ESLint rule (`react/no-danger`) shall enforce this. | Must | T-12 | Test |
| SEC-075 | `script-src 'unsafe-inline'` is accepted for the MVP because Next.js App Router emits inline hydration scripts; a nonce-based CSP shall be adopted when the frontend moves to AWS Amplify. | Should | T-12, RSK-07 | Inspection |
| SEC-076 | The frontend shall not render staff-note bodies or any API string as HTML; all API text is rendered as text nodes. | Must | T-12 | Test |

### 4.10 Input validation

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| SEC-080 | All request bodies shall be validated by Pydantic models with `extra="forbid"`; unknown properties return 422. | Must | T-16 | Test |
| SEC-081 | Bodies shall be limited to 64 KB (5 MB for `POST /ingest`) (TRD 05 API-104). | Must | T-13, T-16 | Test |
| SEC-082 | Only `application/json` (all endpoints) and `multipart/form-data` with a single `text/csv` part (`POST /ingest` only) shall be accepted; any `audio/*` or other media type returns 415. | Must | BR-01, T-16 | Test |
| SEC-083 | All database access shall use SQLAlchemy expressions or `text()` with bound parameters; string formatting of SQL with request data is prohibited and checked by Bandit rule B608 in CI. | Must | T-15 | Test |
| SEC-084 | Path and query parameters shall be validated against the TRD 19 patterns (resident and device codes `^[A-Za-z0-9]{1,16}$`, UUIDs, dates, enums, ranges). | Must | T-15 | Test |
| SEC-085 | Error responses shall not include stack traces, SQL, file paths, library versions or secret values (TRD 05 API-096). | Must | T-10 | Test |
| SEC-086 | CSV uploads shall be parsed with Python's `csv` module as text only; no cell is evaluated, and values starting with `=`, `+`, `-`, `@` are treated as data (numeric parse) and never re-exported to spreadsheets without escaping. | Must | T-15 | Test |

### 4.11 Rate limiting and abuse controls

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| SEC-090 | `POST /api/v1/sessions` and `POST /api/v1/ingest` shall be limited to RATE_LIMIT_INGEST (600/minute) per API key or admin user. | Must | contract §12 | Test |
| SEC-091 | `POST /api/v1/auth/login` shall be limited to RATE_LIMIT_LOGIN (5/minute) per client IP. | Must | contract §12 | Test |
| SEC-092 | Other authenticated endpoints shall be limited to 300/minute per user (TRD 05 API-102). | Should | T-13 | Test |
| SEC-093 | Exceeding a limit shall return 429 `RATE_LIMITED` with `Retry-After` and write no audit row except for login (where `auth.login.failed` with reason `rate_limited` is written). | Must | T-13 | Test |
| SEC-094 | CORS shall allow only the exact origins in CORS_ORIGINS, with `allow_credentials=False` (TRD 05 API-101); a request from another origin receives no `Access-Control-Allow-Origin` header. | Must | contract §12, T-08 | Test |

### 4.12 Audit logging

Audit events (`audit_logs.action`):

| Action | Actor type | entity_type / entity_id | details (no secrets, no feature values) |
|---|---|---|---|
| auth.login.succeeded | user | user / user id | {} |
| auth.login.failed | system | user / user id or null | {"email": "<as entered, lower-cased>", "reason": "invalid_credentials" \| "locked" \| "rate_limited"} |
| auth.logout | user | user / user id | {} |
| ingest.batch.received | api_key or user | ingest_batch / batch id | {"source", "record_count", "accepted", "rejected", "duplicates"} |
| note.created | user | staff_note / note id | {"resident_code", "note_type", "alert_id", "supersedes_id"} (never the note body) |
| alert.reviewed | user | alert / alert id | {"resident_code", "review_id", "outcome", "explanation_count", "previous_status"} (never the note text) |
| alert.snoozed | user | alert / alert id | {"resident_code", "hours", "snoozed_until"} |
| export.csv | user | route / route template | {"filters": {...}, "row_count"} |
| pipeline.run.started | user, api_key or system | pipeline_run / run id | {"trigger", "scope", "profile"} |
| pipeline.run.finished | system | pipeline_run / run id | {"status", "duration_ms", "warning_count"} |
| config.changed | user or system | config_parameter / "<profile>:<key>" or secret name | {"old": value, "new": value} for parameters; {"rotated": true} for secrets |
| user.created | user | user / user id | {"role"} |
| user.updated | user | user / user id | {"changed": ["role", "active", "password", "display_name"]} |
| api_key.created | system | api_key / key id | {"name", "device_code"} |
| api_key.revoked | system | api_key / key id | {"name"} |
| access.denied | user or api_key | route / route template | {"status": 403, "code"} |

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| SEC-100 | Every event in the table above shall write exactly one `audit_logs` row with `occurred_at` (UTC), `actor_type`, `actor_id`, `action`, `entity_type`, `entity_id`, `details`, `ip`, `request_id`. | Must | contract §9, §12, BR-16 | Test |
| SEC-101 | The audit row shall be written in the same database transaction as the change it records, so that a rolled-back change leaves no audit row and a committed change always has one. | Must | T-07 | Test |
| SEC-102 | `audit_logs` shall be append-only: a trigger `audit_logs_no_update_delete` shall raise an exception on UPDATE or DELETE, and `echowell_app` shall have only INSERT and SELECT on it. TRUNCATE shall be revoked from all non-owner roles. The same trigger and grants apply to `raw_sessions`, `alert_reviews` and `staff_notes`. | Must | contract §12, §21 R20, T-04, T-07 | Test |
| SEC-103 | CLI actions (create-user, create-api-key, revoke-api-key) shall write audit rows with `actor_type`=`system` and `details.operator` = the OS user name running the CLI. | Must | T-07 | Test |
| SEC-104 | Audit `details` shall never contain passwords, password hashes, tokens, API keys, DATABASE_URL, request bodies of ingest calls, or feature values. | Must | BR-16, T-09 | Test |
| SEC-105 | Admins and researchers shall be able to read audit logs only through the `echowell_readonly` database role in the MVP; there is no audit-log API endpoint. | Must | BR-16 | Inspection |
| SEC-106 | Audit logs shall be retained for the life of the study database; deletion policy follows OQ-01. | Must | OQ-01 | Inspection |
| SEC-107 | Application logs (TRD 17) shall redact the `Authorization` and `X-API-Key` headers, `password` fields and JWT values, and shall not include request bodies. | Must | T-09 | Test |
| SEC-108 | `access.denied` audit rows shall be written for 403 responses; 401 responses are logged in application logs only. | Should | T-07 | Test |

### 4.13 Database least privilege

| Role | Purpose | Privileges |
|---|---|---|
| echowell_migrator | Alembic migrations (backend start command, TRD 15 DEP-040) and seed CLI, connection string in DATABASE_MIGRATION_URL | Owner of schema `public` and all objects; DDL |
| echowell_app | FastAPI backend and nightly job, connection string in DATABASE_URL | CONNECT; USAGE on schema; SELECT, INSERT on `raw_sessions`, `audit_logs`, `ingest_rejections`, `staff_notes`, `baselines`, `alert_reviews`; no privilege at all on `evaluation_ground_truth`; SELECT, INSERT, UPDATE (no DELETE) on `facilities`, `residents`, `devices`, `device_assignments`, `users`, `api_keys`, `ingest_batches`, `pipeline_runs`, `config_parameters`, `alerts`, `data_alerts`; SELECT, INSERT, UPDATE, DELETE on rebuildable derived tables (`epochs`, `processed_sessions`, `day_ledger`, `scores`, `cusum_state`, `facility_reference_ranges`); USAGE on sequences; no DDL, no TRUNCATE (exact grants: TRD 20 §4.8) |
| echowell_readonly | Researchers' offline analysis, audit review, exports; login used by DATABASE_READONLY_URL (alarm-timing read in `analytics_summary.py`, test_v0_1 only) | SELECT on all tables (including `evaluation_ground_truth` in the test profile) except `users.password_hash` and `api_keys.key_hash` (column-level grants) |

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| SEC-110 | The three roles above shall be created by the first Alembic migration (or a bootstrap SQL script run by the database owner) with the listed privileges, in every environment. | Must | contract §12 | Test |
| SEC-111 | The backend and nightly job shall connect with DATABASE_URL as `echowell_app`; only Alembic (run as `alembic upgrade head` in the backend web service start command, TRD 15 DEP-040) and the seed CLI shall use DATABASE_MIGRATION_URL as `echowell_migrator`; application request and pipeline code shall never use it, and it shall not be set on the Railway cron (`nightly`) service. | Must | contract §12, §21 R20 | Inspection |
| SEC-112 | `raw_sessions` shall be immutable: trigger `raw_sessions_no_update_delete` raises on UPDATE/DELETE, and `echowell_app` has no UPDATE, DELETE or TRUNCATE privilege on it. | Must | BR-02, T-04 | Test |
| SEC-113 | `staff_notes` shall be append-only for `echowell_app` (SELECT, INSERT only); edits create a new row with `supersedes_id`. | Must | contract §9, T-07 | Test |
| SEC-114 | An integration test connected as `echowell_app` shall assert that UPDATE and DELETE on `raw_sessions`, `audit_logs`, `alert_reviews` and `staff_notes` fail and that `SELECT * FROM evaluation_ground_truth` fails with a permission error. | Must | T-04, contract §21 R20 | Test |
| SEC-116 | DATABASE_READONLY_URL (role `echowell_readonly`) shall be set only where PIPELINE_PROFILE is `test_v0_1`, shall be stored as a platform secret, shall use `sslmode=require`, and shall be referenced only by `backend/services/analytics_summary.py`; no application code shall use `SET ROLE` to reach `echowell_readonly` or `evaluation_ground_truth` (the only `SET ROLE` in the codebase is Alembic `env.py` switching to `echowell_migrator` for object ownership, TRD 20). | Must | contract R27, §21 R20 | Test |
| SEC-115 | The Neon/RDS owner (superuser-equivalent) credentials shall be held only by the Team 2 DevOps lead and the PI's designated deputy and shall not be used by applications. | Must | T-09 | Inspection |

### 4.14 Privacy and data minimisation

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| SEC-120 | Residents shall be identified only by study IDs (`resident_code`); EchoWell shall not store names, dates of birth, room numbers tied to names, medical record numbers, photos or contact details of residents. | Must | BR-16, contract §5 | Inspection |
| SEC-121 | No endpoint shall accept, store, transmit or return audio, and no table shall have an audio column; the TRD 19 schemas contain no audio property. | Must | BR-01, SRC-14 | Test |
| SEC-122 | Stored resident attributes shall be limited to those in contract §9 (`sex` for F0 ranges, cohort, enrolment/admission/withdrawal dates, status); adding a resident attribute requires PI approval and a TRD change. | Must | BR-16 | Inspection |
| SEC-123 | `devices.room_label` shall be non-identifying (e.g. "Unit A-1") and may be null. | Must | BR-16 | Inspection |
| SEC-124 | The note form shall display the hint "Do not enter names or other identifying details." and notes are limited to 2000 characters. | Must | BR-16 | Demo |
| SEC-125 | Staff user records shall hold only email, display name, role and login metadata. | Must | BR-16 | Inspection |
| SEC-126 | Ingest of records for withdrawn residents shall be refused (422 `RESIDENT_WITHDRAWN`); handling of existing data after withdrawal follows the IRB decision (OQ-11). | Must | contract §9, OQ-11 | Test |
| SEC-127 | Error monitoring (SENTRY_DSN, optional) shall be configured with `send_default_pii=False`, request bodies and headers stripped in `before_send`, and shall be disabled (empty DSN) on any environment holding live data until approved under SEC-002. | Must | BR-16, D-OWNER-3 | Inspection |
| SEC-128 | EchoWell shall not call any LLM or generative-AI service and shall not send data to any external AI API; CI shall fail if `openai`, `anthropic`, `langchain`, `google-generativeai`, `cohere` or `mistralai` appears in `backend/requirements*.txt`, `analytics` requirements or `frontend/package.json`. | Must | BR-18, SRC-14 | Test |
| SEC-129 | The UI and API wording shall describe results as detecting a change for clinician review, never as a diagnosis (TRD 11); this limits harm from misinterpretation (RSK-09). | Must | BR-18, RSK-09 | Inspection |

### 4.15 Dependency and code scanning

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| SEC-150 | Dependabot shall be configured (`.github/dependabot.yml`) for `pip` (`/backend`, `/analytics`), `npm` (`/frontend`) and `github-actions` (`/`) with a weekly schedule. | Must | T-06 | Inspection |
| SEC-151 | CI shall run `pip-audit` on the backend and analytics requirements and fail on any known vulnerability with a fix available. | Must | T-06 | Test |
| SEC-152 | CI shall run `npm audit --audit-level=high` in `frontend/` and fail on high or critical findings. | Must | T-06 | Test |
| SEC-153 | CI shall run Bandit on `backend/` and `analytics/` and fail on medium or higher severity findings. | Should | T-15 | Test |
| SEC-154 | Third-party GitHub Actions shall be pinned to a full commit SHA; workflows shall declare least-privilege `permissions:` (default `contents: read`). | Must | T-06 | Inspection |
| SEC-155 | Python and npm dependencies shall be pinned (exact versions in requirements files; `package-lock.json` committed). | Must | T-06 | Inspection |
| SEC-156 | A critical vulnerability affecting a deployed component shall be patched and deployed within 7 days of disclosure, a high one within 30 days. | Should | T-06 | Inspection |

### 4.16 Backups and recovery

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| SEC-160 | On the interim stack, Neon point-in-time restore (history retention as provided by the Neon plan in use, recorded in TRD 22) shall be the backup mechanism; because the interim stack holds synthetic/test data only (SEC-001), data can also be regenerated from the SRC-05 input and seeds. | Must | D-OWNER-4, SRC-02 | Inspection |
| SEC-161 | On AWS, RDS automated backups shall be enabled with at least 7 days retention, encrypted with the KMS key (SEC-063), and deletion protection enabled. | Must | D-OWNER-3 | Inspection |
| SEC-162 | A restore drill (restore to a new branch/instance, run `GET /health` and the R01–R10 validation against it) shall be performed before go-live and every 6 months thereafter. | Should | TRD 13 | Demo |
| SEC-163 | Because derived tables are rebuildable from `raw_sessions` (SRC-02), recovery shall restore `raw_sessions`, reference tables, `staff_notes`, `alerts` (status, snoozes), `alert_reviews`, `users`, `api_keys` and `audit_logs`, then run a full pipeline. | Must | BR-02, SRC-02 | Demo |

### 4.17 Incident response

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| SEC-170 | Containment actions shall be documented in `docs/deployment.md` and executable within 1 hour by the on-duty Team 2 DevOps lead: revoke API keys (CLI), deactivate users (`PATCH /users/{id}`), rotate JWT_SECRET (invalidates all sessions), rotate database role passwords, and scale the Railway/App Runner service to zero if needed. | Must | BR-16 | Demo |
| SEC-171 | A suspected security incident shall be reported to the PI and the Team 2 lead within 24 hours of discovery; the PI decides on reporting to UND IT security and the IRB under UND policy. | Must | BR-16 | Inspection |
| SEC-172 | Investigation shall use `audit_logs` (actor, action, request_id, ip) correlated with application logs by `request_id`. | Must | T-07 | Demo |
| SEC-173 | Each incident shall produce a written post-incident note (timeline, cause, data affected, corrective actions) stored in the team's private project space, not in the public repository. | Should | BR-16 | Inspection |

### 4.18 Research data governance

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| SEC-180 | EchoWell data shall be treated as research data of the UND Speech Study, owned by the faculty PI and governed by the IRB-approved protocol; Team 2 acts as system operator only. | Must | BR-16, contract §12 | Inspection |
| SEC-181 | No retention-based deletion job shall run in the MVP; retention periods and storage locations are decided under OQ-01. | Must | OQ-01 | Inspection |
| SEC-182 | Data exports outside EchoWell (e.g. for the offline mixed-effects analysis) shall be made only via the `echowell_readonly` role by personnel listed on the IRB protocol, and only from the approved AWS platform once live data exists. | Must | BR-16, D-OWNER-4 | Inspection |
| SEC-183 | Public development datasets (DAIC-WOZ, E-DAIC) shall be used only under their licence terms, only for development/pipeline validation, and shall not be loaded into any environment that also holds live study data. | Must | contract §2 | Inspection |
| SEC-184 | Third-party-licensed documents (e.g. the SRC-07 preprint PDF) shall be referenced by link, not committed to the repository. | Must | D-OWNER-1 | Inspection |

## 5. Assumptions

- ASM-03 Single facility (Edgewood); one tenant, no cross-facility isolation needed in the MVP.
- ASM-05 Devices reach the API over HTTPS with an API key; device-side key storage is Team 1's responsibility.
- ASM-08 < 25 dashboard users; rate limits and lockout thresholds are sized for this.
- Note for lead (TRD-local): a single Railway web replica is assumed, so in-memory rate-limit storage is
  sufficient; on AWS with more than one instance a shared store (e.g. PostgreSQL- or Redis-backed limits) is required.

## 6. Dependencies

- TRD 05 dependencies, middleware and error codes; TRD 19 security schemes.
- TRD 06/20 for roles, grants and immutability triggers.
- TRD 15/16 for secret provisioning, gitleaks, pip-audit, npm audit, Bandit and Dependabot jobs, post-deploy TLS check and go-live checklist.
- TRD 17 for log redaction and correlation.
- TRD 21 for JWT_SECRET, CORS_ORIGINS, RATE_LIMIT_* and DATA_SOURCE_LABEL; TRD 22 for provider encryption and PITR facts.
- Libraries: argon2-cffi 23.x, PyJWT 2.x, slowapi 0.1.9, gitleaks 8.x, pip-audit 2.x, Bandit 1.7.x.
- Owner decisions D-OWNER-1..D-OWNER-4 (contract §18).

## 7. Acceptance Criteria

- AC-SEC-01: The role-matrix test (SEC-041) passes for all 33 rows × 5 credential types (API keys tested with both scopes).
- AC-SEC-02: The auth-coverage test (SEC-042) passes; adding an unprotected route makes it fail.
- AC-SEC-03: Connected as `echowell_app`, `UPDATE raw_sessions SET resident_id='X'` and `DELETE FROM audit_logs` both fail (SEC-114).
- AC-SEC-04: A JWT with `alg: none`, a JWT signed with a different secret, and an expired JWT are each rejected with 401 (`TOKEN_INVALID`, `TOKEN_INVALID`, `TOKEN_EXPIRED`).
- AC-SEC-05: Creating a user with password "short" or "password1234" returns 422 `PASSWORD_POLICY_VIOLATION`; the stored hash of a valid password starts with `$argon2id$v=19$m=65536,t=3,p=4$`.
- AC-SEC-06: An API key printed by `create-api-key` works once stored on a test device; after `revoke-api-key` the next `POST /sessions` returns 401 `API_KEY_INVALID`; the `api_keys` table contains only the SHA-256 digest.
- AC-SEC-07: The staging frontend response headers include the CSP, HSTS, `X-Frame-Options: DENY`, `Permissions-Policy` with `microphone=()`; the staging API rejects a TLS 1.1 handshake.
- AC-SEC-08: The backend refuses to start with APP_ENV=production and (a) a 16-byte JWT_SECRET, (b) DATABASE_URL without `sslmode=require`, (c) PIPELINE_PROFILE=test_v0_1, (d) PIPELINE_AS_OF set.
- AC-SEC-09: After login, note creation, an alarm review, a snooze, a CSV export and a pipeline run, `audit_logs` contains one row per event with request_id matching the response `X-Request-ID`, and no row contains a password, token or feature value.
- AC-SEC-10: CI fails when a test commit adds a fake secret (gitleaks), when `openai` is added to requirements (SEC-128), and when a known-vulnerable package version is pinned (pip-audit / npm audit).
- AC-SEC-11: The go-live checklist contains the signed item from SEC-005, and the interim stack's header shows the synthetic/test DATA_SOURCE_LABEL.

## 8. Implementation Notes

- `backend/core/security.py`: `hash_password`, `verify_password` (argon2 `PasswordHasher`), `needs_rehash`,
  `create_access_token`, `decode_access_token` (PyJWT with `algorithms=["HS256"]`, `audience`, `issuer`,
  `options={"require": ["exp","iat","sub","aud","iss","jti"]}`), `hash_api_key` (hashlib.sha256).
- Startup checks live in `backend/core/config.py` (`Settings.validate_for_env()`): JWT_SECRET length, `sslmode`,
  PIPELINE_PROFILE vs APP_ENV, CORS_ORIGINS non-empty and without `*` in staging/production.
- Trigger SQL (in the migration): `CREATE FUNCTION forbid_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION '% is append-only', TG_TABLE_NAME; END $$;` attached `BEFORE UPDATE OR DELETE` to `raw_sessions`, `audit_logs`, `staff_notes`, `alert_reviews`.
- `staff_notes.marked_reviewed` remains in the schema but is always written false; the notes request has no `mark_reviewed` field (contract R5/R27).
- Note: the pipeline's natural-key upserts (contract §20 R15) never touch `alert_reviews` or `staff_notes`, so append-only enforcement does not conflict with rebuilds.
- Audit writes go through `services/audit_service.record(session, action, entity_type, entity_id, details)` which
  reads actor, IP and request_id from the request context var; never call it after commit.
- Failed-login rows are written in their own short transaction because the login request itself does not commit other changes.
- For tests, create users with a reduced argon2 memory cost only via a test-only settings override; never weaken production parameters.
- Pitfall: Railway's edge sets `X-Forwarded-For`; without `--proxy-headers` every client appears as the proxy and the login limit would lock everyone out together.
- Pitfall: do not add `allow_origin_regex` for Netlify deploy previews; add explicit staging origins to CORS_ORIGINS instead.

## 9. Open Questions

- OQ-01 Data retention architecture (what is stored where and for how long) — affects SEC-106, SEC-181.
- OQ-07 AWS budget approval timing and account ownership (UND IT) — gates go-live (SEC-002).
- OQ-11 Data handling on participant withdrawal (IRB) — affects SEC-126.
- OQ-14 Speaker verification timing/output — wrong-speaker records remain a data-integrity risk (RSK-01).
- OQ-16 Smart-home wake phrase vs no-raw-audio rule (Team 1 / PI).
- OQ-26 Who may review alarms and how soon (clinician and admin in MVP; no SLA enforced).
- Closed by owner decision D-OWNER-4 (formerly OQ-23): live data on the interim stack — not permitted; now requirements SEC-001..SEC-005. Residual risk RSK-14 (interim providers may not offer a BAA / HIPAA-eligible plan on the tiers used) is mitigated by SEC-001 and the AWS migration path (SEC-006).

## Revision History

| Version | Date | Change | Author |
|---|---|---|---|
| 0.1 | 18 Oct 2026 | Initial generation from TRD_Generation_Prompt.md | — |
| 0.1 | 18 Oct 2026 | Cross-TRD consistency review | — |
