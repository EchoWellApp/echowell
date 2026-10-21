# FEAT-034 Scores and baselines read-outs with CSV export (GET /scores, GET /analytics/baselines)

| Field | Value |
|---|---|
| Epic | Backend API |
| Build phase | Phase 5 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-021, FEAT-014 |
| Status | Not Started |

## Purpose

Expose the scored sessions (per-feature z, composite, running tally and alarm state) that draw the "Running change tally" chart and its mini version on the Alert review page, and the frozen baselines that researchers compare with the answer key, both in the SRC-03 Exp_scores / Exp_baselines shape. Researchers and admins can download either as CSV for offline analysis (mixed-effects models, SRC-14 B.2) with study IDs only.

## Business Context

- BR-10 (daily deviation score) and BR-11 (tally and alarm): `GET /scores` serves the chart data including baseline periods.
- BR-13 (resident detail chart): one bar per scored session, baseline slot, earlier epochs on request.
- BR-09 and BR-15 (frozen baseline; reproduce the answer key): `GET /analytics/baselines` returns 180 rows for the test data equal to Exp_baselines.
- BR-16: CSV export limited to researcher and admin, audited, study IDs only, no note text.
- FRs covered (BACKLOG.md): FR-241, FR-242, FR-244, FR-245.

## Referenced TRDs

- TRD 05 API-079 (scores), API-088 (baselines), API-129 (CSV), API-057, API-069, API-093, API-100, API-121.
- TRD 19 §4.3 E-12, E-19; schemas `ScoresResponse`, `ScoreRow`, `ZValues`, `BaselinePeriod`, `BaselineRow`, `BaselineRowList`, `BaselineFeatureKey`; OAS-018 (`text/csv` alternative), OAS-022, OAS-023, OAS-011 (full precision).
- TRD 09 CUS-024 (scores contract for the chart).
- TRD 07 ANL-042 (composite and alarm-state mapping to workbook labels, used by tests).
- TRD 13 TST-079; TRD 05 AC-API-04, AC-API-16 (CSV part).
- TRD 12 §4.6 (scores JSON all roles, CSV researcher/admin; baselines researcher/admin), §4.12 (`export.csv`), SEC-045.
- TRD 03 NFR-050 (export roles and content).
- TRD 25 AGT-060 (researcher exports through the API with the app role); TRD 24 D-33.

## Scope

- Router `backend/api/scores.py` `GET /api/v1/scores` (`scoring.list_scores` / `export_service`) and `backend/api/analytics.py` `GET /api/v1/analytics/baselines` (`analytics_service.baselines`).
- Filters, ordering, pagination, `cusum_k`, `baseline_periods`.
- Content negotiation on `Accept: text/csv` with streamed CSV, filename, row limit, role check and `export.csv` audit.

## Out of Scope

- `GET /api/v1/analytics` (FEAT-035, FEAT-051).
- Computing z, composite, tally or baselines (Phase 6 engine features FEAT-045..FEAT-047); this feature reads stored rows.
- The chart, CSV download buttons and table alternative (FEAT-067, FEAT-072).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-034-FR-01 | `GET /api/v1/scores` shall accept `resident_code`, `epoch` (integer ≥ 1, only together with `resident_code`), `from`, `to` (local dates, `from` ≤ `to`) and pagination; invalid combinations return 422 `INVALID_QUERY_PARAMETER`, an unknown `resident_code` 404 `RESIDENT_NOT_FOUND`. | API-079, API-093; TRD 19 E-12; FR-242 |
| FEAT-034-FR-02 | Items shall be `ScoreRow` (`session_id`, `resident_code`, `epoch_number`, `local_date`, `is_morning`, `z` with the 7 unsigned `z_<feature>` values, `composite_raw`, `composite_z`, `cusum_tally`, `alarm_state`) ordered by `resident_code`, `local_date`, in full float64 precision. | API-079, CUS-024, OAS-011; FR-242 |
| FEAT-034-FR-03 | The JSON response shall add `cusum_k` (active profile) and `baseline_periods`: one `BaselinePeriod` per resident-epoch present in the result with `first_local_date`, `frozen_after_local_date`, `frozen_after_session_id` and `n_sessions`; `cusum_h` is in `meta`. | API-079, CUS-024; TRD 19 `ScoresResponse` |
| FEAT-034-FR-04 | JSON `GET /scores` shall be available to every user role. | TRD 12 §4.6 |
| FEAT-034-FR-05 | `GET /api/v1/analytics/baselines` (researcher, admin) shall accept optional `resident_code` and `epoch` (requires `resident_code`) with pagination (limit max 500) and return `BaselineRow` items (resident_code, epoch_number, device_code, feature_key, n_sessions, first_session_id, frozen_after_session_id, median, mad, robust_spread, floor_applied) ordered by resident_code, epoch, then contract §6 feature order with `composite` last. | API-088; TRD 19 E-19; FR-241 |
| FEAT-034-FR-06 | Either endpoint requested with `Accept: text/csv` by a researcher or admin shall return `text/csv; charset=utf-8` with `Content-Disposition: attachment; filename="echowell_<scores\|baselines>_<as-of local date>.csv"`, one header row of the DTO field names with `z` flattened to `z_<feature>` columns, and all rows matching the filters (pagination ignored). | API-129, OAS-018, TST-079; FR-244 |
| FEAT-034-FR-07 | A CSV request matching more than 100,000 rows shall return 413 `PAYLOAD_TOO_LARGE`; a clinician requesting CSV shall receive 403 `FORBIDDEN`. | API-129; TRD 12 §4.6 |
| FEAT-034-FR-08 | Each CSV export shall write one `audit_logs` row `export.csv` (entity route / route template; details `{filters, row_count}`). | API-129; TRD 12 §4.12 |
| FEAT-034-FR-09 | Exports and JSON responses shall contain study IDs only (`resident_code`, `session_id`, `device_code`) and no staff-note text or other free text. | FR-245, NFR-050, DME-004 |

