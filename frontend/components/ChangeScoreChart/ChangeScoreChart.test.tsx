// req: FE-093, FE-094, FE-095, FE-096, FE-097, FE-099, FE-183, UX-081..UX-087, UX-090..UX-092, UX-225, UX-243, FEAT-067-AC-01, FEAT-067-AC-03, TST-093, TST-112
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ScoresResponse } from "@/lib/types";
import r07 from "@/tests/fixtures/ds07/resident/R07-scores.json";
import r09 from "@/tests/fixtures/ds07/resident/R09-scores.json";
import r10 from "@/tests/fixtures/ds07/resident/R10-scores.json";
import {
  BASELINE_KEY,
  ChangeScoreChart,
  MIN_WIDTH,
  PLOT_HEIGHT,
  labelledIndices,
  yScale,
} from "./ChangeScoreChart";

const TZ = "America/Chicago";

function renderChart(f: ScoresResponse, code: string, restartedOn: string | null = null) {
  return render(
    <ChangeScoreChart
      points={f.items}
      baselinePeriod={f.baseline_periods[0] ?? null}
      h={f.meta.cusum_h}
      residentCode={code}
      tz={TZ}
      restartedOn={restartedOn}
    />,
  );
}

const bars = (c: HTMLElement) => [...c.querySelectorAll<SVGGElement>("[data-testid='score-bar']")];
const fillOf = (g: Element) => g.querySelector("rect")?.getAttribute("fill");

