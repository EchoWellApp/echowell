# TRD Audit Checklist (PR #1)

This checklist audits the TRDs only. It runs in PR #1, after the TRDs are generated and reviewed, and before any code is written.

The checklist used to also contain the design, skeleton, build-sprint and full-repository audit prompts. Those build the application and belong to PR #3, so they now live in `Implementation_Audit_Checklist.md`.

## Step 1: TRD Validation

### Prompt

```text
Review every document in specs/TRD.

Generate:

- Requirements Traceability Matrix
- Missing Requirements Report
- Contradictions Report
- Cross-Reference Validation Report

Verify:

- Database requirements support all APIs.
- APIs support all frontend requirements.
- Analytics requirements support all business requirements.
- Testing requirements validate all critical functionality.
- Deployment requirements support the architecture.

Do not modify any documents yet.

Generate findings only.
```

This catches holes before code generation.

Write the findings to `docs/reports/TRD_VALIDATION_REPORT.md` (see TRD 25, Phase 1). Give every finding a severity:

- **Critical**: would cause a wrong or unsafe build.
- **Major**: an implementer following the TRDs would very likely build something that fails its own required tests or contradicts the source documents.
- **Minor**: a genuine inconsistency that a careful implementer would resolve without harm.

The report ends with a verdict:

- **FAIL**: any Critical or Major finding.
- **PASS WITH FINDINGS**: only Minor findings.
- **PASS**: no findings.

---

## Step 2: Fix and Re-validate

### Prompt

```text
Read docs/reports/TRD_VALIDATION_REPORT.md.

Fix every finding in specs/TRD/. Make minimal edits, keep requirement IDs stable,
and apply each fix in every TRD that mentions the topic.

Record each fix in docs/reports/TRD_VALIDATION_FIXES.md, one row per finding.
```

Then run Step 1 again with a fresh reviewer that did not make the fixes.

Repeat Steps 1 and 2 until the verdict is PASS or PASS WITH FINDINGS.

---

## Step 3: Confirm the Audit Passes

The TRD audit passes when the latest `docs/reports/TRD_VALIDATION_REPORT.md`:

- has the verdict PASS or PASS WITH FINDINGS;
- shows all five checks passing;
- meets the TRD 25 Phase 1 definition of done.

Remaining Minor findings may be fixed in the same PR or carried to the PR #3 implementation audit.
