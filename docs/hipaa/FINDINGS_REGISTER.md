# HIPAA Readiness Findings Register

Document ID: ECHOWELL-HIPAA-FIND · Version 0.1 · Date: 22 November 2026 · Owner: Team 2 · Status: Draft
Assessed commit: `b74c38e` (`main`, 20 Nov 2026) · Method: `docs/hipaa/HIPAA_VERIFICATION_TRD.md` · Related:
`HIPAA_READINESS_REPORT.md`, `HIPAA_EVIDENCE_MATRIX.md`

EchoWell holds synthetic and test data only (TRD 12 SEC-001). **Severities describe the risk once live
resident data is present**, as defined in the TRD §8. Because this repository is public, findings describe
weaknesses at the level needed to fix them and omit exploitation detail.

## Summary

| Severity | Count | IDs |
|---|---|---|
| Critical | 0 | — |
| High | 2 | HF-01, HF-02 |
| Medium | 7 | HF-03 to HF-09 |
| Low | 5 | HF-10 to HF-14 |
| Informational | 4 | HF-15 to HF-18 |

---

## High

### HF-01: Frontend framework has known critical and high vulnerabilities (waived)

| Field | Content |
|---|---|
| Severity | High |
| Description | The frontend pins `next` 14.2.35. Trivy reports 30 advisories against `frontend/package-lock.json`: 3 critical, 11 high, 14 medium, 2 low, in `next` and its bundled `postcss` 8.4.31. Fixes require a major upgrade (Next 15.5.x or 16.x). The CI gate passes only because of a time-boxed waiver. |
| Evidence | Trivy `fs` scan (22 Nov 2026); `frontend/package.json`; `SECURITY_EXCEPTIONS.md` rows 1–2 (waiver to 20 Dec 2026, decision TRD 24 D-159, accepted debt D-105 / RSK-16); `scripts/ci/audit_gate.py`. |
| Risk | Once real data is present, a framework vulnerability in the dashboard could expose session tokens or resident data to an attacker. The waiver is acceptable only while the stack holds synthetic data, as `SECURITY_EXCEPTIONS.md` itself states. |
| Recommendation | Complete the Next.js major upgrade (D-105) before any real data or public demo, as already required; re-run Trivy and `npm audit` afterwards and remove the waiver rows. Track the 20 Dec 2026 expiry. |

### HF-02: Backend framework dependency has known vulnerabilities (waived)

| Field | Content |
|---|---|
| Severity | High |
| Description | `fastapi` 0.115.12 requires `starlette` 0.46.2, which carries seven advisories (PYSEC-2026-161, -248, -249, -1941, -1942, -2280, -2281). The fix requires a FastAPI major-version line change. |
| Evidence | `backend/requirements.txt`; `SECURITY_EXCEPTIONS.md` row 3 (waiver to 20 Dec 2026, D-159). Not visible to the local scans: see HF-13. |
| Risk | Vulnerabilities in the HTTP framework sit directly in the path of every API request, including device ingestion. |
| Recommendation | Upgrade FastAPI/Starlette (D-105) before live data; add an explicit pin or lock entry for `starlette` so scanners see it (HF-13). |

---

## Medium

### HF-03: No multi-factor authentication for dashboard users

| Field | Content |
|---|---|
| Severity | Medium |
| Description | Admins, clinicians and researchers sign in with email and password only. The password controls are strong (argon2id, 12-character minimum, common-password list, lockout, rate limit), but no second factor exists, and TPS-084 excludes external identity providers. |
| Evidence | `backend/core/security.py`; `backend/services/auth_service.py`; TRD 12 §4.3 (no MFA requirement); TRD 22 TPS-084. |
| Risk | A phished or reused password gives full access for that role, including admin user management and CSV export of all resident scores. OWASP ASVS 5.0 Level 2 expects multi-factor authentication for applications of this sensitivity, and the HHS proposed Security Rule update (January 2025) would require it. |
| Recommendation | Add TOTP-based MFA, at least for admins and for any account that can export data, before go-live; or adopt the AWS identity service at migration time and update TPS-084. |

