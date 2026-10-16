# AI Agent Instructions: Generate All EchoWell TRDs

## Purpose

You are acting as a Principal Software Architect, Technical Product Manager, Solution Architect, Data Architect, DevOps Architect, QA Lead, and Technical Writer.

Your objective is to fully populate every blank TRD document under:

```text
specs/TRD/
```

using the project materials located under:

```text
specs/
```

The generated TRDs will become the source of truth used by AI coding agents to build the complete EchoWell MVP.

All specifications must be implementation-ready and detailed enough that another AI agent can build the application without requiring additional clarification.

## Documents To Analyze

Read and extract requirements from:

```text
specs/business-requirements/
    EchoWell Daily Data Storage and Processing Flowcharts.docx
    EchoWell_pipeline_test_v0_1.xlsx
    EchoWell_preprint-113062-submitted.pdf
    EchoWell_PROSPERO.pdf

specs/data-samples/
    EchoWell_pipeline_test_input_v0_1.csv
    echowell_mock_data_500.csv

specs/algorithm/
    generate_pipeline_test_v0_1.py

specs/architecture/
    Deployment_Architecture.md
```

## Architecture Requirements

Do not invent architecture.

Use the architecture specified in Deployment_Architecture.md.

Frontend:
- React
- Next.js
- Netlify

Backend:
- FastAPI
- Python
- Railway

Database:
- PostgreSQL
- Neon or Railway PostgreSQL

Repository:
- Single GitHub Monorepo

CI/CD:
- GitHub Actions

## Non-Negotiable Rules

1. Do not create additional TRD files.
2. Do not contradict project documents.
3. Every requirement must be traceable.
4. Avoid placeholders.
5. Assume implementation.

## Project Purpose

EchoWell is a voice-based monitoring platform for long-term care settings.

The platform shall ingest acoustic speech features, perform validation, build personalized baselines, compute scores, monitor trends using CUSUM, and generate alerts.

## Database Requirements

Assume PostgreSQL and generate complete schema definitions, relationships, indexes, constraints, and data models.

## API Requirements

Generate full REST API specifications including request/response schemas and authentication requirements.

## Testing Requirements

Generate unit, integration, regression, and algorithm-validation specifications using the EchoWell workbook test suite.

## Security Requirements

Define authentication, authorization, secrets management, audit logging, and HTTPS requirements.

## Deployment Requirements

Generate deployment procedures for Local, Staging, and Production environments.

## Documentation Quality Standard

Each TRD must include:

- Purpose
- Scope
- Requirements
- Assumptions
- Dependencies
- Acceptance Criteria
- Implementation Notes

All documentation must be developer-ready, AI-agent-ready, and implementation-ready.

## Execution Order

Complete TRDs in numerical order from 00_Project_Vision_and_Scope through 25_AI_Agent_Build_Instructions.
