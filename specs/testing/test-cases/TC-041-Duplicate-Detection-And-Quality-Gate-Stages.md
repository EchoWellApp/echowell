# Duplicate detection and quality gate stages

## Feature Description

FEAT-041 implements the first two pipeline stages. `analytics/duplicate_detection.py::mark_duplicates` walks the records in ascending `arrival_seq` (never timestamp order) and keeps the first arrival of each `session_id`; every later copy, even with different values, gets status `duplicate` with reason "session_id already received" and is excluded from all later stages. `analytics/quality_screening.py::apply_quality_gate` sets aside non-duplicate records whose `audio_quality_flag` ≠ "ok" ("quality flag poor"), whose `mic_noise_level_dbfs` > −40.0 ("noise above limit") or whose `speech_duration_s` < 1.0 ("speech too short"), recording every reason in that fixed order joined by "; "; passing records get `pending_screen`. Set-aside records still belong to an epoch and count for the day ledger but are never screened, used as a reference, used for a baseline, scored or counted in the tally. On SRC-05 this gives R04's two duplicates (arrivals 89 and 283) and 12 set-aside records (R03 ×7, R08 ×5).

## Preconditions

- Local development stack per `README.md` quick start; working directory = repository root; Python steps run in a `python` REPL started from the repository root (`import sys; sys.path.insert(0, ".")` first).
- Common REPL imports for the unit-level cases: `from tests.unit.analytics.factory import rec; from analytics.duplicate_detection import mark_duplicates; from analytics.quality_screening import apply_quality_gate; from analytics.config import TEST_V0_1 as C`. `rec(seq, "YYYY-MM-DD HH:MM:SS", session=..., noise=..., speech=..., flag=..., **features)` builds a synthetic R01/D01 record (defaults: flag "ok", noise −55.0, speech 2.5).
- Local PostgreSQL freshly seeded with `python -m backend.cli seed test_v0_1 --reset` (SRC-05 ingested as one batch in file order, arrival_seq 1..283, then a manual run at as-of 2026-10-30 15:00 America/Chicago); `psql` read access.
- Local Docker Compose (demo profile) with the same data for the API case; ADMIN_TOKEN from `POST /api/v1/auth/login` (`admin@example.com`, `SEED_ADMIN_PASSWORD`); the ingest API key from the environment file (INGEST_KEY).

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-041-01 | Arrivals A(S1), B(S2), C(S1): A and B `pending_screen`, C `duplicate` | High | Analytics |
| TC-041-02 | Same `session_id` with different values: first kept unchanged, second `duplicate` | High | Analytics |
| TC-041-03 | Three copies of one session: 1 kept, 2 duplicates | Medium | Analytics |
| TC-041-04 | Arrival order decides, not timestamp order | High | Analytics |
| TC-041-05 | Noise boundary: −40.0 passes, −39.9 is set aside | High | Analytics |
| TC-041-06 | Speech boundary: 1.0 passes, 0.99 is set aside | High | Analytics |
| TC-041-07 | All three reasons in the fixed order and joined with "; " | High | Analytics |
| TC-041-08 | Duplicates bypass the gate and keep only the duplicate reason | Medium | Analytics |
| TC-041-09 | SRC-05: arrivals 89 and 283 are `duplicate` | High | Database |
| TC-041-10 | SRC-05: exactly 12 set-aside records with exact reasons | High | Database |
| TC-041-11 | Set-aside records keep an epoch and a ledger day but never enter baseline, score or tally | High | Database |
| TC-041-12 | Removing arrivals 89 and 283 changes no R04 output | High | Analytics |
| TC-041-13 | Re-sending a record through the API changes no result | High | API |
| TC-041-14 | Check-in log shows set-aside reasons; duplicates are never shown | Medium | API |
| TC-041-15 | Empty input and all-bad input raise no exception; gate ignores feature values | Medium | Negative |

### TC-041-01 Arrivals A(S1), B(S2), C(S1)

