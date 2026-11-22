# Device Security Policy

Policy ID: EW-POL-07 · Version 0.1 · **Status: DRAFT, not in force until approved by the PI and agreed with Team 1** · Date: 22 November 2026
Aligned with: HIPAA § 164.310(a)–(d), § 164.312(d), (e)(1); NIST SP 800-66r2 5.2.1–5.2.4, 5.3.4; NIST CSF 2.0
PR.AA-03, PR.DS-01, PR.PS-02

## 1. Purpose

To protect the voice-recording devices that send data to EchoWell, the audio they handle locally, and the
credentials they hold, as well as staff workstations used to access EchoWell.

## 2. Scope

Team 1 recording devices deployed with residents (identified by device codes such as `T1D01`), any computer used
to run feature extraction, and workstations used by staff to access the EchoWell dashboard.

## 3. Definitions

- **Device:** hardware that records a resident's voice, extracts numeric features and submits them to EchoWell.
- **Device key:** the EchoWell API key issued to one device.
- **Local audio:** recordings held temporarily on a device before or during feature extraction.

## 4. Policy Requirements

1. **No audio leaves the device for EchoWell.** Devices send only numeric features. Local audio is deleted as soon
   as features are extracted and verified, and is never uploaded to EchoWell (which rejects audio).
2. **Local storage.** Any local audio and the device key are stored on encrypted storage. Devices hold no names or
   other direct identifiers of residents; they know only their device code.
3. **One key per device.** Each device receives its own key, bound to its device code with scope `ingest:write`.
   Keys are delivered to the device by a secure channel and never sent by e-mail or chat.
4. **Rotation and revocation.** Keys are rotated every 365 days, on device replacement and on any suspicion.
   A lost, stolen or tampered device is reported immediately; its key is revoked with
   `python -m backend.cli revoke-api-key` and the incident policy (EW-POL-05) applies.
5. **Physical protection.** Devices are mounted or placed to resist removal and tampering, labelled with a
   non-identifying room label, and inventoried with their device code and location.
6. **Software.** Device firmware and extraction software are kept current; the version is reported with each
   record (`extraction_software_version`, `device_firmware_version`).
7. **Transport.** Devices connect to EchoWell only over HTTPS and verify the server certificate.
8. **Disposal.** Before reuse, return or disposal, device storage is securely wiped and the key revoked.
9. **Staff workstations.** Workstations used to access EchoWell have screen locks, current updates and
   anti-malware, and are not shared under one login.

## 5. Responsibilities

| Role | Responsibility |
|---|---|
| Team 1 lead | Device hardening, local audio deletion, firmware updates, device inventory |
| Team 2 DevOps lead | Issues, rotates and revokes device keys |
| Facility staff | Report missing or damaged devices |
| PI | Approves device deployment with residents |

## 6. Compliance Expectations

Evidence: device inventory; key creation and revocation in the audit log; Team 1's written description of local
storage encryption and audio deletion (not yet provided; finding HF-18).

## 7. Exceptions Process

Exceptions (for example, a prototype device without encrypted storage) are allowed only with synthetic or team
test recordings, never with residents, and require PI approval.

## 8. Review Process

Reviewed annually, before each new device type is deployed, and after any device incident.
