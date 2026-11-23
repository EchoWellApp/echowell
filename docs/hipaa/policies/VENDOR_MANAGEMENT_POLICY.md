# Vendor Management Policy

Policy ID: EW-POL-06 · Version 0.1 · **Status: DRAFT, not in force until approved by the PI** · Date: 22 November 2026
Aligned with: HIPAA § 164.308(b)(1), § 164.314(a); NIST SP 800-66r2 5.1.9, 5.4.1; NIST CSF 2.0 GV.SC-05

## 1. Purpose

To ensure that every outside service used by EchoWell is approved, appropriate for the data it can reach, and,
where it may handle ePHI, covered by a Business Associate Agreement (BAA) before any ePHI reaches it.

## 2. Scope

All third-party services, platforms and libraries used to build, host, monitor or operate EchoWell (TRD 22 §4.1),
and any service proposed in future.

## 3. Definitions

- **Business associate:** a vendor that creates, receives, maintains or transmits PHI on behalf of a covered
  entity or another business associate.
- **BAA:** the contract required by § 164.308(b) and § 164.314(a).
- **HIPAA-eligible service:** a service the vendor lists as covered by its BAA.

## 4. Policy Requirements

1. **Approved list only.** EchoWell uses only the services in TRD 22 §4.1. Adding a service requires a pull request
   updating TRD 22, approved by the project coordinator, and this review.
2. **Classification.** Each vendor is classified by the data it can reach: *no data*, *test data only*, or
   *ePHI*.
3. **BAA before ePHI.** No ePHI is sent to a vendor without a signed or accepted BAA and confirmation that each
   service used is HIPAA-eligible. Interim services (Netlify, Render, Neon, Sentry) never receive real data.
4. **Due diligence.** Before approval, record the vendor's security documentation (for example SOC 2 report or
   security page), data location (United States only), and account ownership by the project, not an individual.
5. **Account security.** Each vendor account has at least two administrators with MFA, owned by a project
   mailbox or UND identity.
6. **Monitoring.** Vendors are re-checked annually and on news of a vendor breach; the review is recorded in
   `VENDOR_COMPLIANCE_REVIEW.md`.
7. **Exit.** When a vendor is retired, data is deleted or returned and access tokens are revoked.

## 5. Responsibilities

| Role | Responsibility |
|---|---|
| Project coordinator | Approves new vendors |
| Team 2 DevOps lead | Performs due diligence and annual reviews; manages accounts |
| PI with UND | Accepts or signs BAAs on behalf of the study |

## 6. Compliance Expectations

Evidence: TRD 22 inventory; `VENDOR_COMPLIANCE_REVIEW.md` with verification dates; BAA records held by the PI or
UND (referenced, not stored in the public repository).

## 7. Exceptions Process

No exception allows ePHI to reach a vendor without a BAA. Other exceptions require PI approval and an end date.

## 8. Review Process

Reviewed annually and whenever a vendor is added or changes its terms.
