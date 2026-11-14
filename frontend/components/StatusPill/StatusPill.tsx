// Status pill: glyph + label + colour + border, never colour alone (TRD 11 §4.3.4, UX-004, FE-092).
import type { UiStatus } from "@/lib/types";
import { STATUS_GLYPH, STATUS_LABEL } from "@/lib/wording";
import styles from "./StatusPill.module.css";

export interface StatusPillProps {
  status: UiStatus;
  size?: "sm" | "lg";
}

export function StatusPill({ status, size = "sm" }: StatusPillProps) {
  return (
    <span className={`${styles.pill} ${styles[status]} ${size === "lg" ? styles.lg : ""}`}>
      <span aria-hidden="true" className={styles.glyph}>
        {STATUS_GLYPH[status]}
      </span>
      {STATUS_LABEL[status]}
    </span>
  );
}
