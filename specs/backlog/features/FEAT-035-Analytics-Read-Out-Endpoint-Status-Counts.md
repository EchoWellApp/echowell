# FEAT-035 Analytics read-out endpoint (GET /api/v1/analytics): status counts, outcomes, run info, alarm timing and review outcomes

| Field | Value |
|---|---|
| Epic | Backend API |
| Build phase | Phase 5 (TRD 25) |
| Priority | P0 |
| Complexity | High |
| MVP status | Required |
| Dependencies | FEAT-034, FEAT-008 |
| Status | Not Started |

## Purpose

Deliver `GET /api/v1/analytics` for researchers and admins with everything except the four page aggregates: `meta`, the 30-day `period`, per-resident status counts and outcomes in the shape of SRC-03 Exp_status_counts / Exp_resident_outcomes, the status totals, the latest pipeline run, and exactly one of the "Alarm timing check" (test profile, comparing alarms with the known planted change dates) or the review outcomes (production). The alarm timing check is the only place the answer-key ground truth is read, through a separate read-only database connection, after the pipeline has run, so the answer key can never influence the analytics.

## Business Context

- BR-15 (reproduce the answer key; researchers see that numbers match): status counts, outcomes, totals and run info.
- BR-11 / BR-15: "Alarm timing check · test data only" shows detection delays (R09 0 days, R10 7 days).
- BR-13 / BR-15: in production the panel shows alarms raised, reviewed and review outcomes instead.
- BR-16: analytics restricted to researcher and admin; ground truth isolated from the pipeline (SRC-02 "the answer key never touches the analytics").
- FRs covered (BACKLOG.md): FR-240, FR-243, FR-312, FR-318, FR-319, FR-322.

## Referenced TRDs

- TRD 05 API-087 (endpoint and test values), API-136 (read-only engine for alarm timing only), API-057, API-069, API-125 (engine factory), §4.12 row GET /analytics.
- TRD 19 §4.3 E-18; schemas `AnalyticsResponse`, `StatusTotals`, `StatusCountsRow`, `ResidentOutcome`, `PipelineRun`, `AlarmTimingRow`, `ReviewOutcomes`; OAS-024, OAS-028.
- TRD 09 CUS-047 (alarm timing rows), CUS-048 (ground truth isolation), CUS-049 (review outcomes), CUS-029 (analytics shows active settings).
- TRD 01 ARC-015 (connection strings per role), ARC-034 (`evaluation_ground_truth` read only by `analytics_summary.py`).
- TRD 12 SEC-116 (`DATABASE_READONLY_URL` only in test_v0_1, only in `analytics_summary.py`, no `SET ROLE`), §4.6 (researcher, admin).
- TRD 20 PGS-040 (app role has no privilege on `evaluation_ground_truth`; readonly login role).
- TRD 23 §4.7.3 (Exp_status_counts mapping), §4.7.4 (Exp_resident_outcomes mapping), DME-024.
- TRD 14 TDV-101..TDV-104; TRD 13 TST-068; TRD 05 AC-API-16 (analytics part); TRD 07 ANL-064.
- TRD 24 D-38 (ground truth use), D-46 (Analytics page roles); BACKLOG §12 Q-01 (aggregates delivered by FEAT-051).

## Scope

- Router `backend/api/analytics.py` handler `GET /api/v1/analytics` calling `backend/services/analytics_summary.py::build`.
- `meta`, `period` `{from, to, days}`, `status_totals`, `status_counts` (one row per resident), `resident_outcomes` (one row per resident-epoch with ≥ 1 usable session), `pipeline_run`.
- `alarm_timing` (profile test_v0_1) read through a second SQLAlchemy engine on `DATABASE_READONLY_URL`; `review_outcomes` (profile production) from `alert_reviews`.
- The full `AnalyticsResponse` DTO, with the `kpis`, `daily_series`, `funnel` and `by_resident` blocks filled by FEAT-051.
- Import-boundary test that only `analytics_summary.py` references the read-only engine and `evaluation_ground_truth`.

## Out of Scope