### HF-04: Automatic logoff is limited to a fixed token lifetime

| Field | Content |
|---|---|
| Severity | Medium |
| Description | Sessions end when the 60-minute JWT expires or the tab closes (`sessionStorage`). There is no inactivity time-out: an unattended, signed-in workstation at a nursing station stays usable for up to 60 minutes. There is also no server-side revocation of a single token except by rotating JWT_SECRET for everyone. |
| Evidence | `backend/core/security.py` (60-minute `exp`); `frontend/lib/auth.ts`; TRD 12 SEC-032, SEC-035, SEC-037. |
| Risk | Shared clinical workstations are the typical setting; § 164.312(a)(2)(iii) (addressable) expects sessions to end after a period of inactivity. |
| Recommendation | Add a client-side idle time-out (for example 15 minutes, configurable) that clears the token, and consider a short server-side deny-list keyed on `jti` for logout. Document the chosen idle period as the addressable-specification decision. |

### HF-05: Session token is reachable from page scripts while the CSP allows inline scripts

| Field | Content |
|---|---|
| Severity | Medium |
| Description | The access token is kept in `sessionStorage` (no cookies, so no CSRF), and the Content-Security-Policy allows `script-src 'unsafe-inline'` because Next.js App Router emits inline hydration scripts. Any cross-site scripting flaw could read the token. Mitigations are strong (`react/no-danger`, text-only rendering, no third-party scripts), and the trade-off is recorded. |
| Evidence | `netlify.toml` CSP; `frontend/lib/auth.ts`; TRD 12 SEC-037, SEC-074 to SEC-076, SEC-075 (accepted risk RSK-07). |
| Risk | Token theft would allow access as the victim for up to 60 minutes. |
| Recommendation | Adopt a nonce-based CSP at the AWS Amplify move as SEC-075 plans; re-assess the token storage choice at that point. |

### HF-06: Retention and disposal of resident data are undefined

| Field | Content |
|---|---|
| Severity | Medium |
| Description | No retention period exists for features, scores, alerts, staff notes or audit logs. The question is open (TRD 24 OQ-01, owner: grant team), no deletion job runs (SEC-181), and audit logs are kept for the life of the study database (SEC-106). Purge and withdrawal paths exist (`purge-resident`, `resident.withdrawn`, refusal of new data for withdrawn residents). |
| Evidence | TRD 24 OQ-01; TRD 12 SEC-106, SEC-126, SEC-181; `docs/deployment.md` "Research-data governance"; `backend/cli.py` (purge). |
| Risk | Without a retention rule, ePHI accumulates indefinitely, including in weekly `pg_dump` backups, which widens the impact of any breach. HIPAA requires security documentation to be kept 6 years (§ 164.316(b)(2)(i)) and media disposal procedures (§ 164.310(d)(2)(i)). |
| Recommendation | Close OQ-01 with the PI and IRB before go-live: retention per data class, backup expiry, and a documented disposal procedure; implement any deletion job only after that decision. |

### HF-07: Business Associate Agreements are not yet in place for the go-live platform

| Field | Content |
|---|---|
| Severity | Medium |
| Description | No vendor currently holds real data, and the design forbids it on Netlify, Render, Neon and Sentry (TPS-002). Go-live requires acceptance of the AWS BAA and confirmation of HIPAA-eligible services (TPS-003, DEP-114). No BAA evidence exists in the repository, and GitHub, which holds code and CI logs, is assumed never to receive ePHI. |
| Evidence | TRD 22 §4.1, TPS-002, TPS-003; TRD 15 DEP-114; TRD 24 RSK-14. |
| Risk | Pointing a live device at any environment before the BAA is accepted would place ePHI with a vendor without the required contract (§ 164.308(b)(1), § 164.314(a)). |
| Recommendation | Keep the go-live gate as designed; record the BAA acceptance date and the eligible-services check in `docs/deployment.md` when done. Rated NOT DETERMINED until then. |

### HF-08: Restore drill and provider-setting verification not yet recorded

