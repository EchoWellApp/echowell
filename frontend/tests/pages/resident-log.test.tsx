// req: UX-140..UX-150, UX-047, UX-048, UX-202, UX-203, FE-032, FE-087, FE-101, FE-186, FEAT-068-AC-01..05, TRD 11 §4.13.3
import { configure, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import ResidentChartLayout from "@/app/(protected)/residents/[residentCode]/layout";
import ResidentLogPage from "@/app/(protected)/residents/[residentCode]/log/page";
import R09 from "@/tests/fixtures/ds07/resident/R09.json";
import R09checkins from "@/tests/fixtures/ds07/resident/R09-checkins.json";
import { API, problem } from "@/tests/msw/handlers";
import { server } from "@/tests/msw/server";
import { setLocation } from "@/tests/support/navigation";
import { withQuery } from "@/tests/support/render";

function renderLog(code: string) {
  setLocation(`/residents/${code}/log`, "", { residentCode: code });
  return withQuery(
    <ResidentChartLayout>
      <ResidentLogPage />
    </ResidentChartLayout>,
  );
}

const eventsPanel = () => screen.getByRole("heading", { name: "Events" }).parentElement!;
const lines = () =>
  within(eventsPanel())
    .queryAllByRole("listitem")
    .map((li) => `${li.children[0]?.textContent} ${li.children[1]?.textContent}`);
const counts = () =>
  within(screen.getByRole("heading", { name: "Check-ins, last 30 days" }).parentElement!)
    .getAllByRole("listitem")
    .map((li) => li.querySelector("b")?.textContent)
    .join(" / ");

const OK = "30 / 0 / 0 / 0";
const STD = ["Oct 17 Comparing with baseline started.", "Oct 16 Baseline complete (16 of 16)."];

// TRD 11 §4.13.3 "Newest log lines", oldest line and check-in counts with the DS-07 fixtures.
const EXPECTED: Record<string, { counts: string; first: string[]; last: string; more?: string[] }> =
  {
    R09: {
      counts: OK,
      first: ["Oct 21 Alarm on. Change score crossed 5.", ...STD],
      last: "Oct 1 Check-ins started.",
    },
    R10: {
      counts: OK,
      first: ["Oct 24 Alarm on. Change score crossed 5.", ...STD],
      last: "Oct 1 Check-ins started.",
    },
    R08: {
      counts: "13 / 5 / 0 / 12",
      first: [
        "Oct 29 Check-in set aside: speech too short.",
        "Oct 27 Check-in missed.",
        "Oct 25 Check-in set aside: quality flag poor.",
      ],
      last: "Oct 1 Check-ins started.",
    },
    R07: {
      counts: OK,
      first: [
        "Oct 29 Comparing with baseline started.",
        "Oct 28 Baseline complete (16 of 16).",
        "Oct 13 New device D07B. Baseline restarted.",
      ],
      last: "Oct 1 Check-ins started on D07.",
    },
    R05: {
      counts: "28 / 0 / 2 / 0",
      first: [
        "Oct 22 Check-in held back: possible other voice.",
        "Oct 18 Comparing with baseline started.",
        "Oct 17 Baseline complete (16 of 16).",
      ],
      last: "Oct 1 Check-ins started.",
      more: ["Oct 8 Check-in held back: possible other voice."],
    },
    R03: {
      counts: "22 / 7 / 0 / 1",
      first: [
        "Oct 26 Check-in set aside: speech too short.",
        "Oct 24 Comparing with baseline started.",
        "Oct 23 Baseline complete (16 of 16).",
      ],
      last: "Oct 1 Check-ins started.",
      more: [
        "Oct 18 Check-in set aside: quality flag poor; noise above limit.",
        "Oct 12 Shared device D02 silent all day. Check-in missed.",
      ],
    },
    R02: {
      counts: "24 / 0 / 0 / 6",
      first: [
        "Oct 23 Check-in missed.",
        "Oct 22 Comparing with baseline started.",
        "Oct 21 Baseline complete (16 of 16).",
      ],
      last: "Oct 1 Check-ins started.",
      more: ["Oct 12 Shared device D02 silent all day. Check-in missed."],
    },
    R01: { counts: OK, first: STD, last: "Oct 1 Check-ins started." },
    R04: { counts: OK, first: STD, last: "Oct 1 Check-ins started." },
    R06: { counts: OK, first: STD, last: "Oct 1 Check-ins started." },
  };

// Data arrives through MSW; allow for a busy test machine.
beforeAll(() => configure({ asyncUtilTimeout: 4000 }));

describe("resident Check-in log page", () => {
  it.each(Object.keys(EXPECTED))("%s matches TRD 11 §4.13.3", async (code) => {
    const x = EXPECTED[code]!;
    renderLog(code);
    await within(eventsPanel()).findAllByRole("listitem");
    expect(counts()).toBe(x.counts);
    const all = lines();
    expect(all.slice(0, x.first.length)).toEqual(x.first);
    expect(all[all.length - 1]).toBe(x.last);
    for (const m of x.more ?? []) expect(all).toContain(m);
    expect(screen.getByText("Duplicate records are removed quietly and not shown.")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Show earlier entries" })).toBeNull();
    expect(document.title).toBe(`${code} · Check-in log – EchoWell`);
  });

  it("R08 lists 12 missed and 5 set-aside lines (FEAT-068-AC-03)", async () => {
    renderLog("R08");
    await within(eventsPanel()).findAllByRole("listitem");
    expect(lines().filter((l) => l.endsWith("Check-in missed."))).toHaveLength(12);
    expect(lines().filter((l) => l.includes("Check-in set aside:"))).toHaveLength(5);
  });

  it("asks for the last 30 days and loads earlier entries on request (UX-146)", async () => {
    const searches: string[] = [];
    let failNext = true;
    server.use(
      http.get(`${API}/residents/R09`, () =>
        HttpResponse.json({ ...R09, enrolled_on: "2026-08-15" }),
      ),
      http.get(`${API}/residents/R09/checkins`, ({ request }) => {
        const q = new URL(request.url).searchParams;
        searches.push(`${q.get("from")}..${q.get("to")}`);
        if (q.get("to") === "2026-10-30") return HttpResponse.json(R09checkins);
        if (failNext) {
          failNext = false;
          return problem(500, "INTERNAL", "Boom");
        }
        const items =
          q.get("to") === "2026-09-30"
            ? [{ ...R09checkins.items[3], local_date: "2026-09-20", event_type: "missed" }]
            : [];
        return HttpResponse.json({ ...R09checkins, items, total: items.length });
      }),
    );
    renderLog("R09");
    const button = await screen.findByRole("button", { name: "Show earlier entries" });
    expect(searches).toEqual(["2026-10-01..2026-10-30"]);
    await userEvent.click(button);
    expect(
      await screen.findByText(
        "Could not load earlier entries. Check your connection and try again.",
      ),
    ).toBeVisible();
    expect(lines()).toHaveLength(4);
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("Sep 20")).toBeVisible();
    expect(lines()[4]).toBe("Sep 20 Check-in missed.");
    await userEvent.click(await screen.findByRole("button", { name: "Show earlier entries" }));
    await screen.findByText("Duplicate records are removed quietly and not shown.");
    expect(searches).toContain("2026-08-02..2026-08-31");
    await screen.findByText("Sep 20");
    expect(screen.queryByRole("button", { name: "Show earlier entries" })).toBeNull();
  });

  it("keeps the counts when the events fail (UX-202) and shows loading first", async () => {
    server.use(http.get(`${API}/residents/R09/checkins`, () => problem(500, "INTERNAL", "Boom")));
    renderLog("R09");
    expect(screen.getByText("Loading check-in events…")).toBeVisible();
    expect(
      await screen.findByText(
        "Could not load check-in events. Check your connection and try again.",
      ),
    ).toBeVisible();
    expect(counts()).toBe(OK);
  });

  it("shows the counts error when the resident fails", async () => {
    server.use(http.get(`${API}/residents/:code`, () => problem(500, "INTERNAL", "Boom")));
    renderLog("R09");
    expect(
      await screen.findByText(
        "Could not load check-in counts. Check your connection and try again.",
      ),
    ).toBeVisible();
  });
});
