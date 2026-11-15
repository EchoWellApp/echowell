# Audit log writer and action vocabulary

## Feature Description

FEAT-015 provides the single audit writer `backend/services/audit_service.py`: `record(session, *, action, actor_type, actor_id, entity_type, entity_id, details, ip, request_id)` inserts exactly one `audit_logs` row inside the caller's transaction (no commit), `record_committed()` writes the refused-request rows `auth.login.failed` and `access.denied` in their own committed transaction, and `record_cli()` stores CLI actions with `actor_type = 'system'` and `details.operator` = OS user name. `AuditAction` is the closed vocabulary of the 24 actions of TRD 12 §4.12; a details sanitiser rejects passwords, hashes, tokens, API keys, database URLs, bodies, note text and feature values. Each successful write emits one INFO `audit_event` log line without `details`. There is no audit read endpoint; `audit_logs` is append-only for `echowell_app`.

## Preconditions

- Local development stack running; `.env` from `.env.development.example` (`APP_ENV=local`, `LOG_FORMAT=json`, `PIPELINE_PROFILE=test_v0_1`, `SEED_*` set).
- Database seeded: `python -m backend.cli seed test_v0_1 --reset` (exit code 0).
- Bearer tokens for `admin@example.com`, `clinician@example.com` and `researcher@example.com` (passwords from the matching `SEED_*` variables).
- `psql` access as `echowell_app` (`DATABASE_URL`) and as `echowell_readonly` (`DATABASE_READONLY_URL`).
- Python 3.12 virtual environment with the backend requirements, run from the repository root.
- Backend log stream visible: `docker compose logs -f backend`.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-015-01 | All 24 TRD 12 §4.12 actions are accepted and each creates exactly one row | High | Database |
| TC-015-02 | Unlisted action `login` / `Auth.Login` is rejected before any SQL | High | Negative |
| TC-015-03 | Database CHECK `audit_logs_action_ck` rejects an unlisted action | Medium | Database |
| TC-015-04 | Change and audit row commit or roll back together | High | Database |
| TC-015-05 | Note creation over the API writes exactly one `note.created` row with the request ID | High | API |
| TC-015-06 | Forbidden detail keys and values are rejected and nothing is written | High | Security |
| TC-015-07 | Detail key not documented for the action is rejected | Medium | Negative |
| TC-015-08 | CLI action stores `actor_type = 'system'` and `details.operator` | High | Positive |
| TC-015-09 | Each audit write emits one INFO `audit_event` log line without `details` | High | Positive |
| TC-015-10 | Failed login row is committed separately and contains no password | High | Security |
| TC-015-11 | 403 writes one `access.denied` row; 401 writes none | High | Security |
| TC-015-12 | `audit_logs` is append-only (no UPDATE/DELETE for `echowell_app`) | High | Database |
| TC-015-13 | Inspection: writes only in the audit repository and service; no UPDATE/DELETE | High | Security |
| TC-015-14 | No endpoint returns audit rows; only `echowell_readonly` reads them | Medium | API |
| TC-015-15 | Committed-separately mode is refused for any other action | Medium | Negative |

### TC-015-01 All 24 TRD 12 §4.12 actions are accepted and each creates exactly one row

| Step | Action | Expected Result |
|---|---|---|
| 1 | In a Python REPL: `from backend.services.audit_service import AuditAction; print(len(AuditAction), sorted(a.value for a in AuditAction))` | `24` and exactly: `access.denied`, `alert.closed`, `alert.reviewed`, `alert.snoozed`, `api_key.created`, `api_key.revoked`, `auth.login.failed`, `auth.login.succeeded`, `auth.logout`, `config.changed`, `data_alert.resolved`, `export.csv`, `ingest.batch.received`, `note.created`, `pipeline.rebuild`, `pipeline.run.finished`, `pipeline.run.started`, `resident.cohort_changed`, `resident.purged`, `resident.withdrawn`, `roster.loaded`, `seed.reset`, `user.created`, `user.updated` |
| 2 | Run `pytest -m integration tests/integration/db/test_audit_writer.py -q` | All tests pass (each action inserted as `echowell_app` passes `audit_logs_action_ck`; one row per call) |

### TC-015-02 Unlisted action `login` / `Auth.Login` is rejected before any SQL

| Step | Action | Expected Result |
|---|---|---|
| 1 | In `psql` note `SELECT count(*) FROM audit_logs;` | Baseline count N |
| 2 | In the REPL, open a session on the app engine and call `audit_service.record(s, action="login", actor_type=ActorType.SYSTEM, actor_id=None, entity_type=None, entity_id=None)` | Raises `ValueError: unknown audit action 'login' (TRD 12 §4.12)`; no database error |
| 3 | Repeat with `action="Auth.Login"` | Same `ValueError` |
| 4 | Commit the REPL session; re-run the count | Still N |
| 5 | Run `pytest tests/unit/backend/services/test_audit.py -q` | All tests pass |