- `analytics/aggregates.py` and the four aggregate blocks (FEAT-051, Phase 6).
- Loading `evaluation_ground_truth` (`database/seeds/load_evaluation_ground_truth.py`, FEAT-057).
- `GET /analytics/baselines` (FEAT-034).
- The Analytics page (FEAT-072).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-035-FR-01 | `GET /api/v1/analytics` shall be available to roles researcher and admin only; clinicians receive 403 `FORBIDDEN`. | API-087, FR-243; TRD 12 §4.6; D-46 |
| FEAT-035-FR-02 | `period` shall be the 30 local days ending on the as-of local date of the latest succeeded run (`{from, to, days}`; test data 2026-10-01..2026-10-30, 30). | FR-312, API-069 |
| FEAT-035-FR-03 | `status_counts` shall have one `StatusCountsRow` per resident: `usable`, `set_aside`, `quarantined`, `duplicate` = counts of `processed_sessions` by status, and `missing_resident`, `missing_device_gap` = counts of `day_ledger` by status, over all days from enrolment to as-of; `status_totals` shall be the sums. | FR-240; TRD 23 §4.7.3; OAS-024 |
| FEAT-035-FR-04 | `resident_outcomes` shall have one `ResidentOutcome` per resident-epoch with at least one usable session: `epoch_number`, `device_code`, `usable_in_epoch`, `baseline_formed` (20 baseline rows exist), `baseline_frozen_after`, `scored_sessions` (null when no baseline), `first_alarm_session` (alert session id or null), `note` ("Too few usable sessions: baseline pending, nothing scored" when the baseline is not formed, else null). | FR-240; TRD 23 §4.7.4 |
| FEAT-035-FR-05 | `pipeline_run` shall be the `PipelineRun` DTO of the latest succeeded run (the run that defines `meta.as_of`), or null when none exists. | FR-240, API-069; TRD 19 `AnalyticsResponse` |
| FEAT-035-FR-06 | Exactly one of `alarm_timing` and `review_outcomes` shall be non-null: `alarm_timing` when `PIPELINE_PROFILE` is `test_v0_1`, `review_outcomes` when it is `production`. | API-087, FR-322; TRD 19 E-18 |
| FEAT-035-FR-07 | `alarm_timing` shall be built after the run by comparing persisted alerts with `evaluation_ground_truth` (resident_code, planted_change, true_onset_date): one `AlarmTimingRow` per resident with `planted_change`, `change_began` (true onset), `alarm_rang` (alert local date or null), `delay_days` (alarm local date − true onset date) and `result` ∈ {detected, missed, correct_no_alarm, false_alarm}. | CUS-047, FR-318; TRD 19 `AlarmTimingRow` |
| FEAT-035-FR-08 | `evaluation_ground_truth` shall be read only by `backend/services/analytics_summary.py`, only when `PIPELINE_PROFILE` is `test_v0_1`, through a second engine built by the `backend/core/db.py` factory from `DATABASE_READONLY_URL` (`pool_size=1`, read-only transactions), without `SET ROLE`; when the profile is `production` that engine shall not be created. | API-136, SEC-116, ARC-015, ARC-034, ANL-064, D-38 |
| FEAT-035-FR-09 | `review_outcomes` shall be `{alarms_raised, reviewed, by_outcome: {no_concern, known_cause, referred, data_problem}}` over alerts of the period, counting alerts with ≥ 1 review as reviewed and, per alert, its latest review's outcome. | CUS-049, FR-319, TDV-104 |
| FEAT-035-FR-10 | The response shall be a complete `AnalyticsResponse` including `meta` (with `baseline_n`, `cusum_h`, `pipeline_profile`) and the `kpis`, `daily_series`, `funnel`, `by_resident` blocks produced by FEAT-051's mapping. | API-087, FR-322, CUS-029; BACKLOG §12 Q-01 |

## Inputs

- Bearer JWT (researcher, admin).
- Env `PIPELINE_PROFILE`, `DATABASE_URL`, `DATABASE_READONLY_URL` (test_v0_1 only).
- Tables (app role): `processed_sessions`, `day_ledger`, `epochs`, `baselines`, `scores`, `alerts`, `alert_reviews`, `residents`, `devices`, `pipeline_runs`; (readonly role, test only): `evaluation_ground_truth`.

## Outputs

- 200 `AnalyticsResponse`; 403 for clinicians; 401 for API keys and anonymous.

## Data Flow

