# FEAT-032 Data alerts API and resolve-data-alert CLI

| Field | Value |
|---|---|
| Epic | Backend API |
| Build phase | Phase 5 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-021, FEAT-015 |
| Status | Not Started |

## Purpose

Serve the second queue of the Alert review page, "Data alerts · go to the study team" (SRC-18): data-quality flags such as a stalled baseline, a possible other speaker, many set-aside check-ins, a silent device, or a review that flagged a data problem (`GET /api/v1/data-alerts`). Provide the only way to close a review-flagged data problem: the operator command `python -m backend.cli resolve-data-alert --id <uuid> --reason "<text>"`. Data alerts are never health alarms and never touch the tally.

## Business Context

- BR-12 (data quality visible to the study team), BR-06 (silent devices), BR-04/BR-05 (set-aside and other-speaker patterns), BR-13 (review outcome `data_problem` reaches the study team).
- BR-16: the CLI resolution is audited (`data_alert.resolved`).
- BR-15: with the test data the open list is exactly R08 baseline_stalled, R05 possible_other_speaker, R03 high_set_aside, D02 device_silent.
- FRs covered (BACKLOG.md): FR-297, FR-299.

## Referenced TRDs

- TRD 05 API-133 (endpoint, filters, order, test values), API-057, API-100, API-121.
- TRD 19 §4.3 E-30; schemas `DataAlert`, `DataAlertList`, `DataAlertKind`, `DataAlertStatus`.
- TRD 09 CUS-045 (list fields and order; never in alarm counts), CUS-040 (pipeline never changes `review_flagged_data_problem`), §4.9 (kinds and texts).
- TRD 15 §4.8 command table row `resolve-data-alert --id <uuid> --reason "<text>"`.
- TRD 23 DME-023, §4.2.19, §4.3.7 (data alert lifecycle).
- TRD 06 DB-036 (natural keys; review-flagged rows only changed by the review service and the CLI).
- TRD 12 §4.12 (`data_alert.resolved`), SEC-103 (CLI audit with operator).
- TRD 13 TST-189; TRD 14 TDV-068; TRD 05 AC-API-14 (data-alert half).
- TRD 17 LOG-113 (dashboard only, no notifications), LOG-115 (data alerts are not operational errors).

## Scope

- Handler `GET /api/v1/data-alerts` in `backend/api/alarms.py` calling `services.data_alert_service.list`.
- Filters `status` (default `open`) and `kind`, pagination, ordering by kind in enum order then resident or device code, `meta`.
- CLI command `resolve-data-alert` in `backend/cli.py` with its refusal rules, audit row and exit codes.

## Out of Scope

- Generating rule-based data alerts (`analytics/data_alerts.py`, FEAT-050) and reconciling them in the runner (FEAT-053).
- Creating `review_flagged_data_problem` alerts (review service, FEAT-031).
- The `DataAlertQueue` UI (FEAT-069).
- Any e-mail, SMS or push for data alerts (LOG-113).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-032-FR-01 | `GET /api/v1/data-alerts` shall be available to every authenticated user role and accept `status` ∈ {open, resolved} (default `open`), `kind` ∈ {baseline_stalled, possible_other_speaker, high_set_aside, device_silent, review_flagged_data_problem} and `limit`/`offset`; any other value returns 422 `INVALID_QUERY_PARAMETER`. | API-133; TRD 19 E-30; FR-299 |
| FEAT-032-FR-02 | Items shall be ordered by kind in the enum order above, then by `resident_code` or `device_code` (natural order), and each `DataAlert` shall carry `id`, `kind`, `resident_code`, `device_code`, `title`, `detail`, `status`, `first_detected_at`, `last_detected_at`, `pipeline_run_id`. | API-133, CUS-045; TRD 19 `DataAlert` |
| FEAT-032-FR-03 | The API shall only read `data_alerts`; it shall never compute, create or modify a rule-based data alert. | API-133, CUS-045 |
| FEAT-032-FR-04 | Data alerts shall never appear in `GET /alerts`, the nav count or any alarm count. | CUS-045, FR-300 |
| FEAT-032-FR-05 | `python -m backend.cli resolve-data-alert --id <uuid> --reason "<text>"` shall, connected with `DATABASE_URL` (role `echowell_app`), set the open `review_flagged_data_problem` data alert `<uuid>` to `resolved` with `resolved_at` = now and write one `audit_logs` row `data_alert.resolved` (actor_type `system`, entity data_alert / id, details `{alert_id, kind, reason, operator}`) in the same transaction. | TRD 15 §4.8; FR-297; TRD 12 §4.12, SEC-103 |
| FEAT-032-FR-06 | The command shall refuse with exit code 2 and change nothing for an unknown id, a data alert of any other kind, or one that is not `open`. | TRD 15 §4.8; TST-189 |
| FEAT-032-FR-07 | A `review_flagged_data_problem` data alert shall remain `open` across pipeline runs until resolved by this command; this feature provides the only resolution path. | FR-297, CUS-040, DB-036 |

