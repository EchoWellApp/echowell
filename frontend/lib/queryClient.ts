// QueryClient defaults (TRD 04 FE-080, FE-045: memory only, never persisted).
import { QueryClient } from "@tanstack/react-query";
import { ApiError } from "@/services/api";

export function shouldRetry(failureCount: number, error: unknown): boolean {
  if (failureCount >= 2) return false;
  return error instanceof ApiError && (error.status === 0 || error.status >= 500);
}

export const retryDelay = (attempt: number) => 1000 * 2 ** attempt;

export function makeQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60_000,
        gcTime: 300_000,
        refetchOnWindowFocus: true,
        retry: shouldRetry,
        retryDelay,
      },
      mutations: { retry: false },
    },
  });
}

/** Refresh interval of the list, nav count, devices and chart queries (FE-081). */
export const REFRESH_MS = 300_000;
