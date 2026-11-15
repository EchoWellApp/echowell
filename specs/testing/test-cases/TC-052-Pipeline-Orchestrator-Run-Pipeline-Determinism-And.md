# Pipeline orchestrator run_pipeline, determinism and engine CLI

## Feature Description

`analytics/pipeline.py::run_pipeline(records, residents, assignments, config, as_of, *, frozen_baselines=None)` (FEAT-052) is the single entry point of the analytics engine for every trigger. It validates the input contract (raising `ContractError` with no partial result), excludes records after `as_of` with one `after_as_of` warning each, runs the stages in the fixed 16-step order of TRD 07 §4.5 (duplicates, quality gate, epochs, speaker screen, morning adjustment, baseline, scoring, CUSUM, alerts, day ledger, data alerts, aggregates) and returns a `PipelineResult` with `counts` (12 keys), sorted warnings, `run_config`, `config_hash`, `engine_version` "0.1.0" and `as_of`. Identical input gives a bit-identical result. `scripts/run_engine.py` runs the engine from files and writes the result as JSON.

## Preconditions

- Local development stack, repository root as working directory, `backend/requirements-dev.txt` installed (includes `import-linter`).
- No database or running server is needed: the engine is pure.
- REPL helper (paste into `python` at the repository root):

```python
import dataclasses, random
from datetime import datetime
from zoneinfo import ZoneInfo
from analytics import run_pipeline, TEST_V0_1, ContractError
from tests.unit.analytics.src05 import records, RESIDENTS, ASSIGNMENTS
from tests.unit.analytics.factory import rec
CT = ZoneInfo("America/Chicago"); AS_OF = datetime(2026, 10, 30, 15, tzinfo=CT)
R = lambda recs, **kw: run_pipeline(recs, RESIDENTS, ASSIGNMENTS, TEST_V0_1, AS_OF, **kw)
A = R(records())
```

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-052-01 | SRC-05 with `test_v0_1` reproduces the answer key (302, 10, 11, 180, 98 rows) | High | Analytics |
| TC-052-02 | `counts` equal 283/267/12/2/2/17/2/0/98/2/0/10 in TRD 23 key order | High | Analytics |
| TC-052-03 | Two calls and a shuffled input give equal results | High | Analytics |
| TC-052-04 | Removing R04 duplicate arrivals 89 and 283 changes no R04 output | High | Analytics |
| TC-052-05 | Record after `as_of` is excluded with exactly one `after_as_of` warning | High | Negative |
| TC-052-06 | Contract violations raise `ContractError` and return no result | High | Negative |
| TC-052-07 | Normal data conditions never raise | Medium | Negative |
| TC-052-08 | `sessions` hold one `AdjustedRecord` per record incl. duplicates, ordered by `arrival_seq` | Medium | Positive |
| TC-052-09 | Result metadata: `engine_version`, `config_hash`, `run_config`, `as_of`, sorted warnings | Medium | Positive |
| TC-052-10 | Stage order follows TRD 07 §4.5 | High | Analytics |
| TC-052-11 | `frozen_baselines` are used and a late record leaves a frozen baseline unchanged | High | Analytics |
| TC-052-12 | Static import check forbids database, HTTP and `backend` imports in `analytics/` | High | Security |
| TC-052-13 | Engine on SRC-05 completes in ≤ 5 s | High | Performance |
| TC-052-14 | `scripts/run_engine.py` exits 0 and writes the result JSON files | High | Positive |
| TC-052-15 | `scripts/run_engine.py` with an unreadable input exits non-zero | Medium | Negative |

