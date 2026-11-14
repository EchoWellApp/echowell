// req: UX-320, FEAT-069-AC-07, FE-209
import { render, screen, within } from "@testing-library/react";
import type { AlertReview } from "@/lib/types";
import configUi from "@/tests/fixtures/ds07/config-ui.json";
import { ReviewHistory, explanationLabel } from "./ReviewHistory";

const TZ = "America/Chicago";
const AS_OF = "2026-10-30T20:00:00Z";

const review = (over: Partial<AlertReview>): AlertReview => ({
  id: "rev-1",
  alert_id: "a-1",
  created_at: "2026-10-30T15:05:00Z",
  explanations: [],
  outcome: "no_concern",
  note: null,
  reviewer: { id: "u-1", display_name: "Clinician User" },
  ...over,
});

describe("ReviewHistory", () => {
  it('reads "Not reviewed yet." with no reviews', () => {
    render(<ReviewHistory reviews={[]} tz={TZ} />);
    expect(screen.getByRole("heading", { level: 3, name: "Previous reviews" })).toBeVisible();
    expect(screen.getByText("Not reviewed yet.")).toBeVisible();
  });

  it("lists two reviews newest first with time, reviewer, outcome, explanations and note", () => {
    const reviews = [
      review({ id: "old", created_at: "2026-10-29T14:10:00Z", outcome: "no_concern" }),
      review({
        id: "new",
        created_at: "2026-10-30T19:28:00Z",
        outcome: "known_cause",
        explanations: ["cold_cough_sore_throat"],
        note: "Coughing.\nNurse aware.",
        reviewer: { id: "u-2", display_name: "Admin User" },
      }),
    ];
    render(
      <ReviewHistory
        reviews={reviews}
        tz={TZ}
        asOf={AS_OF}
        explanations={configUi.review_explanations}
      />,
    );
    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(
      within(items[0]!).getByText("Oct 30, 2:28 PM CT · Admin User · Explained by a known cause"),
    ).toBeVisible();
    expect(
      within(items[0]!).getByText("Possible explanations: Cold, cough or sore throat"),
    ).toBeVisible();
    expect(items[0]!.textContent).toContain("Coughing.\nNurse aware.");
    expect(
      within(items[1]!).getByText(
        "Oct 29, 9:10 AM CT · Clinician User · Checked on resident, no concern",
      ),
    ).toBeVisible();
    expect(items[1]!.textContent).not.toContain("Possible explanations");
    expect(screen.queryByText("Not reviewed yet.")).toBeNull();
  });

  it("falls back to the wording labels, then to the code, for unknown explanations", () => {
    expect(explanationLabel("dental_dentures")).toBe("Dental problem or dentures out");
    expect(explanationLabel("new_code", [{ code: "new_code", label: "API label" }])).toBe(
      "API label",
    );
    expect(explanationLabel("mystery")).toBe("mystery");
  });
});
