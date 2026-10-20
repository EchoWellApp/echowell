# Phase 7: Generate Design Docs

## Prompt

Read all finalized documentation:

- specs/TRD/
- specs/backlog/BACKLOG.md
- specs/backlog/features/

Generate:

docs/design/

Create:

- OpenAPI_Spec.md
- Database_ERD.md
- Backend_Architecture.md
- Frontend_Architecture.md
- Analytics_Architecture.md
- Testing_Architecture.md
- Deployment_Architecture.md
- Repository_Structure.md

Requirements:

1. Design documents must be implementation-ready.
2. All API endpoints must map to backend services.
3. All database entities must map to APIs and analytics modules.
4. All frontend pages must map to APIs.
5. All diagrams should be represented using Mermaid where possible.
6. No placeholders.
7. Cross-reference relevant TRDs and feature specifications.

Output only design documents.

UI Design Requirements

Read:

specs/UI-wireframe/

Generate:

docs/design/UI_Architecture.md

Include:

- Page hierarchy
- Navigation architecture
- Component hierarchy
- State management design
- Data flow diagrams

Generate screen designs for:

1. Residents Overview
2. Resident Detail
3. New Admissions

Document:

- Tables
- Filters
- Sorting logic
- Device panel
- CUSUM visualization
- Alert indicators
- Baseline status displays
- Staff review workflow

Map every UI component to supporting APIs and database entities.

# Phase 8: Generate Project Skeleton

## Prompt

```text
Read:

- specs/TRD/
- specs/backlog/
- docs/design/

Generate the complete project skeleton.

Requirements:

Repository Structure:

frontend/
backend/
analytics/
database/
tests/
docs/

Frontend:

- Next.js
- React
- TypeScript
- ESLint
- Prettier

Backend:

- FastAPI
- SQLAlchemy
- Alembic
- Pydantic

Testing:

- Pytest
- Test directories
- Test configuration

Infrastructure:

- Dockerfiles
- docker-compose.yml
- environment templates
- GitHub Actions

Do not implement business logic.

Create only the production-quality project structure and configuration files.

Generate all required imports, wiring, dependency injection, and startup configuration.
```

# Phase 9: Implement Database Layer

## Prompt

```text
Read:

- specs/TRD/
- specs/backlog/features/
- docs/design/

Implement all database-related features.

Requirements:

Generate:

- SQLAlchemy models
- Database connection layer
- Repository layer
- Alembic migrations
- Database configuration
- Seed framework

Implement:

- Residents
- Devices
- RawSessions
- ProcessedSessions
- Baselines
- Scores
- CusumState
- Alerts
- Users
- AuditLogs

Requirements:

1. All tables must match documented schema definitions.
2. All relationships must be implemented.
3. Primary and foreign keys must be enforced.
4. Indexes must be created.
5. Generate unit tests.
6. Update backlog completion status.
7. Generate DATABASE_IMPLEMENTATION_REPORT.md.

Do not implement APIs yet.
```

# Phase 10: Implement Backend Layer

## Prompt

```text
Read:

- specs/TRD/
- specs/backlog/features/
- docs/design/

Implement all backend features.

Generate:

- FastAPI application
- Route handlers
- Service layer
- Validation layer
- DTOs
- Request schemas
- Response schemas
- Error handling

Implement APIs:

GET /health
GET /residents
GET /residents/{id}
GET /alerts
GET /scores
GET /analytics
POST /sessions
POST /ingest

Requirements:

1. Match OpenAPI specification exactly.
2. Implement validation rules.
3. Implement structured error responses.
4. Implement logging.
5. Implement database integration.
6. Generate integration tests.
7. Update backlog status.
8. Generate BACKEND_IMPLEMENTATION_REPORT.md.
```

# Phase 11: Implement Analytics Engine

## Prompt

