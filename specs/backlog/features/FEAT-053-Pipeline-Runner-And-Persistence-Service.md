# FEAT-053 Pipeline runner and persistence service

| Field | Value |
|---|---|
| Epic | Data Processing |
| Build phase | Phase 6 (TRD 25) |
| Priority | P0 |
| Complexity | High |
| MVP status | Required |
| Dependencies | FEAT-052, FEAT-024, FEAT-013 |
| Status | Not Started |

## Purpose

Fill `backend/services/pipeline_runner.py::run(scope, trigger, profile, as_of)`, the only backend caller of `analytics.run_pipeline`. The runner records the run in `pipeline_runs`, loads the immutable raw store and master data, calls the pure engine, and writes every derived table resident by resident in one transaction each, with natural-key upserts so that frozen baselines, alerts, reviews, notes and snoozes survive any number of re-runs. It is the persistence half of the "load → compute → reconcile → write" contract of TRD 07 §4.8 and the service interface that FEAT-024 defined in Phase 5.

## Business Context

- BR-02 (raw data immutable, everything else rebuildable): derived rows are replaced from `raw_sessions` on every run; raw rows are never touched (D-07).
- BR-09, ASM-07 (frozen baselines never recomputed): baselines are insert-only and passed back to the engine (D-57 via ARC-043).
- BR-11, BR-13, R15 (alarm lifecycle and human review): alerts are upserted on `(epoch_id, session_id)`, keeping status, reviews and snoozes (D-45).
- BR-14 (new-admission arm): a new admission whose baseline freezes moves to the longitudinal cohort (DB-025).
- BR-15 (answer key): the persisted tables equal the engine output so Tier B validation matches SRC-03.
- FRs covered (BACKLOG.md): FR-051, FR-094, FR-105, FR-110, FR-205, FR-296.

## Referenced TRDs

- TRD 07 ANL-033..ANL-042 (run row, advisory locks, `RawRecord` from typed columns, delete/insert, insert-only baselines, epoch upsert, alert upsert, success, per-resident failure, value mapping), ANL-060 (data-alert reconciliation), ANL-064 (never read `evaluation_ground_truth`), §4.8 sequence diagram.
- TRD 06 DB-013..DB-020 (per-resident transaction, replaced vs kept tables, epoch upsert, frozen baselines, renumbering block, alert reconciliation, rebuild idempotency, run row contents), DB-021 (advisory keys a and c), DB-022, DB-025 (cohort change), DB-036 (data-alert reconciliation).
- TRD 05 API-063, API-064, API-128 (natural-key upserts).
- TRD 01 ARC-063..ARC-065, ARC-070..ARC-073.
- TRD 03 NFR-120..NFR-129.
- TRD 20 §4.6.10–§4.6.19 (tables), `alerts_closed_ck`, `pipeline_runs_error_ck`; TRD 23 §4.2.10 (`counts`, `warnings` shapes); TRD 12 §4.12 (audit actions `pipeline.run.started`, `pipeline.run.finished`, `alert.closed`, `resident.cohort_changed`).
- TRD 25 AGT-056, AGT-057, AGT-060; TRD 24 D-45, D-62, D-63.
- TRD 13 TST-050, TST-051, TST-067, TST-068, TST-185, AL-04, DA-11; TRD 14 VC-G12, TDV-101, TDV-102.

## Scope

- `pipeline_runner.run(scope, trigger, profile, as_of)` filling the interface of FEAT-024: run-row creation and commit, input loading, engine call, per-resident persistence, run finalisation.
- Loading: `raw_sessions` of the residents in scope plus every resident sharing a device with them in the ledger window; `residents`; all `device_assignments` of the facility; persisted `baselines` as `frozen_baselines`; config via the FEAT-040 loader.
- `RawRecord` construction from typed `raw_sessions` columns (never by re-parsing `payload`).
- Per-resident transaction in ascending `resident_code` with `pg_advisory_xact_lock(advisory_key('resident', resident_code))`: delete+insert `processed_sessions`, `scores`, `cusum_state`, `day_ledger`; upsert `epochs`; insert-only `baselines`; upsert/close `alerts`; resident data-alert reconciliation; cohort transition.
- End-of-run `device_silent` data-alert reconciliation under `advisory_key('device_alerts', 'all')`.
- Run finalisation: `succeeded` or `failed`, `finished_at`, `counts`, `warnings`, `error_message`; audit rows.

