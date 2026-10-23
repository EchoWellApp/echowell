# FEAT-088 Interim staging and production deployment (synthetic and test data only)

| Field | Value |
|---|---|
| Epic | DevOps & Deployment |
| Build phase | Phase 10 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-087 |
| Status | Not Started |

## Purpose

Execute the Phase 10 deployment on the interim stack: provision Neon, Railway and Netlify per the Phase 9 runbooks, deploy staging (profile `test_v0_1`, fixed `PIPELINE_AS_OF` 2026-10-30T15:00:00-05:00, seeded with the answer-key data) and interim production (profile `production`, `bootstrap`, first admin created interactively, a roster of `T`-prefixed demo study IDs, no `test_v0_1` seed data), verify health, HTTPS, login and the R01–R10 suite on the deployed SHA, and write `docs/reports/DEPLOYMENT_REPORT.md` stating that this is a synthetic-data interim deployment, not a go-live.

## Business Context

- BR-17 and VIS-016: EchoWell runs on Netlify, Railway and Neon until the AWS budget is approved (OQ-07).
- BR-15: staging reproduces the answer key and shows the full dashboard (DEP-093, D-59).
- BR-16, VIS-024, D-28: only synthetic and test data on the interim stack; production never contains `test_v0_1` seed data (DEP-007, DEP-073).
- SRC-15 demo steps 4–5 need interim production to receive a live demo check-in under a `T`-prefixed study ID (D-59, FEAT-090).

## Referenced TRDs

- TRD 15 DEP-001..DEP-009, DEP-030..DEP-034, DEP-040..DEP-045, DEP-050..DEP-054, DEP-070..DEP-075, DEP-080, DEP-081, DEP-093, DEP-118, §4.4, §4.5, §4.6, §4.8, §4.9, §4.10.
- TRD 01 ARC-080, ARC-081, ARC-082, ARC-083, ARC-084.
- TRD 00 VIS-016, VIS-024.
- TRD 25 §4.6 Phase 10 (definition of done, commands, pitfalls), AGT-014, AGT-015, AC-AGT-04, AC-AGT-10.
- TRD 21 ENV-050, ENV-051, §4.7 matrix.
- TRD 12 SEC-001, SEC-003, SEC-004, SEC-017.
- TRD 13 TST-152, MVP-08, MVP-15.
- TRD 24 D-28, D-47, D-54, D-59, D-60, D-72.
- TRD 22 TPS-040 (organisation two-factor authentication).

## Scope

- Neon: project `echowell`, PostgreSQL 16, `aws-us-east-1`, database branch `main` (production) and child database branch `staging`; owner-role extensions and `timezone` UTC; group and login roles with generated passwords; pooled and direct URLs recorded only in Railway variables and `STAGING_DATABASE_URL`.
- Railway: project `echowell`, environments `production` (automatic deploys disabled; deployed by `deploy-production.yml`) and `staging` (source branch `main`, Wait for CI), services `backend` (from `/railway.toml`) and `nightly` (from `/railway.nightly.toml`), variables per TRD 21 §4.7, public domains recorded in `docs/deployment.md` and in the repository variables `PRODUCTION_API_BASE_URL` and `STAGING_API_BASE_URL`, usage hard limit.
- Netlify: staging site `echowell-und-staging` (production branch `main`, deploy previews) and production site `echowell-und` (builds stopped, published by `deploy-production.yml`); per-site `NEXT_PUBLIC_API_BASE_URL` and `NEXT_PUBLIC_APP_ENV`; repository variables `PRODUCTION_FRONTEND_URL` and `STAGING_FRONTEND_URL`.
- GitHub: environment `staging` (branch rule `main`) with the five secrets; environment `production` with branch rule `main`, a required reviewer, the secrets `RAILWAY_PRODUCTION_TOKEN` and `NETLIFY_AUTH_TOKEN` and the variable `NETLIFY_PRODUCTION_SITE_ID`.
- Staging data: `deploy-staging.yml` re-seed (`seed test_v0_1 --reset` and the DS-10 loader) with PIPELINE_AS_OF 2026-10-30T15:00:00-05:00.
- Production bootstrap: `python -m backend.cli bootstrap`; first admin via `railway run --environment production python -m backend.cli create-user --email <admin email> --display-name <name> --role admin` with an interactive password; demo roster of `T`-prefixed study IDs (e.g. `T01`) and test devices via `import-master-data`; API keys for test devices or harnesses only (`create-api-key`).
- Verification and `docs/reports/DEPLOYMENT_REPORT.md` ending in "DEPLOYMENT SUCCESSFUL" or "DEPLOYMENT FAILED" with evidence.

