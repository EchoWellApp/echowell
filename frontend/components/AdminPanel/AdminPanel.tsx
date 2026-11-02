"use client";
// Admin tabs Users / Pipeline runs / Upload data, run banners and API status line
// (TRD 11 UX-210..UX-219, TRD 04 §4.8, FE-034, FEAT-074).
import { useQuery } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { useRef, useState, type KeyboardEvent } from "react";
import { useAuth } from "@/lib/AuthProvider";
import { formatDateTimeShort, formatLocalDate } from "@/lib/format";
import { queryKeys } from "@/lib/queryKeys";
import { isAdmin } from "@/lib/roles";
import type { PipelineRun } from "@/lib/types";
import {
  ADMIN_API_UNAVAILABLE,
  ADMIN_TABS,
  ADMIN_TABS_NAME,
  adminApiDegraded,
  adminApiOk,
  adminLatestRunFailed,
  adminNightlyMissing,
} from "@/lib/wording";
import * as api from "@/services/api";
import { ApiError } from "@/services/api";
import styles from "./AdminPanel.module.css";
import { newestFirst, nightlyMissingDate } from "./runHelpers";
import { RunsTab } from "./RunsTab";
import { UploadTab } from "./UploadTab";
import { UsersTab } from "./UsersTab";

export type AdminTab = keyof typeof ADMIN_TABS;
export const ADMIN_TAB_ORDER: AdminTab[] = ["users", "runs", "upload"];

export const tabFrom = (value: string | null): AdminTab =>
  ADMIN_TAB_ORDER.includes(value as AdminTab) ? (value as AdminTab) : "users";

function HealthLine() {
  const health = useQuery({ queryKey: queryKeys.health(), queryFn: api.getHealth });
  let text: string | null = null;
  // A 503 body is only readable once getHealth accepts 503 (see the report); until then the
  // ApiError branch below applies and the version is unknown.
  if (health.data && !health.error)
    text =
      health.data.status === "degraded"
        ? adminApiDegraded(health.data.version)
        : adminApiOk(health.data.version);
  else if (health.error instanceof ApiError && health.error.status === 503)
    text = adminApiDegraded(health.data?.version ?? null);
  else if (health.error) text = ADMIN_API_UNAVAILABLE;
  return (
    <p className={`small muted ${styles.footer}`} data-testid="api-status">
      {text}
    </p>
  );
}

function RunBanners({ runs, tz, asOf }: { runs: PipelineRun[]; tz: string; asOf: string | null }) {
  const latest = newestFirst(runs)[0];
  const missing = nightlyMissingDate(runs, Date.now(), tz);
  return (
    <>
      {latest?.status === "failed" && (
        <p className={styles.bannerRed} role="alert">
          {adminLatestRunFailed(formatDateTimeShort(latest.started_at, tz, asOf))}
        </p>
      )}
      {missing && (
        <p className={styles.bannerYellow} role="alert">
          {adminNightlyMissing(formatLocalDate(missing))}
        </p>
      )}
    </>
  );
}

/** No props: the role comes from `useAuth` (TRD 04 §4.8). */
export type AdminPanelProps = Record<string, never>;

export function AdminPanel() {
  const { user } = useAuth();
  const admin = isAdmin(user?.role);
  const router = useRouter();
  const params = useSearchParams();
  const [tab, setTab] = useState<AdminTab>(() => tabFrom(params?.get("tab") ?? null));
  const refs = useRef<Record<AdminTab, HTMLButtonElement | null>>({
    users: null,
    runs: null,
    upload: null,
  });
  const runs = useQuery({
    queryKey: queryKeys.adminRuns(),
    queryFn: () => api.listPipelineRuns(),
    enabled: admin,
  });

  if (!admin) return null;

  function select(next: AdminTab, focus = false) {
    setTab(next);
    router.replace(`/admin?tab=${next}`, { scroll: false });
    if (focus) refs.current[next]?.focus();
  }

  function onKeyDown(event: KeyboardEvent<HTMLButtonElement>) {
    const i = ADMIN_TAB_ORDER.indexOf(tab);
    const n = ADMIN_TAB_ORDER.length;
    const target: Record<string, number> = {
      ArrowRight: (i + 1) % n,
      ArrowLeft: (i - 1 + n) % n,
      Home: 0,
      End: n - 1,
    };
    const next = target[event.key];
    if (next === undefined) return;
    event.preventDefault();
    select(ADMIN_TAB_ORDER[next] as AdminTab, true);
  }

  return (
    <div className="stack">
      {runs.data && (
        <RunBanners
          runs={runs.data.items}
          tz={runs.data.meta.facility_tz}
          asOf={runs.data.meta.as_of}
        />
      )}
      <div className="panel">
        <div role="tablist" aria-label={ADMIN_TABS_NAME} className={styles.tablist}>
          {ADMIN_TAB_ORDER.map((t) => (
            <button
              key={t}
              ref={(el) => {
                refs.current[t] = el;
              }}
              type="button"
              role="tab"
              id={`admin-tab-${t}`}
              aria-controls={`admin-panel-${t}`}
              aria-selected={tab === t}
              tabIndex={tab === t ? 0 : -1}
              className={styles.tab}
              onClick={() => select(t)}
              onKeyDown={onKeyDown}
            >
              {ADMIN_TABS[t]}
            </button>
          ))}
        </div>
        <div
          role="tabpanel"
          id={`admin-panel-${tab}`}
          aria-labelledby={`admin-tab-${tab}`}
          className={`pad stack ${styles.tabpanel}`}
        >
          {tab === "users" && <UsersTab />}
          {tab === "runs" && <RunsTab runs={runs} />}
          {tab === "upload" && <UploadTab />}
        </div>
      </div>
      <HealthLine />
    </div>
  );
}
