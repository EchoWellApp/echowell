// "Check-ins per day" (TRD 11 UX-356..UX-361): one stacked bar per local day (Used, Set aside,
// Held back, Missed bottom to top), a legend, x labels for the first day, device-silent days and
// the last day, and a table alternative. The Held-back colour is a data category, never "▲".
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";
import { formatLocalDate, formatLocalDateRange } from "@/lib/format";
import type { DailySeriesPoint, Meta } from "@/lib/types";
import {
  STUDY_DAILY_COLUMNS,
  STUDY_DAILY_HEADING,
  STUDY_DAILY_TABLE_TOGGLE,
  STUDY_LEGEND,
  studyDailyChartName,
  studyDayLabel,
  studyDayTooltip,
  studySilentNote,
} from "@/lib/wording";
import styles from "./DailyCheckinsChart.module.css";

export interface DailyCheckinsChartProps {
  series: DailySeriesPoint[];
  meta: Meta;
}

const WIDTH = 760;
const HEIGHT = 200; // plot about 160px plus the x labels

type Key = "used" | "set_aside" | "quarantined" | "missed";
const SEGMENTS: { key: Key; fill: string; dashed?: boolean }[] = [
  { key: "used", fill: "var(--c-used)" },
  { key: "set_aside", fill: "var(--c-aside)" },
  { key: "quarantined", fill: "var(--c-quar)" },
  { key: "missed", fill: "none", dashed: true },
];

export function dailyTotals(series: readonly DailySeriesPoint[]) {
  return series.reduce(
    (t, d) => ({
      used: t.used + d.used,
      set_aside: t.set_aside + d.set_aside,
      quarantined: t.quarantined + d.quarantined,
      missed: t.missed + d.missed,
    }),
    { used: 0, set_aside: 0, quarantined: 0, missed: 0 },
  );
}

/** The x labels: first day, every day with a device-silent gap, last day (UX-358). */
export function dailyAxisLabels(series: readonly DailySeriesPoint[]): Map<string, string> {
  const out = new Map<string, string>();
  series.forEach((d, i) => {
    if (i === 0 || i === series.length - 1 || d.silent_device_codes.length > 0) {
      out.set(d.local_date, studyDayLabel(d.local_date, d.silent_device_codes));
    }
  });
  return out;
}

interface SegmentShapeProps {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  fill?: string;
  payload?: DailySeriesPoint;
}

function segmentShape(dashed: boolean) {
  function Segment({ x = 0, y = 0, width = 0, height = 0, fill, payload }: SegmentShapeProps) {
    if (!payload || height <= 0) return <g />;
    return (
      <g data-testid="day-segment">
        <title>{studyDayTooltip(payload.local_date, payload)}</title>
        {dashed ? (
          <rect
            x={x + 0.5}
            y={y}
            width={Math.max(width - 1, 0)}
            height={height}
            fill="none"
            stroke="var(--muted)"
            strokeDasharray="3 2"
          />
        ) : (
          <rect x={x} y={y} width={width} height={height} fill={fill} />
        )}
      </g>
    );
  }
  return Segment;
}

export function DailyCheckinsChart({ series }: DailyCheckinsChartProps) {
  const totals = dailyTotals(series);
  const first = series[0]?.local_date;
  const last = series[series.length - 1]?.local_date;
  const period = first && last ? formatLocalDateRange(first, last) : "";
  const name = studyDailyChartName(period, totals);
  const labels = dailyAxisLabels(series);
  const lastIndex = series.length - 1;
  const max = Math.max(1, ...series.map((d) => d.used + d.set_aside + d.quarantined + d.missed));

  return (
    <section className="panel pad stack" aria-labelledby="daily-heading">
      <h2 id="daily-heading">{STUDY_DAILY_HEADING}</h2>
      <ul className={styles.legend} aria-label="Legend">
        <li>
          <span className={`${styles.swatch} ${styles.used}`} aria-hidden="true" />
          {STUDY_LEGEND.used}
        </li>
        <li>
          <span className={`${styles.swatch} ${styles.aside}`} aria-hidden="true" />
          {STUDY_LEGEND.setAside}
        </li>
        <li>
          <span className={`${styles.swatch} ${styles.quar}`} aria-hidden="true" />
          {STUDY_LEGEND.heldBack}
        </li>
        <li>
          <span className={`${styles.swatch} ${styles.missed}`} aria-hidden="true" />
          {STUDY_LEGEND.missed}
        </li>
      </ul>
      {/* eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex -- scroll container (UX-243) */}
      <div className={`scroll-x ${styles.scroll}`} tabIndex={0} role="region" aria-label={name}>
        <BarChart
          width={WIDTH}
          height={HEIGHT}
          data={series}
          margin={{ top: 8, right: 12, bottom: 4, left: 0 }}
          barCategoryGap={2}
        >
          <CartesianGrid vertical={false} stroke="var(--rule)" />
          <XAxis
            dataKey="local_date"
            interval={0}
            tickLine={false}
            axisLine={{ stroke: "var(--rule)" }}
            tick={(props: { x: number; y: number; payload: { value: string; index: number } }) => {
              const text = labels.get(props.payload.value);
              if (!text) return <g />;
              const i = props.payload.index;
              const anchor = i === 0 ? "start" : i === lastIndex ? "end" : "middle";
              return (
                <text
                  x={props.x}
                  y={props.y + 12}
                  textAnchor={anchor}
                  fontSize={12}
                  fill="var(--muted)"
                  data-testid="x-label"
                >
                  {text}
                </text>
              );
            }}
          />
          <YAxis
            width={30}
            domain={[0, max]}
            ticks={[0, Math.round(max / 2), max]}
            tickLine={false}
            axisLine={false}
            tick={{ fontSize: 12, fill: "var(--muted)" }}
          />
          {SEGMENTS.map((s) => (
            <Bar
              key={s.key}
              dataKey={s.key}
              stackId="day"
              fill={s.fill}
              isAnimationActive={false}
              shape={segmentShape(Boolean(s.dashed))}
            />
          ))}
        </BarChart>
      </div>
      <details className={styles.details}>
        <summary>{STUDY_DAILY_TABLE_TOGGLE}</summary>
        <div className="scroll-x">
          <table className={styles.table}>
            <thead>
              <tr>
                {STUDY_DAILY_COLUMNS.map((c) => (
                  <th key={c} scope="col">
                    {c}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {series.map((d) => (
                <tr key={d.local_date}>
                  <th scope="row">{formatLocalDate(d.local_date)}</th>
                  <td>{d.used}</td>
                  <td>{d.set_aside}</td>
                  <td>{d.quarantined}</td>
                  <td>{d.missed}</td>
                  <td>{studySilentNote(d.silent_device_codes)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </section>
  );
}
