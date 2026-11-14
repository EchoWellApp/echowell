// req: UX-100, UX-101, UX-102, UX-103, UX-104, UX-106, UX-107, UX-108, UX-163, UX-204, FEAT-067-AC-05, FEAT-067-AC-06, AC-UX-05
import { render, screen, within } from "@testing-library/react";
import type { FeaturesResponse } from "@/lib/types";
import r07 from "@/tests/fixtures/ds07/resident/R07-features.json";
import r08 from "@/tests/fixtures/ds07/resident/R08-features.json";
import r09 from "@/tests/fixtures/ds07/resident/R09-features.json";
import { MeasurementCards, scoredSeries } from "./MeasurementCards";

const LABELS = [
  "Quieter (loudness)",
  "Slower to say the phrase (phrase duration)",
  "Fewer syllables per second (speech rate)",
  "Slower while talking (articulation rate)",
  "More pauses (number of pauses)",
  "More time in pauses (pause fraction)",
  "Less voiced sound (voiced fraction)",
];

describe("MeasurementCards", () => {
  it("renders R09: heading, intro, 7 cards in order with sparklines, the 8th card and caption", () => {
    render(
      <MeasurementCards
        features={r09 as unknown as FeaturesResponse}
        residentCode="R09"
        baselineForming={false}
      />,
    );
    expect(
      screen.getByRole("heading", { level: 2, name: "The 7 voice measurements behind the score" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Each is compared with R09’s own baseline. The score rises when the voice is:",
      ),
    ).toBeInTheDocument();
    const cards = screen.getAllByTestId("feature-card");
    expect(cards).toHaveLength(7);
    cards.forEach((c, i) =>
      expect(c.textContent).toMatch(new RegExp(`^${LABELS[i]?.replace(/[()]/g, "\\$&")}`)),
    );
    expect(
      screen.getByRole("img", {
        name: "Quieter (loudness): latest +2.2 compared with own baseline over 14 scored check-ins",
      }),
    ).toBeInTheDocument();
    expect(screen.getAllByRole("img")).toHaveLength(7);
    expect(screen.getByTestId("other-measurements-card")).toHaveTextContent(
      "12 other measurements (pitch, jitter, MFCCs and others)",
    );
    expect(
      screen.getByText(
        "Measurement names are placeholders until Team 1 confirms the openSMILE output names. Morning check-ins are adjusted before comparing.",
      ),
    ).toBeInTheDocument();
    expect(within(screen.getByRole("list")).getAllByRole("listitem")).toHaveLength(8);
  });

  it("shows Not scored yet on all 7 R08 cards while forming (AC-UX-05)", () => {
    render(
      <MeasurementCards
        features={r08 as unknown as FeaturesResponse}
        residentCode="R08"
        baselineForming
      />,
    );
    expect(screen.getAllByText("Not scored yet")).toHaveLength(7);
    expect(screen.queryAllByRole("img")).toHaveLength(0);
  });

  it("plots only the scored sessions of the current epoch (R07: 2)", () => {
    render(
      <MeasurementCards
        features={r07 as unknown as FeaturesResponse}
        residentCode="R07"
        baselineForming={false}
      />,
    );
    expect(screen.getAllByRole("img", { name: /over 2 scored check-ins$/ })).toHaveLength(7);
  });

  it("treats a missing series as not scored", () => {
    const f = { ...(r09 as unknown as FeaturesResponse), scored_features: [] };
    render(<MeasurementCards features={f} residentCode="R09" baselineForming={false} />);
    expect(screen.getAllByText("Not scored yet")).toHaveLength(7);
    expect(scoredSeries(undefined)).toEqual([]);
  });
});
