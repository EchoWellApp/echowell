# HIPAA Evidence Matrix

Document ID: ECHOWELL-HIPAA-EVID · Version 0.1 · Date: 22 November 2026 · Owner: Team 2 · Status: Draft
Assessed commit: `b74c38e` (`main`, 20 Nov 2026) · Method and ratings: `docs/hipaa/HIPAA_VERIFICATION_TRD.md` §8 ·
Findings: `FINDINGS_REGISTER.md` (HF-xx)

Ratings: **PASS**, **PARTIAL**, **FAIL**, **NOT DETERMINED (ND)**. Evidence types: *observed* (code,
configuration, test or scan), *documented* (design document only). Every PASS below rests on observed evidence.

## 1. Technical safeguards (45 CFR § 164.312)

| Control | Source Requirement | Repository Evidence | File Path | Assessment | Notes |
|---|---|---|---|---|---|
| Unique user identification | § 164.312(a)(2)(i) (R); ASVS V6 | Each user has a UUID and a unique lower-cased email; tokens carry `sub` = user UUID; no shared or default accounts; first admin only via CLI | `backend/models/user.py`; `backend/core/security.py`; `backend/cli.py`; TRD 12 SEC-016, SEC-017 | PASS | |
| Emergency access procedure | § 164.312(a)(2)(ii) (R) | Documented operator paths: CLI user creation and role change by a team member with database access; restore procedure | `docs/deployment.md` "Incident containment", "Backups and restore"; `backend/cli.py` | PARTIAL | No "break-glass" procedure is written as such; restore drill not recorded (HF-08) |
| Automatic logoff | § 164.312(a)(2)(iii) (A); ASVS V7 | 60-minute JWT lifetime, no refresh token; token in `sessionStorage` (cleared on tab close); redirect to login on expiry | `backend/core/security.py`; `frontend/lib/auth.ts`; TRD 12 SEC-032, SEC-037, SEC-038 | PARTIAL | No inactivity time-out (HF-04) |
| Encryption and decryption (at rest) | § 164.312(a)(2)(iv) (A); CSF PR.DS-01; ASVS V11, V14 | Provider-managed encryption (Neon) documented; customer-managed KMS keys specified for AWS; password hashes (argon2id) and API-key hashes (SHA-256) stored instead of secrets | TRD 12 SEC-063; `backend/core/security.py` | ND | Provider settings not evidenced; AWS not built (HF-16) |
| Access control: role-based authorization | § 164.312(a)(1); § 164.308(a)(4); CSF PR.AA-05; ASVS V8 | Server-side role matrix for admin, clinician, researcher and API key; role and `active` read from the database on every request; no self-role-change; researchers read-only; full matrix test; route-coverage test | `backend/api/deps.py`; `backend/api/permissions.py`; `tests/security/test_auth_matrix.py`; `tests/integration/test_auth_coverage.py`; TRD 12 §4.6 | PASS | |
| Audit controls | § 164.312(b); CSF PR.PS-04; ASVS V16 | Single audit vocabulary (24 actions); one row per event in the same transaction; actor, action, entity, IP, request ID; append-only by trigger and grants; no secrets or feature values in details | `backend/services/audit_service.py`; `backend/models/audit_log.py`; `backend/alembic/versions/0001_initial_schema.py` (`reject_mutation`); `tests/integration/db/test_audit_writer.py`; TRD 12 §4.12 | PASS | Review of the logs is a separate administrative control (§2) |
| Integrity of ePHI | § 164.312(c)(1); ASVS V2, V15 | `raw_sessions`, `audit_logs`, `alert_reviews`, `staff_notes` immutable for the app role (triggers + grants); notes edited by superseding rows; strict schema validation, check constraints, derived tables rebuildable from raw data | `backend/alembic/versions/0001_initial_schema.py`; `database/roles/provision_login_roles.sql`; `tests/integration/db/test_grants.py`; `backend/services/validation.py`; TRD 12 SEC-112, SEC-113 | PASS | |
| Mechanism to authenticate ePHI | § 164.312(c)(2) (A) | Immutability and rebuild-from-raw design; `config_hash` on pipeline runs; no cryptographic checksums on stored rows | `backend/services/pipeline_runner.py`; TRD 12 SEC-163 | PARTIAL | Acceptable design for a database-resident system; document as the addressable decision |
| Person or entity authentication: users | § 164.312(d); CSF PR.AA-03; ASVS V6 | argon2id (t=3, m=64 MiB, p=4); rehash on login; 12–128 character policy with common-password list; constant-time behaviour for unknown emails; identical error bodies; lockout after 10 failures in 15 minutes; login rate limit 5/minute | `backend/core/security.py`; `backend/services/auth_service.py`; `backend/core/common_passwords.txt`; `backend/core/rate_limit.py`; `tests/security/test_tokens.py` | PARTIAL | No MFA (HF-03) |
| Person or entity authentication: devices and services | § 164.312(d); ASVS V4, V6 | API keys `ewk_` + 256-bit random, stored as SHA-256 only, shown once; scopes `ingest:write` / `pipeline:run`; bound to one device; header-only; revocable; accepted on three endpoints only | `backend/core/security.py`; `backend/api/deps.py`; `backend/cli.py`; `tests/security/test_api_keys.py`; TRD 12 §4.4 | PASS | Device-side key storage outside repository (HF-18) |
| Token security | § 164.312(d); ASVS V9 | HS256 with explicit algorithm list; `iss`, `aud`, `exp` verified; `jti`; secret ≥ 32 bytes, template values refused at startup in staging/production | `backend/core/security.py`; `backend/core/config.py`; `tests/security/test_tokens.py` | PASS | Single-token revocation only by global secret rotation (HF-04) |
| Transmission security | § 164.312(e)(1), (e)(2)(i)–(ii) (A); CSF PR.DS-02; ASVS V12 | HTTPS-only edges (Netlify, Render); HSTS from backend (staging/production) and Netlify; backend refuses to start without `sslmode=require`/`verify-full`; no HTTP ingest path; TLS check in smoke tests | `backend/core/middleware.py`; `backend/core/config.py`; `netlify.toml`; `tests/security/test_transport_and_secrets.py`; TRD 12 §4.8 | PASS | Edge TLS versions are provider settings (documented, not observed) |

