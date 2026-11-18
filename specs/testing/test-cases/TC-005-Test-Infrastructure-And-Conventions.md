# FEAT-005 Test infrastructure and conventions

## Feature Description

FEAT-005 provides the Python test foundation of TRD 13: the §4.2 test directory layout, the shared `tests/conftest.py` (app built with `create_app()`, dependency overrides, frozen clock with `time-machine`), PostgreSQL 16 test databases through testcontainers (`postgres:16-alpine`) or a provided `DATABASE_URL` when `APP_ENV=test` (never SQLite), the single marker list in `pyproject.toml` with `--strict-markers` and a one-level-marker rule, the no-audio repository scan, the analytics module-test meta-test, coverage configuration (TST-140..TST-144), the trace report `tests/trace_report.py`, the defect conventions, and the Phase 3 smoke tests (health endpoint, startup guard).

## Preconditions

- Local development stack: Python 3.12 venv with `backend/requirements.txt` and `backend/requirements-dev.txt`; commands run from the repository root.
- Docker 24+ running (for testcontainers) unless a case says to stop it.
- For TC-005-02 a throwaway PostgreSQL 16 database that may be migrated up and down. With the Compose stack running: `docker compose exec db createdb -U echowell echowell_test` and `docker compose exec db psql -U echowell -d echowell_test -v ON_ERROR_STOP=1 -f /docker-entrypoint-initdb.d/10_provision_login_roles.sql`. Never point the test suite at the seeded `echowell` database: the integration fixtures run `alembic downgrade base`.
- A scratch working tree you may modify and revert for TC-005-04, TC-005-05 and TC-005-10.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-005-01 | `pytest -q` passes with Docker and no `DATABASE_URL`, using a `postgres:16-alpine` container | High | Positive |
| TC-005-02 | With `APP_ENV=test` and `DATABASE_URL`, pytest uses that database and starts no container | High | Positive |
| TC-005-03 | Exactly the eleven markers are registered with `--strict-markers`; no `pytest.ini` | High | Positive |
| TC-005-04 | A test with an unregistered marker or without a level marker fails collection | High | Negative |
| TC-005-05 | A tracked `tests/fixtures/sample.wav` makes the no-audio test fail | High | Negative |
| TC-005-06 | Health smoke test and startup-guard test pass | High | Positive |
| TC-005-07 | `pytest -p randomly -q` passes with two different seeds | High | Positive |
| TC-005-08 | Coverage report runs; exclusions are only those of TST-144 | High | Positive |
| TC-005-09 | `python tests/trace_report.py` prints the IDs lacking a test or inspection entry | High | Positive |
| TC-005-10 | A skip without a requirement/OQ ID in its reason is rejected | Medium | Negative |
| TC-005-11 | Test tree layout, naming and the analytics module-test meta-test | Medium | Positive |
| TC-005-12 | Docker unavailable and no `DATABASE_URL`: integration fixtures fail, no SQLite fallback | Medium | Negative |
| TC-005-13 | Defect conventions documented for contributors | Low | Documentation |

### TC-005-01 `pytest -q` passes with Docker and no `DATABASE_URL`, using a `postgres:16-alpine` container

| Step | Action | Expected Result |
|---|---|---|
| 1 | In a new shell run `env -u DATABASE_URL -u APP_ENV pytest -q; echo "exit=$?"` and, while it runs, `docker ps --format '{{.Image}}'` in a second shell. | `docker ps` shows a container with image `postgres:16-alpine` (plus the testcontainers `ryuk` helper); pytest ends with `N passed` and `0 failed`, `0 errors`; `exit=0`. |
| 2 | After the run, `docker ps --format '{{.Image}}' \| grep postgres:16-alpine`. | No container left running (removed at session end). |
| 3 | Run `grep -rni "sqlite" tests --include=*.py`. | One match only: the docstring `TST-002; SQLite is never used.` in `tests/conftest.py` (no test uses SQLite). |

### TC-005-02 With `APP_ENV=test` and `DATABASE_URL`, pytest uses that database and starts no container

