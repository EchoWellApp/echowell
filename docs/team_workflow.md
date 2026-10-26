# Team workflow

Branching, commits and pull requests follow TRD 18 and the team plan (TRD 24 D-99..D-101): `main` plus one feature branch and pull request per Block 3 checkpoint; Conventional Commit messages citing the implemented requirement IDs; `.github/pull_request_template.md` filled in.

## Test conventions (TRD 13)

- Layout of TRD 13 §4.2: `tests/unit/`, `tests/integration/{db,api,pipeline}/`, `tests/contract/`, `tests/validation/`, `tests/security/`, `tests/performance/`, `tests/smoke/`, `tests/fixtures/`; files are named `test_<subject>.py` (TST-010); frontend tests live under `frontend/tests/` and co-located `components/<Name>/<Name>.test.tsx`.
- Every test module sets `pytestmark` to exactly one level marker (`unit`, `integration`, `contract`, `validation`, `security`, `performance`, `smoke`); markers are registered only in `pyproject.toml` with `--strict-markers`, there is no `pytest.ini` (TST-006).
- Tests cite their requirement IDs with `@pytest.mark.req("<ID>")` (Python) or `// req: <ID>` (frontend), and names carry the TRD 13 or TRD 14 case ID where one exists (TST-012, TST-013); `python tests/trace_report.py` lists Must requirements without a test or an entry in `docs/reports/traceability_inspections.md`.
- A skip needs a `reason=` that names a requirement or OQ ID (TST-153). Tests are deterministic: frozen clock (`frozen_clock` fixture), no network outside the test stack, any order (TST-005).
- Integration tests use PostgreSQL 16: `DATABASE_URL` when `APP_ENV=test`, otherwise a testcontainers `postgres:16-alpine`; never SQLite (TST-002).
- Defects are GitHub issues labelled `defect` and `sev:S1`..`sev:S4`, citing the failing test and requirement ID; a test that passes only on retry twice within 7 days is an S3 defect; validation tests are never retried or quarantined, and an S1 validation defect is fixed in code, never by editing golden files (TST-160..TST-162).
