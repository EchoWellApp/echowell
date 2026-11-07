// Resident chart copy: banner, section navigation, Summary, Baseline and Check-in log (TRD 11
// §4.5 intro, §4.5.1, §4.5.2, §4.5.2.1, §4.5.6, §4.5.7, §4.5.7.1, UX-312; TRD 04 FE-013, FE-032).
// Every template is filled with API values; nothing here computes a status, count or date.
import { formatLocalDate, formatLocalDateRange, formatThreshold } from "../format";
import type { CheckinEvent, Meta, ResidentDetail } from "../types";
import { CLINICAL_WORDING_APPROVED, PI_MARKER, pageTitle } from "./common";

// ---------------------------------------------------------------------------------------------
// Sections, titles and navigation (UX-410, UX-411, UX-229, FE-032)

export type ChartSectionKey = "summary" | "review" | "trends" | "baseline" | "log" | "device";

export const CHART_SECTION_ORDER: readonly ChartSectionKey[] = [
  "summary",
  "review",
  "trends",
  "baseline",
  "log",
  "device",
];

export const CHART_SECTION_LABEL: Record<ChartSectionKey, string> = {
  summary: "Summary",
  review: "Review and notes",
  trends: "Voice trends",
  baseline: "Baseline",
  log: "Check-in log",
  device: "Device",
};

/** "/residents/R09", "/residents/R09/review", … */
export const chartSectionHref = (code: string, section: ChartSectionKey) =>
  section === "summary"
    ? `/residents/${encodeURIComponent(code)}`
    : `/residents/${encodeURIComponent(code)}/${section}`;

/** The page part of the document title: "R09 · Summary" (UX-229). */
export const chartPageName = (code: string, section: ChartSectionKey) =>
  `${code} · ${CHART_SECTION_LABEL[section]}`;

/** "R09 · Summary – EchoWell" (FE-032). */
export const chartTitle = (code: string, section: ChartSectionKey) =>
  pageTitle(chartPageName(code, section));

export const CHART_NAV_LABEL = "Resident chart";
/** Suffix of the "Review and notes" accessible name: "Review and notes, alarm not reviewed". */
export const CHART_REVIEW_BADGE_LABEL = "alarm not reviewed";

// ---------------------------------------------------------------------------------------------
// Banner (UX-061..UX-063)

export const CHART_BANNER_LABEL = "Resident";
export const CHART_FACT = {
  device: "Device",
  lastCheckin: "Last check-in",
  usable: "Usable check-ins, last 30 days",
  baseline: "Baseline",
} as const;
export const CHART_PENDING = "—";
export const CHART_NO_CHECKINS = "No check-ins yet";
export const CHART_BASELINE_COMPLETE = "Complete";

/** "R01, R02 and R03" (three or more codes); "R02 and R03"; "R03". */
export function joinCodes(codes: readonly string[]): string {
  if (codes.length <= 1) return codes.join("");
  return `${codes.slice(0, -1).join(", ")} and ${codes[codes.length - 1]}`;
}

/** "D07B (replaced D07)", "D02 (shared with R03)", "D09" (UX-063). */
export function bannerDeviceText(device: ResidentDetail["device"]): string {
  const code = device.device_code ?? CHART_PENDING;
  if (device.previous_device_code) return `${code} (replaced ${device.previous_device_code})`;
  if (device.shared && device.shared_with.length > 0) {
    return `${code} (shared with ${joinCodes(device.shared_with)})`;
  }
  return code;
}

/** "30 of 30", "13 of 30". */
export const bannerUsableText = (used: number, days: number) => `${used} of ${days}`;

/** "Complete" or "13 of 16". */
export const bannerBaselineText = (b: ResidentDetail["baseline"]) =>
  b.state === "frozen" ? CHART_BASELINE_COMPLETE : `${b.n_usable} of ${b.n_required}`;

/** Panel names for "Loading <panel>…" and "Could not load <panel>. …" (UX-200, UX-203). */
export const CHART_PANEL = {
  resident: "resident",
  alarm: "alarm details",
  summary: "summary",
  baseline: "baseline",
  counts: "check-in counts",
  events: "check-in events",
  earlier: "earlier entries",
} as const;

// ---------------------------------------------------------------------------------------------
// Summary "Right now" (UX-070..UX-077, §4.5.2.1)

export const RIGHT_NOW = "Right now";
export const MORE_DETAIL = "More detail";

export const SUMMARY_FACT = {
  alarmStarted: "Alarm started",
  open: "Open",
  reviewStatus: "Review status",
  notReviewed: "Not reviewed",
  reviewed: "Reviewed",
} as const;

export const SUMMARY_BUTTON = {
  review: "Review this alert",
  trends: "See what changed",
  log: "See missed and set-aside check-ins",
  device: "Check the device",
} as const;

const NEEDS_ATTENTION_TAIL =
  " EchoWell can’t judge their voice well until more good check-ins come in.";

type Cause = "device" | "firmware" | "software";

