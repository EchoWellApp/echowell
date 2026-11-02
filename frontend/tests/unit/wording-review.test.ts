// req: FE-013, UX-121, UX-124, UX-130, UX-131, UX-132, UX-134, UX-135, UX-310, UX-313..UX-322, UX-430..UX-432, §4.17.3
import * as w from "@/lib/wording";

describe("review and notes wording", () => {
  it("has the exact alarm review copy", () => {
    expect(w.reviewHeading("Oct 21")).toBe("Review alert: changed since Oct 21");
    expect(w.REVIEW_EXPLAIN_LEGEND).toBe("Anything that could explain it?");
    expect(w.REVIEW_EXPLAIN_HINT).toBe(
      "Provisional list — to be confirmed with the clinical team (OQ-25).",
    );
    expect(w.REVIEW_OUTCOME_LEGEND).toBe("What did you find?");
    expect(w.REVIEW_OUTCOMES.map((o) => w.REVIEW_OUTCOME_LABEL[o])).toEqual([
      "Checked on resident, no concern",
      "Explained by a known cause",
      "Referred to nurse or provider",
      "Looks like a data problem: send to study team",
    ]);
    expect(Object.keys(w.REVIEW_EXPLANATION_LABEL)).toEqual([
      "cold_cough_sore_throat",
      "dental_dentures",
      "medication_change",
      "poor_sleep_unusual_day",
      "room_device_moved",
    ]);
    expect(w.REVIEW_NOTE_LABEL).toBe("Note");
    expect(w.REVIEW_NOTE_PLACEHOLDER).toBe("What you saw or did");
    expect(w.noteCharCounter(12)).toBe("12 / 2000");
    expect(w.SAVE_REVIEW).toBe("Save review");
    expect(w.remindButton(24)).toBe("Remind me in 24 hours");
    expect(w.CHOOSE_OUTCOME).toBe("Choose what you found.");
    expect(w.REVIEW_SAVED).toBe("Review saved.");
    expect(w.REVIEW_SAVED_DATA_PROBLEM).toBe(
      "Review saved and sent to the study team as a data problem.",
    );
    expect(w.reminderAnnouncement("Oct 31, 3:05 PM CT")).toBe(
      "Reminder set for Oct 31, 3:05 PM CT. The alarm stays on.",
    );
    expect(w.reminderLine("Oct 31, 3:05 PM CT")).toBe("Reminder set for Oct 31, 3:05 PM CT.");
    expect(w.PREVIOUS_REVIEWS).toBe("Previous reviews");
    expect(w.NOT_REVIEWED_YET).toBe("Not reviewed yet.");
    expect(
      w.reviewLine("Oct 30, 2:28 PM CT", "Clinician User", "Referred to nurse or provider"),
    ).toBe("Oct 30, 2:28 PM CT · Clinician User · Referred to nurse or provider");
    expect(w.possibleExplanations(["A", "B"])).toBe("Possible explanations: A, B");
    expect(w.REVIEW_OPEN_QUESTIONS).toBe(
      "Open questions (OQ-05, OQ-26): Does a saved review reset the change score or turn the alarm off? Who may review? How soon must an alarm be reviewed? Pipeline v0.1 keeps alarms on.",
    );
    expect(w.REVIEW_READ_ONLY).toBe("Only clinicians and admins can review alarms.");
  });

  it("has the exact staff notes copy", () => {
    expect(w.STAFF_NOTES).toBe("Staff notes");
    expect(w.NOTE_TYPE_FIELD).toBe("Type of note");
    expect(w.NOTE_TYPES.map((t) => w.NOTE_TYPE_LABEL[t])).toEqual([
      "Observation",
      "Action taken",
      "Follow-up",
    ]);
    expect(w.NEW_NOTE).toBe("New note");
    expect(w.NOTE_PLACEHOLDER).toBe("Add a note");
    expect(w.NOTE_HINT).toBe("Do not enter names or other identifying details.");
    expect(w.ADD_NOTE).toBe("Add note");
    expect(w.NOTE_EMPTY).toBe("Write a short note before saving.");
    expect(w.NOTE_SAVED).toBe("Note saved.");
    expect(w.NOTE_SAVE_FAILED).toBe("Could not save the note. Your text is kept — try again.");
    expect(w.NOTES_READ_ONLY).toBe("Only clinicians and admins can add notes.");
    expect(w.PREVIOUS_NOTES).toBe("Previous notes");
    expect(w.NO_NOTES).toBe(
      "No notes yet. Add what you saw or did, for example “Resident has a cold; nurse notified.”",
    );
    expect(w.noteLine("Oct 30, 3:05 PM CT", "Observation", "Clinician User")).toBe(
      "Oct 30, 3:05 PM CT · Observation · Clinician User",
    );
    expect(w.showAllNotes(12)).toBe("Show all notes (12)");
    expect(w.NOTES_INITIAL).toBe(10);
    expect(w.NOTE_MAX_LENGTH).toBe(2000);
  });

  it("has the exact device section copy", () => {
    expect(w.deviceHeading("D02")).toBe("Device D02");
    expect(`${w.DEVICE_ONLINE.glyph} ${w.DEVICE_ONLINE.text}`).toBe("● Online");
    expect(`${w.DEVICE_NO_UPLOAD.glyph} ${w.DEVICE_NO_UPLOAD.text}`).toBe("○ No upload today");
    expect(Object.values(w.DEVICE_FACT)).toEqual(["Status", "Last upload", "Firmware", "Used by"]);
    expect(w.DEVICE_THIS_RESIDENT_ONLY).toBe("This resident only");
    expect(w.deviceSharedWith(["R02"])).toBe("Shared with R02");
    expect(w.deviceJoinCodes([])).toBe("");
    expect(w.deviceJoinCodes(["R01", "R02", "R03"])).toBe("R01, R02 and R03");
    expect(w.DEVICE_HISTORY).toBe("History");
    expect(w.deviceSilentAllDay(["R02", "R03"])).toBe("Silent all day. Affected R02 and R03.");
    expect(w.deviceReplaced("D07", "D07B")).toBe("Replaced D07 with D07B. Baseline restarted.");
    expect(w.deviceFirmwareChanged("fw-1.0.0", "fw-1.1.0")).toBe(
      "Firmware changed (fw-1.0.0 to fw-1.1.0). Baseline restarted.",
    );
    expect(w.DEVICE_NO_PROBLEMS).toBe("No problems in the last 30 days.");
    expect(w.DEVICE_CAPTION).toBe(
      "Audio never leaves the device. Only voice measurements are uploaded.",
    );
  });
});
