// req: FE-013, FE-032, FE-077, FE-101, UX-063, UX-065, UX-072, UX-073, UX-142, UX-229, UX-312, UX-421, UX-423
import R07json from "@/tests/fixtures/ds07/resident/R07.json";
import R09json from "@/tests/fixtures/ds07/resident/R09.json";
import type { CheckinEvent, Meta, ResidentDetail } from "@/lib/types";
import {
  bannerDeviceText,
  baselineExplanation,
  baselineForming,
  baselineRestartPrefix,
  baselineText,
  chartSectionHref,
  chartTitle,
  joinCodes,
  leadChangedBelow,
  leadLearning,
  leadUsualNotScored,
  leaningMostText,
  logLine,
  restartFacts,
  summaryNote,
  summaryRestartSentence,
  tileDevice,
} from "@/lib/wording";

const R07 = R07json as unknown as ResidentDetail;
const R09 = R09json as unknown as ResidentDetail;
const meta: Meta = R09.meta;

const ev = (over: Partial<CheckinEvent>): CheckinEvent => ({
  local_date: "2026-10-13",
  event_type: "missed",
  epoch_number: null,
  session_id: null,
  detail: null,
  cusum_tally: null,
  restart_cause: null,
  previous_device_code: null,
  from_value: null,
  to_value: null,
  device_code: null,
  ...over,
});
const ctx = { h: 4.5, baselineN: 30, currentDeviceCode: "D02" };

