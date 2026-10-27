# FEAT-075 Accessibility and responsive conformance (WCAG 2.1 AA, light and dark, v0.2 layouts)

| Field | Value |
|---|---|
| Epic | Frontend |
| Build phase | Phase 8 (TRD 25) |
| Priority | P1 |
| Complexity | Medium |
| MVP status | Required |
| Dependencies | FEAT-065, FEAT-067, FEAT-068, FEAT-069, FEAT-070, FEAT-071, FEAT-072, FEAT-073, FEAT-074 |
| Status | Not Started |

## Purpose

Bring every page of the wireframe v0.2 dashboard (SRC-21) to WCAG 2.1 AA in both the light and the dark colour scheme and to the responsive layout of TRD 11 §4.12, and prove it with automated tests: status never by colour alone (pill glyph, label and border), text alternatives for every chart, keyboard operation of the filter buttons, study-ID links, chart section navigation, review and note forms and admin tabs with the visible 3px focus ring, 44px touch targets, no animation, contrast of every token pair in both schemes, a correct heading outline, live regions for status messages, the chart section navigation as a scrolling row below 760px, one column below 640px, and no page-level horizontal scroll from 320px. Verification uses axe on the single route list in both schemes (`a11y.spec.ts`), a keyboard-only test and the responsive tests.

## Business Context

- BR-12, BR-13 (staff of varying abilities and devices can use the dashboard), contract §11 (WCAG 2.1 AA), NFR-060..NFR-070.
- MVP-11 (zero serious/critical axe violations) is an MVP acceptance criterion; D-112 adds the dark scheme (Should), which must meet the same contrast limits.
- FRs covered (BACKLOG.md): FR-168 (change score chart text table available to assistive technology), FR-320 (every Study team chart has a text-table alternative).

## Referenced TRDs

- TRD 11 (v0.13) — owned by this feature: UX-220..UX-228, UX-230 (AA in both schemes, keyboard order, focus indicator, 44px targets, contrast of the §4.15 token pairs in both schemes, chart alternatives, heading outline, labels, live regions, no animation), UX-240..UX-245 (≥ 1024px layout, chart navigation row and pill below 760px, one column and 12px padding below 640px, no page-level horizontal scroll from 320px with the listed scrolling containers, 200 % zoom, wrapping header row and banner). Verified here but owned elsewhere: UX-004 and UX-250..UX-253 (FEAT-062), UX-229 (FEAT-064). Retired: UX-246 (Alert review stacking).
- TRD 04 (v0.11) FE-162..FE-165 (44px, focus ring, reduced motion, breakpoints incl. 760px), FE-211 (dark scheme, contrast in both schemes), FE-190 (`a11y.spec.ts`), FE-191 (`responsive.spec.ts`), FE-099, FE-097.
- TRD 03 NFR-060..NFR-070, NFR-140..NFR-142.
- TRD 13 TST-110 (axe route list), TST-111 (keyboard-only), TST-112, TST-113 (contrast), E2E-16, MVP-11.
- TRD 02 FR-168, FR-320; TRD 24 D-78, D-112.

## Scope

- Audit and fixes across all pages and components delivered by FEAT-062..FEAT-074: focus styles, target sizes, live regions, labels and `aria-describedby`, heading levels, scroll-container accessible names and `tabindex="0"`, reduced-motion CSS, breakpoint CSS (≥ 1024px, < 760px, < 640px), dark-scheme contrast.
- `frontend/tests/e2e/a11y.spec.ts`: axe with tags `wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa` on `/login`, `/residents`, the six R09 chart sections (`/residents/R09`, `/review`, `/trends`, `/baseline`, `/log`, `/device`), `/residents/R08`, `/admissions`, `/study`, `/admin`, each with `colorScheme: "light"` and `"dark"` (FE-190).
- `frontend/tests/e2e/responsive.spec.ts`: 320×568, 360×800, 375×812 and 390×844 on `/residents`, `/residents/R09` and `/residents/R09/trends` (D-78); 200 % zoom check.
- Keyboard-only E2E (TST-111) and the `<noscript>` message.

## Out of Scope

- Page features themselves (FEAT-065..FEAT-074) beyond accessibility fixes; token values (FEAT-062) except adjustments needed for contrast, which are reported.
- Manual screen-reader pass and the usability session (NFR-060 inspection part, NFR-069 demo) — recorded as inspection evidence, not automated here.
- Lighthouse performance budgets (FEAT-079).

## Functional Requirements

