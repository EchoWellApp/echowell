"use client";
// "Previous notes": the resident's staff notes newest first, 10 at first (TRD 11 UX-134, UX-135).
import { useState } from "react";
import { formatDateTimeShort } from "@/lib/format";
import type { StaffNote } from "@/lib/types";
import {
  NOTES_INITIAL,
  NOTE_TYPE_LABEL,
  NO_NOTES,
  PREVIOUS_NOTES,
  noteLine,
  showAllNotes,
} from "@/lib/wording";
import styles from "./NotesList.module.css";

export interface NotesListProps {
  notes: StaffNote[];
  tz: string;
  /** As-of instant: the year is added to dates of another year (UX-003). */
  asOf?: string | null;
}

export function NotesList({ notes, tz, asOf = null }: NotesListProps) {
  const [showAll, setShowAll] = useState(false);
  if (notes.length === 0) return <p className="muted">{NO_NOTES}</p>;
  const sorted = [...notes].sort((a, b) => b.created_at.localeCompare(a.created_at));
  const shown = showAll ? sorted : sorted.slice(0, NOTES_INITIAL);
  return (
    <div className={styles.notes}>
      <h3>{PREVIOUS_NOTES}</h3>
      <ul className={styles.list}>
        {shown.map((n) => (
          <li key={n.id} className={styles.item}>
            <p className={styles.line}>
              {noteLine(
                formatDateTimeShort(n.created_at, tz, asOf),
                NOTE_TYPE_LABEL[n.note_type] ?? n.note_type,
                n.author.display_name,
              )}
            </p>
            <p className={styles.body}>{n.body}</p>
          </li>
        ))}
      </ul>
      {!showAll && sorted.length > NOTES_INITIAL && (
        <div>
          <button type="button" className="btn btn-secondary" onClick={() => setShowAll(true)}>
            {showAllNotes(sorted.length)}
          </button>
        </div>
      )}
    </div>
  );
}
