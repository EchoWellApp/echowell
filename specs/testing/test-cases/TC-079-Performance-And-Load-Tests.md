# Performance and load tests

## Feature Description

FEAT-079 verifies the contract R8 performance budgets automatically (TRD 13 TST-120..TST-126, TST-190, TST-191; TRD 05 API-120..API-125; TRD 07 ANL-047..ANL-050; TRD 03 NFR-001..NFR-013, NFR-150..NFR-153; TRD 14 DS-08, TDV-007, TDV-008). `tests/performance/make_load_dataset.py` generates DS-08 deterministically (seed 20261004; residents `L001`..`L100`, devices `LD001`..`LD100`, 120 days from 2026-06-01, 10,800 records, never committed). The suite times the SRC-05 pipeline run (≤ 5 s), `POST /api/v1/sessions` with the synchronous per-resident pipeline (p95 ≤ 1,000 ms), six read endpoints on DS-08 (p95 ≤ 500 ms), batch ingest of SRC-05 (202 ≤ 2 s, run `succeeded` ≤ 30 s), the DS-08 rebuild (≤ 120 s), the SRC-05 rebuild (≤ 30 s), `/health` (p95 ≤ 200 ms), sustained ingest (10 records/s for 60 s), the initial JS bundle (≤ 300 KB gzip per route) and Lighthouse on four pages (Performance ≥ 80, LCP ≤ 2.5 s). Results go to `build/performance.json`.

## Preconditions

- Python 3.12 with `pip install -r backend/requirements.txt -r backend/requirements-dev.txt`; Docker available (the suite uses a throwaway `postgres:16-alpine` testcontainer, or the server in TEST_SUPERUSER_URL).
- Never point TEST_SUPERUSER_URL, DATABASE_URL or any performance run at a database that holds real records, staging or production (TDV-007); the suite creates and drops its own databases.
- Node 20; `cd frontend && npm ci && npm run build` with `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` and `NEXT_PUBLIC_APP_ENV=local` for the bundle check.
- For Lighthouse: Compose demo stack running and seeded (`docker compose --profile demo up -d --build --wait db backend frontend-prod`, `seed test_v0_1`), `SEED_ADMIN_PASSWORD` exported, Chrome available.
- Timings are binding on GitHub-hosted runners (`ubuntu-24.04`); local timings are indicative.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-079-01 | `pytest -m budget` passes; SRC-05 pipeline run ≤ 5 s | High | Performance |
| TC-079-02 | Full performance suite passes all budgets and writes `build/performance.json` | High | Performance |
| TC-079-03 | DS-08 generator is deterministic: identical files, 10,800 records, `L001`..`L100` | High | Positive |
| TC-079-04 | Lighthouse on `/residents` (and the other three pages): Performance ≥ 80, LCP ≤ 2.5 s | High | Performance |
| TC-079-05 | PR-scope budgets TST-120, TST-121 (50 requests), TST-124 pass in `backend-test` | High | Performance |
| TC-079-06 | `git ls-files tests/performance` lists no generated dataset | High | Negative |
| TC-079-07 | Read endpoints p95 ≤ 500 ms on DS-08 and `/health` p95 ≤ 200 ms | Medium | Performance |
| TC-079-08 | Sustained ingest 10 records/s for 60 s: only 201/200 responses | Medium | Performance |
| TC-079-09 | Initial JavaScript per dashboard route ≤ 300 KB gzip | Medium | Performance |
| TC-079-10 | A budget breach fails with measured p95 and budget, recorded `passed: false` | Medium | Negative |
| TC-079-11 | Nightly run records DS-08 database size for the NFR-152 projection | Low | Analytics |
| TC-079-12 | Performance modules are deselected from a plain `pytest` run | Low | Negative |