## Out of Scope

- The engine (FEAT-052) and its stages.
- Triggers that call the runner: `POST /api/v1/sessions`, `POST /api/v1/ingest`, nightly job (FEAT-054); `POST /api/v1/pipeline/run` endpoint (FEAT-024).
- The `rebuild=True` path that deletes and recomputes frozen baselines as `echowell_migrator`, and the `config_changed_requires_rebuild` check (FEAT-055, ANL-032).
- Structured log events, stuck-run handling (`run_abandoned`) and single-retry rule (FEAT-056).
- Reading `evaluation_ground_truth` for alarm timing (FEAT-035, `analytics_summary.py` only).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-053-FR-01 | Before loading data, the runner shall insert and commit a `pipeline_runs` row with `status = running`, `trigger` ∈ {ingest, nightly, manual, test}, `scope`, `config_profile`, `config_snapshot` (23 keys plus `config_hash` and `as_of`), `as_of`, `code_version` = `GIT_SHA` (default "unknown") and `started_at`, and write audit `pipeline.run.started`. | ANL-033, DB-020, API-063, ARC-073 |
| FEAT-053-FR-02 | The runner shall load `raw_sessions` for the scope plus all residents sharing a device with a scoped resident on any affected local date, all `device_assignments` of the facility, the residents, and persisted baselines as `frozen_baselines`. | ANL-016, ARC-065, ANL-037 |
| FEAT-053-FR-03 | `RawRecord` objects shall be built from the typed columns of `raw_sessions`, with `timestamp_utc` as an aware UTC datetime; `payload` shall not be re-parsed. | ANL-035 |
| FEAT-053-FR-04 | For each resident in scope, in ascending `resident_code`, the runner shall open one transaction starting with `pg_advisory_xact_lock(advisory_key('resident', resident_code))`; no session-level or global lock shall be used. | ANL-034, DB-021 (a), API-064, ARC-063, D-62 |
| FEAT-053-FR-05 | Within that transaction the runner shall delete the resident's `processed_sessions`, `scores`, `cusum_state` and `day_ledger` rows and insert the newly derived rows (one `processed_sessions` row per `raw_sessions` row, one `scores` row per scored session with the 7 z values, composite_raw, composite_z, cusum_tally, alarm_state, local_date, is_morning, one `cusum_state` row per resident-epoch). | ANL-036, DB-014, FR-094, FR-105, NFR-123 |
| FEAT-053-FR-06 | `baselines`, `alerts`, `alert_reviews`, `staff_notes` and `raw_sessions` shall never be deleted by a run. | ANL-036, DB-014, NFR-120, NFR-126 |
| FEAT-053-FR-07 | `epochs` shall be upserted on `(resident_id, epoch_number)` reusing `epochs.id` and updating `ended_at`; epochs without a frozen baseline that the computation no longer produces are deleted; if the computation would change the key of an epoch with a frozen baseline, all derived rows of that resident stay unchanged, a `late_arrival` warning with detail "epoch renumbering blocked" is recorded and the run continues. | ANL-038, DB-015, DB-017, FR-051 |
| FEAT-053-FR-08 | Baselines shall be inserted (20 rows) only when an epoch's baseline forms for the first time; persisted rows are passed back to the engine and kept even when the engine reports a mismatch. | ANL-037, DB-016, ARC-043, NFR-124 |
| FEAT-053-FR-09 | Alerts shall be upserted on `(epoch_id, session_id)`: a new first crossing inserts `status = open`; a matching row keeps `id`, `status`, `acknowledged_by`, `acknowledged_at`, `snoozed_until`, `snoozed_by` and its reviews; a non-closed alert no longer produced is closed with `closed_reason = 'superseded by rebuild'`; an `AlertEvent` with `epoch_ended = True` closes its alert with `closed_reason = 'epoch ended'`; every close sets `closed_at` = the run's `as_of` and writes audit `alert.closed`. | ANL-039, DB-018, API-128, FR-110, ARC-044 |
| FEAT-053-FR-10 | Rule-kind data alerts shall be reconciled on natural keys `(kind, resident_id)` and `(kind, device_id)`: insert `open` with `first_detected_at` = `last_detected_at` = as-of when absent; update `title`, `detail`, `last_detected_at`, `pipeline_run_id` when open; set `resolved` with `resolved_at` = as-of when not detected in a run covering the subject; never reopen a resolved row; never modify `review_flagged_data_problem` rows. | ANL-060, DB-036, FR-296 |
| FEAT-053-FR-11 | The `device_silent` reconciliation shall run in an end-of-run transaction holding `advisory_key('device_alerts', 'all')`. | DB-021 (c) |
| FEAT-053-FR-12 | When a `new_admission` resident has a frozen baseline in its current epoch, the resident transaction shall set `residents.cohort = 'longitudinal'` and insert audit `resident.cohort_changed` with `{from, to, epoch_number}`; the transition is one-way. | DB-025, FR-205 |
| FEAT-053-FR-13 | An exception inside a resident's transaction shall roll back only that resident (previous rows unchanged), add `{code: "exception", resident_code, session_id: null, detail}` to the warnings and continue; an exception outside the per-resident transactions shall stop the run with no derived writes. | ANL-041, DB-013, ARC-064, D-63 |
| FEAT-053-FR-14 | On completion the runner shall, in a separate transaction, set `status` = `succeeded` (every resident committed) or `failed` (with non-empty `error_message` naming the failed residents or step), `finished_at`, `counts` = `PipelineResult.counts`, `warnings` as `{code, resident_code, session_id, detail}` items, and write audit `pipeline.run.finished`. | ANL-040, ANL-041, LOG-061, LOG-062, LOG-065 |
| FEAT-053-FR-15 | A raw record shall be committed before its run starts, and a failed run shall never remove or alter it. | DB-022, NFR-129 |
| FEAT-053-FR-16 | Engine values shall be stored with the mapping `alarm_state` off/rings/on, `feature_key` `composite`, booleans as booleans, numbers as `double precision` without rounding. | ANL-042, NFR-032 |
| FEAT-053-FR-17 | Two consecutive full runs with unchanged inputs and configuration shall leave every derived table identical on all columns except `id`, `created_at`, `updated_at` and `pipeline_run_id`, with no duplicate alerts, epochs or ledger rows. | DB-019, ARC-071, ANL-023, AGT-056 |
| FEAT-053-FR-18 | The runner shall connect only through `DATABASE_URL` (`echowell_app`) and shall never reference `evaluation_ground_truth`. | ANL-064, AGT-057, AGT-060 |
| FEAT-053-FR-19 | The invariants usable + set_aside + quarantined + duplicate = arrivals per resident, and checked_in + missing_resident + missing_device_gap = ledger days, shall hold after every run. | NFR-125 |

