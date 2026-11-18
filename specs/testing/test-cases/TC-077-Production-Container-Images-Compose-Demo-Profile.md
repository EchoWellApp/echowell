# Production container images, Compose demo profile and environment templates

## Feature Description

FEAT-077 delivers the deployable artefacts (TRD 15 DEP-010..DEP-024, DEP-111, DEP-119; TRD 21 ENV-040, ENV-041, ENV-050..ENV-052; TRD 16 CIC-023; TRD 24 D-55): the backend image `backend/Dockerfile` (`python:3.12-slim`, repository root as context, non-root UID 10001, `uvicorn` only, no migration step, port from `PORT`), the multi-stage frontend image `frontend/Dockerfile` (`node:20-alpine`, `npm ci`, `npm run build`, `next start -p 3000`, build arguments `NEXT_PUBLIC_API_BASE_URL` and `NEXT_PUBLIC_APP_ENV`), the complete `docker-compose.yml` (`db`, `backend`, `frontend` and, under profile `demo`, `frontend-prod` on port 3001; no top-level `version`) and the environment templates `.env.example`, `.env.development.example`, `.env.production.example`. The same backend image runs unchanged on Compose, Render and AWS App Runner.

## Preconditions

- Clean clone of the repository at the commit under test; Docker Engine with Compose v2; `curl`; Python 3.12 with `pip install -r backend/requirements.txt -r backend/requirements-dev.txt` for the unit tests.
- No `.env` present before TC-077-04 (clean clone).
- Ports 5432, 8000, 3000 and 3001 free on 127.0.0.1.
- Local only; nothing here touches the hosted Render, Netlify or Neon deployments.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-077-01 | Backend image runs as UID 10001 and holds no `.env`, `tests`, `specs`, `frontend` | High | Security |
| TC-077-02 | Backend image default command is uvicorn with `${PORT:-8000}` and no `alembic` | High | Positive |
| TC-077-03 | Backend Dockerfile base, context, copied paths and runtime requirements | Medium | Documentation |
| TC-077-04 | Clean clone: `docker compose up --build -d` gives health 200 with `"database":"ok"` within 180 s | High | Positive |
| TC-077-05 | Demo profile: `frontend-prod` healthy and `/login` on :3001 returns 200 | High | Positive |
| TC-077-06 | Compose file has no `version` key and `docker compose config` exits 0 | High | Documentation |
| TC-077-07 | Compose services: db volume, 127.0.0.1 binding, healthchecks, mounts, migration before uvicorn | Medium | Positive |
| TC-077-08 | Backend listens on `PORT` and reads only the three database URLs | Medium | Positive |
| TC-077-09 | Frontend image: multi-stage `node:20-alpine` with the two build arguments | Medium | Positive |
| TC-077-10 | Environment templates exist and pass `test_env_templates.py` | High | Positive |
| TC-077-11 | `.env.production.example` profile, empty `PIPELINE_AS_OF`, no secret value; no `neon.tech` or production secret | High | Security |
| TC-077-12 | Image with `APP_ENV=production` and `PIPELINE_PROFILE=test_v0_1` exits non-zero with a logged error | High | Negative |
| TC-077-13 | Failing migration stops the Compose backend (`&&` chain) | Medium | Negative |
| TC-077-14 | Only `local-dev-only-*` placeholders in Compose; no secret in `NEXT_PUBLIC_*` | High | Security |

### TC-077-01 Backend image runs as UID 10001 and holds no `.env`, `tests`, `specs`, `frontend`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `docker build -f backend/Dockerfile -t echowell-backend:qa .` | Build exits 0. |
| 2 | `docker run --rm --entrypoint id echowell-backend:qa -u` | Prints `10001`. |
| 3 | `docker run --rm --entrypoint sh echowell-backend:qa -c 'ls -a /app'` | Lists `alembic.ini`, `analytics`, `backend`, `database` (and `.`, `..`); none of `.env`, `.env.*`, `tests`, `specs`, `frontend`. |

### TC-077-02 Backend image default command is uvicorn with `${PORT:-8000}` and no `alembic`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `docker inspect --format '{{json .Config.Cmd}}' echowell-backend:qa` | `["sh","-c","uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]`. |
| 2 | `docker inspect --format '{{json .Config.Cmd}} {{json .Config.Entrypoint}}' echowell-backend:qa | grep -c alembic` | `0`. |
| 3 | `docker inspect --format '{{.Config.User}}' echowell-backend:qa` | `10001:10001`. |

