// req: UX-120, UX-121, UX-123, UX-124, UX-130, UX-131, UX-132, UX-133, UX-207, UX-227, UX-228, FE-079, FE-085, FE-089, FE-130, FE-132, FE-133, FE-135, FEAT-071-AC-02, FEAT-071-AC-03, FEAT-071-AC-05, FEAT-071-AC-06
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import type { StaffNote, StaffNoteCreate } from "@/lib/types";
import { API, problem } from "@/tests/msw/handlers";
import { server } from "@/tests/msw/server";
import { testQueryClient, withQuery } from "@/tests/support/render";
import notesR10 from "@/tests/fixtures/ds07/resident/R10-notes.json";
import { StaffNotes } from "./StaffNotes";

const ALERT_ID = "a153a486-6e5a-4b0b-a71b-08d73e9f89b2";

/** Serves POST /notes and keeps the saved notes for the following GET. */
function noteServer() {
  const posted: StaffNoteCreate[] = [];
  const saved: StaffNote[] = [];
  server.use(
    http.post(`${API}/residents/R10/notes`, async ({ request }) => {
      const body = (await request.json()) as StaffNoteCreate;
      posted.push(body);
      const note: StaffNote = {
        id: `n-${posted.length}`,
        alert_id: body.alert_id ?? null,
        author: { id: "u", display_name: "Clinician User" },
        body: body.body,
        created_at: `2026-10-30T20:0${posted.length}:00Z`,
        note_type: body.note_type,
        resident_code: "R10",
        supersedes_id: null,
      };
      saved.push(note);
      return HttpResponse.json(note, { status: 201 });
    }),
    http.get(`${API}/residents/R10/notes`, () =>
      HttpResponse.json({ ...notesR10, items: [...saved].reverse(), total: saved.length }),
    ),
  );
  return posted;
}

const textarea = () => screen.getByRole("textbox", { name: "New note" });
const addButton = () => screen.getByRole("button", { name: "Add note" });

