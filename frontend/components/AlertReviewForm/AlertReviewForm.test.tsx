// req: UX-313, UX-314, UX-315, UX-316, UX-317, UX-318, UX-324, UX-207, UX-227, UX-228, FE-079, FE-136, FE-137, FE-138, FE-209, FEAT-069-AC-02, FEAT-069-AC-04, FEAT-069-AC-05
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import type { AlertReviewCreate } from "@/lib/types";
import configUi from "@/tests/fixtures/ds07/config-ui.json";
import r10Alerts from "@/tests/fixtures/ds07/resident/R10-alerts.json";
import { API, problem } from "@/tests/msw/handlers";
import { server } from "@/tests/msw/server";
import { withQuery } from "@/tests/support/render";
import { AlertReviewForm, apiFieldErrors } from "./AlertReviewForm";
import { ApiError } from "@/services/api";

const ALARM = r10Alerts.items[0]!;
const ID = ALARM.id;
const TZ = "America/Chicago";

function renderForm(onSaved = vi.fn(), snoozedUntil: string | null = null) {
  withQuery(
    <AlertReviewForm
      alertId={ID}
      snoozeHours={configUi.alert_snooze_hours}
      explanations={configUi.review_explanations}
      snoozedUntil={snoozedUntil}
      onSaved={onSaved}
      tz={TZ}
      asOf={configUi.meta.as_of}
    />,
  );
  return onSaved;
}

/** Records every POST; answers reviews and snoozes. */
function recordPosts() {
  const posts: { url: string; body: unknown }[] = [];
  server.use(
    http.post(`${API}/alerts/:id/reviews`, async ({ request }) => {
      const body = (await request.json()) as AlertReviewCreate;
      posts.push({ url: request.url, body });
      return HttpResponse.json(
        {
          id: "rev-new",
          alert_id: ID,
          created_at: "2026-10-30T20:10:00Z",
          explanations: body.explanations ?? [],
          outcome: body.outcome,
          note: body.note ?? null,
          reviewer: { id: "u", display_name: "Clinician User" },
        },
        { status: 201 },
      );
    }),
    http.post(`${API}/alerts/:id/snooze`, async ({ request }) => {
      posts.push({ url: request.url, body: await request.json() });
      return HttpResponse.json({ ...ALARM, snoozed_until: "2026-10-31T20:05:00Z" });
    }),
    http.post(`${API}/alerts/:id/acknowledge`, () => {
      throw new Error("acknowledge must never be called");
    }),
  );
  return posts;
}

