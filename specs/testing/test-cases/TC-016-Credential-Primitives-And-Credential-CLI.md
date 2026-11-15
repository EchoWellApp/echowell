# Credential primitives and credential CLI (argon2id, API keys, create-user, create-api-key, revoke-api-key)

## Feature Description

FEAT-016 implements the credential building blocks in `backend/core/security.py` — argon2id password hashing (`time_cost=3`, `memory_cost=65536`, `parallelism=4`, `hash_len=32`, `salt_len=16`) with rehash detection, the password policy (12..128 characters, not the e-mail, not in `backend/core/common_passwords.txt`, no composition rules, violation `PASSWORD_POLICY_VIOLATION`), e-mail normalisation (trim, lower-case), API key generation (`ewk_` + `secrets.token_urlsafe(32)`) and SHA-256 hashing — and the operator commands `python -m backend.cli create-user`, `create-api-key` and `revoke-api-key`. Each command writes its change and one audit row (`user.created`, `api_key.created`, `api_key.revoked`, `actor_type = system`, `details.operator`) in one transaction; refused input exits with code 2 and writes nothing; invalid settings exit with code 1. There is no HTTP endpoint for API keys.

## Preconditions

- Local development stack running; `.env` from `.env.development.example` (`APP_ENV=local`, `PIPELINE_PROFILE=test_v0_1`, `SEED_*` set).
- Database seeded with the master data: `python -m backend.cli seed test_v0_1 --reset --master-only` (exit code 0; devices D01–D10 and D07B exist).
- CLI commands run from the repository root (or `docker compose exec backend python -m backend.cli …`); exit code read with `echo $?`.
- `psql` access to the local database (read-only `SELECT`).
- Any password used below is chosen locally by the tester, typed at the prompt or piped on stdin, and never written into a ticket or this document.

## Manual Test Cases

| Test Case ID | Test Scenario | Priority | Type |
|---|---|---|---|
| TC-016-01 | `hash_password` produces an argon2id PHC string with the SEC-010 parameters; verify accepts only the plaintext | High | Positive |
| TC-016-02 | `needs_rehash` is true for a hash with other parameters | Medium | Positive |
| TC-016-03 | Password policy boundaries: 11 and 129 rejected, 12 accepted, e-mail and common password rejected | High | Negative |
| TC-016-04 | E-mail normalisation trims and lower-cases | Medium | Positive |
| TC-016-05 | API key format and SHA-256 hash | High | Positive |
| TC-016-06 | `create-api-key --name t1` prints one key, stores scope `ingest:write` and only the hash | High | Database |
| TC-016-07 | `create-api-key` with two scopes and `--device D01` | High | Database |
| TC-016-08 | Invalid scope, unknown device and duplicate active name are refused with exit code 2 | High | Negative |
| TC-016-09 | `revoke-api-key --name t1` deactivates the key and writes `api_key.revoked` | High | Database |
| TC-016-10 | `revoke-api-key` with an unknown name exits 2 | Medium | Negative |
| TC-016-11 | `create-user --password-stdin` stores the normalised e-mail, an argon2id hash and one `user.created` row | High | Database |
| TC-016-12 | `create-user` refusals: policy violation, duplicate e-mail, invalid role | High | Negative |
| TC-016-13 | A revoked key is rejected by ingest; a new key works | Medium | API |
| TC-016-14 | No HTTP route for API keys | High | API |
| TC-016-15 | No password or key appears in output, logs or audit rows | High | Security |
| TC-016-16 | Invalid settings make a credential command exit 1 | Medium | Negative |

### TC-016-01 `hash_password` produces an argon2id PHC string with the SEC-010 parameters; verify accepts only the plaintext

| Step | Action | Expected Result |
|---|---|---|
| 1 | In a Python REPL: `from backend.core.security import hash_password, verify_password; h = hash_password(p)` with `p` = the sample phrase of FEAT-016-AC-01 | `h` starts with `$argon2id$v=19$m=65536,t=3,p=4$` |
| 2 | Call `hash_password(p)` again | Different string (random 16-byte salt) |
| 3 | `verify_password(p, h)` | `True` |
| 4 | `verify_password(p + "x", h)` and `verify_password(p, "not-a-hash")` | Both `False`; no exception |
| 5 | Run `pytest tests/unit/backend/core/test_security.py -q` | All tests pass (TST-032) |

