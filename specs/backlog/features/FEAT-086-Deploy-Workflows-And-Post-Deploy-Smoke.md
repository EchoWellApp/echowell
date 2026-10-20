# FEAT-086 Deploy workflows and post-deploy smoke tests

| Field | Value |
|---|---|
| Epic | DevOps & Deployment |
| Build phase | Phase 9 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-080, FEAT-081, FEAT-082, FEAT-083 |
| Status | Not Started |

## Purpose

Create the two deployment verification and release workflows and the smoke-test suite they run. Code is deployed by the Netlify and Railway GitHub integrations, never by Actions; `deploy-staging.yml` waits until staging serves the pushed SHA, re-seeds staging with `seed test_v0_1 --reset` when migrations or `analytics/` changed (or on request), and runs the authenticated staging smoke tests; `deploy-production.yml` uses no secrets, waits for the merged SHA, runs the unauthenticated read-only production smoke tests, and only then creates the Git tag and GitHub Release for `release: vX.Y.Z` merges.

## Business Context

- BR-17: GitHub → Netlify / Railway deployment with verification (SRC-01; CIC-001).
- BR-15: staging always reflects the answer key (DEP-074, CIC-041) and the smoke tests check tiles 2 / 7 / 1 / 19, R09 alarm and analytics figures (DEP-080).
- BR-16: no production credential in GitHub (CIC-050); production smoke tests prove auth, HSTS and no audio route (DEP-081).

## Referenced TRDs

- TRD 16 CIC-001, CIC-002, CIC-003, CIC-024, CIC-040, CIC-041, CIC-042, CIC-043, CIC-050, CIC-051, CIC-052, CIC-090, CIC-092, §4.4 and §4.5 step lists, §4.9 variables and secrets, §4.10 `smoke-report`, §8 note on skipped Netlify builds.
- TRD 15 DEP-060, DEP-074, DEP-080, DEP-081, DEP-082, DEP-083, §4.9, §4.10, §4.11, §4.12.
- TRD 13 TST-006 (`smoke`, `authenticated` markers), TST-134, TST-135, TST-152.
- TRD 12 SEC-062, SEC-066.
- TRD 21 ENV-053, §4.5 (SMOKE_* variables, `NEXT_PUBLIC_GIT_SHA`).
- TRD 24 D-59, D-71.
- TRD 18 GIT-012 (release PRs from `staging` to `main`), versioning.

## Scope

- `tests/smoke/` (marker `smoke`; tests that log in also marked `authenticated`): reading SMOKE_API_BASE_URL, SMOKE_FRONTEND_URL, SMOKE_EXPECTED_SHA, SMOKE_ENV and, for staging only, SMOKE_USER_EMAIL / SMOKE_USER_PASSWORD.
  - Staging (DEP-080 a–h): health 200, `database: "ok"`, `version` = expected SHA; `/login` 200; login as the seeded `researcher@example.com`; `GET /api/v1/residents` tiles 2 / 7 / 1 / 19; `GET /api/v1/residents/R09` `alarm_on` since Oct 21; `GET /api/v1/alerts` open alarms R09 and R10 and `GET /api/v1/data-alerts` exactly R08 baseline stuck, R05 possible other speaker, R03 many set aside, D02 silent Oct 12; `GET /api/v1/analytics` 281 of 300 received and 267 of 300 used; CORS preflight allowed from the staging frontend origin and refused from `https://example.org`.
  - Production (DEP-081 a–f): health 200 with `database: "ok"` and `version` = expected SHA; `/login` 200 over HTTPS; `GET /api/v1/residents` without token 401 with RFC 7807 body; `POST /api/v1/sessions` without API key 401; HSTS on both origins; `GET /api/v1/audio` 404.
  - Both: TLS check from FEAT-083 (`tests/smoke/test_tls.py`) and HSTS (TST-135).
