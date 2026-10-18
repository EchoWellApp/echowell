# 20 PostgreSQL Schema Definition

Document ID: ECHOWELL-TRD-20 · Version 0.1 (draft for review) · Date: 18 October 2026 · Owner: Team 2 · Status: Draft

## 1. Purpose

This document is the complete, executable PostgreSQL 16 definition of the EchoWell database: extensions, roles,
enumerated types, tables, columns, keys, foreign keys with delete behaviour, CHECK constraints, indexes, triggers,
grants and the configuration seed for both pipeline profiles. The SQL in section 4 was executed end to end against
PostgreSQL 16.15 and the behaviour checks in section 7 passed before publication.

The design rationale (layering, rebuild, backups, retention) lives in TRD 06. The logical meaning of every entity and
column, state machines and the source-to-column mapping live in TRD 23. All three documents use the same table names,
column names and types; where this document and an Alembic migration disagree, the migration is wrong and the schema
diff test (PGS-016) fails.

## 2. Scope

In scope:
- DDL for all 24 tables (the 21 of contract section 9 plus `alert_reviews`, `data_alerts` and `evaluation_ground_truth`
  of contract sections 19/20, with the column additions listed in section 4.10), 15 enumerated types, 2 extensions,
  2 trigger functions, 17 triggers, 4 group roles and their grants.
- Seed SQL for `config_parameters` (profiles `production` and `test_v0_1`).
- Seed SQL for the synthetic test roster (facility "Edgewood", residents R01–R10, devices, assignments) and the
  test-only evaluation answer key.
- Rules that keep the Alembic migrations, `database/schema.sql` and SQLAlchemy models equivalent to this DDL.

Out of scope:
- Why the schema is shaped this way, rebuild and backup procedures (TRD 06).
- Field semantics and state machines (TRD 23).
- How the pipeline computes the values (TRD 07, TRD 08, TRD 09) and how records are validated before insert (TRD 10).
- Login role passwords and connection strings (TRD 21), hosting plans (TRD 22).

## 3. References

| ID | Reference |
|---|---|
| SRC-01 | Deployment Architecture (PostgreSQL on Neon preferred or Railway; AWS RDS target) |
| SRC-02 | Daily Data Storage and Processing Flowcharts ("Only the raw store receives data from Team 1. Every other table can be rebuilt from it, and the answer key never touches the analytics.") |
| SRC-03 | Pipeline test workbook v0.1 (Parameters, Data_dictionary, Annotated_sessions, Exp_baselines, Exp_scores) |
| SRC-04 | Pipeline test generator v0.1 (feature list, residents and sex, device moves) |
| SRC-05 | Pipeline test input CSV v0.1 (column order of `raw_sessions`) |
| SRC-18 / SRC-19 | Wireframes: Alert review (`/alerts`), Analytics (`/analytics`) — alert reviews, snooze, data alerts, alarm timing check |
| TRD 06 | Database Design (DB-xxx) |
| TRD 07 / 08 / 09 | Analytics Engine, Baseline and Scoring, CUSUM and Alerting (writers of derived tables) |
| TRD 10 | Data Ingestion and Validation (writer of `raw_sessions`, `ingest_batches`, `ingest_rejections`) |
| TRD 12 | Security and Authentication (roles, API keys, audit actions) |
| TRD 21 | Environment Configuration (DATABASE_URL, PIPELINE_PROFILE, APP_ENV) |
| TRD 23 | Data Model and Entity Definitions (DME-xxx) |
| Owner decision D-OWNER-2/3 (18 Oct 2026) | Production baseline_n = 30; test_v0_1 for build/test only; feature data treated as potentially PHI-derived |

## 4. Requirements

### 4.1 Requirement table

| ID | Requirement | Priority | Trace | Verification |
|---|---|---|---|---|
| PGS-001 | The database shall run on PostgreSQL major version 16 with encoding UTF8, and the database-level setting `timezone` shall be `UTC` (`ALTER DATABASE <db> SET timezone = 'UTC'`). | Must | SRC-01, BR-17 | Test (`SHOW server_version_num` ≥ 160000 and < 170000; `SHOW timezone` = UTC) |
| PGS-002 | The schema shall create the extensions `pgcrypto` (for `gen_random_uuid()`) and `btree_gist` (for the device-assignment exclusion constraint) and no other extension. | Must | SRC-01 | Inspection of migration 0001; Test (`pg_extension` lists exactly plpgsql, pgcrypto, btree_gist) |
| PGS-003 | All EchoWell objects shall live in schema `public` and shall be owned by group role `echowell_migrator`. | Must | BR-16 | Test (`pg_tables.tableowner` = echowell_migrator for all 24 tables) |
| PGS-004 | Exactly three group roles shall exist: `echowell_migrator` (schema owner; Alembic connects through `DATABASE_MIGRATION_URL`), `echowell_app` (backend runtime and pipeline; `DATABASE_URL`), `echowell_readonly` (SELECT for researchers and exports, including `evaluation_ground_truth`); each is `NOLOGIN` and environments connect through the login roles of section 4.3. | Must | BR-16, TRD 12 | Test (`pg_roles`, `pg_auth_members`) |
| PGS-005 | The schema shall define exactly the 15 enumerated types of section 4.4 with the listed labels in the listed order. | Must | Contract §9 | Test (query `pg_enum` ordered by `enumsortorder`) |
| PGS-006 | The schema shall define exactly the 24 tables of section 4.6, with the column names, types, nullability and defaults shown, and no other tables except `alembic_version`. | Must | Contract §9, §19, §20 R17, BR-02 | Test (schema diff, PGS-016) |
| PGS-007 | Every table except `audit_logs`, `config_parameters` and `cusum_state` shall have primary key `id uuid DEFAULT gen_random_uuid()`; `audit_logs.id` shall be `bigserial`; `config_parameters` shall have primary key `(profile, key)`; `cusum_state` shall have primary key `epoch_id`. | Must | Contract §9 | Test (`information_schema.table_constraints`) |
| PGS-008 | Every column holding an instant shall be `timestamptz`; calendar days in facility local time shall be `date`; local clock time shall be `time(0)`. | Must | Contract §9, ASM-01 | Inspection; Test (no `timestamp without time zone` columns) |
| PGS-009 | `raw_sessions` shall contain one column per ingest field of TRD 10 / contract §5 and one column per feature of contract §6, named exactly `loudness_dbfs, total_phrase_duration_s, speech_rate_syl_per_s, articulation_rate_syl_per_s, number_of_pauses, pause_fraction, voiced_fraction, mean_f0_hz, f0_variability_st, jitter_local_pct, shimmer_local_pct, hnr_db, cpps_db, alpha_ratio_db, hammarberg_index_db, mfcc1, mfcc2, mfcc3, mfcc4`; all are `double precision NOT NULL` except `number_of_pauses integer NOT NULL`. | Must | SRC-03, SRC-05, BR-01 | Test (column list equals SRC-05 header feature names) |
| PGS-010 | Every foreign key shall be `ON DELETE RESTRICT` (PostgreSQL default `NO ACTION` is not used) except `scores.processed_session_id`, which shall be `ON DELETE CASCADE`. | Must | BR-02 | Test (`pg_constraint.confdeltype` = 'r' for all FKs except one 'c') |
| PGS-011 | `raw_sessions.audio_quality_flag` shall be constrained to `ok` or `poor`; `number_of_pauses` ≥ 0; `pause_fraction` and `voiced_fraction` in [0, 1]; `speech_duration_s` ≥ 0; `mean_f0_hz` > 0. | Must | SRC-03 Data_dictionary | Test (insert of each violating value fails with SQLSTATE 23514) |
| PGS-012 | `processed_sessions` shall enforce status/reason consistency by CHECK: `usable` has no reasons; `duplicate` has exactly the reason `session_id already received` and `epoch_id IS NULL`; `set_aside` has 1–3 reasons drawn from `quality flag poor`, `noise above limit`, `speech too short`; `quarantined` has exactly one reason matching `possible other speaker (F0 z=…; composite features with \|z\|>=3: …)` and a non-null `screen_detail`; and `reason_text` equals the reasons joined by `"; "`. | Must | BR-03, BR-04, BR-05, SRC-03 | Test (section 7, checks 4–6) |
| PGS-013 | `processed_sessions.local_date` shall be constrained to within one calendar day of the UTC date of `timestamp_utc`. | Must | ASM-01, BR-07 | Test (insert with local_date two days off fails) |
| PGS-014 | `day_ledger` shall enforce: `checked_in` ⇒ `reason = ''`; `missing_resident` ⇒ `reason = 'no record received'`; `missing_device_gap` ⇒ `device_id IS NOT NULL` and reason matching `all residents on shared device % have no record`; and at most one row per `(resident_id, local_date)`. | Must | BR-06, SRC-03 | Test (section 7, check 7) |
| PGS-015 | `device_assignments` shall reject two assignments of the same resident whose inclusive date ranges overlap (exclusion constraint `device_assignments_no_overlap_ex`); assignments of different residents to the same device may overlap (shared device). | Must | BR-06, BR-08 | Test (section 7, check 8; R02 and R03 both on D02 succeeds) |
| PGS-016 | Running `alembic upgrade head` on an empty PostgreSQL 16 database shall produce a schema equivalent to the DDL in this document, verified by the schema diff test `tests/integration/test_schema_reference.py`, which compares normalised `pg_dump --schema-only --no-owner` output of the migrated database with `database/schema.sql` and fails on any difference. | Must | SRC-01, TRD 13 | Test (CI job `schema-diff`) |
| PGS-017 | `database/schema.sql` shall be regenerated by `scripts/dump_schema.sh` (pg_dump `--schema-only --no-owner --no-comments` of a freshly migrated database, with the `SET`/`SELECT pg_catalog.set_config` preamble removed) in the same pull request as any migration change, and shall never be edited by hand. | Must | Contract §3 | Inspection (PR review); Test (PGS-016) |
| PGS-018 | `raw_sessions` and `audit_logs` shall each carry a row-level `BEFORE UPDATE OR DELETE` trigger and a statement-level `BEFORE TRUNCATE` trigger that call `reject_mutation()`, which raises SQLSTATE `EW001`. | Must | BR-02, SRC-02, BR-16 | Test (section 7, checks 1–3) |
| PGS-019 | `reject_mutation()` shall permit `DELETE` and `TRUNCATE` (never `UPDATE`) only when `current_user = 'echowell_migrator'` and the session setting `echowell.allow_purge` is `on`; this path is reserved for the test-database reset and the IRB withdrawal purge of TRD 06 (DB-024, DB-030). | Must | OQ-11, BR-02 | Test (section 7, check 9) |
| PGS-020 | Every table that has an `updated_at` column shall have a `BEFORE UPDATE` trigger calling `set_updated_at()`, which sets `updated_at = now()`. | Must | Contract §9 | Test (update a residents row; `updated_at` changes) |
| PGS-021 | Grants shall be exactly those of section 4.8: `echowell_app` has only `SELECT, INSERT` on `raw_sessions`, `audit_logs`, `ingest_rejections`, `staff_notes`, `baselines`, `alert_reviews`; no `DELETE` on master/config tables, `alerts` or `data_alerts`; no privilege on `evaluation_ground_truth`; and `echowell_readonly` cannot read `users.password_hash` or `api_keys.key_hash`. | Must | BR-16, TRD 12 | Test (`has_table_privilege`, `has_column_privilege`) |
| PGS-022 | Every migration that creates a table shall issue that table's grants in the same migration; `ALTER DEFAULT PRIVILEGES` shall not be used. | Must | BR-16 | Inspection; Test (PGS-016 compares privileges via `\dp` export) |
| PGS-023 | Constraint and index names shall follow section 4.9 and shall be declared explicitly in SQLAlchemy models (`name=`), so Alembic autogenerate produces no diff on a migrated database. | Must | TRD 06 DB-012 | Test (`alembic check` exits 0 in CI) |
| PGS-024 | Migration `0002_seed_config_parameters` shall insert the 46 rows of section 4.11 (23 keys × 2 profiles: the 16 keys of contract §7, the 5 keys of contract §19/§20 R17 and the 2 ingest keys `supported_schema_versions`, `feature_name_map` of TRD 10) with exactly the listed JSON values. | Must | SRC-03 Parameters, D-OWNER-2, contract §19 | Test (`SELECT count(*) … GROUP BY profile` = 23 each; values equal contract) |
| PGS-025 | `config_parameters` row `('production','baseline_n')` shall hold `30` and `('test_v0_1','baseline_n')` shall hold `16`. | Must | D-OWNER-2, ASM-04 | Test |
| PGS-026 | The synthetic roster seed of section 4.12 shall be applied only by `python -m backend.cli seed test_v0_1`, which shall exit with code 2 without writing when `APP_ENV=production`. | Must | D-OWNER-3, D-OWNER-4 (OQ-23 closed, D-28) | Test (CLI with APP_ENV=production writes nothing) |
| PGS-027 | Backend and Alembic connections shall use TLS: every non-local `DATABASE_URL`, `DATABASE_MIGRATION_URL` and `DATABASE_READONLY_URL` shall include `sslmode=require` (or stricter `verify-full`), and the backend shall refuse to start when `APP_ENV` is `staging` or `production` and the URL lacks it. | Must | D-OWNER-3, BR-16 | Test (startup with URL lacking sslmode in APP_ENV=staging exits non-zero) |
| PGS-028 | The backend shall map SQLSTATE `EW001` to an HTTP 500 `application/problem+json` response (error code from the TRD 05 catalogue, contract R19) and log an `error` event naming the table; no endpoint shall issue UPDATE, DELETE or TRUNCATE on `raw_sessions` or `audit_logs`. | Must | BR-02, TRD 17 | Test (repository unit test); Inspection |
| PGS-029 | `alerts` shall have at most one non-closed row per `epoch_id` (partial unique index `alerts_one_active_per_epoch_uq`) and at most one row per `(epoch_id, session_id)`. | Must | BR-11, TRD 09 | Test |
| PGS-030 | `epochs` shall have at most one row per resident with `ended_at IS NULL` (partial unique index `epochs_current_uq`) and unique `(resident_id, epoch_number)`. | Must | BR-08 | Test |
| PGS-031 | `baselines.feature_key` shall be one of the 19 feature keys or `composite`, and `(epoch_id, feature_key)` shall be unique, giving exactly 20 rows per frozen resident-epoch. | Must | BR-09, SRC-03 Exp_baselines | Test (test_v0_1 run: 180 rows, 9 epochs × 20) |
| PGS-032 | `scores.z` shall be a JSON object containing at least the 7 keys `z_loudness_dbfs, z_total_phrase_duration_s, z_speech_rate_syl_per_s, z_articulation_rate_syl_per_s, z_number_of_pauses, z_pause_fraction, z_voiced_fraction`, and `scores.cusum_tally` shall be ≥ 0. | Must | BR-10, SRC-03 Exp_scores | Test |
| PGS-033 | `processed_sessions.adjusted_features` shall be NULL for `duplicate` rows and otherwise a JSON object containing all 19 feature keys. | Must | BR-07 | Test |
| PGS-034 | `users.email` shall be stored lower-case and unique, and `users.password_hash` shall start with `$argon2id$`. | Must | TRD 12 | Test |
| PGS-035 | `api_keys.key_hash` shall be 64 lower-case hexadecimal characters (SHA-256) and unique; `scopes` shall be a non-empty subset of `{ingest:write, pipeline:run}` (contract R18). | Must | TRD 12 | Test |
| PGS-036 | `staff_notes.body` shall be 1–2000 characters after trimming, and a note may be superseded by at most one later note (`UNIQUE (supersedes_id)`). | Must | BR-13 | Test |
| PGS-037 | `residents.status = 'withdrawn'` shall hold if and only if `withdrawn_on IS NOT NULL`, and `withdrawn_on` shall not precede `enrolled_on`. | Must | OQ-11 | Test |
| PGS-038 | Every index of section 4.7 shall exist with the exact name, columns, order, INCLUDE list and predicate shown. | Should | TRD 06 DB-040..DB-047 | Test (PGS-016) |
| PGS-040 | `echowell_app` shall have no privilege on `evaluation_ground_truth` and no UPDATE, DELETE or TRUNCATE on `raw_sessions`, `audit_logs`, `alert_reviews` or `staff_notes` (contract R20). The Analytics "Alarm timing check" (test_v0_1 only) shall read `evaluation_ground_truth` only through a second connection `DATABASE_READONLY_URL` (login `echowell_readonly_login`, member of `echowell_readonly`, `sslmode=require`), opened solely by `backend/services/analytics_summary.py`; the pipeline and all other code use `DATABASE_URL`. `echowell_app_login` shall have no membership in `echowell_readonly` and no code shall issue `SET ROLE` to reach that table (contract R27). | Must | SRC-02 ("answer key never touches the analytics"), contract §19, R20, R27 | Test (as `echowell_app_login`: SELECT fails with 42501 and `SET ROLE echowell_readonly` fails with 42501; as `echowell_readonly_login`: SELECT returns 10 rows in test_v0_1); Inspection (only `analytics_summary.py` references `DATABASE_READONLY_URL`) |
| PGS-041 | `data_alerts` shall enforce by CHECK that `device_silent` rows reference a device and no resident; `baseline_stalled`, `possible_other_speaker` and `high_set_aside` rows reference a resident and no device; `review_flagged_data_problem` rows reference a resident and an `alert_reviews` row and have no `pipeline_run_id`; all other kinds have a `pipeline_run_id`; and at most one `open` row per `(kind, resident_id, device_id)` for the rule kinds (partial unique index `data_alerts_open_subject_uq`, NULLS NOT DISTINCT). | Must | Contract §19, BR-12 | Test |
| PGS-042 | `alert_reviews` shall be append-only for the application (SELECT, INSERT), shall require an `outcome` of enum `review_outcome`, shall store `explanations` as an array of 0–20 lower-case codes, and `note` NULL or 1–2000 characters. | Must | Contract §19, R5 | Test |
| PGS-043 | `alerts.snoozed_until` and `alerts.snoozed_by` shall be both NULL or both set. | Must | Contract §19 | Test |
| PGS-039 | Storage of every environment that holds non-synthetic data shall be encrypted at rest by the provider (Neon/Railway provider-managed encryption on the interim stack; RDS storage encryption with a customer-managed KMS key on the AWS target). | Must | D-OWNER-3, D-OWNER-4 (OQ-23 closed, D-28) | Inspection (provider settings recorded in TRD 22) |

