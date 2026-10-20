# FEAT-030 Alerts list and UI configuration APIs (GET /api/v1/alerts, GET /api/v1/config/ui)

| Field | Value |
|---|---|
| Epic | Backend API |
| Build phase | Phase 5 (TRD 25) |
| Priority | P0 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-021, FEAT-014 |
| Status | Not Started |

## Purpose

Serve the change-alarm list that drives the Alert review page queue, the "Alerts (<n>)" navigation count and the overview badges (`GET /api/v1/alerts`), and the operational UI configuration the review form needs — the explanation checklist and the snooze hours (`GET /api/v1/config/ui`). Alerts appear only inside the dashboard; there is no outbound notification channel in the MVP.

## Business Context

- BR-11 (alarm when the tally crosses the line, reviewed by staff): list of alarms with device, current tally, open days, review and snooze state.
- BR-13 (staff review workflow): the review checklist and the "Remind me in <h> h" value come only from configuration.
- BR-12: the nav count "Alerts (<n>)" is the total of not-yet-reviewed alarms.
- FRs covered (BACKLOG.md): FR-108, FR-109, FR-261, FR-262.

## Referenced TRDs

- TRD 05 API-080 (alerts list), API-137 (UI configuration), API-057, API-069, API-100, API-121.
- TRD 19 §4.3 E-13, E-32; schemas `Alert`, `AlertList`, `UiConfig`, `ReviewExplanation`, `ReviewExplanationCode`, `AlertStatus`.
- TRD 09 CUS-022 (dashboard-only surfacing, nav count), CUS-023, CUS-024 (chart data contract the page combines with this list), CUS-025 (list fields and order), CUS-026 (wording), CUS-037 (one card per non-closed alarm), CUS-041 ("Leaning most" returned with each alarm), §4.8 (card texts).
- TRD 07 §4.7 `OperationalConfig` (`alert_snooze_hours`, `review_explanations`); TRD 21 ENV-020 (config keys, not env vars).
- TRD 23 §4.2.17 (alerts), §4.4.1 (open days, alert tally, reviewed badge).
- TRD 14 TDV-067; TRD 19 OAS-027; AC-API-14 (alerts half).
- TRD 24 D-05 (dashboard only), D-64 (`GET /config/ui`); BACKLOG §12 Q-02 (phase split of `leaning_most`).

## Scope

- Router `backend/api/alarms.py` (existing skeleton file, AGT-010) handler `GET /api/v1/alerts` calling `services.alert_service.list`.
- Router `backend/api/config.py` handler `GET /api/v1/config/ui` calling `config_service.ui_config` (TRD 05 §4.12).
- Alert DTO assembly: device code, epoch number, current tally from `cusum_state`, open days, reviewed flag, review count, last reviewed time, snooze fields, closed reason, and the `leaning_most` field slot.
- Filters `status`, `resident_code`; ordering by `triggered_at` ascending; pagination and `meta`.

## Out of Scope

