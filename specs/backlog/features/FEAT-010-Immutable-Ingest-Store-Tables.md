# FEAT-010 Immutable ingest store tables (ingest_batches, ingest_rejections, raw_sessions)

| Field | Value |
|---|---|
| Epic | Database |
| Build phase | Phase 4 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-009 |
| Status | Not Started |

## Purpose

Create the raw record store that is the single source of truth for EchoWell: `raw_sessions` (every accepted arrival exactly as received, including duplicates, never edited), `ingest_rejections` (schema-invalid records with their error list) and `ingest_batches` (one row per upload or batch). Database triggers and grants make `raw_sessions` immutable for the application, so every derived table can always be rebuilt from it (D-07).

## Business Context

- BR-02: keep every received record unaltered and derive everything else from it (FR-005, FR-006, ARC-030, ARC-031).
- BR-01: only feature records, never audio, cross into the store; invalid records are rejected and logged, never stored as raw (FR-028, D-08).
- BR-03: duplicates of a `session_id` are stored as received and resolved later by the pipeline (D-09).
- BR-16: ingest provenance (`ingest_batches`) records source, uploader or API key and counts (FR-010).

## Referenced TRDs

- TRD 20 PGS-009, PGS-011, PGS-018, PGS-019; §4.6.7–§4.6.9 DDL; §4.8 (`raw_sessions` triggers, grants, sequence grant); §8 notes; AC-PGS-01, AC-PGS-02.
- TRD 06 DB-001..DB-005, DB-008, DB-009.
- TRD 10 ING-029, ING-030.
- TRD 23 DME-015, DME-019; §4.2.7–§4.2.9; §4.7.1 column mapping.
- TRD 01 ARC-030..ARC-033.
- TRD 02 FR-005, FR-006, FR-010, FR-028.
- TRD 13 TST-040, TST-041, TST-042.
- TRD 24 D-07, D-08, D-09.

## Scope

- Migration 0001 sections for `ingest_batches`, `ingest_rejections`, `raw_sessions` exactly as TRD 20 §4.6.7–§4.6.9, including all named CHECK constraints and `raw_sessions_arrival_seq_uq`.
- Triggers `raw_sessions_no_update_delete` (row-level `BEFORE UPDATE OR DELETE`) and `raw_sessions_no_truncate` (statement-level `BEFORE TRUNCATE`) calling `reject_mutation()`; trigger `ingest_batches_set_updated_at`.
- Grants: `echowell_app` SELECT, INSERT on `raw_sessions` and `ingest_rejections`; SELECT, INSERT, UPDATE on `ingest_batches`; USAGE, SELECT on sequence `raw_sessions_arrival_seq_seq`; `echowell_readonly` SELECT on all three.
- Models (TRD 23 §4.6): `ingest_batch.py:IngestBatch` and `IngestRejection`, `session.py:RawSession` (existing skeleton file).
- Insert-only repositories: `raw_sessions` (insert one arrival returning `id` and `arrival_seq`; select by resident in `arrival_seq` order; select by `session_id`), `ingest_rejections` (insert), `ingest_batches` (insert, update counts, get by id). No update or delete method exists for `raw_sessions` or `ingest_rejections`.
- The immutability and grant tests (TST-040 round-trip with these tables, TST-041 for `raw_sessions`).

## Out of Scope

