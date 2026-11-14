// req: UX-310, UX-313, UX-314, UX-317, UX-320, UX-321, UX-322, UX-126, FE-086, FE-134, FE-135, FE-205, FE-209, §4.17.5
import { act, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import type { ChangeAlarm, UiConfig } from "@/lib/types";
import configUi from "@/tests/fixtures/ds07/config-ui.json";
import r09Alerts from "@/tests/fixtures/ds07/resident/R09-alerts.json";
import r10Alerts from "@/tests/fixtures/ds07/resident/R10-alerts.json";
import { API } from "@/tests/msw/handlers";
import { server } from "@/tests/msw/server";
import { testQueryClient, withQuery } from "@/tests/support/render";
import { AlarmReviewPanel } from "./AlarmReviewPanel";

const ui = configUi as UiConfig;
const meta = ui.meta;
const R09 = r09Alerts.items[0] as ChangeAlarm;
const R10 = r10Alerts.items[0] as ChangeAlarm;

describe("AlarmReviewPanel", () => {
  it.each([
    [R09, "Review alert: changed since Oct 21"],
    [R10, "Review alert: changed since Oct 24"],
  ])("renders the §4.17.5 panel (%#)", (alarm, heading) => {
    withQuery(<AlarmReviewPanel alarm={alarm} reviews={[]} uiConfig={ui} canReview meta={meta} />);
    expect(screen.getByRole("heading", { level: 2, name: heading })).toBeVisible();
    expect(screen.getAllByRole("checkbox")).toHaveLength(5);
    expect(screen.getAllByRole("radio")).toHaveLength(4);
    expect(screen.getByRole("button", { name: "Save review" })).toBeVisible();
    expect(screen.getByRole("button", { name: "Remind me in 24 hours" })).toBeVisible();
    expect(screen.getByRole("heading", { level: 3, name: "Previous reviews" })).toBeVisible();
    expect(screen.getByText("Not reviewed yet.")).toBeVisible();
    expect(
      screen.getByText(
        "Open questions (OQ-05, OQ-26): Does a saved review reset the change score or turn the alarm off? Who may review? How soon must an alarm be reviewed? Pipeline v0.1 keeps alarms on.",
      ),
    ).toBeVisible();
  });

  it("replaces the form for researchers and keeps Previous reviews", () => {
    withQuery(
      <AlarmReviewPanel
        alarm={R09}
        reviews={[
          {
            id: "r1",
            alert_id: R09.id,
            created_at: "2026-10-30T19:00:00Z",
            explanations: [],
            outcome: "referred",
            note: null,
            reviewer: { id: "u", display_name: "Clinician User" },
          },
        ]}
        uiConfig={ui}
        canReview={false}
        meta={meta}
      />,
    );
    expect(screen.getByText("Only clinicians and admins can review alarms.")).toBeVisible();
    expect(screen.queryByRole("checkbox")).toBeNull();
    expect(screen.queryByRole("radio")).toBeNull();
    expect(screen.queryByRole("textbox")).toBeNull();
    expect(screen.queryByRole("button")).toBeNull();
    expect(
      screen.getByText("Oct 30, 2:00 PM CT · Clinician User · Referred to nurse or provider"),
    ).toBeVisible();
  });

  it("renders a history state slot in place of the list", () => {
    withQuery(
      <AlarmReviewPanel
        alarm={R09}
        reviews={[]}
        uiConfig={ui}
        canReview
        meta={meta}
        historyState={<p>Loading previous reviews…</p>}
      />,
    );
    expect(screen.getByText("Loading previous reviews…")).toBeVisible();
    expect(screen.queryByText("Not reviewed yet.")).toBeNull();
  });

  it("invalidates the FE-086 keys after a save and never changes the alarm locally", async () => {
    server.use(
      http.post(`${API}/alerts/:id/reviews`, () =>
        HttpResponse.json(
          {
            id: "rev",
            alert_id: R09.id,
            created_at: "2026-10-30T20:10:00Z",
            explanations: [],
            outcome: "no_concern",
            note: null,
            reviewer: { id: "u", display_name: "Clinician User" },
          },
          { status: 201 },
        ),
      ),
    );
    const client = testQueryClient();
    const invalidate = vi.spyOn(client, "invalidateQueries");
    withQuery(
      <AlarmReviewPanel alarm={R09} reviews={[]} uiConfig={ui} canReview meta={meta} />,
      client,
    );
    await userEvent.click(screen.getByRole("radio", { name: "Checked on resident, no concern" }));
    await userEvent.click(screen.getByRole("button", { name: "Save review" }));
    await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Review saved."));
    const keys = invalidate.mock.calls.map((c) => c[0]?.queryKey);
    expect(keys).toEqual([
      ["alerts"],
      ["data-alerts"],
      ["resident", "R09"],
      ["residents"],
      ["analytics"],
    ]);
    // The panel still shows what the props (the API) say: no review appears until a refetch.
    expect(screen.getByText("Not reviewed yet.")).toBeVisible();
    expect(
      screen.getByRole("heading", { name: "Review alert: changed since Oct 21" }),
    ).toBeVisible();
  });

  describe("reminder line (FE-205)", () => {
    afterEach(() => {
      vi.useRealTimers();
    });

    it("is shown while snoozed_until is in the future and disappears after it, with no request", () => {
      vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout", "Date"] });
      vi.setSystemTime(new Date("2026-10-30T20:00:00Z"));
      const requests: string[] = [];
      const onRequest = ({ request }: { request: Request }) => requests.push(request.url);
      server.events.on("request:start", onRequest);
      const snoozed: ChangeAlarm = {
        ...R10,
        snoozed_until: "2026-10-30T20:01:00Z",
        snoozed_by: "u",
      };
      withQuery(
        <AlarmReviewPanel alarm={snoozed} reviews={[]} uiConfig={ui} canReview meta={meta} />,
      );
      expect(screen.getByText("Reminder set for Oct 30, 3:01 PM CT.")).toBeVisible();
      expect(screen.getByText("Not reviewed yet.")).toBeVisible();
      act(() => {
        vi.advanceTimersByTime(30_000);
      });
      expect(screen.getByText("Reminder set for Oct 30, 3:01 PM CT.")).toBeVisible();
      act(() => {
        vi.advanceTimersByTime(31_000);
      });
      expect(screen.queryByText(/Reminder set for/)).toBeNull();
      expect(screen.getByText("Not reviewed yet.")).toBeVisible();
      expect(requests).toEqual([]);
      server.events.removeListener("request:start", onRequest);
    });

    it("is not shown for a reminder that has passed, also for researchers", () => {
      vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout", "Date"] });
      vi.setSystemTime(new Date("2026-10-30T20:00:00Z"));
      withQuery(
        <AlarmReviewPanel
          alarm={{ ...R10, snoozed_until: "2026-10-30T19:00:00Z" }}
          reviews={[]}
          uiConfig={ui}
          canReview={false}
          meta={meta}
        />,
      );
      expect(screen.queryByText(/Reminder set for/)).toBeNull();
    });

    it("is shown to researchers while active", () => {
      vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout", "Date"] });
      vi.setSystemTime(new Date("2026-10-30T20:00:00Z"));
      withQuery(
        <AlarmReviewPanel
          alarm={{ ...R10, snoozed_until: "2026-10-31T20:00:00Z" }}
          reviews={[]}
          uiConfig={ui}
          canReview={false}
          meta={meta}
        />,
      );
      expect(screen.getByText("Reminder set for Oct 31, 3:00 PM CT.")).toBeVisible();
    });
  });
});
