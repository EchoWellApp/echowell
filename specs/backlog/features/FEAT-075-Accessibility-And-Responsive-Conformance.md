# FEAT-075 Accessibility and responsive conformance (WCAG 2.1 AA)

| Field | Value |
|---|---|
| Epic | Frontend |
| Build phase | Phase 8 (TRD 25) |
| Priority | P1 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-065, FEAT-067, FEAT-068, FEAT-070, FEAT-071, FEAT-072, FEAT-073, FEAT-074 |
| Status | Not Started |

## Purpose

Bring every page of the dashboard to WCAG 2.1 AA and the responsive layout of TRD 11 §4.12, and prove it with automated tests: status never by colour alone, text alternatives for every chart, keyboard operation of sort, links, forms and tabs with visible focus, 44px touch targets, no animation under reduced motion, contrast ≥ 4.5:1, correct heading outline, live regions for status messages, no page-level horizontal scroll at phone widths, and breakpoint layouts. Verification uses axe on the single route list (`a11y.spec.ts`), a keyboard-only test and the responsive tests.

## Business Context

- BR-12, BR-13 (staff of varying abilities and devices can use the dashboard), contract §11 (WCAG 2.1 AA), NFR-060..NFR-070.
- MVP-11 (zero serious/critical axe violations) is an MVP acceptance criterion.
- FRs covered (BACKLOG.md): FR-168 (tally chart text table available to assistive technology), FR-320 (every analytics chart has a text-table alternative).

## Referenced TRDs

- TRD 11 UX-220..UX-230 (AA conformance, keyboard order, focus indicator, 44px targets, contrast, chart alternatives, heading outline, labels, live regions, `lang` and titles, no animation), UX-240..UX-246 (breakpoint layouts, no horizontal page scroll, focusable scroll containers, 200 % zoom, wrapping headers, alert/analytics stacking), UX-004.
- TRD 04 FE-162..FE-165 (44px, focus ring, reduced motion, breakpoints), FE-190 (`a11y.spec.ts`), FE-191 (`responsive.spec.ts`), FE-099, FE-097.
- TRD 03 NFR-060..NFR-070 (AA, colour, contrast, chart outlines, target size, keyboard, plain language, wording CI check, zoom and widths, usability, words for states), NFR-140..NFR-142 (browsers, tablets, JavaScript required message).
- TRD 13 TST-110 (axe route list), TST-111 (keyboard-only), TST-113 (contrast), TST-112, E2E-16, MVP-11.
- TRD 02 FR-168, FR-320.

## Scope

- Audit and fixes across all pages and components delivered by FEAT-062..FEAT-074: focus styles, target sizes, live regions, labels and `aria-describedby`, heading levels, scroll-container accessible names and `tabindex="0"`, reduced-motion CSS, breakpoint CSS (≥ 1024px, 640–1023px, < 640px).
- `frontend/tests/e2e/a11y.spec.ts` (axe with tags `wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa` on `/login`, `/residents`, `/residents/R09`, `/residents/R08`, `/alerts`, `/analytics`, `/admissions`, `/admin`).
- `frontend/tests/e2e/responsive.spec.ts` (320×568, 360×800, 375×812 and 390×844 on `/residents` and `/residents/R09`, D-78; 200 % zoom check).
- Keyboard-only E2E (TST-111) and the `<noscript>` message.

## Out of Scope

