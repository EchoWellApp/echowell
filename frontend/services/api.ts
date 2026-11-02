// The only HTTP client to /api/v1 (TRD 04 §4.6, FE-011, FE-070..FE-076).
import { config } from "@/lib/config";
import { clearToken, getToken } from "@/lib/auth";
import type {
  AdmissionComparison,
  AdmissionList,
  AlertList,
  AlertReview,
  AlertReviewCreate,
  AlertReviewList,
  AnalyticsResponse,
  ChangeAlarm,
  CheckinEventList,
  DataAlertList,
  DeviceList,
  FeaturesResponse,
  Health,
  IngestBatch,
  IngestBatchAccepted,
  PipelineRun,
  PipelineRunAccepted,
  PipelineRunList,
  PipelineRunRequest,
  ProblemFieldError,
  ReferenceRangeList,
  ResidentDetail,
  ResidentsResponse,
  ScoresResponse,
  StaffNote,
  StaffNoteCreate,
  StaffNoteList,
  Token,
  UiConfig,
  User,
  UserCreate,
  UserList,
  UserUpdate,
} from "@/lib/types";

const TIMEOUT_MS = 15_000;
const UPLOAD_TIMEOUT_MS = 120_000;
const LOGOUT_TIMEOUT_MS = 3_000;

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly title: string;
  readonly detail: string;
  readonly requestId: string | null;
  readonly errors: ProblemFieldError[];

  constructor(init: {
    status: number;
    code?: string;
    title: string;
    detail?: string;
    requestId?: string | null;
    errors?: ProblemFieldError[];
  }) {
    super(init.title);
    this.name = "ApiError";
    this.status = init.status;
    this.code = init.code ?? "UNKNOWN";
    this.title = init.title;
    this.detail = init.detail ?? "";
    this.requestId = init.requestId ?? null;
    this.errors = init.errors ?? [];
  }
}

type UnauthorizedHandler = () => void;
let onUnauthorized: UnauthorizedHandler | null = null;

/** Registered by the providers: clears the cache and redirects to /login (FE-056). */
export function setUnauthorizedHandler(handler: UnauthorizedHandler | null): void {
  onUnauthorized = handler;
}

function newRequestId(): string {
  try {
    return crypto.randomUUID();
  } catch {
    return `${Date.now().toString(16)}-${Math.random().toString(16).slice(2)}`;
  }
}

function codeFromType(type: unknown): string {
  if (typeof type !== "string") return "UNKNOWN";
  const m = /^urn:echowell:error:([A-Z0-9_]+)$/.exec(type);
  return m?.[1] ?? "UNKNOWN";
}

async function toApiError(res: Response, requestId: string): Promise<ApiError> {
  const headerId = res.headers.get("X-Request-ID") ?? requestId;
  const type = res.headers.get("Content-Type") ?? "";
  if (type.includes("json")) {
    try {
      const body = (await res.json()) as Record<string, unknown>;
      return new ApiError({
        status: res.status,
        code: type.includes("problem+json") ? codeFromType(body.type) : "UNKNOWN",
        title: typeof body.title === "string" ? body.title : res.statusText || "Error",
        detail: typeof body.detail === "string" ? body.detail : "",
        requestId: typeof body.request_id === "string" ? body.request_id : headerId,
        errors: Array.isArray(body.errors) ? (body.errors as ProblemFieldError[]) : [],
      });
    } catch {
      // fall through to the generic error
    }
  }
  return new ApiError({
    status: res.status,
    title: res.statusText || "Error",
    requestId: headerId,
  });
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  form?: FormData;
  accept?: string;
  timeoutMs?: number;
  auth?: boolean;
  okStatuses?: number[]; // non-2xx statuses whose body is the result (GET /health 503)
}

async function send(path: string, options: RequestOptions = {}): Promise<Response> {
  const requestId = newRequestId();
  const headers: Record<string, string> = {
    Accept: options.accept ?? "application/json",
    "X-Request-ID": requestId,
  };
  const token = options.auth === false ? null : getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  let body: BodyInit | undefined;
  if (options.form) body = options.form;
  else if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.body);
  }
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), options.timeoutMs ?? TIMEOUT_MS);
  let res: Response;
  try {
    res = await fetch(`${config.apiBaseUrl}/api/v1${path}`, {
      method: options.method ?? "GET",
      headers,
      body,
      signal: controller.signal,
    });
  } catch {
    throw new ApiError({ status: 0, title: "Network error", requestId });
  } finally {
    clearTimeout(timer);
  }
  if (!res.ok && !options.okStatuses?.includes(res.status)) {
    const error = await toApiError(res, requestId);
    if (res.status === 401 && token) {
      clearToken();
      onUnauthorized?.();
    }
    throw error;
  }
  return res;
}