### 4.2 Extensions

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;     -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS btree_gist;   -- uuid equality inside GiST exclusion constraints
```

### 4.3 Roles

Group roles are created once per cluster by the provisioning procedure of TRD 15 (on Neon by the project owner role,
on RDS by the master user). Login roles are created by the same procedure with generated passwords stored only in the
platform secret store (TRD 21). Locally (docker-compose) and in CI the procedure is the script
`database/roles/provision_login_roles.sql`, run as the PostgreSQL superuser right after the server starts: it idempotently creates
the three group roles below (NOLOGIN), makes `echowell_migrator` owner of schema `public`, and creates the three login roles with
passwords read via psql `\getenv` from `ECHOWELL_MIGRATOR_DB_PASSWORD`, `ECHOWELL_APP_DB_PASSWORD` and
`ECHOWELL_READONLY_DB_PASSWORD` (local/CI only). Tests run as `echowell_app_login` (TRD 16 CIC-015):

| Login role | Member of | Used by | Connection string |
|---|---|---|---|
| `echowell_app_login` | `echowell_app` | FastAPI backend and pipeline workers | `DATABASE_URL` |
| `echowell_migrator_login` | `echowell_migrator` | Alembic in the deploy step; `backend.cli seed`, `reset-test-db`, `purge-resident` | `DATABASE_MIGRATION_URL` |
| `echowell_readonly_login` | `echowell_readonly` | `backend/services/analytics_summary.py` Alarm timing check (test_v0_1); researchers' offline analysis and restore drills (separate credentials issued by admin) | `DATABASE_READONLY_URL` (`sslmode=require`) |

`echowell_app_login` is a member of `echowell_app` only; it has no membership in `echowell_readonly` (PGS-040, contract R27).

Alembic's `env.py` shall execute `SET ROLE echowell_migrator` immediately after connecting, so that every object is
owned by the group role and not by the login role.

```sql
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'echowell_migrator') THEN
    CREATE ROLE echowell_migrator NOLOGIN;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'echowell_app') THEN
    CREATE ROLE echowell_app NOLOGIN;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'echowell_readonly') THEN
    CREATE ROLE echowell_readonly NOLOGIN;
  END IF;
END
$$;

-- Per-environment login roles (local/CI: database/roles/provision_login_roles.sql with passwords from env via \getenv;
-- staging/production: provider console with generated secrets; passwords never committed):
-- CREATE ROLE echowell_app_login      LOGIN PASSWORD :'app_password'      IN ROLE echowell_app;
-- CREATE ROLE echowell_migrator_login LOGIN PASSWORD :'migrator_password' IN ROLE echowell_migrator;
-- CREATE ROLE echowell_readonly_login LOGIN PASSWORD :'readonly_password' IN ROLE echowell_readonly;
```

### 4.4 Enumerated types

| Type | Labels (in order) | Used by |
|---|---|---|
| `resident_cohort` | longitudinal, new_admission | residents.cohort |
| `resident_status` | active, withdrawn | residents.status |
| `ingest_source` | api_single, api_batch, csv_upload, seed | ingest_batches.source |
| `session_status` | usable, set_aside, quarantined, duplicate | processed_sessions.status |
| `day_status` | checked_in, missing_resident, missing_device_gap | day_ledger.status |
| `alarm_state` | off, rings, on | scores.alarm_state |
| `alert_status` | open, acknowledged, closed | alerts.status |
| `note_type` | observation, action_taken, follow_up | staff_notes.note_type |
| `pipeline_trigger` | ingest, nightly, manual, test | pipeline_runs.trigger |
| `pipeline_run_status` | running, succeeded, failed | pipeline_runs.status |
| `user_role` | admin, clinician, researcher | users.role |
| `actor_type` | user, api_key, system | audit_logs.actor_type |
| `review_outcome` | no_concern, known_cause, referred, data_problem | alert_reviews.outcome |
| `data_alert_kind` | baseline_stalled, possible_other_speaker, high_set_aside, device_silent, review_flagged_data_problem | data_alerts.kind |
| `data_alert_status` | open, resolved | data_alerts.status |

Small closed vocabularies that are not enums (to avoid enum migrations for text values) are CHECK-constrained text:
`residents.sex` and `facility_reference_ranges.sex` (`F`, `M`, NULL), `raw_sessions.audio_quality_flag` (`ok`,
`poor`), `pipeline_runs.config_profile` and `config_parameters.profile` (`production`, `test_v0_1`),
`alerts.closed_reason` (`epoch ended`, `admin`, `superseded by rebuild`), `api_keys.scopes` elements (`ingest:write`, `pipeline:run`).
`alert_reviews.explanations` elements are codes validated by the application against config key `review_explanations`
(provisional list, OQ-25); the database only checks their format.

```sql
CREATE TYPE resident_cohort     AS ENUM ('longitudinal', 'new_admission');
CREATE TYPE resident_status     AS ENUM ('active', 'withdrawn');
CREATE TYPE ingest_source       AS ENUM ('api_single', 'api_batch', 'csv_upload', 'seed');
CREATE TYPE session_status      AS ENUM ('usable', 'set_aside', 'quarantined', 'duplicate');
CREATE TYPE day_status          AS ENUM ('checked_in', 'missing_resident', 'missing_device_gap');
CREATE TYPE alarm_state         AS ENUM ('off', 'rings', 'on');
CREATE TYPE alert_status        AS ENUM ('open', 'acknowledged', 'closed');
CREATE TYPE note_type           AS ENUM ('observation', 'action_taken', 'follow_up');
CREATE TYPE pipeline_trigger    AS ENUM ('ingest', 'nightly', 'manual', 'test');
CREATE TYPE pipeline_run_status AS ENUM ('running', 'succeeded', 'failed');
CREATE TYPE user_role           AS ENUM ('admin', 'clinician', 'researcher');
CREATE TYPE actor_type          AS ENUM ('user', 'api_key', 'system');
CREATE TYPE review_outcome      AS ENUM ('no_concern', 'known_cause', 'referred', 'data_problem');
CREATE TYPE data_alert_kind     AS ENUM ('baseline_stalled', 'possible_other_speaker', 'high_set_aside', 'device_silent',
                                         'review_flagged_data_problem');
