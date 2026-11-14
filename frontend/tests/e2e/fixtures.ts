// Role fixture (TRD 24 D-74; FEAT-076-FR-03): writes the stored token into sessionStorage with
// addInitScript before the first navigation, so scenarios never submit the login form.
import { test as base, expect, type Page } from "@playwright/test";
import { readSession, type E2ERole } from "./auth-store";

export async function signInAs(page: Page, role: E2ERole, prefix = ""): Promise<void> {
  const session = readSession(role, prefix);
  await page.addInitScript((value) => {
    try {
      window.sessionStorage.setItem("echowell.auth", value);
    } catch {
      // ignore
    }
  }, JSON.stringify(session));
}

export const test = base.extend<{ as: (role: E2ERole) => Promise<void> }>({
  as: async ({ page }, use) => {
    await use((role) => signInAs(page, role, process.env.E2E_AUTH_PREFIX ?? ""));
  },
});

export { expect };
