// Copy shared by every page: app chrome, data bar, statuses, states, login (TRD 11 §4.1, §4.3.4,
// §4.9, §4.11, UX-400).
import { formatLocalDateRange } from "../format";
import type { Meta, UiStatus } from "../types";

/** Shown in every Summary note and the resident-list note until the PI approves (OQ-12, UX-164). */
export const CLINICAL_WORDING_APPROVED = false;
export const PI_MARKER = "[Final clinical wording: confirm with PI]";

export const BRAND = "EchoWell";
export const facilityLine = (meta: Meta) => `${meta.facility_name}, Assisted living`;

export const NO_AUDIO = "No audio is stored or played anywhere in EchoWell.";

/** Data bar text (UX-400). `window` is the 30-day window ending on the as-of date. */
export function dataBarText(
  meta: Meta | undefined,
  window: { from: string; to: string } | null,
): string {
  if (!meta || meta.pipeline_profile !== "test_v0_1" || !window) return NO_AUDIO;
  const period = formatLocalDateRange(window.from, window.to, { withYear: true });
  return `Test data only (${meta.data_source_label}, ${period}). No real residents. ${NO_AUDIO}`;
}

export const NAV = {
  label: "Main",
  residents: "Resident list",
  admissions: "New admissions",
  study: "Study team",
  admin: "Admin",
  signOut: "Sign out",
} as const;

/** Accessible name of the "Resident list" link with its badge (UX-018). */
export const residentListLinkName = (n: number) =>
  n > 0 ? `Resident list, ${n} ${n === 1 ? "alarm" : "alarms"} not reviewed` : "Resident list";

export const STATUS_LABEL: Record<UiStatus, string> = {
  changed: "Changed",
  needs_attention: "Needs attention",
  learning: "Learning",
  usual: "Usual",
};

export const STATUS_GLYPH: Record<UiStatus, string> = {
  changed: "▲",
  needs_attention: "!",
  learning: "○",
  usual: "●",
};

/** "▲ Changed", "! Needs attention", "○ Learning", "● Usual" (FE-092). */
export const statusLabel = (s: UiStatus) => `${STATUS_GLYPH[s]} ${STATUS_LABEL[s]}`;

/** Legend meaning texts (TRD 11 §4.3.4). */
export function statusMeaning(s: UiStatus, meta: Meta): string {
  switch (s) {
    case "changed":
      return "Their voice has moved away from their own usual. Check on them.";
    case "needs_attention":
      return "Not enough good check-ins to judge. Check the device or the routine.";
    case "learning":
      return `Still collecting the first ${meta.baseline_n} check-ins to learn their usual.`;
    case "usual":
      return "Within their own usual range.";
  }
}

// States (UX-200..UX-206, FE-035, FE-145)
export const loadingText = (panel: string) => `Loading ${panel}…`;
export const errorText = (panel: string) =>
  `Could not load ${panel}. Check your connection and try again.`;
export const TRY_AGAIN = "Try again";
export const referenceText = (id: string) => `Reference: ${id}`;
export const NO_ACCESS_INFO = "You do not have access to this information.";
export const NO_ACCESS_PAGE = "You do not have access to this page.";
export const BACK_TO_LIST = "← Resident list";
export const SOMETHING_WRONG = "Something went wrong on this page.";
export const RELOAD = "Reload";
export const PAGE_NOT_FOUND = "This page was not found.";
export const residentNotFound = (code: string) => `Resident ${code} was not found.`;
export const couldNotRefresh = (asOf: string) => `Could not refresh. Showing data as of ${asOf}.`;
export const SKIP_LINK = "Skip to main content";
/** TRD 03 NFR-142: shown when JavaScript is disabled. */
export const NOSCRIPT_TEXT = "This dashboard needs JavaScript enabled.";

/** Document titles (UX-229, FE-032). */
export const pageTitle = (page: string) => `${page} – EchoWell`;

// Login (UX-170..UX-176)
export const LOGIN = {
  heading: "EchoWell",
  intro: "Sign in to see voice check-ins",
  email: "Email",
  password: "Password",
  submit: "Sign in",
  submitting: "Signing in…",
  wrong: "Email or password is incorrect.",
  tooMany: "Too many sign-in attempts. Wait one minute and try again.",
  expired: "Your session has ended. Please sign in again.",
  accounts: "Accounts are created by the EchoWell admin.",
  network: "Could not reach EchoWell. Check your connection and try again.",
} as const;
