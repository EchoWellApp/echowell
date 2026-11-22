# HIPAA Technical Readiness Report

Document ID: ECHOWELL-HIPAA-REPORT · Version 0.2 · Date: 22 November 2026 · Owner: Team 2 · Status: Draft
Assessed commit: `b74c38e` (`main`, 20 Nov 2026) · Prompt: `specs/prompts/hipaa/Implement_HIPAA_Verification.md`
Method: `docs/hipaa/HIPAA_VERIFICATION_TRD.md` · Companion documents: `HIPAA_EVIDENCE_MATRIX.md` (46 controls),
`FINDINGS_REGISTER.md` (18 findings)

---

## Executive Summary

**Overall rating: Moderate Readiness.**

EchoWell's software was designed with security requirements from the start (TRD 12 has more than 120 security
requirements), and the code implements them closely. Of 46 controls assessed, 26 pass on observed evidence,
13 are partial, 1 fails and 6 cannot be determined from the repository. No critical finding was raised.

**Strengths, observed in code and tests:** unique accounts with argon2id password hashing, lockout and rate
limiting; a server-enforced role matrix tested cell by cell; per-device API keys stored as hashes and bound to
one device; append-only audit logging of 24 event types; immutable history tables and least-privilege database
roles; TLS enforced end to end, including to the database; strict input validation; log redaction; no raw audio
anywhere in the system; residents identified by study codes only.

**Why not High Readiness:** two high findings (critical and high vulnerabilities in the Next.js and
Starlette framework versions, currently waived until 20 December 2026), no multi-factor authentication, no
inactivity log-off, an undefined retention policy, no audit-log review procedure, and missing operational
evidence (restore drill, provider settings, BAAs). Most of these are already known and tracked in the project's
TRDs as conditions for go-live on AWS.

**Context:** EchoWell holds synthetic and test data only. These findings describe what must be done before
real resident data arrives, not a current exposure.

---

## Scope

The full repository `EchoWellApp/echowell` at commit `b74c38e`: frontend, backend, analytics engine, database
schema and roles, CI/CD workflows, deployment descriptors, environment templates, tests and design documents.

Not in scope: live provider accounts (Netlify, Render, Neon), the AWS account (not yet created), Team 1's
devices and feature extraction, organizational policies in practice, and physical safeguards.

---

## Methodology

As defined in `HIPAA_VERIFICATION_TRD.md`, against:

- **HIPAA Security Rule**, 45 CFR Part 164 Subpart C, with technical safeguards (§ 164.312) assessed in full and
  other standards where the repository holds evidence;
- **NIST SP 800-66 Rev. 2** (February 2024) for implementation guidance per standard;
- **NIST Cybersecurity Framework 2.0** (CSWP 29, February 2024) for outcome mapping;
- **OWASP ASVS 5.0.0** (May 2025), target Level 2.

Work performed on 22 November 2026: repository discovery; automated scans (§ Automated Security Assessment
Results); manual review of authentication, authorization, data flow, logging, encryption, database and device
authentication; triage of every tool finding; rating of each control as PASS, PARTIAL, FAIL or NOT DETERMINED.

---

## System Architecture Summary

| Component | Technologies | Repository paths | Handles resident data? |
|---|---|---|---|
| Frontend | Next.js 14.2.35 (App Router), React 18.3.1, TypeScript 5.6; hosted on Netlify | `frontend/`, `netlify.toml` | Displays it; stores only the session token in `sessionStorage` |
| Backend | Python 3.12, FastAPI 0.115.12, Pydantic 2.10, SQLAlchemy 2.0, slowapi, argon2-cffi, PyJWT; Render web service (Ohio) | `backend/`, `render.yaml`, `backend/Dockerfile` | Yes: receives, validates, stores and serves it |
| Analytics | Deterministic robust statistics and CUSUM in Python (NumPy); no machine learning | `analytics/`, `backend/services/pipeline_*.py`, `backend/jobs/nightly_run.py` | Yes: computes baselines, scores and alerts |
| Database | PostgreSQL 16 on Neon (`aws-us-east-1`); Alembic migrations; three roles | `database/`, `backend/alembic/`, `backend/models/` | Yes: system of record |
| CI/CD | GitHub Actions (5 workflows), Dependabot, CODEOWNERS, protected production environment | `.github/` | No (synthetic test data only) |
| Device ingestion APIs | `POST /api/v1/sessions` (one JSON record), `POST /api/v1/ingest` (CSV), API-key authentication | `backend/api/sessions.py`, `backend/api/ingest.py`, `backend/services/ingestion.py` | Yes: entry point for voice features |
| Third-party services | GitHub, Netlify, Render, Neon, Google Fonts (build time only), optional Sentry; AWS as go-live target | TRD 22 §4.1, `docs/deployment.md` | Interim services: never real data (TPS-002) |