| Step | Action | Expected Result |
|---|---|---|
| 1 | Export, for the throwaway database: `APP_ENV=test`, `DATABASE_URL`, `DATABASE_MIGRATION_URL`, `DATABASE_READONLY_URL` (login roles `echowell_app_login`, `echowell_migrator_login`, `echowell_readonly_login` on `127.0.0.1:5432/echowell_test`, passwords from the `ECHOWELL_*_DB_PASSWORD` values of the Compose file) and `TEST_SUPERUSER_URL` (user `echowell`). | Variables set; no value is written into a file. |
| 2 | Run `pytest -q tests/integration/db/test_roles.py tests/integration/api/test_health.py` and watch `docker ps` in a second shell. | No new `postgres:16-alpine` container appears; tests pass. |
| 3 | In psql on `echowell_test` run `SELECT version_num FROM alembic_version;`. | One row (the head revision, `0004`), showing the suite migrated the provided database. |
| 4 | Drop the throwaway database afterwards: `docker compose exec db dropdb -U echowell echowell_test`. | Database removed. |

### TC-005-03 Exactly the eleven markers are registered with `--strict-markers`; no `pytest.ini`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `grep -n -A13 "^markers" pyproject.toml`. | Exactly eleven entries: `unit`, `integration`, `contract`, `validation`, `security`, `performance`, `smoke`, `slow`, `authenticated`, `budget`, `req(*ids)`. |
| 2 | Run `grep -n "addopts" pyproject.toml`. | `addopts` contains `--strict-markers`. |
| 3 | Run `ls pytest.ini tox.ini setup.cfg 2>&1`. | `No such file or directory` for `pytest.ini` (and no pytest section elsewhere). |
| 4 | Run `pytest -q tests/unit/test_markers.py`. | All tests pass, including `test_tst_006_marker_list_is_exact_and_strict`. |

### TC-005-04 A test with an unregistered marker or without a level marker fails collection

| Step | Action | Expected Result |
|---|---|---|
| 1 | Create `tests/unit/test_qa_marker.py` with `import pytest`, `pytestmark = pytest.mark.unit` and a test decorated `@pytest.mark.qa_unknown`. Run `pytest -q tests/unit/test_qa_marker.py`. | Collection error: `'qa_unknown' not found in markers configuration option`; non-zero exit. |
| 2 | Change the file to remove `pytestmark` and the unknown marker; run again. | Usage error `tests/unit/test_qa_marker.py: needs exactly one level marker, found []`; non-zero exit. |
| 3 | Set `pytestmark = [pytest.mark.unit, pytest.mark.integration]`; run again. | Usage error `needs exactly one level marker, found ['integration', 'unit']`. |
| 4 | Delete `tests/unit/test_qa_marker.py`. | File removed; `git status` clean. |

### TC-005-05 A tracked `tests/fixtures/sample.wav` makes the no-audio test fail

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `pytest -q tests/unit/test_repository_layout.py::test_tst_007_no_audio_files_tracked`. | `1 passed`. |
| 2 | Create an empty file `touch tests/fixtures/sample.wav` and stage it with `git add -f tests/fixtures/sample.wav` (`-f` because `.gitignore` ignores `*.wav`). The file is empty; no audio content is created. | File staged. |
| 3 | Re-run the test of step 1. | `1 failed`; the assertion lists `tests/fixtures/sample.wav`. |
| 4 | Run `git rm --cached -q tests/fixtures/sample.wav && rm tests/fixtures/sample.wav` and re-run. | `1 passed`. |

Note: FEAT-005 names the test `tests/unit/test_no_audio_files.py`; the implementation is `tests/unit/test_repository_layout.py::test_tst_007_no_audio_files_tracked` (tests/unit/test_repository_layout.py:57).

### TC-005-06 Health smoke test and startup-guard test pass

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `pytest -q tests/integration/api/test_health.py`. | `test_tst_054_health_ok_with_database_up` and `test_tst_054_health_degraded_with_database_down` pass (200 `ok`; 503 `degraded`). |
| 2 | Run `pytest -q tests/unit/backend/core/test_config.py::test_cfg_06_production_refuses_test_profile`. | `1 passed` (`APP_ENV=production` + `PIPELINE_PROFILE=test_v0_1` refused). |

### TC-005-07 `pytest -p randomly -q` passes with two different seeds

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `pytest -p randomly --randomly-seed=12345 -q tests/unit`. | Header shows `Using --randomly-seed=12345`; `0 failed`. |
| 2 | Repeat with `--randomly-seed=67890`. | Header shows `Using --randomly-seed=67890`; `0 failed`. |
| 3 | Run the full suite once with `pytest -p randomly -q` (seed chosen at random). | `0 failed`, `0 errors`. |

