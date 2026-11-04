// req: FE-026, FE-037, FE-102, FE-194, FE-195, UX-017, UX-050..UX-058, UX-263, UX-306..UX-309, UX-331, UX-350..UX-384, FEAT-072-AC-01..AC-08
import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import StudyTeamPage from "@/app/(protected)/study/page";
import analyticsFixture from "@/tests/fixtures/ds07/analytics.json";
import { API, problem } from "@/tests/msw/handlers";
import { server } from "@/tests/msw/server";
import { setLocation } from "@/tests/support/navigation";
import { renderSignedIn } from "@/tests/support/render";

const STUDY_PATHS = ["/analytics", "/data-alerts", "/devices", "/scores"];

function spyRequests(): string[] {
  const urls: string[] = [];
  server.events.on("request:start", ({ request }) => {
    urls.push(new URL(request.url).pathname.replace("/api/v1", ""));
  });
  return urls;
}

async function renderStudy(role: "researcher" | "admin" | "clinician" = "researcher") {
  setLocation("/study");
  const r = renderSignedIn(<StudyTeamPage />, role);
  if (role !== "clinician") {
    const wait = { timeout: 5000 };
    await screen.findByRole("heading", { level: 2, name: "Check-ins per day" }, wait);
    await screen.findAllByTestId("device-row", {}, wait);
    await screen.findAllByTestId("data-problem", {}, wait);
  }
  return r;
}

const rowTexts = (testId: string) => screen.getAllByTestId(testId).map((el) => el.textContent);

afterEach(() => {
  server.events.removeAllListeners();
  window.history.replaceState(null, "", "/");
});

