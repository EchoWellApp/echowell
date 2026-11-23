# HIPAA Security Risk Analysis

Document ID: ECHOWELL-HIPAA-RISK · Version 0.1 · Date: 22 November 2026 · Owner: Team 2 (for the PI) · Status: Draft
Prompt: `specs/prompts/hipaa/HIPAA_Compliance_Readiness_Prompt.md` Phase 1 · Inputs: `HIPAA_READINESS_REPORT.md`,
`FINDINGS_REGISTER.md` (HF-xx), TRD 12 §4.1 threat model (T-xx), TRD 24 risk register (RSK-xx)

This is an internal risk analysis in the sense of 45 CFR § 164.308(a)(1)(ii)(A), following the process in NIST
SP 800-66 Rev. 2 Section 3 (scope, data, threats, vulnerabilities, existing controls, likelihood, impact, risk)
and mapped to NIST CSF 2.0. It assesses the system **as it will be once live resident data is present**, using
the controls observed in the repository today. It is not an independent risk assessment.

## Executive Summary

Fifteen risks were identified across the device, API, database, frontend, hosting, CI/CD and people layers.
None is rated Critical. **Four are High**: exploitation of the known framework vulnerabilities (R-13), account
takeover through a stolen staff password (R-03), loss or exposure of data through backups and exports (R-10), and
loss of audio or keys from devices in residents' rooms (R-01). The rest are Medium or Low because the
repository already contains strong controls: hashed and device-bound API keys, a tested role matrix, immutable
audit logging, least-privilege database roles and end-to-end TLS.

The highest-value actions are the framework upgrades already required before go-live, MFA with an idle
time-out, a retention decision covering backups and exports, and a documented security standard for Team 1's
devices.

## Scope and method

- **Assets:** voice features and quality data in `raw_sessions`; resident identifiers and device mappings;
  scores, baselines and alerts; staff reviews and notes; staff accounts; API keys; audit logs; backups and CSV
  exports; the source code and CI/CD pipeline; Team 1 devices (outside the repository, included because they feed
  EchoWell).
