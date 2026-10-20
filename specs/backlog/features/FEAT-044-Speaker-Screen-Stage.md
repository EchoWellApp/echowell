# FEAT-044 Speaker screen stage

| Field | Value |
|---|---|
| Epic | Analytics Engine |
| Build phase | Phase 6 (TRD 25) |
| Priority | P0 |
| Complexity | High |
| MVP status | Required |
| Dependencies | FEAT-042, FEAT-043 |
| Status | Not Started |

## Purpose

Quarantine check-ins that were probably spoken by someone else (a visitor or staff member) before they enter a baseline or a score. Each record that passed the quality gate is compared, on raw values, with the first up to N prior usable sessions of the same resident-epoch: if the pitch (`mean_f0_hz`) is far off and at least two of the seven composite features are also far off, the record is quarantined with a reason that states the pitch z and the count. Without speaker verification from Team 1 (OQ-14), this heuristic protects the baseline; it reproduces R05's two quarantined days exactly.

## Business Context

- BR-05 (possible other speaker set apart): quarantine rule, reason text, exclusion from baseline, scores and tally.
- BR-15: R05-20261008-01 "possible other speaker (F0 z=-8.61; composite features with |z|>=3: 4)" and R05-20261022-01 "possible other speaker (F0 z=-7.34; composite features with |z|>=3: 3)"; no other SRC-05 record quarantined.
- FRs covered (BACKLOG.md): FR-060, FR-061, FR-062, FR-063, FR-064, FR-065.

## Referenced TRDs