```text
Read:

- specs/TRD/
- specs/backlog/features/
- docs/design/
- EchoWell_pipeline_test_v0_1.xlsx
- generate_pipeline_test_v0_1.py

Implement the full analytics engine.

Modules:

- Duplicate Detection
- Quality Screening
- Morning Adjustment
- Epoch Detection
- Baseline Engine
- Robust Statistics
- Z Score Engine
- Composite Score Engine
- CUSUM Engine
- Alert Engine

Requirements:

Implement algorithms exactly as defined in the workbook and generator script.

Compute:

- Median
- MAD
- Robust Spread
- Composite Score
- Composite Z
- CUSUM

Rules:

- Duplicate handling
- Quality screening
- Morning offsets
- Epoch resets
- Baseline freeze logic
- Alarm thresholds

Generate:

- Unit tests
- Analytics test framework
- ANALYTICS_IMPLEMENTATION_REPORT.md

Update feature status when complete.
```
# Phase 12: Pass R01-R10 Validation Tests

## Prompt

```text
Read:

- EchoWell_pipeline_test_v0_1.xlsx
- EchoWell_pipeline_test_input_v0_1.csv
- generate_pipeline_test_v0_1.py

Implement and execute all validation tests.

Requirements:

Validate:

- R01
- R02
- R03
- R04
- R05
- R06
- R07
- R08
- R09
- R10

Testing Requirements:

1. Run the generated pipeline against test data.
2. Compare output to workbook expected results.
3. Compare alarm behavior.
4. Compare baseline calculations.
5. Compare status counts.
6. Verify all acceptance criteria pass.

Generate:

ALGORITHM_VALIDATION_REPORT.md

Include:

- Test Results
- Passed Cases
- Failed Cases
- Root Cause Analysis
- Recommended Fixes

Do not proceed until all validation tests pass.
```

# Phase 13: Implement Frontend

## Prompt

Read:

- specs/TRD/
- specs/backlog/features/
- docs/design/
- specs/UI-wireframe/

Implement all frontend features.

Technology:

- React
- Next.js
- TypeScript

The UI must match the provided wireframes.

Build:

1. Residents Overview Page
2. Resident Detail Page
3. New Admissions Page

Residents Overview Requirements

Display:

- All enrolled residents

Sorting:

- Alarm Status
- Resident ID
- Last Check-In Date

Status Values:

- Alarm On
- No Alarm
- Baseline Still Forming

Each row shall display:

- Resident ID
- Alarm Status
- 30 Day Used Count
- 30 Day Set Aside Count
- 30 Day Quarantined Count
- 30 Day Missed Count

Missing Data Requirements:

- Missing days remain visible
- Missing data is never hidden
- Missing data is never backfilled

Device Monitoring Panel

Display:

- Device Assignment
- Shared Devices
- Device Silence Periods
- Device Activity Status

Resident Detail Requirements

Implement a CUSUM trend visualization.

Display:

- Running CUSUM tally
- Alarm threshold line at 5.0
- Alarm trigger points

Display scored measurements using plain language descriptions.

Examples:

- Quieter
- More Pauses

Display:

- Baseline status
- Baseline progress
- Baseline freeze state

Implement Check-In Log:

- Alarms
- Set-Asides
- Quarantines
- Missed Days
- Baseline Restarts

Implement Staff Review Section:

- Notes
- Interventions
- Follow-Up Actions

New Admissions Requirements

Display:

- Residents awaiting baseline formation
- Facility comparison ranges
- Admission status

Requirements:

- Resident transitions automatically after baseline completion
- Clearly label page as future study-arm functionality

General UI Requirements

- Responsive layout
- Accessible design
- Loading states
- Error states
- Empty states

Data Integration

Connect all pages to backend APIs.

Requirements:

- Real data only
- No mock values in production builds

Testing

Generate:

- Component Tests
- Page Tests
- API Integration Tests
- End-to-End UI Tests

Generate:

FRONTEND_IMPLEMENTATION_REPORT.md

Update feature completion status.

# Phase 14A: Generate Deployment Configuration & Infrastructure Files

## Prompt

Read:

- specs/TRD/
- specs/backlog/
- docs/design/
- specs/architecture/Deployment_Architecture.md

