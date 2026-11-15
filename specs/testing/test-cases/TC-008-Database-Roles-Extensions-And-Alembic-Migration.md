# FEAT-008 Database roles, extensions and Alembic migration foundation

## Feature Description

FEAT-008 lays the database foundation: the provisioning script `database/roles/provision_login_roles.sql` (extensions `pgcrypto` and `btree_gist` only, database `timezone` = `UTC`, NOLOGIN group roles `echowell_migrator`, `echowell_app`, `echowell_readonly`, and login roles `echowell_migrator_login`, `echowell_app_login`, `echowell_readonly_login` each in only its own group), the Alembic environment (`alembic.ini` at the root with `script_location = backend/alembic`, connection through `DATABASE_MIGRATION_URL`, `SET ROLE echowell_migrator`, `lock_timeout = '5s'`, `statement_timeout = '120s'`, advisory lock `0x45434857`), migration 0001 that only checks the extensions, the 15 enum types of TRD 20 §4.4, the trigger functions `set_updated_at()` and `reject_mutation()` (SQLSTATE `EW001`), the naming conventions that keep `alembic check` clean, the migration file naming rule and `scripts/dump_schema.sh`.

## Preconditions

- Local Docker Compose stack running (`cp .env.development.example .env && docker compose up --build -d`); commands from the repository root.
- Connection shorthands (all inside the `db` container, which already holds the `ECHOWELL_*_DB_PASSWORD` variables, so no password is typed):
  - `SU` = `docker compose exec db psql -U echowell -d <db> -v VERBOSITY=verbose -v ON_ERROR_ROLLBACK=on` (superuser of the Compose image).
  - `APP` = `docker compose exec db sh -c 'PGPASSWORD=$ECHOWELL_APP_DB_PASSWORD psql -h 127.0.0.1 -U echowell_app_login -d <db> -v VERBOSITY=verbose -v ON_ERROR_ROLLBACK=on'`.
  - `RO` and `MIG` = the same with `ECHOWELL_READONLY_DB_PASSWORD` / `echowell_readonly_login` and `ECHOWELL_MIGRATOR_DB_PASSWORD` / `echowell_migrator_login`.
  - `<db>` is `echowell` unless the case uses a throwaway database.
- Throwaway database helper (empty, provisioned): `docker compose exec db createdb -U echowell <name>` then `docker compose exec db psql -U echowell -d <name> -v ON_ERROR_STOP=1 -f /docker-entrypoint-initdb.d/10_provision_login_roles.sql`.
- Alembic against a throwaway database, from the backend container (the migrator URL of the Compose file with only the database name changed): `docker compose exec backend sh -c 'DATABASE_MIGRATION_URL=${DATABASE_MIGRATION_URL%/echowell}/<name> alembic <command>'`.
- With `VERBOSITY=verbose`, psql prints the SQLSTATE right after `ERROR:` (for example `ERROR:  42501: permission denied …`).
- For TC-008-07 a host `pg_dump` 16 client and Python venv with dev requirements.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-008-01 | `alembic upgrade head`, `downgrade base`, `upgrade head` succeed on an empty provisioned database | High | Database |
| TC-008-02 | Extensions are exactly `btree_gist`, `pgcrypto`, `plpgsql`; timezone `UTC`; server 16 | High | Database |
| TC-008-03 | Migration 0001 fails with the §4.2 message when `btree_gist` is missing | High | Negative |
| TC-008-04 | Three NOLOGIN group roles and three login roles with single memberships; `SET ROLE echowell_readonly` as app fails 42501 | High | Security |
| TC-008-05 | `pg_enum` holds exactly the 15 types and labels of TRD 20 §4.4 in order | High | Database |
| TC-008-06 | `alembic heads` prints one revision; `alembic check` exits 0 | High | Positive |
| TC-008-07 | `scripts/dump_schema.sh` regenerates `database/schema.sql`; schema reference test passes | High | Positive |
| TC-008-08 | No extension or database setting in migrations; `SET ROLE` only to `echowell_migrator` | High | Security |
| TC-008-09 | `reject_mutation()` and `set_updated_at()` exist as TRD 20 §4.5 | Medium | Database |
| TC-008-10 | Alembic sets role and timeouts and serialises concurrent upgrades with lock `0x45434857` | Medium | Database |
| TC-008-11 | All objects owned by `echowell_migrator` in schema `public`; migration file naming | Medium | Database |
| TC-008-12 | Column and key rules: `timestamptz` instants, `ON DELETE RESTRICT` except `scores`, no PII columns | Medium | Database |
| TC-008-13 | Grants issued per migration; no `ALTER DEFAULT PRIVILEGES`; read-only URL used by one module only | Medium | Security |

