// "Change score" chart: CUSUM tally per scored session of the displayed epoch, the leading
// baseline slot, the dashed alarm line, the "▲" first-crossing marker and the table alternative
// (TRD 11 UX-081..UX-087, UX-090..UX-092; TRD 04 FE-093..FE-097, FE-099).
import { Bar, ComposedChart, ReferenceArea, ReferenceLine, XAxis, YAxis } from "recharts";
import { ChangeScoreTable } from "@/components/ChangeScoreTable/ChangeScoreTable";
import { formatLocalDate, formatLocalDateRange } from "@/lib/format";
import type { BaselinePeriod, ScorePoint } from "@/lib/types";
import {
  TRENDS_ALARM_MARKER,
  TRENDS_CHART_SCROLL_NAME,
  TRENDS_TABLE_TOGGLE,
  changeScoreSummary,
  trendsAlarmLine,
  trendsAlarmTick,
  trendsBarTooltip,
  trendsBaselineLabel,
  trendsDevicePeriod,
} from "@/lib/wording";
import styles from "./ChangeScoreChart.module.css";

export interface ChangeScoreChartProps {
  points: ScorePoint[];
  baselinePeriod: BaselinePeriod | null;
  h: number;
  residentCode: string;
  /** Facility time zone (dates arrive as facility-local `YYYY-MM-DD`, so no conversion is needed). */
  tz: string;
  /** Start of the current device period when the current epoch is > 1 (UX-092), else null. */
  restartedOn: string | null;
}

export const BASELINE_KEY = "__baseline__";
export const PLOT_HEIGHT = 200;
export const MIN_WIDTH = 520;
const SLOT_WIDTH = 44;
const Y_AXIS_WIDTH = 36;
const MARGIN = { top: 22, right: 12, bottom: 0, left: 0 };
const X_AXIS_HEIGHT = 40;
const MIN_LABEL_GAP = 48;

interface Datum {
  key: string;
  cusum_tally: number | null;
  alarm_state: ScorePoint["alarm_state"] | null;
  local_date: string | null;
}

/** UX-087: max(1.2 × h, 1.05 × largest value); ticks every 10 above 20, else every 5. */
export function yScale(h: number, values: number[]): { max: number; ticks: number[] } {
  const max = Math.max(1.2 * h, 1.05 * Math.max(0, ...values));
  const step = max > 20 ? 10 : 5;
  const ticks: number[] = [];
  for (let t = 0; t <= max + 1e-9; t += step) ticks.push(t);
  return { max, ticks };
}

/**
 * Indices (into `points`) whose date is labelled on the x axis: always the first, the alarm and the
 * last scored date (UX-086), then others while they stay at least 48px from every label.
 */
export function labelledIndices(
  points: Pick<ScorePoint, "alarm_state">[],
  slot: number,
): Set<number> {
  const out = new Set<number>();
  if (points.length === 0) return out;
  const alarm = points.findIndex((p) => p.alarm_state === "rings");
  const width = (i: number) => (i === alarm ? 84 : 40);
  const fits = (i: number) =>
    [...out].every(
      (j) => Math.abs(i - j) * slot >= Math.max(MIN_LABEL_GAP, (width(i) + width(j)) / 2 + 8),
    );
  if (alarm >= 0) out.add(alarm);
  out.add(0);
  out.add(points.length - 1);
  for (let i = 0; i < points.length; i++) if (!out.has(i) && fits(i)) out.add(i);
  return out;
}

interface BarShapeProps {
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  payload?: Datum;
}

function ScoreBar({ x = 0, y = 0, width = 0, height = 0, payload }: BarShapeProps) {
  if (!payload || payload.local_date === null || payload.cusum_tally === null) return null;
  const off = payload.alarm_state === "off";
  const stub = payload.cusum_tally === 0;
  const title = trendsBarTooltip(payload.local_date, payload.cusum_tally);
  return (
    <g
      data-testid="score-bar"
      data-date={payload.local_date}
      data-alarm-state={payload.alarm_state}
    >
      <title>{title}</title>
      {stub ? (
        <rect x={x} y={y - 2} width={width} height={2} fill="var(--rule)" data-stub="true" />
      ) : (
        <rect
          x={x}
          y={y}
          width={width}
          height={height}
          fill={off ? "var(--c-aside)" : "var(--red)"}
          stroke={off ? "var(--muted)" : undefined}
          strokeWidth={off ? 1 : undefined}
        />
      )}
      {payload.alarm_state === "rings" && (
        <text
          x={x + width / 2}
          y={(stub ? y - 2 : y) - 6}
          textAnchor="middle"
          fontSize={14}
          fill="var(--red)"
          data-testid="alarm-marker"
        >
          {TRENDS_ALARM_MARKER}
        </text>
      )}
    </g>
  );
}

