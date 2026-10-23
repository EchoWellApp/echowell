# FEAT-012 Alert, review, note, data-alert, reference, audit and ground-truth tables

| Field | Value |
|---|---|
| Epic | Database |
| Build phase | Phase 4 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-011 |
| Status | Not Started |

## Purpose

Create the tables that carry alarm events and the human response to them (`alerts`, `alert_reviews`, `staff_notes`), rule-based data-quality flags (`data_alerts`), facility reference ranges for the experimental new-admission arm, the append-only `audit_logs`, and the test-only `evaluation_ground_truth` that the application role cannot read. Their constraints and grants guarantee that human-entered data survives rebuilds (natural keys, D-45), that reviews, notes and audit entries are append-only, and that the answer key never reaches the pipeline (D-38).

## Business Context

- BR-11 and BR-13: one alarm per epoch, staff reviews and notes recorded without changing the tally (DME-007, D-37, OQ-05).
- BR-16: append-only audit trail (FR-252, SEC-102) and append-only notes (FR-192, SEC-113).
- BR-12: data-quality flags for the study team, separate from health alarms (D-36).
- BR-14: facility reference ranges stored with method and count; method undefined in the MVP (FR-204, OQ-08).
- BR-15: the answer key stays out of the pipeline (DB-007, DME-024, D-38).

## Referenced TRDs

- TRD 20 PGS-029, PGS-036, PGS-041..PGS-044; §4.6.17–§4.6.21, §4.6.23, §4.6.24 DDL; §4.7 (`alerts_one_active_per_epoch_uq`, `data_alerts_open_subject_uq`); §4.8 triggers and grants; AC-PGS-03, AC-PGS-09, AC-PGS-14, AC-PGS-15.
- TRD 06 DB-007, DB-010, DB-011.
- TRD 23 DME-007, DME-021..DME-025; §4.2.17–§4.2.24; §4.3.2, §4.3.2a, §4.3.7 state machines; §4.6 model mapping.
- TRD 12 SEC-102, SEC-112..SEC-114.
- TRD 02 FR-192, FR-204, FR-252.
- TRD 13 TST-041.
- TRD 24 D-36, D-37, D-38, D-45, D-49.

## Scope

- Migration 0001 sections for `alerts`, `alert_reviews`, `data_alerts`, `staff_notes`, `facility_reference_ranges`, `audit_logs`, `evaluation_ground_truth` exactly as TRD 20 §4.6.17–§4.6.21, §4.6.23, §4.6.24.
- Partial unique indexes `alerts_one_active_per_epoch_uq` and `data_alerts_open_subject_uq` (NULLS NOT DISTINCT, open rule kinds only) required by PGS-029 and PGS-041.
- Triggers `audit_logs_no_update_delete`, `audit_logs_no_truncate` (calling `reject_mutation()`), `alerts_set_updated_at`, `data_alerts_set_updated_at`.
- Grants per §4.8: `echowell_app` SELECT, INSERT on `audit_logs`, `staff_notes`, `alert_reviews`; SELECT, INSERT, UPDATE on `alerts`, `data_alerts`; SELECT, INSERT, UPDATE, DELETE on `facility_reference_ranges`; USAGE, SELECT on `audit_logs_id_seq`; no privilege on `evaluation_ground_truth`; `echowell_readonly` SELECT on all seven including `evaluation_ground_truth`.
- Models (TRD 23 §4.6): `alarm.py:Alert`, `AlertReview`, `DataAlert` (existing file `alarm.py`), `staff_note.py:StaffNote`, `reference_range.py:FacilityReferenceRange`, `audit_log.py:AuditLog`, `evaluation.py:EvaluationGroundTruth`.
- Repositories on the `DATABASE_URL` engine for alerts, reviews, data alerts, notes (current notes = not superseded), reference ranges and audit log inserts; no repository on that engine maps `EvaluationGroundTruth` (it is read only by `backend/services/analytics_summary.py` through `DATABASE_READONLY_URL`, delivered by FEAT-035).
- Grant tests per D-49 (`tests/integration/db/test_grants.py`, completing TST-041 and SEC-114).

## Out of Scope

