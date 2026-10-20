# FEAT-084 Error monitoring with Sentry (optional, interim stack only)

| Field | Value |
|---|---|
| Epic | Monitoring & Logging |
| Build phase | Phase 9 (TRD 25) |
| Priority | P2 |
| Complexity | Low |
| MVP status | Optional |
| Dependencies | FEAT-081, FEAT-082, FEAT-018 |
| Status | Not Started |

## Purpose

Offer optional backend error monitoring through Sentry on the interim staging and production environments: when `SENTRY_DSN` is set, initialise `sentry-sdk` with no personal data, no request bodies, no headers, cookies or query strings and the same redaction as the logs; when it is empty, make no network call at all. Sentry is backend-only, receives synthetic-data events only, and must be disabled in production before AWS go-live unless re-approved.

## Business Context

- RSK-05 and RSK-07: faster detection of pipeline failures and missed nightly runs (TRD 17 §4.9 operational alerts list Sentry as a channel when enabled).
- BR-16: no PII, bodies or secrets leave the system (SEC-127, LOG-100).
- D-28: Sentry may hold only synthetic-data events (LOG-102, TPS-060).

## Referenced TRDs

- TRD 17 LOG-070, LOG-100, LOG-101, LOG-102, LOG-111, LOG-023, LOG-024, §4.8 monitoring table, §4.9 operational alerts.
- TRD 22 TPS-001, TPS-002, TPS-060, TPS-061.
- TRD 12 SEC-127.
- TRD 21 §4.2 (`SENTRY_DSN`, secret), §4.7 matrix (local and test empty; staging and interim production optional).
- TRD 15 §4.5 step 6 (SENTRY_DSN allowed on the `nightly` service).

## Scope

- `backend/core/monitoring.py` (or the equivalent startup hook in `backend/main.py`): `init_sentry(settings)` called once at startup and in `backend/jobs/nightly_run.py`.
- Initialisation parameters: `dsn=SENTRY_DSN`, `environment=APP_ENV`, `release=GIT_SHA`, `send_default_pii=False`, `traces_sample_rate=0`, `max_request_body_size="never"`, `before_send` applying the LOG-023/LOG-024 redaction and dropping request headers, cookies and query strings.
- Reporting of `unhandled_exception` (LOG-070) and `nightly_run_missing` (LOG-111) events when enabled.
- Pinned `sentry-sdk` in `backend/requirements.txt`.
- Runbook lines in `docs/deployment.md`: project `echowell-backend`, who receives e-mail per new issue, and the go-live rule.

## Out of Scope

- Any browser SDK or frontend error reporting (TPS-060 backend-only; LOG-082 no frontend telemetry).
- Performance tracing (`traces_sample_rate=0`).
- Sentry on AWS production (disabled unless approved, TPS-061; CloudWatch is the default there, FEAT-092).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-084-FR-01 | When SENTRY_DSN is non-empty, the backend shall initialise `sentry-sdk` with `environment`=APP_ENV, `release`=GIT_SHA, `send_default_pii=False`, `traces_sample_rate=0`, `max_request_body_size="never"` and a `before_send` hook applying the LOG-023/LOG-024 redaction and dropping request headers, cookies and query strings. | LOG-100, SEC-127 |
| FEAT-084-FR-02 | When SENTRY_DSN is empty, no Sentry code path shall make a network call (the SDK is not initialised). | LOG-101 |
| FEAT-084-FR-03 | Sentry shall be enabled only for staging and production of the interim stack (empty in local and test) and receive only synthetic-data events. | LOG-102, TPS-060, TRD 21 §4.7 |
| FEAT-084-FR-04 | Sentry shall be backend-only; no browser SDK shall be added. | TPS-060, LOG-082 |
| FEAT-084-FR-05 | Unhandled request exceptions (`unhandled_exception`) shall be reported to Sentry when enabled, after the same sanitisation as the ERROR log. | LOG-070 |
| FEAT-084-FR-06 | A nightly firing that detects a missing nightly run shall report `nightly_run_missing` to Sentry when enabled. | LOG-111 |
| FEAT-084-FR-07 | Before AWS go-live, SENTRY_DSN shall be empty in production unless the project coordinator and UND IT approve Sentry for PHI-derived data; the runbook shall state this. | TPS-061, SEC-127, LOG-102 |
| FEAT-084-FR-08 | SENTRY_DSN shall be treated as a secret (`SecretStr`, stored only in platform variables). | TRD 21 §4.2, SEC-050 |

