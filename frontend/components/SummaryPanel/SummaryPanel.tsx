// Summary "Right now" panel: lead text, alarm facts, Leaning most, buttons and the note
// (TRD 11 UX-070..UX-077, §4.5.2.1, UX-312; TRD 04 FE-210).
import Link from "next/link";
import type { ReactNode } from "react";
import { formatLocalDate, formatOpenDays } from "@/lib/format";
import { toDisplayStatus } from "@/lib/status";
import type { ChangeAlarm, Meta, ResidentDetail, UiStatus } from "@/lib/types";
import {
  RIGHT_NOW,
  SUMMARY_BUTTON,
  SUMMARY_FACT,
  chartSectionHref,
  leadChangedAbove,
  leadChangedBelow,
  leadLearning,
  leadNeedsAttention,
  leadUsualNotScored,
  leadUsualScored,
  restartFacts,
  summaryNote,
  summaryRestartSentence,
  whatsHappening,
} from "@/lib/wording";
import { LeaningMost } from "../LeaningMost/LeaningMost";
import styles from "./SummaryPanel.module.css";

export interface SummaryPanelProps {
  resident: ResidentDetail;
  /** The resident's non-closed change alarm of the current epoch. */
  alarm: ChangeAlarm | null;
  meta: Meta;
  /** Whether the current epoch has scored check-ins (Usual lead variant). */
  scored?: boolean;
  /** Shown instead of the alarm facts while the alarm loads or fails (UX-202). */
  alarmState?: ReactNode;
}

/** The lead paragraph for the resident's situation (§4.5.2.1). */
export function summaryLead(
  resident: ResidentDetail,
  status: UiStatus,
  meta: Meta,
  scored: boolean,
): string {
  const code = resident.resident_code;
  const date = (d: string) => formatLocalDate(d, meta.as_of, meta.facility_tz);
  let lead: string;
  switch (status) {
    case "changed": {
      const since = date(resident.alarm_since ?? resident.explanation.alarm_crossed_on ?? "");
      const above =
        resident.current_tally !== null
          ? resident.current_tally >= meta.cusum_h
          : resident.explanation.still_above_line;
      lead = above ? leadChangedAbove(code, since) : leadChangedBelow(code, since);
      break;
    }
    case "needs_attention":
      lead = leadNeedsAttention(whatsHappening(resident, status, meta));
      break;
    case "learning":
      lead = leadLearning(code, resident.baseline.n_usable, resident.baseline.n_required);
      break;
    case "usual":
      lead = scored ? leadUsualScored(code) : leadUsualNotScored(code);
      break;
  }
  const restart = restartFacts(resident);
  return restart ? lead + summaryRestartSentence(code, restart, meta) : lead;
}

export function SummaryPanel({
  resident,
  alarm,
  meta,
  scored = true,
  alarmState,
}: SummaryPanelProps) {
  const code = resident.resident_code;
  const status = toDisplayStatus(resident.status, resident.needs_attention);
  const date = (d: string) => formatLocalDate(d, meta.as_of, meta.facility_tz);
  return (
    <section className={`panel pad ${styles.card} ${styles[status]}`} aria-labelledby="right-now">
      <h2 id="right-now" className={styles.heading}>
        {RIGHT_NOW}
      </h2>
      <p className={styles.lead}>{summaryLead(resident, status, meta, scored)}</p>
      {status === "changed" &&
        (alarm ? (
          <>
            <div className={styles.facts}>
              <div>
                <b>{date(alarm.local_date)}</b>
                <span>{SUMMARY_FACT.alarmStarted}</span>
              </div>
              <div>
                <b>{formatOpenDays(alarm.open_days)}</b>
                <span>{SUMMARY_FACT.open}</span>
              </div>
              <div>
                <b>
                  {resident.alarm_reviewed === false
                    ? SUMMARY_FACT.notReviewed
                    : SUMMARY_FACT.reviewed}
                </b>
                <span>{SUMMARY_FACT.reviewStatus}</span>
              </div>
            </div>
            <LeaningMost featureKeys={alarm.leaning_most} />
          </>
        ) : (
          <div className={styles.facts}>{alarmState}</div>
        ))}
      {status === "changed" && (
        <div className={styles.actions}>
          <Link className="btn" href={chartSectionHref(code, "review")}>
            {SUMMARY_BUTTON.review}
          </Link>
          <Link className="btn btn-secondary" href={chartSectionHref(code, "trends")}>
            {SUMMARY_BUTTON.trends}
          </Link>
        </div>
      )}
      {status === "needs_attention" && (
        <div className={styles.actions}>
          <Link className="btn btn-secondary" href={chartSectionHref(code, "log")}>
            {SUMMARY_BUTTON.log}
          </Link>
          <Link className="btn btn-secondary" href={chartSectionHref(code, "device")}>
            {SUMMARY_BUTTON.device}
          </Link>
        </div>
      )}
      <p className={styles.note}>{summaryNote(code, status === "learning")}</p>
    </section>
  );
}