## Inputs

- Arguments: `scope` (`"all"` or a list of resident codes), `trigger`, `profile`, `as_of` (resolved by the caller per API-135).
- Tables read: `raw_sessions`, `residents`, `devices`, `device_assignments`, `baselines`, `epochs`, `alerts`, `data_alerts`, `config_parameters` (through FEAT-040), `facilities`.
- Env: `DATABASE_URL`, `GIT_SHA`, `PIPELINE_PROFILE`, `FACILITY_TZ`.

## Outputs

- One `pipeline_runs` row per invocation with final status, counts and warnings.
- Derived rows in `processed_sessions`, `epochs`, `baselines`, `scores`, `cusum_state`, `day_ledger`, `alerts`, `data_alerts`; `residents.cohort` updates.
- Audit rows `pipeline.run.started`, `pipeline.run.finished`, `alert.closed`, `resident.cohort_changed`.
- Return value: the run id and final status to the caller (FEAT-054, FEAT-055, FEAT-024).

## Data Flow

Trigger → `run()` → INSERT `pipeline_runs` (running) + audit, COMMIT → SELECT inputs → `analytics.run_pipeline(...)` → for each resident (ascending code): BEGIN, resident advisory lock, replace derived rows, upsert epochs, insert new baselines, reconcile alerts and resident data alerts, cohort change, COMMIT or ROLLBACK + `exception` warning → device data-alert transaction under `device_alerts` lock → UPDATE `pipeline_runs` (succeeded/failed, counts, warnings, error_message, finished_at) + audit `pipeline.run.finished`.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-052, FEAT-024, FEAT-013

