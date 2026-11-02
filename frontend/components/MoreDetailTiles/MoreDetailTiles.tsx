// "More detail" heading and the four link tiles of the Summary (TRD 11 UX-078, UX-200).
import Link from "next/link";
import { formatTally } from "@/lib/format";
import { toDisplayStatus } from "@/lib/status";
import type { DeviceItem, Meta, ResidentDetail } from "@/lib/types";
import {
  CHART_PENDING,
  MORE_DETAIL,
  TILE,
  chartSectionHref,
  tileBaseline,
  tileChangeScore,
  tileCheckins,
  tileDevice,
} from "@/lib/wording";
import styles from "./MoreDetailTiles.module.css";

export interface MoreDetailTilesProps {
  resident: ResidentDetail;
  /** Latest change score of the current epoch (null: none, undefined: still loading). */
  latestTally: number | null | undefined;
  /** The resident's current device (null when unknown or still loading: "—"). */
  device: DeviceItem | null;
  meta: Meta;
}

function trendsValue(resident: ResidentDetail, latestTally: number | null | undefined): string {
  if (resident.baseline.state !== "frozen") return TILE.notScored;
  if (toDisplayStatus(resident.status, resident.needs_attention) !== "changed") {
    return TILE.noChange;
  }
  const tally = latestTally === undefined ? null : (latestTally ?? resident.current_tally);
  return tally === null ? CHART_PENDING : tileChangeScore(formatTally(tally));
}

export function MoreDetailTiles({ resident, latestTally, device }: MoreDetailTilesProps) {
  const code = resident.resident_code;
  const c = resident.last_30_days;
  const tiles: { key: string; label: string; value: string; href: string }[] = [
    {
      key: "trends",
      label: TILE.trends,
      value: trendsValue(resident, latestTally),
      href: chartSectionHref(code, "trends"),
    },
    {
      key: "baseline",
      label: TILE.baseline,
      value: tileBaseline(resident.baseline.n_usable, resident.baseline.n_required),
      href: chartSectionHref(code, "baseline"),
    },
    {
      key: "log",
      label: TILE.checkins,
      value: tileCheckins(c.used, c.missed),
      href: chartSectionHref(code, "log"),
    },
    {
      key: "device",
      label: TILE.device,
      value: device ? tileDevice(device.device_code, device.uploaded_on_as_of_date) : CHART_PENDING,
      href: chartSectionHref(code, "device"),
    },
  ];
  return (
    <section className="stack" aria-labelledby="more-detail">
      <h2 id="more-detail">{MORE_DETAIL}</h2>
      <div className={styles.tiles}>
        {tiles.map((t) => (
          <Link key={t.key} href={t.href} className={styles.tile}>
            <span className={styles.k}>{t.label}</span>
            <span className={styles.v}>{t.value}</span>
            <span className={styles.go}>{TILE.open}</span>
          </Link>
        ))}
      </div>
    </section>
  );
}