describe("Study team page (test profile, DS-07)", () => {
  it("shows the header lines and sets the document title (UX-010, UX-017, UX-229, UX-350)", async () => {
    await renderStudy();
    expect(
      screen.getByRole("heading", { level: 1, name: "Study team: how the system is working" }),
    ).toBeVisible();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByText("Counts only. No audio, no names.")).toBeVisible();
    expect(screen.getByTestId("period-line")).toHaveTextContent(
      /^pipeline test data v0\.1, Oct 1–30, 2026 · numbers match the pipeline answer key$/,
    );
    expect(document.title).toBe("Study team – EchoWell");
  });

  it("renders the KPI tiles of §4.18.8 in order (UX-351..UX-355, UX-380)", async () => {
    await renderStudy();
    const tiles = screen
      .getAllByTestId("kpi-tile")
      .map((t) => Array.from(t.children).map((c) => c.textContent));
    expect(tiles).toEqual([
      ["Check-ins received", "94%", "281 of 300 expected"],
      ["Used for scoring", "89%", "267 of 300 expected"],
      ["Baselines formed", "9 of 10", "R08 still forming; R07 restarted once"],
      ["Alarms raised", "2", "R09, R10; neither reviewed yet"],
    ]);
  });

  it("lists exactly the four data problems in order with tags and links (UX-306..UX-308, UX-331)", async () => {
    await renderStudy();
    expect(rowTexts("data-problem")).toEqual([
      "Staff can helpR08: baseline stuck at 13 of 16. 12 missed and 5 set aside in 30 days.",
      "Staff can helpR03: 7 of 29 received check-ins set aside (noise, quality flag, too short).",
      "Study teamR05: 2 check-ins held back as possible other voice (Oct 8, Oct 22).",
      "Study teamD02: silent all day Oct 12. Affected R02 and R03.",
    ]);
    expect(screen.getByRole("link", { name: "R08 · baseline stuck at 13 of 16" })).toHaveAttribute(
      "href",
      "/residents/R08/log",
    );
    expect(screen.getByRole("link", { name: "D02 · device silent all day" })).toHaveAttribute(
      "href",
      "/study#devices",
    );
    const panel = screen.getByRole("region", { name: "Data problems to follow up" });
    expect(panel.textContent).not.toContain("▲");
  });

  it("renders the daily chart name, x labels and table alternative (UX-356..UX-360, UX-381)", async () => {
    const user = userEvent.setup();
    await renderStudy();
    expect(
      screen.getByRole("region", {
        name: "Check-ins per day, Oct 1–30: 267 used, 12 set aside, 2 held back, 19 missed.",
      }),
    ).toHaveAttribute("tabindex", "0");
    const titles = Array.from(document.querySelectorAll("[data-testid='day-segment'] title")).map(
      (t) => t.textContent,
    );
    expect(titles).toContain("Oct 8: 8 used, 0 set aside, 1 held back, 1 missed");
    expect(titles).toContain("Oct 22: 8 used, 1 set aside, 1 held back, 0 missed");
    expect(screen.getAllByTestId("x-label").map((t) => t.textContent)).toEqual([
      "Oct 1",
      "Oct 12: D02 silent",
      "Oct 30",
    ]);
    const legend = screen.getByRole("list", { name: "Legend" });
    expect(
      within(legend)
        .getAllByRole("listitem")
        .map((l) => l.textContent),
    ).toEqual(["Used", "Set aside", "Held back (other voice)", "Missed"]);
    await user.click(screen.getByText("Show daily counts as a table"));
    const table = screen.getAllByRole("table")[0]!;
    const cols = within(table)
      .getAllByRole("columnheader")
      .map((c) => c.textContent);
    expect(cols).toEqual(["Date", "Used", "Set aside", "Held back", "Missed", "Note"]);
    const row = (d: string) =>
      within(within(table).getByRole("rowheader", { name: d }).closest("tr")!)
        .getAllByRole("cell")
        .map((c) => c.textContent);
    expect(row("Oct 1")).toEqual(["10", "0", "0", "0", ""]);
    expect(row("Oct 8")).toEqual(["8", "0", "1", "1", ""]);
    expect(row("Oct 12")).toEqual(["8", "0", "0", "2", "D02 silent"]);
    expect(row("Oct 22")).toEqual(["8", "1", "1", "0", ""]);
    expect(within(table).getAllByRole("row")).toHaveLength(31);
  });

  it("renders the funnel of §4.18.8 (UX-362..UX-366, UX-382)", async () => {
    await renderStudy();
    const rows = screen.getAllByTestId("funnel-row");
    expect(rows.map((r) => r.textContent)).toEqual([
      "Expected30010 residents × 30 days",
      "Received28119 missed; 2 duplicate copies removed",
      "Passed quality checks26912 set aside: quality flag 5, noise 5, too short 3 (1 had two reasons)",
      "Same speaker, used2672 held back as possible other voice",
    ]);
    const widths = rows.map((r) => parseFloat((r.querySelector("i") as HTMLElement).style.width));
    expect(widths).toEqual([100, 93.7, 89.7, 89]);
  });

  it("renders the by-resident rows lowest first (UX-367..UX-370, UX-383)", async () => {
    await renderStudy();
    expect(screen.getByText("Share of 30 days, lowest first")).toBeVisible();
    expect(rowTexts("by-resident-row")).toEqual([
      "R0843%",
      "R0373%",
      "R0280%",
      "R0593%",
      "R01100%",
      "R04100%",
      "R06100%",
      "R07100%",
      "R09100%",
      "R10100%",
    ]);
    expect(
      screen.getByRole("group", {
        name: "R08: 13 of 30 days usable (43%); 5 set aside; 0 held back; 12 missed.",
      }),
    ).toBeVisible();
    expect(screen.getByRole("link", { name: "R05" })).toHaveAttribute("href", "/residents/R05/log");
  });

  it("renders the alarm timing table and no review outcomes (UX-371..UX-374, UX-384)", async () => {
    await renderStudy();
    const panel = screen.getByRole("region", { name: "Alarm timing check" });
    expect(
      within(panel).getByText("Test data only, where the true change date is known."),
    ).toBeVisible();
    const rows = within(panel)
      .getAllByRole("row")
      .map((r) => Array.from(r.children).map((c) => c.textContent));
    expect(rows).toEqual([
      ["Resident", "Planted change", "Change began", "Alarm rang", "Delay"],
      ["R09", "Sudden step", "Oct 21", "Oct 21", "0 days"],
      ["R10", "Slow drift", "Oct 17", "Oct 24", "7 days"],
      ["Other 8", "None", "None", "No alarm", "Correct"],
    ]);
    expect(
      within(panel).getByText(
        "With real residents the true change date is unknown, so this panel becomes: alarms raised, alarms reviewed, and review outcomes.",
      ),
    ).toBeVisible();
    expect(screen.queryByText("Alarms and review outcomes")).toBeNull();
  });

  it("renders the Devices rows and all-devices table of §4.13.4 (UX-050..UX-058, UX-263)", async () => {
    const user = userEvent.setup();
    await renderStudy();
    expect(rowTexts("device-row")).toEqual([
      "● OnlineD01, D04 to D06, D08 to D10: all uploaded Oct 30. Firmware fw-1.0.0.",
      "● OnlineD02 (shared by R02 and R03): last upload Oct 30, 2:55 PM CT. Silent all day Oct 12.",
      "● OnlineD07B (R07): in use since Oct 13, replacing D07. Last upload Oct 30, 2:52 PM CT.",
    ]);
    await user.click(screen.getByText("Show all devices (10)"));
    const table = screen.getByRole("region", { name: "Show all devices (10)" });
    const rows = within(table)
      .getAllByRole("row")
      .map((r) => Array.from(r.children).map((c) => c.textContent));
    expect(rows[0]).toEqual([
      "Device",
      "Residents",
      "In use",
      "Last upload",
      "Firmware",
      "Days with no device activity (last 30 days)",
      "Silent days (shared device)",
    ]);
    const byCode = Object.fromEntries(rows.slice(1).map((r) => [r[0], r.slice(1)]));
    expect(rows.slice(1).map((r) => r[0])).toEqual([
      "D01",
      "D02",
      "D04",
      "D05",
      "D06",
      "D07",
      "D07B",
      "D08",
      "D09",
      "D10",
    ]);
    expect(byCode.D02).toEqual([
      "R02, R03",
      "Since Oct 1",
      "Oct 30, 2:55 PM CT",
      "fw-1.0.0",
      "1 (Oct 12)",
      "1 (Oct 12)",
    ]);
    expect(byCode.D07).toEqual([
      "R07",
      "Oct 1–12 · replaced by D07B",
      "Oct 12, 2:14 PM CT",
      "fw-1.0.0",
      "0",
      "0",
    ]);
    expect(byCode.D07B?.slice(0, 2)).toEqual(["R07", "Since Oct 13"]);
    expect(byCode.D08?.[4]).toMatch(/^12 /);
    expect(byCode.D08?.[5]).toBe("0");
    for (const c of ["D01", "D04", "D05", "D06", "D09", "D10"]) {
      expect(byCode[c]?.slice(3)).toEqual(["fw-1.0.0", "0", "0"]);
    }
  });

  it("orders the page panels as in SRC-21 and offers downloads", async () => {
    await renderStudy();
    expect(screen.getAllByRole("heading", { level: 2 }).map((h) => h.textContent)).toEqual([
      "Data problems to follow up",
      "Check-ins per day",
      "Where check-ins are lost",
      "Usable check-ins by resident",
      "Alarm timing check",
      "Devices",
      "Downloads",
    ]);
    expect(document.getElementById("devices")).toContainElement(
      screen.getByRole("heading", { name: "Devices" }),
    );
  });
});