- FEAT-052 provides `run_pipeline` and `PipelineResult`.
- FEAT-024 provides the service interface, run endpoints and as-of resolution this feature fills.
- FEAT-013 provides the connection layer, `advisory_key` helper and indexes.

## Database Impact

- Tables written: `pipeline_runs` (insert, update), `processed_sessions`, `scores`, `cusum_state`, `day_ledger` (delete + insert per resident), `epochs` (upsert, conditional delete), `baselines` (insert only), `alerts` (insert, update of status/closed_reason/closed_at only), `data_alerts` (insert, update, resolve), `residents` (`cohort`), `audit_logs` (insert).
- Tables read: `raw_sessions`, `residents`, `devices`, `device_assignments`, `facilities`, `config_parameters`.
- Never touched: `alert_reviews`, `staff_notes` (except preserved FKs), `raw_sessions` writes, `evaluation_ground_truth`.
- No tables created or altered (schema delivered by FEAT-011, FEAT-012).

## API Impact

- No endpoint exposed. The runner backs `POST /api/v1/sessions` (E-05), `POST /api/v1/ingest` (E-06) and `POST /api/v1/pipeline/run` (E-20); `GET /api/v1/pipeline/runs` (E-31) and `GET /api/v1/pipeline/runs/{id}` (E-21) read the rows it writes.
- Read endpoints use the `as_of` of the latest succeeded run this feature records (API-069).

## Frontend Impact

None directly. Pages show what the runner persisted; the `/admin` "Pipeline runs" tab (FEAT-074) lists its rows.

## Analytics Impact

- Calls `analytics.run_pipeline` once per run; implements no formula (API-006).
- Maps engine contracts to rows (ANL-042) and passes persisted baselines back as `frozen_baselines` (ANL-037).

## Security Requirements

- Connect only with `DATABASE_URL` (role `echowell_app`); the runner holds no privilege on `evaluation_ground_truth` and a direct SELECT from it fails (DB-009, AC-ANL-14).
- `echowell_app` cannot UPDATE/DELETE `raw_sessions`, `audit_logs`, `alert_reviews`, `staff_notes` (NFR-120, NFR-126); the runner never attempts it.
- Audit rows contain no feature values or secrets (SEC-104).

## Error Handling

- Resident-level exception → rollback of that resident, `exception` warning, continue, run ends `failed` with `error_message` naming the resident (ANL-041, DB-013).
- Load, configuration or engine exception (`ContractError`, `ConfigError`) → no derived writes, run `failed` with `error_message` naming the step (ANL-041).
- Epoch renumbering of a frozen epoch → resident skipped, `late_arrival` warning "epoch renumbering blocked" (DB-017).
- Baseline mismatch → persisted rows kept, `baseline_mismatch` warning (ANL-037).
- The run row's final update happens in its own transaction so it is written even after failures (ANL-041).

## Logging Requirements

- Audit: `pipeline.run.started` at row creation, `pipeline.run.finished` at completion, `alert.closed` per closed alert, `resident.cohort_changed` per transition (TRD 12 §4.12; API-063; DB-025).
- Run warnings stored in `pipeline_runs.warnings` with shape `{code, resident_code, session_id, detail}` (TRD 23 §4.2.10).
- The structured log events (`pipeline_run_started`, `pipeline_run_succeeded` / `pipeline_run_failed`, `pipeline_warning`; D-80) are emitted by FEAT-056 around this service.

## Testing Requirements

- Integration (`tests/integration/pipeline/`, marker `integration`, PostgreSQL 16 via testcontainers, TST-002):
  - TST-051: run row has `config_profile`, `config_snapshot`, `code_version` = `GIT_SHA`, status `succeeded`, counts = status totals.
  - TST-050 / DB-019 `tests/integration/test_rebuild_idempotent.py`: two full runs, identical derived tables.
  - TST-067 / AL-04: rebuild after a review and a snooze keeps alert id, reviews, `acknowledged`, `snoozed_until`.
  - DB-013 fault injection: failure for R05 leaves R05 rows unchanged, other residents updated, run `failed` naming R05 (AC-ANL-08).
  - DB-016 late record inside R01's baseline window: baselines unchanged, warning present.
  - DA-11: same data-alert condition on two runs → one open row, `last_detected_at` updated; condition gone → `resolved`.
  - TST-185: new-admission N01 moves to longitudinal on its 16th usable record with one `resident.cohort_changed` audit row.
  - TST-068 / TDV-101 / TDV-102: static scan finds no `evaluation_ground_truth` reference in the runner; outputs identical with the table empty and loaded.
  - NFR-125 invariant check after each run.
