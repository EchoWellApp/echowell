// req: FE-150, FE-151, FE-152, FE-153, FE-154, UX-003, UX-008, UX-353
import {
  addDays,
  formatAsOf,
  formatDateTimeShort,
  formatLocalDate,
  formatLocalDateRange,
  formatOpenDays,
  formatPercent,
  formatSigned,
  formatTally,
  formatThreshold,
  localDateOf,
  plural,
  windowOf,
  zoneAbbreviation,
} from "@/lib/format";

const TZ = "America/Chicago";
const AS_OF = "2026-10-30T20:00:00Z";

describe("format", () => {
  it("formats short date-times with the facility zone (FE-151)", () => {
    expect(formatDateTimeShort("2026-10-30T19:28:04Z", TZ, AS_OF)).toBe("Oct 30, 2:28 PM CT");
    expect(formatDateTimeShort("2025-12-30T20:28:00Z", TZ, AS_OF)).toBe("Dec 30, 2025, 2:28 PM CT");
    expect(formatDateTimeShort("2026-10-30T05:05:00Z", TZ, null)).toBe("Oct 30, 12:05 AM CT");
  });

  it("formats the as-of with the year (FE-152)", () => {
    expect(formatAsOf(AS_OF, TZ)).toBe("Oct 30, 2026, 3:00 PM CT");
  });

  it("falls back to the short zone name when shortGeneric gives GMT", () => {
    expect(zoneAbbreviation(AS_OF, "Etc/GMT+5")).toMatch(/GMT|-05/);
  });

  it("formats local dates without time-zone conversion (FE-153)", () => {
    expect(formatLocalDate("2026-10-01")).toBe("Oct 1");
    expect(formatLocalDate("2026-10-01", AS_OF, TZ)).toBe("Oct 1");
    expect(formatLocalDate("2025-12-31", AS_OF, TZ)).toBe("Dec 31, 2025");
  });

  it("formats ranges", () => {
    expect(formatLocalDateRange("2026-10-01", "2026-10-16")).toBe("Oct 1–16");
    expect(formatLocalDateRange("2026-09-25", "2026-10-10")).toBe("Sep 25–Oct 10");
    expect(formatLocalDateRange("2025-12-20", "2026-01-05")).toBe("Dec 20, 2025–Jan 5, 2026");
    expect(formatLocalDateRange("2026-10-01", "2026-10-30", { withYear: true })).toBe(
      "Oct 1–30, 2026",
    );
    expect(formatLocalDateRange("2026-10-04", "2026-10-04")).toBe("Oct 4");
  });

  it("formats numbers (FE-154)", () => {
    expect(formatTally(5.44)).toBe("5.4");
    expect(formatTally(26.75)).toBe("26.8");
    expect(formatTally(0)).toBe("0.0");
    expect(formatTally(-0.04)).toBe("0.0");
    expect(formatThreshold(5)).toBe("5");
    expect(formatThreshold(4.5)).toBe("4.5");
    expect(formatSigned(2.24)).toBe("+2.2");
    expect(formatSigned(-0.25)).toBe("−0.3");
    expect(formatSigned(0)).toBe("0.0");
    expect(formatOpenDays(9)).toBe("9 days");
    expect(formatOpenDays(1)).toBe("1 day");
    expect(formatOpenDays(0)).toBe("opened today");
    expect(formatPercent(281, 300)).toBe("94%");
    expect(formatPercent(267, 300)).toBe("89%");
    expect(formatPercent(1, 2)).toBe("50%");
    expect(formatPercent(1, 0)).toBe("0%");
    expect(plural(1, "day", "days")).toBe("1 day");
  });

  it("derives local dates and the 30-day window", () => {
    expect(localDateOf("2026-10-31T03:00:00Z", TZ)).toBe("2026-10-30");
    expect(addDays("2026-10-30", -29)).toBe("2026-10-01");
    expect(windowOf(AS_OF, TZ)).toEqual({ from: "2026-10-01", to: "2026-10-30" });
  });
});