## Inputs

- Bearer JWT; query parameters above; header `Accept` (`application/json` default, `text/csv`).
- Tables `scores`, `processed_sessions`, `epochs`, `baselines`, `devices`, `residents`, `pipeline_runs`, `config_parameters` (`cusum_k`).

## Outputs

- 200 `ScoresResponse` or CSV; 200 `BaselineRowList` or CSV; Problems 403, 404, 413, 422; `audit_logs` row per CSV export.

## Data Flow

1. Auth: scores JSON any role; scores CSV and baselines (both forms) researcher/admin (`require_roles` evaluated after reading `Accept`).
2. Service builds the filtered query (repository layer), orders it, and either pages it (JSON) or counts it and streams all rows (CSV, refusing above 100,000).
3. For scores JSON, a second query loads the composite baseline rows of the resident-epochs in the page to build `baseline_periods`; local dates come from `processed_sessions.local_date` of the first and frozen-after sessions.
4. CSV: `csv.writer` over a `StreamingResponse`; `audit_service.record("export.csv", ...)` committed with the request.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-021, FEAT-014

- FEAT-021 (Role-based authorization matrix): per-representation role rules.
- FEAT-014 (Read-model derivations): as-of local date for the filename and date filters.
- Transitively FEAT-015 (audit writer) via FEAT-021's dependency chain for `export.csv`, and FEAT-011 (tables).

Features that build directly on this one (BACKLOG.md §4): FEAT-035, FEAT-067.

## Database Impact

- Tables read: `scores` (`z`, `composite_raw`, `composite_z`, `cusum_tally`, `alarm_state`, `local_date`, `is_morning`, `epoch_id`, `processed_session_id`), `processed_sessions` (`session_id`, `local_date`), `epochs` (`epoch_number`, `device_id`), `baselines` (all value columns), `devices` (`device_code`), `residents` (`resident_code`).
- Tables written: `audit_logs` (one row per CSV export).
- Tables created or altered: none.

## API Impact

- Exposed: `GET /api/v1/scores` (E-12; JSON or CSV), `GET /api/v1/analytics/baselines` (E-19; JSON or CSV).
- Both operations declare `application/json` and `text/csv` 200 responses (OAS-018).

## Frontend Impact

None in this feature. Consumers: `CusumChart`, `CusumTable`, `MiniTallyChart` via `getScores({residentCode, epoch})`; Analytics "Downloads" via `downloadScoresCsv` and `downloadBaselinesCsv` (TRD 04 §4.6.2), delivered by FEAT-067, FEAT-069 and FEAT-072.

## Analytics Impact

None computed here. Values are the stored outputs of stages 6–8 (baselines, z, composite, CUSUM); `z` is returned unsigned exactly as stored (TRD 19 §8), never re-signed.

## Security Requirements

- Scores JSON: admin, clinician, researcher; scores CSV: admin, researcher (clinician 403); baselines JSON and CSV: admin, researcher (clinician 403); API key 401 (TRD 12 §4.6, TRD 13 Table 4.13-A).
- Researchers have read-only access; export uses the app role through the API, not the migrator or readonly URL (AGT-060).
- No free text or PII in exports (FR-245, SEC-120).

## Error Handling

- `epoch` without `resident_code`, `from` > `to`, bad dates, limit > 500 → 422 `INVALID_QUERY_PARAMETER`.
- Unknown `resident_code` → 404 `RESIDENT_NOT_FOUND` (scores).
- CSV > 100,000 rows → 413 `PAYLOAD_TOO_LARGE`; clinician CSV → 403 `FORBIDDEN` (and `access.denied` audit, SEC-108).
- Empty result → 200 with empty `items`/`baseline_periods` or a CSV with only the header row.

## Logging Requirements

- Access log per request (LOG-010) without query values beyond dates (API-107).
- Audit `export.csv` with filters and row count; no feature values in logs.

## Testing Requirements

