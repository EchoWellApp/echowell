# Vendor Compliance Review

Document ID: ECHOWELL-HIPAA-VENDOR · Version 0.1 · Date: 22 November 2026 · Owner: Team 2 · Status: Draft
Prompt: `specs/prompts/hipaa/HIPAA_Compliance_Readiness_Prompt.md` Phase 4 · Policy: `policies/VENDOR_MANAGEMENT_POLICY.md`

Vendors were identified from TRD 22 §4.1 (service inventory), `docs/deployment.md`, `render.yaml`,
`netlify.toml`, `.github/`, `backend/requirements.txt` and `frontend/package.json`. **No BAA and no vendor
HIPAA-eligibility statement was found in the repository; none is assumed.** "Verified" means verified from
evidence in the repository on the assessment date.

## 1. Vendor table

| Vendor | Purpose | Potential ePHI Exposure | BAA Potentially Required | Verified | Notes |
|---|---|---|---|---|---|
| GitHub (organization `EchoWellApp`) | Source code, CI/CD (Actions), Dependabot, issues | None by design: code and synthetic test data only; risk if real data were pasted into issues or CI logs | No, provided no ePHI enters GitHub | NOT VERIFIED | Public repository on the Free plan; members required to use 2FA (documented, not verified). Never paste resident data into issues, PRs or logs. |
| Netlify | Frontend hosting (interim) | None by design (TPS-002): serves the app; data passes through the browser to the API, not stored by Netlify | Yes, if it ever served the frontend for live data | NOT VERIFIED | To be replaced by AWS Amplify at go-live. No BAA evidence. |
| Render | Backend web services and nightly cron (interim, Ohio) | None by design: synthetic data only; would process all ePHI if live data were sent | Yes, if used with live data | NOT VERIFIED | Go-live is on AWS only (TPS-003). No BAA evidence. |
| Neon | PostgreSQL database (interim, `aws-us-east-1`) | None by design: synthetic data only; would store all ePHI if live data were sent | Yes, if used with live data | NOT VERIFIED | Replaced by RDS at go-live. No BAA evidence. |
| Render Postgres | Contingency database | As Neon | Yes, if used with live data | NOT VERIFIED | Not in use. |
| Google Fonts (via `next/font`) | Font files fetched at build time | None: no runtime calls from browsers, no user data | No | Verified (design): self-hosted fonts, CSP without third-party origins (`netlify.toml`) | |
| Sentry (optional) | Backend exception tracking | Low by design: PII off, bodies and headers stripped; but error context could contain identifiers | Yes, if enabled on any environment with live data | NOT VERIFIED (whether enabled) | Must stay disabled on live data until approved (SEC-127). |
| Amazon Web Services (Amplify, App Runner, ECR, RDS, KMS, Secrets Manager, CloudWatch, EventBridge, SNS, CloudTrail) | Target production platform | High: will host all ePHI after go-live | Yes: AWS BAA must be accepted and each service confirmed HIPAA-eligible (TPS-003, DEP-114) | NOT VERIFIED | Account not yet created; budget pending (OQ-07). |
| UND (identity, storage for backups designated by the PI) | Possible identity provider and designated backup storage | Medium (backups) | Internal to the university; governed by UND policy rather than a BAA | NOT VERIFIED | Confirm designated storage with UND IT. |
| Team 1 (UND Speech Study devices and extraction) | Upstream data source | High (raw audio on devices) | Internal research collaborator, not an outside vendor; covered by the IRB protocol | NOT VERIFIED | Device security not documented (HF-18). |
| Open-source libraries (PyPI, npm) | Application dependencies | None directly; supply-chain risk | No | Verified: exact pins, Dependabot, CI audit gates | See HF-01, HF-02, HF-13. |

**Not used (verified by design and CI rules):** e-mail and SMS providers (TPS-083), analytics and tracking tools
(TPS-081), external identity providers (TPS-084), cloud speech or audio services (TPS-082), LLM or other AI APIs
(TPS-080, enforced by the CI `repo-hygiene` job), third-party CDNs in the browser (TPS-085).

## 2. Verification gaps

1. **BAAs:** none evidenced for any vendor. Required for AWS before go-live; not required for the interim vendors
   as long as they never receive live data.
2. **HIPAA eligibility:** the eligibility of each AWS service on the live-data path must be checked against the
   AWS HIPAA Eligible Services Reference at go-live (DEP-114).
3. **Account security:** the number of administrators, MFA status and plan of each vendor account are documented
   as requirements but not yet recorded as verified in `docs/deployment.md` (HF-08).
4. **Sentry status:** whether Sentry is enabled on any environment is not determinable from the repository.
5. **Data location:** regions are declared in `render.yaml` (Render) and documented for Neon; Neon's region is not
   verifiable from the repository.

## 3. Next review

At the AWS go-live, whenever a vendor is added, and at least annually.

---

*This assessment represents a technical HIPAA readiness review based on repository evidence and does not
constitute legal certification, regulatory certification, or a formal HIPAA audit.*