describe("Study team page: profiles, roles, states", () => {
  it("production profile: review outcomes replace the timing table, no answer-key clause (FE-195)", async () => {
    const meta = { ...analyticsFixture.meta, pipeline_profile: "production" };
    server.use(
      http.get(`${API}/analytics`, () =>
        HttpResponse.json({
          ...analyticsFixture,
          meta,
          alarm_timing: null,
          review_outcomes: {
            alarms_raised: 3,
            reviewed: 2,
            by_outcome: { no_concern: 1, known_cause: 0, referred: 1, data_problem: 0 },
          },
        }),
      ),
    );
    await renderStudy();
    expect(screen.getByTestId("period-line")).toHaveTextContent(
      /^pipeline test data v0\.1, Oct 1–30, 2026$/,
    );
    expect(screen.queryByText(/numbers match the pipeline answer key/)).toBeNull();
    expect(screen.queryByRole("heading", { name: "Alarm timing check" })).toBeNull();
    const panel = screen.getByRole("region", { name: "Alarms and review outcomes" });
    const rows = within(panel)
      .getAllByRole("row")
      .map((r) => Array.from(r.children).map((c) => c.textContent));
    expect(rows).toEqual([
      ["Measure", "Count"],
      ["Alarms raised", "3"],
      ["Reviewed", "2"],
      ["Checked on resident, no concern", "1"],
      ["Explained by a known cause", "0"],
      ["Referred to nurse or provider", "1"],
      ["Looks like a data problem: send to study team", "0"],
    ]);
  });

  it("clinician: access denied and no Study team request (FE-037, UX-350)", async () => {
    const urls = spyRequests();
    await renderStudy("clinician");
    expect(
      await screen.findByRole("heading", {
        level: 1,
        name: "You do not have access to this page.",
      }),
    ).toBeVisible();
    expect(screen.getByRole("link", { name: "← Resident list" })).toHaveAttribute(
      "href",
      "/residents",
    );
    await act(() => new Promise((r) => setTimeout(r, 50)));
    expect(urls).toContain("/auth/me");
    expect(urls.filter((u) => STUDY_PATHS.some((p) => u.startsWith(p)))).toEqual([]);
  });

  it("admin sees the page and the study reads are made", async () => {
    const urls = spyRequests();
    await renderStudy("admin");
    expect(urls).toEqual(expect.arrayContaining(["/analytics", "/data-alerts", "/devices"]));
  });

  it("/study#devices scrolls to the Devices section and focuses its heading (FE-026)", async () => {
    const scroll = vi.fn();
    Element.prototype.scrollIntoView = scroll;
    window.history.replaceState(null, "", "/study#devices");
    await renderStudy();
    const heading = screen.getByRole("heading", { level: 2, name: "Devices" });
    await waitFor(() => expect(heading).toHaveFocus());
    expect(scroll).toHaveBeenCalled();
    // A later hash change (device data-problem link) also focuses it.
    heading.blur();
    window.history.replaceState(null, "", "/study#devices");
    window.dispatchEvent(new HashChangeEvent("hashchange"));
    expect(heading).toHaveFocus();
  });

  it("shows loading states, then 'No data problems' when the list is empty (UX-200, UX-309)", async () => {
    server.use(
      http.get(`${API}/data-alerts`, () =>
        HttpResponse.json({
          meta: analyticsFixture.meta,
          items: [],
          total: 0,
          limit: 50,
          offset: 0,
        }),
      ),
    );
    setLocation("/study");
    renderSignedIn(<StudyTeamPage />, "researcher");
    expect(await screen.findByText("Loading study team counts…")).toBeVisible();
    expect(screen.getAllByTestId("kpi-tile").map((t) => t.textContent)).toEqual([
      "Check-ins received—",
      "Used for scoring—",
      "Baselines formed—",
      "Alarms raised—",
    ]);
    expect(await screen.findByText("No data problems in the last 30 days.")).toBeVisible();
  });

  it("shows 'No pipeline run yet.' without a succeeded run", async () => {
    server.use(
      http.get(`${API}/analytics`, () =>
        HttpResponse.json({ ...analyticsFixture, pipeline_run: null }),
      ),
    );
    setLocation("/study");
    renderSignedIn(<StudyTeamPage />, "researcher");
    expect(await screen.findByText("No pipeline run yet.")).toBeVisible();
    expect(screen.queryByTestId("kpi-tile")).toBeNull();
    expect(screen.queryByRole("heading", { name: "Check-ins per day" })).toBeNull();
    expect(await screen.findAllByTestId("device-row")).toHaveLength(3);
  });

  it("panels fail independently with retry and reference (UX-202, UX-203)", async () => {
    server.use(
      http.get(`${API}/analytics`, () => problem(500, "INTERNAL", "Internal error")),
      http.get(`${API}/devices`, () => problem(500, "INTERNAL", "Internal error")),
      http.get(`${API}/data-alerts`, () => problem(500, "INTERNAL", "Internal error")),
    );
    setLocation("/study");
    renderSignedIn(<StudyTeamPage />, "researcher");
    expect(
      await screen.findByText(
        "Could not load study team counts. Check your connection and try again.",
      ),
    ).toBeVisible();
    expect(
      await screen.findByText("Could not load devices. Check your connection and try again."),
    ).toBeVisible();
    expect(
      await screen.findByText(
        "Could not load data problems to follow up. Check your connection and try again.",
      ),
    ).toBeVisible();
    expect(screen.getAllByText("Reference: req-test-0001")).toHaveLength(3);
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      "Study team: how the system is working",
    );
    // The period line still comes from /config/ui meta.
    expect(await screen.findByTestId("period-line")).toHaveTextContent(
      "pipeline test data v0.1, Oct 1–30, 2026",
    );
    server.resetHandlers();
    const user = userEvent.setup();
    const retry = screen.getAllByRole("button", { name: "Try again" });
    for (const b of retry) await user.click(b);
    expect(await screen.findAllByTestId("device-row")).toHaveLength(3);
    expect(await screen.findAllByTestId("kpi-tile")).toHaveLength(4);
  });

  it("devices empty state (UX-204)", async () => {
    server.use(
      http.get(`${API}/devices`, () =>
        HttpResponse.json({
          meta: analyticsFixture.meta,
          items: [],
          total: 0,
          limit: 500,
          offset: 0,
        }),
      ),
    );
    setLocation("/study");
    renderSignedIn(<StudyTeamPage />, "researcher");
    expect(await screen.findByText("No devices are registered yet.")).toBeVisible();
  });
});

