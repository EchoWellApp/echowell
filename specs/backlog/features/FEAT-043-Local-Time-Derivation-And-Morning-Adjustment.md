# FEAT-043 Local time derivation and morning adjustment

| Field | Value |
|---|---|
| Epic | Analytics Engine |
| Build phase | Phase 6 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-040 |
| Status | Not Started |

## Purpose

Convert every record's UTC timestamp to the facility's local time with the IANA time-zone database, derive the local date (which drives the day ledger and all 30-day windows), the local time and the morning flag (local hour before 12), and compute morning-adjusted feature values by subtracting the configured per-feature morning offsets. Voices sound different in the morning; baselines and scores compare adjusted values so that a morning check-in is not mistaken for a change. A fixed −5 h offset would break after daylight saving ends on 1 Nov 2026.

## Business Context

- BR-07 (account for time of day): morning classification and configured offsets.
- BR-06 (correct local days): local date from the facility time zone, DST-safe.
- BR-15: R06 has 10 morning sessions (days 1, 4, …, 28); Exp_morning_offset values and R06 baselines match.
- FRs covered (BACKLOG.md): FR-070, FR-071, FR-072, FR-073, FR-074.

## Referenced TRDs

- TRD 08 BSC-020..BSC-024 (zoneinfo conversion, morning rule, adjustment, adjusted vs raw use, stored fields), §4.5 worked example (R06-20261004-01).
- TRD 10 ING-027 (local date and time only via `FACILITY_TZ` and zoneinfo).
- TRD 03 NFR-130..NFR-132 (UTC storage, DST vectors, midnight boundaries); NFR-133 and NFR-134 are served by the frontend (FEAT-062) and the nightly job (FEAT-054).
- TRD 07 §4.2 (`morning_offset.adjust` signature), §4.3 (`AdjustedRecord`), §4.7 (`facility_tz`, `morning_cutoff_hour`, `morning_offsets`), ANL-055 (offsets only from config).
- TRD 23 DME-019 (UTC storage, local conversion via `facilities.timezone`).
- TRD 13 Table 4.3-A MO-01..MO-07; TRD 14 VC-R06, VC-G07.
- TRD 25 AGT-040, AGT-050; TRD 24 D-02.

## Scope

- `analytics/morning_offset.py::adjust(rows: Sequence[EpochedRecord], config) -> list[AdjustedRecord]`: local datetime, local date, local time, `is_morning`, adjusted values for all 19 features.
- The shared local-time helper used by every stage that needs a local date (day ledger, windows) so the conversion exists once.
- Unit tests `tests/unit/analytics/test_morning_offset.py`, including the 1 Nov 2026 DST cases.

## Out of Scope

- Estimating offsets from data (OQ-09; future FEAT-094, ANL-055 `estimate_offsets`).
- Baseline membership and ordinal (FEAT-045), although `AdjustedRecord` carries those fields.
- Displaying local times in the UI with the zone abbreviation (NFR-133, FEAT-062) and the nightly 02:xx rule (NFR-134, FEAT-054).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-043-FR-01 | The local datetime of every non-duplicate record shall be `timestamp_utc.astimezone(ZoneInfo(config.facility_tz))`; the UTC hour or UTC date shall never be used for the morning flag or the local date. | BSC-020, ING-027, NFR-130, AGT-040; FR-070 |
| FEAT-043-FR-02 | `local_date` and `local_time` shall be derived from that local datetime for every non-duplicate record. | BSC-024; FR-070 |
| FEAT-043-FR-03 | A record shall be morning if and only if its local hour (0–23) is less than `config.morning_cutoff_hour` (12). | BSC-021; FR-071 |
| FEAT-043-FR-04 | For a morning record, adjusted value = raw − `config.morning_offsets[f]` for each of the 19 features; for any other record adjusted = raw; offsets come only from configuration and are never estimated. | BSC-022, ANL-055, D-02; FR-072, FR-073 |
| FEAT-043-FR-05 | Adjusted values shall be produced for every non-duplicate record (19 keys) for storage in `processed_sessions.adjusted_features`; baselines and scores use adjusted values; the speaker screen keeps using raw values. | BSC-023, AGT-050; FR-074 |
| FEAT-043-FR-06 | Conversions shall be correct across DST transitions: 2026-11-01 06:30:00 UTC → 01:30 CDT and 2026-11-01 07:30:00 UTC → 01:30 CST (both local date 2026-11-01, morning); 2027-03-14 08:30:00 UTC → 03:30 CDT (morning); 2026-10-02 04:59:59 UTC → 2026-10-01 23:59:59 CDT (local date 2026-10-01). | NFR-131, NFR-132 |
| FEAT-043-FR-07 | The function shall be pure and keep raw and adjusted values in separate fields of the contract. | ANL-003; TRD 08 §8 |

## Inputs

- `Sequence[EpochedRecord]` (raw features, `timestamp_utc` tz-aware UTC).
- `PipelineConfig` (`facility_tz` "America/Chicago", `morning_cutoff_hour` 12, `morning_offsets` 19 keys).