| Step | Action | Expected Result |
|---|---|---|
| 1 | `out = mark_duplicates([rec(1, "2026-10-01 19:00:00", session="S1"), rec(2, "2026-10-02 19:00:00", session="S2"), rec(3, "2026-10-03 19:00:00", session="S1")])` | Returns a list of 3 `ScreenedRecord` (one per input) |
| 2 | `print([(o.record.arrival_seq, o.record.session_id, o.status, o.reasons, o.reason_text) for o in out])` | `[(1, 'S1', 'pending_screen', (), ''), (2, 'S2', 'pending_screen', (), ''), (3, 'S1', 'duplicate', ('session_id already received',), 'session_id already received')]` |
| 3 | `pytest -m unit tests/unit/analytics/test_duplicate_detection.py -v` | `test_first_arrival_wins_in_arrival_order` and `test_src05_duplicates` PASSED |

### TC-041-02 Same session_id with different values

| Step | Action | Expected Result |
|---|---|---|
| 1 | `a = rec(1, "2026-10-01 19:00:00", session="S1"); b = rec(2, "2026-10-01 19:00:00", session="S1", loudness_dbfs=-10.0); out = mark_duplicates([a, b])` | 2 rows |
| 2 | `print(out[0].status, out[0].record == a, out[1].status, out[1].reason_text)` | `pending_screen True duplicate session_id already received` |
| 3 | `print(out[0].record.features["loudness_dbfs"])` | `-24.0` (the value of `a` from the factory defaults), not −10.0 |

### TC-041-03 Three copies of one session

| Step | Action | Expected Result |
|---|---|---|
| 1 | `out = mark_duplicates([rec(i, "2026-10-01 19:00:00", session="S1") for i in (1, 2, 3)]); print([o.status for o in out])` | `['pending_screen', 'duplicate', 'duplicate']` |

### TC-041-04 Arrival order decides, not timestamp order

| Step | Action | Expected Result |
|---|---|---|
| 1 | `out = mark_duplicates([rec(5, "2026-10-18 19:25:29", session="S1"), rec(2, "2026-10-01 19:00:00", session="S1")])` (input list not sorted; the copy with arrival_seq 2 has the earlier timestamp) | 2 rows ordered by `arrival_seq`: 2 first, then 5 |
| 2 | `print([(o.record.arrival_seq, o.status) for o in out])` | `[(2, 'pending_screen'), (5, 'duplicate')]` |
| 3 | Swap timestamps (arrival 2 later in time than arrival 5) and repeat | Still `[(2, 'pending_screen'), (5, 'duplicate')]` |

### TC-041-05 Noise boundary

| Step | Action | Expected Result |
|---|---|---|
| 1 | `g = apply_quality_gate(mark_duplicates([rec(1, "2026-10-01 19:00:00", noise=-40.0), rec(2, "2026-10-02 19:00:00", noise=-39.9)]), C)` | 2 rows |
| 2 | `print([(o.status, o.reason_text) for o in g])` | `[('pending_screen', ''), ('set_aside', 'noise above limit')]` |
| 3 | `print(C.noise_limit_dbfs)` | `-40.0` (threshold read from config) |

### TC-041-06 Speech boundary

| Step | Action | Expected Result |
|---|---|---|
| 1 | `g = apply_quality_gate(mark_duplicates([rec(1, "2026-10-01 19:00:00", speech=1.0), rec(2, "2026-10-02 19:00:00", speech=0.99)]), C)` | 2 rows |
| 2 | `print([(o.status, o.reason_text) for o in g])` | `[('pending_screen', ''), ('set_aside', 'speech too short')]` |
| 3 | `pytest -m unit tests/unit/analytics/test_quality_screening.py -v` | `test_thresholds_are_strict`, `test_all_reasons_in_fixed_order`, `test_duplicates_pass_through_ungated`, `test_src05_set_aside` PASSED |

### TC-041-07 All three reasons in the fixed order

| Step | Action | Expected Result |
|---|---|---|
| 1 | `g = apply_quality_gate(mark_duplicates([rec(1, "2026-10-01 19:00:00", flag="poor", noise=-30.0, speech=0.5)]), C); print(g[0].status, g[0].reasons, g[0].reason_text)` | `set_aside ('quality flag poor', 'noise above limit', 'speech too short') quality flag poor; noise above limit; speech too short` |
| 2 | Same with `flag="poor", noise=-30.0` and default speech (R03 day 18 shape, QG-07) | `reason_text` = "quality flag poor; noise above limit" |
| 3 | Same with `flag="ok", noise=-50.0, speech=2.5` (QG-01) | `pending_screen`, `reasons` = `()` |

