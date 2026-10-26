# FEAT-009 Master data, identity and configuration tables (incl. config seed migration 0002)

| Field | Value |
|---|---|
| Epic | Database |
| Build phase | Phase 4 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-008 |
| Status | Complete |

## Purpose

Create the reference tables every other table points to (`facilities`, `users`, `residents`, `devices`, `device_assignments`, `api_keys`, `config_parameters`) with their constraints, triggers, grants, SQLAlchemy models, Python enums usage and repositories, and seed the 46 pipeline parameter rows (23 keys × profiles `production` and `test_v0_1`) through migration `0002_seed_config_parameters`. These tables hold study IDs only, never personal data.

## Business Context

- BR-16: residents identified only by study IDs; no names, contact details or audio (SEC-120, SEC-122, DME-020); staff users hold only email, display name, role and login metadata (SEC-125).
- BR-06 and BR-08: device assignments express shared devices and device moves, with no overlapping assignments per resident (PGS-015).
- BR-09 and BR-11: pipeline parameters live in `config_parameters` per profile; production `baseline_n` is 30 and `test_v0_1` is 16 (PGS-025, D-01, FR-229).
- FR-227: master data is managed by seed files and CLI only, never HTTP.

## Referenced TRDs

- TRD 20 PGS-006, PGS-015, PGS-024, PGS-025, PGS-034, PGS-035, PGS-037; §4.6.1–§4.6.6 and §4.6.22 DDL; §4.8 triggers and grants (rows for these tables); §4.11 seed SQL; AC-PGS-08, AC-PGS-10, AC-PGS-12.
- TRD 06 DB-055.
- TRD 23 DME-001, DME-003, DME-004, DME-008, DME-009, DME-020; §4.2.1–§4.2.6, §4.2.22 entity definitions; §4.6 model mapping.
- TRD 12 SEC-120, SEC-122, SEC-123, SEC-125.
- TRD 02 FR-227, FR-229.
- TRD 13 TST-041, TST-042, CFG-01, CFG-02, CFG-05.
- TRD 01 ARC-105 (one `facilities` row, Edgewood, referenced by every resident and device).

## Scope

- Migration 0001 sections (continuing FEAT-008) for tables `facilities`, `users`, `residents`, `devices`, `device_assignments` (with exclusion constraint `device_assignments_no_overlap_ex`), `api_keys`, `config_parameters`, exactly as TRD 20 §4.6.1–§4.6.6 and §4.6.22, plus their `*_set_updated_at` triggers and the §4.8 grants for these tables, issued in the same migration.
- Migration `backend/alembic/versions/0002_seed_config_parameters.py` inserting the §4.11 rows verbatim; its downgrade deletes exactly those rows.
- Models (TRD 23 §4.6): `facility.py:Facility`, `user.py:User`, `resident.py:Resident` (existing skeleton file kept), `device.py:Device` and `DeviceAssignment`, `api_key.py:ApiKey`, `config_parameter.py:ConfigParameter`, registered in `backend/models/__init__.py`.
- Repositories in `backend/repositories/` (one module per aggregate, API-005): facilities, users (get by lower-cased email, list, insert, update role/active/display name/last_login_at), residents (get by `resident_code`, list active, update status/withdrawn_on/cohort), devices and assignments (get by `device_code`, assignments by resident and date), api_keys (get active by `key_hash`, update `last_used_at`/`active`), config_parameters (load all keys of a profile, update value).

## Out of Scope

