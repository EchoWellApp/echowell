You are a Healthcare Security Engineer, Application Security Engineer, and Technical Compliance Analyst.

Repository:
EchoWell (current VS Code workspace)

Objective:
Develop a Technical Review Document (TRD) that defines how a HIPAA readiness assessment will be performed against this repository.

This is NOT a legal certification effort. The purpose is to define a structured technical verification methodology using authoritative standards.

===============================================================================
DELIVERABLE
===============================================================================

Create:

docs/hipaa/HIPAA_VERIFICATION_TRD.md

Do not perform repository analysis yet.

Only create the assessment methodology.

===============================================================================
AUTHORITATIVE SOURCES
===============================================================================

Source 1:
HHS HIPAA Security Rule Overview
https://www.hhs.gov/hipaa/for-professionals/security/index.html

Source 2:
HIPAA Security Rule Regulations (45 CFR Part 164)
https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164

Source 3:
NIST SP 800-66 Revision 2
https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-66r2.pdf

Source 4:
NIST Cybersecurity Framework (CSF)
Overview: https://www.nist.gov/cyberframework
Direct PDF: https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.29.pdf 

Source 5:
OWASP Application Security Verification Standard (ASVS)
https://owasp.org/www-project-application-security-verification-standard/

===============================================================================
REQUIRED SECTIONS
===============================================================================

# 1. Purpose

Explain:
- Why HIPAA readiness assessments are performed.
- Difference between technical readiness and legal certification.
- Scope of this evaluation.

# 2. Assessment Objectives

Define objectives for evaluating:

- Authentication
- Authorization
- Encryption
- API Security
- Database Security
- Device Security
- Logging and Auditability
- Data Retention
- Voice Data Protection
- Behavioral Health Data Protection
- Infrastructure Security

# 3. EchoWell System Components

Create placeholders for:

- Frontend
- Backend
- Analytics
- Database
- CI/CD
- Device Ingestion APIs
- Third-Party Services

These will be populated later.

# 4. Assessment Framework

Create a matrix:

| Requirement Area | HIPAA Source | NIST Source | OWASP Source | Verification Method |

Map major technical safeguards into categories.

# 5. Verification Methodology

Describe:

A. Automated Analysis

- Secret scanning
- Dependency scanning
- Static application security testing
- Infrastructure review
- CI/CD review

B. Manual Review

- Authentication review
- Authorization review
- Data-flow review
- Logging review
- Encryption review
- Database review
- Device authentication review

# 6. Automated Tool Plan

Create a table containing:

| Tool | Purpose | Command | Expected Evidence |

Include:

- Gitleaks
- Trivy
- Semgrep
- GitHub CodeQL
- npm audit (if applicable)
- pip-audit (if applicable)

# 7. Evidence Collection Strategy

Explain how evidence will be gathered:

- Repository files
- Configuration files
- Environment variable references
- CI/CD workflows
- Security findings
- Infrastructure documentation

# 8. Assessment Scoring

Define ratings:

PASS
PARTIAL
FAIL
NOT DETERMINED

Include clear criteria for each.

# 9. Deliverables

Document future outputs:

- HIPAA_READINESS_REPORT.md
- HIPAA_EVIDENCE_MATRIX.md
- FINDINGS_REGISTER.md

# 10. Assumptions and Limitations

State:

- Repository review cannot verify legal compliance.
- Repository review cannot verify BAAs.
- Repository review cannot verify production cloud configuration unless evidence exists.
- Controls without evidence must be marked NOT DETERMINED.

===============================================================================
OUTPUT REQUIREMENTS
===============================================================================

Generate a complete, professional Markdown document.

The document should be suitable for inclusion in a software engineering capstone, startup security review, or technical compliance review.

Do not perform the repository assessment yet.

Only generate HIPAA_VERIFICATION_TRD.md.