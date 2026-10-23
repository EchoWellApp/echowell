// Playwright configuration for the serial @isolated run (TRD 13 TST-004, TRD 24 D-73, D-74).
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  testMatch: "isolated.spec.ts",
  globalSetup: "./tests/e2e/isolated-setup.ts",
  grep: /@isolated/,
  workers: 1,
  fullyParallel: false,
  retries: 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: { baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3001", trace: "retain-on-failure" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
