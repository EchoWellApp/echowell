# FEAT-005 Test infrastructure and conventions (pytest, testcontainers, markers, coverage)

| Field | Value |
|---|---|
| Epic | Testing & Validation |
| Build phase | Phase 3 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-002, FEAT-003 |
| Status | Not Started |

## Purpose

Provide the Python test foundation that every later feature uses to prove its requirements: the TRD 13 §4.2 directory layout, a shared `tests/conftest.py`, the single pytest marker list in `pyproject.toml`, PostgreSQL 16 test databases through testcontainers (or a provided `DATABASE_URL` in CI), frozen clocks, coverage configuration and gates for `analytics/` and `backend/`, and the two Phase 3 smoke tests (health endpoint and startup guard).

## Business Context

- BR-15: deterministic tests are the precondition for reproducing the R01–R10 answer key (TST-005).
- BR-16: no audio fixtures (TST-007).
- BR-17: CI quality gates on coverage (NFR-082, TST-140, TST-141).

## Referenced TRDs

- TRD 13 TST-001..TST-007 (tools, database, determinism, markers, no audio), TST-010..TST-013 (layout, naming, analytics test files, requirement tracing), TST-140..TST-144 (coverage), TST-160..TST-162 (defect handling); §4.1 pyramid table; §4.2 directory layout; §8 implementation notes; AC-TST-06.
- TRD 16 §6 (`backend/requirements-dev.txt`, root `pyproject.toml` sections).
- TRD 03 NFR-082.
- TRD 05 API-017 (dependency overrides used by fixtures).
- TRD 25 §4.6 Phase 3 (required tests and commands).
- TRD 24 D-74 (autouse limiter reset fixture).

## Scope

- Directories: `tests/unit/analytics/`, `tests/unit/backend/`, `tests/integration/db/`, `tests/integration/api/`, `tests/integration/pipeline/`, `tests/contract/`, `tests/validation/`, `tests/security/`, `tests/performance/`, `tests/smoke/`, `tests/fixtures/` (sub-directories `pipeline_input/`, `answer_key/`, `legacy/`, `seeds/demo_overlay/` are created empty here and populated by FEAT-057 and FEAT-076).
- `tests/conftest.py` with shared fixtures: configuration profile selection, frozen clock (`time-machine`), PostgreSQL 16 database (testcontainers `postgres:16-alpine`, or `DATABASE_URL` when `APP_ENV=test`), per-test SQLAlchemy session, FastAPI `TestClient` built from `create_app()` with `app.dependency_overrides`, and an autouse fixture that empties the in-memory slowapi storage before each test (becomes active once FEAT-022 adds the limiter).
- `pyproject.toml` `[tool.pytest.ini_options]` with the TST-006 markers and `--strict-markers`; no `pytest.ini`.
- `pyproject.toml` `[tool.coverage]` configuration: sources `analytics` and `backend`, exclusions limited to TST-144.
- `tests/trace_report.py` listing requirement IDs without a test or inspection (TST-013).
- A meta-test asserting `tests/unit/analytics/test_<module>.py` exists for each TRD 07 §4.2 module (TST-011); it is registered now and expected to fail until the analytics features add the files, so it is marked with the TST-153 skip reason naming TST-011 until Phase 6.
- A repository scan test that fails on any tracked file with an audio extension (TST-007).
- Smoke tests: `tests/integration/api/test_health.py` (owned by FEAT-003, wired here) and `tests/unit/backend/core/test_config.py` startup-guard case.

## Out of Scope

