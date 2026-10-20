# FEAT-051 Analytics page aggregates (stage 12) wired into GET /api/v1/analytics

| Field | Value |
|---|---|
| Epic | Analytics Engine |
| Build phase | Phase 6 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-050, FEAT-035 |
| Status | Not Started |

## Purpose

Implement stage 12 of the analytics engine, `analytics/aggregates.py::build_analytics_summary`, which turns one pipeline result into the counts shown on the Analytics page (SRC-19): four KPIs, the daily stacked series, the loss funnel and the usable share per resident. Then map that `AnalyticsSummary` in `backend/services/analytics_summary.py` onto the `kpis`, `daily_series`, `funnel` and `by_resident` blocks of `GET /api/v1/analytics` (TRD 19 E-18), which FEAT-035 delivered in Phase 5 without these four blocks (BACKLOG.md §12, first question). The study team needs these numbers to equal the pipeline answer key exactly ("numbers match the pipeline answer key").

## Business Context

- BR-15 (reproduce the answer key): every aggregate is derived from the same `PipelineResult` as the status counts, so the page equals SRC-03 Exp_status_counts (ANL-062) and the TRD 14 Table 4.9-E values.
- BR-12 (staff see missed and set-aside check-ins): the daily series and funnel make missed, set-aside and quarantined check-ins visible as counts.
- BR-03, BR-04, BR-05, BR-06: duplicates are excluded, and set-aside reasons, quarantines and missed days are counted separately in the funnel.
- FRs covered (BACKLOG.md): FR-312, FR-313, FR-314, FR-315, FR-316, FR-317, FR-322.

## Referenced TRDs

- TRD 07 ANL-061, ANL-062, ANL-063, ANL-065, §4.13 (window, definitions, `AnalyticsSummary` shapes and SRC-05 expected values), §4.2 (`aggregates.py` signature), §4.4 (`AnalyticsSummary` helper type), §4.5 step 15, ANL-003 (purity), ANL-021/ANL-022 (ordering, float64).
- TRD 19 §4.3 E-18 `GET /api/v1/analytics` (`AnalyticsResponse`, `AnalyticsKpis`, `DailySeriesPoint`, `Funnel`, `ByResidentRow` field names are authoritative), OAS-028, OAS-024.
- TRD 05 API-006 (no re-implementation of analytics in the backend), API-069 (as-of of the latest succeeded run), API-087, §4.x endpoint map row "GET /analytics".
- TRD 02 FR-312..FR-317, FR-322 (and FR-323 as the reference-data check).
- TRD 11 UX-352..UX-355 (KPI note wording that the UI composes from the DTO), UX-363..UX-366 (funnel notes).
- TRD 13 AN-01..AN-05 (unit cases), TST-011, TST-140; TRD 14 TDV-074, TDV-075, Table 4.9-E, per-day list.
- TRD 03 NFR-128 (one window and one source for overview, alerts and analytics).

## Scope

- `analytics/aggregates.py::build_analytics_summary(sessions, ledger, epochs, alerts, data_alerts, residents, config, as_of) -> AnalyticsSummary` with the shapes of TRD 07 §4.13: `kpis.checkins_received`, `kpis.used_for_scoring`, `kpis.baselines_formed`, `kpis.alarms_raised`, `daily_series[]`, `funnel[]` (4 steps), `by_resident[]`, plus `period_start` and `period_end`.
- The integer half-up percentage helper `pct(n, d) = (200·n + d) // (2·d)`, null when `d = 0`.
- Call of `build_analytics_summary` as step 15 of `run_pipeline` (the orchestrator itself is FEAT-052; this feature delivers the stage and its unit tests).
- `backend/services/analytics_summary.py` mapping from `AnalyticsSummary` to the E-18 DTO blocks `kpis`, `daily_series`, `funnel`, `by_resident` (field names of TRD 19), including `alarms_raised.not_reviewed_count` computed from persisted alert status at response time (ANL-065).
- Unit tests `tests/unit/analytics/test_aggregates.py` (AN-01..AN-05) and the extension of `tests/integration/api/test_analytics.py` for the four blocks.

## Out of Scope

