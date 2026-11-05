// 110 × 28px sparkline of signed deviations (sign × z) with a dashed zero line for the
// resident's own frozen baseline; no axes, grid, tooltip or animation (TRD 04 FE-098, FE-099;
// TRD 11 UX-102, UX-103).
import { Line, LineChart, ReferenceLine, XAxis, YAxis } from "recharts";
import styles from "./Sparkline.module.css";

export interface SparklineProps {
  values: number[];
  ariaLabel: string;
  width?: number;
  height?: number;
}

export function Sparkline({ values, ariaLabel, width = 110, height = 28 }: SparklineProps) {
  const data = values.map((v, i) => ({ i, v }));
  const lo = Math.min(0, ...values);
  const hi = Math.max(0, ...values);
  const pad = hi === lo ? 1 : 0;
  return (
    <div role="img" aria-label={ariaLabel} className={styles.spark} style={{ width, height }}>
      <LineChart
        width={width}
        height={height}
        data={data}
        margin={{ top: 2, right: 2, bottom: 2, left: 2 }}
      >
        <XAxis dataKey="i" type="number" domain={[0, Math.max(1, values.length - 1)]} hide />
        <YAxis type="number" domain={[lo - pad, hi + pad]} hide />
        <ReferenceLine y={0} stroke="var(--rule)" strokeDasharray="3 3" ifOverflow="extendDomain" />
        <Line
          type="linear"
          dataKey="v"
          stroke="var(--ink)"
          strokeWidth={1.5}
          dot={values.length === 1 ? { r: 1.5, fill: "var(--ink)", stroke: "none" } : false}
          activeDot={false}
          isAnimationActive={false}
        />
      </LineChart>
    </div>
  );
}