- The validation harness, comparator and answer-key loader (FEAT-057, FEAT-058, FEAT-059).
- Contract, security, performance and smoke-after-deploy suites' contents (FEAT-038, FEAT-039, FEAT-079, FEAT-086).
- Frontend Vitest configuration (FEAT-004) and Playwright suites (FEAT-076).
- CI workflow (FEAT-007) and the full coverage gates in CI (FEAT-078).
- Defect labels and GitHub issue process are organisational (TST-160..TST-162 are recorded here as conventions only).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-005-FR-01 | Backend and analytics tests shall run with pytest 8.x on Python 3.12 with pytest-cov and the httpx-based FastAPI `TestClient`. | TST-001 |
| FEAT-005-FR-02 | A session-scoped fixture shall start PostgreSQL 16 with testcontainers (image `postgres:16-alpine`) unless `DATABASE_URL` is set and `APP_ENV=test`, in which case that database is used; no SQL-exercising test uses SQLite. | TST-002 |
| FEAT-005-FR-03 | A frozen-clock fixture based on `time-machine` shall be available; no test depends on wall-clock time, network outside the test stack or execution order (compatible with `pytest -p randomly`). | TST-005 |
| FEAT-005-FR-04 | `pyproject.toml` `[tool.pytest.ini_options]` shall register exactly the markers `unit`, `integration`, `contract`, `validation`, `security`, `performance`, `smoke`, `slow`, `authenticated`, `budget`, `req` with `--strict-markers`; a conftest hook shall fail collection of a test module that does not carry exactly one level marker. | TST-006 |
| FEAT-005-FR-05 | A repository scan test shall fail if any tracked file has extension `.wav`, `.mp3`, `.flac`, `.ogg` or `.m4a`. | TST-007 |
| FEAT-005-FR-06 | The test tree shall follow TRD 13 §4.2 and the naming rule `test_<subject>.py`. | TST-010 |
| FEAT-005-FR-07 | A meta-test shall list the TRD 07 §4.2 modules and assert each has `tests/unit/analytics/test_<module>.py`. | TST-011 |
| FEAT-005-FR-08 | Test function names shall include the TRD 13 §4.3 or TRD 14 case ID where one exists; the `req` marker carries requirement IDs. | TST-012, TST-013 |
| FEAT-005-FR-09 | `tests/trace_report.py` shall list Must requirement IDs of TRDs 02, 04, 05, 07–12 that have neither a `@pytest.mark.req`/`// req:` reference nor an entry in `docs/reports/traceability_inspections.md`. | TST-013 |
| FEAT-005-FR-10 | Coverage configuration shall support `--cov=analytics --cov-fail-under=95` (unit + validation) and a backend run with fail-under 85 (unit + integration + contract + security). | TST-140, TST-141, NFR-082 |
| FEAT-005-FR-11 | Coverage exclusions shall be limited to `if __name__ == "__main__":`, `TYPE_CHECKING` blocks and generated Alembic revision headers, each pragma with a reason comment; analytics branch coverage is reported. | TST-143, TST-144 |
| FEAT-005-FR-12 | Fixtures shall build the app via `create_app()` and replace `get_db`, `get_settings` and auth dependencies through `app.dependency_overrides`. | API-017 |
| FEAT-005-FR-13 | The Phase 3 smoke tests shall exist and pass: health endpoint returns 200 and the startup guard refuses `APP_ENV=production` with `PIPELINE_PROFILE=test_v0_1`. | TRD 25 §4.6 Phase 3; TST-054; CFG-06 |
| FEAT-005-FR-14 | Defect conventions shall be documented for contributors: defects are issues labelled `defect` and `sev:S1`..`sev:S4`; flaky tests are S3 defects; validation tests are never retried; S1 validation defects are fixed in code, not by editing golden files. | TST-160, TST-161, TST-162 |

## Inputs

- `backend/requirements-dev.txt` (FEAT-002) with pytest, pytest-cov, pytest-randomly, time-machine, httpx, testcontainers-python 4.x.
- `backend.main:create_app()` and `Settings` (FEAT-003).
- Docker available locally and on GitHub-hosted runners (TRD 13 §8).

## Outputs

- The `tests/` tree, `tests/conftest.py`, `tests/trace_report.py`, `pyproject.toml` pytest and coverage sections, smoke tests.
- Coverage reports (`coverage.xml`, terminal) when run with `--cov`.

## Data Flow

`pytest` → loads `pyproject.toml` options and markers → `tests/conftest.py` session fixture starts `postgres:16-alpine` (or connects to `DATABASE_URL`) → per-test fixtures open a session, freeze the clock, build `TestClient(create_app())` with overrides → tests run → pytest-cov aggregates line and branch coverage for `analytics` and `backend` → fail-under thresholds decide the exit code.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-002, FEAT-003

- FEAT-002 provides the tree, `pyproject.toml` and the dev-tool pins.
- FEAT-003 provides `create_app()`, `Settings`, the startup guards and the health endpoint exercised by the smoke tests.

