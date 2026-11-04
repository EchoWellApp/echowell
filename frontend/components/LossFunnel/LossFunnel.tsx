// "Where check-ins are lost" (TRD 11 UX-362..UX-366): four meters scaled to Expected.
import type { Funnel } from "@/lib/types";
import {
  STUDY_FUNNEL,
  STUDY_FUNNEL_HEADING,
  studyExpectedNote,
  studyHeldBackNote,
  studyPassedNote,
  studyReceivedNote,
} from "@/lib/wording";
import styles from "./LossFunnel.module.css";

export interface LossFunnelProps {
  funnel: Funnel;
}

/** Filled width in percent of Expected, one decimal (93.7, 89.7, 89). */
export const meterWidth = (value: number, expected: number) =>
  expected > 0 ? Number(((value / expected) * 100).toFixed(1)) : 0;

export function LossFunnel({ funnel: f }: LossFunnelProps) {
  const rows = [
    {
      label: STUDY_FUNNEL.expected,
      value: f.expected,
      note: studyExpectedNote(f.residents, f.days, f.expected === f.residents * f.days),
    },
    {
      label: STUDY_FUNNEL.received,
      value: f.received,
      note: studyReceivedNote(f.missed, f.duplicates_removed),
    },
    {
      label: STUDY_FUNNEL.passed,
      value: f.passed_quality,
      note: studyPassedNote(f.set_aside, f.set_aside_reasons, f.set_aside_multi_reason),
    },
    { label: STUDY_FUNNEL.used, value: f.used, note: studyHeldBackNote(f.quarantined) },
  ];
  return (
    <section className="panel pad stack" aria-labelledby="funnel-heading">
      <h2 id="funnel-heading">{STUDY_FUNNEL_HEADING}</h2>
      <ul className={styles.list}>
        {rows.map((r) => (
          <li key={r.label} data-testid="funnel-row">
            <div className={styles.row}>
              <span>{r.label}</span>
              <span className={styles.meter} aria-hidden="true">
                <i style={{ width: `${meterWidth(r.value, f.expected)}%` }} />
              </span>
              <b className={styles.value}>{r.value}</b>
            </div>
            <p className={styles.note}>{r.note}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