describe("StaffNotes", () => {
  it("renders the form controls in order with hint, counter and empty list", async () => {
    withQuery(<StaffNotes residentCode="R10" openAlertId={null} canWrite />);
    expect(screen.getByRole("heading", { level: 2, name: "Staff notes" })).toBeVisible();
    const select = screen.getByRole("combobox", { name: "Type of note" });
    expect(select).toHaveValue("observation");
    expect(
      within(select)
        .getAllByRole("option")
        .map((o) => o.textContent),
    ).toEqual(["Observation", "Action taken", "Follow-up"]);
    expect(textarea()).toHaveAttribute("rows", "3");
    expect(textarea()).toHaveAttribute("placeholder", "Add a note");
    expect(textarea()).toHaveAccessibleDescription(
      "Do not enter names or other identifying details. 0 / 2000",
    );
    expect(addButton()).toHaveAttribute("aria-disabled", "true");
    expect(await screen.findByText(/^No notes yet\./)).toBeVisible();
  });

  it("saves a note of each type, clears the text, keeps the type and lists it", async () => {
    const posted = noteServer();
    const client = testQueryClient();
    const invalidate = vi.spyOn(client, "invalidateQueries");
    withQuery(<StaffNotes residentCode="R10" openAlertId={ALERT_ID} canWrite />, client);
    const user = userEvent.setup();
    const cases = [
      ["observation", "Observation", "Resident has a cold; nurse notified."],
      ["action_taken", "Action taken", "Called the nurse."],
      ["follow_up", "Follow-up", "Check again tomorrow."],
    ] as const;
    for (const [value, label, body] of cases) {
      await user.selectOptions(screen.getByRole("combobox", { name: "Type of note" }), value);
      await user.type(textarea(), body);
      await user.click(addButton());
      await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Note saved."));
      expect(textarea()).toHaveValue("");
      expect(screen.getByRole("combobox", { name: "Type of note" })).toHaveValue(value);
      expect(await screen.findByText(body)).toBeVisible();
      expect(screen.getByText(new RegExp(` · ${label} · Clinician User$`))).toBeVisible();
    }
    expect(posted).toEqual([
      {
        note_type: "observation",
        body: "Resident has a cold; nurse notified.",
        alert_id: ALERT_ID,
      },
      { note_type: "action_taken", body: "Called the nurse.", alert_id: ALERT_ID },
      { note_type: "follow_up", body: "Check again tomorrow.", alert_id: ALERT_ID },
    ]);
    const keys = invalidate.mock.calls.map((c) => c[0]?.queryKey);
    expect(keys).toContainEqual(["resident", "R10"]);
    expect(keys).toContainEqual(["residents"]);
    expect(keys).toContainEqual(["alerts"]);
  });

  it("omits alert_id when the resident has no open alarm", async () => {
    const posted = noteServer();
    withQuery(<StaffNotes residentCode="R10" openAlertId={null} canWrite />);
    await userEvent.type(textarea(), "Seen.");
    await userEvent.click(addButton());
    await waitFor(() => expect(posted).toHaveLength(1));
    expect(posted[0]).toEqual({ note_type: "observation", body: "Seen." });
  });

  it("keeps the typed text and shows the failure message when the save fails", async () => {
    server.use(
      http.post(`${API}/residents/R10/notes`, () => problem(500, "INTERNAL", "Server error")),
    );
    withQuery(<StaffNotes residentCode="R10" openAlertId={null} canWrite />);
    await userEvent.selectOptions(screen.getByRole("combobox"), "follow_up");
    await userEvent.type(textarea(), "Do not lose me");
    await userEvent.click(addButton());
    expect(
      await screen.findByText("Could not save the note. Your text is kept — try again."),
    ).toBeVisible();
    expect(textarea()).toHaveValue("Do not lose me");
    expect(screen.getByRole("combobox")).toHaveValue("follow_up");
    expect(screen.getByRole("status")).toHaveTextContent("");
  });

  it("shows field errors under the matching field (FE-079)", async () => {
    server.use(
      http.post(`${API}/residents/R10/notes`, () =>
        problem(422, "VALIDATION_ERROR", "Invalid", {
          errors: [
            { field: "body.body", code: "string_too_long", message: "Body is too long." },
            { field: "note_type", code: "enum", message: "Unknown note type." },
          ],
        }),
      ),
    );
    withQuery(<StaffNotes residentCode="R10" openAlertId={null} canWrite />);
    await userEvent.type(textarea(), "x");
    await userEvent.click(addButton());
    expect(await screen.findByText("Body is too long.")).toBeVisible();
    expect(textarea()).toHaveAccessibleDescription(
      expect.stringContaining("Body is too long.") as unknown as string,
    );
    expect(screen.getByRole("combobox")).toHaveAccessibleDescription("Unknown note type.");
  });

  it("is disabled for a whitespace-only or 2001-character note and explains an empty save", async () => {
    const requests: string[] = [];
    server.events.on("request:start", ({ request }) => {
      if (request.method === "POST") requests.push(request.url);
    });
    withQuery(<StaffNotes residentCode="R10" openAlertId={null} canWrite />);
    const user = userEvent.setup();
    await user.type(textarea(), "   ");
    expect(addButton()).toHaveAttribute("aria-disabled", "true");
    await user.click(addButton());
    const message = screen.getByText("Write a short note before saving.");
    expect(message).toBeVisible();
    expect(textarea()).toHaveAccessibleDescription(
      expect.stringContaining("Write a short note before saving.") as unknown as string,
    );
    await user.clear(textarea());
    await user.click(textarea());
    await user.paste("a".repeat(2001));
    expect(screen.queryByText("Write a short note before saving.")).toBeNull();
    expect(screen.getByText("2001 / 2000")).toBeVisible();
    expect(addButton()).toHaveAttribute("aria-disabled", "true");
    await user.click(addButton());
    await user.type(textarea(), "{Backspace}");
    expect(screen.getByText("2000 / 2000")).toBeVisible();
    expect(addButton()).toHaveAttribute("aria-disabled", "false");
    expect(requests).toEqual([]);
    server.events.removeAllListeners();
  });

  it("shows the read-only message and the previous notes to researchers", async () => {
    server.use(
      http.get(`${API}/residents/R09/notes`, () =>
        HttpResponse.json({
          ...notesR10,
          total: 1,
          items: [
            {
              id: "n1",
              alert_id: null,
              author: { id: "u", display_name: "Clinician User" },
              body: "Resident has a cold; nurse notified.",
              created_at: "2026-10-30T19:00:00Z",
              note_type: "observation",
              resident_code: "R09",
              supersedes_id: null,
            },
          ],
        }),
      ),
    );
    withQuery(<StaffNotes residentCode="R09" openAlertId={null} canWrite={false} />);
    expect(screen.getByText("Only clinicians and admins can add notes.")).toBeVisible();
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(screen.queryByRole("button", { name: "Add note" })).toBeNull();
    expect(
      await screen.findByText("Oct 30, 2:00 PM CT · Observation · Clinician User"),
    ).toBeVisible();
  });

  it("shows loading and error states for the notes list", async () => {
    server.use(
      http.get(`${API}/residents/R10/notes`, () => problem(500, "INTERNAL", "Server error")),
    );
    withQuery(<StaffNotes residentCode="R10" openAlertId={null} canWrite />);
    expect(screen.getByText("Loading staff notes…")).toBeVisible();
    expect(
      await screen.findByText("Could not load staff notes. Check your connection and try again."),
    ).toBeVisible();
    expect(screen.getByText("Reference: req-test-0001")).toBeVisible();
  });
});
