// req: UX-362..UX-366, UX-382
import { render, screen } from "@testing-library/react";
import type { Funnel } from "@/lib/types";
import analytics from "@/tests/fixtures/ds07/analytics.json";
import { LossFunnel, meterWidth } from "./LossFunnel";

describe("LossFunnel", () => {
  it("uses the partial-enrolment Expected note", () => {
    const f = { ...(analytics.funnel as Funnel), expected: 290, set_aside_multi_reason: 0 };
    render(<LossFunnel funnel={f} />);
    const notes = screen.getAllByTestId("funnel-row").map((r) => r.querySelector("p")?.textContent);
    expect(notes[0]).toBe("sum of days enrolled across 10 residents");
    expect(notes[2]).toBe("12 set aside: quality flag 5, noise 5, too short 3");
  });

  it("meter widths are proportional to Expected", () => {
    expect(meterWidth(281, 300)).toBe(93.7);
    expect(meterWidth(267, 300)).toBe(89);
    expect(meterWidth(5, 0)).toBe(0);
  });
});
