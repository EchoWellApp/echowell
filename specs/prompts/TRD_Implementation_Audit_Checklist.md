# TRD Implementation Audit Checklist

## Phase 1: TRD Validation

### Prompt

```text
Review every document in specs/TRDS.

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

---

## Phase 2: Generate Technical Design Artifacts

Before writing code, have the agent generate:

```text
API Specification
Database Schema
OpenAPI Documentation
Data Models
Repository Structure
Implementation Roadmap
```

### Prompt

```text
Using all completed TRDs:

Generate:

- OpenAPI specification
- PostgreSQL schema
- Entity relationship diagram
- Backend package architecture
- Frontend component architecture
- Analytics module architecture
- Testing architecture
- Repository dependency diagram

Create these under:

docs/design/
```

At this point you'll have a true engineering design package.

---

## Phase 3: Generate the Project Skeleton

### Prompt

```text
Using all TRDs and design documents:

Generate the complete project structure.

Requirements:

- Create files only.
- Do not implement business logic yet.

Generate:

- React/Next.js scaffold
- FastAPI scaffold
- SQLAlchemy models
- Alembic migrations
- CI/CD pipeline
- Pytest framework
- Configuration files
- Docker files

Generate a production-quality skeleton.
```

### Expected Result

```text
frontend/
backend/
analytics/
tests/
database/
docs/
```

With all imports configured.

---

## Phase 4: Build Feature-by-Feature

This is the most important part.

**Do not tell Claude to build everything at once.**

Instead:

---

## Sprint 1: Database Layer

### Prompt

```text
Implement Database Layer.

Use:

06_Database_Design_TRD
20_PostgreSQL_Schema_Definition
23_Data_Model_and_Entity_Definitions

Tasks:

- SQLAlchemy Models
- Alembic migrations
- Repositories
- Database connection layer

Generate tests.

Do not implement APIs yet.
```

**Action:** Do not commit changes.

---

## Sprint 2: Backend API

### Prompt

```text
Implement Backend API.

Use:

05_Backend_API_TRD
19_API_Contracts_OpenAPI_Spec

Tasks:

- FastAPI routes
- DTOs
- Validation
- Error handling

Generate tests.
```

**Action:** Do not commit changes.

---

## Sprint 3: Analytics Engine

### Prompt

```text
Implement Analytics Engine.

Use:

07_Analytics_Engine_TRD
08_Baseline_and_Scoring_Algorithm_Spec
09_CUSUM_and_Alerting_Spec
10_Data_Ingestion_and_Validation_Spec

Tasks:

- Duplicate detection
- Quality screening
- Baseline engine
- Z-score engine
- Composite score engine
- CUSUM engine

Generate unit tests.
```

**Action:** Do not commit changes.

---

## Sprint 4: Algorithm Validation

### Prompt

```text
Implement automated algorithm validation.

Use:

13_Testing_Strategy_and_Acceptance_Criteria
14_Test_Data_and_Validation_Spec

Validate:

R01-R10

Tests must compare generated outputs against workbook expected results.
```

**Action:** Do not commit changes.

---

## Sprint 5: Frontend

### Prompt

```text
Implement frontend.

Use:

04_Frontend_TRD
11_User_Interface_UX_Spec

Build:

- Dashboard
- Resident Detail View
- Alert Review View
- Analytics Pages

Connect to backend APIs.
```

**Action:** Do not commit changes.

---

## Sprint 6: Full Repository Audit

### Prompt

```text
Perform a full repository audit.

Verify:

- Every TRD requirement is implemented.
- Every API endpoint is tested.
- Every database entity is used.
- Every acceptance criterion is satisfied.
- Deployment pipeline works.
- Frontend and backend are connected.

Generate:

TRD_Implementation_Audit.md

with pass/fail status for every requirement.

---

## Sprint 7: Deployment

### Prompt

Generate:

Project_Backlog.md

containing:

- Epic
- Feature
- User Story
- Priority
- Dependencies

**Action:** Do not commit changes.