### TC-005-08 Coverage report runs; exclusions are only those of TST-144

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `pytest --cov=analytics --cov=backend --cov-report=term -q tests/unit`. | A table `Name / Stmts / Miss / Branch / BrPart / Cover / Missing` is printed with a `TOTAL` line (branch coverage on, `branch = true`). |
| 2 | Run `sed -n '/\[tool.coverage.report\]/,/^\]/p' pyproject.toml`. | `exclude_also` lists only `if __name__ == "__main__":` and `if TYPE_CHECKING:`, each with a reason comment. |
| 3 | Run `grep -rn "pragma: no cover" analytics backend --include=*.py`. | Every match (if any) carries a reason comment on the same line and is an entry point, a `TYPE_CHECKING` block or an Alembic revision header. |
| 4 | Run `pytest --cov=analytics --cov-fail-under=95 -q tests/unit/analytics tests/validation`. | Coverage total ≥ 95 % and `Required test coverage of 95% reached`. |

### TC-005-09 `python tests/trace_report.py` prints the IDs lacking a test or inspection entry

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `python tests/trace_report.py; echo "exit=$?"`. | Prints zero or more requirement IDs, one per line, followed by the line `N Must requirement(s) without a test or inspection entry`; the script completes without traceback. |
| 2 | Pick one printed ID (if any) and run `grep -rn "<ID>" tests docs/reports/traceability_inspections.md`. | No `req` marker and no inspection entry for that ID (the report is correct). |

### TC-005-10 A skip without a requirement/OQ ID in its reason is rejected

| Step | Action | Expected Result |
|---|---|---|
| 1 | Create `tests/unit/test_qa_skip.py` with `pytestmark = pytest.mark.unit` and a test decorated `@pytest.mark.skip(reason="later")`. Run `pytest -q tests/unit/test_qa_skip.py`. | Usage error `…: skip reason must name a requirement or OQ ID`; non-zero exit. |
| 2 | Change the reason to `"OQ-18 deferred"` and run again. | The test is reported as skipped; exit 0. |
| 3 | Delete the file. | `git status` clean. |

### TC-005-11 Test tree layout, naming and the analytics module-test meta-test

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `ls tests`. | Contains `unit`, `integration`, `contract`, `validation`, `security`, `performance`, `smoke`, `fixtures`, `conftest.py`, `trace_report.py`. |
| 2 | Run `find tests -name "*.py" -path "*test*" ! -name "test_*.py" ! -name "conftest.py" ! -name "__init__.py" ! -path "*/fixtures/*" ! -path "*/support/*" ! -name "*.pyc"`. | Only helper modules (for example `tests/trace_report.py`, `tests/integration/world.py`, `tests/integration/db_support.py`, `tests/unit/analytics/factory.py`); every test module is named `test_<subject>.py`. |
| 3 | Run `pytest -q tests/unit/analytics/test_module_tests_exist.py`. | Passes: each of the 16 TRD 07 §4.2 modules has `tests/unit/analytics/test_<module>.py`. |
| 4 | Run `grep -rn "def test_cfg_06\|def test_tst_054\|def test_tst_007" tests`. | Test names carry the TRD 13 case IDs (TST-012). |

### TC-005-12 Docker unavailable and no `DATABASE_URL`: integration fixtures fail, no SQLite fallback

| Step | Action | Expected Result |
|---|---|---|
| 1 | Stop the Docker daemon (or run with `DOCKER_HOST=tcp://127.0.0.1:1`) and run `env -u DATABASE_URL -u APP_ENV pytest -q tests/integration/db/test_roles.py`. | Tests error at fixture setup with a Docker connection error; none passes; no `sqlite` engine is created; non-zero exit. |
| 2 | Run `pytest -q tests/unit/test_markers.py` in the same state. | Passes (unit tests need no database). |

Note: FEAT-005 Error Handling asks for an explicit error naming TST-002; the fixture raises the testcontainers Docker error without that ID (tests/conftest.py:110-113, tests/integration/conftest.py:40-42).

