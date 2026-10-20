# FEAT-037 User management API (GET/POST/PATCH /api/v1/users)

| Field | Value |
|---|---|
| Epic | Backend API |
| Build phase | Phase 5 (TRD 25) |
| Priority | P1 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-021, FEAT-016 |
| Status | Not Started |

## Purpose

Let an admin manage dashboard accounts from `/admin`: list users, create a user with e-mail, display name, role and an initial password, and change a user's display name, role, active flag or password. Users are never deleted; an admin cannot change their own role or deactivate themselves, and the system never ends up without an active admin. Every change is audited.

## Business Context

- BR-16 (access control and traceability): only admins manage accounts; roles are exactly admin, clinician, researcher; changes are audited; passwords meet the policy and are stored as argon2id hashes.
- FRs covered (BACKLOG.md): FR-220, FR-221.

## Referenced TRDs

- TRD 05 API-091 (list, create, update), API-092 (last admin, audit), API-100.
- TRD 19 §4.3 E-25, E-26, E-27; schemas `User`, `UserCreate`, `UserUpdate`, `UserList`, `Role`.
- TRD 12 SEC-010 (argon2id), SEC-012 (password policy), SEC-044 (no self role change or self deactivation), SEC-045, SEC-046 (accounts only for IRB-listed personnel; inspection), SEC-125 (user record content), §4.6, §4.12 (`user.created`, `user.updated`).
- TRD 20 §4.6.2 `users`, PGS-034 (lower-case unique e-mail, `$argon2id$` hash).
- TRD 13 TST-053 (audit for user change); TRD 12 AC-SEC-05.
- TRD 25 AGT-062 (role names).

## Scope

- Router `backend/api/users.py` with `GET /api/v1/users`, `POST /api/v1/users`, `PATCH /api/v1/users/{id}`, calling `user_service.list`, `user_service.create`, `user_service.update`.
- Password policy check and hashing through the FEAT-016 primitives; e-mail normalisation.
- Last-admin and self-change guards; audit rows.

## Out of Scope

- Login, logout, `me` and token handling (FEAT-020); credential primitives and the CLI `create-user` (FEAT-016).
- User deletion (not allowed, FR-221) and API-key management (CLI only, FEAT-016).
- The Admin "Users" tab (FEAT-074).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-037-FR-01 | All three endpoints shall be restricted to role `admin`; clinicians and researchers receive 403, API keys and anonymous 401. | API-091; TRD 12 §4.6 |
| FEAT-037-FR-02 | `GET /users` shall return `UserList` (`id`, `email`, `display_name`, `role`, `active`, `last_login_at`, `created_at`) with optional filters `role` and `active` and pagination; `password_hash` is never returned. | API-091; TRD 19 E-25; DME-005 |
| FEAT-037-FR-03 | `POST /users` with `UserCreate` `{email, display_name (1..100), role ∈ {admin, clinician, researcher}, password (12..128)}` shall store the e-mail lower-cased, hash the password with argon2id (SEC-010 parameters) and return 201 `User`; a duplicate e-mail (case-insensitive) returns 409 `EMAIL_ALREADY_EXISTS`. | API-091, PGS-034, SEC-010; FR-220 |
| FEAT-037-FR-04 | A password shorter than 12 or longer than 128 characters, equal to the user's e-mail (case-insensitive) or contained in `backend/core/common_passwords.txt` shall return 422 `PASSWORD_POLICY_VIOLATION`; no composition rules are imposed. | SEC-012, API-091 |
| FEAT-037-FR-05 | `PATCH /users/{id}` with `UserUpdate` (at least one of `display_name`, `role`, `active`, `password`) shall update only the given fields and return 200 `User`; an unknown id returns 404 `USER_NOT_FOUND`; there is no DELETE route. | API-091; TRD 19 E-27; FR-221 |
| FEAT-037-FR-06 | A PATCH by an admin that changes their own `role` or sets their own `active` to false shall return 403 `FORBIDDEN`. | SEC-044 |
| FEAT-037-FR-07 | A PATCH that would leave zero active admins shall return 409 `LAST_ADMIN` and change nothing. | API-092 |
| FEAT-037-FR-08 | Creation shall write audit `user.created` (actor user, details `{role}`) and each update `user.updated` (details `{changed: [field names]}`, never the password or its hash), in the same transaction. | API-092; TRD 12 §4.12, SEC-104 |
| FEAT-037-FR-09 | A role or `active` change shall take effect on the user's next request, because roles and the active flag are read from the database on every request. | API-012, API-013 |

## Inputs

- Bearer JWT (admin); query `role`, `active`, `limit`, `offset`; path `id` (uuid); bodies `UserCreate`, `UserUpdate`.
- Table `users`; file `backend/core/common_passwords.txt`.

## Outputs

- 200 `UserList`, 201 `User`, 200 `User`; Problems 403, 404, 409, 422.
- `users` rows, `audit_logs` rows.

## Data Flow

1. Auth: `require_roles("admin")`.
2. Create: validate body (extra properties forbidden) → normalise e-mail → policy check → existence check (409) → hash → insert → audit → 201.
3. Update: load target (404) → self-change guard (403) → if role or active changes would remove the last active admin → 409 → policy check and hash for a new password → update → audit with changed field names → 200.
4. List: filter and page.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-021, FEAT-016

- FEAT-021 (Role-based authorization matrix): admin-only access and `access.denied` audit for 403.
- FEAT-016 (Credential primitives): `hash_password`, the password policy, e-mail normalisation.
- Downstream: FEAT-038 (OpenAPI), FEAT-074 (Admin Users tab).

