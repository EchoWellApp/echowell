## Prompt 1: Generate BACKLOG.md

Read all completed TRDs located in:

specs/TRDS/

Read all supporting project documents:

specs/business-requirements/
specs/data-samples/
specs/algorithm/
specs/architecture/

Your task is to generate:

specs/backlog/BACKLOG.md

Purpose:

Create the master implementation roadmap for the entire EchoWell project.

Requirements:

1. Identify every feature required to fully implement the MVP defined by the TRDs.

2. Group features into Epics:

- Infrastructure
- Database
- Backend API
- Analytics Engine
- Data Processing
- Frontend
- Authentication & Security
- Testing & Validation
- DevOps & Deployment
- Monitoring & Logging

3. For every feature assign:

- Feature ID (FEAT-001, FEAT-002, etc.)
- Feature Name
- Epic
- Description
- Priority (P0, P1, P2)
- Complexity (Low, Medium, High)
- MVP Status (Required, Optional, Future)
- Dependencies
- Referenced TRDs

4. Create a recommended implementation order.

5. Create a dependency graph showing feature dependencies.

6. Identify:

- MVP Features
- Post-MVP Features
- Future Research Features

7. Create a sprint roadmap showing which features should be implemented together.

8. Add a completion tracking section containing:

- Not Started
- In Progress
- Complete
- Blocked

9. Ensure every functional requirement defined in the TRDs maps to at least one feature.

10. Generate only BACKLOG.md.

Do not generate feature specification files yet.

## Prompt 2: Generate Individual Feature Specification Files

Read:

specs/backlog/BACKLOG.md

Read all documents under:

specs/TRDS/

Generate a feature specification document for every feature in the backlog.

Create:

specs/backlog/features/

Naming Convention:

FEAT-001-Data-Ingestion.md
FEAT-002-Session-Validation.md
FEAT-003-Baseline-Engine.md

etc.

For each feature file include:

# Feature ID and Name

## Purpose

Why this feature exists.

## Business Context

Which business requirements are satisfied.

## Referenced TRDs

List all TRDs relevant to the feature.

## Scope

Included functionality.

## Out of Scope

Explicit exclusions.

## Functional Requirements

Detailed implementation requirements.

## Inputs

Data entering the feature.

## Outputs

Data produced by the feature.

## Data Flow

Explain how information moves through the feature.

## Dependencies

Features required before implementation.

## Database Impact

Tables used.
Tables created.
Tables modified.

## API Impact

Endpoints consumed.
Endpoints exposed.

## Frontend Impact

Pages affected.
Components affected.

## Analytics Impact

Algorithms used.
Calculations performed.

## Security Requirements

Authentication requirements.
Authorization requirements.

## Error Handling

Expected failures.
Recovery strategy.

## Logging Requirements

Logs generated.
Audit records generated.

## Testing Requirements

Unit tests.
Integration tests.
Regression tests.
Algorithm validation tests.

## Acceptance Criteria

Clear pass/fail conditions.

## Definition of Done

Requirements that must be satisfied before the feature is considered complete.

## Implementation Notes

Recommendations for developers and AI coding agents.

Additional Rules:

1. Create one file per feature.
2. Do not leave placeholders.
3. Cross-reference feature dependencies.
4. Ensure every feature can be implemented independently.
5. Ensure acceptance criteria are objectively testable.
6. Derive all requirements from the TRDs.
7. Do not invent requirements that contradict the TRDs.
8. Generate all feature files in a single pass.

## Prompt 3: Generate an Implementation Roadmap for AI Coding Agents

Read:

specs/backlog/BACKLOG.md

Read:

specs/backlog/features/

Generate:

specs/backlog/IMPLEMENTATION_ROADMAP.md

Requirements:

1. Determine the optimal implementation sequence.

2. Produce implementation phases:

Phase 1 - Repository Setup
Phase 2 - Database Layer
Phase 3 - Backend API
Phase 4 - Analytics Engine
Phase 5 - Algorithm Validation
Phase 6 - Frontend
Phase 7 - Authentication
Phase 8 - Deployment
Phase 9 - Final Audit

3. For each phase identify:

- Features implemented
- Dependencies
- Deliverables
- Required tests

4. Produce AI-agent implementation prompts for each phase.

5. Produce a final deployment checklist.

6. Produce a final MVP readiness checklist.

The roadmap should allow a coding agent to build EchoWell from an empty repository to a deployable MVP.