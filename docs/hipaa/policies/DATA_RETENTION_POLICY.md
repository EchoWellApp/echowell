# Data Retention Policy

Policy ID: EW-POL-04 · Version 0.1 · **Status: DRAFT, not in force until approved by the PI and consistent with the IRB protocol** · Date: 22 November 2026
Aligned with: HIPAA § 164.310(d)(2)(i)–(ii), § 164.316(b)(2)(i); NIST SP 800-66r2 5.2.4, 5.5.2; NIST CSF 2.0
ID.AM-07, PR.DS-11

## 1. Purpose

To keep resident data only as long as the study needs it, dispose of it securely, and keep security
documentation as long as HIPAA requires.

## 2. Scope

All EchoWell data classes, in the database, backups, exports and logs, and EchoWell security documentation.

## 3. Definitions

- **Retention period:** how long a data class is kept before deletion or de-identification.
- **Disposal:** deletion that makes data unrecoverable, including from backups once they expire.
- **Withdrawal:** a resident leaving the study (TRD 06 DB-062).

## 4. Policy Requirements

1. **Retention schedule.** The PI, with the IRB, sets retention for each class below. Until then (TRD 24 OQ-01
   open), nothing is deleted automatically, and the values shown are **PLANNED proposals**, not decisions.

   | Data class | Where | Proposed retention (to be decided) |
   |---|---|---|
   | Voice features and check-in records | `raw_sessions`, `processed_sessions` | End of study plus the period required by the IRB protocol |
   | Scores, baselines, alerts | Derived tables | Same as features (rebuildable) |
   | Staff reviews and notes | `alert_reviews`, `staff_notes` | Same as features |
   | Resident and device records | `residents`, `devices`, `device_assignments` | Same as features |
   | Audit logs | `audit_logs` | Life of the database, and at least 6 years |
   | Application logs | Hosting provider | 90 days |
   | Database dumps | Designated storage | 90 days rolling, except dumps required for study closure |
   | CSV exports | Designated storage | Deleted when the analysis is complete, at most 1 year |
   | Security documentation (policies, risk analyses, assessments) | Repository and project space | At least 6 years from creation or last effective date (§ 164.316) |

2. **Withdrawal.** New data for a withdrawn resident is refused. Existing data is kept or purged as the IRB
   decides; purges use the audited `purge-resident` command.
3. **Disposal.** Database records are purged with the audited CLI; dumps and exports are securely deleted from
   storage; provider backups expire according to their configured window. Devices and media that held resident
   data are wiped or destroyed before reuse or disposal (EW-POL-07).
4. **Backups follow retention.** Backups may not be used to keep data beyond its retention period, except
   during their own short expiry window.
5. **Legal or research holds.** The PI may suspend deletion for a hold, recorded in writing.

## 5. Responsibilities

| Role | Responsibility |
|---|---|
| PI | Decides retention with the IRB; approves purges and holds |
| Data steward | Manages dumps and exports; performs disposal of copies |
| Team 2 DevOps lead | Runs purges; configures provider backup and log retention |

## 6. Compliance Expectations

Evidence: the approved retention schedule; audit records `resident.purged` and `resident.withdrawn`; a disposal
log for dumps and exports; provider retention settings recorded in `docs/deployment.md`.

## 7. Exceptions Process

Exceptions require PI approval, consistent with the IRB protocol, recorded with the reason and new date.

## 8. Review Process

Reviewed annually, when the IRB protocol changes, and at study closure.
