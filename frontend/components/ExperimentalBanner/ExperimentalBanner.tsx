// Dashed yellow open-question note at the top of New admissions (TRD 11 UX-181, TRD 04 §4.8).
import type { ReactNode } from "react";
import { ADMISSIONS_NOTE } from "@/lib/wording";
import styles from "./ExperimentalBanner.module.css";

export interface ExperimentalBannerProps {
  children?: ReactNode;
}

export function ExperimentalBanner({ children }: ExperimentalBannerProps) {
  return <p className={styles.note}>{children ?? ADMISSIONS_NOTE}</p>;
}
