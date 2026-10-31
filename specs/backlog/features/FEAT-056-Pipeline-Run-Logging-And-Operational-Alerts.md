# FEAT-056 Pipeline run logging and operational alerts

| Field | Value |
|---|---|
| Epic | Monitoring & Logging |
| Build phase | Phase 6 (TRD 25) |
| Priority | P1 |
| Complexity | Low |
| MVP status | Required |
| Dependencies | FEAT-053, FEAT-018 |
| Status | Complete |

## Purpose

Make every pipeline run observable and every operational failure detectable. Around the runner of FEAT-053 this feature emits the structured pipeline log events, records non-fatal conditions as run warnings, marks runs left in `running` for more than 30 minutes as failed (`run_abandoned`), limits automatic retries to one, logs database size in nightly counts, and makes a missed nightly run detectable (`nightly_run_missing` log and Sentry report) so the operational alert path of TRD 17 §4.9 can fire. The `/admin` banners that display these conditions are rendered by FEAT-074.

## Business Context

- BR-15, BR-16 (repeatable, auditable results): every run leaves a structured trace with its id, profile, config hash, counts and warnings.
- RSK-05 (silent failure goes unnoticed) and RSK-07 (free-tier storage limit): failed runs, missed nightly runs and database growth become visible to the DevOps owner and algorithm lead.
- FRs covered (BACKLOG.md): none directly (enabling feature).

## Referenced TRDs

- TRD 17 LOG-060..LOG-067 (run row lifecycle, per-resident rollback, failure record, exact stage names, warnings, success record, stuck runs, single retry), LOG-110 (cron nightly service), LOG-111 (`nightly_run_missing`), LOG-112 (`/admin` run list and failure banner data), LOG-114 (incident watchers), §4.9 operational alerts table, LOG-001, LOG-004, LOG-006, LOG-020..LOG-022, LOG-115.
- TRD 07 ANL-053 (structured events and fields), ANL-054 (no feature values in logs), ANL-052 (warning codes).
- TRD 06 DB-049 (`db_size_bytes` in nightly counts); TRD 23 §4.2.10 (`counts` incl. `db_size_bytes` on nightly runs, `warnings` shape).
- TRD 05 API-068 (`run_abandoned` owning row).
- TRD 17 AC-LOG-05, AC-LOG-06, AC-LOG-07.

## Scope

- Structured JSON events in `backend/services/pipeline_runner.py` (via `backend/core/logging.py` from FEAT-018): `pipeline_run_started`, `pipeline_run_succeeded` (success, INFO) / `pipeline_run_failed` (failure, ERROR) (D-80) with `pipeline_run_id`, `trigger`, `scope`, `profile`, `config_hash`, `duration_ms`, `counts`, `warning_count`; one `pipeline_warning` per warning (WARNING; ERROR for `baseline_mismatch`); `data_alerts_updated` with per-kind counts.
- Stage naming: exceptions and warnings carry the exact stage names of LOG-063 in `detail` ("<stage name>: <exception type>: <sanitised message>").
- Stuck-run handling: at the start of every run and at backend startup, any `pipeline_runs` row `running` for more than 30 minutes is set `failed` with warning `run_abandoned` and a non-empty `error_message`.
- Retry rule: a failed run is retried automatically at most once, and only by the next ingest or nightly trigger; there is no in-process retry loop.
- Nightly `counts.db_size_bytes` from `pg_database_size(current_database())`.
- `backend/jobs/nightly_run.py` non-running firing: check the most recent facility-local date whose 02:00 hour has passed and log ERROR `nightly_run_missing` (and report to Sentry when `SENTRY_DSN` is set) when no succeeded nightly run exists for it.
- Data for the `/admin` banners: the read-time conditions "most recent run of any trigger is failed" and "no succeeded nightly run started within the previous 26 hours" are derivable from `GET /api/v1/pipeline/runs` (E-31).

## Out of Scope

