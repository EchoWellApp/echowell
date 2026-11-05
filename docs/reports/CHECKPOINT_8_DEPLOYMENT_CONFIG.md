# Checkpoint 8 Report — Phase 14A Generate Deployment Configuration & Infrastructure Files

Block 3 "Implement Features", checkpoint 8 of 9, its own PR (branch `feat/cp8-deployment-config`, created from `main` at fa00286 after GitHub PRs #28, #29 and #30 were merged on 5 November 2026) · Prompt: `specs/prompts/Implement_Feature_Batches.md` "Phase 14A" · TRD 25 Phase 9 · Features: FEAT-077..FEAT-087 · Date: 5 November 2026 · Status: in review (GitHub PR #31).

Build order followed roadmap §5.8: [FEAT-077..FEAT-080] → [FEAT-081..FEAT-083] → [FEAT-084, FEAT-085] → [FEAT-086, FEAT-087]. TRDs read in the roadmap order: 15, 16, 21, 22, 12, 17, then SRC-01. Hosting follows the decisions merged in PR #30: Netlify for the frontend, Render for the backend (the existing `echowell-api` service as staging, region `ohio`, Starter; production created later and released manually), Neon `aws-us-east-1` for the database (TRD 24 D-153..D-158).

**Nothing was deployed.** This checkpoint produces configuration, workflows, tests and documentation only (TRD 25 Phase 9 definition of done). No Render, Netlify, Neon or Sentry API was called and no real secret was used.

## 1. Result

| Measure | Value |
|---|---|
| Configuration validation report | 96 checks: 96 PASS, 0 FAIL (`docs/reports/CONFIGURATION_VALIDATION_REPORT.md`) |
| Local demo stack (`docker compose --profile demo up -d --wait db backend frontend-prod`) | all three services healthy; DS-07 seeded; `/api/v1/health` 200 with `"database":"ok"`; `/login` on :3001 200; resident summary 2 / 2 / 0 / 6 |
| Performance budgets (TST-120..TST-124, TST-190) | all pass after three backend fixes (§3); PR-scope budgets: pipeline 120 ms (≤ 5 s), `POST /sessions` p95 541 ms (≤ 1 s), ingest 202 499 ms (≤ 2 s) |
| Post-deploy smoke tests (run against a local stack) | staging set 8 passed, production set 4 passed; HTTPS-only checks skip on http (SEC-065) |
| CI gates | the 7 `ci.yml` jobs of CIC-070 plus `playwright` in `e2e.yml`; `security-audit` green with time-boxed exceptions (Q-1) |

## 2. What was built

| Group | Features | Delivered |
|---|---|---|
| 1 | FEAT-077, FEAT-080 | `backend/Dockerfile` (non-root UID 10001, PYTHONPATH), new multi-stage `frontend/Dockerfile`, `.dockerignore` files, Compose `frontend-prod` service in the `demo` profile and a backend healthcheck; `e2e.yml` (Playwright readonly, mutating and `@isolated` runs; Chromium on PRs, all three browsers nightly; `performance`, `nightly-validation`, `lighthouse`, and an issue on a failing `main`/nightly run); environment-template tests |
| 1 | FEAT-078, FEAT-079 | `ci.yml` with `repo-hygiene`, `backend-lint`, `backend-test` (coverage gates 95 % analytics / 85 % backend, migration round trip, PR performance budgets), `openapi-contract` (OpenAPI and generated-types drift, D-51), `frontend` (bundle budget), `security-audit` (pip, npm, gitleaks, Bandit), `docker-build`; `.gitleaks.toml`, `SECURITY_EXCEPTIONS.md`, `scripts/ci/audit_gate.py`, `scripts/ci/check-bundle.mjs`; `tests/performance/` (DS-08 generator, budget tests), Lighthouse config and login script |
| 2 | FEAT-081..FEAT-083 | `render.yaml` Blueprint (staging `echowell-api`, production `echowell-backend-production`, two cron jobs `0 7,8 * * *` UTC, environment groups, `sync: false` secrets); `netlify.toml` with the TRD 12 §4.9 headers and CSP; `frontend/scripts/check-csp.mjs`; stricter `sslmode` and placeholder-secret startup guards; Blueprint, Netlify, transport, secret and deployed-CORS tests |
| 3–4 | FEAT-084..FEAT-087 | Optional Sentry (`backend/core/monitoring.py`; on only with `SENTRY_DSN` in staging/production; PII scrubbed); `uptime.yml`; `deploy-staging.yml`; `deploy-production.yml` (verify, one approval, Render API and Netlify deploys, smoke, release); `tests/smoke/` with TLS checks; `docs/deployment.md` runbook, `DEPLOYMENT_CONFIGURATION_GUIDE.md` (incl. branch-protection settings), `CONFIGURATION_VALIDATION_REPORT.md`; both checklists reconciled |

## 3. Defects found and fixed

| # | Found by | Problem | Fix |
|---|---|---|---|
| F-1 | Blueprint test | The nightly job validated settings in web mode, so on Render (group variables only, no JWT/CORS) it would exit 1 at startup | `backend/jobs/nightly_run.py` validates in operator mode (DEP-046, SEC-111) |
| F-2 | TST-190 | One ingest API key was capped at 300 requests/minute by the default limit on top of its own 600/minute | Routes with their own limit skip the default (`backend/core/rate_limit.py`); login likewise |
| F-3 | TST-124 | `POST /ingest` made about 5 database round trips per record (1,432 statements for SRC-05; 202 in 1.6–1.9 s, budget 2 s) | Records stored per batch: 24 statements, about 0.5 s |
| F-4 | TST-122 on DS-08 | `GET /residents` p95 720 ms and `GET /analytics` 2,930 ms (budget 500 ms): per-resident queries and a read of every stored day | Batched read models; analytics reads only its window: 218 ms and 294 ms |
| F-5 | `security-audit` | PyJWT 2.9.0 and python-multipart 0.0.17 had advisories | PyJWT 2.15.1, python-multipart 0.0.33 (same majors) |
| F-7 | `docker-build` on GitHub | The frontend image build failed in `next/font/google` (font download during the build; the same download made the `frontend` job flaky earlier) | Source Sans 3 (SIL OFL) is committed as `frontend/app/fonts/SourceSans3-latin-variable.woff2` and loaded with `next/font/local`; builds no longer fetch fonts (Q-13) |
| F-6 | `repo-hygiene`, Bandit | The old facility name in three design docs and a test; Bandit B608 on a constant-key migration statement | Reworded; `# nosec B608` with the existing reason |

API responses are unchanged (contract, DS-07 and validation suites pass; OpenAPI identical).

## 4. Files

- **Created:** `render.yaml`, `frontend/Dockerfile`, `frontend/.dockerignore`, `.github/workflows/{e2e,uptime,deploy-staging,deploy-production}.yml`, `.gitleaks.toml`, `.gitleaksignore`, `SECURITY_EXCEPTIONS.md`, `scripts/ci/`, `frontend/scripts/check-csp.mjs`, `frontend/lighthouserc.json`, `frontend/tests/lighthouse/login.js`, `backend/core/monitoring.py`, `tests/performance/`, `tests/smoke/`, new unit/security tests, `docs/reports/DEPLOYMENT_CONFIGURATION_GUIDE.md`, `docs/reports/CONFIGURATION_VALIDATION_REPORT.md`, this report.
- **Changed:** `backend/Dockerfile`, `.dockerignore`, `docker-compose.yml`, `netlify.toml`, `.github/workflows/ci.yml`, `backend/requirements.txt`, `backend/main.py`, `backend/jobs/nightly_run.py`, `backend/core/{config,db,rate_limit}.py`, ingest and read-model repositories/services, `frontend/package.json`, `docs/deployment.md`, three design docs, both checklists; tracking files.
- **Size:** about 6,000 added lines: about 3,000 tests, about 2,100 configuration and code, about 900 documentation.

## 5. Commands run and results

Environment: Linux container, Python 3.12, PostgreSQL 16 (local cluster), Node 22, Docker Engine 29 (daemon started locally).

| # | Command | Result |
|---|---|---|
| 1 | `pytest -q -p randomly` (whole suite: unit, integration, contract, security, validation; smoke and performance deselected/skipped by design) | 757 passed, 19 skipped (smoke tests without `SMOKE_API_BASE_URL`), 16 deselected (performance) in 4 min 20 s |
| 2 | Full `backend-test` command with coverage | 752 passed; `analytics/` 98 %, `backend/` 96 % (line + branch) |
| 3 | `pytest -p no:randomly tests/performance -m budget` | 3 passed (pipeline 120 ms, `POST /sessions` p95 541 ms, ingest 202 499 ms) |
| 4 | Targeted nightly budgets (TST-122 on DS-08, TST-124, TST-190) | 8 passed after F-2..F-4 |
| 5 | `cd frontend && npx vitest run` | 429 passed; line coverage 99.41 % |
| 6 | `ruff check .`; `ruff format --check .`; `mypy analytics backend`; `lint-imports`; `bandit -r backend analytics -ll` | all clean |
| 7 | `python -m backend.cli export-openapi \| diff - docs/api_reference/openapi.json` | identical |
| 8 | `python scripts/ci/audit_gate.py pip …` / `npm` | 7 and 29 advisories, all excepted until 12 Nov, 0 blocking (Q-1) |
| 9 | gitleaks v8.18.4 over the full history with `.gitleaks.toml` and `.gitleaksignore` | no leaks; a planted fake key is caught |
| 10 | `docker compose config -q` (with `.env.development.example`) | exit 0 |
| 11 | `docker compose --profile demo up -d --wait db backend frontend-prod`, then `seed test_v0_1` and the DS-10 loader | all healthy; health 200, `/login` 200, summary 2 / 2 / 0 / 6 |
| 12 | Backend image checks (`id -u`, `/app` contents, CMD) | UID 10001; only `alembic.ini`, `analytics`, `backend`, `database`; DEP-022 command |
| 13 | `pytest tests/smoke -m smoke` against a local stack | staging set 8 passed; production set 4 passed |
| 14 | actionlint 1.7.12 with shellcheck on the five workflows | 0 errors (6 info notes on intentionally unquoted variables in `e2e.yml`) |
| 15 | `node frontend/scripts/check-csp.mjs` with each Render origin / a wrong origin | 0 / 1 |


## 6. Exit criteria (roadmap §5.8)

| Criterion | Evidence | Result |
|---|---|---|
| Configuration validated against SRC-01 and TRD 22 | validation report sections A, B | PASS |
| Every TRD 21 variable documented | guide §7 (58 names, checked by script) | PASS |
| CI runs unit, integration and validation tests and the frontend build on every PR | `ci.yml` `backend-test`, `frontend` | PASS (first run on this PR) |
| Production templates: `PIPELINE_PROFILE=production`, no `PIPELINE_AS_OF`; `sslmode=require` | validation report C, D; `tests/unit/test_env_templates.py` | PASS |
| Regions Neon `aws-us-east-1`, Render `ohio` | `render.yaml`, guide §3 | PASS |
| CI fails on OpenAPI drift (D-51) | `openapi-contract` job | PASS |
| No deployment performed | — | PASS |
| Branch protection with the 8 required checks | guide §6.2; needs a repository admin | PENDING (Q-3) |
| Algorithm lead approves and merges (D-101) | review | PENDING |

## 7. New OQ and D IDs

None. Decisions from this review will be recorded in TRD 24 from D-159.

## 8. Notes

| # | Note |
|---|---|
| N-1 | Docker image builds inside this container need the sandbox proxy certificate, so the images were built from a scratch copy with that certificate added; the committed Dockerfiles do not contain it. GitHub runners build them directly (`docker-build` job). |
| N-2 | `.gitleaksignore` lists eight historic test-only values by fingerprint (the fingerprints include commit SHAs, so this branch must not be rebased). New tests use low-entropy values. |
| N-3 | `sync: false` inside Render environment groups and `autoDeployTrigger: checksPass` are as TRD 15 specifies; the Blueprint preview in Block 4 confirms them. The existing `echowell-api` service is linked to the Blueprint and moved from Free to Starter in Block 4 (checklist C.02, C.06). |
| N-4 | `GET /alerts` still issues one scores query per alert (p95 384 ms, within budget). |

## 9. Questions for the reviewer

| ID | Question |
|---|---|
| Q-1 | **Security advisories (RSK-16, due now).** Next.js 14.2.35 has 25 critical advisories (several unauthenticated remote-code-execution and request-smuggling issues) and its PostCSS 4 high; Starlette 0.46 (required by FastAPI 0.115) has 7. All fixes need a major upgrade (Next.js 16, FastAPI/Starlette 1.x), which D-105 reserves for you and the repository owner. They are time-boxed exceptions in `SECURITY_EXCEPTIONS.md` until **12 Nov**, after which `security-audit` fails again. I recommend upgrading Next.js before anything is deployed publicly (Netlify previews are public already) and FastAPI/Starlette with it, as a separate PR right after this one. Approve the upgrades, or extend the exceptions? |
| Q-2 | TRD 21 recommends `openssl rand -hex 32` for `JWT_SECRET` but also requires ≥ 16 distinct characters; about 1 in 4 hex secrets has fewer, so a correctly generated secret can be refused. Change the rule (for example ≥ 10 distinct characters) or the generator (`openssl rand -base64 48`)? |
| Q-3 | Branch protection on `main` (1 approval, CODEOWNERS, the 8 required checks, no force-push, no bypass) needs a repository admin; the exact settings are in the guide §6.2. It would also stop direct pushes to `main`. Who sets it, and when? |
| Q-4 | `.gitleaksignore` exempts eight historic test-only values by fingerprint; CIC-115 says the only allow-list entries are the `local-dev-only-*` / `ci-only-*` placeholders. Accept the fingerprints (the alternative is rewriting history)? |
| Q-5 | CIC-111 limits every job to 20 minutes, but the deploy waits (Render deploy, Netlify build, health and build-meta polling) can exceed that, so the deploy workflows are split into several jobs. Agree? |
| Q-6 | FEAT-086-AC-03 says `deploy-production.yml` contains no `secrets.`, but TRD 16 CIC-050 requires `RENDER_API_KEY` and `NETLIFY_AUTH_TOKEN` there. I followed TRD 16. Update the AC? |
| Q-7 | The release workflow verifies the commit (on `main`, all 8 checks green, staging deploy succeeded) *before* the approval step, while TRD 15 §4.10 says after. It is stricter. Agree? |
| Q-8 | TRD 21 ENV-017 and TRD 15 §5 still quote the old resident tiles "2 / 7 / 1 / 19"; D-114 and DEP-080 say 2 / 2 / 0 / 6, which the local run shows. Update those two places? |
| Q-9 | `e2e.yml` choices: Lighthouse on the four pages of CIC-116/TST-125 (FEAT-080-FR-09 names one); robustness run as `python -m tests.validation.robustness` (the TRD path form cannot import); the failure issue also opens for a failed manual run on `main`. Agree? |
| Q-10 | The backend image now runs as a non-root user (DEP-021) and includes `sentry-sdk` (off unless `SENTRY_DSN` is set). The existing `echowell-api` Render service rebuilds from this Dockerfile on the next merge to `main`; the image still starts with the same command. Any concern? |
| Q-11 | The performance fixes change backend code (rate limiting, ingest batching, read models) inside a configuration checkpoint, because the budget tests found the defects. Accept them here? |
| Q-12 | Size: about 6,000 added lines (half tests) for 11 features. Accept as one PR? |
| Q-13 | TRD 04 §4.2 names `next/font/google` for Source Sans 3. The image build on GitHub failed downloading the font, so the font file (SIL Open Font License) is now committed and loaded with `next/font/local`: same font and weights, no network at build time, still self-hosted (FE-192, UX-252). Update TRD 04 §4.2 to `next/font/local`? |
| Q-14 | E2E-15 (TRD 13, FEAT-076-FR-09) expects R11's check-in log to show only "<Mon D> Check-ins started.". R11 is enrolled on 2026-10-01 in the demo overlay and the scenario runs at the current time, so the log correctly also lists every day since enrolment without a record as "Check-in missed." (29 lines on 5 Nov). The test now checks that the newest line is "Check-ins started." and every other line is a missed day. Update E2E-15's wording, or enrol R11 on the run date instead? |
