# FEAT-006 Local Docker Compose development stack

## Feature Description

FEAT-006 runs the whole of EchoWell on one machine with one command: `docker-compose.yml` defines `db` (`postgres:16-alpine`, named volume `pgdata`, healthcheck `pg_isready -U echowell -d echowell` every 5 s with 10 retries, provisioning script `database/roles/provision_login_roles.sql` on an empty volume), `backend` (built from `backend/Dockerfile`, waits for a healthy `db`, runs `alembic upgrade head` then uvicorn `--reload` on port 8000, connects as `echowell_app_login`) and `frontend` (Node 20, `next dev`, port 3000). All ports bind to `127.0.0.1`; the only secrets are `local-dev-only-*` placeholders. The three root templates `.env.example`, `.env.development.example`, `.env.production.example` follow TRD 21 §4.6.

## Preconditions

- Docker 24+ with Compose v2 (`docker compose version`).
- A clean clone (`git status` clean); ports 3000, 5432 and 8000 free on the host.
- No earlier stack state for TC-006-02: `docker compose down -v` (removes `pgdata`).
- Python 3.12 venv with dev requirements for the unit-test steps.
- Database checks connect as the Compose superuser: `docker compose exec db psql -U echowell -d echowell`.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-006-01 | `docker compose config` lists exactly `db`, `backend`, `frontend` (+ `frontend-prod` under `demo`), image and loopback ports | High | Positive |
| TC-006-02 | From a clean clone, health returns 200 `"database":"ok"` within 180 s | High | Positive |
| TC-006-03 | `db` healthy before `backend` starts; `alembic upgrade head` completes before uvicorn | High | Positive |
| TC-006-04 | Editing a `backend/` file reloads uvicorn without an image rebuild | High | Positive |
| TC-006-05 | `/app/database/seeds` and `/app/tests/fixtures` exist read-only in the backend container | High | Positive |
| TC-006-06 | Compose file holds only `local-dev-only-*` secrets and no hosted database host | High | Security |
| TC-006-07 | ENV-040 template test passes; a `local-dev-only` `JWT_SECRET` in staging exits 1 | High | Negative |
| TC-006-08 | `.env.development.example` and `.env.production.example` match TRD 21 §4.6 | High | Positive |
| TC-006-09 | Provisioning creates the extensions, timezone and login roles; backend connects as `echowell_app_login` | Medium | Database |
| TC-006-10 | Seed command finds the seed and fixture folders through the bind mounts | Medium | Positive |
| TC-006-11 | Failure paths: missing `.env`, failing migration, unhealthy `db` | Medium | Negative |
| TC-006-12 | Frontend dev server answers on `127.0.0.1:3000` and calls the local API | Medium | UI |

### TC-006-01 `docker compose config` lists exactly `db`, `backend`, `frontend` (+ `frontend-prod` under `demo`), image and loopback ports

| Step | Action | Expected Result |
|---|---|---|
| 1 | `cp .env.development.example .env` then `docker compose config --services`. | Exactly three lines: `db`, `backend`, `frontend`. |
| 2 | `docker compose --profile demo config --services`. | Four lines: `db`, `backend`, `frontend`, `frontend-prod`. |
| 3 | `docker compose config \| grep -n "image: postgres"`. | `image: postgres:16-alpine`. |
| 4 | `docker compose --profile demo config \| grep -n "host_ip"`. | Every published port has `host_ip: 127.0.0.1` (5432, 8000, 3000, 3001); no port bound to `0.0.0.0`. |
| 5 | `docker compose config \| grep -n -A3 "healthcheck" \| head -8`. | `db` healthcheck test `pg_isready -U echowell -d echowell`, `interval: 5s`, `retries: 10`. |
| 6 | `docker compose config \| grep -n "pgdata"`. | `db` mounts named volume `pgdata` at `/var/lib/postgresql/data`. |

### TC-006-02 From a clean clone, health returns 200 `"database":"ok"` within 180 s

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `cp .env.development.example .env && date +%s > /tmp/qa_t0 && docker compose up --build -d`. | Images build; three containers start. |
| 2 | Poll: `until curl -fsS http://localhost:8000/api/v1/health; do sleep 5; done; echo; echo $(( $(date +%s) - $(cat /tmp/qa_t0) ))s`. | The JSON printed contains `"status":"ok"` and `"database":"ok"`; elapsed seconds ≤ 180. |
| 3 | `curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/v1/health`. | `200`. |

### TC-006-03 `db` healthy before `backend` starts; `alembic upgrade head` completes before uvicorn

