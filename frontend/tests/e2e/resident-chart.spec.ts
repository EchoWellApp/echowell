// req: FE-186, E2E-08, E2E-10, E2E-11, E2E-12, UX-262, AC-FE-03, FEAT-076-FR-04
// Resident chart sections with the DS-07 seed (TRD 11 §4.13.3; TRD 14 Table 4.9-B).
import type { Page } from "@playwright/test";
import { test, expect } from "./fixtures";
import {
  MEASUREMENT_LABELS,
  banner,
  bannerFact,
  chartNav,
  expectPill,
  logCounts,
  logLines,
  norm,
  pillTexts,
} from "./helpers";

interface Expected {
  code: string;
  device: string;
  last: string;
  usable: string;
  baseline: string;
  pill: string;
  lead: string;
  tiles: string[];
  baselineText: string;
  newestLog: string[];
  oldestLog: string;
  counts: number[];
}

const BASELINE_HELP =
  "First 16 usable check-ins, Oct 1–16, then frozen. Compared with it since Oct 17.";

const EXPECTED: Expected[] = [
  {
    code: "R09",
    device: "D09",
    last: "Oct 30, 2:28 PM CT",
    usable: "30 of 30",
    baseline: "Complete",
    pill: "▲ Changed",
    lead: "R09’s voice has moved away from their own usual pattern, steadily and long enough to set off the alarm on Oct 21. It is still changed.",
    tiles: ["Change score 26.8", "16 of 16 check-ins", "30 used, 0 missed", "D09 online"],
    baselineText: BASELINE_HELP,
    newestLog: [
      "Oct 21 Alarm on. Change score crossed 5.",
      "Oct 17 Comparing with baseline started.",
      "Oct 16 Baseline complete (16 of 16).",
    ],
    oldestLog: "Oct 1 Check-ins started.",
    counts: [30, 0, 0, 0],
  },
  {
    code: "R10",
    device: "D10",
    last: "Oct 30, 2:39 PM CT",
    usable: "30 of 30",
    baseline: "Complete",
    pill: "▲ Changed",
    lead: "R10’s voice has moved away from their own usual pattern, steadily and long enough to set off the alarm on Oct 24. It is still changed.",
    tiles: ["Change score 13.4", "16 of 16 check-ins", "30 used, 0 missed", "D10 online"],
    baselineText: BASELINE_HELP,
    newestLog: [
      "Oct 24 Alarm on. Change score crossed 5.",
      "Oct 17 Comparing with baseline started.",
      "Oct 16 Baseline complete (16 of 16).",
    ],
    oldestLog: "Oct 1 Check-ins started.",
    counts: [30, 0, 0, 0],
  },
  {
    code: "R08",
    device: "D08",
    last: "Oct 30, 2:28 PM CT",
    usable: "13 of 30",
    baseline: "13 of 16",
    pill: "! Needs attention",
    lead: "Missing many check-ins. Baseline stuck at 13 of 16. EchoWell can’t judge their voice well until more good check-ins come in.",
    tiles: ["Not scored yet", "13 of 16 check-ins", "13 used, 12 missed", "D08 online"],
    baselineText:
      "Still forming: 13 of 16 usable check-ins so far. 12 missed and 5 set-aside check-ins in the last 30 days have slowed it down.",
    newestLog: [
      "Oct 29 Check-in set aside: speech too short.",
      "Oct 27 Check-in missed.",
      "Oct 25 Check-in set aside: quality flag poor.",
    ],
    oldestLog: "Oct 1 Check-ins started.",
    counts: [13, 5, 0, 12],
  },
  {
    code: "R07",
    device: "D07B (replaced D07)",
    last: "Oct 30, 2:52 PM CT",
    usable: "30 of 30",
    baseline: "Complete",
    pill: "● Usual",
    lead: "R07’s voice is within their own usual range. Nothing to do. The baseline restarted on Oct 13 because the device changed (D07B, was D07); R07 is now compared only with the new baseline.",
    tiles: ["No change", "16 of 16 check-ins", "30 used, 0 missed", "D07B online"],
    baselineText:
      "Restarted Oct 13 when the device was replaced (D07 to D07B), so readings from the old device are not mixed in. First 16 usable check-ins, Oct 13–28, then frozen. Compared with it since Oct 29.",
    newestLog: [
      "Oct 29 Comparing with baseline started.",
      "Oct 28 Baseline complete (16 of 16).",
      "Oct 13 New device D07B. Baseline restarted.",
    ],
    oldestLog: "Oct 1 Check-ins started on D07.",
    counts: [30, 0, 0, 0],
  },
  {
    code: "R05",
    device: "D05",
    last: "Oct 30, 2:40 PM CT",
    usable: "28 of 30",
    baseline: "Complete",
    pill: "● Usual",
    lead: "R05’s voice is within their own usual range. Nothing to do.",
    tiles: ["No change", "16 of 16 check-ins", "28 used, 0 missed", "D05 online"],
    baselineText:
      "First 16 usable check-ins, Oct 1–17, then frozen. Compared with it since Oct 18.",
    newestLog: [
      "Oct 22 Check-in held back: possible other voice.",
      "Oct 18 Comparing with baseline started.",
      "Oct 17 Baseline complete (16 of 16).",
    ],
    oldestLog: "Oct 1 Check-ins started.",
    counts: [28, 0, 2, 0],
  },
  {
    code: "R03",
    device: "D02 (shared with R02)",
    last: "Oct 30, 2:19 PM CT",
    usable: "22 of 30",
    baseline: "Complete",
    pill: "! Needs attention",
    lead: "7 check-ins too noisy or too short to use. EchoWell can’t judge their voice well until more good check-ins come in.",
    tiles: ["No change", "16 of 16 check-ins", "22 used, 1 missed", "D02 online"],
    baselineText:
      "First 16 usable check-ins, Oct 1–23, then frozen. Compared with it since Oct 24.",
    newestLog: [
      "Oct 26 Check-in set aside: speech too short.",
      "Oct 24 Comparing with baseline started.",
      "Oct 23 Baseline complete (16 of 16).",
    ],
    oldestLog: "Oct 1 Check-ins started.",
    counts: [22, 7, 0, 1],
  },
  {
    code: "R02",
    device: "D02 (shared with R03)",
    last: "Oct 30, 2:55 PM CT",
    usable: "24 of 30",
    baseline: "Complete",
    pill: "● Usual",
    lead: "R02’s voice is within their own usual range. Nothing to do.",
    tiles: ["No change", "16 of 16 check-ins", "24 used, 6 missed", "D02 online"],
    baselineText:
      "First 16 usable check-ins, Oct 1–21, then frozen. Compared with it since Oct 22.",
    newestLog: [
      "Oct 23 Check-in missed.",
      "Oct 22 Comparing with baseline started.",
      "Oct 21 Baseline complete (16 of 16).",
    ],
    oldestLog: "Oct 1 Check-ins started.",
    counts: [24, 0, 0, 6],
  },
];