## Inputs

- `SENTRY_DSN`, `APP_ENV`, `GIT_SHA` settings; logging redaction filters of FEAT-018.
- Railway service variables (FEAT-081); Netlify configuration (FEAT-082) only to confirm no frontend DSN is set.

## Outputs

- Monitoring initialisation module and its unit tests.
- Sentry events (when enabled) containing exception type, sanitised message, stack, `request_id`, environment and release.

## Data Flow

Exception or `nightly_run_missing` → backend logging (ERROR) → if SDK initialised: `before_send` redacts fields and strips headers, cookies, query strings and bodies → event sent over HTTPS to Sentry → e-mail per new issue to the DevOps owner. Empty DSN → nothing leaves the process.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-081, FEAT-082, FEAT-018

- [FEAT-081](FEAT-081-Railway-Backend-And-Nightly-Cron-Services.md) Railway backend and nightly services (where SENTRY_DSN is set).
- [FEAT-082](FEAT-082-Netlify-Frontend-Configuration-Security-Headers-And.md) Netlify configuration (no frontend SDK; CSP has no Sentry origin).
- [FEAT-018](FEAT-018-Structured-JSON-Logging-Redaction-And-Request.md) Structured logging and redaction filters reused by `before_send`.

## Database Impact

None.

## API Impact

None. No endpoint changes; errors still return the RFC 7807 body of TRD 05.

## Frontend Impact

None (no browser SDK, CSP unchanged).

## Analytics Impact

None.

## Security Requirements

- `send_default_pii=False`, no request bodies, headers, cookies or query strings; redaction of secrets, connection URLs and bearer tokens (SEC-127, LOG-100).
- Interim stack only, synthetic data only (TPS-002, LOG-102); production disabled before AWS go-live unless approved (TPS-061).
- No new third-party service beyond TRD 22 §4.1 (TPS-001).

## Error Handling

- The TRDs do not define behaviour when Sentry is unreachable. Sentry is an optional "May" service (TPS-060), so the implementation relies on the SDK's asynchronous transport, which drops undeliverable events; no retry, queue or fallback channel is added. Request handling, the RFC 7807 error response and the ERROR log (LOG-070) are unchanged whatever happens to the event.
- Settings validation failures (any variable) follow LOG-072: exit code 1 and a CRITICAL log naming the variable, never its value.

## Logging Requirements

- The startup summary logs `sentry_enabled` as a boolean, never the DSN (TRD 21 §8).
- No audit rows.

## Testing Requirements

- Unit: with an empty DSN, patch the SDK transport and assert zero calls (LOG-101); with a dummy DSN and a captured transport, assert the event has no `request.data`, no headers, cookies or query string, and that a field `password` and a URL `postgresql://u:p@h/db` are `[REDACTED]` (LOG-100).
- Unit: `init_sentry` passes `traces_sample_rate=0`, `send_default_pii=False`, `max_request_body_size="never"`.

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-084-AC-01 | With `SENTRY_DSN` empty, a request raising an unhandled exception produces the ERROR log and zero calls to the Sentry transport. | LOG-101 |
| FEAT-084-AC-02 | With a test DSN and a captured transport, the captured event contains `environment`, `release` = GIT_SHA and the exception, and contains no request body, headers, cookies, query string, password or connection-URL credentials. | LOG-100, SEC-127 |
| FEAT-084-AC-03 | `grep -rn "@sentry" frontend/package.json` returns nothing. | TPS-060 |
| FEAT-084-AC-04 | `docs/deployment.md` states that SENTRY_DSN is empty in production before AWS go-live unless approved, and the TRD 21 §4.7 values for local and test are empty. | TPS-061, LOG-102 |

## Definition of Done

- All FEAT-084 acceptance criteria pass; `sentry-sdk` pinned with `==` (GIT-112).
- Backend coverage gate unaffected (≥ 85 %).
- Batch report entry (AGT-022).

## Implementation Notes

- Reuse the redaction functions of `backend/core/logging.py` inside `before_send`; do not duplicate patterns.
- Call `init_sentry` in the app lifespan and in `nightly_run` main, never at import time, so `export-openapi` and tests stay offline.
- Sentry's free plan has a small monthly quota and about 30 days of retention (TRD 22); keep events to errors only.
