# HIPAA Verification TRD: Technical Readiness Assessment Methodology

Document ID: ECHOWELL-HIPAA-TRD · Version 0.1 (draft for review) · Date: 22 November 2026 · Owner: Team 2 · Status: Draft
Prompt: `specs/prompts/hipaa/HIPAA_Verification_TRD_Prompt.md` (requested by Dr. Shinar at the last presentation)

**This document defines how the assessment will be done. It does not perform it.** No repository analysis,
scan or rating appears here; those are the outputs of the assessment (§9), produced by
`specs/prompts/hipaa/Implement_HIPAA_Verification.md`.

---

## 1. Purpose

### 1.1 Why a HIPAA readiness assessment

EchoWell turns short daily voice check-ins from nursing-home residents into numeric voice features, compares
each resident with their own usual pattern, and alerts care staff when a resident's voice changes. Once it
receives data about real residents of a care facility, the features, scores, alerts and staff notes are health
information tied to identifiable people. If EchoWell is operated by or for a HIPAA covered entity, that
information is electronic protected health information (ePHI) and the HIPAA Security Rule (45 CFR Part 164,
Subpart C) applies to the systems that create, receive, maintain or transmit it.

Today EchoWell holds synthetic and test data only (TRD 12 SEC-001), so no ePHI is present. A readiness
assessment performed **before** live data arrives:

- shows which Security Rule safeguards the software already supports and which are missing;
- turns gaps into a findings register that can be fixed while fixes are cheap;
- produces an evidence package that a later independent risk assessment or audit can start from; and
- gives the PI, UND IT and the IRB a factual basis for the go-live decision (TRD 15 DEP-112 to DEP-117).

### 1.2 Technical readiness versus legal certification

| | Technical readiness assessment (this methodology) | Legal or regulatory compliance |
|---|---|---|
| Question answered | Does the software and its documented configuration provide the technical safeguards the Security Rule and good practice expect? | Is the organization, as a covered entity or business associate, compliant with HIPAA? |
| Who decides | The project team, from repository evidence | The covered entity, its counsel and compliance office; HHS Office for Civil Rights in an investigation |
| Covers | Code, configuration, CI/CD, documented infrastructure, data flows | Also administrative safeguards in practice, workforce training, policies in force, Business Associate Agreements, physical safeguards, breach notification, Privacy Rule |
| Outcome | Ratings (PASS / PARTIAL / FAIL / NOT DETERMINED) and findings | A legal position; there is no official HIPAA "certification" issued by HHS |

The assessment will not state or imply that EchoWell is "HIPAA compliant" or "HIPAA certified". Every output
carries the disclaimer of §10.

### 1.3 Scope

**In scope:** the contents of the `EchoWellApp/echowell` repository at the assessed commit: the frontend
(`frontend/`), backend API (`backend/`), analytics engine (`analytics/`), database schema and roles
(`database/`, `backend/alembic/`), CI/CD workflows (`.github/`), deployment descriptors (`render.yaml`,
`netlify.toml`, `docker-compose.yml`, Dockerfiles), environment templates (`.env*.example`), tests (`tests/`,
`frontend/tests/`) and design documents (`specs/`, `docs/`).

**Out of scope:** the live Netlify, Render and Neon accounts and their settings; the AWS target account (not yet
created); Team 1's recording devices and feature-extraction software (outside this repository); organizational
policies in force; physical safeguards; the HIPAA Privacy and Breach Notification Rules except where they
create a technical requirement.

---

## 2. Assessment Objectives

