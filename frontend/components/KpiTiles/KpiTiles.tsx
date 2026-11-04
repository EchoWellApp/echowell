// The four Study team tiles (TRD 11 UX-351..UX-355). Notes are composed in lib/wording/study.ts.
import { formatPercent } from "@/lib/format";
import type { AnalyticsKpis } from "@/lib/types";
import {
  STUDY_EMPTY_CELL,
  STUDY_KPI,
  studyAlarmsNote,
  studyBaselinesNote,
  studyBaselinesValue,
  studyOfExpected,
} from "@/lib/wording";
import styles from "./KpiTiles.module.css";

export interface KpiTilesProps {
  /** null while loading: the tiles show "—" (UX-200). */
  kpis: AnalyticsKpis | null;
}

export function KpiTiles({ kpis }: KpiTilesProps) {
  if (!kpis) {
    return (
      <ul className={styles.tiles} aria-label="Key counts" aria-busy="true">
        {Object.values(STUDY_KPI).map((label) => (
          <li key={label} className={styles.tile} data-testid="kpi-tile">
            <span className={styles.label}>{label}</span>
            <span className={styles.value}>{STUDY_EMPTY_CELL}</span>
          </li>
        ))}
      </ul>
    );
  }
  const { checkins_received: rec, used_for_scoring: used, baselines_formed: bl } = kpis;
  const tiles = [
    {
      label: STUDY_KPI.received,
      value: formatPercent(rec.count, rec.expected),
      note: studyOfExpected(rec.count, rec.expected),
    },
    {
      label: STUDY_KPI.used,
      value: formatPercent(used.count, used.expected),
      note: studyOfExpected(used.count, used.expected),
    },
    {
      label: STUDY_KPI.baselines,
      value: studyBaselinesValue(bl.formed, bl.residents),
      note: studyBaselinesNote(bl),
    },
    {
      label: STUDY_KPI.alarms,
      value: String(kpis.alarms_raised.count),
      note: studyAlarmsNote(kpis.alarms_raised),
    },
  ];
  return (
    <ul className={styles.tiles} aria-label="Key counts">
      {tiles.map((t) => (
        <li key={t.label} className={styles.tile} data-testid="kpi-tile">
          <span className={styles.label}>{t.label}</span>
          <span className={styles.value}>{t.value}</span>
          <span className={styles.note}>{t.note}</span>
        </li>
      ))}
    </ul>
  );
}
