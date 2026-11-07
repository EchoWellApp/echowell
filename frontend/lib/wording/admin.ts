// Copy for New admissions (TRD 11 §4.7) and Admin (TRD 11 §4.10); TRD 04 FE-013.
import type { ComparisonStatus, PipelineRun, Role } from "../types";

// ---------- New admissions (UX-181..UX-195) ----------

/** UX-181: the second and third sentences stay until OQ-08 is closed. */
export const ADMISSIONS_NOTE =
  "Future / experimental. Not in pipeline test v0.1: the test data has no admission group or facility range yet. Open question for Shaba and the PI.";
export const ADMISSIONS_TITLE = "New admissions";
export const ADMISSIONS_INTRO =
  "New residents don’t have their own baseline yet, so their first check-ins are compared with the facility’s usual range.";
export const ADMISSIONS_PANEL = "new admissions";
export const ADMISSIONS_COMPARISON_PANEL = "the comparison";
export const ADMISSIONS_TABLE_NAME = "New admissions table";

export const ADMISSIONS_COLUMNS = {
  status: "Status",
  resident: "Resident",
  admitted: "Admitted",
  compared: "Compared with facility range",
  ownBaseline: "Own baseline",
  actions: "Actions",
} as const;

export const ADMISSIONS_SHOW_COMPARISON = "Show comparison";
export const admissionsShowComparisonName = (code: string) => `Show comparison for ${code}`;

export const ADMISSIONS_RANGE_PILL = { inRange: "In range", outOfRange: "Out of range" } as const;

/** "Compared with facility range" column text (UX-185). */
export const ADMISSIONS_COMPARISON_TEXT: Record<ComparisonStatus, string> = {
  outside_range: "Outside facility range",
  within_range: "Within facility range",
  not_enough_checkins: "Not enough check-ins yet",
  range_not_available: "Facility range not available yet",
};

/** "<n> of <N>" (UX-186). */
export const admissionsOwnBaseline = (n: number, N: number) => `${n} of ${N}`;

/** UX-194. */
export function admissionsEmpty(profile: string | undefined): string {
  return profile === "test_v0_1"
    ? "No new admissions. The pipeline test data v0.1 has no admission group."
    : "No new admissions.";
}
export const ADMISSIONS_SELECT_PROMPT = "Select a resident to see the comparison.";

export const admissionsComparisonHeading = (code: string) => `${code} compared with facility range`;
export const ADMISSIONS_CHART_CAPTION = "Grey band = usual range across current residents";
export const admissionsTransition = (N: number) =>
  `After ${N} usable check-ins, the resident moves to the resident list and is compared with their own baseline instead.`;
export const admissionsRangeMethod = (n: number, date: string, method: string) =>
  `Range from ${n} current residents, computed ${date} (method: ${method}).`;
export const admissionsChartName = (code: string, outside: number, total: number) =>
  `${code} compared with facility range: ${outside} of ${total} measurements outside the range`;

export const ADMISSIONS_TABLE_TOGGLE = "Show comparison as a table";
export const ADMISSIONS_TABLE_COLUMNS = {
  measurement: "Measurement",
  value: "Resident value",
  range: "Facility range",
  outside: "Outside range",
} as const;
export const ADMISSIONS_OUTSIDE_YES = "▲ Yes";
export const ADMISSIONS_OUTSIDE_NO = "No";
export const ADMISSIONS_NO_VALUE = "—";

/** Plain-language labels of TRD 11 §4.5.4 for the 7 scored measurements (UX-191). */
export const ADMISSIONS_MEASUREMENT_LABEL: Record<string, string> = {
  loudness_dbfs: "Quieter",
  total_phrase_duration_s: "Slower to say the phrase",
  speech_rate_syl_per_s: "Fewer syllables per second",
  articulation_rate_syl_per_s: "Slower while talking",
  number_of_pauses: "More pauses",
  pause_fraction: "More time in pauses",
  voiced_fraction: "Less voiced sound",
};
export const admissionsMeasurementLabel = (key: string) => ADMISSIONS_MEASUREMENT_LABEL[key] ?? key;

/** Values in the comparison table: at most 2 decimals, U+2212 minus. */
export function admissionsValue(x: number | null): string {
  if (x === null) return ADMISSIONS_NO_VALUE;
  const s = String(Number(x.toFixed(2)));
  return s.startsWith("-") ? `−${s.slice(1)}` : s;
}
export const admissionsRange = (low: number | null, high: number | null) =>
  low === null || high === null
    ? ADMISSIONS_NO_VALUE
    : `${admissionsValue(low)}–${admissionsValue(high)}`;

// ---------- Admin (UX-210..UX-219) ----------

export const ADMIN_TITLE = "Admin";
export const ADMIN_TABS = { users: "Users", runs: "Pipeline runs", upload: "Upload data" } as const;
export const ADMIN_TABS_NAME = "Admin sections";

export const ADMIN_ROLE_LABEL: Record<Role, string> = {
  admin: "Admin",
  clinician: "Clinician",
  researcher: "Researcher",
};

