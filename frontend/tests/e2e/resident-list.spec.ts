// req: FE-185, E2E-03, E2E-04, E2E-05, E2E-06, UX-260, UX-261, UX-402, UX-403, UX-404, FEAT-076-FR-04
// Resident list with the DS-07 seed (TRD 11 §4.13.1, §4.13.2; TRD 14 Table 4.9-B).
import { test, expect } from "./fixtures";
import {
  ALL_CODES,
  DATA_BAR,
  LIST_ROWS,
  STATUS_NOTE,
  expectRowCodes,
  norm,
  pillTexts,
  residentRows,
} from "./helpers";

const FILTERS = ["All (10)", "Changed (2)", "Needs attention (2)", "Usual (6)"];

test.beforeEach(async ({ as }) => {
  await as("clinician");
});

test("FE-185 data bar, nav badge and study-ID link", async ({ page }) => {
  await page.goto("/residents");
  await expect(page.getByText(DATA_BAR, { exact: true })).toBeVisible();
  const nav = page.getByRole("navigation", { name: "Main" });
  const listLink = nav.getByRole("link", { name: "Resident list, 2 alarms not reviewed" });
  await expect(listLink).toBeVisible();
  await expect(listLink.locator("[data-count]")).toHaveAttribute("data-count", "2");
  await expectRowCodes(page, ALL_CODES);

  await page.getByRole("link", { name: "Open chart for R08" }).click();
  await expect(page).toHaveURL(/\/residents\/R08$/);
  await expect(page.getByRole("heading", { level: 1, name: "R08" })).toBeVisible();
});

test("E2E-03 heading, filter buttons, legend and status note", async ({ page }) => {
  await page.goto("/residents");
  await expect(page).toHaveTitle("Resident list – EchoWell");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Residents in the study");
  const group = page.getByRole("group", { name: "Show" });
  await expect(group.getByRole("button")).toHaveText(FILTERS);
  await expect(group.getByRole("button", { name: "All (10)" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  for (const name of FILTERS.slice(1)) {
    await expect(group.getByRole("button", { name })).toHaveAttribute("aria-pressed", "false");
  }
  await expect(group.getByRole("button", { name: /Learning/ })).toHaveCount(0);

  const legend = page.getByRole("list", { name: "Status meanings" });
  await expect(legend.getByRole("listitem")).toHaveCount(4);
  await expect
    .poll(() => pillTexts(legend))
    .toEqual(["▲ Changed", "! Needs attention", "○ Learning", "● Usual"]);
  const meanings = (await legend.getByRole("listitem").allTextContents()).map(norm);
  expect(meanings[0]).toContain("Their voice has moved away from their own usual. Check on them.");
  expect(meanings[1]).toContain(
    "Not enough good check-ins to judge. Check the device or the routine.",
  );
  expect(meanings[2]).toContain("Still collecting the first 16 check-ins to learn their usual.");
  expect(meanings[3]).toContain("Within their own usual range.");
  await expect(page.getByText(STATUS_NOTE, { exact: true })).toBeVisible();
});

test("E2E-04 rows in the default order with pills, texts and last check-ins", async ({ page }) => {
  await page.goto("/residents");
  await expectRowCodes(page, ALL_CODES);
  const rows = residentRows(page);
  for (const [i, [code, pill, text, last]] of LIST_ROWS.entries()) {
    const row = rows.nth(i);
    await expect(row.locator("td").nth(1), code).toHaveText(code);
    await expect.poll(() => pillTexts(row.locator("td").nth(0)), code).toEqual([pill]);
    await expect(row.locator("td").nth(2), code).toHaveText(text);
    await expect(row.locator("td").nth(3), code).toHaveText(last);
  }
});

test("E2E-05 filter Changed then Needs attention", async ({ page }) => {
  await page.goto("/residents");
  await expectRowCodes(page, ALL_CODES);
  const group = page.getByRole("group", { name: "Show" });

  await group.getByRole("button", { name: "Changed (2)" }).click();
  await expect(page).toHaveURL(/\/residents\?show=changed$/);
  await expectRowCodes(page, ["R09", "R10"]);
  await expect(group.getByRole("button", { name: "Changed (2)" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await expect(
    page.getByRole("status").filter({ hasText: "Showing changed residents" }),
  ).toHaveText("Showing changed residents");
  await expect(group.getByRole("button")).toHaveText(FILTERS);

  await group.getByRole("button", { name: "Needs attention (2)" }).click();
  await expect(page).toHaveURL(/\/residents\?show=needs_attention$/);
  await expectRowCodes(page, ["R03", "R08"]);
  await expect(group.getByRole("button")).toHaveText(FILTERS);
  await expect(
    page.getByRole("status").filter({ hasText: "Showing needs attention residents" }),
  ).toBeAttached();
});

test("E2E-06 Usual filter kept on reload and after the back link", async ({ page }) => {
  const usual = ["R01", "R02", "R04", "R05", "R06", "R07"];
  await page.goto("/residents");
  await expectRowCodes(page, ALL_CODES);
  await page
    .getByRole("group", { name: "Show" })
    .getByRole("button", { name: "Usual (6)" })
    .click();
  await expect(page).toHaveURL(/\/residents\?show=usual$/);
  await expectRowCodes(page, usual);

  await page.reload();
  await expect(page).toHaveURL(/\/residents\?show=usual$/);
  await expectRowCodes(page, usual);
  await expect(page.getByRole("button", { name: "Usual (6)" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );

  await page.getByRole("link", { name: "Open chart for R01" }).click();
  await expect(page).toHaveURL(/\/residents\/R01$/);
  await page.getByRole("link", { name: "← Resident list" }).click();
  await expect(page).toHaveURL(/\/residents\?show=usual$/);
  await expectRowCodes(page, usual);
});

test("E2E-03/UX-261 Needs attention and Usual filters from the URL", async ({ page }) => {
  await page.goto("/residents?show=needs_attention");
  await expectRowCodes(page, ["R03", "R08"]);
  await page.goto("/residents?show=changed");
  await expectRowCodes(page, ["R09", "R10"]);
});
