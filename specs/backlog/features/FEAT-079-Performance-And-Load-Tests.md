# FEAT-079 Performance and load tests (DS-08, latency budgets, Lighthouse)

| Field | Value |
|---|---|
| Epic | Testing & Validation |
| Build phase | Phase 9 (TRD 25) |
| Priority | P1 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-054, FEAT-077 |
| Status | Not Started |

## Purpose

Verify the contract R8 performance budgets automatically: generate the deterministic load dataset DS-08 (100 residents × 120 days, 10,800 records) and test the pipeline runtime, `POST /api/v1/sessions` latency including the synchronous per-resident pipeline, read-endpoint latency at 100 residents, batch-ingest timing, the full rebuild of DS-08, and the frontend's Lighthouse score on `/residents`. The budgets protect the demo experience (a check-in appears within seconds) and show the design holds at the ASM-08 scale.

## Business Context

- BR-12, BR-13: overview and detail pages respond within budget (NFR-001..NFR-003, NFR-010).
- BR-01 and SRC-15 demo step 4: `POST /api/v1/sessions` p95 ≤ 1,000 ms including the pipeline (NFR-004).
- BR-15: pipeline on the test input ≤ 5 s and full rebuild budgets (NFR-005..NFR-007).
- ASM-08 (< 25 users, < 100 residents, < 1 session per resident per day) and RSK-07 (free-tier limits).

## Referenced TRDs

- TRD 13 TST-120, TST-121, TST-122, TST-123, TST-124, TST-125, TST-126, TST-006 (`performance`, `budget` markers), §4.1 tooling row "Performance".
- TRD 05 API-120, API-121, API-122, API-123, API-124, API-125.
- TRD 07 ANL-047, ANL-048, ANL-049, ANL-050.
- TRD 03 NFR-001..NFR-013, NFR-150, NFR-151, NFR-152, NFR-153.
- TRD 14 DS-08, TDV-007, TDV-008.
- TRD 06 DB-048, DB-049.
- TRD 16 CIC-035, CIC-036, CIC-116 (jobs wired by FEAT-080), §4.10 `performance-report` artifact.
- TRD 24 D-40, ASM-08.

## Scope

- `tests/performance/make_load_dataset.py --seed 20261004`: resident codes `L001`..`L100`, devices `LD001`..`LD100`, start 2026-06-01, one record per resident-day between 14:00 and 15:00 local, 10 % of resident-days dropped (10,800 records), 5 % with `mic_noise_level_dbfs` −32.0, feature values drawn as SRC-04 `make_values`; plus the matching roster CSVs in the TRD 06 DB-060 format; generated at test time, never committed.
- `tests/performance/test_pipeline_runtime.py`: TST-120 (≤ 5 s, marker `budget` so it also runs in `backend-test`, CIC-036) and TST-123 (DS-08 full rebuild ≤ 120 s).
- `tests/performance/test_api_latency.py`: TST-121 (200 sequential `POST /api/v1/sessions` for a resident with 120 days of history, p95 ≤ 1,000 ms; 50 requests on PRs), TST-122 (100 requests each on `GET /api/v1/residents`, `/residents/{resident_code}`, `/scores`, `/alerts`, `/data-alerts`, `/analytics`, p95 ≤ 500 ms on DS-08), TST-124 (`POST /api/v1/ingest` with SRC-05 returns 202 in ≤ 2 s; batch run `succeeded` in ≤ 30 s), API-120 (`GET /health` p95 ≤ 200 ms).
- `build/performance.json` with p95 timings per budget (artifact `performance-report`).
- Lighthouse CI configuration (`@lhci/cli` 0.14.x, desktop preset) and the scripted login `frontend/tests/lighthouse/login.js` for `/residents` of the seeded Compose `demo` stack: Performance ≥ 80, LCP ≤ 2.5 s (TST-125).

## Out of Scope