- `.github/workflows/deploy-staging.yml`: triggers `push` to `staging` and `workflow_dispatch` with boolean input `reseed`; GitHub environment `staging`; steps 1–6 of TRD 16 §4.4 (wait for backend SHA, wait for frontend build meta or accept the previous build when `frontend/` did not change, conditional re-seed with the operator variable set, smoke tests, upload `build/smoke-junit.xml` as `smoke-report`).
- `.github/workflows/deploy-production.yml`: trigger `push` to `main` and `workflow_dispatch` (smoke only); GitHub environment `production` with branch rule `main` and no secrets; `permissions: contents: write`; steps 1–4 of TRD 16 §4.5; tag and release only for `release: vX.Y.Z` head commits after green smoke tests.
- `docs/deployment.md` sections "Staging release", "Production release" (TRD 15 §4.9/§4.10 verbatim steps) and "Manual authenticated check" (DEP-083).

## Out of Scope

- Platform integrations and their settings (FEAT-081, FEAT-082); any workflow that pushes code or runs migrations against production (forbidden, CIC-001, CIC-003).
- Rollback execution and restore (FEAT-089); performing the first deployment (FEAT-088).
- `ci.yml`, `e2e.yml`, `uptime.yml` (FEAT-078, FEAT-080, FEAT-085).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-086-FR-01 | No workflow shall hold a Netlify or Railway deploy token or push code to the platforms; no workflow shall run migrations against production. | CIC-001, CIC-003, DEP-060 |
| FEAT-086-FR-02 | `deploy-staging.yml` shall poll `${{ vars.STAGING_API_BASE_URL }}/health` every 15 s for up to 15 minutes until `version` equals the pushed SHA, and fail otherwise. | CIC-040, DEP-082 |
| FEAT-086-FR-03 | Both workflows shall wait up to 15 minutes for `<meta name="echowell-build" content="<SHA>">` on `/login`, comparing with `git log -1 --format=%H -- frontend netlify.toml` when Netlify skipped the build. | TRD 16 §4.4 step 3, §8 |
| FEAT-086-FR-04 | `deploy-staging.yml` shall re-seed with `python -m backend.cli seed test_v0_1 --reset` and then the DS-10 loader when the push modifies `backend/alembic/**` or `analytics/**` or when dispatched with `reseed: true`, using DATABASE_URL and DATABASE_MIGRATION_URL = `secrets.STAGING_DATABASE_URL`, APP_ENV=staging, PIPELINE_PROFILE=test_v0_1, PIPELINE_AS_OF=2026-10-30T15:00:00-05:00, FACILITY_NAME=Edgewood, FACILITY_TZ=America/Chicago and SEED_* from `STAGING_SEED_*`, without printing them. | CIC-041, DEP-074, ENV-053, D-71 |
| FEAT-086-FR-05 | `deploy-staging.yml` shall run `pytest tests/smoke -m smoke` with SMOKE_ENV=staging and the seeded researcher credentials, run in GitHub environment `staging` (secrets available only on the `staging` branch), and fail on any smoke failure. | CIC-042, CIC-043, DEP-080 |
| FEAT-086-FR-06 | Staging smoke tests shall verify all ten checks (a)–(j) of DEP-080. | DEP-080, TST-152, TST-134 |
| FEAT-086-FR-07 | `deploy-production.yml` shall use no repository or environment secret and access production only through public HTTPS endpoints. | CIC-050, DEP-033 |
| FEAT-086-FR-08 | `deploy-production.yml` shall fail if production does not report the merged SHA within 15 minutes or if any test of `pytest tests/smoke -m "smoke and not authenticated"` fails; failure triggers the TRD 15 §4.12 rollback decision. | CIC-051, DEP-081 |
| FEAT-086-FR-09 | Production smoke tests shall be unauthenticated and read-only and verify checks (a)–(g) of DEP-081. | DEP-081, TST-152 |
| FEAT-086-FR-10 | A Git tag `vX.Y.Z` and a GitHub Release with generated notes (`gh release create vX.Y.Z --generate-notes --target $SHA`) shall be created only after production smoke tests pass and only when the head commit message starts with `release: vX.Y.Z`. | CIC-052 |
| FEAT-086-FR-11 | A smoke-test run shall finish within 5 minutes, excluding the up-to-15-minute wait for the new version. | DEP-082 |
| FEAT-086-FR-12 | Smoke tests shall assert `Strict-Transport-Security` on API and frontend responses and run the TLS 1.1-refused / TLS 1.2-accepted check. | TST-135, SEC-062, SEC-066 |
| FEAT-086-FR-13 | Only `deploy-production.yml` shall request `contents: write`; secrets shall be passed via `env:`, never as command-line arguments or echoed. | CIC-024, CIC-092 |
| FEAT-086-FR-14 | Smoke junit output shall be uploaded as `smoke-report` (30 days). | TRD 16 §4.10 |
| FEAT-086-FR-15 | After a production deploy a team member shall perform the manual authenticated check (log in, open Residents, open one resident, sign out) and record it in the GitHub Release notes. | DEP-083 |

