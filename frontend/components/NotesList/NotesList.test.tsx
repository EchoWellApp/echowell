// req: UX-128, UX-133, UX-134, UX-135, UX-204, FEAT-071-AC-04
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { NoteType, StaffNote } from "@/lib/types";
import { NotesList } from "./NotesList";

const TZ = "America/Chicago";

function note(i: number, type: NoteType = "observation", body = `Note ${i}`): StaffNote {
  return {
    id: `n-${i}`,
    alert_id: null,
    author: { id: "u", display_name: "Clinician User" },
    body,
    created_at: `2026-10-${String(10 + i).padStart(2, "0")}T15:00:00Z`,
    note_type: type,
    resident_code: "R10",
    supersedes_id: null,
  };
}

describe("NotesList", () => {
  it("shows the empty text instead of the list", () => {
    render(<NotesList notes={[]} tz={TZ} />);
    expect(
      screen.getByText(
        "No notes yet. Add what you saw or did, for example “Resident has a cold; nurse notified.”",
      ),
    ).toBeVisible();
    expect(screen.queryByRole("heading", { name: "Previous notes" })).toBeNull();
  });

  it("lists notes newest first with time, type and author, text kept as typed", () => {
    render(
      <NotesList
        notes={[
          note(1, "observation", "Resident has a cold; nurse notified."),
          note(2, "action_taken", "Line one\nLine two <b>not bold</b>"),
          note(3, "follow_up"),
        ]}
        tz={TZ}
        asOf="2026-10-30T20:00:00Z"
      />,
    );
    expect(screen.getByRole("heading", { level: 3, name: "Previous notes" })).toBeVisible();
    const items = screen.getAllByRole("listitem");
    expect(items.map((li) => li.querySelector("p")?.textContent)).toEqual([
      "Oct 13, 10:00 AM CT · Follow-up · Clinician User",
      "Oct 12, 10:00 AM CT · Action taken · Clinician User",
      "Oct 11, 10:00 AM CT · Observation · Clinician User",
    ]);
    expect(items[1]!.textContent).toContain("Line one\nLine two <b>not bold</b>");
    expect(items[1]!.querySelector("b")).toBeNull();
    expect(screen.getByText("Resident has a cold; nurse notified.")).toBeVisible();
  });

  it('shows 10 notes and "Show all notes (<count>)" when more exist', async () => {
    const notes = Array.from({ length: 12 }, (_, i) => note(i + 1));
    render(<NotesList notes={notes} tz={TZ} />);
    expect(screen.getAllByRole("listitem")).toHaveLength(10);
    await userEvent.click(screen.getByRole("button", { name: "Show all notes (12)" }));
    expect(screen.getAllByRole("listitem")).toHaveLength(12);
    expect(screen.queryByRole("button", { name: /Show all notes/ })).toBeNull();
  });
});