| Field | Content |
|---|---|
| Severity | Medium |
| Description | The restore drill (DEP-097) was due before 15 Nov 2026 and is not recorded; `docs/deployment.md` still says "recorded in Phase 10" for provider plans, administrators, MFA and limits (TPS-006, TPS-007). The checkpoint 9 audit already noted the drill as not run. |
| Evidence | `docs/deployment.md` "Backups and restore", "Service accounts"; `docs/reports/TRD_Implementation_Audit.md` (DB-051). |
| Risk | Contingency planning (§ 164.308(a)(7)) and account security cannot be shown; an untested restore may fail when needed. |
| Recommendation | Run the drill on a Neon branch and record row counts, schema diff and validation result; fill in the "Verified on" column, including administrator MFA, for every service. |

### HF-09: No defined review of audit logs

| Field | Content |
|---|---|
| Severity | Medium |
| Description | Audit logging is thorough and append-only, but no procedure says who reviews `audit_logs`, how often, or what to look for (failed logins, `access.denied`, exports, role changes). Monitoring covers uptime, deploys, application errors and pipeline health only. Audit logs are readable only through the `echowell_readonly` database role (SEC-105). |
| Evidence | `docs/deployment.md` "Monitoring and alerts"; TRD 12 §4.12, SEC-105. |
| Risk | § 164.308(a)(1)(ii)(D) (required) expects regular review of information-system activity; suspicious access could go unnoticed. |
| Recommendation | Add a weekly audit-log review to the runbook with a few saved queries, and consider an alert on bursts of `auth.login.failed`, `access.denied` or `export.csv`. |

---

## Low

### HF-10: No GitHub code scanning (CodeQL) or dependency review

| Field | Content |
|---|---|
| Severity | Low |
| Description | No workflow uses `github/codeql-action` or `actions/dependency-review-action`. SAST in CI is Bandit (Python only); the TypeScript frontend has the ESLint `react/no-danger` rule but no SAST. Secret scanning with push protection (SEC-053, "where the plan allows") cannot be confirmed from the repository. |
| Evidence | `.github/workflows/*.yml`; `.github/workflows/ci.yml` job `security-audit`. |
| Risk | Code-level flaws in the frontend and cross-file data-flow issues in the backend are less likely to be caught before merge. |
| Recommendation | Add a CodeQL workflow (Python and JavaScript/TypeScript; free for public repositories) and the dependency-review action on pull requests; confirm push protection in repository settings. |

### HF-11: Free-text staff notes may capture identifiers

| Field | Content |
|---|---|
| Severity | Low |
| Description | Staff notes are free text up to 2000 characters. The form shows "Do not enter names or other identifying details." and notes never appear in logs or audit details, but nothing on the server detects names or other identifiers. |
| Evidence | TRD 12 SEC-104, SEC-124; `backend/services/note_service.py`; `backend/core/logging.py` (`note` redacted). |
| Risk | Notes are the one place where direct identifiers and sensitive mental-health observations can enter EchoWell. |
| Recommendation | Keep the hint; cover notes in staff training; consider a simple server-side warning for patterns such as dates of birth or phone numbers. Include notes explicitly in the retention decision (HF-06). |

### HF-12: Third-party actions use mutable major-version tags

| Field | Content |
|---|---|
| Severity | Low |
| Description | Semgrep reports 43 action references by tag (for example `actions/checkout@v7`). The project policy (TRD 16 CIC-025, SEC-154) deliberately allows major tags for `actions/*`, `docker/*` and `microsoft/playwright` and requires SHAs for all others; no other publishers are used. Workflows declare `permissions: contents: read`. |
| Evidence | Semgrep rule `github-actions-mutable-action-tag`; `.github/workflows/*.yml`. |
| Risk | A compromised tag of a trusted publisher would run in CI with the job's secrets (deploy jobs hold platform tokens). |
| Recommendation | Pin the deploy workflows' actions to full SHAs (Dependabot keeps them current); keep the policy for read-only CI jobs if preferred. |

### HF-13: Transitive Python dependencies are invisible to scanners

