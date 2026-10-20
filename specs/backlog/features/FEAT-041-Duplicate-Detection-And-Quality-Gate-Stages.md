# FEAT-041 Duplicate detection and quality gate stages

| Field | Value |
|---|---|
| Epic | Data Processing |
| Build phase | Phase 6 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-040 |
| Status | Not Started |

## Purpose

Implement the first two pipeline stages. Duplicate detection processes arrivals in arrival order and keeps the first copy of each `session_id`, marking every later copy `duplicate` so that re-sent records change nothing. The quality gate sets aside non-duplicate records with a poor quality flag, too much background noise or too little speech, recording all reasons in a fixed order; passing records go on to the speaker screen. These two stages produce the R04 duplicate and the R03/R08 set-aside results of the answer key.

## Business Context

- BR-03 (duplicates kept but marked and never used): first arrival wins, later copies are logged as duplicates and excluded from all later stages.
- BR-04 (poor-quality check-ins set aside, never used for baselines or scores): flag, noise and speech-duration rules with exact reason strings.
- BR-15: R04's two copies (arrivals 89 and 283) are duplicates and R04's results are identical to a run without them; 12 set-aside records with exact reasons.
- FRs covered (BACKLOG.md): FR-029, FR-030, FR-031, FR-040, FR-041, FR-042, FR-043, FR-044.

## Referenced TRDs

- TRD 10 ING-034..ING-037 (duplicate key, ordering, logging, differing payload), ING-039 (re-send safe), ING-040..ING-043 (quality gate rules, reason order, set-aside handling, `pending_screen`), §4.7 and §4.8 fixture checks.
- TRD 07 §4.2 (`mark_duplicates`, `apply_quality_gate` signatures), §4.3 (`ScreenedRecord`), ANL-021 (stable, fully keyed sorting), ANL-006 (stage order).
- TRD 01 ARC-074 (arrival order for duplicates; timestamp order afterwards).
- TRD 13 Table 4.3-A DUP-01..DUP-04, QG-01..QG-07; TST-020, TST-022; TRD 07 AC-ANL-03.
- TRD 14 VC-R03, VC-R04 (including VC-R04-INV), VC-R08 (set-aside part).
- TRD 25 AGT-043, AGT-049; TRD 24 D-09.

## Scope

- `analytics/duplicate_detection.py::mark_duplicates(records: Sequence[RawRecord]) -> list[ScreenedRecord]`.
- `analytics/quality_screening.py::apply_quality_gate(rows: Sequence[ScreenedRecord], config) -> list[ScreenedRecord]`.
- Unit tests `tests/unit/analytics/test_duplicate_detection.py`, `tests/unit/analytics/test_quality_screening.py`.

## Out of Scope

- The ingest-side duplicate verdict in HTTP responses and the session advisory lock (FEAT-025, FEAT-026, ING-038).
- The `duplicate_payload_differs` ingest warning stored in `raw_sessions.ingest_warnings` at insert time (FEAT-025/FEAT-026; ING-037, ING-023).
- Persisting `processed_sessions` rows (FEAT-053); orchestration (FEAT-052).
- Epochs, speaker screen and later stages (FEAT-042 onwards).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-041-FR-01 | `mark_duplicates` shall process all records in ascending `arrival_seq` (never timestamp order) and keep the first arrival of each `session_id` (exact string); every later arrival gets status `duplicate`, reasons ("session_id already received",) and `reason_text` "session_id already received"; first arrivals get status `pending_screen` with no reasons. | ING-034, ING-035, ARC-074, AGT-043, D-09; FR-029 |
| FEAT-041-FR-02 | A later arrival with the same `session_id` but different field values shall still be a duplicate; the first arrival's values are kept unchanged. | ING-037; DUP-02 |
| FEAT-041-FR-03 | Duplicate rows shall not be passed through the gate, screen, epoch assignment, baseline, scoring, CUSUM or day ledger; they remain in the output so the result holds one row per input record. | ING-035, ING-036, ANL-012; FR-030 |
| FEAT-041-FR-04 | `apply_quality_gate` shall evaluate each non-duplicate row: reason "quality flag poor" if `audio_quality_flag` ≠ "ok"; "noise above limit" if `mic_noise_level_dbfs` > `noise_limit_dbfs` (strict, −40.0 passes); "speech too short" if `speech_duration_s` < `min_speech_s` (strict, 1.0 passes); thresholds come from `PipelineConfig`. | ING-040; FR-040, FR-041, FR-042 |
| FEAT-041-FR-05 | All applicable reasons shall be recorded in the fixed order quality flag, noise, speech duration, as the `reasons` tuple and joined with "; " in `reason_text`; a row with ≥ 1 reason gets status `set_aside`, otherwise `pending_screen`. | ING-041, ING-043, AGT-049; FR-043 |
| FEAT-041-FR-06 | Set-aside rows shall be passed on unchanged so that they still belong to an epoch and count as a record for the day ledger, but they shall never be screened, used as a screen reference, scored, used for a baseline or used to update the tally. | ING-042; FR-044 |
| FEAT-041-FR-07 | Re-sending records shall change no result: the outcome for the remaining records is identical to a run without the extra copies. | ING-039; FR-031; AC-ANL-03 |
| FEAT-041-FR-08 | Both functions shall be pure, return new frozen instances in a deterministic order (input order by `arrival_seq`), and not depend on feature values for the gate decision. | ANL-003, ANL-021; TST-022 |

## Inputs

- `Sequence[RawRecord]` built from `raw_sessions` typed columns (any order, unique `arrival_seq`).
- `PipelineConfig` (`noise_limit_dbfs` −40.0, `min_speech_s` 1.0).

## Outputs

