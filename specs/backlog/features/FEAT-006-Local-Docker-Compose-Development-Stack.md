# FEAT-006 Local Docker Compose development stack

| Field | Value |
|---|---|
| Epic | DevOps & Deployment |
| Build phase | Phase 3 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-003, FEAT-004 |
| Status | Complete |

## Purpose

Let any developer, CI job or demo operator run the whole of EchoWell (PostgreSQL 16, FastAPI backend, Next.js frontend) on one machine with one command, using the same code as the cloud environments and only local, obviously fake credentials. The local stack is the daily development environment, the base of the E2E stack, and the demo fallback (ARC-081).

## Business Context

- BR-17: single monorepo stack runnable locally (NFR-087: one command, under 10 minutes on an 8 GB laptop).
- BR-15: the same stack is seeded with SRC-05 under `test_v0_1` to show the answer-key Resident list filters "All (10)", "Changed (2)", "Needs attention (2)", "Usual (6)" (DEP-015, DEP-016; seed command delivered by FEAT-017 and FEAT-055).
- BR-16: no real secrets in committed files; synthetic data only; plain HTTP allowed only on localhost (SEC-065, DEP-018).
- RSK-12: the local stack doubles as the demo fallback (ARC-081).

## Referenced TRDs

- TRD 15 DEP-010..DEP-018, DEP-119; §4.2 local setup procedure and Compose outline; DEP-020 (backend Dockerfile base, completed in FEAT-077); AC-DEP-01.
- TRD 21 ENV-040, ENV-041; §4.5 Compose variables; §4.6 template files (`.env.example`, `.env.development.example`, `.env.production.example`).
- TRD 01 ARC-080, ARC-081.
- TRD 12 SEC-065.
- TRD 03 NFR-087.
- TRD 24 D-55 (legacy `version: "3"` compose stub replaced), D-68, D-72, D-90 (provisioning script and `alembic.ini` delivered in Phase 3).

## Scope

- Replace the legacy `docker-compose.yml` (`version: "3"`) with the TRD 15 §4.2 outline (project `name: echowell`):
  - `db`: `postgres:16-alpine`, superuser `echowell` / `local-dev-only-postgres`, database `echowell`, the three `ECHOWELL_*_DB_PASSWORD` local values, port `127.0.0.1:5432`, named volume `pgdata`, mount of `database/roles/provision_login_roles.sql` into `/docker-entrypoint-initdb.d/10_provision_login_roles.sql:ro`, healthcheck `pg_isready -U echowell -d echowell` every 5 s with 10 retries.
  - `backend`: built from `backend/Dockerfile` with the repository root as context, `env_file: .env`, the three login-role URLs, command `alembic upgrade head && uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload`, port `127.0.0.1:8000`, bind mounts `./backend`, `./analytics`, `./database:ro`, `./tests/fixtures:ro`, `depends_on` db healthy.
  - `frontend`: `node:20-alpine`, `npm ci && npm run dev` on port `127.0.0.1:3000`, `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`, volume `frontend_node_modules`.
- A development-capable `backend/Dockerfile` (`python:3.12-slim`, repository-root context, copies `backend/`, `analytics/`, `alembic.ini`, installs `backend/requirements.txt`); hardening (non-root UID 10001, `.dockerignore`, default command without migration) is FEAT-077.
- `database/roles/provision_login_roles.sql` (extensions `pgcrypto` and `btree_gist`, database `timezone` = `UTC`, NOLOGIN group roles, schema ownership and the three login roles, with the content FEAT-008 specifies) and the root `alembic.ini` (`script_location = backend/alembic`) with an empty `backend/alembic/` environment, so the Phase 3 health check returns 200 (TRD 25 §4.6 Phase 3; TRD 24 D-90).
- Root templates `.env.example` (every variable with a comment, secrets empty), `.env.development.example` (exact TRD 21 §4.6 content) and `.env.production.example` (exact TRD 21 §4.6 content).
- Settings validator addition: refuse `local-dev-only`/`ci-only` values in `JWT_SECRET`, any `SEED_*` value or a database URL password when `APP_ENV` is `staging` or `production` (ENV-041).
- Unit test asserting every `Settings` field appears in `.env.example` (ENV-040).
- The local setup procedure of TRD 15 §4.2 reproduced in `docs/deployment.md`.

