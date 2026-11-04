// req: UX-312, FEAT-066-FR-08
import { render, screen } from "@testing-library/react";
import { LeaningMost } from "./LeaningMost";

describe("LeaningMost", () => {
  it("lists up to three lower-case labels", () => {
    render(<LeaningMost featureKeys={["number_of_pauses", "loudness_dbfs", "voiced_fraction"]} />);
    expect(screen.getByText("Leaning most: more pauses, quieter, less voiced sound")).toBeVisible();
  });

  it("says when nothing stands out", () => {
    render(<LeaningMost featureKeys={[]} />);
    expect(screen.getByText("Leaning most: no single measurement stands out.")).toBeVisible();
  });
});
