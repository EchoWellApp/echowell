// req: UX-410, UX-411, FE-206, FE-210, FEAT-066-AC-06
import { render, screen, within } from "@testing-library/react";
import { ChartSectionNav } from "./ChartSectionNav";

describe("ChartSectionNav", () => {
  it("lists the six sections in order with the current one marked", () => {
    render(<ChartSectionNav residentCode="R09" current="log" unreviewedAlarm={false} />);
    const nav = screen.getByRole("navigation", { name: "Resident chart" });
    const links = within(nav).getAllByRole("link");
    expect(links.map((l) => l.textContent)).toEqual([
      "Summary",
      "Review and notes",
      "Voice trends",
      "Baseline",
      "Check-in log",
      "Device",
    ]);
    expect(links.map((l) => l.getAttribute("href"))).toEqual([
      "/residents/R09",
      "/residents/R09/review",
      "/residents/R09/trends",
      "/residents/R09/baseline",
      "/residents/R09/log",
      "/residents/R09/device",
    ]);
    expect(links[4]).toHaveAttribute("aria-current", "page");
    expect(links.filter((l) => l.hasAttribute("aria-current"))).toHaveLength(1);
  });

  it("adds the badge '1' only for an unreviewed alarm", () => {
    const { rerender } = render(
      <ChartSectionNav residentCode="R09" current="summary" unreviewedAlarm />,
    );
    const review = screen.getByRole("link", { name: "Review and notes, alarm not reviewed" });
    const count = review.querySelector("[data-count]");
    expect(count).toHaveAttribute("data-count", "1");
    expect(count).toHaveAttribute("aria-hidden", "true");
    rerender(<ChartSectionNav residentCode="R01" current="summary" unreviewedAlarm={false} />);
    expect(
      screen.getByRole("link", { name: "Review and notes" }).querySelector("[data-count]"),
    ).toBeNull();
  });
});
