"use client";
// Pipeline runs tab: latest 50 runs and "Run pipeline now" with 5-second polling
// (TRD 11 UX-212, TRD 17 LOG-112, FEAT-074-FR-06, FR-07).
import { useMutation, useQuery, useQueryClient, type UseQueryResult } from "@tanstack/react-query";
import { useEffect, useState, type FormEvent } from "react";
import { QueryState } from "@/components/SectionState/SectionState";
import { formatAsOf, formatDateTimeShort } from "@/lib/format";
import { queryKeys } from "@/lib/queryKeys";
import type { PipelineRun, PipelineRunList } from "@/lib/types";
import {
  ADMIN_NO_VALUE,
  ADMIN_PROFILE,
  ADMIN_RUN_ERROR,
  ADMIN_RUN_NOW,
  ADMIN_RUN_STARTING,
  ADMIN_RUN_STATUS_LABEL,
  ADMIN_RUNS_COLUMNS,
  ADMIN_RUNS_EMPTY,
  ADMIN_RUNS_PANEL,
  ADMIN_RUNS_TABLE_NAME,
  ADMIN_TRIGGER_LABEL,
  adminCountsText,
  adminRunState,
} from "@/lib/wording";
import * as api from "@/services/api";
import { ApiError } from "@/services/api";
import { newestFirst } from "./runHelpers";
import styles from "./AdminPanel.module.css";

export const POLL_MS = 5_000;

/** Poll a started run every 5 s until it is "succeeded" or "failed" (UX-212). */
export const runPollInterval = (run: PipelineRun | undefined): number | false =>
  !run || run.status === "running" ? POLL_MS : false;

function runErrorText(e: unknown): string {
  if (e instanceof ApiError) {
    if (e.code === "PIPELINE_RUN_IN_PROGRESS") return ADMIN_RUN_ERROR.inProgress;
    if (e.code === "PROFILE_NOT_ALLOWED") return ADMIN_RUN_ERROR.profile;
  }
  return ADMIN_RUN_ERROR.generic;
}

function StartedRun({ id }: { id: string }) {
  const queryClient = useQueryClient();
  const run = useQuery({
    queryKey: queryKeys.adminRun(id),
    queryFn: () => api.getPipelineRun(id),
    refetchInterval: (q) => runPollInterval(q.state.data),
  });
  const status = run.data?.status;
  useEffect(() => {
    if (status === "succeeded" || status === "failed")
      void queryClient.invalidateQueries({ queryKey: queryKeys.adminRuns() });
  }, [status, queryClient]);
  return <>{status ? adminRunState(status) : adminRunState("running")}</>;
}

export interface RunsTabProps {
  runs: UseQueryResult<PipelineRunList>;
}

export function RunsTab({ runs }: RunsTabProps) {
  const queryClient = useQueryClient();
  const meta = runs.data?.meta;
  const profile = meta?.pipeline_profile;
  const [started, setStarted] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const trigger = useMutation({
    mutationFn: api.triggerPipelineRun,
    onSuccess: (accepted) => {
      setError(null);
      setStarted(accepted.pipeline_run_id);
      void queryClient.invalidateQueries({ queryKey: queryKeys.adminRuns() });
    },
    onError: (e) => setError(runErrorText(e)),
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!profile) return;
    trigger.mutate({ scope: "all", profile });
  }

  return (
    <div className="stack">
      <form className={styles.inline} onSubmit={onSubmit}>
        <div className={styles.field}>
          <label htmlFor="run-profile">{ADMIN_PROFILE}</label>
          <select
            id="run-profile"
            className={styles.input}
            value={profile ?? ""}
            disabled={!profile}
            onChange={() => undefined}
          >
            {profile && <option value={profile}>{profile}</option>}
          </select>
        </div>
        <button type="submit" className="btn" disabled={!profile || trigger.isPending}>
          {trigger.isPending ? ADMIN_RUN_STARTING : ADMIN_RUN_NOW}
        </button>
      </form>
      <p aria-live="polite" className={styles.status}>
        {started && <StartedRun id={started} />}
      </p>
      <p role="alert" className={styles.formError}>
        {error}
      </p>
      <QueryState
        panel={ADMIN_RUNS_PANEL}
        isPending={runs.isPending}
        error={runs.error}
        refetch={runs.refetch}
      />
      {runs.data && runs.data.items.length === 0 && (
        <p className="small muted">{ADMIN_RUNS_EMPTY}</p>
      )}
      {runs.data && meta && runs.data.items.length > 0 && (
        // eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex -- scroll container (UX-243)
        <div className="scroll-x" tabIndex={0} role="region" aria-label={ADMIN_RUNS_TABLE_NAME}>
          <table className={styles.table}>
            <thead>
              <tr>
                <th scope="col">{ADMIN_RUNS_COLUMNS.started}</th>
                <th scope="col">{ADMIN_RUNS_COLUMNS.finished}</th>
                <th scope="col">{ADMIN_RUNS_COLUMNS.trigger}</th>
                <th scope="col">{ADMIN_RUNS_COLUMNS.profile}</th>
                <th scope="col">{ADMIN_RUNS_COLUMNS.status}</th>
                <th scope="col">{ADMIN_RUNS_COLUMNS.asOf}</th>
                <th scope="col">{ADMIN_RUNS_COLUMNS.counts}</th>
                <th scope="col">{ADMIN_RUNS_COLUMNS.warnings}</th>
              </tr>
            </thead>
            <tbody>
              {newestFirst(runs.data.items).map((r) => (
                <tr key={r.id}>
                  <td>{formatDateTimeShort(r.started_at, meta.facility_tz, meta.as_of)}</td>
                  <td>
                    {r.finished_at
                      ? formatDateTimeShort(r.finished_at, meta.facility_tz, meta.as_of)
                      : ADMIN_NO_VALUE}
                  </td>
                  <td>{ADMIN_TRIGGER_LABEL[r.trigger]}</td>
                  <td>{r.config_profile}</td>
                  <td>{ADMIN_RUN_STATUS_LABEL[r.status]}</td>
                  <td>{formatAsOf(r.as_of, meta.facility_tz)}</td>
                  <td>{adminCountsText(r.counts)}</td>
                  <td>{r.warnings.length}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