- The endpoint itself, authentication, `meta`, `period`, `status_totals`, `status_counts`, `resident_outcomes`, `pipeline_run`, `alarm_timing` and `review_outcomes` (FEAT-035, Phase 5).
- Data-alert rules (FEAT-050); the `silent_device_codes` of a day only read the `device_silent` data alerts that FEAT-050 produces.
- The Analytics page UI and every wording string (FEAT-072); the KPI `note` text of TRD 07 §4.13 is rendered by the frontend per TRD 11 UX-354/UX-355.
- Persisting the summary in a table (TRD 20 defines none; see Implementation Notes).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-051-FR-01 | `build_analytics_summary` shall be a pure function in `analytics/aggregates.py` with the binding signature of TRD 07 §4.2, returning a frozen `AnalyticsSummary` (period_start, period_end, kpis, daily_series, funnel, by_resident). | ANL-061, ANL-003, ANL-010 |
| FEAT-051-FR-02 | The period shall be the 30 facility-local days ending on the local date of `as_of`, never starting before a resident's `enrolled_on`; with SRC-05 and as-of 2026-10-30 15:00 America/Chicago it is 2026-10-01..2026-10-30. | TRD 07 §4.13; FR-312; API-069 |
| FEAT-051-FR-03 | "Received" shall count non-duplicate records of any status (including late arrivals) whose local date is in the period; "expected" shall be the sum over active residents of the days they were enrolled in the period. | TRD 07 §4.13; FR-313 |
| FEAT-051-FR-04 | `kpis.checkins_received` = `{value: received, expected, percent: pct(received, expected)}` and `kpis.used_for_scoring` = `{value: usable, expected, percent}` where usable counts status `usable` including baseline sessions. | TRD 07 §4.13; FR-313, FR-314 |
| FEAT-051-FR-05 | Percentages shall use integer arithmetic `pct(n, d) = (200·n + d) // (2·d)` and be null when `d = 0`; no float rounding is used. | ANL-063; FR-314 |
| FEAT-051-FR-06 | `kpis.baselines_formed` shall give the number of active residents whose current epoch has a formed baseline, the number of active residents, the codes of residents still forming and, per resident, restarts = current epoch number − 1 where > 0. | TRD 07 §4.13; FR-313 |
| FEAT-051-FR-07 | `kpis.alarms_raised` shall count alerts that are not superseded and whose `local_date` is in the period and list their resident codes; the not-reviewed count shall be filled by the backend from persisted alert status (`open` = not reviewed) at response time, not by the engine. | TRD 07 §4.13; ANL-065; FR-313 |
| FEAT-051-FR-08 | `daily_series` shall have one item per local day of the period with `local_date`, `used`, `set_aside`, `quarantined`, `missed` (= missing_resident + missing_device_gap ledger rows) and `silent_device_codes` (devices with a `device_silent` data alert covering that day); duplicates are excluded. | TRD 07 §4.13; FR-315 |
| FEAT-051-FR-09 | `funnel` shall carry the four steps expected, received, passed_quality (= received − set_aside, counting each set-aside reason occurrence and the number of sessions with more than one reason) and used (= passed_quality − quarantined), plus the missed and duplicate-copy counts. | TRD 07 §4.13; FR-316 |
| FEAT-051-FR-10 | `by_resident` shall give per active resident `days`, `used_days`, `set_aside_days`, `quarantined_days`, `missed_days` and `used_percent = pct(days with ≥ 1 usable record, days enrolled in period)`, where a day counts once in the first of used, set aside, quarantined that has a record; rows sorted by `used_percent` ascending then `resident_code` (natural order). | TRD 07 §4.13; FR-317; UX-369 |
| FEAT-051-FR-11 | All aggregate counts shall be derived from the sessions, ledger, epochs and alerts of the same pipeline result, so they equal the pipeline status counts; no separate SQL aggregation shall compute them. | ANL-062; NFR-128; API-006 |
| FEAT-051-FR-12 | `backend/services/analytics_summary.py` shall map the summary to the E-18 DTO: `kpis.checkins_received {count, expected, percent}`, `kpis.used_for_scoring {count, expected, percent}`, `kpis.baselines_formed {formed, residents, forming_resident_codes, restarts[{resident_code, restart_count}]}`, `kpis.alarms_raised {count, resident_codes, not_reviewed_count}`, `daily_series[]` (`DailySeriesPoint`), `funnel {expected, residents, days, received, missed, duplicates_removed, passed_quality, set_aside, set_aside_reasons {quality_flag_poor, noise_above_limit, speech_too_short}, set_aside_multi_reason, quarantined, used}` and `by_resident[]` (`ByResidentRow`); TRD 19 names win over the internal names. | TRD 07 §4.13 (DTO note); TRD 19 E-18; API-087; FR-322 |
| FEAT-051-FR-13 | The response blocks shall use the `as_of` of the latest succeeded pipeline run, the same window as `GET /api/v1/residents`. | API-069; NFR-128 |

