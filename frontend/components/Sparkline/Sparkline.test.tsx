// req: FE-098, FE-099, UX-102, UX-103, UX-225
import { render, screen } from "@testing-library/react";
import { Sparkline } from "./Sparkline";

describe("Sparkline", () => {
  it("draws a 110 × 28 line of the values with a dashed zero line and no axes", () => {
    const { container } = render(<Sparkline values={[1, -0.5, 2.2]} ariaLabel="Quieter spark" />);
    const img = screen.getByRole("img", { name: "Quieter spark" });
    expect(img).toHaveStyle({ width: "110px", height: "28px" });
    const svg = container.querySelector("svg");
    expect(svg).toHaveAttribute("width", "110");
    expect(svg).toHaveAttribute("height", "28");
    const curve = container.querySelector(".recharts-line-curve");
    expect(curve).toHaveAttribute("stroke", "var(--ink)");
    expect(curve).toHaveAttribute("stroke-width", "1.5");
    const zero = container.querySelector(".recharts-reference-line-line");
    expect(zero).toHaveAttribute("stroke", "var(--rule)");
    expect(zero).toHaveAttribute("stroke-dasharray", "3 3");
    expect(container.querySelector(".recharts-cartesian-axis")).toBeNull();
    expect(container.querySelector(".recharts-tooltip-wrapper")).toBeNull();
    expect(container.querySelector(".recharts-line-dots")).toBeNull();
  });

  it("shows a dot for a single value and accepts a custom size", () => {
    const { container } = render(<Sparkline values={[0]} ariaLabel="one" width={60} height={20} />);
    expect(container.querySelector("svg")).toHaveAttribute("width", "60");
    expect(container.querySelector(".recharts-line-dots")).not.toBeNull();
  });
});