- Validation of records, payload construction, feature-name mapping and resolution of `resident_id`/`device_id` (FEAT-023).
- Ingest endpoints and the session advisory lock (FEAT-025, FEAT-026).
- `audit_logs` triggers (FEAT-012) and the purge path usage by `purge-resident` (FEAT-017).
- Indexes on these tables (FEAT-013).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-010-FR-01 | `raw_sessions` shall have one typed column per schema-v0.1 ingest field (in SRC-05 column order) and one per feature, named exactly as PGS-009, all `double precision NOT NULL` except `number_of_pauses integer NOT NULL`, plus `arrival_seq` (bigserial, unique), `received_at`, `ingest_batch_id`, `api_key_id`, `payload`, `ingest_warnings`, `resident_id`, `device_id`, `resident_code`, `device_code`. | PGS-009, ING-029, DME-015 |
| FEAT-010-FR-02 | `raw_sessions` CHECKs shall enforce `audio_quality_flag` in {ok, poor}, `number_of_pauses` ≥ 0, `pause_fraction` and `voiced_fraction` in [0, 1], `speech_duration_s` ≥ 0, `mean_f0_hz` > 0, `phrase_id` 1–16 characters, `payload` a JSON object, version strings 1–64 characters. | PGS-011 |
| FEAT-010-FR-03 | `raw_sessions` shall carry `raw_sessions_no_update_delete` and `raw_sessions_no_truncate` triggers calling `reject_mutation()` (SQLSTATE `EW001`); the only bypass is DELETE/TRUNCATE by `echowell_migrator` with `echowell.allow_purge = 'on'`. | PGS-018, PGS-019, DB-008, ING-030 |
| FEAT-010-FR-04 | `echowell_app` shall hold only SELECT, INSERT on `raw_sessions` and `ingest_rejections` (no UPDATE, DELETE, TRUNCATE); trigger and grant each independently block mutation. | DB-004, DB-009, ARC-030, ING-030 |
| FEAT-010-FR-05 | Each accepted arrival, including duplicates, shall be inserted as one new `raw_sessions` row before any processing; `arrival_seq` is assigned by the sequence and never supplied by the application. | DB-001, FR-005, D-09, TRD 20 §8 |
| FEAT-010-FR-06 | `payload` shall hold the record exactly as received (JSON object, or for CSV a header → cell-string object); typed columns are only conversions of payload values. | DB-002, DB-003, ARC-031 |
| FEAT-010-FR-07 | `resident_id` and `device_id` shall be UUID FKs to `residents` and `devices`; the received codes are kept in `resident_code` and `device_code`. | DME-015 |
| FEAT-010-FR-08 | `timestamp_utc` and `received_at` shall be `timestamptz` stored in UTC. | DME-019, PGS-008 |
| FEAT-010-FR-09 | `ingest_rejections` shall store `raw_body` (jsonb) and a non-empty `errors` array, optional `ingest_batch_id`, `api_key_id` and `row_number` ≥ 1; schema-invalid records are written only here, never to `raw_sessions`. | DB-005, FR-028, D-08 |
| FEAT-010-FR-10 | `ingest_batches` shall record `source` (`api_single`, `api_batch`, `csv_upload`, `seed`), `filename` (required for `csv_upload`), record/accepted/rejected/duplicate counts with the §4.6.7 consistency CHECK, `uploaded_by` or `api_key_id` (unless `seed`), and `received_at`. | FR-010 |
| FEAT-010-FR-11 | Repositories shall expose insert and read methods only for `raw_sessions` and `ingest_rejections`, and no code path shall issue UPDATE, DELETE or TRUNCATE on `raw_sessions`. | FR-006, PGS-028 |
| FEAT-010-FR-12 | No table or column shall store audio; the only audio-related column is `audio_quality_flag`. | ARC-003, AC-ARC-08 |
| FEAT-010-FR-13 | The SRC-03 answer key shall not be stored in these tables nor readable by runtime code. | ARC-033 |

## Inputs

- Tables `residents`, `devices`, `users`, `api_keys` and enum `ingest_source` (FEAT-008, FEAT-009); `reject_mutation()` (FEAT-008).

## Outputs

- Three tables with triggers, constraints and grants; models and insert-only repositories used by the ingest features.

## Data Flow

Ingest service (FEAT-025/FEAT-026) validates a record → valid: repository inserts one `raw_sessions` row (sequence assigns `arrival_seq`, default `received_at = now()`) and, for batches, links it to an `ingest_batches` row → invalid: repository inserts one `ingest_rejections` row → the pipeline reads `raw_sessions` in `arrival_seq` order (FEAT-053). Any attempt to UPDATE/DELETE/TRUNCATE `raw_sessions` hits the grant check (42501) or the trigger (`EW001`).

## Dependencies

Required before implementation (BACKLOG.md): FEAT-009

- FEAT-009 provides `residents`, `devices`, `users` and `api_keys`, which the FKs of these tables reference.

Features that build directly on this one (BACKLOG.md §4): FEAT-011, FEAT-023.

## Database Impact

- Tables created: `ingest_batches`, `ingest_rejections`, `raw_sessions`.
- Constraints: `ingest_batches_counts_ck`, `ingest_batches_actor_ck`, `ingest_batches_filename_ck`, `ingest_rejections_errors_ck`, `ingest_rejections_row_number_ck`, `raw_sessions_arrival_seq_uq`, `raw_sessions_payload_ck`, `raw_sessions_schema_version_ck`, `raw_sessions_session_id_ck`, `raw_sessions_audio_quality_flag_ck`, `raw_sessions_speech_duration_ck`, `raw_sessions_number_of_pauses_ck`, `raw_sessions_pause_fraction_ck`, `raw_sessions_voiced_fraction_ck`, `raw_sessions_mean_f0_ck`, `raw_sessions_phrase_id_ck`, `raw_sessions_versions_ck`.
- Triggers: `raw_sessions_no_update_delete`, `raw_sessions_no_truncate`, `ingest_batches_set_updated_at`.
- Sequence: `raw_sessions_arrival_seq_seq` (USAGE, SELECT granted to `echowell_app`).
- Tables used: `residents`, `devices`, `users`, `api_keys` (FK targets).

## API Impact

None exposed. Backs E-05 `POST /sessions`, E-06 `POST /ingest` and E-07 `GET /ingest/batches/{id}` (FEAT-025, FEAT-026).

## Frontend Impact

None.

## Analytics Impact

None computed. `raw_sessions` is the only input of the pipeline (ordered by `arrival_seq` for duplicate detection, TRD 25 AGT-043).

## Security Requirements

- Immutability enforced twice: trigger and grants (DB-004).
- Purge only through the migrator path reserved for IRB withdrawal (PGS-019), never by the app.
- No audio and no PII columns (ARC-003, DB-035).

