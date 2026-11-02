// Copy for the Study team page (TRD 11 §4.18, UX-017, UX-306..UX-309, §4.4 Devices section).
// Every name is prefixed `STUDY_` / `study` so the `export *` barrel never clashes (TRD 04 FE-013).
import { formatLocalDate, formatLocalDateRange, plural } from "../format";
import type { AnalyticsKpis, DataAlertKind, Meta } from "../types";

export const STUDY_PAGE = "Study team"; // document title "Study team – EchoWell" (UX-229)
export const STUDY_H1 = "Study team: how the system is working";
export const STUDY_COUNTS_ONLY = "Counts only. No audio, no names.";
export const STUDY_ANSWER_KEY = " · numbers match the pipeline answer key";
export const STUDY_NO_RUN = "No pipeline run yet.";
export const STUDY_PANEL_ANALYTICS = "study team counts";

/** "pipeline test data v0.1, Oct 1–30, 2026 · numbers match the pipeline answer key" (UX-017). */
export function studyPeriodLine(meta: Meta, period: { from: string; to: string }): string {
  const range = formatLocalDateRange(period.from, period.to, { withYear: true });
  const key = meta.pipeline_profile === "test_v0_1" ? STUDY_ANSWER_KEY : "";
  return `${meta.data_source_label}, ${range}${key}`;
}

/** "R01", "R01 and R02", "R01, R02 and R03" (TRD 11 §4.4). */
export function studyJoinCodes(codes: readonly string[]): string {
  if (codes.length <= 1) return codes.join("");
  return `${codes.slice(0, -1).join(", ")} and ${codes[codes.length - 1]}`;
}

// KPI tiles (UX-351..UX-355)
export const STUDY_KPI = {
  received: "Check-ins received",
  used: "Used for scoring",
  baselines: "Baselines formed",
  alarms: "Alarms raised",
} as const;

export const studyOfExpected = (count: number, expected: number) =>
  `${count} of ${expected} expected`;
export const studyBaselinesValue = (formed: number, residents: number) =>
  `${formed} of ${residents}`;

function restartTimes(k: number): string {
  if (k === 1) return "once";
  if (k === 2) return "twice";
  return `${k} times`;
}

/** "R08 still forming; R07 restarted once", "R03, R08 still forming", "All baselines formed". */
export function studyBaselinesNote(b: AnalyticsKpis["baselines_formed"]): string {
  const parts: string[] = [];
  if (b.forming_resident_codes.length > 0) {
    parts.push(`${b.forming_resident_codes.join(", ")} still forming`);
  }
  for (const r of b.restarts) {
    if (r.restart_count > 0)
      parts.push(`${r.resident_code} restarted ${restartTimes(r.restart_count)}`);
  }
  return parts.length ? parts.join("; ") : "All baselines formed";
}

/** "R09, R10; neither reviewed yet", "none in this period" (UX-355). */
export function studyAlarmsNote(a: AnalyticsKpis["alarms_raised"]): string {
  if (a.count <= 0) return "none in this period";
  const open = a.not_reviewed_count;
  let state: string;
  if (open <= 0)
    state = a.count === 1 ? "reviewed" : a.count === 2 ? "both reviewed" : "all reviewed";
  else if (open >= a.count)
    state =
      a.count === 1
        ? "not reviewed yet"
        : a.count === 2
          ? "neither reviewed yet"
          : "none reviewed yet";
  else state = `${open} not reviewed yet`;
  const codes = a.resident_codes.join(", ");
  return codes ? `${codes}; ${state}` : state;
}

// Data problems to follow up (UX-306..UX-309)
export const STUDY_PROBLEMS_HEADING = "Data problems to follow up";
export const STUDY_PROBLEMS_EMPTY = "No data problems in the last 30 days.";
export const STUDY_TAG_STAFF = "Staff can help";
export const STUDY_TAG_TEAM = "Study team";
/** Kind order of the table in §4.18.2 (UX-307). */
export const STUDY_PROBLEM_ORDER: readonly DataAlertKind[] = [
  "baseline_stalled",
  "high_set_aside",
  "possible_other_speaker",
  "device_silent",
  "review_flagged_data_problem",
];
export const studyProblemTag = (kind: DataAlertKind) =>
  kind === "baseline_stalled" || kind === "high_set_aside" ? STUDY_TAG_STAFF : STUDY_TAG_TEAM;

