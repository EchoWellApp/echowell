// req: FE-194, E2E-07, E2E-20, E2E-21, UX-263, UX-350..UX-384, UX-331, AC-FE-11, FEAT-076-FR-04
// Study team page with the DS-07 seed (TRD 11 §4.13.4, §4.18.8; TRD 14 Tables 4.9-D, 4.9-E).
import type { Page } from "@playwright/test";
import { test, expect } from "./fixtures";
import { readSession } from "./auth-store";
import { API, DATA_PROBLEMS, authHeader, norm } from "./helpers";

const DEVICE_ROWS = [
  "● Online D01, D04 to D06, D08 to D10: all uploaded Oct 30. Firmware fw-1.0.0.",
  "● Online D02 (shared by R02 and R03): last upload Oct 30, 2:55 PM CT. Silent all day Oct 12.",
  "● Online D07B (R07): in use since Oct 13, replacing D07. Last upload Oct 30, 2:52 PM CT.",
];

async function innerTexts(page: Page, selector: ReturnType<Page["locator"]>): Promise<string[]> {
  return (await selector.evaluateAll((els) => els.map((e) => (e as HTMLElement).innerText))).map(
    norm,
  );
}

async function expectDevices(page: Page): Promise<void> {
  const devices = page.getByRole("region", { name: "Devices", exact: true });
  const rows = devices.getByTestId("device-row");
  await expect(rows).toHaveCount(3);
  await expect.poll(() => innerTexts(page, rows)).toEqual(DEVICE_ROWS);

  await devices.getByText("Show all devices (10)").click();
  const table = devices.getByRole("table");
  const body = table.locator("tbody tr");
  await expect(body).toHaveCount(10);
  await expect(body.locator("th")).toHaveText([
    "D01",
    "D02",
    "D04",
    "D05",
    "D06",
    "D07",
    "D07B",
    "D08",
    "D09",
    "D10",
  ]);
  const d07 = body.filter({ has: page.locator('th:text-is("D07")') });
  await expect(d07.locator("td")).toHaveText([
    "R07",
    "Oct 1–12 · replaced by D07B",
    "Oct 12, 2:14 PM CT",
    "fw-1.0.0",
    "0",
    "0",
  ]);
  const d07b = body.filter({ has: page.locator('th:text-is("D07B")') });
  await expect(d07b.locator("td").nth(1)).toHaveText("Since Oct 13");
  const d02 = body.filter({ has: page.locator('th:text-is("D02")') });
  await expect(d02.locator("td")).toHaveText([
    "R02, R03",
    "Since Oct 1",
    "Oct 30, 2:55 PM CT",
    "fw-1.0.0",
    "1 (Oct 12)",
    "1 (Oct 12)",
  ]);
  const d08 = body.filter({ has: page.locator('th:text-is("D08")') });
  await expect(d08.locator("td").nth(4)).toHaveText(/^12\b/);
  await expect(body.locator("td:nth-child(5)")).toHaveText(Array(10).fill("fw-1.0.0"));
}

