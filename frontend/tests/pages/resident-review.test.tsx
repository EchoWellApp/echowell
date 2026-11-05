// req: FE-030, FE-032, FE-085, FE-086, FE-087, FE-130, FE-133, FE-134, FE-135, FE-187, FE-188, FE-193, FE-209, UX-120, UX-126, UX-202, UX-229, UX-310, UX-322, UX-330, §4.17.5, FEAT-069-AC-01, FEAT-069-AC-06, FEAT-071-AC-01, FEAT-071-AC-03, FEAT-071-AC-04
import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import ReviewPage from "@/app/(protected)/residents/[residentCode]/review/page";
import type { AlertReview, AlertReviewCreate, StaffNote, StaffNoteCreate } from "@/lib/types";
import r10Alerts from "@/tests/fixtures/ds07/resident/R10-alerts.json";
import r10Notes from "@/tests/fixtures/ds07/resident/R10-notes.json";
import r10Reviews from "@/tests/fixtures/ds07/resident/R10-reviews.json";
import { API, problem } from "@/tests/msw/handlers";
import { server } from "@/tests/msw/server";
import { setLocation } from "@/tests/support/navigation";
import { renderSignedIn } from "@/tests/support/render";

function open(code: string, role: "admin" | "clinician" | "researcher" = "clinician") {
  setLocation(`/residents/${code}/review`, "", { residentCode: code });
  return renderSignedIn(<ReviewPage />, role);
}

function trackRequests() {
  const seen: string[] = [];
  const listener = ({ request }: { request: Request }) => {
    const url = new URL(request.url);
    seen.push(`${request.method} ${url.pathname}${url.search}`);
  };
  server.events.on("request:start", listener);
  return {
    seen,
    stop: () => server.events.removeListener("request:start", listener),
  };
}

