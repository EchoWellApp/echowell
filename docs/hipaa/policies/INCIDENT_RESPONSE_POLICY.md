# Incident Response Policy

Policy ID: EW-POL-05 · Version 0.1 · **Status: DRAFT, not in force until approved by the PI** · Date: 22 November 2026
Aligned with: HIPAA § 164.308(a)(6), § 164.308(a)(7); Breach Notification Rule (§§ 164.400–414, context);
NIST SP 800-66r2 5.1.6, 5.1.7; NIST CSF 2.0 RS.MA-01, RC.RP-01

## 1. Purpose

To detect, contain, investigate and recover from security incidents affecting EchoWell, and to ensure the PI
can meet reporting obligations.

## 2. Scope

Any suspected or actual unauthorized access, use, disclosure, change or loss of EchoWell data or systems,
including lost devices, leaked credentials, vulnerabilities being exploited and vendor incidents.

## 3. Definitions

- **Security incident:** an attempted or successful unauthorized access, use, disclosure, modification or
  destruction of information, or interference with system operations (§ 164.304).
- **Breach:** an incident involving unsecured PHI that requires notification unless a risk assessment shows a low
  probability of compromise; the determination is made by the covered entity, not by Team 2.

## 4. Policy Requirements

1. **Report.** Anyone who suspects an incident reports it immediately to the Team 2 DevOps lead and the project
   coordinator, without investigating on their own.
2. **Contain within 1 hour.** The on-duty DevOps lead uses the runbook in `docs/deployment.md`: revoke API keys,
   deactivate users, rotate the JWT secret (ends all sessions), rotate database passwords, suspend services.
3. **Escalate within 24 hours.** The PI and the Team 2 lead are informed within 24 hours of discovery. The PI
   decides on reporting to UND IT security, the IRB, the partner facility (as covered entity) and any regulator.
4. **Investigate.** Use audit logs correlated with application logs by request ID; preserve evidence (logs,
   affected records) before changes where possible.
5. **Recover.** Restore from backup if needed (restore procedure in `docs/deployment.md`), rebuild derived data,
   verify with the validation suite, and only then resume service.
6. **Document.** Every incident gets a post-incident note (timeline, cause, data affected, corrective actions)
   stored in the team's private space, never in the public repository. Public issues contain no sensitive detail.
7. **Learn.** Corrective actions are tracked to completion; the risk analysis is updated.
8. **Exercise.** A tabletop exercise is run at least once a year and before go-live (PLANNED).

## 5. Responsibilities

| Role | Responsibility |
|---|---|
| All team members | Report suspected incidents immediately |
| Team 2 DevOps lead | Containment, investigation, recovery, post-incident note |
| Project coordinator | Coordination and communication within the teams |
| PI | Breach determination and external reporting decisions |

## 6. Compliance Expectations

Evidence: post-incident notes; containment entries in the audit log; tabletop exercise records; updated risk
analysis.

## 7. Exceptions Process

None for reporting. Containment steps may be adapted by the DevOps lead to the situation, with the reason recorded
in the post-incident note.

## 8. Review Process

Reviewed annually, after every incident and after every exercise.
