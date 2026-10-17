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

## Frontend Requirements

The application shall be based on the official wireframes located in:

specs/UI-wireframe/

Read all HTML wireframe files and treat them as source-of-truth UI requirements.

The application must contain three primary views:

1. Residents Overview Page
2. Resident Detail Page
3. New Admissions Page

Residents Overview Page Requirements

The page shall display:

- All enrolled residents.
- Sort controls for:
  - Alarm status
  - Resident ID
  - Date of last check-in

Each resident row shall display:

- Resident ID
- Alarm Status

Valid status values:

- Alarm On
- No Alarm
- Baseline Still Forming

Display the previous 30 days of activity:

- Used Sessions
- Set Aside Sessions
- Quarantined Sessions
- Missed Days

Requirements:

- Missing days must remain visible.
- Missing data shall never be backfilled.
- Counts must accurately reflect pipeline results.

Device Monitoring Panel

Display:

- Assigned device
- Shared devices
- Device sharing relationships
- Device silent periods
- Days with no device activity

The panel must support validation against the pipeline mock datasets.

Resident Detail Page Requirements

Primary Visualization:

- Running CUSUM tally
- Alarm threshold line at 5.0

The chart must make visible:

- Baseline period
- Score progression
- Alarm triggers
- Alarm persistence

Scored Features Section

Display only the 7 scored measurements in plain language.

Examples:

- Quieter
- More pauses

Additional requirements:

- Remaining 12 measurements must be stored
- Remaining 12 measurements are not shown in scoring summary

Baseline Information

Display:

- Baseline status
- Baseline formation progress
- Baseline freeze indicator

Requirements:

- Residents must only be compared against their own frozen baseline
- Baseline must never drift after freeze

Check-In Log

Display:

- Alarms
- Set-Asides
- Quarantines
- Missed Days
- Baseline Restarts

Staff Review Section

Allow staff notes documenting:

- Observations
- Actions taken
- Follow-up activity

New Admissions Page Requirements

Purpose:

Support future study-arm functionality.

Display:

- Newly admitted residents
- Facility comparison baseline

Requirements:

- New residents are compared against facility-level ranges until their personal baseline forms
- Once baseline forms, resident transitions to main resident list
- Mark this area as future/experimental functionality

Generate detailed UI specifications that match these requirements exactly.

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
