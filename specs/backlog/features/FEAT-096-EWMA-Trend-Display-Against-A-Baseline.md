# FEAT-096 EWMA trend display against a baseline band

| Field | Value |
|---|---|
| Epic | Analytics Engine |
| Build phase | Future research (TRD 25 Phase 12 open items; gated on OQ-18) |
| Priority | P2 |
| Complexity | Medium |
| MVP status | Future |
| Dependencies | FEAT-046, FEAT-067 |
| Status | Not Started |

## Purpose

Provide the "EWMA trend shown against baseline band" that the final box of the SRC-02 processing flowchart mentions, if the team decides it is wanted. The TRDs fix only its boundaries: it is an additional output field on `ScoreRow`, computed after scoring, display-only, and it must not alter `cusum_tally`, `alarm_state`, alarms or the answer key. Whether to build it at all, its smoothing parameter, the band definition and where it is shown are open (OQ-18). The MVP shows only the CUSUM "Running change tally" chart.

## Business Context

- SRC-02 mentions the EWMA trend; no wireframe (SRC-09, SRC-10) shows it, so it is deferred (DSC-02, TRD 00 X-15, OQ-18).
- BR-11 and BR-15: alarms come only from CUSUM; the answer key (Exp_scores) must stay identical (CUS-036, AGT-008).
- BR-13 (Resident detail): a possible extra visual aid for staff, subject to the plain-language and "not a diagnosis" wording rules (AGT-018).

## Referenced TRDs

- TRD 07 ANL-056 (extension point), ANL-006 (stage order), §4.3 `ScoreRow` contract.
- TRD 09 CUS-036, §4.7.
- TRD 00 X-15.
- TRD 01 §4.5 note (EWMA display deferred).
- TRD 02 §2 out-of-scope (EWMA trend display, OQ-18).
- TRD 04 OQ-18 row (not built), FE-093..FE-097 (CusumChart, owned by FEAT-067).
- TRD 11 §2 out of scope (EWMA trend display or baseline band charts), UX-080..UX-092.
- TRD 25 §4.6 Phase 2 Pitfalls ("Do not add an EWMA chart (OQ-18)"), AGT-008, AGT-020, AGT-021.
- TRD 24 OQ-18 (gate), DSC-02, D-30.

## Scope

Decided by the TRDs:

- Computation as an additional field on `ScoreRow` (frozen dataclass of TRD 07 §4.3) computed after the scoring step, in a pure function, with all parameters from `PipelineConfig` (no hard-coded constant).
- Display-only: no effect on `cusum_tally`, `alarm_state`, alerts, data alerts or any expected value of `test_v0_1`.
- Not built in v0.1; the Resident detail page keeps the CUSUM chart of D-30 unchanged.

Blocked on OQ-18 (not decided here):

- Whether an EWMA trend is displayed at all.
- The EWMA input (composite z or individual features), the smoothing weight λ and its initial value, and the "baseline band" definition; the TRDs give none of these.
- Where it is shown (Resident detail below or beside the tally chart, Alert review mini chart, Analytics) and its wording; no wireframe exists, so a wireframe and TRD 04/TRD 11 requirements are needed first.
- Persistence and API: TRD 20 `scores` has no EWMA column and TRD 19 `ScoreRow`/score DTOs have no EWMA field; adding them requires TRD 20/TRD 19 changes (Alembic migration, OpenAPI regeneration, D-51) decided with OQ-18.
- Stage placement wording: ANL-056 says "computed after step 10", but in the ANL-006 order step 7 is scoring, step 8 CUSUM and step 10 the day ledger; the intended placement (after scoring/CUSUM, before or after the ledger) must be confirmed in TRD 07 when OQ-18 closes. Either way it must not change CUSUM.

Trigger for starting: OQ-18 answered "yes" in TRD 24 (Megan Stubbs with Shaba Rahavi) with the input, λ, band definition and a wireframe for the display location; TRD 07, 09, 11, 19, 20 updated accordingly.

## Out of Scope

