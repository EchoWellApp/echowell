// req: UX-106, UX-107
import { render, screen } from "@testing-library/react";
import features from "@/tests/fixtures/ds07/resident/R09-features.json";
import { OtherMeasurementsCard } from "./OtherMeasurementsCard";

describe("OtherMeasurementsCard", () => {
  it("counts the stored-not-scored keys without listing them", () => {
    render(
      <ul>
        <OtherMeasurementsCard storedKeys={features.stored_feature_keys} />
      </ul>,
    );
    const card = screen.getByTestId("other-measurements-card");
    expect(card).toHaveTextContent(
      /^12 other measurements \(pitch, jitter, MFCCs and others\)Stored, not scored$/,
    );
    expect(card.textContent).not.toMatch(/mfcc1|jitter_local|hnr/);
  });

  it("uses the API count", () => {
    render(
      <ul>
        <OtherMeasurementsCard storedKeys={["a", "b"]} />
      </ul>,
    );
    expect(
      screen.getByText("2 other measurements (pitch, jitter, MFCCs and others)"),
    ).toBeInTheDocument();
  });
});