## 2. Administrative, physical and organizational safeguards (evidence in repository only)

| Control | Source Requirement | Repository Evidence | File Path | Assessment | Notes |
|---|---|---|---|---|---|
| Risk analysis | § 164.308(a)(1)(ii)(A) (R) | STRIDE threat model, risk register RSK-01..17, open questions | TRD 12 §4.1; TRD 24 | PARTIAL | Not a formal HIPAA risk analysis; produced next in `HIPAA_RISK_ANALYSIS.md` |
| Risk management / vulnerability management | § 164.308(a)(1)(ii)(B) (R); CSF ID.RA-01, PR.PS-02 | Dependabot; `pip-audit`, `npm audit`, Bandit, Gitleaks in CI with time-boxed waiver process and patch deadlines | `.github/dependabot.yml`; `.github/workflows/ci.yml` (`security-audit`); `scripts/ci/audit_gate.py`; `SECURITY_EXCEPTIONS.md` | PARTIAL | Waived critical/high vulnerabilities (HF-01, HF-02); no CodeQL (HF-10) |
| Information system activity review | § 164.308(a)(1)(ii)(D) (R); CSF DE.CM-09 | Monitoring of uptime, deploys, errors, pipeline; audit logs readable via read-only role | `docs/deployment.md` "Monitoring and alerts"; TRD 12 SEC-105 | PARTIAL | No audit-log review procedure (HF-09) |
| Workforce access management | § 164.308(a)(3)–(4) | Accounts only for IRB-listed personnel; deactivation within 1 working day; no self-registration | TRD 12 SEC-046, SEC-017; `backend/api/users.py` | ND | Procedure documented; practice not evidenced |
| Password management | § 164.308(a)(5)(ii)(D) (A) | Password policy per NIST SP 800-63B; argon2id | `backend/services/user_service.py`; TRD 12 SEC-012 | PASS | |
| Security incident procedures | § 164.308(a)(6) (R); CSF RS.MA-01 | Containment within 1 hour (revoke keys, deactivate users, rotate secrets, suspend service); 24-hour reporting to PI; investigation by `request_id`; private post-incident note | `docs/deployment.md` "Incident containment"; TRD 12 §4.17 | PASS | Documented runbook with executable steps |
| Contingency plan: backup and restore | § 164.308(a)(7)(ii)(A)–(B) (R); CSF PR.DS-11 | Neon PITR; weekly encrypted `pg_dump` by data steward; restore procedure; rebuild of derived tables | `docs/deployment.md` "Backups and restore"; TRD 12 §4.16 | PARTIAL | Restore drill not recorded (HF-08) |
| Evaluation | § 164.308(a)(8) (R) | This assessment; checkpoint audits | `docs/hipaa/`; `docs/reports/` | PARTIAL | First technical evaluation; periodic schedule not yet set |
| Business associate contracts | § 164.308(b)(1); § 164.314(a) | Vendor inventory; rule that no real data reaches interim vendors; AWS BAA required before go-live | TRD 22 §4.1, TPS-002, TPS-003; TRD 15 DEP-114 | ND | No BAA evidence (HF-07) |
| Device and media controls: disposal | § 164.310(d)(2)(i)–(ii) (R) | Purge and withdrawal commands; no retention rule | `backend/cli.py`; TRD 24 OQ-01 | PARTIAL | Retention undefined (HF-06) |
| Facility access, workstation use and security | § 164.310(a)–(c) | — | — | ND | Outside repository (facility and devices) |
| Documentation retention | § 164.316(b)(2)(i) (6 years) | Version-controlled TRDs and decision log | `specs/`; `docs/` | PARTIAL | No stated retention period for security documentation |

