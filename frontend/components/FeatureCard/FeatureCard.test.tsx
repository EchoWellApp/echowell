// req: UX-101, UX-102, UX-103, UX-104, UX-105, UX-163, FE-098
import { render, screen } from "@testing-library/react";
import { FeatureCard } from "./FeatureCard";

const series = [
  { localDate: "2026-10-29", z: 1.2 },
  { localDate: "2026-10-30", z: -2.17 },
];

describe("FeatureCard", () => {
  it("shows the label, technical name and a signed sparkline (sign × z)", () => {
    const { container } = render(
      <ul>
        <FeatureCard
          label="Quieter"
          technicalName="loudness"
          sign={-1}
          series={series}
          baselineForming={false}
        />
      </ul>,
    );
    const card = screen.getByTestId("feature-card");
    expect(card).toHaveTextContent("Quieter (loudness)");
    expect(screen.getByText("(loudness)")).toBeInTheDocument();
    expect(
      screen.getByRole("img", {
        name: "Quieter (loudness): latest +2.2 compared with own baseline over 2 scored check-ins",
      }),
    ).toBeInTheDocument();
    expect(card.className).toMatch(/solid/);
    expect(screen.queryByText("Not scored yet")).toBeNull();
    expect(container.innerHTML).not.toMatch(/var\(--red\)|abnormal/i);
  });

  it.each([
    ["the baseline is forming", series, true],
    ["there is no scored session", [], false],
  ])("shows Not scored yet with a dashed border when %s", (_, s, forming) => {
    render(
      <ul>
        <FeatureCard
          label="More pauses"
          technicalName="number of pauses"
          sign={1}
          series={s}
          baselineForming={forming}
        />
      </ul>,
    );
    expect(screen.getByText("Not scored yet")).toBeInTheDocument();
    expect(screen.getByTestId("feature-card").className).toMatch(/dashed/);
    expect(screen.queryByRole("img")).toBeNull();
  });
});