Authentication: email and password for staff (admin, clinician, researcher), returning a 60-minute JWT; API keys
for devices and the scheduler. Authorization: role matrix enforced in FastAPI dependencies. Logging: structured
JSON application logs with redaction, plus the `audit_logs` table. Secrets: platform environment variables and
GitHub encrypted secrets; AWS Secrets Manager at go-live.

---

## Automated Security Assessment Results

Run locally on Windows on 22 November 2026 against `b74c38e`. Raw output is kept outside the repository.

| Tool | Version | Result | Triage |
|---|---|---|---|
| Gitleaks | 8.30.1 | 224 commits, 13.6 MB scanned; 2 findings | Both false positives: rule `generic-api-key` matched the text `prepare_threshold=None` in `docs/reports/CHECKPOINT_2_PROJECT_SKELETON.md` and `docs/reports/CHECKPOINT_3_DATABASE.md`. **No secret exposure.** (HF-14) |
| Trivy (`fs`, vuln + misconfig + secret) | 0.76.2 | npm: 3 critical, 11 high, 14 medium, 2 low (`next` 14.2.35, `postcss` 8.4.31); pip: 0; Dockerfiles: 2 × DS-0026 Low; secrets: 0 | npm findings are real and under waiver (HF-01). Python result is incomplete because transitive packages are not pinned (HF-13). DS-0026 has no effect on hosted services (HF-15). |
| Semgrep | 1.186.0 | 58 findings over 567 files | See below |
| pip-audit | 2.10.1 | Full resolution failed on Python 3.14 (project targets 3.12); `--no-deps` mode: no known vulnerabilities in the 15 direct pins | Misses `starlette` advisories (HF-02, HF-13). CI runs a resolving `pip-audit` on Python 3.12. |
| npm audit | — | Not run: npm not installed on the assessment machine | Trivy covered `frontend/package-lock.json`; CI runs `npm audit --audit-level=high` with the waiver gate. |
| CodeQL | — | Not configured (no `github/codeql-action` in `.github/workflows/`) | HF-10 |

**Semgrep detail.** `--config auto` requires sending usage metrics to Semgrep, so the equivalent registry packs
were used with metrics off: `p/default`, `p/python`, `p/typescript`, `p/secrets`.

| Rule | Count | Triage |
|---|---|---|
| `github-actions-mutable-action-tag` | 43 | True observation; tags of `actions/*`, `docker/*` and `microsoft/playwright` are allowed by project policy CIC-025 (HF-12) |
| `sqlalchemy-execute-raw-query`, `formatted-sql-query` | 3 + 3 | False positives: SQL built from module constants in Alembic `downgrade()` functions (`0001_initial_schema.py`, `0002_seed_config_parameters.py`); no request data |
| `avoid-sqlalchemy-text` | 1 | False positive: `backend/core/db.py` advisory-lock expression uses bound parameters |
| `pickles-in-pandas` | 2 | Not applicable to the application: offline test-data generator `specs/algorithm/generate_pipeline_test_v0_1.py` reads a pickle it wrote itself |
| `dependabot-missing-cooldown` | 4 | Informational; optional hardening |
| `directly-returned-format-string`, `detect-non-literal-regexp` | 1 + 1 | False positives: rate-limit key built from a SHA-256 digest (`backend/core/rate_limit.py`); regexp in a frontend unit test |

**CI and workflow posture.** The `security-audit` job runs Gitleaks over full history, `pip-audit`, `npm audit`
(through `scripts/ci/audit_gate.py` with time-boxed waivers) and Bandit (medium or higher fails the build). All
five workflows declare `permissions: contents: read`. Dependabot covers pip, npm, GitHub Actions and Docker.
Production deploys require a reviewer in a protected GitHub environment. No CodeQL and no dependency-review
action.

