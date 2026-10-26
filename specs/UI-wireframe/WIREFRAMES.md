# EchoWell clinical dashboard wireframes, v0.2

Open `echowell-wireframes-v0.2.html` in any browser. It's a single self-contained file, clickable, built on pipeline test data v0.1 (Oct 1–30, 2026, 10 residents). No audio and no real residents.

## What changed from v0.1

v0.1 put everything on one screen per view. v0.2 follows the layout staff already know from EHRs like Epic and Cerner: pick a resident from a list, open their chart, see the current status first, then go into detail only if needed. This responds to Tal's feedback that facility staff need a very simple screen with green/yellow/red status.

- **Four plain statuses.** Changed (red), Needs attention (yellow), Usual (green), and Learning (grey, used while a baseline forms). Each status pairs a colour with a shape, so it never relies on colour alone.
- **The alert review and staff notes now live inside the resident's chart** instead of on a separate Alerts screen. The resident list shows a badge with the count of unreviewed alarms.
- **Data and device problems moved to the Study team screen**, so staff only see what they can act on.
- **All v0.1 content is kept.** Nothing was dropped, only regrouped.
- **Open questions are marked inline.** Use "Show wireframe notes" to hide them when presenting.

## Screens

| Screen | Who it's for | What it shows |
|---|---|---|
| Resident list | Floor staff, charge nurse | Every resident with one status and a one-line reason; alarms sort first |
| Resident chart: Summary | Floor staff | Status right now, what it means, what to do, links to detail |
| Chart: Review and notes | Charge nurse | Alert review form (possible explanations, outcome, note) and staff notes |
| Chart: Voice trends | Nurse, study team | Change score with the alarm line at 5, plus the 7 scored measurements |
| Chart: Baseline | Nurse, study team | Progress toward 16 check-ins, the frozen baseline, restart rule |
| Chart: Check-in log | Nurse, study team | 30-day counts (used, set aside, held back, missed) and events |
| Chart: Device | Staff, study team | Online status, last upload, firmware, shared use, history |
| New admissions | Clinical lead | Comparison with the facility range (placeholder; not in test data) |
| Study team | Study team only | Check-in quality, where check-ins are lost, usable check-ins by resident, alarm timing, devices |

## Open questions carried forward

- Does a saved review reset the change score or turn the alarm off? Who may review, and how soon?
- Can the pipeline rank the 2–3 measurements leaning most, to show on the Summary in plain words?
- Final clinical wording for each status (confirm with the PI).
- Measurement names wait on Team 1's openSMILE output names.
- New admissions screen waits on the admission group and facility range.

## Decided in the v0.2 review

- A device that stops uploading is a study-team device problem and does not turn the resident yellow (TRD 24 D-115).
- No room numbers or room sort on the resident list (UX-001; TRD 24 D-116).
- New admissions use neutral "Out of range" / "In range" pills, because they are compared with the facility range, not with their own usual (TRD 24 D-117).
- Times show the facility time zone: "Oct 30, 2:28 PM CT" (TRD 24 D-119).
