"use client";
// Resident chart section "Voice trends": the Change score panel and the 7 measurements panel
// (TRD 11 §4.5.3, §4.5.4; TRD 04 §4.6.2, FE-087; FEAT-067). The chart layout renders the banner,
// the <h1> and the section navigation; this page renders the section content only.
import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { useId, useState } from "react";
import { ChangeScoreChart } from "@/components/ChangeScoreChart/ChangeScoreChart";
import { MeasurementCards } from "@/components/MeasurementCards/MeasurementCards";
import { QueryState } from "@/components/SectionState/SectionState";
import { useDocumentTitle } from "@/lib/hooks";
import { queryKeys } from "@/lib/queryKeys";
import {
  TRENDS_EPOCH_LABEL,
  TRENDS_MEASURES_HEADING,
  TRENDS_MEASURES_PANEL,
  TRENDS_NO_SCORED,
  TRENDS_SCORE_HEADING,
  TRENDS_SCORE_PANEL,
  trendsEpochOption,
  trendsForming,
  trendsPageTitle,
  trendsScoreIntro,
} from "@/lib/wording";
import * as api from "@/services/api";
import styles from "./page.module.css";

export default function VoiceTrendsPage() {
  const params = useParams<{ residentCode: string }>();
  const code = params?.residentCode ?? "";
  useDocumentTitle(trendsPageTitle(code));
  const selectId = useId();
  /** null = the current epoch (the API default). */
  const [epoch, setEpoch] = useState<number | null>(null);

  // Shared with the chart layout's query (same key), so this adds no request.
  const resident = useQuery({
    queryKey: queryKeys.resident(code),
    queryFn: () => api.getResident(code),
    enabled: code !== "",
  });
  const scores = useQuery({
    queryKey: queryKeys.scores(code, epoch),
    queryFn: () => api.getScores({ residentCode: code, epoch }),
    enabled: code !== "",
  });
  const features = useQuery({
    queryKey: queryKeys.features(code),
    queryFn: () => api.getFeatures(code),
    enabled: code !== "",
  });

  const detail = resident.data;
  const currentEpoch = detail?.current_epoch?.epoch_number ?? 1;
  const shownEpoch = epoch ?? currentEpoch;
  const forming = detail?.baseline.state === "forming";
  const h = scores.data?.meta.cusum_h ?? detail?.meta.cusum_h ?? 5;

  const scorePanel = () => {
    if (!scores.data || !detail) {
      return (
        <QueryState
          panel={TRENDS_SCORE_PANEL}
          isPending
          error={scores.error ?? resident.error}
          refetch={() => (scores.error ? scores.refetch() : resident.refetch())}
        />
      );
    }
    if (forming && epoch === null) {
      return (
        <p className={styles.forming}>
          {trendsForming(detail.baseline.n_usable, detail.baseline.n_required)}
        </p>
      );
    }
    const periods = scores.data.baseline_periods;
    const baselinePeriod =
      periods.find((b) => b.epoch_number === shownEpoch) ?? periods[periods.length - 1] ?? null;
    const points = scores.data.items;
    if (!baselinePeriod && points.length === 0) {
      return <p className={styles.forming}>{TRENDS_NO_SCORED}</p>;
    }
    const restartedOn =
      shownEpoch === currentEpoch && currentEpoch > 1
        ? (detail.current_epoch?.started_on ?? null)
        : null;
    return (
      <ChangeScoreChart
        points={points}
        baselinePeriod={baselinePeriod}
        h={h}
        residentCode={code}
        tz={scores.data.meta.facility_tz}
        restartedOn={restartedOn}
      />
    );
  };

  const featurePanel = () => {
    if (!features.data || !detail) {
      return (
        <section className="panel pad stack" aria-labelledby="measures-heading">
          <h2 id="measures-heading">{TRENDS_MEASURES_HEADING}</h2>
          <QueryState
            panel={TRENDS_MEASURES_PANEL}
            isPending
            error={features.error ?? resident.error}
            refetch={() => (features.error ? features.refetch() : resident.refetch())}
          />
        </section>
      );
    }
    return (
      <MeasurementCards features={features.data} residentCode={code} baselineForming={forming} />
    );
  };

  const epochCount = detail?.epoch_count ?? 1;

  return (
    <div className="stack">
      <section className="panel pad stack" aria-labelledby="score-heading">
        <h2 id="score-heading">{TRENDS_SCORE_HEADING}</h2>
        <p className="muted small">{trendsScoreIntro(code, h)}</p>
        {epochCount > 1 && (
          <div className={styles.epoch}>
            <label htmlFor={selectId}>{TRENDS_EPOCH_LABEL}</label>
            <select
              id={selectId}
              className={styles.select}
              value={shownEpoch}
              onChange={(e) => {
                const n = Number(e.target.value);
                setEpoch(n === currentEpoch ? null : n);
              }}
            >
              {Array.from({ length: epochCount }, (_, i) => i + 1).map((n) => (
                <option key={n} value={n}>
                  {trendsEpochOption(n, currentEpoch)}
                </option>
              ))}
            </select>
          </div>
        )}
        {scorePanel()}
      </section>
      {featurePanel()}
    </div>
  );
}