- Computing `leaning_most` values: owned by `analytics/alert_generator.leaning_most` and wired into this endpoint by FEAT-048 (Phase 6, BACKLOG §12 Q-02).
- Creating, closing or reconciling alerts (pipeline, FEAT-048 and FEAT-053); reviews and snooze (FEAT-031); data alerts (FEAT-032).
- The queue's three-group ordering (not reviewed and not snoozed, snoozed, reviewed) and card texts, which the frontend applies (FR-261, FEAT-069).
- Any SMS, e-mail or push channel (FR-109, OQ-06).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-030-FR-01 | `GET /api/v1/alerts` shall accept optional `status` ∈ {open, acknowledged, closed} and `resident_code` plus `limit`/`offset`; any other value returns 422 `INVALID_QUERY_PARAMETER`. | API-080; TRD 19 E-13; FR-108 |
| FEAT-030-FR-02 | Items shall be ordered by `triggered_at` ascending and returned in the `AlertList` envelope with `meta`; `total` of `?status=open` is the nav count "Alerts (<n>)" (data alerts are never counted). | API-080, CUS-025, CUS-022; TRD 19 E-13 |
| FEAT-030-FR-03 | Each `Alert` shall carry `id`, `resident_code`, `device_code` (device of the alert's epoch), `epoch_number`, `session_id`, `triggered_at`, `local_date`, `cusum_value`, `current_tally` (= `cusum_state.current_tally` of the alert's epoch), `open_days` (= as-of local date − `local_date` in days), `status`, `reviewed` (true when status is `acknowledged`), `review_count` and `last_reviewed_at` (from `alert_reviews`), `snoozed_until`, `snoozed_by`, `leaning_most` and `closed_reason`. | API-080, CUS-025; TRD 23 §4.4.1; FR-262 |
| FEAT-030-FR-04 | `leaning_most` shall always be present as an array of at most 3 `ScoredFeatureKey` values; its values are supplied by the `leaning_most` provider delivered in FEAT-048 (an empty list when no feature has a positive mean, CUS-041). | API-080, CUS-041; BACKLOG §12 Q-02 |
| FEAT-030-FR-05 | Alerts shall be surfaced only through the authenticated API and dashboard; no code path in this feature shall send e-mail, SMS or push messages. | FR-109, CUS-022, D-05 |
| FEAT-030-FR-06 | `GET /api/v1/config/ui` (all user roles) shall return `UiConfig` `{meta, alert_snooze_hours, review_explanations}` read from the `config_parameters` rows of the active profile on every request, with `review_explanations` as `{code, label}` items in configured order. | API-137; TRD 19 E-32; TRD 07 §4.7; ENV-020 |
| FEAT-030-FR-07 | API responses shall return facts only; wording such as "Alarm since", "open <n> days" and the tally to 1 decimal is rendered by the frontend. | CUS-026, OAS-011 |
| FEAT-030-FR-08 | Every non-closed alert shall carry `status`, `reviewed`, `snoozed_until`, `local_date` and `resident_code`, which are the inputs of the change-alarm queue order (not reviewed and not snoozed, snoozed, reviewed; then alarm date, then resident code) that the frontend applies; the API order itself stays `triggered_at` ascending. | FR-261, CUS-037; TRD 09 §4.8 |

## Inputs

- Bearer JWT (admin, clinician, researcher); query `status`, `resident_code`, `limit`, `offset`.
- Tables `alerts`, `epochs`, `devices`, `residents`, `cusum_state`, `alert_reviews`, `pipeline_runs`, `config_parameters`, `facilities`.

## Outputs

- 200 `AlertList`; 200 `UiConfig`; 422 Problem for invalid parameters.

## Data Flow

1. Auth dependencies authorise any user role.
2. `alert_service.list` queries `alerts` joined to `epochs` (epoch number, device), `residents` (code) and `cusum_state` (current tally), with a grouped `alert_reviews` subquery for `review_count` and `max(created_at)`; filters apply; order by `triggered_at`.
3. Open days are computed from the as-of local date of `meta`; `leaning_most` is filled by the provider hook (FEAT-048 implementation).
4. `config_service.ui_config` reads `alert_snooze_hours` and `review_explanations` of `PIPELINE_PROFILE` from `config_parameters` and builds `UiConfig`.

## Dependencies

- FEAT-021 (Role-based authorization matrix): roles for GET /alerts and GET /config/ui.
- FEAT-014 (Read-model derivations): as-of local date, alert open days and alert tally queries.
- Downstream: FEAT-031 (reviews and snooze return the `Alert` DTO built here), FEAT-048 (fills `leaning_most`), FEAT-060, FEAT-069.

## Database Impact

- Tables read: `alerts` (all columns of TRD 20 §4.6.17), `epochs` (`epoch_number`, `device_id`), `devices` (`device_code`), `residents` (`resident_code`), `cusum_state` (`current_tally`), `alert_reviews` (`alert_id`, `created_at`), `config_parameters` (`alert_snooze_hours`, `review_explanations`), `pipeline_runs`.
- Tables created or modified: none.

## API Impact

- Exposed: `GET /api/v1/alerts` (E-13; 200 `AlertList`; 422 `INVALID_QUERY_PARAMETER`), `GET /api/v1/config/ui` (E-32; 200 `UiConfig`).
- Consumed: none.

## Frontend Impact

None in this feature. Consumers: `AppHeader` (open count), `AlertQueue`, `AlertCard`, `ResidentHeader` via `getAlerts({status, residentCode})`; `AlertReviewForm` via `getUiConfig()` (TRD 04 §4.6.2), delivered by FEAT-064, FEAT-069, FEAT-070.

## Analytics Impact

None in this feature. `leaning_most` is computed by `analytics.alert_generator.leaning_most` (TRD 09 §4.8) and wired in by FEAT-048; this feature performs no calculation beyond date differences and counts.

## Security Requirements