| ID | Requirement | Trace |
|---|---|---|
| FEAT-075-FR-01 | All pages shall meet WCAG 2.1 AA in the light and the dark scheme; axe (tags wcag2a, wcag2aa, wcag21a, wcag21aa) on the route list of FE-190 shall report zero serious or critical violations in both schemes. | UX-220, NFR-060, TST-110, FE-190 |
| FEAT-075-FR-02 | Status, alarm and outside-range information shall never be conveyed by colour alone: pills carry glyph, label and border; alarm bars the "▲" marker, "Alarm line" label and the data table; device status "●"/"○" and words. | UX-004, NFR-061 |
| FEAT-075-FR-03 | All functions shall be keyboard-operable in a logical order (app bar, main content top to bottom, chart section navigation before section content) without traps, reaching and operating the filter buttons, every study-ID link, the chart section navigation, "Review this alert", the explanation checkboxes, the "What did you find?" radios, the review note, "Save review", "Remind me in 24 hours", the note type select, the note textarea, "Add note" and the admin tabs. | UX-221, NFR-065, TST-111 |
| FEAT-075-FR-04 | Every focusable element shall show `outline: var(--focus-ring)` (3px solid `--link`) with 2px offset on `:focus-visible`. | UX-222, FE-163 |
| FEAT-075-FR-05 | Every interactive target (buttons, nav and section links, filter buttons, tile links, disclosure summaries) shall be at least 44 × 44 CSS px, except inline links within text. | UX-223, FE-162, NFR-064 |
| FEAT-075-FR-06 | Text contrast shall be ≥ 4.5:1 and non-text UI and chart graphics ≥ 3:1 against their background in both schemes; every TRD 11 §4.15 token pair shall be checked (analysis recorded in the frontend report) and any pair below the limit adjusted before checkpoint 7 is approved. | UX-224, FE-211, NFR-062, NFR-063, TST-113 |
| FEAT-075-FR-07 | Each chart (change score, sparklines, check-ins per day, usable by resident, facility range) shall have an accessible name, and the change score, check-ins-per-day and facility range charts a data table. | UX-225, FR-168, FR-320, TST-112 |
| FEAT-075-FR-08 | Each page shall have one `<h1>`, panels `<h2>`, sub-lists `<h3>`; form fields have visible `<label>`s or `<legend>`s bound by `for`/`id`; error and help texts linked with `aria-describedby`. | UX-226, UX-227 |
| FEAT-075-FR-09 | Status messages (filtering, saving, reminders, errors) shall be announced through `aria-live` regions without moving focus. | UX-228 |
| FEAT-075-FR-10 | Charts render without animation and no CSS transitions or animations run under `prefers-reduced-motion: reduce`. | UX-230, FE-164, FE-099 |
| FEAT-075-FR-11 | At widths ≥ 1024px the layout shall match SRC-21: the chart's section navigation as a 200px left column, the "More detail" tiles in one row of four, the measurement cards in two columns, "Where check-ins are lost" and "Usable check-ins by resident" side by side. | UX-240, FE-165 |
| FEAT-075-FR-12 | Below 760px the chart section navigation shall become a single horizontally scrolling row of links above the content (no wrapping) and the banner's status pill shall move below the facts. | UX-241, FE-165 |
| FEAT-075-FR-13 | Below 640px tiles, measurement cards, count tiles and the Study team columns shall stack in one column, the app bar navigation shall wrap below the brand and the page padding shall become 12px. | UX-242, FE-165 |
| FEAT-075-FR-14 | At every width ≥ 320px there shall be no page-level horizontal scroll; only the residents table (min 640px), the admissions table (min 640px), the change score chart (min 520px), the check-ins-per-day chart (min 560px) and the alarm timing table scroll inside their own keyboard-focusable (`tabindex="0"`), named containers. | UX-243, NFR-068 |
| FEAT-075-FR-15 | Text shall remain readable and functional at 200 % browser zoom; the resident-list header row and the chart banner wrap so that the filter buttons and the status pill move below the heading. | UX-244, UX-245, NFR-068 |
| FEAT-075-FR-16 | Every data region shall state its loading, empty and error state in words. | NFR-070 |
| FEAT-075-FR-17 | The dashboard shall work in the latest two stable Chrome, Edge, Firefox and Safari versions and on tablets ≥ 768px, and show "This dashboard needs JavaScript enabled." when JavaScript is disabled. | NFR-140, NFR-141, NFR-142 |
| FEAT-075-FR-18 | UI copy shall pass the forbidden-terms check in CI and keep plain-language labels for statistical terms ("change score", "held back"). | NFR-066, NFR-067, UX-167 |

## Inputs

- All pages and components from FEAT-062..FEAT-074; DS-07 E2E stack; seeded per-role sessions (D-74).

## Outputs

- Accessibility and responsive fixes in `frontend/styles/`, components and pages; `a11y.spec.ts`, `responsive.spec.ts`, keyboard spec; `<noscript>` text in the root layout; the token contrast table in `docs/reports/FRONTEND_IMPLEMENTATION_REPORT.md`.

## Data Flow

Playwright → per-role session → each route on DS-07 in the light and the dark scheme → axe scan, keyboard traversal, viewport checks (`document.documentElement.scrollWidth <= window.innerWidth`, chart navigation row) → violations fail the job.

## Dependencies

Required before implementation (BACKLOG.md): FEAT-065, FEAT-067, FEAT-068, FEAT-069, FEAT-070, FEAT-071, FEAT-072, FEAT-073, FEAT-074

- These features deliver the pages and interactive components whose conformance is verified here (FEAT-062..FEAT-064 and FEAT-066 through them); FEAT-076 (E2E harness) depends on this feature.

Features that build directly on this one (BACKLOG.md §4): FEAT-076.