| Area | Objective: the assessment determines whether… |
|---|---|
| Authentication | every human user and every device is uniquely identified and authenticated before access; passwords are stored with a memory-hard hash; brute-force and enumeration are resisted; tokens are signed, short-lived and verified on every request. |
| Authorization | access follows least privilege by role, is enforced on the server for every endpoint, takes effect immediately on role change or deactivation, and is tested. |
| Encryption | data in transit uses TLS 1.2 or higher on every external path including device ingestion, database connections require TLS, and data at rest is encrypted, with key management defined. |
| API Security | input is validated against strict schemas, request size and media type are limited, rate limits exist, CORS is restricted, errors leak nothing, and no unauthenticated route exposes data. |
| Database Security | application roles have least privilege, history tables are immutable, credentials are separated by role, and SQL injection is prevented by construction. |
| Device Security | each device holds its own revocable credential, credentials are stored hashed, a device cannot submit data for another device, and keys can be rotated. |
| Logging and Auditability | security-relevant events produce tamper-resistant audit records with actor, action, time and source, logs exclude secrets and health content, and records support investigation. |
| Data Retention | retention periods, deletion and withdrawal handling are defined, implemented or explicitly deferred with an owner, and backups follow the same rules. |
| Voice Data Protection | raw audio never enters EchoWell, and the voice-derived features that do enter are protected as health information. |
| Behavioral Health Data Protection | change scores, alerts, reviews and staff notes, which can reveal mental-health status, are protected, minimized and never presented as a diagnosis. |
| Infrastructure Security | hosting, regions, secrets, dependencies, container images and CI/CD are configured securely and documented, and every vendor that could hold ePHI is identified with its BAA status. |

---

## 3. EchoWell System Components

To be populated by the assessment (Phase 1, repository discovery). Each row will cite repository paths as
evidence.

| Component | Technologies | Repository paths | Handles resident data? | Notes |
|---|---|---|---|---|
| Frontend | *to be populated* | *to be populated* | *to be populated* | |
| Backend | *to be populated* | *to be populated* | *to be populated* | |
| Analytics | *to be populated* | *to be populated* | *to be populated* | |
| Database | *to be populated* | *to be populated* | *to be populated* | |
| CI/CD | *to be populated* | *to be populated* | *to be populated* | |
| Device Ingestion APIs | *to be populated* | *to be populated* | *to be populated* | |
| Third-Party Services | *to be populated* | *to be populated* | *to be populated* | |

---

## 4. Assessment Framework

### 4.1 Sources and versions

| Source | Version used | Role in this assessment |
|---|---|---|
| HIPAA Security Rule, 45 CFR Part 164 Subpart C (§§ 164.302–164.318), and HHS Security Rule guidance | Current eCFR text | The requirement baseline. Technical safeguards (§ 164.312) are rated in full; administrative (§ 164.308), physical (§ 164.310), organizational (§ 164.314) and documentation (§ 164.316) standards are rated only where the repository holds evidence. |
| NIST SP 800-66 Rev. 2, *Implementing the HIPAA Security Rule: A Cybersecurity Resource Guide* | February 2024 | Implementation guidance per standard (Section 5: 5.1 administrative, 5.2 physical, 5.3 technical, 5.4 organizational, 5.5 policies and documentation). |
| NIST Cybersecurity Framework (CSF) 2.0, NIST CSWP 29 | 26 February 2024 | Outcome taxonomy (Govern, Identify, Protect, Detect, Respond, Recover) for mapping and gap reporting. |
| OWASP Application Security Verification Standard (ASVS) | 5.0.0 (May 2025) | Application-level verification requirements. Target: Level 2, the level recommended for applications handling sensitive data. |

Required (R) and addressable (A) implementation specifications are both assessed. An addressable specification
may be met by an equivalent measure or a documented decision that it is not reasonable and appropriate; the
assessment looks for that documentation. HHS has proposed changes to the Security Rule (proposed rule published
January 2025); the assessment uses the rule text in force on the assessment date and notes, as context only,
where a proposed change would affect a rating.

### 4.2 Requirement matrix

