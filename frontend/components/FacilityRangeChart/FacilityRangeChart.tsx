// Resident value vs facility range, one row per measurement, with a table alternative
// (TRD 11 UX-189..UX-193, TRD 04 FE-100). Presentational.
import type { AdmissionComparison } from "@/lib/types";
import {
  ADMISSIONS_CHART_CAPTION,
  ADMISSIONS_COMPARISON_TEXT,
  ADMISSIONS_OUTSIDE_NO,
  ADMISSIONS_OUTSIDE_YES,
  ADMISSIONS_TABLE_COLUMNS,
  ADMISSIONS_TABLE_TOGGLE,
  admissionsChartName,
  admissionsMeasurementLabel,
  admissionsRange,
  admissionsTransition,
  admissionsValue,
} from "@/lib/wording";
import styles from "./FacilityRangeChart.module.css";

export interface FacilityRangeChartProps {
  comparison: AdmissionComparison;
  residentCode: string;
  N: number;
}

type Feature = AdmissionComparison["features"][number];
type Banded = Feature & { low: number; high: number };

const hasBand = (f: Feature): f is Banded => f.low !== null && f.high !== null;

/** Per-row scale: the band takes the middle, the resident value always fits (percentages). */
export function rowScale(f: Banded): { band: [number, number]; dot: number | null } {
  const span = f.high - f.low || Math.abs(f.high) || 1;
  let min = f.low - span * 0.5;
  let max = f.high + span * 0.5;
  if (f.resident_value !== null) {
    min = Math.min(min, f.resident_value - span * 0.1);
    max = Math.max(max, f.resident_value + span * 0.1);
  }
  const pct = (x: number) => ((x - min) / (max - min)) * 100;
  return {
    band: [pct(f.low), pct(f.high)],
    dot: f.resident_value === null ? null : pct(f.resident_value),
  };
}

export function FacilityRangeChart({ comparison, residentCode, N }: FacilityRangeChartProps) {
  const rows = comparison.features.filter(hasBand);
  const outside = rows.filter((f) => f.outside_range === true).length;
  return (
    <div className="stack">
      {rows.length === 0 ? (
        <p className="small muted">{ADMISSIONS_COMPARISON_TEXT.range_not_available}</p>
      ) : (
        <figure className={styles.figure}>
          <div
            className={styles.chart}
            role="img"
            // eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex -- chart (UX-225)
            tabIndex={0}
            aria-label={admissionsChartName(residentCode, outside, rows.length)}
          >
            {rows.map((f) => {
              const s = rowScale(f);
              const out = f.outside_range === true;
              return (
                <div key={f.feature_key} className={styles.row} data-testid="range-row">
                  <span className={styles.label}>{admissionsMeasurementLabel(f.feature_key)}</span>
                  <span className={styles.track}>
                    <span
                      className={styles.band}
                      data-testid="range-band"
                      style={{ left: `${s.band[0]}%`, width: `${s.band[1] - s.band[0]}%` }}
                    />
                    {s.dot !== null && (
                      <span
                        className={`${styles.dot} ${out ? styles.out : styles.in}`}
                        data-testid="range-dot"
                        data-outside={out}
                        style={{ left: `${s.dot}%` }}
                      >
                        {out && (
                          <span aria-hidden="true" className={styles.glyph}>
                            ▲
                          </span>
                        )}
                      </span>
                    )}
                  </span>
                </div>
              );
            })}
          </div>
          <figcaption className="caption">{ADMISSIONS_CHART_CAPTION}</figcaption>
        </figure>
      )}
      {rows.length > 0 && (
        <details className={styles.details}>
          <summary className={styles.summary}>{ADMISSIONS_TABLE_TOGGLE}</summary>
          <table className={styles.table}>
            <thead>
              <tr>
                <th scope="col">{ADMISSIONS_TABLE_COLUMNS.measurement}</th>
                <th scope="col">{ADMISSIONS_TABLE_COLUMNS.value}</th>
                <th scope="col">{ADMISSIONS_TABLE_COLUMNS.range}</th>
                <th scope="col">{ADMISSIONS_TABLE_COLUMNS.outside}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((f) => (
                <tr key={f.feature_key}>
                  <th scope="row">{admissionsMeasurementLabel(f.feature_key)}</th>
                  <td>{admissionsValue(f.resident_value)}</td>
                  <td>{admissionsRange(f.low, f.high)}</td>
                  <td>{f.outside_range ? ADMISSIONS_OUTSIDE_YES : ADMISSIONS_OUTSIDE_NO}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      )}
      <p className="small muted">{admissionsTransition(N)}</p>
    </div>
  );
}
