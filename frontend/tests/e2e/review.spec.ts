// req: FE-193 (read-only part), E2E-17, UX-310, UX-312..UX-317, UX-320, UX-321, UX-330, UX-331,
// AC-FE-11, FEAT-076-FR-04
// Alarm entry points and the review panels with the pristine DS-07 seed (TRD 11 §4.17.5; TRD 14
// Tables 4.9-C, 4.9-D). The reminder step of FE-193 saves data and lives in mutating.spec.ts.
import type { Page } from "@playwright/test";
import { test, expect } from "./fixtures";
import { ALL_CODES, DATA_PROBLEMS, chartNav, expectRowCodes, norm, residentRows } from "./helpers";

const EXPLANATIONS = [
  "Cold, cough or sore throat",
  "Dental problem or dentures out",
  "New or changed medication",
  "Poor sleep or unusual day",
  "Room or device moved",
];
const OUTCOMES = [
  "Checked on resident, no concern",
  "Explained by a known cause",
  "Referred to nurse or provider",
  "Looks like a data problem: send to study team",
];
const OPEN_QUESTIONS =
  "Open questions (OQ-05, OQ-26): Does a saved review reset the change score or turn the alarm off? Who may review? How soon must an alarm be reviewed? Pipeline v0.1 keeps alarms on.";

async function summaryFacts(page: Page, code: string): Promise<string> {
  await page.goto(`/residents/${code}`);
  const now = page.getByRole("region", { name: "Right now" });
  await expect(now.getByRole("link", { name: "Review this alert" })).toBeVisible();
  // Wait for the alarm facts, which load separately (no "Loading …" text, no "—" placeholders).
  await expect(now).toContainText("Alarm started");
  await expect(now).not.toContainText(/Loading|—/);
  return norm(await now.innerText());
}

async function changeScoreTile(page: Page): Promise<string> {
  const tile = page
    .getByRole("region", { name: "More detail" })
    .getByRole("link", { name: /^Voice trends/ });
  await expect(tile).toContainText("Change score"); // loaded, not the "—" placeholder
  return norm(await tile.innerText());
}

async function expectReviewPanel(page: Page, code: string, since: string): Promise<void> {
  await page.goto(`/residents/${code}/review`);
  const panel = page.getByRole("region", { name: `Review alert: changed since ${since}` });
  await expect(panel.getByRole("heading", { level: 2 })).toHaveText(
    `Review alert: changed since ${since}`,
  );
  const explain = panel.getByRole("group", { name: "Anything that could explain it?" });
  await expect(explain.getByRole("checkbox")).toHaveCount(5);
  for (const [i, label] of EXPLANATIONS.entries()) {
    await expect(explain.getByRole("checkbox").nth(i)).toHaveAccessibleName(label);
    await expect(explain.getByRole("checkbox").nth(i)).not.toBeChecked();
  }
  await expect(
    explain.getByText("Provisional list — to be confirmed with the clinical team (OQ-25)."),
  ).toBeVisible();
  const found = panel.getByRole("group", { name: "What did you find?" });
  await expect(found.getByRole("radio")).toHaveCount(4);
  for (const [i, label] of OUTCOMES.entries()) {
    await expect(found.getByRole("radio").nth(i)).toHaveAccessibleName(label);
    await expect(found.getByRole("radio").nth(i)).not.toBeChecked();
  }
  await expect(panel.getByRole("textbox", { name: "Note" })).toHaveAttribute(
    "placeholder",
    "What you saw or did",
  );
  await expect(panel.getByText("0 / 2000")).toBeVisible();
  await expect(panel.getByRole("button", { name: "Save review" })).toBeVisible();
  await expect(panel.getByRole("button", { name: "Remind me in 24 hours" })).toBeVisible();
  await expect(panel.getByRole("heading", { level: 3, name: "Previous reviews" })).toBeVisible();
  await expect(panel.getByText("Not reviewed yet.", { exact: true })).toBeVisible();
  await expect(panel.getByText(OPEN_QUESTIONS, { exact: true })).toBeVisible();
  await expect(page.getByRole("region", { name: "Staff notes" })).toBeVisible();
}