CREATE TYPE data_alert_status   AS ENUM ('open', 'resolved');
```

### 4.5 Trigger functions

```sql
CREATE FUNCTION set_updated_at() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END
$$;

-- Rejects UPDATE, DELETE and TRUNCATE on append-only tables.
-- Single escape hatch: role echowell_migrator with session setting echowell.allow_purge = 'on'
-- (used only by the documented test-database reset and IRB withdrawal purge procedures).
CREATE FUNCTION reject_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF current_user = 'echowell_migrator'
     AND coalesce(current_setting('echowell.allow_purge', true), 'off') = 'on'
     AND TG_OP IN ('DELETE', 'TRUNCATE') THEN
    IF TG_LEVEL = 'ROW' THEN RETURN OLD; ELSE RETURN NULL; END IF;
  END IF;
  RAISE EXCEPTION 'table % is append-only: % is not allowed', TG_TABLE_NAME, TG_OP
    USING ERRCODE = 'EW001';
END
$$;
```

### 4.6 Tables

Tables are listed in creation (dependency) order. Column meaning, allowed values and writers are in TRD 23 section 4.

#### 4.6.1 facilities
```sql
CREATE TABLE facilities (
  id          uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  name        text        NOT NULL,
  timezone    text        NOT NULL DEFAULT 'America/Chicago',
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT facilities_name_uq UNIQUE (name),
  CONSTRAINT facilities_name_ck CHECK (char_length(name) BETWEEN 1 AND 120),
  CONSTRAINT facilities_timezone_ck CHECK (char_length(timezone) BETWEEN 1 AND 64)
);
```

#### 4.6.2 users
```sql
CREATE TABLE users (
  id             uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  email          text        NOT NULL,
  display_name   text        NOT NULL,
  password_hash  text        NOT NULL,
  role           user_role   NOT NULL,
  active         boolean     NOT NULL DEFAULT true,
  last_login_at  timestamptz NULL,
  created_at     timestamptz NOT NULL DEFAULT now(),
  updated_at     timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT users_email_uq UNIQUE (email),
  CONSTRAINT users_email_lower_ck CHECK (email = lower(email)),
  CONSTRAINT users_email_format_ck CHECK (email ~ '^[^@\s]+@[^@\s]+\.[^@\s]+$' AND char_length(email) <= 254),
  CONSTRAINT users_display_name_ck CHECK (char_length(display_name) BETWEEN 1 AND 120),
  CONSTRAINT users_password_hash_ck CHECK (password_hash LIKE '$argon2id$%')
);
```

#### 4.6.3 residents
```sql
CREATE TABLE residents (
  id             uuid            PRIMARY KEY DEFAULT gen_random_uuid(),
  facility_id    uuid            NOT NULL REFERENCES facilities (id) ON DELETE RESTRICT,
  resident_code  text            NOT NULL,
  sex            text            NULL,
  cohort         resident_cohort NOT NULL DEFAULT 'longitudinal',
  enrolled_on    date            NOT NULL,
  admitted_on    date            NULL,
  withdrawn_on   date            NULL,
  status         resident_status NOT NULL DEFAULT 'active',
  created_at     timestamptz     NOT NULL DEFAULT now(),
  updated_at     timestamptz     NOT NULL DEFAULT now(),
  CONSTRAINT residents_resident_code_uq UNIQUE (resident_code),
  CONSTRAINT residents_resident_code_ck CHECK (resident_code ~ '^[A-Z0-9][A-Z0-9-]{0,31}$'),
  CONSTRAINT residents_sex_ck CHECK (sex IS NULL OR sex IN ('F', 'M')),
  CONSTRAINT residents_withdrawn_ck CHECK ((status = 'withdrawn') = (withdrawn_on IS NOT NULL)),
  CONSTRAINT residents_withdrawn_after_enrol_ck CHECK (withdrawn_on IS NULL OR withdrawn_on >= enrolled_on),
  CONSTRAINT residents_admitted_ck CHECK (admitted_on IS NULL OR admitted_on <= enrolled_on)
);
```

#### 4.6.4 devices
```sql
CREATE TABLE devices (
  id                     uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  facility_id            uuid        NOT NULL REFERENCES facilities (id) ON DELETE RESTRICT,
  device_code            text        NOT NULL,
  room_label             text        NULL,
  firmware_version_last  text        NULL,
  active                 boolean     NOT NULL DEFAULT true,
  created_at             timestamptz NOT NULL DEFAULT now(),
  updated_at             timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT devices_device_code_uq UNIQUE (device_code),
  CONSTRAINT devices_device_code_ck CHECK (device_code ~ '^[A-Z0-9][A-Z0-9-]{0,31}$'),
  CONSTRAINT devices_room_label_ck CHECK (room_label IS NULL OR char_length(room_label) BETWEEN 1 AND 60)
);
```

#### 4.6.5 device_assignments
```sql
CREATE TABLE device_assignments (
  id           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  resident_id  uuid        NOT NULL REFERENCES residents (id) ON DELETE RESTRICT,
  device_id    uuid        NOT NULL REFERENCES devices (id) ON DELETE RESTRICT,
  valid_from   date        NOT NULL,
  valid_to     date        NULL,
  created_at   timestamptz NOT NULL DEFAULT now(),
  updated_at   timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT device_assignments_range_ck CHECK (valid_to IS NULL OR valid_to >= valid_from),
  -- one device per resident on any given day (valid_to is inclusive)
  CONSTRAINT device_assignments_no_overlap_ex EXCLUDE USING gist (
    resident_id WITH =,
    daterange(valid_from, valid_to, '[]') WITH &&
  )
);
```

#### 4.6.6 api_keys
```sql
CREATE TABLE api_keys (
  id            uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  name          text        NOT NULL,
  key_hash      text        NOT NULL,
  scopes        text[]      NOT NULL DEFAULT ARRAY['ingest:write']::text[],
  device_id     uuid        NULL REFERENCES devices (id) ON DELETE RESTRICT,
  active        boolean     NOT NULL DEFAULT true,
  created_at    timestamptz NOT NULL DEFAULT now(),
  updated_at    timestamptz NOT NULL DEFAULT now(),
  last_used_at  timestamptz NULL,
  CONSTRAINT api_keys_key_hash_uq UNIQUE (key_hash),
  CONSTRAINT api_keys_key_hash_ck CHECK (key_hash ~ '^[0-9a-f]{64}$'),
  CONSTRAINT api_keys_name_ck CHECK (char_length(name) BETWEEN 1 AND 120),
  CONSTRAINT api_keys_scopes_ck CHECK (cardinality(scopes) >= 1 AND scopes <@ ARRAY['ingest:write', 'pipeline:run']::text[])
);
```

#### 4.6.7 ingest_batches
```sql
CREATE TABLE ingest_batches (
  id              uuid          PRIMARY KEY DEFAULT gen_random_uuid(),
  source          ingest_source NOT NULL,
  filename        text          NULL,
  record_count    integer       NOT NULL DEFAULT 0,
  accepted_count  integer       NOT NULL DEFAULT 0,
  rejected_count  integer       NOT NULL DEFAULT 0,
  duplicate_count integer       NOT NULL DEFAULT 0,
  uploaded_by     uuid          NULL REFERENCES users (id) ON DELETE RESTRICT,
  api_key_id      uuid          NULL REFERENCES api_keys (id) ON DELETE RESTRICT,
  received_at     timestamptz   NOT NULL DEFAULT now(),
  created_at      timestamptz   NOT NULL DEFAULT now(),
  updated_at      timestamptz   NOT NULL DEFAULT now(),
  CONSTRAINT ingest_batches_counts_ck CHECK (
    record_count >= 0 AND accepted_count >= 0 AND rejected_count >= 0 AND duplicate_count >= 0
    AND accepted_count + rejected_count <= record_count
    AND duplicate_count <= accepted_count),
  CONSTRAINT ingest_batches_actor_ck CHECK (source = 'seed' OR uploaded_by IS NOT NULL OR api_key_id IS NOT NULL),
  CONSTRAINT ingest_batches_filename_ck CHECK ((source = 'csv_upload') <= (filename IS NOT NULL))
);
```

#### 4.6.8 ingest_rejections
```sql
CREATE TABLE ingest_rejections (
  id               uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  ingest_batch_id  uuid        NULL REFERENCES ingest_batches (id) ON DELETE RESTRICT,
  api_key_id       uuid        NULL REFERENCES api_keys (id) ON DELETE RESTRICT,
  row_number       integer     NULL,
  received_at      timestamptz NOT NULL DEFAULT now(),
  raw_body         jsonb       NOT NULL,
  errors           jsonb       NOT NULL,
  CONSTRAINT ingest_rejections_errors_ck CHECK (jsonb_typeof(errors) = 'array' AND jsonb_array_length(errors) >= 1),
  CONSTRAINT ingest_rejections_row_number_ck CHECK (row_number IS NULL OR row_number >= 1)
);
```

#### 4.6.9 raw_sessions (immutable raw store)
```sql
CREATE TABLE raw_sessions (
  id                           uuid             PRIMARY KEY DEFAULT gen_random_uuid(),
  arrival_seq                  bigserial        NOT NULL,
  received_at                  timestamptz      NOT NULL DEFAULT now(),
  ingest_batch_id              uuid             NULL REFERENCES ingest_batches (id) ON DELETE RESTRICT,
  api_key_id                   uuid             NULL REFERENCES api_keys (id) ON DELETE RESTRICT,
  payload                      jsonb            NOT NULL,
  ingest_warnings              jsonb            NOT NULL DEFAULT '[]'::jsonb,  -- TRD 10 plausibility warnings {field, code, message}
  resident_id                  uuid             NOT NULL REFERENCES residents (id) ON DELETE RESTRICT,
  device_id                    uuid             NOT NULL REFERENCES devices (id) ON DELETE RESTRICT,
  -- typed copies of the ingest record schema v0.1 fields (TRD 10), in SRC-05 column order
  schema_version               text             NOT NULL,
  session_id                   text             NOT NULL,
  resident_code                text             NOT NULL,
  device_code                  text             NOT NULL,
  timestamp_utc                timestamptz      NOT NULL,
  mic_noise_level_dbfs         double precision NOT NULL,
  audio_quality_flag           text             NOT NULL,
  extraction_software_version  text             NOT NULL,
  device_firmware_version      text             NOT NULL,
  speech_duration_s            double precision NOT NULL,
  phrase_id                    text             NULL,
  -- 19 acoustic features (contract section 6; names are placeholders, OQ-03)
  loudness_dbfs                double precision NOT NULL,
  total_phrase_duration_s      double precision NOT NULL,
  speech_rate_syl_per_s        double precision NOT NULL,
  articulation_rate_syl_per_s  double precision NOT NULL,
  number_of_pauses             integer          NOT NULL,
  pause_fraction               double precision NOT NULL,
  voiced_fraction              double precision NOT NULL,
  mean_f0_hz                   double precision NOT NULL,
  f0_variability_st            double precision NOT NULL,
  jitter_local_pct             double precision NOT NULL,
  shimmer_local_pct            double precision NOT NULL,
  hnr_db                       double precision NOT NULL,
  cpps_db                      double precision NOT NULL,
  alpha_ratio_db               double precision NOT NULL,
  hammarberg_index_db          double precision NOT NULL,
  mfcc1                        double precision NOT NULL,
  mfcc2                        double precision NOT NULL,
  mfcc3                        double precision NOT NULL,
  mfcc4                        double precision NOT NULL,
  CONSTRAINT raw_sessions_arrival_seq_uq UNIQUE (arrival_seq),
  CONSTRAINT raw_sessions_payload_ck CHECK (jsonb_typeof(payload) = 'object'),
  CONSTRAINT raw_sessions_schema_version_ck CHECK (char_length(schema_version) BETWEEN 1 AND 16),
  CONSTRAINT raw_sessions_session_id_ck CHECK (char_length(session_id) BETWEEN 1 AND 64),
  CONSTRAINT raw_sessions_audio_quality_flag_ck CHECK (audio_quality_flag IN ('ok', 'poor')),
  CONSTRAINT raw_sessions_speech_duration_ck CHECK (speech_duration_s >= 0),
  CONSTRAINT raw_sessions_number_of_pauses_ck CHECK (number_of_pauses >= 0),
  CONSTRAINT raw_sessions_pause_fraction_ck CHECK (pause_fraction BETWEEN 0 AND 1),
  CONSTRAINT raw_sessions_voiced_fraction_ck CHECK (voiced_fraction BETWEEN 0 AND 1),
  CONSTRAINT raw_sessions_mean_f0_ck CHECK (mean_f0_hz > 0),
  CONSTRAINT raw_sessions_versions_ck CHECK (
    char_length(extraction_software_version) BETWEEN 1 AND 64
    AND char_length(device_firmware_version) BETWEEN 1 AND 64)
);
```

#### 4.6.10 pipeline_runs
```sql
CREATE TABLE pipeline_runs (
  id               uuid                PRIMARY KEY DEFAULT gen_random_uuid(),
  trigger          pipeline_trigger    NOT NULL,
  scope            jsonb               NOT NULL,
  config_profile   text                NOT NULL,
  config_snapshot  jsonb               NOT NULL,
  code_version     text                NOT NULL,
  as_of            timestamptz         NOT NULL,
  started_at       timestamptz         NOT NULL DEFAULT now(),
  finished_at      timestamptz         NULL,
  status           pipeline_run_status NOT NULL DEFAULT 'running',
  counts           jsonb               NOT NULL DEFAULT '{}'::jsonb,
  warnings         jsonb               NOT NULL DEFAULT '[]'::jsonb,
  error_message    text                NULL,
  created_at       timestamptz         NOT NULL DEFAULT now(),
  updated_at       timestamptz         NOT NULL DEFAULT now(),
  CONSTRAINT pipeline_runs_profile_ck CHECK (config_profile IN ('production', 'test_v0_1')),
  CONSTRAINT pipeline_runs_scope_ck CHECK (
    (scope = '{"type": "all"}'::jsonb)
    OR (scope->>'type' = 'residents' AND jsonb_typeof(scope->'resident_codes') = 'array'
        AND jsonb_array_length(scope->'resident_codes') >= 1)),
  CONSTRAINT pipeline_runs_snapshot_ck CHECK (jsonb_typeof(config_snapshot) = 'object'),
  CONSTRAINT pipeline_runs_counts_ck CHECK (jsonb_typeof(counts) = 'object'),
  CONSTRAINT pipeline_runs_warnings_ck CHECK (jsonb_typeof(warnings) = 'array'),
  CONSTRAINT pipeline_runs_finished_ck CHECK ((status = 'running') = (finished_at IS NULL)),
  CONSTRAINT pipeline_runs_error_ck CHECK ((status = 'failed') = (error_message IS NOT NULL)),
  CONSTRAINT pipeline_runs_order_ck CHECK (finished_at IS NULL OR finished_at >= started_at)
);
```

#### 4.6.11 epochs
```sql
CREATE TABLE epochs (
  id                           uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  resident_id                  uuid        NOT NULL REFERENCES residents (id) ON DELETE RESTRICT,
  epoch_number                 integer     NOT NULL,
  device_id                    uuid        NOT NULL REFERENCES devices (id) ON DELETE RESTRICT,
  device_firmware_version      text        NOT NULL,
  extraction_software_version  text        NOT NULL,
  started_at                   timestamptz NOT NULL,
  ended_at                     timestamptz NULL,
  pipeline_run_id              uuid        NOT NULL REFERENCES pipeline_runs (id) ON DELETE RESTRICT,
  created_at                   timestamptz NOT NULL DEFAULT now(),
  updated_at                   timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT epochs_resident_number_uq UNIQUE (resident_id, epoch_number),
  CONSTRAINT epochs_number_ck CHECK (epoch_number >= 1),
  CONSTRAINT epochs_order_ck CHECK (ended_at IS NULL OR ended_at > started_at)
);
```

#### 4.6.12 processed_sessions
```sql
CREATE TABLE processed_sessions (
  id                 uuid             PRIMARY KEY DEFAULT gen_random_uuid(),
  raw_session_id     uuid             NOT NULL REFERENCES raw_sessions (id) ON DELETE RESTRICT,
  session_id         text             NOT NULL,
  resident_id        uuid             NOT NULL REFERENCES residents (id) ON DELETE RESTRICT,
  epoch_id           uuid             NULL REFERENCES epochs (id) ON DELETE RESTRICT,
  status             session_status   NOT NULL,
  reasons            text[]           NOT NULL DEFAULT '{}'::text[],
  reason_text        text             NOT NULL DEFAULT '',
  timestamp_utc      timestamptz      NOT NULL,
  local_date         date             NOT NULL,
  local_time         time(0)          NOT NULL,
  is_morning         boolean          NOT NULL,
  screen_detail      text             NULL,
  baseline_ordinal   integer          NULL,
  in_baseline        boolean          NOT NULL DEFAULT false,
  adjusted_features  jsonb            NULL,
  pipeline_run_id    uuid             NOT NULL REFERENCES pipeline_runs (id) ON DELETE RESTRICT,
  created_at         timestamptz      NOT NULL DEFAULT now(),
  CONSTRAINT processed_sessions_raw_session_uq UNIQUE (raw_session_id),
  CONSTRAINT processed_sessions_epoch_ck CHECK ((status = 'duplicate') = (epoch_id IS NULL)),
  CONSTRAINT processed_sessions_local_date_ck CHECK (
    local_date BETWEEN (timestamp_utc AT TIME ZONE 'UTC')::date - 1
                   AND (timestamp_utc AT TIME ZONE 'UTC')::date + 1),
  CONSTRAINT processed_sessions_reason_text_ck CHECK (reason_text = array_to_string(reasons, '; ')),
  CONSTRAINT processed_sessions_status_reason_ck CHECK (
       (status = 'usable'      AND cardinality(reasons) = 0)
    OR (status = 'duplicate'   AND reasons = ARRAY['session_id already received']::text[])
    OR (status = 'set_aside'   AND cardinality(reasons) BETWEEN 1 AND 3
        AND reasons <@ ARRAY['quality flag poor', 'noise above limit', 'speech too short']::text[])
    OR (status = 'quarantined' AND cardinality(reasons) = 1
        AND reasons[1] LIKE 'possible other speaker (F0 z=%; composite features with |z|>=3: %)')),
  CONSTRAINT processed_sessions_screen_ck CHECK (status <> 'quarantined' OR screen_detail IS NOT NULL),
  CONSTRAINT processed_sessions_ordinal_ck CHECK (
    (status = 'usable') = (baseline_ordinal IS NOT NULL) AND (baseline_ordinal IS NULL OR baseline_ordinal >= 1)),
  CONSTRAINT processed_sessions_in_baseline_ck CHECK (NOT in_baseline OR status = 'usable'),
  CONSTRAINT processed_sessions_adjusted_ck CHECK (
    (status = 'duplicate' AND adjusted_features IS NULL)
    OR (status <> 'duplicate' AND jsonb_typeof(adjusted_features) = 'object'
        AND adjusted_features ?& ARRAY['loudness_dbfs','total_phrase_duration_s','speech_rate_syl_per_s',
          'articulation_rate_syl_per_s','number_of_pauses','pause_fraction','voiced_fraction','mean_f0_hz',
          'f0_variability_st','jitter_local_pct','shimmer_local_pct','hnr_db','cpps_db','alpha_ratio_db',
          'hammarberg_index_db','mfcc1','mfcc2','mfcc3','mfcc4']))
);
```

#### 4.6.13 day_ledger
```sql
CREATE TABLE day_ledger (
  id               uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  resident_id      uuid        NOT NULL REFERENCES residents (id) ON DELETE RESTRICT,
  local_date       date        NOT NULL,
  status           day_status  NOT NULL,
  device_id        uuid        NULL REFERENCES devices (id) ON DELETE RESTRICT,
  reason           text        NOT NULL DEFAULT '',
  pipeline_run_id  uuid        NOT NULL REFERENCES pipeline_runs (id) ON DELETE RESTRICT,
  created_at       timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT day_ledger_resident_date_uq UNIQUE (resident_id, local_date),
  CONSTRAINT day_ledger_reason_ck CHECK (
       (status = 'checked_in'         AND reason = '')
    OR (status = 'missing_resident'   AND reason = 'no record received')
    OR (status = 'missing_device_gap' AND device_id IS NOT NULL
        AND reason LIKE 'all residents on shared device % have no record'))
);
```

#### 4.6.14 baselines
```sql
CREATE TABLE baselines (
  id                       uuid             PRIMARY KEY DEFAULT gen_random_uuid(),
  resident_id              uuid             NOT NULL REFERENCES residents (id) ON DELETE RESTRICT,
  epoch_id                 uuid             NOT NULL REFERENCES epochs (id) ON DELETE RESTRICT,
  feature_key              text             NOT NULL,
  n_sessions               integer          NOT NULL,
  first_session_id         text             NOT NULL,
  frozen_after_session_id  text             NOT NULL,
  median                   double precision NOT NULL,
  mad                      double precision NOT NULL,
  robust_spread            double precision NOT NULL,
  floor_applied            boolean          NOT NULL,
  frozen_at                timestamptz      NOT NULL,
  pipeline_run_id          uuid             NOT NULL REFERENCES pipeline_runs (id) ON DELETE RESTRICT,
  created_at               timestamptz      NOT NULL DEFAULT now(),
  CONSTRAINT baselines_epoch_feature_uq UNIQUE (epoch_id, feature_key),
  CONSTRAINT baselines_feature_key_ck CHECK (feature_key IN (
    'loudness_dbfs','total_phrase_duration_s','speech_rate_syl_per_s','articulation_rate_syl_per_s',
    'number_of_pauses','pause_fraction','voiced_fraction','mean_f0_hz','f0_variability_st',
    'jitter_local_pct','shimmer_local_pct','hnr_db','cpps_db','alpha_ratio_db','hammarberg_index_db',
    'mfcc1','mfcc2','mfcc3','mfcc4','composite')),
  CONSTRAINT baselines_n_sessions_ck CHECK (n_sessions >= 1),
  CONSTRAINT baselines_spread_ck CHECK (mad >= 0 AND robust_spread >= 0)
);
```

#### 4.6.15 scores
```sql
CREATE TABLE scores (
  id                     uuid             PRIMARY KEY DEFAULT gen_random_uuid(),
  processed_session_id   uuid             NOT NULL REFERENCES processed_sessions (id) ON DELETE CASCADE,
  resident_id            uuid             NOT NULL REFERENCES residents (id) ON DELETE RESTRICT,
  epoch_id               uuid             NOT NULL REFERENCES epochs (id) ON DELETE RESTRICT,
  local_date             date             NOT NULL,
  is_morning             boolean          NOT NULL,
  z                      jsonb            NOT NULL,
  composite_raw          double precision NOT NULL,
  composite_z            double precision NOT NULL,
  cusum_tally            double precision NOT NULL,
  alarm_state            alarm_state      NOT NULL,
  pipeline_run_id        uuid             NOT NULL REFERENCES pipeline_runs (id) ON DELETE RESTRICT,
  created_at             timestamptz      NOT NULL DEFAULT now(),
  CONSTRAINT scores_processed_session_uq UNIQUE (processed_session_id),
  CONSTRAINT scores_z_ck CHECK (jsonb_typeof(z) = 'object' AND z ?& ARRAY[
    'z_loudness_dbfs','z_total_phrase_duration_s','z_speech_rate_syl_per_s','z_articulation_rate_syl_per_s',
    'z_number_of_pauses','z_pause_fraction','z_voiced_fraction']),
  CONSTRAINT scores_cusum_ck CHECK (cusum_tally >= 0)
);
```

#### 4.6.16 cusum_state
```sql
CREATE TABLE cusum_state (
  epoch_id                uuid             PRIMARY KEY REFERENCES epochs (id) ON DELETE RESTRICT,
  resident_id             uuid             NOT NULL REFERENCES residents (id) ON DELETE RESTRICT,
  current_tally           double precision NOT NULL DEFAULT 0,
  last_scored_session_id  text             NULL,
  alarm_on                boolean          NOT NULL DEFAULT false,
  pipeline_run_id         uuid             NOT NULL REFERENCES pipeline_runs (id) ON DELETE RESTRICT,
  updated_at              timestamptz      NOT NULL DEFAULT now(),
  CONSTRAINT cusum_state_tally_ck CHECK (current_tally >= 0),
  CONSTRAINT cusum_state_scored_ck CHECK (last_scored_session_id IS NOT NULL OR (current_tally = 0 AND NOT alarm_on))
);
```

#### 4.6.17 alerts
```sql
CREATE TABLE alerts (
  id                uuid             PRIMARY KEY DEFAULT gen_random_uuid(),
  resident_id       uuid             NOT NULL REFERENCES residents (id) ON DELETE RESTRICT,
  epoch_id          uuid             NOT NULL REFERENCES epochs (id) ON DELETE RESTRICT,
  session_id        text             NOT NULL,
  triggered_at      timestamptz      NOT NULL,
  local_date        date             NOT NULL,
  cusum_value       double precision NOT NULL,
  status            alert_status     NOT NULL DEFAULT 'open',
  closed_reason     text             NULL,
  closed_at         timestamptz      NULL,
  acknowledged_by   uuid             NULL REFERENCES users (id) ON DELETE RESTRICT,
  acknowledged_at   timestamptz      NULL,
  snoozed_until     timestamptz      NULL,
  snoozed_by        uuid             NULL REFERENCES users (id) ON DELETE RESTRICT,
  pipeline_run_id   uuid             NOT NULL REFERENCES pipeline_runs (id) ON DELETE RESTRICT,
  created_at        timestamptz      NOT NULL DEFAULT now(),
  updated_at        timestamptz      NOT NULL DEFAULT now(),
  CONSTRAINT alerts_epoch_session_uq UNIQUE (epoch_id, session_id),
  CONSTRAINT alerts_cusum_ck CHECK (cusum_value >= 0),
  CONSTRAINT alerts_closed_ck CHECK (
    (status = 'closed') = (closed_reason IS NOT NULL)
    AND (status = 'closed') = (closed_at IS NOT NULL)),
  CONSTRAINT alerts_closed_reason_ck CHECK (
    closed_reason IS NULL OR closed_reason IN ('epoch ended', 'admin', 'superseded by rebuild')),
  CONSTRAINT alerts_ack_ck CHECK ((acknowledged_by IS NULL) = (acknowledged_at IS NULL)),
  CONSTRAINT alerts_ack_status_ck CHECK (status <> 'acknowledged' OR acknowledged_at IS NOT NULL),
  CONSTRAINT alerts_snooze_ck CHECK ((snoozed_until IS NULL) = (snoozed_by IS NULL))
);
```

#### 4.6.18 alert_reviews
```sql
CREATE TABLE alert_reviews (
  id                uuid           PRIMARY KEY DEFAULT gen_random_uuid(),
  alert_id          uuid           NOT NULL REFERENCES alerts (id) ON DELETE RESTRICT,
  reviewer_user_id  uuid           NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
  explanations      text[]         NOT NULL DEFAULT '{}'::text[],
  outcome           review_outcome NOT NULL,
  note              text           NULL,
  created_at        timestamptz    NOT NULL DEFAULT now(),
  CONSTRAINT alert_reviews_explanations_ck CHECK (
    cardinality(explanations) <= 20
    AND array_to_string(explanations, ',') ~ '^([a-z][a-z0-9_]{0,63}(,[a-z][a-z0-9_]{0,63})*)?$'),
  CONSTRAINT alert_reviews_note_ck CHECK (note IS NULL OR (char_length(btrim(note)) >= 1 AND char_length(note) <= 2000))
);
```

#### 4.6.19 data_alerts
```sql
CREATE TABLE data_alerts (
  id                 uuid              PRIMARY KEY DEFAULT gen_random_uuid(),
  kind               data_alert_kind   NOT NULL,
  resident_id        uuid              NULL REFERENCES residents (id) ON DELETE RESTRICT,
  device_id          uuid              NULL REFERENCES devices (id) ON DELETE RESTRICT,
  alert_review_id    uuid              NULL REFERENCES alert_reviews (id) ON DELETE RESTRICT,
  title              text              NOT NULL,
  detail             text              NOT NULL DEFAULT '',
  first_detected_at  timestamptz       NOT NULL,
  last_detected_at   timestamptz       NOT NULL,
  status             data_alert_status NOT NULL DEFAULT 'open',
  resolved_at        timestamptz       NULL,
  pipeline_run_id    uuid              NULL REFERENCES pipeline_runs (id) ON DELETE RESTRICT,
  created_at         timestamptz       NOT NULL DEFAULT now(),
  updated_at         timestamptz       NOT NULL DEFAULT now(),
  CONSTRAINT data_alerts_alert_review_uq UNIQUE (alert_review_id),
  CONSTRAINT data_alerts_subject_ck CHECK (
       (kind = 'device_silent' AND device_id IS NOT NULL AND resident_id IS NULL AND alert_review_id IS NULL)
    OR (kind IN ('baseline_stalled', 'possible_other_speaker', 'high_set_aside')
        AND resident_id IS NOT NULL AND device_id IS NULL AND alert_review_id IS NULL)
    OR (kind = 'review_flagged_data_problem' AND resident_id IS NOT NULL AND alert_review_id IS NOT NULL)),
  CONSTRAINT data_alerts_run_ck CHECK ((kind = 'review_flagged_data_problem') = (pipeline_run_id IS NULL)),
  CONSTRAINT data_alerts_resolved_ck CHECK ((status = 'resolved') = (resolved_at IS NOT NULL)),
  CONSTRAINT data_alerts_detected_ck CHECK (last_detected_at >= first_detected_at),
  CONSTRAINT data_alerts_text_ck CHECK (char_length(title) BETWEEN 1 AND 200 AND char_length(detail) <= 500)
);
```

#### 4.6.20 staff_notes
```sql
CREATE TABLE staff_notes (
  id               uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  resident_id      uuid        NOT NULL REFERENCES residents (id) ON DELETE RESTRICT,
  alert_id         uuid        NULL REFERENCES alerts (id) ON DELETE RESTRICT,
  author_user_id   uuid        NOT NULL REFERENCES users (id) ON DELETE RESTRICT,
  note_type        note_type   NOT NULL,
  body             text        NOT NULL,
  marked_reviewed  boolean     NOT NULL DEFAULT false,
  supersedes_id    uuid        NULL REFERENCES staff_notes (id) ON DELETE RESTRICT,
  created_at       timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT staff_notes_body_ck CHECK (char_length(btrim(body)) >= 1 AND char_length(body) <= 2000),
  CONSTRAINT staff_notes_supersedes_uq UNIQUE (supersedes_id),
  CONSTRAINT staff_notes_not_self_ck CHECK (supersedes_id IS NULL OR supersedes_id <> id)
);
```

#### 4.6.21 facility_reference_ranges
```sql
CREATE TABLE facility_reference_ranges (
  id               uuid             PRIMARY KEY DEFAULT gen_random_uuid(),
  facility_id      uuid             NOT NULL REFERENCES facilities (id) ON DELETE RESTRICT,
  feature_key      text             NOT NULL,
  sex              text             NULL,
  low              double precision NOT NULL,
  high             double precision NOT NULL,
  method           text             NOT NULL,
  n_residents      integer          NOT NULL,
  computed_at      timestamptz      NOT NULL,
  pipeline_run_id  uuid             NOT NULL REFERENCES pipeline_runs (id) ON DELETE RESTRICT,
  CONSTRAINT facility_reference_ranges_uq UNIQUE NULLS NOT DISTINCT (facility_id, feature_key, sex, pipeline_run_id),
  CONSTRAINT facility_reference_ranges_feature_ck CHECK (feature_key IN (
    'loudness_dbfs','total_phrase_duration_s','speech_rate_syl_per_s','articulation_rate_syl_per_s',
    'number_of_pauses','pause_fraction','voiced_fraction','mean_f0_hz','f0_variability_st',
    'jitter_local_pct','shimmer_local_pct','hnr_db','cpps_db','alpha_ratio_db','hammarberg_index_db',
    'mfcc1','mfcc2','mfcc3','mfcc4')),
  CONSTRAINT facility_reference_ranges_sex_ck CHECK (sex IS NULL OR sex IN ('F', 'M')),
  CONSTRAINT facility_reference_ranges_bounds_ck CHECK (low <= high),
  CONSTRAINT facility_reference_ranges_n_ck CHECK (n_residents >= 1),
  CONSTRAINT facility_reference_ranges_method_ck CHECK (char_length(method) BETWEEN 1 AND 200)
);
```

#### 4.6.22 config_parameters
```sql
CREATE TABLE config_parameters (
  profile      text        NOT NULL,
  key          text        NOT NULL,
  value        jsonb       NOT NULL,
  description  text        NOT NULL DEFAULT '',
  updated_by   uuid        NULL REFERENCES users (id) ON DELETE RESTRICT,
  updated_at   timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT config_parameters_pk PRIMARY KEY (profile, key),
  CONSTRAINT config_parameters_profile_ck CHECK (profile IN ('production', 'test_v0_1')),
  CONSTRAINT config_parameters_key_ck CHECK (key ~ '^[a-z][a-z0-9_]{0,63}$')
);
```

#### 4.6.23 audit_logs
```sql
CREATE TABLE audit_logs (
  id           bigserial   PRIMARY KEY,
  occurred_at  timestamptz NOT NULL DEFAULT now(),
  actor_type   actor_type  NOT NULL,
  actor_id     text        NULL,
  action       text        NOT NULL,
  entity_type  text        NULL,
  entity_id    text        NULL,
  details      jsonb       NOT NULL DEFAULT '{}'::jsonb,
  ip           inet        NULL,
  request_id   text        NULL,
  CONSTRAINT audit_logs_action_ck CHECK (action ~ '^[a-z_]+\.[a-z_]+$'),
  CONSTRAINT audit_logs_details_ck CHECK (jsonb_typeof(details) = 'object'),
  CONSTRAINT audit_logs_actor_ck CHECK (actor_type = 'system' OR actor_id IS NOT NULL)
);
```

#### 4.6.24 evaluation_ground_truth (test_v0_1 only; never read by the pipeline)
```sql
CREATE TABLE evaluation_ground_truth (
  id               uuid        PRIMARY KEY DEFAULT gen_random_uuid(),
  resident_code    text        NOT NULL,
  planted_change   text        NOT NULL,
  true_onset_date  date        NULL,
  source_file      text        NOT NULL,
  created_at       timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT evaluation_ground_truth_resident_code_uq UNIQUE (resident_code),
  CONSTRAINT evaluation_ground_truth_onset_ck CHECK ((planted_change = 'None') = (true_onset_date IS NULL)),
  CONSTRAINT evaluation_ground_truth_text_ck CHECK (
    char_length(planted_change) BETWEEN 1 AND 60 AND char_length(source_file) BETWEEN 1 AND 200)
);
```

### 4.7 Indexes

The query each index serves is listed in TRD 06 section 4.7.

```sql
-- (UNIQUE constraints above already create indexes; listed here are the additional ones.)
CREATE INDEX residents_facility_idx            ON residents (facility_id);
CREATE INDEX residents_status_cohort_idx       ON residents (status, cohort);
CREATE INDEX devices_facility_idx              ON devices (facility_id);
CREATE INDEX device_assignments_device_idx     ON device_assignments (device_id, valid_from);
CREATE INDEX device_assignments_resident_idx   ON device_assignments (resident_id, valid_from);
CREATE INDEX api_keys_device_idx               ON api_keys (device_id);
CREATE INDEX ingest_batches_received_idx       ON ingest_batches (received_at DESC);
CREATE INDEX ingest_batches_uploaded_by_idx    ON ingest_batches (uploaded_by);
CREATE INDEX ingest_batches_api_key_idx        ON ingest_batches (api_key_id);
CREATE INDEX ingest_rejections_batch_idx       ON ingest_rejections (ingest_batch_id);
CREATE INDEX ingest_rejections_received_idx    ON ingest_rejections (received_at DESC);
CREATE INDEX ingest_rejections_api_key_idx     ON ingest_rejections (api_key_id);
CREATE INDEX raw_sessions_session_id_idx       ON raw_sessions (session_id, arrival_seq);
CREATE INDEX raw_sessions_resident_ts_idx      ON raw_sessions (resident_id, timestamp_utc, arrival_seq);
CREATE INDEX raw_sessions_device_ts_idx        ON raw_sessions (device_id, timestamp_utc DESC);
CREATE INDEX raw_sessions_batch_idx            ON raw_sessions (ingest_batch_id);
CREATE INDEX raw_sessions_api_key_idx          ON raw_sessions (api_key_id);
CREATE INDEX pipeline_runs_started_idx         ON pipeline_runs (started_at DESC);
CREATE INDEX pipeline_runs_status_idx          ON pipeline_runs (status) WHERE status = 'running';
CREATE UNIQUE INDEX epochs_current_uq          ON epochs (resident_id) WHERE ended_at IS NULL;
CREATE INDEX epochs_device_idx                 ON epochs (device_id);
CREATE INDEX epochs_run_idx                    ON epochs (pipeline_run_id);
CREATE INDEX processed_sessions_resident_date_idx ON processed_sessions (resident_id, local_date) INCLUDE (status);
CREATE INDEX processed_sessions_resident_ts_idx   ON processed_sessions (resident_id, timestamp_utc DESC)
  WHERE status <> 'duplicate';