// Check-ins per day (UX-356..UX-360)
export const STUDY_DAILY_HEADING = "Check-ins per day";
export const STUDY_LEGEND = {
  used: "Used",
  setAside: "Set aside",
  heldBack: "Held back (other voice)",
  missed: "Missed",
} as const;
export const STUDY_DAILY_TABLE_TOGGLE = "Show daily counts as a table";
export const STUDY_DAILY_COLUMNS = ["Date", "Used", "Set aside", "Held back", "Missed", "Note"];
/** "D02 silent", "D02, D05 silent"; "" when no device was silent. */
export const studySilentNote = (codes: readonly string[]) =>
  codes.length ? `${codes.join(", ")} silent` : "";
/** X-axis label "Oct 12: D02 silent". */
export const studyDayLabel = (date: string, codes: readonly string[]) =>
  codes.length ? `${formatLocalDate(date)}: ${studySilentNote(codes)}` : formatLocalDate(date);
export const studyDayTooltip = (
  date: string,
  d: { used: number; set_aside: number; quarantined: number; missed: number },
) =>
  `${formatLocalDate(date)}: ${d.used} used, ${d.set_aside} set aside, ${d.quarantined} held back, ${d.missed} missed`;
export const studyDailyChartName = (
  period: string,
  t: { used: number; set_aside: number; quarantined: number; missed: number },
) =>
  `Check-ins per day, ${period}: ${t.used} used, ${t.set_aside} set aside, ${t.quarantined} held back, ${t.missed} missed.`;

// Where check-ins are lost (UX-362..UX-366)
export const STUDY_FUNNEL_HEADING = "Where check-ins are lost";
export const STUDY_FUNNEL = {
  expected: "Expected",
  received: "Received",
  passed: "Passed quality checks",
  used: "Same speaker, used",
} as const;
export const studyExpectedNote = (residents: number, days: number, wholePeriod: boolean) =>
  wholePeriod
    ? `${residents} residents × ${days} days`
    : `sum of days enrolled across ${residents} residents`;
export const studyReceivedNote = (missed: number, duplicates: number) =>
  `${missed} missed; ${plural(duplicates, "duplicate copy", "duplicate copies")} removed`;
export function studyPassedNote(
  setAside: number,
  r: { quality_flag_poor: number; noise_above_limit: number; speech_too_short: number },
  multi: number,
): string {
  const base = `${setAside} set aside: quality flag ${r.quality_flag_poor}, noise ${r.noise_above_limit}, too short ${r.speech_too_short}`;
  if (multi <= 0) return base;
  const extra = r.quality_flag_poor + r.noise_above_limit + r.speech_too_short - setAside;
  return extra === multi
    ? `${base} (${multi} had two reasons)`
    : `${base} (${multi} had more than one reason)`;
}
export const studyHeldBackNote = (n: number) => `${n} held back as possible other voice`;

// Usable check-ins by resident (UX-367..UX-370)
export const STUDY_BY_RESIDENT_HEADING = "Usable check-ins by resident";
export const studyByResidentSubtitle = (days: number) => `Share of ${days} days, lowest first`;
export const studyByResidentRowName = (r: {
  code: string;
  used: number;
  days: number;
  percent: string;
  setAside: number;
  heldBack: number;
  missed: number;
}) =>
  `${r.code}: ${r.used} of ${r.days} days usable (${r.percent}); ${r.setAside} set aside; ${r.heldBack} held back; ${r.missed} missed.`;

// Alarm timing check / Alarms and review outcomes (UX-371..UX-376)
export const STUDY_TIMING_HEADING = "Alarm timing check";
export const STUDY_TIMING_TABLE_NAME = "Alarm timing table";
export const STUDY_TIMING_LINE = "Test data only, where the true change date is known.";
export const STUDY_TIMING_COLUMNS = [
  "Resident",
  "Planted change",
  "Change began",
  "Alarm rang",
  "Delay",
];
export const STUDY_TIMING_CAPTION =
  "With real residents the true change date is unknown, so this panel becomes: alarms raised, alarms reviewed, and review outcomes.";
export const STUDY_TIMING_NONE = "None";
export const STUDY_TIMING_NO_ALARM = "No alarm";
export const STUDY_TIMING_MISSED = "Missed";
export const STUDY_TIMING_FALSE_ALARM = "False alarm";
export const STUDY_TIMING_CORRECT = "Correct";
export const studyTimingDelay = (d: number) => plural(d, "day", "days");
export const studyTimingOther = (k: number) => `Other ${k}`;
export const studyTimingAlarms = (n: number) => plural(n, "alarm", "alarms");
export const studyTimingFalseAlarms = (n: number) => plural(n, "false alarm", "false alarms");

