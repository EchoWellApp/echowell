// Chart section helpers shared by the layout and the section pages (TRD 04 FE-030, FE-206).
import { useQuery } from "@tanstack/react-query";
import { addDays } from "@/lib/format";
import { REFRESH_MS } from "@/lib/queryClient";
import { queryKeys } from "@/lib/queryKeys";
import type { ResidentDetail, ScoresResponse } from "@/lib/types";
import { CHART_SECTION_ORDER, type ChartSectionKey } from "@/lib/wording";
import * as api from "@/services/api";

export type ChartSection = ChartSectionKey;

/** TRD 19 `ResidentCode` pattern (FE-030). */
export const RESIDENT_CODE_PATTERN = /^[A-Z0-9]{1,16}$/;

export const isValidResidentCode = (code: string) => RESIDENT_CODE_PATTERN.test(code);

/** The chart section of a pathname: "/residents/R09/log" → "log", "/residents/R09" → "summary". */
export function sectionFromPath(pathname: string | null | undefined): ChartSection {
  const parts = (pathname ?? "").split("/").filter(Boolean);
  const last = parts.length > 2 ? parts[2] : undefined;
  return CHART_SECTION_ORDER.find((s) => s !== "summary" && s === last) ?? "summary";
}

/** The `residentCode` route parameter as a string ("" when absent). */
export function codeParam(params: Record<string, string | string[]> | null | undefined): string {
  const raw = params?.residentCode;
  const value = Array.isArray(raw) ? (raw[0] ?? "") : (raw ?? "");
  try {
    return decodeURIComponent(value);
  } catch {
    return value;
  }
}

/** Whether the current epoch has scored sessions: from the scores when known, else the detail. */
export function hasScoredSessions(
  resident: ResidentDetail,
  scores: ScoresResponse | undefined,
): boolean {
  const epoch = resident.current_epoch?.epoch_number;
  if (scores) return scores.items.some((s) => s.epoch_number === epoch);
  return (
    resident.baseline.state === "frozen" &&
    resident.watching_since !== null &&
    resident.watching_since <= resident.window.to
  );
}

/** The latest change score of the current epoch, or null without a scored session. */
export function latestTally(resident: ResidentDetail, scores: ScoresResponse | undefined) {
  const epoch = resident.current_epoch?.epoch_number;
  const items = (scores?.items ?? []).filter((s) => s.epoch_number === epoch);
  if (items.length === 0) return null;
  return items.reduce((a, b) => (b.local_date >= a.local_date ? b : a)).cusum_tally;
}

/** The chart's resident query (layout and sections share its cache entry, FE-087, FE-206). */
export function useResident(code: string) {
  return useQuery({
    queryKey: queryKeys.resident(code),
    queryFn: () => api.getResident(code),
    refetchInterval: REFRESH_MS,
    enabled: isValidResidentCode(code),
  });
}

/** The current epoch's events: from its start (at most 366 days back) to the as-of date. */
export function epochRange(r: ResidentDetail): { from: string; to: string } {
  const to = r.window.to;
  const earliest = addDays(to, -365);
  const start = r.current_epoch?.started_on ?? r.window.from;
  return { from: start > earliest ? start : earliest, to };
}

const LOG_DAYS = 30;

/** Page k of the log: the 30 local days ending `30 × k` days before the as-of date (UX-146). */
export function logRange(asOfDate: string, page: number): { from: string; to: string } {
  const to = addDays(asOfDate, -LOG_DAYS * page);
  return { from: addDays(to, -(LOG_DAYS - 1)), to };
}
