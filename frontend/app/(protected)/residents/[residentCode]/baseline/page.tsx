"use client";
// Resident chart, Baseline section (TRD 11 §4.5.7, UX-420..UX-423, UX-065, UX-066; TRD 04 §4.6.2
// Baseline reads `getResident` and `getCheckins`, FE-087).
import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { BaselinePanel } from "@/components/BaselinePanel/BaselinePanel";
import { QueryState } from "@/components/SectionState/SectionState";
import { useDocumentTitle } from "@/lib/hooks";
import { REFRESH_MS } from "@/lib/queryClient";
import { queryKeys } from "@/lib/queryKeys";
import { CHART_PANEL, baselineHeading, chartPageName } from "@/lib/wording";
import * as api from "@/services/api";
import { codeParam, epochRange, useResident } from "../section";

export default function ResidentBaselinePage() {
  const code = codeParam(useParams());
  useDocumentTitle(chartPageName(code, "baseline"));
  const resident = useResident(code);
  const r = resident.data;
  const range = r ? epochRange(r) : null;
  const checkins = useQuery({
    queryKey: [...queryKeys.checkins(code), range],
    queryFn: () => api.getCheckins(code, range ?? {}),
    refetchInterval: REFRESH_MS,
    enabled: range !== null,
  });

  const data = checkins.data;
  if (!r || !data) {
    return (
      <section className="panel pad stack" aria-labelledby="baseline-heading">
        <h2 id="baseline-heading">{baselineHeading(code)}</h2>
        <QueryState
          panel={CHART_PANEL.baseline}
          isPending={!r ? resident.isPending : checkins.isPending}
          error={!r ? resident.error : checkins.error}
          refetch={!r ? resident.refetch : checkins.refetch}
        />
      </section>
    );
  }
  const epoch = r.current_epoch?.epoch_number ?? null;
  const inEpoch = data.items.filter((e) => e.epoch_number === epoch);
  const restart = inEpoch.find((e) => e.event_type === "baseline_restarted") ?? null;
  const scored = inEpoch.find((e) => e.event_type === "watching_started");
  return (
    <BaselinePanel
      resident={r}
      restart={restart}
      meta={r.meta}
      firstScoredDate={scored?.local_date ?? null}
    />
  );
}