### TC-016-02 `needs_rehash` is true for a hash with other parameters

| Step | Action | Expected Result |
|---|---|---|
| 1 | In the REPL: `from argon2 import PasswordHasher; old = PasswordHasher(time_cost=2, memory_cost=32768, parallelism=2).hash(p)` | Hash starts with `$argon2id$v=19$m=32768,t=2,p=2$` |
| 2 | `needs_rehash(old)` and `needs_rehash(hash_password(p))` | `True` and `False` |

### TC-016-03 Password policy boundaries: 11 and 129 rejected, 12 accepted, e-mail and common password rejected

| Step | Action | Expected Result |
|---|---|---|
| 1 | `validate_password("a" * 5 + "b" * 6, "qa@example.com")` (11 characters) | Raises `PasswordPolicyError` (code `PASSWORD_POLICY_VIOLATION`) with detail `password must be 12 to 128 characters` |
| 2 | `validate_password("ab" * 64 + "c", "qa@example.com")` (129 characters) | Same error and detail |
| 3 | A 12-character string not in the list, e.g. `"qx" * 6` | Returns `None` (accepted) |
| 4 | `validate_password("QA.LONGUSER@EXAMPLE.COM", "qa.longuser@example.com")` | Raises with detail `password must not be the e-mail address` |
| 5 | Take one entry of length ≥ 12 from the list (`grep -v '^#' backend/core/common_passwords.txt \| awk 'length>=12' \| head -1`) and validate it | Raises with detail `password is in the list of common passwords` |
| 6 | Validate a 12-character string of one repeated lower-case letter that is not in the list | Accepted (no composition rules) |

### TC-016-04 E-mail normalisation trims and lower-cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | `normalise_email("  Admin@Example.COM ")` | `"admin@example.com"` |

### TC-016-05 API key format and SHA-256 hash

| Step | Action | Expected Result |
|---|---|---|
| 1 | `from backend.core.security import generate_api_key, hash_api_key; k = generate_api_key()` | `k` matches `^ewk_[A-Za-z0-9_-]{43}$` (47 characters) |
| 2 | Generate 3 keys | All different |
| 3 | `hash_api_key(k)` | 64 lower-case hex characters; equals `hashlib.sha256(k.encode()).hexdigest()` |

### TC-016-06 `create-api-key --name t1` prints one key, stores scope `ingest:write` and only the hash

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `python -m backend.cli create-api-key --name t1 > key.txt` | Exit code 0; stderr `New API key (shown only once; store it in the device's secret store):`; `key.txt` has exactly one line matching `^ewk_[A-Za-z0-9_-]{43}$` |
| 2 | `SELECT name, scopes, device_id, active, key_hash FROM api_keys WHERE name = 't1';` | 1 row; `scopes` `{ingest:write}`; `device_id` NULL; `active` `true`; `key_hash` = SHA-256 hex of the line in `key.txt` (compute with `sha256sum` on the key without newline) |
| 3 | `SELECT count(*) FROM api_keys WHERE key_hash LIKE 'ewk_%';` | 0 (plaintext never stored) |
| 4 | `SELECT actor_type, details FROM audit_logs WHERE action = 'api_key.created' AND details->>'name' = 't1';` | 1 row; `actor_type` `system`; `details` keys `name`, `device_code` (null), `operator`; no `ewk_` text |
| 5 | Delete `key.txt` after the test | File removed |

### TC-016-07 `create-api-key` with two scopes and `--device D01`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `python -m backend.cli create-api-key --name t2 --scope pipeline:run --scope ingest:write --device D01` | Exit code 0; one key printed |
| 2 | `SELECT k.scopes, d.device_code FROM api_keys k JOIN devices d ON d.id = k.device_id WHERE k.name = 't2';` | `scopes` contains both `ingest:write` and `pipeline:run`; `device_code` `D01` |
| 3 | Audit row for `t2` | `api_key.created` with `details.device_code` `D01` and `details.operator` |