### TC-008-01 `alembic upgrade head`, `downgrade base`, `upgrade head` succeed on an empty provisioned database

| Step | Action | Expected Result |
|---|---|---|
| 1 | Create and provision throwaway database `echowell_qa` (helper in Preconditions). | `createdb` returns silently; the provisioning script ends without error and prints no password. |
| 2 | Run `alembic upgrade head` against `echowell_qa`; `echo "exit=$?"`. | Log lines `Running upgrade  -> 0001`, `0001 -> 0002`, `0002 -> 0003`, `0003 -> 0004`; `exit=0`. |
| 3 | Run `alembic downgrade base`; `echo "exit=$?"`. | Log lines downgrading `0004 -> 0003` … `0001 -> `; `exit=0`. |
| 4 | `SU` on `echowell_qa`: `SELECT count(*) FROM pg_tables WHERE schemaname='public';` and `SELECT extname FROM pg_extension ORDER BY 1;` | Tables: `1` (only `alembic_version`) or `0`; extensions still `btree_gist`, `pgcrypto`, `plpgsql` (downgrade never drops them). |
| 5 | Run `alembic upgrade head` again; `echo "exit=$?"`. | `exit=0`; `SELECT version_num FROM alembic_version;` returns `0004`. |
| 6 | Run `pytest -q tests/integration/db/test_migrations.py`. | All tests pass (TST-040). |
| 7 | Drop the throwaway database: `docker compose exec db dropdb -U echowell echowell_qa`. | Dropped. |

### TC-008-02 Extensions are exactly `btree_gist`, `pgcrypto`, `plpgsql`; timezone `UTC`; server 16

| Step | Action | Expected Result |
|---|---|---|
| 1 | `APP`: `SELECT extname FROM pg_extension ORDER BY 1;` | Exactly 3 rows: `btree_gist`, `pgcrypto`, `plpgsql`. |
| 2 | `APP`: `SHOW timezone;` | `UTC`. |
| 3 | `APP`: `SHOW server_version_num;` | A value ≥ `160000` and < `170000`. |

### TC-008-03 Migration 0001 fails with the §4.2 message when `btree_gist` is missing

| Step | Action | Expected Result |
|---|---|---|
| 1 | Create and provision throwaway database `echowell_noext`; then `SU` on it: `DROP EXTENSION btree_gist;` | `DROP EXTENSION`. |
| 2 | Run `alembic upgrade head` against `echowell_noext`; `echo "exit=$?"`. | The run fails in revision 0001 with an exception whose message contains `EchoWell needs extensions pgcrypto and btree_gist; run the provisioning step as the database owner or superuser first (TRD 15 §4.2/§4.4, TRD 20 §4.2)`; exit non-zero. |
| 3 | `SU` on `echowell_noext`: `SELECT count(*) FROM pg_type WHERE typname = 'resident_cohort';` | `0` (nothing was created; the migration rolled back). |
| 4 | Drop `echowell_noext`. | Dropped. |

