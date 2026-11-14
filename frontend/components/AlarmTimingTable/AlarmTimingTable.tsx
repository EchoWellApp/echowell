// "Alarm timing check", test profile only (TRD 11 UX-371..UX-374, UX-376). Rows come pre-built by
// `buildAlarmTimingRows()` so the table itself only renders strings.
import { naturalCompare } from "@/lib/deviceGroups";
import { formatLocalDate } from "@/lib/format";
import type { AlarmTimingRow } from "@/lib/types";
import {
  STUDY_TIMING_CAPTION,
  STUDY_TIMING_COLUMNS,
  STUDY_TIMING_CORRECT,
  STUDY_TIMING_FALSE_ALARM,
  STUDY_TIMING_HEADING,
  STUDY_TIMING_TABLE_NAME,
  STUDY_TIMING_LINE,
  STUDY_TIMING_MISSED,
  STUDY_TIMING_NONE,
  STUDY_TIMING_NO_ALARM,
  studyTimingAlarms,
  studyTimingDelay,
  studyTimingFalseAlarms,
  studyTimingOther,
} from "@/lib/wording";
import styles from "./AlarmTimingTable.module.css";

export interface AlarmTimingDisplayRow {
  label: string;
  planted_change: string;
  change_began: string | null;
  alarm_rang: string | null;
  delay: string;
}

export interface AlarmTimingTableProps {
  rows: AlarmTimingDisplayRow[];
}

const NO_PLANTED = "None";

/** One row per planted change (resident order), then "Other <k>" (UX-372, UX-373). */
export function buildAlarmTimingRows(api: readonly AlarmTimingRow[]): AlarmTimingDisplayRow[] {
  const planted = api
    .filter((r) => r.planted_change !== NO_PLANTED)
    .sort((a, b) => naturalCompare(a.resident_code, b.resident_code));
  const out: AlarmTimingDisplayRow[] = planted.map((r) => ({
    label: r.resident_code,
    planted_change: r.planted_change,
    change_began: r.change_began ? formatLocalDate(r.change_began) : null,
    alarm_rang: r.alarm_rang ? formatLocalDate(r.alarm_rang) : null,
    delay:
      r.result === "false_alarm"
        ? STUDY_TIMING_FALSE_ALARM
        : r.alarm_rang === null || r.result === "missed"
          ? STUDY_TIMING_MISSED
          : studyTimingDelay(r.delay_days ?? 0),
  }));
  const others = api.filter((r) => r.planted_change === NO_PLANTED);
  if (others.length > 0) {
    const alarmed = others.filter(
      (r) => r.alarm_rang !== null || r.result === "false_alarm",
    ).length;
    out.push({
      label: studyTimingOther(others.length),
      planted_change: STUDY_TIMING_NONE,
      change_began: null,
      alarm_rang: alarmed ? studyTimingAlarms(alarmed) : null,
      delay: alarmed ? studyTimingFalseAlarms(alarmed) : STUDY_TIMING_CORRECT,
    });
  }
  return out;
}

export function AlarmTimingTable({ rows }: AlarmTimingTableProps) {
  return (
    <section className="panel pad stack" aria-labelledby="timing-heading">
      <h2 id="timing-heading">{STUDY_TIMING_HEADING}</h2>
      <p className="small muted">{STUDY_TIMING_LINE}</p>
      {/* eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex -- scroll container (UX-243) */}
      <div className="scroll-x" tabIndex={0} role="region" aria-label={STUDY_TIMING_TABLE_NAME}>
        <table className={styles.table}>
          <thead>
            <tr>
              {STUDY_TIMING_COLUMNS.map((c) => (
                <th key={c} scope="col">
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.label}>
                <th scope="row">{r.label}</th>
                <td>{r.planted_change}</td>
                <td>{r.change_began ?? STUDY_TIMING_NONE}</td>
                <td>{r.alarm_rang ?? STUDY_TIMING_NO_ALARM}</td>
                <td>{r.delay}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="caption">{STUDY_TIMING_CAPTION}</p>
    </section>
  );
}