Features that build directly on this one: FEAT-007 and every feature that adds tests.

## Database Impact

- Tables used: none yet; the database fixture creates an empty PostgreSQL 16 database. From FEAT-008 onward the fixture runs `alembic upgrade head` as the migrator role and tests connect as `echowell_app` (TRD 25 AGT-060); that wiring is added by FEAT-008.
- Tables created or modified: none.

## API Impact

None exposed. Consumes E-01 `GET /api/v1/health` in the smoke test.

## Frontend Impact

None (frontend test tooling is FEAT-004).

## Analytics Impact

None computed. Coverage measurement of `analytics/` and the TST-011 meta-test are configured.

## Security Requirements

- Test credentials are generated or obviously test-only and never valid on staging or production (GIT-083).
- No audio fixture (TST-007); no real resident data in fixtures (GIT-092, AGT-017).
- Tests never read the answer key outside `tests/validation/` (AGT-007); enforced by FEAT-057.

## Error Handling

- Docker unavailable and no `DATABASE_URL`: integration fixtures fail with an explicit error naming TST-002, never silently fall back to SQLite.
- Unknown marker: collection error from `--strict-markers` (TST-006).
- A skip without a `reason=` naming a requirement or OQ ID is rejected by a conftest hook (TST-153).

## Logging Requirements

None at runtime. Pytest output and coverage reports are the artefacts; no audit rows.

## Testing Requirements

- Unit: `tests/unit/backend/core/test_config.py::test_cfg_06_production_refuses_test_profile` (CFG-06).
- Integration: `tests/integration/api/test_health.py` (TST-054).
- Meta: `tests/unit/test_markers.py` (one level marker per module, TST-006), `tests/unit/test_no_audio_files.py` (TST-007), `tests/unit/analytics/test_module_tests_exist.py` (TST-011).
- Command: `pytest -q` (TRD 25 §4.6 Phase 3 Commands); `pytest -p randomly -q` passes twice in a row with different seeds (TST-005).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-005-AC-01 | `pytest -q` exits 0 on a machine with Docker and no `DATABASE_URL`, starting a `postgres:16-alpine` container. | TST-001, TST-002 |
| FEAT-005-AC-02 | With `APP_ENV=test` and `DATABASE_URL` pointing to a running PostgreSQL 16, `pytest -q` uses it and starts no container. | TST-002 |
| FEAT-005-AC-03 | `grep -n "markers" pyproject.toml` shows exactly the eleven TST-006 markers; no `pytest.ini` exists; a test using an unregistered marker fails collection. | TST-006 |
| FEAT-005-AC-04 | Adding a tracked file `tests/fixtures/sample.wav` makes the no-audio test fail. | TST-007 |
| FEAT-005-AC-05 | The health smoke test and the startup-guard test pass. | TRD 25 §4.6 Phase 3; TST-054; CFG-06 |
| FEAT-005-AC-06 | `pytest -p randomly -q` passes with two different random seeds. | TST-005 |
| FEAT-005-AC-07 | Running `pytest --cov=analytics --cov=backend --cov-report=term` produces a coverage report and the configured exclusions are only those of TST-144. | TST-144, AC-TST-06 (mechanism) |
| FEAT-005-AC-08 | `python tests/trace_report.py` runs and prints the list of requirement IDs lacking a test or inspection entry. | TST-013 |

## Definition of Done

- All FEAT-005 acceptance criteria pass.
- Every directory of TRD 13 §4.2 exists; conventions (naming, markers, req marker, defect handling) are described in `tests/README` comments or `docs/team_workflow.md` without contradicting TRD 13.
- Batch report lists IDs and command results (AGT-022).

## Implementation Notes

- Use `testcontainers.postgres.PostgresContainer("postgres:16-alpine")` (the image of TST-002, DEP-010 and CIC-012) with session scope; wrap each test in a transaction or truncate between tests so order does not matter (TST-005).
- The rate-limit reset fixture (D-74) must be autouse and import the limiter lazily, so it is harmless before FEAT-022 exists.
- Keep the answer-key loader out of `tests/conftest.py`; it lives only in `tests/validation/conftest.py` (TRD 13 §8, AGT-007).
- Coverage thresholds are enforced in CI by FEAT-078; locally they are available as `--cov-fail-under` options so early phases are not blocked by empty modules.
