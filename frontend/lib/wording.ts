// All user-facing copy (TRD 04 FE-013, TRD 11 §8: copy strings from TRD 11 and test them with
// exact matches). Each screen's templates live in `lib/wording/<area>.ts` and are re-exported here,
// so every component imports copy from "@/lib/wording" only.
export * from "./wording/common";
export * from "./wording/list";
export * from "./wording/chart";
export * from "./wording/review";
export * from "./wording/study";
export * from "./wording/admin";
