// Baseline section panel: text, native <progress> meter, caption and explanation
// (TRD 11 UX-420..UX-423, §4.5.7.1, UX-065, UX-066).
import type { CheckinEvent, Meta, ResidentDetail } from "@/lib/types";
import {
  baselineExplanation,
  baselineHeading,
  baselineMeterText,
  baselineText,
  restartFacts,
} from "@/lib/wording";
import styles from "./BaselinePanel.module.css";

export interface BaselinePanelProps {
  resident: ResidentDetail;
  /** The current epoch's `baseline_restarted` event (cause and values); null in epoch 1. */
  restart: CheckinEvent | null;
  meta: Meta;
  /** Local date of the first scored check-in of the current epoch (the watching_started event). */
  firstScoredDate?: string | null;
}

export function BaselinePanel({
  resident,
  restart,
  meta,
  firstScoredDate = null,
}: BaselinePanelProps) {
  const code = resident.resident_code;
  const b = resident.baseline;
  const meter = baselineMeterText(b.n_usable, b.n_required);
  return (
    <section className="panel pad stack" aria-labelledby="baseline-heading">
      <h2 id="baseline-heading">{baselineHeading(code)}</h2>
      <p>{baselineText(resident, restartFacts(resident, restart), firstScoredDate, meta)}</p>
      <div>
        <progress
          className={styles.meter}
          max={b.n_required}
          value={b.n_usable}
          aria-label={meter}
        />
        <p className={styles.caption}>{meter}</p>
      </div>
      <p className={styles.caption}>{baselineExplanation(meta.baseline_n)}</p>
    </section>
  );
}
