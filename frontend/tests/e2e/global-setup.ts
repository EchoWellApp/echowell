// Global setup of the read-only and mutating E2E runs (TRD 24 D-73, D-74; FEAT-076-FR-02):
// reset and re-seed the main E2E database (seed test_v0_1 --reset + the DS-10 loader), restart the
// backend so its pool and login limiter start empty, wait for /health, then log in once per role.
// E2E_RESET_COMMAND replaces the docker compose steps when the stack runs without Compose
// (for example a local uvicorn); it must reset, re-seed and restart the backend itself.
import { execSync } from "node:child_process";
import { join } from "node:path";
import { storeSessions, waitForHealth } from "./auth-store";

const ROOT = join(__dirname, "..", "..", "..");
const GROUND_TRUTH = "tests/fixtures/answer_key/evaluation_ground_truth_v0_1.csv";

function run(command: string): void {
  execSync(command, { cwd: ROOT, stdio: "inherit", env: process.env });
}

export default async function globalSetup(): Promise<void> {
  if (process.env.E2E_SKIP_RESET !== "1") {
    if (process.env.E2E_RESET_COMMAND) {
      run(process.env.E2E_RESET_COMMAND);
    } else {
      run("docker compose exec -T backend python -m backend.cli seed test_v0_1 --reset");
      run(
        `docker compose exec -T backend python database/seeds/load_evaluation_ground_truth.py ${GROUND_TRUTH}`,
      );
      run("docker compose restart backend");
    }
  }
  await waitForHealth();
  await storeSessions();
}
