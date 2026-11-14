// "Leaning most: <labels>" for a Changed resident (TRD 11 UX-312, TRD 24 D-92).
import { leaningMostText } from "@/lib/wording";
import styles from "./LeaningMost.module.css";

export interface LeaningMostProps {
  /** The alert's `leaning_most` keys, highest first (at most 3 are shown). */
  featureKeys: readonly string[];
}

export function LeaningMost({ featureKeys }: LeaningMostProps) {
  return <p className={styles.leaning}>{leaningMostText(featureKeys)}</p>;
}
