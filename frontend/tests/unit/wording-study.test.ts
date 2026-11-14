// req: UX-017, UX-352..UX-355, UX-358, UX-360, UX-363..UX-366, UX-370, UX-373, §4.4 silent text, UX-056, FE-013
import type { Meta } from "@/lib/types";
import {
  studyAlarmsNote,
  studyBaselinesNote,
  studyByResidentRowName,
  studyCsvName,
  studyDailyChartName,
  studyDayCount,
  studyDayLabel,
  studyDayTooltip,
  studyDownloadFailed,
  studyExpectedNote,
  studyFirmwareText,
  studyHeldBackNote,
  studyInUseRange,
  studyJoinCodes,
  studyLastUpload,
  studyPassedNote,
  studyPeriodLine,
  studyProblemTag,
  studyReceivedNote,
  studySilentNote,
  studySilentText,
  studyTimingAlarms,
  studyTimingDelay,
  studyTimingFalseAlarms,
} from "@/lib/wording";
import analytics from "@/tests/fixtures/ds07/analytics.json";

const meta = analytics.meta as Meta;

describe("Study team wording", () => {
  it("period line with and without the answer-key clause (UX-017)", () => {
    const p = { from: "2026-10-01", to: "2026-10-30" };
    expect(studyPeriodLine(meta, p)).toBe(
      "pipeline test data v0.1, Oct 1–30, 2026 · numbers match the pipeline answer key",
    );
    expect(studyPeriodLine({ ...meta, pipeline_profile: "production" }, p)).toBe(
      "pipeline test data v0.1, Oct 1–30, 2026",
    );
  });

  it("joins codes (§4.4)", () => {
    expect(studyJoinCodes([])).toBe("");
    expect(studyJoinCodes(["R01"])).toBe("R01");
    expect(studyJoinCodes(["R01", "R02"])).toBe("R01 and R02");
    expect(studyJoinCodes(["R01", "R02", "R03"])).toBe("R01, R02 and R03");
  });

  it("baselines note (UX-354)", () => {
    const b = { formed: 9, residents: 10, forming_resident_codes: [] as string[], restarts: [] };
    expect(studyBaselinesNote(b)).toBe("All baselines formed");
    expect(studyBaselinesNote({ ...b, forming_resident_codes: ["R08"] })).toBe("R08 still forming");
    expect(studyBaselinesNote({ ...b, forming_resident_codes: ["R03", "R08"] })).toBe(
      "R03, R08 still forming",
    );
    const r = (k: number) => [{ resident_code: "R07", restart_count: k }];
    expect(studyBaselinesNote({ ...b, forming_resident_codes: ["R08"], restarts: r(1) })).toBe(
      "R08 still forming; R07 restarted once",
    );
    expect(studyBaselinesNote({ ...b, restarts: r(2) })).toBe("R07 restarted twice");
    expect(studyBaselinesNote({ ...b, restarts: r(4) })).toBe("R07 restarted 4 times");
    expect(studyBaselinesNote({ ...b, restarts: r(0) })).toBe("All baselines formed");
  });

  it.each([
    [0, 0, [], "none in this period"],
    [1, 1, ["R09"], "R09; not reviewed yet"],
    [2, 2, ["R09", "R10"], "R09, R10; neither reviewed yet"],
    [3, 3, ["R01", "R09", "R10"], "R01, R09, R10; none reviewed yet"],
    [3, 1, ["R01", "R09", "R10"], "R01, R09, R10; 1 not reviewed yet"],
    [1, 0, ["R09"], "R09; reviewed"],
    [2, 0, ["R09", "R10"], "R09, R10; both reviewed"],
    [3, 0, ["R01", "R09", "R10"], "R01, R09, R10; all reviewed"],
    [1, 0, [], "reviewed"],
  ])("alarms note %i raised, %i open (UX-355)", (count, open, codes, text) => {
    expect(
      studyAlarmsNote({ count, not_reviewed_count: open, resident_codes: codes as string[] }),
    ).toBe(text);
  });

  it("data problem tags", () => {
    expect(studyProblemTag("baseline_stalled")).toBe("Staff can help");
    expect(studyProblemTag("high_set_aside")).toBe("Staff can help");
    expect(studyProblemTag("possible_other_speaker")).toBe("Study team");
    expect(studyProblemTag("device_silent")).toBe("Study team");
    expect(studyProblemTag("review_flagged_data_problem")).toBe("Study team");
  });

  it("daily chart texts (UX-358, UX-360)", () => {
    expect(studySilentNote([])).toBe("");
    expect(studyDayLabel("2026-10-01", [])).toBe("Oct 1");
    expect(studyDayLabel("2026-10-12", ["D02"])).toBe("Oct 12: D02 silent");
    expect(studyDayLabel("2026-10-12", ["D02", "D05"])).toBe("Oct 12: D02, D05 silent");
    const d = { used: 8, set_aside: 0, quarantined: 1, missed: 1 };
    expect(studyDayTooltip("2026-10-08", d)).toBe(
      "Oct 8: 8 used, 0 set aside, 1 held back, 1 missed",
    );
    expect(studyDailyChartName("Oct 1–30", d)).toBe(
      "Check-ins per day, Oct 1–30: 8 used, 0 set aside, 1 held back, 1 missed.",
    );
  });

  it("funnel notes (UX-363..UX-366)", () => {
    expect(studyExpectedNote(10, 30, true)).toBe("10 residents × 30 days");
    expect(studyExpectedNote(11, 30, false)).toBe("sum of days enrolled across 11 residents");
    expect(studyReceivedNote(19, 2)).toBe("19 missed; 2 duplicate copies removed");
    expect(studyReceivedNote(0, 1)).toBe("0 missed; 1 duplicate copy removed");
    const r = { quality_flag_poor: 5, noise_above_limit: 5, speech_too_short: 3 };
    expect(studyPassedNote(12, r, 1)).toBe(
      "12 set aside: quality flag 5, noise 5, too short 3 (1 had two reasons)",
    );
    expect(studyPassedNote(13, r, 0)).toBe("13 set aside: quality flag 5, noise 5, too short 3");
    expect(studyPassedNote(11, r, 1)).toBe(
      "11 set aside: quality flag 5, noise 5, too short 3 (1 had more than one reason)",
    );
    expect(studyHeldBackNote(2)).toBe("2 held back as possible other voice");
  });

  it("by-resident row name (UX-370)", () => {
    expect(
      studyByResidentRowName({
        code: "R08",
        used: 13,
        days: 30,
        percent: "43%",
        setAside: 5,
        heldBack: 0,
        missed: 12,
      }),
    ).toBe("R08: 13 of 30 days usable (43%); 5 set aside; 0 held back; 12 missed.");
  });

  it("timing texts (UX-372, UX-373)", () => {
    expect(studyTimingDelay(0)).toBe("0 days");
    expect(studyTimingDelay(1)).toBe("1 day");
    expect(studyTimingAlarms(1)).toBe("1 alarm");
    expect(studyTimingFalseAlarms(2)).toBe("2 false alarms");
  });

  it("device texts (§4.4, UX-056, UX-057)", () => {
    expect(studySilentText([])).toBe("");
    expect(studySilentText(["2026-10-12"])).toBe(" Silent all day Oct 12.");
    expect(studySilentText(["2026-10-13", "2026-10-12", "2026-10-14"])).toBe(
      " Silent all day Oct 12, Oct 13, Oct 14.",
    );
    expect(studySilentText(["2026-10-02", "2026-10-04", "2026-10-06", "2026-10-27"])).toBe(
      " Silent all day on 4 days (latest Oct 27).",
    );
    expect(studyDayCount([])).toBe("0");
    expect(studyDayCount(["2026-10-12"])).toBe("1 (Oct 12)");
    expect(studyDayCount(["2026-10-02", "2026-10-04", "2026-10-06", "2026-10-27"])).toBe(
      "4 (latest Oct 4, Oct 6, Oct 27)",
    );
    expect(studyFirmwareText(null)).toBe("");
    expect(studyFirmwareText("fw-1.1.0")).toBe(" Firmware fw-1.1.0.");
    expect(studyLastUpload(null)).toBe("no upload yet");
    expect(studyLastUpload(null, true)).toBe("No upload yet");
    expect(studyInUseRange("2026-10-01", "2026-10-12", "D07B")).toBe("Oct 1–12 · replaced by D07B");
    expect(studyInUseRange("2026-10-01", "2026-10-12", null)).toBe("Oct 1–12");
  });

  it("download texts (UX-377)", () => {
    expect(studyCsvName("scores", "2026-10-30")).toBe("echowell_scores_2026-10-30.csv");
    expect(studyDownloadFailed("Scores (CSV)")).toBe(
      "Could not download Scores (CSV). Check your connection and try again.",
    );
  });
});