### TC-052-01 SRC-05 with `test_v0_1` reproduces the answer key (302, 10, 11, 180, 98 rows)

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/unit/analytics/test_pipeline.py -q` | Exit code 0 (all tests incl. `test_src05_counts_and_sessions`) |
| 2 | `pytest tests/validation/test_harness.py -q -k tier_a_matches` (Tier A comparator; a partial run does not rewrite `docs/reports/`, TRD 24 D-137) | `test_tier_a_matches_the_answer_key` passes; 0 mismatches against Annotated_sessions (302 rows), Exp_status_counts (10), Exp_resident_outcomes (11), Exp_baselines (180), Exp_scores (98) |
| 3 | REPL: `len(A.baselines), len(A.scores)` | `(180, 98)` |

### TC-052-02 `counts` equal 283/267/12/2/2/17/2/0/98/2/0/10 in TRD 23 key order

| Step | Action | Expected Result |
|---|---|---|
| 1 | REPL: `list(A.counts.items())` | `[('arrivals', 283), ('usable', 267), ('set_aside', 12), ('quarantined', 2), ('duplicate', 2), ('missing_resident', 17), ('missing_device_gap', 2), ('late_arrival', 0), ('scored', 98), ('alerts_opened', 2), ('excluded_after_as_of', 0), ('residents', 10)]` |

### TC-052-03 Two calls and a shuffled input give equal results

| Step | Action | Expected Result |
|---|---|---|
| 1 | `B = R(records()); A == B` | `True` (field-by-field equal, floats bitwise equal) |
| 2 | `s = list(records()); random.Random(7).shuffle(s); C = R(s); A == C` | `True` (input order irrelevant while `arrival_seq` is kept) |
| 3 | `pytest tests/unit/analytics/test_pipeline.py -q -k deterministic` | `test_deterministic_and_order_independent` passes |

### TC-052-04 Removing R04 duplicate arrivals 89 and 283 changes no R04 output

| Step | Action | Expected Result |
|---|---|---|
| 1 | `D = R([r for r in records() if r.arrival_seq not in (89, 283)])` | No exception; `D.counts["arrivals"]` 281, `D.counts["duplicate"]` 0 |
| 2 | `f = lambda res, k: [x for x in getattr(res, k) if getattr(x, "resident_code", None) == "R04"]; f(A,"baselines")==f(D,"baselines"), f(A,"scores")==f(D,"scores"), f(A,"ledger")==f(D,"ledger")` | `(True, True, True)` |
| 3 | `pytest tests/validation/test_invariance.py -q -k r04_inv` | `test_vc_r04_inv_identical_without_the_copies` passes (VC-R04-INV) |

### TC-052-05 Record after `as_of` is excluded with exactly one `after_as_of` warning

| Step | Action | Expected Result |
|---|---|---|
| 1 | `X = R(list(records()) + [rec(999, "2026-10-30 21:00:00", resident="R01", device="D01", session="R01-20261030-09")])` | No exception (21:00 UTC is after 20:00 UTC as-of) |
| 2 | `X.counts["excluded_after_as_of"], [(w.code, w.resident_code, w.session_id) for w in X.warnings]` | `1`, `[('after_as_of', 'R01', 'R01-20261030-09')]` |
| 3 | `any(s.record.session_id == "R01-20261030-09" for s in X.sessions)`; same check over `X.scores` session ids and `X.ledger` dates beyond 2026-10-30 | `False`; not in scores; no ledger row after 2026-10-30 |

### TC-052-06 Contract violations raise `ContractError` and return no result

| Step | Action | Expected Result |
|---|---|---|
| 1 | `run_pipeline(records(), RESIDENTS, ASSIGNMENTS, TEST_V0_1, datetime(2026,10,30,15))` (naive as-of) | `ContractError: as_of must be a timezone-aware datetime` |
| 2 | `R(list(records()) + [dataclasses.replace(records()[0], session_id="X")])` (repeated `arrival_seq` 1) | `ContractError: arrival_seq values must be unique` |
| 3 | `dataclasses.replace(records()[0], features={k: v for k, v in list(records()[0].features.items())[:18]})` (18 feature keys) | `ContractError: R01-20261001-01: features must be the 19 canonical keys in contract order` |
| 4 | `run_pipeline(records(), RESIDENTS[:9], ASSIGNMENTS, TEST_V0_1, AS_OF)` | `ContractError: assignment for unknown resident R10` |
| 5 | `run_pipeline(records(), RESIDENTS, ASSIGNMENTS, {}, AS_OF)` | `ContractError: config must be a PipelineConfig` |
| 6 | For each step, check that no result variable was assigned | Exception raised before any stage; nothing returned |

### TC-052-07 Normal data conditions never raise

| Step | Action | Expected Result |
|---|---|---|
| 1 | `E = run_pipeline([], RESIDENTS, ASSIGNMENTS, TEST_V0_1, AS_OF); E.counts` | No exception; `arrivals` 0, `missing_resident` 240, `missing_device_gap` 60, `residents` 10 |
| 2 | Only duplicates: `R([records()[0], dataclasses.replace(records()[0], arrival_seq=900)])` | No exception; `counts["duplicate"]` 1 |
| 3 | R08 (forming, 13 usable) in `A` | `[e for e in A.epochs if e.resident_code=="R08"][0].baseline_formed` is `False`; no R08 score |

### TC-052-08 `sessions` hold one `AdjustedRecord` per record incl. duplicates, ordered by `arrival_seq`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `len(A.sessions)` | `283` |
| 2 | `[s.record.arrival_seq for s in A.sessions] == list(range(1, 284))` | `True` |
| 3 | `[(s.record.arrival_seq, s.status, s.reasons) for s in A.sessions if s.status == "duplicate"]` | Arrivals 89 and 283, reasons containing `session_id already received` |

### TC-052-09 Result metadata: `engine_version`, `config_hash`, `run_config`, `as_of`, sorted warnings

| Step | Action | Expected Result |
|---|---|---|
| 1 | `A.engine_version, len(A.config_hash), A.as_of` | `('0.1.0', 64, datetime(2026, 10, 30, 15, 0, tzinfo=America/Chicago))` |
| 2 | `A.config_hash == TEST_V0_1.config_hash()` and `A.run_config` | `True`; `run_config` is the profile snapshot |
| 3 | `A.warnings` | `()` on SRC-05 |
| 4 | With TC-052-05 `X`: add a second late record for R02 and check `[(w.code, w.resident_code, w.session_id) for w in X.warnings]` | Sorted by (code, resident_code, session_id) |

### TC-052-10 Stage order follows TRD 07 §4.5

| Step | Action | Expected Result |
|---|---|---|
| 1 | Open `analytics/pipeline.py`, read `run_pipeline` top to bottom | Calls in order: validate, sort by `arrival_seq`, as-of exclusion, `mark_duplicates`, `apply_quality_gate`, late-arrival classification, `assign_epochs`, `screen_speakers`, `adjust`, `build_baselines`, `feature_z` / `composite_raw` / `composite_z`, `run_cusum`, `EpochSummary`, `generate_alerts`, `build_ledger`, `generate_data_alerts`, `build_analytics_summary`, `PipelineResult` |
| 2 | Confirm aggregates come after data alerts | `build_analytics_summary` receives the data-alert list (step 15 after step 14) |

### TC-052-11 `frozen_baselines` are used and a late record leaves a frozen baseline unchanged

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/unit/analytics/test_pipeline.py -q -k "frozen or late"` | `test_late_arrival_leaves_r01_unchanged`, `test_out_of_order_after_freeze_is_not_late`, `test_frozen_baselines_win_and_mismatch_warns` pass |
| 2 | Read the result of step 1 test `test_late_arrival_leaves_r01_unchanged` | Late record before R01's frozen baseline gives a `late_arrival` warning; R01 baselines identical |