- TRD 08 BSC-011..BSC-019 (screen order, first-N reference, minimum 5, robust z with zero-spread rule, quarantine rule, reason format, exclusion, before and after freeze, `screen_detail`), §4.4 pseudocode and fixture check, BSC-040 (late records' own screen).
- TRD 07 §4.2 (`screen_speakers` signature), §4.3 (`EpochedRecord.screen_detail`), §4.7 (`screen_min_n`, `screen_f0_z`, `screen_other_z`, `screen_other_count`).
- TRD 13 Table 4.3-A SCR-01..SCR-10; TRD 08 AC-BSC-04; TRD 14 VC-R05.
- TRD 25 AGT-044, AGT-054; TRD 24 D-13; OQ-14 (speaker verification).

## Scope

- `analytics/speaker_screen.py::screen_speakers(rows: Sequence[EpochedRecord], config) -> list[EpochedRecord]`.
- The screen for late records with their own reference (BSC-040), without adding them to any reference list.
- Unit tests `tests/unit/analytics/test_speaker_screen.py`.

## Out of Scope

- Speaker verification by the device (OQ-14; future FEAT-097).
- Late-arrival classification itself (FEAT-045) and the appended late reason (BSC-040, set by FEAT-045).
- Persisting `screen_detail` (FEAT-053) and the `possible_other_speaker` data alert (FEAT-050).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-044-FR-01 | For each (resident, epoch), the screen shall visit records in `(timestamp_utc, arrival_seq)` order, excluding late records from the walk, and evaluate only `pending_screen` records; set-aside records are skipped and never become references. | BSC-011, BSC-017; FR-060 |
| FEAT-044-FR-02 | The reference for record r shall be `prior[0:baseline_n]`: the first up to N usable sessions of the same epoch that precede r in time order (not the most recent N); after freeze it therefore equals the baseline members. | BSC-012, BSC-018, AGT-044, D-13; FR-060, FR-064 |
| FEAT-044-FR-03 | The screen shall run only when the reference has at least `screen_min_n` (5) sessions; otherwise r becomes `usable` with `screen_detail` None. | BSC-013; FR-061 |
| FEAT-044-FR-04 | For `mean_f0_hz` and each of the 7 composite features, z = (x − median) / spread from `robust(reference raw values, floor_f, mad_scale)` using raw (unadjusted) values; if spread equals 0 the z value is 0.0. | BSC-014, AGT-042, AGT-050; FR-060 |
| FEAT-044-FR-05 | `screen_detail` shall be "F0 z=<z_F0 with {:.2f}>; composite features with \|z\|>=3: <n3>" where n3 counts composite features with \|z\| ≥ `screen_other_z`. | BSC-016, BSC-019, AGT-054 |
| FEAT-044-FR-06 | r shall be quarantined if and only if \|z_F0\| ≥ `screen_f0_z` (4.0) and n3 ≥ `screen_other_count` (2) (both inclusive); a quarantined record gets exactly one reason, equal to its `reason_text`, "possible other speaker (" + screen_detail + ")". | BSC-015, BSC-016, PGS-012; FR-062, FR-063 |
| FEAT-044-FR-07 | A quarantined record shall not be appended to the reference list and shall never enter a baseline, be scored or update the tally; a usable record shall be appended. | BSC-017; FR-065 |
| FEAT-044-FR-08 | The screen shall apply both before and after the baseline freezes. | BSC-018; FR-064 |
| FEAT-044-FR-09 | A late record that passed the gate shall be screened against the first N usable non-late sessions that precede it in its assigned epoch (no screen when it has no epoch or fewer than 5 references), becoming `usable` or `quarantined` without joining any reference list. | BSC-040, ANL-025 |
| FEAT-044-FR-10 | `screen_detail` shall be set for every screened record, usable or quarantined, so it can be stored in `processed_sessions.screen_detail`. | BSC-019 |

## Inputs

- `Sequence[EpochedRecord]` (statuses duplicate, set_aside, pending_screen; epochs assigned; late flag).
- `PipelineConfig` (`baseline_n`, `screen_min_n`, `screen_f0_z`, `screen_other_z`, `screen_other_count`, `mad_scale`, `pause_floor`).

## Outputs

- `list[EpochedRecord]` with final statuses `usable`, `quarantined`, `set_aside`, `duplicate`, `reasons`, `reason_text`, `screen_detail`.

## Data Flow

1. `run_pipeline` step 6 (FEAT-052): `screen_speakers(assign_epochs(screened, late), config)`.
2. Per (resident, epoch): walk non-late records in time order with `prior = []`; compute robust stats of the reference raw values for F0 and the 7 composite features; decide; append usable records.
3. Late records are screened afterwards against their own reference.
4. Output feeds morning adjustment and baselines (FEAT-043, FEAT-045); the runner stores status, reasons and `screen_detail`.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-042, FEAT-043

- FEAT-042 (Epoch detection): records grouped by epoch, late records marked.
- FEAT-043 (Local time derivation): the shared ordering/local-time helper and the separation of raw and adjusted values in the contracts.
- Transitively FEAT-040 (`robust`, config).
- Downstream: FEAT-045, FEAT-050 (quarantine count per resident), FEAT-052.

## Database Impact

None directly. The runner writes `processed_sessions.status` (`quarantined`), `reasons`, `reason_text`, `screen_detail` (FEAT-053); TRD 20 CHECKs require the quarantine reason pattern and a non-null `screen_detail` for quarantined rows.

## API Impact

None directly; quarantine reasons appear in check-in events (FEAT-028) and counts (FEAT-027, FEAT-035).

## Frontend Impact

None.

## Analytics Impact

- Algorithm: robust z of a record against the first-N usable reference of its epoch (median/MAD × 1.4826 with the pauses floor 0.5), joint rule on F0 and composite features.
- Calculations: z per feature (zero when spread is 0), count of \|z\| ≥ 3, two-decimal formatting only for the reason string.
- Stage 4 of ANL-006 (`speaker_screen`, LOG-063).

## Security Requirements

None specific (pure function). The screen is a heuristic substitute for speaker verification; it does not identify anyone (RSK-01, OQ-14).

## Error Handling

- Zero spread → z = 0.0 (no division error) (BSC-014).
- Fewer than 5 references → no screen, no error.
- Contract violations raise `ContractError` only via `run_pipeline` input validation.

## Logging Requirements

None in `analytics/` (LOG-006).

## Testing Requirements

- Unit (`tests/unit/analytics/test_speaker_screen.py`, marker `unit`): SCR-01..SCR-10 (4 vs 5 references, inclusive thresholds, first-16 reference with 20 priors, floored pause spread and zero F0 spread, quarantined not appended, raw values for morning sessions, R05 day 8 exact reason); a "most recent 16" variant must fail the R05 day 22 assertion (TRD 08 §4.4 note).
- Validation (FEAT-059): VC-R05 (two quarantined sessions with exact strings), VC-G01 quarantined 2, AC-BSC-04 (267 usable).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-044-AC-01 | With 4 prior usable sessions the screen does not run and the record is `usable` with `screen_detail` None; with 5 it runs and sets `screen_detail` "F0 z=<2dp>; composite features with \|z\|>=3: <n>". | SCR-01, SCR-02, BSC-013 |
| FEAT-044-AC-02 | \|z_F0\| = 4.0 with exactly 2 composite features at \|z\| = 3.0 → `quarantined`; \|z_F0\| = 4.5 with 1 → `usable`; \|z_F0\| = 3.99 with 7 → `usable`. | SCR-03..SCR-05, BSC-015 |
| FEAT-044-AC-03 | With 20 prior usable sessions the reference uses only the first 16. | SCR-06, BSC-012 |
| FEAT-044-AC-04 | Identical prior `number_of_pauses` gives a spread of 0.5 (floor) and identical prior F0 gives z_F0 = 0. | SCR-07, BSC-014 |
| FEAT-044-AC-05 | A morning session is screened on raw values (changing the configured offsets does not change its screen result). | SCR-09, AGT-050 |
| FEAT-044-AC-06 | On SRC-05, R05-20261008-01 reason_text is exactly "possible other speaker (F0 z=-8.61; composite features with \|z\|>=3: 4)" and R05-20261022-01 exactly "possible other speaker (F0 z=-7.34; composite features with \|z\|>=3: 3)"; no other record is quarantined and 267 records are usable. | SCR-10, VC-R05, AC-BSC-04 |

## Definition of Done

- Module implemented with the binding signature; SCR-01..SCR-10 pass (TST-020); test file exists (TST-011).
- VC-R05 passes in the validation suite (FEAT-059); `analytics/` coverage ≥ 95 %.

## Implementation Notes

- The reference list is `prior[:config.baseline_n]` — the first N, never a sliding window (AGT-044); after freeze it equals the baseline sessions.
- Use raw values from `record.features`; never the adjusted mapping (a common bug, TRD 08 §8).
- Format with `f"{z_f0:.2f}"` on the float64 value; do not round z anywhere else (AGT-054).
- Former TRD conflict: the TRD 08 §4.4 pseudocode set `reasons = ("possible other speaker",)` with the long form only in `reason_text`, while TRD 07 §4.3 defines `reason_text` as the reasons joined by "; " and TRD 20 `processed_sessions_status_reason_ck` (PGS-012) requires `reasons[1]` to match `possible other speaker (F0 z=…; composite features with |z|>=3: …)` and `reason_text = array_to_string(reasons, '; ')`. Store the full reason text as the single element of `reasons` (it then equals `reason_text` and the workbook string); the TRD 08 §4.4 pseudocode now does the same (aligned in the PR #2 consistency fixes).
