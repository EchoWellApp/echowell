// Per-role sessions for E2E (TRD 24 D-74): one API login per role, stored in a git-ignored file
// and written into sessionStorage before the first navigation by the role fixture.
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";

export type E2ERole = "admin" | "clinician" | "researcher";
export const ROLES: readonly E2ERole[] = ["admin", "clinician", "researcher"];

export const API_BASE = process.env.E2E_API_BASE_URL ?? "http://localhost:8000";
const AUTH_DIR = join(__dirname, ".auth");

/** Credentials come from the per-job SEED_* variables, never literals (FEAT-076-FR-16). */
export function credentials(role: E2ERole): { email: string; password: string } {
  const password = process.env[`SEED_${role.toUpperCase()}_PASSWORD`];
  if (!password) throw new Error(`SEED_${role.toUpperCase()}_PASSWORD is not set`);
  return { email: `${role}@example.com`, password };
}

export async function waitForHealth(timeoutMs = 60_000): Promise<void> {
  const until = Date.now() + timeoutMs;
  while (Date.now() < until) {
    try {
      const res = await fetch(`${API_BASE}/api/v1/health`);
      if (res.ok) return;
    } catch {
      // not up yet
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  throw new Error(`backend not healthy at ${API_BASE}`);
}

export async function apiLogin(role: E2ERole): Promise<{ token: string; exp: number }> {
  const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(credentials(role)),
  });
  if (!res.ok) throw new Error(`login ${role} failed: ${res.status}`);
  const body = (await res.json()) as { access_token: string; expires_in: number };
  const payload = JSON.parse(Buffer.from(body.access_token.split(".")[1] ?? "", "base64url").toString());
  return { token: body.access_token, exp: Number(payload.exp) };
}

export async function storeSessions(prefix = ""): Promise<void> {
  mkdirSync(AUTH_DIR, { recursive: true });
  for (const role of ROLES) {
    const session = await apiLogin(role);
    writeFileSync(join(AUTH_DIR, `${prefix}${role}.json`), JSON.stringify(session));
  }
}

export function readSession(role: E2ERole, prefix = ""): { token: string; exp: number } {
  return JSON.parse(readFileSync(join(AUTH_DIR, `${prefix}${role}.json`), "utf8"));
}

export function ensureDir(file: string): void {
  mkdirSync(dirname(file), { recursive: true });
}