### TC-015-03 Database CHECK `audit_logs_action_ck` rejects an unlisted action

| Step | Action | Expected Result |
|---|---|---|
| 1 | In `psql` as `echowell_app`: `INSERT INTO audit_logs (actor_type, action, details) VALUES ('system', 'login', '{}'::jsonb);` | Fails with `new row for relation "audit_logs" violates check constraint "audit_logs_action_ck"`; no row inserted |

### TC-015-04 Change and audit row commit or roll back together

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `pytest -m integration tests/integration/db/test_audit_writer.py -q -k shares_the_change_transaction` | Test passes: a `staff_notes` row plus its `note.created` row in one transaction, rolled back, leaves zero rows in both tables; committed, leaves exactly one of each |
| 2 | Run the same file with `-k refused_request_rows_survive` | Test passes: `auth.login.failed` / `access.denied` rows written in their own transaction survive the request rollback |
| 3 | As a clinician, `POST /api/v1/residents/R01/notes` with body `{"note_type": "observation", "body": "QA synthetic note", "unknown": 1}` | 422 `VALIDATION_ERROR`; `SELECT count(*) FROM audit_logs WHERE action = 'note.created';` unchanged |

### TC-015-05 Note creation over the API writes exactly one `note.created` row with the request ID

| Step | Action | Expected Result |
|---|---|---|
| 1 | As a clinician, `POST /api/v1/residents/R01/notes` with header `X-Request-ID: qa-audit-note-0001` and body `{"note_type": "observation", "body": "QA synthetic note"}` | 201; response header `X-Request-ID: qa-audit-note-0001` |
| 2 | `SELECT actor_type, action, entity_type, details, request_id, ip FROM audit_logs WHERE request_id = 'qa-audit-note-0001';` | Exactly 1 row: `actor_type` `user`, `action` `note.created`, `entity_type` `staff_note`, `details` has keys `resident_code` (`R01`), `note_type` (`observation`), `alert_id` (null), `supersedes_id` (null); `details` does not contain `QA synthetic note`; `ip` is a valid `inet` |
| 3 | `SELECT occurred_at FROM audit_logs WHERE request_id = 'qa-audit-note-0001';` | UTC timestamp within a few seconds of the request |

### TC-015-06 Forbidden detail keys and values are rejected and nothing is written

| Step | Action | Expected Result |
|---|---|---|
| 1 | In the REPL call `record(s, action="config.changed", actor_type=ActorType.SYSTEM, actor_id=None, entity_type="config", entity_id="x", details={"password": "x"})` | Raises `AuditDetailsError` (a `ValueError`); no row written |
| 2 | Repeat with `details={"loudness_dbfs": -30.1}` | Raises `AuditDetailsError`; no row written |
| 3 | Repeat with `details={"old": {"token": "x"}}` and with `details={"old": "postgresql://u:p@h/db"}` | Both raise `AuditDetailsError` (nested key and secret-looking value) |
| 4 | Count rows before and after steps 1–3 | Unchanged |

### TC-015-07 Detail key not documented for the action is rejected

| Step | Action | Expected Result |
|---|---|---|
| 1 | Call `record(s, action="auth.logout", actor_type=ActorType.SYSTEM, actor_id=None, entity_type="user", entity_id=None, details={"reason": "x"})` | Raises `AuditDetailsError` with message naming `['reason']` as not documented for `auth.logout` |
| 2 | Call `record(..., action="auth.login.failed", details={"email": "nobody@example.com", "reason": "invalid_credentials"})` | Succeeds; returns an integer id |

### TC-015-08 CLI action stores `actor_type = 'system'` and `details.operator`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `whoami` in the shell that runs the CLI | Prints the OS user name U |
| 2 | Run `python -m backend.cli create-api-key --name qa-audit-key` | Exit code 0; one key printed on stdout |
| 3 | `SELECT actor_type, actor_id, details FROM audit_logs WHERE action = 'api_key.created' AND details->>'name' = 'qa-audit-key';` | 1 row; `actor_type` `system`; `actor_id` NULL; `details.operator` = U; `details.device_code` null; no key value in `details` |
| 4 | Run `python -m backend.cli revoke-api-key --name qa-audit-key` | Exit code 0; one `api_key.revoked` row with `actor_type` `system` and `details.operator` = U |

### TC-015-09 Each audit write emits one INFO `audit_event` log line without `details`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Watch `docker compose logs -f backend`; log in as `admin@example.com` | Exactly one JSON line with `"event": "audit_event"`, `"level": "INFO"`, `"action": "auth.login.succeeded"`, `"entity_type": "user"` and an `entity_id`; the line has no `details` key and no e-mail address |
| 2 | Log out (`POST /api/v1/auth/logout`) | Exactly one `audit_event` line with `"action": "auth.logout"` |
| 3 | Run `pytest tests/unit/backend/services/test_audit.py -q -k one_info_record_without_details` | Test passes (uses `caplog`) |