## 3. Application and infrastructure controls

| Control | Source Requirement | Repository Evidence | File Path | Assessment | Notes |
|---|---|---|---|---|---|
| Input validation | ASVS V1, V2, V4; CSF PR.PS-06 | Pydantic models with `extra="forbid"`; path/query patterns; CSV parsed as text; body limits 64 KB / 5 MB; media types limited, `audio/*` refused | `backend/schemas/`; `backend/core/middleware.py`; `backend/services/validation.py`; TRD 12 §4.10 | PASS | |
| SQL injection prevention | ASVS V1; TRD 12 SEC-083 | SQLAlchemy expressions and bound parameters; Bandit B608 in CI; Semgrep's 6 error-level SQL/pickle hits triaged as false positives | `backend/repositories/`; `backend/core/db.py`; `backend/alembic/versions/` | PASS | See report §5 for triage |
| Rate limiting and abuse controls | ASVS V2, V4 | Login 5/minute per IP; ingest 600/minute per key; 300/minute per user; 429 with `Retry-After` | `backend/core/rate_limit.py`; TRD 12 §4.11 | PASS | |
| CORS | ASVS V3, V4 | Exact origins; no wildcard (refused by config validation); `allow_credentials=False` | `backend/core/config.py`; `tests/security/test_cors.py`, `test_deployed_cors.py` | PASS | |
| Error handling | ASVS V16 | No stack traces, SQL, paths or versions in error responses | `backend/core/error_handlers.py`; TRD 12 SEC-085 | PASS | |
| Browser security headers | ASVS V3 | HSTS, `nosniff`, `X-Frame-Options: DENY`, `no-referrer`, Permissions-Policy denying microphone and camera, CSP without third-party origins; no third-party scripts | `netlify.toml`; `backend/core/middleware.py`; TRD 12 §4.9 | PARTIAL | `script-src 'unsafe-inline'` accepted (HF-05) |
| Secrets management | ASVS V13; CSF PR.AA-01 | Secrets only in platform settings and GitHub encrypted secrets; `.env` files blocked by CI; startup refuses template secrets and placeholder passwords; Gitleaks full-history scan in CI; local Gitleaks 8.30.1: 2 findings, both false positives | `backend/core/config.py`; `.gitleaks.toml`; `.github/workflows/ci.yml`; `docs/deployment.md` | PASS | Upgrade CI Gitleaks (HF-14) |
| Application logging and redaction | ASVS V16; CSF PR.PS-04 | Structured JSON logs with request ID; redaction of authorization, API key, password, token, DSN, body and note fields; Sentry with `send_default_pii=False` and scrubbing | `backend/core/logging.py`; `backend/core/monitoring.py` | PASS | |
| Database least privilege | CSF PR.AA-05; ASVS V15 | Three roles (migrator, app, read-only); app has no DELETE on history tables and no access to ground truth; read-only role cannot read password or key hashes; owner credentials restricted | `database/roles/provision_login_roles.sql`; `tests/integration/db/test_grants.py`, `test_roles.py`; TRD 12 §4.13 | PASS | |
| CI/CD security | CSF PR.PS-06, GV.SC-05 | `permissions: contents: read` on all five workflows; protected production environment with required reviewer; eight required checks on `main`; CODEOWNERS | `.github/workflows/*.yml`; `.github/CODEOWNERS`; `docs/deployment.md` | PASS | Tag pinning by policy (HF-12) |
| Code scanning (CodeQL) | CSF ID.RA-01 | None configured | `.github/workflows/` | FAIL | HF-10 |
| Dependency vulnerabilities | CSF ID.RA-01, PR.PS-02 | Trivy: 3 critical, 11 high in `next`/`postcss`; Starlette advisories; all under waiver to 20 Dec 2026 | `frontend/package-lock.json`; `SECURITY_EXCEPTIONS.md` | PARTIAL | HF-01, HF-02, HF-13 |
| Container and IaC configuration | CSF PR.PS-01 | Trivy: only DS-0026 (no HEALTHCHECK, Low) in two Dockerfiles; slim/alpine base images | `backend/Dockerfile`; `frontend/Dockerfile` | PASS | HF-15 |
| Hosting region and data residency | TRD 12 SEC-007 | Render `ohio`, Neon `aws-us-east-1`, AWS `us-east-1` | `render.yaml`; TRD 22 TPS-004 | PASS | Neon region documented, not observed |
| Account security of providers (MFA, owners) | CSF PR.AA-01 | ≥ 2 administrators with MFA required; GitHub 2FA required for members | TRD 22 TPS-005; `docs/deployment.md` "Service accounts" | ND | "Verified on" not recorded (HF-08) |