## Outputs

- `list[AdjustedRecord]` with `local_datetime`, `local_date`, `is_morning`, `adjusted` (19 keys) and the other contract fields.

## Data Flow

1. `run_pipeline` step 7 (FEAT-052) calls `adjust(epoched, config)`; the same zoneinfo helper also fills `EpochedRecord.local_date` used by the ledger.
2. For each non-duplicate record: convert, classify, subtract offsets when morning.
3. Output feeds baselines and scores (FEAT-045, FEAT-046); the runner stores `local_date`, `local_time`, `is_morning`, `adjusted_features` in `processed_sessions` and `is_morning` in `scores`.

## Dependencies

- FEAT-040 (Analytics contracts and PipelineConfig): `EpochedRecord`, `AdjustedRecord`, `PipelineConfig` with `facility_tz`, `morning_cutoff_hour`, `morning_offsets`.
- Downstream: FEAT-044 (local dates for ordering context), FEAT-045, FEAT-049 (local date per record).

## Database Impact

None directly. The runner writes `processed_sessions.local_date`, `local_time`, `is_morning`, `adjusted_features` and `scores.is_morning` (FEAT-053); TRD 20 `processed_sessions_local_date_ck` bounds `local_date` within one day of the UTC date.

## API Impact

None directly; `is_morning`, `local_date` and adjusted values are read by FEAT-028 and FEAT-034.

## Frontend Impact

None.

## Analytics Impact

- Algorithm: IANA time-zone conversion (zoneinfo, DST-aware), morning classification, per-feature additive offset adjustment.
- Offsets (configured): loudness_dbfs −1.50, total_phrase_duration_s +0.10, speech_rate_syl_per_s −0.12, articulation_rate_syl_per_s −0.10, pause_fraction +0.010, voiced_fraction −0.020, all others 0.
- Stage 5 of ANL-006 (`context_adjustment`, LOG-063).

## Security Requirements

None specific (pure function). The backend image must include `tzdata` so `America/Chicago` resolves (TRD 07 §6).

## Error Handling

- An unresolvable `facility_tz` is rejected earlier by `PipelineConfig.from_mapping` (`ConfigError`, FEAT-040).
- A naive `timestamp_utc` is a contract violation (`ContractError`, ANL-018).

## Logging Requirements

None in `analytics/` (LOG-006).

## Testing Requirements

- Unit (`tests/unit/analytics/test_morning_offset.py`, marker `unit`): MO-01..MO-07; NFR-131 and NFR-132 vectors; adjusted equals raw for afternoon sessions and for the 12 non-composite features; R06-20261004-01 worked example (TRD 08 §4.5).
- Validation (FEAT-059): VC-R06 (10 morning sessions, 4 scored with `is_morning` true), VC-G07 (19 offsets equal Exp_morning_offset).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-043-AC-01 | `2026-10-01 16:59:59` UTC is local 11:59:59 CDT and morning; `2026-10-01 17:00:00` UTC is 12:00:00 and not morning. | MO-01, MO-02 |
| FEAT-043-AC-02 | `2026-11-01 17:59:59` UTC is 11:59:59 CST and morning; `2026-11-01 18:00:00` UTC is not morning. | MO-03, MO-04, AGT-040 |
| FEAT-043-AC-03 | The NFR-131 and NFR-132 vectors give exactly the stated local times, dates and morning flags. | NFR-131, NFR-132 |
| FEAT-043-AC-04 | R06 day 1 raw loudness −25.42, phrase 4.01, rate 4.14, artic 4.52, pauses 2, pause_frac 0.126, voiced 0.595 adjusts to −23.92, 3.91, 4.26, 4.62, 2, 0.116, 0.615 (±1e-9). | MO-05, BSC-022 |
| FEAT-043-AC-05 | An afternoon session has adjusted == raw for all 19 features, and the 12 stored-not-scored features of a morning session are unchanged. | MO-06, MO-07 |
| FEAT-043-AC-06 | On SRC-05, exactly 10 R06 sessions (days 1, 4, …, 28) are morning and the scored ones are R06-20261019-01, -22, -25, -28 with `is_morning` true. | VC-R06, TRD 08 §4.5 |

## Definition of Done

- Module implemented with the binding signature; MO-01..MO-07 pass (TST-020); test file exists (TST-011).
- VC-R06 and VC-G07 pass in the validation suite (FEAT-059).

## Implementation Notes

- Parse is done by the backend (`datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)`); the engine receives aware datetimes and converts with `astimezone(ZoneInfo(config.facility_tz))` (TRD 07 §8).
- A variant using the UTC hour classifies none of R06's sessions as morning and fails 31 workbook rows (TRD 08 §4.5) — add a regression test that would catch it.
- Subtract offsets in float64 without rounding (AGT-054).
- Use one helper for local conversion in the whole package so the day ledger and windows never re-implement it.
