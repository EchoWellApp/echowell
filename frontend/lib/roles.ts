// Role helpers (TRD 04 FE-059).
import type { Role } from "./types";

type MaybeRole = Role | null | undefined;

export const canWriteNotes = (role: MaybeRole): boolean => role === "admin" || role === "clinician";
export const canReviewAlarms = (role: MaybeRole): boolean =>
  role === "admin" || role === "clinician";
export const isAdmin = (role: MaybeRole): boolean => role === "admin";
export const canSeeStudyTeam = (role: MaybeRole): boolean =>
  role === "admin" || role === "researcher";
