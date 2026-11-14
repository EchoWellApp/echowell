// New admissions table (TRD 11 UX-182..UX-188, UX-194; TRD 04 §4.8, FE-092). Presentational.
import { formatLocalDate } from "@/lib/format";
import type { AdmissionRow, ComparisonStatus, Meta } from "@/lib/types";
import {
  ADMISSIONS_COLUMNS,
  ADMISSIONS_COMPARISON_TEXT,
  ADMISSIONS_NO_VALUE,
  ADMISSIONS_SHOW_COMPARISON,
  ADMISSIONS_TABLE_NAME,
  admissionsEmpty,
  admissionsOwnBaseline,
  admissionsShowComparisonName,
} from "@/lib/wording";
import { RangePill } from "../RangePill/RangePill";
import { StatusPill } from "../StatusPill/StatusPill";
import styles from "./AdmissionsTable.module.css";

export interface AdmissionsTableProps {
  rows: AdmissionRow[];
  meta: Meta;
  selected: string | null;
  onSelect(code: string): void;
}

/** The one place that maps a comparison status to its pill (UX-185, D-117). */
export function AdmissionPill({ status }: { status: ComparisonStatus }) {
  switch (status) {
    case "outside_range":
      return <RangePill inRange={false} />;
    case "within_range":
      return <RangePill inRange />;
    default:
      return <StatusPill status="learning" />;
  }
}

export function AdmissionsTable({ rows, meta, selected, onSelect }: AdmissionsTableProps) {
  if (rows.length === 0) {
    return <p className={styles.empty}>{admissionsEmpty(meta.pipeline_profile)}</p>;
  }
  return (
    // eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex -- scroll container (UX-243)
    <div className="scroll-x" tabIndex={0} role="region" aria-label={ADMISSIONS_TABLE_NAME}>
      <table className={styles.table}>
        <thead>
          <tr>
            <th scope="col">{ADMISSIONS_COLUMNS.status}</th>
            <th scope="col">{ADMISSIONS_COLUMNS.resident}</th>
            <th scope="col">{ADMISSIONS_COLUMNS.admitted}</th>
            <th scope="col">{ADMISSIONS_COLUMNS.compared}</th>
            <th scope="col">{ADMISSIONS_COLUMNS.ownBaseline}</th>
            <th scope="col">
              <span className="visually-hidden">{ADMISSIONS_COLUMNS.actions}</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => {
            const isSelected = row.resident_code === selected;
            return (
              <tr
                key={row.resident_code}
                aria-selected={isSelected}
                className={isSelected ? styles.selected : undefined}
              >
                <td>
                  <AdmissionPill status={row.comparison_status} />
                </td>
                <td className={styles.rid}>{row.resident_code}</td>
                <td>
                  {row.admitted_on
                    ? formatLocalDate(row.admitted_on, meta.as_of, meta.facility_tz)
                    : ADMISSIONS_NO_VALUE}
                </td>
                <td>{ADMISSIONS_COMPARISON_TEXT[row.comparison_status]}</td>
                <td>
                  {admissionsOwnBaseline(row.own_baseline_progress.n_usable, meta.baseline_n)}
                </td>
                <td>
                  <button
                    type="button"
                    className="btn btn-secondary"
                    aria-label={admissionsShowComparisonName(row.resident_code)}
                    aria-pressed={isSelected}
                    onClick={() => onSelect(row.resident_code)}
                  >
                    {ADMISSIONS_SHOW_COMPARISON}
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
