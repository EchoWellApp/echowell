"use client";
// "Staff notes" panel: note form (clinician, admin) and "Previous notes" (TRD 11 UX-120..UX-135;
// TRD 04 FE-085, FE-089, FE-130, FE-132, FE-133, FE-135).
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useId, useState } from "react";
import { QueryState } from "@/components/SectionState/SectionState";
import { NotesList } from "@/components/NotesList/NotesList";
import { apiFieldErrors } from "@/components/AlertReviewForm/AlertReviewForm";
import { queryKeys } from "@/lib/queryKeys";
import type { NoteType, StaffNoteCreate } from "@/lib/types";
import {
  ADD_NOTE,
  NEW_NOTE,
  NOTES_PANEL_NAME,
  NOTES_READ_ONLY,
  NOTE_EMPTY,
  NOTE_HINT,
  NOTE_MAX_LENGTH,
  NOTE_PLACEHOLDER,
  NOTE_SAVED,
  NOTE_SAVE_FAILED,
  NOTE_TYPES,
  NOTE_TYPE_FIELD,
  NOTE_TYPE_LABEL,
  STAFF_NOTES,
  noteCharCounter,
} from "@/lib/wording";
import * as api from "@/services/api";
import styles from "./StaffNotes.module.css";

export interface StaffNotesProps {
  residentCode: string;
  openAlertId: string | null;
  canWrite: boolean;
}

export function StaffNotes({ residentCode, openAlertId, canWrite }: StaffNotesProps) {
  const id = useId();
  const queryClient = useQueryClient();
  const notes = useQuery({
    queryKey: queryKeys.notes(residentCode),
    queryFn: () => api.getNotes(residentCode),
  });
  const [noteType, setNoteType] = useState<NoteType>("observation");
  const [body, setBody] = useState("");
  const [emptyTried, setEmptyTried] = useState(false);
  const [status, setStatus] = useState("");

  const save = useMutation({
    mutationFn: (input: StaffNoteCreate) => api.createNote(residentCode, input),
    onMutate: () => setStatus(""),
    onSuccess: () => {
      setBody("");
      setStatus(NOTE_SAVED);
      // FE-085: the resident prefix covers notes and check-ins.
      void queryClient.invalidateQueries({ queryKey: queryKeys.resident(residentCode) });
      void queryClient.invalidateQueries({ queryKey: queryKeys.residents() });
      void queryClient.invalidateQueries({ queryKey: queryKeys.alertsAll() });
    },
  });

  const trimmed = body.trim();
  const tooLong = body.length > NOTE_MAX_LENGTH;
  const blocked = trimmed === "" || tooLong || save.isPending;
  const fieldErrors = apiFieldErrors(save.error);

  function submit() {
    if (trimmed === "") {
      setEmptyTried(true);
      return;
    }
    if (blocked) return;
    const input: StaffNoteCreate = { note_type: noteType, body };
    if (openAlertId) input.alert_id = openAlertId;
    save.mutate(input);
  }

  const ids = {
    heading: `${id}-heading`,
    type: `${id}-type`,
    typeError: `${id}-type-error`,
    body: `${id}-body`,
    hint: `${id}-hint`,
    counter: `${id}-counter`,
    empty: `${id}-empty`,
    bodyError: `${id}-body-error`,
  };
  const bodyDescribedBy = [
    ids.hint,
    ids.counter,
    emptyTried && trimmed === "" ? ids.empty : null,
    fieldErrors.body ? ids.bodyError : null,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <section className="panel pad stack" aria-labelledby={ids.heading}>
      <h2 id={ids.heading}>{STAFF_NOTES}</h2>
      {canWrite ? (
        <form
          className={styles.form}
          noValidate
          onSubmit={(e) => {
            e.preventDefault();
            submit();
          }}
        >
          <div className={styles.field}>
            <label htmlFor={ids.type} className={styles.label}>
              {NOTE_TYPE_FIELD}
            </label>
            <select
              id={ids.type}
              className={styles.select}
              value={noteType}
              aria-describedby={fieldErrors.note_type ? ids.typeError : undefined}
              onChange={(e) => setNoteType(e.target.value as NoteType)}
            >
              {NOTE_TYPES.map((t) => (
                <option key={t} value={t}>
                  {NOTE_TYPE_LABEL[t]}
                </option>
              ))}
            </select>
            {fieldErrors.note_type && (
              <p id={ids.typeError} className={styles.error}>
                {fieldErrors.note_type}
              </p>
            )}
          </div>
          <div className={styles.field}>
            <label htmlFor={ids.body} className="visually-hidden">
              {NEW_NOTE}
            </label>
            <textarea
              id={ids.body}
              className={styles.textarea}
              rows={3}
              placeholder={NOTE_PLACEHOLDER}
              value={body}
              aria-describedby={bodyDescribedBy}
              aria-invalid={tooLong || (emptyTried && trimmed === "") || !!fieldErrors.body}
              onChange={(e) => {
                setBody(e.target.value);
                if (e.target.value.trim() !== "") setEmptyTried(false);
              }}
            />
            {emptyTried && trimmed === "" && (
              <p id={ids.empty} className={styles.error} role="alert">
                {NOTE_EMPTY}
              </p>
            )}
            {fieldErrors.body && (
              <p id={ids.bodyError} className={styles.error}>
                {fieldErrors.body}
              </p>
            )}
            <p id={ids.hint} className={styles.hint}>
              {NOTE_HINT}
            </p>
            <p id={ids.counter} className={tooLong ? styles.counterOver : styles.counter}>
              {noteCharCounter(body.length)}
            </p>
          </div>
          {save.isError && (
            <p className={styles.error} role="alert">
              {NOTE_SAVE_FAILED}
            </p>
          )}
          <div>
            <button type="submit" className="btn btn-secondary" aria-disabled={blocked}>
              {ADD_NOTE}
            </button>
          </div>
          <p className="visually-hidden" role="status" aria-live="polite">
            {status}
          </p>
        </form>
      ) : (
        <p className="muted">{NOTES_READ_ONLY}</p>
      )}
      {notes.data ? (
        <NotesList
          notes={notes.data.items}
          tz={notes.data.meta.facility_tz}
          asOf={notes.data.meta.as_of}
        />
      ) : (
        <QueryState
          panel={NOTES_PANEL_NAME}
          isPending={notes.isPending}
          error={notes.error}
          refetch={notes.refetch}
        />
      )}
    </section>
  );
}
