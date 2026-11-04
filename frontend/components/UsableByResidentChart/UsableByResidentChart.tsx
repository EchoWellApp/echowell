// "Usable check-ins by resident" (TRD 11 UX-367..UX-370): data completeness, not health.
import Link from "next/link";
import { formatPercent } from "@/lib/format";
import { naturalCompare } from "@/lib/deviceGroups";
import type { ByResidentRow } from "@/lib/types";
import {
  STUDY_BY_RESIDENT_HEADING,
  studyByResidentRowName,
  studyByResidentSubtitle,
} from "@/lib/wording";
import styles from "./UsableByResidentChart.module.css";

export interface UsableByResidentChartProps {
  rows: ByResidentRow[];
}

const share = (r: ByResidentRow) => (r.days > 0 ? r.used_days / r.days : 0);

/** Percentage ascending, ties by natural resident-code order (UX-369). */
export function orderByUsable(rows: readonly ByResidentRow[]): ByResidentRow[] {
  return [...rows].sort((a, b) => {
    const pa = parseInt(formatPercent(a.used_days, a.days), 10);
    const pb = parseInt(formatPercent(b.used_days, b.days), 10);
    return pa - pb || naturalCompare(a.resident_code, b.resident_code);
  });
}

export function UsableByResidentChart({ rows }: UsableByResidentChartProps) {
  const ordered = orderByUsable(rows);
  const days = Math.max(0, ...rows.map((r) => r.days));
  return (
    <section className="panel pad stack" aria-labelledby="by-resident-heading">
      <h2 id="by-resident-heading">{STUDY_BY_RESIDENT_HEADING}</h2>
      <p className="small muted">{studyByResidentSubtitle(days)}</p>
      <ul className={styles.list}>
        {ordered.map((r) => {
          const percent = formatPercent(r.used_days, r.days);
          const name = studyByResidentRowName({
            code: r.resident_code,
            used: r.used_days,
            days: r.days,
            percent,
            setAside: r.set_aside_days,
            heldBack: r.quarantined_days,
            missed: r.missed_days,
          });
          return (
            <li key={r.resident_code} data-testid="by-resident-row">
              <div className={styles.row} role="group" aria-label={name}>
                <Link href={`/residents/${r.resident_code}/log`} className={styles.code}>
                  {r.resident_code}
                </Link>
                <span className={styles.meter} aria-hidden="true">
                  <i style={{ width: `${Number((share(r) * 100).toFixed(1))}%` }} />
                </span>
                <span className={styles.percent}>{percent}</span>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
