// req: UX-189..UX-193, UX-225, FE-100, FEAT-073-FR-08, FR-09, FR-11
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { AdmissionComparison } from "@/lib/types";
import { FacilityRangeChart, rowScale } from "./FacilityRangeChart";

const meta: AdmissionComparison["meta"] = {
  facility_name: "Edgewood",
  facility_tz: "America/Chicago",
  data_source_label: "synthetic",
  as_of: "2026-10-30T20:00:00Z",
  baseline_n: 16,
  cusum_h: 5,
  pipeline_profile: "production",
};

const comparison: AdmissionComparison = {
  resident_code: "A01",
  comparison_status: "outside_range",
  meta,
  features: [
    {
      feature_key: "loudness_dbfs",
      low: -30,
      high: -20,
      resident_value: -35.456,
      outside_range: true,
    },
    {
      feature_key: "pause_fraction",
      low: 0.1,
      high: 0.3,
      resident_value: 0.2,
      outside_range: false,
    },
    { feature_key: "mean_f0_hz", low: 150, high: 210, resident_value: null, outside_range: null },
    {
      feature_key: "voiced_fraction",
      low: null,
      high: null,
      resident_value: 0.5,
      outside_range: null,
    },
  ],
};

describe("FacilityRangeChart", () => {
  it("draws a band per measurement and dots inside/outside", () => {
    render(<FacilityRangeChart comparison={comparison} residentCode="A01" N={16} />);
    const chart = screen.getByRole("img", {
      name: "A01 compared with facility range: 1 of 3 measurements outside the range",
    });
    expect(chart).toHaveAttribute("tabindex", "0");
    const rows = within(chart).getAllByTestId("range-row");
    expect(rows.map((r) => r.firstChild?.textContent)).toEqual([
      "Quieter",
      "More time in pauses",
      "mean_f0_hz",
    ]);
    expect(within(chart).getAllByTestId("range-band")).toHaveLength(3);
    const dots = within(chart).getAllByTestId("range-dot");
    expect(dots).toHaveLength(2);
    expect(dots[0]).toHaveAttribute("data-outside", "true");
    expect(dots[0]).toHaveTextContent("▲");
    expect(dots[1]).toHaveAttribute("data-outside", "false");
    expect(dots[1]).not.toHaveTextContent("▲");
    expect(screen.getByText("Grey band = usual range across current residents")).toBeVisible();
    expect(
      screen.getByText(
        "After 16 usable check-ins, the resident moves to the resident list and is compared with their own baseline instead.",
      ),
    ).toBeVisible();
  });

  it("offers the comparison as a table", async () => {
    render(<FacilityRangeChart comparison={comparison} residentCode="A01" N={16} />);
    await userEvent.click(screen.getByText("Show comparison as a table"));
    const table = screen.getByRole("table");
    const text = within(table)
      .getAllByRole("row")
      .map((r) => Array.from(r.children).map((c) => c.textContent));
    expect(text).toEqual([
      ["Measurement", "Resident value", "Facility range", "Outside range"],
      ["Quieter", "−35.46", "−30–−20", "▲ Yes"],
      ["More time in pauses", "0.2", "0.1–0.3", "No"],
      ["mean_f0_hz", "—", "150–210", "No"],
    ]);
  });

  it("says the range is not available when no band exists", () => {
    render(
      <FacilityRangeChart
        comparison={{
          ...comparison,
          comparison_status: "range_not_available",
          features: [comparison.features[3]!],
        }}
        residentCode="A01"
        N={16}
      />,
    );
    expect(screen.getByText("Facility range not available yet")).toBeVisible();
    expect(screen.queryByRole("img")).toBeNull();
    expect(screen.queryByText("Show comparison as a table")).toBeNull();
  });

  it("scales the band and dot into 0–100%", () => {
    const s = rowScale({
      feature_key: "pause_fraction",
      low: 0.1,
      high: 0.3,
      resident_value: 0.2,
      outside_range: false,
    });
    expect(s.band[0]).toBeCloseTo(25);
    expect(s.band[1]).toBeCloseTo(75);
    expect(s.dot).toBeCloseTo(50);
    const z = rowScale({
      feature_key: "mfcc1",
      low: 0,
      high: 0,
      resident_value: null,
      outside_range: null,
    });
    expect(z.dot).toBeNull();
  });
});