- The `e2e.yml` jobs that schedule these tests (`performance`, `lighthouse`; FEAT-080) and the `backend-test` wiring of the `budget` marker (FEAT-078).
- Correctness claims on DS-08 (performance only, TRD 14 DS-08 row).
- Load beyond ASM-08 (NFR-153: treated as a design change, not a defect).
- External load tools: TRD 03 NFR-001 names "k6 or Locust" as examples, TRD 13 fixes pytest with `time.perf_counter`; this feature uses the TRD 13 tooling.

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-079-FR-01 | `make_load_dataset.py` shall generate DS-08 deterministically from seed 20261004 with the TDV-008 rules and shall not write it into the repository. | TDV-008, DS-08 |
| FEAT-079-FR-02 | A full `test_v0_1` run of `analytics.pipeline.run_pipeline` on SRC-05 (283 arrivals) shall complete in ≤ 5 s; the test carries markers `performance` and `budget`. | TST-120, ANL-047, NFR-005, CIC-036 |
| FEAT-079-FR-03 | `POST /api/v1/sessions` including the synchronous per-resident pipeline shall have p95 ≤ 1,000 ms over 200 sequential requests (50 on PRs) for a resident with 120 days of history on a local PostgreSQL 16 container. | TST-121, API-122, ANL-049, NFR-004, TST-126 |
| FEAT-079-FR-04 | `GET /api/v1/residents`, `GET /api/v1/residents/{resident_code}`, `GET /api/v1/scores`, `GET /api/v1/alerts`, `GET /api/v1/data-alerts` and `GET /api/v1/analytics` shall each have p95 ≤ 500 ms over 100 warm requests on DS-08. | TST-122, API-121, NFR-001, NFR-002, NFR-003 |
| FEAT-079-FR-05 | A full rebuild on DS-08 shall complete end to end (load, compute, write) in ≤ 120 s (nightly). | TST-123, ANL-048, API-124, NFR-007 |
| FEAT-079-FR-06 | `POST /api/v1/ingest` with SRC-05 as CSV shall return 202 in ≤ 2 s and its batch pipeline run shall reach `succeeded` in ≤ 30 s. | TST-124, API-123, NFR-009 |
| FEAT-079-FR-07 | A full rebuild of SRC-05 including database writes shall complete in ≤ 30 s. | API-124, NFR-006 |
| FEAT-079-FR-08 | `GET /api/v1/health` p95 latency shall be ≤ 200 ms. | API-120 |
| FEAT-079-FR-09 | PR runs shall execute TST-120, TST-121 with 50 requests and TST-124; TST-121 with 200 requests, TST-122 and TST-123 run nightly. | TST-126 |
| FEAT-079-FR-10 | Lighthouse CI (desktop preset) on `/residents` of the seeded Compose `demo` stack built from the PR shall report Performance ≥ 80 and LCP ≤ 2.5 s, after a scripted login. | TST-125, NFR-010, CIC-116 |
| FEAT-079-FR-11 | The performance suite shall write `build/performance.json` with the measured p95 per budget and fail when any budget is exceeded. | CIC-035, TRD 16 §4.10 |
| FEAT-079-FR-12 | DS-08 and test fixture data shall never be loaded into a database that holds real records. | TDV-007 |
| FEAT-079-FR-13 | The nightly run shall record the DS-08 database size so the NFR-152 projection (100 residents × 3 years ≤ 2 GB) can be computed from it. | NFR-152, DB-049 |

## Inputs

- SRC-05 fixture `tests/fixtures/pipeline_input/EchoWell_pipeline_test_input_v0_1.csv`.
- DS-08 generated at test time; the SRC-04 `make_values` rules as described in TDV-008 (the generator script is read for rules only, never imported from `analytics/` or `backend/`, TRD 25 §8).
- A PostgreSQL 16 container (`postgres:16-alpine` service in CI) and the backend with the ingest-triggered and nightly runs of FEAT-054.
- Seeded Compose `demo` stack (FEAT-077) for Lighthouse.

## Outputs

- `tests/performance/make_load_dataset.py`, `test_pipeline_runtime.py`, `test_api_latency.py`, `conftest.py` (DS-08 fixture, timing helpers).
- `frontend/lighthouserc.json` (or `.lighthouserc.js`) and `frontend/tests/lighthouse/login.js`.
- `build/performance.json`, Lighthouse report under `build/` (artifacts, never committed).

## Data Flow

Seed 20261004 → `make_load_dataset.py` → CSV + roster in a temp directory → `import-master-data` and `POST /api/v1/ingest` (or direct service calls) into the test database → `POST /api/v1/pipeline/run` scope all (rebuild timing) → timed HTTP requests through `httpx` `TestClient` or the running backend → p95 computed with `time.perf_counter` samples → compared with budgets → `build/performance.json`. Lighthouse: Compose `demo` stack seeded with DS-07 → scripted login → `/residents` audited.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-054, FEAT-077

- [FEAT-054](FEAT-054-Ingest-Triggered-And-Nightly-Pipeline-Runs.md) Ingest-triggered and nightly pipeline runs (synchronous per-resident run measured by TST-121).
- [FEAT-077](FEAT-077-Production-Container-Images-Compose-Demo-Profile.md) Production images and Compose `demo` profile (Lighthouse target).

## Database Impact