### TC-041-08 Duplicates bypass the gate

| Step | Action | Expected Result |
|---|---|---|
| 1 | `g = apply_quality_gate(mark_duplicates([rec(1, "2026-10-01 19:00:00", session="S1"), rec(2, "2026-10-01 19:00:00", session="S1", flag="poor", noise=-30.0)]), C)` | 2 rows |
| 2 | `print([(o.status, o.reasons) for o in g])` | `[('pending_screen', ()), ('duplicate', ('session_id already received',))]` — no quality reason added to the duplicate |

### TC-041-09 SRC-05: arrivals 89 and 283 are duplicate

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT r.arrival_seq, p.session_id, p.status, p.reason_text, p.epoch_id FROM processed_sessions p JOIN raw_sessions r ON r.id = p.raw_session_id WHERE p.status = 'duplicate' ORDER BY r.arrival_seq;` | 2 rows: (89, `R04-20261005-01`, `duplicate`, `session_id already received`, NULL) and (283, `R04-20261018-01`, `duplicate`, `session_id already received`, NULL) |
| 2 | `SELECT r.arrival_seq, p.status FROM processed_sessions p JOIN raw_sessions r ON r.id = p.raw_session_id WHERE p.session_id IN ('R04-20261005-01','R04-20261018-01') ORDER BY 1;` | (88, `usable`), (89, `duplicate`), (102, `usable`), (283, `duplicate`) |
| 3 | `SELECT count(*) FROM raw_sessions;` | 283 (duplicates are kept in the raw store) |
| 4 | `SELECT count(*) FROM scores s JOIN processed_sessions p ON p.id = s.processed_session_id WHERE p.status = 'duplicate';` | 0 |

### TC-041-10 SRC-05: exactly 12 set-aside records

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT p.session_id, p.reasons, p.reason_text FROM processed_sessions p WHERE p.status = 'set_aside' ORDER BY p.session_id;` | 12 rows exactly: R03-20261003-01 "noise above limit"; R03-20261007-01 "quality flag poor"; R03-20261010-01 "speech too short"; R03-20261014-01 "noise above limit"; R03-20261018-01 `{"quality flag poor","noise above limit"}` / "quality flag poor; noise above limit"; R03-20261022-01 "quality flag poor"; R03-20261026-01 "speech too short"; R08-20261005-01 "noise above limit"; R08-20261009-01 "quality flag poor"; R08-20261020-01 "noise above limit"; R08-20261025-01 "quality flag poor"; R08-20261029-01 "speech too short" |
| 2 | `SELECT counts->>'set_aside', counts->>'duplicate', counts->>'usable', counts->>'quarantined', counts->>'arrivals' FROM pipeline_runs WHERE status='succeeded' ORDER BY started_at DESC LIMIT 1;` | `12`, `2`, `267`, `2`, `283` (VC-G01) |
| 3 | Cross-check with SRC-03 `Exp_status_counts` | set_aside R03 7, R08 5; duplicate R04 2 |

### TC-041-11 Set-aside records keep an epoch and a ledger day, nothing else

| Step | Action | Expected Result |
|---|---|---|
| 1 | `SELECT p.session_id, e.epoch_number, p.in_baseline, p.baseline_ordinal FROM processed_sessions p JOIN epochs e ON e.id = p.epoch_id WHERE p.status='set_aside' ORDER BY 1;` | 12 rows, each `epoch_number` 1, `in_baseline` false, `baseline_ordinal` NULL |
| 2 | `SELECT count(*) FROM scores s JOIN processed_sessions p ON p.id = s.processed_session_id WHERE p.status='set_aside';` | 0 |
| 3 | `SELECT d.status FROM day_ledger d JOIN residents r ON r.id = d.resident_id WHERE r.resident_code='R03' AND d.local_date='2026-10-18';` | `checked_in` (a set-aside record still counts as a record for the day) |
| 4 | `SELECT b.n_sessions, b.frozen_after_session_id FROM baselines b JOIN residents r ON r.id=b.resident_id WHERE r.resident_code='R03' AND b.feature_key='loudness_dbfs';` | 16, `R03-20261023-01` (the 7 set-aside days are skipped when counting to 16) |

