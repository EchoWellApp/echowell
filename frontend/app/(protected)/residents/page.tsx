"use client";
// Resident list `/residents` (TRD 11 §4.3, TRD 04 FE-076, FE-081..FE-084; FEAT-065).
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useEffect } from "react";
import { rememberShow } from "@/components/BackLink/BackLink";
import { FilterButtons } from "@/components/FilterButtons/FilterButtons";
import { ResidentsTable } from "@/components/ResidentsTable/ResidentsTable";
import { QueryState, SectionState } from "@/components/SectionState/SectionState";
import { StatusLegend } from "@/components/StatusLegend/StatusLegend";
import { formatAsOf } from "@/lib/format";
import { useDocumentTitle } from "@/lib/hooks";
import { REFRESH_MS } from "@/lib/queryClient";
import { queryKeys } from "@/lib/queryKeys";
import {
  LIST_EMPTY,
  LIST_FILTERS,
  LIST_HEADING,
  LIST_PAGE,
  LIST_PANEL,
  couldNotRefresh,
  listNote,
  showingOfTotal,
  type ListFilter,
} from "@/lib/wording";
import * as api from "@/services/api";
import styles from "./page.module.css";

/** `?show=` value, `all` when absent or invalid (UX-404, FE-082). */
function parseShow(value: string | null): ListFilter {
  return LIST_FILTERS.find((f) => f === value) ?? "all";
}

function ResidentList() {
  useDocumentTitle(LIST_PAGE);
  const router = useRouter();
  const pathname = usePathname() ?? "/residents";
  const searchParams = useSearchParams();
  const filter = parseShow(searchParams?.get("show") ?? null);
  // Keep the shown filter for the chart's back link (FE-025), also after a reload with ?show=.
  useEffect(() => rememberShow(filter), [filter]);

  const q = useQuery({
    queryKey: queryKeys.residents(),
    queryFn: api.getResidents,
    refetchInterval: REFRESH_MS,
    placeholderData: keepPreviousData,
  });
  const data = q.data;

  const onChange = useCallback(
    (v: ListFilter) => {
      rememberShow(v);
      const params = new URLSearchParams(searchParams?.toString() ?? "");
      params.set("show", v);
      router.replace(`${pathname}?${params.toString()}`, { scroll: false });
    },
    [router, pathname, searchParams],
  );

  return (
    <div className="stack">
      {data && q.isRefetchError && data.meta.as_of && (
        <p role="status" className={styles.stale}>
          {couldNotRefresh(formatAsOf(data.meta.as_of, data.meta.facility_tz))}
        </p>
      )}
      <section className="panel" aria-labelledby="residents-heading">
        <div className={styles.listhead}>
          <h1 id="residents-heading" className={styles.h1}>
            {LIST_HEADING}
          </h1>
          <FilterButtons
            summary={data?.summary}
            total={data?.total}
            value={filter}
            onChange={onChange}
          />
        </div>
        {data ? (
          <>
            {data.items.length === 0 ? (
              <div className="pad">
                <SectionState state="empty" message={LIST_EMPTY} />
              </div>
            ) : (
              <ResidentsTable
                rows={data.items}
                meta={data.meta}
                filter={filter}
                isFetching={q.isFetching}
              />
            )}
            {data.total > data.items.length && (
              <p className={styles.truncated}>{showingOfTotal(data.items.length, data.total)}</p>
            )}
            <StatusLegend meta={data.meta} />
          </>
        ) : (
          <div className="pad">
            <QueryState
              panel={LIST_PANEL}
              isPending={q.isPending}
              error={q.error}
              refetch={q.refetch}
            />
          </div>
        )}
      </section>
      <p className={styles.note}>{listNote()}</p>
    </div>
  );
}

export default function ResidentsPage() {
  return (
    <Suspense fallback={null}>
      <ResidentList />
    </Suspense>
  );
}
