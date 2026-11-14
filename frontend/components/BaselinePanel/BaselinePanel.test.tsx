// req: UX-420, UX-421, UX-422, UX-423, UX-065, UX-066, FEAT-068-AC-06, FEAT-068-AC-07
import { render, screen } from "@testing-library/react";
import type { CheckinEvent, CheckinEventList, ResidentDetail } from "@/lib/types";
import R07 from "@/tests/fixtures/ds07/resident/R07.json";
import R07checkins from "@/tests/fixtures/ds07/resident/R07-checkins.json";
import R08 from "@/tests/fixtures/ds07/resident/R08.json";
import R09 from "@/tests/fixtures/ds07/resident/R09.json";
import { BaselinePanel } from "./BaselinePanel";

const as = (x: unknown) => x as ResidentDetail;
const EXPLANATION =
  "The baseline is built from the first 16 usable check-ins, then frozen so slow changes still show up. It restarts if the resident gets a new device or the device or extraction software changes.";

describe("BaselinePanel", () => {
  it("R09: frozen and compared since Oct 17, meter 16 of 16", () => {
    const r = as(R09);
    render(
      <BaselinePanel resident={r} restart={null} meta={r.meta} firstScoredDate="2026-10-17" />,
    );
    expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent("Baseline: R09’s usual");
    expect(
      screen.getByText(
        "First 16 usable check-ins, Oct 1–16, then frozen. Compared with it since Oct 17.",
      ),
    ).toBeVisible();
    const meter = screen.getByRole("progressbar", { name: "16 of 16 usable check-ins" });
    expect(meter.tagName).toBe("PROGRESS");
    expect(meter).toHaveAttribute("max", "16");
    expect(meter).toHaveAttribute("value", "16");
    expect(screen.getByText("16 of 16 usable check-ins", { selector: "p" })).toBeVisible();
    expect(screen.getByText(EXPLANATION)).toBeVisible();
  });

  it("R08: still forming with the slowed-down clause", () => {
    const r = as(R08);
    render(<BaselinePanel resident={r} restart={null} meta={r.meta} />);
    expect(
      screen.getByText(
        "Still forming: 13 of 16 usable check-ins so far. 12 missed and 5 set-aside check-ins in the last 30 days have slowed it down.",
      ),
    ).toBeVisible();
    const meter = screen.getByRole("progressbar", { name: "13 of 16 usable check-ins" });
    expect(meter).toHaveAttribute("value", "13");
  });

  it("R07: restart prefix from the event; frozen without a scored check-in", () => {
    const r = as(R07);
    const restart = (R07checkins as unknown as CheckinEventList).items.find(
      (e) => e.event_type === "baseline_restarted",
    ) as CheckinEvent;
    const { rerender } = render(
      <BaselinePanel resident={r} restart={restart} meta={r.meta} firstScoredDate="2026-10-29" />,
    );
    expect(
      screen.getByText(
        "Restarted Oct 13 when the device was replaced (D07 to D07B), so readings from the old device are not mixed in. First 16 usable check-ins, Oct 13–28, then frozen. Compared with it since Oct 29.",
      ),
    ).toBeVisible();
    rerender(<BaselinePanel resident={as(R09)} restart={null} meta={r.meta} />);
    expect(
      screen.getByText(
        "First 16 usable check-ins, Oct 1–16, then frozen. Comparing starts with the next usable check-in.",
      ),
    ).toBeVisible();
  });
});