| Requirement Area | HIPAA Source | NIST Source | OWASP Source | Verification Method |
|---|---|---|---|---|
| Unique user identification | § 164.312(a)(2)(i) (R) | SP 800-66r2 5.3.1; CSF PR.AA-01 | ASVS V6 Authentication | Code review of user model and login; automated tests |
| Emergency access procedure | § 164.312(a)(2)(ii) (R) | SP 800-66r2 5.3.1; CSF RC.RP-01 | — | Documentation review (runbooks, CLI) |
| Automatic logoff | § 164.312(a)(2)(iii) (A) | SP 800-66r2 5.3.1 | ASVS V7 Session Management | Code review of token lifetime, idle handling, frontend session handling |
| Encryption at rest | § 164.312(a)(2)(iv) (A) | SP 800-66r2 5.3.1; CSF PR.DS-01 | ASVS V11 Cryptography, V14 Data Protection | Infrastructure documentation review; provider settings (evidence required) |
| Role-based access control | § 164.312(a)(1); § 164.308(a)(4) | SP 800-66r2 5.1.4, 5.3.1; CSF PR.AA-05 | ASVS V8 Authorization | Code review of dependencies and role matrix; authorization test matrix |
| Audit controls | § 164.312(b) | SP 800-66r2 5.3.2; CSF PR.PS-04, DE.CM-09 | ASVS V16 Security Logging and Error Handling | Code and schema review of audit tables, triggers, privileges; tests |
| Information system activity review | § 164.308(a)(1)(ii)(D) (R) | SP 800-66r2 5.1.1; CSF DE.CM-09 | ASVS V16 | Documentation review (who reviews audit logs, how often) |
| Integrity of ePHI | § 164.312(c)(1), (c)(2) (A) | SP 800-66r2 5.3.3; CSF PR.DS-01 | ASVS V2 Validation and Business Logic, V15 Secure Coding and Architecture | Schema review (immutability, constraints); validation code; tests |
| Person or entity authentication (devices and services) | § 164.312(d) | SP 800-66r2 5.3.4; CSF PR.AA-03 | ASVS V6, V9 Self-contained Tokens | Code review of API keys and JWTs; tests |
| Transmission security | § 164.312(e)(1), (e)(2)(i) (A), (e)(2)(ii) (A) | SP 800-66r2 5.3.5; CSF PR.DS-02 | ASVS V12 Secure Communication | Configuration review (TLS, HSTS, database `sslmode`); deployment descriptors |
| API security and input validation | § 164.312(c)(1); § 164.308(a)(1)(ii)(B) | CSF PR.PS-06 | ASVS V1 Encoding and Sanitization, V2, V4 API and Web Service | SAST; code review of schemas, limits, CORS, rate limiting |
| Browser and frontend security | § 164.312(a)(1), (e)(1) | CSF PR.PS-06 | ASVS V3 Web Frontend Security | Header configuration review; frontend code review |
| Secrets management | § 164.312(d); § 164.308(a)(5)(ii)(D) (A) | CSF PR.AA-01, PR.DS-01 | ASVS V13 Configuration | Secret scanning; configuration and environment-template review |
| Database security and least privilege | § 164.312(a)(1), (c)(1) | SP 800-66r2 5.3.1, 5.3.3; CSF PR.AA-05 | ASVS V15 | Schema, role-provisioning and migration review; privilege tests |
| Device security | § 164.312(d); § 164.310(d)(1) | SP 800-66r2 5.2.4, 5.3.4; CSF PR.AA-03 | ASVS V4, V6 | Code review of device keys and device binding; tests |
| Vulnerability and dependency management | § 164.308(a)(1)(ii)(A)–(B) (R) | SP 800-66r2 5.1.1; CSF ID.RA-01, PR.PS-02 | ASVS V15 | Dependency and container scanning; CI review |
| Secure development and CI/CD | § 164.308(a)(1)(ii)(B) (R) | CSF PR.PS-06, GV.SC-05 | ASVS V15 | Workflow review (permissions, pinning, required checks) |
| Data retention and disposal | § 164.316(b)(2)(i) (documentation, 6 years); § 164.310(d)(2)(i)–(ii) (R) | SP 800-66r2 5.2.4, 5.5.2; CSF ID.AM-07 | ASVS V14 | Documentation and code review (retention decisions, purge and withdrawal paths) |
| Backup and contingency | § 164.308(a)(7)(ii)(A)–(B) (R) | SP 800-66r2 5.1.7; CSF PR.DS-11, RC.RP-01 | — | Infrastructure documentation review; restore-drill evidence |
| Security incident procedures | § 164.308(a)(6) (R) | SP 800-66r2 5.1.6; CSF RS.MA-01 | — | Documentation review (containment runbook) |
| Business associate arrangements | § 164.308(b)(1); § 164.314(a) | SP 800-66r2 5.1.9, 5.4.1; CSF GV.SC-05 | — | Vendor inventory review; BAA evidence (expected NOT DETERMINED from the repository) |
| Data minimization (voice and behavioral-health data) | § 164.502(b) minimum necessary (Privacy Rule, context) | CSF ID.AM-07, PR.DS-01 | ASVS V14 | Schema and API review; no-audio tests; wording review |