- Grant test (TST-041): as `echowell_app`, `SELECT` on `evaluation_ground_truth` raises permission denied (AC-ANL-14).
- Coverage `backend/` ≥ 85 % (TST-141).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-053-AC-01 | After a full `test_v0_1` run on SRC-05 at as-of 2026-10-30 15:00 America/Chicago, `pipeline_runs.counts` = 283/267/12/2/2/17/2/0/98/2/0/10 and `config_snapshot` contains the 23 keys, `config_hash` and `as_of`. | AC-ANL-09; DB-020; TST-051 |
| FEAT-053-AC-02 | Two consecutive full runs leave every derived table identical except `id`, `created_at`, `updated_at`, `pipeline_run_id`; alert, epoch and ledger row counts are unchanged. | TST-050; DB-019; AGT-056 |
| FEAT-053-AC-03 | A full rebuild with an R09 alert that has a saved review and a snooze keeps the alert id, its `alert_reviews` rows, `status = acknowledged` and `snoozed_until`. | AC-ANL-11; TST-067 |
| FEAT-053-AC-04 | A deliberately failing write for R05 leaves R05's previously persisted derived rows unchanged, updates the other residents, and ends the run `failed` with an `exception` warning and an `error_message` naming R05. | AC-ANL-08; DB-013 |
| FEAT-053-AC-05 | After the SRC-05 run, `alerts` holds exactly R09 (R09-20261021-01) and R10 (R10-20261024-01), both `open`, and `data_alerts` holds exactly the four open rows R08 baseline_stalled, R05 possible_other_speaker, R03 high_set_aside, D02 device_silent with `first_detected_at` = 2026-10-30T20:00:00Z. | CUS-028; DB-036 |
| FEAT-053-AC-06 | As `echowell_app`, `SELECT * FROM evaluation_ground_truth` fails with a permission error, and a static scan of `backend/services/pipeline_runner.py` finds no reference to it. | AC-ANL-14; TDV-101 |
| FEAT-053-AC-07 | Inserting a late record dated inside R01's baseline window and re-running leaves R01's `baselines` rows byte-identical and adds a `late_arrival` warning. | DB-016; AC-ANL-05 |
| FEAT-053-AC-08 | The N01 fixture moves from `new_admission` to `longitudinal` in the run that freezes its baseline, with one `resident.cohort_changed` audit row. | TST-185; DB-025 |

## Definition of Done

- All FEAT-053 acceptance criteria pass; `pytest tests/integration -q -k pipeline` green (TRD 25 Phase 6 Commands).
- Full rebuild from `raw_sessions` reproduces identical derived tables; each run stores its config snapshot and git SHA (TRD 25 Phase 6 DoD).
- Backend coverage ≥ 85 %; batch report lists IDs and tests (AGT-022).

## Implementation Notes

- Keep the file name `backend/services/pipeline_runner.py` (TRD 07 §4.8); `backend/services/{baseline,cusum,scoring,speaker_screen,morning_adjustment}.py` stay thin read services and must not reimplement formulas (TRD 07 §8).
- Commit the run row in its own transaction before loading data, so a crash leaves a visible `running` row that FEAT-056 can mark `run_abandoned`.
- Emit `baseline_mismatch` (detail "epoch <n>") for value or membership differences of a frozen baseline (ANL-037, ANL-052; TRD 06 DB-016 aligned in the PR #2 consistency fixes) and `late_arrival` for records classified late (ANL-025) and for blocked renumbering (DB-017).
- `alerts` updates by `echowell_app` are limited to status/closure columns; the table has no DELETE grant for the app role (DB-009).
- Use the scope JSON shapes of TRD 20 `pipeline_runs_scope_ck`: `{"type": "all"}` or `{"type": "residents", "resident_codes": [...]}`.
