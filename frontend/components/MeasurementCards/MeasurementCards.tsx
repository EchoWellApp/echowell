// Panel "The 7 voice measurements behind the score": 7 FeatureCards in the §4.5.4 order, the
// "12 other measurements" card and the placeholder caption (TRD 11 UX-100..UX-108).
import { FeatureCard } from "@/components/FeatureCard/FeatureCard";
import { OtherMeasurementsCard } from "@/components/OtherMeasurementsCard/OtherMeasurementsCard";
import type { FeaturesResponse } from "@/lib/types";
import {
  TRENDS_MEASURES,
  TRENDS_MEASURES_CAPTION,
  TRENDS_MEASURES_HEADING,
  trendsMeasuresIntro,
} from "@/lib/wording";
import styles from "./MeasurementCards.module.css";

export interface MeasurementCardsProps {
  features: FeaturesResponse;
  residentCode: string;
  baselineForming: boolean;
}

type Series = FeaturesResponse["scored_features"][number];

/** The scored (non-baseline) sessions of the current epoch with their z values. */
export function scoredSeries(s: Series | undefined): { localDate: string; z: number }[] {
  if (!s) return [];
  return s.points.flatMap((p) =>
    !p.in_baseline && p.z !== null ? [{ localDate: p.local_date, z: p.z }] : [],
  );
}

export function MeasurementCards({
  features,
  residentCode,
  baselineForming,
}: MeasurementCardsProps) {
  return (
    <section className="panel pad stack" aria-labelledby="measures-heading">
      <h2 id="measures-heading">{TRENDS_MEASURES_HEADING}</h2>
      <p className="muted small">{trendsMeasuresIntro(residentCode)}</p>
      <ul className={styles.grid}>
        {TRENDS_MEASURES.map((m) => {
          // Labels follow TRD 11 §4.5.4 (the API label "Quieter (loudness)" carries the same text).
          const s = features.scored_features.find((f) => f.feature_key === m.key);
          return (
            <FeatureCard
              key={m.key}
              label={m.label}
              technicalName={m.technicalName}
              sign={s?.composite_sign ?? 1}
              series={scoredSeries(s)}
              baselineForming={baselineForming}
            />
          );
        })}
        <OtherMeasurementsCard storedKeys={features.stored_feature_keys} />
      </ul>
      <p className="caption">{TRENDS_MEASURES_CAPTION}</p>
    </section>
  );
}
