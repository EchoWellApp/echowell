"use client";
// Resident chart shell shared by the six sections: back link, banner, section navigation and the
// two-column grid (TRD 11 §4.5 intro, UX-060..UX-063, UX-410..UX-412, UX-206; TRD 04 FE-025,
// FE-030, FE-032, FE-087, FE-142, FE-144, FE-206, FE-210).
import { useParams, usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { BackLink } from "@/components/BackLink/BackLink";
import { ChartBanner } from "@/components/ChartBanner/ChartBanner";
import { ChartSectionNav } from "@/components/ChartSectionNav/ChartSectionNav";
import { QueryState } from "@/components/SectionState/SectionState";
import { formatAsOf } from "@/lib/format";
import { useDocumentTitle } from "@/lib/hooks";
import { CHART_PANEL, chartPageName, couldNotRefresh, residentNotFound } from "@/lib/wording";
import { ApiError } from "@/services/api";
import styles from "./layout.module.css";
import { codeParam, isValidResidentCode, sectionFromPath, useResident } from "./section";

export default function ResidentChartLayout({ children }: { children: ReactNode }) {
  const code = codeParam(useParams());
  const section = sectionFromPath(usePathname());
  const valid = isValidResidentCode(code);
  useDocumentTitle(chartPageName(code, section));
  const resident = useResident(code);
  const notFound = !valid || (resident.error instanceof ApiError && resident.error.status === 404);

  if (notFound) {
    return (
      <div className="stack">
        <div>
          <BackLink />
        </div>
        <h1 className={styles.notFound}>{residentNotFound(code)}</h1>
      </div>
    );
  }

  const data = resident.data;
  return (
    <div>
      <BackLink />
      {data && resident.isRefetchError && data.meta.as_of && (
        <p role="status" className={styles.notice}>
          {couldNotRefresh(formatAsOf(data.meta.as_of, data.meta.facility_tz))}
        </p>
      )}
      <ChartBanner resident={data ?? null} residentCode={code} />
      {!data && (
        <QueryState
          panel={CHART_PANEL.resident}
          isPending={false}
          error={resident.error}
          refetch={resident.refetch}
        />
      )}
      <div className={styles.chart}>
        <ChartSectionNav
          residentCode={code}
          current={section}
          unreviewedAlarm={data?.alarm_reviewed === false}
        />
        <div className="stack">{children}</div>
      </div>
    </div>
  );
}