### TC-008-04 Three NOLOGIN group roles and three login roles with single memberships; `SET ROLE echowell_readonly` as app fails 42501

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SU`: `SELECT rolname, rolcanlogin, rolsuper FROM pg_roles WHERE rolname LIKE 'echowell\_%' ORDER BY 1;` | 6 rows: `echowell_app` f f, `echowell_app_login` t f, `echowell_migrator` f f, `echowell_migrator_login` t f, `echowell_readonly` f f, `echowell_readonly_login` t f. |
| 2 | `SU`: `SELECT m.rolname AS member, r.rolname AS role FROM pg_auth_members a JOIN pg_roles r ON r.oid=a.roleid JOIN pg_roles m ON m.oid=a.member WHERE m.rolname LIKE 'echowell\_%' ORDER BY 1;` | Exactly 3 rows: `echowell_app_login` → `echowell_app`, `echowell_migrator_login` → `echowell_migrator`, `echowell_readonly_login` → `echowell_readonly`. |
| 3 | `APP`: `SET ROLE echowell_readonly;` | `ERROR:  42501: permission denied to set role "echowell_readonly"`. |
| 4 | `APP`: `SET ROLE echowell_migrator;` | `ERROR:  42501: permission denied to set role "echowell_migrator"`. |
| 5 | `MIG`: `SET ROLE echowell_migrator; SELECT current_user;` | `SET`; `echowell_migrator`. |
| 6 | Run `pytest -q tests/integration/db/test_roles.py`. | All tests pass. |

### TC-008-05 `pg_enum` holds exactly the 15 types and labels of TRD 20 §4.4 in order

| Step | Action | Expected Result |
|---|---|---|
| 1 | `APP`: `SELECT t.typname, string_agg(e.enumlabel, ',' ORDER BY e.enumsortorder) FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid GROUP BY t.typname ORDER BY t.typname;` | Exactly 15 rows: `actor_type` user,api_key,system; `alarm_state` off,rings,on; `alert_status` open,acknowledged,closed; `data_alert_kind` baseline_stalled,possible_other_speaker,high_set_aside,device_silent,review_flagged_data_problem; `data_alert_status` open,resolved; `day_status` checked_in,missing_resident,missing_device_gap; `ingest_source` api_single,api_batch,csv_upload,seed; `note_type` observation,action_taken,follow_up; `pipeline_run_status` running,succeeded,failed; `pipeline_trigger` ingest,nightly,manual,test; `resident_cohort` longitudinal,new_admission; `resident_status` active,withdrawn; `review_outcome` no_concern,known_cause,referred,data_problem; `session_status` usable,set_aside,quarantined,duplicate; `user_role` admin,clinician,researcher. |
| 2 | Run `pytest -q tests/integration/db/test_enums.py`. | All tests pass. |

### TC-008-06 `alembic heads` prints one revision; `alembic check` exits 0

| Step | Action | Expected Result |
|---|---|---|
| 1 | `docker compose exec backend alembic heads`. | Exactly one line: `0004 (head)`. |
| 2 | `docker compose exec backend alembic check; echo "exit=$?"`. | `No new upgrade operations detected.`; `exit=0`. |

### TC-008-07 `scripts/dump_schema.sh` regenerates `database/schema.sql`; schema reference test passes

| Step | Action | Expected Result |
|---|---|---|
| 1 | Export `DATABASE_MIGRATION_URL` for host access (`postgresql://echowell_migrator_login:<ECHOWELL_MIGRATOR_DB_PASSWORD from the Compose file>@127.0.0.1:5432/echowell`) and run `scripts/dump_schema.sh`. | Prints `wrote …/database/schema.sql`; exit 0. |
| 2 | Run `git diff --stat database/schema.sql`. | No difference: the committed file equals the regenerated one. |
| 3 | Run `pytest -q tests/integration/test_schema_reference.py`. | Passes against a freshly migrated database. |
| 4 | Run `head -5 database/schema.sql`. | Generated `pg_dump` output (no hand-written header claiming manual edits). |