---

## 5. Verification Methodology

The assessment runs in two strands whose results are combined per control. Automated results are evidence,
not ratings: each tool finding is triaged (true positive, false positive, accepted risk) before it affects a
rating or enters the findings register.

### A. Automated Analysis

| Activity | What it checks | Notes |
|---|---|---|
| Secret scanning | Credentials, keys, tokens and connection strings in the working tree and the full Git history | Placeholder values allow-listed in `.gitleaks.toml` are reviewed, not ignored silently. |
| Dependency scanning | Known vulnerabilities in Python and npm dependencies and in the container base image | Compared with the waivers in `SECURITY_EXCEPTIONS.md`; a waived finding stays a finding, marked as accepted risk with its expiry. |
| Static application security testing (SAST) | Injection, unsafe deserialization, weak cryptography, missing authorization checks and similar code patterns | Every high-severity result is confirmed by reading the code. |
| Infrastructure review | Misconfigurations in Dockerfiles, `docker-compose.yml`, `render.yaml`, `netlify.toml` | Covers what is declared in the repository; provider-side settings are NOT DETERMINED unless documented. |
| CI/CD review | Workflow permissions, action pinning, secret handling, required security checks, presence of CodeQL and dependency review | Read from `.github/workflows/` and `.github/dependabot.yml`. |

### B. Manual Review

| Review | Method | Primary evidence |
|---|---|---|
| Authentication review | Read login, password hashing, lockout, token issuance and verification; compare with TRD 12 §4.3–4.5 | `backend/core/security.py`, `backend/services/auth_service.py`, `backend/api/auth.py`, `tests/security/` |
| Authorization review | Trace each route's dependencies; compare with the TRD 12 §4.6 role matrix and its tests | `backend/api/deps.py`, `backend/api/permissions.py`, `tests/security/test_auth_matrix.py` |
| Data-flow review | Follow a check-in from device to dashboard: entry points, storage, processing, transmission, outputs | `backend/api/ingest.py`, `backend/api/sessions.py`, `backend/services/`, `analytics/`, `frontend/` |
| Logging review | Read audit and application logging; confirm redaction, append-only storage and investigation support | `backend/services/audit_service.py`, `backend/core/logging.py`, migrations |
| Encryption review | Confirm TLS enforcement, HSTS, database `sslmode`, and documented at-rest encryption and key management | `backend/core/config.py`, `backend/core/middleware.py`, `netlify.toml`, `render.yaml`, TRD 12 §4.8 |
| Database review | Confirm roles, grants, immutability triggers, constraints and parameterized queries | `database/roles/`, `backend/alembic/versions/`, `backend/repositories/` |
| Device authentication review | Confirm per-device keys, hashing, scopes, device binding, revocation and rotation | `backend/core/security.py`, `backend/api/deps.py`, `backend/cli.py`, `tests/security/test_api_keys.py` |