| Step | Action | Expected Result |
|---|---|---|
| 1 | `docker compose down -v && docker compose up -d` and immediately run `docker compose ps` every 2 s for 30 s. | `db` shows `(health: starting)` then `(healthy)`; `backend` is created/started only after `db` is `(healthy)` (`depends_on: condition: service_healthy`). |
| 2 | `docker compose logs backend \| grep -n "alembic\|Uvicorn running"`. | Alembic lines (`INFO  [alembic.runtime.migration] Running upgrade  -> 0001`, … `-> 0004`) appear on lower line numbers than `Uvicorn running on http://0.0.0.0:8000`. |
| 3 | `docker compose exec db psql -U echowell -d echowell -c "SELECT version_num FROM alembic_version;"`. | One row `0004`. |

### TC-006-04 Editing a `backend/` file reloads uvicorn without an image rebuild

| Step | Action | Expected Result |
|---|---|---|
| 1 | Note `docker compose images backend` (image ID). | Image ID noted. |
| 2 | Append the line `# qa reload check` to `backend/api/health.py` and save. | File saved on the host. |
| 3 | Within 10 s run `docker compose logs --since 30s backend`. | Log shows `WatchFiles detected changes in 'backend/api/health.py'. Reloading...` followed by `Application startup complete.` |
| 4 | Re-run `docker compose images backend`; call `curl -fsS http://localhost:8000/api/v1/health`. | Same image ID (no rebuild); health still 200. |
| 5 | Remove the added line. | `git status` clean; another reload is logged. |

### TC-006-05 `/app/database/seeds` and `/app/tests/fixtures` exist read-only in the backend container

| Step | Action | Expected Result |
|---|---|---|
| 1 | `docker compose exec backend ls /app/database/seeds/test_v0_1 /app/tests/fixtures`. | `test_v0_1` lists `facilities.csv`, `residents.csv`, `devices.csv`, `device_assignments.csv`, `EchoWell_pipeline_test_input_v0_1.csv`; `/app/tests/fixtures` lists the fixture folders (including `pipeline_input`). |
| 2 | `docker compose exec backend sh -c 'touch /app/database/seeds/qa.txt'`. | `touch: cannot touch '/app/database/seeds/qa.txt': Read-only file system`; non-zero exit. |
| 3 | `docker compose exec backend sh -c 'touch /app/tests/fixtures/qa.txt'`. | `Read-only file system`; non-zero exit. |
| 4 | `docker compose exec backend sh -c 'grep " /app/database \| /app/tests/fixtures " /proc/mounts'`. | Both mounts show option `ro`. |

### TC-006-06 Compose file holds only `local-dev-only-*` secrets and no hosted database host

| Step | Action | Expected Result |
|---|---|---|
| 1 | `grep -niE "password\|secret\|key" docker-compose.yml`. | Each match is a comment or a value starting `local-dev-only-` (`POSTGRES_PASSWORD`, `ECHOWELL_MIGRATOR_DB_PASSWORD`, `ECHOWELL_APP_DB_PASSWORD`, `ECHOWELL_READONLY_DB_PASSWORD` and the passwords inside the three `postgresql+psycopg://…@db:5432/echowell` URLs). |
| 2 | `grep -rn "neon.tech" docker-compose.yml backend/Dockerfile; echo "exit=$?"`. | `exit=1`. |
| 3 | `grep -niE "render.com\|onrender\|amazonaws" docker-compose.yml backend/Dockerfile; echo "exit=$?"`. | `exit=1` (no staging or production host). |
| 4 | `pytest -q tests/unit/test_env_templates.py -k "compose or hosted"`. | All selected tests pass. |