- The audit service and action vocabulary (FEAT-015).
- Alert generation and lifecycle upserts (FEAT-048, FEAT-053), data-alert rules (FEAT-050).
- Review, snooze, data-alert and notes endpoints (FEAT-031, FEAT-032, FEAT-033) and their service transactions (e.g. `data_problem` review creating a `review_flagged_data_problem` row).
- The ground-truth loader script (FEAT-057) and the Alarm timing check (FEAT-035).
- Reference-range computation method (FEAT-095, Future, OQ-08).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-012-FR-01 | The seven tables shall be created with exactly the columns, types, nullability, defaults and named constraints of TRD 20 §4.6.17–§4.6.21, §4.6.23, §4.6.24. | PGS-006 |
| FEAT-012-FR-02 | `alerts` shall allow at most one non-closed row per `epoch_id` (`alerts_one_active_per_epoch_uq`) and at most one row per `(epoch_id, session_id)` (`alerts_epoch_session_uq`). | PGS-029, D-45 |
| FEAT-012-FR-03 | `alerts.snoozed_until` and `snoozed_by` shall be both NULL or both set; `acknowledged_by`/`acknowledged_at` likewise; `closed` iff `closed_reason` and `closed_at` set, with `closed_reason` in {`epoch ended`, `admin`, `superseded by rebuild`}. | PGS-043, TRD 20 §4.6.17 |
| FEAT-012-FR-04 | `alert_reviews` shall be append-only for the app (SELECT, INSERT), require an `outcome` of `review_outcome`, store `explanations` as 0–20 lower-case codes, and `note` NULL or 1–2000 characters. | PGS-042, DME-021 |
| FEAT-012-FR-05 | `data_alerts` shall enforce the subject CHECK (device_silent → device only; baseline_stalled, possible_other_speaker, high_set_aside → resident only; review_flagged_data_problem → resident and `alert_review_id`, no run), `pipeline_run_id` NULL iff review-flagged, resolved ⇔ `resolved_at`, and one open row per `(kind, resident_id, device_id)` for rule kinds. | PGS-041, D-36 |
| FEAT-012-FR-06 | `staff_notes.body` shall be 1–2000 characters after trimming; a note may be superseded by at most one later note (`staff_notes_supersedes_uq`) and never by itself; the app has SELECT, INSERT only, so corrections are new rows with `supersedes_id`. | PGS-036, FR-192, DB-010, SEC-113 |
| FEAT-012-FR-07 | `audit_logs` shall have `id bigserial`, actor type/id, action matching `^[a-z_]+(\.[a-z_]+){1,2}$`, entity type/id, `details` object, `ip` (inet), `request_id`, and the row-level UPDATE/DELETE and statement-level TRUNCATE triggers calling `reject_mutation()`; the app has SELECT, INSERT only. | PGS-044, SEC-102, FR-252 |
| FEAT-012-FR-08 | `evaluation_ground_truth` shall hold `resident_code` (unique), `planted_change`, `true_onset_date` (NULL iff `None`), `source_file`; `echowell_app` shall have no privilege on it and `echowell_readonly` SELECT. | DB-007, DME-024, PGS-040, D-38 |
| FEAT-012-FR-09 | `facility_reference_ranges` shall store `feature_key` (19 features), `sex` (F, M or NULL), `low` ≤ `high`, `method`, `n_residents` ≥ 1, `computed_at`, `pipeline_run_id`, unique `NULLS NOT DISTINCT (facility_id, feature_key, sex, pipeline_run_id)`. | FR-204 |
| FEAT-012-FR-10 | Tables carrying human state (`alerts`, `alert_reviews`, `staff_notes`, `data_alerts`) shall be addressable by natural keys so later upserts keep their primary keys across rebuilds: alerts by `(epoch_id, session_id)`, rule data alerts by `(kind, resident_id, device_id)`. | DME-025, D-45, ARC-045 |
| FEAT-012-FR-11 | The schema shall let the review and snooze services change only `alerts.status`, `acknowledged_*` and `snoozed_*`; no review or snooze column exists on `scores` or `cusum_state`. | DME-007, DME-022, D-37 |
| FEAT-012-FR-12 | The audit insert repository shall be callable inside the caller's transaction (no own commit), so an audited change and its audit row commit or roll back together. | DB-011 |
| FEAT-012-FR-13 | Connected as `echowell_app`, UPDATE and DELETE on `raw_sessions`, `audit_logs`, `alert_reviews` and `staff_notes`, `DELETE` on `alerts`, and `SELECT` on `evaluation_ground_truth` shall fail; `SET ROLE echowell_readonly` shall fail. | SEC-114, SEC-112, TST-041, D-49 |
| FEAT-012-FR-14 | No table shall store SRC-03 expected statuses, baselines or scores; only planted change type and onset date live in `evaluation_ground_truth`. | DB-007 |

## Inputs

- `residents`, `devices`, `users`, `epochs`, `pipeline_runs` (FEAT-009, FEAT-011); enums `alert_status`, `review_outcome`, `data_alert_kind`, `data_alert_status`, `note_type`, `actor_type` (FEAT-008).

