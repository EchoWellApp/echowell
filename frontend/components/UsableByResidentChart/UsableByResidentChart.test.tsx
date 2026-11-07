// req: UX-367..UX-370, UX-383
import { render, screen } from "@testing-library/react";
import type { ByResidentRow } from "@/lib/types";
import { UsableByResidentChart, orderByUsable } from "./UsableByResidentChart";

const row = (code: string, used: number, days = 30): ByResidentRow => ({
  resident_code: code,
  days,
  used_days: used,
  set_aside_days: 0,
  quarantined_days: 1,
  missed_days: days - used - 1,
  used_percent: 0,
});

describe("UsableByResidentChart", () => {
  it("orders by rounded percentage, ties by natural code", () => {
    const ordered = orderByUsable([row("R10", 15), row("R2", 15), row("R1", 29), row("R3", 0, 0)]);
    expect(ordered.map((r) => r.resident_code)).toEqual(["R3", "R2", "R10", "R1"]);
  });

  it("computes the percentage from counts, half up, with the row name", () => {
    render(<UsableByResidentChart rows={[row("R04", 13, 26), row("R05", 1, 8)]} />);
    expect(screen.getByText("Share of 26 days, lowest first")).toBeVisible();
    expect(screen.getAllByTestId("by-resident-row").map((r) => r.textContent)).toEqual([
      "R0513%",
      "R0450%",
    ]);
    expect(
      screen.getByRole("group", {
        name: "R05: 1 of 8 days usable (13%); 0 set aside; 1 held back; 6 missed.",
      }),
    ).toBeVisible();
    const meter = screen.getAllByTestId("by-resident-row")[0]!.querySelector("i") as HTMLElement;
    expect(meter.style.width).toBe("12.5%");
  });
});
