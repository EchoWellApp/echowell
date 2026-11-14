#!/usr/bin/env node
// Initial-JavaScript budget per dashboard route (TRD 03 NFR-012, TRD 13 TST-191, FEAT-079-FR-15).
//
// Run from frontend/ after `npm run build` (the `frontend` CI job runs it as `npm run check:bundle`):
//   node ../scripts/ci/check-bundle.mjs [--budget-kb 300] [--next-dir .next]
//
// For every dashboard page of the App Router build (`/residents`, `/residents/[residentCode]` and its
// sections, `/admissions`, `/study`, `/admin`: the pages under the `(protected)` route group) the initial
// JavaScript is the set of chunks the browser loads before the page is interactive: the root main files
// of `.next/build-manifest.json` plus the chunks `.next/app-build-manifest.json` lists for the root
// layout, every layout above the page and the page itself (deduplicated). Each chunk is gzip-compressed
// (level 9, like the "First Load JS" column of `next build`) and summed. The legacy `polyfills` chunk is
// excluded: it is loaded only by browsers without ES-module support (`nomodule`), as in Next.js's own
// First Load JS figure. Fails (exit 1) when any route exceeds the budget (default 300 KB = 300 × 1024 B).
import { readFileSync, existsSync } from "node:fs";
import { gzipSync } from "node:zlib";
import { join } from "node:path";

const args = process.argv.slice(2);
const option = (name, fallback) => {
  const index = args.indexOf(name);
  return index >= 0 && args[index + 1] ? args[index + 1] : fallback;
};
const budgetKb = Number(option("--budget-kb", "300"));
const nextDir = option("--next-dir", ".next");
const DASHBOARD_GROUP = "/(protected)/";

for (const file of ["build-manifest.json", "app-build-manifest.json"]) {
  if (!existsSync(join(nextDir, file))) {
    console.error(
      `check:bundle: ${join(nextDir, file)} not found; run \`npm run build\` first.`,
    );
    process.exit(2);
  }
}
const buildManifest = JSON.parse(
  readFileSync(join(nextDir, "build-manifest.json"), "utf8"),
);
const appManifest = JSON.parse(
  readFileSync(join(nextDir, "app-build-manifest.json"), "utf8"),
).pages;

const sizes = new Map();
const gzipSize = (chunk) => {
  if (!sizes.has(chunk))
    sizes.set(
      chunk,
      gzipSync(readFileSync(join(nextDir, chunk)), { level: 9 }).length,
    );
  return sizes.get(chunk);
};

// "/(protected)/residents/[residentCode]/trends/page" -> its layouts from the root down.
const layoutsAbove = (entry) => {
  const parts = entry.split("/").slice(1, -1); // ["(protected)", "residents", "[residentCode]", "trends"]
  const layouts = ["/layout"];
  for (let i = 1; i <= parts.length; i += 1)
    layouts.push(`/${parts.slice(0, i).join("/")}/layout`);
  return layouts;
};

const pages = Object.keys(appManifest).filter(
  (e) => e.startsWith(DASHBOARD_GROUP) && e.endsWith("/page"),
);
if (pages.length === 0) {
  console.error(
    "check:bundle: no dashboard pages found in app-build-manifest.json",
  );
  process.exit(2);
}
const budget = budgetKb * 1024;
const rows = [];
for (const entry of pages.sort()) {
  const chunks = new Set(buildManifest.rootMainFiles ?? []);
  for (const key of [...layoutsAbove(entry), entry]) {
    for (const chunk of appManifest[key] ?? [])
      if (chunk.endsWith(".js")) chunks.add(chunk);
  }
  const bytes = [...chunks].reduce((sum, chunk) => sum + gzipSize(chunk), 0);
  const route = entry.replace("/(protected)", "").replace(/\/page$/, "") || "/";
  rows.push({ route, kb: bytes / 1024, ok: bytes <= budget });
}

console.log(
  `Initial JavaScript per dashboard route (gzip), budget ${budgetKb} KB (NFR-012, TST-191)`,
);
for (const { route, kb, ok } of rows) {
  console.log(
    `${ok ? "ok  " : "FAIL"}  ${kb.toFixed(1).padStart(7)} KB  ${route}`,
  );
}
const failed = rows.filter((r) => !r.ok);
if (failed.length > 0) {
  console.error(
    `check:bundle: ${failed.length} route(s) exceed ${budgetKb} KB of initial JavaScript (gzip).`,
  );
  process.exit(1);
}
