"use client";
// Chart section "Review and notes": alarm review panel (Changed residents only) and "Staff notes"
// (TRD 11 §4.5.5, §4.17; TRD 04 §4.9, FE-087, FE-209). The banner, section nav and the resident
// not-found state come from the chart layout (FE-206).
import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { AlarmReviewPanel } from "@/components/AlarmReviewPanel/AlarmReviewPanel";
import { QueryState } from "@/components/SectionState/SectionState";
import { StaffNotes } from "@/components/StaffNotes/StaffNotes";
import { useAuth } from "@/lib/AuthProvider";
import { useDocumentTitle, useUiConfig } from "@/lib/hooks";
import { REFRESH_MS } from "@/lib/queryClient";
import { queryKeys } from "@/lib/queryKeys";
import { canReviewAlarms, canWriteNotes } from "@/lib/roles";
import { toDisplayStatus } from "@/lib/status";
import type { ChangeAlarm, ResidentDetail } from "@/lib/types";
import { REVIEW_PANEL_NAME, REVIEWS_PANEL_NAME, REVIEW_SECTION } from "@/lib/wording";
import * as api from "@/services/api";
import { ApiError } from "@/services/api";
import { codeParam, isValidResidentCode } from "../section";

/** The resident's non-closed alert of the current epoch (FE-209). */
function currentAlarm(resident: ResidentDetail, alarms: ChangeAlarm[]): ChangeAlarm | null {
  const byId = resident.open_alert_id
    ? alarms.find((a) => a.id === resident.open_alert_id)
    : undefined;
  if (byId) return byId;
  const epoch = resident.current_epoch?.epoch_number;
  return alarms.find((a) => a.status !== "closed" && a.epoch_number === epoch) ?? null;
}

export default function ReviewAndNotesPage() {
  const code = codeParam(useParams());
  const valid = isValidResidentCode(code);
  useDocumentTitle(`${code} · ${REVIEW_SECTION}`);
  const { user } = useAuth();
  const role = user?.role;

  const resident = useQuery({
    queryKey: queryKeys.resident(code),
    queryFn: () => api.getResident(code),
    refetchInterval: REFRESH_MS,
    enabled: valid,
  });
  const alerts = useQuery({
    queryKey: queryKeys.alerts({ residentCode: code }),
    queryFn: () => api.getAlerts({ residentCode: code }),
    refetchInterval: REFRESH_MS,
    enabled: valid,
  });
  const ui = useUiConfig(valid);
  const changed =
    !!resident.data &&
    toDisplayStatus(resident.data.status, resident.data.needs_attention) === "changed";
  const alarm =
    changed && resident.data && alerts.data ? currentAlarm(resident.data, alerts.data.items) : null;
  const reviews = useQuery({
    queryKey: queryKeys.alertReviews(alarm?.id ?? ""),
    queryFn: () => api.getAlertReviews(alarm?.id ?? ""),
    enabled: !!alarm,
  });

  if (!valid) return null;
  // The chart layout shows "Resident <code> was not found." (FE-142).
  if (resident.error instanceof ApiError && resident.error.status === 404) return null;

  let reviewPanel: JSX.Element | null = null;
  if (resident.isPending || resident.error) {
    reviewPanel = null;
  } else if (changed) {
    const failed = alerts.error ?? ui.error;
    if (alarm && ui.data && alerts.data) {
      const meta = alerts.data.meta;
      reviewPanel = (
        <AlarmReviewPanel
          alarm={alarm}
          reviews={reviews.data?.items ?? []}
          uiConfig={ui.data}
          canReview={canReviewAlarms(role)}
          meta={meta}
          historyState={
            reviews.data ? undefined : (
              <QueryState
                panel={REVIEWS_PANEL_NAME}
                isPending={reviews.isPending}
                error={reviews.error}
                refetch={reviews.refetch}
              />
            )
          }
        />
      );
    } else if (failed || alerts.isPending || ui.isPending) {
      reviewPanel = (
        <section className="panel pad stack" aria-label={REVIEW_PANEL_NAME}>
          <QueryState
            panel={REVIEW_PANEL_NAME}
            isPending={alerts.isPending || ui.isPending}
            error={failed}
            refetch={() => {
              if (alerts.error) void alerts.refetch();
              if (ui.error) void ui.refetch();
            }}
          />
        </section>
      );
    }
  }

  return (
    <div className="stack">
      {resident.error && !resident.data && (
        <section className="panel pad stack" aria-label={REVIEW_PANEL_NAME}>
          <QueryState
            panel={REVIEW_PANEL_NAME}
            isPending={false}
            error={resident.error}
            refetch={resident.refetch}
          />
        </section>
      )}
      {reviewPanel}
      <StaffNotes
        residentCode={code}
        openAlertId={resident.data?.open_alert_id ?? null}
        canWrite={canWriteNotes(role)}
      />
    </div>
  );
}
