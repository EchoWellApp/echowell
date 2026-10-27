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

Create the staging deployment verification workflow, the manual production release workflow and the smoke-test suite they run (D-99). Staging is deployed by the Netlify and Railway GitHub integrations on every merge to `main`; `deploy-staging.yml` (on every push to `main`) waits until staging serves the pushed SHA, re-seeds the staging database with `seed test_v0_1 --reset` when migrations or `analytics/` changed (or on request), and runs the authenticated staging smoke tests. Production is deployed only by `deploy-production.yml`, a manual `workflow_dispatch` run for a chosen `main` commit approved by a required reviewer of the `production` environment: it checks the commit's required checks and staging run, deploys with `railway up` and the Netlify CLI using only the two production deploy tokens, waits for the released SHA, runs the unauthenticated read-only production smoke tests, and only then creates the Git tag `vX.Y.Z` and the GitHub Release.

## Business Context

- BR-17: GitHub → Netlify / Railway deployment with verification (SRC-01; CIC-001).
- BR-15: staging always reflects the answer key (DEP-074, CIC-041) and the smoke tests check the resident summary 2 / 2 / 0 / 6 (changed, needs attention, learning, usual), R09 alarm and analytics figures (DEP-080).
- BR-16: no production database URL or application credential in GitHub, only the two production deploy tokens behind a required reviewer (CIC-050, CIC-090); production smoke tests prove auth, HSTS and no audio route (DEP-081).

## Referenced TRDs

- TRD 16 CIC-001, CIC-002, CIC-003, CIC-024, CIC-040, CIC-041, CIC-042, CIC-043, CIC-050, CIC-051, CIC-052, CIC-053, CIC-090, CIC-092, §4.4 and §4.5 step lists, §4.9 variables and secrets, §4.10 `smoke-report`, §8 note on skipped Netlify builds.
- TRD 15 DEP-060, DEP-074, DEP-080, DEP-081, DEP-082, DEP-083, §4.9, §4.10, §4.11, §4.12.
- TRD 13 TST-006 (`smoke`, `authenticated` markers), TST-134, TST-135, TST-152.
- TRD 12 SEC-062, SEC-066.
- TRD 21 ENV-053, §4.5 (SMOKE_* variables, `NEXT_PUBLIC_GIT_SHA`).
- TRD 24 D-59, D-71, D-99.
- TRD 18 GIT-012, GIT-013 (PRs to `main` only; production changes only through the release workflow), versioning.

## Scope

- `tests/smoke/` (marker `smoke`; tests that log in also marked `authenticated`): reading SMOKE_API_BASE_URL, SMOKE_FRONTEND_URL, SMOKE_EXPECTED_SHA, SMOKE_ENV and, for staging only, SMOKE_USER_EMAIL / SMOKE_USER_PASSWORD.
  - Staging (DEP-080 a–h): health 200, `database: "ok"`, `version` = expected SHA; `/login` 200; login as the seeded `researcher@example.com`; `GET /api/v1/residents` summary changed 2, needs_attention 2, learning 0, usual 6 (TRD 24 D-114); `GET /api/v1/residents/R09` `alarm_on` since Oct 21; `GET /api/v1/alerts` open alarms R09 and R10 and `GET /api/v1/data-alerts` exactly R08 baseline stuck, R05 possible other speaker, R03 many set aside, D02 silent Oct 12; `GET /api/v1/analytics` 281 of 300 received and 267 of 300 used; CORS preflight allowed from the staging frontend origin and refused from `https://example.org`.
  - Production (DEP-081 a–f): health 200 with `database: "ok"` and `version` = expected SHA; `/login` 200 over HTTPS; `GET /api/v1/residents` without token 401 with RFC 7807 body; `POST /api/v1/sessions` without API key 401; HSTS on both origins; `GET /api/v1/audio` 404.
  - Both: TLS check from FEAT-083 (`tests/smoke/test_tls.py`) and HSTS (TST-135).
- `.github/workflows/deploy-staging.yml`: triggers `push` to `main` and `workflow_dispatch` with boolean input `reseed`; GitHub environment `staging` (branch rule `main`); steps 1–6 of TRD 16 §4.4 (wait for backend SHA, wait for frontend build meta or accept the previous build when `frontend/` did not change, conditional re-seed with the operator variable set, smoke tests, upload `build/smoke-junit.xml` as `smoke-report`).
- `.github/workflows/deploy-production.yml`: trigger `workflow_dispatch` only (inputs `sha`, `version`, `smoke_only`); GitHub environment `production` with branch rule `main`, a required reviewer and the secrets `RAILWAY_PRODUCTION_TOKEN` and `NETLIFY_AUTH_TOKEN`; `permissions: contents: write`; steps 1–7 of TRD 16 §4.5; tag and release only for the released SHA after green smoke tests.
- `docs/deployment.md` sections "Staging deploy", "Production release" (TRD 15 §4.9/§4.10 verbatim steps) and "Manual authenticated check" (DEP-083).

## Out of Scope

