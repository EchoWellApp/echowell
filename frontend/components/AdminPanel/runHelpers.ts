// Pure helpers for the pipeline runs list and banners (TRD 11 UX-212, UX-219; TRD 17 LOG-111, LOG-112).
import { localDateOf } from "@/lib/format";
import type { PipelineRun } from "@/lib/types";

const HOUR = 3_600_000;

/** UX-219: the local date to name when no succeeded nightly run started within 26 h, else null. */
export function nightlyMissingDate(runs: PipelineRun[], now: number, tz: string): string | null {
  const ok = runs.some(
    (r) =>
      r.trigger === "nightly" &&
      r.status === "succeeded" &&
      Date.parse(r.started_at) >= now - 26 * HOUR,
  );
  if (ok) return null;
  // The most recent facility-local date whose 02:00 has passed is the local date of now − 2 h.
  return localDateOf(new Date(now - 2 * HOUR).toISOString(), tz);
}

/** Runs newest first, at most 50 (LOG-112). */
export const newestFirst = (runs: PipelineRun[]) =>
  [...runs].sort((a, b) => Date.parse(b.started_at) - Date.parse(a.started_at)).slice(0, 50);
