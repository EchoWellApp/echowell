// req: UX-207, UX-210, UX-212, UX-219, FE-079, LOG-111, LOG-112
import type { PipelineRun } from "@/lib/types";
import { ApiError } from "@/services/api";
import { tabFrom } from "./AdminPanel";
import { formErrorsFrom } from "./formErrors";
import { newestFirst, nightlyMissingDate } from "./runHelpers";
import { runPollInterval } from "./RunsTab";

const run = (p: Partial<PipelineRun>): PipelineRun => ({
  id: "r",
  trigger: "nightly",
  scope: "all",
  config_profile: "test_v0_1",
  code_version: "x",
  as_of: "2026-10-30T20:00:00Z",
  started_at: "2026-10-31T07:00:00Z",
  finished_at: null,
  status: "succeeded",
  counts: {},
  warnings: [],
  ...p,
});

describe("AdminPanel helpers", () => {
  it("reads the tab from ?tab=", () => {
    expect(tabFrom("runs")).toBe("runs");
    expect(tabFrom("upload")).toBe("upload");
    expect(tabFrom("nope")).toBe("users");
    expect(tabFrom(null)).toBe("users");
  });

  it("computes the nightly-missing date (UX-219)", () => {
    const tz = "America/Chicago";
    // Oct 31, 1:30 AM CDT: 02:00 of Oct 31 has not passed yet → Oct 30.
    const early = Date.parse("2026-10-31T06:30:00Z");
    expect(nightlyMissingDate([], early, tz)).toBe("2026-10-30");
    // Oct 31, 2:30 AM CDT → Oct 31.
    const later = Date.parse("2026-10-31T07:30:00Z");
    expect(nightlyMissingDate([], later, tz)).toBe("2026-10-31");
    expect(nightlyMissingDate([run({})], later, tz)).toBeNull();
    expect(nightlyMissingDate([run({ status: "failed" })], later, tz)).toBe("2026-10-31");
    expect(nightlyMissingDate([run({ trigger: "manual" })], later, tz)).toBe("2026-10-31");
    const old = run({ started_at: "2026-10-30T05:00:00Z" }); // 26.5 h before
    expect(nightlyMissingDate([old], later, tz)).toBe("2026-10-31");
  });

  it("sorts runs newest first and keeps 50", () => {
    const items = Array.from({ length: 60 }, (_, i) =>
      run({ id: `r${i}`, started_at: new Date(Date.UTC(2026, 9, 1, i)).toISOString() }),
    );
    const out = newestFirst(items);
    expect(out).toHaveLength(50);
    expect(out[0]?.id).toBe("r59");
  });

  it("polls until a terminal status", () => {
    expect(runPollInterval(undefined)).toBe(5000);
    expect(runPollInterval(run({ status: "running" }))).toBe(5000);
    expect(runPollInterval(run({ status: "succeeded" }))).toBe(false);
    expect(runPollInterval(run({ status: "failed" }))).toBe(false);
  });

  it("maps API errors to fields by code (FE-079)", () => {
    const err = (code: string, errors: ApiError["errors"] = []) =>
      new ApiError({ status: 409, code, title: "t", errors });
    expect(formErrorsFrom(new Error("x"), ["email"])).toEqual({
      fields: {},
      form: "Could not save. Check your connection and try again.",
    });
    expect(formErrorsFrom(err("EMAIL_ALREADY_EXISTS"), ["email"]).fields.email).toBe(
      "A user with this email already exists.",
    );
    expect(formErrorsFrom(err("EMAIL_ALREADY_EXISTS"), []).form).toBe(
      "A user with this email already exists.",
    );
    expect(formErrorsFrom(err("PASSWORD_POLICY_VIOLATION"), ["password"]).fields.password).toBe(
      "This password does not meet the password rules.",
    );
    expect(formErrorsFrom(err("PASSWORD_POLICY_VIOLATION"), []).form).toBe(
      "This password does not meet the password rules.",
    );
    expect(formErrorsFrom(err("FORBIDDEN"), []).form).toBe(
      "You cannot change your own role or deactivate yourself.",
    );
    expect(
      formErrorsFrom(
        err("VALIDATION_ERROR", [{ field: "email", code: "missing", message: "Field required" }]),
        ["email"],
      ),
    ).toEqual({ fields: { email: "Field required" }, form: null });
    expect(formErrorsFrom(err("VALIDATION_ERROR"), ["email"]).form).toBe(
      "Check the highlighted fields.",
    );
  });
});