CREATE INDEX processed_sessions_epoch_idx      ON processed_sessions (epoch_id, timestamp_utc);
CREATE INDEX processed_sessions_session_id_idx ON processed_sessions (session_id);
CREATE INDEX processed_sessions_run_idx        ON processed_sessions (pipeline_run_id);
CREATE INDEX day_ledger_missing_idx            ON day_ledger (resident_id, local_date) WHERE status <> 'checked_in';
CREATE INDEX day_ledger_device_date_idx        ON day_ledger (device_id, local_date);
CREATE INDEX day_ledger_run_idx                ON day_ledger (pipeline_run_id);
CREATE INDEX baselines_resident_idx            ON baselines (resident_id);
CREATE INDEX baselines_run_idx                 ON baselines (pipeline_run_id);
CREATE INDEX scores_resident_date_idx          ON scores (resident_id, local_date);
CREATE INDEX scores_epoch_date_idx             ON scores (epoch_id, local_date);
CREATE INDEX scores_run_idx                    ON scores (pipeline_run_id);
CREATE INDEX cusum_state_resident_idx          ON cusum_state (resident_id);
CREATE INDEX cusum_state_run_idx               ON cusum_state (pipeline_run_id);
CREATE UNIQUE INDEX alerts_one_active_per_epoch_uq ON alerts (epoch_id) WHERE status <> 'closed';
CREATE INDEX alerts_status_triggered_idx       ON alerts (status, triggered_at DESC);
CREATE INDEX alerts_resident_triggered_idx     ON alerts (resident_id, triggered_at DESC);
CREATE INDEX alerts_acknowledged_by_idx        ON alerts (acknowledged_by);
CREATE INDEX alerts_run_idx                    ON alerts (pipeline_run_id);
CREATE INDEX alerts_snoozed_by_idx             ON alerts (snoozed_by);
CREATE INDEX alert_reviews_alert_created_idx   ON alert_reviews (alert_id, created_at DESC);
CREATE INDEX alert_reviews_reviewer_idx        ON alert_reviews (reviewer_user_id);
CREATE INDEX alert_reviews_outcome_idx         ON alert_reviews (outcome);
CREATE UNIQUE INDEX data_alerts_open_subject_uq ON data_alerts (kind, resident_id, device_id) NULLS NOT DISTINCT
  WHERE status = 'open' AND kind <> 'review_flagged_data_problem';