## Out of Scope

- Real residents, real devices at Edgewood or any go-live step (AGT-014, DEP-118; go-live is FEAT-092 on AWS).
- Backups, restore drill and rollback rehearsal (FEAT-089); demo acceptance (FEAT-090).
- Changes to requirements or application logic, except to fix a deployment-specific defect, which must be reported (TRD 25 §4.6 Phase 10 Pitfalls).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-088-FR-01 | The system shall be deployed to exactly the environments `staging` and `production` (plus `local`), identified by APP_ENV, each with its own Neon database branch, Railway environment and Netlify site. | DEP-001, DEP-004, DEP-005, ARC-080 |
| FEAT-088-FR-02 | Staging shall be deployed from `main` on every merge through the Netlify and Railway GitHub integrations; production frontend and backend shall be deployed only by an approved manual `deploy-production.yml` run for a chosen `main` commit, tagged `vX.Y.Z`. | DEP-002, DEP-003, DEP-004 |
| FEAT-088-FR-03 | Staging shall run PIPELINE_PROFILE=`test_v0_1` with PIPELINE_AS_OF=2026-10-30T15:00:00-05:00 and be seeded with `seed test_v0_1 --reset` from the deploy-staging re-seed step. | D-59, DEP-074, TRD 21 §4.7 |
| FEAT-088-FR-04 | Production shall run PIPELINE_PROFILE=`production`, PIPELINE_AS_OF empty, DATABASE_READONLY_URL unset and DATA_SOURCE_LABEL `demo data (synthetic)`. | AGT-015, SEC-116, SEC-004, TRD 21 §4.7 |
| FEAT-088-FR-05 | Production shall contain only the facility row, `config_parameters`, users, API keys and data received from devices or CSV upload of team test check-ins under `T`-prefixed demo study IDs; no row with `ingest_batches.source = seed` and no `test_v0_1` data. | DEP-007, DEP-008, DEP-073, DEP-093 |
| FEAT-088-FR-06 | `python -m backend.cli bootstrap` shall be run on production (idempotent); the first production admin shall be created only with `railway run --environment production python -m backend.cli create-user --email <admin email> --display-name <name> --role admin`, the password entered interactively and never written to a file, shell history or chat. | DEP-072, DEP-075, SEC-017 |
| FEAT-088-FR-07 | Each environment shall have its own JWT_SECRET, API keys and users; a staging credential shall be rejected by production. | DEP-006, ENV-051 |
| FEAT-088-FR-08 | Interim API keys shall be issued only to test devices or harnesses, never to devices deployed at Edgewood. | SEC-003, AGT-014 |
| FEAT-088-FR-09 | Migrations shall run only as the Railway pre-deploy command `alembic upgrade head`, never by hand against the target. | DEP-060, ARC-082, TRD 25 §4.6 Phase 10 Commands |
| FEAT-088-FR-10 | Health shall return `status` ok with `database` ok and `version` = deployed SHA in both environments; the frontend shall load over HTTPS; login shall work; staging and production smoke tests shall pass. | ARC-083, DEP-080, DEP-081, TST-152 |
| FEAT-088-FR-11 | The R01–R10 suite (`pytest tests/validation -q`) shall pass in CI on the deployed commit. | TRD 25 §4.6 Phase 10 DoD, AC-AGT-04 |
| FEAT-088-FR-12 | Regions shall be Neon `aws-us-east-1` and Railway US East. | ARC-084, D-54 |
| FEAT-088-FR-13 | `docs/reports/DEPLOYMENT_REPORT.md` shall end in "DEPLOYMENT SUCCESSFUL" or "DEPLOYMENT FAILED" with evidence, state that the deployment is a synthetic-data interim deployment and not a go-live, and state that no real resident data was loaded. | TRD 25 §4.6 Phase 10 Outputs and DoD, AC-AGT-10, VIS-024 |
| FEAT-088-FR-14 | Every deviation from the TRD 21 §4.7 matrix shall be recorded in `docs/deployment.md` with a reason. | ENV-050 |
| FEAT-088-FR-15 | Before the first deployment, two-factor authentication shall be required for all members of the `EchoWellApp` GitHub organisation, verified in the organisation settings and recorded in DEPLOYMENT_CHECKLIST.md A.04. | TPS-040 |