### TC-079-01 `pytest -m budget` passes; SRC-05 pipeline run ≤ 5 s

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest -p no:randomly tests/performance -m budget` | Exit 0; `test_pipeline_on_src05_within_5_s`, `test_post_sessions_p95_pr_scope`, `test_ingest_src05_accepted_and_processed` pass. |
| 2 | `python -c "import json;print(json.load(open('build/performance.json'))['budgets']['TST-120'])"` | `statistic` `elapsed`, `budget_ms` 5000, `measured_ms` ≤ 5000, `passed` `true`. |
| 3 | In the latest `main` run of `ci.yml`, job `backend-test`, step `pytest -p no:randomly tests/performance -m budget`. | Passes on the GitHub-hosted runner. |

### TC-079-02 Full performance suite passes all budgets and writes `build/performance.json`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest -p no:randomly tests/performance -m performance` | Exit 0; all tests pass (TST-120..TST-124, API-120, API-124/NFR-006, TST-190, TDV-008 checks). |
| 2 | Read `build/performance.json`. | Keys `generated_at` (UTC), `git_sha`, `budgets`, `info`; every budget `passed: true`. |
| 3 | Check budget values. | TST-121 (200 samples) p95 ≤ 1000 ms; each TST-122 endpoint p95 ≤ 500 ms; TST-124 202 ≤ 2000 ms and processed ≤ 30000 ms; TST-123 DS-08 rebuild ≤ 120000 ms; SRC-05 rebuild ≤ 30000 ms; health p95 ≤ 200 ms. |
| 4 | Latest scheduled `e2e.yml` run, job `performance`; download artifact `performance-report`. | Job passed; artifact holds `build/performance.json` with the same structure. |

### TC-079-03 DS-08 generator is deterministic: identical files, 10,800 records, `L001`..`L100`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `python tests/performance/make_load_dataset.py --seed 20261004 --out /tmp/ds08a` and again with `--out /tmp/ds08b`. | Both exit 0; each writes `ds08_sessions.csv`, `facilities.csv`, `residents.csv`, `devices.csv`, `device_assignments.csv`. |
| 2 | `diff -r /tmp/ds08a /tmp/ds08b && echo identical` | `identical`. |
| 3 | `tail -n +2 /tmp/ds08a/ds08_sessions.csv | wc -l` | `10800`. |
| 4 | `pytest -q tests/performance/test_load_dataset.py -k deterministic` | Pass: 100 distinct resident codes `L001`..`L100`, devices `LD001`..`LD100`, first day 20260601, last 20260928, 540 records with `mic_noise_level_dbfs` `-32.0`, every record at 14:xx America/Chicago. |
| 5 | Run with `--seed 20261005`. | Output differs from seed 20261004. |

### TC-079-04 Lighthouse on `/residents` (and the other three pages): Performance ≥ 80, LCP ≤ 2.5 s

| Step | Action | Expected Result |
|---|---|---|
| 1 | `cat frontend/lighthouserc.json` | URLs `http://localhost:3001/residents`, `/residents/R09`, `/residents/R09/trends`, `/study`; preset `desktop`; `numberOfRuns` 3; `puppeteerScript` `./tests/lighthouse/login.js`; assertions `categories:performance` minScore 0.8 and `largest-contentful-paint` ≤ 2500 ms (median run). |
| 2 | With the seeded demo stack: `cd frontend && npx --yes -p @lhci/cli@0.14.x -p puppeteer@23 lhci autorun`. | Scripted admin login succeeds; all assertions pass; results written to `build/lighthouse`. |
| 3 | Open the `/residents` report in `build/lighthouse`. | Performance score ≥ 80; LCP ≤ 2.5 s. |
| 4 | On a recent PR, open the `lighthouse` job of `e2e.yml`. | Passed; artifact `lighthouse-report`. |

### TC-079-05 PR-scope budgets TST-120, TST-121 (50 requests), TST-124 pass in `backend-test`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open any recent PR run of `ci.yml`, job `backend-test`, step `pytest -p no:randomly tests/performance -m budget`. | 3 tests passed. |
| 2 | Read the uploaded `backend-reports` → `build/performance.json`. | TST-121 `samples` 50 and `passed` true; TST-120 and TST-124 `passed` true. |

