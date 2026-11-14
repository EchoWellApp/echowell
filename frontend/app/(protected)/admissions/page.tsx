"use client";
// New admissions, experimental (TRD 11 §4.7, UX-181..UX-195; TRD 04 §4.6.2, FEAT-073).
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { AdmissionsTable } from "@/components/AdmissionsTable/AdmissionsTable";
import { ExperimentalBanner } from "@/components/ExperimentalBanner/ExperimentalBanner";
import { FacilityRangeChart } from "@/components/FacilityRangeChart/FacilityRangeChart";
import { QueryState } from "@/components/SectionState/SectionState";
import { formatLocalDate, localDateOf } from "@/lib/format";
import { useDocumentTitle } from "@/lib/hooks";
import { queryKeys } from "@/lib/queryKeys";
import {
  ADMISSIONS_COMPARISON_PANEL,
  ADMISSIONS_INTRO,
  ADMISSIONS_PANEL,
  ADMISSIONS_SELECT_PROMPT,
  ADMISSIONS_TITLE,
  admissionsComparisonHeading,
  admissionsRangeMethod,
} from "@/lib/wording";
import * as api from "@/services/api";
import styles from "./page.module.css";

function RangeMethodLine() {
  const ranges = useQuery({
    queryKey: queryKeys.referenceRanges(),
    queryFn: api.getReferenceRanges,
  });
  const first = ranges.data?.items[0];
  if (!ranges.data || !first) return null;
  const tz = ranges.data.meta.facility_tz;
  const date = formatLocalDate(localDateOf(first.computed_at, tz), ranges.data.meta.as_of, tz);
  return (
    <p className="small muted">{admissionsRangeMethod(first.n_residents, date, first.method)}</p>
  );
}

function ComparisonPanel({ code }: { code: string }) {
  const comparison = useQuery({
    queryKey: queryKeys.admissionComparison(code),
    queryFn: () => api.getAdmissionComparison(code),
  });
  return (
    <section className="panel pad stack" aria-labelledby="comparison-heading">
      <h2 id="comparison-heading">{admissionsComparisonHeading(code)}</h2>
      <QueryState
        panel={ADMISSIONS_COMPARISON_PANEL}
        isPending={comparison.isPending}
        error={comparison.error}
        refetch={comparison.refetch}
      />
      {comparison.data && (
        <>
          <FacilityRangeChart
            comparison={comparison.data}
            residentCode={code}
            N={comparison.data.meta.baseline_n}
          />
          <RangeMethodLine />
        </>
      )}
    </section>
  );
}

export default function AdmissionsPage() {
  useDocumentTitle(ADMISSIONS_TITLE);
  const [selected, setSelected] = useState<string | null>(null);
  const admissions = useQuery({ queryKey: queryKeys.admissions(), queryFn: api.getAdmissions });
  const rows = admissions.data?.items ?? [];
  const current = rows.some((r) => r.resident_code === selected) ? selected : null;

  return (
    <div className="stack">
      <ExperimentalBanner />
      <section className="panel" aria-labelledby="admissions-heading">
        <div className={styles.head}>
          <h1 id="admissions-heading" className={styles.title}>
            {ADMISSIONS_TITLE}
          </h1>
        </div>
        <p className={`muted ${styles.intro}`}>{ADMISSIONS_INTRO}</p>
        <div className={styles.body}>
          <QueryState
            panel={ADMISSIONS_PANEL}
            isPending={admissions.isPending}
            error={admissions.error}
            refetch={admissions.refetch}
          />
          {admissions.data && (
            <AdmissionsTable
              rows={rows}
              meta={admissions.data.meta}
              selected={current}
              onSelect={setSelected}
            />
          )}
        </div>
      </section>
      {current ? (
        <ComparisonPanel code={current} />
      ) : (
        admissions.data && (
          <section className="panel pad" aria-live="polite">
            <p className="small muted">{ADMISSIONS_SELECT_PROMPT}</p>
          </section>
        )
      )}
    </div>
  );
}
