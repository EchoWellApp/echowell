// req: FE-181, FE-082, UX-401, UX-402, UX-403, UX-200, FEAT-065-FR-01, FEAT-065-FR-03, FEAT-065-AC-01
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import residents from "@/tests/fixtures/ds07/residents.json";
import type { ResidentsResponse } from "@/lib/types";
import { FilterButtons } from "./FilterButtons";

const data = residents as unknown as ResidentsResponse;

function buttons() {
  return within(screen.getByRole("group", { name: "Show" })).getAllByRole("button");
}

describe("FilterButtons", () => {
  it("shows the DS-07 counts in order, no Learning button, All pressed (FE-181)", () => {
    render(
      <FilterButtons summary={data.summary} total={data.total} value="all" onChange={vi.fn()} />,
    );
    expect(buttons().map((b) => b.textContent)).toEqual([
      "All (10)",
      "Changed (2)",
      "Needs attention (2)",
      "Usual (6)",
    ]);
    expect(screen.queryByRole("button", { name: /Learning/ })).toBeNull();
    expect(screen.getByRole("button", { name: "All (10)" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    for (const b of buttons().slice(1)) expect(b).toHaveAttribute("aria-pressed", "false");
    const s = data.summary;
    expect(s.changed + s.needs_attention + s.learning + s.usual).toBe(data.total);
  });

  it("shows Learning (n) before Usual when someone is Learning", () => {
    render(
      <FilterButtons
        summary={{ changed: 1, needs_attention: 0, learning: 1, usual: 2 }}
        total={4}
        value="learning"
        onChange={vi.fn()}
      />,
    );
    expect(buttons().map((b) => b.textContent)).toEqual([
      "All (4)",
      "Changed (1)",
      "Needs attention (0)",
      "Learning (1)",
      "Usual (2)",
    ]);
    expect(screen.getByRole("button", { name: "Learning (1)" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("shows — as counts while loading (UX-200)", () => {
    render(<FilterButtons summary={undefined} total={undefined} value="all" onChange={vi.fn()} />);
    expect(buttons().map((b) => b.textContent)).toEqual([
      "All (—)",
      "Changed (—)",
      "Needs attention (—)",
      "Usual (—)",
    ]);
  });

  it("reports the pressed filter, keeps focus and announces it (UX-403)", async () => {
    const onChange = vi.fn();
    const { rerender } = render(
      <FilterButtons summary={data.summary} total={data.total} value="all" onChange={onChange} />,
    );
    const live = screen.getByTestId("filter-live");
    expect(live).toHaveAttribute("aria-live", "polite");
    expect(live).toHaveTextContent("");
    const changed = screen.getByRole("button", { name: "Changed (2)" });
    await userEvent.click(changed);
    expect(onChange).toHaveBeenCalledWith("changed");
    rerender(
      <FilterButtons
        summary={data.summary}
        total={data.total}
        value="changed"
        onChange={onChange}
      />,
    );
    expect(changed).toHaveFocus();
    expect(changed).toHaveAttribute("aria-pressed", "true");
    expect(live).toHaveTextContent("Showing changed residents");
    // Counts stay the same after filtering (UX-402).
    expect(buttons().map((b) => b.textContent)).toEqual([
      "All (10)",
      "Changed (2)",
      "Needs attention (2)",
      "Usual (6)",
    ]);
    await userEvent.click(screen.getByRole("button", { name: "Needs attention (2)" }));
    expect(live).toHaveTextContent("Showing needs attention residents");
    await userEvent.click(screen.getByRole("button", { name: "All (10)" }));
    expect(live).toHaveTextContent("Showing all residents");
    expect(onChange).toHaveBeenLastCalledWith("all");
  });

  it("does not report a change when the pressed button is pressed again", async () => {
    const onChange = vi.fn();
    render(
      <FilterButtons summary={data.summary} total={data.total} value="usual" onChange={onChange} />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Usual (6)" }));
    expect(onChange).not.toHaveBeenCalled();
    expect(screen.getByTestId("filter-live")).toHaveTextContent("Showing usual residents");
  });
});