## Database Impact

- Tables read and written: `users` (`email`, `display_name`, `role`, `password_hash`, `active`, `last_login_at`, `created_at`, `updated_at`); `audit_logs` (INSERT).
- Constraints relied on: unique lower-case e-mail and the `$argon2id$` prefix check (PGS-034).
- Tables created or altered: none.

## API Impact

- Exposed: `GET /api/v1/users` (E-25), `POST /api/v1/users` (E-26), `PATCH /api/v1/users/{id}` (E-27).

## Frontend Impact

None in this feature. Consumer: `AdminPanel` "Users" tab via `listUsers()`, `createUser(input)`, `updateUser(id, patch)` (TRD 04 §4.6.2), delivered by FEAT-074.

## Analytics Impact

None: user management has no algorithmic content.

## Security Requirements

- Authentication: bearer JWT; authorisation: admin only (TRD 13 Table 4.13-A row "GET, POST, PATCH /api/v1/users").
- Passwords: argon2id with SEC-010 parameters; never stored or logged in plaintext; never in audit details (SEC-010, SEC-104, LOG-020).
- User records hold only e-mail, display name, role and login metadata (SEC-125).
- Accounts only for IRB-listed personnel and deactivation within 1 working day of notice are procedural (SEC-046, inspection).

## Error Handling

| Condition | Response |
|---|---|
| Duplicate e-mail | 409 `EMAIL_ALREADY_EXISTS` |
| Policy violation | 422 `PASSWORD_POLICY_VIOLATION` |
| Malformed body, empty PATCH, unknown role, extra property | 422 `VALIDATION_ERROR` |
| Unknown user id | 404 `USER_NOT_FOUND` |
| Self role change or self deactivation | 403 `FORBIDDEN` |
| Would leave no active admin | 409 `LAST_ADMIN` |
| Non-admin caller | 403 `FORBIDDEN` |

## Logging Requirements

- Access log per request (LOG-010); users identified by UUID only, never e-mail (LOG-022); redaction of `password` fields (LOG-023).
- Audit rows `user.created` and `user.updated` with the paired `audit_event` line (LOG-092).

## Testing Requirements

- Integration (`tests/integration/api/test_users.py`, marker `integration`): admin create 201 with stored hash starting `$argon2id$v=19$m=65536,t=3,p=4$` (AC-SEC-05); "short" and "password1234" → 422 `PASSWORD_POLICY_VIOLATION`; password equal to e-mail → 422; duplicate e-mail in different case → 409; PATCH role and active → 200 with audit `changed`; self role change → 403; unknown id → 404; clinician and researcher → 403; list never contains `password_hash`; audit rows for user change (TST-053).
- Unit (`tests/unit/backend/services/test_user_service.py`, marker `unit`): last-admin guard raises `LAST_ADMIN` with a repository double (FEAT-037-AC-06).
- Contract: TST-061; auth cells via TST-130 (FEAT-039).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-037-AC-01 | An admin `POST /users` with a valid 14-character password returns 201, stores the e-mail lower-cased and a hash starting with `$argon2id$v=19$m=65536,t=3,p=4$`, and writes one `user.created` audit row with details `{"role": ...}`. | API-091, AC-SEC-05, FR-220 |
| FEAT-037-AC-02 | Passwords "short" and "password1234" each return 422 `PASSWORD_POLICY_VIOLATION` and create no user. | SEC-012, AC-SEC-05 |
| FEAT-037-AC-03 | Creating `Clinician@Example.com` when `clinician@example.com` exists returns 409 `EMAIL_ALREADY_EXISTS`. | API-091, PGS-034 |
| FEAT-037-AC-04 | `PATCH /users/{id}` with `{"role": "researcher", "active": false}` on another user returns 200 and writes `user.updated` with `changed` containing `role` and `active` and no password value. | API-091, API-092, FR-221 |
| FEAT-037-AC-05 | An admin PATCH of their own `role` or their own `active: false` returns 403 `FORBIDDEN`. | SEC-044 |
| FEAT-037-AC-06 | A unit test of `user_service.update` with a repository state in which the target user is the only active admin and the change sets `active` false or `role` to a non-admin value raises the `LAST_ADMIN` error (HTTP 409) and performs no write. | API-092 |
| FEAT-037-AC-07 | `DELETE /api/v1/users/{id}` returns 405 or 404, and no response of the three endpoints contains `password_hash`. | FR-221, DME-005 |
| FEAT-037-AC-08 | Clinician and researcher JWTs receive 403 on all three endpoints; an API key receives 401. | TRD 13 Table 4.13-A |

## Definition of Done

- Three endpoints implemented with TRD 19 schemas; no delete route.
- Integration tests pass; requirement markers (TST-013); coverage ≥ 85 %; OpenAPI drift check passes.

## Implementation Notes

- Run the last-admin check inside the update transaction with `SELECT ... FOR UPDATE` on the active admin rows, so two concurrent PATCHes cannot both pass.
- The self-change guard compares the path id with the authenticated user id; changing one's own `display_name` or password is allowed (SEC-044 restricts role and deactivation only).
- Test users use a reduced argon2 memory cost only through a test-only settings override; never weaken production parameters (TRD 12 §8).
- TRD observation: through the HTTP API the `LAST_ADMIN` state is unreachable, because the caller is itself an active admin and SEC-044 forbids changing one's own role or active flag; any other admin target leaves the caller active. Keep the API-092 guard in the service (it also protects concurrent requests) and test it at service level (FEAT-037-AC-06); TRD 05 API-092 now records it as a defensive invariant verified by a service-level test.