- Logging infrastructure, JSON formatter, redaction and request-ID propagation (FEAT-018).
- Sentry SDK setup (FEAT-084) and uptime monitoring workflow `uptime.yml` and incident issues (FEAT-085).
- Rendering of the `/admin` run list and banners (FEAT-074).
- Data-alert rules and their dashboard display (FEAT-050, FEAT-069); data alerts are never operational errors (LOG-115).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-056-FR-01 | Every run (trigger `ingest`, `nightly`, `manual`, `test`) shall have its `pipeline_runs` row with status `running`, `config_profile`, `config_snapshot`, `code_version` and `started_at` committed before the first stage executes, and an INFO `pipeline_run_started` event with `pipeline_run_id`, `trigger`, `scope`, `profile`, `config_hash`. | LOG-060, ANL-053 |
| FEAT-056-FR-02 | On success the runner shall log INFO with `pipeline_run_id`, `counts` (keys of TRD 23 §4.2.10), `duration_ms` and `warning_count`. | LOG-065, ANL-053 |
| FEAT-056-FR-03 | On failure the run row shall be updated per ANL-041 and one ERROR `pipeline_run_failed` log with `pipeline_run_id` shall be written; each failed resident adds `{"code": "exception", "resident_code": <code or null>, "session_id": null, "detail": "<stage name>: <exception type>: <sanitised message>"}`. | LOG-062, LOG-061 |
| FEAT-056-FR-04 | Stage names in warnings and logs shall be exactly `duplicate_detection`, `quality_gate`, `epoch_detection`, `speaker_screen`, `context_adjustment`, `baseline`, `scoring`, `cusum`, `alerts`, `day_ledger`, `data_alerts`, `aggregates`. | LOG-063, D-80 |
| FEAT-056-FR-05 | Each run warning shall be stored in `pipeline_runs.warnings` as `{code, resident_code, session_id, detail}` without failing the run, and logged as one `pipeline_warning` event (WARNING; ERROR for `baseline_mismatch`). | LOG-064, ANL-052, ANL-053 |
| FEAT-056-FR-06 | A run row left `running` for more than 30 minutes shall be marked `failed` with warning `run_abandoned` and a non-empty `error_message` by the next run (before it proceeds) or at backend startup. | LOG-066, API-068 |
| FEAT-056-FR-07 | A failed run shall be retried automatically at most once, at the next ingest or nightly trigger; repeated failure stays visible in `GET /api/v1/pipeline/runs` for the `/admin` list. | LOG-067 |
| FEAT-056-FR-08 | Nightly runs shall add `db_size_bytes` (`pg_database_size`) to `counts`. | DB-049; TRD 23 §4.2.10 |
| FEAT-056-FR-09 | Each firing of `backend.jobs.nightly_run` that does not start a run shall check the most recent facility-local date whose 02:00 hour has passed and, if no succeeded nightly run exists for it, log ERROR `nightly_run_missing` and report it to Sentry when enabled. | LOG-111, TRD 17 §4.9 |
| FEAT-056-FR-10 | The data needed for the `/admin` banners (latest run status of any trigger; latest succeeded nightly run `started_at`) shall be available through `GET /api/v1/pipeline/runs` with the `trigger` and `status` filters, computed at read time. | LOG-111, LOG-112, API-134 |
| FEAT-056-FR-11 | Pipeline logs shall contain only study IDs and run metadata: no feature values, payloads, e-mail addresses or secrets. | ANL-054, LOG-020, LOG-021, LOG-022 |
| FEAT-056-FR-12 | Each run shall log one INFO `data_alerts_updated` with counts per kind (open, resolved); data alerts are not logged as operational errors. | LOG-115 |
| FEAT-056-FR-13 | Operational alerts (failed run, missed nightly) shall reach the DevOps owner and the algorithm lead through Sentry/ERROR logs and the repository `incident` issue watchers. | LOG-114, TRD 17 §4.9 |

## Inputs

- Runner lifecycle events and `PipelineResult.warnings` (FEAT-053).
- `pipeline_runs` rows (status, trigger, `started_at`); clock and `FACILITY_TZ` in the nightly job; `pg_database_size`.
- Logging setup of FEAT-018 (`LOG_FORMAT`, `LOG_LEVEL`, context vars `pipeline_run_id`, `resident_code`); `SENTRY_DSN` (optional).

## Outputs

- JSON log lines: `pipeline_run_started`, success event, `pipeline_run_failed`, `pipeline_warning`, `data_alerts_updated`, `nightly_run_missing`.
- `pipeline_runs.warnings` entries (incl. `run_abandoned`, `exception`), `error_message`, `counts.db_size_bytes`.
- Sentry events for failed and missing runs when enabled.

## Data Flow

Runner start → abandoned-run sweep (UPDATE stale `running` rows) → INSERT run row → `pipeline_run_started` → engine and per-resident writes → warnings stored and logged → final UPDATE → success or `pipeline_run_failed` log. Nightly job non-running firing → SELECT latest succeeded nightly run for the last passed 02:00 date → `nightly_run_missing` ERROR (+ Sentry). `/admin` (FEAT-074) → `GET /api/v1/pipeline/runs` → banners.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-053, FEAT-018

- FEAT-053 provides the runner whose lifecycle is logged.
- FEAT-018 provides structured JSON logging, redaction and context propagation.

Features that build directly on this one (BACKLOG.md §4): none.

## Database Impact

- `pipeline_runs`: UPDATE of stale rows (`status = failed`, `finished_at`, `warnings` + `run_abandoned`, `error_message`); `counts.db_size_bytes` on nightly runs. No new table or column.
- Reads `pipeline_runs` for the abandoned-run sweep and the nightly-missing check.

## API Impact

None new. `GET /api/v1/pipeline/runs` (E-31) and `GET /api/v1/pipeline/runs/{id}` (E-21) expose the stored warnings, counts and statuses.

## Frontend Impact

