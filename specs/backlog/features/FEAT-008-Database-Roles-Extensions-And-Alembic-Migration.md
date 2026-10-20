# FEAT-008 Database roles, extensions and Alembic migration framework

| Field | Value |
|---|---|
| Epic | Database |
| Build phase | Phase 4 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-006, FEAT-003 |
| Status | Not Started |

## Purpose

Establish the database foundation every table feature relies on: the provisioning script that creates the extensions, UTC timezone, three group roles and three login roles (local and CI), the Alembic environment that always migrates as `echowell_migrator`, the 15 enum types, the trigger functions `reject_mutation()` and `set_updated_at()`, the naming conventions that make `alembic check` clean, the migration file naming rule, and the script that regenerates `database/schema.sql`. Least privilege (D-49) and the append-only raw store (BR-02) depend on this groundwork.

## Business Context

- BR-02: raw records and audit logs are append-only; the `reject_mutation()` trigger function is the database-level guarantee (PGS-018, PGS-019).
- BR-16: least-privilege roles (`echowell_migrator`, `echowell_app`, `echowell_readonly`), no PII columns (DB-035), TLS connections (PGS-027).
- BR-17: PostgreSQL 16 with Alembic migrations as the only schema-change mechanism (DB-026, NFR-086).

## Referenced TRDs

- TRD 20 PGS-001..PGS-005, PGS-007, PGS-008, PGS-010, PGS-016..PGS-023, PGS-040; §4.2 extensions; §4.3 roles; §4.4 enumerated types; §4.5 trigger functions; §4.9 naming conventions; §8 implementation notes; AC-PGS-11, AC-PGS-13.
- TRD 06 DB-012, DB-026..DB-035.
- TRD 12 SEC-110, SEC-111, SEC-115, SEC-116.
- TRD 15 DEP-024, DEP-064; §4.2 provisioning paragraph.
- TRD 13 TST-040, TST-041.
- TRD 23 DME-003, §4.6 (model package layout).
- TRD 24 D-49, D-58, D-72.
- TRD 01 ARC-102 (timestamps stored as `timestamptz` in UTC).

## Scope

- `database/roles/provision_login_roles.sql` (created in Phase 3 by FEAT-006 with this content, TRD 24 D-90; this feature verifies it with the grant tests; run as superuser, local and CI only): `CREATE EXTENSION IF NOT EXISTS pgcrypto; CREATE EXTENSION IF NOT EXISTS btree_gist;`, `ALTER DATABASE <current> SET timezone = 'UTC'`, idempotent creation of NOLOGIN group roles `echowell_migrator`, `echowell_app`, `echowell_readonly`, ownership of schema `public` by `echowell_migrator`, and login roles `echowell_migrator_login`, `echowell_app_login`, `echowell_readonly_login` with passwords read through psql `\getenv` from `ECHOWELL_MIGRATOR_DB_PASSWORD`, `ECHOWELL_APP_DB_PASSWORD`, `ECHOWELL_READONLY_DB_PASSWORD`.
- `alembic.ini` at the repository root with `script_location = backend/alembic` (created in Phase 3 by FEAT-006, D-90; kept unchanged).
- `backend/alembic/env.py`: connects with `DATABASE_MIGRATION_URL`, executes `SET ROLE echowell_migrator`, `SET lock_timeout = '5s'`, `SET statement_timeout = '120s'`, takes advisory lock `0x45434857` for the upgrade, uses the models' `MetaData` as target.
- Migration `backend/alembic/versions/0001_initial_schema.py` started here with: the extension-existence check block of TRD 20 §4.2, the 15 enum types of §4.4, and the functions of §4.5. The table, index, trigger and grant sections of 0001 are added by FEAT-009..FEAT-013 in the same Phase 4 batch.
- `backend/models/__init__.py`: the SQLAlchemy 2.0 declarative `Base` with a `MetaData(naming_convention=...)` matching §4.9, `postgresql.ENUM(..., create_type=False)` definitions for the 15 enums, and the `str`-valued Python `enum.Enum` classes mirroring them (TRD 23 §4.6, DME-003); model modules are imported here as they are added.
- `scripts/dump_schema.sh` regenerating `database/schema.sql` (`pg_dump --schema-only --no-owner --no-comments` of a freshly migrated database, preamble removed).
- Schema reference test `tests/integration/test_schema_reference.py` (PGS-016) and the first role and extension tests.
- CI wiring in `ci.yml` `backend-test`: run the provisioning script as the service superuser, then `alembic upgrade head`, `alembic downgrade base && alembic upgrade head` before pytest (TRD 16 CIC-015 steps, completing FEAT-007).

