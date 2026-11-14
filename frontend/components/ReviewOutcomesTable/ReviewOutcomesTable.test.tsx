// req: UX-375, FE-195
import { render, screen } from "@testing-library/react";
import { ReviewOutcomesTable } from "./ReviewOutcomesTable";

describe("ReviewOutcomesTable", () => {
  it("shows the six production rows with counts", () => {
    render(
      <ReviewOutcomesTable
        outcomes={{
          alarms_raised: 5,
          reviewed: 4,
          by_outcome: { no_concern: 1, known_cause: 2, referred: 0, data_problem: 1 },
        }}
      />,
    );
    expect(
      screen.getByRole("heading", { level: 2, name: "Alarms and review outcomes" }),
    ).toBeVisible();
    expect(screen.getByRole("columnheader", { name: "Count" })).toBeVisible();
    const rows = screen
      .getAllByRole("row")
      .slice(1)
      .map((r) => r.textContent);
    expect(rows).toEqual([
      "Alarms raised5",
      "Reviewed4",
      "Checked on resident, no concern1",
      "Explained by a known cause2",
      "Referred to nurse or provider0",
      "Looks like a data problem: send to study team1",
    ]);
  });
});
