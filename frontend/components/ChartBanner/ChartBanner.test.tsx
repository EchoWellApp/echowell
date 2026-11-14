// req: UX-061, UX-062, UX-063, UX-200, FEAT-066-AC-01, FEAT-066-AC-05
import { render, screen, within } from "@testing-library/react";
import type { ResidentDetail } from "@/lib/types";
import R03 from "@/tests/fixtures/ds07/resident/R03.json";
import R07 from "@/tests/fixtures/ds07/resident/R07.json";
import R08 from "@/tests/fixtures/ds07/resident/R08.json";
import R09 from "@/tests/fixtures/ds07/resident/R09.json";
import { ChartBanner } from "./ChartBanner";

const as = (x: unknown) => x as ResidentDetail;

function facts() {
  const dl = screen.getByRole("region", { name: "Resident" }).querySelector("dl")!;
  return Array.from(dl.querySelectorAll("div")).map(
    (d) => `${d.querySelector("dt")?.textContent}: ${d.querySelector("dd")?.textContent}`,
  );
}

describe("ChartBanner", () => {
  it("shows R09's code, facts and large pill", () => {
    render(<ChartBanner resident={as(R09)} />);
    const banner = screen.getByRole("region", { name: "Resident" });
    expect(within(banner).getByRole("heading", { level: 1 })).toHaveTextContent("R09");
    expect(facts()).toEqual([
      "Device: D09",
      "Last check-in: Oct 30, 2:28 PM CT",
      "Usable check-ins, last 30 days: 30 of 30",
      "Baseline: Complete",
    ]);
    expect(banner).toHaveTextContent("▲Changed");
  });

  it("names replaced and shared devices and a forming baseline", () => {
    const { rerender } = render(<ChartBanner resident={as(R07)} />);
    expect(facts()[0]).toBe("Device: D07B (replaced D07)");
    rerender(<ChartBanner resident={as(R03)} />);
    expect(facts()[0]).toBe("Device: D02 (shared with R02)");
    expect(facts()[2]).toBe("Usable check-ins, last 30 days: 22 of 30");
    rerender(<ChartBanner resident={as(R08)} />);
    expect(facts().slice(2)).toEqual([
      "Usable check-ins, last 30 days: 13 of 30",
      "Baseline: 13 of 16",
    ]);
    expect(screen.getByRole("region")).toHaveTextContent("!Needs attention");
  });

  it("shows dashes while loading and 'No check-ins yet' without a check-in", () => {
    const { rerender } = render(<ChartBanner resident={null} residentCode="R05" />);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("R05");
    expect(facts()).toEqual([
      "Device: —",
      "Last check-in: —",
      "Usable check-ins, last 30 days: —",
      "Baseline: —",
    ]);
    rerender(<ChartBanner resident={as({ ...R09, last_checkin_at: null })} />);
    expect(facts()[1]).toBe("Last check-in: No check-ins yet");
  });
});
