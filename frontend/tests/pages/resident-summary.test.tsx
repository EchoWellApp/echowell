// req: UX-062, UX-063, UX-070..UX-078, UX-065, UX-202, UX-312, UX-200, FE-087, FE-186, FE-193, FE-210, FEAT-066-AC-01..05, TRD 11 §4.13.3
import { configure, screen, within } from "@testing-library/react";
import { http } from "msw";
import ResidentChartLayout from "@/app/(protected)/residents/[residentCode]/layout";
import ResidentSummaryPage from "@/app/(protected)/residents/[residentCode]/page";
import { API, problem } from "@/tests/msw/handlers";
import { server } from "@/tests/msw/server";
import { setLocation } from "@/tests/support/navigation";
import { withQuery } from "@/tests/support/render";

function renderSummary(code: string) {
  setLocation(`/residents/${code}`, "", { residentCode: code });
  return withQuery(
    <ResidentChartLayout>
      <ResidentSummaryPage />
    </ResidentChartLayout>,
  );
}

const bannerFacts = () =>
  Array.from(screen.getByRole("region", { name: "Resident" }).querySelectorAll("dd")).map(
    (d) => d.textContent,
  );
const tileValues = () =>
  Array.from(
    within(screen.getByRole("heading", { name: "More detail" }).parentElement!).getAllByRole(
      "link",
    ),
  ).map((a) => a.children[1]?.textContent);
const facts = () =>
  Array.from(
    screen.getByRole("heading", { name: "Right now" }).parentElement!.querySelectorAll("b"),
  ).map((b) => b.textContent);

// TRD 11 §4.13.3 (banner, Summary lead, tiles) with the DS-07 fixtures.
const EXPECTED: Record<
  string,
  {
    banner: string[];
    pill: string;
    lead: string;
    tiles: string[];
    facts?: string[];
    leaning?: string;
  }
> = {
  R09: {
    banner: ["D09", "Oct 30, 2:28 PM CT", "30 of 30", "Complete"],
    pill: "▲Changed",
    lead: "R09’s voice has moved away from their own usual pattern, steadily and long enough to set off the alarm on Oct 21. It is still changed.",
    facts: ["Oct 21", "9 days", "Not reviewed"],
    leaning: "Leaning most: more pauses, quieter, less voiced sound",
    tiles: ["Change score 26.8", "16 of 16 check-ins", "30 used, 0 missed", "D09 online"],
  },
  R10: {
    banner: ["D10", "Oct 30, 2:39 PM CT", "30 of 30", "Complete"],
    pill: "▲Changed",
    lead: "R10’s voice has moved away from their own usual pattern, steadily and long enough to set off the alarm on Oct 24. It is still changed.",
    facts: ["Oct 24", "6 days", "Not reviewed"],
    leaning: "Leaning most: more pauses, slower while talking, fewer syllables per second",
    tiles: ["Change score 13.4", "16 of 16 check-ins", "30 used, 0 missed", "D10 online"],
  },
  R08: {
    banner: ["D08", "Oct 30, 2:28 PM CT", "13 of 30", "13 of 16"],
    pill: "!Needs attention",
    lead: "Missing many check-ins. Baseline stuck at 13 of 16. EchoWell can’t judge their voice well until more good check-ins come in.",
    tiles: ["Not scored yet", "13 of 16 check-ins", "13 used, 12 missed", "D08 online"],
  },
  R03: {
    banner: ["D02 (shared with R02)", "Oct 30, 2:19 PM CT", "22 of 30", "Complete"],
    pill: "!Needs attention",
    lead: "7 check-ins too noisy or too short to use. EchoWell can’t judge their voice well until more good check-ins come in.",
    tiles: ["No change", "16 of 16 check-ins", "22 used, 1 missed", "D02 online"],
  },
  R07: {
    banner: ["D07B (replaced D07)", "Oct 30, 2:52 PM CT", "30 of 30", "Complete"],
    pill: "●Usual",
    lead: "R07’s voice is within their own usual range. Nothing to do. The baseline restarted on Oct 13 because the device changed (D07B, was D07); R07 is now compared only with the new baseline.",
    tiles: ["No change", "16 of 16 check-ins", "30 used, 0 missed", "D07B online"],
  },
  R05: {
    banner: ["D05", "Oct 30, 2:40 PM CT", "28 of 30", "Complete"],
    pill: "●Usual",
    lead: "R05’s voice is within their own usual range. Nothing to do.",
    tiles: ["No change", "16 of 16 check-ins", "28 used, 0 missed", "D05 online"],
  },
  R02: {
    banner: ["D02 (shared with R03)", "Oct 30, 2:55 PM CT", "24 of 30", "Complete"],
    pill: "●Usual",
    lead: "R02’s voice is within their own usual range. Nothing to do.",
    tiles: ["No change", "16 of 16 check-ins", "24 used, 6 missed", "D02 online"],
  },
};

