# Wireframe v0.2 Update Report

Date: 26 October 2026 · Branch `docs/wireframes-v0.2` (from `main` at a1c718c) · Requested by Megan Stubbs (project coordinator): replace the wireframes in the repository with v0.2 and bring the TRDs, design documents and backlog in line now · Not a Block 3 checkpoint: no prompt was run and no code changed.

## 1. What changed

- `specs/UI-wireframe/`: the five v0.1 wireframes (`Main.dc.html` SRC-09, `Resident.dc.html` SRC-10, `Admission.dc.html` SRC-11, `Alerts.dc.html` SRC-18, `Analytics.dc.html` SRC-19) are deleted (they remain in Git history); `echowell-wireframes-v0.2.html` and `WIREFRAMES.md` are added as SRC-21.
- Wireframe v0.2 follows the electronic-health-record pattern: Resident list → Resident chart (Summary first, detail in sections). Four plain statuses (Changed, Needs attention, Learning, Usual) with a colour and a shape each. The Alert review page is folded into the chart; data and device problems move to a Study team page (formerly Analytics).
- TRD 24 records the decisions: D-108 (v0.2 adopted, SRC-21), D-109 (four display statuses, list order), D-110 (pages and navigation; Alert review page retired), D-111 (content kept although not drawn in v0.2), D-112 (visual tokens, Source Sans 3, dark mode), D-113 (UI wording, `checkins_started` event), D-114 (API additions); new open questions OQ-31 (what turns a resident yellow; when a device is offline) and OQ-32 (room numbers). Older decisions D-05, D-17, D-23, D-30, D-31, D-44, D-46, D-67 are marked amended or superseded.
- Numbering: the checkpoint 2 PR (GitHub PR #4, merged 26 Oct 2026) added D-103 to D-107 and OQ-30, so this update uses D-108 onward and OQ-31 onward. After PR #4 was merged, `main` was merged into this branch and the version numbers and revision rows of the files both PRs touched were renumbered: TRD 18 v0.15, TRD 21 v0.12, TRD 24 v0.18, BACKLOG.md v0.9, IMPLEMENTATION_ROADMAP.md v0.7 (the wireframe rows follow the checkpoint 2 rows).

## 2. Requirement IDs

IDs are kept wherever the requirement survives (text updated); requirements of removed screen elements are marked "(Retired by TRD 24 D-110: …)" with where they went; new requirements take the next free number.

| Document | Retired | Added |
|---|---|---|
| TRD 11 (v0.13) | UX-005, UX-020–024, UX-030–033, UX-035, UX-039, UX-064 (moved), UX-088, UX-125 (moved), UX-136–138, UX-180, UX-246, UX-300–305, UX-311, UX-319, UX-323 | UX-252, UX-253, UX-400–UX-412, UX-420–UX-423, UX-430–UX-433 |
| TRD 04 (v0.11) | FE-103, FE-131, FE-139 | FE-206–FE-211 |
| TRD 02 (v0.5) | FR-136, FR-139, FR-195, FR-207, FR-260, FR-261, FR-265, FR-278, FR-321 | FR-302 |
| TRD 05 (v0.13) | — | API-138 |
| TRD 09 (v0.9) | CUS-037 | — |

Feature files keep their IDs and file names (97 features). Retitled: FEAT-064 App chrome, FEAT-065 Resident list page, FEAT-066 Resident chart frame and Summary, FEAT-067 Voice trends, FEAT-068 Check-in log and Baseline sections, FEAT-069 Alarm review panel in the chart (absorbs the old FEAT-070 scope), FEAT-070 Device section of the chart (ID reused), FEAT-071 Staff notes, FEAT-072 Study team page. Every active UX ID is owned by exactly one frontend feature (`BACKLOG.md` §5.6).

## 3. API changes (D-114; no new endpoint, table or database enum)

- `ResidentOverviewRow`, `ResidentDetail`: + `needs_attention`, `attention_reasons` (`baseline_stalled`, `high_set_aside`), `alarm_reviewed`, `restart_cause`; `ResidentDetail` + `window` (`DateWindow` gains `days`).
- `OverviewSummary`: `{changed, needs_attention, learning, usual}` (test data 2 / 2 / 0 / 6).
- `sort=alarm` order: Changed, Needs attention, Learning, Usual (test data R09, R10, R03, R08, R01, R02, R04, R05, R06, R07).
- `CheckinEventType` + `checkins_started`; `CheckinEvent` + `device_code`; `EpochInfo` + `from_value`, `to_value`; `Device` + `uploaded_on_as_of_date`.
- Data-alert `detail` texts follow the v0.2 "Data problems to follow up" wording (titles unchanged). The API keeps kind order (R08, R05, R03, D02); the Study team page shows R08, R03, R05, D02 (UX-307).

## 4. Files changed

91 files. TRDs 00–25 except 24's numbering note above (each changed TRD has a new version and one 26 Oct 2026 revision row); `docs/design/` UI_Architecture, Frontend_Architecture, Repository_Structure, OpenAPI_Spec, Backend_Architecture, Database_ERD, Analytics_Architecture (now versioned, with a revision table), Testing_Architecture and Deployment_Architecture ("Revised" line); 47 feature files; BACKLOG.md, IMPLEMENTATION_ROADMAP.md, MVP_READINESS_CHECKLIST.md, DEPLOYMENT_CHECKLIST.md. Not changed: historical reports in `docs/reports/`, older revision-history rows, `specs/prompts/` (they name only the `specs/UI-wireframe/` directory), all code.

## 5. Checks

| Check | Result |
|---|---|
| grep for the deleted file names, `/alerts` and `/analytics` pages, "Residents overview", "Running change tally", "Alarms first", SRC-09/10/11/18/19 as current sources | only intentional hits (superseded-source rows, retirement notes, revision rows, API endpoint paths that still exist) |
| Markdown tables of every changed file | consistent column counts (the only flagged rows are ASCII sketches inside code blocks) |
| Mermaid diagrams changed in TRD 04, 11 and the design docs | parse with mermaid 10.9.1 |
| TRD 19 YAML and JSON examples | parse; required lists match properties |
| Test-data expectations (order, summary 2/2/0/6, data problems, Study team values) across TRD 11, 13, 14, 19, 09 and features | consistent |
| New text with the forbidden facility name (AGT-019) | none added |
| UX ownership | each active UX ID owned by exactly one feature |

## 6. Follow-ups outside this PR

- Code: the checkpoint 2 skeleton (PR #4) loads IBM Plex in `frontend/app/layout.tsx`; FEAT-062 switches it to Source Sans 3 in checkpoint 7.
- API fields of D-114 are built in checkpoint 4 (FEAT-027, FEAT-028, FEAT-029, FEAT-014).
- Dark-mode and below-line-bar contrast are checked before checkpoint 7 is approved (UX-224, TRD 03 NFR-063).

## 7. Questions for the algorithm lead

| # | Question |
|---|---|
| W-1 | D-109 / OQ-31: yellow comes only from the `baseline_stalled` and `high_set_aside` data alerts (R05's held-back check-ins and D02's silent day stay study-team items). Agree? Should a device with no upload turn its residents yellow, and after one or two silent days? |
| W-2 | The wireframe has no "Learning" filter; it is shown only when someone is Learning. OK? |
| W-3 | D-111 keeps content not drawn in v0.2: Login, Admin, Sign out, note types, "Previous notes", "Previous reviews", the baseline slot and data table of the change-score chart, bar colour by alarm state, "Show all devices", Downloads, the notes privacy hint (SEC-124). Keep all? |
| W-4 | New admissions pills: outside the facility range shown as red "Changed", within as green "Usual". Or neutral pills, since this compares with the facility, not with the resident's own usual? |
| W-5 | D-114 API additions (section 3) built in checkpoint 4. OK? |
| W-6 | D-112: Source Sans 3 replaces IBM Plex; dark mode is a Should. The grey change-score bars need a 1px outline to reach 3:1 (kept from v0.1). OK? |
| W-7 | Backlog: FEAT-069 now holds the whole review panel and FEAT-070 is reused for the chart's Device section; FEAT-066 complexity Medium → High, FEAT-068 Low → Medium, FEAT-070 P1 Low. OK? |
| W-8 | Tests: E2E-09 now saves a second review on R09 after E2E-18's first one (the "Mark as reviewed" path is gone). OK, or move it to R10? NFR-133 drops the "CT" time-zone abbreviation to match "Oct 30, 2:28 PM". OK? |
| W-9 | OQ-32: room numbers on the resident list (the wireframe asks; UX-001 forbids room data today). |

## 8. Review round 1 resolutions (26 October 2026)

The algorithm lead (Shaba) answered W-1..W-9 on GitHub PR #5 and requested changes. Every answer is applied on this branch.

| # | Answer | Resolution | Files changed |
|---|---|---|---|
| W-1 | Keep the OQ-31 rule: only `baseline_stalled` and `high_set_aside` turn a resident yellow. A device with no upload is device health, not resident status; if it is ever surfaced through status, wait for two consecutive silent days. | OQ-31 Answered, D-115. UX-433 states the rule; the wireframe's Device-section question becomes a decided note; "interim" wording removed. | TRD 24, 02, 04, 05, 07, 09, 11, 13, 14, 19, 23; FEAT-027, FEAT-029, FEAT-065, FEAT-070; MVP checklist; BACKLOG; design docs; wireframe and WIREFRAMES.md |
| W-2 | Show the Learning filter only when someone is Learning. | No change (already so). | — |
| W-3 | Keep the D-111 content; make sure the SEC-124 privacy hint is represented if it is required. | No change. SEC-124 is a Must and the hint "Do not enter names or other identifying details." is already required by TRD 11 UX-121 and FEAT-071. | — |
| W-4 | Use neutral pills for New admissions ("In range" / "Out of range"). | D-117: neutral `RangePill` "Out of range" / "In range" (ink on surface, no status colour, no glyph); "○ Learning" stays for the two waiting states. UX-185, FE-092, new `RangePill` in the TRD 04 inventory, FEAT-073, the wireframe table. | TRD 04, 11, 24; FEAT-073; UI_Architecture; wireframe |
| W-5 | Build the D-114 API additions in checkpoint 4. | No change (planned for checkpoint 4, section 6). | — |
| W-6 | Source Sans 3, dark mode as a Should and the 1px bar outline are fine. | No change. | — |
| W-7 | Backlog moves and complexity changes are fine. | No change. | — |
| W-8 | Move E2E-09 to R10 so it does not depend on E2E-18; keep "CT" in timestamps. | D-118 (amends D-73): the `@mutating` order is E2E-18 on R09, the FE-193 reminder step on R10, then E2E-09 on R10; E2E-09/FE-187 assert only R10 facts. FEAT-069-AC-07 (two reviews on one alarm) moves to a component test. D-119: date-time values end with "CT" ("Oct 30, 2:28 PM CT"): UX-003, NFR-133, AC-NFR-10, FE-151, the TRD 04 §4.11 format and every date-time example (88 strings) and the wireframe's sample times. | TRD 03, 04, 09, 11, 13, 14, 16, 23, 24, 25; FEAT-062, FEAT-065, FEAT-066, FEAT-069, FEAT-070, FEAT-071, FEAT-072, FEAT-076; roadmap; Testing_Architecture, UI_Architecture; wireframe |
| W-9 | Follow UX-001: no room numbers; update the wireframe. | OQ-32 Answered, D-116. The wireframe's room question is replaced by the UX-001 rule ("No room numbers and no room sort"); UX-001 cites D-116. | TRD 24, 02, 04, 11; FEAT-065; design docs; wireframe and WIREFRAMES.md |

New IDs: D-115, D-116, D-117, D-118, D-119 (TRD 24 v0.19). RAQ-018 no longer lists OQ-31, since its note is no longer an open question.

Also answered on PR #17 by W-5: the D-114 read-model fields are added in checkpoint 4, not in the checkpoint 3 database PR.