CREATE INDEX data_alerts_status_detected_idx   ON data_alerts (status, last_detected_at DESC);
CREATE INDEX data_alerts_resident_idx          ON data_alerts (resident_id);
CREATE INDEX data_alerts_device_idx            ON data_alerts (device_id);
CREATE INDEX data_alerts_run_idx               ON data_alerts (pipeline_run_id);
CREATE INDEX staff_notes_resident_created_idx  ON staff_notes (resident_id, created_at DESC);
CREATE INDEX staff_notes_alert_idx             ON staff_notes (alert_id);
CREATE INDEX staff_notes_author_idx            ON staff_notes (author_user_id);
CREATE INDEX facility_reference_ranges_lookup_idx ON facility_reference_ranges (facility_id, feature_key, computed_at DESC);
CREATE INDEX facility_reference_ranges_run_idx ON facility_reference_ranges (pipeline_run_id);
CREATE INDEX config_parameters_updated_by_idx  ON config_parameters (updated_by);
CREATE INDEX audit_logs_occurred_idx           ON audit_logs (occurred_at DESC);
CREATE INDEX audit_logs_entity_idx             ON audit_logs (entity_type, entity_id);
CREATE INDEX audit_logs_actor_idx              ON audit_logs (actor_type, actor_id, occurred_at DESC);
CREATE INDEX audit_logs_action_idx             ON audit_logs (action, occurred_at DESC);
```

### 4.8 Triggers and grants

```sql
CREATE TRIGGER raw_sessions_no_update_delete BEFORE UPDATE OR DELETE ON raw_sessions
  FOR EACH ROW EXECUTE FUNCTION reject_mutation();
