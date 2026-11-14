// All date, time and number formatting (TRD 04 §4.11, FE-150..FE-154; TRD 11 UX-003, D-119).
// Every function takes the facility time zone from `meta.facility_tz`; the browser's own time
// zone is never used, and local `YYYY-MM-DD` dates are split, never parsed with `new Date()`.

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

interface LocalParts {
  year: number;
  month: number; // 1-12
  day: number;
  hour: number; // 0-23
  minute: number;
}

function parts(isoUtc: string, tz: string): LocalParts {
  const fmt = new Intl.DateTimeFormat("en-US", {
    timeZone: tz,
    year: "numeric",
    month: "numeric",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hourCycle: "h23",
  });
  const out: Record<string, number> = {};
  for (const p of fmt.formatToParts(new Date(isoUtc))) {
    if (p.type !== "literal") out[p.type] = Number(p.value);
  }
  return {
    year: out.year ?? 0,
    month: out.month ?? 1,
    day: out.day ?? 1,
    hour: (out.hour ?? 0) % 24,
    minute: out.minute ?? 0,
  };
}

/** Time-zone abbreviation: "CT" (shortGeneric), else "CDT"/"CST" when the runtime gives "GMT±h". */
export function zoneAbbreviation(isoUtc: string, tz: string): string {
  const pick = (style: "shortGeneric" | "short") =>
    new Intl.DateTimeFormat("en-US", { timeZone: tz, timeZoneName: style })
      .formatToParts(new Date(isoUtc))
      .find((p) => p.type === "timeZoneName")?.value ?? "";
  const generic = pick("shortGeneric");
  if (generic && !/^GMT/.test(generic)) return generic;
  return pick("short");
}

function clock(p: LocalParts): string {
  const h12 = p.hour % 12 === 0 ? 12 : p.hour % 12;
  return `${h12}:${String(p.minute).padStart(2, "0")} ${p.hour < 12 ? "AM" : "PM"}`;
}

function monthDay(month: number, day: number): string {
  return `${MONTHS[month - 1]} ${day}`;
}

function splitLocal(yyyyMmDd: string): { year: number; month: number; day: number } {
  const [y, m, d] = yyyyMmDd.split("-").map(Number);
  return { year: y ?? 0, month: m ?? 1, day: d ?? 1 };
}

function asOfYear(asOfIso: string | null | undefined, tz: string): number | null {
  return asOfIso ? parts(asOfIso, tz).year : null;
}

/** "Oct 30, 2:28 PM CT"; "Dec 30, 2025, 2:28 PM CT" when the year differs from the as-of year. */
export function formatDateTimeShort(
  isoUtc: string,
  tz: string,
  asOfIso: string | null | undefined,
): string {
  const p = parts(isoUtc, tz);
  const year = asOfYear(asOfIso, tz);
  const date =
    year !== null && year !== p.year
      ? `${monthDay(p.month, p.day)}, ${p.year}`
      : monthDay(p.month, p.day);
  return `${date}, ${clock(p)} ${zoneAbbreviation(isoUtc, tz)}`;
}

/** "Oct 30, 2026, 3:00 PM CT" (always with the year). */
export function formatAsOf(isoUtc: string, tz: string): string {
  const p = parts(isoUtc, tz);
  return `${monthDay(p.month, p.day)}, ${p.year}, ${clock(p)} ${zoneAbbreviation(isoUtc, tz)}`;
}

/** "Oct 21"; ", YYYY" appended when the year differs from the as-of year. */
export function formatLocalDate(yyyyMmDd: string, asOfIso?: string | null, tz?: string): string {
  const d = splitLocal(yyyyMmDd);
  const year = asOfIso && tz ? asOfYear(asOfIso, tz) : null;
  const base = monthDay(d.month, d.day);
  return year !== null && year !== d.year ? `${base}, ${d.year}` : base;
}

/** "Oct 1–16", "Sep 25–Oct 10", "Dec 20, 2025–Jan 5, 2026"; with `withYear` "Oct 1–30, 2026". */
export function formatLocalDateRange(
  a: string,
  b: string,
  options: { withYear?: boolean } = {},
): string {
  const x = splitLocal(a);
  const y = splitLocal(b);
  let text: string;
  if (x.year !== y.year) {
    return `${monthDay(x.month, x.day)}, ${x.year}–${monthDay(y.month, y.day)}, ${y.year}`;
  }
  if (x.month === y.month) {
    text = x.day === y.day ? monthDay(x.month, x.day) : `${monthDay(x.month, x.day)}–${y.day}`;
  } else {
    text = `${monthDay(x.month, x.day)}–${monthDay(y.month, y.day)}`;
  }
  return options.withYear ? `${text}, ${y.year}` : text;
}

/** The facility-local date (YYYY-MM-DD) of a UTC instant. */
export function localDateOf(isoUtc: string, tz: string): string {
  const p = parts(isoUtc, tz);
  return `${p.year}-${String(p.month).padStart(2, "0")}-${String(p.day).padStart(2, "0")}`;
}

/** Adds `days` to a local date without any time-zone arithmetic. */
export function addDays(yyyyMmDd: string, days: number): string {
  const d = splitLocal(yyyyMmDd);
  const t = new Date(Date.UTC(d.year, d.month - 1, d.day + days));
  return t.toISOString().slice(0, 10);
}

/** The 30-day window ending on the as-of local date (data bar, Study team period line). */
export function windowOf(asOfIso: string, tz: string, days = 30): { from: string; to: string } {
  const to = localDateOf(asOfIso, tz);
  return { from: addDays(to, -(days - 1)), to };
}

function roundHalfAway(x: number, decimals: number): number {
  const f = 10 ** decimals;
  const v = Math.abs(x) * f;
  // Guard against binary noise such as 2.675 → 2.67499999.
  const r = Math.round(v + 1e-9);
  return (Math.sign(x) || 1) * (r / f);
}

/** Change score with one decimal, half away from zero: "5.4", "26.8", "0.0". */
export function formatTally(x: number): string {
  const v = roundHalfAway(x, 1);
  return (Object.is(v, -0) || v === 0 ? 0 : v).toFixed(1);
}

/** The alarm line value without trailing zeros: "5", "4.5". */
export function formatThreshold(h: number): string {
  return String(Number(h.toFixed(4)));
}

/** "+2.2", "−0.3" (U+2212 minus). */
export function formatSigned(x: number): string {
  const v = roundHalfAway(x, 1);
  if (v === 0) return "0.0";
  return v > 0 ? `+${v.toFixed(1)}` : `−${Math.abs(v).toFixed(1)}`;
}

/** Alarm "Open" fact: "9 days", "1 day", "opened today". */
export function formatOpenDays(d: number): string {
  if (d <= 0) return "opened today";
  return d === 1 ? "1 day" : `${d} days`;
}

/** Whole-number percentage, rounded half up (TRD 11 UX-353). */
export function formatPercent(numerator: number, denominator: number): string {
  if (denominator <= 0) return "0%";
  return `${Math.floor((numerator * 100) / denominator + 0.5 + 1e-9)}%`;
}

/** "1 day" / "<n> days". */
export function plural(n: number, one: string, many: string): string {
  return `${n} ${n === 1 ? one : many}`;
}
