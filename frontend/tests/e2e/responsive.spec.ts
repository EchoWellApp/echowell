// req: FE-191, E2E-16, UX-223, UX-240, UX-241, UX-242, UX-243, D-78, FEAT-075-AC-02, AC-03, AC-07,
// FEAT-076-FR-15
// Phone widths and the wide layout (TRD 11 §4.12).
import type { Locator, Page } from "@playwright/test";
import { test, expect } from "./fixtures";
import { chartNav, residentRows } from "./helpers";

const VIEWPORTS = [
  { width: 320, height: 568 },
  { width: 360, height: 800 },
  { width: 375, height: 812 },
  { width: 390, height: 844 },
];
const ROUTES = ["/residents", "/residents/R09", "/residents/R09/trends"];

async function ready(page: Page, route: string): Promise<void> {
  await page.goto(route);
  if (route === "/residents") await expect(residentRows(page)).toHaveCount(10);
  else await expect(chartNav(page)).toBeVisible();
  if (route.endsWith("/trends")) {
    await expect(page.getByTestId("score-bar")).toHaveCount(14);
  }
  if (route === "/residents/R09") {
    await expect(page.getByRole("region", { name: "More detail" }).getByRole("link")).toHaveCount(
      4,
    );
  }
}

async function expectNoPageScroll(page: Page): Promise<void> {
  const { scrollWidth, innerWidth } = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth: window.innerWidth,
  }));
  expect(scrollWidth).toBeLessThanOrEqual(innerWidth);
}

async function expectScrollsInside(container: Locator): Promise<void> {
  await expect(container).toHaveAttribute("tabindex", "0");
  const { scrollWidth, clientWidth, overflowX } = await container.evaluate((el) => ({
    scrollWidth: el.scrollWidth,
    clientWidth: el.clientWidth,
    overflowX: getComputedStyle(el).overflowX,
  }));
  expect(["auto", "scroll"]).toContain(overflowX);
  expect(scrollWidth).toBeGreaterThan(clientWidth);
}

/** Chart section navigation is one horizontally scrolling row above the content (UX-241). */
async function expectNavRow(page: Page): Promise<void> {
  const nav = chartNav(page);
  const style = await nav.evaluate((el) => {
    const cs = getComputedStyle(el);
    return { overflowX: cs.overflowX, whiteSpace: cs.whiteSpace, flexWrap: cs.flexWrap };
  });
  expect(["auto", "scroll"]).toContain(style.overflowX);
  expect(style.flexWrap).not.toBe("wrap");
  const tops = await nav
    .getByRole("link")
    .evaluateAll((els) => els.map((e) => Math.round(e.getBoundingClientRect().top)));
  expect(tops).toHaveLength(6);
  expect(new Set(tops).size).toBe(1);
  const navBox = (await nav.boundingBox())!;
  const contentBox = (await page.locator("main section").last().boundingBox())!;
  expect(navBox.y + navBox.height).toBeLessThanOrEqual(contentBox.y + 1);
}

/** Every interactive target in the header and main is at least 44 × 44 px, except inline links. */
async function expectTouchTargets(page: Page): Promise<void> {
  const small = await page.evaluate(() => {
    const out: string[] = [];
    const els = document.querySelectorAll<HTMLElement>(
      "header a, header button, main a, main button, main summary, main select, main [role='button']",
    );
    for (const el of els) {
      if (el.closest("p") && el.tagName === "A") continue; // inline links within text
      const r = el.getBoundingClientRect();
      if (r.width === 0 && r.height === 0) continue;
      const cs = getComputedStyle(el);
      if (cs.visibility === "hidden" || cs.display === "none") continue;
      if (r.height < 44 - 0.5 || r.width < 44 - 0.5) {
        out.push(
          `${el.tagName} "${(el.textContent ?? "").trim().slice(0, 40)}" ${r.width}×${r.height}`,
        );
      }
    }
    return out;
  });
  expect(small).toEqual([]);
}

test.beforeEach(async ({ as }) => {
  await as("clinician");
});

for (const vp of VIEWPORTS) {
  test.describe(`${vp.width}×${vp.height}`, () => {
    test.use({ viewport: vp });

    for (const route of ROUTES) {
      test(`FE-191 / E2E-16 ${route}`, async ({ page }) => {
        await ready(page, route);
        await expectNoPageScroll(page);
        await expectTouchTargets(page);
        if (route === "/residents") {
          await expectScrollsInside(page.getByRole("region", { name: "Residents table" }));
        } else {
          await expectNavRow(page);
        }
        if (route.endsWith("/trends")) {
          await expectScrollsInside(page.getByRole("region", { name: "Change score chart" }));
        }
      });
    }
  });
}

test.describe("wide layout 1280px", () => {
  test.use({ viewport: { width: 1280, height: 900 } });

  test("FEAT-075-AC-07 200px section navigation beside the content, tiles in one row", async ({
    page,
  }) => {
    await ready(page, "/residents/R09");
    await expectNoPageScroll(page);
    const navBox = (await chartNav(page).boundingBox())!;
    expect(Math.round(navBox.width)).toBe(200);
    const content = (await page.getByRole("region", { name: "Right now" }).boundingBox())!;
    expect(content.x).toBeGreaterThanOrEqual(navBox.x + navBox.width);
    expect(Math.abs(content.y - navBox.y)).toBeLessThan(40);
    const tops = await page
      .getByRole("region", { name: "More detail" })
      .getByRole("link")
      .evaluateAll((els) => els.map((e) => Math.round(e.getBoundingClientRect().top)));
    expect(new Set(tops).size).toBe(1);
  });
});

test.describe("narrow layout 600px", () => {
  test.use({ viewport: { width: 600, height: 900 } });

  test("FEAT-075-AC-07 tiles stack in one column and page padding is 12px", async ({ page }) => {
    await ready(page, "/residents/R09");
    await expectNoPageScroll(page);
    const lefts = await page
      .getByRole("region", { name: "More detail" })
      .getByRole("link")
      .evaluateAll((els) => els.map((e) => Math.round(e.getBoundingClientRect().left)));
    expect(new Set(lefts).size).toBe(1);
    const padding = await page
      .locator("main")
      .evaluate((el) => [getComputedStyle(el).paddingLeft, getComputedStyle(el).paddingRight]);
    expect(padding).toEqual(["12px", "12px"]);
  });
});