## 4. EchoWell-specific controls

| Control | Source Requirement | Repository Evidence | File Path | Assessment | Notes |
|---|---|---|---|---|---|
| No raw audio | TRD 12 SEC-121; BR-01 | No audio column or endpoint; `audio/*` returns 415; extra fields such as `audio_base64` rejected; CI blocks audio files; Permissions-Policy denies microphone | `tests/security/test_no_audio.py`; `backend/core/middleware.py`; `.github/workflows/ci.yml` (`repo-hygiene`) | PASS | Audio exists only on Team 1 devices (HF-18) |
| Resident data minimization | § 164.502(b) (context); TRD 12 SEC-120, SEC-122 | Study codes only; resident attributes limited to sex, cohort, dates, status; non-identifying room labels | `backend/models/resident.py`; `backend/models/device.py`; `tests/security/test_data_minimisation.py` | PASS | Dates are HIPAA identifiers; see report §9 |
| Voice-feature protection | § 164.312(a)(1), (b), (e)(1) | Features stored in immutable `raw_sessions`; never logged or in audit details; role-restricted reads | `backend/core/logging.py`; `backend/services/audit_service.py`; TRD 12 SEC-104 | PASS | |
| Behavioral-health outputs (scores, alerts, reviews, notes) | § 164.312(a)(1); TRD 12 SEC-129 | Role-gated; reviews and notes append-only and audited without content; wording "detects a change", never a diagnosis; CSV export limited to admin/researcher and audited | `backend/api/scores.py`, `alarms.py`; `backend/services/note_service.py`; TRD 00 X-03 | PASS | Notes free text (HF-11) |
| Withdrawal handling | TRD 12 SEC-126 | Ingest refused for withdrawn residents; purge command audited | `backend/services/validation.py`; `backend/cli.py` | PASS | Retention of existing data pending OQ-01 (HF-06) |
| No external AI or analytics services | TRD 12 SEC-128; TRD 22 TPS-080, TPS-081 | CI blocks LLM and ML packages and imports; no trackers | `.github/workflows/ci.yml` (`repo-hygiene`) | PASS | |
| Synthetic-data-only interim stack | TRD 12 SEC-001 to SEC-005 | Rule, data-source banner, go-live checklist | TRD 12 §4.2; TRD 15 DEP-112..117 | ND | Operational practice; consistent with all repository evidence |

## 5. Rating totals

| Rating | Count |
|---|---|
| PASS | 26 |
| PARTIAL | 13 |
| FAIL | 1 |
| ND | 6 |
| **Total controls** | **46** |

---

*This assessment represents a technical HIPAA readiness review based on repository evidence and does not
constitute legal certification, regulatory certification, or a formal HIPAA audit.*