## Inputs

- Repository variables `STAGING_API_BASE_URL`, `STAGING_FRONTEND_URL`, `PRODUCTION_API_BASE_URL`, `PRODUCTION_FRONTEND_URL`; staging environment secrets `STAGING_DATABASE_URL`, `STAGING_SEED_ADMIN_PASSWORD`, `STAGING_SEED_CLINICIAN_PASSWORD`, `STAGING_SEED_RESEARCHER_PASSWORD`, `STAGING_SEED_INGEST_API_KEY` (FEAT-083).
- Seed and loader commands (FEAT-055, FEAT-057); health `version` = `GIT_SHA` (FEAT-081); `echowell-build` meta (FEAT-082).

## Outputs

- `.github/workflows/deploy-staging.yml`, `.github/workflows/deploy-production.yml`, `tests/smoke/conftest.py`, `tests/smoke/test_staging_smoke.py`, `tests/smoke/test_production_smoke.py` (plus `test_tls.py` from FEAT-083).
- Artifacts `smoke-report`; tags `vX.Y.Z` and GitHub Releases.

## Data Flow

Merge to `staging` → Railway/Netlify deploy (integrations) → `deploy-staging.yml` polls health and build meta → optional re-seed from the CI checkout into the Neon `staging` branch (migrator URL) → smoke tests over HTTPS → junit uploaded. Merge `release: vX.Y.Z` to `main` → production deploy → `deploy-production.yml` polls → unauthenticated smoke tests → tag and release → manual authenticated check recorded in the release notes.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-080, FEAT-081, FEAT-082, FEAT-083

- [FEAT-080](FEAT-080-E2E-Performance-And-Nightly-Workflows.md) E2E, performance and nightly workflows (the workflow set of CIC-002 is completed together).
- [FEAT-081](FEAT-081-Railway-Backend-And-Nightly-Cron-Services.md) Railway backend and Neon configuration.
- [FEAT-082](FEAT-082-Netlify-Frontend-Configuration-Security-Headers-And.md) Netlify configuration and build meta tag.
- [FEAT-083](FEAT-083-Secrets-Management-And-Transport-Security.md) Secrets management and the TLS smoke test.

## Database Impact

- Staging re-seed recreates the staging schema (`reset-test-db`: `alembic downgrade base`, `alembic upgrade head`) and reloads the `test_v0_1` data, the single exception to the forward-only rule (DEP-060, D-71); it writes an `audit_logs` row `seed.reset`.
- Production: no write of any kind; smoke tests are read-only (DEP-081).

## API Impact

- Consumed (staging): `GET /api/v1/health`, `POST /api/v1/auth/login`, `GET /api/v1/residents`, `GET /api/v1/residents/R09`, `GET /api/v1/alerts`, `GET /api/v1/data-alerts`, `GET /api/v1/analytics`, CORS preflight `OPTIONS`.
- Consumed (production): `GET /api/v1/health`, `GET /api/v1/residents` (401), `POST /api/v1/sessions` (401), `GET /api/v1/audio` (404).
- Exposed: none.