CREATE TRIGGER raw_sessions_no_truncate BEFORE TRUNCATE ON raw_sessions
  FOR EACH STATEMENT EXECUTE FUNCTION reject_mutation();
CREATE TRIGGER audit_logs_no_update_delete BEFORE UPDATE OR DELETE ON audit_logs
  FOR EACH ROW EXECUTE FUNCTION reject_mutation();
CREATE TRIGGER audit_logs_no_truncate BEFORE TRUNCATE ON audit_logs
  FOR EACH STATEMENT EXECUTE FUNCTION reject_mutation();

CREATE TRIGGER facilities_set_updated_at         BEFORE UPDATE ON facilities         FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER users_set_updated_at              BEFORE UPDATE ON users              FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER residents_set_updated_at          BEFORE UPDATE ON residents          FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER devices_set_updated_at            BEFORE UPDATE ON devices            FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER device_assignments_set_updated_at BEFORE UPDATE ON device_assignments FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER api_keys_set_updated_at           BEFORE UPDATE ON api_keys           FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER ingest_batches_set_updated_at     BEFORE UPDATE ON ingest_batches     FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER pipeline_runs_set_updated_at      BEFORE UPDATE ON pipeline_runs      FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER epochs_set_updated_at             BEFORE UPDATE ON epochs             FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER cusum_state_set_updated_at        BEFORE UPDATE ON cusum_state        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER alerts_set_updated_at             BEFORE UPDATE ON alerts             FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER data_alerts_set_updated_at        BEFORE UPDATE ON data_alerts        FOR EACH ROW EXECUTE FUNCTION set_updated_at();
CREATE TRIGGER config_parameters_set_updated_at  BEFORE UPDATE ON config_parameters  FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```

```sql
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO echowell_app, echowell_readonly;
GRANT USAGE, CREATE ON SCHEMA public TO echowell_migrator;

-- echowell_app: append-only tables (INSERT + SELECT only)
GRANT SELECT, INSERT ON raw_sessions, audit_logs, ingest_rejections, staff_notes, baselines, alert_reviews TO echowell_app;
-- echowell_app: master/config tables and tables whose rows carry human state (no DELETE)
GRANT SELECT, INSERT, UPDATE ON facilities, residents, devices, device_assignments, users, api_keys,
  ingest_batches, pipeline_runs, config_parameters, alerts, data_alerts TO echowell_app;
-- echowell_app: rebuildable derived tables
GRANT SELECT, INSERT, UPDATE, DELETE ON epochs, processed_sessions, day_ledger, scores, cusum_state,
  facility_reference_ranges TO echowell_app;
GRANT USAGE, SELECT ON SEQUENCE raw_sessions_arrival_seq_seq, audit_logs_id_seq TO echowell_app;
-- echowell_app: NO privilege on evaluation_ground_truth (the pipeline never reads the answer key, SRC-02; contract R20)

-- echowell_readonly: everything except credential columns (incl. evaluation_ground_truth, which holds rows only in test_v0_1)
GRANT SELECT ON facilities, residents, devices, device_assignments, ingest_batches, ingest_rejections,
  raw_sessions, epochs, processed_sessions, day_ledger, baselines, scores, cusum_state, alerts, alert_reviews,
  data_alerts, staff_notes, facility_reference_ranges, pipeline_runs, config_parameters, audit_logs,
  evaluation_ground_truth TO echowell_readonly;