## Outputs

- Seven tables, two partial unique indexes, four triggers, grants; models and repositories.

## Data Flow

Pipeline runner (FEAT-053) upserts `alerts` and rule `data_alerts` by natural key → review service inserts `alert_reviews` and updates `alerts.status`/`acknowledged_*` (and may insert a `review_flagged_data_problem` row) → snooze service updates `snoozed_*` → notes service inserts `staff_notes` (corrections as superseding rows) → every audited action inserts one `audit_logs` row in its own transaction (FEAT-015) → the ground-truth loader (migrator role) fills `evaluation_ground_truth` in `test_v0_1`, read only through `DATABASE_READONLY_URL`.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-011

- FEAT-011 provides `epochs` and `pipeline_runs`, referenced by `alerts`, `data_alerts` and `facility_reference_ranges`.

Features that build directly on this one (BACKLOG.md §4): FEAT-013, FEAT-015, FEAT-057.

## Database Impact

- Tables created: `alerts`, `alert_reviews`, `data_alerts`, `staff_notes`, `facility_reference_ranges`, `audit_logs`, `evaluation_ground_truth`.
- Constraints: `alerts_epoch_session_uq`, `alerts_cusum_ck`, `alerts_closed_ck`, `alerts_closed_reason_ck`, `alerts_ack_ck`, `alerts_ack_status_ck`, `alerts_snooze_ck`, `alert_reviews_explanations_ck`, `alert_reviews_note_ck`, `data_alerts_alert_review_uq`, `data_alerts_subject_ck`, `data_alerts_run_ck`, `data_alerts_resolved_ck`, `data_alerts_detected_ck`, `data_alerts_text_ck`, `staff_notes_body_ck`, `staff_notes_supersedes_uq`, `staff_notes_not_self_ck`, `facility_reference_ranges_uq`, `facility_reference_ranges_feature_ck`, `facility_reference_ranges_sex_ck`, `facility_reference_ranges_bounds_ck`, `facility_reference_ranges_n_ck`, `facility_reference_ranges_method_ck`, `audit_logs_action_ck`, `audit_logs_details_ck`, `audit_logs_actor_ck`, `evaluation_ground_truth_resident_code_uq`, `evaluation_ground_truth_onset_ck`, `evaluation_ground_truth_text_ck`.
- Indexes: `alerts_one_active_per_epoch_uq`, `data_alerts_open_subject_uq`.
- Triggers: `audit_logs_no_update_delete`, `audit_logs_no_truncate`, `alerts_set_updated_at`, `data_alerts_set_updated_at`.
- Sequence: `audit_logs_id_seq` (USAGE, SELECT to `echowell_app`).

## API Impact

None exposed. Backs E-13, E-14, E-15, E-16, E-18, E-22..E-24, E-28..E-30 delivered by later features.

## Frontend Impact

None.

## Analytics Impact

None computed. `evaluation_ground_truth` is never read by `analytics/` (AGT-057).

## Security Requirements

- `echowell_app` has no privilege on `evaluation_ground_truth`; only `echowell_readonly` can read it, through `DATABASE_READONLY_URL` in `test_v0_1` (PGS-040, D-38, SEC-116).
- Append-only: `audit_logs` (trigger + grants), `alert_reviews` and `staff_notes` (grants) (SEC-102, SEC-113).
- No DELETE on `alerts` or `data_alerts` for the app (PGS-021).
- `details` and notes never store passwords, tokens, keys or feature values (enforced by the services, FEAT-015, FEAT-033).

## Error Handling

| Failure | Behaviour | Trace |
|---|---|---|
| UPDATE/DELETE on `audit_logs` as app | 42501; as owner `EW001` | AC-PGS-03 |
| Migrator with `echowell.allow_purge = 'on'` | DELETE on `audit_logs` succeeds; UPDATE on `raw_sessions` still fails | AC-PGS-09, PGS-019 |
| Second open `device_silent` for D02 | 23505 | AC-PGS-15 |
| `device_silent` without `pipeline_run_id` | 23514 | AC-PGS-15 |
| DELETE on `alerts` as app | 42501 | AC-PGS-15 |
| SELECT on `evaluation_ground_truth` as app | 42501 | AC-PGS-14 |
| Invalid audit action (`Auth.Login`, `login`) | 23514 | PGS-044 |

## Logging Requirements

None from the tables; `audit_logs` is itself the audit store written by FEAT-015.

## Testing Requirements