describe("chart wording", () => {
  it("builds section links and titles (FE-032, UX-229)", () => {
    expect(chartSectionHref("R09", "summary")).toBe("/residents/R09");
    expect(chartSectionHref("R09", "log")).toBe("/residents/R09/log");
    expect(chartTitle("R09", "review")).toBe("R09 · Review and notes – EchoWell");
  });

  it("names devices in the banner (UX-063)", () => {
    expect(joinCodes(["R01", "R02", "R03"])).toBe("R01, R02 and R03");
    expect(joinCodes(["R03"])).toBe("R03");
    expect(
      bannerDeviceText({
        device_code: "D02",
        shared: true,
        shared_with: ["R03", "R04"],
        previous_device_code: null,
      }),
    ).toBe("D02 (shared with R03 and R04)");
    expect(
      bannerDeviceText({
        device_code: null,
        shared: false,
        shared_with: [],
        previous_device_code: null,
      }),
    ).toBe("—");
    expect(tileDevice("D08", false)).toBe("D08 no upload today");
  });

  it("states every restart cause in the Summary and the Baseline (UX-065)", () => {
    const fw = { cause: "firmware" as const, on: "2026-10-13", from: "fw-1.0.0", to: "fw-1.1.0" };
    const sw = { cause: "software" as const, on: "2026-10-13", from: "3.0.2", to: "3.1.0" };
    expect(summaryRestartSentence("R07", fw, meta)).toBe(
      " The baseline restarted on Oct 13 because the device firmware changed; R07 is now compared only with the new baseline.",
    );
    expect(summaryRestartSentence("R07", sw, meta)).toContain(
      "because the extraction software changed;",
    );
    expect(baselineRestartPrefix(fw, meta)).toBe(
      "Restarted Oct 13 when the device firmware changed (fw-1.0.0 to fw-1.1.0), so earlier readings are not mixed in. ",
    );
    expect(baselineRestartPrefix(sw, meta)).toBe(
      "Restarted Oct 13 when the extraction software changed (3.0.2 to 3.1.0), so earlier readings are not mixed in. ",
    );
    expect(restartFacts(R09)).toBeNull();
    expect(restartFacts(R07)).toEqual({
      cause: "device",
      on: "2026-10-13",
      from: "D07",
      to: "D07B",
    });
  });

  it("fills the Summary templates (§4.5.2.1, UX-072, UX-073)", () => {
    expect(leadChangedBelow("R09", "Oct 21")).toBe(
      "R09’s voice moved away from their own usual pattern, steadily and long enough to set off the alarm on Oct 21. The change score is now below the alarm line, but the alarm stays on: in this version alarms are not switched off automatically.",
    );
    expect(leadLearning("R11", 4, 30)).toBe(
      "EchoWell is still learning R11’s usual pattern: 4 of 30 usable check-ins so far. Nothing is scored and no alarm can ring until the baseline is complete.",
    );
    expect(leadUsualNotScored("R01")).toBe(
      "R01’s baseline is complete. Comparing starts with the next usable check-in.",
    );
    expect(summaryNote("R09", false)).toBe(
      "This compares R09 only with R09. It is a prompt to check in, not a diagnosis. [Final clinical wording: confirm with PI]",
    );
    expect(summaryNote("R11", true, true)).toBe(
      "Once the baseline is complete, R11 will be compared only with R11. A change is a prompt to check in, not a diagnosis.",
    );
  });

  it("lists at most three leaning labels (UX-312)", () => {
    expect(leaningMostText([])).toBe("Leaning most: no single measurement stands out.");
    expect(
      leaningMostText([
        "total_phrase_duration_s",
        "pause_fraction",
        "articulation_rate_syl_per_s",
        "voiced_fraction",
      ]),
    ).toBe("Leaning most: slower to say the phrase, more time in pauses, slower while talking");
  });

  it("fills the Baseline templates (§4.5.7.1, UX-423)", () => {
    expect(baselineForming(3, 16, 0, 0)).toBe("Still forming: 3 of 16 usable check-ins so far.");
    expect(baselineText(R09, null, null, meta)).toBe(
      "First 16 usable check-ins, Oct 1–16, then frozen. Comparing starts with the next usable check-in.",
    );
    expect(baselineExplanation(30)).toBe(
      "The baseline is built from the first 30 usable check-ins, then frozen so slow changes still show up. It restarts if the resident gets a new device or the device or extraction software changes.",
    );
  });

  it("writes every log line (UX-142, FE-101)", () => {
    expect(logLine(ev({ event_type: "alarm_on" }), ctx)).toBe(
      "Alarm on. Change score crossed 4.5.",
    );
    expect(logLine(ev({ event_type: "baseline_complete" }), ctx)).toBe(
      "Baseline complete (30 of 30).",
    );
    expect(
      logLine(
        ev({
          event_type: "baseline_restarted",
          restart_cause: "firmware",
          from_value: "fw-1.0.0",
          to_value: "fw-1.1.0",
        }),
        ctx,
      ),
    ).toBe("Device firmware changed (fw-1.0.0 to fw-1.1.0). Baseline restarted.");
    expect(
      logLine(
        ev({
          event_type: "baseline_restarted",
          restart_cause: "software",
          from_value: "3.0.2",
          to_value: "3.1.0",
        }),
        ctx,
      ),
    ).toBe("Extraction software changed (3.0.2 to 3.1.0). Baseline restarted.");
    expect(
      logLine(
        ev({ event_type: "baseline_restarted", restart_cause: "device", to_value: "D07B" }),
        ctx,
      ),
    ).toBe("New device D07B. Baseline restarted.");
    expect(logLine(ev({ event_type: "device_silent", device_code: "D05" }), ctx)).toBe(
      "Shared device D05 silent all day. Check-in missed.",
    );
    expect(logLine(ev({ event_type: "device_silent" }), ctx)).toBe(
      "Shared device D02 silent all day. Check-in missed.",
    );
    expect(
      logLine(
        ev({ event_type: "quarantined", detail: "possible other speaker (F0 z=-7.34)" }),
        ctx,
      ),
    ).toBe("Check-in held back: possible other voice.");
    expect(logLine(ev({ event_type: "checkins_started", device_code: "D02" }), ctx)).toBe(
      "Check-ins started.",
    );
    expect(logLine(ev({ event_type: "checkins_started", device_code: "D01" }), ctx)).toBe(
      "Check-ins started on D01.",
    );
  });
});
