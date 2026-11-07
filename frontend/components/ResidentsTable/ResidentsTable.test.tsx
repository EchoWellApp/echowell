// req: FE-182, FE-083, FE-084, FE-092, FE-207, UX-034, UX-036, UX-037, UX-038, UX-040, UX-042,
// UX-043, UX-044, UX-402, UX-405, UX-408, UX-260, UX-261, FEAT-065-AC-02, FEAT-065-AC-05
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import residents from "@/tests/fixtures/ds07/residents.json";
import { nav } from "@/tests/support/navigation";
import type { ResidentRow, ResidentsResponse } from "@/lib/types";
import type { ListFilter } from "@/lib/wording";
import { ResidentsTable } from "./ResidentsTable";

const data = residents as unknown as ResidentsResponse;

/** TRD 11 §4.13.1 (binding). */
const EXPECTED: [string, string, string, string][] = [
  [
    "R09",
    "▲ Changed",
    "Changed from their usual since Oct 21. Not reviewed yet.",
    "Oct 30, 2:28 PM CT",
  ],
  [
    "R10",
    "▲ Changed",
    "Changed from their usual since Oct 24. Not reviewed yet.",
    "Oct 30, 2:39 PM CT",
  ],
  ["R03", "! Needs attention", "7 check-ins too noisy or too short to use.", "Oct 30, 2:19 PM CT"],
  [
    "R08",
    "! Needs attention",
    "Missing many check-ins. Baseline stuck at 13 of 16.",
    "Oct 30, 2:28 PM CT",
  ],
  ["R01", "● Usual", "Within their usual range.", "Oct 30, 2:07 PM CT"],
  ["R02", "● Usual", "Within their usual range.", "Oct 30, 2:55 PM CT"],
  ["R04", "● Usual", "Within their usual range.", "Oct 30, 2:17 PM CT"],
  ["R05", "● Usual", "Within their usual range.", "Oct 30, 2:40 PM CT"],
  ["R06", "● Usual", "Within their usual range.", "Oct 30, 2:38 PM CT"],
  ["R07", "● Usual", "Usual. Baseline restarted Oct 13 after a new device.", "Oct 30, 2:52 PM CT"],
];

/** TRD 11 §4.13.2 (binding). */
const FILTER_ROWS: [ListFilter, string[]][] = [
  ["all", ["R09", "R10", "R03", "R08", "R01", "R02", "R04", "R05", "R06", "R07"]],
  ["changed", ["R09", "R10"]],
  ["needs_attention", ["R03", "R08"]],
  ["usual", ["R01", "R02", "R04", "R05", "R06", "R07"]],
];

function bodyRows() {
  const [, body] = screen.getAllByRole("rowgroup");
  return within(body!).getAllByRole("row");
}

/** "▲ Changed": the hidden glyph, a space, then the label. */
function pillText(cell: HTMLElement): string {
  const glyph = cell.querySelector("[aria-hidden='true']")?.textContent ?? "";
  return `${glyph} ${(cell.textContent ?? "").slice(glyph.length)}`;
}

function renderTable(filter: ListFilter = "all", rows: ResidentRow[] = data.items) {
  return render(<ResidentsTable rows={rows} meta={data.meta} filter={filter} isFetching={false} />);
}

