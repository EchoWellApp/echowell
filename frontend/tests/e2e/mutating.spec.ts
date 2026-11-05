// req: E2E-18, FE-193 (reminder step), E2E-09, FE-187, UX-316, UX-317, UX-318, UX-320, UX-330,
// AC-FE-10, OQ-05, D-73, D-118, FEAT-076-FR-05, FR-06, FR-07
// The @mutating group of TRD 24 D-73 as amended by D-118, serial and in this order:
// (1) E2E-18 on R09; (2) the FE-193 reminder step on R10; (3) E2E-09 = FE-187 on R10.
// Runs only through `test:e2e:mutating` (--workers=1), after every read-only scenario.
import type { Page } from "@playwright/test";
import { test, expect } from "./fixtures";
import { readSession } from "./auth-store";
import { API, authHeader, banner, chartNav, norm, pillTexts, residentRows } from "./helpers";

const WHEN = /[A-Z][a-z]{2} \d{1,2}, \d{1,2}:\d{2} [AP]M CT/.source;
const CLINICIAN = "Clinician";

/** "<Mon D, h:mm AM/PM CT>" in the facility time zone (TRD 24 D-119). */
function facilityTime(ms: number): string {
  const s = new Intl.DateTimeFormat("en-US", {
    timeZone: process.env.FACILITY_TZ ?? "America/Chicago",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(ms));
  return `${s.replace(/ /g, " ")} CT`;
}

async function expectSummary(page: Page, code: string, status: string, score: string) {
  await page.goto(`/residents/${code}`);
  const now = page.getByRole("region", { name: "Right now" });
  await expect(now.getByRole("link", { name: "Review this alert" })).toBeVisible();
  await expect.poll(async () => norm(await now.innerText())).toContain(`${status} Review status`);
  await expect.poll(() => pillTexts(banner(page))).toEqual(["▲ Changed"]);
  const tile = page
    .getByRole("region", { name: "More detail" })
    .getByRole("link", { name: /^Voice trends/ });
  await expect(tile).toContainText(`Change score ${score}`);
}

async function listText(page: Page, code: string): Promise<string> {
  await page.goto("/residents");
  await expect(residentRows(page)).toHaveCount(10);
  const row = residentRows(page).filter({
    has: page.getByRole("link", { name: `Open chart for ${code}` }),
  });
  expect(await pillTexts(row.locator("td").nth(0))).toEqual(["▲ Changed"]);
  return norm(await row.locator("td").nth(2).innerText());
}

test.describe("@mutating D-73 group", () => {
  test.describe.configure({ mode: "serial" });

  test.beforeEach(async ({ as }) => {
    await as("clinician");
  });

  test("(1) E2E-18 save review on R09", async ({ page }) => {
    const reviewPosts: string[] = [];
    page.on("request", (r) => {
      if (r.method() === "POST" && r.url().includes("/reviews")) reviewPosts.push(r.url());
    });
    await page.goto("/residents/R09/review");
    const panel = page.getByRole("region", { name: "Review alert: changed since Oct 21" });
    await expect(panel.getByRole("heading", { level: 2 })).toHaveText(
      "Review alert: changed since Oct 21",
    );

    await panel.getByRole("button", { name: "Save review" }).click();
    await expect(panel.getByText("Choose what you found.", { exact: true })).toBeVisible();
    await expect(panel.getByText("Not reviewed yet.", { exact: true })).toBeVisible();
    expect(reviewPosts).toEqual([]);

    await panel.getByRole("radio", { name: "Checked on resident, no concern" }).check();
    await panel.getByRole("button", { name: "Save review" }).click();
    await expect(panel.getByRole("status").filter({ hasText: "Review saved." })).toHaveText(
      "Review saved.",
    );
    expect(reviewPosts).toHaveLength(1);
    const reviews = panel.getByRole("listitem");
    await expect(reviews).toHaveCount(1);
    await expect(reviews.first()).toHaveText(
      new RegExp(`^${WHEN} · ${CLINICIAN} · Checked on resident, no concern`),
    );
    await expect(panel.getByText("Not reviewed yet.", { exact: true })).toHaveCount(0);

    // Badges: nav "1" (only not-yet-reviewed alarms), R09 section badge gone.
    const listLink = page
      .getByRole("navigation", { name: "Main" })
      .getByRole("link", { name: "Resident list, 1 alarm not reviewed" });
    await expect(listLink).toBeVisible();
    await expect(listLink.locator("[data-count]")).toHaveAttribute("data-count", "1");
    await expect(
      chartNav(page).getByRole("link", { name: /^Review and notes/ }),
    ).toHaveAccessibleName("Review and notes");

    await expectSummary(page, "R09", "Reviewed", "26.8");
    expect(await listText(page, "R09")).toBe("Changed from their usual since Oct 21. Reviewed.");
  });

  test("(2) FE-193 reminder step on R10", async ({ page, request }) => {
    await page.goto("/residents/R10/review");
    const panel = page.getByRole("region", { name: "Review alert: changed since Oct 24" });
    const remind = panel.getByRole("button", { name: "Remind me in 24 hours" });
    await expect(remind).toBeVisible();
    const before = Date.now();
    await remind.click();
    const announced = panel
      .getByRole("status")
      .filter({ hasText: /Reminder set for .*\. The alarm stays on\./ });
    await expect(announced).toBeVisible();
    const after = Date.now();
    const text = norm(await announced.innerText());
    const m = new RegExp(`^Reminder set for (${WHEN})\\. The alarm stays on\\.$`).exec(text);
    expect(m, text).not.toBeNull();
    const candidates = new Set(
      [before, after].flatMap((t) =>
        [-60_000, 0, 60_000].map((d) => facilityTime(t + 24 * 3600_000 + d)),
      ),
    );
    expect([...candidates]).toContain(m![1]);
    await expect(panel.getByText(`Reminder set for ${m![1]}.`, { exact: true })).toBeVisible();
    await expect(panel.getByText("Not reviewed yet.", { exact: true })).toBeVisible();

    const { token } = readSession("clinician", process.env.E2E_AUTH_PREFIX ?? "");
    const res = await request.get(`${API}/alerts?status=open&resident_code=R10`, {
      headers: authHeader(token),
    });
    const alert = (
      (await res.json()) as { items: { snoozed_until: string | null; reviewed: boolean }[] }
    ).items[0]!;
    const until = Date.parse(alert.snoozed_until!);
    expect(until).toBeGreaterThanOrEqual(before + 24 * 3600_000 - 120_000);
    expect(until).toBeLessThanOrEqual(after + 24 * 3600_000 + 120_000);
    expect(alert.reviewed).toBe(false);

    await expectSummary(page, "R10", "Not reviewed", "13.4");
    expect(await listText(page, "R10")).toBe(
      "Changed from their usual since Oct 24. Not reviewed yet.",
    );
  });

  test("(3) E2E-09 / FE-187 staff note and review on R10", async ({ page, request }) => {
    await page.goto("/residents/R10/review");
    const notes = page.getByRole("region", { name: "Staff notes" });
    await notes
      .getByRole("combobox", { name: "Type of note" })
      .selectOption({ label: "Observation" });
    await notes
      .getByRole("textbox", { name: "New note" })
      .fill("Resident has a cold; nurse notified.");
    await notes.getByRole("button", { name: "Add note" }).click();
    await expect(notes.getByRole("status").filter({ hasText: "Note saved." })).toHaveText(
      "Note saved.",
    );
    await expect(notes.getByRole("heading", { level: 3, name: "Previous notes" })).toBeVisible();
    const noteItem = notes.getByRole("listitem").first();
    await expect(noteItem).toContainText("Resident has a cold; nurse notified.");
    await expect(noteItem).toContainText(new RegExp(`${WHEN} · Observation · ${CLINICIAN}`));

    const panel = page.getByRole("region", { name: "Review alert: changed since Oct 24" });
    await panel.getByRole("checkbox", { name: "Cold, cough or sore throat" }).check();
    await panel.getByRole("radio", { name: "Explained by a known cause" }).check();
    await panel.getByRole("button", { name: "Save review" }).click();
    await expect(panel.getByRole("status").filter({ hasText: "Review saved." })).toHaveText(
      "Review saved.",
    );
    const review = panel.getByRole("listitem").first();
    await expect(review).toContainText(
      new RegExp(`${WHEN} · ${CLINICIAN} · Explained by a known cause`),
    );
    await expect(review).toContainText("Possible explanations: Cold, cough or sore throat");
    await expect(
      chartNav(page).getByRole("link", { name: /^Review and notes/ }),
    ).toHaveAccessibleName("Review and notes");

    const { token } = readSession("clinician", process.env.E2E_AUTH_PREFIX ?? "");
    const res = await request.get(`${API}/alerts?resident_code=R10`, {
      headers: authHeader(token),
    });
    const alert = ((await res.json()) as { items: { status: string; reviewed: boolean }[] })
      .items[0]!;
    expect(alert.status).toBe("acknowledged");
    expect(alert.reviewed).toBe(true);

    await expectSummary(page, "R10", "Reviewed", "13.4");
    expect(await listText(page, "R10")).toBe("Changed from their usual since Oct 24. Reviewed.");
  });
});
