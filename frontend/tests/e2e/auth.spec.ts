// req: FE-188, E2E-01, E2E-02, E2E-14, FE-034, UX-014, UX-018, UX-215, FEAT-076-FR-03, FR-16
// The only spec that submits the login form (TRD 24 D-74 (a); FEAT-076-AC-06). Credentials come
// from the SEED_* environment variables through credentials() (FEAT-076-FR-16).
import type { Page } from "@playwright/test";
import { test, expect } from "./fixtures";
import { credentials, type E2ERole } from "./auth-store";
import { DATA_BAR, sql } from "./helpers";

const FACILITY = process.env.FACILITY_NAME ?? "Edgewood";

async function submitLogin(page: Page, role: E2ERole, password?: string): Promise<void> {
  const c = credentials(role);
  await expect(page.getByRole("heading", { level: 1, name: "EchoWell" })).toBeVisible();
  await page.getByLabel("Email").fill(c.email);
  await page.getByLabel("Password").fill(password ?? c.password);
  await page.getByRole("button", { name: "Sign in" }).click();
}

const storedToken = (page: Page) =>
  page.evaluate(() => window.sessionStorage.getItem("echowell.auth"));

test("E2E-01 login as clinician from /", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/login\?next=%2Fresidents$/);
  await expect(page).toHaveTitle("Sign in – EchoWell");
  await submitLogin(page, "clinician");
  await expect(page).toHaveURL(/\/residents$/);

  const header = page.getByRole("banner");
  await expect(header).toContainText("EchoWell");
  await expect(header).toContainText(`${FACILITY}, Assisted living`);
  const nav = page.getByRole("navigation", { name: "Main" });
  const list = nav.getByRole("link", { name: "Resident list, 2 alarms not reviewed" });
  await expect(list).toBeVisible();
  await expect(list.locator("[data-count]")).toHaveAttribute("data-count", "2");
  await expect(nav.getByRole("link")).toHaveCount(2);
  await expect(nav.getByRole("link", { name: "New admissions" })).toBeVisible();
  await expect(nav.getByRole("link", { name: "Study team" })).toHaveCount(0);
  await expect(nav.getByRole("link", { name: "Admin" })).toHaveCount(0);
  await expect(header.getByText("Clinician", { exact: true })).toBeVisible();
  await expect(header.getByRole("button", { name: "Sign out" })).toBeVisible();
  await expect(page.getByText(DATA_BAR, { exact: true })).toBeVisible();
  expect(await storedToken(page)).toContain('"token"');
});

test("E2E-02 bad login: error, no token, audit row", async ({ page }) => {
  const started = new Date().toISOString();
  await page.goto("/login");
  await submitLogin(page, "clinician", "wrong-password-for-e2e");
  await expect(page.getByRole("alert").filter({ hasText: /\S/ })).toHaveText(
    "Email or password is incorrect.",
  );
  await expect(page).toHaveURL(/\/login/);
  expect(await storedToken(page)).toBeNull();
  const rows = sql(
    `SELECT count(*) FROM audit_logs WHERE action = 'auth.login.failed' ` +
      `AND details->>'email' = 'clinician@example.com' AND occurred_at >= '${started}'::timestamptz - interval '5 seconds';`,
  );
  expect(Number(rows)).toBeGreaterThanOrEqual(1);
});

test("FE-188 redirect to /login without a token and back to next after sign-in", async ({
  page,
}) => {
  await page.goto("/residents/R09/log");
  await expect(page).toHaveURL(/\/login\?next=%2Fresidents%2FR09%2Flog$/);
  await submitLogin(page, "clinician");
  await expect(page).toHaveURL(/\/residents\/R09\/log$/);
  await expect(page.getByRole("region", { name: "Events" })).toBeVisible();
});

test("FE-188 an external next value is rejected", async ({ page }) => {
  await page.goto(`/login?next=${encodeURIComponent("https://example.org/steal")}`);
  await submitLogin(page, "researcher");
  await expect(page).toHaveURL(/^http:\/\/localhost(:\d+)?\/residents$/);
  await page.goto(`/login?next=${encodeURIComponent("//example.org/steal")}`);
  await expect(page).toHaveURL(/\/residents$/);
});

test("FE-188 sign-out clears the session", async ({ page }) => {
  await page.goto("/login");
  await submitLogin(page, "admin");
  await expect(page).toHaveURL(/\/residents$/);
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login$/);
  expect(await storedToken(page)).toBeNull();
  await page.goto("/residents");
  await expect(page).toHaveURL(/\/login\?next=%2Fresidents$/);
});

test("FE-188 researcher: read-only review and notes, no admin page", async ({ page, as }) => {
  await as("researcher");
  await page.goto("/residents/R09/review");
  await expect(
    page.getByText("Only clinicians and admins can add notes.", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Only clinicians and admins can review alarms.", { exact: true }),
  ).toBeVisible();
  await page.goto("/admin");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "You do not have access to this page.",
  );
});

test("E2E-14 clinician on /admin: access denied, no admin API call, no Admin link", async ({
  page,
  as,
}) => {
  await as("clinician");
  const adminCalls: string[] = [];
  page.on("request", (r) => {
    if (/\/api\/v1\/(users|pipeline|ingest)/.test(r.url())) adminCalls.push(r.url());
  });
  await page.goto("/admin");
  await expect(page).toHaveURL(/\/admin$/);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "You do not have access to this page.",
  );
  await expect(page.getByRole("link", { name: "← Resident list" })).toHaveAttribute(
    "href",
    "/residents",
  );
  await expect(
    page.getByRole("navigation", { name: "Main" }).getByRole("link", { name: "Admin" }),
  ).toHaveCount(0);
  expect(adminCalls).toEqual([]);
});