- Tables used: `residents`, `devices`, `device_assignments`, `raw_sessions`, `ingest_batches`, `processed_sessions`, `epochs`, `baselines`, `scores`, `cusum_state`, `alerts`, `data_alerts`, `day_ledger`, `pipeline_runs` on an ephemeral test database.
- Tables created or modified: none. DB-048 states the schema needs no partitioning for this load; the test confirms it within budget.

## API Impact

- Consumed: `POST /api/v1/sessions`, `POST /api/v1/ingest`, `GET /api/v1/ingest/batches/{id}`, `POST /api/v1/pipeline/run`, `GET /api/v1/pipeline/runs/{id}`, `GET /api/v1/residents`, `GET /api/v1/residents/{resident_code}`, `GET /api/v1/scores`, `GET /api/v1/alerts`, `GET /api/v1/data-alerts`, `GET /api/v1/analytics`, `GET /api/v1/health`.
- Exposed: none.

## Frontend Impact

- Lighthouse audit of `/residents` (no code change); a failing score is an S3 defect (TRD 13 §4.16 "Lighthouse below target").

## Analytics Impact

- Measures `run_pipeline` on SRC-05 and a full rebuild on DS-08; ANL-050 complexity limits are the expected cause of any regression. No algorithm change.

## Security Requirements

- Test credentials (admin JWT, API key with `ingest:write`) are created per run in the ephemeral database; no secret is committed (CIC-026).
- DS-08 is synthetic; residents are `L`-prefixed study IDs (AGT-017).
- Rate limits: TST-121 stays under RATE_LIMIT_INGEST 600/minute; tests set limits explicitly where needed.

## Error Handling

- Each budget test fails with the measured p95 and the budget in its message.
- A timeout waiting for a batch run (30 s) or rebuild (120 s) fails the test and records the elapsed time in `build/performance.json`.
- Cold starts are excluded: latency tests warm each endpoint before sampling ("warm" in NFR-001..NFR-004).

## Logging Requirements

- No new application logs. The suite reads `pipeline_runs.counts` (including `db_size_bytes` from nightly runs, DB-049) where useful and writes its own JSON report.

## Testing Requirements

- Performance tests: TST-120..TST-126 under marker `performance`; TST-120 also `budget`.
- Command: `pytest tests/performance -m performance` (nightly, CIC-035); `pytest -m budget` within `backend-test` (CIC-036).
- Lighthouse: `npx @lhci/cli@0.14 autorun` against `http://localhost:3001/residents` (CIC-116).
- Regression: the DS-08 generator run twice with seed 20261004 produces byte-identical CSVs.

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-079-AC-01 | `pytest -m budget` passes with the SRC-05 pipeline run ≤ 5 s on a GitHub-hosted runner. | TST-120, ANL-047 |
| FEAT-079-AC-02 | `pytest tests/performance -m performance` passes all budgets (sessions p95 ≤ 1,000 ms, reads p95 ≤ 500 ms, ingest 202 ≤ 2 s and processed ≤ 30 s, DS-08 rebuild ≤ 120 s) and writes `build/performance.json`. | AC-CIC-10, TST-121..TST-124 |
| FEAT-079-AC-03 | `make_load_dataset.py --seed 20261004` run twice yields identical files containing 10,800 records for `L001`..`L100`. | TDV-008 |
| FEAT-079-AC-04 | Lighthouse CI on `/residents` of the seeded `demo` stack reports Performance ≥ 80 and LCP ≤ 2.5 s. | TST-125 |
| FEAT-079-AC-05 | PR-scope budgets TST-120, TST-121 (50 requests) and TST-124 pass. | AC-TST-08, TST-126 |
| FEAT-079-AC-06 | `git ls-files tests/performance` lists no generated dataset file. | TDV-008 |

## Definition of Done

- All FEAT-079 acceptance criteria pass locally against `postgres:16`; test modules carry exactly one level marker (TST-006).
- `build/performance.json` format documented in the module docstring.
- Batch report lists measured p95 values (AGT-022).

## Implementation Notes

- Use one session-scoped PostgreSQL container and load DS-08 once per session; keep DS-08 in a temporary directory.
- Measure p95 with `statistics.quantiles(samples, n=100)[94]` over the sample list; report milliseconds.
- TST-121 needs a resident with 120 days of history: pre-load 119 records for that resident, then time the POSTs with fresh session IDs and increasing timestamps.
- TRD gaps to note in the batch report: NFR-151 (10 records/s for 60 s) and NFR-012 (≤ 300 KB initial JavaScript) have no TRD 13 test ID; NFR-010 names four pages while TST-125 audits only `/residents`; TST-120 and ANL-047 say `ubuntu-latest` while CIC-027 fixes `ubuntu-24.04` (use `ubuntu-24.04`).
