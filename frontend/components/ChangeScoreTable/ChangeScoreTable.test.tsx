// req: FE-184, UX-090, UX-225, TST-112, FEAT-067-AC-02
import { render, screen, within } from "@testing-library/react";
import type { ScoresResponse } from "@/lib/types";
import r09 from "@/tests/fixtures/ds07/resident/R09-scores.json";
import { ChangeScoreTable } from "./ChangeScoreTable";

const f = r09 as unknown as ScoresResponse;

describe("ChangeScoreTable", () => {
  it("lists the 14 R09 change scores with one decimal (FE-184)", () => {
    render(<ChangeScoreTable points={f.items} h={5} />);
    const table = screen.getByRole("table", { name: "Change score for R09, by scored check-in" });
    const headers = within(table)
      .getAllByRole("columnheader")
      .map((h) => h.textContent);
    expect(headers).toEqual(["Date", "Change score", "Alarm"]);
    const rows = within(table).getAllByRole("row").slice(1);
    expect(rows).toHaveLength(14);
    const cells = rows.map((r) =>
      within(r)
        .getAllByRole("cell")
        .map((c) => c.textContent),
    );
    expect(cells.map((c) => c[1])).toEqual([
      "3.2",
      "2.6",
      "1.8",
      "1.6",
      "5.4",
      "8.0",
      "8.3",
      "10.7",
      "12.4",
      "15.3",
      "16.7",
      "18.8",
      "23.1",
      "26.8",
    ]);
    expect(cells[0]).toEqual(["Oct 17", "3.2", "—"]);
    expect(cells[4]).toEqual(["Oct 21", "5.4", "▲ Alarm rings (first crossing)"]);
    expect(cells[13]).toEqual(["Oct 30", "26.8", "▲ Alarm on"]);
  });

  it("renders an empty body for no points", () => {
    render(<ChangeScoreTable points={[]} h={5} />);
    expect(screen.getAllByRole("row")).toHaveLength(1);
  });
});
