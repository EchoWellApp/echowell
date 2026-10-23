# FEAT-077 Production container images, Compose demo profile and environment templates

| Field | Value |
|---|---|
| Epic | DevOps & Deployment |
| Build phase | Phase 9 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-006, FEAT-062 |
| Status | Not Started |

## Purpose

Produce the deployable artefacts every later deployment feature builds on: the final backend image (`python:3.12-slim`, non-root UID 10001, `uvicorn` only, no migration step), the multi-stage frontend image used for local demo and E2E, the complete `docker-compose.yml` with the `demo` profile (`frontend-prod` on port 3001) replacing the legacy stub, and the three environment templates that match the TRD 21 per-environment matrix. The same backend image must run unchanged on Docker Compose, Railway and AWS App Runner.

## Business Context

- BR-17 (Next.js, FastAPI, PostgreSQL, GitHub Actions; portable to AWS): one image for every host (DEP-022, ARC-090, NFR-090).
- BR-16: the image holds no `.env`, tests, `specs/` or `frontend/`, runs as non-root, and templates carry no real secret (DEP-021, ENV-041, SEC-050).
- RSK-12 (timeline): the `demo` profile is the local fallback for the end-of-semester demo (DEP-017, DEP-090) and the stack for E2E (CIC-030).

## Referenced TRDs

- TRD 15 DEP-010, DEP-011, DEP-012, DEP-017, DEP-018, DEP-020, DEP-021, DEP-022, DEP-023, DEP-024, DEP-111, DEP-119, §4.2 Compose outline, §8 Implementation Notes.
- TRD 21 ENV-040, ENV-041, ENV-050, ENV-051, ENV-052, §4.6 template contents, §4.7 per-environment matrix.
- TRD 16 CIC-023 (image checks in `docker-build`), §8 notes on Compose healthchecks.
- TRD 01 ARC-090, ARC-091.
- TRD 03 NFR-090, NFR-087.
- TRD 12 SEC-050, SEC-051, SEC-054, SEC-065.
- TRD 24 D-55 (legacy `docker-compose.yml` `version: "3"` stub replaced in Phase 9), D-53, D-65, D-72.
- TRD 25 §4.6 Phase 9 outputs and definition of done, AGT-010, AGT-014, AGT-015, AGT-016.

## Scope

- `backend/Dockerfile`: build context = repository root, `FROM python:3.12-slim`, `WORKDIR /app`, copy `backend/` to `/app/backend`, `analytics/` to `/app/analytics` and `alembic.ini`, `ENV PYTHONPATH=/app`, install only `backend/requirements.txt` (with `psycopg[binary]` 3.x, D-53), create and switch to a user with UID 10001, default command `sh -c "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"`.
- Root `.dockerignore` excluding `.env`, `.env.*` (except none needed), `tests/`, `specs/`, `frontend/`, `docs/`, `.git`.
- `frontend/Dockerfile`: multi-stage `node:20-alpine` (`npm ci`, `npm run build`, `next start -p 3000`) with build arguments `NEXT_PUBLIC_API_BASE_URL` and `NEXT_PUBLIC_APP_ENV`; used for local demo and E2E only, never for Netlify.
- `docker-compose.yml` replacing the legacy stub (no top-level `version` key): services `db` (`postgres:16-alpine`, volume `pgdata`, `127.0.0.1:5432`, healthcheck `pg_isready -U echowell -d echowell` every 5 s, 10 retries, provisioning script mounted into `/docker-entrypoint-initdb.d`), `backend` (built from `backend/Dockerfile`, `alembic upgrade head` then uvicorn `--reload`, read-only mounts of `database/` and `tests/fixtures/`, healthcheck on `/api/v1/health`), `frontend` (`node:20-alpine`, `next dev` :3000), `frontend-prod` (profile `demo`, built from `frontend/Dockerfile`, `127.0.0.1:3001:3000`, healthcheck on `/login`), volumes `pgdata` and `frontend_node_modules`.
- `.env.example` (every `Settings` field and every frontend variable with a one-line comment, secrets empty), `.env.development.example` and `.env.production.example` with exactly the TRD 21 §4.6 content.
- A unit test asserting every field of `Settings` appears in `.env.example` (ENV-040).

