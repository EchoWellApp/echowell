// Text alternative of the change score chart: "Date", "Change score", "Alarm" (TRD 11 UX-090,
// TRD 04 FE-097, FE-184, TRD 13 TST-112).
import { formatLocalDate, formatTally } from "@/lib/format";
import type { ScorePoint } from "@/lib/types";
import { TRENDS_ALARM_TEXT, TRENDS_TABLE_COLUMNS, trendsTableCaption } from "@/lib/wording";
import styles from "./ChangeScoreTable.module.css";

export interface ChangeScoreTableProps {
  points: ScorePoint[];
  /** The alarm line; the "Alarm" column follows `alarm_state`, never a comparison with h. */
  h: number;
}

export function ChangeScoreTable({ points }: ChangeScoreTableProps) {
  const code = points[0]?.resident_code ?? "";
  return (
    <table className={styles.table}>
      <caption className={styles.caption}>{trendsTableCaption(code)}</caption>
      <thead>
        <tr>
          <th scope="col">{TRENDS_TABLE_COLUMNS.date}</th>
          <th scope="col">{TRENDS_TABLE_COLUMNS.score}</th>
          <th scope="col">{TRENDS_TABLE_COLUMNS.alarm}</th>
        </tr>
      </thead>
      <tbody>
        {points.map((p) => (
          <tr key={p.session_id} data-alarm-state={p.alarm_state}>
            <td>{formatLocalDate(p.local_date)}</td>
            <td className={styles.num}>{formatTally(p.cusum_tally)}</td>
            <td className={p.alarm_state === "off" ? undefined : styles.alarm}>
              {TRENDS_ALARM_TEXT[p.alarm_state]}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
