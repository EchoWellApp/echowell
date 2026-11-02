// req: UX-420, UX-421, UX-422, UX-423, UX-065, UX-066, UX-202, UX-203, FE-032, FE-087, FE-186, FEAT-068-AC-06, FEAT-068-AC-07, TRD 11 §4.13.3
import { configure, screen } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import ResidentChartLayout from "@/app/(protected)/residents/[residentCode]/layout";
import ResidentBaselinePage from "@/app/(protected)/residents/[residentCode]/baseline/page";
import R01 from "@/tests/fixtures/ds07/resident/R01.json";
import R01checkins from "@/tests/fixtures/ds07/resident/R01-checkins.json";
import { API, problem } from "@/tests/msw/handlers";
import { server } from "@/tests/msw/server";
import { setLocation } from "@/tests/support/navigation";
import { withQuery } from "@/tests/support/render";

function renderBaseline(code: string) {
  setLocation(`/residents/${code}/baseline`, "", { residentCode: code });
  return withQuery(
    <ResidentChartLayout>
      <ResidentBaselinePage />
    </ResidentChartLayout>,
  );
}

const frozen = (range: string, since: string) =>
  `First 16 usable check-ins, ${range}, then frozen. Compared with it since ${since}.`;

// TRD 11 §4.13.3 "Baseline section text" with the DS-07 fixtures.
const EXPECTED: Record<string, { text: string; n: number }> = {
  R09: { text: frozen("Oct 1–16", "Oct 17"), n: 16 },
  R10: { text: frozen("Oct 1–16", "Oct 17"), n: 16 },
  R08: {
    text: "Still forming: 13 of 16 usable check-ins so far. 12 missed and 5 set-aside check-ins in the last 30 days have slowed it down.",
    n: 13,
  },
  R07: {
    text: `Restarted Oct 13 when the device was replaced (D07 to D07B), so readings from the old device are not mixed in. ${frozen("Oct 13–28", "Oct 29")}`,
    n: 16,
  },
  R05: { text: frozen("Oct 1–17", "Oct 18"), n: 16 },
  R03: { text: frozen("Oct 1–23", "Oct 24"), n: 16 },
  R02: { text: frozen("Oct 1–21", "Oct 22"), n: 16 },
  R01: { text: frozen("Oct 1–16", "Oct 17"), n: 16 },
  R04: { text: frozen("Oct 1–16", "Oct 17"), n: 16 },
  R06: { text: frozen("Oct 1–16", "Oct 17"), n: 16 },
};

// Data arrives through MSW; allow for a busy test machine.
beforeAll(() => configure({ asyncUtilTimeout: 4000 }));

describe("resident Baseline page", () => {
  it.each(Object.keys(EXPECTED))("%s matches TRD 11 §4.13.3", async (code) => {
    const x = EXPECTED[code]!;
    renderBaseline(code);
    expect(await screen.findByText(x.text)).toBeVisible();
    expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent(
      `Baseline: ${code}’s usual`,
    );
    const meter = screen.getByRole("progressbar", { name: `${x.n} of 16 usable check-ins` });
    expect(meter).toHaveAttribute("value", String(x.n));
    expect(meter).toHaveAttribute("max", "16");
    expect(
      screen.getByText(
        "The baseline is built from the first 16 usable check-ins, then frozen so slow changes still show up. It restarts if the resident gets a new device or the device or extraction software changes.",
      ),
    ).toBeVisible();
    expect(document.title).toBe(`${code} · Baseline – EchoWell`);
  });

  it("asks for the current epoch's events only", async () => {
    const urls: string[] = [];
    server.use(
      http.get(`${API}/residents/R07/checkins`, ({ request }) => {
        urls.push(new URL(request.url).search);
        return problem(500, "INTERNAL", "Boom");
      }),
    );
    renderBaseline("R07");
    expect(
      await screen.findByText("Could not load baseline. Check your connection and try again."),
    ).toBeVisible();
    expect(urls[0]).toBe("?from=2026-10-13&to=2026-10-30&limit=500&offset=0");
  });

  it("says comparing starts next when no check-in was scored yet", async () => {
    server.use(
      http.get(`${API}/residents/R01/checkins`, () =>
        HttpResponse.json({
          ...R01checkins,
          items: R01checkins.items.filter((e) => e.event_type !== "watching_started"),
        }),
      ),
    );
    renderBaseline("R01");
    expect(
      await screen.findByText(
        "First 16 usable check-ins, Oct 1–16, then frozen. Comparing starts with the next usable check-in.",
      ),
    ).toBeVisible();
    expect(R01.baseline.state).toBe("frozen");
  });

  it("shows loading, then the resident error in the panel", async () => {
    server.use(http.get(`${API}/residents/:code`, () => problem(500, "INTERNAL", "Boom")));
    renderBaseline("R09");
    expect(screen.getByText("Loading baseline…")).toBeVisible();
    expect(
      await screen.findByText("Could not load baseline. Check your connection and try again."),
    ).toBeVisible();
  });
});