1. Auth: `require_roles("researcher","admin")`.
2. `analytics_summary.build` gets `meta` and the period from the latest succeeded run.
3. Grouped queries on the app engine produce status counts, outcomes and the run DTO.
4. Profile branch: test_v0_1 → open a read-only transaction on the readonly engine, read `evaluation_ground_truth`, join in Python with the alerts already loaded on the app engine, build `alarm_timing`; production → aggregate `alert_reviews` per alert (latest review) into `review_outcomes`.
5. The FEAT-051 mapper adds `kpis`, `daily_series`, `funnel`, `by_resident`; the router returns the DTO.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-034, FEAT-008

- FEAT-034 (Scores and baselines read-outs): `analytics.py` router module, the baseline/epoch read queries and the researcher/admin role pattern reused here (and transitively FEAT-021, FEAT-014).
- FEAT-008 (Database roles, extensions and Alembic): the `echowell_readonly` role and its login role with SELECT on `evaluation_ground_truth`, and no privilege for `echowell_app` (PGS-040).
- Downstream: FEAT-051 (adds the aggregate blocks), FEAT-060 (DS-07 analytics values), FEAT-072.

## Database Impact

- Tables read (app role): `processed_sessions` (`status`, `resident_id`), `day_ledger` (`status`, `resident_id`), `epochs`, `baselines` (row count per epoch, `frozen_after_session_id`), `scores` (count per epoch), `alerts` (`session_id`, `local_date`, `epoch_id`), `alert_reviews` (`alert_id`, `outcome`, `created_at`), `residents`, `devices`, `pipeline_runs`.
- Tables read (readonly role, test_v0_1 only): `evaluation_ground_truth` (`resident_code`, `planted_change`, `true_onset_date`, `source_file`).
- Tables written, created or altered: none.

## API Impact

- Exposed: `GET /api/v1/analytics` (E-18; 200 `AnalyticsResponse`; universal errors).

## Frontend Impact

None in this feature. Consumers: Analytics page `AlarmTimingTable`, `ReviewOutcomesTable` and the page header via `getAnalytics()` (TRD 04 §4.6.2), delivered by FEAT-072.

## Analytics Impact

No engine computation. Calculations performed in the backend read path: per-resident counts by status, outcome rows, delay in days (alarm local date − true onset date), and review outcome counts; all derived from persisted pipeline output after the run (ANL-062, ANL-064).

## Security Requirements

- Authentication: bearer JWT; researcher and admin 200, clinician 403, API key and anonymous 401 (TRD 13 Table 4.13-A).
- Least privilege: the app role cannot read `evaluation_ground_truth` (PGS-040); only `analytics_summary.py` opens `DATABASE_READONLY_URL`, which is set only where the profile is test_v0_1 (SEC-116).
- No `SET ROLE` anywhere in application code (SEC-116, PGS-040).
- Ground-truth columns appear only inside `alarm_timing` (DME-005).

## Error Handling

- Readonly engine unavailable or misconfigured under test_v0_1 → 503 `SERVICE_UNAVAILABLE` for this request (API-097 mapping); the pipeline is unaffected because it never uses that engine.
- `evaluation_ground_truth` empty under test_v0_1 → `alarm_timing` is an empty array (rows are built only from ground-truth rows, CUS-047); no 500.
- No succeeded run → `pipeline_run` null, `meta.as_of` null, empty arrays and zero totals.

## Logging Requirements

- Access log per request (LOG-010); no audit row (read endpoint); never log ground-truth values or connection URLs (LOG-020, LOG-024).

## Testing Requirements

