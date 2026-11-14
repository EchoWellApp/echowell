// req: FE-190, TST-110, TST-111, UX-220, UX-221, UX-222, UX-228, NFR-142, FEAT-075-FR-01, FR-03,
// FR-04, FEAT-075-AC-01, AC-04, AC-08
// axe on the TST-110 route list in both colour schemes, the keyboard-only run of TST-111 and the
// no-JavaScript message. The keyboard run never writes: every POST is answered by a stub.
import AxeBuilder from "@axe-core/playwright";
import type { Locator, Page } from "@playwright/test";
import { test, expect } from "./fixtures";
import { residentRows, settled } from "./helpers";

/** TRD 13 TST-110: exactly these 12 routes. */
const ROUTES = [
  "/login",
  "/residents",
  "/residents/R09",
  "/residents/R09/review",
  "/residents/R09/trends",
  "/residents/R09/baseline",
  "/residents/R09/log",
  "/residents/R09/device",
  "/residents/R08",
  "/admissions",
  "/study",
  "/admin",
];
const TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"];

async function ready(page: Page, route: string): Promise<void> {
  await page.goto(route);
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  if (route === "/login") return;
  await settled(page);
  if (route === "/residents") await expect(residentRows(page)).toHaveCount(10);
  if (route.endsWith("/trends")) await expect(page.getByTestId("score-bar")).toHaveCount(14);
  if (route === "/study") {
    await expect(page.getByRole("list", { name: "Key counts" })).toContainText("94%");
  }
  if (route === "/admin") await expect(page.getByRole("table").first()).toBeVisible();
  await page.waitForLoadState("networkidle");
}

for (const scheme of ["light", "dark"] as const) {
  test.describe(`axe, ${scheme} scheme`, () => {
    test.use({ colorScheme: scheme });

    for (const route of ROUTES) {
      test(`FE-190 ${route} has no serious or critical violations (${scheme})`, async ({
        page,
        as,
      }) => {
        if (route !== "/login") await as("admin");
        await ready(page, route);
        const matches = await page.evaluate(
          () => window.matchMedia("(prefers-color-scheme: dark)").matches,
        );
        expect(matches).toBe(scheme === "dark");
        const result = await new AxeBuilder({ page }).withTags(TAGS).analyze();
        const bad = result.violations
          .filter((v) => v.impact === "serious" || v.impact === "critical")
          .map(
            (v) => `${v.id} (${v.impact}): ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`,
          );
        expect(bad).toEqual([]);
      });
    }
  });
}

test("NFR-142 / FEAT-075-AC-08 shows a message when JavaScript is disabled", async ({
  browser,
  baseURL,
}) => {
  const context = await browser.newContext({ javaScriptEnabled: false, baseURL });
  const page = await context.newPage();
  await page.goto("/login");
  await expect(
    page.getByText("This dashboard needs JavaScript enabled.", { exact: true }),
  ).toBeVisible();
  await context.close();
});

// ---------------------------------------------------------------- TST-111 keyboard-only run

async function isFocused(target: Locator): Promise<boolean> {
  return target.evaluate((el) => el === document.activeElement).catch(() => false);
}

/** Presses Tab (or Shift+Tab) until `target` has focus; fails after `max` presses. */
async function tabTo(page: Page, target: Locator, max = 80, key = "Tab"): Promise<void> {
  await expect(target).toBeVisible();
  for (let i = 0; i < max; i++) {
    if (await isFocused(target)) break;
    await page.keyboard.press(key);
  }
  expect(await isFocused(target), `reached by ${key}`).toBe(true);
  // UX-222: visible 3px solid focus outline.
  const outline = await target.evaluate((el) => {
    const cs = getComputedStyle(el);
    return { style: cs.outlineStyle, width: cs.outlineWidth };
  });
  expect(outline).toEqual({ style: "solid", width: "3px" });
}

/** Names of the elements reached by pressing Tab `count` times. */
async function tabNames(page: Page, count: number): Promise<string[]> {
  const names: string[] = [];
  for (let i = 0; i < count; i++) {
    await page.keyboard.press("Tab");
    names.push(
      await page.evaluate(() => {
        const el = document.activeElement as HTMLElement | null;
        return (el?.getAttribute("aria-label") ?? el?.textContent ?? "")
          .replace(/\s+/g, " ")
          .trim();
      }),
    );
  }
  return names;
}