## Inputs

- `PipelineResult` parts produced by stages 1–11: `sessions` (`AdjustedRecord`, every input record incl. duplicates), `ledger` (`LedgerDay`), `epochs` (`EpochSummary`), `alerts` (`AlertEvent`), `data_alerts` (`DataAlert`, from FEAT-050), `residents` (`ResidentInfo`), `PipelineConfig` (`facility_tz`, `baseline_n`), `as_of` (timezone-aware).
- At response time: persisted `alerts.status` for `not_reviewed_count` (ANL-065) and the latest succeeded `pipeline_runs.as_of` (API-069).

## Outputs

- `AnalyticsSummary` returned inside `PipelineResult.analytics`.
- E-18 blocks `kpis`, `daily_series`, `funnel`, `by_resident`. SRC-05 values (TRD 07 §4.13, TRD 14 Table 4.9-E): received 281 of 300 = 94; used 267 of 300 = 89; baselines formed 9 of 10, forming ["R08"], restarts R07 = 1; alarms 2 (R09, R10), not reviewed 2; Oct 12 = used 8, missed 2, silent ["D02"]; Σ of all daily segments 300; funnel 300 → 281 (19 missed, 2 duplicates) → 269 (12 set aside: quality flag 5, noise 5, too short 3, 1 multi-reason) → 267 (2 quarantined); by_resident R08 43, R03 73, R02 80, R05 93, then R01, R04, R06, R07, R09, R10 at 100.

## Data Flow

`run_pipeline` step 14 yields data alerts → step 15 calls `build_analytics_summary(adjusted, ledger, epochs, alerts, data_alerts, residents, config, as_of)` → `AnalyticsSummary` is part of `PipelineResult`. On `GET /api/v1/analytics`, `analytics_summary.py` obtains the summary for the latest succeeded run (see Implementation Notes), adds `not_reviewed_count` from `alerts.status`, maps the internal shapes onto the TRD 19 DTO and returns it alongside the FEAT-035 blocks.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-050, FEAT-035

- FEAT-050 supplies the `DataAlert` list (`device_silent` days drive `silent_device_codes`).
- FEAT-035 supplies `GET /api/v1/analytics`, its router, auth, `meta`, `period` and the other response blocks into which this feature adds four blocks.
- FEAT-052 (orchestrator) calls this stage as step 15; FEAT-060 and FEAT-072 consume the result.

## Database Impact

- Tables created or modified: none.
- Tables read at response time (TRD 05 endpoint map, TRD 20): `alerts` (`status`, `local_date`, `closed_reason`), `pipeline_runs` (`as_of`, `status`), and the derived tables the summary is built from (`processed_sessions`, `day_ledger`, `epochs`, `data_alerts`) when the summary is rebuilt from persisted rows.
- No new table: TRD 20 §4.6 defines no table for `AnalyticsSummary`.

## API Impact

- Endpoint extended: `GET /api/v1/analytics` (E-18, roles admin and researcher). Adds the blocks `kpis`, `daily_series`, `funnel`, `by_resident` with the exact property names of TRD 19 §4.5 schemas; the OpenAPI contract is unchanged if FEAT-035 already declared the schemas, otherwise `docs/api_reference/openapi.json` is regenerated with `python -m backend.cli export-openapi` (OAS-002, OAS-005).
- No endpoint consumed.

## Frontend Impact

None in this feature. The blocks are rendered by FEAT-072 (`KpiTiles`, `DailyCheckinsChart`, `LossFunnel`, `UsableByResidentChart`, TRD 04 §4.8).

## Analytics Impact

- Module: `analytics/aggregates.py` (TRD 07 §4.2), stage 12.
- Calculations: window selection by facility-local date; counts by status from `AdjustedRecord.status` and `LedgerDay.status`; reason-occurrence counts from `reasons` (fixed order quality flag, noise, speech duration); restarts from `EpochSummary.epoch_number`; integer half-up `pct`.
- No floating-point result; no rounding other than `pct`.

## Security Requirements

- `GET /api/v1/analytics` stays restricted to admin and researcher (clinician 403, FR-310, TRD 19 E-18).
- The engine and this stage never read `evaluation_ground_truth`; only `analytics_summary.py` may read it, for the separate `alarm_timing` block owned by FEAT-035 (ANL-064, API-136).
- Responses carry counts and study IDs only; no names, notes or audio (OAS-016).

## Error Handling