- Integration (`tests/integration/api/test_analytics.py`, marker `integration`): role checks (researcher/admin 200, clinician 403); exactly one of `alarm_timing` / `review_outcomes` per profile (TDV-104 with an app instance configured for `production` against the test database without `PIPELINE_AS_OF`); `review_outcomes` counting latest review per alert; status counts and outcomes on fixture rows; schema validation (TST-061) and `meta` (TST-064).
- Security/static (`tests/integration/test_readonly_boundary.py` or `tests/unit/backend/test_import_boundary.py`): import-boundary test of API-136 — no module other than `backend/services/analytics_summary.py` references `DATABASE_READONLY_URL` or `evaluation_ground_truth` (TST-068 (a), TDV-101); no `SET ROLE` in application code.
- Grant test: as the app login role `SELECT * FROM evaluation_ground_truth` fails with 42501 (PGS-040, AC-ANL-14) — owned by FEAT-008/FEAT-012 and must stay green.
- DS-07 values (FEAT-060, OAS-024, OAS-028 for `alarm_timing`, AC-API-16): status totals 267/12/2/2/17/2; alarm timing R09 0 days, R10 7 days, others `correct_no_alarm`.
- TDV-102 (identical pipeline output with and without ground truth loaded) runs in the validation suite (FEAT-059).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-035-AC-01 | A clinician `GET /api/v1/analytics` returns 403 `FORBIDDEN`; researcher and admin return 200. | FR-243, API-087 |
| FEAT-035-AC-02 | With DS-07 loaded (profile test_v0_1), `status_totals` is usable 267, set_aside 12, quarantined 2, duplicate 2, missing_resident 17, missing_device_gap 2; `status_counts` has 10 rows (R02: usable 24, missing_resident 5, missing_device_gap 1); `resident_outcomes` has 11 rows (R07 epochs 1 and 2). | OAS-024, FR-240, TRD 23 §4.7.3, §4.7.4 |
| FEAT-035-AC-03 | With DS-07 and DS-10 loaded, `alarm_timing` contains R09 (Sudden step, change_began 2026-10-21, alarm_rang 2026-10-21, delay_days 0, result `detected`), R10 (Slow drift, 2026-10-17, 2026-10-24, 7, `detected`) and 8 rows with planted_change "None", alarm_rang null, result `correct_no_alarm`; `review_outcomes` is null. | CUS-047, OAS-028, AC-API-16 |
| FEAT-035-AC-04 | With `PIPELINE_PROFILE=production`, `alarm_timing` is null and `review_outcomes` is non-null with `by_outcome` keys no_concern, known_cause, referred, data_problem; no connection to `DATABASE_READONLY_URL` is opened. | TDV-104, CUS-049, API-136 |
| FEAT-035-AC-05 | A static test fails if any file other than `backend/services/analytics_summary.py` under `backend/` or any file under `analytics/` contains `DATABASE_READONLY_URL` or `evaluation_ground_truth`, and it passes on the delivered code. | API-136, TST-068, TDV-101 |
| FEAT-035-AC-06 | `pipeline_run` equals the latest succeeded run (id, trigger, scope, config_profile, as_of, status `succeeded`, counts) and the response validates against `AnalyticsResponse`. | FR-240, TST-061 |

## Definition of Done

- Endpoint implemented with the full `AnalyticsResponse` schema; FEAT-051 integration point documented.
- Integration and boundary tests pass; DS-07 criteria pass in FEAT-060 once FEAT-051 has filled the aggregate blocks.
- Requirement markers (TST-013); coverage ≥ 85 %; OpenAPI drift check passes.

## Implementation Notes

- Create the read-only engine lazily inside `analytics_summary.py` only when `PIPELINE_PROFILE == "test_v0_1"`, through the single engine factory of `backend/core/db.py` (API-125); set `default_transaction_read_only` or `SET TRANSACTION READ ONLY` per transaction; never share it with any other module.
- Use `true_onset_date` and the alert `local_date` (facility local) for `delay_days`; both are dates, so subtraction gives whole days.
- `result` mapping: planted change with an alarm on or after onset → `detected`; planted change without an alarm → `missed`; no planted change and no alarm → `correct_no_alarm`; no planted change with an alarm → `false_alarm`; this follows the four enum values of TRD 19 `AlarmTimingRow` and CUS-047 ("else listing them as false alarms"). An alarm raised before a planted onset is not classified by the TRDs; report it if encountered (it does not occur in DS-07).
- The UI groups the 8 "None" rows into "Other 8" (TRD 19 E-18 note); the API returns one row per resident.
- TRD gap: CUS-029 asks the analytics response to include `cusum_k`, `cusum_h`, `baseline_n` and the profile, but `Meta` has no `cusum_k` and E-18 has no other place for it; return what TRD 19 defines and report the gap (TRD 19 wins for fields).
- TRD gap: FR-240 says "latest pipeline run" without saying whether a newer running or failed run counts; this file uses the latest succeeded run so that it matches `meta.as_of` (API-069); report it.
- Until FEAT-051 lands, the aggregate blocks are provided by the FEAT-051 mapping seam; no acceptance criterion of this feature asserts their values (BACKLOG §12 Q-01).