---

## Data Flow Review

**Where speech or audio enters, is stored, processed or transmitted:** nowhere in EchoWell. Audio is recorded
and reduced to numeric features on Team 1's devices, outside this repository. EchoWell has no audio column or
endpoint; `audio/*` uploads return 415; unknown fields such as `audio_base64` are rejected; CI blocks audio files;
the dashboard denies microphone access (`tests/security/test_no_audio.py`, `.github/workflows/ci.yml`).

**Narrative of one check-in:**

1. **Entry.** A device sends one record of about 30 fields (study code, device code, timestamp, quality flags
   and 21 voice features such as pitch, pauses and voice quality) to `POST /api/v1/sessions` over HTTPS with its
   API key. Bulk test data arrives as CSV at `POST /api/v1/ingest` (API key or admin).
2. **Validation.** The backend authenticates the key (hash lookup, scope, device binding), validates every field
   (`backend/services/validation.py`), and records accepted records in `raw_sessions` and rejected ones in
   `ingest_rejections`, with an `ingest.batch.received` audit row.
3. **Processing.** The nightly job (Render cron, `backend/jobs/nightly_run.py`) or an admin-triggered run builds
   each resident's personal baseline, sets aside low-quality or possibly-other-speaker check-ins, computes change
   scores and runs CUSUM to raise alerts (`analytics/`, `backend/services/pipeline_*.py`). Results go to derived
   tables (`baselines`, `scores`, `alerts`, `data_alerts`), all rebuildable from `raw_sessions`.
4. **Use.** Staff sign in to the Netlify frontend, which calls the API over HTTPS. Clinicians see resident
   status, alerts and trends, record reviews and notes (`alert_reviews`, `staff_notes`, append-only). Researchers
   view analytics and export CSV (audited as `export.csv`).
5. **Outputs.** No e-mail, SMS or push notifications (TPS-083). Backups: Neon point-in-time restore and weekly
   encrypted `pg_dump` to PI-designated storage.

**Where behavioral-health metrics are stored:** `scores`, `baselines`, `alerts`, `alert_reviews`, `data_alerts`,
`staff_notes`. **Where resident identifiers are stored:** `residents` (study code, sex, cohort, enrolment,
admission and withdrawal dates, status); `devices` and `device_assignments` link devices to residents by date;
no names, birth dates, record numbers or contact details (SEC-120). **Relationships:** a facility has residents
and devices; a device is assigned to one resident for a date range; each check-in belongs to a resident and
device; scores and alerts belong to a resident; reviews and notes link a staff user to an alert or resident;
every security event in `audit_logs` names its actor (user, API key or system).

---

## HIPAA Technical Safeguards Assessment

| Control | Assessment | Evidence | Rating | Recommendation |
|---|---|---|---|---|
| Authentication | Strong password-based authentication: argon2id, NIST 800-63B password policy, constant-time handling of unknown emails, lockout, rate limit | `backend/core/security.py`, `backend/services/auth_service.py`, `tests/security/` | PARTIAL | Add MFA (HF-03) |
| Authorization | Server-side role matrix, read from the database each request, tested for every endpoint and credential type | `backend/api/deps.py`, `tests/security/test_auth_matrix.py`, `tests/integration/test_auth_coverage.py` | PASS | — |
| Audit Controls | Append-only `audit_logs`, 24 actions, same-transaction writes, no secrets or health content | `backend/services/audit_service.py`, migration triggers, `tests/integration/db/test_audit_writer.py` | PASS | Define log review (HF-09) |
| Integrity Controls | Immutable raw and history tables, superseding notes, strict validation, rebuildable derived data | `0001_initial_schema.py`, `tests/integration/db/test_grants.py` | PASS | — |
| Transmission Security | HTTPS only, HSTS, `sslmode=require` enforced at startup, no plain ingest path | `backend/core/config.py`, `backend/core/middleware.py`, `netlify.toml` | PASS | Record edge TLS settings as evidence |
| Encryption (at rest) | Provider-managed on Neon (documented); KMS design for AWS | TRD 12 SEC-063 | NOT DETERMINED | Evidence at go-live (HF-16) |
| Database Security | Three least-privilege roles, column-level grants hiding hashes, bound parameters | `database/roles/provision_login_roles.sql`, `tests/integration/db/test_roles.py` | PASS | — |
| Logging | Structured logs with request IDs and redaction; Sentry scrubbing | `backend/core/logging.py`, `backend/core/monitoring.py` | PASS | — |
| Session Management | 60-minute JWT, no refresh, `sessionStorage`; no idle time-out; revocation only globally | `frontend/lib/auth.ts`, `backend/core/security.py` | PARTIAL | Idle time-out and `jti` deny-list (HF-04, HF-05) |
| API Security | Schema validation with forbidden extras, size and media-type limits, rate limits, strict CORS, clean errors, three anonymous routes only | `backend/core/middleware.py`, `backend/core/rate_limit.py`, `tests/security/test_cors.py` | PASS | Upgrade Starlette (HF-02) |
| Secrets Management | Platform secrets only; startup refuses weak or template secrets; Gitleaks in CI; no secrets found | `backend/core/config.py`, `.gitleaks.toml` | PASS | Upgrade CI Gitleaks (HF-14) |