## Error Handling

| Failure | Behaviour | Trace |
|---|---|---|
| UPDATE/DELETE/TRUNCATE on `raw_sessions` as `echowell_app` | SQLSTATE 42501 (privilege) | AC-PGS-01, AC-PGS-02 |
| Same as table owner without purge setting | SQLSTATE `EW001` from `reject_mutation()`; the HTTP mapping to 500 is FEAT-019 (PGS-028) | PGS-018 |
| CHECK violation on insert (e.g. `audio_quality_flag = 'bad'`) | SQLSTATE 23514; validation (FEAT-023) prevents this for validated records | PGS-011 |
| Unknown resident/device FK | SQLSTATE 23503; validation rejects unknown codes first | DME-015 |

## Logging Requirements

None from the tables. Ingest log events and audit rows for batches are produced by FEAT-025/FEAT-026 (LOG-050..LOG-054) and FEAT-015.

## Testing Requirements

- Integration (`tests/integration/db/test_raw_store.py`, marker `integration`): AC-PGS-01 (UPDATE fails: 42501 as app, `EW001` as owner), AC-PGS-02 (DELETE and TRUNCATE fail for app and owner without the purge setting); PGS-011 CHECK cases (each violating value fails with 23514).
- Integration (`tests/integration/db/test_grants.py`): TST-041 for `raw_sessions` (UPDATE/DELETE as `echowell_app` raise and leave the row unchanged); `has_table_privilege('echowell_app','raw_sessions','UPDATE')` is false (DB-009).
- Integration: TST-042 for `raw_sessions.arrival_seq`; column list of `raw_sessions` equals the SRC-05 header feature names (PGS-009).
- Integration: `ingest_batches_counts_ck` and `ingest_batches_filename_ck` cases.
- Unit (`tests/unit/backend/repositories/test_raw_session_repository.py`): the repository class has no update/delete methods and never sets `arrival_seq`.

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-010-AC-01 | As `echowell_app_login`, `UPDATE raw_sessions SET phrase_id = 'x'` fails with SQLSTATE 42501; as the table owner it fails with SQLSTATE `EW001`; the row is unchanged. Verified by: Integration (`tests/integration/db/test_raw_store.py`). | AC-PGS-01, DB-004 |
| FEAT-010-AC-02 | `DELETE FROM raw_sessions` and `TRUNCATE raw_sessions` fail for `echowell_app_login` and for the owner without `echowell.allow_purge = 'on'`. Verified by: Integration (`tests/integration/db/test_raw_store.py`). | AC-PGS-02, PGS-018 |
| FEAT-010-AC-03 | `has_table_privilege('echowell_app','raw_sessions','UPDATE')`, `…'DELETE')` and `has_table_privilege('echowell_app','ingest_rejections','UPDATE')` are all false; `…'raw_sessions','INSERT')` is true. Verified by: Integration (`tests/integration/db/test_grants.py`). | DB-009, ING-030 |
| FEAT-010-AC-04 | Inserting a row with `audio_quality_flag = 'bad'`, `number_of_pauses = -1`, `pause_fraction = 1.5`, `mean_f0_hz = 0` or a 17-character `phrase_id` each fails with SQLSTATE 23514. Verified by: Integration (`tests/integration/db/test_raw_store.py`). | PGS-011 |
| FEAT-010-AC-05 | The `raw_sessions` feature column names equal the 19 feature names in the SRC-05 header and `number_of_pauses` is `integer`. Verified by: Integration (column list of `raw_sessions` equals the SRC-05 header feature names (PGS-009)). | PGS-009 |
| FEAT-010-AC-06 | Two inserts with the same `session_id` both succeed and receive increasing `arrival_seq` values. Verified by: Unit (`tests/unit/backend/repositories/test_raw_session_repository.py`). | DB-001, D-09 |
| FEAT-010-AC-07 | An `ingest_rejections` insert with `errors = '[]'` fails with 23514; an `ingest_batches` row with `source = 'csv_upload'` and NULL `filename` fails with 23514. Verified by: Integration (`tests/integration/db/test_raw_store.py`). | FR-028, FR-010 |
| FEAT-010-AC-08 | `alembic upgrade head`, `downgrade base`, `upgrade head` succeed with the three tables present. | TST-040 |

## Definition of Done

- All FEAT-010 acceptance criteria pass; `database/schema.sql` regenerated (PGS-017); `alembic check` clean.
- Repository docstrings cite DB-001..DB-005; delivered in the Phase 4 PR (AGT-013).

## Implementation Notes

- Never insert `arrival_seq` explicitly; duplicate detection orders by it (TRD 20 §8; AGT-043).
- Map the 18 float feature columns and `mic_noise_level_dbfs`/`speech_duration_s` with `sqlalchemy.Double`; convert numpy scalars with `float()` before binding (TRD 20 §8).
- Never truncate `raw_sessions` in tests; use a fresh migrated database per test session (TRD 20 §8).
- `session.py` is an existing skeleton file (ARC-050); it will also hold `ProcessedSession` (FEAT-011).
