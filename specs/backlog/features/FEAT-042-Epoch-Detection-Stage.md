# FEAT-042 Epoch detection stage

| Field | Value |
|---|---|
| Epic | Analytics Engine |
| Build phase | Phase 6 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-041 |
| Status | Not Started |

## Purpose

Split each resident's records into epochs — continuous periods on one device with one firmware and one extraction software version — because voice features are not comparable across hardware or software changes. A new epoch restarts the baseline, the speaker-screen reference and the tally. This stage produces R07's epoch 2 when the resident moved from device D07 to D07B on Oct 13.

## Business Context

- BR-08 (device or software changes restart the baseline): epoch key (device_id, device_firmware_version, extraction_software_version).
- BR-09 / BR-11: baseline count and CUSUM restart per epoch.
- BR-15: R07 epoch 1 = 12 records on D07 (Oct 1–12), epoch 2 from R07-20261013-01 on D07B; every other test resident has one epoch.
- FRs covered (BACKLOG.md): FR-050, FR-051.

## Referenced TRDs

- TRD 08 BSC-006..BSC-010 (epoch rules, start/end, duplicates without epoch, per-epoch state), §4.3 pseudocode and fixture check.
- TRD 10 ING-047 (epochs use the record's device_id, not the assignment table).
- TRD 07 §4.2 (`assign_epochs` signature), §4.3 (`EpochedRecord`), §4.4 (`EpochSummary`), ANL-021.
- TRD 01 ARC-074 (timestamp order with `arrival_seq` tie-break).
- TRD 13 Table 4.3-A EP-01..EP-07; TRD 14 VC-R07; TRD 08 AC-BSC-05 (epoch part).
- TRD 25 AGT-045; TRD 24 D-11.

## Scope

- `analytics/epoch_detection.py::assign_epochs(rows: Sequence[ScreenedRecord], late: Collection[ScreenedRecord] = ()) -> list[EpochedRecord]` (the late-arrival set supplied by the orchestrator per TRD 07 §4.5 step 6 and TRD 08 §4.3).
- Epoch numbering, epoch boundaries (`started_at`, `ended_at`) and the local fields carried on `EpochedRecord`.
- Unit tests `tests/unit/analytics/test_epoch_detection.py`.

## Out of Scope

- Late-arrival classification (FEAT-045) — this stage only applies the given late set.
- Closing alerts of an ended epoch (FEAT-048 facts, FEAT-053 persistence).
- Persisting `epochs` rows and their natural-key upsert (FEAT-053, DB-015).
- Restart-cause derivation for the API (DB-065, FEAT-014/FEAT-028).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-042-FR-01 | Epochs shall be computed per resident over all non-duplicate, non-late records — usable candidates and set-aside records alike — sorted by `(timestamp_utc, arrival_seq)`. | BSC-006, ARC-074; FR-050 |
| FEAT-042-FR-02 | The first record of a resident starts epoch 1; a record whose (device_id, device_firmware_version, extraction_software_version) differs from the previous record's key starts a new epoch numbered previous + 1; numbers are never reused (a return to an earlier key starts a new, higher epoch). | BSC-007, AGT-045; FR-050, FR-051 |
| FEAT-042-FR-03 | The epoch key shall use the `device_id` (device code) carried by each record, not the device assignment table. | ING-047 |
| FEAT-042-FR-04 | Duplicate records shall get `epoch_number = None`. | BSC-009; EP-07 |
| FEAT-042-FR-05 | A late record shall get the epoch of the last non-late record of the same resident at or before it in time order (None if there is none) and shall never start or split an epoch. | TRD 08 §4.3; ANL-025 |
| FEAT-042-FR-06 | Each epoch shall have `started_at` = `timestamp_utc` of its first record and `ended_at` = `started_at` of the resident's next epoch (None for the current epoch); these values feed `EpochSummary` (device code, firmware, software, started_at, ended_at). | BSC-008; FR-051 |
| FEAT-042-FR-07 | Within an epoch the speaker-screen reference list, the baseline count and the CUSUM state shall start empty; nothing carries over from an earlier epoch (downstream stages group by (resident, epoch)). | BSC-010, D-11 |
| FEAT-042-FR-08 | The function shall be pure and deterministic; input order of equal-key rows does not change the output. | ANL-003, ANL-021 |

## Inputs

- `Sequence[ScreenedRecord]` from the quality gate (statuses duplicate, set_aside, pending_screen).
- The late-arrival set from FEAT-045's classifier (record identities), passed by the orchestrator.

## Outputs

- `list[EpochedRecord]` with `epoch_number`, `late_arrival`, `local_datetime` and `local_date` slots (local fields are filled by FEAT-043's conversion), status carried from the gate.
- Per-epoch boundary facts used to build `EpochSummary` (TRD 07 §4.4).

## Data Flow

1. `run_pipeline` step 6 (FEAT-052) calls `screen_speakers(assign_epochs(screened, late), config)`.
2. `assign_epochs` groups by `resident_code`, sorts non-duplicate non-late rows by `(timestamp_utc, arrival_seq)`, walks them comparing keys, assigns numbers, then assigns late rows to the preceding epoch.
3. Output goes to the speaker screen (FEAT-044); epoch boundaries go to `EpochSummary` and, through the runner, to the `epochs` table.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-041

- FEAT-041 (Duplicate detection and quality gate): `ScreenedRecord` statuses (duplicates excluded; set-aside included).
- Transitively FEAT-040 (contracts).
- Downstream: FEAT-044 (screen per epoch), FEAT-045, FEAT-048 (epoch-ended facts), FEAT-052.

## Database Impact

None directly. The runner upserts `epochs` (`resident_id`, `epoch_number`, `device_id`, `device_firmware_version`, `extraction_software_version`, `started_at`, `ended_at`) and sets `processed_sessions.epoch_id` (FEAT-053).

## API Impact

None directly; epochs surface through `current_epoch`, `epoch_count` and `baseline_restarted` events (FEAT-027, FEAT-028).

## Frontend Impact

None directly (badge "No alarm · baseline restarted Oct 13" and the log entry are FEAT-065/FEAT-068).

## Analytics Impact

- Algorithm: run-length segmentation on the epoch key in time order; stage 3 of ANL-006 (`epoch_detection`, LOG-063).

## Security Requirements

None specific (pure function).

## Error Handling

- Naive datetimes or missing fields are rejected by `run_pipeline` input validation (`ContractError`).
- A resident with only duplicates or only late records produces no epoch and no error (ANL-019).

## Logging Requirements

None in `analytics/` (LOG-006).

## Testing Requirements

- Unit (`tests/unit/analytics/test_epoch_detection.py`, marker `unit`): EP-01..EP-07; return to an earlier key gives a new higher number; late record inherits the preceding epoch and does not split.
- Validation (FEAT-059): VC-R07 (epoch 2 from day 13 on D07B; set-aside records have epoch 1 for R03/R08, TRD 08 §4.3 fixture check).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-042-AC-01 | Three records with the same key all get epoch 1. | EP-01 |
| FEAT-042-AC-02 | Device change D07 → D07B at record 13 gives records 1–12 epoch 1 and 13+ epoch 2; a firmware-only change (fw-1.0.0 → fw-1.0.1) and a software-only change each start a new epoch. | EP-02..EP-04, BSC-007 |
| FEAT-042-AC-03 | A set-aside record carrying a new key starts the new epoch at that record. | EP-05, BSC-006 |
| FEAT-042-AC-04 | Records given out of timestamp order are numbered by `(timestamp_utc, arrival_seq)`; a duplicate with a different key gets `epoch_number` None and does not start an epoch. | EP-06, EP-07 |
| FEAT-042-AC-05 | Keys A, B, A in time order give epochs 1, 2, 3. | BSC-007 |
| FEAT-042-AC-06 | On SRC-05, R07 has epoch 1 with 12 records (2026-10-01..2026-10-12, D07) and epoch 2 starting at R07-20261013-01 (D07B) with epoch 1 `ended_at` = epoch 2 `started_at`; every other resident has exactly one epoch. | VC-R07, BSC-008, AC-BSC-05 |

## Definition of Done

- Module implemented with the binding signature; EP-01..EP-07 pass (TST-020); `tests/unit/analytics/test_epoch_detection.py` exists (TST-011).
- VC-R07 epoch values pass in the validation suite (FEAT-059).

## Implementation Notes

- Compare the three key strings exactly as received; ingest stores text without trimming or case change (ING-022), so "fw-1.0.0" and "fw-1.0.0 " would be different keys by design.
- TRD 07 §4.2 now lists the signature with the late set as a keyword argument with an empty default, matching the calls in §4.5 step 6 and TRD 08 §4.3 (aligned in the PR #2 consistency fixes).
- Keep sorting keyed on `(timestamp_utc, arrival_seq)`; never rely on dict insertion order (ANL-021).
