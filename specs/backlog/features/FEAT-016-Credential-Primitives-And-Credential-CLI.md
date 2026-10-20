# FEAT-016 Credential primitives and credential CLI (argon2id, API keys, create-user, create-api-key, revoke-api-key)

| Field | Value |
|---|---|
| Epic | Authentication & Security |
| Build phase | Phase 4 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-015 |
| Status | Not Started |

## Purpose

Implement the credential building blocks every authentication path relies on — argon2id password hashing with the mandated parameters and rehash support, the password policy, e-mail normalisation, API key generation and hashing — and the operator CLI commands that create users and create or revoke API keys. Users are also created over HTTP later (FEAT-037), but the first admin and every API key exist only through this CLI; there is no HTTP endpoint for API keys (FR-226, D-34).

## Business Context

- BR-16: authenticated access with strong password hashing, no default credentials, no self-registration (SEC-010, SEC-017).
- BR-01: devices authenticate to ingest with per-device API keys whose plaintext is shown once and stored only as a hash (FR-226, SEC-020, SEC-021).
- Least attack surface: API keys, residents and devices are managed only by CLI in the MVP (ARC-067, D-34).

## Referenced TRDs

- TRD 12 SEC-010..SEC-012 (hashing, rehash, password policy), SEC-016 (e-mail normalisation), SEC-017 (first admin by CLI), SEC-020..SEC-024 (API key generation, hashing, scopes, device binding, revocation), SEC-103 (CLI audit).
- TRD 15 §4.8 CLI table (`create-user`, `create-api-key`, `revoke-api-key`), DEP-075.
- TRD 05 §8 (`create-user --email --display-name --role`).
- TRD 01 ARC-067.
- TRD 02 FR-226.
- TRD 13 TST-032.
- TRD 24 D-34.

## Scope

- `backend/core/security.py` (TRD 01 §4.6 "core/ … security (JWT, argon2id, API keys)"):
  - `hash_password(plain)` and `verify_password(plain, hash)` using argon2-cffi 23.x with `time_cost=3`, `memory_cost=65536`, `parallelism=4`, `hash_len=32`, `salt_len=16`; `needs_rehash(hash)` for rehash-on-login.
  - A fixed dummy argon2id hash constant for unknown-email verification (consumed by FEAT-020, SEC-013).
  - `validate_password(plain, email)` enforcing 12..128 characters, not equal to the e-mail (case-insensitive), not in `backend/core/common_passwords.txt` (top 10,000), with no composition rules; violation raises an `AppError` mapped to 422 `PASSWORD_POLICY_VIOLATION`.
  - `normalise_email(email)` → trimmed, lower-case.
  - `generate_api_key()` → `ewk_` + `secrets.token_urlsafe(32)`; `hash_api_key(key)` → SHA-256 lower-case hex.
- `backend/core/common_passwords.txt` (bundled list).
- `backend/cli.py` commands (argparse or Typer):
  - `create-user --email E --display-name N --role R [--password-stdin]`: password from `getpass` prompt or stdin, validated, hashed, user inserted; audited `user.created` (`actor_type = system`, `details.role`, `details.operator`).
  - `create-api-key --name N [--device D] [--scope S]…`: `--scope` repeatable, values `ingest:write` or `pipeline:run`, default `ingest:write`; optional device binding by `device_code`; inserts the hash; prints the plaintext key once to stdout; audited `api_key.created` (`details.name`, `details.device_code`).
  - `revoke-api-key --name N`: sets `active = false`; audited `api_key.revoked`.
- Each command runs settings validation for its ENV-053 subset, uses one transaction with its audit row, and exits non-zero on failure.

## Out of Scope