---

## OWASP ASVS Assessment

Indicative chapter-level assessment against ASVS 5.0.0 Level 2 (not a full requirement-by-requirement
verification).

| Chapter | Assessment | Notes |
|---|---|---|
| V1 Encoding and Sanitization | Meets | Text-only rendering, no `dangerouslySetInnerHTML`, bound SQL parameters |
| V2 Validation and Business Logic | Meets | Pydantic with forbidden extras, range checks, CSV as text |
| V3 Web Frontend Security | Partly meets | Strong headers; CSP allows inline scripts (HF-05) |
| V4 API and Web Service | Meets | Limits, media types, rate limits, CORS |
| V5 File Handling | Meets | Only CSV accepted, size-limited, parsed as text; no files stored |
| V6 Authentication | Partly meets | No MFA (HF-03) |
| V7 Session Management | Partly meets | No idle time-out; no per-token revocation (HF-04) |
| V8 Authorization | Meets | Server-side, tested matrix |
| V9 Self-contained Tokens | Meets | Algorithm pinned; `iss`, `aud`, `exp` verified |
| V10 OAuth and OIDC | Not applicable | No OAuth (TPS-084) |
| V11 Cryptography | Meets | argon2id, SHA-256 for 256-bit keys, CSPRNG; at-rest keys at go-live (HF-16) |
| V12 Secure Communication | Meets | TLS everywhere, HSTS, database TLS |
| V13 Configuration | Partly meets | Strong startup checks; framework vulnerabilities waived (HF-01, HF-02) |
| V14 Data Protection | Partly meets | Minimization strong; retention undefined (HF-06) |
| V15 Secure Coding and Architecture | Partly meets | Pinned dependencies, Bandit; no CodeQL, no lock file (HF-10, HF-13) |
| V16 Security Logging and Error Handling | Meets | Audit trail and redaction; review procedure missing (HF-09) |
| V17 WebRTC | Not applicable | No real-time media |

---

## NIST Mapping Summary

| CSF 2.0 Function | Status | Main evidence and gaps |
|---|---|---|
| Govern (GV) | Partial | Decision log, owners and supply-chain rules exist (TRD 22, TRD 24); BAAs not yet in place (HF-07) |
| Identify (ID) | Partial | Data inventory and threat model exist; vulnerabilities identified but waived (ID.RA-01; HF-01, HF-02); formal risk analysis follows |
| Protect (PR) | Largely met | PR.AA-01/03/05, PR.DS-02, PR.PS-04/06 met; PR.AA-03 lacks MFA; PR.DS-01 and PR.DS-11 not evidenced (HF-08, HF-16) |
| Detect (DE) | Partial | Uptime and error monitoring; no audit-log review or alerting (DE.CM-09; HF-09) |
| Respond (RS) | Met (documented) | One-hour containment runbook, reporting chain, investigation by request ID |
| Recover (RC) | Partial | Restore procedure documented; drill not recorded (HF-08) |

NIST SP 800-66r2 sections covered: 5.1.1, 5.1.4, 5.1.6, 5.1.7, 5.1.8, 5.1.9 (administrative, partly), 5.2.4
(media disposal, partly) and 5.3.1–5.3.5 (all technical safeguards). Sections 5.2.1–5.2.3, 5.4 and 5.5 depend
on organizational evidence outside the repository.

