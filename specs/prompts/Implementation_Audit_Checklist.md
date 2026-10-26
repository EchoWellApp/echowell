# Implementation Audit Checklist (Block 3)

These prompts were split out of `TRD_Implementation_Audit_Checklist.md`, which now covers the TRD audit only (Block 1). They build and audit the application, so they run in Block 3 (Implement Features, one PR per checkpoint), alongside `Implement_Feature_Batches.md`.

Where a step here and a phase in `Implement_Feature_Batches.md` cover the same work, run it once. TRD 25 maps each step to its build phase.

| Step here | Same work in `Implement_Feature_Batches.md` |
|---|---|
| Phase 2: Design artifacts | Phase 7 |
| Phase 3: Project skeleton | Phase 8 |
| Sprint 1: Database layer | Phase 9 |
| Sprint 2: Backend API | Phase 10 |
| Sprint 3: Analytics engine | Phase 11 |
| Sprint 4: Algorithm validation | Phase 12 |
| Sprint 5: Frontend | Phase 13 |
| Phases 14A and 14B: Audit Checklist (review only, no prompt) | Phases 14A and 14B |
| Sprint 6: Full repository audit | Phase 15 |
| Sprint 7: Backlog | `Generate_Backlog.md` |

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
```

---

## Sprint 7: Backlog

### Prompt

```text
Generate:

Project_Backlog.md

containing:

- Epic
- Feature
- User Story
- Priority
- Dependencies
```

**Action:** Do not commit changes.

---

## Phases 14A and 14B: Audit Checklist

Added on 26 Oct 2026 at the algorithm lead's request (TRD 24 D-107). This section has no prompt and is not run. The reviewer uses it on the checkpoint 8 PR (Phase 14A) and the Block 4 PR (Phase 14B). Each item repeats an output or check that the `Implement_Feature_Batches.md` prompt of that phase already names; it adds no requirement. Record each item as Pass, Fail or Not applicable, with evidence.

### Phase 14A: Deployment configuration (checkpoint 8 PR)

- [ ] Frontend: `netlify.toml`, environment templates and build configuration exist.
- [ ] Backend: Railway configuration, environment templates and startup configuration exist.
- [ ] Database: connection configuration and migration execution configuration exist.
- [ ] CI/CD: GitHub Actions workflows for tests and deployment exist.
- [ ] Docker: backend Dockerfile (and a frontend Dockerfile if needed) and `docker-compose.yml` for local development exist.
- [ ] Environment: `.env.example`, `.env.development.example` and `.env.production.example` exist.
- [ ] Security: the secrets management strategy and the environment variable documentation are written.
- [ ] `DEPLOYMENT_CONFIGURATION_GUIDE.md` covers the purpose of each generated file, required environment variables, local development, staging setup, production setup and deployment prerequisites.
- [ ] `CONFIGURATION_VALIDATION_REPORT.md` summarises every generated infrastructure artefact.
- [ ] The configurations were validated against `Deployment_Architecture.md` and checked for compatibility with FastAPI, PostgreSQL, Railway, Netlify and GitHub Actions.
- [ ] No deployment was performed; only configuration files and documentation were generated.

### Phase 14B: Deployment (Block 4 PR)

- [ ] Deployment tasks 1–12 of the prompt are done: production environment variables, database provisioned, migrations applied, backend and frontend deployments configured, CI/CD deployment workflows configured, frontend connected to backend, backend connected to PostgreSQL, startup, API connectivity, frontend functionality and database access verified.
- [ ] Post-deployment validation: the health endpoint responds, the database connection is healthy, the frontend loads, API requests succeed, authentication works (if implemented), analytics services initialise, automated tests pass and the R01–R10 validation suite still passes.
- [ ] `DEPLOYMENT_REPORT.md` includes deployment URLs, environment summary, infrastructure summary, services deployed, validation results, issues discovered, remediation steps and deployment status.
- [ ] The report ends with "DEPLOYMENT SUCCESSFUL" or "DEPLOYMENT FAILED", with justification and supporting evidence.
- [ ] Requirements and application logic were changed only where needed to fix a deployment-specific issue, and each such change is reported.