- Password hashing, API key generation and the credential CLI (FEAT-016).
- The roster CSVs, `import-master-data`, `withdraw-resident`, `seed` commands (FEAT-017) and the `set-config` command with its `config.changed` audit row (FEAT-055).
- The pipeline's `cohort` transition (DME-008) and the reading of `config_parameters` into `PipelineConfig` (FEAT-040, FEAT-053); only the column and repository method exist here.
- `/api/v1/users` endpoints (FEAT-037) and auth endpoints (FEAT-020).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-009-FR-01 | The seven tables shall be created with exactly the columns, types, nullability, defaults and named constraints of TRD 20 §4.6.1–§4.6.6 and §4.6.22. | PGS-006, DME-001 |
| FEAT-009-FR-02 | `device_assignments` shall reject overlapping inclusive date ranges for the same resident (`device_assignments_no_overlap_ex`, `daterange(valid_from, valid_to, '[]')`), while different residents may share a device in overlapping ranges. | PGS-015 |
| FEAT-009-FR-03 | `users.email` shall be lower-case and unique and `users.password_hash` shall start with `$argon2id$`. | PGS-034 |
| FEAT-009-FR-04 | `api_keys.key_hash` shall be 64 lower-case hex characters and unique; `scopes` a non-empty subset of `{ingest:write, pipeline:run}`. | PGS-035 |
| FEAT-009-FR-05 | `residents.status = 'withdrawn'` iff `withdrawn_on IS NOT NULL`; `withdrawn_on` not before `enrolled_on`; `admitted_on` not after `enrolled_on`. | PGS-037 |
| FEAT-009-FR-06 | Each table with `updated_at` shall have its `<table>_set_updated_at` trigger. | PGS-020 |
| FEAT-009-FR-07 | Grants: `echowell_app` SELECT, INSERT, UPDATE (no DELETE) on all seven tables; `echowell_readonly` SELECT on all except the credential columns `users.password_hash` and `api_keys.key_hash`, using the column lists of TRD 20 §4.8. | PGS-021, PGS-022 |
| FEAT-009-FR-08 | Migration 0002 shall insert the 46 rows of §4.11 (23 keys per profile) with the exact JSON values; `('production','baseline_n')` = 30 and `('test_v0_1','baseline_n')` = 16. | PGS-024, PGS-025, DB-055 |
| FEAT-009-FR-09 | Each table shall be one SQLAlchemy 2.0 declarative class in the TRD 23 §4.6 model file, with attributes, types and nullability of TRD 23 §4.2; models reuse the Python enums of `backend/models/__init__.py`. | DME-001, DME-003 |
| FEAT-009-FR-10 | No column for resident names, birth dates, room numbers tied to names, record numbers, photos, contact details or audio shall exist; resident attributes are limited to `sex`, `cohort`, enrolment/admission/withdrawal dates and `status`; `devices.room_label` is optional and non-identifying (1–60 characters). | SEC-120, SEC-122, SEC-123, DME-020 |
| FEAT-009-FR-11 | Users shall hold only email, display name, password hash, role, active flag and login metadata. | SEC-125 |
| FEAT-009-FR-12 | Repositories shall look residents and devices up by `resident_code`/`device_code` so that APIs never need or expose `residents.id` or `devices.id`. | DME-004 |
| FEAT-009-FR-13 | No HTTP endpoint shall create or modify facilities, residents, devices or assignments; these tables are written only by the seed and CLI features. | FR-227 |
| FEAT-009-FR-14 | `residents.status` changes only from `active` to `withdrawn` (CLI, FEAT-017), and `residents.cohort` only from `new_admission` to `longitudinal` (pipeline, FEAT-053); the repository exposes only these transitions. | DME-008, DME-009 |
| FEAT-009-FR-15 | `config_parameters` shall be changed only through the `set-config` operator command (delivered later); no endpoint writes it. | FR-229 |
| FEAT-009-FR-16 | The facility shall be modelled as a row in `facilities`; every resident and device shall reference it, and the MVP shall operate with exactly one facility (Edgewood). | ARC-105 |

## Inputs

- Migration framework, enums and `set_updated_at()` from FEAT-008.
- TRD 20 DDL and seed SQL.

## Outputs

- Seven tables with constraints, triggers and grants; 46 `config_parameters` rows.
- Model classes and repository modules for the seven tables.

## Data Flow