- **Likelihood:** Low (unlikely within a year given controls), Medium (plausible), High (expected without action).
- **Impact:** Low (no ePHI exposed, minor disruption), Medium (limited ePHI or service loss, recoverable),
  High (exposure of many residents' ePHI, loss of integrity of clinical alerts, or regulatory breach notification).
- **Overall rating:** from the matrix below.

## Risk Matrix

| Likelihood ↓ / Impact → | Low | Medium | High |
|---|---|---|---|
| **High** | Medium | High | Critical |
| **Medium** | Low | Medium | High |
| **Low** | Low | Low | Medium |

Placement of the 15 risks:

| Likelihood ↓ / Impact → | Low | Medium | High |
|---|---|---|---|
| **High** | | | |
| **Medium** | | R-05, R-14 | R-01, R-03, R-10, R-13 |
| **Low** | R-15 | R-06, R-07, R-09, R-11 | R-02, R-04, R-08, R-12 |

## Risk Register

| Risk ID | Asset | Description | Likelihood | Impact | Overall Risk Rating | Existing Controls | Recommended Controls |
|---|---|---|---|---|---|---|---|
| R-01 | Team 1 devices; device API key | A device in a resident's room is stolen, tampered with or accessed, exposing locally held audio and its API key | Medium | High | High | Key bound to one device and scope `ingest:write`, revocable by CLI, stored server-side as SHA-256 (SEC-021–SEC-024); rotation every 365 days (SEC-057); EchoWell accepts no audio | Device security standard from Team 1 (encrypted storage, audio deleted after extraction, tamper-evident mounting); key-loss procedure in `DEVICE_SECURITY_POLICY.md` (HF-18) |
| R-02 | Device API key | A stolen key is used to submit false check-ins, distorting a resident's baseline or alerts | Low | High | Medium | Device binding (403 `DEVICE_KEY_MISMATCH`); ingest rate limit 600/minute; immutable raw data with audit rows per batch; speaker screen sets aside other voices; rebuild from raw data | Alert on ingest from unexpected times or volumes; revoke and rebuild procedure |
| R-03 | Staff accounts | A staff password is phished, guessed or reused, giving access to resident status, notes and (for admin or researcher) CSV export | Medium | High | High | argon2id; 12-character minimum and common-password list; lockout; login rate limit; deactivation within 1 working day (SEC-046) | MFA for all roles, mandatory for admin and exporters (HF-03); audit-log review of logins and exports (HF-09) |
| R-04 | Database (Neon now, RDS at go-live) | Database credentials leak or the provider is breached, exposing all stored ePHI | Low | High | Medium | Credentials only in platform secrets; TLS required; least-privilege roles; owner credentials held by two people (SEC-115); provider encryption at rest | KMS-encrypted RDS with deletion protection (HF-16); 180-day credential rotation evidence; network restriction on AWS |
| R-05 | All ePHI in the dashboard | Unauthorized access by a signed-in but unattended workstation at a nursing station | Medium | Medium | Medium | 60-minute token; token cleared when the tab closes | Idle time-out of about 15 minutes (HF-04); workstation lock policy in `ACCESS_CONTROL_POLICY.md` |
| R-06 | Voice features | Voice data leaks through logs, error monitoring or debugging output | Low | Medium | Low | Log redaction of bodies, notes and credentials (SEC-107); Sentry with PII off and scrubbing (SEC-127); audit details exclude feature values (SEC-104) | Keep Sentry disabled on live data until approved; periodic log sampling review |
| R-07 | Application logs | Logs on the hosting provider are retained too long or accessed by too many people | Low | Medium | Low | Structured logs with no bodies; provider access limited to administrators | Set log retention on AWS CloudWatch; include logs in retention policy (HF-06) |
| R-08 | ePHI and audit logs | An insider with legitimate access misuses it (browsing residents without need, bulk export) | Low | High | Medium | Role matrix; researchers read-only; exports audited; audit logs append-only; IRB-listed personnel only | Weekly audit-log review including `export.csv` and unusual reads (HF-09); annual access recertification |
| R-09 | ePHI held by vendors | A hosting or tooling vendor is compromised or handles data without a BAA | Low | Medium | Low | Interim vendors never receive real data (TPS-002); go-live only on AWS after BAA (TPS-003) | Vendor management process (`VENDOR_MANAGEMENT_POLICY.md`); record BAA and eligible services (HF-07) |
| R-10 | Backups and CSV exports | `pg_dump` files or CSV exports are copied to unmanaged storage, kept indefinitely or lost | Medium | High | High | Weekly encrypted dumps by the data steward on UND-managed workstations; dumps never committed (DEP-096); exports audited | Retention and expiry for backups and exports (HF-06); encrypted designated storage only; export register |
| R-11 | Cloud configuration | A provider setting is wrong (public database endpoint, missing encryption, weak TLS policy, admin without MFA) | Low | Medium | Low | Infrastructure as code for Render; documented settings; startup checks refuse unsafe configuration | Record and periodically re-verify provider settings (HF-08); AWS Config or equivalent at go-live |
| R-12 | Access control | An authorization flaw lets a role reach data or actions beyond its rights | Low | High | Medium | Server-side role matrix tested for every endpoint and credential; route-coverage test fails on unprotected routes | Keep tests mandatory; add CodeQL (HF-10); independent penetration test |
| R-13 | Frontend and API frameworks | Known vulnerabilities in Next.js 14.2.35 (3 critical, 11 high) and Starlette 0.46.2 are exploited | Medium | High | High | Time-boxed waiver to 20 Dec 2026 (D-159); synthetic data only; patch deadlines (SEC-156) | Major upgrades before real data (HF-01, HF-02); lock file so scanners see transitive packages (HF-13) |
| R-14 | Source code and CI/CD | A malicious dependency or compromised action runs in CI or ships in a build | Medium | Medium | Medium | Exact pins; Dependabot; `permissions: contents: read`; SHAs for non-official actions; protected production environment | Hashed lock file (HF-13); SHA-pin deploy workflows (HF-12); dependency review action (HF-10) |
| R-15 | Secrets | A secret is committed to the public repository | Low | Low | Low | Gitleaks over full history in CI; `.env` files blocked; startup refuses template secrets; 0 real secrets found (22 Nov 2026) | Upgrade Gitleaks (HF-14); confirm GitHub push protection |

Insecure API endpoints are covered by R-12 and R-13; weak access controls by R-03, R-05 and R-12; exposed secrets
by R-15; dependency vulnerabilities by R-13 and R-14.

## Prioritized Remediation Table

| Priority | Action | Risks reduced | Findings | Owner (role) | Target |
|---|---|---|---|---|---|
| 1 | Upgrade Next.js and FastAPI/Starlette; remove waivers | R-13 | HF-01, HF-02 | Team 2 DevOps lead | Before 20 Dec 2026 or any real data |
| 2 | Implement MFA and an idle time-out | R-03, R-05 | HF-03, HF-04 | Team 2 backend and frontend developers | Before go-live |
| 3 | Decide retention for all data classes, backups and exports; designate storage | R-10, R-07 | HF-06 | PI with IRB; data steward | Before go-live |
| 4 | Obtain device security standard from Team 1 | R-01, R-02 | HF-18 | Project coordinator with Team 1 lead | Before devices are deployed with residents |
| 5 | Weekly audit-log review procedure | R-08, R-03 | HF-09 | Team 2 DevOps lead | 30 days |
| 6 | Record restore drill and provider settings | R-11, R-04 | HF-08 | Team 2 DevOps lead | 30 days |
| 7 | CodeQL, dependency review, Gitleaks upgrade, lock file, SHA pins | R-12, R-14, R-15 | HF-10, HF-12–HF-14 | Team 2 DevOps lead | 60 days |
| 8 | AWS go-live controls: BAA, eligible services, KMS, backups, deletion protection | R-04, R-09, R-11 | HF-07, HF-16 | PI, UND IT, Team 2 DevOps lead | At go-live |

## Review

This analysis shall be reviewed when real data is first planned, at the AWS go-live, after any security
incident, and at least once a year.

---

*This assessment represents a technical HIPAA readiness review based on repository evidence and does not
constitute legal certification, regulatory certification, or a formal HIPAA audit.*
