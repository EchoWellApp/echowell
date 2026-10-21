# 16 CI/CD Pipeline Specification

Document ID: ECHOWELL-TRD-16 · Version 0.11 (draft for review) · Date: 18 October 2026 · Owner: Team 2 · Status: Draft

## 1. Purpose

This document specifies the GitHub Actions continuous integration and deployment verification pipeline for the
EchoWell monorepo: which workflows exist, when they run, which jobs and commands they execute, what must pass
before code is merged or deployed, which secrets they use, what they publish as artifacts and how long they may
take. It implements the CI/CD responsibilities of SRC-01 ("on every pull request or merge: run unit tests, run
integration tests, run algorithm validation tests, build frontend, validate backend") and the "GitHub Actions
workflows / test automation workflows / deployment workflows" output of Phase 14A (SRC-17).

## 2. Scope

**In scope**

- Workflows `ci.yml`, `e2e.yml`, `deploy-staging.yml`, `deploy-production.yml`, `uptime.yml` in `.github/workflows/`.
- Backend and analytics linting, typing, tests (unit, integration, validation R01–R10) with a PostgreSQL service.
- Frontend lint, typecheck, unit tests, build; Playwright E2E against the Docker Compose stack.
- OpenAPI contract check, dependency audits, repository hygiene checks (no audio files, no secrets, no `.env`).
- Required status checks for branch protection, caching, artifacts, secrets and time budgets.
- Choice of deployment mechanism (platform GitHub integrations for staging, a manual approved release workflow for production) and its justification.

**Out of scope**

- Test case content (TRD 13, TRD 14), deployment procedures (TRD 15), branch and review policy (TRD 18),
  environment variable semantics (TRD 21).
- AWS deployment pipeline (TRD 15 §4.16): the same workflows apply with URLs changed; an AWS OIDC deploy job is
  added only at cut-over.

## 3. References

| ID | Reference |
|---|---|
| SRC-01 | Deployment Architecture — CI/CD section, GitHub → Netlify, GitHub → Railway |
| SRC-03 / SRC-04 / SRC-05 | Workbook answer key, generator script, input CSV (validation suite inputs) |
| SRC-17 | Implement_Feature_Batches.md Phases 8, 12, 14A, 14B, 15 (ALGORITHM_VALIDATION_REPORT.md) |
| D-OWNER-3 | AWS target / interim stack decision |
| TRD 13 | Testing Strategy and Acceptance Criteria (test pyramid, coverage policy) |
| TRD 14 | Test Data and Validation (R01–R10 validation suite) |
| TRD 15 | Deployment and DevOps (staging deploy from `main`, manual production release, smoke tests, Railway "Wait for CI") |
| D-99 | TRD 24: branching is `main` plus short-lived feature branches only; staging deploys from `main`; production only through the manual release workflow (PR #2 review) |
| TRD 17 | Logging, Monitoring and Error Handling (uptime check) |
| TRD 18 | GitHub Repository Standards (branch protection, Conventional Commits) |
| TRD 19 | API Contracts / OpenAPI (committed contract file) |
| TRD 21 | Environment Configuration |

## 4. Requirements

### 4.1 Deployment mechanism decision

**Decision (TRD 24 D-99):** the repository has only `main` and short-lived feature branches; pull requests target
`main`. **Staging** is deployed by the **platform GitHub integrations** on every merge to `main` (the Netlify staging
site builds `main` and PR deploy previews; the Railway `staging` environment builds `main` with "Wait for CI");
`deploy-staging.yml` then verifies it, re-seeds the staging database when needed and runs the staging smoke tests.
**Production** is deployed only by a deliberate manual release: a `workflow_dispatch` run of `deploy-production.yml` for a
chosen `main` commit, gated by the GitHub environment `production` with a required reviewer. That run checks the commit
("Wait for CI" semantics), deploys the Railway production services with `railway up`, publishes the Netlify production
site with `netlify deploy --build --prod`, runs the production smoke tests (TRD 15 §4.11) and tags `vX.Y.Z`.

**Justification:**

1. SRC-01 specifies "GitHub → Netlify" and "GitHub → Railway"; the native integrations are the literal implementation for
   staging, and the release workflow builds production from the same repository commit.
2. A merge to `main` can never reach production by accident: the production site's builds are stopped and the Railway
   production services have no GitHub trigger; only an approved release run deploys them.
3. The only platform deploy tokens in GitHub are the two secrets of the `production` environment (CIC-090); they are
   released to a job only after the required reviewer approves it, and they give no access to the production database
   URL or application secrets (BR-16).
4. Railway "Wait for CI" makes a staging deploy conditional on green checks; the release workflow refuses a commit whose
   required checks or staging deploy did not succeed (CIC-053).
5. Platform-native rollback ("publish previous deploy" / "redeploy") stays available (TRD 15 §4.12).
6. Migrations run as the Railway pre-deploy command (`alembic upgrade head`, TRD 15 DEP-040), also for `railway up`
   deploys, so no workflow needs the production database URL.

```mermaid
sequenceDiagram
  participant Dev as Developer
  participant GH as GitHub (PR / main)
  participant CI as ci.yml
  participant NF as Netlify
  participant RW as Railway
  participant DS as deploy-staging.yml
  participant DV as deploy-production.yml
  Dev->>GH: open PR (feature branch to main)
  GH->>CI: pull_request
  CI-->>GH: required checks green
  GH->>NF: deploy preview (staging site, staging API)
  Dev->>GH: merge to main
  GH->>CI: push main
  GH->>NF: staging site build + publish
  CI-->>RW: checks green (Wait for CI)
  RW->>RW: staging: build image, pre-deploy alembic upgrade head, start uvicorn, healthcheck
  GH->>DS: push main
  DS->>DS: wait for sha, re-seed if needed, staging smoke tests
  Dev->>DV: workflow_dispatch (sha, version), reviewer approves
  DV->>DV: verify sha on main, checks green, staging run green
  DV->>RW: railway up (production)
  DV->>NF: netlify deploy --build --prod (production site)
  DV->>DV: wait for sha, production smoke tests, tag vX.Y.Z, GitHub Release
```

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| CIC-001 | Code shall be deployed to the staging environment only through the Netlify and Railway GitHub integrations watching `main`, and to production only by an approved manual run of `deploy-production.yml`; no other workflow shall hold a Netlify or Railway deploy token (D-99). | Must | BR-17, SRC-01, BR-16, D-99 | Inspection |
| CIC-002 | Workflow files shall be: `.github/workflows/ci.yml`, `e2e.yml`, `deploy-staging.yml`, `deploy-production.yml`, `uptime.yml`; no other workflow shall be added without a TRD change. | Must | SRC-17 Phase 14A | Inspection |
| CIC-003 | Database migrations shall never be executed by a GitHub Actions workflow against production; they run only as the Railway pre-deploy command (TRD 15 DEP-040, DEP-060). | Must | BR-16, TRD 15 | Inspection |

### 4.2 Workflow `ci.yml`

Triggers: `pull_request` (all PRs; they target `main`), `push` to `main`, `workflow_dispatch`.
Concurrency: group `ci-${{ github.ref }}`, `cancel-in-progress: true` for pull requests only.
Permissions: `contents: read` (default for all jobs).

Jobs (run in parallel unless noted):

| Job id | Purpose | Key commands | Time budget |
|---|---|---|---|
| `repo-hygiene` | Policy checks | audio-file check, `.env` check, file size check, forbidden-term check ("Edge4Care", "diagnoses", "severity"), LLM-dependency check, Conventional Commit title check (PR only) | 1 min |
| `backend-lint` | Static checks | `ruff check .`, `ruff format --check .`, `mypy analytics backend`, `lint-imports` (import-linter: `analytics/` purity, TRD 01 ARC-041) | 3 min |
| `backend-test` | Pytest with PostgreSQL | `alembic upgrade head`; `pytest -p no:randomly tests/unit tests/integration tests/contract tests/security tests/validation --cov=analytics --cov=backend --cov-report=xml:build/coverage.xml --junitxml=build/junit.xml --validation-report=docs/reports/ALGORITHM_VALIDATION_REPORT.md`; coverage gates | 8 min |
| `openapi-contract` | API contract unchanged unless intended | `python -m backend.cli export-openapi > /tmp/openapi.json`; `diff -u docs/api_reference/openapi.json /tmp/openapi.json`; regenerate `frontend/lib/api-types.ts` with `openapi-typescript` and `git diff --exit-code` | 2 min |
| `frontend` | Frontend quality and build | `npm ci`, `npm run lint`, `npm run typecheck`, `npm run format:check`, `npm run test:coverage`, `npm run build` | 6 min |
| `security-audit` | Known vulnerabilities, secrets, insecure code | `pip-audit -r backend/requirements.txt -r backend/requirements-dev.txt`, `npm audit --audit-level=high --omit=dev`, `gitleaks detect` (8.x), `bandit -r backend analytics -ll` | 3 min |
| `docker-build` | Images build | `docker build -f backend/Dockerfile .`; `docker build frontend`; image check (non-root, no `.env`, no `tests/`) | 5 min |

Outline:

```yaml
name: CI
on:
  pull_request:
  push:
    branches: [main]
  workflow_dispatch:
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}
permissions:
  contents: read
env:
  PYTHON_VERSION: "3.12"
  NODE_VERSION: "20"
jobs:
  repo-hygiene:
    runs-on: ubuntu-24.04
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v4
      - name: No audio files
        run: |
          if git ls-files | grep -Ei '\.(wav|mp3|flac|m4a|ogg|opus|aac|wma|aif|aiff|amr|webm|caf|pcm)$'; then
            echo "::error::Audio files are forbidden in this repository"; exit 1; fi
      - name: No env files
        run: |
          if git ls-files | grep -E '(^|/)\.env($|\.)' | grep -v '\.example$'; then
            echo "::error::.env files must not be committed"; exit 1; fi
      - name: File size limit 10 MB
        run: |
          git ls-files -z | xargs -0 du -k | awk '$1 > 10240 {print; bad=1} END {exit bad}'
      - name: Forbidden terms (TRD 00 VIS-008, TRD 03 NFR-067)
        run: |
          if git grep -n -I -i "edge4care" -- . ':!specs/' ':!docs/reports/'; then
            echo "::error::'Edge4Care' must not be used (the facility is Edgewood)"; exit 1; fi
          if git grep -n -I -w -i -E "diagnoses|severity" -- frontend/app frontend/components frontend/lib/wording.ts; then
            echo "::error::Forbidden wording in UI copy (detection, not diagnosis)"; exit 1; fi
      - name: No LLM SDK dependencies (TRD 12 SEC-128, TRD 03 NFR-115)
        run: |
          if grep -n -i -E "^(openai|anthropic|langchain[a-z_-]*|google-generativeai|cohere|mistralai)([=<>~ !\[]|$)" backend/requirements*.txt; then
            echo "::error::LLM SDKs are not allowed"; exit 1; fi
          if grep -n -E '"(openai|@anthropic-ai/[a-z-]+|langchain|@langchain/[a-z-]+|@google/generative-ai|cohere-ai|@mistralai/[a-z-]+)"' frontend/package.json; then
            echo "::error::LLM SDKs are not allowed"; exit 1; fi
      - name: PR title is a Conventional Commit
        if: github.event_name == 'pull_request'
        env: { TITLE: "${{ github.event.pull_request.title }}" }
        run: |
          echo "$TITLE" | grep -Eq '^(feat|fix|docs|chore|refactor|test|ci|build|perf|release)(\([a-z0-9-]+\))?!?: .{3,}$'
  backend-lint:
    runs-on: ubuntu-24.04
    timeout-minutes: 8
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: pip
          cache-dependency-path: backend/requirements*.txt
      - run: pip install -r backend/requirements.txt -r backend/requirements-dev.txt
      - run: ruff check .
      - run: ruff format --check .
      - run: mypy analytics backend
      - run: lint-imports    # import-linter contracts in pyproject.toml [tool.importlinter] (TRD 01 ARC-041, AC-ARC-01)
  backend-test:
    runs-on: ubuntu-24.04
    timeout-minutes: 15
    services:
      postgres:
        image: postgres:16-alpine
        env: { POSTGRES_USER: echowell, POSTGRES_PASSWORD: ci-only-postgres, POSTGRES_DB: echowell_test }
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U echowell -d echowell_test"
          --health-interval 5s --health-retries 10
    env:
      APP_ENV: test
      PGPASSWORD: ci-only-postgres               # superuser, used only by the provisioning step
      ECHOWELL_MIGRATOR_DB_PASSWORD: ci-only-migrator # CI-only throwaway values (ephemeral service container)
      ECHOWELL_APP_DB_PASSWORD: ci-only-app
      ECHOWELL_READONLY_DB_PASSWORD: ci-only-readonly
      DATABASE_URL: postgresql+psycopg://echowell_app_login:ci-only-app@localhost:5432/echowell_test
      DATABASE_MIGRATION_URL: postgresql+psycopg://echowell_migrator_login:ci-only-migrator@localhost:5432/echowell_test
      DATABASE_READONLY_URL: postgresql+psycopg://echowell_readonly_login:ci-only-readonly@localhost:5432/echowell_test
      FACILITY_NAME: Edgewood
      FACILITY_TZ: America/Chicago
      PIPELINE_PROFILE: test_v0_1
      CORS_ORIGINS: http://localhost:3000
      LOG_FORMAT: json
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: pip
          cache-dependency-path: backend/requirements*.txt
      - run: pip install -r backend/requirements.txt -r backend/requirements-dev.txt
      - run: echo "JWT_SECRET=$(openssl rand -hex 32)" >> "$GITHUB_ENV"
      - run: psql -h localhost -U echowell -d echowell_test -v ON_ERROR_STOP=1 -f database/roles/provision_login_roles.sql   # as superuser: extensions + timezone UTC (D-72), then roles
      - run: alembic upgrade head
      - run: alembic downgrade base && alembic upgrade head   # migrations reversible in test
      - run: >
          pytest -p no:randomly tests/unit tests/integration tests/contract tests/security tests/validation
          --cov=analytics --cov=backend --cov-branch --cov-report=xml:build/coverage.xml
          --cov-report=html:build/htmlcov --junitxml=build/junit.xml
          --validation-report=docs/reports/ALGORITHM_VALIDATION_REPORT.md
      - run: coverage report --include='analytics/*' --fail-under=95
      - run: coverage report --include='backend/*' --fail-under=85
      - if: always()
        uses: actions/upload-artifact@v4
        with:
          name: backend-reports
          path: |
            build/
            docs/reports/ALGORITHM_VALIDATION_REPORT.md
            docs/reports/validation_results.json
          retention-days: 30
  openapi-contract:
    runs-on: ubuntu-24.04
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12", cache: pip, cache-dependency-path: backend/requirements*.txt }
      - run: pip install -r backend/requirements.txt
      - run: APP_ENV=test JWT_SECRET=$(openssl rand -hex 32) DATABASE_URL=postgresql+psycopg://x:x@localhost/x python -m backend.cli export-openapi > /tmp/openapi.json
      - run: diff -u docs/api_reference/openapi.json /tmp/openapi.json
      - run: npx --yes openapi-typescript@7 docs/api_reference/openapi.json -o frontend/lib/api-types.ts && git diff --exit-code frontend/lib/api-types.ts
  frontend:
    runs-on: ubuntu-24.04
    timeout-minutes: 12
    defaults: { run: { working-directory: frontend } }
    env: { NEXT_PUBLIC_API_BASE_URL: "http://localhost:8000", NEXT_PUBLIC_APP_ENV: local, NEXT_TELEMETRY_DISABLED: "1" }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20", cache: npm, cache-dependency-path: frontend/package-lock.json }
      - run: npm ci
      - run: npm run lint
      - run: npm run typecheck
      - run: npm run format:check   # Prettier (TRD 04 FE-202, TRD 18 GIT-042)
      - run: npm run test:coverage  # = vitest run --coverage; thresholds in vitest.config.ts (TRD 04 FE-180)
      - run: npm run build
      - run: npm run check:bundle  # initial JS per dashboard route ≤ 300 KB gzip (TRD 03 NFR-012, TRD 13 TST-191)
      - uses: actions/upload-artifact@v4
        with: { name: frontend-coverage, path: frontend/coverage/, retention-days: 30 }
  security-audit:
    runs-on: ubuntu-24.04
    timeout-minutes: 8
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }   # full history for gitleaks
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install pip-audit
      - run: pip-audit -r backend/requirements.txt -r backend/requirements-dev.txt
      - uses: actions/setup-node@v4
        with: { node-version: "20" }
      - run: npm audit --audit-level=high --omit=dev
        working-directory: frontend
      - name: Secret scan (TRD 12 SEC-052)
        run: docker run --rm -v "$PWD:/repo" ghcr.io/gitleaks/gitleaks:v8.18.4 detect --source /repo --redact --no-banner
      - name: Bandit (TRD 12 SEC-153)
        run: pip install "bandit==1.7.*" && bandit -r backend analytics -ll -q
  docker-build:
    runs-on: ubuntu-24.04
    timeout-minutes: 12
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/build-push-action@v6
        with:
          context: .
          file: backend/Dockerfile
          load: true
          tags: echowell-backend:ci
          cache-from: type=gha,scope=backend
          cache-to: type=gha,mode=max,scope=backend
      - run: |
          test "$(docker run --rm --entrypoint id echowell-backend:ci -u)" = "10001"
          ! docker run --rm --entrypoint sh echowell-backend:ci -c 'ls -a /app' | grep -E '^(\.env|tests|specs|frontend)$'
      - uses: docker/build-push-action@v6
        with:
          context: frontend
          load: true
          tags: echowell-frontend:ci
          cache-from: type=gha,scope=frontend
          cache-to: type=gha,mode=max,scope=frontend
```

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| CIC-010 | `ci.yml` shall run on every pull request, on every push to `main`, and on manual dispatch. | Must | SRC-01 CI/CD | Inspection |
| CIC-011 | `backend-lint` shall fail on any `ruff check` finding, any `ruff format --check` difference, or any `mypy` error (strict mode for `analytics/`, TRD 18). | Must | TRD 18 | Test |
| CIC-012 | `backend-test` shall run against a `postgres:16-alpine` service container, never against SQLite, so integration tests exercise PostgreSQL-specific behaviour (jsonb, triggers, roles). | Must | contract §3, TRD 13 | Inspection |
| CIC-013 | `backend-test` shall run the unit, integration and validation suites (`tests/unit`, `tests/integration`, `tests/validation`) in one pytest invocation and fail if any test fails or errors. | Must | SRC-01, BR-15 | Test |
| CIC-014 | The validation suite shall compare pipeline output against the SRC-03 answer key for R01–R10 with absolute tolerance 1e-6 and exact string match for statuses, reasons and alarm states; any mismatch shall fail the job. | Must | BR-15, SRC-03, TRD 14 | Test |
| CIC-015 | `backend-test` shall first run `database/roles/provision_login_roles.sql` as the service superuser (creating the extensions `pgcrypto` and `btree_gist` before any migration, TRD 24 D-72, then `echowell_migrator_login`, `echowell_app_login`, `echowell_readonly_login`, TRD 20 §4.3, TRD 15 §4.2; passwords are CI-only throwaway values in the workflow env), then run all tests with DATABASE_URL = `echowell_app_login`, DATABASE_MIGRATION_URL = `echowell_migrator_login` and DATABASE_READONLY_URL = `echowell_readonly_login`; it shall then apply `alembic upgrade head`, then `alembic downgrade base` and `alembic upgrade head` again, failing on any migration error; migrations run as `echowell_migrator` and never create or drop extensions (D-72). | Must | TRD 06, TRD 15 DEP-060 | Test |
| CIC-016 | Line coverage shall be at least 95 % for `analytics/` and at least 85 % for `backend/`; the job shall fail below either gate. | Must | contract R7, TRD 13 | Test |
| CIC-017 | The `frontend` job shall run `npm ci`, `npm run lint` (ESLint, zero warnings allowed: `--max-warnings=0`), `npm run typecheck` (`tsc --noEmit`), `npm run format:check` (`prettier --check .`), `npm run test:coverage` (`vitest run --coverage`: Vitest + React Testing Library with `@vitest/coverage-v8`, line coverage at least 80 % per `vitest.config.ts`, TRD 04 FE-180) and `npm run build`, failing on any non-zero exit. | Must | contract §3, TRD 04, TRD 13 | Test |
| CIC-018 | The `openapi-contract` job shall fail when the OpenAPI document generated from the backend differs from the committed `docs/api_reference/openapi.json`; intentional API changes shall update `docs/api_reference/openapi.json` and the generated `frontend/lib/api-types.ts` in the same PR; the job shall also fail if `frontend/lib/api-types.ts` differs from the output of openapi-typescript. | Must | TRD 19 | Test |
| CIC-019 | The `security-audit` job shall fail on any known vulnerability reported by `pip-audit` for runtime or dev requirements and on any `high` or `critical` advisory reported by `npm audit --omit=dev`. | Must | BR-16, TRD 12 | Test |
| CIC-020 | The `repo-hygiene` job shall fail if any tracked file has an audio extension (wav, mp3, flac, m4a, ogg, opus, aac, wma, aif, aiff, amr, webm, caf, pcm). | Must | BR-01, contract §2, TRD 18 | Test |
| CIC-021 | The `repo-hygiene` job shall fail if any tracked file is named `.env` or `.env.*` other than `*.example`, or if any tracked file exceeds 10 MB. | Must | BR-16, TRD 18 | Test |
| CIC-022 | The `repo-hygiene` job shall fail a pull request whose title is not a Conventional Commit header (types: feat, fix, docs, chore, refactor, test, ci, build, perf, release). | Must | TRD 18 | Test |
| CIC-023 | The `docker-build` job shall build both images and fail if the backend image runs as root or contains `.env`, `tests/`, `specs/` or `frontend/` under `/app`. | Must | TRD 15 DEP-021 | Test |
| CIC-024 | Workflows shall use `permissions: contents: read` by default; only `deploy-production.yml` shall request `contents: write` (for tags and releases). | Must | BR-16 | Inspection |
| CIC-025 | Third-party actions shall be pinned to a major version tag from the publishers `actions/*`, `docker/*` and `microsoft/playwright` only; any other action shall be pinned to a full commit SHA. | Must | BR-16 | Inspection |
| CIC-026 | `ci.yml` shall not use any repository secret; the test JWT_SECRET shall be generated per run with `openssl rand -hex 32`. | Must | BR-16, TRD 21 | Inspection |
| CIC-027 | Runners shall be GitHub-hosted `ubuntu-24.04`; self-hosted runners shall not be used (public repository, untrusted PRs from forks). | Must | BR-16 | Inspection |

### 4.3 Workflow `e2e.yml`

Triggers: `pull_request` to `main` (every PR; job `playwright` is a required check, CIC-070); `push` to
`main`; `schedule` daily at `0 8 * * *` (08:00 UTC, 03:00 America/Chicago during CDT, after the nightly run
window); `workflow_dispatch`. On pull requests and pushes the suite runs in Chromium (including `a11y.spec.ts`, TRD 13
TST-110); on the schedule it runs in Chromium, Firefox and WebKit (TRD 13 TST-100, TST-151), and the schedule also runs the jobs `performance` and `nightly-validation` (CIC-035, CIC-037).

```yaml
name: E2E
on:
  push: { branches: [main] }
  schedule: [{ cron: "0 8 * * *" }]
  workflow_dispatch:
  pull_request: { branches: [main] }
permissions: { contents: read }
jobs:
  playwright:
    runs-on: ubuntu-24.04
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@v4
      - run: cp .env.development.example .env && echo "JWT_SECRET=$(openssl rand -hex 32)" >> .env
      - run: sed -i 's#^RATE_LIMIT_LOGIN=.*#RATE_LIMIT_LOGIN=60/minute#' .env   # E2E stack only, main and isolated runs (D-74, TRD 21 ENV-054)
      - name: Per-job seed credentials (TRD 21 SEED_*, masked, never printed)
        run: |
          for v in SEED_ADMIN_PASSWORD SEED_CLINICIAN_PASSWORD SEED_RESEARCHER_PASSWORD; do
            val="E2e-$(openssl rand -hex 16)"; echo "::add-mask::$val"; echo "$v=$val" >> "$GITHUB_ENV"; sed -i "/^$v=/d" .env; echo "$v=$val" >> .env
          done
          key="ewk_$(openssl rand -hex 24)"; echo "::add-mask::$key"; echo "SEED_INGEST_API_KEY=$key" >> "$GITHUB_ENV"; sed -i "/^SEED_INGEST_API_KEY=/d" .env; echo "SEED_INGEST_API_KEY=$key" >> .env
      - run: docker compose --profile demo up -d --build --wait db backend frontend-prod
      - run: docker compose exec -T backend python -m backend.cli seed test_v0_1      # roster + SRC-05 + pipeline (D-68)
      - run: docker compose exec -T backend python database/seeds/load_evaluation_ground_truth.py tests/fixtures/answer_key/evaluation_ground_truth_v0_1.csv   # DS-10 for E2E-20
      - uses: actions/setup-node@v4
        with: { node-version: "20", cache: npm, cache-dependency-path: frontend/package-lock.json }
      - run: npm ci && npx playwright install --with-deps ${{ github.event_name == 'schedule' && 'chromium firefox webkit' || 'chromium' }}
        working-directory: frontend
      - name: Main run, one browser project at a time (TRD 24 D-73)
        working-directory: frontend
        env: { E2E_BASE_URL: "http://localhost:3001" }   # logins: seeded admin/clinician/researcher@example.com with the masked SEED_* values from $GITHUB_ENV
        run: |   # globalSetup (frontend/tests/e2e/global-setup.ts) before each invocation: seed test_v0_1 --reset + DS-10 loader, docker compose restart backend, one login per role (D-73, D-74)
          for p in ${{ github.event_name == 'schedule' && 'chromium firefox webkit' || 'chromium' }}; do
            npm run test:e2e:readonly -- --project=$p   # read-only scenarios on the pristine seed (--grep-invert "@isolated|@mutating")
            npm run test:e2e:mutating -- --project=$p   # D-73 group, --workers=1: E2E-18; E2E-09 (FE-187); FE-193 snooze step
          done
      - name: Isolated database echowell_demo for E2E-15, E2E-19, TST-187 (CIC-030; the main DB stays exactly the test_v0_1 seed)
        run: |
          docker compose exec -T db psql -U echowell -d echowell -v ON_ERROR_STOP=1 -c "CREATE DATABASE echowell_demo"
          docker compose exec -T db psql -U echowell -d echowell_demo -v ON_ERROR_STOP=1 -f /docker-entrypoint-initdb.d/10_provision_login_roles.sql   # same provisioning: extensions (D-72), roles (idempotent)
          DEMO="-e PIPELINE_AS_OF= -e DATABASE_URL=postgresql+psycopg://echowell_app_login:local-dev-only-app@db:5432/echowell_demo -e DATABASE_MIGRATION_URL=postgresql+psycopg://echowell_migrator_login:local-dev-only-migrator@db:5432/echowell_demo -e DATABASE_READONLY_URL=postgresql+psycopg://echowell_readonly_login:local-dev-only-readonly@db:5432/echowell_demo"
          docker compose stop backend
          docker compose run -d --no-deps --service-ports $DEMO backend      # service command: alembic upgrade head, then uvicorn on :8000
          curl -fsS --retry 30 --retry-all-errors --retry-delay 2 http://localhost:8000/api/v1/health
          docker compose run --rm --no-deps $DEMO backend python -m backend.cli seed test_v0_1 --master-only
          docker compose run --rm --no-deps $DEMO backend python -m backend.cli import-master-data --dir tests/fixtures/seeds/demo_overlay
      - run: npm run test:e2e:isolated   # isolated-setup.ts: no reset/seed, one login per role -> .auth/isolated-<role>.json (D-74); E2E-15, TST-187, E2E-19 in this order
        working-directory: frontend
        env: { E2E_BASE_URL: "http://localhost:3001" }
      - if: failure()
        run: docker compose logs --no-color > e2e-compose.log
      - if: always()
        uses: actions/upload-artifact@v4
        with: { name: playwright-report, path: "frontend/playwright-report/\ne2e-compose.log", retention-days: 14 }
      - if: always()
        run: docker compose down -v
  nightly-validation:   # CIC-037: schedule and manual dispatch only; informational, not a required check (CIC-070)
    if: github.event_name == 'schedule' || github.event_name == 'workflow_dispatch'
    runs-on: ubuntu-24.04
    timeout-minutes: 20
    # services, env, Python setup, provisioning and `alembic upgrade head` steps identical to ci.yml backend-test (section 4.2)
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r backend/requirements.txt -r backend/requirements-dev.txt
      - run: psql -h localhost -U echowell -d echowell_test -v ON_ERROR_STOP=1 -f database/roles/provision_login_roles.sql && alembic upgrade head
      - run: pytest -p randomly tests/unit tests/integration tests/contract tests/security tests/validation   # random order, seed printed (TST-005)
      - run: python tests/validation/robustness.py   # multi-seed reproduction + false-alarm rate, TDV-080..TDV-083 (TST-084)
        continue-on-error: true                       # informational, never gates
      - if: always()
        uses: actions/upload-artifact@v4
        with: { name: nightly-validation-report, path: build/, retention-days: 30 }
```

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| CIC-030 | `e2e.yml` shall run Playwright (Chromium) against the Docker Compose `demo` profile stack (db, backend, frontend-prod on :3001) seeded with `seed test_v0_1` (roster, SRC-05 and pipeline run, TRD 24 D-68) and loaded with the DS-10 ground truth (for E2E-20); every scenario except those tagged `@isolated` runs on that database (TRD 24 D-73): the Playwright `globalSetup` (`frontend/tests/e2e/global-setup.ts`) resets and re-seeds it with `seed test_v0_1 --reset` and the DS-10 loader at the start of each browser project (one Playwright invocation per project and group), the read-only scenarios run first, and the scenarios tagged `@mutating` (every scenario that saves a review, a note or a snooze) run afterwards as the `@mutating` group of TRD 24 D-73 (`frontend/tests/e2e/mutating.spec.ts`, serial, in this order: E2E-18; E2E-09, implemented by TRD 04 FE-187; the FE-193 snooze step on R10), so every read-only assertion sees the pristine seed. After the reset `globalSetup` restarts the backend container (`docker compose restart backend`, waiting for `/api/v1/health`), so the connection pool and the in-memory login limiter start empty, and then logs in once per role and stores the sessions in `frontend/tests/e2e/.auth/` (TRD 24 D-74); only the login scenarios perform form logins. Both runs use RATE_LIMIT_LOGIN=`60/minute` (D-74, TRD 21 ENV-054). The `@isolated` scenarios E2E-15, TST-187 and E2E-19 (TRD 13 §8) shall run afterwards, serially in Chromium, against a second database `echowell_demo` in the same Postgres service, provisioned the same way (`provision_login_roles.sql` as superuser: extensions and roles, TRD 24 D-72), migrated by the backend start command, seeded with `seed test_v0_1 --master-only` and `import-master-data --dir tests/fixtures/seeds/demo_overlay`, with the backend restarted on that database with PIPELINE_AS_OF empty (as-of = current time); this run uses `frontend/playwright.isolated.config.ts`, whose `globalSetup` `frontend/tests/e2e/isolated-setup.ts` does not reset or seed but logs in once per role against the `echowell_demo` backend and writes `frontend/tests/e2e/.auth/isolated-<role>.json` (TRD 24 D-74). The workflow invokes Playwright only through the `frontend/package.json` scripts `test:e2e:readonly`, `test:e2e:mutating` and `test:e2e:isolated` (D-73). | Must | contract §3, TRD 13, TRD 15 DEP-017 | Test |
| CIC-031 | `e2e.yml` shall run on every pull request to `main`, on every push to `main`, nightly at 08:00 UTC and on manual dispatch; its `playwright` job (Chromium E2E including the accessibility suite of TRD 13 TST-110) shall be a required check for pull requests (CIC-070, TRD 13 TST-150). | Must | TRD 13 | Inspection |
| CIC-032 | The E2E suite shall at minimum assert: login; overview tiles 2 / 7 / 1 / 19; default sort "Alarms first" order R09, R10, R08, R07, R03, R02, R05, R01, R04, R06; nav shows "Alerts (2)"; R09 detail shows "Alarm on", the alarm line labelled "alarm line 5.0" and the 7 measurement cards; R08 shows "Baseline forming"; `/alerts` shows alarm cards R09 (open 9 days, tally 26.8) and R10 (open 6 days, tally 13.4) and data alerts R08, R05, R03, D02 and, in the `@mutating` group after all read-only assertions (D-73), a review can be saved for R09 (badge becomes "Reviewed", tally unchanged); `/analytics` (researcher) shows "281 of 300 expected" and "267 of 300 expected" and the alarm timing table; `/analytics` is not accessible to a clinician; the New admissions page shows the "Future / experimental study arm" banner. | Must | BR-12, BR-13, BR-14, SRC-09, SRC-10, SRC-11, SRC-18, SRC-19 | Test |
| CIC-033 | A failing scheduled or `main` `e2e.yml` run shall open (or comment on) a GitHub issue labelled `ci-failure` (the single label for nightly and CI failures, TRD 13 TST-151) via the `gh` CLI using the default `GITHUB_TOKEN` with `issues: write` permission scoped to that step's job. | Should | TRD 17 | Demo |
| CIC-035 | `e2e.yml` shall contain a second job `performance`, run only on the nightly schedule and manual dispatch, that generates dataset DS-08 with `python tests/performance/make_load_dataset.py` (100 residents, 10,800 records) and runs `pytest tests/performance -m performance` against a `postgres:16-alpine` service, failing if any budget of contract R8 is exceeded: read endpoints p95 ≤ 500 ms (100 residents); `POST /api/v1/sessions` p95 ≤ 1,000 ms including the synchronous per-resident pipeline; batch ingest of the test CSV returns 202 ≤ 2 s and finishes processing ≤ 30 s; analytics pipeline on the test input ≤ 5 s; full rebuild of DS-08 ≤ 120 s; and the sustained ingest of 10 records/s for 60 s without errors (TRD 03 NFR-151, TRD 13 TST-190). | Must | contract R8, TRD 03, TRD 13 | Test |
| CIC-037 | `e2e.yml` shall contain a job `nightly-validation`, run only on the nightly schedule and manual dispatch, with the PostgreSQL service and setup of `ci.yml` `backend-test`, that runs the pytest suites in random order (`pytest -p randomly`, pytest-randomly 3.x; seed printed in the log; TRD 13 TST-005) and the multi-seed robustness check `tests/validation/robustness.py` (TRD 14 TDV-080..TDV-083, TRD 13 TST-084) as an informational step (`continue-on-error: true`); it is not a required check (CIC-070), and a failure opens or comments on the `ci-failure` issue like the other nightly jobs (CIC-033). `backend-test` runs with `-p no:randomly` so pull-request order stays fixed. | Should | TRD 13 TST-005, TST-084, TST-151 | Inspection |
| CIC-036 | The `backend-test` job shall additionally assert the single budget that is cheap enough for every PR: the analytics pipeline on the SRC-05 test input completes in ≤ 5 s (pytest marker `budget`). | Should | contract R8 | Test |
| CIC-034 | The E2E credentials (SEED_ADMIN_PASSWORD, SEED_CLINICIAN_PASSWORD, SEED_RESEARCHER_PASSWORD, SEED_INGEST_API_KEY) shall be generated per job, masked with `::add-mask::` before use, passed to the stack through `.env` and to Playwright through `$GITHUB_ENV`, and shall never be valid on staging or production; Playwright logs in as the seeded admin, clinician and researcher users (TRD 06 DB-057, TRD 24 D-71). | Must | BR-16 | Inspection |
| CIC-114 | `repo-hygiene` shall fail when "Edge4Care" appears in any tracked file outside `specs/` and `docs/reports/` (TRD 00 VIS-008), when the words "diagnoses" or "severity" appear in UI copy under `frontend/app`, `frontend/components` or `frontend/lib/wording.ts` (TRD 03 NFR-067), or when an LLM SDK listed in TRD 12 SEC-128 appears in `backend/requirements*.txt` or `frontend/package.json` (TRD 00 VIS-004, TRD 03 NFR-115). | Must | BR-18, RSK-10 | Test |
| CIC-115 | `security-audit` shall run `gitleaks detect` 8.x over the full history (TRD 12 SEC-052, TRD 13 TST-136; the only allow-list entries are the `local-dev-only-*` and `ci-only-*` placeholder values in `.env.development.example`, `docker-compose.yml` and `ci.yml`, TRD 06 DB-057, TRD 21 ENV-041) and Bandit on `backend/` and `analytics/` failing on medium or higher severity (TRD 12 SEC-153); `backend-lint` shall run import-linter with contracts that forbid `analytics` from importing `backend`, `sqlalchemy`, `psycopg`, `fastapi`, `httpx`, `requests` and `random` (TRD 01 ARC-041, AC-ARC-01). | Must | BR-16, BR-15 | Test |
| CIC-116 | `e2e.yml` shall contain a job `lighthouse`, run on pull requests to `main` (not a required check), that runs Lighthouse CI (`@lhci/cli` 0.14.x, the version of TRD 13 §4, desktop preset) on `/residents`, `/residents/R09`, `/alerts` and `/analytics` of the seeded Compose `demo` stack after a scripted admin login (`frontend/tests/lighthouse/login.js`) and fails when any page is below Performance 80 or above LCP 2.5 s (TRD 13 TST-125, TRD 03 NFR-010). | Should | TRD 13, TRD 03 | Test |

### 4.4 Workflow `deploy-staging.yml`

Triggers: `push` to `main` (every merge deploys staging, D-99); `workflow_dispatch` with input `reseed` (boolean).
Concurrency: group `deploy-staging`, runs queued in order (`cancel-in-progress: false`).

Steps:
1. Checkout; set `EXPECTED_SHA=${{ github.sha }}`.
2. Wait for backend: poll `${{ vars.STAGING_API_BASE_URL }}/health` every 15 s, up to 15 min, until JSON `version` equals `EXPECTED_SHA`.
3. Wait for frontend: poll `${{ vars.STAGING_FRONTEND_URL }}/login` until the HTML contains `<meta name="echowell-build" content="EXPECTED_SHA">` (TRD 21 NEXT_PUBLIC_GIT_SHA), up to 15 min. If the commit changed no file under `frontend/` (Netlify skipped the build), accept the previous build.
4. Re-seed when `inputs.reseed` is true or the push changed `backend/alembic/**` or `analytics/**`: `python -m backend.cli seed test_v0_1 --reset` with `DATABASE_URL` and `DATABASE_MIGRATION_URL` both `${{ secrets.STAGING_DATABASE_URL }}` (migrator role), `APP_ENV=staging`, `PIPELINE_PROFILE=test_v0_1`, `PIPELINE_AS_OF=2026-10-30T15:00:00-05:00`, `FACILITY_NAME=Edgewood`, `FACILITY_TZ=America/Chicago` (the complete variable set of an operator command, TRD 21 ENV-053), with SEED_ADMIN_PASSWORD, SEED_CLINICIAN_PASSWORD, SEED_RESEARCHER_PASSWORD and SEED_INGEST_API_KEY from the environment secrets `STAGING_SEED_*` (the seed upserts the users and key and prints nothing, TRD 06 DB-057), followed by `python database/seeds/load_evaluation_ground_truth.py tests/fixtures/answer_key/evaluation_ground_truth_v0_1.csv` with the same variables.
5. Run `pytest tests/smoke -m smoke` with SMOKE_API_BASE_URL, SMOKE_FRONTEND_URL, SMOKE_EXPECTED_SHA, SMOKE_USER_EMAIL `researcher@example.com` (the seeded researcher), SMOKE_USER_PASSWORD (`secrets.STAGING_SEED_RESEARCHER_PASSWORD`), `SMOKE_ENV=staging`.
6. Upload `build/smoke-junit.xml`.

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| CIC-040 | `deploy-staging.yml` shall fail if the staging backend does not report the pushed commit SHA in `/api/v1/health` `version` within 15 minutes. | Must | TRD 15 DEP-080, DEP-082 | Test |
| CIC-041 | `deploy-staging.yml` shall re-seed staging with `seed test_v0_1 --reset` when the push modifies `backend/alembic/**` or `analytics/**`, or when dispatched with `reseed: true`. | Should | TRD 15 DEP-074 | Demo |
| CIC-042 | `deploy-staging.yml` shall run the staging smoke tests (TRD 15 DEP-080) and fail on any failure. | Must | TRD 15 | Test |
| CIC-043 | `deploy-staging.yml` shall run in GitHub environment `staging`, whose secrets are available only to workflows running on `main` (environment deployment branch rule `main`). | Must | BR-16, D-99 | Inspection |

### 4.5 Workflow `deploy-production.yml`

Triggers: `workflow_dispatch` only (manual release, D-99), inputs `sha` (a commit on `main`, required), `version`
(`vX.Y.Z`, required unless `smoke_only`) and `smoke_only` (boolean, default false: re-run the production smoke tests of
the deployed version without deploying or tagging). A push or merge never triggers it.
Environment: GitHub environment `production` (deployment branch rule `main`; required reviewer from `team2-devops` or
the algorithm lead, self-review prevented), holding the deploy secrets of §4.9.
Permissions: `contents: write`. Concurrency: group `deploy-production`, `cancel-in-progress: false`.

Steps:
1. Checkout `inputs.sha` with full history; fail unless it is an ancestor of `origin/main`
   (`git merge-base --is-ancestor`), `version` matches `^v\d+\.\d+\.\d+$` and the tag does not exist yet.
2. "Wait for CI": fail unless every required check of CIC-070 on that SHA concluded `success`
   (`gh api repos/{owner}/{repo}/commits/{sha}/check-runs`) and the `deploy-staging.yml` run for that SHA succeeded
   (`gh run list --workflow deploy-staging.yml --commit {sha}`) (CIC-053, TRD 15 DEP-062).
3. Backend: with `RAILWAY_TOKEN` = `secrets.RAILWAY_PRODUCTION_TOKEN`, run
   `railway variables --set "GIT_SHA=$SHA" --service backend --environment production --skip-deploys` (same for `nightly`),
   then `railway up --ci --service backend --environment production` and `railway up --ci --service nightly --environment production`
   (Railway CLI 4.x); the pre-deploy command `alembic upgrade head` and the healthcheck run as for every Railway deploy (TRD 15 DEP-040, DEP-041).
4. Frontend: in `frontend/`, with `NETLIFY_AUTH_TOKEN` and `GIT_SHA=$SHA`, run
   `npx netlify-cli@17 deploy --build --prod --site "${{ vars.NETLIFY_PRODUCTION_SITE_ID }}"` (the site's environment variables
   apply; `NEXT_PUBLIC_GIT_SHA` comes from `GIT_SHA`, TRD 21 ENV-033).
5. Wait for backend `version` = SHA at `${{ vars.PRODUCTION_API_BASE_URL }}/health` and frontend build meta = SHA at
   `${{ vars.PRODUCTION_FRONTEND_URL }}/login` (15 min timeout each).
6. Run `pytest tests/smoke -m "smoke and not authenticated"` with `SMOKE_ENV=production` (TRD 15 DEP-081).
7. Create tag `vX.Y.Z` on SHA and a GitHub Release with generated notes (`gh release create vX.Y.Z --generate-notes --target $SHA`).

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| CIC-050 | `deploy-production.yml` shall use only the two deploy secrets of the `production` environment (`RAILWAY_PRODUCTION_TOKEN`, `NETLIFY_AUTH_TOKEN`); it shall never hold or read a production database URL, JWT secret or application credential, and it shall verify production only through public HTTPS endpoints. | Must | BR-16, TRD 15 DEP-033, D-99 | Inspection |
| CIC-051 | `deploy-production.yml` shall fail if production does not report the released SHA within 15 minutes or if any production smoke test fails; failure shall trigger the rollback decision in TRD 15 §4.12. | Must | TRD 15 DEP-081 | Test |
| CIC-052 | A Git tag `vX.Y.Z` and GitHub Release shall be created only by `deploy-production.yml`, only for the released SHA and only after the production smoke tests pass. | Must | TRD 18 versioning, D-99 | Demo |
| CIC-053 | `deploy-production.yml` shall run only on manual dispatch, only after approval by a required reviewer of the GitHub environment `production`, and shall deploy nothing unless the chosen SHA is on `main`, every required check of CIC-070 on it succeeded and its `deploy-staging.yml` run succeeded. | Must | BR-17, D-99, TRD 15 DEP-062 | Test |

### 4.6 Workflow `uptime.yml`

Trigger: `schedule` `*/30 * * * *`; `workflow_dispatch`. One job: `curl --fail --max-time 30` on production and staging
`/api/v1/health`, then on the production frontend `/login`; on failure, open or update the issue titled
"Uptime check failing" with label `incident` (step permission `issues: write`). Details of alerting in TRD 17.

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| CIC-060 | `uptime.yml` shall check production and staging `/api/v1/health` and production frontend `/login` every 30 minutes and shall open or update an `incident` issue when any check fails twice in a row (one retry after 60 s). | Should | TRD 17, RSK-05, RSK-07 | Demo |
| CIC-061 | The uptime interval shall be no shorter than 30 minutes, to limit Neon compute usage (TRD 15 DEP-102). | Should | RSK-07 | Inspection |

### 4.7 Required status checks and branch protection

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| CIC-070 | Branch protection on `main` (the only long-lived branch, D-99) shall require these checks to pass: `repo-hygiene` (incl. forbidden-term and LLM-dependency checks), `backend-lint` (incl. import-linter), `backend-test` (incl. the PR-scope performance budget, CIC-036), `openapi-contract`, `frontend`, `security-audit` (incl. gitleaks and Bandit), `docker-build`, `playwright` (E2E Chromium and accessibility). This list implements TRD 13 TST-150. The `e2e.yml` jobs `performance`, `lighthouse` and `nightly-validation` (CIC-035, CIC-116, CIC-037) are not required checks. | Must | contract §13, TRD 18 | Inspection |
| CIC-071 | Required checks shall be evaluated on the PR head merged with the latest base ("Require branches to be up to date before merging"). | Must | TRD 18 | Inspection |
| CIC-072 | A newly disclosed vulnerability that makes `security-audit` fail on an unchanged dependency may be waived for at most 7 days by an `ignore` entry (`pip-audit --ignore-vuln <ID>` or an `npm audit` override documented in the PR) that references a tracking issue. | May | BR-16 | Inspection |

### 4.8 Caching

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| CIC-080 | pip downloads shall be cached by `actions/setup-python` keyed on `backend/requirements*.txt`. | Should | timing budget | Inspection |
| CIC-081 | npm downloads shall be cached by `actions/setup-node` keyed on `frontend/package-lock.json`; `npm ci` shall be used (never `npm install`) so the lockfile is authoritative. | Must | reproducibility | Inspection |
| CIC-082 | Docker layers shall be cached with Buildx `type=gha` caches scoped `backend` and `frontend`. | Should | timing budget | Inspection |
| CIC-083 | The Next.js build cache (`frontend/.next/cache`) shall be cached keyed on the lockfile hash and the hash of `frontend/**/*.{ts,tsx,js,css}`. | May | timing budget | Inspection |

### 4.9 Secrets and variables

| Name | Kind | Scope | Used by | Content |
|---|---|---|---|---|
| `STAGING_DATABASE_URL` | secret | environment `staging` | deploy-staging.yml (re-seed) | Neon `staging` database branch direct URL of role `echowell_migrator` |
| `STAGING_SEED_ADMIN_PASSWORD`, `STAGING_SEED_CLINICIAN_PASSWORD`, `STAGING_SEED_RESEARCHER_PASSWORD`, `STAGING_SEED_INGEST_API_KEY` | secret | environment `staging` | deploy-staging.yml (re-seed step 4 as SEED_*; smoke step 5 uses the researcher password) | credentials of the seeded staging users and API key (TRD 21 SEED_*) |
| `STAGING_API_BASE_URL` | variable | repository | deploy-staging.yml, uptime.yml | e.g. `https://echowell-backend-staging.up.railway.app/api/v1` |
| `STAGING_FRONTEND_URL` | variable | repository | deploy-staging.yml | e.g. `https://echowell-und-staging.netlify.app` |
| `PRODUCTION_API_BASE_URL` | variable | repository | deploy-production.yml, uptime.yml | e.g. `https://echowell-backend-production.up.railway.app/api/v1` |
| `PRODUCTION_FRONTEND_URL` | variable | repository | deploy-production.yml, uptime.yml | e.g. `https://echowell-und.netlify.app` |
| `RAILWAY_PRODUCTION_TOKEN` | secret | environment `production` | deploy-production.yml (step 3) | Railway project token scoped to the `production` environment of project `echowell` |
| `NETLIFY_AUTH_TOKEN` | secret | environment `production` | deploy-production.yml (step 4) | Netlify personal access token of the team-owned deploy account |
| `NETLIFY_PRODUCTION_SITE_ID` | variable | environment `production` | deploy-production.yml (step 4) | site ID of the Netlify production site `echowell-und` |
| `GITHUB_TOKEN` | automatic | per job | releases, issues | least permissions per job |

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| CIC-090 | The only GitHub Actions secrets shall be the five `staging` environment secrets listed above (`STAGING_DATABASE_URL` and the four `STAGING_SEED_*`) and the two deploy tokens of the `production` environment (`RAILWAY_PRODUCTION_TOKEN`, `NETLIFY_AUTH_TOKEN`), which are released only to an approved `deploy-production.yml` job; no production database URL, JWT secret, API key or user credential shall be stored in GitHub. | Must | BR-16, TRD 12, D-99 | Inspection |
| CIC-091 | Workflows triggered by `pull_request` from forks shall not have access to any secret (GitHub default) and `pull_request_target` shall not be used. | Must | BR-16 | Inspection |
| CIC-092 | Secret values shall never be echoed; steps that use secrets shall pass them via `env:` and not via command-line arguments. | Must | BR-16, TRD 17 | Inspection |

### 4.10 Artifacts

| Artifact | Producer | Retention | Content |
|---|---|---|---|
| `backend-reports` | ci.yml backend-test | 30 days | `build/coverage.xml`, `build/htmlcov/`, `build/junit.xml`, `docs/reports/ALGORITHM_VALIDATION_REPORT.md`, `docs/reports/validation_results.json` |
| `performance-report` | e2e.yml performance | 30 days | `build/performance.json` (p95 timings per budget) |
| `nightly-validation-report` | e2e.yml nightly-validation | 30 days | random-order junit, robustness report (TDV-081) |
| `frontend-coverage` | ci.yml frontend | 30 days | Vitest coverage (lcov + html) |
| `playwright-report` | e2e.yml | 14 days | HTML report, traces of failures, compose logs |
| `smoke-report` | deploy-*.yml | 30 days | smoke junit |

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| CIC-100 | The validation suite shall write `docs/reports/ALGORITHM_VALIDATION_REPORT.md` and the machine-readable `docs/reports/validation_results.json` (sections: Test Results, Passed Cases, Failed Cases, Root Cause Analysis, Recommended Fixes — SRC-17 Phase 12) on every run, and CI shall upload it even when tests fail. | Must | SRC-17 Phase 12, BR-15 | Inspection |
| CIC-101 | Test outputs (coverage, junit, Playwright output) shall be written to `build/` (gitignored); `docs/reports/` is tracked and its files are committed only by the PR #3 checkpoints (and PR #4) that SRC-17 asks to produce them (CI regenerates and uploads them but never commits). Artifacts shall contain only synthetic test data and never database dumps or production data. | Must | contract R6, BR-16, TRD 18 | Inspection |
| CIC-102 | On pull requests, the job summary (`$GITHUB_STEP_SUMMARY`) shall show the R01–R10 pass/fail table and the coverage percentages for `analytics/` and `backend/`. | Should | BR-15 | Demo |

### 4.11 Timing budget

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| CIC-110 | The wall-clock time of `ci.yml` from trigger to all required checks complete shall be under 15 minutes at the 90th percentile over the last 20 runs on `main`. | Must | contract task | Analysis (Actions run history) |
| CIC-111 | Every job shall define `timeout-minutes` no greater than 20. | Must | timing budget | Inspection |
| CIC-112 | Each `e2e.yml` job (`playwright`, `performance`, `lighthouse`, `nightly-validation`) shall complete within 20 minutes. | Should | timing budget | Analysis |
| CIC-113 | If the 90th percentile of `ci.yml` exceeds 12 minutes for a week, the team shall split `backend-test` into a matrix (unit+validation / integration) before adding further tests. | Should | CIC-110 | Analysis |

## 5. Assumptions

- ASM-08 Small team and dataset: one validation dataset (SRC-05) and one PostgreSQL service fit the budget.
- The repository is public, so GitHub-hosted runner minutes are free (TRD 22); if the repository becomes private the
  2,000 free minutes per month of GitHub Free organizations apply and CIC-031's nightly E2E should become weekly.
- Railway "Wait for CI", the Netlify GitHub integration, the Railway CLI (`railway up`) and the Netlify CLI remain available on the plans in TRD 22.

## 6. Dependencies

- `backend/requirements.txt` (runtime, exact pins) and `backend/requirements-dev.txt`, the single dev-tool list (TRD 13 §6 refers to it): ruff 0.6.x+, mypy 1.11+, pytest 8.x, pytest-cov 5.x, pytest-randomly 3.x, time-machine 2.x, httpx, testcontainers-python 4.x, openapi-core 0.19.x, Hypothesis 6.x, openpyxl 3.1.x, import-linter 2.x (`lint-imports`), Bandit 1.7.x, pip-audit 2.x.
- Root `pyproject.toml` with `[tool.ruff]`, `[tool.mypy]`, `[tool.pytest.ini_options]` (the marker list of TRD 13 TST-006, registered with `--strict-markers`) and `[tool.coverage]`.
- `frontend/package.json` scripts `dev`, `build`, `start`, `lint`, `typecheck`, `format`, `format:check`, `test`, `test:coverage`, `test:e2e:readonly`, `test:e2e:mutating`, `test:e2e:isolated` (no bare `test:e2e`, TRD 24 D-73); `frontend/package-lock.json` committed.
- `backend.cli export-openapi` and `seed` commands (TRD 15 §4.8); `docs/api_reference/openapi.json` (TRD 19).
- pytest plugin option `--validation-report` implemented in `tests/validation/conftest.py` (TRD 14); it also writes `validation_results.json` next to the Markdown report.
- `tests/performance/make_load_dataset.py` and `tests/performance/` suite (TRD 13/TRD 14).
- Railway "Wait for CI" and the Netlify staging-site integration configured; production services and site set to deploy only through `deploy-production.yml` (TRD 15 §4.5, §4.6).

## 7. Acceptance Criteria

- AC-CIC-01 A PR that changes one composite sign in `analytics/config.py` fails `backend-test` (validation suite) and cannot be merged.
- AC-CIC-02 A PR that adds `tests/fixtures/sample.wav` fails `repo-hygiene`.
- AC-CIC-03 A PR that adds an endpoint without updating `docs/api_reference/openapi.json` fails `openapi-contract`.
- AC-CIC-04 A PR titled "Updated stuff" fails `repo-hygiene`; "feat(api): add device panel endpoint" passes.
- AC-CIC-05 `ci.yml` on `main` completes all required checks in under 15 minutes (CIC-110) and uploads `backend-reports` containing `docs/reports/ALGORITHM_VALIDATION_REPORT.md` with 10 of 10 residents passing and `docs/reports/validation_results.json`.
- AC-CIC-10 The nightly `performance` job passes all contract R8 budgets and uploads `performance-report`.
- AC-CIC-06 `grep -r "secrets\." .github/workflows` lists only `STAGING_DATABASE_URL`, `STAGING_SEED_ADMIN_PASSWORD`, `STAGING_SEED_CLINICIAN_PASSWORD`, `STAGING_SEED_RESEARCHER_PASSWORD`, `STAGING_SEED_INGEST_API_KEY` (in `deploy-staging.yml`), `RAILWAY_PRODUCTION_TOKEN`, `NETLIFY_AUTH_TOKEN` (in `deploy-production.yml` only) and `GITHUB_TOKEN`.
- AC-CIC-07 A merge to `main` yields a green `deploy-staging.yml` run whose log shows the staging health `version` equal to the merge SHA and leaves production unchanged; an approved manual `deploy-production.yml` run for that SHA shows the production health `version` equal to it and creates the tag.
- AC-CIC-08 Branch protection settings for `main` list exactly the eight required checks of CIC-070.
- AC-CIC-09 The nightly `e2e.yml` run passes on `main` for 3 consecutive nights before the demo freeze (15 Nov 2026).

## 8. Implementation Notes

- Replace the existing stub `.github/workflows/ci.yml` (currently only `name: CI`) with the outline in 4.2.
- Job ids are the status check names; do not rename them without updating branch protection (CIC-070).
- `openapi-contract` must not need a database: the app factory must not connect to the database at import time;
  connect lazily in the lifespan handler, which `export-openapi` does not run.
- `--validation-report` is a custom pytest option; register it in `tests/validation/conftest.py` with `pytest_addoption` and write the report in `pytest_sessionfinish`.
- `docker compose up --wait` requires healthchecks on every waited service; give `backend` a healthcheck (`python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')"`) and `frontend-prod` one on `/login`.
- When the Netlify staging site skips a build (ignore command), the old build meta SHA remains; the verification step must compare against the latest commit that touched `frontend/` or `netlify.toml` (`git log -1 --format=%H -- frontend netlify.toml`).
- `npm audit --omit=dev` excludes dev tooling to avoid blocking on advisories in build-only packages; Dependabot (TRD 18) still raises those.
- Use `ubuntu-24.04` explicitly rather than `ubuntu-latest` to avoid silent runner image changes before the demo.

## 9. Open Questions

- OQ-07 AWS budget approval timing — at AWS cut-over, `deploy-production.yml` gains an AWS OIDC role and the URLs in Actions variables change; no other workflow changes.
- (OQ-23 is closed by D-OWNER-4: CI, staging and the interim stack hold synthetic data only — reflected in CIC-101.)

## Revision History

| Version | Date | Description | Author |
|---|---|---|---|
| 0.1 | 18 Oct 2026 | Initial generation from TRD_Generation_Prompt.md | — |
| 0.1 | 18 Oct 2026 | Cross-TRD consistency review | — |
| 0.2 | 19 Oct 2026 | Phase 1 validation fixes (F-13, F-16, F-19, F-20, F-40) | — |
| 0.3 | 19 Oct 2026 | Phase 1 round-2 fixes (R2-02, R2-18, R2-20) | — |
| 0.4 | 19 Oct 2026 | Phase 1 round-3 fixes (R3-01, R3-07) | — |
| 0.5 | 19 Oct 2026 | Phase 1 round-4 fixes (R4-02, R4-05, R4-07) | — |
| 0.6 | 19 Oct 2026 | Phase 1 round-5 fixes (R5-01, R5-02, R5-04, R5-05, R5-07, R5-11) | — |
| 0.7 | 19 Oct 2026 | Phase 1 round-6 fixes (R6-01, R6-02, R6-03, R6-07) | — |
| 0.8 | 19 Oct 2026 | Phase 1 round-7 fixes (R7-01, R7-02, R7-05) | — |
| 0.9 | 19 Oct 2026 | Phase 1 round-8 minor fixes (R8-02, R8-03) | — |
| 0.10 | 20 Oct 2026 | PR #2 backlog consistency fixes (frontend job check:bundle (TST-191); CIC-035 sustained ingest (TST-190); CIC-116 four pages (D-98)) | — |
| 0.11 | 21 Oct 2026 | PR #2 review: branching (D-99) and PR structure (D-100) | — |
