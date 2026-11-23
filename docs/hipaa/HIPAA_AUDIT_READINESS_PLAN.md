# HIPAA Audit Readiness Plan

Document ID: ECHOWELL-HIPAA-PLAN · Version 0.1 · Date: 22 November 2026 · Owner: Team 2 (for the PI) · Status: Draft
Prompt: `specs/prompts/hipaa/HIPAA_Compliance_Readiness_Prompt.md` Phase 5 · Inputs: `FINDINGS_REGISTER.md` (HF-xx),
`HIPAA_RISK_ANALYSIS.md` (R-xx)

The plan moves EchoWell from this internal readiness assessment toward an independent HIPAA security risk
assessment and penetration test. Owners are roles; effort is approximate person-days (S ≤ 2, M 3–10, L > 10).
All actions are **PLANNED** unless stated otherwise.

## Immediate Actions (0–30 Days)

| # | Description | Owner | Priority | Dependencies | Estimated Effort |
|---|---|---|---|---|---|
| I-1 | Review and approve this package; decide which draft policies to adopt | PI, project coordinator | High | — | S |
| I-2 | Upgrade Next.js to a supported major version and remove the npm waivers (HF-01) | Team 2 frontend developer | High | Regression test pass | M |
| I-3 | Upgrade FastAPI/Starlette and remove the pip waiver (HF-02) | Team 2 backend developer | High | Regression test pass | M |
| I-4 | Run and record the restore drill; record provider administrators, MFA, plans and regions (HF-08) | Team 2 DevOps lead | High | Neon access | S |
| I-5 | Add a weekly audit-log review with saved queries to `docs/deployment.md` (HF-09, EW-POL-03) | Team 2 DevOps lead | Medium | I-1 | S |
| I-6 | Add CodeQL and dependency review; upgrade Gitleaks with a narrow allow-list entry (HF-10, HF-14) | Team 2 DevOps lead | Medium | — | S |

## Short-Term Actions (30–90 Days)

| # | Description | Owner | Priority | Dependencies | Estimated Effort |
|---|---|---|---|---|---|
| S-1 | Implement TOTP multi-factor authentication, mandatory for admins and exporters (HF-03) | Team 2 backend and frontend developers | High | TRD 12 update | M |
| S-2 | Add a dashboard idle time-out and per-token logout revocation (HF-04) | Team 2 developers | High | TRD 12 update | S–M |
| S-3 | Close OQ-01: retention per data class, backup and export expiry, disposal procedure (HF-06, EW-POL-04) | PI with IRB; data steward | High | IRB input | M |
| S-4 | Obtain Team 1's device security description and agree EW-POL-07 (HF-18, R-01) | Project coordinator, Team 1 lead | High | — | S |
| S-5 | Generate a hashed Python lock file; SHA-pin deploy-workflow actions (HF-13, HF-12) | Team 2 DevOps lead | Medium | I-3 | S |
| S-6 | Security awareness briefing for all account holders (passwords, notes without identifiers, incident reporting) | Project coordinator | Medium | I-1 | S |
| S-7 | First quarterly access review (EW-POL-01) | PI or delegate | Medium | I-1 | S |

## Medium-Term Actions (90–180 Days)

| # | Description | Owner | Priority | Dependencies | Estimated Effort |
|---|---|---|---|---|---|
| M-1 | Build the AWS production account: accept the BAA, confirm HIPAA-eligible services, root MFA, CloudTrail (HF-07) | PI, UND IT, Team 2 DevOps lead | High | AWS budget (OQ-07) | L |
| M-2 | RDS with customer-managed KMS key, encrypted backups, deletion protection, private networking; record evidence (HF-16) | Team 2 DevOps lead | High | M-1 | M |
| M-3 | Nonce-based CSP on AWS Amplify; re-assess token storage (HF-05) | Team 2 frontend developer | Medium | M-1 | M |
| M-4 | Incident response tabletop exercise (EW-POL-05) | Team 2 DevOps lead, PI | Medium | I-1 | S |
| M-5 | Repeat this internal assessment on the go-live commit; update the risk analysis | Team 2 | High | M-1 to M-3 | M |
| M-6 | Independent HIPAA security risk assessment | PI (engages provider) | High | M-5; Critical and High findings closed | External |

## Long-Term Actions (180+ Days)

| # | Description | Owner | Priority | Dependencies | Estimated Effort |
|---|---|---|---|---|---|
| L-1 | Independent penetration test of the application, API and AWS configuration; retest | PI (engages provider) | High | M-6 remediation | External |
| L-2 | Annual policy review and risk analysis update | PI, project coordinator | Medium | — | S |
| L-3 | Decide on a compliance management platform if commercial use or enterprise customers are planned | PI | Low | Funding | S (decision) |
| L-4 | Decide repository visibility for live operations (HF-17) | PI, project coordinator | Low | M-1 | S |

## Exit criteria for independent review

Ready for an external HIPAA security risk assessment when: no open Critical or High findings; MFA and idle
time-out live; retention decided; AWS BAA accepted and eligible services confirmed; restore drill and provider
settings recorded; policies approved; and the internal assessment repeated on the go-live commit.

---

*This assessment represents a technical HIPAA readiness review based on repository evidence and does not
constitute legal certification, regulatory certification, or a formal HIPAA audit.*