---

## EchoWell-Specific Risk Review

| Data | Likely ePHI once live? | Reasoning | Exposure points | Missing safeguards | Recommended controls |
|---|---|---|---|---|---|
| Voice recordings | Yes, on the device | A voice recording of an identifiable resident is health information and can itself identify the speaker | Team 1 devices only; never in EchoWell | Device storage and deletion not documented | Team 1 to document local retention and deletion (HF-18) |
| Audio-derived features | Yes | Linked to a study code that the facility can map to a person, and collected for health monitoring; HIPAA's de-identification standard is not met while the facility holds the key | `raw_sessions`, ingest endpoints, backups | — | Keep as designed; protect backups (HF-06) |
| Voice feature storage | Yes | As above | Database, `pg_dump` files | Retention (HF-06) | Retention and backup expiry |
| Alert generation | Yes | Alerts state that a resident's voice has changed, implying a possible health change | `alerts`, dashboard | Idle log-off, MFA | HF-03, HF-04 |
| Device ingestion APIs | Carries ePHI in transit | Records include study code, timestamp and features | `POST /sessions`, `POST /ingest` | Framework vulnerabilities | HF-02 |
| Resident-device mappings | Yes | Date-ranged links between devices (with room labels) and residents | `devices`, `device_assignments` | — | Keep room labels non-identifying (SEC-123) |
| Behavioral-health analytics | Yes | Change scores relate to mood and cognition research | `scores`, `baselines`, CSV export | Export review | Audit-log review of `export.csv` (HF-09) |
| Depression-risk indicators | Not computed | EchoWell deliberately does not diagnose or score depression (TRD 00 X-03, SEC-129); it detects change from a personal baseline | — | — | Keep the wording rules |
| Mental-health-related data | Yes | Staff notes and reviews may record mood observations | `staff_notes`, `alert_reviews` | Free-text identifiers (HF-11) | Training, retention, optional pattern warning |

**Note on dates.** Enrolment, admission and withdrawal dates are among HIPAA's 18 identifiers. Combined with the
facility, they keep the data identifiable even without names; EchoWell should treat all live data as ePHI rather
than as de-identified.

---

## Findings Summary

Full entries in `FINDINGS_REGISTER.md`.

| Severity | Count | Findings |
|---|---|---|
| Critical | 0 | — |
| High | 2 | HF-01 Next.js vulnerabilities (waived); HF-02 Starlette vulnerabilities (waived) |
| Medium | 7 | HF-03 no MFA; HF-04 no idle log-off; HF-05 token reachable by scripts with inline CSP; HF-06 retention undefined; HF-07 BAAs not in place; HF-08 restore drill and provider settings not recorded; HF-09 no audit-log review |
| Low | 5 | HF-10 no CodeQL; HF-11 free-text notes; HF-12 action tags; HF-13 transitive dependencies unpinned; HF-14 old Gitleaks in CI |
| Informational | 4 | HF-15 Dockerfile HEALTHCHECK; HF-16 at-rest keys at go-live; HF-17 public repository; HF-18 device-side security |

---

## Remediation Roadmap

**Immediate (0–30 days)**
- Upgrade Next.js and FastAPI/Starlette before the 20 Dec 2026 waiver expiry, or before any real data (HF-01, HF-02).
- Run and record the restore drill; record provider administrators, MFA and settings (HF-08).
- Add a weekly audit-log review with saved queries to `docs/deployment.md` (HF-09).
- Add CodeQL and dependency review; upgrade Gitleaks in CI with a narrow allow-list entry (HF-10, HF-14).

**Short-Term (30–90 days)**
- Implement MFA for admins and exporters, and an idle time-out (HF-03, HF-04).
- Close OQ-01: retention per data class, backup expiry, disposal procedure (HF-06).
- Generate a hashed lock file for Python dependencies (HF-13); pin deploy-workflow actions by SHA (HF-12).
- Obtain Team 1's device security description (HF-18).

**Long-Term (90+ days)**
- AWS go-live: accept the BAA, confirm HIPAA-eligible services, KMS encryption, encrypted backups, deletion
  protection, and record the evidence (HF-07, HF-16).