### TC-008-08 No extension or database setting in migrations; `SET ROLE` only to `echowell_migrator`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `grep -rn --include=*.py "CREATE EXTENSION\|DROP EXTENSION\|ALTER DATABASE" backend/alembic; echo "exit=$?"`. | `exit=1` (the extension names appear only inside the 0001 check query and its message). |
| 2 | Run `grep -rn --include=*.py "SET ROLE" backend analytics`. | Statements only `SET ROLE echowell_migrator` (`backend/core/db.py`) plus docstrings/comments that mention it (`backend/alembic/env.py`, `backend/cli.py`, `backend/services/analytics_summary.py` "no `SET ROLE`"); no `SET ROLE` to any other role. |
| 3 | Run `grep -c "CREATE EXTENSION IF NOT EXISTS" database/roles/provision_login_roles.sql`. | `2` (pgcrypto, btree_gist) — extensions are created only by provisioning. |

### TC-008-09 `reject_mutation()` and `set_updated_at()` exist as TRD 20 §4.5

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SU`: `SELECT proname, pg_get_userbyid(proowner) FROM pg_proc WHERE proname IN ('reject_mutation','set_updated_at') ORDER BY 1;` | 2 rows, both owned by `echowell_migrator`. |
| 2 | `SU`: `SELECT prosrc FROM pg_proc WHERE proname='reject_mutation';` | Body checks `current_user = 'echowell_migrator'`, `coalesce(current_setting('echowell.allow_purge', true), 'off') = 'on'` and `TG_OP IN ('DELETE', 'TRUNCATE')`; otherwise raises `'table % is append-only: % is not allowed'` with `ERRCODE = 'EW001'`. UPDATE is never allowed. |
| 3 | `SU`: `SELECT prosrc FROM pg_proc WHERE proname='set_updated_at';` | Body sets `NEW.updated_at := now()` and returns `NEW`. |

Behaviour of the triggers that use these functions is tested in TC-010-01/02, TC-012-01/02 and TC-009-10.

### TC-008-10 Alembic sets role and timeouts and serialises concurrent upgrades with lock `0x45434857`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `grep -n "SET ROLE echowell_migrator\|lock_timeout\|statement_timeout\|0x45434857\|MIGRATION_LOCK_KEY" backend/core/db.py backend/alembic/env.py`. | `MIGRATOR_SETUP` contains `SET ROLE echowell_migrator`, `SET lock_timeout = '5s'`, `SET statement_timeout = '120s'`; `MIGRATION_LOCK_KEY = 0x45434857`; `env.py` executes `SELECT pg_advisory_xact_lock(:key)` before `run_migrations()`. |
| 2 | Create and provision `echowell_qa2`; start two upgrades at once: `for i in 1 2; do docker compose exec -T backend sh -c 'DATABASE_MIGRATION_URL=${DATABASE_MIGRATION_URL%/echowell}/echowell_qa2 alembic upgrade head' & done; wait`. | Both commands exit 0; one applies 0001–0004, the other waits on the lock and then finds nothing to do. |
| 3 | `SU` on `echowell_qa2`: `SELECT count(*), max(version_num) FROM alembic_version;` | `1`, `0004` (no migration applied twice). Drop `echowell_qa2` afterwards. |
| 4 | Run `pytest -q tests/unit/backend/core/test_db.py`. | Passes (env.py unit test of the `SET ROLE` and timeout statements, DB-028). |

### TC-008-11 All objects owned by `echowell_migrator` in schema `public`; migration file naming

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SU`: `SELECT tableowner, count(*) FROM pg_tables WHERE schemaname = 'public' GROUP BY 1;` | One row: `echowell_migrator`, `25` (24 tables + `alembic_version`). |
| 2 | `SU`: `SELECT DISTINCT pg_get_userbyid(typowner) FROM pg_type t JOIN pg_enum e ON e.enumtypid = t.oid;` | `echowell_migrator`. |
| 3 | `SU`: `SELECT nspname FROM pg_namespace WHERE nspowner = 'echowell_migrator'::regrole;` | `public`. |
| 4 | Run `ls backend/alembic/versions/*.py \| xargs -n1 basename`. | `0001_initial_schema.py`, `0002_seed_config_parameters.py`, `0003_ingest_batch_pipeline_run.py`, `0004_schema_check_grant_data_alert_days.py`: four-digit sequential prefix, snake_case summary. |
| 5 | Run `grep -n "script_location" alembic.ini`. | `script_location = backend/alembic`; `alembic.ini` is at the repository root. |

