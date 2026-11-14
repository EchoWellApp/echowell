// Shared E2E helpers (TRD 13 §4.10; FEAT-076-FR-04): DS-07 expected values of TRD 11 §4.13 /
// TRD 14 Table 4.9-B and small locator helpers used by several spec files.
import { execSync } from "node:child_process";
import { join } from "node:path";
import { expect, type Locator, type Page } from "@playwright/test";
import { API_BASE } from "./auth-store";

export const API = `${API_BASE}/api/v1`;

export const DATA_BAR =
  "Test data only (pipeline test data v0.1, Oct 1–30, 2026). No real residents. No audio is stored or played anywhere in EchoWell.";

export const STATUS_NOTE =
  "A status is a prompt to check on someone, not a diagnosis. [Final clinical wording: confirm with PI]";

/** TRD 11 §4.13.1 / TRD 14 Table 4.9-B, default order (D-109). */
export const LIST_ROWS = [
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
] as const;

export const ALL_CODES = LIST_ROWS.map((r) => r[0]);

/** TRD 11 §4.18.8 / TRD 14 Table 4.9-D, in the UX-307 order. */
export const DATA_PROBLEMS = [
  ["Staff can help", "R08:", "baseline stuck at 13 of 16. 12 missed and 5 set aside in 30 days."],
  [
    "Staff can help",
    "R03:",
    "7 of 29 received check-ins set aside (noise, quality flag, too short).",
  ],
  ["Study team", "R05:", "2 check-ins held back as possible other voice (Oct 8, Oct 22)."],
  ["Study team", "D02:", "silent all day Oct 12. Affected R02 and R03."],
] as const;

/** TRD 11 §4.5.4 card labels with technical names. */
export const MEASUREMENT_LABELS = [
  "Quieter (loudness)",
  "Slower to say the phrase (phrase duration)",
  "Fewer syllables per second (speech rate)",
  "Slower while talking (articulation rate)",
  "More pauses (number of pauses)",
  "More time in pauses (pause fraction)",
  "Less voiced sound (voiced fraction)",
] as const;

export const norm = (s: string | null | undefined): string => (s ?? "").replace(/\s+/g, " ").trim();

/** Body rows of the residents table. */
export function residentRows(page: Page): Locator {
  return page.getByRole("table", { name: /^Residents in the study/ }).locator("tbody tr");
}

/** Study IDs of the rendered resident rows, in order (waits for the table to settle). */
export async function expectRowCodes(page: Page, codes: readonly string[]): Promise<void> {
  await expect(residentRows(page)).toHaveCount(codes.length);
  await expect(residentRows(page).locator("td:nth-child(2)")).toHaveText([...codes]);
}

/**
 * Status pills inside `scope`, as "<glyph> <label>" (the glyph is aria-hidden, so it is joined from
 * the DOM instead of the accessible name). Pills are spans whose first child is the hidden glyph.
 */
export async function pillTexts(scope: Locator): Promise<string[]> {
  const texts = await scope
    .locator('span:has(> span[aria-hidden="true"]:first-child)')
    .evaluateAll((els) =>
      els.map((el) => {
        const glyph = (el.firstElementChild?.textContent ?? "").trim();
        const rest = (el.textContent ?? "").slice((el.firstElementChild?.textContent ?? "").length);
        return `${glyph} ${rest.replace(/\s+/g, " ").trim()}`;
      }),
    );
  return texts.filter((t) => /^[▲!●○] /.test(t));
}

export async function expectPill(scope: Locator, pill: string): Promise<void> {
  await expect.poll(() => pillTexts(scope)).toContain(pill);
}

/** The chart banner region ("Resident") and its fact value by term. */
export function banner(page: Page): Locator {
  return page.getByRole("region", { name: "Resident" });
}

export function bannerFact(page: Page, term: string): Locator {
  return banner(page).locator(`dt:text-is("${term}") + dd`);
}

/** Chart section navigation. */
export function chartNav(page: Page): Locator {
  return page.getByRole("navigation", { name: "Resident chart" });
}

/** Event lines of the Check-in log as "<Mon D> <text>". */
export async function logLines(page: Page): Promise<string[]> {
  const items = page.getByRole("region", { name: "Events" }).getByRole("listitem");
  await expect(items.first()).toBeVisible();
  return items.evaluateAll((els) =>
    els.map((li) =>
      Array.from(li.children)
        .map((c) => (c.textContent ?? "").replace(/\s+/g, " ").trim())
        .join(" "),
    ),
  );
}

/** Check-in counts Used / Set aside / Held back / Missed as numbers. */
export async function logCounts(page: Page): Promise<number[]> {
  const items = page.getByRole("region", { name: "Check-ins, last 30 days" }).getByRole("listitem");
  await expect(items).toHaveCount(4);
  await expect(items.first()).toHaveText(/\d/);
  return (await items.allTextContents()).map((t) => Number(/\d+/.exec(t)?.[0]));
}

/** Waits until the page's main content stops showing loading text. */
export async function settled(page: Page): Promise<void> {
  await expect(page.locator("main")).not.toContainText("Loading", { timeout: 15_000 });
}

/** Runs SQL on the main E2E database (audit assertions only; never writes). */
export function sql(query: string): string {
  const command =
    process.env.E2E_PSQL_COMMAND ?? "docker compose exec -T db psql -U echowell -d echowell -tA";
  return execSync(command, {
    cwd: join(__dirname, "..", "..", ".."),
    input: query,
    env: process.env,
  })
    .toString()
    .trim();
}

/** Bearer token of the stored per-role session for direct API calls. */
export function authHeader(token: string): Record<string, string> {
  return { Authorization: `Bearer ${token}` };
}
