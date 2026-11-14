// "Check-ins, last 30 days" count tiles (TRD 11 UX-140, §4.3.5, UX-047, UX-048, UX-200).
import type { ResidentDetail } from "@/lib/types";
import { CHART_PENDING, COUNTS_HEADING, COUNT_LABEL } from "@/lib/wording";
import styles from "./CheckinCounts.module.css";

export interface CheckinCountsProps {
  /** The API `last_30_days` counts; null while loading ("—"). */
  counts: ResidentDetail["last_30_days"] | null;
}

const ORDER = ["used", "set_aside", "quarantined", "missed"] as const;

export function CheckinCounts({ counts }: CheckinCountsProps) {
  return (
    <section className="panel pad stack" aria-labelledby="checkin-counts">
      <h2 id="checkin-counts">{COUNTS_HEADING}</h2>
      <ul className={styles.counts}>
        {ORDER.map((k) => (
          <li key={k}>
            <b>{counts ? counts[k] : CHART_PENDING}</b>
            <span>{COUNT_LABEL[k]}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