## Out of Scope

- Railway, Netlify and Neon configuration (`railway.toml`, `railway.nightly.toml`, `netlify.toml`; FEAT-081, FEAT-082).
- CI jobs that build and inspect the images (`docker-build` in `ci.yml`, FEAT-078) and the E2E workflow (FEAT-080).
- The development stack basics already delivered by FEAT-006 (kept and extended, not rewritten).
- Any deployment to a hosted environment (Phase 10, FEAT-088); AWS ECR/App Runner set-up (FEAT-092).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-077-FR-01 | `backend/Dockerfile` shall build from `python:3.12-slim` with the repository root as context, copy `backend/`, `analytics/` and `alembic.ini`, and install only `backend/requirements.txt`. | DEP-020, AGT-024 |
| FEAT-077-FR-02 | The backend image shall run as UID 10001 and shall not contain `.env` files, `tests/`, `specs/` or `frontend/` (root `.dockerignore`). | DEP-021, CIC-023 |
| FEAT-077-FR-03 | The backend image default command shall be `sh -c "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"` with no migration step. | DEP-022, ARC-090 |
| FEAT-077-FR-04 | The backend shall read its port only from `PORT` (default 8000) and its databases only from `DATABASE_URL`, `DATABASE_MIGRATION_URL`, `DATABASE_READONLY_URL`, and keep no state on local disk between requests. | DEP-111, ARC-091, NFR-090 |
| FEAT-077-FR-05 | `frontend/Dockerfile` shall be a multi-stage `node:20-alpine` build running `npm ci`, `npm run build` and `next start -p 3000`, taking `NEXT_PUBLIC_API_BASE_URL` and `NEXT_PUBLIC_APP_ENV` as build arguments. | DEP-023 |
| FEAT-077-FR-06 | `docker-compose.yml` shall define `db`, `backend`, `frontend` and, under profile `demo`, `frontend-prod` on port 3001, as in the TRD 15 §4.2 outline, and shall not contain a top-level `version` key. | DEP-010, DEP-017, D-55 |
| FEAT-077-FR-07 | The `db` service shall use volume `pgdata`, bind 5432 to 127.0.0.1 only, define the `pg_isready` healthcheck (5 s, 10 retries) and mount `database/roles/provision_login_roles.sql` into `/docker-entrypoint-initdb.d` (extensions, `timezone` UTC, roles). | DEP-011, D-72 |
| FEAT-077-FR-08 | The `backend` service shall start after `db` is healthy, run `alembic upgrade head` before uvicorn, bind-mount `backend/`, `analytics/`, and read-only `database/` and `tests/fixtures/` at `/app/database` and `/app/tests/fixtures`. | DEP-012, DEP-013, DEP-119 |
| FEAT-077-FR-09 | `backend` and `frontend-prod` shall have healthchecks (`/api/v1/health` and `/login`) so `docker compose up --wait` works. | TRD 16 §8, CIC-030 |
| FEAT-077-FR-10 | The Compose file shall contain no secret other than the `local-dev-only-*` placeholders (`local-dev-only-postgres`, `local-dev-only-migrator`, `local-dev-only-app`, `local-dev-only-readonly`) and shall never reference staging or production secrets. | DEP-018, ENV-041, SEC-050 |
| FEAT-077-FR-11 | `.env.example`, `.env.development.example` and `.env.production.example` shall exist at the repository root with the content of TRD 21 §4.6; `.env.example` shall be the union of all variables with comments and empty secrets. | ENV-040, SEC-051 |
| FEAT-077-FR-12 | `.env.production.example` shall set `PIPELINE_PROFILE=production`, leave `PIPELINE_AS_OF` empty for production, leave every secret empty, and state that DATABASE_URL, DATABASE_MIGRATION_URL and DATABASE_READONLY_URL must include `sslmode=require` and that DATABASE_READONLY_URL is empty in production. | ENV-050, SEC-116, AGT-015, TRD 25 §4.6 Phase 9 DoD |
| FEAT-077-FR-13 | No `NEXT_PUBLIC_*` variable in any template shall hold a secret. | SEC-054 |
| FEAT-077-FR-14 | `docker compose up` from a clean clone with `.env` copied from `.env.development.example` shall make `http://localhost:8000/api/v1/health` return 200 with `database: "ok"` within 180 s. | DEP-014 |
| FEAT-077-FR-15 | `alembic.ini` shall stay at the repository root with `script_location = backend/alembic`. | DEP-024 |