### TC-079-06 `git ls-files tests/performance` lists no generated dataset

| Step | Action | Expected Result |
|---|---|---|
| 1 | `git ls-files tests/performance` | Only `.py` files (`conftest.py`, `make_load_dataset.py`, `test_api_latency.py`, `test_ingest_sustained.py`, `test_load_dataset.py`, `test_pipeline_runtime.py`, `__init__.py` if present); no `.csv`, `.json`, `.xlsx`, `.parquet`, `.gz`. |
| 2 | `pytest -q tests/performance/test_load_dataset.py -k no_generated_dataset` | Pass. |

### TC-079-07 Read endpoints p95 ≤ 500 ms on DS-08 and `/health` p95 ≤ 200 ms

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest -p no:randomly tests/performance/test_api_latency.py -m performance -k "read_endpoints or health"` | Passes for `/residents`, `/residents/L001`, `/scores?resident_code=L001`, `/alerts`, `/data-alerts`, `/analytics` and `/health`. |
| 2 | Read `build/performance.json`. | 100 warm samples per read endpoint, each p95 ≤ 500 ms; health p95 ≤ 200 ms; endpoints warmed before sampling. |

### TC-079-08 Sustained ingest 10 records/s for 60 s: only 201/200 responses

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest -p no:randomly tests/performance/test_ingest_sustained.py -m performance` | `test_sustained_10_records_per_second_for_60_s` passes (about 600 requests with one API key). |
| 2 | Check the test output / `build/performance.json`. | No 429 and no 5xx; every response 201 or 200. |

### TC-079-09 Initial JavaScript per dashboard route ≤ 300 KB gzip

| Step | Action | Expected Result |
|---|---|---|
| 1 | After `npm run build` in `frontend/`, run `npm run check:bundle`. | Exit 0; every `(protected)` route (`/residents`, `/residents/[residentCode]` and sections, `/admissions`, `/study`, `/admin`) ≤ 300 KB gzip. |
| 2 | `node ../scripts/ci/check-bundle.mjs --budget-kb 50` | Exit 1 naming the routes above 50 KB (shows the check fails on a breach). |

### TC-079-10 A budget breach fails with measured p95 and budget, recorded `passed: false`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Locally lower one budget constant in `tests/performance/test_pipeline_runtime.py` (`PIPELINE_BUDGET_MS = 5_000` → `1`); run `pytest -p no:randomly tests/performance -m budget -k src05`. | Test fails; message contains the measured value and the budget. |
| 2 | Read `build/performance.json`. | TST-120 `passed: false` with `measured_ms` and `budget_ms`. |
| 3 | Revert the change (`git checkout -- tests/performance/test_pipeline_runtime.py`). | Working tree clean. |

### TC-079-11 Nightly run records DS-08 database size for the NFR-152 projection

| Step | Action | Expected Result |
|---|---|---|
| 1 | After TC-079-02, read `info` in `build/performance.json`. | `ds08_db_size_bytes` and `nfr152_projection_bytes` present. |
| 2 | Compare the projection with 2 GB (100 residents × 3 years). | `nfr152_projection_bytes` ≤ 2,147,483,648. |

