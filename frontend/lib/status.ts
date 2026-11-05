// Presentation mapping of the API status to the four UI statuses (TRD 04 FE-207, TRD 11 §4.3.4).
// The browser evaluates no data-alert rule, threshold or device silence.
import type { DisplayStatus, UiStatus } from "./types";

export function toDisplayStatus(status: DisplayStatus, needsAttention: boolean): UiStatus {
  if (status === "alarm_on") return "changed";
  if (needsAttention) return "needs_attention";
  if (status === "baseline_forming") return "learning";
  return "usual";
}

export const UI_STATUSES: readonly UiStatus[] = ["changed", "needs_attention", "learning", "usual"];
