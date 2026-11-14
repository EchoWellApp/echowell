"use client";
// Study team page `/study` (TRD 04 §4.3, FE-026, FE-037, FE-195; TRD 11 §4.18, §4.4, UX-017).
// The role check comes before any data hook, so a clinician triggers no Study team request.
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState, type ReactNode } from "react";
import { AccessDenied } from "@/components/AccessDenied/AccessDenied";
import {
  AlarmTimingTable,
  buildAlarmTimingRows,
} from "@/components/AlarmTimingTable/AlarmTimingTable";
import { DailyCheckinsChart } from "@/components/DailyCheckinsChart/DailyCheckinsChart";
import { DataProblemsList } from "@/components/DataProblemsList/DataProblemsList";
import { DevicesSection } from "@/components/DevicesSection/DevicesSection";
import { KpiTiles } from "@/components/KpiTiles/KpiTiles";
import { LossFunnel } from "@/components/LossFunnel/LossFunnel";
import { ReviewOutcomesTable } from "@/components/ReviewOutcomesTable/ReviewOutcomesTable";
import { QueryState, SectionState } from "@/components/SectionState/SectionState";
import { UsableByResidentChart } from "@/components/UsableByResidentChart/UsableByResidentChart";
import { useAuth } from "@/lib/AuthProvider";
import { localDateOf, windowOf } from "@/lib/format";
import { useDocumentTitle, useUiConfig } from "@/lib/hooks";
import { REFRESH_MS } from "@/lib/queryClient";
import { queryKeys } from "@/lib/queryKeys";
import { canSeeStudyTeam } from "@/lib/roles";
import type { AnalyticsResponse, Meta } from "@/lib/types";
import {
  STUDY_COUNTS_ONLY,
  STUDY_DEVICES_HEADING,
  STUDY_DEVICES_PANEL,
  STUDY_DOWNLOADING,
  STUDY_DOWNLOADS_HEADING,
  STUDY_DOWNLOAD_BASELINES,
  STUDY_DOWNLOAD_SCORES,
  STUDY_H1,
  STUDY_NO_RUN,
  STUDY_PAGE,
  STUDY_PANEL_ANALYTICS,
  STUDY_PROBLEMS_HEADING,
  loadingText,
  studyCsvName,
  studyDownloadFailed,
  studyPeriodLine,
} from "@/lib/wording";
import * as api from "@/services/api";
import { ApiError } from "@/services/api";
import styles from "./page.module.css";

export default function StudyTeamPage() {
  useDocumentTitle(STUDY_PAGE);
  const { status, user } = useAuth();
  if (status !== "signed-in")
    return <SectionState state="loading" message={loadingText(STUDY_PAGE)} />;
  if (!canSeeStudyTeam(user?.role)) return <AccessDenied />;
  return <StudyTeamContent />;
}

/** A panel frame with its heading, for loading and error states of a panel-owning component. */
function Frame({ id, heading, children }: { id?: string; heading: string; children: ReactNode }) {
  const hid = `${id ?? heading.replace(/\W+/g, "-").toLowerCase()}-heading`;
  return (
    <section id={id} className="panel pad stack" aria-labelledby={hid}>
      <h2 id={hid} tabIndex={id ? -1 : undefined}>
        {heading}
      </h2>
      {children}
    </section>
  );
}

/** FE-026: `/study#devices` scrolls to the Devices section and focuses its heading. */
function useDevicesHash(ready: boolean) {
  useEffect(() => {
    const go = () => {
      if (window.location.hash !== "#devices") return;
      document.getElementById("devices")?.scrollIntoView?.({ block: "start" });
      document.getElementById("devices-heading")?.focus();
    };
    if (ready) go();
    window.addEventListener("hashchange", go);
    return () => window.removeEventListener("hashchange", go);
  }, [ready]);
}