### TC-008-12 Column and key rules: `timestamptz` instants, `ON DELETE RESTRICT` except `scores`, no PII columns

| Step | Action | Expected Result |
|---|---|---|
| 1 | `APP`: `SELECT table_name, column_name FROM information_schema.columns WHERE table_schema='public' AND data_type = 'timestamp without time zone';` | 0 rows (every instant column is `timestamptz`). |
| 2 | `SU`: `SELECT conname, confdeltype FROM pg_constraint WHERE contype='f' AND connamespace='public'::regnamespace AND confdeltype <> 'r';` | Exactly one row: `scores_processed_session_id_fkey`, `c` (all other FKs RESTRICT). |
| 3 | `APP`: `SELECT table_name, column_name FROM information_schema.columns WHERE table_schema='public' AND column_name ~ '(birth\|phone\|address\|audio\|first_name\|last_name)';` | Only `raw_sessions.audio_quality_flag` (no name, birth date, contact, address or audio column). |
| 4 | `APP`: `SELECT column_name, data_type FROM information_schema.columns WHERE table_name='processed_sessions' AND column_name IN ('local_date','local_time');` | `local_date` = `date`; `local_time` = `time without time zone` (time(0)). |

### TC-008-13 Grants issued per migration; no `ALTER DEFAULT PRIVILEGES`; read-only URL used by one module only

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `grep -rn --include=*.py "ALTER DEFAULT PRIVILEGES" backend; echo "exit=$?"`. | `exit=1`. |
| 2 | `SU`: `SELECT count(*) FROM pg_default_acl;` | `0`. |
| 3 | Run `grep -rln --include=*.py "database_readonly_url\|DATABASE_READONLY_URL" backend analytics`. | `backend/core/config.py` (definition), `backend/services/analytics_summary.py` (only user) and the docstring of `backend/models/evaluation.py`; no other module. |
| 4 | Run `grep -rn "GRANT" backend/alembic/versions/0001_initial_schema.py \| head -5`. | Grants for the tables are issued in the same migration that creates them. |

## API Validation

