// "Previous reviews" of a change alarm, newest first (TRD 11 UX-320).
import { formatDateTimeShort } from "@/lib/format";
import type { AlertReview, ReviewExplanation } from "@/lib/types";
import {
  NOT_REVIEWED_YET,
  PREVIOUS_REVIEWS,
  REVIEW_EXPLANATION_LABEL,
  REVIEW_OUTCOME_LABEL,
  possibleExplanations,
  reviewLine,
} from "@/lib/wording";
import styles from "./ReviewHistory.module.css";

export interface ReviewHistoryProps {
  reviews: AlertReview[];
  tz: string;
  /** As-of instant: the year is added to dates of another year (UX-003). */
  asOf?: string | null;
  /** Configured explanation labels (GET /config/ui); unknown codes fall back to the wording list. */
  explanations?: ReviewExplanation[];
}

export function explanationLabel(code: string, configured: ReviewExplanation[] = []): string {
  return configured.find((e) => e.code === code)?.label ?? REVIEW_EXPLANATION_LABEL[code] ?? code;
}

export function ReviewHistory({ reviews, tz, asOf = null, explanations = [] }: ReviewHistoryProps) {
  const sorted = [...reviews].sort((a, b) => b.created_at.localeCompare(a.created_at));
  return (
    <div className={styles.history}>
      <h3>{PREVIOUS_REVIEWS}</h3>
      {sorted.length === 0 ? (
        <p className="muted">{NOT_REVIEWED_YET}</p>
      ) : (
        <ul className={styles.list}>
          {sorted.map((r) => (
            <li key={r.id} className={styles.item}>
              <p className={styles.line}>
                {reviewLine(
                  formatDateTimeShort(r.created_at, tz, asOf),
                  r.reviewer.display_name,
                  REVIEW_OUTCOME_LABEL[r.outcome] ?? r.outcome,
                )}
              </p>
              {r.explanations.length > 0 && (
                <p>
                  {possibleExplanations(
                    r.explanations.map((c) => explanationLabel(c, explanations)),
                  )}
                </p>
              )}
              {r.note && <p className={styles.note}>{r.note}</p>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