- Integration (`tests/integration/test_schema_behaviour.py`): AC-PGS-03, AC-PGS-09, AC-PGS-14 (without the loader: app SELECT and `SET ROLE` fail with 42501; readonly SELECT succeeds), AC-PGS-15; PGS-029 (second non-closed alert per epoch fails), PGS-036 (second note superseding the same note fails), PGS-042, PGS-043, PGS-044 (each TRD 12 action inserts; `Auth.Login` and `login` fail).
- Integration (`tests/integration/db/test_grants.py`): TST-041 and SEC-114 complete set (UPDATE/DELETE as `echowell_app` on `raw_sessions`, `audit_logs`, `alert_reviews`, `staff_notes` fail and leave rows unchanged; SELECT on `evaluation_ground_truth` fails; readonly SELECT succeeds and INSERT/UPDATE/DELETE fail).
- Integration: DB-011 transaction test helper (forced rollback leaves neither a change nor an audit row) using the audit insert repository.
- Static check: `grep -rn "evaluation_ground_truth\|EvaluationGroundTruth" analytics backend/repositories` returns nothing (AGT-057, DB-007).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-012-AC-01 | As `echowell_app_login`, `UPDATE audit_logs …` and `DELETE FROM audit_logs` fail. Verified by: Integration (`tests/integration/test_schema_behaviour.py`). | AC-PGS-03, FR-252 |
| FEAT-012-AC-02 | As `echowell_migrator` with `SET echowell.allow_purge = 'on'`, `DELETE FROM audit_logs` succeeds and `UPDATE raw_sessions` still fails. Verified by: Integration (`tests/integration/test_schema_behaviour.py`). | AC-PGS-09 |
| FEAT-012-AC-03 | As `echowell_app_login`, `SELECT count(*) FROM evaluation_ground_truth` and `SET ROLE echowell_readonly` fail with 42501; as `echowell_readonly_login` the SELECT succeeds. Verified by: Integration (`tests/integration/test_schema_behaviour.py`). | AC-PGS-14, SEC-114 |
| FEAT-012-AC-04 | A second `open` `device_silent` data alert for D02 fails with 23505; a `device_silent` row without `pipeline_run_id` fails with 23514; `DELETE FROM alerts` as app fails with 42501. Verified by: Integration (`tests/integration/test_schema_behaviour.py`). | AC-PGS-15 |
| FEAT-012-AC-05 | A second non-closed alert for the same epoch fails with 23505; a closed alert plus a new open alert for the same epoch succeed. Verified by: Integration (`tests/integration/test_schema_behaviour.py`). | PGS-029 |
| FEAT-012-AC-06 | An alert with `snoozed_until` set and `snoozed_by` NULL fails with 23514. Verified by: Integration (`tests/integration/test_schema_behaviour.py`). | PGS-043 |
| FEAT-012-AC-07 | UPDATE and DELETE on `alert_reviews` and `staff_notes` as `echowell_app_login` fail; two notes with the same `supersedes_id` fail with 23505. Verified by: Integration (`tests/integration/test_schema_behaviour.py`). | SEC-113, PGS-036, PGS-042 |
| FEAT-012-AC-08 | `audit_logs` accepts actions `auth.logout` and `auth.login.succeeded` and rejects `Auth.Login` and `login` with 23514. Verified by: Integration (`tests/integration/test_schema_behaviour.py`). | PGS-044 |
| FEAT-012-AC-09 | `grep -rn "evaluation_ground_truth" analytics` returns nothing. Verified by: Inspection (run the command in the criterion and check its output). | AC-AGT-02, DB-007 |

## Definition of Done

- All FEAT-012 acceptance criteria pass; the TRD 25 Phase 4 DoD items for `data_alerts`, `alert_reviews`, `evaluation_ground_truth`, `alerts.snoozed_until`/`snoozed_by` and alert uniqueness on `(epoch_id, session_id)` are met.
- `database/schema.sql` regenerated; `alembic check` clean; delivered in the Phase 4 checkpoint PR of Block 3.

## Implementation Notes

- `UNIQUE NULLS NOT DISTINCT` and the `NULLS NOT DISTINCT` partial index require PostgreSQL ≥ 15 (TRD 20 §8); write them with `op.execute()`.
- Do not create a repository for `EvaluationGroundTruth` on the main engine; FEAT-035 opens the separate read-only engine in `analytics_summary.py` only.
- `alerts.closed_reason = 'admin'` is admitted by the CHECK, but v0.1 has no manual closure path (AGT-058, OQ-05); do not add one.
- The `review_explanations` codes are validated by the application against config; the database checks only their format (TRD 20 §4.4 note, OQ-25).
