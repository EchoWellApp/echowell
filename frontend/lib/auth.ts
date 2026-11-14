// Token store: module memory mirrored to sessionStorage["echowell.auth"] (TRD 04 §4.5.1,
// FE-050..FE-053). The token never goes to localStorage, cookies, URLs or logs (FE-051).
const KEY = "echowell.auth";
const RESTORE_MARGIN_S = 30;

interface Stored {
  token: string;
  exp: number; // seconds since the epoch
}

let current: Stored | null = null;

function storage(): Storage | null {
  try {
    return typeof window === "undefined" ? null : window.sessionStorage;
  } catch {
    return null;
  }
}

/** Reads `exp` from a JWT payload (base64url, no signature check); null when unreadable. */
export function readExp(token: string): number | null {
  const payload = token.split(".")[1];
  if (!payload) return null;
  try {
    const b64 = payload.replace(/-/g, "+").replace(/_/g, "/");
    const padded = b64 + "=".repeat((4 - (b64.length % 4)) % 4);
    const json = JSON.parse(atob(padded)) as { exp?: unknown };
    return typeof json.exp === "number" ? json.exp : null;
  } catch {
    return null;
  }
}

export function setToken(token: string): Stored | null {
  const exp = readExp(token);
  if (exp === null) return null;
  current = { token, exp };
  try {
    storage()?.setItem(KEY, JSON.stringify(current));
  } catch {
    // memory-only fallback (FE-050)
  }
  return current;
}

export function getToken(): string | null {
  return current?.token ?? null;
}

export function getExp(): number | null {
  return current?.exp ?? null;
}

export function clearToken(): void {
  current = null;
  try {
    storage()?.removeItem(KEY);
  } catch {
    // ignore
  }
}

/** Restores the stored token when it expires more than 30 s from now (FE-053). */
export function restoreToken(nowMs: number = Date.now()): Stored | null {
  if (current) return current;
  let raw: string | null = null;
  try {
    raw = storage()?.getItem(KEY) ?? null;
  } catch {
    return null;
  }
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as Partial<Stored>;
    if (typeof parsed.token === "string" && typeof parsed.exp === "number") {
      if (parsed.exp * 1000 - nowMs > RESTORE_MARGIN_S * 1000) {
        current = { token: parsed.token, exp: parsed.exp };
        return current;
      }
    }
  } catch {
    // fall through
  }
  clearToken();
  return null;
}

/** The post-login destination: a same-origin path, else "/residents" (FE-057). */
export function safeNext(next: string | null | undefined): string {
  if (!next || !next.startsWith("/") || next.startsWith("//") || next.includes("://")) {
    return "/residents";
  }
  if (next.startsWith("/login")) return "/residents";
  return next;
}