export function ChangeScoreChart({
  points,
  baselinePeriod,
  h,
  residentCode,
  restartedOn,
}: ChangeScoreChartProps) {
  const baselineRange = baselinePeriod
    ? formatLocalDateRange(baselinePeriod.first_local_date, baselinePeriod.frozen_after_local_date)
    : null;
  const data: Datum[] = [
    ...(baselineRange
      ? [{ key: BASELINE_KEY, cusum_tally: null, alarm_state: null, local_date: null }]
      : []),
    ...points.map((p) => ({
      key: p.local_date,
      cusum_tally: p.cusum_tally,
      alarm_state: p.alarm_state,
      local_date: p.local_date,
    })),
  ];
  const width = Math.max(MIN_WIDTH, Y_AXIS_WIDTH + MARGIN.right + data.length * SLOT_WIDTH);
  const slot = data.length > 0 ? (width - Y_AXIS_WIDTH - MARGIN.right) / data.length : 0;
  const labelled = labelledIndices(points, slot);
  const offset = baselineRange ? 1 : 0;
  const { max, ticks } = yScale(
    h,
    points.map((p) => p.cusum_tally),
  );
  const summary = changeScoreSummary({ residentCode, points, baselineRange, h });

  const renderTick = (props: {
    x?: number;
    y?: number;
    payload?: { value?: string; index?: number };
  }) => {
    const { x = 0, y = 0, payload } = props;
    const value = payload?.value ?? "";
    if (value === BASELINE_KEY) {
      return (
        <text x={x - slot / 2 + 2} y={y + 28} textAnchor="start" fontSize={12} fill="var(--muted)">
          {trendsBaselineLabel(baselineRange ?? "")}
        </text>
      );
    }
    const i = data.findIndex((d) => d.key === value) - offset;
    const point = points[i];
    if (!point || !labelled.has(i)) return <g />;
    const date = formatLocalDate(point.local_date);
    const rings = point.alarm_state === "rings";
    return (
      <text
        x={x}
        y={y + 12}
        textAnchor="middle"
        fontSize={12}
        fill={rings ? "var(--red)" : "var(--muted)"}
        data-testid={rings ? "alarm-tick" : undefined}
      >
        {rings ? trendsAlarmTick(date) : date}
      </text>
    );
  };

  const renderAlarmLabel = (props: { viewBox?: { x?: number; y?: number } }) => (
    <text
      x={(props.viewBox?.x ?? 0) + 6}
      y={(props.viewBox?.y ?? 0) - 6}
      textAnchor="start"
      fontSize={12}
      fill="var(--red)"
      data-testid="alarm-line-label"
    >
      {trendsAlarmLine(h)}
    </text>
  );

  return (
    <div className={styles.wrap}>
      {restartedOn && <p className="muted small">{trendsDevicePeriod(restartedOn)}</p>}
      {/* UX-243: the chart alone may scroll sideways, inside a focusable, named container. */}
      <div
        className={styles.scroll}
        // eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex -- UX-243 keyboard scrolling
        tabIndex={0}
        role="region"
        aria-label={TRENDS_CHART_SCROLL_NAME}
      >
        <div role="img" aria-label={summary} style={{ width, minWidth: MIN_WIDTH }}>
          <ComposedChart
            width={width}
            height={PLOT_HEIGHT + MARGIN.top + X_AXIS_HEIGHT}
            data={data}
            margin={MARGIN}
            barCategoryGap="20%"
          >
            {baselineRange && (
              <ReferenceArea
                x1={BASELINE_KEY}
                x2={BASELINE_KEY}
                fill="var(--grey-bg)"
                fillOpacity={1}
                stroke="none"
                ifOverflow="extendDomain"
                className="baseline-slot"
              />
            )}
            <XAxis
              dataKey="key"
              type="category"
              interval={0}
              height={X_AXIS_HEIGHT}
              tickLine={false}
              axisLine={{ stroke: "var(--rule)" }}
              tick={renderTick}
            />
            <YAxis
              type="number"
              domain={[0, max]}
              ticks={ticks}
              width={Y_AXIS_WIDTH}
              allowDecimals={false}
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 12, fill: "var(--muted)" }}
            />
            <Bar
              dataKey="cusum_tally"
              isAnimationActive={false}
              maxBarSize={32}
              shape={(p: unknown) => <ScoreBar {...(p as BarShapeProps)} />}
            />
            <ReferenceLine
              y={h}
              stroke="var(--red)"
              strokeWidth={2}
              strokeDasharray="6 4"
              ifOverflow="extendDomain"
              label={renderAlarmLabel}
            />
          </ComposedChart>
        </div>
      </div>
      <details className={styles.details}>
        <summary className={styles.summary}>{TRENDS_TABLE_TOGGLE}</summary>
        <ChangeScoreTable points={points} h={h} />
      </details>
    </div>
  );
}