### TC-052-12 Static import check forbids database, HTTP and `backend` imports in `analytics/`

| Step | Action | Expected Result |
|---|---|---|
| 1 | `lint-imports` | Contract "analytics is pure: no backend, database, HTTP, environment or randomness" KEPT |
| 2 | Temporarily add `import sqlalchemy` at the top of `analytics/pipeline.py`, run `lint-imports`, then revert the line | Contract BROKEN, non-zero exit; after revert KEPT again |
| 3 | `grep -n -e datetime.now -e os.environ -e random -e evaluation_ground_truth -e true_onset -e planted_change analytics/pipeline.py` | No match (no clock, environment, randomness or ground truth) |

### TC-052-13 Engine on SRC-05 completes in ≤ 5 s

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest tests/performance/test_pipeline_runtime.py -q` | Exit code 0 (TST-120, ≤ 5 s) |
| 2 | `pytest tests/unit/analytics/test_pipeline.py -q -k five_seconds` | `test_src05_runs_within_five_seconds` passes |

### TC-052-14 `scripts/run_engine.py` exits 0 and writes the result JSON files

| Step | Action | Expected Result |
|---|---|---|
| 1 | `python scripts/run_engine.py --input tests/fixtures/pipeline_input/EchoWell_pipeline_test_input_v0_1.csv --profile test_v0_1 --as-of "2026-10-30 15:00" --assignments database/seeds/test_v0_1/device_assignments.csv --residents database/seeds/test_v0_1/residents.csv --out /tmp/engine_out` | Exit code 0; prints `wrote 14 files to /tmp/engine_out` and no feature value |
| 2 | `ls /tmp/engine_out` | `alerts.json`, `analytics.json`, `as_of.json`, `baselines.json`, `config_hash.json`, `counts.json`, `data_alerts.json`, `engine_version.json`, `epochs.json`, `ledger.json`, `run_config.json`, `scores.json`, `sessions.json`, `warnings.json` |
| 3 | `cat /tmp/engine_out/counts.json` | Same 12 values as TC-052-02 |
| 4 | Run step 1 again into `/tmp/engine_out2`; `diff -r /tmp/engine_out /tmp/engine_out2` | No difference (byte-identical, PIP-02) |
| 5 | `pytest tests/unit/analytics/test_run_engine.py -q` | Exit code 0 |

### TC-052-15 `scripts/run_engine.py` with an unreadable input exits non-zero

| Step | Action | Expected Result |
|---|---|---|
| 1 | Step 1 of TC-052-14 with `--input /nonexistent.csv` | Non-zero exit (1); message contains `No such file or directory: '/nonexistent.csv'` |
| 2 | Step 1 of TC-052-14 with `--profile unknown` | Exit code 2 (argparse: invalid choice) |

## API Validation

Not applicable: the engine exposes and consumes no endpoint; the backend reaches it only through `pipeline_runner` (FEAT-053, API-006).

## Database Validation

Not applicable: `analytics/` performs no database access (ANL-002); persistence is tested in TC-053.

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Naive `as_of` | `ContractError`, no result |
| 2 | Duplicate `arrival_seq` | `ContractError`, no result |
| 3 | 18 feature keys | `ContractError` |
| 4 | Assignment for a resident not in `residents` | `ContractError` |
| 5 | `config` not a `PipelineConfig` | `ContractError` |
| 6 | Record after `as_of` | Excluded, one `after_as_of` warning, `excluded_after_as_of` 1 |
| 7 | `analytics/` module importing `sqlalchemy` | `lint-imports` fails |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-052-AC-01 | SRC-05 passes all SRC-03 comparisons (302, 10, 11, 180, 98 rows) at 1e-6 and exact strings | TC-052-01 |
| FEAT-052-AC-02 | Two calls and a shuffled input return equal results | TC-052-03, TC-052-14 step 4 |
| FEAT-052-AC-03 | Removing arrivals 89 and 283 changes nothing in R04's baselines, scores or ledger | TC-052-04 |
| FEAT-052-AC-04 | Static import check fails on database, HTTP or `backend` imports | TC-052-12 |
| FEAT-052-AC-05 | `counts` = 283/267/12/2/2/17/2/0/98/2/0/10 in TRD 23 order | TC-052-02 |
| FEAT-052-AC-06 | After-as-of record absent from sessions, scores and ledger with exactly one `after_as_of` warning | TC-052-05 |
| FEAT-052-AC-07 | Naive `as_of`, duplicate `arrival_seq`, missing feature key each raise `ContractError` | TC-052-06 |
| FEAT-052-AC-08 | SRC-05 completes in ≤ 5 s | TC-052-13 |
| FEAT-052-AC-09 | `python scripts/run_engine.py ...` exits 0 and writes the result JSON files | TC-052-14 |

## Test Data Requirements

- SRC-05 `tests/fixtures/pipeline_input/EchoWell_pipeline_test_input_v0_1.csv`; roster files `database/seeds/test_v0_1/device_assignments.csv` and `residents.csv`; answer key `tests/fixtures/answer_key/EchoWell_pipeline_test_v0_1.xlsx` (read only by the validation tests).
- Synthetic extra records from `tests.unit.analytics.factory.rec` (session `R01-20261030-09`, arrival 999).
- No environment secrets needed; no database.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-052-FR-01 / ANL-014, ARC-040 | FEAT-052 | TC-052-01, TC-052-10 |
| FEAT-052-FR-02 / ANL-006 | FEAT-052 | TC-052-10 |
| FEAT-052-FR-03 / ANL-018, ANL-013 | FEAT-052 | TC-052-06 |
| FEAT-052-FR-04 / ANL-015 | FEAT-052 | TC-052-05 |
| FEAT-052-FR-05 / ANL-016 | FEAT-052 | TC-052-01 (D02 ledger), TC-049-04 |
| FEAT-052-FR-06 / ANL-021, NFR-034 | FEAT-052 | TC-052-03, TC-052-09 |
| FEAT-052-FR-07 / ANL-022, NFR-030 | FEAT-052 | TC-052-01, TC-052-03 |
| FEAT-052-FR-08 / ANL-020, NFR-033, AGT-021 | FEAT-052 | TC-052-03, TC-052-14 |
| FEAT-052-FR-09 / ANL-019 | FEAT-052 | TC-052-07 |
| FEAT-052-FR-10 / ANL-012 | FEAT-052 | TC-052-08 |
| FEAT-052-FR-11 | FEAT-052 | TC-052-02, TC-052-09 |
| FEAT-052-FR-12 / ARC-043, ANL-037 | FEAT-052 | TC-052-11 |
| FEAT-052-FR-13 / ANL-017, NFR-031 | FEAT-052 | TC-052-01 |
| FEAT-052-FR-14 / FR-031 | FEAT-052 | TC-052-04 |
| FEAT-052-FR-15 / ANL-047, CIC-027 | FEAT-052 | TC-052-13 |
| FEAT-052-FR-16 / ANL-007 | FEAT-052 | TC-052-14, TC-052-15 |
| FEAT-052-FR-17 / ANL-002, ANL-003 | FEAT-052 | TC-052-12 |
| PIP-01, PIP-02, PIP-03, PIP-04, PIP-05 | FEAT-052 | TC-052-01, TC-052-03, TC-052-10, TC-052-11, TC-052-12 |
| TST-120, TST-021, TST-022 | FEAT-052 | TC-052-13, TC-052-12, TC-052-03 |
| VC-G12, VC-R04-INV | FEAT-052 | TC-052-03, TC-052-04 |
| AC-ANL-01..AC-ANL-04, AC-ANL-07 | FEAT-052 | TC-052-01, TC-052-03, TC-052-04, TC-052-12, TC-052-13 |