## Out of Scope

- Alembic migrations, grants and grant tests (FEAT-008).
- The `seed test_v0_1` command and ground-truth loader (FEAT-017, FEAT-055, FEAT-057).
- The `demo` profile service `frontend-prod` (DEP-017), `frontend/Dockerfile` (DEP-023) and production image hardening (DEP-021, DEP-022) (FEAT-077).
- CI service containers (FEAT-007), staging and production hosting (FEAT-081, FEAT-082).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-006-FR-01 | `docker-compose.yml` at the repository root shall define services `db` (`postgres:16-alpine`), `backend` (from `backend/Dockerfile`, port 8000) and `frontend` (Node 20, `next dev`, port 3000), replacing the legacy stub. | DEP-010, D-55 |
| FEAT-006-FR-02 | `db` shall persist to named volume `pgdata`, publish 5432 on 127.0.0.1 only, and use healthcheck `pg_isready -U echowell -d echowell` every 5 s with 10 retries. | DEP-011 |
| FEAT-006-FR-03 | `db` shall run `database/roles/provision_login_roles.sql` from `/docker-entrypoint-initdb.d` as superuser on an empty volume, with the login-role passwords supplied as `ECHOWELL_MIGRATOR_DB_PASSWORD`, `ECHOWELL_APP_DB_PASSWORD`, `ECHOWELL_READONLY_DB_PASSWORD`. | TRD 15 §4.2; TRD 21 §4.5; D-72 |
| FEAT-006-FR-04 | `backend` shall start only after `db` is healthy and shall run `alembic upgrade head` before uvicorn. | DEP-012 |
| FEAT-006-FR-05 | `backend` shall bind-mount `backend/` and `analytics/` and run uvicorn with `--reload`. | DEP-013 |
| FEAT-006-FR-06 | `backend` shall bind-mount `database/` and `tests/fixtures/` read-only at `/app/database` and `/app/tests/fixtures`. | DEP-119 |
| FEAT-006-FR-07 | `backend` shall connect as `echowell_app_login` (`DATABASE_URL`), with `DATABASE_MIGRATION_URL` for `echowell_migrator_login` and `DATABASE_READONLY_URL` for `echowell_readonly_login`. | TRD 15 §4.2; ARC-015 |
| FEAT-006-FR-08 | All published ports shall bind to 127.0.0.1; plain HTTP is used only on localhost with synthetic data. | DEP-011, SEC-065 |
| FEAT-006-FR-09 | `docker-compose.yml` shall contain no secret other than the `local-dev-only-*` placeholders listed in DEP-018 and shall reference no staging or production secret. | DEP-018, GIT-080 |
| FEAT-006-FR-10 | `.env.example`, `.env.development.example` and `.env.production.example` shall exist at the root with the TRD 21 §4.6 content; a unit test shall assert every `Settings` field appears in `.env.example`. | ENV-040 |
| FEAT-006-FR-11 | Secrets in `.env.development.example`, `docker-compose.yml` and `ci.yml` shall be `local-dev-only-*` or `ci-only-*`; the backend and every CLI command shall exit with code 1 when `JWT_SECRET`, any `SEED_*` value or a database URL password contains `local-dev-only` or `ci-only` and `APP_ENV` is `staging` or `production`. | ENV-041, ENV-002 |
| FEAT-006-FR-12 | From a clean clone with `.env` copied from `.env.development.example`, `docker compose up` shall make `http://localhost:8000/api/v1/health` return 200 with `database: "ok"` within 180 s on Docker 24+. | DEP-014, NFR-087 |
| FEAT-006-FR-13 | The local environment shall run the same backend, analytics and frontend code as the cloud environments, configured only through TRD 21 variables. | ARC-080, ARC-081 |
| FEAT-006-FR-14 | The bind mounts shall let `docker compose exec backend python -m backend.cli seed test_v0_1` find `database/seeds/test_v0_1/` and `tests/fixtures/pipeline_input/` (the command itself is delivered later). | DEP-015, DEP-119, D-68 |
| FEAT-006-FR-15 | This feature shall deliver `database/roles/provision_login_roles.sql` and the root `alembic.ini` with an empty Alembic environment, so that the Compose `db` provisions the login roles and the backend connects as `echowell_app_login` in Phase 3. | D-90, D-72, DEP-024 |