## Database Impact

None.

## API Impact

None new. Tests read the DS-07 API through the pages.

## Frontend Impact

- All routes: `/login`, `/residents`, `/residents/[residentCode]` and its five section routes, `/admissions`, `/study`, `/admin`.
- Shared CSS: `frontend/styles/globals.css` (focus ring, reduced motion, breakpoints), component CSS modules; tests `frontend/tests/e2e/a11y.spec.ts`, `frontend/tests/e2e/responsive.spec.ts`.

## Analytics Impact

None.

## Security Requirements

None beyond the existing pages; accessibility code adds no third-party script (FE-064) — axe runs only in tests.

## Error Handling

- Any serious or critical axe violation in either scheme fails `a11y.spec.ts`; any page-level horizontal scroll fails `responsive.spec.ts`.
- Known false positives are not suppressed silently; any exclusion must name the rule and a requirement or OQ ID (TST-153 practice).

## Logging Requirements

None at runtime. CI publishes the axe report with the E2E artefacts.

## Testing Requirements

- E2E (Playwright): `a11y.spec.ts` on the FE-190 route list in light and dark (TST-110); keyboard-only flow (TST-111); `responsive.spec.ts` at 320×568, 360×800, 375×812 and 390×844 (FE-191) and E2E-16 at the same widths (no page scroll, residents table and change score chart scroll within their containers, chart navigation is a scrolling row, targets ≥ 44px); contrast via axe (TST-113) and the token-pair analysis; change score table reachable (TST-112).
- Component: chart accessible names and tables (UX-091, UX-360, UX-370, UX-193); live-region announcements for filtering and saving.
- Browser projects Chromium, Firefox, WebKit nightly (NFR-140, TST-100); tablet emulation ≥ 768px (NFR-141).
- Inspection: manual keyboard and screen-reader pass recorded in `docs/reports/FRONTEND_IMPLEMENTATION_REPORT.md` (NFR-060).

## Acceptance Criteria

| ID | Criterion | Realises |
|---|---|---|
| FEAT-075-AC-01 | `a11y.spec.ts` reports zero serious or critical axe violations on `/login`, `/residents`, the six R09 chart sections, `/residents/R08`, `/admissions`, `/study` and `/admin`, in the light and the dark scheme. | TST-110; FE-190; MVP-11; AC-UX-09 |
| FEAT-075-AC-02 | At each of 320×568, 360×800, 375×812 and 390×844, `document.documentElement.scrollWidth <= window.innerWidth` on `/residents`, `/residents/R09` and `/residents/R09/trends`, and the chart section navigation is one horizontally scrolling row. | FE-191; UX-241; UX-243; AC-UX-09 |
| FEAT-075-AC-03 | At 375×812 the residents table and the change score chart scroll within their named, focusable containers and every interactive target is at least 44px. | E2E-16; UX-223 |
| FEAT-075-AC-04 | A keyboard-only run reaches and operates every control listed in TST-111 with a visible 3px focus outline. | TST-111; AC-UX-09 |
| FEAT-075-AC-05 | axe colour-contrast checks pass on all routes in both schemes, and the token-pair contrast table shows every text pair ≥ 4.5:1 and every non-text pair ≥ 3:1 in light and dark. | TST-113; UX-224; FE-211 |
| FEAT-075-AC-06 | The R09 change score table has role `table` with a caption naming R09, and every Study team chart has a disclosure table or row accessible names. | TST-112; FR-168; FR-320 |
| FEAT-075-AC-07 | At 1280px the R09 chart shows the 200px section navigation beside the content and the four "More detail" tiles in one row; at 600px the tiles stack in one column and the page padding is 12px. Verified by: E2E (`responsive.spec.ts`). | UX-240; UX-242 |
| FEAT-075-AC-08 | With JavaScript disabled, the page shows "This dashboard needs JavaScript enabled." Verified by: E2E (`a11y.spec.ts`; TST-110, FE-190). | NFR-142 |

## Definition of Done

- All FEAT-075 acceptance criteria pass in Chromium on every PR and in Firefox/WebKit nightly.
- WCAG 2.1 AA statement (status never by colour alone, chart text tables, both colour schemes) satisfied (TRD 25 Phase 8 DoD).
- Batch report lists IDs and any token adjusted for contrast (AGT-022).

## Implementation Notes

- Phone widths: UX-243 requires no horizontal page scroll from 320px; NFR-068, FE-191 and E2E-16 test 320, 360, 375 and 390px (TRD 24 D-78).
- Scroll containers need `tabindex="0"` and an accessible name (UX-243), otherwise axe flags `scrollable-region-focusable`.
- Run the dark scheme with Playwright `colorScheme: "dark"`; there is no in-app toggle (FE-211).
- The route list: TRD 04 FE-190 names all six R09 chart sections, TRD 13 TST-110 lists nine routes (`/residents/R09`, `/review`, `/trends` only); this feature runs the longer FE-190 list, which covers TST-110.
- Playwright contexts use `timezoneId: "America/Los_Angeles"` (TRD 04 §8) so tests also prove facility-time rendering.