Each control is assessed in four steps: (1) **design**: is the control specified (TRDs, policies)?
(2) **implementation**: does the code or configuration do it? (3) **verification**: does a test or scan prove
it? (4) **operation**: is there evidence it is in effect in the deployed environment? A control can reach PASS
on repository evidence for steps 1–3; step 4 is usually NOT DETERMINED for provider-side settings (§10).

---

## 6. Automated Tool Plan

| Tool | Purpose | Command | Expected Evidence |
|---|---|---|---|
| Gitleaks (8.x) | Secret scanning of working tree and full history | `gitleaks detect --source . --redact --report-format json --report-path gitleaks.json` | Count of findings with rule ID, file and commit (values redacted); triage of each |
| Trivy | Dependency vulnerabilities (`requirements*.txt`, `package-lock.json`), IaC and Dockerfile misconfigurations, embedded secrets | `trivy fs --scanners vuln,misconfig,secret --format json --output trivy.json .` | Severity breakdown (critical, high, medium, low); misconfiguration list; comparison with `SECURITY_EXCEPTIONS.md` |
| Semgrep | SAST for Python and TypeScript | `semgrep scan --config auto --json --output semgrep.json .` (equivalent: explicit registry rule packs, e.g. `--config p/default --config p/python --config p/typescript --config p/secrets --metrics=off`, if telemetry must be avoided) | Findings by rule and category (injection, authentication, authorization, input validation); triage notes |
| GitHub CodeQL | Semantic code scanning in GitHub | Inspect `.github/workflows/` for `github/codeql-action`; if present, read its results in the repository's Security tab | Whether CodeQL is configured; languages covered; open alerts if available |
| npm audit (applicable: `frontend/package-lock.json` exists) | Known npm vulnerabilities | `npm audit --audit-level=high` in `frontend/` | Counts by severity; comparison with the CI gate (`scripts/ci/audit_gate.py`) and waivers |
| pip-audit (applicable: `backend/requirements.txt` exists) | Known Python vulnerabilities | `pip-audit -r backend/requirements.txt --format json` | Vulnerable packages with fix versions; comparison with waivers |
| Bandit (already in CI) | Python security linting | `bandit -r backend analytics -ll` | Medium-and-higher findings (CI fails on any) |

If a tool cannot be installed or run, the assessment records that fact, the reason, and any substitute
evidence (for example, the result of the same check in the most recent CI run). Raw tool output is kept outside
the repository; the reports quote counts and triaged findings only, and never reproduce a secret value.

---

## 7. Evidence Collection Strategy

| Evidence source | What is collected | How it is cited |
|---|---|---|
| Repository files | Source code implementing a control (functions, middleware, models, migrations) | `path/to/file.py` and, where useful, the function or line |
| Configuration files | `render.yaml`, `netlify.toml`, Dockerfiles, `docker-compose.yml`, `.gitleaks.toml`, `.github/dependabot.yml` | File path and setting name |
| Environment variable references | Names of variables in `.env*.example` and `backend/core/config.py`, with the startup checks that validate them | Variable name and the check; never a value |
| CI/CD workflows | Jobs, steps, permissions and security gates in `.github/workflows/` | Workflow file and job name |
| Security findings | Triaged output of the §6 tools | Tool, rule ID, file; summarized counts |
| Infrastructure documentation | TRDs (`specs/TRD/`), `docs/deployment.md`, `docs/design/`, decision log (TRD 24) | Document and requirement ID (e.g. TRD 12 SEC-061) |
| Tests | Automated tests that prove a control | Test file and test name |

Evidence is labelled as **observed** (seen in code, configuration or a tool result), **documented** (stated in
a design document but not confirmed in code), or **assumed** (neither; such controls are rated NOT DETERMINED).
A requirement in a TRD alone is design evidence, not proof of implementation.