// Users
export const ADMIN_USERS_PANEL = "users";
export const ADMIN_USERS_COLUMNS = {
  email: "Email",
  displayName: "Display name",
  role: "Role",
  active: "Active",
  lastSignIn: "Last sign-in",
  actions: "Actions",
} as const;
export const ADMIN_YES = "Yes";
export const ADMIN_NO = "No";
export const ADMIN_NEVER = "Never";
export const ADMIN_NO_VALUE = "—";
export const ADMIN_DEACTIVATE = "Deactivate";
export const ADMIN_REACTIVATE = "Reactivate";
export const ADMIN_CANCEL = "Cancel";
export const adminDeactivateName = (email: string) => `Deactivate ${email}`;
export const adminReactivateName = (email: string) => `Reactivate ${email}`;
export const adminRoleFor = (email: string) => `Role for ${email}`;
export const adminDeactivateConfirm = (email: string) =>
  `Deactivate ${email}? They will not be able to sign in.`;
export const adminUserUpdated = (email: string) => `${email} updated.`;
export const ADMIN_USERS_EMPTY = "No users yet.";

export const ADMIN_ADD_USER = "Add user";
export const ADMIN_ADD_USER_SUBMIT = "Add user";
export const ADMIN_ADDING_USER = "Adding user…";
export const ADMIN_FIELD = {
  email: "Email",
  displayName: "Display name",
  role: "Role",
  password: "Temporary password",
} as const;
export const adminUserAdded = (email: string) => `${email} was added.`;
export const ADMIN_ERROR = {
  emailExists: "A user with this email already exists.",
  passwordPolicy: "This password does not meet the password rules.",
  lastAdmin: "At least one active admin must remain.",
  forbidden: "You cannot change your own role or deactivate yourself.",
  invalid: "Check the highlighted fields.",
  generic: "Could not save. Check your connection and try again.",
  required: "This field is required.",
} as const;

// Pipeline runs
export const ADMIN_RUNS_PANEL = "pipeline runs";
export const ADMIN_RUNS_TABLE_NAME = "Pipeline runs table";
export const ADMIN_RUNS_COLUMNS = {
  started: "Started",
  finished: "Finished",
  trigger: "Trigger",
  profile: "Profile",
  status: "Status",
  asOf: "As of",
  counts: "Counts",
  warnings: "Warnings",
} as const;
export const ADMIN_TRIGGER_LABEL: Record<PipelineRun["trigger"], string> = {
  ingest: "Ingest",
  nightly: "Nightly",
  manual: "Manual",
  test: "Test",
};
export const ADMIN_RUN_STATUS_LABEL: Record<PipelineRun["status"], string> = {
  running: "Running",
  succeeded: "Succeeded",
  failed: "Failed",
};
/** Counts column: the main counts in a fixed order, then any others. */
export const ADMIN_COUNT_LABEL: Record<string, string> = {
  arrivals: "Arrivals",
  usable: "Usable",
  scored: "Scored",
  residents: "Residents",
  alerts_opened: "Alarms opened",
};
export function adminCountsText(counts: Record<string, number>): string {
  const keys = Object.keys(ADMIN_COUNT_LABEL).filter((k) => k in counts);
  if (keys.length === 0) return ADMIN_NO_VALUE;
  return keys.map((k) => `${ADMIN_COUNT_LABEL[k]} ${counts[k]}`).join(" · ");
}
export const ADMIN_RUNS_EMPTY = "No pipeline runs yet.";
export const ADMIN_RUN_NOW = "Run pipeline now";
export const ADMIN_RUN_STARTING = "Starting…";
export const ADMIN_PROFILE = "Profile";
export const adminRunState = (status: PipelineRun["status"]) =>
  status === "running"
    ? "Pipeline run started. Status: Running (refreshed every 5 seconds)."
    : `Pipeline run ${ADMIN_RUN_STATUS_LABEL[status].toLowerCase()}.`;
export const ADMIN_RUN_ERROR = {
  inProgress: "A pipeline run is already in progress. Try again when it has finished.",
  profile: "This profile is not allowed in this environment.",
  generic: "Could not start the pipeline run. Check your connection and try again.",
} as const;
export const adminNightlyMissing = (date: string) => `Nightly run missing for ${date}`;
export const adminLatestRunFailed = (started: string) =>
  `The latest pipeline run failed (started ${started}).`;

// Upload
export const ADMIN_UPLOAD_SYNTHETIC =
  "Only synthetic or test data may be uploaded to this environment.";
export const ADMIN_UPLOAD_FILE = "CSV file (pipeline input format v0.1)";
export const ADMIN_UPLOAD = "Upload";
export const ADMIN_UPLOADING = "Uploading…";
export const ADMIN_UPLOAD_CHOOSE = "Choose a CSV file first.";
export const ADMIN_UPLOAD_PANEL = "the upload result";
export const adminUploadResult = (a: number, r: number, d: number) =>
  `Accepted ${a} · Rejected ${r} · Duplicates ${d}`;
export const ADMIN_REJECTIONS_NAME = "Rejected rows";
export const ADMIN_REJECTIONS_COLUMNS = { row: "Row", errors: "Errors" } as const;
/** UX-217; a trailing full stop of the API detail is dropped to avoid "..". */
export const adminFileNotAccepted = (detail: string) =>
  `The file was not accepted: ${detail.replace(/\.+$/, "")}. Nothing was stored.`;
export const ADMIN_UPLOAD_ERROR = "Could not upload the file. Check your connection and try again.";

// API status (UX-216)
export const adminApiOk = (version: string) => `API status: ok · version ${version}`;
export const adminApiDegraded = (version: string | null) =>
  version
    ? `API status: degraded (database unavailable) · version ${version}`
    : "API status: degraded (database unavailable)";
export const ADMIN_API_UNAVAILABLE = "API status: unavailable";
