# Access Control Policy

Policy ID: EW-POL-01 · Version 0.1 · **Status: DRAFT, not in force until approved by the PI** · Date: 22 November 2026
Aligned with: HIPAA § 164.308(a)(3)–(4), § 164.312(a)(1), (a)(2)(i)–(iii), (d); NIST SP 800-66r2 5.1.3, 5.1.4,
5.3.1, 5.3.4; NIST CSF 2.0 PR.AA-01, PR.AA-03, PR.AA-05

## 1. Purpose

To ensure that only authorized people and devices can access EchoWell and resident data, each with the least
access needed for their role.

## 2. Scope

All EchoWell environments that hold or may hold resident data (the AWS production platform once live; the
interim stack while it holds test data), all staff user accounts, device and scheduler API keys, database roles,
and administrative accounts on hosting providers and GitHub.

## 3. Definitions

- **ePHI:** electronic protected health information, including voice features, scores, alerts, reviews and notes
  linked to a resident study code.
- **User roles:** *admin* (system and user management, all data), *clinician* (view and review), *researcher*
  (view, analytics and export, no review actions).
- **API key:** a credential issued to one device or to the pipeline scheduler.
- **Access owner:** the PI, who approves who may hold an account.

## 4. Policy Requirements

1. **Eligibility.** Accounts are created only for personnel listed on the IRB-approved protocol, on request of
   the PI or delegate, by an admin through the Admin page or the CLI. There is no self-registration and no
   shared or default account.
2. **Unique identification.** Every person has their own account; sharing credentials is prohibited.
3. **Least privilege.** Each account receives the lowest role that meets the person's duties. Admin is limited to
   two to three people. Researchers receive read-only access.
4. **Authentication.** Passwords are 12–128 characters, not on the common-password list and not equal to the
   email. Multi-factor authentication shall be enabled for all accounts once available, and is mandatory for
   admins and anyone who can export data (planned, finding HF-03).
5. **Sessions.** Sessions expire after at most 60 minutes. Workstations must be locked when unattended. An idle
   time-out of about 15 minutes shall be enforced in the dashboard once implemented (planned, HF-04).
6. **Changes and removal.** Role changes take effect immediately. Accounts of people leaving the study are
   deactivated within 1 working day of notice. Users cannot change their own role.
7. **Access review.** Every quarter the PI or delegate reviews the list of active accounts and roles and
   confirms each one; the review is recorded.
8. **Device and service credentials.** API keys are issued per device, bound to that device, limited to the
   needed scope, stored only as hashes, and revoked on loss, replacement or suspicion (see EW-POL-07).
9. **Database and provider access.** Applications use least-privilege database roles. Database owner credentials
   are held only by the DevOps lead and the PI's deputy. Every provider account has at least two administrators,
   all with MFA.
10. **Emergency access.** In an emergency the DevOps lead may create or restore an admin account through the CLI;
    the action is audited and reported to the PI within 24 hours.

## 5. Responsibilities

| Role | Responsibility |
|---|---|
| PI | Approves accounts and roles; performs or delegates quarterly reviews |
| Admins | Create, change and deactivate accounts as approved |
| Team 2 DevOps lead | Issues and revokes API keys; manages database and provider access; emergency access |
| All users | Protect their credentials; lock workstations; report suspected misuse |

## 6. Compliance Expectations

Compliance is shown by the audit trail (`user.created`, `user.updated`, `api_key.created`, `api_key.revoked`,
`access.denied`), the recorded quarterly reviews, and the automated authorization tests that run on every change.

## 7. Exceptions Process

Exceptions (for example, temporary elevated access) require written PI approval stating the reason and an end
date of no more than 30 days, recorded in the project's private space and reviewed at expiry.

## 8. Review Process

Reviewed annually, at the AWS go-live, and after any incident involving unauthorized access.