## Inputs

- Existing skeleton files: `backend/Dockerfile`, `frontend/Dockerfile` (if present), legacy `docker-compose.yml` stub (`version: "3"`), `backend/requirements.txt`, `alembic.ini` (AGT-010: kept and filled in).
- Development stack and templates of FEAT-006; frontend build of FEAT-062 (`npm run build` must succeed).
- TRD 21 §4.6 template text and §4.7 matrix.

## Outputs

- `backend/Dockerfile`, `frontend/Dockerfile`, `.dockerignore`, `docker-compose.yml`.
- `.env.example`, `.env.development.example`, `.env.production.example`.
- `tests/unit/backend/core/test_env_example.py` (Settings fields present in `.env.example`).

## Data Flow

Source tree → `docker build -f backend/Dockerfile .` → backend image (no tests, non-root) → Compose `backend` service (local, with mounts and `--reload`) or Railway/App Runner (same image, `PORT` injected, migrations run by the platform pre-deploy step, FEAT-081/FEAT-092). `frontend/` → `docker build frontend` with build args → `frontend-prod` on :3001 → browser → backend :8000. Templates → copied to `.env` locally or used as the key checklist for Railway/Netlify (FEAT-081, FEAT-082, FEAT-088).

## Dependencies

Required before implementation (BACKLOG.md): FEAT-006, FEAT-062

- [FEAT-006](FEAT-006-Local-Docker-Compose-Development-Stack.md) Local Docker Compose development stack (db, backend, frontend services and first templates).
- [FEAT-062](FEAT-062-Frontend-Foundations.md) Frontend foundations (a frontend that builds with `npm run build`, API base URL handling).

Features that build directly on this one (BACKLOG.md §4): FEAT-078, FEAT-079, FEAT-081, FEAT-082.

## Database Impact

None. The provisioning script and migrations are owned by the database features; this feature only mounts `database/roles/provision_login_roles.sql` and runs `alembic upgrade head` in the Compose backend command.

## API Impact

None exposed or changed. The images serve the existing API; `GET /api/v1/health` is used as the container healthcheck.

## Frontend Impact

- `frontend/Dockerfile` and the `frontend-prod` Compose service (production build on :3001).
- No page or component change.

## Analytics Impact

None. `analytics/` is copied into the backend image unchanged (D-61).

## Security Requirements

- Backend container user UID 10001; image without `.env`, tests, `specs/`, `frontend/` (DEP-021).
- Ports bound to 127.0.0.1 locally (DEP-011, Compose outline); plain HTTP allowed only on localhost with synthetic data (SEC-065).
- Templates: secrets empty or `local-dev-only-*` placeholders only; the backend refuses those placeholders when APP_ENV is `staging` or `production` (ENV-041).
- Production template enforces `PIPELINE_PROFILE=production` and no `PIPELINE_AS_OF` (AGT-015).

## Error Handling

- If `alembic upgrade head` fails in the Compose backend command, the container exits non-zero and uvicorn does not start (`&&` chain).
- `docker compose up --wait` fails when a healthcheck never passes; the developer inspects `docker compose logs`.
- Image build fails on any missing pinned dependency (no unpinned install).

## Logging Requirements

