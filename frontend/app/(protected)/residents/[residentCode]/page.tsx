"use client";
// Resident chart, Summary section: "Right now" and "More detail" (TRD 11 §4.5.2, UX-070..UX-078,
// UX-312; TRD 04 §4.6.2 Summary reads, FE-087).
import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { MoreDetailTiles } from "@/components/MoreDetailTiles/MoreDetailTiles";
import { QueryState } from "@/components/SectionState/SectionState";
import { SummaryPanel } from "@/components/SummaryPanel/SummaryPanel";
import { useDocumentTitle } from "@/lib/hooks";
import { REFRESH_MS } from "@/lib/queryClient";
import { queryKeys } from "@/lib/queryKeys";
import { CHART_PANEL, RIGHT_NOW, chartPageName } from "@/lib/wording";
import * as api from "@/services/api";
import {
  codeParam,
  hasScoredSessions,
  isValidResidentCode,
  latestTally,
  useResident,
} from "./section";

export default function ResidentSummaryPage() {
  const code = codeParam(useParams());
  const enabled = isValidResidentCode(code);
  useDocumentTitle(chartPageName(code, "summary"));
  const resident = useResident(code);
  const alerts = useQuery({
    queryKey: queryKeys.alerts({ residentCode: code }),
    queryFn: () => api.getAlerts({ residentCode: code }),
    refetchInterval: REFRESH_MS,
    enabled,
  });
  const scores = useQuery({
    queryKey: queryKeys.scores(code),
    queryFn: () => api.getScores({ residentCode: code }),
    refetchInterval: REFRESH_MS,
    enabled,
  });
  const devices = useQuery({
    queryKey: queryKeys.devices(),
    queryFn: api.getDevices,
    refetchInterval: REFRESH_MS,
    enabled,
  });

  const r = resident.data;
  if (!r) {
    return (
      <section className="panel pad stack" aria-labelledby="right-now">
        <h2 id="right-now">{RIGHT_NOW}</h2>
        <QueryState
          panel={CHART_PANEL.summary}
          isPending={resident.isPending}
          error={resident.error}
          refetch={resident.refetch}
        />
      </section>
    );
  }

  const epoch = r.current_epoch?.epoch_number;
  const alarm =
    alerts.data?.items.find((a) => a.status !== "closed" && a.epoch_number === epoch) ??
    alerts.data?.items.find((a) => a.status !== "closed") ??
    null;
  const device = devices.data?.items.find((d) => d.device_code === r.device.device_code) ?? null;
  return (
    <>
      <SummaryPanel
        resident={r}
        alarm={alarm}
        meta={r.meta}
        scored={hasScoredSessions(r, scores.data)}
        alarmState={
          <QueryState
            panel={CHART_PANEL.alarm}
            isPending={alerts.isPending}
            error={alerts.error}
            refetch={alerts.refetch}
          />
        }
      />
      <MoreDetailTiles
        resident={r}
        latestTally={scores.data ? latestTally(r, scores.data) : scores.error ? null : undefined}
        device={device}
        meta={r.meta}
      />
    </>
  );
}