describe("AlertReviewForm", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders the checklist in the configured order, the four choices, note and buttons", () => {
    renderForm();
    const explain = screen.getByRole("group", { name: "Anything that could explain it?" });
    expect(
      within(explain)
        .getAllByRole("checkbox")
        .map((c) => c.parentElement?.textContent),
    ).toEqual([
      "Cold, cough or sore throat",
      "Dental problem or dentures out",
      "New or changed medication",
      "Poor sleep or unusual day",
      "Room or device moved",
    ]);
    expect(explain).toHaveAccessibleDescription(
      "Provisional list — to be confirmed with the clinical team (OQ-25).",
    );
    const found = screen.getByRole("group", { name: "What did you find?" });
    const radios = within(found).getAllByRole("radio");
    expect(radios.map((r) => r.parentElement?.textContent)).toEqual([
      "Checked on resident, no concern",
      "Explained by a known cause",
      "Referred to nurse or provider",
      "Looks like a data problem: send to study team",
    ]);
    radios.forEach((r) => expect(r).not.toBeChecked());
    const note = screen.getByRole("textbox", { name: "Note" });
    expect(note).toHaveAttribute("placeholder", "What you saw or did");
    expect(note).toHaveAttribute("rows", "3");
    expect(note).toHaveAccessibleDescription("0 / 2000");
    expect(screen.getByRole("button", { name: "Save review" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Remind me in 24 hours" })).toBeVisible();
  });

  it('shows "Choose what you found." without a choice, focuses the first radio and sends nothing', async () => {
    const posts = recordPosts();
    renderForm();
    await userEvent.click(screen.getByRole("button", { name: "Save review" }));
    expect(screen.getByText("Choose what you found.")).toBeVisible();
    const first = screen.getByRole("radio", { name: "Checked on resident, no concern" });
    expect(first).toHaveFocus();
    expect(screen.getByRole("group", { name: "What did you find?" })).toHaveAccessibleDescription(
      "Choose what you found.",
    );
    expect(posts).toEqual([]);
    await userEvent.click(first);
    expect(screen.queryByText("Choose what you found.")).toBeNull();
  });

  it("sends the checked codes and outcome, omits a whitespace note, resets and announces", async () => {
    const posts = recordPosts();
    const onSaved = renderForm();
    const user = userEvent.setup();
    await user.click(screen.getByRole("checkbox", { name: "Cold, cough or sore throat" }));
    await user.click(screen.getByRole("checkbox", { name: "Room or device moved" }));
    await user.click(screen.getByRole("checkbox", { name: "Room or device moved" }));
    await user.click(screen.getByRole("radio", { name: "Explained by a known cause" }));
    await user.type(screen.getByRole("textbox", { name: "Note" }), "   ");
    await user.click(screen.getByRole("button", { name: "Save review" }));
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Review saved."));
    expect(posts).toEqual([
      {
        url: `${API}/alerts/${ID}/reviews`,
        body: { explanations: ["cold_cough_sore_throat"], outcome: "known_cause" },
      },
    ]);
    expect(onSaved).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("checkbox", { name: "Cold, cough or sore throat" })).not.toBeChecked();
    expect(screen.getByRole("radio", { name: "Explained by a known cause" })).not.toBeChecked();
    expect(screen.getByRole("textbox", { name: "Note" })).toHaveValue("");
  });

  it("sends a typed note and announces the data-problem message", async () => {
    const posts = recordPosts();
    renderForm();
    await userEvent.click(
      screen.getByRole("radio", { name: "Looks like a data problem: send to study team" }),
    );
    await userEvent.type(screen.getByRole("textbox", { name: "Note" }), "Device moved?");
    expect(screen.getByText("13 / 2000")).toBeVisible();
    await userEvent.click(screen.getByRole("button", { name: "Save review" }));
    await waitFor(() =>
      expect(screen.getByRole("status")).toHaveTextContent(
        "Review saved and sent to the study team as a data problem.",
      ),
    );
    expect(posts[0]?.body).toEqual({
      explanations: [],
      outcome: "data_problem",
      note: "Device moved?",
    });
  });

  it("sets a reminder with an empty body and announces it; no review is created", async () => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date("2026-10-30T20:05:00Z"));
    const posts = recordPosts();
    const onSaved = renderForm();
    await userEvent.click(screen.getByRole("button", { name: "Remind me in 24 hours" }));
    await waitFor(() =>
      expect(screen.getByRole("status")).toHaveTextContent(
        "Reminder set for Oct 31, 3:05 PM CT. The alarm stays on.",
      ),
    );
    expect(posts).toEqual([{ url: `${API}/alerts/${ID}/snooze`, body: {} }]);
    expect(onSaved).toHaveBeenCalledWith({ snoozedUntil: "2026-10-31T20:05:00Z" });
    expect(screen.getByText("Reminder set for Oct 31, 3:05 PM CT.")).toBeVisible();
  });

  it("shows the reminder line from the alarm's snoozed_until", () => {
    renderForm(vi.fn(), new Date(Date.now() + 3_600_000).toISOString());
    expect(screen.getByText(/^Reminder set for .+ CT\.$/)).toBeVisible();
  });

  it("keeps the choices and shows the error above the buttons when the save fails", async () => {
    server.use(http.post(`${API}/alerts/:id/reviews`, () => problem(500, "INTERNAL", "Boom")));
    renderForm();
    await userEvent.click(screen.getByRole("radio", { name: "Referred to nurse or provider" }));
    await userEvent.click(screen.getByRole("button", { name: "Save review" }));
    expect(
      await screen.findByText("Could not save the review. Your choices are kept — try again."),
    ).toBeVisible();
    expect(screen.getByRole("radio", { name: "Referred to nurse or provider" })).toBeChecked();
  });

  it("branches on ALERT_CLOSED and shows field errors under their field", async () => {
    server.use(
      http.post(`${API}/alerts/:id/reviews`, () => problem(409, "ALERT_CLOSED", "Alert closed")),
    );
    renderForm();
    await userEvent.click(screen.getByRole("radio", { name: "Referred to nurse or provider" }));
    await userEvent.click(screen.getByRole("button", { name: "Save review" }));
    expect(
      await screen.findByText("This alarm has closed, so it can no longer be reviewed."),
    ).toBeVisible();

    server.use(
      http.post(`${API}/alerts/:id/reviews`, () =>
        problem(422, "VALIDATION_ERROR", "Invalid", {
          errors: [
            { field: "body.note", code: "too_long", message: "Note is too long." },
            { field: "body.explanations.0", code: "enum", message: "Unknown explanation." },
            { field: "body.outcome", code: "enum", message: "Unknown outcome." },
          ],
        }),
      ),
    );
    await userEvent.click(screen.getByRole("button", { name: "Save review" }));
    expect(await screen.findByText("Note is too long.")).toBeVisible();
    expect(screen.getByRole("textbox", { name: "Note" })).toHaveAccessibleDescription(
      "0 / 2000 Note is too long.",
    );
    expect(
      screen.getByRole("group", { name: "Anything that could explain it?" }),
    ).toHaveAccessibleDescription(
      "Provisional list — to be confirmed with the clinical team (OQ-25). Unknown explanation.",
    );
    expect(screen.getByRole("group", { name: "What did you find?" })).toHaveAccessibleDescription(
      "Unknown outcome.",
    );
    expect(screen.queryByText(/Could not save the review/)).toBeNull();
  });

  it("shows a failure when the reminder cannot be set", async () => {
    server.use(http.post(`${API}/alerts/:id/snooze`, () => problem(500, "INTERNAL", "Boom")));
    const onSaved = renderForm();
    await userEvent.click(screen.getByRole("button", { name: "Remind me in 24 hours" }));
    expect(await screen.findByText("Could not set the reminder. Try again.")).toBeVisible();
    expect(onSaved).not.toHaveBeenCalled();
  });

  it("maps API field locations to form fields", () => {
    expect(apiFieldErrors(new Error("x"))).toEqual({});
    expect(
      apiFieldErrors(
        new ApiError({
          status: 422,
          title: "Invalid",
          errors: [
            { field: "outcome", code: "c", message: "A" },
            { field: "body.outcome", code: "c", message: "B" },
            { field: "body", code: "c", message: "C" },
            { field: "", code: "c", message: "D" },
          ],
        }),
      ),
    ).toEqual({ outcome: "A", body: "C" });
  });
});
