// req: UX-405, FE-013, FE-207, TRD 11 §4.3.6, FEAT-065-FR-09
import { render } from "@testing-library/react";
import residents from "@/tests/fixtures/ds07/residents.json";
import R07 from "@/tests/fixtures/ds07/resident/R07.json";
import R08 from "@/tests/fixtures/ds07/resident/R08.json";
import R09 from "@/tests/fixtures/ds07/resident/R09.json";
import type { ResidentDetail, ResidentRow, ResidentsResponse } from "@/lib/types";
import { WhatsHappening } from "./WhatsHappening";

const data = residents as unknown as ResidentsResponse;
const row = (code: string) => data.items.find((r) => r.resident_code === code)!;
const text = (r: ResidentRow | ResidentDetail) =>
  render(<WhatsHappening row={r} meta={data.meta} />).container.textContent;

describe("WhatsHappening", () => {
  it.each([
    ["R09", "Changed from their usual since Oct 21. Not reviewed yet."],
    ["R10", "Changed from their usual since Oct 24. Not reviewed yet."],
    ["R03", "7 check-ins too noisy or too short to use."],
    ["R08", "Missing many check-ins. Baseline stuck at 13 of 16."],
    ["R01", "Within their usual range."],
    ["R07", "Usual. Baseline restarted Oct 13 after a new device."],
  ])("list row %s", (code, expected) => {
    expect(text(row(code))).toBe(expected);
  });

  it("works with a resident detail (chart Summary)", () => {
    expect(text(R09 as unknown as ResidentDetail)).toBe(
      "Changed from their usual since Oct 21. Not reviewed yet.",
    );
    expect(text(R07 as unknown as ResidentDetail)).toBe(
      "Usual. Baseline restarted Oct 13 after a new device.",
    );
    expect(text(R08 as unknown as ResidentDetail)).toBe(
      "Missing many check-ins. Baseline stuck at 13 of 16.",
    );
  });

  it("renders the reviewed variant", () => {
    expect(text({ ...row("R09"), alarm_reviewed: true })).toBe(
      "Changed from their usual since Oct 21. Reviewed.",
    );
  });
});
