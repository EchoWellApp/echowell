// Copy for the chart "Review and notes" section: alarm review panel (TRD 11 §4.17) and staff notes
// (TRD 11 §4.5.5). All strings are exact (TRD 04 FE-013).
import type { NoteType, ReviewOutcome } from "../types";

export const REVIEW_SECTION = "Review and notes";

// Alarm review panel (UX-310..UX-322)
export const reviewHeading = (alarmDate: string) => `Review alert: changed since ${alarmDate}`;
export const REVIEW_EXPLAIN_LEGEND = "Anything that could explain it?";
export const REVIEW_EXPLAIN_HINT =
  "Provisional list — to be confirmed with the clinical team (OQ-25).";
export const REVIEW_OUTCOME_LEGEND = "What did you find?";

/** Outcome labels in the order offered (UX-314, §4.17.3). */
export const REVIEW_OUTCOME_LABEL: Record<ReviewOutcome, string> = {
  no_concern: "Checked on resident, no concern",
  known_cause: "Explained by a known cause",
  referred: "Referred to nurse or provider",
  data_problem: "Looks like a data problem: send to study team",
};
export const REVIEW_OUTCOMES: readonly ReviewOutcome[] = [
  "no_concern",
  "known_cause",
  "referred",
  "data_problem",
];

/** Fallback labels for explanation codes when the configured list does not name them (§4.17.3). */
export const REVIEW_EXPLANATION_LABEL: Record<string, string> = {
  cold_cough_sore_throat: "Cold, cough or sore throat",
  dental_dentures: "Dental problem or dentures out",
  medication_change: "New or changed medication",
  poor_sleep_unusual_day: "Poor sleep or unusual day",
  room_device_moved: "Room or device moved",
};

export const REVIEW_NOTE_LABEL = "Note";
export const REVIEW_NOTE_PLACEHOLDER = "What you saw or did";
export const NOTE_MAX_LENGTH = 2000;
/** "<count> / 2000" (UX-121, UX-315). */
export const noteCharCounter = (count: number) => `${count} / ${NOTE_MAX_LENGTH}`;

export const SAVE_REVIEW = "Save review";
export const remindButton = (hours: number) => `Remind me in ${hours} hours`;
export const CHOOSE_OUTCOME = "Choose what you found.";
export const REVIEW_SAVED = "Review saved.";
export const REVIEW_SAVED_DATA_PROBLEM =
  "Review saved and sent to the study team as a data problem.";
/** Announcement after "Remind me in <h> hours" (UX-317). */
export const reminderAnnouncement = (when: string) =>
  `Reminder set for ${when}. The alarm stays on.`;
/** Line under the buttons while a reminder is active (UX-317). */
export const reminderLine = (when: string) => `Reminder set for ${when}.`;
export const REVIEW_SAVE_FAILED = "Could not save the review. Your choices are kept — try again.";
export const REVIEW_ALERT_CLOSED = "This alarm has closed, so it can no longer be reviewed.";
export const REMINDER_FAILED = "Could not set the reminder. Try again.";

export const PREVIOUS_REVIEWS = "Previous reviews";
export const NOT_REVIEWED_YET = "Not reviewed yet.";
/** "<Mon D, h:mm AM/PM CT> · <display name> · <outcome label>" (UX-320). */
export const reviewLine = (when: string, reviewer: string, outcome: string) =>
  `${when} · ${reviewer} · ${outcome}`;
export const possibleExplanations = (labels: string[]) =>
  `Possible explanations: ${labels.join(", ")}`;

export const REVIEW_OPEN_QUESTIONS =
  "Open questions (OQ-05, OQ-26): Does a saved review reset the change score or turn the alarm off? Who may review? How soon must an alarm be reviewed? Pipeline v0.1 keeps alarms on.";
export const REVIEW_READ_ONLY = "Only clinicians and admins can review alarms.";

/** Panel names for the loading and error copy (UX-200, UX-203). */
export const REVIEW_PANEL_NAME = "the alarm review";
export const REVIEWS_PANEL_NAME = "previous reviews";
export const NOTES_PANEL_NAME = "staff notes";

// Staff notes (UX-120..UX-135)
export const STAFF_NOTES = "Staff notes";
export const NOTE_TYPE_FIELD = "Type of note";
export const NOTE_TYPE_LABEL: Record<NoteType, string> = {
  observation: "Observation",
  action_taken: "Action taken",
  follow_up: "Follow-up",
};
export const NOTE_TYPES: readonly NoteType[] = ["observation", "action_taken", "follow_up"];
export const NEW_NOTE = "New note";
export const NOTE_PLACEHOLDER = "Add a note";
export const NOTE_HINT = "Do not enter names or other identifying details.";
export const ADD_NOTE = "Add note";
export const NOTE_EMPTY = "Write a short note before saving.";
export const NOTE_SAVED = "Note saved.";
export const NOTE_SAVE_FAILED = "Could not save the note. Your text is kept — try again.";
export const NOTES_READ_ONLY = "Only clinicians and admins can add notes.";
export const PREVIOUS_NOTES = "Previous notes";
export const NO_NOTES =
  "No notes yet. Add what you saw or did, for example “Resident has a cold; nurse notified.”";
/** "<Mon D, h:mm AM/PM CT> · <Type> · <display name>" (UX-134). */
export const noteLine = (when: string, type: string, author: string) =>
  `${when} · ${type} · ${author}`;
export const showAllNotes = (count: number) => `Show all notes (${count})`;
export const NOTES_INITIAL = 10;