test.describe("as clinician", () => {
  test.beforeEach(async ({ as }) => {
    await as("clinician");
  });

  test("E2E-17 alarm entry points: nav badge, list and Summaries", async ({ page }) => {
    await page.goto("/residents");
    const listLink = page
      .getByRole("navigation", { name: "Main" })
      .getByRole("link", { name: "Resident list, 2 alarms not reviewed" });
    await expect(listLink).toBeVisible();
    await expect(listLink.locator("[data-count]")).toHaveAttribute("data-count", "2");
    await expectRowCodes(page, ALL_CODES);
    await expect(residentRows(page).nth(0).locator("td").nth(2)).toHaveText(
      /^Changed from their usual since Oct 21\. Not reviewed yet\.$/,
    );
    await expect(residentRows(page).nth(1).locator("td").nth(2)).toHaveText(
      /^Changed from their usual since Oct 24\. Not reviewed yet\.$/,
    );

    const r09 = await summaryFacts(page, "R09");
    expect(r09).toContain("Oct 21 Alarm started");
    expect(r09).toContain("9 days Open");
    expect(r09).toContain("Not reviewed Review status");
    expect(await changeScoreTile(page)).toContain("Change score 26.8");

    const r10 = await summaryFacts(page, "R10");
    expect(r10).toContain("Oct 24 Alarm started");
    expect(r10).toContain("6 days Open");
    expect(r10).toContain("Not reviewed Review status");
    expect(await changeScoreTile(page)).toContain("Change score 13.4");
  });

  test("FE-193 Summary facts, Leaning most and buttons of R09 and R10", async ({ page }) => {
    const r09 = await summaryFacts(page, "R09");
    expect(r09).toContain("Oct 21 Alarm started 9 days Open Not reviewed Review status");
    expect(r09).toContain("Leaning most: more pauses, quieter, less voiced sound");
    const now = page.getByRole("region", { name: "Right now" });
    await expect(now.getByRole("link", { name: "Review this alert" })).toBeVisible();
    await expect(now.getByRole("link", { name: "See what changed" })).toBeVisible();

    const r10 = await summaryFacts(page, "R10");
    expect(r10).toContain("Oct 24 Alarm started 6 days Open");
    expect(r10).toContain(
      "Leaning most: more pauses, slower while talking, fewer syllables per second",
    );
  });

  test("FE-193 Review and notes badge 1 on R09 and R10 only", async ({ page }) => {
    for (const code of ALL_CODES) {
      await page.goto(`/residents/${code}`);
      const nav = chartNav(page);
      await expect(nav.getByRole("link", { name: "Summary" })).toBeVisible();
      const review = nav.getByRole("link", { name: /^Review and notes/ });
      if (code === "R09" || code === "R10") {
        await expect(review).toHaveAccessibleName("Review and notes, alarm not reviewed");
        await expect(review.locator("[data-count]")).toHaveAttribute("data-count", "1");
      } else {
        await expect(review).toHaveAccessibleName("Review and notes");
        await expect(review.locator("[data-count]")).toHaveCount(0);
      }
    }
  });

  test("FE-193 review panels of R09 and R10 (TRD 11 §4.17.5)", async ({ page }) => {
    await expectReviewPanel(page, "R09", "Oct 21");
    await expectReviewPanel(page, "R10", "Oct 24");
  });

  test("FE-193 other residents have no review panel, Staff notes only", async ({ page }) => {
    await page.goto("/residents/R01/review");
    await expect(page.getByRole("region", { name: "Staff notes" })).toBeVisible();
    await expect(page.getByRole("heading", { name: /^Review alert/ })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Save review" })).toHaveCount(0);
  });

  test("FE-193 Save review without a choice shows the error and saves nothing", async ({
    page,
  }) => {
    const posts: string[] = [];
    page.on("request", (r) => {
      if (r.method() === "POST") posts.push(r.url());
    });
    await page.goto("/residents/R09/review");
    const panel = page.getByRole("region", { name: "Review alert: changed since Oct 21" });
    await panel.getByRole("button", { name: "Save review" }).click();
    await expect(panel.getByText("Choose what you found.", { exact: true })).toBeVisible();
    const found = panel.getByRole("group", { name: "What did you find?" });
    await expect(found).toHaveAccessibleDescription(/Choose what you found\./);
    await expect(found.getByRole("radio").first()).toBeFocused();
    await expect(panel.getByText("Not reviewed yet.", { exact: true })).toBeVisible();
    expect(posts).toEqual([]);
  });
});

test("E2E-17 Study team data problems (researcher)", async ({ page, as }) => {
  await as("researcher");
  await page.goto("/study");
  const panel = page.getByRole("region", { name: "Data problems to follow up" });
  const rows = panel.getByRole("listitem");
  await expect(rows).toHaveCount(4);
  for (const [i, [tag, code, detail]] of DATA_PROBLEMS.entries()) {
    await expect
      .poll(async () => norm(await rows.nth(i).innerText()))
      .toBe(`${tag} ${code} ${detail}`);
  }
});