### TC-079-12 Performance modules are deselected from a plain `pytest` run

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest -q --collect-only tests | grep -c "tests/performance"` | `0` (deselected, not skipped; TST-153). |
| 2 | `pytest -q --collect-only tests/performance -m performance | tail -1` | Performance tests collected. |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `POST /api/v1/sessions` (TST-121, throwaway stack) | 201; p95 ≤ 1,000 ms over 200 (nightly) / 50 (PR) requests |
| 2 | `GET /api/v1/residents`, `/residents/L001`, `/scores`, `/alerts`, `/data-alerts`, `/analytics` on DS-08 | 200; p95 ≤ 500 ms each |
| 3 | `POST /api/v1/ingest` with SRC-05 | 202 in ≤ 2 s; batch run `succeeded` in ≤ 30 s |
| 4 | `GET /api/v1/health` | 200; p95 ≤ 200 ms |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | DS-08 throwaway database after rebuild (TST-123): `SELECT count(*) FROM raw_sessions;` (recorded as `ds08_raw_sessions`) | 10,800 |
| 2 | `pipeline_runs.counts` of the DS-08 rebuild | Includes the run counts; `db_size_bytes` recorded for nightly runs (DB-049) |
| 3 | After the suite, list databases on the test server | Throwaway performance databases removed; no DS-08 data in any other database (TDV-007) |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Lowered budget (TC-079-10) | Test fails with measured value and budget; `passed: false` |
| 2 | Bundle budget 50 KB (TC-079-09) | `check:bundle` exits 1 |
| 3 | Different seed (TC-079-03 step 5) | Different dataset (determinism tied to the seed) |
| 4 | Plain `pytest` (TC-079-12) | Performance tests not collected |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-079-AC-01 | `pytest -m budget` passes with the SRC-05 pipeline run ≤ 5 s on a GitHub-hosted runner | TC-079-01 |
| FEAT-079-AC-02 | `pytest tests/performance -m performance` passes all budgets and writes `build/performance.json` | TC-079-02, TC-079-07 |
| FEAT-079-AC-03 | `make_load_dataset.py --seed 20261004` twice yields identical files with 10,800 records for `L001`..`L100` | TC-079-03 |
| FEAT-079-AC-04 | Lighthouse CI on `/residents` of the seeded demo stack reports Performance ≥ 80 and LCP ≤ 2.5 s | TC-079-04 |
| FEAT-079-AC-05 | PR-scope budgets TST-120, TST-121 (50 requests), TST-124 pass | TC-079-05 |
| FEAT-079-AC-06 | `git ls-files tests/performance` lists no generated dataset file | TC-079-06 |

## Test Data Requirements

- DS-08 generated at run time (seed 20261004, synthetic `L`-prefixed study IDs), never committed; SRC-05 `tests/fixtures/pipeline_input/EchoWell_pipeline_test_input_v0_1.csv`.
- `test_v0_1` seed with R09 for Lighthouse pages.
- Environment: optional TEST_SUPERUSER_URL (throwaway server only), `SEED_ADMIN_PASSWORD` for the Lighthouse login, `NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_APP_ENV`.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-079-FR-01 / TDV-008, DS-08 | FEAT-079 | TC-079-03, TC-079-06 |
| FEAT-079-FR-02 / TST-120, ANL-047, NFR-005 | FEAT-079 | TC-079-01 |
| FEAT-079-FR-03 / TST-121, API-122, NFR-004 | FEAT-079 | TC-079-02, TC-079-05 |
| FEAT-079-FR-04 / TST-122, API-121, NFR-001..NFR-003 | FEAT-079 | TC-079-07 |
| FEAT-079-FR-05 / TST-123, ANL-048, NFR-007 | FEAT-079 | TC-079-02 |
| FEAT-079-FR-06 / TST-124, API-123, NFR-009 | FEAT-079 | TC-079-01, TC-079-02 |
| FEAT-079-FR-07 / API-124, NFR-006 | FEAT-079 | TC-079-02 |
| FEAT-079-FR-08 / API-120 | FEAT-079 | TC-079-07 |
| FEAT-079-FR-09 / TST-126 | FEAT-079 | TC-079-05, TC-079-12 |
| FEAT-079-FR-10 / TST-125, NFR-010, CIC-116 | FEAT-079 | TC-079-04 |
| FEAT-079-FR-11 / CIC-035 | FEAT-079 | TC-079-02, TC-079-10 |
| FEAT-079-FR-12 / TDV-007 | FEAT-079 | TC-079-02 (Preconditions), Database Validation step 3 |
| FEAT-079-FR-13 / NFR-152, DB-049 | FEAT-079 | TC-079-11 |
| FEAT-079-FR-14 / TST-190, NFR-151 | FEAT-079 | TC-079-08 |
| FEAT-079-FR-15 / TST-191, NFR-012 | FEAT-079 | TC-079-09 |