test.describe("as researcher", () => {
  test.beforeEach(async ({ as }) => {
    await as("researcher");
  });

  test("E2E-07 /study#devices scrolls to the Devices section", async ({ page }) => {
    await page.goto("/study#devices");
    const heading = page.getByRole("heading", { level: 2, name: "Devices" });
    await expect(heading).toBeVisible();
    await expect(heading).toBeInViewport();
    await expectDevices(page);
  });

  test("E2E-20 / FE-194 Study team values of TRD 14 Table 4.9-E", async ({ page }) => {
    await page.goto("/study");
    await expect(page).toHaveTitle("Study team – EchoWell");
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(
      "Study team: how the system is working",
    );
    const main = page.locator("main");
    await expect(main.getByText("Counts only. No audio, no names.", { exact: true })).toBeVisible();
    await expect(
      main.getByText(
        "pipeline test data v0.1, Oct 1–30, 2026 · numbers match the pipeline answer key",
        { exact: true },
      ),
    ).toBeVisible();

    // KPI tiles
    const tiles = page.getByRole("list", { name: "Key counts" }).getByRole("listitem");
    await expect(tiles).toHaveCount(4);
    await expect
      .poll(() => innerTexts(page, tiles))
      .toEqual([
        "Check-ins received 94% 281 of 300 expected",
        "Used for scoring 89% 267 of 300 expected",
        "Baselines formed 9 of 10 R08 still forming; R07 restarted once",
        "Alarms raised 2 R09, R10; neither reviewed yet",
      ]);

    // Data problems with tags and links
    const problems = page
      .getByRole("region", { name: "Data problems to follow up" })
      .getByRole("listitem");
    await expect(problems).toHaveCount(4);
    await expect
      .poll(() => innerTexts(page, problems))
      .toEqual(DATA_PROBLEMS.map(([tag, code, detail]) => `${tag} ${code} ${detail}`));
    const links = [
      ["R08 · baseline stuck at 13 of 16", "/residents/R08/log"],
      ["R03 · many check-ins set aside", "/residents/R03/log"],
      ["R05 · possible other speaker", "/residents/R05/log"],
      ["D02 · device silent all day", "/study#devices"],
    ];
    for (const [i, [name, href]] of links.entries()) {
      await expect(problems.nth(i).getByRole("link")).toHaveAccessibleName(name!);
      await expect(problems.nth(i).getByRole("link")).toHaveAttribute("href", href!);
    }

    // Check-ins per day: accessible name, x labels and the table alternative
    const daily = page.getByRole("region", { name: "Check-ins per day", exact: true });
    await expect(
      daily.getByRole("region", {
        name: "Check-ins per day, Oct 1–30: 267 used, 12 set aside, 2 held back, 19 missed.",
      }),
    ).toBeVisible();
    for (const label of ["Oct 1", "Oct 12: D02 silent", "Oct 30"]) {
      await expect(daily.locator("svg text", { hasText: label }).first()).toBeAttached();
    }
    await daily.getByText("Show daily counts as a table").click();
    const dayRows = daily.getByRole("table").locator("tbody tr");
    await expect(dayRows).toHaveCount(30);
    const day = (label: string) => dayRows.filter({ has: page.locator(`th:text-is("${label}")`) });
    await expect(day("Oct 1").locator("td")).toHaveText(["10", "0", "0", "0", ""]);
    await expect(day("Oct 8").locator("td")).toHaveText(["8", "0", "1", "1", ""]);
    await expect(day("Oct 12").locator("td")).toHaveText(["8", "0", "0", "2", "D02 silent"]);
    await expect(day("Oct 22").locator("td")).toHaveText(["8", "1", "1", "0", ""]);

    // Where check-ins are lost
    const funnel = page
      .getByRole("region", { name: "Where check-ins are lost" })
      .getByTestId("funnel-row");
    await expect
      .poll(() => innerTexts(page, funnel))
      .toEqual([
        "Expected 300 10 residents × 30 days",
        "Received 281 19 missed; 2 duplicate copies removed",
        "Passed quality checks 269 12 set aside: quality flag 5, noise 5, too short 3 (1 had two reasons)",
        "Same speaker, used 267 2 held back as possible other voice",
      ]);
    expect(
      await funnel
        .locator("i")
        .evaluateAll((els) => els.map((e) => (e as HTMLElement).style.width)),
    ).toEqual(["100%", "93.7%", "89.7%", "89%"]);

    // Usable check-ins by resident
    const byRes = page.getByRole("region", { name: "Usable check-ins by resident" });
    await expect(byRes.getByText("Share of 30 days, lowest first", { exact: true })).toBeVisible();
    const resRows = byRes.getByRole("group");
    await expect(resRows).toHaveCount(10);
    await expect
      .poll(() => innerTexts(page, resRows))
      .toEqual([
        "R08 43%",
        "R03 73%",
        "R02 80%",
        "R05 93%",
        "R01 100%",
        "R04 100%",
        "R06 100%",
        "R07 100%",
        "R09 100%",
        "R10 100%",
      ]);
    await expect(resRows.first()).toHaveAccessibleName(
      "R08: 13 of 30 days usable (43%); 5 set aside; 0 held back; 12 missed.",
    );

    // Alarm timing check
    const timing = page.getByRole("region", { name: "Alarm timing check" });
    await expect(
      timing.getByText("Test data only, where the true change date is known.", { exact: true }),
    ).toBeVisible();
    await expect(timing.getByRole("columnheader")).toHaveText([
      "Resident",
      "Planted change",
      "Change began",
      "Alarm rang",
      "Delay",
    ]);
    const timingRows = timing.locator("tbody tr");
    await expect(timingRows).toHaveCount(3);
    await expect(timingRows.nth(0).locator("th, td")).toHaveText([
      "R09",
      "Sudden step",
      "Oct 21",
      "Oct 21",
      "0 days",
    ]);
    await expect(timingRows.nth(1).locator("th, td")).toHaveText([
      "R10",
      "Slow drift",
      "Oct 17",
      "Oct 24",
      "7 days",
    ]);
    await expect(timingRows.nth(2).locator("th, td")).toHaveText([
      "Other 8",
      "None",
      "None",
      "No alarm",
      "Correct",
    ]);

    await expectDevices(page);
    await expect(page.getByRole("button", { name: "Scores (CSV)" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Baselines (CSV)" })).toBeVisible();
  });

  test("E2E-21 researcher cannot review or add notes; direct POST is refused", async ({
    page,
    request,
  }) => {
    await page.goto("/residents/R09/review");
    const panel = page.getByRole("region", { name: "Review alert: changed since Oct 21" });
    await expect(
      panel.getByText("Only clinicians and admins can review alarms.", { exact: true }),
    ).toBeVisible();
    await expect(panel.getByRole("checkbox")).toHaveCount(0);
    await expect(panel.getByRole("radio")).toHaveCount(0);
    await expect(panel.getByRole("textbox")).toHaveCount(0);
    await expect(panel.getByRole("button")).toHaveCount(0);
    await expect(panel.getByRole("heading", { level: 3, name: "Previous reviews" })).toBeVisible();
    const notes = page.getByRole("region", { name: "Staff notes" });
    await expect(
      notes.getByText("Only clinicians and admins can add notes.", { exact: true }),
    ).toBeVisible();
    await expect(notes.getByRole("textbox")).toHaveCount(0);
    await expect(notes.getByRole("button", { name: "Add note" })).toHaveCount(0);

    const { token } = readSession("researcher", process.env.E2E_AUTH_PREFIX ?? "");
    const alerts = await request.get(`${API}/alerts?status=open&resident_code=R09`, {
      headers: authHeader(token),
    });
    expect(alerts.ok()).toBe(true);
    const alertId = ((await alerts.json()) as { items: { id: string }[] }).items[0]!.id;
    const post = await request.post(`${API}/alerts/${alertId}/reviews`, {
      headers: authHeader(token),
      data: { outcome: "no_concern", explanations: [], note: null },
    });
    expect(post.status()).toBe(403);
  });
});

test("E2E-21 / FE-194 clinician gets the access-denied state on /study", async ({ page, as }) => {
  await as("clinician");
  await page.goto("/study");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "You do not have access to this page.",
  );
  await expect(page.getByRole("link", { name: "← Resident list" })).toBeVisible();
  const nav = page.getByRole("navigation", { name: "Main" });
  await expect(nav.getByRole("link", { name: "New admissions" })).toBeVisible();
  await expect(nav.getByRole("link", { name: "Study team" })).toHaveCount(0);
});
