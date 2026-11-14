// req: UX-181, AC-UX-07, FEAT-073-FR-01
import { render, screen } from "@testing-library/react";
import { ExperimentalBanner } from "./ExperimentalBanner";

describe("ExperimentalBanner", () => {
  it("shows the open-question note by default", () => {
    render(<ExperimentalBanner />);
    expect(
      screen.getByText(
        "Future / experimental. Not in pipeline test v0.1: the test data has no admission group or facility range yet. Open question for Shaba and the PI.",
      ),
    ).toBeVisible();
  });

  it("renders given children instead", () => {
    render(<ExperimentalBanner>Other note</ExperimentalBanner>);
    expect(screen.getByText("Other note")).toBeVisible();
  });
});
