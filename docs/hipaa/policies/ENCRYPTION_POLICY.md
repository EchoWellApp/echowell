# Encryption Policy

Policy ID: EW-POL-02 · Version 0.1 · **Status: DRAFT, not in force until approved by the PI** · Date: 22 November 2026
Aligned with: HIPAA § 164.312(a)(2)(iv), § 164.312(e)(1)–(2); NIST SP 800-66r2 5.3.1, 5.3.5; NIST CSF 2.0
PR.DS-01, PR.DS-02, PR.DS-11

## 1. Purpose

To protect resident data from disclosure in transit and at rest through encryption and sound key management.

## 2. Scope

All EchoWell data in transit (device to API, browser to frontend and API, API to database, backups to storage) and
at rest (database, backups, exports, logs), and the keys and secrets that protect them.

## 3. Definitions

- **TLS:** Transport Layer Security; version 1.2 or higher is required.
- **KMS key:** a customer-managed key in AWS Key Management Service.
- **Secret:** any credential, key, token or connection string.

## 4. Policy Requirements

1. **In transit.** All external traffic uses HTTPS with TLS 1.2 or higher; HTTP only redirects. HSTS is sent by
   the frontend and the API. Devices submit data only over HTTPS. The API connects to PostgreSQL only with
   `sslmode=require` or `verify-full` and refuses to start otherwise.
2. **At rest: production.** On AWS, the database uses RDS storage encryption with a customer-managed KMS key;
   automated backups and snapshots are encrypted; any S3 bucket is encrypted and private.
3. **At rest: interim stack.** Provider-managed encryption is accepted only because the interim stack holds
   synthetic and test data.
4. **Backups and exports.** Database dumps and CSV exports containing resident data are encrypted at rest and
   stored only on storage designated by the PI; never on personal devices, e-mail or public file-sharing.
5. **Credentials.** Passwords are stored only as argon2id hashes; API keys only as SHA-256 digests. Plaintext
   credentials are never stored or logged.
6. **Key and secret management.** Secrets are stored only in the hosting platforms' secret settings, GitHub
   encrypted secrets, or AWS Secrets Manager. The JWT secret is generated randomly (at least 48 bytes), differs per
   environment, and is rotated every 180 days and on suspected exposure or departure of anyone with access.
   Database role passwords follow the same rotation. KMS keys have rotation enabled.
7. **Algorithms.** Only current, well-reviewed algorithms provided by maintained libraries are used; no custom
   cryptography.

## 5. Responsibilities

| Role | Responsibility |
|---|---|
| Team 2 DevOps lead | Configures TLS, database encryption, KMS and secrets; performs rotations and records them |
| Data steward | Encrypts and stores backups on designated storage |
| Developers | Keep startup checks and tests for TLS and secrets passing |

## 6. Compliance Expectations

Evidence: startup checks and transport tests in the repository; recorded TLS checks in post-deploy smoke tests;
AWS settings (KMS key, RDS encryption, backup encryption) recorded in `docs/deployment.md` at go-live; rotation
entries in the audit log or operations log.

## 7. Exceptions Process

Any exception (for example, a legacy client that cannot use TLS 1.2) requires PI approval after a risk review
and is recorded with an end date. Exceptions are not permitted for live resident data in transit.

## 8. Review Process

Reviewed annually and whenever hosting, cryptographic libraries or industry guidance change.
