# Audit Logging Policy

Policy ID: EW-POL-03 · Version 0.1 · **Status: DRAFT, not in force until approved by the PI** · Date: 22 November 2026
Aligned with: HIPAA § 164.312(b), § 164.308(a)(1)(ii)(D); NIST SP 800-66r2 5.1.1, 5.3.2; NIST CSF 2.0 PR.PS-04,
DE.CM-09

## 1. Purpose

To record security-relevant activity in EchoWell, protect those records from change, and review them regularly
so that misuse is detected and incidents can be investigated.

## 2. Scope

The `audit_logs` table, application logs, hosting-provider logs (Render now; AWS CloudWatch and CloudTrail at
go-live), GitHub organization audit logs, and error monitoring if enabled.

## 3. Definitions

- **Audit event:** one of the actions in the EchoWell audit vocabulary (TRD 12 §4.12), for example
  `auth.login.failed`, `access.denied`, `export.csv`, `user.updated`, `api_key.revoked`.
- **Application log:** structured JSON log lines written by the backend, each with a request ID.

## 4. Policy Requirements

1. **What is logged.** Every audit event writes one record with time (UTC), actor type and ID, action, entity,
   details, IP address and request ID, in the same transaction as the change it records.
2. **What is never logged.** Passwords, password hashes, tokens, API keys, connection strings, request bodies of
   ingest calls, voice-feature values and staff-note text.
3. **Protection.** Audit records are append-only (database triggers and grants). Only the read-only database role
   can read them; there is no API to change or delete them.
4. **Review.** The DevOps lead reviews audit logs **weekly** using saved queries for: failed logins and lockouts,
   `access.denied`, `export.csv`, user and role changes, API-key creation and revocation, and configuration
   changes. Findings and "no issues" are recorded with the date (planned procedure, finding HF-09).
5. **Alerts.** Bursts of failed logins, access denials or exports shall raise an alert once monitoring on AWS is in
   place (planned).
6. **Retention.** Audit logs are retained for the life of the study database and at least 6 years, or longer if
   the retention decision under OQ-01 requires; application logs for the period set in EW-POL-04.
7. **Time.** All systems use UTC from synchronized platform clocks.
8. **Investigation.** Incidents are investigated by correlating audit records with application logs by request
   ID (EW-POL-05).

## 5. Responsibilities

| Role | Responsibility |
|---|---|
| Team 2 DevOps lead | Weekly review; maintains saved queries and alerts |
| PI | Receives escalations; reviews the review record quarterly |
| Developers | Add an audit event for every new security-relevant action, using the existing vocabulary |

## 6. Compliance Expectations

Evidence: automated tests of the audit writer and immutability; the weekly review record; alert configuration
at go-live.

## 7. Exceptions Process

A missed weekly review is recorded with the reason and caught up within 7 days. Any change to what is logged
requires a TRD 12 update approved by the project coordinator.

## 8. Review Process

Reviewed annually and after any incident in which logs were insufficient.