### TC-041-12 Removing arrivals 89 and 283 changes no R04 output

| Step | Action | Expected Result |
|---|---|---|
| 1 | `pytest -m unit tests/unit/analytics/test_pipeline.py -k dropping_duplicates -v` | `test_dropping_duplicates_changes_nothing_else` PASSED |
| 2 | REPL: `from tests.unit.analytics.src05 import records, result, RESIDENTS, ASSIGNMENTS, AS_OF; from analytics.pipeline import run_pipeline; res = run_pipeline([r for r in records() if r.arrival_seq not in (89, 283)], RESIDENTS, ASSIGNMENTS, C, AS_OF)` | No exception |
| 3 | `f = lambda rows: [x for x in rows if x.resident_code == "R04"]; print(f(res.baselines) == f(result().baselines), f(res.scores) == f(result().scores))` | `True True` |
| 4 | `pytest -m validation tests/validation/test_r04_duplicate_records.py tests/validation/test_invariance.py -v` | All PASSED (VC-R04, VC-R04-INV) |

### TC-041-13 Re-sending a record through the API changes no result

| Step | Action | Expected Result |
|---|---|---|
| 1 | Record the R01 results: `GET /api/v1/scores?resident_code=R01` as admin; note `total` and the `cusum_tally` of the last item | `total` = 14 |
| 2 | `POST /api/v1/sessions` with `X-API-Key: INGEST_KEY` and the SRC-05 row `R01-20261001-01` unchanged as JSON | HTTP 200 (duplicate verdict for an already received `session_id`, not 201) |
| 3 | Admin `POST /api/v1/pipeline/run` body `{"scope": ["R01"], "profile": "test_v0_1", "as_of": "2026-10-30T15:00:00-05:00"}`; poll `GET /api/v1/pipeline/runs/{id}` | Run `succeeded` |
| 4 | `SELECT p.status, p.reason_text FROM processed_sessions p JOIN raw_sessions r ON r.id=p.raw_session_id WHERE p.session_id='R01-20261001-01' ORDER BY r.arrival_seq;` | Two rows: `usable` then `duplicate` "session_id already received" |
| 5 | Repeat step 1 | `total` = 14 and every `z`, `composite_z`, `cusum_tally` identical to step 1 |

### TC-041-14 Check-in log shows set-aside reasons; duplicates never shown

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/residents/R03/checkins?from=2026-10-18&to=2026-10-18` as admin | One event with `event_type` = "set_aside", `session_id` = "R03-20261018-01", `detail` = "quality flag poor; noise above limit" |
| 2 | `GET /api/v1/residents/R04/checkins` | No event refers to a duplicate (no event type for duplicates exists; `CheckinEventType` enum has no `duplicate`) |

### TC-041-15 Empty and all-bad input; gate ignores feature values

| Step | Action | Expected Result |
|---|---|---|
| 1 | `print(mark_duplicates([]), apply_quality_gate([], C))` | `[] []`, no exception |
| 2 | `g = apply_quality_gate(mark_duplicates([rec(i, f"2026-10-0{i} 19:00:00", flag="poor") for i in range(1, 4)]), C); print({o.status for o in g})` | `{'set_aside'}`, no exception |
| 3 | `g1 = apply_quality_gate(mark_duplicates([rec(1, "2026-10-01 19:00:00", noise=-39.9)]), C); g2 = apply_quality_gate(mark_duplicates([rec(1, "2026-10-01 19:00:00", noise=-39.9, loudness_dbfs=-99.0, mean_f0_hz=50.0)]), C); print(g1[0].status == g2[0].status, g1[0].reasons == g2[0].reasons)` | `True True` |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `POST /api/v1/sessions` re-sending an existing `session_id` | 200 duplicate verdict; nothing changes downstream (TC-041-13) |
| 2 | `GET /api/v1/residents/R03/checkins` | `set_aside` events with the exact reason text (TC-041-14) |
| 3 | `GET /api/v1/residents/R04/checkins` | No duplicate events |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT status, count(*) FROM processed_sessions GROUP BY status ORDER BY status;` | duplicate 2, quarantined 2, set_aside 12, usable 267 |
| 2 | `SELECT DISTINCT unnest(reasons) FROM processed_sessions WHERE status IN ('set_aside','duplicate') ORDER BY 1;` | Only "noise above limit", "quality flag poor", "session_id already received", "speech too short" |
| 3 | `SELECT count(*) FROM processed_sessions WHERE reason_text <> array_to_string(reasons, '; ');` | 0 |
| 4 | Duplicate rows `epoch_id` | NULL (TC-041-09) |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Later copy with different values | `duplicate`; first copy's values kept (TC-041-02) |
| 2 | Noise −39.9, speech 0.99, flag "poor" | `set_aside` with the matching reason (TC-041-05..07) |
| 3 | Re-sent record | No change to any result (TC-041-12, TC-041-13) |
| 4 | Empty input / all records bad | No exception (TC-041-15) |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-041-AC-01 | A(S1), B(S2), C(S1) → A, B `pending_screen`; C `duplicate` with reason_text "session_id already received" | TC-041-01 |
| FEAT-041-AC-02 | Same `session_id`, different features → first unchanged, second `duplicate` | TC-041-02 |
| FEAT-041-AC-03 | Noise −40.0 passes, −39.9 `set_aside` "noise above limit"; speech 1.0 passes, 0.99 `set_aside` "speech too short" | TC-041-05, TC-041-06 |
| FEAT-041-AC-04 | Flag poor, noise −30.0, speech 0.5 → reasons in fixed order, reason_text "quality flag poor; noise above limit; speech too short" | TC-041-07 |
| FEAT-041-AC-05 | SRC-05: arrivals 89 and 283 `duplicate`; exactly 12 `set_aside` (R03 days 3, 7, 10, 14, 18, 22, 26; R08 days 5, 9, 20, 25, 29); R03-20261018-01 "quality flag poor; noise above limit" | TC-041-09, TC-041-10 |
| FEAT-041-AC-06 | Removing arrivals 89 and 283 leaves every R04 output unchanged | TC-041-12, TC-041-13 |

