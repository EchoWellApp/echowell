"use client";
// Upload data tab: CSV upload, batch result, rejections and whole-file rejection
// (TRD 11 UX-213, UX-214, UX-217; TRD 04 FE-072, FE-079; FEAT-074-FR-09..FR-11).
import { useMutation, useQuery } from "@tanstack/react-query";
import { useRef, useState, type FormEvent } from "react";
import { QueryState } from "@/components/SectionState/SectionState";
import { queryKeys } from "@/lib/queryKeys";
import type { IngestBatchAccepted } from "@/lib/types";
import {
  ADMIN_REJECTIONS_COLUMNS,
  ADMIN_REJECTIONS_NAME,
  ADMIN_UPLOAD,
  ADMIN_UPLOAD_CHOOSE,
  ADMIN_UPLOAD_ERROR,
  ADMIN_UPLOAD_FILE,
  ADMIN_UPLOAD_PANEL,
  ADMIN_UPLOAD_SYNTHETIC,
  ADMIN_UPLOADING,
  adminFileNotAccepted,
  adminUploadResult,
  referenceText,
} from "@/lib/wording";
import * as api from "@/services/api";
import { ApiError } from "@/services/api";
import styles from "./AdminPanel.module.css";

function BatchResult({ accepted }: { accepted: IngestBatchAccepted }) {
  const batch = useQuery({
    queryKey: queryKeys.adminBatch(accepted.ingest_batch_id),
    queryFn: () => api.getIngestBatch(accepted.ingest_batch_id),
  });
  const b = batch.data;
  const summary = b
    ? adminUploadResult(b.accepted_count, b.rejected_count, b.duplicate_count)
    : adminUploadResult(accepted.accepted, accepted.rejected, accepted.duplicates);
  return (
    <div className="stack">
      <p className={styles.status}>
        <strong>{summary}</strong>
      </p>
      <QueryState
        panel={ADMIN_UPLOAD_PANEL}
        isPending={batch.isPending}
        error={batch.error}
        refetch={batch.refetch}
      />
      {b && b.rejections.length > 0 && (
        <table className={styles.table} aria-label={ADMIN_REJECTIONS_NAME}>
          <thead>
            <tr>
              <th scope="col">{ADMIN_REJECTIONS_COLUMNS.row}</th>
              <th scope="col">{ADMIN_REJECTIONS_COLUMNS.errors}</th>
            </tr>
          </thead>
          <tbody>
            {b.rejections.map((r) => (
              <tr key={r.row_number}>
                <td>{r.row_number}</td>
                <td>{r.errors.map((e) => e.message).join("; ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function UploadError({ error }: { error: unknown }) {
  const whole =
    error instanceof ApiError && error.status >= 400 && error.status < 500 && error.status !== 401;
  if (whole) {
    return (
      <div role="alert" className="stack">
        <p>{adminFileNotAccepted(error.detail || error.title)}</p>
        {error.errors.length > 0 && (
          <ul>
            {error.errors.map((e, i) => (
              <li key={`${e.field}-${i}`}>{e.message}</li>
            ))}
          </ul>
        )}
      </div>
    );
  }
  const id = error instanceof ApiError ? error.requestId : null;
  return (
    <div role="alert" className="stack">
      <p>{ADMIN_UPLOAD_ERROR}</p>
      {id && <p className="caption">{referenceText(id)}</p>}
    </div>
  );
}

export function UploadTab() {
  const fileRef = useRef<HTMLInputElement>(null);
  const [missing, setMissing] = useState(false);
  const upload = useMutation({ mutationFn: api.uploadIngestCsv });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    const file = fileRef.current?.files?.[0];
    if (!file) {
      setMissing(true);
      return;
    }
    setMissing(false);
    upload.mutate(file);
  }

  return (
    <div className="stack">
      <p className={styles.bannerYellow}>{ADMIN_UPLOAD_SYNTHETIC}</p>
      <form className={styles.inline} onSubmit={onSubmit} noValidate>
        <div className={styles.field}>
          <label htmlFor="upload-file">{ADMIN_UPLOAD_FILE}</label>
          <input
            id="upload-file"
            ref={fileRef}
            type="file"
            accept=".csv,text/csv"
            className={styles.input}
            aria-invalid={missing || undefined}
            aria-describedby={missing ? "upload-file-error" : undefined}
            onChange={() => setMissing(false)}
          />
          {missing && (
            <p id="upload-file-error" className={styles.fieldError}>
              {ADMIN_UPLOAD_CHOOSE}
            </p>
          )}
        </div>
        <button type="submit" className="btn" disabled={upload.isPending}>
          {upload.isPending ? ADMIN_UPLOADING : ADMIN_UPLOAD}
        </button>
      </form>
      <div aria-live="polite">
        {upload.data && <BatchResult accepted={upload.data} />}
        {upload.error && <UploadError error={upload.error} />}
      </div>
    </div>
  );
}
