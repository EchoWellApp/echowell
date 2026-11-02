// req: UX-140, UX-141, UX-142, UX-143, UX-144, UX-145, UX-146, UX-147, UX-148, UX-149, UX-150, FE-101, FEAT-068-AC-01..05, FEAT-068-AC-08
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { CheckinEvent, CheckinEventList } from "@/lib/types";
import R03checkins from "@/tests/fixtures/ds07/resident/R03-checkins.json";
import R05checkins from "@/tests/fixtures/ds07/resident/R05-checkins.json";
import R07checkins from "@/tests/fixtures/ds07/resident/R07-checkins.json";
import { CheckinLog, type CheckinLogProps } from "./CheckinLog";

const items = (x: unknown) => (x as CheckinEventList).items;
const base: Omit<CheckinLogProps, "events" | "currentDeviceCode" | "residentCode"> = {
  h: 5,
  tz: "America/Chicago",
  asOf: "2026-10-30T20:00:00Z",
  baselineN: 16,
};
const CAPTION = "Duplicate records are removed quietly and not shown.";

const lines = () =>
  screen
    .getAllByRole("listitem")
    .map((li) => `${li.children[0]?.textContent} ${li.children[1]?.textContent}`);

describe("CheckinLog", () => {
  it("R07: API order, restart line and 'Check-ins started on D07.'", () => {
    render(
      <CheckinLog
        {...base}
        events={items(R07checkins)}
        residentCode="R07"
        currentDeviceCode="D07B"
      />,
    );
    expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent("Events");
    expect(lines()).toEqual([
      "Oct 29 Comparing with baseline started.",
      "Oct 28 Baseline complete (16 of 16).",
      "Oct 13 New device D07B. Baseline restarted.",
      "Oct 1 Check-ins started on D07.",
    ]);
    expect(screen.getByText(CAPTION)).toBeVisible();
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("R03 set-aside reasons and the shared-device silent day; R05 held back without statistics", () => {
    const { rerender, container } = render(
      <CheckinLog
        {...base}
        events={items(R03checkins)}
        residentCode="R03"
        currentDeviceCode="D02"
      />,
    );
    expect(lines()).toContain("Oct 18 Check-in set aside: quality flag poor; noise above limit.");
    expect(lines()).toContain("Oct 12 Shared device D02 silent all day. Check-in missed.");
    expect(lines()[lines().length - 1]).toBe("Oct 1 Check-ins started.");
    rerender(
      <CheckinLog
        {...base}
        events={items(R05checkins)}
        residentCode="R05"
        currentDeviceCode="D05"
      />,
    );
    expect(lines()).toContain("Oct 22 Check-in held back: possible other voice.");
    expect(lines()).toContain("Oct 8 Check-in held back: possible other voice.");
    expect(container.textContent).not.toMatch(/F0|z=|composite/);
  });

  it("drops anything that is not a log event (UX-144)", () => {
    const usable = {
      ...items(R07checkins)[0],
      event_type: "usable",
    } as unknown as CheckinEvent;
    render(<CheckinLog {...base} events={[usable]} residentCode="R04" currentDeviceCode="D04" />);
    expect(screen.queryByRole("listitem")).toBeNull();
    expect(screen.getByText("Nothing to report yet.")).toBeVisible();
  });

  it("shows the empty state followed by the caption (UX-149)", () => {
    render(<CheckinLog {...base} events={[]} residentCode="R11" currentDeviceCode={null} />);
    const empty = screen.getByText("Nothing to report yet.");
    expect(empty.nextElementSibling).toHaveTextContent(CAPTION);
  });

  it("offers 'Show earlier entries' and its loading and error states (UX-146)", async () => {
    const more = vi.fn();
    const { rerender } = render(
      <CheckinLog
        {...base}
        events={items(R07checkins)}
        residentCode="R07"
        currentDeviceCode="D07B"
        hasEarlier
        onShowEarlier={more}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Show earlier entries" }));
    expect(more).toHaveBeenCalledTimes(1);
    rerender(
      <CheckinLog
        {...base}
        events={items(R07checkins)}
        residentCode="R07"
        currentDeviceCode="D07B"
        hasEarlier
        loadingEarlier
      />,
    );
    expect(screen.getByRole("button", { name: "Loading earlier entries…" })).toBeDisabled();
    rerender(
      <CheckinLog
        {...base}
        events={items(R07checkins)}
        residentCode="R07"
        currentDeviceCode="D07B"
        hasEarlier
        earlierState={<p>earlier failed</p>}
      />,
    );
    expect(screen.getByText("earlier failed")).toBeVisible();
    expect(screen.queryByRole("button")).toBeNull();
    rerender(
      <CheckinLog
        {...base}
        events={[]}
        residentCode="R07"
        currentDeviceCode="D07B"
        state={<p>first failed</p>}
      />,
    );
    expect(screen.getByText("first failed")).toBeVisible();
    expect(screen.queryByText("Nothing to report yet.")).toBeNull();
  });
});
