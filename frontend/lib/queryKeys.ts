// Query-key factory (TRD 04 §4.7).
export const queryKeys = {
  me: () => ["me"] as const,
  uiConfig: () => ["config", "ui"] as const,
  residents: () => ["residents"] as const,
  resident: (code: string) => ["resident", code] as const,
  checkins: (code: string) => ["resident", code, "checkins"] as const,
  features: (code: string) => ["resident", code, "features"] as const,
  scores: (code: string, epoch: number | null = null) =>
    ["resident", code, "scores", epoch] as const,
  notes: (code: string) => ["resident", code, "notes"] as const,
  alerts: (filter: { status?: string; residentCode?: string } = {}) =>
    [
      "alerts",
      { status: filter.status ?? null, residentCode: filter.residentCode ?? null },
    ] as const,
  alertsAll: () => ["alerts"] as const,
  dataAlerts: (status: string | null = null) => ["data-alerts", { status }] as const,
  alertReviews: (id: string) => ["alerts", id, "reviews"] as const,
  analytics: () => ["analytics"] as const,
  devices: () => ["devices"] as const,
  admissions: () => ["admissions"] as const,
  admissionComparison: (code: string) => ["admissions", code, "comparison"] as const,
  referenceRanges: () => ["reference-ranges"] as const,
  adminUsers: () => ["admin", "users"] as const,
  adminRuns: () => ["admin", "runs"] as const,
  adminRun: (id: string) => ["admin", "run", id] as const,
  adminBatch: (id: string) => ["admin", "batch", id] as const,
  health: () => ["health"] as const,
};
