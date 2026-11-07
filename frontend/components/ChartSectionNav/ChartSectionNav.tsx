// Section navigation of the resident chart (TRD 11 UX-410, UX-411, UX-241; TRD 04 FE-206, FE-210).
import Link from "next/link";
import {
  CHART_NAV_LABEL,
  CHART_REVIEW_BADGE_LABEL,
  CHART_SECTION_LABEL,
  CHART_SECTION_ORDER,
  type ChartSectionKey,
  chartSectionHref,
} from "@/lib/wording";
import { CountBadge } from "../CountBadge/CountBadge";
import styles from "./ChartSectionNav.module.css";

export interface ChartSectionNavProps {
  residentCode: string;
  current: ChartSectionKey;
  /** `ResidentDetail.alarm_reviewed === false` (FE-210). */
  unreviewedAlarm: boolean;
}

export function ChartSectionNav({ residentCode, current, unreviewedAlarm }: ChartSectionNavProps) {
  return (
    <nav aria-label={CHART_NAV_LABEL} className={styles.nav}>
      {CHART_SECTION_ORDER.map((section) => (
        <Link
          key={section}
          href={chartSectionHref(residentCode, section)}
          className={styles.link}
          aria-current={section === current ? "page" : undefined}
          aria-label={
            section === "review" && unreviewedAlarm
              ? `${CHART_SECTION_LABEL.review}, ${CHART_REVIEW_BADGE_LABEL}`
              : undefined
          }
        >
          <span>{CHART_SECTION_LABEL[section]}</span>
          {section === "review" && (
            <CountBadge count={unreviewedAlarm ? 1 : 0} label={CHART_REVIEW_BADGE_LABEL} />
          )}
        </Link>
      ))}
    </nav>
  );
}