GRANT SELECT (id, email, display_name, role, active, last_login_at, created_at, updated_at) ON users TO echowell_readonly;
GRANT SELECT (id, name, scopes, device_id, active, created_at, updated_at, last_used_at) ON api_keys TO echowell_readonly;
```

Privilege matrix (summary of the grants above):

| Table group | echowell_app | echowell_readonly | echowell_migrator |
|---|---|---|---|
| raw_sessions, audit_logs (trigger-protected) | SELECT, INSERT | SELECT | owner (DELETE/TRUNCATE only via purge path, PGS-019) |
| ingest_rejections, staff_notes, baselines, alert_reviews (append-only by grant) | SELECT, INSERT | SELECT | owner |
| facilities, residents, devices, device_assignments, ingest_batches, pipeline_runs, config_parameters, alerts, data_alerts | SELECT, INSERT, UPDATE | SELECT | owner |
| users, api_keys | SELECT, INSERT, UPDATE | SELECT on non-credential columns only | owner |
| epochs, processed_sessions, day_ledger, scores, cusum_state, facility_reference_ranges | SELECT, INSERT, UPDATE, DELETE | SELECT | owner |
| evaluation_ground_truth | none (read only through `DATABASE_READONLY_URL`, PGS-040) | SELECT | owner |

### 4.9 Naming conventions

| Object | Pattern | Example |
|---|---|---|
| Table | snake_case plural noun (exceptions fixed by contract: `day_ledger`, `cusum_state`) | `processed_sessions` |
| Column | snake_case; FK = `<referenced singular>_id`; booleans as adjectives/`is_`; dates `_on`/`local_date`; instants `_at` | `resident_id`, `is_morning`, `enrolled_on`, `frozen_at` |
| Business keys from devices | kept as received in text columns: `session_id`, `resident_code`, `device_code` | `R01-20261001-01` |
| Primary key | `<table>_pkey` (PostgreSQL default) or explicit `<table>_pk` | `config_parameters_pk` |
| Unique | `<table>_<cols>_uq` | `day_ledger_resident_date_uq` |
| Check | `<table>_<topic>_ck` | `processed_sessions_status_reason_ck` |
| Exclusion | `<table>_<topic>_ex` | `device_assignments_no_overlap_ex` |
| Foreign key | `<table>_<column>_fkey` (PostgreSQL default) | `scores_processed_session_id_fkey` |
| Index | `<table>_<cols or purpose>_idx`; unique index `_uq` | `scores_epoch_date_idx` |
| Trigger | `<table>_<purpose>` | `raw_sessions_no_update_delete` |
| Enum type | singular snake_case noun | `session_status` |

### 4.10 Columns and tables added beyond the contract section 9 key-column list

The contract lists key columns; the following columns were added in this TRD set (identical in TRD 06, 20 and 23):

| Table | Added column(s) | Reason |
|---|---|---|
| all mutable tables | `created_at`, `updated_at` | contract §9 rule "created_at/updated_at on mutable tables" |
| facilities | `created_at`, `updated_at` only | — |
| api_keys | `updated_at` | mutable (active, last_used_at) |
| ingest_batches | `duplicate_count`, `api_key_id`, `created_at`, `updated_at` | `POST /api/v1/ingest` returns `duplicates`; provenance of key-authenticated batches |
| ingest_rejections | `api_key_id`, `row_number` | provenance of single-record rejections; CSV row number for the batch report |
| raw_sessions | `resident_id uuid`, `device_id uuid` (resolved FKs), `resident_code`, `device_code` (typed copies of the ingest fields `resident_id`, `device_id`), `api_key_id`, `ingest_warnings` (jsonb array, TRD 10 §4.4) | in the database `resident_id`/`device_id` are UUID FKs; the received study codes are kept verbatim in `*_code` and in `payload` |
| pipeline_runs | `as_of`, `error_message`, `created_at`, `updated_at` | reproducible ledger end date (test as-of 2026-10-30 15:00 America/Chicago); failure detail |
| epochs, day_ledger, baselines, scores, cusum_state, alerts | `pipeline_run_id` | every derived row names the run that wrote it |
| processed_sessions | `timestamp_utc`, `created_at` | ordering and "last check-in" without joining raw_sessions |
| alerts | `closed_at`, `created_at`, `updated_at`, `pipeline_run_id`; closed_reason value `superseded by rebuild` (contract §19 adds `snoozed_until`, `snoozed_by`) | alert lifecycle (TRD 23 §4.3) |
| data_alerts (contract §19 table) | `alert_review_id`, `resolved_at`, `created_at`, `updated_at`; `pipeline_run_id` nullable (NULL for `review_flagged_data_problem`) | link to the review that flagged a data problem; resolution time |
| alert_reviews (contract §19 table) | none beyond contract | — |
| evaluation_ground_truth (contract §19 table) | `id`, `created_at` | surrogate key |
| facility_reference_ranges | `sex` | sex-specific F0 ranges (OQ-08, OQ-20) |
| epochs, baselines, scores, day_ledger, staff_notes | `created_at` | insertion time |

No table beyond contract sections 9, 19 and 20 was added.

### 4.11 Seed: config_parameters (migration 0002)

Values are exactly contract section 7 plus the five keys of contract sections 19/20 (R17) plus the two ingest keys `supported_schema_versions` and `feature_name_map` (TRD 10; 23 keys per profile); the data-alert thresholds and
the explanation list are provisional (OQ-24, OQ-25). Numeric values are JSON numbers; `facility_tz` is a JSON string;
`morning_offsets` is a JSON object with all 19 feature keys. `production.baseline_n = 30` is the owner-confirmed
production value (D-OWNER-2); `test_v0_1` exists only for build-out and testing.

```sql
INSERT INTO config_parameters (profile, key, value, description)
SELECT p.profile, v.key, v.value, v.description
FROM (VALUES ('production'), ('test_v0_1')) AS p(profile)
CROSS JOIN (VALUES
  ('facility_tz',                 '"America/Chicago"'::jsonb, 'IANA time zone used for morning classification and the day ledger'),
  ('noise_limit_dbfs',            '-40.0'::jsonb,             'Set aside if mic_noise_level_dbfs is above this limit (dBFS)'),
  ('min_speech_s',                '1.0'::jsonb,               'Set aside if speech_duration_s is below this minimum (seconds)'),
  ('screen_min_n',                '5'::jsonb,                 'Prior usable sessions in the epoch required before the speaker screen runs'),
  ('screen_f0_z',                 '4.0'::jsonb,               'Speaker screen: |z| of mean_f0_hz at or above this value'),
  ('screen_other_z',              '3.0'::jsonb,               'Speaker screen: |z| threshold for the 7 composite features'),
  ('screen_other_count',          '2'::jsonb,                 'Speaker screen: minimum count of composite features at or above screen_other_z'),
  ('mad_scale',                   '1.4826'::jsonb,            'Robust spread = MAD x mad_scale'),
  ('pause_floor',                 '0.5'::jsonb,               'Spread floor for number_of_pauses'),
  ('composite_floor',             '0.1'::jsonb,               'Spread floor for the composite baseline'),
  ('cusum_k',                     '0.5'::jsonb,               'CUSUM reference value k'),
  ('cusum_h',                     '5.0'::jsonb,               'CUSUM alarm threshold h (UI alarm line 5.0)'),
  ('morning_cutoff_hour',         '12'::jsonb,                'Session is morning if its local hour is below this value'),
  ('morning_offsets',             '{"loudness_dbfs": -1.5, "total_phrase_duration_s": 0.10, "speech_rate_syl_per_s": -0.12, "articulation_rate_syl_per_s": -0.10, "number_of_pauses": 0, "pause_fraction": 0.010, "voiced_fraction": -0.020, "mean_f0_hz": 0, "f0_variability_st": 0, "jitter_local_pct": 0, "shimmer_local_pct": 0, "hnr_db": 0, "cpps_db": 0, "alpha_ratio_db": 0, "hammarberg_index_db": 0, "mfcc1": 0, "mfcc2": 0, "mfcc3": 0, "mfcc4": 0}'::jsonb,
                                                              'Configured morning offset per feature; adjusted = raw - offset for morning sessions (estimation deferred, OQ-09)'),
  ('shared_device_min_residents', '2'::jsonb,                 'Minimum residents on one device for the missing_device_gap rule')
) AS v(key, value, description);

INSERT INTO config_parameters (profile, key, value, description) VALUES
  ('production', 'baseline_n', '30'::jsonb, 'Usable sessions that form and freeze a baseline (owner decision D-OWNER-2)'),
  ('test_v0_1',  'baseline_n', '16'::jsonb, 'Build/test only: usable sessions that form and freeze a baseline in the 30-day test set (SRC-03)');

-- Alert review and data-alert parameters (contract sections 19/20; provisional, OQ-24, OQ-25)
INSERT INTO config_parameters (profile, key, value, description)
SELECT p.profile, v.key, v.value, v.description
FROM (VALUES ('production'), ('test_v0_1')) AS p(profile)
CROSS JOIN (VALUES
  ('data_alert_baseline_stalled_enabled', 'true'::jsonb, 'Raise baseline_stalled data alerts (forming and days since epoch start >= baseline_n)'),
  ('data_alert_set_aside_fraction',       '0.20'::jsonb, 'high_set_aside data alert when set_aside / received >= this in 30 days (received >= 10)'),
  ('data_alert_device_silent_days',       '2'::jsonb,    'Consecutive silent days on a single-resident device that raise a device_silent data alert'),
  ('alert_snooze_hours',                  '24'::jsonb,   'Hours added by "Remind me in 24 h" (alerts.snoozed_until)'),
  ('review_explanations',
   '[{"code": "cold_cough_sore_throat", "label": "Cold, cough or sore throat"}, {"code": "dental_dentures", "label": "Dental problem or dentures out"}, {"code": "medication_change", "label": "New or changed medication"}, {"code": "poor_sleep_unusual_day", "label": "Poor sleep or unusual day"}, {"code": "room_device_moved", "label": "Room or device moved"}]'::jsonb,
   'Checklist "Anything that could explain it?" on the alert review form (codes stored in alert_reviews.explanations)')
) AS v(key, value, description);

-- Ingest settings (lead decision 18 Oct 2026; read by the ingestion service, TRD 10 ING-013, ING-016)
INSERT INTO config_parameters (profile, key, value, description)
SELECT p.profile, v.key, v.value, v.description
FROM (VALUES ('production'), ('test_v0_1')) AS p(profile)
CROSS JOIN (VALUES
  ('supported_schema_versions', '["0.1"]'::jsonb, 'Accepted values of schema_version; others are rejected (unsupported_schema_version)'),
  ('feature_name_map',
   '{"schema_version": "schema_version", "session_id": "session_id", "resident_id": "resident_id", "device_id": "device_id", "timestamp_utc": "timestamp_utc", "mic_noise_level_dbfs": "mic_noise_level_dbfs", "audio_quality_flag": "audio_quality_flag", "extraction_software_version": "extraction_software_version", "device_firmware_version": "device_firmware_version", "speech_duration_s": "speech_duration_s", "phrase_id": "phrase_id", "loudness_dbfs": "loudness_dbfs", "total_phrase_duration_s": "total_phrase_duration_s", "speech_rate_syl_per_s": "speech_rate_syl_per_s", "articulation_rate_syl_per_s": "articulation_rate_syl_per_s", "number_of_pauses": "number_of_pauses", "pause_fraction": "pause_fraction", "voiced_fraction": "voiced_fraction", "mean_f0_hz": "mean_f0_hz", "f0_variability_st": "f0_variability_st", "jitter_local_pct": "jitter_local_pct", "shimmer_local_pct": "shimmer_local_pct", "hnr_db": "hnr_db", "cpps_db": "cpps_db", "alpha_ratio_db": "alpha_ratio_db", "hammarberg_index_db": "hammarberg_index_db", "mfcc1": "mfcc1", "mfcc2": "mfcc2", "mfcc3": "mfcc3", "mfcc4": "mfcc4"}'::jsonb,
   'External field name -> canonical name (identity for the 11 record fields and 19 features of schema 0.1; OQ-03)')
) AS v(key, value, description);
```

### 4.12 Seed: synthetic test roster (test_v0_1, non-production only)

Applied by `python -m backend.cli seed test_v0_1` (PGS-026) as role `echowell_migrator`. The test facility is named "Edgewood"
(`meta.facility_name` is read from `facilities.name`; `DATA_SOURCE_LABEL` marks the data as test data). The answer-key facts for the
Analytics "Alarm timing check" (SRC-19) are NOT part of this seed: they are loaded from the CSV fixture
`tests/fixtures/answer_key/evaluation_ground_truth_v0_1.csv` (TRD 14 DS-10) by running
`python database/seeds/load_evaluation_ground_truth.py <csv_path>` directly (refuses when APP_ENV=production or PIPELINE_PROFILE is not
`test_v0_1`); the seed CLI does not call it and `backend/cli.py` never references `evaluation_ground_truth`. Sex values are from SRC-04
`RESIDENTS`. Device D07 is inactive after R07 moved to D07B on 2026-10-13. Users and the ingest API key are not
seeded by SQL: the CLI creates `admin@echowell.test`, `clinician@echowell.test` and `researcher@echowell.test` and one
API key named `test-ingest`, generating random secrets that are printed once to the terminal and stored only as
argon2id / SHA-256 hashes (TRD 12). The CLI then ingests SRC-05 as an `ingest_batches` row with `source = 'seed'`.

```sql
BEGIN;
INSERT INTO facilities (name, timezone) VALUES ('Edgewood', 'America/Chicago');

