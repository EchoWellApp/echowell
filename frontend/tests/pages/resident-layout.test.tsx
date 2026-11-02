// req: UX-060, UX-061, UX-410, UX-411, UX-412, UX-205, UX-206, UX-229, FE-025, FE-030, FE-031, FE-032, FE-142, FE-144, FE-206, FE-210, FEAT-066-AC-06, FEAT-066-AC-07
import { act, configure, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http } from "msw";
import ResidentChartLayout from "@/app/(protected)/residents/[residentCode]/layout";
import {
  codeParam,
  epochRange,
  hasScoredSessions,
  latestTally,
  logRange,
  sectionFromPath,
} from "@/app/(protected)/residents/[residentCode]/section";
import { rememberShow } from "@/components/BackLink/BackLink";
import { queryKeys } from "@/lib/queryKeys";
import type { ResidentDetail, ScoresResponse } from "@/lib/types";
import R07 from "@/tests/fixtures/ds07/resident/R07.json";
import R08 from "@/tests/fixtures/ds07/resident/R08.json";
import R09 from "@/tests/fixtures/ds07/resident/R09.json";
import R09scores from "@/tests/fixtures/ds07/resident/R09-scores.json";
import { API, problem } from "@/tests/msw/handlers";
import { server } from "@/tests/msw/server";
import { setLocation } from "@/tests/support/navigation";
import { testQueryClient, withQuery } from "@/tests/support/render";

const as = (x: unknown) => x as ResidentDetail;

function renderChart(code: string, path = `/residents/${code}`, client = testQueryClient()) {
  setLocation(path, "", { residentCode: code });
  return withQuery(
    <ResidentChartLayout>
      <p>section content</p>
    </ResidentChartLayout>,
    client,
  );
}

// Data arrives through MSW; allow for a busy test machine.
beforeAll(() => configure({ asyncUtilTimeout: 4000 }));