/** Old and new value of the current epoch's restart (device codes or versions). */
export interface RestartFacts {
  cause: Cause;
  on: string; // local date
  from: string;
  to: string;
}

/** Restart facts from a `baseline_restarted` event, falling back to the resident detail. */
export function restartFacts(
  resident: ResidentDetail,
  event: CheckinEvent | null = null,
): RestartFacts | null {
  const epoch = resident.current_epoch;
  if (!epoch || epoch.epoch_number <= 1) return null;
  const cause: Cause = event?.restart_cause ?? resident.restart_cause ?? "device";
  const from =
    event?.from_value ??
    event?.previous_device_code ??
    epoch.from_value ??
    resident.device.previous_device_code ??
    "";
  const to = event?.to_value ?? epoch.to_value ?? epoch.device_code;
  return { cause, on: event?.local_date ?? epoch.started_on, from, to };
}

const date = (d: string, meta: Meta) => formatLocalDate(d, meta.as_of, meta.facility_tz);

/** " The baseline restarted on Oct 13 because the device changed (D07B, was D07); R07 is … ." */
export function summaryRestartSentence(code: string, r: RestartFacts, meta: Meta): string {
  const cause =
    r.cause === "device"
      ? `the device changed (${r.to}, was ${r.from})`
      : r.cause === "firmware"
        ? "the device firmware changed"
        : "the extraction software changed";
  return ` The baseline restarted on ${date(r.on, meta)} because ${cause}; ${code} is now compared only with the new baseline.`;
}

export const leadChangedAbove = (code: string, alarmDate: string) =>
  `${code}’s voice has moved away from their own usual pattern, steadily and long enough to set off the alarm on ${alarmDate}. It is still changed.`;

export const leadChangedBelow = (code: string, alarmDate: string) =>
  `${code}’s voice moved away from their own usual pattern, steadily and long enough to set off the alarm on ${alarmDate}. The change score is now below the alarm line, but the alarm stays on: in this version alarms are not switched off automatically.`;

export const leadNeedsAttention = (happening: string) => `${happening}${NEEDS_ATTENTION_TAIL}`;

export const leadLearning = (code: string, n: number, total: number) =>
  `EchoWell is still learning ${code}’s usual pattern: ${n} of ${total} usable check-ins so far. Nothing is scored and no alarm can ring until the baseline is complete.`;

export const leadUsualScored = (code: string) =>
  `${code}’s voice is within their own usual range. Nothing to do.`;

export const leadUsualNotScored = (code: string) =>
  `${code}’s baseline is complete. Comparing starts with the next usable check-in.`;

/** Note at the end of "Right now" (UX-072, UX-073). */
export function summaryNote(
  code: string,
  learning: boolean,
  approved: boolean = CLINICAL_WORDING_APPROVED,
): string {
  const text = learning
    ? `Once the baseline is complete, ${code} will be compared only with ${code}. A change is a prompt to check in, not a diagnosis.`
    : `This compares ${code} only with ${code}. It is a prompt to check in, not a diagnosis.`;
  return approved ? text : `${text} ${PI_MARKER}`;
}

// Leaning most (UX-312): the §4.5.4 plain-language labels, lower case.
export const CHART_LEANING_LABEL: Record<string, string> = {
  loudness_dbfs: "quieter",
  total_phrase_duration_s: "slower to say the phrase",
  speech_rate_syl_per_s: "fewer syllables per second",
  articulation_rate_syl_per_s: "slower while talking",
  number_of_pauses: "more pauses",
  pause_fraction: "more time in pauses",
  voiced_fraction: "less voiced sound",
};

export const LEANING_NONE = "no single measurement stands out.";

/** "Leaning most: more pauses, quieter, less voiced sound" (at most 3 labels). */
export function leaningMostText(keys: readonly string[]): string {
  const labels = keys
    .map((k) => CHART_LEANING_LABEL[k])
    .filter((l): l is string => Boolean(l))
    .slice(0, 3);
  return `Leaning most: ${labels.length ? labels.join(", ") : LEANING_NONE}`;
}

// More detail tiles (UX-078)
export const TILE = {
  trends: "Voice trends",
  baseline: "Baseline",
  checkins: "Check-ins, last 30 days",
  device: "Device",
  open: "Open",
  notScored: "Not scored yet",
  noChange: "No change",
} as const;
export const tileChangeScore = (tally: string) => `Change score ${tally}`;
export const tileBaseline = (n: number, total: number) => `${n} of ${total} check-ins`;
export const tileCheckins = (used: number, missed: number) => `${used} used, ${missed} missed`;
export const tileDevice = (code: string, online: boolean) =>
  `${code} ${online ? "online" : "no upload today"}`;

// ---------------------------------------------------------------------------------------------
// Baseline section (UX-420..UX-423, §4.5.7.1)

export const baselineHeading = (code: string) => `Baseline: ${code}’s usual`;

