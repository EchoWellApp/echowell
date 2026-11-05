// req: UX-406, FE-092, TRD 11 §4.3.4, FEAT-065-AC-04
import { render, screen, within } from "@testing-library/react";
import residents from "@/tests/fixtures/ds07/residents.json";
import type { ResidentsResponse } from "@/lib/types";
import { StatusLegend } from "./StatusLegend";

const meta = (residents as unknown as ResidentsResponse).meta;

describe("StatusLegend", () => {
  it("lists the four pills with their meanings, N from meta", () => {
    render(<StatusLegend meta={meta} />);
    const items = within(screen.getByRole("list", { name: "Status meanings" })).getAllByRole(
      "listitem",
    );
    expect(items.map((i) => i.textContent)).toEqual([
      "▲ChangedTheir voice has moved away from their own usual. Check on them.",
      "!Needs attentionNot enough good check-ins to judge. Check the device or the routine.",
      "○LearningStill collecting the first 16 check-ins to learn their usual.",
      "●UsualWithin their own usual range.",
    ]);
  });

  it("uses meta.baseline_n for the Learning meaning", () => {
    render(<StatusLegend meta={{ ...meta, baseline_n: 20 }} />);
    expect(
      screen.getByText("Still collecting the first 20 check-ins to learn their usual."),
    ).toBeInTheDocument();
  });
});