### TC-077-03 Backend Dockerfile base, context, copied paths and runtime requirements

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -n "^FROM\|^COPY\|pip install" backend/Dockerfile` | `FROM python:3.12-slim`; copies `backend/requirements.txt`, `alembic.ini`, `analytics/`, `backend/`, `database/`; `pip install -r backend/requirements.txt` only (no `requirements-dev.txt`). |
| 2 | `grep -n "^tests\|^specs\|^frontend\|^\.env" .dockerignore` | Entries `.env`, `.env.*`, `tests`, `specs`, `frontend` present. |
| 3 | `grep -n "script_location" alembic.ini` (file at repository root) | `script_location = backend/alembic`. |

Note: FEAT-077-FR-01 lists `backend/`, `analytics/` and `alembic.ini`; TRD 15 DEP-020 also lists `database/`, which `backend/Dockerfile:30` copies. The case follows DEP-020.

### TC-077-04 Clean clone: `docker compose up --build -d` gives health 200 with `"database":"ok"` within 180 s

| Step | Action | Expected Result |
|---|---|---|
| 1 | `cp .env.development.example .env && time docker compose up --build -d` | Exit 0; services `db`, `backend`, `frontend` created. |
| 2 | Within 180 s of step 1, `curl -s -w '\n%{http_code}\n' http://localhost:8000/api/v1/health` (repeat every 5 s). | HTTP `200`; body contains `"database":"ok"`; first 200 reached ≤ 180 s after step 1 started. |
| 3 | `docker compose ps` | `db` and `backend` "healthy". |

### TC-077-05 Demo profile: `frontend-prod` healthy and `/login` on :3001 returns 200

| Step | Action | Expected Result |
|---|---|---|
| 1 | `docker compose --profile demo up -d --wait db backend frontend-prod` | Exit 0 (all three services report healthy). |
| 2 | `curl -fsS -o /dev/null -w '%{http_code}\n' http://localhost:3001/login` | `200`. |
| 3 | Open `http://localhost:3001/login` in a browser. | Login page with heading "EchoWell" and "Sign in to see voice check-ins". |

### TC-077-06 Compose file has no `version` key and `docker compose config` exits 0

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -n '^version' docker-compose.yml` | No output. |
| 2 | `docker compose config > /dev/null; echo $?` | `0`. |
| 3 | `docker compose --profile demo config --services` | `db`, `backend`, `frontend`, `frontend-prod`. |

### TC-077-07 Compose services: db volume, 127.0.0.1 binding, healthchecks, mounts, migration before uvicorn

| Step | Action | Expected Result |
|---|---|---|
| 1 | `docker compose config` and read `db`. | Image `postgres:16-alpine`; volume `pgdata:/var/lib/postgresql/data`; port `127.0.0.1:5432:5432`; healthcheck `pg_isready -U echowell -d echowell`, interval 5s, retries 10; `database/roles/provision_login_roles.sql` mounted under `/docker-entrypoint-initdb.d`. |
| 2 | Read `backend`. | `depends_on: db: condition: service_healthy`; command `sh -c "alembic upgrade head && uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"`; mounts `./backend`, `./analytics`, `./database:/app/database:ro`, `./tests/fixtures:/app/tests/fixtures:ro`; healthcheck on `http://localhost:8000/api/v1/health`. |
| 3 | Read `frontend-prod`. | Profile `demo`; port `127.0.0.1:3001:3000`; healthcheck `wget -q -O /dev/null http://127.0.0.1:3000/login`. |
| 4 | `docker compose exec -T db psql -U echowell -d echowell -tA -c "SHOW timezone; SELECT extname FROM pg_extension ORDER BY 1;"` | `UTC`; `btree_gist`, `pgcrypto` (and `plpgsql`). |

### TC-077-08 Backend listens on `PORT` and reads only the three database URLs

| Step | Action | Expected Result |
|---|---|---|
| 1 | With the Compose stack of TC-077-04 running: `docker run --rm -d --name ew-port --network echowell_default --env-file .env -e PORT=9100 -p 127.0.0.1:9100:9100 echowell-backend:qa` (`.env` holds the three local database URLs pointing at `db:5432`). | Container starts. |
| 2 | `curl -s -o /dev/null -w '%{http_code}\n' http://localhost:9100/api/v1/health`; then `docker rm -f ew-port`. | `200` (port taken from `PORT`). |
| 3 | `grep -rn "os.environ\|getenv" backend --include=*.py | grep -i "database"` | No direct reads other than through `Settings` fields DATABASE_URL, DATABASE_MIGRATION_URL, DATABASE_READONLY_URL. |