- Nonce-based CSP at the Amplify move (HF-05); decide on repository visibility for live operations (HF-17).
- Formal HIPAA risk analysis, policies and an independent assessment (next stage of this package).

---

## Conclusion

EchoWell's codebase provides most of the technical safeguards the HIPAA Security Rule expects, and they are
backed by tests rather than intentions. The gaps are concentrated in four areas: dependency upgrades already
scheduled as go-live conditions, stronger session and login protection (MFA, idle log-off), operational evidence
(restore drill, provider settings, audit-log review), and organizational decisions outside the code (retention,
BAAs). Closing the Immediate and Short-Term items would support a High Readiness rating before any real resident
data is collected.

This assessment represents a technical HIPAA readiness review based on repository evidence and does not
constitute legal certification, regulatory certification, or a formal HIPAA audit.

---

*Sections below added in version 0.2 by `specs/prompts/hipaa/HIPAA_Compliance_Readiness_Prompt.md`. The
findings, ratings and sections above are unchanged.*

## Path to Independent HIPAA Assessment

**HIPAA has no official certification program, and there is no government-issued HIPAA certification.**
Compliance is demonstrated through evidence: implemented safeguards, risk analyses, policies, training and
independent reviews. This roadmap is a realistic path toward external validation and healthcare audit
readiness; it is not a claim of compliance.

### 1. What remains self-assessed

Everything in this package: the technical readiness assessment, evidence matrix, findings register, risk
analysis, draft policies, data-flow analysis, vendor review and audit readiness plan. All were produced by the
project team from repository evidence; none has been reviewed by an independent party.

### 2. What requires third-party validation

- That the risk analysis is complete and the safeguards are reasonable and appropriate for the organization
  (independent HIPAA security risk assessment).
- That the application, API and cloud configuration resist real attacks (penetration test).
- That vendor arrangements, including BAAs, are in place and adequate (vendor compliance review, legal review).
- That administrative safeguards (training, access reviews, incident handling) operate in practice.

### 3. Evidence package already produced

| Document | Content |
|---|---|
| `HIPAA_VERIFICATION_TRD.md` | Assessment methodology |
| `HIPAA_READINESS_REPORT.md` | This report |
| `HIPAA_EVIDENCE_MATRIX.md` | 46 controls with evidence and ratings |
| `FINDINGS_REGISTER.md` | 18 findings with recommendations |
| `HIPAA_RISK_ANALYSIS.md` | 15 risks, matrix, register, prioritized remediation |
| `policies/` (7 files) | Draft access control, encryption, audit logging, data retention, incident response, vendor management and device security policies |
| `DATA_FLOW_ANALYSIS.md` | Architecture and stage-by-stage data-flow analysis |
| `VENDOR_COMPLIANCE_REVIEW.md` | Vendor inventory with BAA and verification status |
| `HIPAA_AUDIT_READINESS_PLAN.md` | Actions by time horizon with owners and effort |
| Existing project evidence | TRD 12 security specification, TRD 22 vendor rules, `docs/deployment.md` runbook, automated security tests and CI gates |

### 4. Remaining gaps before external review

Open High findings (HF-01, HF-02); MFA and idle time-out (HF-03, HF-04); retention decision (HF-06); AWS BAA and
eligible services (HF-07); restore drill and provider settings (HF-08); audit-log review (HF-09); draft policies
not yet approved; no training or access review performed yet; Team 1 device security undocumented (HF-18).

### 5. Recommended engagement plan

| Engagement | Purpose | When |
|---|---|---|
| HIPAA Security Risk Assessment | Independent evaluation of the Security Rule risk analysis and safeguards | After the internal gaps above are closed and the AWS platform is built |
| Independent Security Assessment | Review of architecture, configuration and controls against HIPAA and NIST | Can be combined with the risk assessment |
| Penetration Test | Hands-on testing of application, API, authentication, authorization and AWS configuration, with retest | After the risk assessment's Critical and High items are fixed, before live data at scale |
| Vendor Compliance Review | Check of BAAs, HIPAA-eligible services and vendor security documentation | Before go-live |

**Estimated industry costs** (typical startup ranges supplied in the assessment brief; not independently
verified; actual quotes vary widely with organization size, system scope and provider):