describe("ChangeScoreChart", () => {
  it("renders R09 as in TRD 11 §4.13.3 (FE-183)", () => {
    const { container } = renderChart(r09 as unknown as ScoresResponse, "R09");
    const b = bars(container);
    expect(b).toHaveLength(14);
    expect(b.map((g) => g.dataset.date)).toEqual(
      Array.from({ length: 14 }, (_, i) => `2026-10-${String(17 + i).padStart(2, "0")}`),
    );
    expect(b.slice(0, 4).map(fillOf)).toEqual(Array(4).fill("var(--c-aside)"));
    expect(b.slice(4).map(fillOf)).toEqual(Array(10).fill("var(--red)"));
    // off bars carry a 1px --muted outline (NFR-063); red ones none
    expect(b[0]?.querySelector("rect")).toHaveAttribute("stroke", "var(--muted)");
    expect(b[0]?.querySelector("rect")).toHaveAttribute("stroke-width", "1");
    expect(b[4]?.querySelector("rect")).not.toHaveAttribute("stroke");
    // baseline slot
    const slot = container.querySelector(".baseline-slot path");
    expect(slot).toHaveAttribute("fill", "var(--grey-bg)");
    expect(slot).toHaveAttribute("height", String(PLOT_HEIGHT));
    expect(screen.getByText("Baseline Oct 1–16")).toBeInTheDocument();
    // reference line at y = 5
    const line = container.querySelector(".recharts-reference-line-line");
    expect(line).toHaveAttribute("y", "5");
    expect(line).toHaveAttribute("stroke", "var(--red)");
    expect(line).toHaveAttribute("stroke-width", "2");
    expect(line).toHaveAttribute("stroke-dasharray", "6 4");
    expect(screen.getByTestId("alarm-line-label")).toHaveTextContent(/^Alarm line: 5$/);
    expect(screen.getByTestId("alarm-line-label")).toHaveAttribute("fill", "var(--red)");
    // marker and tick of the first crossing
    const markers = screen.getAllByTestId("alarm-marker");
    expect(markers).toHaveLength(1);
    expect(markers[0]).toHaveTextContent("▲");
    expect(markers[0]?.closest("[data-testid='score-bar']")).toHaveAttribute(
      "data-date",
      "2026-10-21",
    );
    expect(screen.getByTestId("alarm-tick")).toHaveTextContent(/^Oct 21 · alarm$/);
    const xTicks = [...container.querySelectorAll(".recharts-xAxis text")].map(
      (t) => t.textContent,
    );
    expect(xTicks).toContain("Oct 17");
    expect(xTicks).toContain("Oct 30");
    // tooltips
    expect(b[0]?.querySelector("title")).toHaveTextContent(/^Oct 17: 3.2$/);
    expect(b[13]?.querySelector("title")).toHaveTextContent(/^Oct 30: 26.8$/);
  });

  it("has the UX-091 accessible name and a focusable named scroll container", () => {
    renderChart(r09 as unknown as ScoresResponse, "R09");
    expect(
      screen.getByRole("img", {
        name: "Change score for R09 from Oct 17 to Oct 30. Baseline Oct 1–16. Alarm line 5. Crossed the alarm line on Oct 21; now 26.8.",
      }),
    ).toBeInTheDocument();
    const region = screen.getByRole("region", { name: "Change score chart" });
    expect(region).toHaveAttribute("tabindex", "0");
    const svg = region.querySelector("svg");
    expect(Number(svg?.getAttribute("width"))).toBeGreaterThanOrEqual(MIN_WIDTH);
  });

  it("labels the y axis 0, 10, 20 for R09 (UX-087)", () => {
    const { container } = renderChart(r09 as unknown as ScoresResponse, "R09");
    const ticks = [...container.querySelectorAll(".recharts-yAxis tspan")].map(
      (t) => t.textContent,
    );
    expect(ticks).toEqual(["0", "10", "20"]);
  });

  it("puts the table alternative in a closed <details> (UX-090, TST-112)", async () => {
    const { container } = renderChart(r09 as unknown as ScoresResponse, "R09");
    const details = container.querySelector("details");
    expect(details).not.toHaveAttribute("open");
    expect(within(details as HTMLElement).getByText("Show change score as a table")).toBeVisible();
    await userEvent.click(screen.getByText("Show change score as a table"));
    expect(details).toHaveAttribute("open");
    const table = screen.getByRole("table", { name: /R09/ });
    expect(within(table).getAllByRole("row")).toHaveLength(15);
  });

  it("colours R10 by alarm_state: 7 off, Oct 24 rings, 6 on", () => {
    const { container } = renderChart(r10 as unknown as ScoresResponse, "R10");
    const b = bars(container);
    expect(b).toHaveLength(14);
    expect(b.slice(0, 7).map(fillOf)).toEqual(Array(7).fill("var(--c-aside)"));
    expect(b.slice(7).map(fillOf)).toEqual(Array(7).fill("var(--red)"));
    expect(b[7]).toHaveAttribute("data-alarm-state", "rings");
    expect(screen.getByTestId("alarm-tick")).toHaveTextContent("Oct 24 · alarm");
    expect(
      screen.getByRole("img", { name: /Crossed the alarm line on Oct 24; now 13.4\.$/ }),
    ).toBeInTheDocument();
  });

  it("keeps a bar red after the first crossing even below the line (D-03)", () => {
    const f = structuredClone(r10) as unknown as ScoresResponse;
    const last = f.items[f.items.length - 1];
    if (last) last.cusum_tally = 2;
    const { container } = renderChart(f, "R10");
    expect(fillOf(bars(container)[13] as Element)).toBe("var(--red)");
  });

  it("draws R07 zero values as 2px --rule stubs with the device-period line (FE-095, UX-092)", () => {
    const { container } = renderChart(r07 as unknown as ScoresResponse, "R07", "2026-10-13");
    const b = bars(container);
    expect(b).toHaveLength(2);
    for (const g of b) {
      const rect = g.querySelector("rect");
      expect(rect).toHaveAttribute("height", "2");
      expect(rect).toHaveAttribute("fill", "var(--rule)");
    }
    expect(screen.getByText("Baseline Oct 13–28")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Showing the current device period since Oct 13. Earlier periods are not scored against this baseline.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("img", {
        name: "Change score for R07 from Oct 29 to Oct 30. Baseline Oct 13–28. Alarm line 5. Below the alarm line throughout; now 0.0.",
      }),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("alarm-marker")).toBeNull();
  });

  it("marks a zero-value first crossing above its stub", () => {
    const f = structuredClone(r07) as unknown as ScoresResponse;
    const first = f.items[0];
    if (first) first.alarm_state = "rings";
    renderChart(f, "R07");
    expect(screen.getByTestId("alarm-marker")).toBeInTheDocument();
  });

  it("shows only the baseline slot when nothing is scored yet", () => {
    const f = structuredClone(r07) as unknown as ScoresResponse;
    f.items = [];
    const { container } = renderChart(f, "R07");
    expect(bars(container)).toHaveLength(0);
    expect(screen.getByText("Baseline Oct 13–28")).toBeInTheDocument();
    expect(
      screen.getByRole("img", {
        name: "Change score for R07: no scored check-ins yet. Baseline Oct 13–28. Alarm line 5.",
      }),
    ).toBeInTheDocument();
  });

  it("renders without a baseline slot when there is no baseline period", () => {
    const f = structuredClone(r09) as unknown as ScoresResponse;
    f.baseline_periods = [];
    const { container } = renderChart(f, "R09");
    expect(container.querySelector(".baseline-slot")).toBeNull();
    expect(bars(container)).toHaveLength(14);
    expect(BASELINE_KEY).toBe("__baseline__");
  });
});

describe("yScale", () => {
  it("uses max(1.2h, 1.05 × max) with 10-unit ticks above 20, else 5", () => {
    expect(yScale(5, [3, 26.8])).toEqual({ max: 1.05 * 26.8, ticks: [0, 10, 20] });
    expect(yScale(5, [0, 0])).toEqual({ max: 6, ticks: [0, 5] });
    expect(yScale(5, [13.4]).ticks).toEqual([0, 5, 10]);
    expect(yScale(5, []).max).toBe(6);
  });
});

describe("labelledIndices", () => {
  const pts = (n: number, alarm = -1) =>
    Array.from({ length: n }, (_, i) => ({ alarm_state: i === alarm ? "rings" : "off" }) as const);
  it("always labels the first, alarm and last dates", () => {
    expect([...labelledIndices(pts(14, 4), 10)].sort((a, b) => a - b)).toEqual([0, 4, 13]);
    expect([...labelledIndices(pts(1, 0), 40)]).toEqual([0]);
  });
  it("adds other dates only at least 48px apart", () => {
    const s = [...labelledIndices(pts(6), 48)].sort((a, b) => a - b);
    expect(s).toEqual([0, 1, 2, 3, 4, 5]);
    expect([...labelledIndices(pts(6), 30)].sort((a, b) => a - b)).toEqual([0, 2, 5]);
    expect(labelledIndices([], 40).size).toBe(0);
  });
});
