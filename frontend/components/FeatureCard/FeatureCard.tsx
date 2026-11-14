// One of the 7 scored measurements: plain label, technical name and a signed sparkline, or
// "Not scored yet" (TRD 11 UX-101..UX-105, UX-163; no thresholds, alarms or red here).
import { Sparkline } from "@/components/Sparkline/Sparkline";
import { TRENDS_NOT_SCORED, trendsSparklineName } from "@/lib/wording";
import styles from "./FeatureCard.module.css";

export interface FeatureCardProps {
  label: string;
  technicalName: string;
  sign: 1 | -1;
  series: { localDate: string; z: number }[];
  baselineForming: boolean;
}

export function FeatureCard({
  label,
  technicalName,
  sign,
  series,
  baselineForming,
}: FeatureCardProps) {
  const values = series.map((p) => sign * p.z);
  const latest = values[values.length - 1];
  const scored = !baselineForming && latest !== undefined;
  return (
    <li
      className={`${styles.card} ${scored ? styles.solid : styles.dashed}`}
      data-testid="feature-card"
    >
      <span>
        {label} <span className={styles.tech}>({technicalName})</span>
      </span>
      {scored ? (
        <Sparkline
          values={values}
          ariaLabel={trendsSparklineName(label, technicalName, latest, values.length)}
        />
      ) : (
        <span className={styles.notScored}>{TRENDS_NOT_SCORED}</span>
      )}
    </li>
  );
}
