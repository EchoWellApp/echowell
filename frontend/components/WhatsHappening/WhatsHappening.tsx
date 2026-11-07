// One "What's happening" sentence (TRD 11 §4.3.6, UX-405); templates live in lib/wording/list.ts.
import { toDisplayStatus } from "@/lib/status";
import type { Meta, ResidentDetail, ResidentRow } from "@/lib/types";
import { whatsHappening } from "@/lib/wording";
import styles from "./WhatsHappening.module.css";

export interface WhatsHappeningProps {
  row: ResidentRow | ResidentDetail;
  meta: Meta;
}

export function WhatsHappening({ row, meta }: WhatsHappeningProps) {
  const status = toDisplayStatus(row.status, row.needs_attention);
  return <span className={styles.text}>{whatsHappening(row, status, meta)}</span>;
}
