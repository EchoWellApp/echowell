# FEAT-015 Audit log writer and action vocabulary

| Field | Value |
|---|---|
| Epic | Authentication & Security |
| Build phase | Phase 4 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-012, FEAT-013 |
| Status | Not Started |

## Purpose

Provide the single audit writer, `backend/services/audit.py` (`audit_service`), that every endpoint and CLI command calls to record a security- or research-relevant action: exactly one `audit_logs` row, written in the same transaction as the change, with actor, action from the fixed TRD 12 §4.12 vocabulary, entity, sanitised details, client IP and request ID, plus one paired INFO `audit_event` log line. Centralising it guarantees the vocabulary, the no-secrets rule and the transactional guarantee are enforced in one place.

## Business Context

- BR-16: an append-only audit trail of logins, logouts, failed logins, ingest batches, notes, reviews, snoozes, pipeline runs, configuration and user changes (FR-250..FR-252).
- Research integrity: every human action on alarms and every configuration change is traceable to an actor and request (SEC-100, SEC-103).

## Referenced TRDs

- TRD 12 SEC-100..SEC-109; §4.12 audit action table (single vocabulary).
- TRD 17 LOG-090..LOG-092.
- TRD 06 DB-011.
- TRD 20 PGS-044 (`audit_logs_action_ck`), §4.6.23.
- TRD 23 §4.2.23, §4.5 (`audit_logs.details` shape).
- TRD 02 FR-250..FR-252.

## Scope

- `backend/services/audit.py` with:
  - `AuditAction` — a closed enumeration of exactly the 24 actions of TRD 12 §4.12: `auth.login.succeeded`, `auth.login.failed`, `auth.logout`, `ingest.batch.received`, `note.created`, `alert.reviewed`, `alert.snoozed`, `export.csv`, `pipeline.run.started`, `pipeline.run.finished`, `config.changed`, `user.created`, `user.updated`, `api_key.created`, `api_key.revoked`, `access.denied`, `alert.closed`, `data_alert.resolved`, `resident.cohort_changed`, `resident.withdrawn`, `resident.purged`, `roster.loaded`, `seed.reset`, `pipeline.rebuild`.
  - `record(session, *, action, actor_type, actor_id, entity_type, entity_id, details, ip=None, request_id=None)` inserting one row through the audit repository (FEAT-012) without committing, so it joins the caller's transaction.
  - A details sanitiser that rejects (raises) any key or value that is a password, password hash, token, API key, database URL, ingest request body or feature value, and permits only the documented detail keys per action.
  - A helper building the CLI actor: `actor_type='system'`, `details.operator` = OS user name running the CLI.
  - After a successful insert, one INFO log record `audit_event` with `action`, `entity_type`, `entity_id` (no `details`).
- Unit and integration tests for the vocabulary, sanitiser and transaction behaviour.

## Out of Scope

- Calling the writer for each specific event: each endpoint or CLI feature records its own events (FEAT-016, FEAT-017, FEAT-020, FEAT-021, FEAT-025, FEAT-026, FEAT-031, FEAT-033, FEAT-034, FEAT-037, FEAT-053, FEAT-055).
- An audit-log read API (none exists in the MVP, SEC-105).
- Application logging configuration and redaction filters (FEAT-018).
- Request-ID generation (FEAT-018); the writer receives the request ID as a parameter.

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-015-FR-01 | Each audited event shall write exactly one `audit_logs` row with `occurred_at` (UTC, database default), `actor_type`, `actor_id`, `action`, `entity_type`, `entity_id`, `details`, `ip`, `request_id`. | SEC-100, FR-251 |
| FEAT-015-FR-02 | The audit row shall be inserted in the same database transaction as the change it records; a rolled-back change leaves no audit row, and a failed audit insert fails the action. The writer shall also offer a committed-separately mode used only for refused-request rows that accompany no change (`auth.login.failed`, `access.denied`; TRD 12 SEC-101, TRD 24 D-87). | SEC-101, DB-011, LOG-090 |
| FEAT-015-FR-03 | `action` shall be one of the 24 values of TRD 12 §4.12; the writer shall reject an unlisted action before the insert, and every listed action shall pass `audit_logs_action_ck`. | SEC-109, PGS-044 |
| FEAT-015-FR-04 | `details` shall never contain passwords, password hashes, tokens, API keys, `DATABASE_URL`, ingest request bodies or feature values; note bodies and review note text are never included. | SEC-104, FR-251, TRD 12 §4.12 |
| FEAT-015-FR-05 | CLI actions (create-user, create-api-key, revoke-api-key, set-config, rebuild and the other system actions of §4.12 run from the CLI) shall be recorded with `actor_type = 'system'` and `details.operator` = the OS user name. | SEC-103 |
| FEAT-015-FR-06 | The writer shall support the 403 `access.denied` row with `entity_type = 'route'`, `entity_id` = route template, `details` `{"status": 403, "code"}`; 401 responses are not audited. | SEC-108 |
| FEAT-015-FR-07 | Each successful audit write shall emit one INFO application log `audit_event` with `action`, `entity_type`, `entity_id` and no `details`. | LOG-092 |
| FEAT-015-FR-08 | Application logs shall not serve as the audit trail; audit rows are never deleted or rotated by log retention. | LOG-091, SEC-106 |
| FEAT-015-FR-09 | The writer shall only INSERT; no code path updates or deletes `audit_logs` (append-only for `echowell_app`). | SEC-102, FR-252 |
| FEAT-015-FR-10 | The events of FR-250 (login, logout, failed login, ingest batch, note created, review saved, alarm snoozed, pipeline run, config change, user change) shall be expressible with the vocabulary and detail shapes of TRD 12 §4.12. | FR-250 |
| FEAT-015-FR-11 | Audit logs shall be readable only through the `echowell_readonly` database role; no endpoint returns them. | SEC-105 |