Generate all deployment and infrastructure configuration files required for EchoWell.

Target Architecture:

Frontend:
- Netlify

Backend:
- Railway

Database:
- Neon PostgreSQL (preferred)
  or Railway PostgreSQL

Generate:

Frontend:
- netlify.toml
- environment templates
- build configuration

Backend:
- Railway configuration
- environment templates
- startup configuration

Database:
- database connection configuration
- migration execution configuration

CI/CD:
- GitHub Actions workflows
- test automation workflows
- deployment workflows

Docker:
- Dockerfile (frontend if needed)
- Dockerfile (backend)
- docker-compose.yml for local development

Environment:
- .env.example
- .env.development.example
- .env.production.example

Security:
- secrets management strategy
- environment variable documentation

Documentation:

Generate:

DEPLOYMENT_CONFIGURATION_GUIDE.md

Include:

- Purpose of each generated file
- Required environment variables
- Local development setup
- Staging setup
- Production setup
- Deployment prerequisites

Requirements:

1. Do not perform deployment.
2. Only generate configuration files and documentation.
3. Validate configurations against Deployment_Architecture.md.
4. Verify compatibility with FastAPI, PostgreSQL, Railway, Netlify, and GitHub Actions.
5. Generate CONFIGURATION_VALIDATION_REPORT.md summarizing all generated infrastructure artifacts.

# Phase 14B: Deploy Application

## Prompt

Read:

- Deployment_Architecture.md
- DEPLOYMENT_CONFIGURATION_GUIDE.md
- DEPLOYMENT_CHECKLIST.md
- MVP_READINESS_CHECKLIST.md

Review:

- Source code
- Deployment configuration files
- CI/CD configuration
- Environment variable templates

Deploy the EchoWell MVP.

Deployment Targets:

Frontend:
- Netlify

Backend:
- Railway

Database:
- Neon PostgreSQL
  or Railway PostgreSQL

Deployment Tasks:

1. Configure production environment variables.
2. Provision database.
3. Apply database migrations.
4. Configure backend deployment.
5. Configure frontend deployment.
6. Configure CI/CD deployment workflows.
7. Connect frontend to backend.
8. Connect backend to PostgreSQL.
9. Verify application startup.
10. Verify API connectivity.
11. Verify frontend functionality.
12. Verify database access.

Post-Deployment Validation:

- Health endpoint responds successfully.
- Database connection is healthy.
- Frontend loads successfully.
- API requests succeed.
- Authentication functions correctly (if implemented).
- Analytics services initialize successfully.
- Automated tests pass.
- R01–R10 validation suite remains passing.

Generate:

DEPLOYMENT_REPORT.md

Include:

- Deployment URLs
- Environment summary
- Infrastructure summary
- Services deployed
- Validation results
- Issues discovered
- Remediation steps
- Deployment status

Provide one of the following final outcomes:

DEPLOYMENT SUCCESSFUL

or

DEPLOYMENT FAILED

with justification and supporting evidence.

Do not modify requirements or application logic during deployment unless required to resolve deployment-specific issues.

# Phase 15: Run Final Audit

## Prompt

```text
Perform a complete implementation audit.

Review:

- specs/TRD/
- specs/backlog/
- docs/design/
- source code
- test results
- deployment configuration

Verify:

Requirements:

1. Every TRD requirement is implemented.
2. Every feature specification is implemented.
3. Every API endpoint is functional.
4. Every database entity is implemented.
5. Every analytics module is implemented.
6. All R01-R10 tests pass.
7. Frontend connects successfully to backend.
8. Deployment is operational.
9. CI/CD pipeline functions.
10. MVP readiness checklist passes.

Generate:

FINAL_IMPLEMENTATION_AUDIT.md

Include:

- Requirements Traceability Matrix
- Pass/Fail Status
- Missing Functionality
- Risks
- Technical Debt
- Overall MVP Readiness Assessment

Provide a final recommendation:

READY FOR DEMO
or
NOT READY FOR DEMO

with justification.
```