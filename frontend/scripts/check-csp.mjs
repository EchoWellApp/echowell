#!/usr/bin/env node
// Netlify build guard (TRD 12 SEC-070, TRD 15 DEP-050; FEAT-082-FR-06, FEAT-082-AC-02).
// Run as `node scripts/check-csp.mjs && npm run build` from `frontend/`: exits non-zero, naming
// the origin, when NEXT_PUBLIC_API_BASE_URL is unset, is not a bare origin (D-65), or is not listed
// in `connect-src` of the Content-Security-Policy in the repository-root netlify.toml. It also
// refuses a wildcard in `connect-src`. An optional first argument names another netlify.toml.
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const tomlPath = resolve(process.argv[2] ?? resolve(here, "..", "..", "netlify.toml"));

function fail(message) {
  console.error(`check-csp: ${message}`);
  process.exit(1);
}

function connectSources(toml) {
  const match = toml.match(/^\s*Content-Security-Policy\s*=\s*"([^"]*)"\s*$/m);
  if (!match) fail(`no Content-Security-Policy header found in ${tomlPath}`);
  const directive = match[1]
    .split(";")
    .map((part) => part.trim().split(/\s+/))
    .find(([name]) => name === "connect-src");
  if (!directive) fail(`the Content-Security-Policy in ${tomlPath} has no connect-src`);
  return directive.slice(1);
}

function apiOrigin(value) {
  if (!value) fail("NEXT_PUBLIC_API_BASE_URL is not set");
  let url;
  try {
    url = new URL(value);
  } catch {
    fail(`NEXT_PUBLIC_API_BASE_URL is not a URL: ${value}`);
  }
  const bare = url.pathname === "/" && !url.search && !url.hash && !value.endsWith("/");
  if (!bare || url.username || url.password) {
    fail(`NEXT_PUBLIC_API_BASE_URL must be an origin without path, e.g. ${url.origin}`);
  }
  return url.origin;
}

let toml;
try {
  toml = readFileSync(tomlPath, "utf8");
} catch {
  fail(`cannot read ${tomlPath}`);
}
const sources = connectSources(toml);
if (sources.some((source) => source.includes("*"))) {
  fail("connect-src must not contain a wildcard (SEC-070)");
}
const origin = apiOrigin(process.env.NEXT_PUBLIC_API_BASE_URL);
if (!sources.includes(origin)) {
  fail(`${origin} is not listed in connect-src of ${tomlPath}; update TRD 12 §4.9 first (D-65)`);
}
console.log(`check-csp: ${origin} is listed in connect-src`);
