// req: UX-182..UX-188, UX-194, FE-092, FEAT-073-FR-03..FR-06, FR-12
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { AdmissionRow, Meta } from "@/lib/types";
import { AdmissionsTable } from "./AdmissionsTable";

const meta: Meta = {
  facility_name: "Edgewood",
  facility_tz: "America/Chicago",
  data_source_label: "synthetic",
  as_of: "2026-10-30T20:00:00Z",
  baseline_n: 16,
  cusum_h: 5,
  pipeline_profile: "production",
};

const row = (code: string, status: AdmissionRow["comparison_status"], n: number): AdmissionRow => ({
  resident_code: code,
  admitted_on: "2026-10-21",
  checkins_so_far: n,
  comparison_status: status,
  own_baseline_progress: { n_usable: n, n_required: 16 },
});

const rows = [
  row("A01", "outside_range", 6),
  row("A02", "within_range", 7),
  row("A03", "not_enough_checkins", 2),
  { ...row("A04", "range_not_available", 3), admitted_on: null },
];

describe("AdmissionsTable", () => {
  it("renders the columns, pills and texts of the four statuses", () => {
    render(<AdmissionsTable rows={rows} meta={meta} selected={null} onSelect={() => {}} />);
    const headers = screen.getAllByRole("columnheader").map((h) => h.textContent);
    expect(headers).toEqual([
      "Status",
      "Resident",
      "Admitted",
      "Compared with facility range",
      "Own baseline",
      "Actions",
    ]);
    expect(screen.getByRole("region", { name: "New admissions table" })).toHaveAttribute(
      "tabindex",
      "0",
    );
    const body = screen.getAllByRole("row").slice(1);
    const cells = body.map((r) =>
      within(r)
        .getAllByRole("cell")
        .map((c) => c.textContent),
    );
    expect(cells[0]?.slice(0, 5)).toEqual([
      "Out of range",
      "A01",
      "Oct 21",
      "Outside facility range",
      "6 of 16",
    ]);
    expect(cells[1]?.slice(0, 5)).toEqual([
      "In range",
      "A02",
      "Oct 21",
      "Within facility range",
      "7 of 16",
    ]);
    expect(cells[2]?.slice(0, 5)).toEqual([
      "○Learning",
      "A03",
      "Oct 21",
      "Not enough check-ins yet",
      "2 of 16",
    ]);
    expect(cells[3]?.slice(0, 5)).toEqual([
      "○Learning",
      "A04",
      "—",
      "Facility range not available yet",
      "3 of 16",
    ]);
    // neutral pills carry no glyph and no red/green status class (D-117)
    expect(within(body[0] as HTMLElement).queryByText("▲")).toBeNull();
  });

  it("selects a row with Show comparison", async () => {
    const onSelect = vi.fn();
    const { rerender } = render(
      <AdmissionsTable rows={rows} meta={meta} selected={null} onSelect={onSelect} />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Show comparison for A02" }));
    expect(onSelect).toHaveBeenCalledWith("A02");
    rerender(<AdmissionsTable rows={rows} meta={meta} selected="A02" onSelect={onSelect} />);
    const selected = screen
      .getAllByRole("row")
      .filter((r) => r.getAttribute("aria-selected") === "true");
    expect(selected).toHaveLength(1);
    expect(selected[0]).toHaveTextContent("A02");
  });

  it("shows the empty text by profile", () => {
    const { rerender } = render(
      <AdmissionsTable rows={[]} meta={meta} selected={null} onSelect={() => {}} />,
    );
    expect(screen.getByText("No new admissions.")).toBeVisible();
    rerender(
      <AdmissionsTable
        rows={[]}
        meta={{ ...meta, pipeline_profile: "test_v0_1" }}
        selected={null}
        onSelect={() => {}}
      />,
    );
    expect(
      screen.getByText("No new admissions. The pipeline test data v0.1 has no admission group."),
    ).toBeVisible();
  });
});