test("TST-111 keyboard-only run through list, chart and review", async ({ page, as }) => {
  await as("clinician");
  const posts: string[] = [];
  await page.route("**/api/v1/**", async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    posts.push(new URL(route.request().url()).pathname);
    return route.fulfill({
      status: 503,
      contentType: "application/problem+json",
      body: JSON.stringify({
        type: "about:blank",
        title: "Stubbed by the E2E keyboard run",
        status: 503,
        code: "SERVICE_UNAVAILABLE",
      }),
    });
  });

  // Resident list: filter buttons and every study-ID link.
  await page.goto("/residents");
  await expect(residentRows(page)).toHaveCount(10);
  const changed = page.getByRole("button", { name: "Changed (2)" });
  await tabTo(page, changed);
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\?show=changed$/);
  await expect(residentRows(page)).toHaveCount(2);
  const all = page.getByRole("button", { name: "All (10)" });
  await tabTo(page, all, 10, "Shift+Tab");
  await page.keyboard.press("Space");
  await expect(page).toHaveURL(/\/residents(\?show=all)?$/);
  await expect(residentRows(page)).toHaveCount(10);
  await tabTo(page, page.getByRole("link", { name: "Open chart for R09" }));
  const names = await tabNames(page, 12);
  const codes = names.filter((n) => n.startsWith("Open chart for ")).map((n) => n.slice(-3));
  expect(codes.slice(0, 9)).toEqual([
    "R10",
    "R03",
    "R08",
    "R01",
    "R02",
    "R04",
    "R05",
    "R06",
    "R07",
  ]);

  // Chart: the section navigation comes before the section content.
  await page.goto("/residents");
  await expect(residentRows(page)).toHaveCount(10);
  await tabTo(page, page.getByRole("link", { name: "Open chart for R09" }));
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/residents\/R09$/);
  const navLinks = page.getByRole("navigation", { name: "Resident chart" }).getByRole("link");
  await expect(navLinks.nth(1)).toHaveAccessibleName("Review and notes, alarm not reviewed");
  await expect(page.getByRole("link", { name: "Review this alert" })).toBeVisible();
  await tabTo(page, navLinks.first());
  const order = await tabNames(page, 5);
  expect(order).toEqual([
    "Review and notes, alarm not reviewed",
    "Voice trends",
    "Baseline",
    "Check-in log",
    "Device",
  ]);
  await tabTo(page, navLinks.nth(2), 10, "Shift+Tab");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/residents\/R09\/trends$/);
  await page.goto("/residents/R09");
  const reviewThis = page.getByRole("link", { name: "Review this alert" });
  await tabTo(page, reviewThis);
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/residents\/R09\/review$/);

  // Review panel: checkboxes, Save review (no choice), radios, note, reminder.
  const panel = page.getByRole("region", { name: "Review alert: changed since Oct 21" });
  const firstBox = panel.getByRole("checkbox", { name: "Cold, cough or sore throat" });
  await tabTo(page, firstBox);
  await page.keyboard.press("Space");
  await expect(firstBox).toBeChecked();
  await page.keyboard.press("Tab");
  await expect(
    panel.getByRole("checkbox", { name: "Dental problem or dentures out" }),
  ).toBeFocused();

  const save = panel.getByRole("button", { name: "Save review" });
  await tabTo(page, save);
  await page.keyboard.press("Enter");
  await expect(panel.getByText("Choose what you found.", { exact: true })).toBeVisible();
  const radios = panel.getByRole("group", { name: "What did you find?" }).getByRole("radio");
  await expect(radios.first()).toBeFocused();
  await page.keyboard.press("Space");
  await expect(radios.first()).toBeChecked();
  await page.keyboard.press("ArrowDown");
  await expect(radios.nth(1)).toBeChecked();
  await expect(radios.nth(1)).toBeFocused();

  const note = panel.getByRole("textbox", { name: "Note" });
  await tabTo(page, note);
  await page.keyboard.type("Checked by keyboard.");
  await expect(note).toHaveValue("Checked by keyboard.");
  await tabTo(page, save);
  const remind = panel.getByRole("button", { name: "Remind me in 24 hours" });
  await tabTo(page, remind);
  await page.keyboard.press("Enter");
  await expect.poll(() => posts.filter((p) => p.endsWith("/snooze")).length).toBe(1);

  // Staff notes: type select, note textarea, Add note.
  const notes = page.getByRole("region", { name: "Staff notes" });
  const type = notes.getByRole("combobox", { name: "Type of note" });
  await tabTo(page, type);
  await page.keyboard.press("ArrowDown");
  await expect(type).not.toHaveValue("observation");
  const body = notes.getByRole("textbox", { name: "New note" });
  await tabTo(page, body);
  await page.keyboard.type("Keyboard note.");
  const add = notes.getByRole("button", { name: "Add note" });
  await tabTo(page, add);
  await page.keyboard.press("Enter");
  await expect.poll(() => posts.filter((p) => p.endsWith("/notes")).length).toBe(1);

  // Nothing reached the backend: only stubbed POSTs, and no review POST at all.
  expect(posts.some((p) => p.endsWith("/reviews"))).toBe(false);
});