- `list[ScreenedRecord]` with status `duplicate`, `set_aside` or `pending_screen`, `reasons`, `reason_text`, one per input record, ordered by `arrival_seq`.

## Data Flow

1. `run_pipeline` step 4 (FEAT-052) calls `apply_quality_gate(mark_duplicates(recs), config)` after sorting by `arrival_seq` and excluding records after as-of.
2. `mark_duplicates` walks arrivals keeping a set of seen `session_id`s.
3. `apply_quality_gate` evaluates non-duplicate rows and returns new `ScreenedRecord`s.
4. Output flows to late-arrival detection and epoch assignment (FEAT-045, FEAT-042) and, via the runner, to `processed_sessions.status`, `reasons`, `reason_text`.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-040

- FEAT-040 (Analytics contracts and PipelineConfig): `RawRecord`, `ScreenedRecord`, `PipelineConfig`, `ContractError`.
- Downstream: FEAT-042 (epochs), FEAT-049 (day ledger), FEAT-052 (orchestrator).

## Database Impact

None directly (pure functions). The runner (FEAT-053) persists the results to `processed_sessions` (`status`, `reasons`, `reason_text`); TRD 20 `processed_sessions_status_reason_ck` admits exactly these reason strings.

## API Impact

None.

## Frontend Impact

None directly. Set-aside reasons appear in the check-in log ("quality flag poor; noise above limit") via FEAT-028 and FEAT-068; duplicates are never displayed (AGT-053).

## Analytics Impact

- Algorithms: first-arrival-wins deduplication keyed on `session_id` in `arrival_seq` order; threshold rules with strict comparisons.
- Calculations: reason list in fixed order, joined with "; ".
- Stage numbers 1 and 2 of ANL-006; stage names in warnings and logs `duplicate_detection`, `quality_gate` (LOG-063).

## Security Requirements

None specific: pure functions with no I/O; no feature values leave the engine except through persisted derived rows.

## Error Handling

- Duplicate `arrival_seq` values or a missing feature key are contract violations detected by `run_pipeline` input validation (`ContractError`, ANL-018).
- No exception for normal data (all duplicates, all set aside, empty input) (ANL-019).

## Logging Requirements

None in `analytics/` (LOG-006). Duplicate and set-aside counts appear in `PipelineResult.counts` (`duplicate`, `set_aside`), logged by the runner (FEAT-056).

## Testing Requirements

- Unit (`tests/unit/analytics/test_duplicate_detection.py`, marker `unit`): DUP-01..DUP-04; duplicate arriving out of time order (R04 day 18 copy last in the file) still `duplicate`.
- Unit (`tests/unit/analytics/test_quality_screening.py`): QG-01..QG-07 including boundaries −40.0 / −39.9 and 1.0 / 0.99, all-three-reasons order, R03 day 18 shape; Hypothesis property: gate output independent of feature values (TST-022).
- Validation (FEAT-059): VC-R04 and VC-R04-INV (removing arrivals 89 and 283 changes nothing for R04, AC-ANL-03), VC-R03 set-aside reasons, VC-G01 totals set_aside 12 and duplicate 2.

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-041-AC-01 | For arrivals A(S1), B(S2), C(S1), `mark_duplicates` returns A and B `pending_screen` and C `duplicate` with reason_text "session_id already received". | DUP-03, ING-034 |
| FEAT-041-AC-02 | Two arrivals of the same `session_id` with different feature values yield the first unchanged and the second `duplicate`. | DUP-02, ING-037 |
| FEAT-041-AC-03 | Noise −40.0 passes; −39.9 is `set_aside` with "noise above limit"; speech 1.0 passes; 0.99 is `set_aside` with "speech too short". | QG-02..QG-05, ING-040 |
| FEAT-041-AC-04 | A record with flag poor, noise −30.0 and speech 0.5 gets reasons ("quality flag poor", "noise above limit", "speech too short") and reason_text "quality flag poor; noise above limit; speech too short". | QG-06, ING-041 |
| FEAT-041-AC-05 | On SRC-05 the two stages mark arrivals 89 and 283 `duplicate` and exactly 12 records `set_aside` (R03 days 3, 7, 10, 14, 18, 22, 26; R08 days 5, 9, 20, 25, 29), with R03-20261018-01 reason_text "quality flag poor; noise above limit". | TRD 10 §4.7, §4.8 fixture checks, VC-G01 |
| FEAT-041-AC-06 | Removing arrivals 89 and 283 from the input leaves every R04 output of the full pipeline unchanged. | AC-ANL-03, VC-R04-INV, FR-031 |

## Definition of Done

- Both modules implemented with the binding signatures; unit cases DUP-01..DUP-04 and QG-01..QG-07 pass (TST-020).
- Test files exist for both modules (TST-011); `analytics/` coverage ≥ 95 % (TST-140).
- FEAT-041-AC-06 passes in the validation suite once FEAT-052 assembles the pipeline.

## Implementation Notes

- Sort by `arrival_seq` explicitly even if the input looks sorted (ANL-021).
- Gate thresholds are read from `config.noise_limit_dbfs` and `config.min_speech_s`; do not hard-code −40.0 or 1.0 (AGT-020).
- Reason strings must match TRD 20 `processed_sessions_status_reason_ck` exactly: "quality flag poor", "noise above limit", "speech too short", "session_id already received".
- TRD gap: ING-037 requires a later copy with differing values to "carry warning `duplicate_payload_differs`"; ING-023 lists it among ingest warning codes (stored in `raw_sessions.ingest_warnings`), while TRD 07 ANL-052 does not list it as a `RunWarning`. This stage therefore does not emit it; the ingest path (FEAT-025/FEAT-026) does. Report the ambiguity for TRD 24 confirmation.