## Test Data Requirements

- SRC-05 `tests/fixtures/pipeline_input/EchoWell_pipeline_test_input_v0_1.csv` (283 records; R04-20261005-01 at arrivals 88 and 89, R04-20261018-01 at arrivals 102 and 283).
- SRC-03 answer key `tests/fixtures/answer_key/EchoWell_pipeline_test_v0_1.xlsx` (`Annotated_sessions`, `Exp_status_counts`).
- Synthetic records from `tests/unit/analytics/factory.py::rec` (study IDs R01/D01, session ids S1/S2).
- `PipelineConfig` `test_v0_1`: `noise_limit_dbfs` −40.0, `min_speech_s` 1.0.

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-041-FR-01 | FEAT-041 | TC-041-01, TC-041-03, TC-041-04 |
| FEAT-041-FR-02 | FEAT-041 | TC-041-02 |
| FEAT-041-FR-03 | FEAT-041 | TC-041-08, TC-041-09 |
| FEAT-041-FR-04 | FEAT-041 | TC-041-05, TC-041-06 |
| FEAT-041-FR-05 | FEAT-041 | TC-041-07, TC-041-10 |
| FEAT-041-FR-06 | FEAT-041 | TC-041-11 |
| FEAT-041-FR-07 | FEAT-041 | TC-041-12, TC-041-13 |
| FEAT-041-FR-08 | FEAT-041 | TC-041-04, TC-041-15 |
| TRD 10 ING-034..ING-037, ING-039 | FEAT-041 | TC-041-01..TC-041-04, TC-041-13 |
| TRD 10 ING-040..ING-043 | FEAT-041 | TC-041-05..TC-041-08, TC-041-11 |
| TRD 01 ARC-074 | FEAT-041 | TC-041-04 |
| TRD 13 DUP-01..DUP-04 | FEAT-041 | TC-041-01..TC-041-03 |
| TRD 13 QG-01..QG-07 | FEAT-041 | TC-041-05..TC-041-07 |
| TRD 07 AC-ANL-03 | FEAT-041 | TC-041-12 |
| TRD 14 VC-R03, VC-R04, VC-R04-INV, VC-R08, VC-G01 | FEAT-041 | TC-041-09, TC-041-10, TC-041-12 |
| FR-029, FR-030, FR-031, FR-040..FR-044 | FEAT-041 | TC-041-01..TC-041-13 |
