## Prompt: Final Documentation Audit

Review all documentation generated for EchoWell:

- specs/TRDS/
- specs/backlog/BACKLOG.md
- specs/backlog/features/
- specs/backlog/IMPLEMENTATION_ROADMAP.md
- specs/backlog/DEPLOYMENT_CHECKLIST.md
- specs/backlog/MVP_READINESS_CHECKLIST.md

Generate:

DOCUMENTATION_COMPLETENESS_AUDIT.md

Verify:

1. Every business requirement maps to a TRD.
2. Every TRD requirement maps to a feature.
3. Every feature maps to implementation tasks.
4. Every database table is defined.
5. Every API endpoint is defined.
6. Every algorithm requirement is defined.
7. Every acceptance criterion has associated tests.
8. Every deployment step is documented.
9. No conflicting requirements exist.
10. No placeholder sections remain.

Produce a pass/fail matrix with issues and recommendations.

Frontend Verification

Verify:

Residents Overview

- Resident sorting functions
- Alarm status displays correctly
- 30-day counts display correctly
- Missing days remain visible
- Device panel displays correctly

Resident Detail

- CUSUM chart displays correctly
- Alarm line at 5.0 present
- Scored features display correctly
- Check-In log displays correctly
- Staff review section functions

New Admissions

- Facility baseline view exists
- Transition workflow documented
- Future study-arm functionality identified

Verify all wireframe requirements have been implemented.

Generate a UI_REQUIREMENTS_TRACEABILITY_MATRIX showing:

Wireframe Requirement
→ Feature
→ Component
→ API
→ Test Coverage