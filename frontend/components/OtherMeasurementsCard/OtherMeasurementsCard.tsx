// The eighth card: the stored-not-scored measurements are counted, never listed or plotted
// (TRD 11 UX-106, UX-107).
import { TRENDS_STORED_NOT_SCORED, trendsOtherMeasures } from "@/lib/wording";
import styles from "./OtherMeasurementsCard.module.css";

export interface OtherMeasurementsCardProps {
  storedKeys: string[];
}

export function OtherMeasurementsCard({ storedKeys }: OtherMeasurementsCardProps) {
  return (
    <li className={styles.card} data-testid="other-measurements-card">
      <span>{trendsOtherMeasures(storedKeys.length)}</span>
      <span className={styles.right}>{TRENDS_STORED_NOT_SCORED}</span>
    </li>
  );
}
