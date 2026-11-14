// Copy for the Voice trends section (TRD 11 §4.5.3, §4.5.4; TRD 04 FE-013, FE-097).
import { formatLocalDate, formatSigned, formatTally, formatThreshold } from "../format";
import type { ScorePoint } from "../types";

export const TRENDS_SECTION = "Voice trends";
export const TRENDS_SCORE_HEADING = "Change score";
export const TRENDS_SCORE_PANEL = "the change score";
export const TRENDS_MEASURES_HEADING = "The 7 voice measurements behind the score";
export const TRENDS_MEASURES_PANEL = "the voice measurements";

/** Document title page part: "R09 · Voice trends" (FE-032). */
export const trendsPageTitle = (code: string) => `${code} · ${TRENDS_SECTION}`;

/** UX-080 intro line. */
export const trendsScoreIntro = (code: string, h: number) =>
  `Goes up when check-ins keep leaning away from ${code}’s usual. The alarm turns on at ${formatThreshold(h)}. Missed, set-aside and held-back check-ins leave it unchanged.`;

/** UX-089: shown instead of the chart while the baseline is forming. */
export const trendsForming = (n: number, required: number) =>
  `No change score yet. Scoring starts after the baseline is complete (${n} of ${required} usable check-ins so far).`;

/** Shown for a device period with neither a baseline nor a scored session (e.g. an earlier epoch). */
export const TRENDS_NO_SCORED = "No check-ins were scored in this device period.";

/** UX-092: line above the chart when the current epoch is greater than 1. */
export const trendsDevicePeriod = (startedOn: string) =>
  `Showing the current device period since ${formatLocalDate(startedOn)}. Earlier periods are not scored against this baseline.`;

/** FEAT-067-FR-14: the epoch selector. */
export const TRENDS_EPOCH_LABEL = "Device period";
export const trendsEpochOption = (n: number, current: number) =>
  n === current ? `Period ${n} (current)` : `Period ${n}`;

/** UX-082 baseline slot label: "Baseline Oct 1–16". */
export const trendsBaselineLabel = (range: string) => `Baseline ${range}`;

/** UX-084 reference line label: "Alarm line: 5". */
export const trendsAlarmLine = (h: number) => `Alarm line: ${formatThreshold(h)}`;

/** UX-085 marker and tick of the first crossing. */
export const TRENDS_ALARM_MARKER = "▲";
export const trendsAlarmTick = (monthDay: string) => `${monthDay} · alarm`;

/** UX-086 bar tooltip "<Mon D>: <value>". */
export const trendsBarTooltip = (localDate: string, tally: number) =>
  `${formatLocalDate(localDate)}: ${formatTally(tally)}`;

/** Accessible name of the scroll container (UX-243). */
export const TRENDS_CHART_SCROLL_NAME = "Change score chart";

/**
 * UX-091 text alternative: "Change score for R09 from Oct 17 to Oct 30. Baseline Oct 1–16.
 * Alarm line 5. Crossed the alarm line on Oct 21; now 26.8."
 */
export function changeScoreSummary(input: {
  residentCode: string;
  points: Pick<ScorePoint, "local_date" | "cusum_tally" | "alarm_state">[];
  baselineRange: string | null;
  h: number;
}): string {
  const { residentCode, points, baselineRange, h } = input;
  const parts: string[] = [];
  const first = points[0];
  const last = points[points.length - 1];
  if (first && last) {
    parts.push(
      `Change score for ${residentCode} from ${formatLocalDate(first.local_date)} to ${formatLocalDate(last.local_date)}.`,
    );
  } else {
    parts.push(`Change score for ${residentCode}: no scored check-ins yet.`);
  }
  if (baselineRange) parts.push(`Baseline ${baselineRange}.`);
  parts.push(`Alarm line ${formatThreshold(h)}.`);
  if (last) {
    const rings = points.find((p) => p.alarm_state === "rings");
    const crossed = rings
      ? `Crossed the alarm line on ${formatLocalDate(rings.local_date)};`
      : "Below the alarm line throughout;";
    parts.push(`${crossed} now ${formatTally(last.cusum_tally)}.`);
  }
  return parts.join(" ");
}

// UX-090 table alternative
export const TRENDS_TABLE_TOGGLE = "Show change score as a table";
export const TRENDS_TABLE_COLUMNS = {
  date: "Date",
  score: "Change score",
  alarm: "Alarm",
} as const;
export const TRENDS_ALARM_TEXT: Record<ScorePoint["alarm_state"], string> = {
  off: "—",
  rings: "▲ Alarm rings (first crossing)",
  on: "▲ Alarm on",
};
export const trendsTableCaption = (code: string) => `Change score for ${code}, by scored check-in`;

// §4.5.4 measurement cards
export interface TrendsMeasure {
  key: string;
  label: string;
  technicalName: string;
}

/** The 7 scored measurements in the order of TRD 11 §4.5.4 (UX-101, UX-163). */
export const TRENDS_MEASURES: readonly TrendsMeasure[] = [
  { key: "loudness_dbfs", label: "Quieter", technicalName: "loudness" },
  {
    key: "total_phrase_duration_s",
    label: "Slower to say the phrase",
    technicalName: "phrase duration",
  },
  {
    key: "speech_rate_syl_per_s",
    label: "Fewer syllables per second",
    technicalName: "speech rate",
  },
  {
    key: "articulation_rate_syl_per_s",
    label: "Slower while talking",
    technicalName: "articulation rate",
  },
  { key: "number_of_pauses", label: "More pauses", technicalName: "number of pauses" },
  { key: "pause_fraction", label: "More time in pauses", technicalName: "pause fraction" },
  { key: "voiced_fraction", label: "Less voiced sound", technicalName: "voiced fraction" },
];

/** UX-100 intro line. */
export const trendsMeasuresIntro = (code: string) =>
  `Each is compared with ${code}’s own baseline. The score rises when the voice is:`;

export const TRENDS_NOT_SCORED = "Not scored yet";

/** UX-103 sparkline accessible name. */
export const trendsSparklineName = (
  label: string,
  technicalName: string,
  latest: number,
  k: number,
) =>
  `${label} (${technicalName}): latest ${formatSigned(latest)} compared with own baseline over ${k} scored ${k === 1 ? "check-in" : "check-ins"}`;

/** UX-106 eighth card. */
export const trendsOtherMeasures = (n: number) =>
  `${n} other measurements (pitch, jitter, MFCCs and others)`;
export const TRENDS_STORED_NOT_SCORED = "Stored, not scored";

/** UX-108 caption. */
export const TRENDS_MEASURES_CAPTION =
  "Measurement names are placeholders until Team 1 confirms the openSMILE output names. Morning check-ins are adjusted before comparing.";
