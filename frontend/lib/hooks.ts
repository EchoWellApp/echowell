"use client";
// Shared queries and page helpers.
import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";
import * as api from "@/services/api";
import { pageTitle } from "./wording";
import { queryKeys } from "./queryKeys";
import { REFRESH_MS } from "./queryClient";

/** GET /config/ui: meta for the app bar and data bar, one query per session (FE-088). */
export function useUiConfig(enabled = true) {
  return useQuery({
    queryKey: queryKeys.uiConfig(),
    queryFn: api.getUiConfig,
    staleTime: Infinity,
    enabled,
  });
}

/** Open change alarms for the nav badge (FE-036). */
export function useOpenAlarmCount(enabled = true) {
  return useQuery({
    queryKey: queryKeys.alerts({ status: "open" }),
    queryFn: () => api.getAlerts({ status: "open" }),
    refetchInterval: REFRESH_MS,
    enabled,
  });
}

/** Sets "<Page> – EchoWell" (FE-032). */
export function useDocumentTitle(page: string): void {
  useEffect(() => {
    document.title = pageTitle(page);
  }, [page]);
}
