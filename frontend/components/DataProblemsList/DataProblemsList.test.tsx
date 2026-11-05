// req: UX-306..UX-309, UX-331
import { render, screen } from "@testing-library/react";
import type { DataAlert, Meta } from "@/lib/types";
import dataAlerts from "@/tests/fixtures/ds07/data-alerts-open.json";
import { DataProblemsList, orderDataProblems } from "./DataProblemsList";

const meta = dataAlerts.meta as Meta;
const items = dataAlerts.items as DataAlert[];
const alert = (patch: Partial<DataAlert>): DataAlert => ({ ...items[0]!, ...patch });

describe("DataProblemsList", () => {
  it("orders by kind then natural code (UX-307)", () => {
    const ordered = orderDataProblems([
      alert({ id: "a", kind: "review_flagged_data_problem", resident_code: "R09" }),
      alert({ id: "b", kind: "device_silent", resident_code: null, device_code: "D10" }),
      alert({ id: "c", kind: "device_silent", resident_code: null, device_code: "D2" }),
      alert({ id: "d", kind: "baseline_stalled", resident_code: "R10" }),
      alert({ id: "e", kind: "baseline_stalled", resident_code: "R9" }),
      alert({ id: "f", kind: "unknown" as DataAlert["kind"], resident_code: "R01" }),
    ]);
    expect(ordered.map((a) => a.id)).toEqual(["e", "d", "c", "b", "a", "f"]);
  });

  it("uses yellow tags for staff items and muted for study-team items, links by title", () => {
    render(<DataProblemsList alerts={items} meta={meta} />);
    const staff = screen.getAllByText("Staff can help");
    const team = screen.getAllByText("Study team");
    expect(staff).toHaveLength(2);
    expect(team).toHaveLength(2);
    expect(staff[0]!.className).toMatch(/tagStaff/);
    expect(team[0]!.className).toMatch(/tagTeam/);
    expect(screen.getByRole("link", { name: "R05 · possible other speaker" })).toHaveAttribute(
      "href",
      "/residents/R05/log",
    );
  });

  it("renders a row without any code as plain text", () => {
    render(
      <DataProblemsList
        alerts={[alert({ resident_code: null, device_code: null, detail: "something." })]}
        meta={meta}
      />,
    );
    expect(screen.getByTestId("data-problem").textContent).toBe("Staff can help: something.");
    expect(screen.queryByRole("link")).toBeNull();
  });

  it("shows the empty text (UX-309)", () => {
    render(<DataProblemsList alerts={[]} meta={meta} />);
    expect(screen.getByText("No data problems in the last 30 days.")).toBeVisible();
  });
});