- Platform integrations and their settings (FEAT-081, FEAT-082); any workflow that pushes code or runs migrations against production (forbidden, CIC-001, CIC-003).
- Rollback execution and restore (FEAT-089); performing the first deployment (FEAT-088).
- `ci.yml`, `e2e.yml`, `uptime.yml` (FEAT-078, FEAT-080, FEAT-085).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-086-FR-01 | No workflow other than `deploy-production.yml` shall hold a Netlify or Railway deploy token or deploy code to the platforms; no workflow shall run migrations against production (they run only as the Railway pre-deploy command). | CIC-001, CIC-003, DEP-060 |
| FEAT-086-FR-02 | `deploy-staging.yml` shall poll `${{ vars.STAGING_API_BASE_URL }}/health` every 15 s for up to 15 minutes until `version` equals the pushed SHA, and fail otherwise. | CIC-040, DEP-082 |
| FEAT-086-FR-03 | Both workflows shall wait up to 15 minutes for `<meta name="echowell-build" content="<SHA>">` on `/login`, comparing with `git log -1 --format=%H -- frontend netlify.toml` when Netlify skipped the build. | TRD 16 §4.4 step 3, §8 |
| FEAT-086-FR-04 | `deploy-staging.yml` shall re-seed with `python -m backend.cli seed test_v0_1 --reset` and then the DS-10 loader when the push modifies `backend/alembic/**` or `analytics/**` or when dispatched with `reseed: true`, using DATABASE_URL and DATABASE_MIGRATION_URL = `secrets.STAGING_DATABASE_URL`, APP_ENV=staging, PIPELINE_PROFILE=test_v0_1, PIPELINE_AS_OF=2026-10-30T15:00:00-05:00, FACILITY_NAME=Edgewood, FACILITY_TZ=America/Chicago and SEED_* from `STAGING_SEED_*`, without printing them. | CIC-041, DEP-074, ENV-053, D-71 |
| FEAT-086-FR-05 | `deploy-staging.yml` shall run `pytest tests/smoke -m smoke` with SMOKE_ENV=staging and the seeded researcher credentials, run in GitHub environment `staging` (secrets available only to runs on `main`), and fail on any smoke failure. | CIC-042, CIC-043, DEP-080 |
| FEAT-086-FR-06 | Staging smoke tests shall verify all ten checks (a)–(j) of DEP-080. | DEP-080, TST-152, TST-134 |
| FEAT-086-FR-07 | `deploy-production.yml` shall use only the `production` environment secrets `RAILWAY_PRODUCTION_TOKEN` and `NETLIFY_AUTH_TOKEN`, never a production database URL or application credential, and verify production only through public HTTPS endpoints. | CIC-050, CIC-090, DEP-033 |
| FEAT-086-FR-08 | `deploy-production.yml` shall fail if production does not report the released SHA within 15 minutes or if any test of `pytest tests/smoke -m "smoke and not authenticated"` fails; failure triggers the TRD 15 §4.12 rollback decision. | CIC-051, DEP-081 |
| FEAT-086-FR-09 | Production smoke tests shall be unauthenticated and read-only and verify checks (a)–(g) of DEP-081. | DEP-081, TST-152 |
| FEAT-086-FR-10 | A Git tag `vX.Y.Z` and a GitHub Release with generated notes (`gh release create vX.Y.Z --generate-notes --target $SHA`) shall be created only by `deploy-production.yml`, for the released SHA, and only after production smoke tests pass. | CIC-052 |
| FEAT-086-FR-11 | A smoke-test run shall finish within 5 minutes, excluding the up-to-15-minute wait for the new version. | DEP-082 |
| FEAT-086-FR-12 | Smoke tests shall assert `Strict-Transport-Security` on API and frontend responses and run the TLS 1.1-refused / TLS 1.2-accepted check. | TST-135, SEC-062, SEC-066 |
| FEAT-086-FR-13 | Only `deploy-production.yml` shall request `contents: write`; secrets shall be passed via `env:`, never as command-line arguments or echoed. | CIC-024, CIC-092 |
| FEAT-086-FR-14 | Smoke junit output shall be uploaded as `smoke-report` (30 days). | TRD 16 §4.10 |
| FEAT-086-FR-15 | After a production deploy a team member shall perform the manual authenticated check (log in, open Residents, open one resident, sign out) and record it in the GitHub Release notes. | DEP-083 |
| FEAT-086-FR-16 | `deploy-production.yml` shall run only on manual dispatch after approval by a required reviewer of the `production` environment, and shall deploy nothing unless the chosen SHA is on `main`, every CIC-070 check on it succeeded and its `deploy-staging.yml` run succeeded; it then sets `GIT_SHA`, runs `railway up` for `backend` and `nightly` and `netlify deploy --build --prod` for the production site from that SHA. | CIC-053, DEP-002, DEP-003, DEP-062 |

## Inputs