async function json<T>(path: string, options?: RequestOptions): Promise<T> {
  const res = await send(path, options);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

function query(params: Record<string, string | number | boolean | null | undefined>): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params))
    if (v !== undefined && v !== null) q.set(k, String(v));
  const s = q.toString();
  return s ? `?${s}` : "";
}

const code = (c: string) => encodeURIComponent(c);

export const LIST = { limit: 500, offset: 0 } as const;

// Auth
export const login = (email: string, password: string) =>
  json<Token>("/auth/login", { method: "POST", body: { email, password }, auth: false });
export async function logout(): Promise<void> {
  try {
    await send("/auth/logout", { method: "POST", timeoutMs: LOGOUT_TIMEOUT_MS });
  } catch {
    // best effort (FE-058)
  }
}
export const getMe = () => json<User>("/auth/me");
export const getUiConfig = () => json<UiConfig>("/config/ui");

// Residents
export const getResidents = () =>
  json<ResidentsResponse>(
    `/residents${query({ sort: "alarm", cohort: "longitudinal", include_withdrawn: false, ...LIST })}`,
  );
export const getResident = (c: string) => json<ResidentDetail>(`/residents/${code(c)}`);
export const getCheckins = (c: string, range: { from?: string; to?: string } = {}) =>
  json<CheckinEventList>(`/residents/${code(c)}/checkins${query(range)}`);
export const getFeatures = (c: string) => json<FeaturesResponse>(`/residents/${code(c)}/features`);
export const getScores = (p: { residentCode: string; epoch?: number | null }) =>
  json<ScoresResponse>(`/scores${query({ resident_code: p.residentCode, epoch: p.epoch })}`);
export const getNotes = (c: string) => json<StaffNoteList>(`/residents/${code(c)}/notes`);
export const createNote = (c: string, input: StaffNoteCreate) =>
  json<StaffNote>(`/residents/${code(c)}/notes`, { method: "POST", body: input });

// Alerts
export const getAlerts = (p: { status?: string; residentCode?: string } = {}) =>
  json<AlertList>(`/alerts${query({ status: p.status, resident_code: p.residentCode })}`);
export const getDataAlerts = (p: { status?: string } = {}) =>
  json<DataAlertList>(`/data-alerts${query({ status: p.status })}`);
export const getAlertReviews = (id: string) =>
  json<AlertReviewList>(`/alerts/${encodeURIComponent(id)}/reviews`);
export const createAlertReview = (id: string, input: AlertReviewCreate) =>
  json<AlertReview>(`/alerts/${encodeURIComponent(id)}/reviews`, { method: "POST", body: input });
export const snoozeAlert = (id: string, input: { hours?: number } = {}) =>
  json<ChangeAlarm>(`/alerts/${encodeURIComponent(id)}/snooze`, { method: "POST", body: input });

// Devices, admissions, study team
export const getDevices = () => json<DeviceList>(`/devices${query(LIST)}`);
export const getAdmissions = () => json<AdmissionList>(`/admissions${query(LIST)}`);
export const getAdmissionComparison = (c: string) =>
  json<AdmissionComparison>(`/admissions/${code(c)}/comparison`);
export const getReferenceRanges = () => json<ReferenceRangeList>("/facility/reference-ranges");
export const getAnalytics = () => json<AnalyticsResponse>("/analytics");

async function csv(path: string): Promise<Blob> {
  const res = await send(path, { accept: "text/csv" });
  return res.blob();
}
export const downloadScoresCsv = (p: { residentCode?: string } = {}) =>
  csv(`/scores${query({ resident_code: p.residentCode })}`);
export const downloadBaselinesCsv = () => csv("/analytics/baselines");

// Admin
export const listPipelineRuns = (p: { trigger?: string; status?: string; limit?: number } = {}) =>
  json<PipelineRunList>(`/pipeline/runs${query({ limit: 50, ...p })}`);
export const getPipelineRun = (id: string) =>
  json<PipelineRun>(`/pipeline/runs/${encodeURIComponent(id)}`);
export const triggerPipelineRun = (input: PipelineRunRequest) =>
  json<PipelineRunAccepted>("/pipeline/run", { method: "POST", body: input });
export function uploadIngestCsv(file: File): Promise<IngestBatchAccepted> {
  const form = new FormData();
  form.append("file", file);
  return json<IngestBatchAccepted>("/ingest", {
    method: "POST",
    form,
    timeoutMs: UPLOAD_TIMEOUT_MS,
  });
}
export const getIngestBatch = (id: string) =>
  json<IngestBatch>(`/ingest/batches/${encodeURIComponent(id)}`);
export const listUsers = () => json<UserList>("/users");
export const createUser = (input: UserCreate) =>
  json<User>("/users", { method: "POST", body: input });
export const updateUser = (id: string, patch: UserUpdate) =>
  json<User>(`/users/${encodeURIComponent(id)}`, { method: "PATCH", body: patch });
export const getHealth = () => json<Health>("/health", { auth: false, okStatuses: [503] });