describe("Review and notes section", () => {
  it.each([
    ["R09", "Review alert: changed since Oct 21"],
    ["R10", "Review alert: changed since Oct 24"],
  ])("renders the §4.17.5 review panel and Staff notes for %s", async (code, heading) => {
    open(code);
    const h2 = await screen.findByRole("heading", { level: 2, name: heading });
    const panel = h2.closest("section")!;
    expect(within(panel).getAllByRole("checkbox")).toHaveLength(5);
    expect(within(panel).getAllByRole("radio")).toHaveLength(4);
    expect(within(panel).getByRole("button", { name: "Save review" })).toBeVisible();
    expect(within(panel).getByRole("button", { name: "Remind me in 24 hours" })).toBeVisible();
    expect(
      within(panel).getByRole("heading", { level: 3, name: "Previous reviews" }),
    ).toBeVisible();
    expect(await within(panel).findByText("Not reviewed yet.")).toBeVisible();
    // UX-120: Staff notes follows the review panel.
    const sections = screen.getAllByRole("region");
    expect(sections.map((s) => s.querySelector("h2")?.textContent)).toEqual([
      heading,
      "Staff notes",
    ]);
    expect(screen.queryByRole("heading", { level: 1 })).toBeNull();
    expect(document.title).toBe(`${code} · Review and notes – EchoWell`);
  });

  it("shows only Staff notes for a resident who is not Changed (R01)", async () => {
    open("R01");
    expect(await screen.findByRole("heading", { level: 2, name: "Staff notes" })).toBeVisible();
    expect(
      await screen.findByText(
        "No notes yet. Add what you saw or did, for example “Resident has a cold; nurse notified.”",
      ),
    ).toBeVisible();
    await waitFor(() => expect(screen.getAllByRole("region")).toHaveLength(1));
    expect(screen.queryByText(/Review alert/)).toBeNull();
  });

  it("shows the read-only messages to researchers with Previous reviews visible", async () => {
    open("R09", "researcher");
    expect(await screen.findByText("Only clinicians and admins can review alarms.")).toBeVisible();
    expect(screen.getByText("Only clinicians and admins can add notes.")).toBeVisible();
    expect(screen.getByRole("heading", { name: "Previous reviews" })).toBeVisible();
    expect(await screen.findByText("Not reviewed yet.")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Save review" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Add note" })).toBeNull();
  });

  it("FE-187 on R10: adds a note, saves a review, refetches, and never acknowledges", async () => {
    const notes: StaffNote[] = [];
    const reviews: AlertReview[] = [];
    let reviewed = false;
    const alarmId = r10Alerts.items[0]!.id;
    server.use(
      http.post(`${API}/residents/R10/notes`, async ({ request }) => {
        const body = (await request.json()) as StaffNoteCreate;
        const note: StaffNote = {
          id: "n1",
          alert_id: body.alert_id ?? null,
          author: { id: "u", display_name: "Clinician User" },
          body: body.body,
          created_at: "2026-10-30T20:05:00Z",
          note_type: body.note_type,
          resident_code: "R10",
          supersedes_id: null,
        };
        notes.push(note);
        return HttpResponse.json(note, { status: 201 });
      }),
      http.get(`${API}/residents/R10/notes`, () =>
        HttpResponse.json({ ...r10Notes, items: notes, total: notes.length }),
      ),
      http.post(`${API}/alerts/:id/reviews`, async ({ request, params }) => {
        const body = (await request.json()) as AlertReviewCreate;
        const review: AlertReview = {
          id: "rev1",
          alert_id: String(params.id),
          created_at: "2026-10-30T20:10:00Z",
          explanations: body.explanations ?? [],
          outcome: body.outcome,
          note: body.note ?? null,
          reviewer: { id: "u", display_name: "Clinician User" },
        };
        reviews.push(review);
        reviewed = true;
        return HttpResponse.json(review, { status: 201 });
      }),
      http.get(`${API}/alerts/:id/reviews`, () =>
        HttpResponse.json({ ...r10Reviews, items: reviews, total: reviews.length }),
      ),
      http.get(`${API}/alerts`, () =>
        HttpResponse.json({
          ...r10Alerts,
          items: [
            {
              ...r10Alerts.items[0],
              status: reviewed ? "acknowledged" : "open",
              reviewed,
              review_count: reviews.length,
            },
          ],
        }),
      ),
    );
    const requests = trackRequests();
    open("R10");
    const user = userEvent.setup();

    const noteBox = await screen.findByRole("textbox", { name: "New note" });
    expect(screen.getByRole("combobox", { name: "Type of note" })).toHaveValue("observation");
    await user.type(noteBox, "Resident has a cold; nurse notified.");
    await user.click(screen.getByRole("button", { name: "Add note" }));
    expect(await screen.findByText("Note saved.")).toBeInTheDocument();
    expect(
      await screen.findByText("Oct 30, 3:05 PM CT · Observation · Clinician User"),
    ).toBeVisible();
    expect(screen.getByText("Resident has a cold; nurse notified.")).toBeVisible();

    await user.click(await screen.findByRole("checkbox", { name: "Cold, cough or sore throat" }));
    await user.click(screen.getByRole("radio", { name: "Explained by a known cause" }));
    await user.click(screen.getByRole("button", { name: "Save review" }));
    expect(await screen.findByText("Review saved.")).toBeInTheDocument();
    expect(
      await screen.findByText("Oct 30, 3:10 PM CT · Clinician User · Explained by a known cause"),
    ).toBeVisible();
    expect(screen.getByText("Possible explanations: Cold, cough or sore throat")).toBeVisible();
    // FE-134: the panel still reviews the same alarm; nothing was reset locally.
    expect(
      screen.getByRole("heading", { name: "Review alert: changed since Oct 24" }),
    ).toBeVisible();

    const posts = requests.seen.filter((r) => r.startsWith("POST"));
    expect(posts).toEqual([
      "POST /api/v1/residents/R10/notes",
      `POST /api/v1/alerts/${alarmId}/reviews`,
    ]);
    expect(requests.seen.some((r) => r.includes("acknowledge"))).toBe(false);
    // FE-085 / FE-086: the resident and its alerts are read again after each save.
    expect(requests.seen.filter((r) => r === "GET /api/v1/residents/R10").length).toBeGreaterThan(
      1,
    );
    expect(
      requests.seen.filter((r) => r === "GET /api/v1/alerts?resident_code=R10").length,
    ).toBeGreaterThan(1);
    requests.stop();
  });

  it("shows an error in the review panel only when the alerts fail (UX-202)", async () => {
    server.use(http.get(`${API}/alerts`, () => problem(500, "INTERNAL", "Boom")));
    open("R09");
    expect(
      await screen.findByText(
        "Could not load the alarm review. Check your connection and try again.",
      ),
    ).toBeVisible();
    expect(screen.getByRole("heading", { name: "Staff notes" })).toBeVisible();
    server.resetHandlers();
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(
      await screen.findByRole("heading", { name: "Review alert: changed since Oct 21" }),
    ).toBeVisible();
  });

  it("shows loading then error states for Previous reviews", async () => {
    server.use(http.get(`${API}/alerts/:id/reviews`, () => problem(503, "UNAVAILABLE", "Down")));
    open("R09");
    expect(await screen.findByText("Loading previous reviews…")).toBeInTheDocument();
    expect(
      await screen.findByText(
        "Could not load previous reviews. Check your connection and try again.",
      ),
    ).toBeVisible();
  });

  it("shows the resident error and still the notes when the resident fails", async () => {
    server.use(http.get(`${API}/residents/R09`, () => problem(500, "INTERNAL", "Boom")));
    open("R09");
    expect(
      await screen.findByText(
        "Could not load the alarm review. Check your connection and try again.",
      ),
    ).toBeVisible();
    expect(screen.getByRole("heading", { name: "Staff notes" })).toBeVisible();
  });

  it("renders nothing for an unknown resident (the layout shows not-found)", async () => {
    server.use(
      http.get(`${API}/residents/R99`, () => problem(404, "RESIDENT_NOT_FOUND", "Not found")),
      http.get(`${API}/residents/R99/notes`, () => problem(404, "RESIDENT_NOT_FOUND", "Not found")),
    );
    const { container } = open("R99");
    await waitFor(() => expect(container).toBeEmptyDOMElement());
  });

  it("makes no API call for an invalid resident code (FE-030)", async () => {
    const requests = trackRequests();
    const { container } = open("r09%3Cx%3E");
    await act(async () => {
      await new Promise((r) => setTimeout(r, 50));
    });
    expect(container).toBeEmptyDOMElement();
    expect(requests.seen.filter((r) => !r.includes("/auth/me"))).toEqual([]);
    requests.stop();
  });
});