| Item | Typical range |
|---|---|
| HIPAA Security Risk Assessment | $5,000–$25,000 |
| Penetration Test | $7,000–$30,000 |
| Compliance Consulting | $5,000–$50,000+ |
| Compliance Automation Platform | $5,000–$20,000 per year |

Because EchoWell is a university research system, UND's own IT security and compliance offices may be able to
perform or arrange parts of this review at lower cost; this should be asked first.

## External Validation and Independent Review Strategy

The objective is a realistic route from this internal readiness assessment to external validation. Provider
names are examples taken from the assessment brief, listed for orientation only; they are not recommendations,
and none has been contacted.

### Option 1: HIPAA Security Risk Assessment

- **Purpose:** independent evaluation of HIPAA Security Rule compliance and risk exposure.
- **Typical providers:** Clearwater, CompliancePoint, Meditology, Fortified Health Security, Impact Advisors.
- **Deliverables:** formal risk assessment report, risk register, risk prioritization, remediation
  recommendations.
- **Typical cost:** $5,000–$25,000.
- **Recommended timing:** after completion of the internal readiness assessment and remediation of major
  findings.

### Option 2: Independent Penetration Test

- **Purpose:** independent validation of application, API, authentication, authorization and infrastructure
  security.
- **Typical providers:** Bishop Fox, Coalfire, NCC Group, NetSPI, Praetorian.
- **Deliverables:** executive summary, technical findings report, severity ratings, retest validation.
- **Typical cost:** $7,000–$30,000.
- **Recommended timing:** after remediation of Critical and High findings from internal review.

### Option 3: Compliance Management Platform

- **Purpose:** ongoing collection of compliance evidence, policies, controls, vendor documentation and audit
  readiness materials.
- **Typical platforms:** Vanta, Drata, Secureframe, Thoropass, Sprinto.
- **Deliverables:** evidence repository, continuous monitoring, vendor tracking, compliance dashboards.
- **Typical cost:** $5,000–$30,000+ per year.
- **Recommended timing:** when preparing for healthcare customers, enterprise procurement reviews, SOC 2 audits
  or ongoing compliance management. Likely unnecessary while EchoWell remains a university research system.

### Recommended path for EchoWell

| Phase | Activity | Status | Expected deliverables |
|---|---|---|---|
| 1 | Internal HIPAA readiness assessment | **Current activity** (this package) | Methodology, report, evidence matrix, findings, risk analysis, draft policies, data-flow and vendor reviews, plan |
| 2 | Remediation of findings | PLANNED | Closed findings with evidence; approved policies; AWS platform with recorded settings |
| 3 | Independent HIPAA security risk assessment | PLANNED | External risk assessment report and remediation list |
| 4 | Independent penetration test | PLANNED | Penetration test report, fixes, retest letter |
| 5 | Compliance automation platform (optional) | PLANNED (optional) | Continuous evidence collection and dashboards |

### Estimated budget ranges (from the assessment brief; not independently verified)

| Path | Components | Estimated total |
|---|---|---|
| Minimum Validation Path | HIPAA Security Risk Assessment $5,000–$10,000; Penetration Test $7,000–$15,000 | $12,000–$25,000 |
| Moderate Validation Path | Risk Assessment $10,000–$20,000; Penetration Test $15,000–$30,000; Compliance Platform $5,000–$15,000/year | $30,000–$65,000 (first year) |
| Enterprise Validation Path | Risk Assessment $20,000–$25,000+; Advanced Penetration Testing $25,000–$50,000+; Compliance Platform $15,000–$30,000+/year | $60,000–$100,000+ (first year) |

For a single-facility research deployment, the Minimum Validation Path, possibly with UND support, is the
proportionate choice.

**Important:** HIPAA does not provide an official certification program; there is no government-issued HIPAA
certification. Compliance is demonstrated through evidence, implemented safeguards, risk assessments, policies,
training and independent reviews. The purpose of this roadmap is a realistic path toward external validation and
healthcare audit readiness.

## Demonstration of Due Diligence