## Inputs

- Phase 9 artefacts and runbooks (FEAT-077..FEAT-087), team-owned Netlify, Railway and Neon accounts (TRD 22), the `main` commit chosen for the release.
- Synthetic data only: SRC-05 via the staging re-seed; demo roster CSVs with `T`-prefixed IDs.

## Outputs

- Running staging and interim production environments.
- `docs/deployment.md` updated with actual names (site, domains), plan limits and verification dates.
- `docs/reports/DEPLOYMENT_REPORT.md`.

## Data Flow

Merge to `main` → Railway staging pre-deploy migration → backend start → healthcheck → Netlify staging-site deploy → `deploy-staging.yml` re-seed and smoke → algorithm lead reviews staging (tiles 2 / 7 / 1 / 19, R09 alarm). Manual `deploy-production.yml` run for that commit, approved by the required reviewer → `railway up` and Netlify CLI production deploy → smoke and tag → `bootstrap`, `create-user`, demo roster → manual authenticated check → report.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-087

- [FEAT-087](FEAT-087-Deployment-Documentation-And-Readiness-Checklists.md) Deployment documentation and readiness checklists (the runbooks and checklist this feature executes).

Features that build directly on this one (BACKLOG.md §4): FEAT-089, FEAT-090.

## Database Impact

- Neon `staging`: full schema via Alembic; `test_v0_1` data (roster, users, API key `test-ingest`, SRC-05 ingest, pipeline outputs, `evaluation_ground_truth`).
- Neon `main`: full schema; `facilities`, `config_parameters` (bootstrap), `users`, `api_keys`, `residents`/`devices`/`device_assignments` for `T`-prefixed demo IDs; `audit_logs` rows `user.created`, `api_key.created`, `roster.loaded`.
- No manual DDL (DEP-060).

## API Impact

- Consumed for verification: `GET /api/v1/health`, `POST /api/v1/auth/login`, the staging smoke endpoints (FEAT-086).
- Exposed: the full TRD 19 API at the Railway domains; no change.

## Frontend Impact

- Netlify production and staging sites serving all routes; staging header shows "pipeline test data v0.1", production "demo data (synthetic)" (SEC-004).

## Analytics Impact

- Staging runs the pipeline with `test_v0_1` at the fixed as-of; production with `production` (baseline_n 30) at request time; nightly runs via the `nightly` cron service (D-47). No algorithm change.

## Security Requirements

- Hard rule: no real resident data, no Edgewood devices (AGT-014, SEC-001, SEC-003, DEP-008).
- `test_v0_1` refused in production (AGT-015); seeding refused in production (DEP-070).
- Secrets entered only in platform stores (FEAT-083); first admin password interactive only (DEP-075).
- TLS everywhere, HSTS, `sslmode=require` (DEP-009, DEP-034, DEP-045).

## Error Handling

- Failed pre-deploy migration or healthcheck → previous deployment stays live (DEP-041, DEP-065); fix forward by PR.
- Failed production smoke → rollback decision within 30 minutes (TRD 15 §4.10 step 5, §4.12).
- If cloud is not passing DEP-081 by 5 Nov 2026, the demo uses the local Compose fallback (RSK-12, DEP-090; FEAT-090).
- Report ends "DEPLOYMENT FAILED" with the failing items when the definition of done is not met; Phase 11 does not start (TRD 25 §8).