async function expectBanner(page: Page, e: Expected): Promise<void> {
  await expect(page.getByRole("link", { name: "← Resident list" })).toBeVisible();
  await expect(banner(page).getByRole("heading", { level: 1 })).toHaveText(e.code);
  await expect(bannerFact(page, "Device")).toHaveText(e.device);
  await expect(bannerFact(page, "Last check-in")).toHaveText(e.last);
  await expect(bannerFact(page, "Usable check-ins, last 30 days")).toHaveText(e.usable);
  await expect(bannerFact(page, "Baseline")).toHaveText(e.baseline);
  await expect.poll(() => pillTexts(banner(page))).toEqual([e.pill]);
}

async function tileTexts(page: Page): Promise<string[]> {
  const tiles = page.getByRole("region", { name: "More detail" }).getByRole("link");
  await expect(tiles).toHaveCount(4);
  return tiles.evaluateAll((els) =>
    els.map((el) => {
      // Tile = label, value, "Open"; keep the value only.
      const parts = Array.from(el.children).map((c) => (c.textContent ?? "").trim());
      return parts[1] ?? "";
    }),
  );
}

test.beforeEach(async ({ as }) => {
  await as("clinician");
});

for (const e of EXPECTED) {
  test(`FE-186 ${e.code} banner, Summary, Baseline and Check-in log`, async ({ page }) => {
    await page.goto(`/residents/${e.code}`);
    await expect(page).toHaveTitle(`${e.code} · Summary – EchoWell`);
    await expectBanner(page, e);
    const now = page.getByRole("region", { name: "Right now" });
    await expect(now.locator("p").first()).toHaveText(e.lead);
    expect(await tileTexts(page)).toEqual(e.tiles);

    await page.goto(`/residents/${e.code}/baseline`);
    await expect(
      page
        .getByRole("region", { name: `Baseline: ${e.code}’s usual` })
        .locator("p")
        .first(),
    ).toHaveText(e.baselineText);

    await page.goto(`/residents/${e.code}/log`);
    expect(await logCounts(page)).toEqual(e.counts);
    const lines = await logLines(page);
    expect(lines.slice(0, 3)).toEqual(e.newestLog);
    expect(lines.at(-1)).toBe(e.oldestLog);
  });
}

