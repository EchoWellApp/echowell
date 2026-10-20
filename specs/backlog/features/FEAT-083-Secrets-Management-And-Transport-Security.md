# FEAT-083 Secrets management and transport security

| Field | Value |
|---|---|
| Epic | Authentication & Security |
| Build phase | Phase 9 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-081, FEAT-082 |
| Status | Not Started |

## Purpose

Define, document and verify how every secret of every environment is created, stored, separated and rotated, and how every network hop is encrypted: secrets only in Railway variables, Netlify variables (none secret), the GitHub `staging` environment secrets and, on AWS, Secrets Manager; distinct JWT secrets, database role passwords and API keys per environment; rotation procedures recorded as audit rows; no secret in any `NEXT_PUBLIC_*` variable or committed file; TLS 1.2 or higher everywhere with `sslmode=require` on every non-local database URL; a TLS smoke check; and the rule that the interim stack holds synthetic and test data only.

## Business Context

- BR-16 (privacy and security of potentially PHI-derived feature data): D-27 requires TLS 1.2+ including `sslmode=require`, encryption at rest, least privilege and no secrets in code.
- D-28 / AGT-014 (hard rule): no real resident data on the interim Netlify/Railway/Neon stack; interim API keys are never issued to devices at Edgewood (SEC-003).

## Referenced TRDs

- TRD 12 SEC-001..SEC-007, SEC-050..SEC-058, SEC-060..SEC-066, SEC-111, SEC-116, §4.12 (`config.changed` with `{"rotated": true}` for secrets).
- TRD 21 ENV-004, ENV-005, ENV-041, ENV-051, ENV-052, AC-ENV-02, AC-ENV-03, AC-ENV-09.
- TRD 15 DEP-006, DEP-008, DEP-009, DEP-033, DEP-034, DEP-045.
- TRD 16 CIC-090, CIC-091, CIC-092, §4.9 secrets table.
- TRD 06 DB-052, DB-053; TRD 20 PGS-039.
- TRD 25 AGT-014, AGT-016.
- TRD 24 D-27, D-28, RSK-14, RSK-15.

## Scope

- `docs/deployment.md` section "Secrets and transport security": inventory table (secret name, environment, store, owner, rotation interval, last rotated), generation commands, rotation procedures, and the synthetic-data-only rule.
- Settings validation hooks (if not already present from the backend core): refuse `local-dev-only` / `ci-only` placeholders and non-`sslmode=require` URLs when APP_ENV is `staging` or `production` (ENV-041, SEC-061).
- `tests/smoke/test_tls.py` (marker `smoke`): `curl --tlsv1.1 --tls-max 1.1` against the API and frontend origins must fail, `--tlsv1.2` must succeed (SEC-066), plus HSTS presence (SEC-062).
- Unit tests for `SecretStr` masking (`repr(get_settings())`) and for the placeholder and `sslmode` refusals.
- A credential-separation check documented for Phase 10: a JWT issued on staging is rejected by production (DEP-006).

## Out of Scope