### TC-077-09 Frontend image: multi-stage `node:20-alpine` with the two build arguments

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -n "^FROM\|^ARG\|npm ci\|npm run build\|next\", \"start" frontend/Dockerfile` | Three `FROM node:20-alpine` stages; `ARG NEXT_PUBLIC_API_BASE_URL`, `ARG NEXT_PUBLIC_APP_ENV`; `npm ci`; `npm run build`; `CMD ["node_modules/.bin/next", "start", "-p", "3000"]`. |
| 2 | `docker build --build-arg NEXT_PUBLIC_API_BASE_URL=http://localhost:8000 --build-arg NEXT_PUBLIC_APP_ENV=local -t echowell-frontend:qa frontend` | Exit 0. |
| 3 | `docker build -t echowell-frontend:noargs frontend` (no build arguments). | Build fails in `npm run build` (`lib/config.ts` requires the public variables). |

### TC-077-10 Environment templates exist and pass `test_env_templates.py`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `ls -a | grep '^\.env'` | `.env.development.example`, `.env.example`, `.env.production.example` (and `.env` only if created locally). |
| 2 | `pytest -q tests/unit/backend/core/test_env_templates.py tests/unit/test_env_templates.py` | All tests pass, including `test_env_040_every_settings_field_in_env_example`. |
| 3 | `grep -c "=" .env.example` and compare with the variables of TRD 21 §4.2. | `.env.example` lists every variable with a comment; every secret value is empty. |

Note: FEAT-077-AC-06 names `tests/unit/backend/core/test_env_example.py`; the repository has `tests/unit/backend/core/test_env_templates.py` (and `tests/unit/test_env_templates.py`) instead.

### TC-077-11 `.env.production.example` profile, empty `PIPELINE_AS_OF`, no secret value; no `neon.tech` or production secret

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -n "^PIPELINE_PROFILE=\|^PIPELINE_AS_OF=" .env.production.example` | `PIPELINE_PROFILE=production`; `PIPELINE_AS_OF=` with nothing before the comment. |
| 2 | `grep -nE "^(DATABASE_URL|DATABASE_MIGRATION_URL|DATABASE_READONLY_URL|JWT_SECRET|SENTRY_DSN)=" .env.production.example` | Each value empty; comments state `sslmode=require` for the three URLs and that DATABASE_READONLY_URL must be empty in production. |
| 3 | `grep -rn "neon.tech" docker-compose.yml backend/Dockerfile frontend/Dockerfile` | No output. |
| 4 | `grep -rniE "SEED_.*=.+|JWT_SECRET=.+" docker-compose.yml backend/Dockerfile frontend/Dockerfile` | No output (no production secret). |

### TC-077-12 Image with `APP_ENV=production` and `PIPELINE_PROFILE=test_v0_1` exits non-zero with a logged error

| Step | Action | Expected Result |
|---|---|---|
| 1 | `docker run --rm --env-file .env.development.example -e APP_ENV=production -e PIPELINE_PROFILE=test_v0_1 echowell-backend:qa; echo "exit=$?"` | Container stops; `exit=1`; stderr contains `startup_config_invalid` and names `PIPELINE_PROFILE`; no secret value is printed. |
| 2 | `pytest -q tests/unit/backend/core/test_config.py -k cfg_06` | `test_cfg_06_production_refuses_test_profile` and `test_cfg_06_process_exits_1_with_critical_log` pass. |

### TC-077-13 Failing migration stops the Compose backend (`&&` chain)

| Step | Action | Expected Result |
|---|---|---|
| 1 | `docker compose run --rm --no-deps -e DATABASE_MIGRATION_URL=postgresql+psycopg://nobody:x@db:5432/nodb backend; echo "exit=$?"` | `alembic upgrade head` fails; uvicorn is not started; `exit` non-zero. |
| 2 | `docker compose ps backend` | The regular `backend` service is unaffected (still healthy). |

