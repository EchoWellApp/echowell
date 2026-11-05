// "Events" panel of the check-in log (TRD 11 UX-140..UX-150, §4.5.6; TRD 04 FE-101).
// Events are rendered in the API order (newest first); nothing is re-sorted, filled or estimated.
import type { ReactNode } from "react";
import { formatLocalDate } from "@/lib/format";
import type { CheckinEvent } from "@/lib/types";
import {
  DUPLICATES_CAPTION,
  EVENTS_EMPTY,
  EVENTS_HEADING,
  LOADING_EARLIER,
  SHOW_EARLIER,
  logLine,
} from "@/lib/wording";
import styles from "./CheckinLog.module.css";

export interface CheckinLogProps {
  events: readonly CheckinEvent[];
  /** Alarm line `meta.cusum_h`. */
  h: number;
  tz: string;
  residentCode: string;
  currentDeviceCode: string | null;
  /** `meta.as_of`, so dates in another year carry the year. */
  asOf?: string | null;
  /** `meta.baseline_n`, used when a baseline_complete event has no detail. */
  baselineN?: number;
  /** Whether earlier events may exist before the shown range (UX-146). */
  hasEarlier?: boolean;
  onShowEarlier?: () => void;
  loadingEarlier?: boolean;
  /** Error state of a failed "Show earlier entries" request (shown below the events). */
  earlierState?: ReactNode;
  /** Loading or error state of the first request (replaces the list). */
  state?: ReactNode;
}

/** Only the event types the log shows (UX-143, UX-144): never a usable check-in or duplicate. */
const SHOWN = new Set<string>([
  "alarm_on",
  "watching_started",
  "baseline_complete",
  "baseline_restarted",
  "set_aside",
  "quarantined",
  "missed",
  "device_silent",
  "checkins_started",
]);

export function CheckinLog({
  events,
  h,
  tz,
  residentCode,
  currentDeviceCode,
  asOf = null,
  baselineN = 0,
  hasEarlier = false,
  onShowEarlier,
  loadingEarlier = false,
  earlierState,
  state,
}: CheckinLogProps) {
  const shown = events.filter((e) => SHOWN.has(e.event_type));
  const ctx = { h, baselineN, currentDeviceCode };
  return (
    <section className="panel pad stack" aria-labelledby={`events-${residentCode}`}>
      <h2 id={`events-${residentCode}`}>{EVENTS_HEADING}</h2>
      {state ??
        (shown.length === 0 ? (
          <p>{EVENTS_EMPTY}</p>
        ) : (
          <ul className={styles.events}>
            {shown.map((e, i) => (
              <li key={`${e.local_date}-${e.event_type}-${e.session_id ?? ""}-${i}`}>
                <span className={styles.date}>{formatLocalDate(e.local_date, asOf, tz)}</span>
                <span>{logLine(e, ctx)}</span>
              </li>
            ))}
          </ul>
        ))}
      {!state && earlierState}
      {!state && hasEarlier && !earlierState && (
        <div>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onShowEarlier}
            disabled={loadingEarlier}
          >
            {loadingEarlier ? LOADING_EARLIER : SHOW_EARLIER}
          </button>
        </div>
      )}
      <p className={styles.caption}>{DUPLICATES_CAPTION}</p>
    </section>
  );
}
