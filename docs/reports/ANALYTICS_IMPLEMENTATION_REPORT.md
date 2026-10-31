# Analytics Implementation Report

Block 3 checkpoint 5 · Prompt: `specs/prompts/Implement_Feature_Batches.md` "Phase 11: Implement Analytics Engine" · TRD 25 Phase 6 · Features FEAT-040..FEAT-056 · Branch `feat/cp5-analytics-engine` · 31 October 2026.

This report covers the engine itself: the pure `analytics/` package, how the backend runs and stores it, and how its output was checked against the answer key. The checkpoint summary, the exit criteria and the questions for the reviewer are in `docs/reports/CHECKPOINT_5_ANALYTICS_ENGINE.md`.

The engine is plain arithmetic on 19 numeric voice features per check-in: medians, MADs, z-scores, a composite and a one-sided CUSUM. It uses no machine learning, no language model and no audio. It runs on synthetic test data only.

## 1. Summary

| Prompt item | Delivered | Where |
|---|---|---|
| Pipeline stages as pure functions | 16 modules, one per stage of TRD 07 §4.2, each a pure function of frozen dataclasses (no I/O, no clock, no database) | `analytics/` |
| One entry point | `run_pipeline(records, residents, assignments, config, as_of, frozen=None) -> PipelineResult`; equal inputs give an equal result whatever the record order (ANL-020) | `analytics/pipeline.py` |
| Profiles | `production` (baseline 30) and `test_v0_1` (baseline 16), loaded from `config_parameters`; `config_hash` covers the algorithm keys only (D-56) | `analytics/config.py`, `backend/services/config_service.py` |
| Persistence | Per-resident transactions under a resident lock; natural-key upserts for alerts and data alerts (D-45); reviews and snoozes survive reruns | `backend/services/pipeline_persistence.py`, `pipeline_runner.py` |
| Triggers | After every ingest, nightly at 02:xx local (DST-safe, one run per night, D-47, D-70), manual (`POST /pipeline/run`, CLI) | `backend/services/ingestion.py`, `backend/jobs/nightly_run.py`, `backend/cli.py` |
| Read side | `GET /analytics` aggregates and `GET /alerts` `leaning_most` are computed by the engine functions on the stored rows (D-79, D-92) | `backend/services/engine_read.py`, `analytics_summary.py`, `alert_service.py` |
| Operator commands | `run-pipeline`, `rebuild --confirm REBUILD`, `set-config`; the full `seed test_v0_1` ingests SRC-05 and runs the pipeline (D-93) | `backend/cli.py` |
| Engine from files | `python scripts/run_engine.py --input … --profile … --as-of … --assignments … --residents … --out …` (ANL-007) | `scripts/run_engine.py` |

## 2. Stages

Stage order follows TRD 07 §4.5. Every stage has its own test module under `tests/unit/analytics/` (TST-011 checks that each module has one).

| # | Stage | Module | Main rules |
|---|---|---|---|
| 1 | Duplicates | `duplicate_detection` | First arrival of a `session_id` wins, by `arrival_seq` (AGT-053); copies are `duplicate` and never counted |
| 2 | Quality gate | `quality_screening` | Set aside for quality flag `poor`, noise above −40 dBFS, speech under 1.0 s; every reason kept, in TRD order |
| 3 | Late arrivals | `pipeline.detect_late_arrivals` | A record older than an already frozen baseline is `late_arrival`; the frozen baseline is not changed (ANL-023) |
| 4 | Epochs | `epoch_detection` | A new epoch when device, firmware or extraction software changes; restart cause in that order (D-64) |
| 5 | Local time | `morning_offset.local_time` | UTC → America/Chicago with DST, local date, morning before 12:00 |
| 6 | Speaker screen | `speaker_screen` | Once at least 5 usable sessions precede it, a record is compared on raw values with the first (up to N) of them, and quarantined when F0 \|z\| ≥ 4 **and** at least 2 composite features have \|z\| ≥ 3 |
| 7 | Morning adjustment | `morning_offset` | Per-feature morning offsets subtracted before scoring |
| 8 | Baseline | `baseline_builder` | First N usable sessions of the epoch (16 test, 30 production); median, MAD × 1.4826, spread floors (pause features 0.5, composite 0.1); frozen once formed |
| 9 | Scores | `zscore_calculator`, `composite_score` | Signed z per feature; composite = sum of the 7 signed z / 7, then z against the composite baseline |
| 10 | CUSUM | `cusum_engine` | Tally = max(0, tally + composite z − 0.5); the alarm rings when the tally first reaches 5.0 and then stays on for the rest of the epoch |
| 11 | Alerts | `alert_generator` | One alert per epoch whose alarm rang, closed when the epoch ends; `leaning_most` = up to 3 features with the highest positive mean signed z since the alarm |
| 12 | Day ledger | `day_ledger` | One row per resident per day: checked in, missed, or device gap (all residents on a shared device silent) |
| 13 | Data alerts | `data_alerts` | In the 30-day window, for residents not withdrawn: baseline stalled (epoch at least N days old, baseline not formed); possible other speaker (any quarantined check-in); many set aside (at least 20 % of at least 10 received, when not stalled); device silent (every shared-device silent day, or 2 or more consecutive silent days for a one-resident device). Natural keys, so reruns update rather than duplicate |
| 14 | Aggregates | `aggregates` | KPI tiles, funnel, by-resident percentages, by-day chart for `GET /analytics` |