### TC-077-14 Only `local-dev-only-*` placeholders in Compose; no secret in `NEXT_PUBLIC_*`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -nE "PASSWORD|://[^:]+:[^@]+@" docker-compose.yml` | Every password value is `local-dev-only-postgres`, `local-dev-only-migrator`, `local-dev-only-app` or `local-dev-only-readonly`. |
| 2 | `grep -n "NEXT_PUBLIC_" .env.example .env.development.example .env.production.example docker-compose.yml` | Only `NEXT_PUBLIC_API_BASE_URL` (an origin) and `NEXT_PUBLIC_APP_ENV`; no key, token or password. |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `GET http://localhost:8000/api/v1/health` after `docker compose up` | 200; `"database":"ok"` |
| 2 | `GET http://localhost:9100/api/v1/health` on the image started with `PORT=9100` | 200 |
| 3 | `GET http://localhost:3001/login` (demo profile) | 200 HTML |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SHOW timezone;` on the Compose database | `UTC` |
| 2 | `SELECT extname FROM pg_extension;` | Includes `pgcrypto` and `btree_gist` (created by `provision_login_roles.sql`, not by Alembic) |
| 3 | `SELECT version_num FROM alembic_version;` after `docker compose up` | One row equal to the head revision of `backend/alembic/versions` |
| 4 | `SELECT rolname FROM pg_roles WHERE rolname LIKE 'echowell_%';` | Includes `echowell_app_login`, `echowell_migrator_login`, `echowell_readonly_login` |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Production profile guard (TC-077-12) | Exit 1, `startup_config_invalid` naming `PIPELINE_PROFILE` |
| 2 | Broken migration URL (TC-077-13) | Container exits non-zero, uvicorn not started |
| 3 | Frontend build without build arguments (TC-077-09 step 3) | Build fails |
| 4 | Add a file `tests/x.txt` and rebuild the backend image | `ls -a /app` still shows no `tests` (excluded by `.dockerignore`) |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-077-AC-01 | `docker run --rm --entrypoint id <image> -u` prints `10001`; `ls -a /app` lists none of `.env`, `tests`, `specs`, `frontend` | TC-077-01 |
| FEAT-077-AC-02 | `docker inspect` shows the uvicorn default command and no `alembic` | TC-077-02 |
| FEAT-077-AC-03 | From a clean clone, health returns 200 with `"database":"ok"` within 180 s | TC-077-04 |
| FEAT-077-AC-04 | `docker compose --profile demo up -d --wait db backend frontend-prod` succeeds; `curl -fsS http://localhost:3001/login` returns 200 | TC-077-05 |
| FEAT-077-AC-05 | `grep -n '^version' docker-compose.yml` returns nothing; `docker compose config` exits 0 | TC-077-06 |
| FEAT-077-AC-06 | The env-template unit test passes | TC-077-10 |
| FEAT-077-AC-07 | `.env.production.example` has `PIPELINE_PROFILE=production`, empty `PIPELINE_AS_OF=`, no secret; no `neon.tech` or production secret in Compose and Dockerfiles | TC-077-11 |
| FEAT-077-AC-08 | Image with `APP_ENV=production`, `PIPELINE_PROFILE=test_v0_1` exits non-zero with a logged error | TC-077-12 |

## Test Data Requirements

- No resident data needed; optional `seed test_v0_1` only to log in on :3001.
- Environment templates `.env.example`, `.env.development.example`, `.env.production.example`; variables PORT, DATABASE_URL, DATABASE_MIGRATION_URL, DATABASE_READONLY_URL, APP_ENV, PIPELINE_PROFILE, PIPELINE_AS_OF, NEXT_PUBLIC_API_BASE_URL, NEXT_PUBLIC_APP_ENV.
- Local image tags `echowell-backend:qa`, `echowell-frontend:qa`.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-077-FR-01 / DEP-020, AGT-024 | FEAT-077 | TC-077-03 |
| FEAT-077-FR-02 / DEP-021, CIC-023 | FEAT-077 | TC-077-01 |
| FEAT-077-FR-03 / DEP-022, ARC-090 | FEAT-077 | TC-077-02 |
| FEAT-077-FR-04 / DEP-111, ARC-091, NFR-090 | FEAT-077 | TC-077-08 |
| FEAT-077-FR-05 / DEP-023 | FEAT-077 | TC-077-09 |
| FEAT-077-FR-06 / DEP-010, DEP-017, D-55 | FEAT-077 | TC-077-05, TC-077-06 |
| FEAT-077-FR-07 / DEP-011, D-72 | FEAT-077 | TC-077-07 |
| FEAT-077-FR-08 / DEP-012, DEP-013, DEP-119 | FEAT-077 | TC-077-07, TC-077-13 |
| FEAT-077-FR-09 / TRD 16 §8, CIC-030 | FEAT-077 | TC-077-05, TC-077-07 |
| FEAT-077-FR-10 / DEP-018, ENV-041, SEC-050 | FEAT-077 | TC-077-14 |
| FEAT-077-FR-11 / ENV-040, SEC-051 | FEAT-077 | TC-077-10 |
| FEAT-077-FR-12 / ENV-050, SEC-116, AGT-015 | FEAT-077 | TC-077-11 |
| FEAT-077-FR-13 / SEC-054 | FEAT-077 | TC-077-14 |
| FEAT-077-FR-14 / DEP-014 | FEAT-077 | TC-077-04 |
| FEAT-077-FR-15 / DEP-024 | FEAT-077 | TC-077-03 |
| AGT-015, CFG-06 | FEAT-077 | TC-077-12 |
