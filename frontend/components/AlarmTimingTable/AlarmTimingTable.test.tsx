// req: UX-371..UX-374, UX-384
import { render, screen, within } from "@testing-library/react";
import type { AlarmTimingRow } from "@/lib/types";
import analytics from "@/tests/fixtures/ds07/analytics.json";
import { AlarmTimingTable, buildAlarmTimingRows } from "./AlarmTimingTable";

const none = (code: string, patch: Partial<AlarmTimingRow> = {}): AlarmTimingRow => ({
  resident_code: code,
  planted_change: "None",
  change_began: null,
  alarm_rang: null,
  delay_days: null,
  result: "correct_no_alarm",
  ...patch,
});

describe("buildAlarmTimingRows", () => {
  it("DS-07: planted rows then Other 8", () => {
    expect(buildAlarmTimingRows(analytics.alarm_timing as AlarmTimingRow[])).toEqual([
      {
        label: "R09",
        planted_change: "Sudden step",
        change_began: "Oct 21",
        alarm_rang: "Oct 21",
        delay: "0 days",
      },
      {
        label: "R10",
        planted_change: "Slow drift",
        change_began: "Oct 17",
        alarm_rang: "Oct 24",
        delay: "7 days",
      },
      {
        label: "Other 8",
        planted_change: "None",
        change_began: null,
        alarm_rang: null,
        delay: "Correct",
      },
    ]);
  });

  it("missed, false alarm, 1 day and alarming others", () => {
    const rows = buildAlarmTimingRows([
      none("R03", { planted_change: "Slow drift", change_began: "2026-10-10", result: "missed" }),
      none("R02", {
        planted_change: "Sudden step",
        change_began: "2026-10-20",
        alarm_rang: "2026-10-12",
        result: "false_alarm",
      }),
      none("R10", {
        planted_change: "Sudden step",
        change_began: "2026-10-20",
        alarm_rang: "2026-10-21",
        delay_days: 1,
        result: "detected",
      }),
      none("R01", { alarm_rang: "2026-10-05", result: "false_alarm" }),
      none("R04"),
    ]);
    expect(rows.map((r) => [r.label, r.alarm_rang, r.delay])).toEqual([
      ["R02", "Oct 12", "False alarm"],
      ["R03", null, "Missed"],
      ["R10", "Oct 21", "1 day"],
      ["Other 2", "1 alarm", "1 false alarm"],
    ]);
    expect(buildAlarmTimingRows([])).toEqual([]);
  });
});

describe("AlarmTimingTable", () => {
  it("renders null cells as None / No alarm in a focusable scroll container", () => {
    render(
      <AlarmTimingTable
        rows={[
          {
            label: "R03",
            planted_change: "Slow drift",
            change_began: null,
            alarm_rang: null,
            delay: "Missed",
          },
        ]}
      />,
    );
    const scroller = screen.getByRole("region", { name: "Alarm timing table" });
    expect(scroller).toHaveAttribute("tabindex", "0");
    const cells = within(scroller)
      .getAllByRole("cell")
      .map((c) => c.textContent);
    expect(cells).toEqual(["Slow drift", "None", "No alarm", "Missed"]);
  });
});