### TC-015-10 Failed login row is committed separately and contains no password

| Step | Action | Expected Result |
|---|---|---|
| 1 | `POST /api/v1/auth/login` with `{"email": "Clinician@Example.com", "password": "wrong-password-qa-1"}` | 401 `INVALID_CREDENTIALS` |
| 2 | `SELECT actor_type, actor_id, details FROM audit_logs WHERE action = 'auth.login.failed' ORDER BY id DESC LIMIT 1;` | `actor_type` `system`; `actor_id` NULL; `details` = `{"email": "clinician@example.com", "reason": "invalid_credentials"}`; the attempted password appears nowhere in the row |

### TC-015-11 403 writes one `access.denied` row; 401 writes none

| Step | Action | Expected Result |
|---|---|---|
| 1 | Count `SELECT count(*) FROM audit_logs WHERE action = 'access.denied';` | Baseline M |
| 2 | As the researcher, `POST /api/v1/residents/R01/notes` with a valid body | 403 `FORBIDDEN` |
| 3 | Re-count; read the newest `access.denied` row | M + 1; `actor_type` `user`; `details` = `{"status": 403, "code": "FORBIDDEN"}` |
| 4 | Call `GET /api/v1/residents` without any token | 401 `NOT_AUTHENTICATED`; `access.denied` count still M + 1 |

Note: TRD 12 §4.12 and FEAT-015-FR-06 require `entity_type = 'route'` and `entity_id` = route template; `backend/api/deps.py:196` writes `entity_type=None, entity_id=None`. Record `entity_type`/`entity_id` against the TRD.

### TC-015-12 `audit_logs` is append-only (no UPDATE/DELETE for `echowell_app`)

| Step | Action | Expected Result |
|---|---|---|
| 1 | In `psql` as `echowell_app`: `UPDATE audit_logs SET action = 'auth.logout' WHERE id = (SELECT max(id) FROM audit_logs);` | Fails with `permission denied for table audit_logs` |
| 2 | `DELETE FROM audit_logs WHERE id = (SELECT max(id) FROM audit_logs);` | Fails with `permission denied for table audit_logs` |
| 3 | As `echowell_migrator` without `echowell.allow_purge`: `UPDATE audit_logs SET action = 'auth.logout' WHERE id = 1;` | Fails with `table audit_logs is append-only: UPDATE is not allowed` |

### TC-015-13 Inspection: writes only in the audit repository and service; no UPDATE/DELETE

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `grep -rn "audit_logs" backend --include=*.py` | Matches only in `backend/services/audit_service.py` (docstring), `backend/models/audit_log.py` (table and index declarations), `backend/repositories/audit_repository.py` and `backend/alembic/versions/*` (schema); no router or other service writes the table |
| 2 | Run `grep -rniE "update\(AuditLog|delete\(AuditLog|UPDATE audit_logs|DELETE FROM audit_logs" backend --include=*.py` | No output |

### TC-015-14 No endpoint returns audit rows; only `echowell_readonly` reads them

| Step | Action | Expected Result |
|---|---|---|
| 1 | As admin, `GET /api/v1/audit-logs` | 404 `NOT_FOUND` Problem body |
| 2 | `GET /api/v1/openapi.json` and search the `paths` keys for `audit` | No path contains `audit` |
| 3 | In `psql` as `echowell_readonly`: `SELECT count(*) FROM audit_logs;` | Returns a count (SELECT permitted) |
| 4 | As `echowell_readonly`: `INSERT INTO audit_logs (actor_type, action, details) VALUES ('system','auth.logout','{}');` | Fails with `permission denied` (read-only) |

### TC-015-15 Committed-separately mode is refused for any other action

