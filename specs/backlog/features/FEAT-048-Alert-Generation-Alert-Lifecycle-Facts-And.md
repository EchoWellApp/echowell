# FEAT-048 Alert generation, alert lifecycle facts and Leaning most

| Field | Value |
|---|---|
| Epic | Analytics Engine |
| Build phase | Phase 6 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-047, FEAT-030 |
| Status | Not Started |

## Purpose

Create exactly one alarm event when a resident's tally first crosses the alarm line in an epoch, carry the facts the persistence service needs to close it only when the epoch ends or a rebuild no longer produces that crossing (no manual closure in v0.1), and compute "Leaning most" — the up to three measurements that moved most in the direction of change since the alarm — which the Resident chart Summary shows as plain words ("Leaning most: …", TRD 11 UX-312; the v0.1 Alert review panel is retired, TRD 24 D-110) ("more pauses, quieter, less voiced sound" for R09). The alert is a prompt for a nurse to check in, delivered only inside the dashboard.

## Business Context

- BR-11 (one alarm per sustained change; alarm persists; dashboard only): alert events, epoch-end closure facts, no push.
- BR-13 / BR-10: "Leaning most" helps the reviewer see which measurements moved.
- BR-14: new-admission comparisons never create alerts (FR-206).
- FRs covered (BACKLOG.md): FR-053, FR-104, FR-109, FR-110, FR-206, FR-266.

## Referenced TRDs