describe("ResidentsTable", () => {
  beforeEach(() => nav.router.push.mockClear());

  it("renders every row of TRD 11 §4.13.1 in API order (FE-182)", () => {
    renderTable();
    expect(screen.getAllByRole("columnheader").map((h) => h.textContent)).toEqual([
      "Status",
      "Resident",
      "What's happening",
      "Last check-in",
    ]);
    for (const h of screen.getAllByRole("columnheader")) expect(h).toHaveAttribute("scope", "col");
    const rows = bodyRows();
    expect(rows).toHaveLength(EXPECTED.length);
    rows.forEach((row, i) => {
      const [code, pill, happening, last] = EXPECTED[i]!;
      const cells = within(row).getAllByRole("cell");
      expect(pillText(cells[0]!)).toBe(pill);
      expect(cells[1]!.textContent).toBe(code);
      expect(cells[2]!.textContent).toBe(happening);
      expect(cells[3]!.textContent).toBe(last);
    });
  });

  it.each(FILTER_ROWS)("filter %s shows the rows of TRD 11 §4.13.2", (filter, codes) => {
    renderTable(filter);
    expect(bodyRows().map((r) => within(r).getAllByRole("cell")[1]!.textContent)).toEqual(codes);
  });

  it("has a visually hidden caption per filter (UX-043)", () => {
    const { container, rerender } = renderTable();
    const caption = container.querySelector("caption")!;
    expect(caption).toHaveTextContent("Residents in the study, all");
    expect(caption).toHaveClass("visually-hidden");
    rerender(
      <ResidentsTable rows={data.items} meta={data.meta} filter="changed" isFetching={false} />,
    );
    expect(caption).toHaveTextContent("Residents in the study, changed");
    rerender(
      <ResidentsTable
        rows={data.items}
        meta={data.meta}
        filter="needs_attention"
        isFetching={false}
      />,
    );
    expect(caption).toHaveTextContent("Residents in the study, needs attention");
  });

  it("shows one row when no resident has the status (UX-402)", () => {
    renderTable("learning");
    const rows = bodyRows();
    expect(rows).toHaveLength(1);
    const cell = within(rows[0]!).getByRole("cell");
    expect(cell).toHaveTextContent("No residents with this status.");
    expect(cell).toHaveAttribute("colspan", "4");
  });

  it("marks Changed and Needs-attention rows for their left border (UX-034)", () => {
    renderTable();
    const statuses = bodyRows().map((r) => r.getAttribute("data-status"));
    expect(statuses).toEqual([
      "changed",
      "changed",
      "needs_attention",
      "needs_attention",
      "usual",
      "usual",
      "usual",
      "usual",
      "usual",
      "usual",
    ]);
    expect(bodyRows()[0]!.className).toMatch(/changed/);
    expect(bodyRows()[2]!.className).toMatch(/needs_attention/);
  });

  it("links each study ID to its chart (UX-037) and opens it on row click (UX-040)", async () => {
    renderTable();
    for (const [code] of EXPECTED) {
      expect(screen.getByRole("link", { name: `Open chart for ${code}` })).toHaveAttribute(
        "href",
        `/residents/${code}`,
      );
    }
    expect(screen.getAllByRole("link")).toHaveLength(10);
    await userEvent.click(
      screen.getByText("Changed from their usual since Oct 21. Not reviewed yet."),
    );
    expect(nav.router.push).toHaveBeenCalledWith("/residents/R09");
    nav.router.push.mockClear();
    const link = screen.getByRole("link", { name: "Open chart for R10" });
    link.addEventListener("click", (e) => e.preventDefault());
    await userEvent.click(link);
    expect(nav.router.push).not.toHaveBeenCalled();
  });

  it("sits in a focusable scroll container and sets aria-busy while fetching (UX-042, FE-083)", () => {
    const { rerender } = renderTable();
    const region = screen.getByRole("region", { name: "Residents table" });
    expect(region).toHaveAttribute("tabindex", "0");
    expect(screen.getByRole("table")).toHaveAttribute("aria-busy", "false");
    rerender(<ResidentsTable rows={data.items} meta={data.meta} filter="all" isFetching />);
    expect(screen.getByRole("table")).toHaveAttribute("aria-busy", "true");
    expect(bodyRows()).toHaveLength(10);
  });

  it("shows 'No check-ins yet' and a Learning row", () => {
    const learner: ResidentRow = {
      ...data.items[4]!,
      resident_code: "R11",
      status: "baseline_forming",
      baseline_progress: { n_usable: 4, n_required: 16 },
      last_checkin_at: null,
      last_checkin_local: null,
    };
    renderTable("learning", [...data.items, learner]);
    const cells = within(bodyRows()[0]!).getAllByRole("cell");
    expect(pillText(cells[0]!)).toBe("○ Learning");
    expect(cells[2]!.textContent).toBe("Learning their usual: 4 of 16 check-ins so far.");
    expect(cells[3]!.textContent).toBe("No check-ins yet");
  });

  it("never shows R04's duplicates: one R04 row (UX-044)", () => {
    renderTable();
    expect(screen.getAllByRole("link", { name: "Open chart for R04" })).toHaveLength(1);
  });
});