- Login, logout, `/auth/me`, JWT issuing and verification, lockout, the API-key authentication dependency and `last_used_at` updates (FEAT-020).
- `POST/PATCH /api/v1/users` (FEAT-037), which reuses these primitives.
- Seeded test users and the `test-ingest` key from `SEED_*` variables (FEAT-017).
- Scope enforcement on endpoints (FEAT-020, FEAT-021) and device-key mismatch on ingest (FEAT-023, FEAT-025).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-016-FR-01 | Passwords shall be hashed with argon2id (argon2-cffi 23.x) using time_cost 3, memory_cost 65536 KiB, parallelism 4, hash_len 32, salt_len 16; plaintext passwords are never stored or logged. | SEC-010 |
| FEAT-016-FR-02 | A helper shall report whether a stored hash's parameters differ from SEC-010 so login can rehash and store it. | SEC-011 |
| FEAT-016-FR-03 | Passwords shall be 12..128 characters, not equal to the user's email (case-insensitive), not in `backend/core/common_passwords.txt`; violations raise `PASSWORD_POLICY_VIOLATION` (422 over HTTP); no composition rules and no forced periodic change. | SEC-012 |
| FEAT-016-FR-04 | Emails shall be trimmed and lower-cased before lookup and storage. | SEC-016 |
| FEAT-016-FR-05 | The first admin shall be created only by `python -m backend.cli create-user --role admin`; no default credentials and no self-registration exist; in production it is run via `railway run` from a workstation with the password entered interactively. | SEC-017, DEP-075 |
| FEAT-016-FR-06 | API keys shall be generated as `ewk_` + `secrets.token_urlsafe(32)` by `create-api-key --name <name> [--scope <ingest:write\|pipeline:run>]… [--device <device_code>]`, `--scope` optional, repeatable, default `ingest:write`. | SEC-020, FR-226 |
| FEAT-016-FR-07 | Only the SHA-256 hex digest shall be stored in `api_keys.key_hash`; the plaintext is printed once by `create-api-key` and never stored, logged or retrievable. | SEC-021, FR-226 |
| FEAT-016-FR-08 | Scopes shall be a non-empty subset of {`ingest:write`, `pipeline:run`}; other values are refused by the CLI. | SEC-022, PGS-035 |
| FEAT-016-FR-09 | `--device` shall bind the key to that device (`api_keys.device_id`); an unknown device code is refused. | SEC-023 |
| FEAT-016-FR-10 | `revoke-api-key --name <name>` shall set `active = false`. | SEC-024 |
| FEAT-016-FR-11 | `create-user`, `create-api-key` and `revoke-api-key` shall each write one audit row (`user.created`, `api_key.created`, `api_key.revoked`) with `actor_type = system` and `details.operator` = OS user, in the same transaction as the change. | SEC-103, SEC-101 |
| FEAT-016-FR-12 | No HTTP endpoint shall exist for API keys. | ARC-067, D-34, FR-226 |

## Inputs

- CLI arguments; password from interactive prompt or stdin; environment for settings (ENV-053 subset).
- `devices` rows for `--device` resolution; `users`, `api_keys` tables (FEAT-009).

## Outputs

- `users` and `api_keys` rows; audit rows; the plaintext API key printed once to stdout by `create-api-key`.
- Library functions in `backend/core/security.py` reused by FEAT-017, FEAT-020, FEAT-037.

## Data Flow

Operator runs `python -m backend.cli create-api-key --name edgewood-gateway --device D01` → settings validated → key generated → SHA-256 computed → `api_keys` row inserted and `api_key.created` audit row written in one transaction → commit → plaintext printed once. `create-user` → password read via `getpass`/stdin → policy check → argon2id hash → `users` insert + `user.created` audit → commit.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-015

- FEAT-015 provides `audit_service.record` and the CLI actor helper used by every command here.

Features that build directly on this one: FEAT-017, FEAT-020.

## Database Impact

- Tables written: `users` (INSERT), `api_keys` (INSERT, UPDATE `active`), `audit_logs` (INSERT).
- Tables read: `devices` (resolve `--device`), `users` (duplicate e-mail check).
- Tables created or modified (schema): none.

## API Impact

None exposed (no API-key endpoint, ARC-067). The primitives are consumed by E-02 `POST /auth/login` (FEAT-020) and E-26/E-27 `/users` (FEAT-037).

## Frontend Impact

None.

## Analytics Impact

None.

## Security Requirements

- Authentication/authorization: CLI access requires database access (operator workstation); there is no network endpoint.
- Plaintext passwords and keys never logged, never in audit `details` (SEC-010, SEC-021, SEC-104).
- The CLI connects with `DATABASE_URL` (`echowell_app`), which holds INSERT/UPDATE on `users` and `api_keys` (PGS-021); these commands are not in the migrator closed list (TRD 20 §4.3).
- Passwords are never accepted as command-line arguments (prompt or stdin only) so they do not reach shell history (DEP-075).

## Error Handling

| Failure | Behaviour |
|---|---|
| Invalid settings | Exit code 1 with CRITICAL `startup_config_invalid` (ENV-002) |
| Password policy violation | Error message naming the rule, non-zero exit, nothing written (SEC-012) |
| Duplicate e-mail or key name collision | Non-zero exit with a clear message; transaction rolled back |
| Unknown `--device` code or invalid `--scope` | Non-zero exit, nothing written (SEC-022, SEC-023) |
| `revoke-api-key` with an unknown name | Non-zero exit, nothing written |

