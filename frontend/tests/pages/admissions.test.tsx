// req: UX-181..UX-195, UX-202, UX-229, UX-264, AC-UX-07, FE-032, FE-092, FE-100, FE-189, FEAT-073-AC-01..AC-05
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import AdmissionsPage from "@/app/(protected)/admissions/page";
import ProtectedLayout from "@/app/(protected)/layout";
import type { AdmissionComparison, AdmissionList, ReferenceRangeList } from "@/lib/types";
import admissionsDs07 from "@/tests/fixtures/ds07/admissions.json";
import { API, problem } from "@/tests/msw/handlers";
import { server } from "@/tests/msw/server";
import { setLocation } from "@/tests/support/navigation";
import { renderSignedIn } from "@/tests/support/render";

const NOTE =
  "Future / experimental. Not in pipeline test v0.1: the test data has no admission group or facility range yet. Open question for Shaba and the PI.";

// Synthetic new-admission cohort (DS-07 has none, TST-186).
const meta = { ...(admissionsDs07 as AdmissionList).meta, pipeline_profile: "production" as const };
const list: AdmissionList = {
  meta,
  total: 2,
  limit: 500,
  offset: 0,
  items: [
    {
      resident_code: "A01",
      admitted_on: "2026-10-24",
      checkins_so_far: 6,
      comparison_status: "outside_range",
      own_baseline_progress: { n_usable: 5, n_required: 16 },
    },
    {
      resident_code: "A02",
      admitted_on: "2026-10-27",
      checkins_so_far: 1,
      comparison_status: "range_not_available",
      own_baseline_progress: { n_usable: 1, n_required: 16 },
    },
  ],
};
const comparison: AdmissionComparison = {
  resident_code: "A01",
  comparison_status: "outside_range",
  meta,
  features: [
    { feature_key: "loudness_dbfs", low: -30, high: -20, resident_value: -36, outside_range: true },
    {
      feature_key: "speech_rate_syl_per_s",
      low: 3,
      high: 5,
      resident_value: 4,
      outside_range: false,
    },
  ],
};
const ranges: ReferenceRangeList = {
  meta,
  total: 1,
  limit: 50,
  offset: 0,
  items: [
    {
      feature_key: "loudness_dbfs",
      low: -30,
      high: -20,
      method: "p10_p90",
      n_residents: 10,
      computed_at: "2026-10-30T07:05:00Z",
      pipeline_run_id: null,
    },
  ],
};

function withCohort() {
  server.use(
    http.get(`${API}/admissions`, () => HttpResponse.json(list)),
    http.get(`${API}/admissions/:code/comparison`, () => HttpResponse.json(comparison)),
    http.get(`${API}/facility/reference-ranges`, () => HttpResponse.json(ranges)),
  );
}

describe("/admissions", () => {
  beforeEach(() => setLocation("/admissions"));

  it("renders the note and the DS-07 empty state (AC-UX-07, UX-264)", async () => {
    renderSignedIn(
      <ProtectedLayout>
        <AdmissionsPage />
      </ProtectedLayout>,
      "clinician",
    );
    expect(await screen.findByText(NOTE)).toBeVisible();
    expect(screen.getByRole("heading", { level: 1, name: "New admissions" })).toBeVisible();
    expect(
      screen.getByText(
        "New residents don’t have their own baseline yet, so their first check-ins are compared with the facility’s usual range.",
      ),
    ).toBeVisible();
    expect(screen.getByRole("status")).toHaveTextContent("Loading new admissions…");
    expect(
      await screen.findByText(
        "No new admissions. The pipeline test data v0.1 has no admission group.",
      ),
    ).toBeVisible();
    expect(screen.getByText("Select a resident to see the comparison.")).toBeVisible();
    expect(screen.queryByRole("link", { name: "← Resident list" })).toBeNull();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(document.title).toBe("New admissions – EchoWell");
    expect(await screen.findByRole("link", { name: "New admissions" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByTestId("data-bar")).toBeVisible();
    expect(screen.queryByRole("contentinfo")).toBeNull();
  });

  it("shows rows and the comparison of the selected resident (FEAT-073-AC-02..AC-04)", async () => {
    withCohort();
    renderSignedIn(<AdmissionsPage />, "researcher");
    const a01 = (await screen.findByText("A01")).closest("tr") as HTMLElement;
    expect(within(a01).getByText("Out of range")).toBeVisible();
    expect(within(a01).getByText("Outside facility range")).toBeVisible();
    expect(within(a01).getByText("Oct 24")).toBeVisible();
    expect(within(a01).getByText("5 of 16")).toBeVisible();
    const a02 = screen.getByText("A02").closest("tr") as HTMLElement;
    // StatusPill: glyph "○" (aria-hidden) + "Learning" (FE-092)
    expect(within(a02).getByText("Learning").textContent).toBe("○Learning");
    expect(within(a02).getByText("Facility range not available yet")).toBeVisible();
    expect(screen.getByText("Select a resident to see the comparison.")).toBeVisible();

    await userEvent.click(screen.getByRole("button", { name: "Show comparison for A01" }));
    expect(a01).toHaveAttribute("aria-selected", "true");
    expect(a02).toHaveAttribute("aria-selected", "false");
    expect(
      await screen.findByRole("heading", { level: 2, name: "A01 compared with facility range" }),
    ).toBeVisible();
    expect(
      await screen.findByText("Grey band = usual range across current residents"),
    ).toBeVisible();
    expect(
      screen.getByText(
        "After 16 usable check-ins, the resident moves to the resident list and is compared with their own baseline instead.",
      ),
    ).toBeVisible();
    const dots = screen.getAllByTestId("range-dot");
    expect(dots[0]).toHaveAttribute("data-outside", "true");
    expect(dots[0]).toHaveTextContent("▲");
    expect(
      await screen.findByText(
        "Range from 10 current residents, computed Oct 30 (method: p10_p90).",
      ),
    ).toBeVisible();
  });

  it("shows the admissions error only in the table panel", async () => {
    server.use(http.get(`${API}/admissions`, () => problem(500, "INTERNAL", "Server error")));
    renderSignedIn(<AdmissionsPage />, "clinician");
    expect(
      await screen.findByText(
        "Could not load new admissions. Check your connection and try again.",
      ),
    ).toBeVisible();
    expect(screen.getByText("Reference: req-test-0001")).toBeVisible();
    expect(screen.getByText(NOTE)).toBeVisible();
    expect(screen.queryByText("Select a resident to see the comparison.")).toBeNull();
  });

  it("keeps the table when the comparison fails (UX-202)", async () => {
    withCohort();
    server.use(
      http.get(`${API}/admissions/:code/comparison`, () =>
        problem(404, "RESIDENT_NOT_FOUND", "Resident not found"),
      ),
    );
    renderSignedIn(<AdmissionsPage />, "clinician");
    await userEvent.click(await screen.findByRole("button", { name: "Show comparison for A01" }));
    expect(
      await screen.findByText(
        "Could not load the comparison. Check your connection and try again.",
      ),
    ).toBeVisible();
    expect(screen.getByText("A02")).toBeVisible();
  });

  it("omits the method line when no ranges are returned", async () => {
    withCohort();
    server.use(
      http.get(`${API}/facility/reference-ranges`, () =>
        HttpResponse.json({ ...ranges, items: [], total: 0 }),
      ),
    );
    renderSignedIn(<AdmissionsPage />, "clinician");
    await userEvent.click(await screen.findByRole("button", { name: "Show comparison for A01" }));
    await screen.findByText("Grey band = usual range across current residents");
    await waitFor(() => expect(screen.queryByText(/^Range from/)).toBeNull());
  });
});
