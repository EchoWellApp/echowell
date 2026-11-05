// req: FEAT-065, FE-032, FE-076, FE-081, FE-082, FE-083, FE-084, FE-025, FE-035, FE-056, UX-041,
// UX-044, UX-045, UX-200, UX-201, UX-202, UX-203, UX-204, UX-206, UX-260, UX-261, UX-401..UX-408
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import ResidentsPage from "@/app/(protected)/residents/page";
import { SHOW_KEY } from "@/components/BackLink/BackLink";
import residents from "@/tests/fixtures/ds07/residents.json";
import { API, problem } from "@/tests/msw/handlers";
import { server } from "@/tests/msw/server";
import { nav, setLocation } from "@/tests/support/navigation";
import { renderSignedIn } from "@/tests/support/render";
import { queryKeys } from "@/lib/queryKeys";

const ALL = ["R09", "R10", "R03", "R08", "R01", "R02", "R04", "R05", "R06", "R07"];

/** Counts GET /residents requests while still serving the fixture. */
function countResidentRequests() {
  const calls: string[] = [];
  server.use(
    http.get(`${API}/residents`, ({ request }) => {
      calls.push(request.url);
      return HttpResponse.json(residents);
    }),
  );
  return calls;
}

function shownCodes(): string[] {
  const [, body] = screen.getAllByRole("rowgroup");
  return within(body!)
    .getAllByRole("row")
    .map((r) => within(r).getAllByRole("cell")[1]!.textContent ?? "");
}

function filterTexts(): string[] {
  return within(screen.getByRole("group", { name: "Show" }))
    .getAllByRole("button")
    .map((b) => b.textContent ?? "");
}