- TRD 09 CUS-011..CUS-021 (alert events, epoch-ended facts, no alert without formed baseline or below h, natural-key upsert, never deleted, superseded by rebuild, review semantics, epoch-end closure, reserved `admin`, display status while open or acknowledged, status after epoch end), CUS-041 ("Leaning most"), §4.3 lifecycle, §4.8 "Leaning most" definition and reference values.
- TRD 07 §4.2 (`generate_alerts`, `leaning_most` signatures), §4.3 (`AlertEvent`), §4.5 step 12, ANL-039 (persistence rules this feature's facts must support).
- TRD 06 DB-018 (alert reconciliation).
- TRD 05 API-080 (`leaning_most` on `GET /api/v1/alerts`), API-006.
- TRD 13 Table 4.3-A AL-01..AL-04, Table 4.3-B AN-08; TRD 09 AC-CUS-02, AC-CUS-03, AC-CUS-07, AC-CUS-09; TRD 19 OAS-027; TRD 14 TDV-069, VC-G10.
- TRD 25 AGT-058; TRD 24 D-03, D-11, D-79, D-92.

## Scope

- `analytics/alert_generator.py::generate_alerts(scores, epochs, config) -> list[AlertEvent]` and `leaning_most(scores, alert, config) -> tuple[str, ...]`.
- Epoch-ended facts on `AlertEvent` (`epoch_ended`, `epoch_ended_at`).
- Wiring `leaning_most` into `GET /api/v1/alerts` by replacing the FEAT-030 provider: the alert service builds `ScoreRow` contracts from persisted `scores` of the alert's epoch up to the as-of and calls `analytics.alert_generator.leaning_most`.
- Unit tests `tests/unit/analytics/test_alert_generator.py`; API assertion of `leaning_most` values.

## Out of Scope

- Persisting alerts: natural-key upsert, closing with `epoch ended` / `superseded by rebuild`, `closed_at`, `alert.closed` audit, `alert_first_crossing_changed` warning (FEAT-053, which implements CUS-014, CUS-015, CUS-018, ANL-039, DB-018 using these facts).
- Reviews and snooze (FEAT-031); the alerts list endpoint itself (FEAT-030).
- Rendering labels ("more pauses, quieter, …") — the frontend `LeaningMost` component (FEAT-069) maps keys to lower-cased TRD 11 labels.

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-048-FR-01 | `generate_alerts` shall emit exactly one `AlertEvent` per resident-epoch whose scores contain a session with `alarm_state` "rings", with `session_id` of that session, `triggered_at` = its `timestamp_utc`, `local_date` = its local date and `cusum_value` = its `cusum_tally`. | CUS-011; FR-104 |
| FEAT-048-FR-02 | No alert shall be generated for an epoch without a formed baseline, nor while the tally stays below h, nor a second time in the same epoch after the tally falls below h and crosses again. | CUS-013, CUS-007; AL-02 |
| FEAT-048-FR-03 | `AlertEvent.epoch_ended` shall be true and `epoch_ended_at` = the next epoch's `started_at` when the resident has a later epoch; otherwise false and None. These facts let the persistence service close the alert with reason "epoch ended". | CUS-012, CUS-018, D-11; FR-053 |
| FEAT-048-FR-04 | Alert events shall carry everything the natural key `(epoch_id, session_id)` needs (resident, epoch number, session_id) so that a rebuild maps them to existing alert rows and their reviews and snooze survive; an event the computation no longer produces is the signal for "superseded by rebuild". | CUS-014, CUS-015, API-128; AL-04 |
| FEAT-048-FR-05 | The engine shall offer no manual closure; `closed_reason` "admin" is reserved and never produced. | CUS-019; FR-110 |
| FEAT-048-FR-06 | `leaning_most(scores, alert, config)` shall take the scored sessions of the alert's epoch with `local_date` ≥ the alert's `local_date` (ringing session included) up to as-of, compute per composite feature the mean of signed z (sign_f × z_f), keep features with mean > 0, sort by mean descending with ties broken by canonical feature order, and return at most 3 feature keys (an empty tuple when none qualifies). | CUS-041; TRD 09 §4.8; FR-266 |
| FEAT-048-FR-07 | `GET /api/v1/alerts` shall return `leaning_most` for each alert computed as in FEAT-048-FR-06 from persisted scores up to the as-of of the latest succeeded run. | API-080, CUS-041; D-92 |
| FEAT-048-FR-08 | Alerts shall be produced only from longitudinal own-baseline scoring; new-admission facility comparisons never create alerts or affect any tally. | FR-206; D-06 |
| FEAT-048-FR-09 | No code in this feature shall send e-mail, SMS or push notifications. | FR-109, CUS-022 |

## Inputs

- `ScoreRow`s with `cusum_tally` and `alarm_state` (FEAT-047); `EpochSummary` per resident-epoch (epoch boundaries); `PipelineConfig` (signs, feature order).
- For the API: persisted `scores` rows of the alert's epoch and the as-of.

## Outputs

- `list[AlertEvent]` (including `leaning_most` at run time); `leaning_most` values in `Alert` DTOs.

## Data Flow

1. `run_pipeline` step 12 (FEAT-052): `generate_alerts(scores, epochs, config)` scans each epoch's rows for the "rings" row, builds the event and its epoch-ended facts, and fills `leaning_most` with the scores up to as-of.
2. The runner (FEAT-053) upserts `alerts` on `(epoch_id, session_id)`, closes epoch-ended or superseded alerts with `closed_at` = as-of.
3. At read time, `alert_service` (FEAT-030 seam) loads the epoch's scores from `local_date` ≥ alert date to the as-of, maps them to `ScoreRow`, calls `analytics.alert_generator.leaning_most`, and returns the keys.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-047, FEAT-030

- FEAT-047 (CUSUM engine): tallies and "rings" states.
- FEAT-030 (Alerts list API): the `leaning_most` provider seam and the `Alert` DTO.

Features that build directly on this one (BACKLOG.md §4): FEAT-050, FEAT-052, FEAT-066.

## Database Impact

- Engine: none (pure).
- API wiring: reads `scores` (`z`, `local_date`, `epoch_id`) and `alerts`; writes nothing.
- The runner (FEAT-053) writes `alerts` using these facts.

## API Impact

- Modified: `GET /api/v1/alerts` (E-13) now returns computed `leaning_most` values (schema unchanged).

## Frontend Impact

None in this feature; `LeaningMost` renders the keys (FEAT-069).

## Analytics Impact

- Algorithms: first-crossing alert event; epoch-end facts; mean signed z ranking with canonical tie-break.
- Calculations: mean of sign × z per feature over sessions since the alarm.
- Stage 9 of ANL-006 (`alerts`, LOG-063).

## Security Requirements

- Read path: `GET /alerts` keeps the FEAT-030 roles (all user roles).
- No outbound channel (FR-109).

## Error Handling

- Epochs without scores or crossings yield no events (no error).
- `leaning_most` with no qualifying feature returns an empty list (CUS-041), rendered by the UI as "No single measurement stands out".

## Logging Requirements

None in `analytics/` (LOG-006); the runner logs alert counts (`alerts_opened`) and `alert.closed` audit rows (FEAT-053/FEAT-056).

## Testing Requirements

- Unit (`tests/unit/analytics/test_alert_generator.py`, marker `unit`): AL-01..AL-03 (first crossing, no second alert on recrossing, epoch-ended facts); AN-08 (R09 → number_of_pauses, loudness_dbfs, voiced_fraction); R10 → number_of_pauses, articulation_rate_syl_per_s, speech_rate_syl_per_s; tie-break by canonical order; empty when all means ≤ 0.
- Integration (`tests/integration/pipeline/`, with FEAT-053): AL-04 rebuild keeps id, reviews, `acknowledged`, `snoozed_until`; AC-CUS-07 new epoch closes the epoch-1 alert with "epoch ended".
- API (`tests/integration/api/test_alerts.py`): `leaning_most` values for DS-07 (OAS-027, TDV-069).
- Validation (FEAT-059): VC-G10 (exactly two open alerts R09, R10 with session, times and cusum values).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-048-AC-01 | A first crossing yields one `AlertEvent` with resident, epoch, session_id, `triggered_at`, `cusum_value` of the "rings" row; a tally that drops below h and recrosses in the same epoch yields no second event. | AL-01, AL-02, CUS-011 |
| FEAT-048-AC-02 | When the resident has a later epoch, the epoch-1 event has `epoch_ended` true and `epoch_ended_at` equal to epoch 2's `started_at`. | AL-03, CUS-012 |
| FEAT-048-AC-03 | On SRC-05 exactly two events exist: R09 epoch 1 at R09-20261021-01 (triggered 2026-10-21 19:07:50 UTC, local 2026-10-21, cusum_value 5.431965 ±1e-6) and R10 epoch 1 at R10-20261024-01 (cusum_value 5.972050 ±1e-6), both not epoch-ended. | AC-CUS-02, AC-CUS-03, VC-G10 |
| FEAT-048-AC-04 | `leaning_most` for R09 (sessions Oct 21–30) returns (number_of_pauses, loudness_dbfs, voiced_fraction) and for R10 (Oct 24–30) (number_of_pauses, articulation_rate_syl_per_s, speech_rate_syl_per_s). | AN-08, TRD 09 §4.8, OAS-027 |
| FEAT-048-AC-05 | With DS-07 loaded, `GET /api/v1/alerts?status=open` returns those `leaning_most` arrays for R09 and R10. Verified by: Test (`tests/integration/api/test_alerts.py`). | OAS-027, TDV-069, AC-CUS-09 |
| FEAT-048-AC-06 | After a review and a snooze on the R09 alert, a full rebuild keeps the alert id, its reviews, status `acknowledged` and `snoozed_until`. | AL-04, AC-ANL-11 |
| FEAT-048-AC-07 | A resident with an open epoch-1 alert who starts epoch 2 has the epoch-1 alert `closed` with `closed_reason` "epoch ended" and shows `baseline_forming` until epoch 2 forms. Verified by: Integration (`tests/integration/pipeline/`). | AC-CUS-07, CUS-018, CUS-021 |

## Definition of Done

- All FEAT-048 acceptance criteria pass.
- `generate_alerts` and `leaning_most` implemented with the binding signatures; AL-01..AL-03 and AN-08 pass (TST-020); test file exists (TST-011).
- `GET /alerts` returns computed `leaning_most`; OAS-027 passes on DS-07.
- AL-04 and AC-CUS-07 pass with FEAT-053 in the same Phase 6 checkpoint PR of Block 3.
- The batch report lists the implemented requirement IDs (AGT-022); the TRD differences noted under Implementation Notes were resolved in PR #2 and need no report.

## Implementation Notes

- Sessions for "Leaning most" are the alert epoch's scored sessions with `local_date` ≥ the alert date up to as-of; reference means for R09: pauses 2.158, loudness 2.133, voiced 2.092 (TRD 09 §4.8).
- TRD 20 has no column for `leaning_most`, so it must be computed on read; TRD 05 API-006 says analytics computations happen "only by calling `analytics.pipeline`", while TRD 07 §4.2 exposes `alert_generator.leaning_most` as a public function and API-080 requires the value on every alert. Calling `analytics.alert_generator.leaning_most` from the alert service re-implements nothing (TRD 07 §8); API-006 now names this read-side call explicitly (TRD 24 D-79).
- Keep the alert row free of human state in the engine: reviews, acknowledgement and snooze are never engine inputs (AGT-058).
- `triggered_at` is the session's `timestamp_utc`, so alert ids and times are deterministic under rebuild (TRD 19 E-13 note).