### TC-016-08 Invalid scope, unknown device and duplicate active name are refused with exit code 2

| Step | Action | Expected Result |
|---|---|---|
| 1 | Count rows: `SELECT count(*) FROM api_keys;` and `SELECT count(*) FROM audit_logs;` | Baselines K and A |
| 2 | Run `python -m backend.cli create-api-key --name t3 --scope admin` | Exit code 2; stderr `Refused: unknown scope admin (allowed: ingest:write, pipeline:run)`; nothing printed on stdout |
| 3 | Run `python -m backend.cli create-api-key --name t4 --device D99` | Exit code 2; stderr `Refused: unknown device D99` |
| 4 | Run `python -m backend.cli create-api-key --name t2` (t2 is active) | Exit code 2; stderr `Refused: an active API key named t2 already exists` |
| 5 | Re-count | Still K and A |

### TC-016-09 `revoke-api-key --name t1` deactivates the key and writes `api_key.revoked`

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `python -m backend.cli revoke-api-key --name t1` | Exit code 0; stderr `Revoked API key t1.` |
| 2 | `SELECT active FROM api_keys WHERE name = 't1';` | `false` (row kept) |
| 3 | `SELECT actor_type, details FROM audit_logs WHERE action = 'api_key.revoked' AND details->>'name' = 't1';` | Exactly 1 row; `actor_type` `system`; `details.operator` = output of `whoami` |

### TC-016-10 `revoke-api-key` with an unknown name exits 2

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `python -m backend.cli revoke-api-key --name no-such-key` | Exit code 2; stderr `Refused: no active API key named no-such-key`; no audit row added |
| 2 | Run `python -m backend.cli revoke-api-key --name t1` again (already revoked) | Exit code 2; same message pattern |

### TC-016-11 `create-user --password-stdin` stores the normalised e-mail, an argon2id hash and one `user.created` row

| Step | Action | Expected Result |
|---|---|---|
| 1 | Pipe a locally chosen valid password into `python -m backend.cli create-user --email QA.Admin@Example.com --display-name "QA Admin" --role admin --password-stdin` | Exit code 0; stderr `Created user qa.admin@example.com (admin).` |
| 2 | `SELECT email, role, active, left(password_hash, 31) FROM users WHERE email = 'qa.admin@example.com';` | 1 row; `role` `admin`; `active` `true`; hash prefix `$argon2id$v=19$m=65536,t=3,p=4$` |
| 3 | `SELECT actor_type, details FROM audit_logs WHERE action = 'user.created' ORDER BY id DESC LIMIT 1;` | `actor_type` `system`; `details` = `{"role": "admin", "operator": "<whoami>"}` |
| 4 | Log in at `POST /api/v1/auth/login` with `qa.admin@example.com` and the chosen password | 200 with `token_type` `bearer` and `user.role` `admin` |
| 5 | Run the command without `--password-stdin` in a terminal | Prompt `Password: ` appears and input is not echoed |

### TC-016-12 `create-user` refusals: policy violation, duplicate e-mail, invalid role

| Step | Action | Expected Result |
|---|---|---|
| 1 | Pipe an 11-character password into `create-user --email qa.short@example.com --display-name "QA Short" --role clinician --password-stdin` | Exit code 2; stderr `Refused: password must be 12 to 128 characters`; no `users` row for `qa.short@example.com` |
| 2 | Repeat step 1 of TC-016-11 (same e-mail, any case) with a valid password | Exit code 2; stderr `Refused: a user with e-mail qa.admin@example.com already exists`; user count unchanged |
| 3 | Run `create-user --email qa.role@example.com --display-name "QA Role" --role superuser --password-stdin` | Exit code 2; argparse message `invalid choice: 'superuser' (choose from 'admin', 'clinician', 'researcher')` |
| 4 | Run `create-user --email qa.arg@example.com --display-name X --role admin --password anything` | Exit code 2; argparse `unrecognized arguments` (passwords are never accepted as arguments) |
| 5 | Pipe a valid password into `create-user --email not-an-email --display-name "QA Bad" --role clinician --password-stdin` | Exit code 2; stderr starts with `Refused:` and names `users_email_format_ck`; no `users` row added (TST-195) |
| 6 | Count `audit_logs` rows with `action = 'user.created'` before and after steps 1–5 | Unchanged |

