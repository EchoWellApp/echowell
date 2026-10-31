# Checkpoint 5 Report — Phase 11 Implement Analytics Engine

Block 3 "Implement Features", checkpoint 5 of 9, its own PR (branch `feat/cp5-analytics-engine`, created from `main` after GitHub PR #18 was merged on 30 October 2026) · Prompt: `specs/prompts/Implement_Feature_Batches.md` "Phase 11: Implement Analytics Engine" · TRD 25 Phase 6 · Features: FEAT-040..FEAT-056, plus FEAT-038-FR-10 carried over from checkpoint 4 (D-128) · Date: 31 October 2026 · Status: in review.

Build order followed roadmap §5.5: [FEAT-040..FEAT-043] → [FEAT-044..FEAT-047] → [FEAT-048..FEAT-052] → [FEAT-053..FEAT-056]. TRDs read in the roadmap order: 07, 08, 09, 10, 06, 20, 23, 24; then SRC-04 and the SRC-03 Parameters sheet, for the rules only.

The engine is plain arithmetic (medians, MADs, z-scores, CUSUM) on numeric voice features. It uses no machine learning, no language model and no audio. All data is synthetic test data.

## 1. What was built

The stage-by-stage account and the answer-key check are in `docs/reports/ANALYTICS_IMPLEMENTATION_REPORT.md`. In short:

| Group | Features | Delivered |
|---|---|---|
| 1 | FEAT-040..FEAT-043 | Engine contracts (frozen dataclasses), `PipelineConfig` with the `production` and `test_v0_1` profiles and a hash over the algorithm keys only (D-56), robust statistics, duplicates, quality gate, epochs, local time and morning adjustment |
| 2 | FEAT-044..FEAT-047 | Speaker screen, baseline build and freeze, late arrivals, z-scores, composite, CUSUM |
| 3 | FEAT-048..FEAT-052 | Alerts and "Leaning most", day ledger, the four data-alert rules, the Analytics page aggregates, `run_pipeline` (pure, deterministic), `scripts/run_engine.py` |
| 4 | FEAT-053..FEAT-056 | The analytics executor (per-resident transactions, natural-key upserts, rebuild), ingest-triggered and nightly runs, the `run-pipeline`, `rebuild` and `set-config` commands, the full `seed test_v0_1`, run logging |
| Carried over | FEAT-038-FR-10 | The 26 TRD 19 §4.3 JSON examples attached to the OpenAPI document and validated against their schemas |

What changes for users of the API:

- `GET /analytics` now returns real KPI tiles, funnel, by-resident and by-day blocks, and `GET /alerts` returns `leaning_most`; both were empty in checkpoint 4 (D-92).
- Every ingest starts a pipeline run, so a new check-in is scored within seconds.
- The test site can be rebuilt from scratch with one command, `seed test_v0_1`.

## 2. Files

**Filled** (empty skeleton modules from checkpoint 2):
- `analytics/` (16 modules).

**Created:**
- `backend/services/pipeline_persistence.py` and `engine_read.py`;
- `backend/api/openapi_examples.json`;
- `database/seeds/test_v0_1/EchoWell_pipeline_test_input_v0_1.csv`, a copy of SRC-05 (Q-2);
- `tests/unit/analytics/` (20 modules);
- `tests/integration/pipeline/test_runner_persistence.py` and `test_nightly_run.py`;
- `tests/integration/test_cli_pipeline.py`;
- `tests/contract/test_openapi_examples.py`;
- this report and `ANALYTICS_IMPLEMENTATION_REPORT.md`.

**Changed:**
- `backend/services/pipeline_runner.py` (the analytics executor is now the default), `config_service.py`, `ingestion.py`, `alert_service.py`, `analytics_summary.py`, `resident_service.py`;
- `backend/repositories/pipeline_run_repository.py` and `read_models.py`;
- `backend/jobs/nightly_run.py`, `backend/cli.py`, `backend/api/openapi.py`, `backend/api/deps.py`;
- `scripts/run_engine.py`;
- `docs/api_reference/openapi.json` (regenerated);
- `tests/integration/world.py` (date fix, N-1);
- checkpoint 4 tests that assumed every run fails;
- `tests/integration/db/test_read_models.py` (FEAT-014 seed values, N-3);
- `frontend/package-lock.json` (N-2);
- `BACKLOG.md` §10, roadmap §2.1, the FEAT-040..FEAT-056 Status fields.

**Size:** about 8,400 added lines.
- 3,300 are generated or copied data: `openapi.json`, the SRC-05 copy, the examples file and the lockfile.
- The remaining 5,100 are hand-written: 1,960 in `analytics/`, 1,350 in the backend and scripts, and 1,820 in tests.

## 3. Tests added

| Area | Files | Covers |
|---|---|---|
| Stages | `tests/unit/analytics/test_<module>.py` (one per module, TST-011) | Every pitfall AGT-040..AGT-062 that applies to the stage: DST conversion, even-count median, MAD floors, arrival-order duplicates, first-N speaker screen, epoch keys, missing days, CUSUM on non-usable days, alarm persistence, reason order |
| Orchestrator | `test_pipeline.py`, `test_run_engine.py` | SRC-05 counts; two runs give the same result in any record order (AGT-021); as-of filter; late arrival leaves the frozen baseline unchanged; ≤ 5 s |
| Persistence | `tests/integration/pipeline/test_runner_persistence.py` | Full run on PostgreSQL equals the engine output; a second run changes nothing; reviews and snoozes survive (AGT-056); one failing resident is rolled back alone; the analytics and alerts endpoints after a run |
| Nightly job | `test_nightly_run.py` | One run per local night across the 1 Nov 2026 DST change (AGT-059); missed night reported; schema check |
| CLI and seed | `tests/integration/test_cli_pipeline.py` | Full seed; `run-pipeline`; `set-config` → refused run → `rebuild`; rebuild reproduces identical derived tables |
| Read models | `tests/integration/db/test_read_models.py` | FEAT-014-AC-01..AC-07 and AC-09 on the full seed (were skipped until now) |
| Contract | `tests/contract/test_openapi_examples.py` | The 26 examples equal TRD 19 §4.3 (except the four completed ones, Q-9) and validate against their schemas |

## 4. Commands run and results

Environment: Linux container, Python 3.12 (virtualenv), PostgreSQL 16 (local cluster provisioned with `database/roles/provision_login_roles.sql`).

| # | Command | Result |
|---|---|---|
| 1 | `pytest tests/unit tests/integration tests/contract tests/security tests/validation`, random order, with `--cov=analytics --cov=backend --cov-branch` | 561 passed, 0 skipped (4 min 16 s). Coverage of `analytics` and `backend` together 97 % |
| 2 | `pytest tests/unit --cov=analytics --cov-branch` | 245 passed; `analytics/` 97 % (target 95 %, TST-140) |
| 3 | `pytest tests/integration -q -k pipeline` | 27 passed |
| 4 | `ruff check .`; `ruff format --check .`; `mypy analytics backend`; `lint-imports` | all exit 0; 3 import contracts kept |
| 5 | `python -m backend.jobs.nightly_run` at 21:54 local | exit 0 without running (outside 02:xx); logs `schema_revision_unreadable` (Q-1) and `nightly_run_missing` (no run on the empty development database) |
| 6 | `python scripts/run_engine.py` on the `database/seeds/test_v0_1` files, as of 2026-10-30 15:00 | 14 JSON files: 283 arrivals, 267 usable, 98 scored, 180 baselines, alerts R09 and R10, 4 data alerts; 0.06 s in the engine |
| 7 | Engine result compared with the SRC-03 workbook by a one-off script outside the repository (AGT-007) | 302 annotated rows, 180 baselines, 98 scores, 4 data alerts, KPIs, funnel and by-resident percentages: 0 mismatches |
| 8 | `grep -rn "evaluation_ground_truth" analytics` | no match (AGT-057) |
| 9 | `npm ci --dry-run` in `frontend/` | fails on `main` (lockfile out of date); passes on this branch (N-2) |
| 10 | Case-insensitive grep for the forbidden facility name (AGT-019) | no match |

## 5. Exit criteria (roadmap §5.5)

| Criterion | Evidence | Result |
|---|---|---|
| Stage order matches TRD 07; each stage is a pure function with unit tests | `analytics/pipeline.py`; one test module per stage; `lint-imports` keeps `analytics` free of backend and I/O imports | PASS |
| A full rebuild from `raw_sessions` reproduces identical derived tables | `test_rebuild_reproduces_identical_derived_tables` | PASS |
| Profiles load from `config_parameters`; each run stores its config snapshot and git SHA (AGT-020) | `test_full_run_on_src05` (snapshot, hash); `test_set_config_then_rebuild` | PASS |
| `analytics/` line coverage ≥ 95 % (D-39) | item 2 | PASS (97 %) |
| Pipeline on the test input ≤ 5 s (D-40) | `test_src05_runs_within_five_seconds`, `test_run_engine_on_the_seed_files` | PASS (0.06 s) |
| `grep -rn "evaluation_ground_truth" analytics` returns nothing (AGT-057) | item 8 | PASS |
| Data-alert rules give exactly R08 baseline stuck, R05 other speaker, R03 set aside, D02 silent Oct 12 | `test_full_run_on_src05`, `test_data_alerts.py` | PASS |
| Nightly job frozen-clock test across the 1 Nov 2026 DST change | `test_one_run_per_local_night_across_dst` | PASS |
| Definition of Done of every feature | feature files FEAT-040..FEAT-056 | PASS, apart from the questions below |
| CI green on the PR head | needs the PR | PENDING |
| Algorithm lead approves and merges (D-101) | review | PENDING |

## 6. New OQ and D IDs

None. Decisions from this review will be recorded in TRD 24 with the next free numbers (from D-129).

## 7. Deviations and notes

| # | Note | Handling |
|---|---|---|
| N-1 | `main` CI has failed since 30 October. A test fixture stamped pipeline runs with today's date, and once today passed the test as-of (30 Oct 20:00 UTC), the database's `started_at ≤ as_of` check rejected them | `tests/integration/world.py` now starts runs no later than the as-of. The pipeline runner also takes `started_at` from the application clock (Q-6) |
| N-2 | Commit `f340545` on `main` ("Fix Netlify deploy") added `@netlify/plugin-nextjs` to `frontend/package.json` without updating `package-lock.json`, so `npm ci` and the frontend CI job fail | Lockfile regenerated with `npm install --package-lock-only` (11 lines, no other change) |
| N-3 | The FEAT-014 seed-value test looked for a seed file that never existed, so it was always skipped | It now seeds a throwaway database and checks FEAT-014-AC-01..AC-07 and AC-09; all values match |
| N-4 | `rebuild` deletes frozen baselines, which the application role may not do (TRD 20 §4.8) | The command runs as `echowell_migrator`, like `seed` (Q-10) |
| N-5 | `test_alerts.py` expected `leaning_most: []` (checkpoint 4 placeholder) | Now the engine value. The fixture's z-scores are all equal, so the three up-signed features tie and appear in canonical order (CUS-041) |
| N-6 | `scripts/run_engine.py` reads residents and assignments as JSON or CSV | The seed files can be used directly |

## 8. Questions for the reviewer

| ID | Question |
|---|---|
| Q-1 | The nightly job should refuse to run when the database schema is not the one bundled with the code (DEP-048). The application role cannot read `alembic_version` (TRD 20 §4.8 grants it nothing), so the job only logs `schema_revision_unreadable`. Grant `SELECT ON alembic_version TO echowell_app` (a new migration), or keep the warning? |
| Q-2 | The full seed reads SRC-05 from a copy at `database/seeds/test_v0_1/EchoWell_pipeline_test_input_v0_1.csv` (the Docker image does not contain `specs/`). Is that the right place? |
| Q-3 | A `device_silent` data alert stores no list of days. For `GET /analytics`, the days are read back from its detail text ("Oct 12"). Keep that, or add a `days` column to `data_alerts` (a new migration)? |
| Q-4 | Withdrawn residents are left out of data alerts and the KPI and funnel totals, and their ledger stops at `withdrawn_on`. Correct? |
| Q-5 | FEAT-056-FR-07 ("retry a failed run once, at the next ingest or nightly trigger"): every ingest and every night already starts a fresh run, so no separate retry counter is kept. Enough? |
| Q-6 | `pipeline_runs.started_at` now comes from the application clock instead of the database's `now()`, so the nightly de-duplication and the tests agree on the time. Agree? |
| Q-7 | This PR also fixes two failures that are on `main` (N-1, the test date; N-2, the frontend lockfile). Keep them here, or move them to a separate small PR? |
| Q-8 | The automated SRC-03 workbook comparison belongs to FEAT-057/FEAT-058 (checkpoint 6). Here the comparison was a one-off script, reported in section 4, item 7. Agree? |
| Q-9 | Four TRD 19 §4.3 examples are abbreviated and do not validate as written. I completed them in the examples file: E-05 R03 response (`"..."` ids → UUIDs), E-10 (null fields added), E-11 (all 7 features, from the engine output), E-19 (`meta` written out). Update TRD 19 §4.3 to match? |
| Q-10 | `rebuild` runs as `echowell_migrator`, because only the table owner may delete frozen baselines (N-4). Agree? |
| Q-11 | Size: about 5,100 hand-written lines (1,960 engine, 1,350 backend, 1,820 tests) for 17 features. Accept as one PR, as for checkpoints 3 and 4? |
