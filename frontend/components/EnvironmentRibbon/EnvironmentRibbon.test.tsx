// req: FE-172, ENV-032
import { render, screen } from "@testing-library/react";
import { EnvironmentRibbon } from "./EnvironmentRibbon";

describe("EnvironmentRibbon", () => {
  it("shows LOCAL for the local environment", () => {
    render(<EnvironmentRibbon appEnv="local" />);
    expect(screen.getByRole("note")).toHaveTextContent("LOCAL");
  });

  it("shows the staging label", () => {
    render(<EnvironmentRibbon appEnv="staging" />);
    expect(screen.getByRole("note")).toHaveTextContent("STAGING – synthetic data");
  });

  it("renders nothing in production", () => {
    const { container } = render(<EnvironmentRibbon appEnv="production" />);
    expect(container).toBeEmptyDOMElement();
  });
});