test("E2E-08 R09 from the list through Voice trends, Baseline and Check-in log", async ({
  page,
}) => {
  await page.goto("/residents");
  await page.getByRole("link", { name: "Open chart for R09" }).click();
  await expect(page).toHaveURL(/\/residents\/R09$/);
  await expectBanner(page, EXPECTED[0]!);

  const nav = chartNav(page);
  await expect(nav.getByRole("link")).toHaveCount(6);
  await expect(nav.getByRole("link")).toHaveText([
    "Summary",
    /^Review and notes/,
    "Voice trends",
    "Baseline",
    "Check-in log",
    "Device",
  ]);
  const reviewLink = nav.getByRole("link", { name: "Review and notes, alarm not reviewed" });
  await expect(reviewLink.locator("[data-count]")).toHaveAttribute("data-count", "1");

  const now = page.getByRole("region", { name: "Right now" });
  await expect(now.locator("p").first()).toHaveText(EXPECTED[0]!.lead);
  const facts = norm(await now.innerText());
  expect(facts).toContain("Oct 21 Alarm started");
  expect(facts).toContain("9 days Open");
  expect(facts).toContain("Not reviewed Review status");
  await expect(
    now.getByText("Leaning most: more pauses, quieter, less voiced sound", { exact: true }),
  ).toBeVisible();
  await expect(now.getByRole("link", { name: "Review this alert" })).toHaveAttribute(
    "href",
    "/residents/R09/review",
  );
  await expect(now.getByRole("link", { name: "See what changed" })).toHaveAttribute(
    "href",
    "/residents/R09/trends",
  );
  expect(await tileTexts(page)).toEqual(EXPECTED[0]!.tiles);

  // Voice trends
  await nav.getByRole("link", { name: "Voice trends" }).click();
  await expect(page).toHaveURL(/\/residents\/R09\/trends$/);
  const chart = page.getByRole("region", { name: "Change score chart" });
  await expect(chart.getByText("Baseline Oct 1–16")).toBeVisible();
  const bars = chart.getByTestId("score-bar");
  await expect(bars).toHaveCount(14);
  const fills = await bars.evaluateAll((els) =>
    els.map((g) => ({
      date: g.getAttribute("data-date"),
      fill: g.querySelector("rect")?.getAttribute("fill"),
    })),
  );
  expect(fills.map((f) => f.date)).toEqual(
    Array.from({ length: 14 }, (_, i) => `2026-10-${String(17 + i).padStart(2, "0")}`),
  );
  expect(fills.slice(0, 4).every((f) => f.fill === "var(--c-aside)")).toBe(true);
  expect(fills.slice(4).every((f) => f.fill === "var(--red)")).toBe(true);
  await expect(chart.getByTestId("alarm-line-label")).toHaveText("Alarm line: 5");
  await expect(chart.getByTestId("alarm-marker")).toHaveText("▲");
  await expect(chart.getByText("Oct 21 · alarm")).toBeVisible();

  const cards = page.getByRole("region", { name: "The 7 voice measurements behind the score" });
  const items = cards.getByRole("listitem");
  await expect(items).toHaveCount(8);
  for (const [i, label] of MEASUREMENT_LABELS.entries()) {
    await expect(items.nth(i)).toContainText(label);
  }
  await expect(items.nth(7)).toContainText(
    "12 other measurements (pitch, jitter, MFCCs and others)",
  );
  await expect(items.nth(7)).toContainText("Stored, not scored");

  // Baseline
  await nav.getByRole("link", { name: "Baseline" }).click();
  await expect(page).toHaveURL(/\/residents\/R09\/baseline$/);
  await expect(page.getByText(BASELINE_HELP, { exact: true })).toBeVisible();

  // Check-in log
  await nav.getByRole("link", { name: "Check-in log" }).click();
  await expect(page).toHaveURL(/\/residents\/R09\/log$/);
  expect(await logCounts(page)).toEqual([30, 0, 0, 0]);
  expect((await logLines(page)).slice(0, 3)).toEqual(EXPECTED[0]!.newestLog);
});

test("E2E-10 device move R07", async ({ page }) => {
  await page.goto("/residents/R07");
  await expect.poll(() => pillTexts(banner(page))).toEqual(["● Usual"]);
  await expect(bannerFact(page, "Device")).toHaveText("D07B (replaced D07)");
  await expect(page.getByRole("region", { name: "Right now" }).locator("p").first()).toHaveText(
    EXPECTED[3]!.lead,
  );

  await chartNav(page).getByRole("link", { name: "Check-in log" }).click();
  const lines = await logLines(page);
  expect(lines).toContain("Oct 28 Baseline complete (16 of 16).");
  expect(lines).toContain("Oct 13 New device D07B. Baseline restarted.");
  expect(lines.at(-1)).toBe("Oct 1 Check-ins started on D07.");

  await chartNav(page).getByRole("link", { name: "Voice trends" }).click();
  await expect(
    page.getByText(
      "Showing the current device period since Oct 13. Earlier periods are not scored against this baseline.",
      { exact: true },
    ),
  ).toBeVisible();
  const chart = page.getByRole("region", { name: "Change score chart" });
  await expect(chart.getByText("Baseline Oct 13–28")).toBeVisible();
  const bars = chart.getByTestId("score-bar");
  await expect(bars).toHaveCount(2);
  expect(await bars.evaluateAll((els) => els.map((g) => g.getAttribute("data-date")))).toEqual([
    "2026-10-29",
    "2026-10-30",
  ]);

  await chartNav(page).getByRole("link", { name: "Baseline" }).click();
  await expect(
    page.getByRole("region", { name: "Baseline: R07’s usual" }).locator("p").first(),
  ).toHaveText(/^Restarted Oct 13 when the device was replaced \(D07 to D07B\)/);
});