- Repository variables `STAGING_API_BASE_URL`, `STAGING_FRONTEND_URL`, `PRODUCTION_API_BASE_URL`, `PRODUCTION_FRONTEND_URL`; staging environment secrets `STAGING_DATABASE_URL`, `STAGING_SEED_ADMIN_PASSWORD`, `STAGING_SEED_CLINICIAN_PASSWORD`, `STAGING_SEED_RESEARCHER_PASSWORD`, `STAGING_SEED_INGEST_API_KEY`; production environment secrets `RAILWAY_PRODUCTION_TOKEN`, `NETLIFY_AUTH_TOKEN` and variable `NETLIFY_PRODUCTION_SITE_ID` (FEAT-083).
- Release inputs of a manual `deploy-production.yml` run: `sha` (a `main` commit), `version` (`vX.Y.Z`).
- Seed and loader commands (FEAT-055, FEAT-057); health `version` = `GIT_SHA` (FEAT-081); `echowell-build` meta (FEAT-082).

## Outputs

- `.github/workflows/deploy-staging.yml`, `.github/workflows/deploy-production.yml`, `tests/smoke/conftest.py`, `tests/smoke/test_staging_smoke.py`, `tests/smoke/test_production_smoke.py` (plus `test_tls.py` from FEAT-083).
- Artifacts `smoke-report`; tags `vX.Y.Z` and GitHub Releases.

## Data Flow

Merge to `main` → Railway/Netlify staging deploy (integrations) → `deploy-staging.yml` polls health and build meta → optional re-seed from the CI checkout into the Neon `staging` database branch (migrator URL) → smoke tests over HTTPS → junit uploaded. Manual `deploy-production.yml` run for a chosen `main` commit → reviewer approval → commit, checks and staging run verified → `railway up` and Netlify CLI deploy of that commit → workflow polls → unauthenticated smoke tests → tag and release → manual authenticated check recorded in the release notes.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-080, FEAT-081, FEAT-082, FEAT-083

- [FEAT-080](FEAT-080-E2E-Performance-And-Nightly-Workflows.md) E2E, performance and nightly workflows (the workflow set of CIC-002 is completed together).
- [FEAT-081](FEAT-081-Railway-Backend-And-Nightly-Cron-Services.md) Railway backend and Neon configuration.
- [FEAT-082](FEAT-082-Netlify-Frontend-Configuration-Security-Headers-And.md) Netlify configuration and build meta tag.
- [FEAT-083](FEAT-083-Secrets-Management-And-Transport-Security.md) Secrets management and the TLS smoke test.

Features that build directly on this one (BACKLOG.md §4): FEAT-087.

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

- The production workflow holds only the two deploy tokens, released to a job only after reviewer approval (CIC-050, CIC-053); staging secrets are scoped to the `staging` environment, available only to runs on `main` (CIC-043).
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
| FEAT-086-AC-01 | A merge to `main` yields a Railway staging deployment whose health `version` equals the merge SHA, a Netlify staging-site deploy, and a green `deploy-staging.yml` run, and leaves production unchanged. Verified by: Smoke tests (TST-134, TST-135, TST-152). | AC-DEP-03 |
| FEAT-086-AC-02 | An approved manual `deploy-production.yml` run for a `main` commit and version `vX.Y.Z` yields production health `version` = that SHA and a green run that created tag `vX.Y.Z`. Verified by: Smoke tests (TST-134, TST-135, TST-152). | AC-DEP-04, AC-CIC-07 |
| FEAT-086-AC-03 | `grep -n "secrets\." .github/workflows/deploy-production.yml` returns nothing. Verified by: Inspection (run the command in the criterion and check its output). | CIC-050 |
| FEAT-086-AC-04 | A push to `main` changing a file under `analytics/` triggers the re-seed step; a push changing only `docs/` does not. Verified by: Demo (the demo method of CIC-041, applied to the condition stated in the criterion). | CIC-041 |
| FEAT-086-AC-05 | The staging smoke suite contains tests for each of DEP-080 (a)–(h) and the production suite for each of DEP-081 (a)–(f); production tests carry no `authenticated` marker. | DEP-080, DEP-081, TST-006 |
| FEAT-086-AC-06 | A merge to `main` produces no production deploy, tag or release; a `deploy-production.yml` run for a SHA whose required checks or staging run did not succeed deploys nothing. Verified by: Demo (the demo method of CIC-052, applied to the condition stated in the criterion). | CIC-052, CIC-053 |

## Definition of Done

- All FEAT-086 acceptance criteria pass.
- All FEAT-086 acceptance criteria demonstrated (FEAT-086-AC-01 and FEAT-086-AC-02 in Phase 10 with FEAT-088).
- Workflow files listed in CIC-002 exist and no other workflow file was added.
- Batch report entry (AGT-022).

## Implementation Notes

- Re-seeding runs from the CI checkout, which contains `database/seeds/` and `tests/fixtures/` (DEP-119 note).
- Operator commands validate only their own variables (ENV-053); do not pass JWT_SECRET or CORS settings to the re-seed step.
- The `http://` → `https://` redirect (TST-135) and the TLS check (SEC-066) are now items (i)/(j) of DEP-080 and (e)/(g) of DEP-081 (aligned in the PR #2 consistency fixes).
- Production deploys should avoid the 08:00–20:00 facility-local window while OQ-15 is open (TRD 15 §9).
