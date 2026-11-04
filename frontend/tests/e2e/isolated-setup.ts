// Global setup of the @isolated run (TRD 24 D-74; FEAT-076-FR-08): no reset and no seed; one login
// per role against the echowell_demo backend into .auth/isolated-<role>.json.
import { storeSessions, waitForHealth } from "./auth-store";

export default async function isolatedSetup(): Promise<void> {
  await waitForHealth();
  await storeSessions("isolated-");
}
