// The only API type names components use (TRD 04 §4.6.3); every type comes from the generated
// `lib/api-types.ts` (FE-012), never written by hand.
import type { components } from "./api-types";

type S = components["schemas"];

export type Meta = S["Meta"];
export type Role = S["Role"];
export type User = S["User"];
export type DisplayStatus = S["DisplayStatus"];
export type ResidentRow = S["ResidentOverviewRow"];
export type ResidentsResponse = S["ResidentsOverviewResponse"];
export type ResidentDetail = S["ResidentDetail"];
export type CheckinEventType = S["CheckinEventType"];
export type CheckinEvent = S["CheckinEvent"];
export type CheckinEventList = S["CheckinEventList"];
export type DeviceItem = S["Device"];
export type DeviceList = S["DeviceList"];
export type ChangeAlarm = S["Alert"];
export type AlertList = S["AlertList"];
export type DataAlertKind = S["DataAlertKind"];
export type DataAlert = S["DataAlert"];
export type DataAlertList = S["DataAlertList"];
export type ReviewOutcome = S["ReviewOutcome"];
export type AlertReview = S["AlertReview"];
export type AlertReviewList = S["AlertReviewList"];
export type AlertReviewCreate = S["AlertReviewCreate"];
export type UiConfig = S["UiConfig"];
export type BaselinePeriod = S["BaselinePeriod"];
export type ScorePoint = S["ScoreRow"];
export type ScoresResponse = S["ScoresResponse"];
export type FeaturesResponse = S["FeaturesResponse"];
export type StaffNote = S["StaffNote"];
export type StaffNoteList = S["StaffNoteList"];
export type StaffNoteCreate = S["StaffNoteCreate"];
export type NoteType = S["NoteType"];
export type AdmissionRow = S["AdmissionRow"];
export type AdmissionList = S["AdmissionList"];
export type AdmissionComparison = S["AdmissionComparison"];
export type ComparisonStatus = S["ComparisonStatus"];
export type ReferenceRangeList = S["ReferenceRangeList"];
export type BaselineProgress = S["BaselineProgress"];
export type ReviewExplanation = S["ReviewExplanation"];
export type AnalyticsResponse = S["AnalyticsResponse"];
export type DailySeriesPoint = S["DailySeriesPoint"];
export type Funnel = S["Funnel"];
export type ByResidentRow = S["ByResidentRow"];
export type ReviewOutcomes = S["ReviewOutcomes"];
export type AnalyticsKpis = S["AnalyticsKpis"];
export type AlarmTimingRow = S["AlarmTimingRow"];
export type PipelineRun = S["PipelineRun"];
export type PipelineRunList = S["PipelineRunList"];
export type PipelineRunRequest = S["PipelineRunRequest"];
export type PipelineRunAccepted = S["PipelineRunAccepted"];
export type IngestBatch = S["IngestBatch"];
export type IngestBatchAccepted = S["IngestBatchAccepted"];
export type UserList = S["UserList"];
export type UserCreate = S["UserCreate"];
export type UserUpdate = S["UserUpdate"];
export type Health = S["Health"];
export type Token = S["Token"];
export type ProblemFieldError = S["ProblemFieldError"];

/** UI display status (presentation only, TRD 04 FE-207). */
export type UiStatus = "changed" | "needs_attention" | "learning" | "usual";