The TRDs fix exit code 1 for settings-validation failures (ENV-002) and exit code 2 for the command-specific refusals listed in TRD 15 §4.8; they do not state an exit code for a refused input to these three commands, and no TRD 24 OQ covers it. The requirement here is only that the command exits non-zero and writes nothing; if a specific code is needed, raise an OQ under AGT-009.

## Logging Requirements

- Audit rows `user.created`, `api_key.created`, `api_key.revoked` with `actor_type = system` and `details.operator` (SEC-103, TRD 12 §4.12).
- One INFO `audit_event` per audit write (LOG-092, via FEAT-015).
- No password, hash or key in any log line (SEC-107).

## Testing Requirements

- Unit (`tests/unit/backend/core/test_security.py`): TST-032 argon2id hash/verify with SEC-010 parameters (parse the encoded hash `$argon2id$v=19$m=65536,t=3,p=4$…`); `needs_rehash` true for a hash with other parameters (SEC-011); policy cases 11 chars rejected, 12 accepted, 129 rejected, equal-to-email rejected, common password rejected (SEC-012); e-mail normalisation (SEC-016); API key format `^ewk_[A-Za-z0-9_-]{43}$` and SHA-256 hash 64 lower-case hex (SEC-020, SEC-021).
- Integration (`tests/integration/test_cli_credentials.py`): `create-user` with `--password-stdin` inserts one user and one `user.created` audit row; `create-api-key --scope ingest:write --scope pipeline:run --device D01` stores the hash, binds D01, prints the key once, writes `api_key.created`; stored `key_hash` equals SHA-256 of the printed key; `revoke-api-key` sets `active = false` and writes `api_key.revoked`; output and logs contain no password.
- Inspection: no router under `backend/api/` references `api_keys` creation (ARC-067).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-016-AC-01 | `hash_password("correct horse battery")` returns a string starting `$argon2id$v=19$m=65536,t=3,p=4$` and `verify_password` accepts the plaintext and rejects any other. | SEC-010, TST-032 |
| FEAT-016-AC-02 | `validate_password` rejects an 11-character password, a 129-character password, the user's own e-mail in different case and a password from `common_passwords.txt`, and accepts a 12-character non-listed password. | SEC-012 |
| FEAT-016-AC-03 | `create-api-key --name t1` prints one key matching `^ewk_[A-Za-z0-9_-]{43}$`, stores scopes `{ingest:write}` and `key_hash` = SHA-256 of the printed key; no log line or audit row contains the key. | SEC-020, SEC-021, FR-226 |
| FEAT-016-AC-04 | `create-api-key --name t2 --scope pipeline:run --scope ingest:write --device D01` stores both scopes and `device_id` of D01; `--scope admin` exits non-zero and writes nothing. | SEC-020, SEC-022, SEC-023 |
| FEAT-016-AC-05 | `revoke-api-key --name t1` sets `active = false` and writes one `api_key.revoked` audit row with `actor_type = system` and `details.operator`. | SEC-024, SEC-103 |
| FEAT-016-AC-06 | `echo 'a-valid-password-123' \| python -m backend.cli create-user --email Admin@Example.com --display-name Admin --role admin --password-stdin` stores email `admin@example.com`, an argon2id hash and one `user.created` audit row with `details.role = admin`. | SEC-016, SEC-017, SEC-103 |
| FEAT-016-AC-07 | The OpenAPI document and `backend/api/` contain no route for API keys. | ARC-067, D-34 |

## Definition of Done

- All FEAT-016 acceptance criteria pass; TST-032 hashing and key tests exist and pass.
- CLI help text documents each command; delivered in the Phase 4 PR.

## Implementation Notes

- Use `argon2.PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4, hash_len=32, salt_len=16, type=Type.ID)`; `check_needs_rehash` implements SEC-011.
- `secrets.token_urlsafe(32)` yields 43 URL-safe characters (256 bits).
- Print the key with a short warning that it is shown only once; never echo it into logs (`print` to stdout only).
- `create-user` requires `--display-name` because `users.display_name` is NOT NULL (TRD 20 §4.6.2; TRD 05 §8 lists `--display-name`), although the TRD 15 §4.8 table abbreviates the command to `--email E --role R`.