---

## 8. Assessment Scoring

| Rating | Criteria |
|---|---|
| **PASS** | The control is specified, implemented, and verified by observed repository evidence (code or configuration, plus a test or scan result where one is feasible). No open finding of Medium or higher severity affects it. |
| **PARTIAL** | Some of the control is implemented and evidenced, but part is missing, unverified, limited to some components, or affected by an open Medium or High finding; or the control is designed and partly implemented but awaits a planned step (for example, the AWS migration). |
| **FAIL** | The control is absent, or the evidence shows it is implemented incorrectly, or an open Critical finding defeats it. |
| **NOT DETERMINED** | The repository holds no evidence either way, typically because the control lives outside the repository (provider settings, BAAs, workforce practices) or depends on an environment not yet built. Not a negative rating, but a verification gap that must be closed by other evidence. |

Findings use five severities: **Critical** (likely exposure of ePHI or full compromise with little effort),
**High** (significant exposure or control failure requiring prompt fix), **Medium** (weakness that needs other
conditions to exploit or limits a safeguard), **Low** (hardening or best-practice gap), **Informational**
(observation, no direct risk). Because no ePHI is held today, severity reflects the risk **once live data is
present**; the reports state this explicitly.

The overall readiness rating in the final report (High, Moderate or Low Readiness) is a reasoned judgement
from the control ratings and open findings, explained in its rationale; it is not a formula.

---

## 9. Deliverables

All under `docs/hipaa/`, produced by `specs/prompts/hipaa/Implement_HIPAA_Verification.md`:

| Deliverable | Content |
|---|---|
| `HIPAA_READINESS_REPORT.md` | Executive summary with overall readiness rating, scope, methodology, architecture, automated results, data-flow review, technical safeguards, OWASP ASVS and NIST mapping, EchoWell-specific risks, findings summary, remediation roadmap, conclusion |
| `HIPAA_EVIDENCE_MATRIX.md` | One row per control: source requirement, repository evidence, file path, rating, notes |
| `FINDINGS_REGISTER.md` | One entry per finding: ID, title, severity, description, evidence, risk, recommendation |

A later stage (`specs/prompts/hipaa/HIPAA_Compliance_Readiness_Prompt.md`) extends these into an audit readiness
package (risk analysis, policies, data-flow analysis, vendor review, audit readiness plan) without overwriting
the findings above.

---

## 10. Assumptions and Limitations

- **A repository review cannot verify legal compliance.** Compliance depends on the covered entity's
  organization, policies in force, training and practices, which are not in the repository.
- **A repository review cannot verify Business Associate Agreements.** Whether a BAA exists with any vendor
  (Netlify, Render, Neon, GitHub, Sentry, AWS) is a contractual fact outside the repository; it is reported as
  NOT DETERMINED unless documented evidence is provided.
- **A repository review cannot verify production cloud configuration unless evidence exists.** Encryption at
  rest, backup retention, account MFA, network settings and log retention on the providers are rated from
  documentation only and marked NOT DETERMINED when no evidence exists.
- **Controls without evidence must be marked NOT DETERMINED.** The assessment does not infer a control from the
  absence of a contrary finding.
- The assessment covers one commit; later changes are not covered until it is repeated.
- EchoWell holds synthetic and test data only at the time of assessment, so findings describe readiness for
  live data, not current exposure.
- Team 1's devices and extraction software are outside the repository; the assessment covers only the interface
  EchoWell exposes to them.
- Automated tools produce false positives and miss issues; their results are triaged and are not a substitute
  for an independent penetration test.

Every deliverable states: *"This assessment represents a technical HIPAA readiness review based on repository
evidence and does not constitute legal certification, regulatory certification, or a formal HIPAA audit."*

## Revision History

| Version | Date | Change |
|---|---|---|
| 0.1 | 22 Nov 2026 | First draft: methodology only (PR 1 of 3). |