- Creating platform variables and secrets (Phase 10, FEAT-088) and AWS Secrets Manager set-up (FEAT-092).
- gitleaks and secret-scanning CI jobs (FEAT-078); deploy workflows that use the staging secrets (FEAT-086).
- Password hashing, JWT issue/verify and API-key hashing primitives (FEAT-016, FEAT-020).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-083-FR-01 | Secrets (JWT_SECRET, DATABASE_URL, DATABASE_MIGRATION_URL, DATABASE_READONLY_URL, SENTRY_DSN, the test-only SEED_* values, database role passwords) shall be stored only in local `.env` (gitignored), Railway service variables, the GitHub Actions `staging` environment secrets and, on AWS, Secrets Manager; never in `netlify.toml`, `railway.toml`, Dockerfiles, `docker-compose.yml` or any committed file except the `local-dev-only-*` / `ci-only-*` placeholders. | SEC-050, ENV-005, AGT-016 |
| FEAT-083-FR-02 | Secret settings shall be `pydantic.SecretStr` so they are masked in `repr()`, logs and error messages. | ENV-004, AC-ENV-09 |
| FEAT-083-FR-03 | `NEXT_PUBLIC_*` variables shall contain no secret. | SEC-054 |
| FEAT-083-FR-04 | Each environment shall have its own JWT_SECRET, API keys, user accounts and database role passwords; a credential issued in one environment shall be rejected in every other. | DEP-006, ENV-051, SEC-056 |
| FEAT-083-FR-05 | JWT_SECRET shall be generated with `openssl rand -hex 32` (64 hex characters) and rotated every 180 days and immediately on suspected exposure or departure of a team member with access; rotation invalidates all tokens (users log in again). | SEC-055, ENV-052 |
| FEAT-083-FR-06 | Database role passwords of staging, production and AWS shall differ per environment and role, be ≥ 32 random characters and be rotated every 180 days and on team-member departure; `echowell_migrator_login` shall also be rotated after each environment rebuild. | SEC-056, RSK-15 |
| FEAT-083-FR-07 | Device API keys shall be rotated every 365 days, on device replacement and on suspected exposure (create new, deploy, revoke old). | SEC-057 |
| FEAT-083-FR-08 | Each rotation shall be recorded as an `audit_logs` row `config.changed` with the secret name and `{"rotated": true}` (never the value) or, for platform-side secrets, in the operations log of `docs/deployment.md`. | SEC-058, TRD 12 §4.12 |
| FEAT-083-FR-09 | The only GitHub Actions secrets shall be `STAGING_DATABASE_URL` and the four `STAGING_SEED_*` secrets in environment `staging`; no production credential shall be stored in GitHub; fork PRs get no secrets; secrets are passed via `env:` and never echoed. | CIC-090, CIC-091, CIC-092, DEP-033 |
| FEAT-083-FR-10 | All external traffic shall use HTTPS with TLS 1.2 or higher, HTTP redirected; device-to-API traffic HTTPS only. | SEC-060, SEC-064, DEP-009 |
| FEAT-083-FR-11 | The backend shall refuse to start in staging and production unless every database URL uses `sslmode=require` (or `verify-full`); every non-local connection uses TLS. | SEC-061, DEP-034, DB-053, AC-ENV-02 |
| FEAT-083-FR-12 | The backend and every CLI command shall refuse to start when JWT_SECRET, any SEED_* value or a database URL password contains `local-dev-only` or `ci-only` and APP_ENV is `staging` or `production`. | ENV-041, AC-ENV-03 |
| FEAT-083-FR-13 | A TLS check (TLS 1.1 refused, TLS 1.2 accepted) shall be part of the staging and production smoke tests, together with the HSTS header on both origins. | SEC-066, SEC-062, DEP-045 |
| FEAT-083-FR-14 | Data at rest shall rely on provider-managed encryption on Neon and Railway (KMS on AWS), recorded per provider in `docs/deployment.md`. | SEC-063, DB-052, PGS-039 |
| FEAT-083-FR-15 | The interim stack shall hold synthetic and test data only; interim API keys shall be bound to test devices or harnesses, never issued to devices deployed at Edgewood; DATA_SOURCE_LABEL shall name the synthetic or test source. | SEC-001, SEC-003, SEC-004, DEP-008, AGT-014 |
| FEAT-083-FR-16 | All hosted data shall reside in US East regions (Neon `aws-us-east-1`, Railway US East, AWS `us-east-1`). | SEC-007 |
| FEAT-083-FR-17 | GitHub secret scanning with push protection shall be enabled where the plan allows. | SEC-053 |

## Inputs

- Railway and Neon configuration (FEAT-081), Netlify configuration (FEAT-082), TRD 21 §4.7 matrix, TRD 16 §4.9 secrets table.
- Backend settings module `backend/core/config.py`.

## Outputs

- `docs/deployment.md` "Secrets and transport security" (inventory without values, procedures, operations log table).
- `tests/smoke/test_tls.py`; unit tests `tests/unit/backend/core/test_settings_secrets.py`.

## Data Flow

Operator generates a secret locally → enters it directly in the platform store (Railway variable, GitHub `staging` environment secret) → platform injects it as an environment variable → `Settings` loads it as `SecretStr` → validation refuses placeholders and non-TLS URLs → application uses it. Rotation: new value set → redeploy → old tokens/keys invalid → `config.changed` audit row or operations-log entry.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-081, FEAT-082

- [FEAT-081](FEAT-081-Railway-Backend-And-Nightly-Cron-Services.md) Railway and Neon configuration (where the secrets live).
- [FEAT-082](FEAT-082-Netlify-Frontend-Configuration-Security-Headers-And.md) Netlify configuration and header set (HSTS on the frontend origin).

Features that build directly on this one (BACKLOG.md §4): FEAT-086.

## Database Impact