describe("Study team downloads (UX-377)", () => {
  const created: Blob[] = [];
  beforeEach(() => {
    created.length = 0;
    URL.createObjectURL = vi.fn((b: Blob) => {
      created.push(b);
      return "blob:test";
    });
    URL.revokeObjectURL = vi.fn();
  });

  it.each([
    ["Scores (CSV)", "/scores", "echowell_scores_2026-10-30.csv"],
    ["Baselines (CSV)", "/analytics/baselines", "echowell_baselines_2026-10-30.csv"],
  ])("%s downloads the CSV export", async (label, path, filename) => {
    let accept: string | null = null;
    server.use(
      http.get(`${API}${path}`, ({ request }) => {
        accept = request.headers.get("accept");
        return new HttpResponse("a,b\n1,2\n", { headers: { "Content-Type": "text/csv" } });
      }),
    );
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (
      this: HTMLAnchorElement,
    ) {
      expect(this.download).toBe(filename);
      expect(this.getAttribute("href")).toBe("blob:test");
    });
    const user = userEvent.setup();
    await renderStudy();
    await user.click(screen.getByRole("button", { name: label }));
    await waitFor(() => expect(click).toHaveBeenCalledTimes(1));
    expect(accept).toBe("text/csv");
    expect(await created[0]!.text()).toBe("a,b\n1,2\n");
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:test");
    click.mockRestore();
  });

  it("shows an error with reference when a download fails", async () => {
    server.use(
      http.get(`${API}/analytics/baselines`, () => problem(413, "EXPORT_TOO_LARGE", "Too large")),
    );
    const user = userEvent.setup();
    await renderStudy();
    await user.click(screen.getByRole("button", { name: "Baselines (CSV)" }));
    expect(
      await screen.findByText(
        "Could not download Baselines (CSV). Check your connection and try again.",
      ),
    ).toBeVisible();
    expect(screen.getByText("Reference: req-test-0001")).toBeVisible();
    expect(screen.getByRole("button", { name: "Baselines (CSV)" })).toBeEnabled();
  });
});
