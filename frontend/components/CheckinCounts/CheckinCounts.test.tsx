// req: UX-140, UX-047, UX-048, UX-200, FEAT-068-FR-01
import { render, screen } from "@testing-library/react";
import { CheckinCounts } from "./CheckinCounts";

const tiles = () =>
  screen
    .getAllByRole("listitem")
    .map((li) => `${li.querySelector("b")?.textContent} ${li.querySelector("span")?.textContent}`);

describe("CheckinCounts", () => {
  it("shows the four counts with their labels", () => {
    render(<CheckinCounts counts={{ used: 13, set_aside: 5, quarantined: 0, missed: 12 }} />);
    expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent("Check-ins, last 30 days");
    expect(tiles()).toEqual([
      "13 Used",
      "5 Set aside (noise, poor quality or too short)",
      "0 Held back (possible other voice)",
      "12 Missed",
    ]);
  });

  it("shows dashes while loading", () => {
    render(<CheckinCounts counts={null} />);
    expect(tiles().every((t) => t.startsWith("— "))).toBe(true);
  });
});