Not applicable: FEAT-008 exposes no endpoint; it provides database objects only.

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT extname FROM pg_extension ORDER BY 1;` | `btree_gist`, `pgcrypto`, `plpgsql` |
| 2 | `SHOW timezone;` / `SHOW server_version_num;` | `UTC` / 160000–169999 |
| 3 | Roles and memberships (TC-008-04) | 3 group + 3 login roles, single memberships |
| 4 | `pg_enum` (TC-008-05) | 15 types, labels in TRD order |
| 5 | `SELECT version_num FROM alembic_version;` | `0004` |
| 6 | Ownership (TC-008-11) | All objects owned by `echowell_migrator` |
| 7 | `pg_constraint` FK delete rules (TC-008-12) | Only `scores_processed_session_id_fkey` cascades |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run 0001 without `btree_gist` (TC-008-03) | Fails with "EchoWell needs extensions pgcrypto and btree_gist…" |
| 2 | `SET ROLE echowell_readonly` as `echowell_app_login` (TC-008-04) | SQLSTATE 42501 |
| 3 | `SET ROLE echowell_migrator` as `echowell_app_login` (TC-008-04) | SQLSTATE 42501 |
| 4 | Two concurrent upgrades (TC-008-10) | No double application; one `alembic_version` row |
| 5 | UPDATE on an append-only table (see TC-010-01) | SQLSTATE `EW001` from `reject_mutation()` |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-008-AC-01 | On an empty provisioned PostgreSQL 16 database, `alembic upgrade head && alembic downgrade base && alembic upgrade head` succeed. | TC-008-01 |
| FEAT-008-AC-02 | Extensions exactly `btree_gist`, `pgcrypto`, `plpgsql`; `SHOW timezone` = `UTC`; `server_version_num` in [160000, 170000). | TC-008-02 |
| FEAT-008-AC-03 | 0001 without `btree_gist` fails with "EchoWell needs extensions pgcrypto and btree_gist". | TC-008-03 |
| FEAT-008-AC-04 | 3 NOLOGIN group + 3 login roles; each login role only in its group; `SET ROLE echowell_readonly` as app → 42501. | TC-008-04 |
| FEAT-008-AC-05 | `pg_enum` returns exactly the 15 types and labels of TRD 20 §4.4. | TC-008-05 |
| FEAT-008-AC-06 | `alembic heads` prints one revision; `alembic check` exits 0. | TC-008-06 |
| FEAT-008-AC-07 | `scripts/dump_schema.sh` regenerates `database/schema.sql`; schema reference test passes. | TC-008-07 |
| FEAT-008-AC-08 | No `CREATE EXTENSION`/`DROP EXTENSION`/`ALTER DATABASE` in `backend/alembic`; `SET ROLE` only `echowell_migrator`. | TC-008-08 |

## Test Data Requirements

- Compose database `echowell` (migrated; seed not required for this feature) and throwaway databases `echowell_qa`, `echowell_qa2`, `echowell_noext` created and dropped by the cases.
- Login-role passwords come from the `ECHOWELL_*_DB_PASSWORD` variables already present in the `db` container; never typed into a test record.
- No resident data and no audio.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-008-FR-01 (PGS-001, PGS-002, D-72) | FEAT-008 | TC-008-02, TC-008-08 |
| FEAT-008-FR-02 (PGS-002, DB-029) | FEAT-008 | TC-008-01, TC-008-03 |
| FEAT-008-FR-03 (PGS-004, PGS-040, SEC-110, ARC-019, D-49) | FEAT-008 | TC-008-04 |
| FEAT-008-FR-04 (PGS-003) | FEAT-008 | TC-008-11, TC-008-10 |
| FEAT-008-FR-05 (DEP-024) | FEAT-008 | TC-008-11 |
| FEAT-008-FR-06 (DB-028, SEC-111, D-58) | FEAT-008 | TC-008-10 |
| FEAT-008-FR-07 (DEP-064) | FEAT-008 | TC-008-10 |
| FEAT-008-FR-08 (DB-027) | FEAT-008 | TC-008-06, TC-008-11 |
| FEAT-008-FR-09 (DB-026, PGS-016, PGS-017) | FEAT-008 | TC-008-07 |
| FEAT-008-FR-10 (PGS-005, DB-034) | FEAT-008 | TC-008-05 |
| FEAT-008-FR-11 (PGS-018, PGS-019, PGS-020) | FEAT-008 | TC-008-09 |
| FEAT-008-FR-12 (PGS-023, DB-012) | FEAT-008 | TC-008-06 |
| FEAT-008-FR-13 (PGS-007, PGS-008, PGS-010, DB-033) | FEAT-008 | TC-008-12 |
| FEAT-008-FR-14 (PGS-021, PGS-022) | FEAT-008 | TC-008-13 |
| FEAT-008-FR-15 (DB-029, DB-030, DB-032) | FEAT-008 | TC-008-01, TC-008-08 |
| FEAT-008-FR-16 (DB-035) | FEAT-008 | TC-008-12 |
| FEAT-008-FR-17 (SEC-115, SEC-116, PGS-040) | FEAT-008 | TC-008-08, TC-008-13 |
| FEAT-008-FR-18 (ARC-102) | FEAT-008 | TC-008-12 |
| TST-040 | FEAT-008 | TC-008-01 |
| AC-PGS-11, AC-DB-07 | FEAT-008 | TC-008-06 |
| AC-PGS-14 (SET ROLE part) | FEAT-008 | TC-008-04 |