## Logging Requirements

- Railway logs JSON to stdout; `nightly_run_missing` and pipeline failures visible as in FEAT-056.
- Audit rows for bootstrap-created users and keys and the staging `seed.reset`.
- The report records commands run and their results (AGT-022).

## Testing Requirements

- Post-deploy smoke tests DEP-080 (staging) and DEP-081 (production) via FEAT-086; TLS check SEC-066.
- `pytest tests/validation -q` on the deployed SHA (CI).
- Credential separation check: staging JWT against production `/api/v1/auth/me` returns 401 (DEP-006).
- SQL check in production: `SELECT count(*) FROM raw_sessions r JOIN ingest_batches b ON r.ingest_batch_id = b.id WHERE b.source = 'seed'` returns 0 (DEP-073, AC-DEP-05).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-088-AC-01 | `curl -fsS "$BACKEND_URL/api/v1/health"` returns `status` ok, `database` ok and `version` = deployed SHA for staging and production. Verified by: Test (run the command in the criterion against the stated environment and check the stated result). | TRD 25 §4.6 Phase 10 DoD, ARC-083 |
| FEAT-088-AC-02 | `curl -fsSI "$FRONTEND_URL/residents"` succeeds over HTTPS for both environments. Verified by: Test (run the command in the criterion against the stated environment and check the stated result). | TRD 25 §4.6 Phase 10 Commands |
| FEAT-088-AC-03 | `deploy-staging.yml` and `deploy-production.yml` are green on the deployed commits. Verified by: Inspection (review of `deploy-staging.yml` against the cited requirements). | AC-DEP-03, AC-DEP-04 |
| FEAT-088-AC-04 | Production `raw_sessions` has zero rows linked to `ingest_batches.source = 'seed'`. Verified by: SQL check in production (`SELECT count(*) FROM raw_sessions r JOIN ingest_batches b ON r.ingest_batch_id = b.id WHERE b.source = 'seed'` returns 0 (DEP-073, AC-DEP-05)). | AC-DEP-05, DEP-073 |
| FEAT-088-AC-05 | Starting production with PIPELINE_PROFILE=`test_v0_1` (tested on a throwaway deployment or locally with the same variables) is refused. Verified by: Test (the test method of AGT-015, applied to the condition stated in the criterion). | AGT-015, AC-AGT-05 |
| FEAT-088-AC-06 | The interim Neon project contains no resident_code outside `R01`–`R10` (staging seed) and `T`-prefixed demo IDs. Verified by: Inspection (the inspection method of DEP-008, applied to the condition stated in the criterion). | AC-DEP-11, DEP-008 |
| FEAT-088-AC-07 | `docs/reports/DEPLOYMENT_REPORT.md` exists, ends with "DEPLOYMENT SUCCESSFUL" or "DEPLOYMENT FAILED", and contains the sentences that it is a synthetic-data interim deployment, not a go-live, and that no real resident data was loaded. Verified by: Inspection (review of `docs/reports/DEPLOYMENT_REPORT.md` against the cited requirements). | AC-AGT-10, AC-AGT-07 |
| FEAT-088-AC-08 | A JWT issued by staging is rejected (401) by production. Verified by: Test (staging JWT against production `/api/v1/auth/me` returns 401 (DEP-006)). | DEP-006 |

## Definition of Done

- All FEAT-088 acceptance criteria pass; `specs/backlog/DEPLOYMENT_CHECKLIST.md` evidence columns filled for the Phase 10 items.
- The Block 4 PR (Phase 10, with FEAT-089, FEAT-090) approved by the algorithm lead (AGT-013).

## Implementation Notes

- Read TRD 15, 22, 21, 17, 13 in that order before starting (TRD 25 §4.4 "Deploy").
- Disable Railway app sleeping on demo days (DEP-042).
- If default domain names are taken, record the generated names in `docs/deployment.md` and the repository variables, and raise a TRD 12 §4.9 change for `connect-src` (FEAT-082 note).
- The demo check-in on production uses the production profile (baseline_n 30), so the demo resident shows "Baseline forming · 1 of 30 sessions" (TST-184).