- Integration (`tests/integration/api/test_scores.py`, `tests/integration/api/test_analytics.py` baseline cases, marker `integration`) with fixture rows: ordering; `epoch` without `resident_code` → 422; unknown resident → 404; `baseline_periods` per resident-epoch; CSV headers equal JSON field names with flattened `z_*` and rows equal JSON items (TST-079); clinician CSV → 403; researcher CSV → 200 with audit row; > 100,000 rows → 413 (unit test of the export service with a repository double that reports a count of 100,001, so no large fixture is needed).
- Contract: TST-061 for JSON; OAS-018 representation declared.
- DS-07 values (validation suite FEAT-058/FEAT-059 and OAS-022/OAS-023): `GET /scores?resident_code=R09` 14 rows, R09-20261021-01 `cusum_tally` 5.431965 `rings`, R09-20261030-01 26.830256 `on`; baselines 180 rows equal Exp_baselines within 1e-6 (composite ↔ "COMPOSITE (raw signed mean of 7 z)", ANL-042).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-034-AC-01 | `GET /api/v1/scores?epoch=1` (no `resident_code`) returns 422 `INVALID_QUERY_PARAMETER`; `GET /scores?resident_code=R11` returns 404 `RESIDENT_NOT_FOUND`. Verified by: Integration (`tests/integration/api/test_scores.py`). | API-079 |
| FEAT-034-AC-02 | With DS-07 loaded, `GET /scores?resident_code=R09` returns `total` 14, `cusum_k` 0.5, one `baseline_periods` entry (epoch 1, 2026-10-01..2026-10-16, frozen after R09-20261016-01, n 16), row R09-20261021-01 with `cusum_tally` 5.431965 and `alarm_state` `rings`, and row R09-20261030-01 with 26.830256 and `on` (±1e-6). Verified by: DS-07 values (DS-07 values (validation suite FEAT-058/FEAT-059 and OAS-022/OAS-023): `GET /scores?resident_code=R09` 14 rows, R09-20261021-01 `cusum_tally` 5.431965 `rings`, R09-20261030-01 26.830256 `on`). | AC-API-04, OAS-022 |
| FEAT-034-AC-03 | With DS-07 loaded, a researcher `GET /scores` with `Accept: text/csv` receives `text/csv; charset=utf-8`, filename `echowell_scores_2026-10-30.csv`, a header row equal to the `ScoreRow` field names with `z` flattened to the 7 `z_*` columns, and 98 data rows; a clinician receives 403. | AC-API-16, API-129, TST-079 |
| FEAT-034-AC-04 | With DS-07 loaded, `GET /analytics/baselines?limit=500` as researcher returns `total` 180 and values equal to SRC-03 Exp_baselines within 1e-6; R09 loudness_dbfs has median -22.405, mad 1.45, robust_spread 2.14977, `floor_applied` false. Verified by: DS-07 values (DS-07 values (validation suite FEAT-058/FEAT-059 and OAS-022/OAS-023): `GET /scores?resident_code=R09` 14 rows, R09-20261021-01 `cusum_tally` 5.431965 `rings`, R09-20261030-01 26.830256 `on`). | OAS-023, API-088 |
| FEAT-034-AC-05 | The baselines CSV header equals the `BaselineRow` field names and its rows equal the JSON items; a clinician receives 403 for both JSON and CSV. | TST-079, TRD 12 §4.6 |
| FEAT-034-AC-06 | Each CSV export writes exactly one `audit_logs` row `export.csv` with `row_count` equal to the number of data rows. Verified by: Integration (`tests/integration/api/test_scores.py`; TST-079). | API-129, AC-SEC-09 |
| FEAT-034-AC-07 | Within one resident-epoch, baseline rows are ordered loudness_dbfs … mfcc4 and then `composite`. Verified by: DS-07 values (baselines 180 rows equal Exp_baselines within 1e-6 (composite ↔ "COMPOSITE (raw signed mean of 7 z)", ANL-042)). | API-088 |

## Definition of Done

- All FEAT-034 acceptance criteria pass.
- Both endpoints implemented with JSON and CSV representations declared in OpenAPI.
- Integration tests pass; DS-07 criteria pass in the validation and FEAT-060 suites.
- Requirement markers (TST-013); coverage ≥ 85 %; OpenAPI drift check passes.
- The batch report lists the implemented requirement IDs (AGT-022); the TRD differences noted under Implementation Notes were resolved in PR #2 and need no report.

## Implementation Notes

- Choose the representation from `request.headers["accept"]` and declare both media types via `responses=` (TRD 19 §8); stream with `csv.writer` and `StreamingResponse`.
- Count first (`SELECT count(*)`) and refuse above 100,000 before streaming, so a 413 never follows a partial body.
- Write floats with `repr`-level precision (Python `str(float)`), no fixed decimals, so CSV rows equal JSON items (TST-079).
- CSV columns use the TRD 19 DTO field names (TRD 05 API-129, TRD 13 TST-079); TRD 02 FR-244 was aligned in the PR #2 consistency fixes.
- TRD 19 `BaselineRow.robust_spread` now has `minimum: 0` (aligned with TRD 08 BSC-035 and TRD 20 `baselines_spread_ck` in the PR #2 consistency fixes), so a legitimate zero-spread row of a non-composite feature passes response validation (OAS-006); the test data has no such row.
- Natural sort of `resident_code` is not required by API-079/API-088; R01..R10 sort identically either way. Use the same natural key as FEAT-027 for consistency.
