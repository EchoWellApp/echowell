# FEAT-097 Device speaker-verification input

| Field | Value |
|---|---|
| Epic | Data Processing |
| Build phase | Future research (TRD 25) |
| Priority | P2 |
| Complexity | Medium |
| MVP status | Future |
| Dependencies | FEAT-023, FEAT-044 |
| Status | Not Started |
| Gate | Gated on OQ-14 |

## Purpose

Accept the speaker-verification result that Team 1's device may produce in future, so that a record spoken by someone other than the resident (a visitor, roommate or staff member) can be recognised from the device's own verification instead of only from the statistical speaker screen. The TRDs fix the mechanism: the field arrives only under a new record `schema_version`, registered through the validator registry and feature-name mapping without changing schema v0.1, and schema v0.1 plus the R05 answer key stay unchanged. The schedule, the output type (binary decision or confidence score) and how it combines with the statistical screen are open (OQ-14).

## Business Context

- RSK-01: without speaker verification another person's record is attributed to the resident; the mitigation in the MVP is the statistical speaker screen (|z_F0| ≥ 4.0 and ≥ 2 composite features with |z| ≥ 3.0, D-13); the contingency is "when Team 1 delivers verification output (OQ-14), add it under a new schema_version and quarantine on it".
- BR-05 (quarantine likely other speakers) and BR-01 (strict schema, no unexpected content, FR-013).
- BR-15: R05 (possible other speaker on days 8 and 22) must keep reproducing the answer key.

## Referenced TRDs

- TRD 10 ING-013, ING-014, ING-015, ING-016, ING-017, ING-018, ING-019, §4.2, §4.3, §9 (OQ-14 note).
- TRD 08 BSC-011..BSC-019 (statistical speaker screen), §9 (OQ-14 note).
- TRD 02 FR-012, FR-013, FR-060..FR-065 (speaker screen behaviour, via BR-05).
- TRD 19 §9 (OQ-14: confidence field not in schema v0.1; adding it is a `schema_version` change).
- TRD 20 `raw_sessions.schema_version`, `processed_sessions.screen_detail`, PGS-012 (quarantine reason CHECK), PGS-024 and §4.11 (`supported_schema_versions` seeded `["0.1"]`, `feature_name_map`).
- TRD 13 §9 (OQ-14: no test of a confidence field until Team 1 defines it), TST-030, TST-031.
- TRD 14 §9 (OQ-14: not in DS-01; no validation case until defined), VC-R05 via TDV-050..TDV-060.
- TRD 24 OQ-14 (gate), RSK-01, D-13, D-56.
- TRD 25 AGT-005 (no ML on the pipeline path), AGT-008, AGT-044.

## Scope

Decided by the TRDs:

