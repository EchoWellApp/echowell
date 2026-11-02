// Chart banner: resident code as <h1>, the four facts and the large status pill
// (TRD 11 UX-061..UX-063, UX-200, UX-241; TRD 04 §4.8).
import { formatDateTimeShort } from "@/lib/format";
import { toDisplayStatus } from "@/lib/status";
import type { Meta, ResidentDetail } from "@/lib/types";
import {
  CHART_BANNER_LABEL,
  CHART_FACT,
  CHART_NO_CHECKINS,
  CHART_PENDING,
  bannerBaselineText,
  bannerDeviceText,
  bannerUsableText,
} from "@/lib/wording";
import { StatusPill } from "../StatusPill/StatusPill";
import styles from "./ChartBanner.module.css";

export interface ChartBannerProps {
  /** null while the resident loads: the facts show "—" (UX-200). */
  resident: ResidentDetail | null;
  meta?: Meta;
  /** The code from the route, shown while the resident loads. */
  residentCode?: string;
}

export function ChartBanner({ resident, meta, residentCode }: ChartBannerProps) {
  const m = meta ?? resident?.meta;
  const facts: [string, string][] = resident
    ? [
        [CHART_FACT.device, bannerDeviceText(resident.device)],
        [
          CHART_FACT.lastCheckin,
          resident.last_checkin_at && m
            ? formatDateTimeShort(resident.last_checkin_at, m.facility_tz, m.as_of)
            : CHART_NO_CHECKINS,
        ],
        [CHART_FACT.usable, bannerUsableText(resident.last_30_days.used, resident.window.days)],
        [CHART_FACT.baseline, bannerBaselineText(resident.baseline)],
      ]
    : [
        [CHART_FACT.device, CHART_PENDING],
        [CHART_FACT.lastCheckin, CHART_PENDING],
        [CHART_FACT.usable, CHART_PENDING],
        [CHART_FACT.baseline, CHART_PENDING],
      ];
  return (
    <section aria-label={CHART_BANNER_LABEL} className={styles.banner}>
      <h1 className={styles.who}>{resident?.resident_code ?? residentCode}</h1>
      <dl className={styles.facts}>
        {facts.map(([term, value]) => (
          <div key={term}>
            <dt>{term}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
      {resident && (
        <span className={styles.pill}>
          <StatusPill
            status={toDisplayStatus(resident.status, resident.needs_attention)}
            size="lg"
          />
        </span>
      )}
    </section>
  );
}
