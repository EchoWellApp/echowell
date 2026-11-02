// req: FE-192, AC-FE-09, BR-01, BR-16, TPS-050, TPS-081, FEAT-076-FR-14
// No third-party requests (in particular no font service) and no <audio>/<video> anywhere.
import type { Page } from "@playwright/test";
import { test, expect } from "./fixtures";
import { API_BASE } from "./auth-store";
import { residentRows, settled } from "./helpers";

const ROUTES = [
  "/residents",
  "/residents?show=changed",
  "/residents/R09",
  "/residents/R09/review",
  "/residents/R09/trends",
  "/residents/R09/baseline",
  "/residents/R09/log",
  "/residents/R09/device",
  "/residents/R07/trends",
  "/residents/R08",
  "/residents/R08/trends",
  "/residents/R03/device",
  "/admissions",
  "/study",
  "/admin",
];

function trackOrigins(page: Page): Set<string> {
  const origins = new Set<string>();
  page.on("request", (r) => {
    const url = new URL(r.url());
    if (url.protocol === "data:" || url.protocol === "blob:") return;
    origins.add(url.origin);
  });
  return origins;
}

async function expectNoMedia(page: Page): Promise<void> {
  expect(await page.locator("audio, video").count()).toBe(0);
}

test("FE-192 only the frontend origin and the API origin are contacted; no audio or video", async ({
  page,
  as,
  baseURL,
}) => {
  const allowed = new Set([new URL(baseURL!).origin, new URL(API_BASE).origin]);
  const origins = trackOrigins(page);

  await page.goto("/login");
  await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();
  await expectNoMedia(page);

  await as("admin");
  for (const route of ROUTES) {
    await page.goto(route);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await settled(page);
    if (route.startsWith("/residents?") || route === "/residents") {
      await expect(residentRows(page).first()).toBeVisible();
    }
    await page.waitForLoadState("networkidle");
    await expectNoMedia(page);
  }

  expect([...origins].filter((o) => !allowed.has(o))).toEqual([]);
  expect([...origins].some((o) => /fonts\.(googleapis|gstatic)\.com/.test(o))).toBe(false);
});