test("E2E-11 Needs attention R08", async ({ page }) => {
  await page.goto("/residents/R08");
  await expect.poll(() => pillTexts(banner(page))).toEqual(["! Needs attention"]);
  await expect(bannerFact(page, "Baseline")).toHaveText("13 of 16");
  await expect(bannerFact(page, "Usable check-ins, last 30 days")).toHaveText("13 of 30");
  const now = page.getByRole("region", { name: "Right now" });
  await expect(now.locator("p").first()).toHaveText(EXPECTED[2]!.lead);
  await expect(now.getByRole("link", { name: "See missed and set-aside check-ins" })).toBeVisible();
  await expect(now.getByRole("link", { name: "Check the device" })).toBeVisible();

  await chartNav(page).getByRole("link", { name: "Voice trends" }).click();
  await expect(
    page.getByText(
      "No change score yet. Scoring starts after the baseline is complete (13 of 16 usable check-ins so far).",
      { exact: true },
    ),
  ).toBeVisible();
  const cards = page
    .getByRole("region", { name: "The 7 voice measurements behind the score" })
    .getByRole("listitem");
  await expect(cards).toHaveCount(8);
  for (const [i, label] of MEASUREMENT_LABELS.entries()) {
    await expect(cards.nth(i)).toContainText(label);
    await expect(cards.nth(i)).toContainText("Not scored yet");
  }
  await expect(page.locator("main").getByRole("alert").filter({ hasText: /\S/ })).toHaveCount(0);

  await chartNav(page).getByRole("link", { name: "Check-in log" }).click();
  expect(await logCounts(page)).toEqual([13, 5, 0, 12]);
  const lines = await logLines(page);
  expect(lines.filter((l) => / Check-in missed\.$/.test(l))).toHaveLength(12);
  expect(lines.filter((l) => / Check-in set aside: .+/.test(l))).toHaveLength(5);
  await expect(page.locator("main").getByRole("alert").filter({ hasText: /\S/ })).toHaveCount(0);
});

test("E2E-12 set-aside reasons and silent device R03", async ({ page }) => {
  await page.goto("/residents/R03/log");
  const lines = await logLines(page);
  expect(lines).toContain("Oct 18 Check-in set aside: quality flag poor; noise above limit.");
  expect(lines).toContain("Oct 12 Shared device D02 silent all day. Check-in missed.");

  await page.goto("/residents/R03/device");
  const device = page.getByRole("region", { name: "Device D02" });
  await expect(device.getByRole("heading", { level: 2 })).toHaveText("Device D02");
  await expect(device.locator('dt:text-is("Status") + dd')).toHaveText(/^●\s*Online$/);
  await expect(device.locator('dt:text-is("Last upload") + dd')).toHaveText("Oct 30, 2:55 PM CT");
  await expect(device.locator('dt:text-is("Firmware") + dd')).toHaveText("fw-1.0.0");
  await expect(device.locator('dt:text-is("Used by") + dd')).toHaveText("Shared with R02");
  await expect(device.getByRole("heading", { level: 3 })).toHaveText("History");
  expect(norm(await device.innerText())).toContain("Oct 12 Silent all day. Affected R02 and R03.");
});

test("FE-186 Device section of R07 and of a resident without problems", async ({ page }) => {
  await page.goto("/residents/R07/device");
  const device = page.getByRole("region", { name: "Device D07B" });
  await expect(device.locator('dt:text-is("Status") + dd')).toHaveText(/^●\s*Online$/);
  await expect(device.locator('dt:text-is("Last upload") + dd')).toHaveText("Oct 30, 2:52 PM CT");
  await expect(device.locator('dt:text-is("Firmware") + dd')).toHaveText("fw-1.0.0");
  await expect(device.locator('dt:text-is("Used by") + dd')).toHaveText("This resident only");
  expect(norm(await device.innerText())).toContain(
    "Oct 13 Replaced D07 with D07B. Baseline restarted.",
  );

  await page.goto("/residents/R09/device");
  await expect(
    page.getByRole("region", { name: "Device D09" }).getByText("No problems in the last 30 days."),
  ).toBeVisible();
  await expectPill(page.locator("main"), "▲ Changed");
});
