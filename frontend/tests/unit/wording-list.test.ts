// req: FE-013, UX-041, UX-043, UX-401, UX-403, UX-405, UX-407, TRD 11 §4.3.6, FEAT-065-FR-09
import residents from "@/tests/fixtures/ds07/residents.json";
import R07 from "@/tests/fixtures/ds07/resident/R07.json";
import type { ResidentDetail, ResidentRow, ResidentsResponse } from "@/lib/types";
import {
  LIST_FILTERS,
  PI_MARKER,
  filterButtonText,
  listCaption,
  listNote,
  openChartName,
  showingAnnouncement,
  showingOfTotal,
  whatsHappening,
} from "@/lib/wording";

const data = residents as unknown as ResidentsResponse;
const meta = data.meta;
const base = data.items.find((r) => r.resident_code === "R01")!;
const r = (patch: Partial<ResidentRow>): ResidentRow => ({ ...base, ...patch });

describe("whatsHappening templates (TRD 11 §4.3.6)", () => {
  it("Changed, not reviewed / reviewed", () => {
    const row = r({ status: "alarm_on", alarm_since: "2026-10-21", alarm_reviewed: false });
    expect(whatsHappening(row, "changed", meta)).toBe(
      "Changed from their usual since Oct 21. Not reviewed yet.",
    );
    expect(whatsHappening({ ...row, alarm_reviewed: true }, "changed", meta)).toBe(
      "Changed from their usual since Oct 21. Reviewed.",
    );
  });

  it("Changed in another year shows the year; no alarm date falls back", () => {
    const row = r({ alarm_since: "2025-12-30", alarm_reviewed: null });
    expect(whatsHappening(row, "changed", meta)).toBe(
      "Changed from their usual since Dec 30, 2025. Not reviewed yet.",
    );
    expect(whatsHappening(r({ alarm_since: null }), "changed", meta)).toBe(
      "Changed from their usual. Not reviewed yet.",
    );
  });

  it("Needs attention: stalled, set aside, both (stalled first)", () => {
    const progress = { n_usable: 13, n_required: 16 };
    const sa = { ...base.last_30_days, set_aside: 7 };
    expect(
      whatsHappening(
        r({ attention_reasons: ["baseline_stalled"], baseline_progress: progress }),
        "needs_attention",
        meta,
      ),
    ).toBe("Missing many check-ins. Baseline stuck at 13 of 16.");
    expect(
      whatsHappening(
        r({ attention_reasons: ["high_set_aside"], last_30_days: sa }),
        "needs_attention",
        meta,
      ),
    ).toBe("7 check-ins too noisy or too short to use.");
    expect(
      whatsHappening(
        r({
          attention_reasons: ["high_set_aside", "baseline_stalled"],
          baseline_progress: progress,
          last_30_days: sa,
        }),
        "needs_attention",
        meta,
      ),
    ).toBe(
      "Missing many check-ins. Baseline stuck at 13 of 16. 7 check-ins too noisy or too short to use.",
    );
  });

  it("Learning", () => {
    expect(
      whatsHappening(r({ baseline_progress: { n_usable: 5, n_required: 16 } }), "learning", meta),
    ).toBe("Learning their usual: 5 of 16 check-ins so far.");
  });

  it("Usual: epoch 1, and restarts by device, firmware, software", () => {
    expect(whatsHappening(base, "usual", meta)).toBe("Within their usual range.");
    const restarted = r({ current_epoch: 2, baseline_restarted_on: "2026-10-13" });
    expect(whatsHappening({ ...restarted, restart_cause: "device" }, "usual", meta)).toBe(
      "Usual. Baseline restarted Oct 13 after a new device.",
    );
    expect(whatsHappening({ ...restarted, restart_cause: "firmware" }, "usual", meta)).toBe(
      "Usual. Baseline restarted Oct 13 after a firmware change.",
    );
    expect(whatsHappening({ ...restarted, restart_cause: "software" }, "usual", meta)).toBe(
      "Usual. Baseline restarted Oct 13 after a software change.",
    );
    expect(whatsHappening({ ...restarted, restart_cause: null }, "usual", meta)).toBe(
      "Usual. Baseline restarted Oct 13 after a new device.",
    );
  });

  it("reads a resident detail (current_epoch object, baseline)", () => {
    const d = R07 as unknown as ResidentDetail;
    expect(whatsHappening(d, "usual", meta)).toBe(
      "Usual. Baseline restarted Oct 13 after a new device.",
    );
    expect(whatsHappening({ ...d, current_epoch: null }, "usual", meta)).toBe(
      "Within their usual range.",
    );
    expect(whatsHappening(d, "learning", meta)).toBe(
      "Learning their usual: 16 of 16 check-ins so far.",
    );
  });
});

describe("resident list copy", () => {
  it("filter labels, announcements and captions", () => {
    expect(LIST_FILTERS).toEqual(["all", "changed", "needs_attention", "learning", "usual"]);
    expect(filterButtonText("needs_attention", 2)).toBe("Needs attention (2)");
    expect(filterButtonText("all", null)).toBe("All (—)");
    expect(showingAnnouncement("all")).toBe("Showing all residents");
    expect(showingAnnouncement("needs_attention")).toBe("Showing needs attention residents");
    expect(listCaption("all")).toBe("Residents in the study, all");
    expect(openChartName("R09")).toBe("Open chart for R09");
    expect(showingOfTotal(500, 612)).toBe("Showing 500 of 612 residents.");
  });

  it("note keeps the PI marker until approved (UX-407)", () => {
    expect(listNote()).toBe(
      "A status is a prompt to check on someone, not a diagnosis. [Final clinical wording: confirm with PI]",
    );
    expect(listNote(false)).toContain(PI_MARKER);
    expect(listNote(true)).toBe("A status is a prompt to check on someone, not a diagnosis.");
  });
});
