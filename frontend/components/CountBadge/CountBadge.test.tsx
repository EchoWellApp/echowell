// req: UX-018, UX-411
import { render } from "@testing-library/react";
import { CountBadge } from "./CountBadge";

describe("CountBadge", () => {
  it("renders the count with a hidden label, nothing for 0", () => {
    const { container, rerender } = render(<CountBadge count={2} label="2 alarms not reviewed" />);
    expect(container.textContent).toBe("2, 2 alarms not reviewed");
    rerender(<CountBadge count={0} label="x" />);
    expect(container).toBeEmptyDOMElement();
  });
});