None in this feature; FEAT-074 renders the run list, the failure banner and the "Nightly run missing for <date>" banner from E-31.

## Analytics Impact

None. `analytics/` does not log (ANL-053, LOG-006); its warnings are logged by the backend.

## Security Requirements

- No secrets, feature values, payloads, e-mails or note bodies in logs (LOG-020..LOG-022, ANL-054); the redaction filter of FEAT-018 applies.
- Sentry reports carry no PII (`send_default_pii=False`, LOG-100) and are sent only when `SENTRY_DSN` is set.

## Error Handling

- A failure to write a log line never fails a run.
- A failure of the abandoned-run sweep is logged at ERROR and the new run proceeds.
- The nightly-missing check never starts a run; it only logs.

## Logging Requirements

- Events and levels as in FEAT-056-FR-01..FEAT-056-FR-12; every record carries `ts`, `level`, `logger`, `msg`, `event`, `env`, `version` and the `pipeline_run_id` context (LOG-001, LOG-004).
- Audit rows `pipeline.run.started` / `pipeline.run.finished` remain the runner's (FEAT-053); this feature adds no audit action.

## Testing Requirements

- Integration (`tests/integration/pipeline/test_run_logging.py`, marker `integration`, logs captured with `caplog` and JSON parsing):
  - AC-LOG-05: exception injected into the `cusum` stage → `scores`, `cusum_state`, `alerts` unchanged, run `failed`, warning detail starting with `cusum:`, triggering ingest still 201.
  - AC-LOG-06: row left `running` with `started_at` 31 minutes ago → `failed` with `run_abandoned` on the next run.
  - AC-LOG-07: no nightly run in the past 26 hours → a non-running firing logs `nightly_run_missing`.
  - Success run logs one start and one success event with `config_hash`, `counts`, `duration_ms`, `warning_count`.
  - Nightly run `counts` contains `db_size_bytes` > 0 (DB-049).
  - Log scan: no feature value or e-mail in captured pipeline logs (AC-LOG-02 style grep).
- Retry rule: two consecutive failures produce at most one automatic retry (LOG-067).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-056-AC-01 | An exception injected into the `cusum` stage leaves `scores`, `cusum_state` and `alerts` unchanged, sets the run `failed` with an `exception` warning whose `detail` names stage `cusum`, and the triggering ingest returns 201. Verified by: Integration (`tests/integration/pipeline/test_run_logging.py`). | AC-LOG-05; LOG-062 |
| FEAT-056-AC-02 | A `pipeline_runs` row left `running` with `started_at` 31 minutes ago is marked `failed` with warning `run_abandoned` and non-empty `error_message` when the next run starts. Verified by: Integration (`tests/integration/pipeline/test_run_logging.py`). | AC-LOG-06; API-068 |
| FEAT-056-AC-03 | With no succeeded nightly run in the past 26 hours, a non-running firing of `backend.jobs.nightly_run` logs ERROR `nightly_run_missing`. Verified by: Integration (`tests/integration/pipeline/test_run_logging.py`). | AC-LOG-07; LOG-111 |
| FEAT-056-AC-04 | A successful run emits exactly one `pipeline_run_started` and one completion event, each a single JSON line containing `pipeline_run_id`, `trigger`, `profile`, `config_hash`, and the completion event `counts`, `duration_ms`, `warning_count`. Verified by: Integration (`tests/integration/pipeline/test_run_logging.py`). | ANL-053; LOG-065 |
| FEAT-056-AC-05 | A nightly run stores `counts.db_size_bytes` as a positive integer. Verified by: Integration (`tests/integration/pipeline/test_run_logging.py`). | DB-049 |
| FEAT-056-AC-06 | `grep` over captured logs of a SRC-05 batch run finds no feature value from the CSV and no e-mail address. Verified by: Inspection (run the command in the criterion and check its output). | ANL-054; LOG-021 |

## Definition of Done

- All FEAT-056 acceptance criteria pass; integration tests green.
- Batch report lists IDs and the TRD inconsistencies noted below (AGT-022).

## Implementation Notes

- Resolved (TRD 24 D-80): the end event is exactly one of `pipeline_run_succeeded` (LOG-065) or `pipeline_run_failed` (LOG-062); TRD 07 ANL-053 no longer names `pipeline_run_finished`.
- LOG-063 now lists `data_alerts` and `aggregates` for stages 11 and 12 of ANL-006 (D-80).
- AC-LOG-05 now checks an `exception` warning whose `detail` starts with `cusum:`; the warning shape (TRD 23 §4.2.10, LOG-062) has no `stage` field (D-80).
- `epoch_key_changed` was removed from ANL-053 (D-80); the renumbering case is recorded as `late_arrival` with detail "epoch renumbering blocked" (ANL-038).
- Use `contextvars` from FEAT-018 so `pipeline_run_id` and `resident_code` appear on every record without passing them explicitly (LOG-004).