export function baselineRestartPrefix(r: RestartFacts, meta: Meta): string {
  const on = date(r.on, meta);
  if (r.cause === "device") {
    return `Restarted ${on} when the device was replaced (${r.from} to ${r.to}), so readings from the old device are not mixed in. `;
  }
  const what = r.cause === "firmware" ? "the device firmware" : "the extraction software";
  return `Restarted ${on} when ${what} changed (${r.from} to ${r.to}), so earlier readings are not mixed in. `;
}

export const baselineFrozenScored = (n: number, range: string, since: string) =>
  `First ${n} usable check-ins, ${range}, then frozen. Compared with it since ${since}.`;

export const baselineFrozenNotScored = (n: number, range: string) =>
  `First ${n} usable check-ins, ${range}, then frozen. Comparing starts with the next usable check-in.`;

export function baselineForming(
  n: number,
  total: number,
  missed: number,
  setAside: number,
): string {
  const head = `Still forming: ${n} of ${total} usable check-ins so far.`;
  if (missed <= 0 && setAside <= 0) return head;
  return `${head} ${missed} missed and ${setAside} set-aside check-ins in the last 30 days have slowed it down.`;
}

/** The first paragraph of the Baseline panel (UX-421). */
export function baselineText(
  resident: ResidentDetail,
  restart: RestartFacts | null,
  firstScoredDate: string | null,
  meta: Meta,
): string {
  const b = resident.baseline;
  const prefix = restart ? baselineRestartPrefix(restart, meta) : "";
  if (b.state === "forming" || !b.first_local_date || !b.frozen_after_local_date) {
    const c = resident.last_30_days;
    return prefix + baselineForming(b.n_usable, b.n_required, c.missed, c.set_aside);
  }
  const range = formatLocalDateRange(b.first_local_date, b.frozen_after_local_date);
  return (
    prefix +
    (firstScoredDate
      ? baselineFrozenScored(b.n_required, range, date(firstScoredDate, meta))
      : baselineFrozenNotScored(b.n_required, range))
  );
}

/** "13 of 16 usable check-ins" (meter name and caption, UX-422). */
export const baselineMeterText = (n: number, total: number) => `${n} of ${total} usable check-ins`;

export const baselineExplanation = (n: number) =>
  `The baseline is built from the first ${n} usable check-ins, then frozen so slow changes still show up. It restarts if the resident gets a new device or the device or extraction software changes.`;

// ---------------------------------------------------------------------------------------------
// Check-in log (UX-140..UX-150, §4.5.6)

export const COUNTS_HEADING = "Check-ins, last 30 days";
export const COUNT_LABEL = {
  used: "Used",
  set_aside: "Set aside (noise, poor quality or too short)",
  quarantined: "Held back (possible other voice)",
  missed: "Missed",
} as const;

export const EVENTS_HEADING = "Events";
export const EVENTS_EMPTY = "Nothing to report yet.";
export const DUPLICATES_CAPTION = "Duplicate records are removed quietly and not shown.";
export const SHOW_EARLIER = "Show earlier entries";
export const LOADING_EARLIER = "Loading earlier entries…";

export interface LogLineContext {
  h: number;
  baselineN: number;
  currentDeviceCode: string | null;
}

/** The silent device of a `device_silent` event: the API's device_code (TRD 24 D-145). */
function silentDevice(e: CheckinEvent, ctx: LogLineContext): string {
  return e.device_code ?? ctx.currentDeviceCode ?? "";
}

/** The line text of one check-in event (UX-142, FE-101). */
export function logLine(e: CheckinEvent, ctx: LogLineContext): string {
  switch (e.event_type) {
    case "alarm_on":
      return `Alarm on. Change score crossed ${formatThreshold(ctx.h)}.`;
    case "watching_started":
      return "Comparing with baseline started.";
    case "baseline_complete": {
      const m = /^(\d+) of (\d+)$/.exec(e.detail ?? "");
      return `Baseline complete (${m ? `${m[1]} of ${m[2]}` : `${ctx.baselineN} of ${ctx.baselineN}`}).`;
    }
    case "baseline_restarted":
      if (e.restart_cause === "firmware") {
        return `Device firmware changed (${e.from_value ?? ""} to ${e.to_value ?? ""}). Baseline restarted.`;
      }
      if (e.restart_cause === "software") {
        return `Extraction software changed (${e.from_value ?? ""} to ${e.to_value ?? ""}). Baseline restarted.`;
      }
      return `New device ${e.to_value ?? e.device_code ?? ctx.currentDeviceCode ?? ""}. Baseline restarted.`;
    case "set_aside":
      return `Check-in set aside: ${e.detail ?? ""}.`;
    case "quarantined":
      return "Check-in held back: possible other voice.";
    case "missed":
      return "Check-in missed.";
    case "device_silent":
      return `Shared device ${silentDevice(e, ctx)} silent all day. Check-in missed.`;
    case "checkins_started":
      return e.device_code && e.device_code !== ctx.currentDeviceCode
        ? `Check-ins started on ${e.device_code}.`
        : "Check-ins started.";
  }
}