## Out of Scope

- Every table, its columns, constraints, indexes, triggers and grants (FEAT-009, FEAT-010, FEAT-011, FEAT-012, FEAT-013).
- Migration `0002_seed_config_parameters` (FEAT-009).
- Runtime engine, pool and advisory-lock helper for the app (FEAT-013).
- Provisioning on Neon, Railway PostgreSQL or AWS RDS (performed through the provider console by the DevOps owner; documented by FEAT-081 and FEAT-092); the script here is never run there.
- The `reset-test-db` and `purge-resident` commands that use the purge escape hatch (FEAT-017).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-008-FR-01 | The provisioning step shall create extensions `pgcrypto` and `btree_gist` (and no other) and set the database `timezone` to `UTC`; no Alembic migration creates or drops an extension or sets a database parameter. | PGS-001, PGS-002, D-72 |
| FEAT-008-FR-02 | Migration 0001 shall only check that both extensions exist and raise the §4.2 message otherwise; no downgrade drops them. | PGS-002, D-72, DB-029 |
| FEAT-008-FR-03 | Exactly three NOLOGIN group roles `echowell_migrator`, `echowell_app`, `echowell_readonly` shall exist, plus login roles `echowell_migrator_login`, `echowell_app_login`, `echowell_readonly_login`, each a member of only its group role; `echowell_app_login` has no membership in `echowell_readonly`. | PGS-004, PGS-040, SEC-110, ARC-019, D-49 |
| FEAT-008-FR-04 | All EchoWell objects shall live in schema `public` and be owned by `echowell_migrator`; `env.py` and every migrator command issue `SET ROLE echowell_migrator` right after connecting. | PGS-003, TRD 20 §4.3 |
| FEAT-008-FR-05 | `alembic.ini` shall be at the repository root with `script_location = backend/alembic`. | DEP-024 |
| FEAT-008-FR-06 | Alembic `env.py` shall connect only through `DATABASE_MIGRATION_URL` and set `lock_timeout = '5s'` and `statement_timeout = '120s'`. | DB-028, SEC-111, D-58 |
| FEAT-008-FR-07 | Alembic upgrade shall hold PostgreSQL advisory lock key `0x45434857` so concurrent starts cannot apply migrations twice. | DEP-064 |
| FEAT-008-FR-08 | Migration files shall be named `NNNN_<snake_case_summary>.py` with four-digit sequential revision ids and exactly one head. | DB-027 |
| FEAT-008-FR-09 | Alembic migrations shall be the only schema-change mechanism; `database/schema.sql` is generated by `scripts/dump_schema.sh` in the same PR as any migration and never edited by hand. | DB-026, PGS-016, PGS-017 |
| FEAT-008-FR-10 | The 15 enum types of §4.4 shall be created with the exact labels in the listed order; label additions use `ALTER TYPE … ADD VALUE` in their own migration and labels are never renamed or removed. | PGS-005, DB-034 |
| FEAT-008-FR-11 | `set_updated_at()` and `reject_mutation()` shall be created exactly as §4.5; `reject_mutation()` raises SQLSTATE `EW001` and permits DELETE/TRUNCATE only for `current_user = 'echowell_migrator'` with `echowell.allow_purge = 'on'`, never UPDATE. | PGS-018, PGS-019, PGS-020 |
| FEAT-008-FR-12 | Constraint, index, trigger and enum names shall follow §4.9 and be declared explicitly in SQLAlchemy (`name=`) so `alembic check` reports no diff. | PGS-023, DB-012 |
| FEAT-008-FR-13 | Every primary key shall follow PGS-007, every instant column shall be `timestamptz`, local days `date`, local clock time `time(0)`; every FK `ON DELETE RESTRICT` except `scores.processed_session_id` CASCADE (rules enforced in the shared model base and checked by tests as tables are added). | PGS-007, PGS-008, PGS-010, DB-033 |
| FEAT-008-FR-14 | Every migration that creates a table shall issue that table's grants in the same migration; `ALTER DEFAULT PRIVILEGES` shall not be used. | PGS-021, PGS-022 |
| FEAT-008-FR-15 | Database constraints duplicate (not replace) application validation; staging and production migrations are forward-only with downgrades implemented for local/test; no migration UPDATEs or DELETEs `raw_sessions` or `audit_logs`. | DB-029, DB-030, DB-032 |
| FEAT-008-FR-16 | The schema shall contain no column for names, birth dates, contact details, addresses or audio. | DB-035 |
| FEAT-008-FR-17 | Owner/superuser credentials are never used by applications; `DATABASE_READONLY_URL` is referenced only by `backend/services/analytics_summary.py`, and the only `SET ROLE` in the codebase is to `echowell_migrator` in Alembic and the migrator commands. | SEC-115, SEC-116, PGS-040 |
| FEAT-008-FR-18 | Every timestamp column created by the migrations shall be `timestamptz` holding UTC; local-time conversion uses the IANA zone of `facilities.timezone` through Python `zoneinfo`. | ARC-102 |

