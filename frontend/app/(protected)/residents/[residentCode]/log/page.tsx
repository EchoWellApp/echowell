"use client";
// Resident chart, Check-in log section: counts and events with "Show earlier entries"
// (TRD 11 §4.5.6, UX-140..UX-150; TRD 04 §4.6.2 Check-in log reads, FE-087, FE-101).
import { useInfiniteQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { CheckinCounts } from "@/components/CheckinCounts/CheckinCounts";
import { CheckinLog } from "@/components/CheckinLog/CheckinLog";
import { QueryState } from "@/components/SectionState/SectionState";
import { useDocumentTitle } from "@/lib/hooks";
import { REFRESH_MS } from "@/lib/queryClient";
import { queryKeys } from "@/lib/queryKeys";
import { CHART_PANEL, chartPageName } from "@/lib/wording";
import * as api from "@/services/api";
import { codeParam, logRange, useResident } from "../section";

export default function ResidentLogPage() {
  const code = codeParam(useParams());
  useDocumentTitle(chartPageName(code, "log"));
  const resident = useResident(code);
  const r = resident.data;
  const asOfDate = r?.window.to ?? "";
  const enrolled = r?.enrolled_on ?? "";
  const log = useInfiniteQuery({
    queryKey: [...queryKeys.checkins(code), "log", asOfDate],
    queryFn: ({ pageParam }) => api.getCheckins(code, logRange(asOfDate, pageParam)),
    initialPageParam: 0,
    // Earlier events can exist only on or after the enrolment date.
    getNextPageParam: (_last, _all, page) =>
      logRange(asOfDate, page).from > enrolled ? page + 1 : undefined,
    refetchInterval: REFRESH_MS,
    enabled: r !== undefined,
  });

  const events = log.data?.pages.flatMap((p) => p.items) ?? [];
  const firstState = !log.data ? (
    <QueryState
      panel={CHART_PANEL.events}
      isPending={!r ? resident.isPending : log.isPending}
      error={!r ? resident.error : log.error}
      refetch={!r ? resident.refetch : log.refetch}
    />
  ) : undefined;
  const earlierState =
    log.data && log.isFetchNextPageError ? (
      <QueryState
        panel={CHART_PANEL.earlier}
        isPending={false}
        error={log.error}
        refetch={() => log.fetchNextPage()}
      />
    ) : undefined;
  return (
    <>
      {r || !resident.error ? (
        <CheckinCounts counts={r?.last_30_days ?? null} />
      ) : (
        <section className="panel pad">
          <QueryState
            panel={CHART_PANEL.counts}
            isPending={false}
            error={resident.error}
            refetch={resident.refetch}
          />
        </section>
      )}
      <CheckinLog
        events={events}
        h={r?.meta.cusum_h ?? 0}
        tz={r?.meta.facility_tz ?? "UTC"}
        asOf={r?.meta.as_of ?? null}
        baselineN={r?.meta.baseline_n ?? 0}
        residentCode={code}
        currentDeviceCode={r?.device.device_code ?? null}
        hasEarlier={log.hasNextPage}
        onShowEarlier={() => void log.fetchNextPage()}
        loadingEarlier={log.isFetchingNextPage}
        earlierState={earlierState}
        state={firstState}
      />
    </>
  );
}