## Frontend Impact

- `/login` fetched for status 200 and the `echowell-build` meta tag; no code change beyond FEAT-082.

## Analytics Impact

None in code. The staging re-seed runs the pipeline with profile `test_v0_1` at the fixed as-of (D-59).

## Security Requirements

- Production workflow holds no secret (CIC-050); staging secrets are scoped to the `staging` environment and branch (CIC-043).
- The staging smoke user is the seeded researcher; no smoke user exists in production (TST-152).
- Secrets never echoed; masked by GitHub; passed via `env:` (CIC-092).
- Re-seeding never runs against production (DEP-070, AGT-015).

## Error Handling

- Version not live within 15 minutes → workflow fails (CIC-040, CIC-051).
- Production smoke failure → rollback decision within 30 minutes per TRD 15 §4.12 (FEAT-089); no tag is created.
- Re-seed failure → workflow fails before smoke tests; staging is re-seeded by dispatching with `reseed: true` after the fix.

## Logging Requirements

- Workflow logs show polling attempts, observed `version`, smoke results; never secrets.
- Staging re-seed writes the `seed.reset` audit row (DEP-071) and the seed's own audit rows (`user.created`/`user.updated`, `api_key.created`).

## Testing Requirements

- Smoke tests: DEP-080, DEP-081, TST-134, TST-135, TST-152, SEC-066.
- Local verification: run `pytest tests/smoke -m smoke` against the Compose `demo` stack with SMOKE_ENV=staging-equivalent variables (http, so TLS/HSTS tests are skipped with `reason=` citing SEC-065, TST-153).
- Workflow dry run in Phase 9 with `workflow_dispatch` (smoke against a local tunnel is not required; first live run in Phase 10).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-086-AC-01 | A merge to `staging` yields a Railway staging deployment whose health `version` equals the merge SHA, a Netlify branch deploy, and a green `deploy-staging.yml` run. | AC-DEP-03 |
| FEAT-086-AC-02 | A merge `release: vX.Y.Z` to `main` yields production health `version` = merge SHA and a green `deploy-production.yml` run that created tag `vX.Y.Z`. | AC-DEP-04, AC-CIC-07 |
| FEAT-086-AC-03 | `grep -n "secrets\." .github/workflows/deploy-production.yml` returns nothing. | CIC-050 |
| FEAT-086-AC-04 | A push to `staging` changing a file under `analytics/` triggers the re-seed step; a push changing only `docs/` does not. | CIC-041 |
| FEAT-086-AC-05 | The staging smoke suite contains tests for each of DEP-080 (a)–(h) and the production suite for each of DEP-081 (a)–(f); production tests carry no `authenticated` marker. | DEP-080, DEP-081, TST-006 |
| FEAT-086-AC-06 | A commit to `main` whose message does not start with `release: v` produces no tag or release. | CIC-052 |

## Definition of Done

- All FEAT-086 acceptance criteria demonstrated (FEAT-086-AC-01 and FEAT-086-AC-02 in Phase 10 with FEAT-088).
- Workflow files listed in CIC-002 exist and no other workflow file was added.
- Batch report entry (AGT-022).

## Implementation Notes

- Re-seeding runs from the CI checkout, which contains `database/seeds/` and `tests/fixtures/` (DEP-119 note).
- Operator commands validate only their own variables (ENV-053); do not pass JWT_SECRET or CORS settings to the re-seed step.
- The `http://` → `https://` redirect (TST-135) and the TLS check (SEC-066) are now items (i)/(j) of DEP-080 and (e)/(g) of DEP-081 (aligned in the PR #2 consistency fixes).
- Production deploys should avoid the 08:00–20:00 facility-local window while OQ-15 is open (TRD 15 §9).