describe("resident chart layout", () => {
  it("renders back link, banner and section navigation for R09 (FE-206, FE-210)", async () => {
    renderChart("R09");
    expect(screen.getByRole("link", { name: "← Resident list" })).toHaveAttribute(
      "href",
      "/residents",
    );
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("R09");
    expect(screen.getByText("section content")).toBeVisible();
    const banner = screen.getByRole("region", { name: "Resident" });
    expect(await within(banner).findByText("Oct 30, 2:28 PM CT")).toBeVisible();
    expect(banner).toHaveTextContent("▲Changed");
    const nav = screen.getByRole("navigation", { name: "Resident chart" });
    expect(within(nav).getByRole("link", { name: "Summary" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(
      within(nav).getByRole("link", { name: "Review and notes, alarm not reviewed" }),
    ).toHaveTextContent("1");
    expect(document.title).toBe("R09 · Summary – EchoWell");
  });

  it("marks the current section from the path and keeps ?show= (FE-025, FE-032)", async () => {
    rememberShow("changed");
    renderChart("R01", "/residents/R01/log");
    const nav = screen.getByRole("navigation", { name: "Resident chart" });
    expect(within(nav).getByRole("link", { name: "Check-in log" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(document.title).toBe("R01 · Check-in log – EchoWell");
    await screen.findByText("Oct 30, 2:07 PM CT");
    expect(within(nav).getByRole("link", { name: "Review and notes" })).not.toHaveTextContent("1");
    await waitFor(() =>
      expect(screen.getByRole("link", { name: "← Resident list" })).toHaveAttribute(
        "href",
        "/residents?show=changed",
      ),
    );
  });

  it("shows only the not-found state for an unknown resident (UX-412, FE-142)", async () => {
    renderChart("R11");
    expect(
      await screen.findByRole("heading", { level: 1, name: "Resident R11 was not found." }),
    ).toBeVisible();
    expect(screen.getByRole("link", { name: "← Resident list" })).toBeVisible();
    expect(screen.queryByRole("region", { name: "Resident" })).toBeNull();
    expect(screen.queryByRole("navigation", { name: "Resident chart" })).toBeNull();
    expect(screen.queryByText("section content")).toBeNull();
  });

  it("rejects an invalid code without calling the API (FE-030)", async () => {
    const seen: string[] = [];
    const listener = ({ request }: { request: Request }) => void seen.push(request.url);
    server.events.on("request:start", listener);
    renderChart("r09");
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      "Resident r09 was not found.",
    );
    expect(screen.queryByText("section content")).toBeNull();
    await act(() => new Promise((r) => setTimeout(r, 20)));
    server.events.removeListener("request:start", listener);
    expect(seen.filter((u) => u.includes("/residents/"))).toEqual([]);
  });

  it("shows an error in the banner only and keeps the sections (UX-202, UX-203)", async () => {
    server.use(http.get(`${API}/residents/:code`, () => problem(500, "INTERNAL", "Boom")));
    renderChart("R09");
    expect(
      await screen.findByText("Could not load resident. Check your connection and try again."),
    ).toBeVisible();
    expect(screen.getByText("Reference: req-test-0001")).toBeVisible();
    expect(screen.getByRole("button", { name: "Try again" })).toBeVisible();
    expect(screen.getByText("section content")).toBeVisible();
    expect(screen.getByRole("navigation", { name: "Resident chart" })).toBeVisible();
    server.resetHandlers();
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("Oct 30, 2:28 PM CT")).toBeVisible();
  });

  it("keeps cached data and shows the refresh notice after a failed refresh (UX-206, FE-144)", async () => {
    const client = testQueryClient();
    client.setQueryData(queryKeys.resident("R09"), R09);
    server.use(http.get(`${API}/residents/:code`, () => problem(503, "UNAVAILABLE", "Down")));
    renderChart("R09", "/residents/R09", client);
    expect(
      await screen.findByText("Could not refresh. Showing data as of Oct 30, 2026, 3:00 PM CT."),
    ).toBeVisible();
    expect(screen.getByText("Oct 30, 2:28 PM CT")).toBeVisible();
  });
});

describe("chart section helpers", () => {
  it("reads the section from the path", () => {
    expect(sectionFromPath("/residents/R09")).toBe("summary");
    expect(sectionFromPath("/residents/R09/")).toBe("summary");
    expect(sectionFromPath("/residents/R09/review")).toBe("review");
    expect(sectionFromPath("/residents/R09/device")).toBe("device");
    expect(sectionFromPath("/residents/R09/summary")).toBe("summary");
    expect(sectionFromPath("/residents/R09/other")).toBe("summary");
    expect(sectionFromPath(null)).toBe("summary");
  });

  it("reads and decodes the route parameter", () => {
    expect(codeParam({ residentCode: "R09" })).toBe("R09");
    expect(codeParam({ residentCode: ["R10", "x"] })).toBe("R10");
    expect(codeParam({ residentCode: "R%2009" })).toBe("R 09");
    expect(codeParam({ residentCode: "%E0%A4%A" })).toBe("%E0%A4%A");
    expect(codeParam(null)).toBe("");
  });

  it("derives scored state, latest tally and request ranges", () => {
    const scores = R09scores as unknown as ScoresResponse;
    expect(hasScoredSessions(as(R09), scores)).toBe(true);
    expect(hasScoredSessions(as(R09), undefined)).toBe(true);
    expect(hasScoredSessions(as(R08), undefined)).toBe(false);
    expect(latestTally(as(R09), scores)).toBeCloseTo(26.83, 2);
    expect(latestTally(as(R08), undefined)).toBeNull();
    expect(epochRange(as(R07))).toEqual({ from: "2026-10-13", to: "2026-10-30" });
    expect(
      epochRange(as({ ...R07, current_epoch: { ...R07.current_epoch, started_on: "2024-01-01" } })),
    ).toEqual({ from: "2025-10-30", to: "2026-10-30" });
    expect(epochRange(as({ ...R07, current_epoch: null }))).toEqual({
      from: "2026-10-01",
      to: "2026-10-30",
    });
    expect(logRange("2026-10-30", 0)).toEqual({ from: "2026-10-01", to: "2026-10-30" });
    expect(logRange("2026-10-30", 1)).toEqual({ from: "2026-09-01", to: "2026-09-30" });
  });
});
