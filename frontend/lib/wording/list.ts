// Resident list copy (TRD 11 §4.3, §4.3.6, UX-041, UX-204, UX-401..UX-407; TRD 04 FE-013).
import { formatLocalDate } from "../format";
import type { Meta, ResidentDetail, ResidentRow, UiStatus } from "../types";
import { PI_MARKER, CLINICAL_WORDING_APPROVED } from "./common";

export type ListFilter = UiStatus | "all";

/** Filter values in button order (UX-401); also the accepted `?show=` values (UX-404). */
export const LIST_FILTERS: readonly ListFilter[] = [
  "all",
  "changed",
  "needs_attention",
  "learning",
  "usual",
];

export const LIST_PAGE = "Resident list";
export const LIST_HEADING = "Residents in the study";
export const LIST_PANEL = "residents";
export const LIST_FILTER_GROUP = "Show";
export const LIST_TABLE_NAME = "Residents table";
export const LIST_COLUMNS = {
  status: "Status",
  resident: "Resident",
  whatsHappening: "What's happening",
  lastCheckin: "Last check-in",
} as const;
export const LIST_NO_MATCH = "No residents with this status.";
export const LIST_EMPTY = "No residents are enrolled yet.";
export const LIST_NO_CHECKINS = "No check-ins yet";
export const LIST_LEGEND_NAME = "Status meanings";
/** Shown as the count while the list loads (UX-200). */
export const LIST_COUNT_PENDING = "—";

/** Button text without the count: "All", "Changed", "Needs attention", "Learning", "Usual". */
export const LIST_FILTER_LABEL: Record<ListFilter, string> = {
  all: "All",
  changed: "Changed",
  needs_attention: "Needs attention",
  learning: "Learning",
  usual: "Usual",
};

/** "All (10)"; "All (—)" while loading. */
export const filterButtonText = (f: ListFilter, n: number | null) =>
  `${LIST_FILTER_LABEL[f]} (${n === null ? LIST_COUNT_PENDING : n})`;

/** "Showing changed residents", "Showing all residents" (UX-403). */
export const showingAnnouncement = (f: ListFilter) =>
  `Showing ${LIST_FILTER_LABEL[f].toLowerCase()} residents`;

/** Visually hidden caption "Residents in the study, all" (UX-043). */
export const listCaption = (f: ListFilter) =>
  `${LIST_HEADING}, ${LIST_FILTER_LABEL[f].toLowerCase()}`;

/** "Open chart for R09" (UX-037). */
export const openChartName = (code: string) => `Open chart for ${code}`;

/** "Showing 500 of 612 residents." (UX-041). */
export const showingOfTotal = (returned: number, total: number) =>
  `Showing ${returned} of ${total} residents.`;

/** Note under the panel (UX-407); the PI marker stays until OQ-12 is closed. */
export const LIST_NOTE_TEXT = "A status is a prompt to check on someone, not a diagnosis.";
export const listNote = (approved: boolean = CLINICAL_WORDING_APPROVED) =>
  approved ? LIST_NOTE_TEXT : `${LIST_NOTE_TEXT} ${PI_MARKER}`;

const RESTART_CAUSE_TEXT = {
  device: "a new device",
  firmware: "a firmware change",
  software: "a software change",
} as const;

/** The fields the §4.3.6 templates need, from a list row or a resident detail. */
interface HappeningInput {
  alarmSince: string | null;
  alarmReviewed: boolean | null;
  reasons: readonly string[];
  nUsable: number;
  nRequired: number;
  setAside: number;
  epoch: number | null;
  restartedOn: string | null;
  restartCause: keyof typeof RESTART_CAUSE_TEXT | null;
}

function isDetail(r: ResidentRow | ResidentDetail): r is ResidentDetail {
  return "baseline" in r;
}

function happeningInput(r: ResidentRow | ResidentDetail): HappeningInput {
  const common = {
    alarmSince: r.alarm_since,
    alarmReviewed: r.alarm_reviewed,
    reasons: r.attention_reasons,
    setAside: r.last_30_days.set_aside,
    restartCause: r.restart_cause,
  };
  if (isDetail(r)) {
    return {
      ...common,
      nUsable: r.baseline.n_usable,
      nRequired: r.baseline.n_required,
      epoch: r.current_epoch?.epoch_number ?? null,
      restartedOn: r.current_epoch?.started_on ?? null,
    };
  }
  return {
    ...common,
    nUsable: r.baseline_progress.n_usable,
    nRequired: r.baseline_progress.n_required,
    epoch: r.current_epoch,
    restartedOn: r.baseline_restarted_on,
  };
}

/** One "What's happening" sentence (TRD 11 §4.3.6, UX-405) for the row's display status. */
export function whatsHappening(
  row: ResidentRow | ResidentDetail,
  status: UiStatus,
  meta: Meta,
): string {
  const x = happeningInput(row);
  const date = (d: string) => formatLocalDate(d, meta.as_of, meta.facility_tz);
  switch (status) {
    case "changed": {
      const since = x.alarmSince
        ? `Changed from their usual since ${date(x.alarmSince)}.`
        : "Changed from their usual.";
      return `${since} ${x.alarmReviewed ? "Reviewed." : "Not reviewed yet."}`;
    }
    case "needs_attention": {
      const parts: string[] = [];
      if (x.reasons.includes("baseline_stalled")) {
        parts.push(`Missing many check-ins. Baseline stuck at ${x.nUsable} of ${x.nRequired}.`);
      }
      if (x.reasons.includes("high_set_aside")) {
        parts.push(`${x.setAside} check-ins too noisy or too short to use.`);
      }
      return parts.join(" ");
    }
    case "learning":
      return `Learning their usual: ${x.nUsable} of ${x.nRequired} check-ins so far.`;
    case "usual":
      if (x.epoch !== null && x.epoch > 1 && x.restartedOn) {
        const cause = RESTART_CAUSE_TEXT[x.restartCause ?? "device"];
        return `Usual. Baseline restarted ${date(x.restartedOn)} after ${cause}.`;
      }
      return "Within their usual range.";
  }
}