function StudyTeamContent() {
  const ui = useUiConfig();
  const analytics = useQuery({
    queryKey: queryKeys.analytics(),
    queryFn: () => api.getAnalytics(),
  });
  const problems = useQuery({
    queryKey: queryKeys.dataAlerts("open"),
    queryFn: () => api.getDataAlerts({ status: "open" }),
  });
  const devices = useQuery({
    queryKey: queryKeys.devices(),
    queryFn: () => api.getDevices(),
    refetchInterval: REFRESH_MS,
  });
  useDevicesHash(!analytics.isPending && !devices.isPending);

  const meta: Meta | undefined = analytics.data?.meta ?? ui.data?.meta;
  const period =
    analytics.data?.period ?? (meta?.as_of ? windowOf(meta.as_of, meta.facility_tz) : null);

  return (
    <div className="stack">
      <header className={`panel ${styles.head}`}>
        <h1 className={styles.h1}>{STUDY_H1}</h1>
        <p className="small muted">{STUDY_COUNTS_ONLY}</p>
        {meta && period && (
          <p className="small muted" data-testid="period-line">
            {studyPeriodLine(meta, period)}
          </p>
        )}
      </header>

      {analytics.isPending ? (
        <>
          <KpiTiles kpis={null} />
          <QueryState
            panel={STUDY_PANEL_ANALYTICS}
            isPending
            error={null}
            refetch={analytics.refetch}
          />
        </>
      ) : analytics.error ? (
        <div className="panel pad">
          <QueryState
            panel={STUDY_PANEL_ANALYTICS}
            isPending={false}
            error={analytics.error}
            refetch={analytics.refetch}
          />
        </div>
      ) : analytics.data.pipeline_run === null ? (
        <div className="panel pad">
          <SectionState state="empty" message={STUDY_NO_RUN} />
        </div>
      ) : (
        <KpiTiles kpis={analytics.data.kpis} />
      )}

      {problems.data ? (
        <DataProblemsList alerts={problems.data.items} meta={problems.data.meta} />
      ) : (
        <Frame heading={STUDY_PROBLEMS_HEADING}>
          <QueryState
            panel={STUDY_PROBLEMS_HEADING.toLowerCase()}
            isPending={!problems.error}
            error={problems.error}
            refetch={problems.refetch}
          />
        </Frame>
      )}

      {analytics.data && analytics.data.pipeline_run !== null && (
        <AnalyticsPanels data={analytics.data} />
      )}

      {devices.data ? (
        <DevicesSection devices={devices.data.items} meta={devices.data.meta} />
      ) : (
        <Frame id="devices" heading={STUDY_DEVICES_HEADING}>
          <QueryState
            panel={STUDY_DEVICES_PANEL}
            isPending={!devices.error}
            error={devices.error}
            refetch={devices.refetch}
          />
        </Frame>
      )}

      <Downloads meta={meta} />
    </div>
  );
}

function AnalyticsPanels({ data }: { data: AnalyticsResponse }) {
  const testProfile = data.meta.pipeline_profile === "test_v0_1";
  return (
    <>
      <DailyCheckinsChart series={data.daily_series} meta={data.meta} />
      <div className={styles.cols2}>
        <LossFunnel funnel={data.funnel} />
        <UsableByResidentChart rows={data.by_resident} />
      </div>
      {testProfile
        ? data.alarm_timing && <AlarmTimingTable rows={buildAlarmTimingRows(data.alarm_timing)} />
        : data.review_outcomes && <ReviewOutcomesTable outcomes={data.review_outcomes} />}
    </>
  );
}

type CsvKind = "scores" | "baselines";

/** UX-377: CSV export → Blob → object URL → `<a download>` click. */
function Downloads({ meta }: { meta: Meta | undefined }) {
  const [busy, setBusy] = useState<CsvKind | null>(null);
  const [error, setError] = useState<{ message: string; requestId?: string } | null>(null);
  const label = (k: CsvKind) => (k === "scores" ? STUDY_DOWNLOAD_SCORES : STUDY_DOWNLOAD_BASELINES);

  async function download(kind: CsvKind) {
    setBusy(kind);
    setError(null);
    try {
      const blob =
        kind === "scores" ? await api.downloadScoresCsv() : await api.downloadBaselinesCsv();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = studyCsvName(
        kind,
        meta?.as_of ? localDateOf(meta.as_of, meta.facility_tz) : "export",
      );
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError({
        message: studyDownloadFailed(label(kind)),
        requestId: e instanceof ApiError ? (e.requestId ?? undefined) : undefined,
      });
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="panel pad stack" aria-labelledby="downloads-heading">
      <h2 id="downloads-heading">{STUDY_DOWNLOADS_HEADING}</h2>
      <div className={styles.buttons}>
        {(["scores", "baselines"] as const).map((k) => (
          <button
            key={k}
            type="button"
            className="btn btn-secondary"
            disabled={busy !== null}
            onClick={() => void download(k)}
          >
            {busy === k ? STUDY_DOWNLOADING : label(k)}
          </button>
        ))}
      </div>
      {error && <SectionState state="error" message={error.message} requestId={error.requestId} />}
    </section>
  );
}