- `audit_logs`: rows `config.changed` for secret rotations performed through the CLI (SEC-058); no schema change.
- Database login role passwords are rotated in the provider console (no DDL by this feature).

## API Impact

None exposed. The TLS and HSTS checks target `GET /api/v1/health` and the frontend `/login`.

## Frontend Impact

None in code; confirms no secret in `NEXT_PUBLIC_*`.

## Analytics Impact

None.

## Security Requirements

This feature is itself the security control set listed in the Functional Requirements; in addition, the inventory in `docs/deployment.md` contains names, stores, owners and dates only, never values (AGT-016), and the repository is public, so nothing in issues, PRs, logs or artifacts may contain a secret (TPS-041).

## Error Handling

- Startup refuses invalid secret configurations with exit code 1 and a CRITICAL `startup_config_invalid` log naming variables, never values (LOG-072).
- Suspected exposure: follow the containment steps (revoke API keys, rotate JWT_SECRET and role passwords) documented by FEAT-087 (SEC-170).

## Logging Requirements

- Logs never contain secrets, URLs with credentials or tokens (LOG-020, LOG-024).
- Rotations produce `config.changed` audit rows (SEC-058) or operations-log entries.

## Testing Requirements

- Unit: `repr(get_settings())` masks DATABASE_URL, DATABASE_MIGRATION_URL, DATABASE_READONLY_URL, JWT_SECRET, SENTRY_DSN (AC-ENV-09); staging with a URL lacking `sslmode=require` exits 1 (AC-ENV-02); production with the development JWT_SECRET exits 1 without logging it (AC-ENV-03).
- Smoke: `tests/smoke/test_tls.py` (SEC-066), HSTS (TST-135), run by FEAT-086.
- Inspection: AC-CIC-06 secret list; gitleaks job (FEAT-078).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-083-AC-01 | Starting the backend with APP_ENV=staging and a DATABASE_URL without `sslmode=require` exits with code 1; with APP_ENV=local it starts. Verified by: Unit (staging with a URL lacking `sslmode=require` exits 1 (AC-ENV-02)). | AC-ENV-02, SEC-061 |
| FEAT-083-AC-02 | Starting with APP_ENV=production and the JWT_SECRET of `.env.development.example` exits with code 1 and the log does not contain the value. Verified by: Unit (production with the development JWT_SECRET exits 1 without logging it (AC-ENV-03)). | AC-ENV-03, ENV-041 |
| FEAT-083-AC-03 | `repr(get_settings())` shows `**********` for the five secret settings. Verified by: Unit (`repr(get_settings())` masks DATABASE_URL, DATABASE_MIGRATION_URL, DATABASE_READONLY_URL, JWT_SECRET, SENTRY_DSN (AC-ENV-09)). | AC-ENV-09, ENV-004 |
| FEAT-083-AC-04 | `grep -r "secrets\." .github/workflows` lists only `STAGING_DATABASE_URL`, `STAGING_SEED_ADMIN_PASSWORD`, `STAGING_SEED_CLINICIAN_PASSWORD`, `STAGING_SEED_RESEARCHER_PASSWORD`, `STAGING_SEED_INGEST_API_KEY` (and `GITHUB_TOKEN`). Verified by: Inspection (run the command in the criterion and check its output). | AC-CIC-06, CIC-090 |
| FEAT-083-AC-05 | `tests/smoke/test_tls.py` passes against a TLS 1.2-only test endpoint and fails when TLS 1.1 is accepted. | SEC-066 |
| FEAT-083-AC-06 | `docs/deployment.md` contains the secret inventory with store, owner and rotation interval for every secret of TRD 21 §4.2 and no secret value (`gitleaks detect` on the file finds nothing). Verified by: Inspection (the inspection method of SEC-050, applied to the condition stated in the criterion). | SEC-050, SEC-058 |

## Definition of Done

- All FEAT-083 acceptance criteria pass; Phase 10 checklist (FEAT-087) includes the cross-environment credential rejection check (DEP-006).
- Batch report entry (AGT-022).

## Implementation Notes

- JWT_SECRET is generated with `openssl rand -hex 32`, as TRD 21 §4.2/§4.6 and CI use; TRD 12 SEC-055 was aligned to it in the PR #2 consistency fixes (it exceeds the 32-byte minimum, AC-ENV-04).
- Record platform-side rotations (Railway variables, Neon role passwords) in the operations log because they have no CLI and therefore no audit row (SEC-058).
- Credentials are never migrated between environments; AWS cut-over creates them anew (DEP-117 step 4).
