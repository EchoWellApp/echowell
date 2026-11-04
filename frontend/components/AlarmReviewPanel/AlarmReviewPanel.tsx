"use client";
// "Review alert: changed since <Mon D>" panel of the chart "Review and notes" section (TRD 11
// UX-310, UX-313..UX-322; TRD 04 FE-086, FE-134, FE-135, FE-209).
import { useQueryClient } from "@tanstack/react-query";
import { useId, type ReactNode } from "react";
import { AlertReviewForm, ReminderLine } from "@/components/AlertReviewForm/AlertReviewForm";
import { ReviewHistory } from "@/components/ReviewHistory/ReviewHistory";
import { formatLocalDate } from "@/lib/format";
import { queryKeys } from "@/lib/queryKeys";
import type { AlertReview, ChangeAlarm, Meta, UiConfig } from "@/lib/types";
import {
  PREVIOUS_REVIEWS,
  REVIEW_OPEN_QUESTIONS,
  REVIEW_READ_ONLY,
  reviewHeading,
} from "@/lib/wording";
import styles from "./AlarmReviewPanel.module.css";

export interface AlarmReviewPanelProps {
  alarm: ChangeAlarm;
  reviews: AlertReview[];
  uiConfig: UiConfig;
  canReview: boolean;
  meta: Meta;
  /** Shown under "Previous reviews" instead of the list while it loads or fails (FE-140). */
  historyState?: ReactNode;
}

export function AlarmReviewPanel({
  alarm,
  reviews,
  uiConfig,
  canReview,
  meta,
  historyState,
}: AlarmReviewPanelProps) {
  const headingId = useId();
  const queryClient = useQueryClient();
  const tz = meta.facility_tz;
  const code = alarm.resident_code;

  // FE-086: show the API state after a review or reminder; never change the alarm locally (FE-134).
  function onSaved() {
    void queryClient.invalidateQueries({ queryKey: queryKeys.alertsAll() });
    void queryClient.invalidateQueries({ queryKey: queryKeys.dataAlerts().slice(0, 1) });
    void queryClient.invalidateQueries({ queryKey: queryKeys.resident(code) });
    void queryClient.invalidateQueries({ queryKey: queryKeys.residents() });
    void queryClient.invalidateQueries({ queryKey: queryKeys.analytics() });
  }

  const snoozedUntil = alarm.snoozed_until;

  return (
    <section className="panel pad stack" aria-labelledby={headingId}>
      <h2 id={headingId}>{reviewHeading(formatLocalDate(alarm.local_date, meta.as_of, tz))}</h2>
      {canReview ? (
        <AlertReviewForm
          alertId={alarm.id}
          snoozeHours={uiConfig.alert_snooze_hours}
          explanations={uiConfig.review_explanations}
          snoozedUntil={snoozedUntil}
          onSaved={onSaved}
          tz={tz}
          asOf={meta.as_of}
        />
      ) : (
        <>
          <p className="muted">{REVIEW_READ_ONLY}</p>
          <ReminderLine until={snoozedUntil} tz={tz} asOf={meta.as_of} />
        </>
      )}
      {historyState ? (
        <div className="stack">
          <h3>{PREVIOUS_REVIEWS}</h3>
          {historyState}
        </div>
      ) : (
        <ReviewHistory
          reviews={reviews}
          tz={tz}
          asOf={meta.as_of}
          explanations={uiConfig.review_explanations}
        />
      )}
      <p className={styles.questions}>{REVIEW_OPEN_QUESTIONS}</p>
    </section>
  );
}