### TC-005-13 Defect conventions documented for contributors

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `grep -n "sev:S1\|S3 defect\|never retried\|golden files" docs/team_workflow.md`. | One paragraph states: defects are GitHub issues labelled `defect` and `sev:S1`..`sev:S4`; a flaky test is an S3 defect; validation tests are never retried or quarantined; an S1 validation defect is fixed in code, never by editing golden files. |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | Health smoke test via `TestClient` (`tests/integration/api/test_health.py`) | 200 `{"status":"ok","database":"ok",…}`; 503 `degraded` when the `get_db`/engine override fails |

No other endpoint is in scope; the feature provides the fixtures other features use.

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | During TC-005-01, `docker ps` | One `postgres:16-alpine` container per session, removed afterwards |
| 2 | After TC-005-02, `SELECT version_num FROM alembic_version;` on `echowell_test` | Head revision present: the provided database was used |
| 3 | `SELECT current_setting('server_version_num')::int;` on the test database | ≥ 160000 and < 170000 |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Unregistered marker (TC-005-04) | Collection error |
| 2 | Missing or double level marker (TC-005-04) | Usage error naming the module |
| 3 | Tracked `sample.wav` (TC-005-05) | No-audio test fails |
| 4 | Skip without requirement ID (TC-005-10) | Usage error |
| 5 | Docker unavailable, no `DATABASE_URL` (TC-005-12) | Integration fixtures error; no SQLite fallback |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-005-AC-01 | `pytest -q` exits 0 with Docker and no `DATABASE_URL`, starting a `postgres:16-alpine` container. | TC-005-01 |
| FEAT-005-AC-02 | With `APP_ENV=test` and `DATABASE_URL` set, pytest uses that database and starts no container. | TC-005-02 |
| FEAT-005-AC-03 | Exactly eleven TST-006 markers; no `pytest.ini`; an unregistered marker fails collection. | TC-005-03, TC-005-04 |
| FEAT-005-AC-04 | A tracked `tests/fixtures/sample.wav` makes the no-audio test fail. | TC-005-05 |
| FEAT-005-AC-05 | Health smoke test and startup-guard test pass. | TC-005-06 |
| FEAT-005-AC-06 | `pytest -p randomly -q` passes with two different seeds. | TC-005-07 |
| FEAT-005-AC-07 | Coverage report produced; exclusions only those of TST-144. | TC-005-08 |
| FEAT-005-AC-08 | `python tests/trace_report.py` runs and prints the IDs lacking a test or inspection entry. | TC-005-09 |

## Test Data Requirements

- No resident data is created by these cases; integration tests build their own synthetic `test_v0_1` worlds.
- Throwaway database `echowell_test` (TC-005-02) provisioned with `database/roles/provision_login_roles.sql`; passwords come from the `ECHOWELL_*_DB_PASSWORD` values of the Compose file, never written into a test file.
- An empty placeholder file `tests/fixtures/sample.wav` (zero bytes, no audio) used only in TC-005-05 and removed afterwards.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-005-FR-01 (TST-001) | FEAT-005 | TC-005-01 |
| FEAT-005-FR-02 (TST-002) | FEAT-005 | TC-005-01, TC-005-02, TC-005-12 |
| FEAT-005-FR-03 (TST-005) | FEAT-005 | TC-005-07 |
| FEAT-005-FR-04 (TST-006) | FEAT-005 | TC-005-03, TC-005-04 |
| FEAT-005-FR-05 (TST-007) | FEAT-005 | TC-005-05 |
| FEAT-005-FR-06 (TST-010) | FEAT-005 | TC-005-11 |
| FEAT-005-FR-07 (TST-011) | FEAT-005 | TC-005-11 |
| FEAT-005-FR-08 (TST-012, TST-013) | FEAT-005 | TC-005-11 |
| FEAT-005-FR-09 (TST-013) | FEAT-005 | TC-005-09 |
| FEAT-005-FR-10 (TST-140, TST-141, NFR-082) | FEAT-005 | TC-005-08 |
| FEAT-005-FR-11 (TST-143, TST-144) | FEAT-005 | TC-005-08 |
| FEAT-005-FR-12 (API-017) | FEAT-005 | TC-005-06 |
| FEAT-005-FR-13 (TST-054, CFG-06) | FEAT-005 | TC-005-06 |
| FEAT-005-FR-14 (TST-160, TST-161, TST-162) | FEAT-005 | TC-005-13 |
| TST-153 (skip reasons) | FEAT-005 | TC-005-10 |
| AC-TST-06 (mechanism) | FEAT-005 | TC-005-08 |
