# Deployment and local environment

Operational guide (TRD 18 GIT-054). Requirements: TRD 15 (deployment), TRD 21 (configuration), TRD 16 (CI/CD). Staging, production and the AWS target are documented from Block 3 checkpoint 8 (FEAT-077..FEAT-086).

## Local environment (Docker Compose)

The local setup procedure of TRD 15 §4.2, reproduced verbatim. Steps 6–8 need commands delivered by later features: `backend.cli seed test_v0_1` (FEAT-017 for `--master-only`, FEAT-055 for the full seed), `database/seeds/load_evaluation_ground_truth.py` (FEAT-057) and the frontend pages (FEAT-063..FEAT-074). Until then steps 1–5 and 9 work and the health check returns `"database":"ok"`.

1. Install Docker Desktop 4.x (or Docker Engine 24+ with Compose v2), Git, and optionally Node.js 20 LTS and Python 3.12 for running tools outside containers.
2. `git clone https://github.com/EchoWellApp/echowell.git && cd echowell`
3. `cp .env.development.example .env` (values in TRD 21 §4.6). Do not edit `JWT_SECRET` for local use unless sharing the stack on a network.
4. `docker compose up --build -d`
5. Wait until `docker compose ps` shows `db` healthy and `curl -s http://localhost:8000/api/v1/health` returns `"status":"ok"`.
6. `docker compose exec backend python -m backend.cli seed test_v0_1`, then `docker compose exec backend python database/seeds/load_evaluation_ground_truth.py tests/fixtures/answer_key/evaluation_ground_truth_v0_1.csv` (Analytics alarm timing check; test_v0_1 only).
7. The seed has created `admin@example.com`, `clinician@example.com` and `researcher@example.com` with the local values of SEED_ADMIN_PASSWORD, SEED_CLINICIAN_PASSWORD and SEED_RESEARCHER_PASSWORD from `.env` (TRD 21; never printed, TRD 06 DB-057).
8. Open `http://localhost:3000`, sign in as `admin@example.com`, confirm tiles 2 / 7 / 1 / 19.
9. Reset: `docker compose down -v` deletes the `pgdata` volume; repeat from step 4.

Database login roles (local and CI): `database/roles/provision_login_roles.sql` runs as the PostgreSQL superuser right after the
server starts (Compose: `/docker-entrypoint-initdb.d`; CI: TRD 16). It first runs `CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS btree_gist;` and sets the current database's `timezone` to `UTC` (`ALTER DATABASE … SET timezone = 'UTC'`, TRD 20 PGS-001; extensions are created only by provisioning, never by Alembic; TRD 20 §4.2,
TRD 24 D-72), then idempotently creates the group roles `echowell_migrator`,
`echowell_app`, `echowell_readonly` (NOLOGIN), makes `echowell_migrator` owner of schema `public`, and creates the login roles
`echowell_migrator_login`, `echowell_app_login`, `echowell_readonly_login` (TRD 20 §4.3) with passwords read via psql `\getenv` from
`ECHOWELL_MIGRATOR_DB_PASSWORD`, `ECHOWELL_APP_DB_PASSWORD`, `ECHOWELL_READONLY_DB_PASSWORD` (local/CI only, TRD 21). Staging,
production and AWS create the login roles through the provider console with generated secrets; the script is never run there.
The backend then connects as `echowell_app_login` (DATABASE_URL), Alembic as `echowell_migrator_login` (DATABASE_MIGRATION_URL) and
`analytics_summary.py` as `echowell_readonly_login` (DATABASE_READONLY_URL).


The local Compose command runs uvicorn without `--proxy-headers`, so the client IP is the socket peer (TRD 05 API-103); the image default command and the Railway start command add `--proxy-headers --forwarded-allow-ips="*"` (TRD 15 DEP-022, DEP-040).
