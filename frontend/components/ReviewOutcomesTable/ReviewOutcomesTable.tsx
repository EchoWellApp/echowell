// "Alarms and review outcomes", production profile (TRD 11 UX-375): replaces the timing table.
import type { ReviewOutcomes } from "@/lib/types";
import {
  STUDY_OUTCOMES,
  STUDY_OUTCOMES_COUNT,
  STUDY_OUTCOMES_FIRST_COLUMN,
  STUDY_OUTCOMES_HEADING,
} from "@/lib/wording";
import styles from "./ReviewOutcomesTable.module.css";

export interface ReviewOutcomesTableProps {
  outcomes: ReviewOutcomes;
}

export function ReviewOutcomesTable({ outcomes: o }: ReviewOutcomesTableProps) {
  const rows: [string, number][] = [
    [STUDY_OUTCOMES.raised, o.alarms_raised],
    [STUDY_OUTCOMES.reviewed, o.reviewed],
    [STUDY_OUTCOMES.no_concern, o.by_outcome.no_concern],
    [STUDY_OUTCOMES.known_cause, o.by_outcome.known_cause],
    [STUDY_OUTCOMES.referred, o.by_outcome.referred],
    [STUDY_OUTCOMES.data_problem, o.by_outcome.data_problem],
  ];
  return (
    <section className="panel pad stack" aria-labelledby="outcomes-heading">
      <h2 id="outcomes-heading">{STUDY_OUTCOMES_HEADING}</h2>
      <table className={styles.table}>
        <thead>
          <tr>
            <th scope="col">
              <span className="visually-hidden">{STUDY_OUTCOMES_FIRST_COLUMN}</span>
            </th>
            <th scope="col" className={styles.count}>
              {STUDY_OUTCOMES_COUNT}
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([label, n]) => (
            <tr key={label}>
              <th scope="row">{label}</th>
              <td className={styles.count}>{n}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