- A new `schema_version` value (for example the next version after "0.1"; its string is set by Team 1's record specification) added to `supported_schema_versions` through `set-config` (operational ingest key, D-56) and to the registry `backend/services/validation.py::VALIDATORS` with a new validator function; `validate_v0_1` and the identity `feature_name_map` entries for v0.1 stay unchanged.
- The new field carries the device's verification output; `raw_sessions.payload` keeps the original names and values; `raw_sessions.schema_version` stores the received value.
- Records with `schema_version` "0.1" continue to be validated, processed and screened exactly as today; R05 output is unchanged.
- The statistical speaker screen stays in place as the substitute until verification exists (D-13) and uses raw values and the first-N reference as specified.
- No ML model on the pipeline path: the verification is computed on the device by Team 1; EchoWell only receives its output (AGT-005).

Blocked on OQ-14 (not decided here):

- When Team 1 schedules speaker verification, the field name, whether it is a binary decision or a confidence score, its range and missing-value semantics.
- How the device result combines with the statistical screen, and any threshold value.
- The quarantine reason text for a verification-based quarantine and how it appears in `screen_detail`, the check-in log and the R05-style data alert.
- Whether derived processing may depend on `schema_version` beyond validation (ING-015 forbids it in v0.1).

Trigger for starting: OQ-14 answered in TRD 24 by Team 1 with the schedule and output type, and a record specification for the new `schema_version`; TRD 10, TRD 08, TRD 19, TRD 20 updated accordingly.

## Out of Scope

- Changing schema v0.1, `validate_v0_1`, the R01–R10 inputs or expected values (AGT-008).
- Any speaker-recognition cloud service or audio processing in EchoWell (TPS-082, AGT-006).
- Device-side verification (Team 1).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-097-FR-01 | The verification output shall be accepted only in records with a new `schema_version` listed in `supported_schema_versions`; records with any other unsupported version shall be rejected with `unsupported_schema_version`. | ING-013, RSK-01, OQ-14 |
| FEAT-097-FR-02 | The new version shall be added as a new validator in `backend/services/validation.py::VALIDATORS` and, where needed, new feature-name mapping entries, without changing the existing v0.1 validator or mapping. | ING-014, ING-016 |
| FEAT-097-FR-03 | Unknown fields shall remain rejected for v0.1 records (strict schema after mapping); the new field shall be accepted only under the new version. | FR-013, ING-019 |
| FEAT-097-FR-04 | The stored `schema_version` shall be the received value, and `raw_sessions.payload` shall keep the original names and values. | ING-015, ING-018 |
| FEAT-097-FR-05 | The statistical speaker screen of BSC-011..BSC-019 shall keep its behaviour for all records until the combination rule of OQ-14 is decided; v0.1 R05 days 8 and 22 shall stay quarantined with the exact reason strings. | BSC-011..BSC-019, D-13, AGT-044 |
| FEAT-097-FR-06 | The field type (binary or confidence), name, range and the combination rule with the statistical screen shall be those recorded in TRD 24 when OQ-14 closes; the implementer shall not choose them. | OQ-14, AGT-009 |
| FEAT-097-FR-07 | No machine-learning model or speaker-recognition service shall run in EchoWell; only the device's output is consumed. | AGT-005, TPS-082 |
| FEAT-097-FR-08 | Adding the new version's values to `supported_schema_versions` and `feature_name_map` shall use `set-config` (operational keys, effective at the next request, no rebuild). | D-56, D-69 |

## Inputs

- Records from Team 1 devices with the new `schema_version` and the verification field (once specified).
- `supported_schema_versions` and `feature_name_map` from `config_parameters`.

## Outputs

- New validator and mapping entries; stored raw records with the new version.
- After OQ-14: processing that applies the decided combination rule, with statuses and reasons per the updated TRDs.

## Data Flow

Device → `POST /api/v1/sessions` or `POST /api/v1/ingest` → schema version check (ING-013) → registry selects the validator (ING-014) → mapping (ING-016) → `raw_sessions` (payload unmapped, typed columns canonical) → pipeline: duplicate → quality gate → epoch → speaker screen (statistical; plus the device result per OQ-14) → downstream stages unchanged.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-023, FEAT-044

- [FEAT-023](FEAT-023-Ingest-Record-Validation-Schema-Version-Registry.md) Ingest record validation, schema-version registry and feature-name mapping.
- [FEAT-044](FEAT-044-Speaker-Screen-Stage.md) Speaker screen stage.

Gate: OQ-14 (speaker verification schedule and output type).

Features that build directly on this one (BACKLOG.md §4): none.

## Database Impact

- Tables used: `raw_sessions` (`schema_version`, `payload`), `processed_sessions` (`status`, `reasons`, `screen_detail`), `config_parameters` (`supported_schema_versions`, `feature_name_map`), `ingest_rejections`.
- Tables created or modified: none decided. Gaps that need TRD 20 changes with OQ-14: the typed record columns of `raw_sessions` cover only the 30 v0.1 fields, and ING-017 limits mapping targets to those 30 canonical names, so a new canonical field needs a schema change; PGS-012 allows a `quarantined` row only with the reason `possible other speaker (F0 z=…; composite features with |z|>=3: …)`, so a verification-based quarantine reason would violate the current CHECK.

## API Impact

- Endpoints consumed or exposed: `POST /api/v1/sessions`, `POST /api/v1/ingest` accept the new version once registered; the request schema in TRD 19 gains the new field under the new version (OpenAPI regeneration, D-51). No new endpoint.

## Frontend Impact

- None decided. Display of a verification-based quarantine (check-in log entry, data alert text) follows the OQ-14 decision and TRD 11 updates.

## Analytics Impact

- Speaker screen (BSC-011..BSC-019) unchanged for v0.1; the combination rule with the device result is added only after OQ-14. Baseline, scoring and CUSUM unchanged except through which sessions are usable.

## Security Requirements

- Strict validation and rejection of unknown fields keep unexpected content out of storage (FR-013).
- No audio, no speaker-recognition service (AGT-006, TPS-082); API key with `ingest:write` as today.

## Error Handling

- Unsupported version → 422 with `unsupported_schema_version` and an `ingest_rejections` row (ING-013).
- Invalid verification value under the new version → 422 with field-level errors from the new validator (all violations collected, ING-019).

## Logging Requirements

- Ingest logs contain identifiers and validation error locations only, never feature or verification values (LOG-021).

## Testing Requirements

- Unit: registry dispatch test (v0.1 → `validate_v0_1`, new version → new validator); v0.1 record with the new field still rejected (FR-013); TST-030 and TST-031 unchanged.
- Validation: `pytest tests/validation -q` unchanged (VC-R05 reasons exact).
- After OQ-14: tests for the decided combination rule (TRD 13 §9: no test of a confidence field until Team 1 defines it).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-097-AC-01 | A v0.1 record containing an extra verification field is rejected with 422 and creates no `raw_sessions` row. | FR-013, TST-045 |
| FEAT-097-AC-02 | With the new version added to `supported_schema_versions`, a valid new-version record returns 201 and is stored with the received `schema_version` and unmapped payload; without it, the same record is rejected with `unsupported_schema_version`. Verified by: Unit (TST-030, TST-031). | ING-013, ING-015, ING-018 |
| FEAT-097-AC-03 | `git diff` of the feature shows no change to `validate_v0_1` or the v0.1 mapping entries. Verified by: Test (run the command in the criterion against the stated environment and check the stated result). | ING-014 |
| FEAT-097-AC-04 | `pytest tests/validation -q` passes unchanged; R05 days 8 and 22 are quarantined with the exact SRC-03 reason strings. | AGT-008, BSC-016 |

## Definition of Done

- All FEAT-097 acceptance criteria pass.
- Gate satisfied (OQ-14 answered with output type and record specification) and TRDs 10, 08, 19, 20 updated; all FEAT-097 acceptance criteria pass.

## Implementation Notes

- Keep v0.1 behaviour byte-for-byte: the registry exists precisely so a new version adds code beside the old one (ING-014).
- The registry and mapping work (FEAT-097-FR-01..FEAT-097-FR-04) can be prepared as soon as Team 1 publishes the record specification, but the combination rule (FEAT-097-FR-06) waits for OQ-14.
- The PGS-012 and ING-017 constraints above are now recorded in the OQ-14 interim decision of TRD 24 as TRD changes needed when OQ-14 is answered.
