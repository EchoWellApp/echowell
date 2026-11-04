// req: UX-356..UX-361, FE-099
import { render, screen } from "@testing-library/react";
import type { DailySeriesPoint, Meta } from "@/lib/types";
import analytics from "@/tests/fixtures/ds07/analytics.json";
import { DailyCheckinsChart, dailyAxisLabels, dailyTotals } from "./DailyCheckinsChart";

const meta = analytics.meta as Meta;
const day = (d: string, silent: string[] = []): DailySeriesPoint => ({
  local_date: d,
  used: 2,
  set_aside: 0,
  quarantined: 0,
  missed: 1,
  silent_device_codes: silent,
});

describe("DailyCheckinsChart", () => {
  it("labels first, silent and last days", () => {
    const series = [day("2026-10-01"), day("2026-10-02", ["D02", "D05"]), day("2026-10-03")];
    expect([...dailyAxisLabels(series).values()]).toEqual([
      "Oct 1",
      "Oct 2: D02, D05 silent",
      "Oct 3",
    ]);
    expect(dailyTotals(series)).toEqual({ used: 6, set_aside: 0, quarantined: 0, missed: 3 });
  });

  it("renders the DS-07 totals and never the ▲ glyph (UX-361)", () => {
    const { container } = render(
      <DailyCheckinsChart series={analytics.daily_series as DailySeriesPoint[]} meta={meta} />,
    );
    const totals = dailyTotals(analytics.daily_series as DailySeriesPoint[]);
    expect(totals).toEqual({ used: 267, set_aside: 12, quarantined: 2, missed: 19 });
    for (const d of analytics.daily_series) {
      expect(d.used + d.set_aside + d.quarantined + d.missed).toBe(10);
    }
    expect(container.textContent).not.toContain("▲");
    expect(container.querySelectorAll("rect[stroke-dasharray]").length).toBeGreaterThan(0);
  });

  it("renders an empty series without crashing", () => {
    render(<DailyCheckinsChart series={[]} meta={meta} />);
    expect(
      screen.getByRole("region", {
        name: "Check-ins per day, : 0 used, 0 set aside, 0 held back, 0 missed.",
      }),
    ).toBeInTheDocument();
  });
});
