// Residents table: Status · Resident · What's happening · Last check-in, in API order
// (TRD 11 UX-034..UX-046, UX-405, UX-408; TRD 04 FE-083, FE-084).
import Link from "next/link";
import { useRouter } from "next/navigation";
import type { MouseEvent } from "react";
import { StatusPill } from "@/components/StatusPill/StatusPill";
import { WhatsHappening } from "@/components/WhatsHappening/WhatsHappening";
import { formatDateTimeShort } from "@/lib/format";
import { toDisplayStatus } from "@/lib/status";
import type { Meta, ResidentRow } from "@/lib/types";
import {
  LIST_COLUMNS,
  LIST_NO_CHECKINS,
  LIST_NO_MATCH,
  LIST_TABLE_NAME,
  listCaption,
  openChartName,
  type ListFilter,
} from "@/lib/wording";
import styles from "./ResidentsTable.module.css";

export interface ResidentsTableProps {
  rows: ResidentRow[];
  meta: Meta;
  filter: ListFilter;
  isFetching: boolean;
}

const chartHref = (code: string) => `/residents/${encodeURIComponent(code)}`;

export function ResidentsTable({ rows, meta, filter, isFetching }: ResidentsTableProps) {
  const router = useRouter();
  // Filter in the browser by display status; keep the API order (FE-084).
  const shown = rows
    .map((row) => ({ row, status: toDisplayStatus(row.status, row.needs_attention) }))
    .filter((x) => filter === "all" || x.status === filter);

  const openRow = (e: MouseEvent<HTMLTableRowElement>, code: string) => {
    // The study-ID link navigates on its own.
    if ((e.target as HTMLElement).closest("a")) return;
    router.push(chartHref(code));
  };

  return (
    // eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex -- scroll container (UX-042)
    <div className={styles.wrap} tabIndex={0} role="region" aria-label={LIST_TABLE_NAME}>
      <table className={styles.table} aria-busy={isFetching}>
        <caption className="visually-hidden">{listCaption(filter)}</caption>
        <thead>
          <tr>
            <th scope="col">{LIST_COLUMNS.status}</th>
            <th scope="col">{LIST_COLUMNS.resident}</th>
            <th scope="col">{LIST_COLUMNS.whatsHappening}</th>
            <th scope="col">{LIST_COLUMNS.lastCheckin}</th>
          </tr>
        </thead>
        <tbody>
          {shown.length === 0 ? (
            <tr>
              <td colSpan={4} className={styles.muted}>
                {LIST_NO_MATCH}
              </td>
            </tr>
          ) : (
            shown.map(({ row, status }) => (
              <tr
                key={row.resident_code}
                className={`${styles.row} ${styles[status] ?? ""}`}
                data-status={status}
                onClick={(e) => openRow(e, row.resident_code)}
              >
                <td>
                  <StatusPill status={status} />
                </td>
                <td className={styles.rid}>
                  <Link
                    href={chartHref(row.resident_code)}
                    aria-label={openChartName(row.resident_code)}
                  >
                    {row.resident_code}
                  </Link>
                </td>
                <td>
                  <WhatsHappening row={row} meta={meta} />
                </td>
                <td className={styles.muted}>
                  {row.last_checkin_at
                    ? formatDateTimeShort(row.last_checkin_at, meta.facility_tz, meta.as_of)
                    : LIST_NO_CHECKINS}
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