| Field | Content |
|---|---|
| Severity | Low |
| Description | `backend/requirements.txt` pins direct dependencies only. `pip-audit --no-deps` and Trivy found no Python vulnerabilities, yet `starlette` (HF-02) is vulnerable, because it is not listed. The full resolution failed locally on Python 3.14 (the project targets 3.12). |
| Evidence | Local `pip-audit` and Trivy runs (22 Nov 2026); `backend/requirements.txt`. CI runs `pip-audit` on Python 3.12 with resolution, which does see transitive packages. |
| Risk | Local and third-party scans under-report Python risk. |
| Recommendation | Generate a fully pinned, hashed lock file (for example `pip-compile --generate-hashes`) and scan that. |

### HF-14: CI secret scanner is an older version

| Field | Content |
|---|---|
| Severity | Low |
| Description | CI runs Gitleaks 8.18.4. Gitleaks 8.30.1 scanned 224 commits and reported 2 findings, both false positives (`generic-api-key` matching the text `prepare_threshold=None` in `docs/reports/CHECKPOINT_2_PROJECT_SKELETON.md` and `docs/reports/CHECKPOINT_3_DATABASE.md`). No real secret was found. |
| Evidence | Local Gitleaks run (redacted); `.github/workflows/ci.yml` step "Secret scan"; `.gitleaks.toml`. |
| Risk | Newer rules catch more secret formats; upgrading without an exact allow-list entry would break CI on these false positives. |
| Recommendation | Upgrade Gitleaks in CI and add a narrow regex allow-list entry for `prepare_threshold=None` (not a path, per `.gitleaks.toml`). |

---

## Informational

### HF-15: Container images declare no HEALTHCHECK

| Field | Content |
|---|---|
| Severity | Informational |
| Description | Trivy DS-0026 (Low) on `backend/Dockerfile` and `frontend/Dockerfile`. Render and AWS App Runner use their own HTTP health checks (`/api/v1/health`), so this has no effect on the deployed services. |
| Evidence | Trivy misconfiguration scan; `render.yaml`. |
| Risk | None material. |
| Recommendation | Optional: add a HEALTHCHECK for local Docker Compose use. |

### HF-16: Encryption at rest and key management rely on provider defaults until AWS

| Field | Content |
|---|---|
| Severity | Informational |
| Description | The interim stack relies on Neon's provider-managed storage encryption; customer-managed KMS keys, encrypted backups and deletion protection are specified for AWS (SEC-063, SEC-161) but not built. No repository evidence shows the provider settings. |
| Evidence | TRD 12 SEC-063, SEC-161; TRD 15 §AWS target. |
| Risk | None today (synthetic data); must be verified at go-live. |
| Recommendation | Record KMS key, RDS encryption and backup settings as evidence when the AWS account is built. |

### HF-17: Security documentation is in a public repository

| Field | Content |
|---|---|
| Severity | Informational |
| Description | The repository is public (GitHub Free organization). The TRDs, runbook and these reports describe the security design in detail. Design transparency is not itself a weakness, and post-incident notes are already kept private (SEC-173). |
| Evidence | `docs/deployment.md` "Service accounts"; TRD 12 SEC-173. |
| Risk | Attackers can study the design; operational details (hostnames, schedules, open findings) aid targeting. |
| Recommendation | Keep open findings and operational specifics of the live platform in a private space once real data exists, or make the repository private at go-live. |

### HF-18: Device-side security is outside the repository

| Field | Content |
|---|---|
| Severity | Informational |
| Description | Server-side device controls are strong (per-device hashed keys, scopes, device binding, revocation, HTTPS only, no audio accepted). How Team 1's devices store their API key, protect locally recorded audio and delete it after feature extraction is not in this repository. |
| Evidence | `backend/core/security.py`; `backend/api/deps.py`; `tests/security/test_api_keys.py`, `test_no_audio.py`. |
| Risk | Raw audio and a device key live on hardware in residents' rooms; that is likely the highest-sensitivity asset in the overall study. |
| Recommendation | Ask Team 1 to document device key storage, local audio retention and deletion, and physical protection; include the devices in the HIPAA risk analysis. |

---

*This assessment represents a technical HIPAA readiness review based on repository evidence and does not
constitute legal certification, regulatory certification, or a formal HIPAA audit.*