// Data arrives through MSW; allow for a busy test machine.
beforeAll(() => configure({ asyncUtilTimeout: 4000 }));

describe("resident Summary page", () => {
  it.each(Object.keys(EXPECTED))("%s matches TRD 11 §4.13.3", async (code) => {
    const x = EXPECTED[code]!;
    renderSummary(code);
    expect(await screen.findByText(x.lead)).toBeVisible();
    expect(bannerFacts()).toEqual(x.banner);
    expect(screen.getByRole("region", { name: "Resident" })).toHaveTextContent(x.pill);
    await screen.findByText(x.tiles[3]!);
    await screen.findByText(x.tiles[0]!);
    expect(tileValues()).toEqual(x.tiles);
    if (x.facts) {
      expect(await screen.findByText(x.leaning!)).toBeVisible();
      expect(facts()).toEqual(x.facts);
      expect(screen.getByRole("link", { name: "Review this alert" })).toHaveAttribute(
        "href",
        `/residents/${code}/review`,
      );
      expect(screen.getByRole("link", { name: "See what changed" })).toBeVisible();
    } else {
      expect(screen.queryByText(/Leaning most/)).toBeNull();
    }
    expect(
      screen.getByText(
        `This compares ${code} only with ${code}. It is a prompt to check in, not a diagnosis. [Final clinical wording: confirm with PI]`,
      ),
    ).toBeVisible();
    expect(document.title).toBe(`${code} · Summary – EchoWell`);
  });

  it("R08 shows the Needs-attention buttons and no error", async () => {
    renderSummary("R08");
    expect(
      await screen.findByRole("link", { name: "See missed and set-aside check-ins" }),
    ).toHaveAttribute("href", "/residents/R08/log");
    expect(screen.getByRole("link", { name: "Check the device" })).toHaveAttribute(
      "href",
      "/residents/R08/device",
    );
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("shows the loading state first (UX-200)", async () => {
    renderSummary("R09");
    expect(screen.getByText("Loading summary…")).toHaveAttribute("role", "status");
    await screen.findByText(EXPECTED.R09!.lead);
  });

  it("keeps the lead and tiles when the alarm and devices fail (UX-202, FE-087)", async () => {
    server.use(
      http.get(`${API}/alerts`, () => problem(500, "INTERNAL", "Boom")),
      http.get(`${API}/devices`, () => problem(500, "INTERNAL", "Boom")),
      http.get(`${API}/scores`, () => problem(500, "INTERNAL", "Boom")),
    );
    renderSummary("R09");
    expect(
      await screen.findByText("Could not load alarm details. Check your connection and try again."),
    ).toBeVisible();
    expect(screen.getByText(EXPECTED.R09!.lead)).toBeVisible();
    expect(tileValues()).toEqual([
      "Change score 26.8",
      "16 of 16 check-ins",
      "30 used, 0 missed",
      "—",
    ]);
  });

  it("shows an error in the Right now panel when the resident fails", async () => {
    server.use(http.get(`${API}/residents/:code`, () => problem(500, "INTERNAL", "Boom")));
    renderSummary("R09");
    expect(
      await screen.findByText("Could not load summary. Check your connection and try again."),
    ).toBeVisible();
  });
});