INSERT INTO residents (facility_id, resident_code, sex, cohort, enrolled_on, status)
SELECT f.id, r.code, r.sex, 'longitudinal', DATE '2026-10-01', 'active'
FROM facilities f
CROSS JOIN (VALUES ('R01','F'), ('R02','M'), ('R03','F'), ('R04','M'), ('R05','F'),
                   ('R06','M'), ('R07','F'), ('R08','M'), ('R09','F'), ('R10','M')) AS r(code, sex)
WHERE f.name = 'Edgewood';

INSERT INTO devices (facility_id, device_code, firmware_version_last, active)
SELECT f.id, d.code, 'fw-1.0.0', d.active
FROM facilities f
CROSS JOIN (VALUES ('D01', true), ('D02', true), ('D04', true), ('D05', true), ('D06', true),
                   ('D07', false), ('D07B', true), ('D08', true), ('D09', true), ('D10', true)) AS d(code, active)
WHERE f.name = 'Edgewood';

INSERT INTO device_assignments (resident_id, device_id, valid_from, valid_to)
SELECT r.id, d.id, a.valid_from, a.valid_to
FROM (VALUES
  ('R01', 'D01',  DATE '2026-10-01', NULL::date),
  ('R02', 'D02',  DATE '2026-10-01', NULL),
  ('R03', 'D02',  DATE '2026-10-01', NULL),
  ('R04', 'D04',  DATE '2026-10-01', NULL),
  ('R05', 'D05',  DATE '2026-10-01', NULL),
  ('R06', 'D06',  DATE '2026-10-01', NULL),
  ('R07', 'D07',  DATE '2026-10-01', DATE '2026-10-12'),
  ('R07', 'D07B', DATE '2026-10-13', NULL),
  ('R08', 'D08',  DATE '2026-10-01', NULL),
  ('R09', 'D09',  DATE '2026-10-01', NULL),
  ('R10', 'D10',  DATE '2026-10-01', NULL)
) AS a(resident_code, device_code, valid_from, valid_to)
JOIN residents r ON r.resident_code = a.resident_code
JOIN devices   d ON d.device_code   = a.device_code;
COMMIT;

-- Equivalent rows, for reference only: the canonical source is the CSV fixture loaded by
-- database/seeds/load_evaluation_ground_truth.py (test_v0_1 only, never read by the pipeline); do not execute this block.
BEGIN;
INSERT INTO evaluation_ground_truth (resident_code, planted_change, true_onset_date, source_file) VALUES
  ('R01', 'None', NULL, 'EchoWell_pipeline_test_v0_1.xlsx'),
  ('R02', 'None', NULL, 'EchoWell_pipeline_test_v0_1.xlsx'),
  ('R03', 'None', NULL, 'EchoWell_pipeline_test_v0_1.xlsx'),
  ('R04', 'None', NULL, 'EchoWell_pipeline_test_v0_1.xlsx'),
  ('R05', 'None', NULL, 'EchoWell_pipeline_test_v0_1.xlsx'),
  ('R06', 'None', NULL, 'EchoWell_pipeline_test_v0_1.xlsx'),
  ('R07', 'None', NULL, 'EchoWell_pipeline_test_v0_1.xlsx'),
  ('R08', 'None', NULL, 'EchoWell_pipeline_test_v0_1.xlsx'),
  ('R09', 'Sudden step', DATE '2026-10-21', 'EchoWell_pipeline_test_v0_1.xlsx'),
  ('R10', 'Slow drift',  DATE '2026-10-17', 'EchoWell_pipeline_test_v0_1.xlsx');
COMMIT;
```

## 5. Assumptions

- ASM-01 Facility time zone America/Chicago (default of `facilities.timezone` and `config_parameters.facility_tz`).
- ASM-02 At most one session per resident per local day in v0.1; the schema does not enforce it (a second session on the
  same day is stored and processed; `day_ledger` still has one row).
- ASM-03 Single facility in the MVP; every resident and device carries `facility_id` so more facilities need no migration.
- ASM-08 Fewer than 100 residents, fewer than 25 users, at most one session per resident per day.
- Note for lead (TRD-local): the managed PostgreSQL service permits `CREATE ROLE` and `CREATE EXTENSION btree_gist`
  for the project owner role (true for Neon, Railway PostgreSQL and RDS PostgreSQL 16).

## 6. Dependencies

- PostgreSQL 16 server (local docker image `postgres:16`; Neon; Railway; target AWS RDS PostgreSQL 16).
- Alembic 1.13.x, SQLAlchemy 2.0.x, psycopg 3.x (TRD 05, TRD 06).
- `pg_dump` 16 client in CI for PGS-016/PGS-017.
- TRD 10 for the validation that guarantees inserts into `raw_sessions` satisfy these constraints.
- TRD 21 for `DATABASE_URL` (app role), `DATABASE_MIGRATION_URL` (migrator role), `DATABASE_READONLY_URL` (readonly role, R27) and `APP_ENV`.

## 7. Acceptance Criteria

Executed by `tests/integration/test_schema_behaviour.py` against a database migrated to head (connected as
`echowell_app_login` unless stated):

1. AC-PGS-01: `UPDATE raw_sessions …` fails (SQLSTATE 42501 as `echowell_app`; SQLSTATE EW001 as table owner).
2. AC-PGS-02: `DELETE FROM raw_sessions` and `TRUNCATE raw_sessions` fail for `echowell_app` and for the owner without the purge setting.
3. AC-PGS-03: `UPDATE audit_logs …` and `DELETE FROM audit_logs` fail for `echowell_app`.
4. AC-PGS-04: inserting a `set_aside` row with reasons `{quality flag poor, noise above limit}` and reason_text `quality flag poor; noise above limit` succeeds; changing reason_text to `noise above limit` fails with SQLSTATE 23514.
5. AC-PGS-05: a `quarantined` row with reason `possible other speaker (F0 z=5.12; composite features with |z|>=3: 3)` and non-null screen_detail succeeds; the same row with screen_detail NULL fails.
6. AC-PGS-06: a `duplicate` row with a non-null `epoch_id` fails.
7. AC-PGS-07: a `missing_resident` ledger row with reason `no record` fails; a `missing_device_gap` row for R02 on 2026-10-12 with device D02 and reason `all residents on shared device D02 have no record` succeeds.
8. AC-PGS-08: after the roster seed, inserting an R07 assignment to D09 from 2026-10-20 fails with SQLSTATE 23P01, while R02 and R03 both hold open assignments to D02.
9. AC-PGS-09: as `echowell_migrator` with `SET echowell.allow_purge = 'on'`, `DELETE FROM audit_logs` succeeds and `UPDATE raw_sessions` still fails.
10. AC-PGS-10: `config_parameters` holds 23 rows per profile; `baseline_n` is 30 (production) and 16 (test_v0_1); `morning_offsets` has 19 keys with `loudness_dbfs = -1.5`.
11. AC-PGS-11: the schema diff test (PGS-016) and `alembic check` pass on a clean database.
12. AC-PGS-12: `echowell_readonly_login` gets SQLSTATE 42501 on `SELECT password_hash FROM users` and succeeds on `SELECT email FROM users`.
13. AC-PGS-13: `pg_constraint` shows every FK with `confdeltype = 'r'` except `scores_processed_session_id_fkey` with `'c'`.
14. AC-PGS-14: as `echowell_app_login`, `SELECT count(*) FROM evaluation_ground_truth` and `SET ROLE echowell_readonly` both fail with 42501; as `echowell_readonly_login` the SELECT returns 10 (test seed).
15. AC-PGS-15: inserting a second `open` `device_silent` data alert for D02 fails with 23505; a `device_silent` row without `pipeline_run_id` fails with 23514; `DELETE FROM alerts` as `echowell_app` fails with 42501.

## 8. Implementation Notes

- Migration layout: `backend/alembic/versions/0001_initial_schema.py` (sections 4.2–4.8 except role creation, which is
  provisioning), `0002_seed_config_parameters.py` (section 4.11). Use `op.execute()` with the SQL of this document for
  enum types, trigger functions, triggers, exclusion constraint, partial/INCLUDE indexes and grants; use
  `op.create_table` only if the generated SQL is identical. Downgrade of 0001 drops everything in reverse order.
- SQLAlchemy: use `postgresql.ENUM(..., name='session_status', create_type=False)` so models never try to create types;
  declare `CheckConstraint(..., name='processed_sessions_status_reason_ck')` etc. with the exact names; map
  `double precision` to `sqlalchemy.Double` (float64), never `Numeric`, so values compare with absolute tolerance 1e-6
  against SRC-03.
- `raw_sessions.arrival_seq` is `bigserial`; never insert it explicitly. Duplicate detection orders by `arrival_seq`.
- The column `pipeline_runs.trigger` is a non-reserved keyword; quote nothing, it works in PostgreSQL 16 and SQLAlchemy.
- The local_date CHECK uses `timestamp_utc AT TIME ZONE 'UTC'`, an immutable expression; do not replace it with
  `now()` or a facility time-zone lookup.
- Convert pipeline floats with `float(numpy.float64)` before binding; psycopg 3 does not adapt numpy scalars.
- `UNIQUE NULLS NOT DISTINCT` (facility_reference_ranges) requires PostgreSQL ≥ 15; do not lower the server version.
- Test isolation: integration tests create a fresh database per session from the migrations; never truncate
  `raw_sessions` in tests except through the purge path (PGS-019).
- Pitfall: Neon pooled connection strings (`-pooler` host) use PgBouncer transaction mode; Alembic and the advisory locks
  of TRD 06 DB-021 must use the direct (non-pooled) host.

## 9. Open Questions

- OQ-01 Retention: no deletion jobs or partitioning are defined; the purge path exists only for IRB-directed actions.
- OQ-03 Final feature column names: renaming means a migration that renames 19 columns in `raw_sessions` and keys in
  JSON columns; the ingest feature-name mapping (TRD 10) avoids it for input names.
- OQ-08 / OQ-20 Facility norm statistic and sex availability (shape of `facility_reference_ranges`).
- OQ-10 Late records before a frozen baseline.
- OQ-11 Data handling on withdrawal.
- OQ-13 Alarm-limit calibration (values of `cusum_h`, `cusum_k` may change through `config_parameters`, not DDL).
- OQ-23 (closed by D-OWNER-4 / D-28): live PHI-derived feature data is never stored on the interim Neon/Railway stack.
- OQ-24 Data-alert thresholds (`data_alert_*` keys) confirmation by the study team.
- OQ-25 Explanation checklist (`review_explanations`) confirmation by the clinical team.
- OQ-26 Who may review alarms and how soon (affects `alert_reviews` writers, not schema).

## Revision History

| Version | Date | Change | Author |
|---|---|---|---|
| 0.1 | 18 Oct 2026 | Initial generation from TRD_Generation_Prompt.md | — |
| 0.1 | 18 Oct 2026 | Cross-TRD consistency review | — |