- Any change to CUSUM, alarm persistence, alert generation or review behaviour (CUS-036).
- Alarming or data alerts on the EWMA trend.
- Building any EWMA chart before OQ-18 is answered (TRD 25 §4.6 Phase 2 Pitfalls).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-096-FR-01 | The EWMA trend shall be an additional output field on `ScoreRow` computed after scoring and shall not alter `cusum_tally` or `alarm_state`. | ANL-056 |
| FEAT-096-FR-02 | The EWMA shall be display-only and shall not influence alarms. | CUS-036 |
| FEAT-096-FR-03 | The computation shall be pure and deterministic, with every parameter read from `PipelineConfig` (loaded from `config_parameters`). | AGT-020, AGT-021, ARC-041 |
| FEAT-096-FR-04 | The EWMA input, smoothing weight, initialisation, band definition, display location and wording shall be those recorded in TRD 24 when OQ-18 closes; the implementer shall not choose them. | OQ-18, AGT-009 |
| FEAT-096-FR-05 | The R01–R10 validation (Exp_scores `cusum_tally`, `alarm_state`, all other compared values) shall pass unchanged with the EWMA field present. | AGT-008, TST-080 |
| FEAT-096-FR-06 | Any display shall follow the plain-language and "detects a change, not a diagnosis" wording rules and the WCAG 2.1 AA rules (status not by colour alone, text alternative table). | AGT-018, UX-225 |
| FEAT-096-FR-07 | No EWMA component, chart or API field shall exist in the codebase before OQ-18 closes. | TRD 25 §4.6 Phase 2 Pitfalls, X-15 |

## Inputs

- `ScoreRow` stream from the scoring stage (FEAT-046), active `PipelineConfig`.
- The OQ-18 decision and the new wireframe.

## Outputs

- After OQ-18: the EWMA field on `ScoreRow`, its persisted column and API field (per the TRD 20/TRD 19 changes), and the display component on the decided page.

## Data Flow

Scored sessions (`composite_z` and/or feature z) → EWMA function (pure, config parameters) → `ScoreRow.<ewma field>` → persistence (per decided schema) → score read endpoint → frontend chart against the band. CUSUM and alerts consume the same `ScoreRow` values as before and ignore the EWMA field.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-046, FEAT-067

- [FEAT-046](FEAT-046-Z-Score-And-Composite-Scoring-Stage.md) Z-score and composite scoring stage (produces the `ScoreRow` values the EWMA would smooth).
- [FEAT-067](FEAT-067-Running-Change-Tally-Chart-And-Text.md) Running change tally chart and text table (the existing chart the display would sit beside).

Gate: OQ-18 (whether to display EWMA).

## Database Impact

- None until OQ-18 closes. A decided EWMA would need a new nullable column on `scores` (TRD 20 change, Alembic migration, expand-only per DEP-061); no such column exists today.

## API Impact

- None until OQ-18 closes. A decided EWMA would add a field to the score DTOs of TRD 19 (OpenAPI regeneration and `frontend/lib/api-types.ts`, D-51).

## Frontend Impact

- None until OQ-18 closes and a wireframe exists. The CUSUM chart (`CusumChart`, `CusumTable`, D-30) remains unchanged.

## Analytics Impact

- Algorithm (after OQ-18): exponentially weighted moving average over scored sessions with the decided λ and band; calculation added after scoring, independent of the CUSUM recursion S = max(0, S + composite_z − k).

## Security Requirements

- Same read roles as the score endpoints; no new data category; study IDs only.

## Error Handling

- Residents without a frozen baseline have no scored sessions and therefore no EWMA values (empty state as the tally chart, UX-104 pattern); other conditions follow the OQ-18 decision.

## Logging Requirements

- None beyond existing pipeline logs; `analytics/` does not log (LOG-006).

## Testing Requirements

- Unit: EWMA function determinism and the decided recursion; property test that adding the field leaves `cusum_tally` and `alarm_state` identical for random inputs (extending TST-022).
- Validation: `pytest tests/validation -q` unchanged.
- Frontend: component test and axe check for the new display (TST-110 route list).
- Inspection before OQ-18: `grep -rni "ewma" analytics backend frontend/app frontend/components` returns nothing.

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-096-AC-01 | Before OQ-18 is answered, `grep -rni "ewma" analytics backend frontend/app frontend/components` returns no match. | CUS-036, X-15 |
| FEAT-096-AC-02 | After implementation, pipeline output with and without the EWMA field has identical `cusum_tally`, `alarm_state` and alerts for SRC-05 and for random property-test inputs. | ANL-056, CUS-036 |
| FEAT-096-AC-03 | After implementation, `pytest tests/validation -q` passes unchanged. | AGT-008 |
| FEAT-096-AC-04 | After implementation, every EWMA parameter is a `config_parameters` key validated by `PipelineConfig.from_mapping`. | AGT-020, ANL-029 |

## Definition of Done

- Gate satisfied (OQ-18 answered yes with parameters and wireframe) and TRDs updated; all FEAT-096 acceptance criteria pass. If OQ-18 is answered "no", nothing is implemented and FEAT-096-AC-01 remains the standing check.

## Implementation Notes

- Treat this as a display addition only: keep the CUSUM engine untouched and compute the EWMA in its own module or helper fed from `ScoreRow`.
- A new algorithm key changes `config_hash()` and requires `rebuild` (ANL-032); plan the release accordingly.