## Inputs

- `.env` copied from `.env.development.example`.
- Source trees `backend/`, `analytics/`, `frontend/`, `database/`, `tests/fixtures/`.
- `backend/requirements.txt` (FEAT-002), `create_app()` (FEAT-003), `frontend/` scaffold (FEAT-004).

## Outputs

- Running containers `db`, `backend`, `frontend`; volumes `pgdata`, `frontend_node_modules`.
- Committed `docker-compose.yml`, `backend/Dockerfile`, three `.env*.example` templates, the ENV-040 test, local setup steps in `docs/deployment.md`.

## Data Flow

`docker compose up --build -d` → `db` initialises the empty `pgdata` volume and runs the provisioning script as superuser (extensions, UTC timezone, roles) → healthcheck turns healthy → `backend` runs `alembic upgrade head` as the migrator login role, then uvicorn as the app login role → `frontend` installs and starts `next dev`, calling the API at `http://localhost:8000` from the browser. `docker compose down -v` deletes `pgdata` for a full reset.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-003, FEAT-004

- FEAT-003 provides the backend app, settings validation (extended here by ENV-041) and the health endpoint the stack is checked with.
- FEAT-004 provides the frontend project run by the `frontend` service.

Features that build directly on this one (BACKLOG.md §4): FEAT-008, FEAT-077.

## Database Impact

- Creates the local PostgreSQL 16 server and `echowell` database through the image entrypoint; schema objects come from FEAT-008 onward.
- No table created or modified by this feature.

## API Impact

None exposed. Health (E-01) is consumed to verify the stack.

## Frontend Impact

None in code. The development server runs at `http://localhost:3000` with `NEXT_PUBLIC_APP_ENV=local` (ribbon "LOCAL" from FEAT-004).

## Analytics Impact

None. `analytics/` is bind-mounted into the backend container so edits apply on reload.

## Security Requirements

- Only `local-dev-only-*` placeholder secrets in committed files (DEP-018, ENV-041, GIT-080); real `.env` is git-ignored (TRD 18 §4.11).
- The backend connects as `echowell_app_login`, never as the superuser (TRD 21 §4.6 comment; AGT-060).
- Ports bound to 127.0.0.1 only; HTTP only on localhost (SEC-065).
- Staging and production refuse placeholder credentials (ENV-041).

## Error Handling

| Failure | Behaviour |
|---|---|
| `db` not healthy | `backend` does not start (`depends_on: condition: service_healthy`, DEP-012). |
| `alembic upgrade head` fails | The backend container command exits; `docker compose logs backend` shows the Alembic error. |
| `.env` missing or invalid | Settings validation exits with code 1 and a CRITICAL `startup_config_invalid` record (ENV-002). |
| Stale volume after role or extension change | `docker compose down -v` and restart (TRD 15 §4.2 step 9). |

## Logging Requirements

- `LOG_FORMAT=console` and `LOG_LEVEL=INFO` locally (TRD 21 §4.6); format and fields are FEAT-018.
- No audit rows are generated by the stack itself.

## Testing Requirements