`alembic upgrade head` → 0001 creates the seven tables, triggers and grants as `echowell_migrator` → 0002 inserts the parameter rows → the app (as `echowell_app_login`) reads them through repositories: auth reads `users`/`api_keys`, the pipeline runner reads `config_parameters` for `PIPELINE_PROFILE`, read APIs resolve `resident_code`/`device_code`, the CLI (FEAT-016, FEAT-017) writes master data.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-008

- FEAT-008 provides the Alembic environment, the 0001 migration file, the enum types `resident_cohort`, `resident_status`, `user_role`, and the `set_updated_at()` function.

Features that build directly on this one (BACKLOG.md §4): FEAT-010, FEAT-023, FEAT-040.

## Database Impact

- Tables created: `facilities`, `users`, `residents`, `devices`, `device_assignments`, `api_keys`, `config_parameters`.
- Constraints: `facilities_name_uq`, `facilities_name_ck`, `facilities_timezone_ck`, `users_email_uq`, `users_email_lower_ck`, `users_email_format_ck`, `users_display_name_ck`, `users_password_hash_ck`, `residents_resident_code_uq`, `residents_resident_code_ck`, `residents_sex_ck`, `residents_withdrawn_ck`, `residents_withdrawn_after_enrol_ck`, `residents_admitted_ck`, `devices_device_code_uq`, `devices_device_code_ck`, `devices_room_label_ck`, `device_assignments_range_ck`, `device_assignments_no_overlap_ex`, `api_keys_key_hash_uq`, `api_keys_key_hash_ck`, `api_keys_name_ck`, `api_keys_scopes_ck`, `config_parameters_pk`, `config_parameters_profile_ck`, `config_parameters_key_ck`.
- Triggers: `facilities_set_updated_at`, `users_set_updated_at`, `residents_set_updated_at`, `devices_set_updated_at`, `device_assignments_set_updated_at`, `api_keys_set_updated_at`, `config_parameters_set_updated_at`.
- Rows inserted: 46 in `config_parameters` (0002).

## API Impact

None exposed. The tables back E-02..E-04 (auth), E-08..E-11, E-17, E-25..E-27 and E-32 delivered by later features.

## Frontend Impact

None.

## Analytics Impact

None computed. `config_parameters` supplies the parameter values (`baseline_n`, `cusum_h`, `cusum_k`, `morning_offsets`, thresholds) that `analytics.config.PipelineConfig` loads in FEAT-040.

## Security Requirements

- No DELETE grant for `echowell_app` on master or config tables (PGS-021); users and API keys are deactivated, never deleted.
- `echowell_readonly` cannot read `users.password_hash` or `api_keys.key_hash` (PGS-021, AC-PGS-12).
- Only hashes are stored for passwords and API keys (PGS-034, PGS-035).
- No PII columns (SEC-120, SEC-122, DME-020).

## Error Handling

| Failure | Behaviour | Trace |
|---|---|---|
| Overlapping assignment for one resident | Insert fails with SQLSTATE 23P01 | PGS-015, AC-PGS-08 |
| Duplicate `resident_code`, `device_code`, email or key hash | Insert fails with SQLSTATE 23505 | TST-042 |
| Constraint violation (bad code pattern, withdrawn without date, non-argon2id hash) | Insert/update fails with SQLSTATE 23514 | PGS-034, PGS-037 |
| DELETE by `echowell_app` | Fails with SQLSTATE 42501 | PGS-021 |

Repositories let these errors propagate; callers (CLI, services) translate them (FEAT-016, FEAT-017, FEAT-019).

## Logging Requirements

None directly; writes to these tables are audited by the CLI and endpoint features that perform them (FEAT-015, FEAT-016, FEAT-017).

## Testing Requirements

