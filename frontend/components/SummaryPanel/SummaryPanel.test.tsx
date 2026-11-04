// req: UX-070, UX-071, UX-072, UX-073, UX-075, UX-076, UX-077, UX-065, UX-312, FE-210, TST-096, TST-097, FEAT-066-AC-02..05
import { render, screen } from "@testing-library/react";
import type { AlertList, ChangeAlarm, ResidentDetail } from "@/lib/types";
import R03 from "@/tests/fixtures/ds07/resident/R03.json";
import R07 from "@/tests/fixtures/ds07/resident/R07.json";
import R08 from "@/tests/fixtures/ds07/resident/R08.json";
import R09 from "@/tests/fixtures/ds07/resident/R09.json";
import R09alerts from "@/tests/fixtures/ds07/resident/R09-alerts.json";
import { SummaryPanel } from "./SummaryPanel";

const as = (x: unknown) => x as ResidentDetail;
const alarm = (R09alerts as unknown as AlertList).items[0] as ChangeAlarm;
const r09 = as(R09);
const NOTE_TAIL = "[Final clinical wording: confirm with PI]";

function facts() {
  return Array.from(document.querySelectorAll("b")).map(
    (b) => `${b.textContent} / ${b.nextElementSibling?.textContent}`,
  );
}

describe("SummaryPanel", () => {
  it("R09: lead, facts, leaning most, buttons and note", () => {
    render(<SummaryPanel resident={r09} alarm={alarm} meta={r09.meta} />);
    expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent("Right now");
    expect(
      screen.getByText(
        "R09’s voice has moved away from their own usual pattern, steadily and long enough to set off the alarm on Oct 21. It is still changed.",
      ),
    ).toBeVisible();
    expect(facts()).toEqual([
      "Oct 21 / Alarm started",
      "9 days / Open",
      "Not reviewed / Review status",
    ]);
    expect(screen.getByText("Leaning most: more pauses, quieter, less voiced sound")).toBeVisible();
    expect(screen.getByRole("link", { name: "Review this alert" })).toHaveAttribute(
      "href",
      "/residents/R09/review",
    );
    expect(screen.getByRole("link", { name: "See what changed" })).toHaveAttribute(
      "href",
      "/residents/R09/trends",
    );
    const note = screen.getByText(/It is a prompt to check in, not a diagnosis\./);
    expect(note.textContent?.endsWith(NOTE_TAIL)).toBe(true);
  });

  it("shows 'Reviewed', '1 day', 'opened today' and the below-line lead", () => {
    const reviewed = as({ ...R09, alarm_reviewed: true, current_tally: 3.2 });
    const { rerender } = render(
      <SummaryPanel resident={reviewed} alarm={{ ...alarm, open_days: 1 }} meta={r09.meta} />,
    );
    expect(facts()).toContain("Reviewed / Review status");
    expect(facts()).toContain("1 day / Open");
    expect(screen.getByText(/The change score is now below the alarm line/)).toBeVisible();
    rerender(
      <SummaryPanel resident={reviewed} alarm={{ ...alarm, open_days: 0 }} meta={r09.meta} />,
    );
    expect(facts()).toContain("opened today / Open");
    const noTally = as({ ...R09, current_tally: null });
    rerender(
      <SummaryPanel resident={noTally} alarm={{ ...alarm, leaning_most: [] }} meta={r09.meta} />,
    );
    expect(screen.getByText(/It is still changed\./)).toBeVisible();
    expect(screen.getByText("Leaning most: no single measurement stands out.")).toBeVisible();
  });

  it("renders the alarm state while the alarm is not available", () => {
    render(
      <SummaryPanel
        resident={r09}
        alarm={null}
        meta={r09.meta}
        alarmState={<p>loading alarm</p>}
      />,
    );
    expect(screen.getByText("loading alarm")).toBeVisible();
    expect(screen.queryByText(/Leaning most/)).toBeNull();
  });

  it("R08 and R03: Needs attention lead and buttons", () => {
    const r08 = as(R08);
    const { rerender } = render(<SummaryPanel resident={r08} alarm={null} meta={r08.meta} />);
    expect(
      screen.getByText(
        "Missing many check-ins. Baseline stuck at 13 of 16. EchoWell can’t judge their voice well until more good check-ins come in.",
      ),
    ).toBeVisible();
    expect(
      screen.getByRole("link", { name: "See missed and set-aside check-ins" }),
    ).toHaveAttribute("href", "/residents/R08/log");
    expect(screen.getByRole("link", { name: "Check the device" })).toHaveAttribute(
      "href",
      "/residents/R08/device",
    );
    expect(screen.queryByRole("link", { name: "Review this alert" })).toBeNull();
    rerender(<SummaryPanel resident={as(R03)} alarm={null} meta={r08.meta} />);
    expect(
      screen.getByText(
        "7 check-ins too noisy or too short to use. EchoWell can’t judge their voice well until more good check-ins come in.",
      ),
    ).toBeVisible();
  });

  it("R07: usual lead with the restart sentence and no buttons", () => {
    const r07 = as(R07);
    render(<SummaryPanel resident={r07} alarm={null} meta={r07.meta} />);
    expect(
      screen.getByText(
        "R07’s voice is within their own usual range. Nothing to do. The baseline restarted on Oct 13 because the device changed (D07B, was D07); R07 is now compared only with the new baseline.",
      ),
    ).toBeVisible();
    expect(screen.queryAllByRole("link")).toHaveLength(0);
  });

  it("Learning and usual-not-scored leads use their templates and note", () => {
    const learning = as({ ...R08, needs_attention: false, attention_reasons: [] });
    const { rerender } = render(
      <SummaryPanel resident={learning} alarm={null} meta={learning.meta} />,
    );
    expect(
      screen.getByText(
        "EchoWell is still learning R08’s usual pattern: 13 of 16 usable check-ins so far. Nothing is scored and no alarm can ring until the baseline is complete.",
      ),
    ).toBeVisible();
    expect(
      screen.getByText(
        `Once the baseline is complete, R08 will be compared only with R08. A change is a prompt to check in, not a diagnosis. ${NOTE_TAIL}`,
      ),
    ).toBeVisible();
    const r01 = as({ ...R03, resident_code: "R01", needs_attention: false, attention_reasons: [] });
    rerender(<SummaryPanel resident={r01} alarm={null} meta={r01.meta} scored={false} />);
    expect(
      screen.getByText(
        "R01’s baseline is complete. Comparing starts with the next usable check-in.",
      ),
    ).toBeVisible();
  });
});
