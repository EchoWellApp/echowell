"use client";
// Alarm review form: explanation checklist, "What did you find?", note, "Save review" and
// "Remind me in <h> hours" (TRD 11 UX-313..UX-318, UX-324; TRD 04 FE-079, FE-136..FE-138).
// It never calls /alerts/{id}/acknowledge and never changes the shown alarm state (FE-134).
import { useMutation } from "@tanstack/react-query";
import { useEffect, useId, useRef, useState } from "react";
import { formatDateTimeShort } from "@/lib/format";
import type { AlertReviewCreate, ReviewExplanation, ReviewOutcome } from "@/lib/types";
import {
  CHOOSE_OUTCOME,
  NOTE_MAX_LENGTH,
  REMINDER_FAILED,
  REVIEW_ALERT_CLOSED,
  REVIEW_EXPLAIN_HINT,
  REVIEW_EXPLAIN_LEGEND,
  REVIEW_NOTE_LABEL,
  REVIEW_NOTE_PLACEHOLDER,
  REVIEW_OUTCOMES,
  REVIEW_OUTCOME_LABEL,
  REVIEW_OUTCOME_LEGEND,
  REVIEW_SAVED,
  REVIEW_SAVED_DATA_PROBLEM,
  REVIEW_SAVE_FAILED,
  SAVE_REVIEW,
  noteCharCounter,
  reminderAnnouncement,
  reminderLine,
  remindButton,
} from "@/lib/wording";
import * as api from "@/services/api";
import { ApiError } from "@/services/api";
import styles from "./AlertReviewForm.module.css";

export interface AlertReviewFormProps {
  alertId: string;
  snoozeHours: number;
  explanations: ReviewExplanation[];
  snoozedUntil: string | null;
  /** Called after a review or reminder is saved (the caller refetches, FE-086). */
  onSaved(result?: { snoozedUntil?: string | null }): void;
  /** Facility time zone (`meta.facility_tz`) for the reminder time. */
  tz: string;
  asOf?: string | null;
}

/** Maps `ApiError.errors[].field` ("body.note", "outcome", "explanations.0") to its form field. */
export function apiFieldErrors(error: unknown): Record<string, string> {
  const out: Record<string, string> = {};
  if (!(error instanceof ApiError)) return out;
  for (const e of error.errors) {
    const parts = String(e.field ?? "")
      .split(".")
      .filter((p) => p !== "" && !/^\d+$/.test(p));
    // Pydantic locations start with "body" ("body.note"); a bare "body" is the note field itself.
    const key = parts[0] === "body" && parts.length > 1 ? parts[1] : parts[0];
    if (key && !(key in out)) out[key] = e.message;
  }
  return out;
}

/** True while `until` is in the future; flips to false when it passes, without a request. */
export function useActiveUntil(until: string | null): boolean {
  const [active, setActive] = useState(() => !!until && Date.parse(until) > Date.now());
  useEffect(() => {
    if (!until) {
      setActive(false);
      return;
    }
    const ms = Date.parse(until) - Date.now();
    if (!(ms > 0)) {
      setActive(false);
      return;
    }
    setActive(true);
    const timer = setTimeout(() => setActive(false), ms);
    return () => clearTimeout(timer);
  }, [until]);
  return active;
}

/** "Reminder set for <Mon D, h:mm AM/PM CT>." while the reminder is active (UX-317). */
export function ReminderLine(props: { until: string | null; tz: string; asOf?: string | null }) {
  const active = useActiveUntil(props.until);
  if (!active || !props.until) return null;
  return (
    <p className={styles.reminder}>
      {reminderLine(formatDateTimeShort(props.until, props.tz, props.asOf ?? null))}
    </p>
  );
}

