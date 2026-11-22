You are a Healthcare Security Engineer, Application Security Engineer, Security Auditor, and Technical Compliance Analyst.

Repository:
EchoWell (current VS Code workspace)

The HIPAA verification methodology has already been defined in:

HIPAA_VERIFICATION_TRD.md

Use that methodology to perform a complete technical HIPAA readiness assessment.

This is NOT a legal certification.

Do not claim HIPAA compliance unless verifiable evidence exists.

===============================================================================
PHASE 1 - REPOSITORY DISCOVERY
===============================================================================

Analyze the entire repository.

Identify and document:

- Frontend technologies
- Backend technologies
- Database technologies
- Authentication mechanisms
- Authorization mechanisms
- Device ingestion architecture
- Analytics pipelines
- Logging implementation
- CI/CD implementation
- Secrets management approach
- Third-party integrations

Capture evidence using repository paths.

===============================================================================
PHASE 2 - AUTOMATED SECURITY ANALYSIS
===============================================================================

Run security tools when available.

If a tool is unavailable, attempt to install it. If unsuccessful after you have tried everything, document that it was not installed.

----------------------------------------------------------------------------
Gitleaks
----------------------------------------------------------------------------

Run:

gitleaks detect

Capture:
- Secret findings
- Credential exposure findings
- Risk summary

----------------------------------------------------------------------------
Trivy
----------------------------------------------------------------------------

Run:

trivy fs .

Capture:
- Dependency vulnerabilities
- Misconfigurations
- Severity breakdown

----------------------------------------------------------------------------
Semgrep
----------------------------------------------------------------------------

Run:

semgrep --config auto .

Capture:
- Security findings
- Authentication concerns
- Authorization concerns
- Input validation concerns
- Injection risks

----------------------------------------------------------------------------
CodeQL
----------------------------------------------------------------------------

Inspect:

.github/workflows

Determine:
- Whether CodeQL exists
- Whether dependency scanning exists
- Whether security scanning exists

===============================================================================
PHASE 3 - DATA FLOW REVIEW
===============================================================================

Identify and document:

- Where speech/audio enters the system
- Where speech/audio is stored
- Where speech/audio is processed
- Where speech/audio is transmitted
- Where behavioral-health metrics are stored
- Where resident or patient identifiers are stored
- Relationships between users, residents, devices, and alerts

Produce a data-flow narrative.

===============================================================================
PHASE 4 - HIPAA TECHNICAL SAFEGUARD REVIEW
===============================================================================

Evaluate:

Authentication
Authorization
Audit Controls
Integrity Controls
Transmission Security
Encryption
Database Security
Logging
Session Management
API Security
Secrets Management

For each control:

Provide:

- Assessment
- Evidence
- PASS / PARTIAL / FAIL / NOT DETERMINED
- Recommendation

===============================================================================
PHASE 5 - ECHOWELL-SPECIFIC REVIEW
===============================================================================

Specifically evaluate:

- Voice recordings
- Audio-derived features
- Voice feature storage
- Alert generation
- Device ingestion APIs
- Resident-device mappings
- Behavioral-health analytics
- Depression-risk indicators
- Mental-health-related data

Determine:

- Whether the data should likely be treated as ePHI
- Potential exposure points
- Missing safeguards
- Recommended controls

===============================================================================
PHASE 6 - CREATE EVIDENCE MATRIX
===============================================================================

Generate:

docs/hipaa/HIPAA_EVIDENCE_MATRIX.md

Columns:

| Control | Source Requirement | Repository Evidence | File Path | Assessment | Notes |

Populate with discovered evidence.

===============================================================================
PHASE 7 - CREATE FINDINGS REGISTER
===============================================================================

Generate:

docs/hipaa/FINDINGS_REGISTER.md

Severity levels:

Critical
High
Medium
Low
Informational

Each finding must contain:

- Finding ID
- Title
- Severity
- Description
- Evidence
- Risk
- Recommendation

===============================================================================
PHASE 8 - CREATE FINAL REPORT
===============================================================================

Generate:

docs/hipaa/HIPAA_READINESS_REPORT.md

Include the following sections:

# Executive Summary

Provide an overall readiness rating:

- High Readiness
- Moderate Readiness
- Low Readiness

Explain the rationale.

# Scope

# Methodology

Reference:
- HIPAA Security Rule
- NIST SP 800-66 Rev. 2
- NIST CSF
- OWASP ASVS

# System Architecture Summary

# Automated Security Assessment Results

# Data Flow Review

# HIPAA Technical Safeguards Assessment

# OWASP ASVS Assessment

# NIST Mapping Summary

# EchoWell-Specific Risk Review

# Findings Summary

Summarize:
- Critical findings
- High findings
- Medium findings
- Low findings

# Remediation Roadmap

Immediate (0–30 days)

Short-Term (30–90 days)

Long-Term (90+ days)

# Conclusion

Include the following statement verbatim:

"This assessment represents a technical HIPAA readiness review based on repository evidence and does not constitute legal certification, regulatory certification, or a formal HIPAA audit."

===============================================================================
IMPORTANT RULES
===============================================================================

- Use repository evidence whenever possible.
- Cite specific files and paths.
- Do not invent controls that cannot be verified.
- Mark unverifiable controls as NOT DETERMINED.
- Distinguish clearly between observed evidence and assumptions.
- Prefer evidence-based conclusions over best guesses.
- Generate all reports as Markdown files.
- Produce professional-quality deliverables suitable for stakeholders, faculty reviewers, or security reviewers.