- Containers log to stdout only (TRD 17 LOG-001); `LOG_FORMAT=console` locally, `json` in CI and hosted environments (TRD 21 §4.7).
- No audit records are generated by this feature.

## Testing Requirements

- Unit: `test_env_example.py` (ENV-040).
- Integration/CI: `docker build -f backend/Dockerfile .`; `test "$(docker run --rm --entrypoint id echowell-backend:ci -u)" = "10001"`; no `.env`, `tests`, `specs`, `frontend` under `/app` (CIC-023; job wired by FEAT-078).
- Smoke: `docker compose config` and `docker compose up -d && pytest -q` (TRD 25 §4.6 Phase 9 Commands); `docker compose --profile demo up -d --wait db backend frontend-prod` followed by `curl -fsS http://localhost:3001/login`.
- Regression: startup-guard test (AGT-015, CFG-06) still passes with the image.

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-077-AC-01 | `docker run --rm --entrypoint id <backend image> -u` prints `10001`, and `ls -a /app` in the image lists none of `.env`, `tests`, `specs`, `frontend`. Verified by: Test (run the command in the criterion against the stated environment and check the stated result). | DEP-021, CIC-023 |
| FEAT-077-AC-02 | `docker inspect` of the backend image shows the default command `sh -c "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"` and no `alembic` in it. Verified by: Test (run the command in the criterion against the stated environment and check the stated result). | DEP-022 |
| FEAT-077-AC-03 | From a clean clone, `cp .env.development.example .env && docker compose up --build -d` makes `curl -s http://localhost:8000/api/v1/health` return 200 with `"database":"ok"` within 180 s. Verified by: Test (run the command in the criterion against the stated environment and check the stated result). | DEP-014 |
| FEAT-077-AC-04 | `docker compose --profile demo up -d --wait db backend frontend-prod` succeeds and `curl -fsS http://localhost:3001/login` returns 200. Verified by: Test (run the command in the criterion against the stated environment and check the stated result). | DEP-017 |
| FEAT-077-AC-05 | `grep -n '^version' docker-compose.yml` returns nothing and `docker compose config` exits 0. Verified by: Inspection (run the command in the criterion and check its output). | D-55 |
| FEAT-077-AC-06 | `tests/unit/backend/core/test_env_example.py` passes. | ENV-040, AC-ENV-08 |
| FEAT-077-AC-07 | `.env.production.example` contains `PIPELINE_PROFILE=production`, an empty `PIPELINE_AS_OF=` and no non-empty secret value; `grep -r` over `docker-compose.yml` and both Dockerfiles finds no hostname containing `neon.tech` and no production secret. Verified by: Inspection (run the command in the criterion and check its output). | AC-DEP-10, ENV-050 |
| FEAT-077-AC-08 | Running the backend image with `APP_ENV=production` and `PIPELINE_PROFILE=test_v0_1` exits non-zero with a logged error. Verified by: Test (CFG-06). | AGT-015, AC-AGT-05 |

## Definition of Done

- All FEAT-077 acceptance criteria pass; existing skeleton files kept at their paths (AGT-010, AC-AGT-06).
- `docs/reports/CONFIGURATION_VALIDATION_REPORT.md` (written by FEAT-087) can cite the image and template checks.
- Batch report entry with commands and results (AGT-022).

## Implementation Notes

- Start uvicorn from the repository root module path `backend.main:app`; `analytics` must import as a top-level package (TRD 15 §8).
- Keep the `sh -c` wrapper so `${PORT:-8000}` is expanded on Railway and App Runner.
- Normalise `postgres://` and `postgresql://` URLs to `postgresql+psycopg://` in settings, not in templates (TRD 15 §8, AC-ENV-05).
- `frontend-prod` must not inherit `next dev` settings; build args are baked at build time, so rebuild after changing `NEXT_PUBLIC_*` (TRD 21 §8).
- The `db` provisioning script runs only on an empty volume; `docker compose down -v` resets it (TRD 15 §4.2 step 9).
