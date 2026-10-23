// The only reader of the public build variables (TRD 04 FE-170, FE-171; TRD 21 ENV-030; D-65).
export type AppEnv = "local" | "staging" | "production";

export interface PublicConfig {
  apiBaseUrl: string;
  appEnv: AppEnv;
  gitSha: string;
}

const APP_ENVS: readonly string[] = ["local", "staging", "production"];

function fail(message: string): never {
  throw new Error(`Invalid frontend configuration: ${message}`);
}

export function parsePublicConfig(raw: {
  apiBaseUrl?: string;
  appEnv?: string;
  gitSha?: string;
}): PublicConfig {
  const { apiBaseUrl, appEnv } = raw;
  if (!appEnv || !APP_ENVS.includes(appEnv)) {
    fail("NEXT_PUBLIC_APP_ENV must be local, staging or production");
  }
  if (!apiBaseUrl) fail("NEXT_PUBLIC_API_BASE_URL is required");
  let url: URL;
  try {
    url = new URL(apiBaseUrl);
  } catch {
    fail("NEXT_PUBLIC_API_BASE_URL must be an absolute http(s) URL");
  }
  if (url.protocol !== "http:" && url.protocol !== "https:") {
    fail("NEXT_PUBLIC_API_BASE_URL must be an absolute http(s) URL");
  }
  if (url.origin !== apiBaseUrl) {
    fail(
      "NEXT_PUBLIC_API_BASE_URL must be an origin only (no path, no /api/v1, no trailing slash)",
    );
  }
  if (url.protocol === "http:" && appEnv !== "local") {
    fail("NEXT_PUBLIC_API_BASE_URL must use https:// in staging and production");
  }
  return { apiBaseUrl, appEnv: appEnv as AppEnv, gitSha: raw.gitSha || "unknown" };
}

export const config: PublicConfig = parsePublicConfig({
  apiBaseUrl: process.env.NEXT_PUBLIC_API_BASE_URL,
  appEnv: process.env.NEXT_PUBLIC_APP_ENV,
  gitSha: process.env.NEXT_PUBLIC_GIT_SHA,
});