export function AlertReviewForm({
  alertId,
  snoozeHours,
  explanations,
  snoozedUntil,
  onSaved,
  tz,
  asOf = null,
}: AlertReviewFormProps) {
  const id = useId();
  const firstRadio = useRef<HTMLInputElement>(null);
  const [checked, setChecked] = useState<string[]>([]);
  const [outcome, setOutcome] = useState<ReviewOutcome | null>(null);
  const [note, setNote] = useState("");
  const [missingOutcome, setMissingOutcome] = useState(false);
  const [status, setStatus] = useState("");
  const [localSnooze, setLocalSnooze] = useState<string | null>(null);

  const review = useMutation({
    mutationFn: (input: AlertReviewCreate) => api.createAlertReview(alertId, input),
    onMutate: () => setStatus(""),
    onSuccess: (_saved, input) => {
      setChecked([]);
      setOutcome(null);
      setNote("");
      setStatus(input.outcome === "data_problem" ? REVIEW_SAVED_DATA_PROBLEM : REVIEW_SAVED);
      onSaved();
    },
  });
  const snooze = useMutation({
    mutationFn: () => api.snoozeAlert(alertId, {}),
    onMutate: () => setStatus(""),
    onSuccess: (alarm) => {
      const until = alarm?.snoozed_until ?? null;
      setLocalSnooze(until);
      if (until) setStatus(reminderAnnouncement(formatDateTimeShort(until, tz, asOf)));
      onSaved({ snoozedUntil: until });
    },
  });

  const fieldErrors = apiFieldErrors(review.error);
  const closed = review.error instanceof ApiError && review.error.code === "ALERT_CLOSED";
  const busy = review.isPending || snooze.isPending;

  function save() {
    if (busy) return;
    if (!outcome) {
      setMissingOutcome(true);
      firstRadio.current?.focus();
      return;
    }
    const input: AlertReviewCreate = { explanations: checked, outcome };
    if (note.trim() !== "") input.note = note;
    review.mutate(input);
  }

  const ids = {
    explain: `${id}-explain`,
    explainHint: `${id}-explain-hint`,
    explainError: `${id}-explain-error`,
    outcome: `${id}-outcome`,
    outcomeError: `${id}-outcome-error`,
    note: `${id}-note`,
    noteCounter: `${id}-note-counter`,
    noteError: `${id}-note-error`,
  };
  const outcomeMessage = missingOutcome && !outcome ? CHOOSE_OUTCOME : fieldErrors.outcome;
  const reminderUntil = snoozedUntil ?? localSnooze;

  return (
    <form
      className={styles.form}
      noValidate
      onSubmit={(e) => {
        e.preventDefault();
        save();
      }}
    >
      <fieldset
        className={styles.fieldset}
        aria-describedby={
          [ids.explainHint, fieldErrors.explanations ? ids.explainError : null]
            .filter(Boolean)
            .join(" ") || undefined
        }
      >
        <legend className={styles.legend}>{REVIEW_EXPLAIN_LEGEND}</legend>
        {explanations.map((e) => (
          <label key={e.code} className={styles.choice}>
            <input
              type="checkbox"
              value={e.code}
              checked={checked.includes(e.code)}
              onChange={(ev) =>
                setChecked((prev) =>
                  ev.target.checked ? [...prev, e.code] : prev.filter((c) => c !== e.code),
                )
              }
            />
            {e.label}
          </label>
        ))}
        <p id={ids.explainHint} className={styles.hint}>
          {REVIEW_EXPLAIN_HINT}
        </p>
        {fieldErrors.explanations && (
          <p id={ids.explainError} className={styles.error}>
            {fieldErrors.explanations}
          </p>
        )}
      </fieldset>

      <fieldset
        className={styles.fieldset}
        aria-describedby={outcomeMessage ? ids.outcomeError : undefined}
        aria-invalid={outcomeMessage ? true : undefined}
      >
        <legend className={styles.legend}>{REVIEW_OUTCOME_LEGEND}</legend>
        {REVIEW_OUTCOMES.map((o, i) => (
          <label key={o} className={styles.choice}>
            <input
              ref={i === 0 ? firstRadio : undefined}
              type="radio"
              name={ids.outcome}
              value={o}
              checked={outcome === o}
              aria-describedby={outcomeMessage ? ids.outcomeError : undefined}
              onChange={() => {
                setOutcome(o);
                setMissingOutcome(false);
              }}
            />
            {REVIEW_OUTCOME_LABEL[o]}
          </label>
        ))}
        {outcomeMessage && (
          <p id={ids.outcomeError} className={styles.error} role="alert">
            {outcomeMessage}
          </p>
        )}
      </fieldset>

      <div className={styles.field}>
        <label htmlFor={ids.note} className={styles.noteLabel}>
          {REVIEW_NOTE_LABEL}
        </label>
        <textarea
          id={ids.note}
          className={styles.textarea}
          rows={3}
          maxLength={NOTE_MAX_LENGTH}
          placeholder={REVIEW_NOTE_PLACEHOLDER}
          value={note}
          aria-describedby={[ids.noteCounter, fieldErrors.note ? ids.noteError : null]
            .filter(Boolean)
            .join(" ")}
          onChange={(e) => setNote(e.target.value)}
        />
        {fieldErrors.note && (
          <p id={ids.noteError} className={styles.error}>
            {fieldErrors.note}
          </p>
        )}
        <p id={ids.noteCounter} className={styles.counter}>
          {noteCharCounter(note.length)}
        </p>
      </div>

      {review.isError && Object.keys(fieldErrors).length === 0 && (
        <p className={styles.error} role="alert">
          {closed ? REVIEW_ALERT_CLOSED : REVIEW_SAVE_FAILED}
        </p>
      )}
      {snooze.isError && (
        <p className={styles.error} role="alert">
          {REMINDER_FAILED}
        </p>
      )}
      <div className={styles.buttons}>
        <button type="submit" className="btn" aria-disabled={busy}>
          {SAVE_REVIEW}
        </button>
        <button
          type="button"
          className="btn btn-secondary"
          aria-disabled={busy}
          onClick={() => {
            if (!busy) snooze.mutate();
          }}
        >
          {remindButton(snoozeHours)}
        </button>
      </div>
      <ReminderLine until={reminderUntil} tz={tz} asOf={asOf} />
      <p className="visually-hidden" role="status" aria-live="polite">
        {status}
      </p>
    </form>
  );
}