### TC-006-07 ENV-040 template test passes; a `local-dev-only` `JWT_SECRET` in staging exits 1

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest -q tests/unit/backend/core/test_env_templates.py`. | `test_env_040_every_settings_field_in_env_example`, `test_env_040_templates_match_trd21` and `test_env_041_local_dev_jwt_refused_in_staging` pass. |
| 2 | `docker compose run --rm --no-deps -e APP_ENV=staging -e JWT_SECRET=local-dev-only-$(openssl rand -hex 16) backend python -c "from backend.main import create_app; create_app()"; echo "exit=$?"`. | A CRITICAL `startup_config_invalid:` record contains `JWT_SECRET` (placeholder refused in staging and production); `exit=1`. |
| 3 | Repeat step 2 with `APP_ENV=local` and the default `JWT_SECRET` from `.env`. | No `startup_config_invalid`; `exit=0`. |
| 4 | `docker compose run --rm --no-deps -e APP_ENV=staging backend python -m backend.cli bootstrap; echo "exit=$?"` (the `local-dev-only-*` database passwords of the Compose URLs stay in place). | Exit code `1` before any database work, with `startup_config_invalid` containing `DATABASE_URL: placeholder password refused in staging and production` — CLI commands apply ENV-041 too. |

### TC-006-08 `.env.development.example` and `.env.production.example` match TRD 21 §4.6

| Step | Action | Expected Result |
|---|---|---|
| 1 | Copy the `.env.development.example` block of TRD 21 §4.6 to `/tmp/qa_dev.txt` and run `diff -w /tmp/qa_dev.txt .env.development.example`. | No difference other than whitespace inside comments. |
| 2 | Same for the `.env.production.example` block. | No difference other than whitespace inside comments. |
| 3 | `grep -nE "^(JWT_SECRET\|SEED_[A-Z_]+)=" .env.development.example`. | Each secret value starts with `local-dev-only-`. |
| 4 | `grep -nE "^(JWT_SECRET\|SEED_[A-Z_]+\|DATABASE_[A-Z_]*URL)=" .env.production.example`. | No real secret value (empty or a documented placeholder without credentials). |
| 5 | `pytest -q tests/unit/test_env_templates.py`. | All tests pass. |

### TC-006-09 Provisioning creates the extensions, timezone and login roles; backend connects as `echowell_app_login`

| Step | Action | Expected Result |
|---|---|---|
| 1 | In psql: `SELECT extname FROM pg_extension ORDER BY 1;` | `btree_gist`, `pgcrypto`, `plpgsql`. |
| 2 | `SHOW timezone;` | `UTC`. |
| 3 | `SELECT rolname, rolcanlogin FROM pg_roles WHERE rolname LIKE 'echowell_%' ORDER BY 1;` | `echowell_app` f, `echowell_app_login` t, `echowell_migrator` f, `echowell_migrator_login` t, `echowell_readonly` f, `echowell_readonly_login` t. |
| 4 | After one health call: `SELECT DISTINCT usename FROM pg_stat_activity WHERE datname = 'echowell' AND usename LIKE 'echowell_%';` | `echowell_app_login` is listed (the backend's pool); the backend never connects as `echowell`. |
| 5 | `docker compose logs db \| grep -i "password"`. | No password value is printed by the provisioning script. |

### TC-006-10 Seed command finds the seed and fixture folders through the bind mounts

| Step | Action | Expected Result |
|---|---|---|
| 1 | `docker compose exec backend python -m backend.cli seed test_v0_1; echo "exit=$?"`. | Completes with `exit=0`; no "file not found" for `database/seeds/test_v0_1/` or `tests/fixtures/pipeline_input/`; no secret is printed. |
| 2 | In psql: `SELECT count(*) FROM residents;` and `SELECT count(*) FROM raw_sessions;` | `residents` = 10 (R01–R10); `raw_sessions` = 283 (the SRC-05 arrivals, DS-01). |

### TC-006-11 Failure paths: missing `.env`, failing migration, unhealthy `db`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `mv .env /tmp/qa_env && docker compose up -d backend; echo "exit=$?"`. | Compose refuses: `env file … .env not found`; non-zero exit. Restore with `mv /tmp/qa_env .env`. |
| 2 | Set `JWT_SECRET=short` in `.env`, run `docker compose up -d --force-recreate backend` and `docker compose logs backend`. | Log has CRITICAL `startup_config_invalid:` naming `JWT_SECRET`; `docker compose ps backend` shows the container exited / restarting, health not reachable. Restore `.env`. |
| 3 | `docker compose stop db` then `docker compose up -d --force-recreate backend`. | `backend` is not started while `db` is unhealthy (Compose waits on the `service_healthy` condition and reports `dependency failed to start` if `db` stays down). Restart `db` afterwards. |
| 4 | In a scratch tree add `raise RuntimeError("qa")` at the top of `upgrade()` in a copy of the newest migration, recreate `backend`, check `docker compose logs backend`. | The Alembic traceback with `RuntimeError: qa` is shown; uvicorn never starts (the `&&` chain stops); container exits non-zero. Revert the change. |

### TC-006-12 Frontend dev server answers on `127.0.0.1:3000` and calls the local API

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `http://localhost:3000/login`. | The sign-in page renders with the `LOCAL` ribbon at the top. |
| 2 | Sign in as `clinician@example.com` with `SEED_CLINICIAN_PASSWORD` from `.env` and watch the browser network tab. | Requests go to `http://localhost:8000/api/v1/…` (origin of `NEXT_PUBLIC_API_BASE_URL`), e.g. `POST /api/v1/auth/login` → 200. |
| 3 | From another machine on the network, try `http://<host-ip>:3000`. | Connection refused (bound to 127.0.0.1 only). |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `curl -fsS http://localhost:8000/api/v1/health` after `docker compose up` | 200, `{"status":"ok","database":"ok","version":"unknown",…}` within 180 s |
| 2 | Same with `db` stopped | 503 `{"status":"degraded","database":"unavailable",…}` |
| 3 | `curl http://<host-ip>:8000/api/v1/health` from another machine | Connection refused (loopback binding) |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT extname FROM pg_extension ORDER BY 1;` | `btree_gist`, `pgcrypto`, `plpgsql` |
| 2 | `SELECT rolname FROM pg_roles WHERE rolname LIKE 'echowell_%' ORDER BY 1;` | The three group roles and three login roles |
| 3 | `SELECT version_num FROM alembic_version;` | `0004` |
| 4 | `docker volume ls \| grep pgdata` | Volume `echowell_pgdata` exists; removed by `docker compose down -v` |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Staging + `local-dev-only` `JWT_SECRET` (TC-006-07) | Exit 1, `startup_config_invalid` naming `JWT_SECRET` |
| 2 | `.env` missing (TC-006-11) | Compose refuses to start `backend` |
| 3 | Invalid `.env` value (TC-006-11) | CRITICAL `startup_config_invalid`, backend exits |
| 4 | Failing migration (TC-006-11) | Alembic error in `docker compose logs backend`; uvicorn not started |
| 5 | `db` unhealthy (TC-006-11) | `backend` not started |
| 6 | Write into a read-only mount (TC-006-05) | `Read-only file system` |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-006-AC-01 | `docker compose config` lists exactly `db`, `backend`, `frontend` (+ `frontend-prod` under `demo`); `db` image `postgres:16-alpine`; all ports on `127.0.0.1`. | TC-006-01 |
| FEAT-006-AC-02 | Clean clone + `cp .env.development.example .env && docker compose up --build -d` → health 200 with `"database":"ok"` within 180 s. | TC-006-02 |
| FEAT-006-AC-03 | `db` healthy before `backend` starts; `alembic upgrade head` completes before uvicorn. | TC-006-03 |
| FEAT-006-AC-04 | Editing a `backend/` file triggers a uvicorn reload without rebuilding the image. | TC-006-04 |
| FEAT-006-AC-05 | `/app/database/seeds` and `/app/tests/fixtures` exist and are read-only. | TC-006-05 |
| FEAT-006-AC-06 | Compose secrets are only `local-dev-only-*`; no `neon.tech` in `docker-compose.yml` or `backend/Dockerfile`. | TC-006-06 |
| FEAT-006-AC-07 | ENV-040 unit test passes; staging + `local-dev-only-…` `JWT_SECRET` exits 1. | TC-006-07 |
| FEAT-006-AC-08 | `.env.development.example` and `.env.production.example` match TRD 21 §4.6 line for line. | TC-006-08 |

## Test Data Requirements

- `.env` copied from `.env.development.example` (placeholders only; never edit in real secrets).
- `test_v0_1` seed files under `database/seeds/test_v0_1/` and `tests/fixtures/` (synthetic R01–R10, D01–D10, D07B).
- Seeded users `admin@example.com`, `clinician@example.com`, `researcher@example.com` with the `SEED_*` passwords from `.env`.
- A `JWT_SECRET` for TC-006-07 generated as `local-dev-only-` + 32 random hex characters.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-006-FR-01 (DEP-010, D-55) | FEAT-006 | TC-006-01 |
| FEAT-006-FR-02 (DEP-011) | FEAT-006 | TC-006-01, TC-006-03 |
| FEAT-006-FR-03 (TRD 15 §4.2, TRD 21 §4.5, D-72) | FEAT-006 | TC-006-09 |
| FEAT-006-FR-04 (DEP-012) | FEAT-006 | TC-006-03, TC-006-11 |
| FEAT-006-FR-05 (DEP-013) | FEAT-006 | TC-006-04 |
| FEAT-006-FR-06 (DEP-119) | FEAT-006 | TC-006-05 |
| FEAT-006-FR-07 (TRD 15 §4.2, ARC-015) | FEAT-006 | TC-006-09 |
| FEAT-006-FR-08 (DEP-011, SEC-065) | FEAT-006 | TC-006-01, TC-006-12 |
| FEAT-006-FR-09 (DEP-018, GIT-080) | FEAT-006 | TC-006-06 |
| FEAT-006-FR-10 (ENV-040) | FEAT-006 | TC-006-07, TC-006-08 |
| FEAT-006-FR-11 (ENV-041, ENV-002) | FEAT-006 | TC-006-07 |
| FEAT-006-FR-12 (DEP-014, NFR-087) | FEAT-006 | TC-006-02 |
| FEAT-006-FR-13 (ARC-080, ARC-081) | FEAT-006 | TC-006-02, TC-006-12 |
| FEAT-006-FR-14 (DEP-015, DEP-119, D-68) | FEAT-006 | TC-006-10 |
| FEAT-006-FR-15 (D-90, D-72, DEP-024) | FEAT-006 | TC-006-09 |
| AC-DEP-10 | FEAT-006 | TC-006-06 |
| AC-ENV-03 | FEAT-006 | TC-006-07 |
| AC-DEP-01 (full Resident list check) | FEAT-006 | Out of scope here: verified after FEAT-055 (seed) |