## Inputs

- HTTP GET with bearer JWT; query `status`, `kind`, `limit`, `offset`.
- CLI arguments `--id` (uuid) and `--reason` (text); OS user name as operator.
- Tables `data_alerts`, `residents`, `devices`, `pipeline_runs`.

## Outputs

- 200 `DataAlertList`; 422 Problem.
- CLI: updated `data_alerts` row (`status`, `resolved_at`, `updated_at`), one `audit_logs` row; exit code 0 on success, 2 on refusal.

## Data Flow

1. API: auth (any user role) → `data_alert_service.list` selects `data_alerts` joined to `residents`/`devices` for codes → filter → order (enum position, natural code) → page → DTO with `meta`.
2. CLI: parse args → open a session on `DATABASE_URL` → `SELECT ... FOR UPDATE` the row → check exists, kind `review_flagged_data_problem`, status `open` (else print the reason and exit 2) → update status and `resolved_at` → `audit_service.record(...)` with operator → commit → exit 0.

## Dependencies

- FEAT-021 (Role-based authorization matrix): roles for GET /data-alerts.
- FEAT-015 (Audit log writer): `data_alert.resolved` row with operator.
- Transitively FEAT-012 (`data_alerts` table, app-role UPDATE grant) and FEAT-016/FEAT-017 (CLI framework in `backend/cli.py`).
- TST-189 runs a full pipeline and a `data_problem` review, so it executes once FEAT-031 and FEAT-053 are merged.

## Database Impact

- Tables read: `data_alerts` (all columns of TRD 20 §4.6.19), `residents` (`resident_code`), `devices` (`device_code`).
- Tables written (CLI only): `data_alerts` (`status`, `resolved_at`), `audit_logs` (INSERT).
- Constraint relied on: `data_alerts_resolved_ck` (`status = 'resolved'` ⇔ `resolved_at` not null).
- Tables created or altered: none.

## API Impact

- Exposed: `GET /api/v1/data-alerts` (E-30; 200 `DataAlertList`; 422 `INVALID_QUERY_PARAMETER`).
- No endpoint resolves or edits data alerts (resolution is CLI-only, FR-297).

## Frontend Impact

None in this feature. Consumer: `DataAlertQueue` on `/alerts` via `getDataAlerts({status})` (TRD 04 §4.6.2), delivered by FEAT-069.

## Analytics Impact

None: the rules that produce data alerts belong to FEAT-050; this feature reads stored results.

## Security Requirements

- API: bearer JWT, admin, clinician and researcher allowed; API key and anonymous 401 (TRD 12 §4.6).
- CLI: operator access only (shell on the backend host); uses `DATABASE_URL` (app role), never `DATABASE_MIGRATION_URL` (TRD 15 §4.8, SEC-111); audit `details.operator` = OS user (SEC-103); the reason text is stored in audit details and must not contain names (SEC-120 guidance).

## Error Handling