### TC-016-13 A revoked key is rejected by ingest; a new key works

| Step | Action | Expected Result |
|---|---|---|
| 1 | `POST /api/v1/sessions` with header `X-API-Key: <t1 key from TC-016-06>` and any JSON body | 401 `API_KEY_INVALID` (key revoked in TC-016-09) |
| 2 | Same call with the `t2` key and a valid synthetic D01 record of R01 | Not 401 (key accepted; outcome decided by validation) |

### TC-016-14 No HTTP route for API keys

| Step | Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/openapi.json`; list the `paths` keys | No path contains `api-key`, `api_key` or `apikeys` |
| 2 | Run `grep -rn "api_keys\|ApiKeyRepository(.*).insert\|generate_api_key" backend/api` | No route creates or lists API keys (any match is only the authentication dependency reading keys) |
| 3 | As admin, `POST /api/v1/api-keys` with `{}` | 404 `NOT_FOUND` |

### TC-016-15 No password or key appears in output, logs or audit rows

| Step | Action | Expected Result |
|---|---|---|
| 1 | After TC-016-06..TC-016-12, search `docker compose logs backend` and the CLI stderr for `ewk_` and for the chosen passwords | 0 matches (the key appears only on the stdout of `create-api-key`) |
| 2 | `SELECT count(*) FROM audit_logs WHERE details::text ~ '(ewk_|argon2)';` | 0 |
| 3 | Run `pytest -m integration tests/integration/test_cli_credentials.py -q` | All tests pass |

### TC-016-16 Invalid settings make a credential command exit 1

| Step | Action | Expected Result |
|---|---|---|
| 1 | Run `APP_ENV=staging DATABASE_URL=postgresql+psycopg://u:p@db.example.org/x python -m backend.cli revoke-api-key --name t2` (no `sslmode`, other staging settings missing) | Exit code 1; CRITICAL `startup_config_invalid` log line; no secret value printed; nothing written |

## API Validation

| Step | API Action | Expected Result |
|---|---|---|
| 1 | `GET /api/v1/openapi.json` | No API-key path (TC-016-14) |
| 2 | `POST /api/v1/auth/login` with a user created by `create-user` | 200 `Token` (TC-016-11) |
| 3 | `POST /api/v1/sessions` with a revoked key | 401 `API_KEY_INVALID` (TC-016-13) |

## Database Validation

| Step | Database Check | Expected Result |
|---|---|---|
| 1 | `SELECT count(*) FROM api_keys WHERE key_hash !~ '^[0-9a-f]{64}$';` | 0 |
| 2 | `SELECT count(*) FROM users WHERE password_hash NOT LIKE '$argon2id$v=19$m=65536,t=3,p=4$%';` | 0 for users created by this feature |
| 3 | `SELECT count(*) FROM users WHERE email <> lower(trim(email));` | 0 |
| 4 | `SELECT action, actor_type, details->>'operator' IS NOT NULL FROM audit_logs WHERE action IN ('user.created','api_key.created','api_key.revoked');` | Every row `actor_type` `system` and operator present |
| 5 | `SELECT scopes FROM api_keys;` | Every array is a non-empty subset of `{ingest:write, pipeline:run}` |

## Negative Test Cases

| Step | Action | Expected Result |
|---|---|---|
| 1 | Password of 11 or 129 characters, equal to the e-mail, or in the common list | `PASSWORD_POLICY_VIOLATION`; CLI exit 2, nothing written (TC-016-03, TC-016-12) |
| 2 | `--scope admin` | Exit 2, nothing written (TC-016-08) |
| 3 | `--device D99` | Exit 2, nothing written (TC-016-08) |
| 4 | Duplicate e-mail / duplicate active key name | Exit 2, transaction rolled back (TC-016-08, TC-016-12) |
| 5 | `revoke-api-key` unknown name | Exit 2 (TC-016-10) |
| 6 | Invalid settings | Exit 1 with `startup_config_invalid` (TC-016-16) |

