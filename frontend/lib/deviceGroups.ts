// Device-range compression (TRD 04 FE-102, TRD 11 UX-054): "D01, D04 to D06, D08 to D10".
const PLAIN = /^([A-Za-z]+)(\d+)$/;

function naturalKey(code: string): [string, number, string] {
  const m = /^([A-Za-z]*)(\d*)(.*)$/.exec(code);
  return [m?.[1] ?? code, m?.[2] ? Number(m[2]) : -1, m?.[3] ?? ""];
}

export function naturalCompare(a: string, b: string): number {
  const [pa, na, sa] = naturalKey(a);
  const [pb, nb, sb] = naturalKey(b);
  if (pa !== pb) return pa < pb ? -1 : 1;
  if (na !== nb) return na - nb;
  return sa < sb ? -1 : sa > sb ? 1 : 0;
}

export function compressDeviceCodes(codes: readonly string[]): string {
  const sorted = [...new Set(codes)].sort(naturalCompare);
  const out: string[] = [];
  let run: string[] = [];
  const flush = () => {
    if (run.length >= 3) out.push(`${run[0]} to ${run[run.length - 1]}`);
    else out.push(...run);
    run = [];
  };
  for (const code of sorted) {
    const prev = run[run.length - 1];
    const m = PLAIN.exec(code);
    const pm = prev ? PLAIN.exec(prev) : null;
    const consecutive =
      m &&
      pm &&
      m[1] === pm[1] &&
      m[2]!.length === pm[2]!.length &&
      Number(m[2]) === Number(pm[2]) + 1;
    if (!consecutive) flush();
    if (m) run.push(code);
    else out.push(code);
  }
  flush();
  return out.join(", ");
}
