# Checkpoint 3 Report — Phase 9 Implement Database Layer

Block 3 "Implement Features", checkpoint 3 of 9, its own PR (branch `feat/cp3-database`, created from `main` at fa93306 after GitHub PR #4 was merged) · Prompt: `specs/prompts/Implement_Feature_Batches.md` "Phase 9: Implement Database Layer" · TRD 25 Phase 4 · Features: FEAT-008..FEAT-017 · Date: 26 October 2026 · Status: delivered as GitHub PR #17; review round 1 (algorithm lead, 27 Oct 2026) answered and applied, section 9; ready for re-review.

Build order followed `BACKLOG.md` §9: [FEAT-008] → [FEAT-009, FEAT-010, FEAT-011, FEAT-012] → [FEAT-013, FEAT-015, FEAT-016] → [FEAT-014, FEAT-017]. Reading order: TRD 25, 00, 24; Phase 9 prompt; roadmap §5.3; FEAT-008..FEAT-017; TRDs 20, 06, 12, 15, 21, 23, 13; `docs/design/Database_ERD.md` and `Backend_Architecture.md`.

The interim stack holds synthetic test data only; nothing here loads or expects real resident data.

## 1. What was built

The table-by-table account (models, repositories, grants, relationships, keys, indexes) is `docs/reports/DATABASE_IMPLEMENTATION_REPORT.md`. In short:

| Feature | Delivered |
|---|---|
| FEAT-008 | Migration `0001_initial_schema` with the TRD 20 §4.4–§4.8 SQL unchanged (extension check, 15 enum types, trigger functions, 24 tables, indexes, triggers, grants) and a full `downgrade()`; `backend/alembic/env.py` (migrator connection, transaction-scoped migration lock `0x45434857`, lock and statement timeouts); `scripts/dump_schema.sh` and the regenerated `database/schema.sql` |
| FEAT-009 | Models and repositories for `facilities`, `users`, `residents`, `devices`, `device_assignments`, `api_keys`, `config_parameters`; migration `0002_seed_config_parameters` (46 rows, 23 keys per profile) |
| FEAT-010 | `ingest_batches`, `ingest_rejections`, `raw_sessions`; the insert-only `RawSessionRepository` |
| FEAT-011 | `pipeline_runs`, `epochs`, `processed_sessions`, `day_ledger`, `baselines`, `scores`, `cusum_state`; JSON-column validation (`backend/schemas/json_columns.py`) |
| FEAT-012 | `alerts`, `alert_reviews`, `data_alerts`, `staff_notes`, `facility_reference_ranges`, `audit_logs`, `evaluation_ground_truth` |
| FEAT-013 | `backend/core/db.py`: `create_engine_for` (API-125 pool, `prepare_threshold=None`, TLS refusal outside local/test), `session_factory`, `advisory_key`, `lock_xact`, `lock_residents`, `migrator_connection` |
| FEAT-014 | `backend/repositories/read_models.py`: activity counts, last check-in, current epochs, baseline progress, watching-since, alarm facts, restart cause, scores series, device silent and gap days, device use, last upload, device label, check-in event sources. Nothing derived is stored |
| FEAT-015 | `backend/services/audit_service.py`: the 24-action vocabulary, documented `details` keys per action, secret and feature-value refusal, `record`, `record_cli`, `record_committed`; `AuditRepository` |
| FEAT-016 | `backend/core/security.py` (argon2id, password policy with the bundled common-password list, API-key generation and hashing); CLI `create-user`, `create-api-key`, `revoke-api-key` |
| FEAT-017 | CLI `bootstrap`, `import-master-data`, `withdraw-resident`, `purge-resident`, `seed test_v0_1 [--master-only] [--reset]`, `reset-test-db`; the roster CSV files of TRD 20 §4.12 under `database/seeds/test_v0_1/` |

No API route was added (prompt: "Do not implement APIs yet").

## 2. Files

Created: `backend/alembic/versions/0001_initial_schema.py`, `0002_seed_config_parameters.py`; `backend/core/security.py`, `backend/core/common_passwords.txt`; `backend/models/{base,api_key,audit_log,config_parameter,day_ledger,device,epoch,evaluation,facility,ingest_batch,pipeline_run,reference_range,staff_note,user}.py`; 19 files under `backend/repositories/` plus `read_models.py`; `backend/schemas/json_columns.py`; `backend/services/audit_service.py`; `database/seeds/test_v0_1/{facilities,residents,devices,device_assignments}.csv`; `scripts/dump_schema.sh`; the test modules of section 3 and the helpers `tests/integration/{conftest,db_support,world}.py`; this report and `DATABASE_IMPLEMENTATION_REPORT.md`.

Changed: `backend/alembic/env.py`, `backend/api/deps.py` (new engine helper), `backend/cli.py`, `backend/core/{config,db,errors}.py`, `backend/models/{__init__,alarm,baseline,resident,score,session}.py` (were empty skeleton files), `backend/requirements.txt` (`argon2-cffi==23.1.0`), `pyproject.toml` (E501 ignored only for migration files, which hold the TRD SQL verbatim), `database/schema.sql` (generated), `.github/workflows/ci.yml`, `tests/conftest.py`, `tests/integration/api/test_health.py`, `tests/unit/backend/test_deps.py`; `specs/backlog/BACKLOG.md` §10, `IMPLEMENTATION_ROADMAP.md` §2.1, FEAT-008..FEAT-017 Status fields. Deleted: `database/seeds/.gitkeep`, `scripts/.gitkeep` (their folders now hold files).

Size: about 9,100 changed lines without the two generated files (`common_passwords.txt`, 10,004 lines; `database/schema.sql`, about 2,200 lines): about 3,000 test lines, 2,100 model lines (generated from the DDL), 1,850 repository lines, 1,000 migration lines (TRD SQL), 600 CLI lines. Above the GIT-034 guideline of 1,500 (Q-6).

## 3. Tests added

| File | Level | Covers |
|---|---|---|
| `tests/unit/backend/core/test_db.py` | unit | FEAT-013-AC-03 (TLS refusal, local/test accepted), AC-04 (pool settings, `prepare_threshold=None`), advisory key text and namespaces, sorted resident locks, migrator setup statements |
| `tests/unit/backend/core/test_security.py` | unit | FEAT-016-AC-01 (argon2id parameters), AC-02 (password policy), AC-03 (key format and SHA-256), dummy hash, e-mail normalisation |
| `tests/unit/backend/services/test_audit.py` | unit | FEAT-015-AC-02 (unknown action, no SQL), AC-04 (forbidden keys and secret-looking values), AC-05 (CLI operator), AC-06 (one INFO `audit_event` without details), `record_committed` restriction |
| `tests/unit/backend/schemas/test_json_columns.py` | unit | PGS-032, PGS-033 JSON shapes; scope, errors, counts |
| `tests/unit/backend/repositories/test_raw_session_repository.py` | unit | FEAT-010-AC-06 (database-assigned columns refused, no update/delete method) |
| `tests/unit/backend/test_db_inspection.py` | unit | the inspection criteria as greps: FEAT-008-AC-08, FEAT-012-AC-09, FEAT-013-AC-06, FEAT-015-AC-07, FEAT-016-AC-07, FEAT-017-AC-09 |
| `tests/integration/db/test_migrations.py` | integration | TST-040 round trip (FEAT-008-AC-01), one head (AC-06), `alembic check` (PGS-023) |
| `tests/integration/db/test_roles.py` | integration | FEAT-008-AC-02..AC-05 (extensions, UTC, server 16, roles and memberships, `SET ROLE` refused, 15 enum types equal to Python, 0001 fails without extensions) |
| `tests/integration/db/test_master_tables.py` | integration | FEAT-009-AC-02..AC-05, AC-08 |
| `tests/integration/db/test_grants.py` | integration | PGS-021 exact grants per table, credential columns, AC-PGS-12, AC-PGS-13, FEAT-011-AC-07, AC-08 |
| `tests/integration/db/test_config_seed.py` | integration | AC-PGS-10 (FEAT-009-AC-01) |
| `tests/integration/db/test_raw_store.py` | integration | FEAT-010-AC-04, AC-05, AC-07, and the database half of AC-06 (increasing `arrival_seq`) |
| `tests/integration/db/test_indexes.py` | integration | FEAT-013-AC-01 (each TRD 20 §4.7 index equals its definition), AC-02 (FK columns lead an index) |
| `tests/integration/db/test_advisory_locks.py` | integration | FEAT-013-AC-05 (second transaction waits; other keys do not; released at commit) |
| `tests/integration/db/test_audit_writer.py` | integration | FEAT-015-AC-01 (24 actions, one row each), AC-03 (audit row shares the change transaction), refused-request rows survive a rollback |
| `tests/integration/db/test_read_models.py` | integration | FEAT-014-AC-01..AC-08 on hand-built rows; seed-valued case skipped until FEAT-055 |
| `tests/integration/db/test_repositories.py` | integration | every repository's write/read round trip and its own rules |
| `tests/integration/test_schema_behaviour.py` | integration | AC-PGS-01..09, 14, 15; FEAT-011-AC-01..05, AC-09; FEAT-012-AC-01..08 |
| `tests/integration/test_schema_reference.py` | integration | PGS-016, PGS-017 (FEAT-008-AC-07) |
| `tests/integration/test_cli_credentials.py` | integration | FEAT-016-AC-03..AC-06 |
| `tests/integration/test_cli_seed.py` | integration | FEAT-017-AC-01..AC-08 |

Shared database fixtures run every test inside a transaction that is rolled back; tests that must commit (CLI, audit transaction, ground-truth read) get a throwaway database that is created, provisioned, migrated and dropped (`TEST_SUPERUSER_URL`).

## 4. Commands run and results

Environment: Linux container, Python 3.12.3 (virtualenv), PostgreSQL 16.15 (local cluster on port 5433 provisioned with `database/roles/provision_login_roles.sql`), `pg_dump` 16.15, Docker 29.8 (for the testcontainers run).

| # | Command | Result |
|---|---|---|
| 1 | `alembic upgrade head && alembic downgrade base && alembic upgrade head && alembic check` | exit 0; "No new upgrade operations detected" |
| 2 | `scripts/dump_schema.sh` then `git diff database/schema.sql` | no difference after regeneration |
| 3 | `pytest -p no:randomly tests/unit tests/integration tests/validation --cov=analytics --cov=backend --cov-branch` (CI job env plus `TEST_SUPERUSER_URL`) | 190 passed, 2 skipped; branch coverage 93 % |
| 4 | `pytest -p randomly --randomly-seed=1234` and `=98765` (same paths) | 190 passed, 2 skipped, both seeds |
| 5 | `pytest -q -p no:randomly tests/integration` with no database variables (testcontainers `postgres:16-alpine`) | 106 passed, 1 skipped |
| 6 | `ruff check .`; `ruff format --check .`; `mypy analytics backend`; `lint-imports` | all exit 0; 3 contracts kept |
| 7 | CLI by hand on a fresh database: `seed test_v0_1 --master-only` twice, `reset-test-db`, `withdraw-resident R08 --on 2026-10-20`, `purge-resident R08 --confirm R08`, `APP_ENV=production … seed` | counts 1/10/10/11/3/1 twice; reset leaves 46 config rows and one `seed.reset` row; refusals exit 2; purge writes one `resident.purged` row and deletes no audit row |
| 8 | Case-insensitive grep for the forbidden facility name (AGT-019) in `backend`, `database`, `scripts` and `tests` | no match |

CI changes (`.github/workflows/ci.yml`, `backend-test`): `TEST_SUPERUSER_URL` added (CI-only service-container superuser, already in the job as `PGPASSWORD`); the `alembic upgrade head` step replaced by the TST-040 round trip; `alembic check` step added. CI itself runs on the PR head.

## 5. Exit criteria (roadmap §5.3, TRD 25 Phase 4)

| Criterion | Evidence | Result |
|---|---|---|
| All 24 tables match TRD 20 | migration holds the TRD SQL; schema reference test; `alembic check` | PASS |
| Upgrade/downgrade/upgrade round trip on an empty database | item 1; `test_tst_040_…`; CI step | PASS |
| Relationships, primary and foreign keys enforced | AC-PGS-13; DATABASE_IMPLEMENTATION_REPORT §3 | PASS |
| Indexes created as defined | `test_indexes.py` | PASS |
| Raw store and audit log immutable for the app role | AC-PGS-01..03, 09 | PASS |
| Answer key unreachable from the app role | AC-PGS-14 | PASS |
| Seed framework idempotent, refused in production | FEAT-017-AC-01..05 | PASS |
| Unit and integration tests; no API endpoints | section 3; `backend/api/` unchanged except the engine helper | PASS |
| GIT-034 size ≤ ~1,500 lines | about 9,100 lines | NOT MET (Q-6) |
| CI green on the PR head | needs the PR | PENDING |

## 6. New OQ and D IDs

None in this PR. GitHub PR #5 (wireframes v0.2, still open) reserves D-108..D-114 and OQ-31..OQ-32; to avoid clashing numbers, the decisions that come out of this review will be recorded in TRD 24 after PR #5 is merged, using the next free numbers.

## 7. Deviations and notes

| # | Note | Handling |
|---|---|---|
| N-1 | DEP-064 asks for an advisory lock during migrations; DB-021 forbids session-level advisory locks in `backend/` | the migration lock is `pg_advisory_xact_lock(0x45434857)` inside the migration transaction: same protection, released at commit (Q-1) |
| N-2 | SEC-012 needs a bundled top-10,000 list but names no source | SecLists `10k-most-common.txt` (MIT licence, attribution kept in the file header) (Q-2) |
| N-3 | The seed users' passwords come from `SEED_*` variables and are not checked against the password policy; each seed run writes `user.created` (first run) or `user.updated` audit rows | the policy guards people choosing passwords; seed values are test-only (Q-3) |
| N-4 | FEAT-014 acceptance values (R02 24·0·0·6 etc.) are stated on the full test_v0_1 seed, which FEAT-055 (checkpoint 5) loads | same rules verified on hand-built rows; a skipped test names FEAT-055 and will carry the seed values (Q-4) |
| N-5 | AC-PGS-14 expects 10 ground-truth rows "after the loader"; the loader is FEAT-057 | the test commits 10 synthetic rows as the migrator in a throwaway database and reads them as `echowell_readonly_login` |
| N-6 | Bug found by the tests: SQLAlchemy stored Python `None` in `processed_sessions.adjusted_features` as JSON `null`, which breaks the duplicate-row CHECK | column declared `JSONB(none_as_null=True)`; `alembic check` unaffected |
| N-7 | Some CLI refusals must happen before settings are validated (production seed, reset profile) | `environment_value()` added to `backend/core/config.py` for those pre-settings checks (exit 2, TRD 15 §4.8) |
| N-8 | FEAT-008-AC-03 names `test_roles.py`; FEAT-010-AC-06 names a unit test but needs a database | the AC-03 test lives in `test_roles.py`; AC-06 is split: unit (repository refuses database-assigned columns) and integration (increasing `arrival_seq`) |
| N-9 | PR #5's D-114 adds fields to the FEAT-014 read models (for example `checkins_started`) and FEAT-014-AC-09 | built in checkpoint 4 with the endpoints that use them, as decided in the PR #5 review (W-5, answering Q-5). PR #5 was merged on 27 Oct 2026 and `main` is merged into this branch |
| N-10 | `mypy` in CI checks `analytics` and `backend` only; the test folder has type warnings from checkpoint 2 as well | unchanged scope |

## 8. Questions for the reviewer

| ID | Question |
|---|---|
| Q-1 | Migration lock: accept the transaction-scoped `pg_advisory_xact_lock(0x45434857)` in `env.py` as meeting DEP-064 (DB-021 forbids session locks), and add one sentence to DEP-064 saying so? |
| Q-2 | Common-password list: accept SecLists `10k-most-common.txt` (MIT, attribution in the file header) as the SEC-012 bundled list? |
| Q-3 | Seed users: keep seed passwords outside the password policy, and keep one `user.created` / `user.updated` audit row per seed user per run? |
| Q-4 | FEAT-014: mark it Complete now (derivations verified on hand-built rows), with the seed-valued numbers checked when FEAT-055 lands, as was done for the deferred parts in checkpoint 2? |
| Q-5 | PR #5 (D-114) read-model fields: add them in checkpoint 4 with their endpoints, or would you like them in this PR once PR #5 is merged? |
| Q-6 | Size: about 9,100 lines (3,000 of them tests, 2,100 models generated from the DDL). Accept as one PR, as for checkpoint 2? |

## 9. Review round 1 resolutions (27 October 2026)

The algorithm lead (Shaba) answered Q-1..Q-6 on GitHub PR #17 on 27 Oct 2026 and requested changes. The decisions are recorded in TRD 24 v0.20 (D-120..D-123); GitHub PR #5 had taken D-108..D-119 first, as section 6 planned.

| ID | Reviewer answer | Resolution | Files changed |
|---|---|---|---|
| Q-1 | Accept the transaction-scoped lock; add a note to DEP-064 that transaction-scoped advisory locks are preferred. | DEP-064 now requires the transaction-scoped `pg_advisory_xact_lock(0x45434857)` in `env.py` and never a session-level lock (D-120). The `env.py` docstring cites D-120. | TRD 15 DEP-064 (v0.14); TRD 24 D-120; `backend/alembic/env.py` (docstring) |
| Q-2 | Accept the SecLists list (MIT, attribution kept). | Recorded as D-121. | TRD 24 D-121 |
| Q-3 | Keep the policy bypass and the audit rows, with a safeguard that seed users cannot be created in production. | The safeguard already exists: `seed` is refused in production with exit 2 before any settings or database access, with no override (DEP-070, DB-059). It is tested by `test_production_refuses_seed_and_reset` (FEAT-017-AC-03), which also checks that no table changes. Recorded as D-122; no code change needed. | TRD 24 D-122 |
| Q-4 | Mark FEAT-014 Complete now; re-check the seed numbers in checkpoint 5 as an additional validation, not a blocker. | FEAT-014 stays Complete; the BACKLOG §10 note and D-123 say the seed values are an additional validation. | TRD 24 D-123; `BACKLOG.md` §10 |
| Q-5 | Add the D-114 fields in checkpoint 4 with their endpoints. | Already planned (N-9); recorded in D-123. | TRD 24 D-123 |
| Q-6 | Keep one PR. | No change. | — |

Verification after review round 1: `pytest -p no:randomly tests/unit tests/integration tests/validation` gives 190 passed, 2 skipped; `ruff check`, `ruff format --check`, `mypy analytics backend` and `lint-imports` are clean; D-120..D-123 are defined in TRD 24; Markdown tables of the changed files have consistent column counts.