## Acceptance Criteria Validation

| Requirement | Pass Condition | Test Case |
|---|---|---|
| FEAT-016-AC-01 | Hash starts `$argon2id$v=19$m=65536,t=3,p=4$`; verify accepts the plaintext and rejects any other | TC-016-01 |
| FEAT-016-AC-02 | 11-char, 129-char, own e-mail (different case) and common password rejected; 12-char non-listed accepted | TC-016-03 |
| FEAT-016-AC-03 | `create-api-key --name t1` prints one `^ewk_[A-Za-z0-9_-]{43}$` key, stores `{ingest:write}` and its SHA-256; no log or audit row contains the key | TC-016-05, TC-016-06, TC-016-15 |
| FEAT-016-AC-04 | `t2` with both scopes and D01 stored; `--scope admin` exits 2 and writes nothing | TC-016-07, TC-016-08 |
| FEAT-016-AC-05 | `revoke-api-key --name t1` sets `active = false` and writes one `api_key.revoked` row with `actor_type = system` and `details.operator` | TC-016-09 |
| FEAT-016-AC-06 | `create-user --email Admin@Example.com … --role admin --password-stdin` stores lower-case e-mail, argon2id hash and one `user.created` row with `details.role = admin` | TC-016-11 (uses `QA.Admin@Example.com` because `admin@example.com` is already seeded), TC-016-04 |
| FEAT-016-AC-07 | OpenAPI and `backend/api/` contain no API-key route | TC-016-14 |

## Test Data Requirements

- Master data of `test_v0_1` (devices D01–D10, D07B); device code D99 does not exist.
- Synthetic key names `t1`, `t2`, `t3`, `t4`, `no-such-key`; synthetic users `qa.admin@example.com`, `qa.short@example.com`, `qa.role@example.com`, `qa.arg@example.com` (RFC 2606 domain).
- Passwords chosen locally at run time and never recorded; the common-password sample taken from `backend/core/common_passwords.txt` at run time.
- Environment: `APP_ENV`, `DATABASE_URL`, `PIPELINE_PROFILE`, `SEED_*` (values from the environment file).

## Traceability

| Requirement | Feature | Test Case |
|---|---|---|
| FEAT-016-FR-01 / SEC-010 / TST-032 | FEAT-016 | TC-016-01, TC-016-11 |
| FEAT-016-FR-02 / SEC-011 | FEAT-016 | TC-016-02 |
| FEAT-016-FR-03 / SEC-012 | FEAT-016 | TC-016-03, TC-016-12 |
| FEAT-016-FR-04 / SEC-016 | FEAT-016 | TC-016-04, TC-016-11 |
| FEAT-016-FR-05 / SEC-017 / DEP-075 | FEAT-016 | TC-016-11, TC-016-12 |
| FEAT-016-FR-06 / SEC-020 / FR-226 | FEAT-016 | TC-016-05, TC-016-06 |
| FEAT-016-FR-07 / SEC-021 | FEAT-016 | TC-016-06, TC-016-15 |
| FEAT-016-FR-08 / SEC-022 / PGS-035 | FEAT-016 | TC-016-07, TC-016-08 |
| FEAT-016-FR-09 / SEC-023 | FEAT-016 | TC-016-07, TC-016-08 |
| FEAT-016-FR-10 / SEC-024 | FEAT-016 | TC-016-09, TC-016-13 |
| FEAT-016-FR-11 / SEC-103 / SEC-101 | FEAT-016 | TC-016-06, TC-016-09, TC-016-11 |
| FEAT-016-FR-12 / ARC-067 / D-34 | FEAT-016 | TC-016-14 |
| TST-195 / D-86 (CLI refusal exit 2) | FEAT-016 | TC-016-08, TC-016-10, TC-016-12 |
| ENV-002 (settings failure exit 1) | FEAT-016 | TC-016-16 |
