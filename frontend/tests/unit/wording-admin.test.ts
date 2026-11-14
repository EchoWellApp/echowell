// req: FE-013, UX-181, UX-185, UX-186, UX-192..UX-195, UX-213, UX-216, UX-217, UX-219
import * as w from "@/lib/wording";

describe("admissions wording", () => {
  it("keeps the exact TRD 11 copy", () => {
    expect(w.ADMISSIONS_NOTE).toBe(
      "Future / experimental. Not in pipeline test v0.1: the test data has no admission group or facility range yet. Open question for Shaba and the PI.",
    );
    expect(w.admissionsEmpty("test_v0_1")).toBe(
      "No new admissions. The pipeline test data v0.1 has no admission group.",
    );
    expect(w.admissionsEmpty("production")).toBe("No new admissions.");
    expect(w.admissionsOwnBaseline(5, 16)).toBe("5 of 16");
    expect(w.admissionsComparisonHeading("A01")).toBe("A01 compared with facility range");
    expect(w.admissionsTransition(16)).toBe(
      "After 16 usable check-ins, the resident moves to the resident list and is compared with their own baseline instead.",
    );
    expect(w.admissionsRangeMethod(10, "Oct 30", "p10_p90")).toBe(
      "Range from 10 current residents, computed Oct 30 (method: p10_p90).",
    );
    expect(w.ADMISSIONS_COMPARISON_TEXT).toEqual({
      outside_range: "Outside facility range",
      within_range: "Within facility range",
      not_enough_checkins: "Not enough check-ins yet",
      range_not_available: "Facility range not available yet",
    });
  });

  it("labels measurements and formats values", () => {
    expect(w.admissionsMeasurementLabel("articulation_rate_syl_per_s")).toBe(
      "Slower while talking",
    );
    expect(w.admissionsMeasurementLabel("mfcc2")).toBe("mfcc2");
    expect(w.admissionsValue(null)).toBe("—");
    expect(w.admissionsValue(-1.234)).toBe("−1.23");
    expect(w.admissionsValue(2)).toBe("2");
    expect(w.admissionsRange(null, 2)).toBe("—");
    expect(w.admissionsRange(0.1, 0.35)).toBe("0.1–0.35");
  });
});

describe("admin wording", () => {
  it("keeps the exact TRD 11 copy", () => {
    expect(w.adminDeactivateConfirm("a@example.com")).toBe(
      "Deactivate a@example.com? They will not be able to sign in.",
    );
    expect(w.adminUploadResult(283, 0, 2)).toBe("Accepted 283 · Rejected 0 · Duplicates 2");
    expect(w.adminFileNotAccepted("Header wrong.")).toBe(
      "The file was not accepted: Header wrong. Nothing was stored.",
    );
    expect(w.adminFileNotAccepted("Header wrong")).toBe(
      "The file was not accepted: Header wrong. Nothing was stored.",
    );
    expect(w.adminNightlyMissing("Oct 31")).toBe("Nightly run missing for Oct 31");
    expect(w.adminApiOk("1.0")).toBe("API status: ok · version 1.0");
    expect(w.adminApiDegraded("1.0")).toBe(
      "API status: degraded (database unavailable) · version 1.0",
    );
    expect(w.adminApiDegraded(null)).toBe("API status: degraded (database unavailable)");
    expect(w.ADMIN_API_UNAVAILABLE).toBe("API status: unavailable");
    expect(w.ADMIN_UPLOAD_SYNTHETIC).toBe(
      "Only synthetic or test data may be uploaded to this environment.",
    );
  });

  it("formats run counts and run states", () => {
    expect(w.adminCountsText({})).toBe("—");
    expect(w.adminCountsText({ usable: 3, arrivals: 4, other: 1 })).toBe("Arrivals 4 · Usable 3");
    expect(w.adminRunState("failed")).toBe("Pipeline run failed.");
    expect(w.adminRunState("running")).toBe(
      "Pipeline run started. Status: Running (refreshed every 5 seconds).",
    );
  });
});
