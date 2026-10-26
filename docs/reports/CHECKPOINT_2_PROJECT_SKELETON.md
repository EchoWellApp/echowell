# Checkpoint 2 Report — Phase 8 Generate Project Skeleton

Block 3 "Implement Features", checkpoint 2 of 9, its own PR (branch `feat/cp2-project-skeleton`, created from `main` at a1c718c after GitHub PR #3 was merged) · Prompt: `specs/prompts/Implement_Feature_Batches.md` "Phase 8: Generate Project Skeleton" · TRD 25 Phase 3 · Features: FEAT-002..FEAT-007 · Date: 23 October 2026, revised 26 October 2026 · Status: delivered as GitHub PR #4; review rounds 1 and 2 (algorithm lead, 26 Oct 2026) answered and applied, sections 9 and 10; ready for re-review and merge to `main` (D-101).

Build groups were followed in the `BACKLOG.md` §9 order: [FEAT-002, FEAT-003, FEAT-005] → [FEAT-004] → [FEAT-006, FEAT-007]. Reading order: TRD 25, 00, 24; Phase 8 prompt; roadmap §2.2, §2.3, §5.2; FEAT-002..FEAT-007; TRDs 01, 18, 21, 16, 15, 13, 04, 05, 07; `docs/design/`.

## 1. What was built

No business logic: configuration, wiring, dependency injection, startup guards, the health endpoint and empty, documented modules only.

| Feature | Delivered |
|---|---|
| FEAT-002 | Backend package tree (`core/`, `schemas/`, `repositories/`, `jobs/nightly_run.py`, `cli.py`, `alembic/`, `models/__init__.py` with the declarative `Base`); `analytics/` with exactly the 16 TRD 07 §4.2 modules plus `__init__.py` (7 created, 9 kept), each with a docstring naming its owning TRD; module docstrings in every kept skeleton file; root `pyproject.toml` (`[tool.ruff]`, `[tool.mypy]`, three import-linter contracts); `backend/requirements.txt` (exact pins, `psycopg[binary]==3.2.4`) and `requirements-dev.txt` (TRD 16 §6 list); `.gitignore` (TRD 18 §4.11, replaced), `.editorconfig`, `.gitattributes`, `.pre-commit-config.yaml`; `.github/` PR template, CODEOWNERS, dependabot, issue templates with blank issues disabled; `README.md` (GIT-056 sentence); `scripts/` and `database/seeds/` directories |
| FEAT-003 | `backend/core/config.py`: one `Settings` class (every TRD 21 §4.2/§4.3 variable, secrets `SecretStr`), cached `get_settings()`, `.env` only for `local`/`test`, `ECHOWELL_*` typo check, URL normalisation, and the guards ENV-010..ENV-015, ENV-041, ENV-053, ENV-054 with exit code 1 and one CRITICAL `startup_config_invalid` record naming variables and rules only; `backend/core/db.py` (the one engine factory, API-125 pool settings, `prepare_threshold=None`, lazy, 2 s `SELECT 1` probe); `backend/core/errors.py` (`AppError`, `InvalidQueryParameterError`); `backend/api/deps.py` (`get_settings`, `get_engine`, `get_db`, `get_pagination`); `backend/main.py` `create_app()` mounting under `/api/v1`, OpenAPI at `/api/v1/openapi.json`, Swagger UI off in production, ReDoc off; `GET /api/v1/health` → `backend/services/health_service.py` `get_health()` (Q-1 of checkpoint 1) → `backend/schemas/health.py` `Health`; nightly job and CLI entry points run the same guards |
| FEAT-005 | `tests/` tree of TRD 13 §4.2 (empty directories kept with `.gitkeep`); `tests/conftest.py` (level-marker and skip-reason collection rules, isolated settings factory, frozen clock, testcontainers `postgres:16-alpine` or `DATABASE_URL` when `APP_ENV=test`, rolled-back DB session, `TestClient` with dependency overrides, autouse limiter reset); pytest and coverage configuration in `pyproject.toml` (11 TST-006 markers, `--strict-markers`, no `pytest.ini`); `tests/trace_report.py`; conventions in `docs/team_workflow.md` |
| FEAT-004 | Next.js 14.2.35 App Router project (TypeScript 5.6 strict, React 18.3.1, TanStack Query 5, Recharts 2), exact pins and committed `package-lock.json`, `.nvmrc` 20; the TRD 04 script table (no bare `test:e2e`); ESLint (FE-200), Prettier (FE-201), `vitest.config.ts` (FE-180, 80 % lines), Playwright configs (TST-004) with empty global setups; `lib/config.ts` (the only reader of the public variables, build fails on invalid values); root layout (IBM Plex via `next/font/google`, `echowell-build` meta, environment ribbon), `/` → `/residents` redirect, minimal `/login`; `services/api.ts` kept as an empty module (FEAT-062) |
| FEAT-006 | `docker-compose.yml` (TRD 15 §4.2 outline: `db` postgres:16-alpine with healthcheck and init script, `backend` running `alembic upgrade head` then uvicorn `--reload` without proxy flags, `frontend` node:20-alpine `next dev`; all ports on 127.0.0.1; only `local-dev-only-*` values); `backend/Dockerfile` (`python:3.12-slim`, default command with `--proxy-headers --forwarded-allow-ips='*'`, Q-10); `.dockerignore`; `database/roles/provision_login_roles.sql` (extensions, database time zone UTC, NOLOGIN group roles, schema owner, login roles via `\getenv`, idempotent); root `alembic.ini` and empty Alembic environment (`SET ROLE echowell_migrator`); `.env.example`, `.env.development.example`, `.env.production.example`; `docs/deployment.md` with the TRD 15 §4.2 procedure verbatim |
| FEAT-007 | `.github/workflows/ci.yml` replacing the stub: jobs `backend-lint`, `backend-test` (postgres service, provisioning step, `alembic upgrade head`, one pytest run over unit/integration/validation with JUnit and coverage XML), `frontend` (six npm commands in CIC-017 order); `contents: read`; ubuntu-24.04; `actions/*` major tags; no secrets |

Requirement IDs implemented (AGT-022): ARC-010, ARC-011, ARC-013, ARC-015, ARC-016, ARC-050, ARC-051, ARC-056, ARC-057, ARC-083; ANL-001, ANL-002, ANL-004, ANL-005; API-001..API-005 (structure), API-007, API-008, API-010, API-011, API-016, API-017, API-103 (local), API-110..API-113, API-125; ENV-001..ENV-006, ENV-010..ENV-015, ENV-018, ENV-030..ENV-033, ENV-040, ENV-041, ENV-053, ENV-054; FE-001..FE-008, FE-010, FE-012, FE-043, FE-044, FE-170..FE-173, FE-180, FE-200..FE-203; DEP-010..DEP-014, DEP-018, DEP-020, DEP-022, DEP-024, DEP-119; CIC-010..CIC-013, CIC-017, CIC-024..CIC-027, CIC-080, CIC-081; GIT-001..GIT-003, GIT-032, GIT-033, GIT-037, GIT-040..GIT-045, GIT-056, GIT-072, GIT-080, GIT-090..GIT-097, GIT-100, GIT-110, GIT-112; TST-001..TST-007, TST-010, TST-011 (registered, skipped until Phase 6), TST-013, TST-021, TST-038 (startup part), TST-054, TST-140..TST-144 (mechanism), TST-153, TST-160..TST-162 (conventions); AGT-004, AGT-007, AGT-010, AGT-015, AGT-016, AGT-017, AGT-019, AGT-024; D-53, D-72, D-90, D-94; FEAT-002..FEAT-007 FRs.

## 2. Files

Created: `pyproject.toml`, `alembic.ini`, `.editorconfig`, `.gitattributes`, `.pre-commit-config.yaml`, `.dockerignore`, `.env.example`, `.env.development.example`, `.env.production.example`; `.github/` `pull_request_template.md`, `CODEOWNERS`, `dependabot.yml`, `ISSUE_TEMPLATE/{bug_report,feature_request,config}.yml`; `analytics/{__init__,config,robust_stats,speaker_screen,day_ledger,data_alerts,aggregates,pipeline}.py`; `backend/{__init__,cli}.py`, `backend/Dockerfile`, `backend/requirements-dev.txt`, `backend/api/{__init__,deps}.py`, `backend/core/{__init__,config,db,errors}.py`, `backend/schemas/{__init__,health}.py`, `backend/services/{__init__,health_service}.py`, `backend/repositories/__init__.py`, `backend/models/__init__.py`, `backend/jobs/{__init__,nightly_run}.py`, `backend/alembic/{env.py,script.py.mako,versions/.gitkeep}`; `database/roles/provision_login_roles.sql`, `database/seeds/.gitkeep`, `scripts/.gitkeep`; `tests/conftest.py`, `tests/trace_report.py`, nine test modules (section 3) and `.gitkeep` files for the empty TRD 13 directories; `frontend/` `.nvmrc`, `.eslintrc.json`, `.prettierrc`, `.prettierignore`, `.env.example`, `tsconfig.json`, `vitest.config.ts`, `vitest.setup.ts`, `playwright.config.ts`, `playwright.isolated.config.ts`, `package-lock.json`, `app/{layout,page}.tsx`, `app/login/page.tsx`, `lib/config.ts`, `components/EnvironmentRibbon/*`, `tests/{unit,pages,e2e}/*`; `docs/deployment.md`, `docs/team_workflow.md` (were empty); this report.

Changed (kept at their paths, AGT-010): `README.md`, `.gitignore`, `docker-compose.yml`, `.github/workflows/ci.yml` (stub replaced, D-55, D-94), `backend/requirements.txt` (D-53), `backend/main.py`, `backend/api/health.py`, the other 25 empty skeleton files (module docstring added), `frontend/package.json`, `frontend/next.config.js`, `frontend/services/api.ts`; `specs/TRD/24_Risk_Assumptions_and_Open_Questions.md` (OQ-30, v0.15); `specs/backlog/BACKLOG.md` (§10, v0.6). Not changed: `database/schema.sql` (stays empty until FEAT-008 regenerates it). Nothing deleted, renamed or moved.

Size: about 2,800 changed lines excluding `frontend/package-lock.json`, above the GIT-034 guideline of 1,500. GIT-034 asks for sub-batches in that case; proposed commit order for the PR (Q-1): (1) `chore: repository standards and pinned dependencies` (FEAT-002); (2) `feat(api): app factory, settings, startup guards and health` (FEAT-003); (3) `test: pytest infrastructure and conventions` (FEAT-005); (4) `feat(frontend): Next.js 14.2 scaffold` (FEAT-004, lockfile); (5) `build: local Docker Compose stack and provisioning` (FEAT-006); (6) `ci: core CI jobs` (FEAT-007); (7) `docs: checkpoint 2 report, OQ-30, backlog tracking`.

## 3. Tests added

| File | Level | Covers |
|---|---|---|
| `tests/unit/backend/core/test_config.py` | unit | CFG-06 (`test_cfg_06_production_refuses_test_profile`, and a subprocess start of `create_app()` exiting 1 with a CRITICAL `startup_config_invalid` naming `PIPELINE_PROFILE` and no secret, AC-AGT-05); TST-038 startup refusal of `PIPELINE_AS_OF` (also as subprocess); ENV-011/AC-ENV-02 staging vs local TLS; ENV-012 CORS regex, console logs, `http://` origins; ENV-013 31-byte secret in all four environments (AC-ENV-04); ENV-013/ENV-041 template and placeholder secrets (AC-ENV-03); ENV-015 facility name (AC-ENV-07); ENV-014 URL normalisation (AC-ENV-05); ENV-004 masking (AC-ENV-09); ENV-054; ENV-003; ENV-006; ENV-053 operator subset |
| `tests/unit/backend/core/test_env_templates.py` | unit | ENV-040 every `Settings` field in `.env.example`; both templates equal the TRD 21 §4.6 blocks line for line (FEAT-006-AC-08); ENV-041 local-dev-only `JWT_SECRET` refused in staging (FEAT-006-AC-07) |
| `tests/unit/backend/test_deps.py` | unit | API-016 bounds and defaults (FEAT-003-AC-09); API-011 commit/rollback/close |
| `tests/unit/backend/test_entry_points.py` | unit | nightly job exits 1 with the production test profile (ENV-010 reused by the job); CLI help |
| `tests/unit/backend/test_import_boundary.py` | unit | ANL-002, ANL-005, AC-ARC-01, TST-021 (AST scan backing `lint-imports`) |
| `tests/unit/test_markers.py` | unit | TST-006 exact marker list, `--strict-markers`, no `pytest.ini`; TST-010 naming and one level marker per module |
| `tests/unit/test_repository_layout.py` | unit | AC-AGT-06/ARC-050 skeleton presence; ANL-004 exact module list (FEAT-002-AC-02); TST-007 no audio; no `.env` or `LICENSE` tracked (AC-GIT-02); GIT-100; AC-AGT-11 pins |
| `tests/unit/analytics/test_module_tests_exist.py` | unit | TST-011 meta-test, skipped with reason naming TST-011 until Phase 6 (TST-153) |
| `tests/integration/api/test_health.py` | integration | TST-054 200 ok/ok with `version` = `GIT_SHA` and 503 degraded/unavailable with the database unreachable (`get_engine` override); API-002 and API-113 |
| `frontend/tests/pages/login.test.tsx` | Vitest page | renders `/login` (TRD 25 Phase 3 required test, FEAT-004-AC-02) |
| `frontend/tests/pages/root.test.tsx` | Vitest page | root layout `lang="en"`; `/` redirects to `/residents` |
| `frontend/tests/unit/config.test.ts` | Vitest unit | FE-171/AC-ENV-08: missing, non-absolute, non-http(s), with path or `/api/v1`, trailing slash, `http://` in staging, unknown app env |
| `frontend/components/EnvironmentRibbon/EnvironmentRibbon.test.tsx` | Vitest component | FE-172 "LOCAL", staging label, no ribbon in production (FEAT-004-AC-08) |

Totals: pytest 38 passed, 1 skipped (TST-011, by design); Vitest 14 passed, line coverage 96.5 %.

## 4. Commands run and results

Environment: Linux container; Python 3.12.3 (`/usr/bin/python3.12`, virtualenv in the session scratchpad; the system `python3` is 3.13 and was not used); Node 22.22.0 / npm 10.9.4 (CI and `.nvmrc` use Node 20; not available locally); Docker 29.8.2 with Compose v5.6.0 (the daemon was not running and was started in the session); host psql 16.15.

| # | Command | Result |
|---|---|---|
| 1 | `cp .env.development.example .env && docker compose config --services` | `db`, `backend`, `frontend`; all three published ports on 127.0.0.1 |
| 2 | `docker compose up --build -d` | first attempts failed on the session's network, not on the project: Docker Hub returned 429 for `node:20-alpine` (succeeded on retry), and `pip install` inside the build failed TLS verification against the session's intercepting proxy. Workaround (session only, nothing committed): local images tagged `python:3.12-slim` and `node:20-alpine` built from the official images plus the proxy CA (`/root/.ccr/README.md`). With those, the committed Dockerfile and Compose file built and started unchanged |
| 3 | `curl -fsS http://localhost:8000/api/v1/health` | `{"status":"ok","database":"ok","version":"unknown","time":"2026-10-23T22:52:05Z"}` (HTTP 200) |
| 4 | `docker compose down -v && docker compose up -d`, then poll health | 200 with `"database":"ok"` 11 s after start from an empty volume (DEP-014 limit 180 s); `db` healthy before `backend` started; backend log shows `alembic.runtime.migration` lines before `Uvicorn running` (FEAT-006-AC-03) |
| 5 | `psql` checks in the Compose `db` | login roles `echowell_{migrator,app,readonly}_login` each in only its group role; group roles NOLOGIN; `timezone` UTC; extensions `pgcrypto`, `btree_gist`; schema `public` owned by `echowell_migrator`; `alembic_version` owned by `echowell_migrator`; the backend's sessions run as `echowell_app_login` |
| 6 | `touch` in `/app/database` and `/app/tests/fixtures` inside `backend` | "Read-only file system" (FEAT-006-AC-05); editing `backend/alembic/env.py` triggered `StatReload` (FEAT-006-AC-04) |
| 7 | `curl http://localhost:3000/login` (Compose `frontend`) | 200 |
| 8 | `docker run` of the backend image (default command with `--proxy-headers`) with `APP_ENV=production PIPELINE_PROFILE=test_v0_1`, and with `APP_ENV=production PIPELINE_AS_OF=…` | exit 1, `startup_config_invalid: PIPELINE_PROFILE: …` / `PIPELINE_AS_OF: …` (AC-AGT-05) |
| 9 | `pytest -q` (no `DATABASE_URL`; testcontainers `postgres:16-alpine`) | 38 passed, 1 skipped (FEAT-005-AC-01) |
| 10 | `pytest -q -p randomly --randomly-seed=1234` and `=98765` | both 38 passed, 1 skipped (TST-005, FEAT-005-AC-06) |
| 11 | CI `backend-test` emulation on a fresh `postgres:16-alpine` (port 5433) with the job's env: `psql … -f database/roles/provision_login_roles.sql` (twice), `alembic upgrade head`, `pytest -p no:randomly tests/unit tests/integration tests/validation --cov=analytics --cov=backend --cov-branch --cov-report=xml:build/coverage.xml --junitxml=build/junit.xml` | provisioning exit 0 both times (idempotent); Alembic exit 0; 38 passed, 1 skipped; no extra container started (FEAT-005-AC-02). This run first exposed that test settings read the job environment; fixed by `IsolatedSettings` in `tests/conftest.py` |
| 12 | `pytest --cov=analytics --cov=backend --cov-report=term` | report produced; backend 84 % lines (gates arrive with FEAT-078); only the TST-144 exclusions configured (FEAT-005-AC-07) |
| 13 | `python tests/trace_report.py` | runs; lists 999 Must IDs of TRDs 02, 04, 05, 07–12 not yet referenced (expected at Phase 3) |
| 14 | `ruff check .`; `ruff format --check .`; `mypy analytics backend`; `lint-imports` (the `backend-lint` job) | all exit 0; 3 contracts kept |
| 15 | `lint-imports` after adding `import sqlalchemy` to `analytics/pipeline.py`, and `import os` to `analytics/config.py` (reverted) | both broken, as required (FEAT-002-AC-03, TST-021) |
| 16 | `python -c "import analytics"` | exit 0 |
| 17 | `cd frontend && npm ci && npm run lint && npm run typecheck && npm run format:check && npm run test:coverage && npm run build && npm run test` (with the CI `frontend` job env) | all exit 0; ESLint no warnings; build lists `/`, `/_not-found`, `/login`, 87 kB first-load JS |
| 18 | `npx next build` with `NEXT_PUBLIC_API_BASE_URL` unset; with `http://api.example.org` and `NEXT_PUBLIC_APP_ENV=staging` | both exit 1 with "Invalid frontend configuration: …" (FEAT-004-AC-03) |
| 19 | `next start`, `curl -I /login`, `curl /login`, `curl -I /` | no `X-Powered-By` (FEAT-004-AC-06); page contains "LOCAL" ribbon, `echowell-build` meta, heading; `/` answers 307 |
| 20 | `grep -rlE "fonts.(googleapis\|gstatic).com" .next/server/app .next/static/css` | no match; font files under `.next/static/media`; no font tracked by git (FEAT-004-AC-04). The Next.js runtime chunks contain these host names as framework constants, not as links |
| 21 | AGT/AC greps: `grep -rniE "openai\|anthropic\|langchain\|llama\|gpt" frontend backend analytics` (sources); `grep -rni "edge4care" frontend backend analytics tests`; `grep -n "psycopg2" backend/requirements.txt`; `grep -rn "pipeline_test_v0_1.xlsx" analytics backend`; `grep -n "secrets\." .github/workflows/ci.yml`; `grep -rn "neon.tech" docker-compose.yml backend/Dockerfile` | all no match (the first runs of the Edge4Care and psycopg2 greps found the guard literal in `config.py` and a requirements comment; both fixed) |
| 22 | `pip-audit -r backend/requirements.txt -r backend/requirements-dev.txt`; `npm audit --audit-level=high --omit=dev` (informational; the `security-audit` job is FEAT-078) | fixed inside the pinned majors: python-dotenv 1.0.1 → 1.2.2, @playwright/test 1.48.2 → 1.55.1. Remaining: Starlette 0.46.x (7 advisories, fixes need FastAPI > 0.115.x), pytest 8.3.4 (fix in 9.x), Next.js 14.2.35 critical + bundled PostCSS (fix in Next.js 16). Raised as OQ-30 |

Not run or not verifiable here: the CI workflow itself on GitHub (FEAT-007-AC-01..AC-04 need a real PR; the job steps were emulated locally, item 11); Node 20 (Node 22 used locally); the deliberate-failure workflow validations of FEAT-007 (ruff violation, failing test, ESLint warning) need GitHub runs.

## 5. Exit criteria (roadmap §5.2, TRD 25 Phase 3)

| Criterion | Evidence | Result |
|---|---|---|
| App starts locally; `GET /api/v1/health` 200 with `database` "ok" against the provisioned Compose `db` (D-90) | items 2–5 | PASS (with the session-only CA base images) |
| Existing skeleton files kept (AGT-010, AC-AGT-06) | `test_skeleton_files_kept`; nothing deleted or renamed | PASS |
| Startup guard refuses `PIPELINE_PROFILE=test_v0_1` (and `PIPELINE_AS_OF`) with `APP_ENV=production` | CFG-06 tests; items 8, 10 | PASS |
| `backend/requirements.txt` with `psycopg[binary]` 3.x, all pinned, no psycopg2 (D-53, AC-AGT-11) | item 21; `test_requirements_pinned_without_psycopg2` | PASS |
| No business logic | inspection: modules are docstrings, wiring, guards and the health probe | PASS |
| Health smoke test, startup-guard test, frontend renders `/login` | section 3 | PASS |
| `docker compose up -d`; `pytest -q`; `npm ci && npm run lint && npm run build && npm run test`; `curl -fsS …/health` | items 2, 3, 9, 17 | PASS |
| `ci.yml` jobs `backend-lint`, `backend-test`, `frontend` replacing the stub (D-94); triggers `pull_request`, `push` to `main` (CIC-010) | file inspection | PASS (`workflow_dispatch` kept per CIC-010, Q-2) |
| CI core jobs green on the PR head | needs the PR | PENDING (local emulation green) |
| `.env` files gitignored; no secrets beyond local-only defaults | `git check-ignore .env`; `test_no_env_file_or_licence_tracked`; item 21 | PASS |
| GIT-034 size ≤ ~1,500 lines | about 2,800 lines | NOT MET; sub-batch commit order proposed (section 2, Q-1) |
| Each feature's Definition of Done | FEAT-002, FEAT-003, FEAT-004, FEAT-005, FEAT-006 acceptance criteria verified locally (FEAT-003-AC-08 audit-row part waits for FEAT-012); FEAT-007 needs a real PR | PASS locally; FEAT-007 PENDING the PR |

## 6. New OQ and D IDs

- OQ-30 (TRD 24 §4.2, v0.15): pinned majors with known advisories (Next.js 14.2.x, Starlette via FastAPI 0.115.x, pytest 8.x) vs the CIC-019 `security-audit` gate. Interim: keep the §4.7 majors and take only in-range fixes; decide before checkpoint 8. No new D entry (no pinned major was changed). Answered in review round 1 (D-105, RSK-16).
- Review round 1 (TRD 24 v0.16): D-103, D-104, D-105, D-106, D-107 and RSK-16 (section 9).

## 7. Deviations and notes

| # | Note | Handling |
|---|---|---|
| N-1 | Prompt vs TRDs: the prompt asks for "all required imports, wiring" and the TRD 25 Phase 3 list; FEAT-002..FEAT-007 narrow this (no service, repository or model modules beyond the skeleton) | feature files followed; services `config_service.py`, `auth_service.py`, `audit_service.py` and repository modules (Database_ERD §5 names) are created by their features (FEAT-009..FEAT-037) |
| N-2 | TRD 18 CODEOWNERS block has `/netlify.toml /railway.toml    @…team2-devops` on one line, which GitHub parses as one pattern with an invalid owner | split into two lines; TRD 18 §4.4 updated to match (Q-3, accepted) |
| N-3 | `LOG_FORMAT=console`: ENV-012 refuses it in production; the TRD 21 §4.2 table refuses it in staging and production | both refused (stricter reading); ENV-012 and FEAT-003-FR-12 now say so (Q-4, D-103) |
| N-4 | ENV-003 rejects unknown `ECHOWELL_*` variables, but the CI `backend-test` job env carries `ECHOWELL_*_DB_PASSWORD` (TRD 21 §4.5) | the three §4.5 names are treated as known |
| N-5 | TRD 18 §4.5 ignores only S101 under `tests/**`; test secrets and `git` subprocess calls trigger S105/S106/S603 | per-line `noqa` with a reason (GIT-043), configuration unchanged |
| N-6 | ENV-015 needs the forbidden facility name in code, while AGT-019/AC-AGT-03 forbid the literal in `backend/` | case-insensitive pattern `edge\W*4\W*care` (also catches spaced spellings); the test builds the string by concatenation so the future `repo-hygiene` term scan stays clean |
| N-7 | ENV-021 (verify `config_parameters` rows at startup) and the FEAT-003-AC-08 "no audit row" part need tables from FEAT-009/FEAT-012 | deferred to those features |
| N-8 | `get_pagination()` raises `InvalidQueryParameterError` (422, `INVALID_QUERY_PARAMETER`); the problem+json handler that renders it over HTTP is FEAT-019 | unit-tested at the dependency level |
| N-9 | Swagger's OAuth redirect route defaults to `/docs/oauth2-redirect`, outside `/api/v1` (API-002) | moved to `/api/v1/docs/oauth2-redirect`; a test asserts every route starts with `/api/v1/` |
| N-10 | `ci.yml` `backend-test` includes the provisioning step and `alembic upgrade head` (no-op until FEAT-008); the downgrade/upgrade round trip, coverage gates and `--validation-report` are left to FEAT-008/FEAT-078 | per FEAT-007 Out of Scope and D-94 |
| N-11 | Frontend `services/api.ts` is an empty module (`export {}`), so it shows 0 % in the coverage table (no statements) | filled by FEAT-062 |
| N-12 | Feature-file meta blocks still say "Status: Not Started"; checkpoint 1 left them unchanged as well, and D-95 tracks status in `BACKLOG.md` §10 | resolved (Q-5, D-104): feature-file Status fields of FEAT-001..FEAT-007 and roadmap §2.1 refreshed with §10 |

## 8. Questions for the reviewer (all answered in review round 1, section 9)

| ID | Question (as raised on 23 Oct 2026) |
|---|---|
| Q-1 | The checkpoint is about 2,800 changed lines (GIT-034 "should" ≤ 1,500). Accept it as one PR committed in the seven sub-batches of section 2, or split differently? |
| Q-2 | The roadmap pitfall says `ci.yml` triggers are "`pull_request` and `push` to `main` only", while CIC-010 and FEAT-007-FR-01 also require `workflow_dispatch`. I kept `workflow_dispatch` (TRD wins, AGT-001). Confirm? |
| Q-3 | Accept the two-line CODEOWNERS fix for `/netlify.toml` and `/railway.toml`, and update the TRD 18 block to match? |
| Q-4 | Refuse `LOG_FORMAT=console` in staging as well as production (TRD 21 table), or only in production (ENV-012, FEAT-003-FR-12)? |
| Q-5 | Should feature-file "Status" fields and the roadmap §2.1 Block 3 status cell also be refreshed per checkpoint, or is `BACKLOG.md` §10 the only tracker (D-95)? |
| Q-6 | OQ-30: upgrade Next.js, FastAPI/Starlette and pytest beyond the §4.7 majors under the GIT-111 security exception (new D entry), or accept the advisories for the synthetic-data interim stack until the demo? Needed before checkpoint 8. |

## 9. Review round 1 resolutions (26 October 2026)

The algorithm lead (Shaba) answered Q-1..Q-6 and the three questions still open from earlier on GitHub PR #4 on 26 Oct 2026. Every answer is applied on this branch.

### 9.1 Answers to Q-1..Q-6

| ID | Reviewer answer | Resolution | Files changed |
|---|---|---|---|
| Q-1 | Accept it as one PR. | Kept as one PR in the seven sub-batch commits of section 2 (GIT-034 guideline exceeded with approval). | — |
| Q-2 | Keep `workflow_dispatch`. | Kept (CIC-010, FEAT-007-FR-01); the roadmap pitfall that said "only" `pull_request` and `push` now lists all three triggers. | `IMPLEMENTATION_ROADMAP.md` §5.2 |
| Q-3 | Accept the split; update TRD 18 to the valid format. | The TRD 18 §4.4 CODEOWNERS block now has `/netlify.toml` and `/railway.toml` on separate lines, identical to `.github/CODEOWNERS`; ownership unchanged. | TRD 18 §4.4 (v0.14) |
| Q-4 | Keep as implemented; staging mirrors production; update ENV-012 and FEAT-003. | ENV-012 and FEAT-003-FR-12 refuse `LOG_FORMAT=console` in staging and production (D-103); the other ENV-012 guards stay production-only because staging uses a fixed PIPELINE_AS_OF (D-59). The code already did this; a staging test was added (`test_staging_refuses_console_logs`). | TRD 21 ENV-012 (v0.11); FEAT-003; FEAT-018; TRD 24 D-103; `tests/unit/backend/core/test_config.py` |
| Q-5 | Update all status sources; `BACKLOG.md` §10 stays primary. | D-104 (amends D-95): each checkpoint PR also refreshes the feature-file Status fields and the roadmap §2.1 status cell. FEAT-001 Complete; FEAT-002..FEAT-007 In Progress until this PR is merged; roadmap §2.1 names GitHub PR #4. | TRD 24 D-95, D-104; `IMPLEMENTATION_ROADMAP.md` §2.1, §2.3 (v0.5); `BACKLOG.md` §10 (v0.7); FEAT-001..FEAT-007 |
| Q-6 | Defer the major upgrades; record an approved security-risk/debt item; revisit before the demo or checkpoint 8. | OQ-30 Answered (D-105); RSK-16 records the accepted security debt and the revisit point. The GIT-111 exception remains available as a scope decision. | TRD 24 OQ-30, RSK-16, D-105 (v0.16) |

### 9.2 Earlier open questions

| Question | Reviewer answer | Resolution |
|---|---|---|
| Test-case output path (roadmap §11 question 3) | `specs/testing/test-cases/` | D-106; roadmap §7 and §11 updated |
| Audit-checklist section for 14A/14B (roadmap §11 question 1) | Yes, if they define verifiable deliverables | They do (files, reports, deployment checks): `Implementation_Audit_Checklist.md` gains a review-only section "Phases 14A and 14B: Audit Checklist" that lists only what the two prompts already require (D-107); roadmap §3.1 and §5.8 updated |
| GitHub Support purge of old commits containing the removed preprint PDF | No; leave the history as is | No action |

### 9.3 Verification after review round 1

| Check | Result |
|---|---|
| `ruff check .`; `ruff format --check .`; `mypy analytics backend`; `lint-imports` | all exit 0; 3 contracts kept |
| `pytest -q tests/unit -p no:randomly` (Python 3.12.3) | 36 passed, 1 skipped (TST-011, by design), including the new `test_staging_refuses_console_logs` |
| Markdown tables of every changed file | equal column counts |
| D-103..D-107 and RSK-16 cited in changed files | all defined in TRD 24 |
| grep: "Checkpoint 1 in review", "opened when checkpoint 2" | none left |
| Integration tests and the frontend | unchanged by this round; run by CI on the PR head |

## 10. Review round 2 resolutions (26 October 2026)

| Follow-up question | Reviewer answer | Resolution |
|---|---|---|
| 1. Status of a checkpoint's own features | Set "Complete" in the checkpoint PR before it is merged, once implemented and verified | D-104 amended (TRD 24 v0.17); FEAT-002..FEAT-007 Status "Complete"; `BACKLOG.md` §10 (v0.8): 7 Complete, 0 In Progress; roadmap §2.3 rule (v0.6). The deferred parts noted in section 7 (N-7: ENV-021 and the FEAT-003-AC-08 audit-row check) stay with FEAT-009 and FEAT-012 |
| 2. 14A/14B audit-checklist section | Approved as written | No change |