- Invalid query parameter → 422.
- CLI unknown id, wrong kind, already resolved → message on stderr, exit 2, no change; database unavailable → non-zero exit with the error class, no partial change (single transaction).

## Logging Requirements

- API access log (LOG-010).
- CLI: one INFO log line for the resolution and the `audit_event` line (LOG-092); data alerts are not logged as operational errors (LOG-115).
- Audit: `data_alert.resolved` per successful resolution.

## Testing Requirements

- Integration (`tests/integration/api/test_alerts.py` data-alert cases, marker `integration`): default `status=open`; `kind` filter; ordering by enum then natural code (fixture with R10 and R2, D02); 422 for unknown kind; schema validation (TST-061) and `meta` (TST-064).
- Integration (`tests/integration/test_resolve_data_alert.py`): TST-189 — a `data_problem` review creates the data alert, a full pipeline run leaves it `open`, the CLI resolves it with `resolved_at` and one `data_alert.resolved` audit row containing `alert_id` and `reason`; the CLI on another kind, an unknown id and an already resolved alert exits 2 with no change.
- DS-07 values (FEAT-060, TDV-068, AC-API-14): exactly four open data alerts with the TRD 19 E-30 titles and details.

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-032-AC-01 | `GET /api/v1/data-alerts?kind=unknown` returns 422 `INVALID_QUERY_PARAMETER`; `GET /data-alerts` without parameters returns only `open` rows. | API-133 |
| FEAT-032-AC-02 | With fixture rows of kinds device_silent (D02), baseline_stalled (R08) and high_set_aside (R03), the list order is R08 baseline_stalled, R03 high_set_aside, D02 device_silent. | API-133, CUS-045 |
| FEAT-032-AC-03 | With DS-07 loaded, the open list is exactly: R08 baseline_stalled "R08 · baseline stuck at 13 of 16" / "12 missed and 5 set aside in 30 days"; R05 possible_other_speaker "R05 · possible other speaker" / "2 check-ins quarantined: Oct 8, Oct 22"; R03 high_set_aside "R03 · many check-ins set aside" / "7 of 29 received: noise, quality flag, too short"; D02 device_silent "D02 · device silent all day" / "Oct 12 · affects R02 and R03". | AC-API-14, TDV-068, FR-301 |
| FEAT-032-AC-04 | `resolve-data-alert --id <open review_flagged_data_problem id> --reason "checked"` exits 0, sets `status` `resolved` and `resolved_at`, and writes exactly one `audit_logs` row `data_alert.resolved` whose details contain `alert_id`, `kind`, `reason` "checked" and `operator`. | TST-189, FR-297 |
| FEAT-032-AC-05 | The same command with the id of a `device_silent` row, a random uuid, or an already resolved row exits 2 and changes no row in `data_alerts` or `audit_logs`. | TST-189, TRD 15 §4.8 |
| FEAT-032-AC-06 | A full pipeline run after a `data_problem` review leaves the `review_flagged_data_problem` row `open` and unchanged. | TST-189, CUS-040 |
| FEAT-032-AC-07 | Every user role receives 200 and an API key 401 on `GET /data-alerts`. | TRD 13 Table 4.13-A |

## Definition of Done

- Endpoint and CLI command implemented; CLI listed in the command help.
- Integration tests pass; TST-189 passes once FEAT-031 and FEAT-053 are merged; DS-07 criterion passes in FEAT-060.
- Requirement markers (TST-013); coverage ≥ 85 %; OpenAPI drift check passes.

## Implementation Notes

- Order by the enum position (`array_position` of the kind list or a CASE expression), never alphabetically.
- The CLI takes no `--force` option and has no batch mode; one id per call (TRD 15 §4.8).
- `resolved_at` for the CLI is the resolution time (TRD 23 §4.2.19); the pipeline sets `resolved_at` = run as-of only for rule kinds (FEAT-053).
- Keep the CLI free of the readonly and migrator URLs; an import-boundary test elsewhere checks that only `analytics_summary.py` references `DATABASE_READONLY_URL` (API-136).