- Empty input, a resident with no records, or `expected = 0` shall return a valid summary with null percentages, never raise (ANL-019, ANL-063).
- A contract violation in the inputs raises `ContractError` from the orchestrator (ANL-018); the stage defines no other exception (ANL-051).
- When no succeeded pipeline run exists, the endpoint behaviour of FEAT-035 applies (empty state rendered by FEAT-072 "No pipeline run yet").

## Logging Requirements

- `analytics/` does not log (ANL-053). The backend request log of TRD 17 covers the endpoint call; no feature values appear in logs (ANL-054).
- No audit record (read endpoint).

## Testing Requirements

- Unit (`tests/unit/analytics/test_aggregates.py`, marker `unit`, TST-011): AN-01 (94% / 89%), AN-02 (1 of 8 → 13%), AN-03 (funnel), AN-04 (by-resident order), AN-05 (baselines formed and restarts); plus `d = 0` → null.
- Integration (`tests/integration/api/test_analytics.py`, marker `integration`): on DS-07 the four blocks equal TRD 14 Table 4.9-E and the per-day list (TDV-074, OAS-028); every response validated against the OpenAPI schema (OAS-006, TST-061).
- Validation (`tests/validation/`, FEAT-059/FEAT-060): every Table 4.9-E figure recomputed from DS-02 and compared (TDV-075).
- Coverage: `analytics/` ≥ 95 % (TST-140).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-051-AC-01 | `pytest tests/unit/analytics/test_aggregates.py -q` passes cases AN-01..AN-05; AN-02 returns 13 for 1 of 8. | TRD 13 AN-01..AN-05 |
| FEAT-051-AC-02 | On SRC-05 the `AnalyticsSummary` equals every expected value of the TRD 07 §4.13 table (281/300/94, 267/300/89, 9 of 10 with R08 forming and R07 restarted once, 2 alarms R09 R10, funnel 300/281/269/267 with 5/5/3 and 1 multi-reason, by-resident order and percentages). | AC-ANL-10 |
| FEAT-051-AC-03 | The 30 `daily_series` rows equal the TRD 14 §4.9.2 per-day list exactly, and Oct 12 has `silent_device_codes` ["D02"]. | TDV-074 |
| FEAT-051-AC-04 | With DS-07 loaded, `GET /api/v1/analytics` as researcher returns `kpis`, `funnel`, `by_resident` equal to the E-18 example values and passes OpenAPI response validation. | OAS-028; API-087 |
| FEAT-051-AC-05 | Sum over `daily_series` of used, set_aside, quarantined, missed equals 267, 12, 2, 19 respectively, matching `status_totals` usable, set_aside, quarantined and missing_resident + missing_device_gap. | ANL-062; OAS-024 |
| FEAT-051-AC-06 | After a review is saved on R09, `kpis.alarms_raised.not_reviewed_count` is 1 while `count` stays 2. | ANL-065; TDV-076 |
| FEAT-051-AC-07 | A summary computed with zero residents returns null percentages and no exception. | ANL-063; ANL-019 |

## Definition of Done

- All FEAT-051 acceptance criteria pass; `pytest tests/unit -q` and `pytest tests/integration -q -k analytics` green.
- `analytics/` line coverage ≥ 95 % (TST-140); import-linter boundary check passes (ANL-002).
- OpenAPI contract unchanged or regenerated and committed (OAS-005).
- Phase 6 batch report lists the requirement IDs above (AGT-022).

## Implementation Notes

- The TRDs do not say how `GET /api/v1/analytics` obtains the `AnalyticsSummary` at request time: TRD 20 has no table for it, while TRD 05's endpoint map lists the derived tables as read by `analytics_summary.build`. Interim approach consistent with API-006 and ANL-062: rebuild the stage inputs (`AdjustedRecord`, `LedgerDay`, `EpochSummary`, `AlertEvent`, `DataAlert`) from the persisted rows of the latest succeeded run and call the pure `analytics.aggregates.build_analytics_summary` (no SQL formulas). This gap should be recorded as a new OQ in TRD 24 (AGT-009).
- The internal `funnel` is a 4-item list and `restarts` a dict (TRD 07 §4.13), while the DTO uses an object and a list (TRD 19 E-18); the mapping lives only in `analytics_summary.py`.
- The internal `note` strings of TRD 07 §4.13 are not DTO fields; the frontend composes notes from the DTO counts (TRD 11 UX-354/UX-355).
- Use `local_date` from `AdjustedRecord`/`LedgerDay` (FACILITY_TZ), never the UTC date (TRD 07 §8).
- Sort `by_resident` with a natural-sort key on `resident_code` (AGT-052).
