// Yellow data bar under the app bar (TRD 11 UX-400, TRD 04 FE-208).
import { windowOf } from "@/lib/format";
import type { Meta } from "@/lib/types";
import { dataBarText } from "@/lib/wording";
import styles from "./DataBar.module.css";

export interface DataBarProps {
  meta: Meta | undefined;
}

export function DataBar({ meta }: DataBarProps) {
  const window = meta?.as_of ? windowOf(meta.as_of, meta.facility_tz) : null;
  return (
    <div className={styles.bar} data-testid="data-bar">
      {dataBarText(meta, window)}
    </div>
  );
}