- Authentication: bearer JWT; admin, clinician and researcher allowed on both endpoints; API key and anonymous 401 (TRD 12 §4.6).
- Configuration values are read from the database, never from environment variables (ENV-020).
- No resident PII; reviewer identities appear only as user UUIDs (`snoozed_by`).

## Error Handling

- Invalid `status`, `limit`, `offset` → 422 `INVALID_QUERY_PARAMETER`; an unknown `resident_code` filter returns an empty list (TRD 19 E-13 lists only 422).
- Missing `alert_snooze_hours` or `review_explanations` row for the profile → the built-in `OperationalConfig` default of `analytics/config.py` is used (ANL-031 default rule).
- Database unavailable → 503.

## Logging Requirements

- Access log `request_completed` (LOG-010); no audit rows; no notification events (LOG-113).

## Testing Requirements

- Integration (`tests/integration/api/test_alerts.py`, marker `integration`) with fixture alerts: ordering by `triggered_at`; status filter; `reviewed`/`review_count`/`last_reviewed_at` after inserting `alert_reviews` rows; `open_days` from the as-of; `current_tally` from `cusum_state`; `leaning_most` present as an array; 422 on bad status.
- Integration (`tests/integration/api/test_config_ui.py`): test_v0_1 returns 24 h and the 5 codes in order (API-137 verification); a changed `alert_snooze_hours` row is visible on the next request without restart.
- Contract: TST-061, TST-064.
- DS-07 values (FEAT-060, TDV-067, AC-API-14, OAS-027 except `leaning_most`, which FEAT-048 asserts).
- Performance: TST-122 on `/alerts` (FEAT-079).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-030-AC-01 | `GET /api/v1/alerts?status=bogus` returns 422 `INVALID_QUERY_PARAMETER`. | API-080 |
| FEAT-030-AC-02 | For two fixture alerts with `triggered_at` 2026-10-24 and 2026-10-21, the list returns the 2026-10-21 alert first, and `?status=open` `total` equals the number of `open` alerts only. | API-080, CUS-025, CUS-022 |
| FEAT-030-AC-03 | After one `alert_reviews` row is inserted and the alert set to `acknowledged`, the item has `reviewed` true, `review_count` 1 and `last_reviewed_at` equal to the review's `created_at`. | API-080, TRD 23 §4.4.1 |
| FEAT-030-AC-04 | With DS-07 loaded, `GET /alerts?status=open` returns exactly R09 (`device_code` D09, `local_date` 2026-10-21, `open_days` 9, `current_tally` 26.830256 ±1e-6) and R10 (D10, 2026-10-24, `open_days` 6, `current_tally` 13.418183 ±1e-6), in that order, both `reviewed` false. | AC-API-14, TDV-067, OAS-027 |
| FEAT-030-AC-05 | Under profile test_v0_1, `GET /api/v1/config/ui` returns `alert_snooze_hours` 24 and `review_explanations` codes cold_cough_sore_throat, dental_dentures, medication_change, poor_sleep_unusual_day, room_device_moved in that order with their TRD 19 E-32 labels. | API-137 |
| FEAT-030-AC-06 | Every alert item contains the key `leaning_most` with an array value of length ≤ 3, and both responses validate against `AlertList` / `UiConfig` with `meta`. | API-080, CUS-041, TST-061, TST-064 |
| FEAT-030-AC-07 | A dependency scan of `backend/` finds no e-mail, SMS or push client library and no code that sends alerts outside the API. | FR-109, AC-CUS-08 |

## Definition of Done

- Both endpoints implemented with TRD 19 schemas; the `leaning_most` provider seam documented for FEAT-048.
- Integration tests pass; DS-07 criterion FEAT-030-AC-04 passes in the FEAT-060 suite.
- Requirement markers (TST-013); coverage ≥ 85 %; OpenAPI drift check passes (FEAT-038).

## Implementation Notes

- `backend/api/alarms.py` is the existing skeleton file that serves `/api/v1/alerts`; do not rename it (AGT-010, API-008). `backend/models/alarm.py` holds the Alert model.
- Use one SQL query with the `alert_reviews` aggregate as a lateral or grouped subquery; avoid N+1 queries.
- Keep `leaning_most` behind a small provider function in `alert_service` so FEAT-048 only replaces that function; until FEAT-048 is merged the provider yields an empty list (BACKLOG §12 Q-02 interim plan), and no acceptance criterion of this feature asserts its values.
- `open_days` uses facility-local dates of the as-of and the alert, not UTC dates.
- `current_tally` is shown to 1 decimal only in the UI; the API returns full float64 (OAS-011).
