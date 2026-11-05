// req: E2E-15, TST-187, E2E-19, FR-184, NFR-011, UX-144, UX-317, TST-065, D-67, D-73, D-74, D-113,
// FEAT-076-FR-08, FR-09, FR-10, FR-11, FEAT-076-AC-04
// The @isolated run (TRD 13 §8, TRD 16 CIC-030): database echowell_demo seeded with
// `seed test_v0_1 --master-only` plus the overlay roster tests/fixtures/seeds/demo_overlay (R11, D11),
// PIPELINE_AS_OF empty (as-of = current time). Only through `test:e2e:isolated`
// (playwright.isolated.config.ts: Chromium, one worker, serial), in the order E2E-15, TST-187,
// E2E-19. Sessions come from isolated-setup.ts (.auth/isolated-<role>.json); no login form.
import { readFileSync } from "node:fs";
import { join } from "node:path";
import type { APIRequestContext, Page } from "@playwright/test";
import { test, expect, signInAs } from "./fixtures";
import { readSession, type E2ERole } from "./auth-store";
import {
  API,
  authHeader,
  banner,
  logCounts,
  logLines,
  norm,
  pillTexts,
  residentRows,
} from "./helpers";

const PREFIX = "isolated-";
const TZ = process.env.FACILITY_TZ ?? "America/Chicago";
const REPO = join(__dirname, "..", "..", "..");
const SRC05 = join(REPO, "tests/fixtures/pipeline_input/EchoWell_pipeline_test_input_v0_1.csv");
const AS_OF = "2026-10-30T15:00:00-05:00";

/** Valid feature values of an ordinary check-in (copied from SRC-05 R01-20261001-01). */
const FEATURES = {
  schema_version: "0.1",
  mic_noise_level_dbfs: -55.7,
  audio_quality_flag: "ok",
  extraction_software_version: "openSMILE 3.0.2",
  device_firmware_version: "fw-1.0.0",
  speech_duration_s: 2.78,
  phrase_id: "P01",
  loudness_dbfs: -30.67,
  total_phrase_duration_s: 2.78,
  speech_rate_syl_per_s: 3.83,
  articulation_rate_syl_per_s: 5.52,
  number_of_pauses: 1,
  pause_fraction: 0.239,
  voiced_fraction: 0.564,
  mean_f0_hz: 202.8,
  f0_variability_st: 4.31,
  jitter_local_pct: 0.885,
  shimmer_local_pct: 1.18,
  hnr_db: 10.68,
  cpps_db: 12.04,
  alpha_ratio_db: -14.18,
  hammarberg_index_db: 16.77,
  mfcc1: 39.22,
  mfcc2: 16.66,
  mfcc3: -0.24,
  mfcc4: -8.71,
};