describe("/residents page", () => {
  beforeEach(() => {
    setLocation("/residents");
    nav.router.replace.mockClear();
    nav.router.push.mockClear();
  });

  it("loads, then shows filters, the ten rows, the legend and the note (UX-260)", async () => {
    const calls = countResidentRequests();
    renderSignedIn(<ResidentsPage />, "clinician");
    expect(screen.getByRole("heading", { level: 1, name: "Residents in the study" })).toBeVisible();
    expect(screen.getByText("Loading residents…")).toHaveAttribute("role", "status");
    expect(filterTexts()).toEqual(["All (—)", "Changed (—)", "Needs attention (—)", "Usual (—)"]);
    expect(await screen.findByRole("link", { name: "Open chart for R09" })).toBeVisible();
    expect(document.title).toBe("Resident list – EchoWell");
    expect(filterTexts()).toEqual(["All (10)", "Changed (2)", "Needs attention (2)", "Usual (6)"]);
    expect(screen.getByRole("button", { name: "All (10)" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(shownCodes()).toEqual(ALL);
    expect(screen.getByRole("list", { name: "Status meanings" })).toHaveTextContent(
      "Still collecting the first 16 check-ins to learn their usual.",
    );
    expect(
      screen.getByText(
        "A status is a prompt to check on someone, not a diagnosis. [Final clinical wording: confirm with PI]",
      ),
    ).toBeVisible();
    expect(screen.queryByText(/Showing \d+ of/)).toBeNull();
    // FE-076, FE-084: one request with the default list parameters.
    const url = new URL(calls[0]!);
    expect(url.searchParams.get("sort")).toBe("alarm");
    expect(url.searchParams.get("cohort")).toBe("longitudinal");
    expect(url.searchParams.get("include_withdrawn")).toBe("false");
    expect(url.searchParams.get("limit")).toBe("500");
    expect(url.searchParams.get("offset")).toBe("0");
    // AC-06: R04's duplicates never show; one R04 row and the usual count stays 6.
    expect(screen.getAllByRole("link", { name: "Open chart for R04" })).toHaveLength(1);
  });

  it("filters in the browser, writes ?show= with replace and makes no request (FE-082)", async () => {
    const calls = countResidentRequests();
    const view = renderSignedIn(<ResidentsPage />, "clinician");
    await screen.findByRole("link", { name: "Open chart for R09" });
    const before = calls.length;
    const button = screen.getByRole("button", { name: "Needs attention (2)" });
    await userEvent.click(button);
    expect(nav.router.replace).toHaveBeenCalledWith("/residents?show=needs_attention", {
      scroll: false,
    });
    expect(window.sessionStorage.getItem(SHOW_KEY)).toBe("needs_attention");
    expect(screen.getByTestId("filter-live")).toHaveTextContent(
      "Showing needs attention residents",
    );
    // The URL change re-renders the page with the new filter.
    setLocation("/residents", "?show=needs_attention");
    view.rerender(<ResidentsPage />);
    expect(shownCodes()).toEqual(["R03", "R08"]);
    expect(button).toHaveFocus();
    expect(button).toHaveAttribute("aria-pressed", "true");
    expect(filterTexts()).toEqual(["All (10)", "Changed (2)", "Needs attention (2)", "Usual (6)"]);
    expect(calls.length).toBe(before);
  });

  it.each([
    ["?show=changed", ["R09", "R10"], "Changed (2)"],
    ["?show=needs_attention", ["R03", "R08"], "Needs attention (2)"],
    ["?show=usual", ["R01", "R02", "R04", "R05", "R06", "R07"], "Usual (6)"],
    ["?show=all", ALL, "All (10)"],
    ["?show=bogus", ALL, "All (10)"],
  ])("%s on load shows the rows of TRD 11 §4.13.2 (UX-404)", async (search, codes, pressed) => {
    setLocation("/residents", search);
    renderSignedIn(<ResidentsPage />, "clinician");
    await waitFor(() => expect(shownCodes()).toEqual(codes));
    expect(screen.getByRole("button", { name: pressed })).toHaveAttribute("aria-pressed", "true");
    const stored = search === "?show=bogus" ? "all" : search.slice(6);
    expect(window.sessionStorage.getItem(SHOW_KEY)).toBe(stored);
  });

  it("opens the chart on row click (UX-040, AC-05)", async () => {
    renderSignedIn(<ResidentsPage />, "clinician");
    await userEvent.click(
      await screen.findByText("Missing many check-ins. Baseline stuck at 13 of 16."),
    );
    expect(nav.router.push).toHaveBeenCalledWith("/residents/R08");
  });

  it("shows the empty state (UX-204)", async () => {
    server.use(
      http.get(`${API}/residents`, () =>
        HttpResponse.json({
          ...residents,
          total: 0,
          items: [],
          summary: { changed: 0, needs_attention: 0, learning: 0, usual: 0 },
        }),
      ),
    );
    renderSignedIn(<ResidentsPage />, "clinician");
    expect(await screen.findByText("No residents are enrolled yet.")).toBeVisible();
    expect(screen.queryByRole("table")).toBeNull();
    expect(filterTexts()).toEqual(["All (0)", "Changed (0)", "Needs attention (0)", "Usual (0)"]);
  });

  it("shows the truncation line when total exceeds the rows (UX-041)", async () => {
    server.use(http.get(`${API}/residents`, () => HttpResponse.json({ ...residents, total: 612 })));
    renderSignedIn(<ResidentsPage />, "clinician");
    expect(await screen.findByText("Showing 10 of 612 residents.")).toBeVisible();
  });

  it("shows the error with reference and retries (UX-203)", async () => {
    server.use(http.get(`${API}/residents`, () => problem(500, "INTERNAL", "Boom")));
    renderSignedIn(<ResidentsPage />, "clinician");
    expect(
      await screen.findByText("Could not load residents. Check your connection and try again."),
    ).toBeVisible();
    expect(screen.getByText("Reference: req-test-0001")).toBeVisible();
    // The note and the panel header stay (UX-202).
    expect(screen.getByRole("heading", { level: 1 })).toBeVisible();
    server.resetHandlers();
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByRole("link", { name: "Open chart for R09" })).toBeVisible();
  });

  it("shows the no-access message on 403 (FE-035)", async () => {
    server.use(http.get(`${API}/residents`, () => problem(403, "FORBIDDEN", "No")));
    renderSignedIn(<ResidentsPage />, "researcher");
    expect(await screen.findByText("You do not have access to this information.")).toBeVisible();
  });

  it("keeps rows and shows the stale notice after a failed refresh (UX-201, UX-206)", async () => {
    const { client } = renderSignedIn(<ResidentsPage />, "clinician");
    await screen.findByRole("link", { name: "Open chart for R09" });
    server.use(http.get(`${API}/residents`, () => problem(500, "INTERNAL", "Boom")));
    await client.refetchQueries({ queryKey: queryKeys.residents() });
    expect(
      await screen.findByText("Could not refresh. Showing data as of Oct 30, 2026, 3:00 PM CT."),
    ).toBeVisible();
    expect(shownCodes()).toEqual(ALL);
  });

  it("sets aria-busy while a refresh is in flight and keeps the rows (FE-083)", async () => {
    const { client } = renderSignedIn(<ResidentsPage />, "clinician");
    await screen.findByRole("link", { name: "Open chart for R09" });
    let release: () => void = () => undefined;
    server.use(
      http.get(`${API}/residents`, async () => {
        await new Promise<void>((r) => (release = r));
        return HttpResponse.json(residents);
      }),
    );
    void client.refetchQueries({ queryKey: queryKeys.residents() });
    await waitFor(() => expect(screen.getByRole("table")).toHaveAttribute("aria-busy", "true"));
    expect(shownCodes()).toEqual(ALL);
    release();
    await waitFor(() => expect(screen.getByRole("table")).toHaveAttribute("aria-busy", "false"));
  });

  it("goes to the login page on a 401 (FE-056)", async () => {
    window.history.pushState({}, "", "/residents?show=usual");
    server.use(http.get(`${API}/residents`, () => problem(401, "UNAUTHORIZED", "x")));
    renderSignedIn(<ResidentsPage />, "clinician");
    await waitFor(() =>
      expect(nav.router.replace).toHaveBeenCalledWith(expect.stringMatching(/^\/login\?/)),
    );
  });
});
