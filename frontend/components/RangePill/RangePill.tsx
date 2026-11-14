// Neutral "In range" / "Out of range" pill: compared with the facility range, not the resident's
// own usual, so no status colour and no glyph (TRD 11 UX-185, TRD 24 D-117, TRD 04 FE-092).
import { ADMISSIONS_RANGE_PILL } from "@/lib/wording";
import styles from "./RangePill.module.css";

export interface RangePillProps {
  inRange: boolean;
}

export function RangePill({ inRange }: RangePillProps) {
  return (
    <span className={styles.pill}>
      {inRange ? ADMISSIONS_RANGE_PILL.inRange : ADMISSIONS_RANGE_PILL.outOfRange}
    </span>
  );
}