- Unit: `tests/unit/backend/core/test_env_templates.py` asserting every `Settings` field appears in `.env.example` (ENV-040) and that a `local-dev-only` `JWT_SECRET` with `APP_ENV=staging` exits with code 1 (ENV-041, AC-ENV-03).
- Manual/CI check: `docker compose up -d` then `curl -fsS http://localhost:8000/api/v1/health` returns 200 with `database: "ok"` within 180 s (DEP-014; TRD 25 §4.6 Phase 3 Commands).
- Inspection: `grep` over `docker-compose.yml` and Dockerfiles finds no production secret and no `neon.tech` host (AC-DEP-10).
- AC-DEP-01 (full 10-minute Resident list check) is verified after FEAT-055 delivers the full seed.

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-006-AC-01 | `docker compose config` lists exactly the services `db`, `backend`, `frontend` (plus `frontend-prod` only under profile `demo` once FEAT-077 lands), with `db` image `postgres:16-alpine` and all ports bound to `127.0.0.1`. Verified by: Test (run the command in the criterion against the stated environment and check the stated result). | DEP-010, DEP-011 |
| FEAT-006-AC-02 | From a clean clone, `cp .env.development.example .env && docker compose up --build -d` yields `curl -fsS http://localhost:8000/api/v1/health` = 200 with `"database":"ok"` within 180 s. Verified by: Test (run the command in the criterion against the stated environment and check the stated result). | DEP-014 |
| FEAT-006-AC-03 | `docker compose ps` shows `db` healthy before `backend` starts, and the backend log shows `alembic upgrade head` completing before uvicorn starts. Verified by: Test (run the command in the criterion against the stated environment and check the stated result). | DEP-011, DEP-012 |
| FEAT-006-AC-04 | Editing a file in `backend/` triggers a uvicorn reload without rebuilding the image. Verified by: Demo (the demo method of DEP-013, applied to the condition stated in the criterion). | DEP-013 |
| FEAT-006-AC-05 | Inside the backend container, `/app/database/seeds` and `/app/tests/fixtures` exist and are read-only. | DEP-119 |
| FEAT-006-AC-06 | `grep -nE "password\|secret\|key" docker-compose.yml` shows only `local-dev-only-*` values, and `grep -rn "neon.tech" docker-compose.yml backend/Dockerfile` returns nothing. Verified by: Inspection (run the command in the criterion and check its output). | DEP-018, AC-DEP-10 |
| FEAT-006-AC-07 | The ENV-040 unit test passes; starting the backend with `APP_ENV=staging` and `JWT_SECRET=local-dev-only-0123456789abcdef0123456789abcdef` exits with code 1. Verified by: Unit (`tests/unit/backend/core/test_env_templates.py`). | ENV-040, ENV-041, AC-ENV-03 |
| FEAT-006-AC-08 | `.env.development.example` and `.env.production.example` match the TRD 21 §4.6 blocks line for line (comments may differ only in whitespace). Verified by: Unit (`tests/unit/backend/core/test_env_templates.py`). | ENV-040 |

## Definition of Done

- All FEAT-006 acceptance criteria pass on a machine with Docker 24+.
- `docs/deployment.md` contains the TRD 15 §4.2 local procedure verbatim (steps whose commands arrive in later features are marked with the feature that delivers them).
- No real secret committed; batch report lists IDs and command results (AGT-022).

## Implementation Notes

- Resolved (TRD 24 D-90): this feature authors `database/roles/provision_login_roles.sql` and the root `alembic.ini` in Phase 3, so the `echowell_*_login` roles exist and FEAT-006-AC-02 (health 200 with database "ok") is verifiable in the Phase 3 checkpoint PR of Block 3; FEAT-008 adds migrations, grants and grant tests on top.
- `alembic upgrade head` with the empty Alembic environment of Phase 3 (TRD 25 §4.6 Phase 3 Outputs list `backend/alembic/`) is a no-op; this feature adds the root `alembic.ini` (DEP-024, D-90) and FEAT-008 the migrations.
- TRD 15 DEP-010, TRD 16 CIC-012 and TRD 13 TST-002 all name `postgres:16-alpine` (TST-002 aligned in the PR #2 consistency fixes).
- Initialisation scripts in `/docker-entrypoint-initdb.d` run only on an empty volume; changes to the script require `docker compose down -v`.
- Never put `PIPELINE_AS_OF` or `test_v0_1` into `.env.production.example` values for production; the template already documents the staging-only values in comments.