## Inputs

- PostgreSQL 16 server (Compose `db`, CI service container, testcontainers).
- Environment: `DATABASE_MIGRATION_URL`, `ECHOWELL_*_DB_PASSWORD` (local/CI only).
- TRD 20 SQL blocks of §4.2–§4.5.

## Outputs

- Provisioned database (extensions, timezone, roles), `alembic_version` table, 15 enum types, 2 trigger functions.
- Files: `database/roles/provision_login_roles.sql`, `alembic.ini`, `backend/alembic/env.py`, `backend/alembic/script.py.mako`, `backend/alembic/versions/0001_initial_schema.py` (partial), `backend/models/__init__.py`, `scripts/dump_schema.sh`, `database/schema.sql`.

## Data Flow

Superuser runs `provision_login_roles.sql` on server start (Compose init directory or CI step) → `alembic upgrade head` from the repository root reads `alembic.ini` → `env.py` connects with `DATABASE_MIGRATION_URL`, `SET ROLE echowell_migrator`, sets timeouts, takes the advisory lock → 0001 checks extensions, creates enums and functions (tables follow in FEAT-009..FEAT-013) → `scripts/dump_schema.sh` dumps the migrated schema into `database/schema.sql` → the schema reference test compares a fresh migration with that file.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-006, FEAT-003

- FEAT-006 provides the Compose `db` service that mounts the provisioning script and the backend command that runs `alembic upgrade head`.
- FEAT-003 provides `Settings` with `DATABASE_MIGRATION_URL` and the `postgresql+psycopg://` normalisation used by `env.py`.

Features that build directly on this one: FEAT-009 (first tables), and transitively every Database feature.

## Database Impact

- Created: extensions `pgcrypto`, `btree_gist` (provisioning only); roles `echowell_migrator`, `echowell_app`, `echowell_readonly` and their login roles (provisioning only); enum types `resident_cohort`, `resident_status`, `ingest_source`, `session_status`, `day_status`, `alarm_state`, `alert_status`, `note_type`, `pipeline_trigger`, `pipeline_run_status`, `user_role`, `actor_type`, `review_outcome`, `data_alert_kind`, `data_alert_status`; functions `set_updated_at()`, `reject_mutation()`; table `alembic_version` (Alembic).
- Tables used or modified: none of the 24 TRD 20 §4.6 tables yet.

## API Impact

None.

## Frontend Impact

None.

## Analytics Impact

None.

## Security Requirements

- Least privilege per D-49: the app never connects as the migrator (AGT-060); migrator credentials are used only by Alembic and the closed list of TRD 20 §4.3 (SEC-111).
- Login-role passwords for local/CI come from environment variables with `local-dev-only-*` / `ci-only-*` values; staging and production roles are created in the provider console with generated secrets (TRD 15 §4.2).
- Owner credentials held only by the DevOps lead and the PI's deputy (SEC-115).

## Error Handling

| Failure | Behaviour | Trace |
|---|---|---|
| Extensions missing when 0001 runs | Migration fails with the §4.2 message naming the provisioning step | PGS-002 |
| Concurrent `alembic upgrade` | Second process waits on advisory lock `0x45434857` | DEP-064 |
| Long lock wait or statement | Fails after `lock_timeout` 5 s / `statement_timeout` 120 s; deploy aborts before traffic switches | DB-028 |
| Mutation of an append-only table (once triggers exist) | `EW001` raised by `reject_mutation()` | PGS-018 |

## Logging Requirements