export const STUDY_OUTCOMES_HEADING = "Alarms and review outcomes";
export const STUDY_OUTCOMES_FIRST_COLUMN = "Measure"; // visually hidden; the header cell reads ""
export const STUDY_OUTCOMES_COUNT = "Count";
export const STUDY_OUTCOMES = {
  raised: "Alarms raised",
  reviewed: "Reviewed",
  no_concern: "Checked on resident, no concern",
  known_cause: "Explained by a known cause",
  referred: "Referred to nurse or provider",
  data_problem: "Looks like a data problem: send to study team",
} as const;

// Devices section (TRD 11 §4.4, UX-050..UX-058)
export const STUDY_DEVICES_HEADING = "Devices";
export const STUDY_DEVICES_PANEL = "devices";
export const STUDY_DEVICES_EMPTY = "No devices are registered yet.";
export const STUDY_DEVICE_ONLINE = "● Online";
export const STUDY_DEVICE_NO_UPLOAD = "○ No upload today";
export const studyShowAllDevices = (n: number) => `Show all devices (${n})`;
export const STUDY_DEVICE_COLUMNS = [
  "Device",
  "Residents",
  "In use",
  "Last upload",
  "Firmware",
  "Days with no device activity (last 30 days)",
  "Silent days (shared device)",
];

/** " Silent all day Oct 12." / " Silent all day on 5 days (latest Oct 27)." / "" (§4.4). */
export function studySilentText(days: readonly string[]): string {
  if (days.length === 0) return "";
  const sorted = [...days].sort();
  if (sorted.length <= 3)
    return ` Silent all day ${sorted.map((d) => formatLocalDate(d)).join(", ")}.`;
  return ` Silent all day on ${sorted.length} days (latest ${formatLocalDate(sorted[sorted.length - 1]!)}).`;
}
export const studyFirmwareText = (v: string | null) => (v ? ` Firmware ${v}.` : "");
/** "last upload Oct 30, 2:55 PM CT" or "no upload yet". */
export const studyLastUpload = (dt: string | null, capital = false) => {
  if (dt) return `${capital ? "Last" : "last"} upload ${dt}`;
  return capital ? "No upload yet" : "no upload yet";
};
export const studySharedRest = (codes: readonly string[], lastUpload: string | null) =>
  ` (shared by ${studyJoinCodes(codes)}): ${studyLastUpload(lastUpload)}.`;
export const studyReplacementRest = (
  codes: readonly string[],
  since: string,
  old: string,
  lastUpload: string | null,
) =>
  ` (${studyJoinCodes(codes)}): in use since ${since}, replacing ${old}. ${studyLastUpload(lastUpload, true)}.`;
export const studyAttentionRest = (codes: readonly string[], lastUpload: string | null) =>
  `${codes.length ? ` (${studyJoinCodes(codes)})` : ""}: ${studyLastUpload(lastUpload)}.`;
export const studyGroupedRest = (asOfDate: string) => ` all uploaded ${formatLocalDate(asOfDate)}.`;
export const studyInUseSince = (since: string) => `Since ${formatLocalDate(since)}`;
export const studyInUseRange = (from: string, to: string, replacedBy: string | null) =>
  `${formatLocalDateRange(from, to)}${replacedBy ? ` · replaced by ${replacedBy}` : ""}`;
/** "0", "1 (Oct 12)", "12 (latest Oct 21, Oct 24, Oct 27)" (UX-056: up to 3 dates). */
export function studyDayCount(days: readonly string[]): string {
  if (days.length === 0) return "0";
  const sorted = [...days].sort();
  if (sorted.length <= 3)
    return `${sorted.length} (${sorted.map((d) => formatLocalDate(d)).join(", ")})`;
  const latest = sorted.slice(-3).map((d) => formatLocalDate(d));
  return `${sorted.length} (latest ${latest.join(", ")})`;
}
export const STUDY_EMPTY_CELL = "—";

// Downloads (UX-377)
export const STUDY_DOWNLOADS_HEADING = "Downloads";
export const STUDY_DOWNLOAD_SCORES = "Scores (CSV)";
export const STUDY_DOWNLOAD_BASELINES = "Baselines (CSV)";
export const STUDY_DOWNLOADING = "Downloading…";
export const studyDownloadFailed = (what: string) =>
  `Could not download ${what}. Check your connection and try again.`;
export const studyCsvName = (kind: "scores" | "baselines", asOfDate: string) =>
  `echowell_${kind}_${asOfDate}.csv`;
