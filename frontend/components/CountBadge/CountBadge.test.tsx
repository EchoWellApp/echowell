// req: UX-018, UX-411
import { render } from "@testing-library/react";
import { CountBadge } from "./CountBadge";

describe("CountBadge", () => {
  it("renders the count with a hidden label, nothing for 0", () => {
    const { container, rerender } = render(<CountBadge count={2} label="2 alarms not reviewed" />);
    expect(container.textContent).toBe(", 2 alarms not reviewed");
    const count = container.querySelector("[data-count]");
    expect(count).toHaveAttribute("data-count", "2");
    expect(count).toHaveAttribute("aria-hidden", "true");
    rerender(<CountBadge count={0} label="x" />);
    expect(container).toBeEmptyDOMElement();
  });
});