## 3. How the backend runs it

- `PipelineRunner.start` inserts the `pipeline_runs` row (`running`) with the configuration snapshot, its hash and the git SHA (AGT-020); `execute` loads the inputs, calls `run_pipeline` and writes each resident in its own transaction under `lock_xact("resident", code)`.
- One resident failing rolls back only that resident; the run is `failed`, keeps its counts and warnings, and the next ingest or nightly run retries (FEAT-056-FR-07).
- If the algorithm configuration changed since the last run, the run fails with `config_changed_requires_rebuild` until an operator runs `rebuild --confirm REBUILD` (D-56, D-69). `rebuild` runs as `echowell_migrator`, because the application role may not delete frozen baselines.
- Run logging: `pipeline_run_succeeded`, `pipeline_run_failed`, `pipeline_warning`, `data_alerts_updated`, `nightly_run_missing`; nightly runs add `db_size_bytes` to their counts.

## 4. Check against the answer key

The engine was run on SRC-05 (283 synthetic records, 10 residents, 1–30 October 2026, as of 30 October 15:00 Chicago) and compared with SRC-03, the reference workbook:

| Compared | Rows | Result |
|---|---|---|
| Per-session status and reason (Annotated sheet) | 302 (283 records + 19 missed days) | identical |
| Baselines (median, MAD, spread, floor flag) | 180 | identical |
| Scores (signed z, composite, CUSUM tally, alarm state) | 98 | identical |
| Data alerts | 4: R08 baseline stuck at 13 of 16, R05 possible other speaker, R03 many set aside, D02 silent on 12 Oct | identical |
| KPI tiles, funnel, by-resident percentages | all | identical |

Total: 0 mismatches. The comparison ran as a one-off script outside the repository, because AGT-007 forbids any module in `analytics/` or `backend/` from reading the workbook. The automated version of this comparison is FEAT-057/FEAT-058 in checkpoint 6. Inside the repository the same values are pinned by unit tests on SRC-05 (`tests/unit/analytics/test_pipeline.py` and per stage), by `tests/integration/pipeline/test_runner_persistence.py` on PostgreSQL, and by the FEAT-014 read-model values on the full seed.

## 5. Performance

SRC-05 runs through `run_pipeline` in about 0.06 s, well inside the 5 s limit (TST-120, D-40); `test_pipeline.py` and `test_run_engine.py` assert the limit.

## 6. Tests

| Area | Files |
|---|---|
| Stages | `tests/unit/analytics/test_<module>.py` for every module, plus `src05.py` (SRC-05 loader) and `factory.py` (record builder) |
| Orchestrator | `test_pipeline.py`: SRC-05 counts, determinism and order independence, duplicates, as-of filter, late arrival, frozen baselines, contract errors, ≤ 5 s |
| Engine from files | `test_run_engine.py` |
| Persistence | `tests/integration/pipeline/test_runner_persistence.py`: full run, second run changes nothing, reviews and snoozes survive, one failing resident rolled back alone, late record, endpoints after a run |
| Nightly job | `tests/integration/pipeline/test_nightly_run.py`: one run per local night across the 1 Nov 2026 DST change, missed night reported, schema check |
| CLI and seed | `tests/integration/test_cli_pipeline.py`: full seed, `run-pipeline`, `set-config` → refused run → `rebuild`, rebuild reproduces identical derived tables |
| Read models | `tests/integration/db/test_read_models.py::test_seed_values_on_the_full_seed` (FEAT-014 values) |

`analytics/` coverage: 97 % lines and branches (target 95 %, TST-140).