- Page features themselves (FEAT-065..FEAT-074) beyond accessibility fixes.
- Manual screen-reader pass and the usability session (NFR-060 inspection part, NFR-069 demo) — recorded as inspection evidence, not automated here.
- Lighthouse performance budgets (FEAT-079).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-075-FR-01 | All pages shall meet WCAG 2.1 AA; axe (tags wcag2a, wcag2aa, wcag21a, wcag21aa) on the TST-110 route list shall report zero serious or critical violations. | UX-220, NFR-060, TST-110, FE-190 |
| FEAT-075-FR-02 | Status, alarm and outside-range information shall never be conveyed by colour alone (▲ glyph, text label, border style). | UX-004, NFR-061 |
| FEAT-075-FR-03 | All functions shall be keyboard-operable in a logical order (header, main top to bottom, left column before right) without traps, reaching and operating the sort control, every "Open" link, note textarea and type select, "Mark as reviewed", alarm cards, explanation checkboxes, outcome radios, "Save review", "Remind me in 24 h" and the admin tabs. | UX-221, NFR-065, TST-111 |
| FEAT-075-FR-04 | Every focusable element shall show `outline: var(--focus-ring)` (3px solid ink) with 2px offset on `:focus-visible`. | UX-222, FE-163 |
| FEAT-075-FR-05 | Every interactive element shall render at least 44 × 44 CSS px. | UX-223, FE-162, NFR-064 |
| FEAT-075-FR-06 | Text contrast shall be ≥ 4.5:1 and non-text UI and chart graphics ≥ 3:1 (grey bars outlined #8A8A85). | UX-224, NFR-062, NFR-063, TST-113 |
| FEAT-075-FR-07 | Each chart shall have a text alternative: an accessible name, and data tables for the tally chart, facility range chart and every analytics chart. | UX-225, FR-168, FR-320, TST-112 |
| FEAT-075-FR-08 | Each page shall have one `<h1>`, sections `<h2>`, sub-lists `<h3>`; form fields have visible `<label>`s bound by `for`/`id`; error and help texts linked with `aria-describedby`. | UX-226, UX-227 |
| FEAT-075-FR-09 | Status messages (sorting, saving, errors) shall be announced through `aria-live` regions without moving focus. | UX-228 |
| FEAT-075-FR-10 | Pages shall declare `lang="en"` and unique titles "<Page> – EchoWell"; charts render without animation and no CSS transitions or animations run under `prefers-reduced-motion: reduce`. | UX-229, UX-230, FE-164, FE-099 |
| FEAT-075-FR-11 | Breakpoints: ≥ 1024px wireframe layout (4 tiles, 3-column devices, 2-column features, review and log side by side); 640–1023px 2 × 2 tiles, 2-column grids, review above log; < 640px single columns, nav wrapping below the title, page padding 16px 12px. | UX-240, UX-241, UX-242, FE-165 |
| FEAT-075-FR-12 | At every width ≥ 320px there shall be no page-level horizontal scroll; only the residents table (min 900px), admissions table (min 760px), tally chart (min 700px), analytics daily chart (min 760px) and timing table (min 640px) scroll inside their own keyboard-focusable, named containers. | UX-243, UX-246, NFR-068 |
| FEAT-075-FR-13 | Text shall remain readable and functional at 200 % browser zoom; the residents and tally section headings wrap so "Sort by" and the chart subtitle move below the heading. | UX-244, UX-245, NFR-068 |
| FEAT-075-FR-14 | Below 1024px the Alert review page stacks queues then panel, and the Analytics page stacks funnel and by-resident sections. | UX-246 |
| FEAT-075-FR-15 | Every data region shall state its loading, empty and error state in words. | NFR-070 |
| FEAT-075-FR-16 | The dashboard shall work in the latest two stable Chrome, Edge, Firefox and Safari versions and on tablets ≥ 768px, and show "This dashboard needs JavaScript enabled." when JavaScript is disabled. | NFR-140, NFR-141, NFR-142 |
| FEAT-075-FR-17 | UI copy shall pass the forbidden-terms check in CI and keep plain-language labels for statistical terms. | NFR-066, NFR-067 |

## Inputs

- All pages and components from FEAT-062..FEAT-074; DS-07 E2E stack; seeded per-role sessions (D-74).

## Outputs

- Accessibility and responsive fixes in `frontend/styles/`, components and pages; `a11y.spec.ts`, `responsive.spec.ts`, keyboard spec; `<noscript>` text in the root layout.

## Data Flow

Playwright → per-role session → each route on DS-07 → axe scan, keyboard traversal, viewport checks (`document.documentElement.scrollWidth <= window.innerWidth`) → violations fail the job.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-065, FEAT-067, FEAT-068, FEAT-070, FEAT-071, FEAT-072, FEAT-073, FEAT-074

- These features deliver the pages and interactive components whose conformance is verified here; FEAT-076 (E2E harness) depends on this feature.

## Database Impact

None.

## API Impact

None new. Tests read the DS-07 API through the pages.

## Frontend Impact

- All routes: `/login`, `/residents`, `/residents/[residentCode]`, `/alerts`, `/analytics`, `/admissions`, `/admin`.
- Shared CSS: `frontend/styles/globals.css` (focus ring, reduced motion, breakpoints), component CSS modules; tests `frontend/tests/e2e/a11y.spec.ts`, `frontend/tests/e2e/responsive.spec.ts`.

## Analytics Impact

None.

## Security Requirements

None beyond the existing pages; accessibility code adds no third-party script (FE-064) — axe runs only in tests.

## Error Handling

- Any serious or critical axe violation fails `a11y.spec.ts`; any page-level horizontal scroll fails `responsive.spec.ts`.
- Known false positives are not suppressed silently; any exclusion must name the rule and a requirement or OQ ID (TST-153 practice).

## Logging Requirements

None at runtime. CI publishes the axe report with the E2E artefacts.

## Testing Requirements

- E2E (Playwright): `a11y.spec.ts` on the exact TST-110 route list (FE-190); keyboard-only flow (TST-111); `responsive.spec.ts` at 320×568, 360×800, 375×812 and 390×844 (FE-191) and E2E-16 at the same widths (no page scroll, table scrolls within container, targets ≥ 44px); contrast via axe (TST-113); tally table reachable (TST-112).
- Component: chart accessible names and tables (UX-091, UX-360, UX-370, UX-193); live-region announcements for sort and save.
- Browser projects Chromium, Firefox, WebKit nightly (NFR-140, TST-100); tablet emulation ≥ 768px (NFR-141).
- Inspection: manual keyboard and screen-reader pass recorded in `docs/reports/FRONTEND_IMPLEMENTATION_REPORT.md` (NFR-060).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-075-AC-01 | `a11y.spec.ts` reports zero serious or critical axe violations on `/login`, `/residents`, `/residents/R09`, `/residents/R08`, `/alerts`, `/analytics`, `/admissions` and `/admin`. | TST-110; FE-190; MVP-11; AC-FE-08 |
| FEAT-075-AC-02 | At each of 320×568, 360×800, 375×812 and 390×844, `document.documentElement.scrollWidth <= window.innerWidth` on `/residents` and `/residents/R09`. | FE-191; AC-FE-08 |
| FEAT-075-AC-03 | At 375×812, `/residents` and `/residents/R09` have no horizontal page scroll, the residents table scrolls within its container, and every interactive target is at least 44px. | E2E-16 |
| FEAT-075-AC-04 | A keyboard-only run reaches and operates every control listed in TST-111 with a visible 3px focus outline. | TST-111; AC-UX-09 |
| FEAT-075-AC-05 | axe colour-contrast checks pass on all routes. | TST-113 |
| FEAT-075-AC-06 | The R09 tally chart table has role `table` with a caption naming R09, and every analytics chart has a disclosure table. | TST-112; FR-168; FR-320 |
| FEAT-075-AC-07 | With JavaScript disabled, the page shows "This dashboard needs JavaScript enabled." | NFR-142 |

## Definition of Done

- All FEAT-075 acceptance criteria pass in Chromium on every PR and in Firefox/WebKit nightly.
- WCAG 2.1 AA statement (status never by colour alone, chart text tables) satisfied (TRD 25 Phase 8 DoD).
- Batch report lists IDs and the viewport inconsistency below (AGT-022).

## Implementation Notes

- Phone widths: UX-243 requires no horizontal page scroll from 320px; NFR-068, FE-191 and E2E-16 now all test 320, 360, 375 and 390px (plus 768 and 1280px for NFR-068) (TRD 24 D-78).
- Scroll containers need `tabindex="0"` and an accessible name (UX-243), otherwise axe flags `scrollable-region-focusable`.
- Use `prefers-reduced-motion` media queries globally; Recharts animation is already disabled (FE-099).
- Playwright contexts use `timezoneId: "America/Los_Angeles"` (TRD 04 §8) so tests also prove facility-time rendering.
