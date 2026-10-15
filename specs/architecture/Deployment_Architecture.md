# EchoWell Deployment Architecture

## Overview

EchoWell will be developed as a single GitHub monorepo containing the frontend, backend, analytics engine, database schema, testing framework, and documentation. This architecture prioritizes simplicity, rapid development, low operational cost, and ease of maintenance while remaining scalable enough to support future migration to AWS or another enterprise cloud provider.

---

# Repository Strategy

## Monorepo

All application components will be maintained in a single repository.

### Benefits

- Simplified project management
- Easier onboarding for new contributors
- Shared versioning between frontend and backend
- Centralized documentation
- Simplified CI/CD workflows
- Improved AI-assisted development

---

# Technology Stack

## Frontend

### Framework

- React
- Next.js

### Purpose

Provides the web-based dashboard for:

- Resident monitoring
- Alert review
- Analytics visualization
- System administration

### Hosting

- Netlify

### Justification

Netlify provides:

- Free hosting for prototype development
- Automatic deployments from GitHub
- Built-in HTTPS
- Environment variable management
- Simplified frontend deployment

---

## Backend

### Framework

- FastAPI
- Python

### Responsibilities

- Session ingestion
- Validation
- Baseline generation
- Statistical scoring
- Alert generation
- API endpoints
- Database interactions

### Hosting

- Railway

### Justification

Railway provides:

- Convenient FastAPI deployment
- Simple configuration
- GitHub integration
- Minimal DevOps overhead
- Suitable free/trial tier for MVP development

---

## Analytics Engine

### Language

- Python

### Responsibilities

- Duplicate detection
- Quality screening
- Missing session handling
- Morning adjustment
- Epoch detection
- Baseline generation
- Z-score calculation
- Composite score generation
- CUSUM monitoring
- Alert generation

### Location

Contained within the backend codebase as a dedicated analytics module.

### Justification

Python is the native language of the reference implementation and provides strong support for:

- Statistical processing
- Numerical computation
- Data analysis

---

# Database

## Database Engine

PostgreSQL

### Responsibilities

- Resident storage
- Device storage
- Session storage
- Baseline storage
- Scoring history
- Alert history

### Hosting Options

#### Preferred Prototype Options

- Neon PostgreSQL
- Railway PostgreSQL

#### Future Production Option

- AWS RDS PostgreSQL

### Justification

PostgreSQL provides:

- Strong relational modeling
- Excellent performance
- Robust querying
- Industry-standard deployment patterns

---

# Hosting Architecture

```text
                 GitHub Monorepo
                         │
        ┌────────────────┴────────────────┐
        │                                 │
        ▼                                 ▼

  Netlify Hosting                  Railway Hosting
 (React / Next.js)                 (FastAPI Backend)

        │                                 │
        └───────────────┬─────────────────┘
                        ▼

                Analytics Engine

                        ▼

                  PostgreSQL
          (Neon or Railway PostgreSQL)
Testing Infrastructure
Framework

Pytest

Test Categories
Unit Tests

Validate:

Baseline calculations
MAD calculations
Z-score calculations
Composite score calculations
CUSUM calculations
Integration Tests

Validate:

Database interactions
API endpoints
End-to-end processing
Algorithm Validation Tests

Validate outputs against:

EchoWell test dataset
Expected workbook results
CI/CD
Platform

GitHub Actions

Responsibilities

On every pull request or merge:

Run unit tests
Run integration tests
Run algorithm validation tests
Build frontend
Validate backend
Deployment Strategy
Frontend

GitHub → Netlify

Backend

GitHub → Railway

Future AWS Migration

If AWS credits or sponsorship become available, the architecture may migrate to:

Plain Text
Frontend:
AWS Amplify
 
Backend:
AWS App Runner
 
Database:
AWS RDS PostgreSQL
Migration Justification

This provides:

Enterprise scalability
Managed infrastructure
Monitoring and observability
Long-term production readiness

No significant application code changes should be required for migration.

Final Architecture Decision

Repository: Single GitHub Monorepo

Frontend: React + Next.js

Frontend Hosting: Netlify

Backend: FastAPI + Python

Backend Hosting: Railway

Database: PostgreSQL

Database Hosting: Neon or Railway PostgreSQL

Testing: Pytest

CI/CD: GitHub Actions

Future Cloud Target: AWS