// req: UX-185, FE-092, D-117
import { render, screen } from "@testing-library/react";
import { RangePill } from "./RangePill";

describe("RangePill", () => {
  it("shows the neutral labels without a glyph", () => {
    const { rerender } = render(<RangePill inRange={false} />);
    expect(screen.getByText("Out of range").textContent).toBe("Out of range");
    rerender(<RangePill inRange />);
    expect(screen.getByText("In range").textContent).toBe("In range");
    expect(screen.queryByText("▲")).toBeNull();
  });
});