function parts(ms: number): Record<string, string> {
  const out: Record<string, string> = {};
  for (const p of new Intl.DateTimeFormat("en-US", {
    timeZone: TZ,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date(ms))) {
    out[p.type] = p.value;
  }
  return out;
}

/** Facility-local date as YYYYMMDD (session ID) and "Mon D" (log). */
const localYmd = (ms: number) => {
  const p = parts(ms);
  return `${p.year}${p.month}${p.day}`;
};
const localMonD = (ms: number) =>
  new Intl.DateTimeFormat("en-US", { timeZone: TZ, month: "short", day: "numeric" }).format(
    new Date(ms),
  );
/** "<Mon D, h:mm AM/PM CT>" (TRD 24 D-119). */
const localWhen = (ms: number) =>
  `${new Intl.DateTimeFormat("en-US", {
    timeZone: TZ,
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  })
    .format(new Date(ms))
    .replace(/ /g, " ")} CT`;
/** `timestamp_utc` with seconds precision, "YYYY-MM-DD HH:MM:SS". */
const utcStamp = (ms: number) => new Date(ms).toISOString().slice(0, 19).replace("T", " ");

function apiKey(): string {
  const key = process.env.SEED_INGEST_API_KEY;
  if (!key) throw new Error("SEED_INGEST_API_KEY is not set");
  return key;
}

const token = (role: E2ERole) => readSession(role, PREFIX).token;

/** POST one R11 record stamped with the current time (whole seconds); returns its time and 201 time. */
async function postR11(request: APIRequestContext, suffix: string) {
  const ms = Math.floor(Date.now() / 1000) * 1000;
  const res = await request.post(`${API}/sessions`, {
    headers: { "X-API-Key": apiKey() },
    data: {
      ...FEATURES,
      session_id: `R11-${localYmd(ms)}-${suffix}`,
      resident_id: "R11",
      device_id: "D11",
      timestamp_utc: utcStamp(ms),
    },
  });
  expect(res.status(), await res.text()).toBe(201);
  return { ms, at: Date.now() };
}

/** Text of every resident row as [code, pill, what's happening, last check-in]. */
async function rowTexts(page: Page): Promise<string[][]> {
  const rows = residentRows(page);
  await expect(rows.first()).toBeVisible();
  const out: string[][] = [];
  for (const row of await rows.all()) {
    const cells = row.locator("td");
    out.push([
      norm(await cells.nth(1).innerText()),
      (await pillTexts(cells.nth(0))).join(""),
      norm(await cells.nth(2).innerText()),
      norm(await cells.nth(3).innerText()),
    ]);
  }
  return out;
}

const r11Row = (rows: string[][]) => rows.find((r) => r[0] === "R11");
const others = (rows: string[][]) => rows.filter((r) => r[0] !== "R11");

async function waitForRun(request: APIRequestContext, runId: string): Promise<void> {
  await expect
    .poll(
      async () => {
        const res = await request.get(`${API}/pipeline/runs/${runId}`, {
          headers: authHeader(token("admin")),
        });
        return ((await res.json()) as { status: string }).status;
      },
      { timeout: 120_000, intervals: [500, 1000, 2000] },
    )
    .toBe("succeeded");
}

test.describe("@isolated demo path", () => {
  // Serial, and longer than the 30 s default: TST-187 waits for the next minute and E2E-19 uploads
  // SRC-05 and runs the pipeline before its checks.
  test.describe.configure({ mode: "serial", timeout: 120_000 });

  let firstPostMs = 0;
  let firstLast = "";

  test("E2E-15 new check-in appears", async ({ page, request }) => {
    await signInAs(page, "clinician", PREFIX);
    await page.goto("/residents");
    const before = await rowTexts(page);

    const { ms } = await postR11(request, "01");
    firstPostMs = ms;
    firstLast = localWhen(ms);

    await page.reload();
    await expect
      .poll(async () => r11Row(await rowTexts(page)), { timeout: 15_000 })
      .toEqual(["R11", "○ Learning", "Learning their usual: 1 of 16 check-ins so far.", firstLast]);
    expect(others(await rowTexts(page))).toEqual(others(before));

    await page.goto("/residents/R11/log");
    expect((await logCounts(page))[0]).toBe(1);
    // "Check-ins started." is dated by the first record of the enrolment (TRD 24 D-113) and is the
    // newest line; there is no event for the usable check-in itself. R11 is enrolled on 2026-10-01
    // (demo overlay) and this scenario runs at the current time, so every earlier line in the window
    // is a day without a record ("Check-in missed."), however many days that is.
    const lines = await logLines(page);
    expect(lines[0]).toBe(`${localMonD(ms)} Check-ins started.`);
    for (const line of lines.slice(1))
      expect(line).toMatch(/^[A-Z][a-z]{2} \d{1,2} Check-in missed\.$/);
    expect(await pillTexts(banner(page))).toEqual(["○ Learning"]);

    await page.goto("/residents/R11/trends");
    await expect(page.getByRole("heading", { level: 2, name: "Change score" })).toBeVisible();
    await expect(page.getByTestId("score-bar")).toHaveCount(0);
  });

  test("TST-187 a posted check-in shows within 5 s", async ({ page, request }) => {
    expect(firstPostMs).toBeGreaterThan(0);
    await signInAs(page, "clinician", PREFIX);
    // A different minute, so that the new "Last check-in" is distinguishable.
    const nextMinute = Math.ceil((firstPostMs + 1) / 60_000) * 60_000;
    if (Date.now() < nextMinute) await page.waitForTimeout(nextMinute - Date.now() + 1_000);

    const { ms, at } = await postR11(request, "02");
    const expected = localWhen(ms);
    expect(expected).not.toBe(firstLast);
    let shownAt = 0;
    while (Date.now() - at < 5_000) {
      await page.goto("/residents");
      const row = r11Row(await rowTexts(page));
      if (row?.[3] === expected) {
        await page.goto("/residents/R11/log");
        if ((await logCounts(page))[0] === 2) {
          shownAt = Date.now();
          break;
        }
      }
    }
    expect(shownAt, "new check-in not shown within 5 s").toBeGreaterThan(0);
    expect(shownAt - at).toBeLessThanOrEqual(5_000);
  });

  test("E2E-19 reminder (snooze) without advancing any clock", async ({ page, request }) => {
    // Load SRC-05 and run the pipeline as of the test date (§8).
    const upload = await request.post(`${API}/ingest`, {
      headers: authHeader(token("admin")),
      multipart: {
        file: {
          name: "EchoWell_pipeline_test_input_v0_1.csv",
          mimeType: "text/csv",
          buffer: readFileSync(SRC05),
        },
      },
    });
    expect(upload.status(), await upload.text()).toBe(202);
    const accepted = (await upload.json()) as {
      ingest_batch_id: string;
      pipeline_run_id: string | null;
    };
    await expect
      .poll(
        async () => {
          const res = await request.get(`${API}/ingest/batches/${accepted.ingest_batch_id}`, {
            headers: authHeader(token("admin")),
          });
          return res.ok();
        },
        { timeout: 60_000 },
      )
      .toBe(true);
    if (accepted.pipeline_run_id) await waitForRun(request, accepted.pipeline_run_id);

    const run = await request.post(`${API}/pipeline/run`, {
      headers: authHeader(token("admin")),
      data: { as_of: AS_OF, profile: "test_v0_1", scope: "all" },
    });
    expect(run.status(), await run.text()).toBe(202);
    await waitForRun(request, ((await run.json()) as { pipeline_run_id: string }).pipeline_run_id);

    await signInAs(page, "clinician", PREFIX);
    await page.goto("/residents/R10/review");
    const panel = page.getByRole("region", { name: "Review alert: changed since Oct 24" });
    const remind = panel.getByRole("button", { name: "Remind me in 24 hours" });
    await expect(remind).toBeVisible();
    const clickAt = Date.now();
    await remind.click();
    const announced = panel
      .getByRole("status")
      .filter({ hasText: /Reminder set for .*\. The alarm stays on\./ });
    await expect(announced).toBeVisible();
    const text = norm(await announced.innerText());
    const when = /^Reminder set for (.+)\. The alarm stays on\.$/.exec(text)?.[1];
    const candidates = [-60_000, 0, 60_000, 120_000].map((d) =>
      localWhen(clickAt + 86_400_000 + d),
    );
    expect(candidates).toContain(when);
    await expect(panel.getByText(`Reminder set for ${when}.`, { exact: true })).toBeVisible();
    await expect(panel.getByText("Not reviewed yet.", { exact: true })).toBeVisible();

    const res = await request.get(`${API}/alerts?resident_code=R10`, {
      headers: authHeader(token("clinician")),
    });
    const alert = (
      (await res.json()) as {
        items: { status: string; reviewed: boolean; snoozed_until: string | null }[];
      }
    ).items[0]!;
    expect(alert.status).toBe("open");
    expect(alert.reviewed).toBe(false);
    const until = Date.parse(alert.snoozed_until!);
    expect(Math.abs(until - (clickAt + 86_400_000))).toBeLessThanOrEqual(120_000);

    await page.goto("/residents/R10");
    const now = page.getByRole("region", { name: "Right now" });
    await expect
      .poll(async () => norm(await now.innerText()))
      .toContain("Not reviewed Review status");
    expect(await pillTexts(banner(page))).toEqual(["▲ Changed"]);
  });
});