| Step | Action | Expected Result |
|---|---|---|
| 1 | In the REPL call `audit_service.record_committed(engine, action="note.created", actor_type=ActorType.USER, actor_id="x", entity_type="staff_note", entity_id="x", details={})` | Raises `ValueError: record_committed() is only for auth.login.failed and access.denied`; no row written |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `POST /api/v1/auth/login` (valid admin) | 200; one `auth.login.succeeded` row with the request's `X-Request-ID` in `request_id` |
| 2 | `POST /api/v1/auth/logout` | 204; one `auth.logout` row |
| 3 | `POST /api/v1/residents/R01/notes` (clinician) | 201; one `note.created` row (TC-015-05) |
| 4 | `POST /api/v1/residents/R01/notes` (researcher) | 403 `FORBIDDEN`; one `access.denied` row (TC-015-11) |
| 5 | Any audit read path (`GET /api/v1/audit-logs`) | 404 `NOT_FOUND` |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT DISTINCT action FROM audit_logs ORDER BY 1;` after seed, login, logout, note, 403 | Every value is one of the 24 actions of TRD 12 §4.12 |
| 2 | `SELECT count(*) FROM audit_logs WHERE details::text ~* '(password|token|ewk_|argon2|postgresql://)';` | 0 |
| 3 | `SELECT count(*) FROM audit_logs WHERE actor_id IS NULL AND actor_type <> 'system';` | 0 (`audit_logs_actor_ck`) |
| 4 | `SELECT request_id FROM audit_logs WHERE action = 'note.created' ORDER BY id DESC LIMIT 1;` | Equals the `X-Request-ID` of the note request |
| 5 | `SELECT count(*) FROM audit_logs WHERE occurred_at IS NULL;` | 0 |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | `record(..., action="login")` | `ValueError` before SQL; no row (TC-015-02) |
| 2 | Direct INSERT with action `login` | Check-constraint violation `audit_logs_action_ck` (TC-015-03) |
| 3 | `details={"password": "x"}` or `{"loudness_dbfs": -30.1}` | `AuditDetailsError`; no row (TC-015-06) |
| 4 | Undocumented detail key | `AuditDetailsError` (TC-015-07) |
| 5 | Request rolled back by a 422 | No audit row for the rejected change (TC-015-04) |
| 6 | UPDATE / DELETE on `audit_logs` as `echowell_app` | `permission denied for table audit_logs` (TC-015-12) |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-015-AC-01 | Each of the 24 actions inserted through `record` as `echowell_app` succeeds with exactly one row each | TC-015-01 |
| FEAT-015-AC-02 | Action `login` raises before any SQL; no row and no database error | TC-015-02 |
| FEAT-015-AC-03 | Rollback leaves zero `staff_notes` and `note.created` rows; commit leaves exactly one of each | TC-015-04, TC-015-05 |
| FEAT-015-AC-04 | `{"password": "x"}` and `{"loudness_dbfs": -30.1}` raise and write nothing | TC-015-06 |
| FEAT-015-AC-05 | CLI-originated row has `actor_type` `system` and `details.operator` = OS user name | TC-015-08 |
| FEAT-015-AC-06 | Exactly one INFO `audit_event` record per call with `action`, `entity_type`, `entity_id`, no `details` | TC-015-09 |
| FEAT-015-AC-07 | grep shows writes only in `audit_repository.py` / `audit_service.py`; no UPDATE/DELETE on `audit_logs` | TC-015-13, TC-015-12 |

## Test Data Requirements

- `test_v0_1` seed (users `admin@example.com`, `clinician@example.com`, `researcher@example.com`; resident R01).
- Synthetic note text "QA synthetic note"; synthetic request IDs `qa-audit-note-0001`; synthetic wrong password `wrong-password-qa-1` (not a credential).
- Synthetic API key name `qa-audit-key` (created and revoked within TC-015-08).
- Environment: `DATABASE_URL`, `DATABASE_READONLY_URL`, `DATABASE_MIGRATION_URL`, `LOG_FORMAT=json`, `SEED_*` (values never written down).

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-015-FR-01 / SEC-100 / FR-251 | FEAT-015 | TC-015-01, TC-015-05 |
| FEAT-015-FR-02 / SEC-101 / DB-011 / LOG-090 / D-87 | FEAT-015 | TC-015-04, TC-015-10, TC-015-15 |
| FEAT-015-FR-03 / SEC-109 / PGS-044 | FEAT-015 | TC-015-01, TC-015-02, TC-015-03 |
| FEAT-015-FR-04 / SEC-104 | FEAT-015 | TC-015-06, TC-015-07, TC-015-10 |
| FEAT-015-FR-05 / SEC-103 | FEAT-015 | TC-015-08 |
| FEAT-015-FR-06 / SEC-108 | FEAT-015 | TC-015-11 |
| FEAT-015-FR-07 / LOG-092 | FEAT-015 | TC-015-09 |
| FEAT-015-FR-08 / LOG-091 / SEC-106 | FEAT-015 | TC-015-12 |
| FEAT-015-FR-09 / SEC-102 / FR-252 | FEAT-015 | TC-015-12, TC-015-13 |
| FEAT-015-FR-10 / FR-250 | FEAT-015 | TC-015-01, API Validation 1–4 |
| FEAT-015-FR-11 / SEC-105 | FEAT-015 | TC-015-14 |
| FEAT-015-FR-12 / ARC-103 | FEAT-015 | TC-015-01, TC-015-13 |
| LOG-033 (request ID in audit rows) | FEAT-015, FEAT-018 | TC-015-05 |
| TST-053 (audit rows for login, failed login, logout) | FEAT-015, FEAT-020 | TC-015-09, TC-015-10 |