- Integration (`tests/integration/db/test_master_tables.py`, marker `integration`): TST-042 uniqueness of `residents.resident_code`; AC-PGS-08 (overlapping R07 assignment fails with 23P01, R02 and R03 share D02); PGS-034, PGS-035, PGS-037 CHECK cases; `updated_at` changes on update (PGS-020).
- Integration (`tests/integration/db/test_grants.py`): `has_table_privilege` and `has_column_privilege` for the seven tables (PGS-021, AC-PGS-12); part of TST-041.
- Integration (`tests/integration/db/test_config_seed.py`): AC-PGS-10 (23 rows per profile, `baseline_n` 30/16, `morning_offsets` 19 keys with `loudness_dbfs = -1.5`); DB-055 values including the five review/data-alert keys and the two ingest keys.
- Unit (`tests/unit/backend/repositories/`): repository queries with a mocked session (TRD 13 §4.2).
- Model introspection test: Python enums equal `pg_enum` labels (DME-003); `alembic check` no diff (DME-001).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-009-AC-01 | After `alembic upgrade head`, `SELECT profile, count(*) FROM config_parameters GROUP BY profile` returns 23 for `production` and 23 for `test_v0_1`; `baseline_n` is 30 and 16 respectively; `morning_offsets` has 19 keys with `loudness_dbfs = -1.5`. Verified by: Test (run the command in the criterion against the stated environment and check the stated result). | AC-PGS-10, PGS-024, PGS-025, DB-055 |
| FEAT-009-AC-02 | With R02 and R03 both holding open assignments to D02, the inserts succeed; inserting a second R07 assignment overlapping an existing one fails with SQLSTATE 23P01. Verified by: Integration (`tests/integration/db/test_master_tables.py`). | AC-PGS-08, PGS-015 |
| FEAT-009-AC-03 | Inserting a user with email `Admin@Example.com` or a password hash not starting with `$argon2id$` fails with SQLSTATE 23514; a second user with the same email fails with 23505. Verified by: Integration (`tests/integration/db/test_master_tables.py`). | PGS-034 |
| FEAT-009-AC-04 | Inserting an API key with a 63-character hash, an upper-case hash, empty scopes or scope `admin` fails with 23514. Verified by: Integration (`tests/integration/db/test_master_tables.py`). | PGS-035 |
| FEAT-009-AC-05 | Setting `status = 'withdrawn'` without `withdrawn_on` fails with 23514. Verified by: Integration (`tests/integration/db/test_master_tables.py`). | PGS-037 |
| FEAT-009-AC-06 | As `echowell_readonly_login`, `SELECT password_hash FROM users` fails with 42501 and `SELECT email FROM users` succeeds; as `echowell_app_login`, `DELETE FROM residents` fails with 42501. Verified by: Integration (`tests/integration/db/test_grants.py`). | AC-PGS-12, PGS-021 |
| FEAT-009-AC-07 | `alembic check` exits 0 and the Python enum labels equal the `pg_enum` labels. Verified by: Test (run the command in the criterion against the stated environment and check the stated result). | DME-001, DME-003 |
| FEAT-009-AC-08 | The column whitelist test finds no column named like name, birth, phone, address, email (outside `users.email`) or audio in the seven tables. Verified by: Inspection (the inspection method of DB-035, applied to the condition stated in the criterion). | DB-035, SEC-120, DME-020 |

## Definition of Done

- All FEAT-009 acceptance criteria pass; migrations upgrade and downgrade cleanly (TST-040).
- `database/schema.sql` regenerated (PGS-017); models and repositories have docstrings citing TRD IDs (NFR-085).
- Delivered in the Phase 4 checkpoint PR of Block 3 (AGT-013).

## Implementation Notes

- Write the DDL with `op.execute()` using the TRD 20 SQL verbatim, especially the exclusion constraint and array CHECKs (TRD 20 §8).
- `resident.py` is an existing skeleton file and must hold `Resident` (ARC-050, AGT-010).
- `resident_code` follows `^[A-Z0-9]{1,16}$` (TRD 20 §4.6.3, TRD 19 `ResidentCode`); TRD 23 §4.2.3 was aligned to the same pattern in the PR #2 consistency fixes.
- 0002 must not be edited to change parameters later; parameter changes go through `set-config` (FR-229, D-69) and the `test_v0_1` values are never changed to make a test pass (AGT-008).
