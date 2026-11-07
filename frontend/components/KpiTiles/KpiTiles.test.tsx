// req: UX-200, UX-351..UX-355, UX-380
import { render, screen } from "@testing-library/react";
import type { AnalyticsKpis } from "@/lib/types";
import analytics from "@/tests/fixtures/ds07/analytics.json";
import { KpiTiles } from "./KpiTiles";

const tiles = () => screen.getAllByTestId("kpi-tile").map((t) => t.textContent);

describe("KpiTiles", () => {
  it("renders DS-07 values", () => {
    render(<KpiTiles kpis={analytics.kpis as AnalyticsKpis} />);
    expect(tiles()).toEqual([
      "Check-ins received94%281 of 300 expected",
      "Used for scoring89%267 of 300 expected",
      "Baselines formed9 of 10R08 still forming; R07 restarted once",
      "Alarms raised2R09, R10; neither reviewed yet",
    ]);
  });

  it("rounds half up and shows 'none in this period'", () => {
    const k = analytics.kpis as AnalyticsKpis;
    render(
      <KpiTiles
        kpis={{
          ...k,
          checkins_received: { count: 1, expected: 8, percent: 13 },
          used_for_scoring: { count: 0, expected: 0, percent: 0 },
          alarms_raised: { count: 0, resident_codes: [], not_reviewed_count: 0 },
        }}
      />,
    );
    expect(tiles()[0]).toBe("Check-ins received13%1 of 8 expected");
    expect(tiles()[1]).toBe("Used for scoring0%0 of 0 expected");
    expect(tiles()[3]).toBe("Alarms raised0none in this period");
  });

  it("shows dashes while loading", () => {
    render(<KpiTiles kpis={null} />);
    expect(tiles()).toEqual([
      "Check-ins received—",
      "Used for scoring—",
      "Baselines formed—",
      "Alarms raised—",
    ]);
  });
});