## Inputs

- Caller-supplied SQLAlchemy session (open transaction), action, actor, entity, details, IP and request ID.

## Outputs

- One `audit_logs` row per call; one `audit_event` INFO log record.

## Data Flow

Endpoint or CLI performs its change inside a transaction → calls `audit_service.record(session, …)` → the sanitiser validates action and details → the audit repository inserts the row → the caller commits (both persist) or rolls back (neither persists) → after insert the service logs `audit_event`.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-012, FEAT-013

- FEAT-012 provides the `audit_logs` table, its CHECK, triggers and grants, and the audit insert repository.
- FEAT-013 provides the session factory used in the transaction tests.

Features that build directly on this one: FEAT-016, FEAT-025, and every feature that records an audited action.

## Database Impact

- Table used: `audit_logs` (INSERT only).
- Tables created or modified: none.

## API Impact

None exposed (SEC-105). Every mutating endpoint and `/auth/logout` will call the writer (TRD 23 §4.6 "written by all mutating endpoints and `/auth/logout`").

## Frontend Impact

None.

## Analytics Impact

None.

## Security Requirements

- Append-only writes; no update/delete code path (SEC-102).
- Details sanitised against secrets and feature values (SEC-104).
- `ip` stored as `inet`; `request_id` correlates audit rows with application logs (SEC-100).
- No audit read endpoint (SEC-105).

## Error Handling

| Failure | Behaviour | Trace |
|---|---|---|
| Unlisted action | `ValueError` raised before any SQL; caller's transaction is rolled back by its error handling | SEC-109 |
| Forbidden detail key/value | `ValueError` raised; the action fails | SEC-104 |
| Insert fails (database error) | Exception propagates; the caller's change rolls back with it | LOG-090, SEC-101 |

## Logging Requirements

- INFO `audit_event` with `action`, `entity_type`, `entity_id` per audit write (LOG-092).
- No `details` in the log line; no secrets (SEC-107).
- Audit rows themselves are the audit record (LOG-091).

## Testing Requirements

- Unit (`tests/unit/backend/services/test_audit.py`): every one of the 24 actions accepted; `login` and `Auth.Login` rejected before insert (SEC-109); details containing keys `password`, `token`, `api_key`, `key_hash`, `password_hash`, `database_url`, or a feature name such as `loudness_dbfs` rejected (SEC-104); CLI actor sets `actor_type = 'system'` and `details.operator` (SEC-103); `audit_event` log line emitted without `details` (LOG-092, using `caplog`).
- Integration (`tests/integration/db/test_audit_writer.py`): each listed action inserted as `echowell_app` passes `audit_logs_action_ck` (SEC-109); DB-011 forced-rollback test (change plus audit row in one transaction, rollback leaves neither); committed change has exactly one audit row (SEC-100, SEC-101).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-015-AC-01 | Inserting each of the 24 TRD 12 §4.12 actions through `audit_service.record` as `echowell_app_login` succeeds and creates exactly one row each. | SEC-109, SEC-100 |
| FEAT-015-AC-02 | Calling `record` with action `login` raises before any SQL is sent (no row, no database error). | SEC-109 |
| FEAT-015-AC-03 | In one transaction, inserting a `staff_notes` row and its `note.created` audit row then rolling back leaves zero rows in both tables; committing leaves exactly one of each. | DB-011, SEC-101, LOG-090 |
| FEAT-015-AC-04 | `record` with details `{"password": "x"}` or `{"loudness_dbfs": -30.1}` raises and writes nothing. | SEC-104 |
| FEAT-015-AC-05 | A CLI-originated call stores `actor_type = 'system'` and `details.operator` equal to the OS user name. | SEC-103 |
| FEAT-015-AC-06 | Each successful call emits exactly one INFO record with message/event `audit_event` and fields `action`, `entity_type`, `entity_id`, and no `details` field. | LOG-092 |
| FEAT-015-AC-07 | `grep -rn "audit_logs" backend --include=*.py` shows writes only in the audit repository and `backend/services/audit.py`, and no UPDATE/DELETE statement on `audit_logs`. | SEC-102, FR-252 |

## Definition of Done

- All FEAT-015 acceptance criteria pass; the vocabulary in code equals TRD 12 §4.12 exactly (a unit test compares the enum to the TRD list).
- Docstrings cite SEC-100..SEC-109; delivered in the Phase 4 PR.

## Implementation Notes

- Keep `record()` free of `commit()`; transactional ownership stays with the caller (`get_db()` commits at the end of a request, CLI commands commit explicitly).
- `auth.login.failed` uses `actor_type = 'system'` with the user id or NULL (TRD 12 §4.12); `audit_logs_actor_ck` allows NULL `actor_id` only for `system`.
- The `ip` value is the client address as resolved by uvicorn `--proxy-headers` (API-001); pass it in from the request layer (CLI calls pass NULL).
- The paired `audit_event` log line is formatted by FEAT-018 once structured logging is configured; use the standard `logging` module with `extra` fields now.