- Alembic writes its standard revision log lines to stdout during deploy; no application log or audit row is produced by migrations.
- The provisioning script prints no passwords (values come through `\getenv`).

## Testing Requirements

- Integration (`tests/integration/db/test_migrations.py`, marker `integration`): TST-040 (upgrade head as migrator on a provisioned empty database; downgrade base then upgrade head).
- Integration (`tests/integration/db/test_roles.py`): role existence and memberships (PGS-004), `echowell_app_login` cannot `SET ROLE echowell_readonly` (PGS-040 part of AC-PGS-14), `pg_extension` lists exactly `plpgsql`, `pgcrypto`, `btree_gist` (PGS-002), `SHOW timezone` = UTC and server version 16 (PGS-001).
- Integration: enum labels and order from `pg_enum` (PGS-005); 0001 on a database without the extensions fails with the 0001 message (PGS-002).
- Schema reference test `tests/integration/test_schema_reference.py` (PGS-016) and `alembic check` (PGS-023, AC-PGS-11); `alembic heads` returns one revision (DB-027, AC-DB-07).
- Unit: `env.py` issues the `SET ROLE` and timeout statements (DB-028 "env.py unit test").
- TST-041 grant assertions are extended by FEAT-010 and FEAT-012 as the tables appear.

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-008-AC-01 | On an empty PostgreSQL 16 database provisioned by the script, `alembic upgrade head && alembic downgrade base && alembic upgrade head` run from the repository root succeed. | TST-040, DEP-024, TRD 25 §4.6 Phase 4 Commands |
| FEAT-008-AC-02 | `SELECT extname FROM pg_extension ORDER BY 1` returns exactly `btree_gist`, `pgcrypto`, `plpgsql`; `SHOW timezone` returns `UTC`; `SHOW server_version_num` is ≥ 160000 and < 170000. | PGS-001, PGS-002 |
| FEAT-008-AC-03 | Running 0001 on a database without `btree_gist` fails with an exception whose message contains "EchoWell needs extensions pgcrypto and btree_gist". | PGS-002 |
| FEAT-008-AC-04 | `pg_roles` contains the three NOLOGIN group roles and three login roles; `pg_auth_members` shows each login role in only its own group; `SET ROLE echowell_readonly` as `echowell_app_login` fails with SQLSTATE 42501. | PGS-004, PGS-040 |
| FEAT-008-AC-05 | Querying `pg_enum` ordered by `enumsortorder` returns exactly the 15 types and labels of TRD 20 §4.4. | PGS-005 |
| FEAT-008-AC-06 | `alembic heads` prints one revision and `alembic check` exits 0. | DB-027, PGS-023, AC-PGS-11 |
| FEAT-008-AC-07 | `scripts/dump_schema.sh` regenerates `database/schema.sql` and the schema reference test passes against a freshly migrated database. | PGS-016, PGS-017 |
| FEAT-008-AC-08 | `grep -rn "CREATE EXTENSION\|DROP EXTENSION\|ALTER DATABASE" backend/alembic` returns nothing, and `grep -rn "SET ROLE" backend analytics` returns only `echowell_migrator` usages. | D-72, SEC-116 |

## Definition of Done

- All FEAT-008 acceptance criteria pass locally and in `backend-test`.
- `ci.yml` `backend-test` runs the provisioning script, the migration round-trip and then pytest as `echowell_app_login` (CIC-015 steps).
- `database/schema.sql` regenerated in the same PR; batch report lists IDs and command results (AGT-022); delivered in the single Phase 4 PR with FEAT-009..FEAT-017.

## Implementation Notes

- Copy the SQL of TRD 20 §4.2–§4.5 into `op.execute()` calls verbatim (TRD 20 §8); do not let autogenerate create enum types (`create_type=False`).
- 0001 is a single initial migration assembled across FEAT-008..FEAT-013 in Phase 4 (TRD 20 §8 migration layout); the downgrade drops only EchoWell objects in reverse order.
- Alembic must use the direct (non-pooled) Neon host; transaction-scoped advisory locks for the app work over the pooled host (TRD 20 §8).
- Map `double precision` columns to `sqlalchemy.Double` in models, never `Numeric` (TRD 20 §8).
- TRD 12 SEC-110 now states the provisioning step (TRD 20 §4.3, D-72) as the only way roles are created; migrations only grant privileges (aligned in the PR #2 consistency fixes).
