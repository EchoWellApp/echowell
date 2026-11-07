// req: FE-013, FE-097, UX-080, UX-084, UX-085, UX-086, UX-089, UX-090, UX-091, UX-092, UX-100, UX-103, UX-106, UX-108, FEAT-067-AC-03
import {
  TRENDS_ALARM_TEXT,
  TRENDS_MEASURES,
  TRENDS_MEASURES_CAPTION,
  TRENDS_NO_SCORED,
  changeScoreSummary,
  trendsAlarmLine,
  trendsAlarmTick,
  trendsBarTooltip,
  trendsBaselineLabel,
  trendsDevicePeriod,
  trendsEpochOption,
  trendsForming,
  trendsMeasuresIntro,
  trendsOtherMeasures,
  trendsPageTitle,
  trendsScoreIntro,
  trendsSparklineName,
  trendsTableCaption,
} from "@/lib/wording";

describe("Voice trends wording", () => {
  it("builds the exact TRD 11 §4.5.3 texts", () => {
    expect(trendsScoreIntro("R09", 5)).toBe(
      "Goes up when check-ins keep leaning away from R09’s usual. The alarm turns on at 5. Missed, set-aside and held-back check-ins leave it unchanged.",
    );
    expect(trendsScoreIntro("R09", 4.5)).toContain("The alarm turns on at 4.5.");
    expect(trendsForming(13, 16)).toBe(
      "No change score yet. Scoring starts after the baseline is complete (13 of 16 usable check-ins so far).",
    );
    expect(trendsDevicePeriod("2026-10-13")).toBe(
      "Showing the current device period since Oct 13. Earlier periods are not scored against this baseline.",
    );
    expect(trendsBaselineLabel("Oct 1–16")).toBe("Baseline Oct 1–16");
    expect(trendsAlarmLine(5)).toBe("Alarm line: 5");
    expect(trendsAlarmTick("Oct 21")).toBe("Oct 21 · alarm");
    expect(trendsBarTooltip("2026-10-21", 5.4237)).toBe("Oct 21: 5.4");
    expect(TRENDS_ALARM_TEXT).toEqual({
      off: "—",
      rings: "▲ Alarm rings (first crossing)",
      on: "▲ Alarm on",
    });
    expect(trendsTableCaption("R09")).toBe("Change score for R09, by scored check-in");
    expect(trendsPageTitle("R09")).toBe("R09 · Voice trends");
    expect(trendsEpochOption(2, 2)).toBe("Period 2 (current)");
    expect(trendsEpochOption(1, 2)).toBe("Period 1");
    expect(TRENDS_NO_SCORED).toBe("No check-ins were scored in this device period.");
  });

  it("changeScoreSummary matches UX-091", () => {
    const pts = [
      { local_date: "2026-10-17", cusum_tally: 3.2, alarm_state: "off" as const },
      { local_date: "2026-10-21", cusum_tally: 5.4, alarm_state: "rings" as const },
      { local_date: "2026-10-30", cusum_tally: 26.84, alarm_state: "on" as const },
    ];
    expect(
      changeScoreSummary({ residentCode: "R09", points: pts, baselineRange: "Oct 1–16", h: 5 }),
    ).toBe(
      "Change score for R09 from Oct 17 to Oct 30. Baseline Oct 1–16. Alarm line 5. Crossed the alarm line on Oct 21; now 26.8.",
    );
    expect(
      changeScoreSummary({ residentCode: "R07", points: [pts[0]!], baselineRange: null, h: 5 }),
    ).toBe(
      "Change score for R07 from Oct 17 to Oct 17. Alarm line 5. Below the alarm line throughout; now 3.2.",
    );
    expect(
      changeScoreSummary({ residentCode: "R07", points: [], baselineRange: "Oct 13–28", h: 5 }),
    ).toBe("Change score for R07: no scored check-ins yet. Baseline Oct 13–28. Alarm line 5.");
  });

  it("builds the exact TRD 11 §4.5.4 texts", () => {
    expect(TRENDS_MEASURES.map((m) => `${m.label} (${m.technicalName})`)).toEqual([
      "Quieter (loudness)",
      "Slower to say the phrase (phrase duration)",
      "Fewer syllables per second (speech rate)",
      "Slower while talking (articulation rate)",
      "More pauses (number of pauses)",
      "More time in pauses (pause fraction)",
      "Less voiced sound (voiced fraction)",
    ]);
    expect(trendsMeasuresIntro("R09")).toBe(
      "Each is compared with R09’s own baseline. The score rises when the voice is:",
    );
    expect(trendsSparklineName("Quieter", "loudness", 2.17, 14)).toBe(
      "Quieter (loudness): latest +2.2 compared with own baseline over 14 scored check-ins",
    );
    expect(trendsSparklineName("Quieter", "loudness", -0.3, 1)).toBe(
      "Quieter (loudness): latest −0.3 compared with own baseline over 1 scored check-in",
    );
    expect(trendsOtherMeasures(12)).toBe("12 other measurements (pitch, jitter, MFCCs and others)");
    expect(TRENDS_MEASURES_CAPTION).toBe(
      "Measurement names are placeholders until Team 1 confirms the openSMILE output names. Morning check-ins are adjusted before comparing.",
    );
  });
});
