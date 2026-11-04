// Status legend under the residents table: each pill with its meaning (TRD 11 UX-406, §4.3.4).
import { StatusPill } from "@/components/StatusPill/StatusPill";
import { UI_STATUSES } from "@/lib/status";
import type { Meta } from "@/lib/types";
import { LIST_LEGEND_NAME, statusMeaning } from "@/lib/wording";
import styles from "./StatusLegend.module.css";

export interface StatusLegendProps {
  meta: Meta;
}

export function StatusLegend({ meta }: StatusLegendProps) {
  return (
    <ul className={styles.legend} aria-label={LIST_LEGEND_NAME}>
      {UI_STATUSES.map((s) => (
        <li key={s} className={styles.item}>
          <StatusPill status={s} />
          <span>{statusMeaning(s, meta)}</span>
        </li>
      ))}
    </ul>
  );
}
