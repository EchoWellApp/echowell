// req: FE-208, FE-088, UX-400
import { render, screen } from "@testing-library/react";
import configUi from "@/tests/fixtures/ds07/config-ui.json";
import type { Meta } from "@/lib/types";
import { DataBar } from "./DataBar";

const meta = configUi.meta as Meta;

describe("DataBar", () => {
  it("shows the test-data sentence on test_v0_1", () => {
    render(<DataBar meta={meta} />);
    expect(screen.getByTestId("data-bar")).toHaveTextContent(
      "Test data only (pipeline test data v0.1, Oct 1–30, 2026). No real residents. No audio is stored or played anywhere in EchoWell.",
    );
  });

  it("shows only the no-audio sentence in production and before meta", () => {
    const { rerender } = render(<DataBar meta={{ ...meta, pipeline_profile: "production" }} />);
    expect(screen.getByTestId("data-bar").textContent).toBe(
      "No audio is stored or played anywhere in EchoWell.",
    );
    rerender(<DataBar meta={undefined} />);
    expect(screen.getByTestId("data-bar").textContent).toBe(
      "No audio is stored or played anywhere in EchoWell.",
    );
  });
});