| Area | Summary |
|---|---|
| Standards reviewed | HIPAA Security Rule (45 CFR Part 164 Subpart C); NIST SP 800-66 Rev. 2; NIST CSF 2.0; OWASP ASVS 5.0.0 |
| Evidence collected | Code, configuration, migrations, workflows, tests and design documents at commit `b74c38e`; outputs of four automated tools |
| Security controls evaluated | 46 controls: 26 PASS, 13 PARTIAL, 1 FAIL, 6 NOT DETERMINED |
| Risks identified | 15 risks: 4 High, 7 Medium, 4 Low (`HIPAA_RISK_ANALYSIS.md`) |
| Policies created | 7 policies, all **DRAFT** and not yet approved or in force |
| Data flows reviewed | 7 flows from device to dashboard, backups and administration (`DATA_FLOW_ANALYSIS.md`) |
| Security findings documented | 18 findings: 0 Critical, 2 High, 7 Medium, 5 Low, 4 Informational |
| External validation plan established | Five-phase path with budget ranges (above) |

### Completed Activities

- Assessment methodology defined (`HIPAA_VERIFICATION_TRD.md`).
- Repository discovery and architecture summary.
- Automated scans: Gitleaks, Trivy, Semgrep, pip-audit (22 Nov 2026), with triage.
- Manual review of authentication, authorization, data flow, logging, encryption, database and device
  authentication.
- Evidence matrix, findings register and readiness report.
- Internal risk analysis.
- Drafting of seven policies.
- Data-flow analysis and vendor compliance review.
- Audit readiness plan.

### Planned Activities

- Remediation of findings HF-01 to HF-18 — PLANNED
- Approval and adoption of the seven policies — PLANNED
- MFA and idle time-out — PLANNED
- Retention decision (OQ-01) — PLANNED
- Restore drill and provider-settings record — PLANNED
- Weekly audit-log review, quarterly access review, security briefing — PLANNED
- AWS platform with BAA, eligible services and KMS encryption — PLANNED
- Incident response tabletop exercise — PLANNED
- Repeat of this assessment on the go-live commit — PLANNED
- Independent risk assessment and penetration test — PLANNED

### Externally Validated Activities

**None.** No part of EchoWell's security or HIPAA readiness has been reviewed or validated by an independent party
as of 22 November 2026.

## Appendix: Healthcare Customer and Investor Readiness Summary

1. **Internal HIPAA readiness work completed.** A technical HIPAA readiness assessment of the full EchoWell
   repository against the HIPAA Security Rule, NIST SP 800-66 Rev. 2, NIST CSF 2.0 and OWASP ASVS 5.0, rated
   Moderate Readiness, with an audit readiness package (risk analysis, draft policies, data-flow and vendor
   reviews, plan).
2. **Technical assessments performed.** Secret scanning of full history (no real secrets found), dependency and
   configuration scanning, static code analysis, and manual review of every technical safeguard. EchoWell also
   runs security tests and gates on every change (authorization matrix, no-audio, CORS, tokens, transport,
   database privileges; Gitleaks, pip-audit, npm audit, Bandit).
3. **Security controls reviewed.** 46 controls. Strengths: argon2id passwords with lockout; server-enforced,
   fully tested role-based access; per-device hashed API keys; append-only audit trail; immutable raw data;
   least-privilege database roles; TLS end to end; strict input validation; log redaction; no raw audio in the
   system; study codes instead of names.
4. **Documentation package created.** Fifteen documents under `docs/hipaa/` (eight assessment documents and seven
   draft policies), plus the existing security, vendor and deployment specifications.
5. **Risk analysis completed (internal).** 15 risks with likelihood, impact, existing and recommended controls;
   4 High risks with a prioritized remediation table. Not yet independently reviewed.
6. **Gaps remaining before independent validation.** Framework upgrades (two High findings), MFA, idle
   time-out, retention decision, AWS BAA and production platform, restore drill, audit-log review, policy
   approval, training, device security documentation.
7. **Estimated costs for external validation.** Minimum path about $12,000–$25,000; moderate path about
   $30,000–$65,000 in the first year (industry ranges, not quotes).
8. **Recommended next steps.** Close the Immediate and Short-Term actions of `HIPAA_AUDIT_READINESS_PLAN.md`;
   build the AWS platform under a BAA; repeat the internal assessment; then commission an independent HIPAA
   security risk assessment followed by a penetration test.

EchoWell does not claim HIPAA compliance, HIPAA certification, audit success or external validation. It currently
holds synthetic and test data only.

This assessment represents a technical HIPAA readiness review based on repository evidence and does not
constitute legal certification, regulatory certification, or a formal HIPAA audit.
