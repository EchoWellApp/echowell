// Study team "Devices" section (TRD 11 §4.4, UX-050..UX-058; TRD 04 FE-026, FE-102): tagged rows
// in the order grouped, shared, replacement, needing attention, then "Show all devices (<n>)".
// The heading has tabIndex -1 so `/study#devices` can move focus to it (the page does that).
import { formatDateTimeShort, formatLocalDate, localDateOf, windowOf } from "@/lib/format";
import { compressDeviceCodes, naturalCompare } from "@/lib/deviceGroups";
import type { DeviceItem, Meta } from "@/lib/types";
import {
  STUDY_DEVICES_EMPTY,
  STUDY_DEVICES_HEADING,
  STUDY_DEVICE_COLUMNS,
  STUDY_DEVICE_NO_UPLOAD,
  STUDY_DEVICE_ONLINE,
  STUDY_EMPTY_CELL,
  studyAttentionRest,
  studyDayCount,
  studyFirmwareText,
  studyGroupedRest,
  studyInUseRange,
  studyInUseSince,
  studyReplacementRest,
  studySharedRest,
  studyShowAllDevices,
  studySilentText,
} from "@/lib/wording";
import styles from "./DevicesSection.module.css";

export interface DevicesSectionProps {
  devices: DeviceItem[];
  meta: Meta;
}

export type DeviceRowKind = "grouped" | "shared" | "replacement" | "attention";

export interface DeviceRow {
  kind: DeviceRowKind;
  key: string;
  online: boolean;
  /** The bold part: "D02" or, for a grouped row, "D01, D04 to D06, D08 to D10:". */
  code: string;
  /** The text after the bold part. */
  rest: string;
}

const KIND_ORDER: DeviceRowKind[] = ["grouped", "shared", "replacement", "attention"];

/** The most common firmware version of the active devices (ties: natural order of the version). */
export function mostCommonFirmware(devices: readonly DeviceItem[]): string | null {
  const counts = new Map<string, number>();
  for (const d of devices) {
    if (d.active && d.firmware_version) {
      counts.set(d.firmware_version, (counts.get(d.firmware_version) ?? 0) + 1);
    }
  }
  let best: string | null = null;
  for (const [v, n] of [...counts].sort((a, b) => naturalCompare(a[0], b[0]))) {
    if (best === null || n > (counts.get(best) ?? 0)) best = v;
  }
  return best;
}

/** The rows of the Devices panel (TRD 11 §4.4 table). Retired devices get no row (UX-053). */
export function buildDeviceRows(devices: readonly DeviceItem[], meta: Meta): DeviceRow[] {
  const tz = meta.facility_tz;
  const asOfDate = meta.as_of ? localDateOf(meta.as_of, tz) : null;
  const windowFrom = meta.as_of ? windowOf(meta.as_of, tz).from : null;
  const common = mostCommonFirmware(devices);
  const upload = (d: DeviceItem) =>
    d.last_upload_at ? formatDateTimeShort(d.last_upload_at, tz, meta.as_of) : null;

  const active = devices
    .filter((d) => d.active)
    .sort((a, b) => naturalCompare(a.device_code, b.device_code));
  const rows: DeviceRow[] = [];
  const grouped = new Map<string, DeviceItem[]>();

  for (const d of active) {
    const silent = studySilentText(d.device_gap_days_last_30);
    const base = { key: d.device_code, online: d.uploaded_on_as_of_date, code: d.device_code };
    const firmwareDiffers = Boolean(d.firmware_version && common && d.firmware_version !== common);
    const replacedRecently =
      d.replaces_device_code !== null &&
      d.in_use_since !== null &&
      (windowFrom === null || d.in_use_since >= windowFrom);

    if (d.shared || d.resident_codes.length >= 2) {
      rows.push({
        ...base,
        kind: "shared",
        rest: studySharedRest(d.resident_codes, upload(d)) + silent,
      });
    } else if (replacedRecently) {
      rows.push({
        ...base,
        kind: "replacement",
        rest:
          studyReplacementRest(
            d.resident_codes,
            formatLocalDate(d.in_use_since!),
            d.replaces_device_code!,
            upload(d),
          ) + silent,
      });
    } else if (
      !d.uploaded_on_as_of_date ||
      d.device_gap_days_last_30.length > 0 ||
      firmwareDiffers
    ) {
      rows.push({
        ...base,
        kind: "attention",
        rest:
          studyAttentionRest(d.resident_codes, upload(d)) +
          silent +
          (firmwareDiffers ? studyFirmwareText(d.firmware_version) : ""),
      });
    } else {
      const v = d.firmware_version ?? "";
      grouped.set(v, [...(grouped.get(v) ?? []), d]);
    }
  }

  for (const [version, list] of grouped) {
    const codes = list.map((d) => d.device_code);
    rows.push({
      kind: "grouped",
      key: `group-${version}`,
      online: true,
      code: `${compressDeviceCodes(codes)}:`,
      rest: (asOfDate ? studyGroupedRest(asOfDate) : "") + studyFirmwareText(version || null),
    });
  }

  // Groups are ordered among themselves by their first device code.
  const firstCode = (r: DeviceRow) => r.code.split(/[,:\s]/)[0] ?? r.code;
  return rows.sort(
    (a, b) =>
      KIND_ORDER.indexOf(a.kind) - KIND_ORDER.indexOf(b.kind) ||
      naturalCompare(firstCode(a), firstCode(b)),
  );
}

/** Resident codes for the all-devices table; a retired device shows its successor's residents. */
function residentsOf(d: DeviceItem, all: readonly DeviceItem[]): string[] {
  if (d.resident_codes.length > 0 || !d.replaced_by_device_code) return d.resident_codes;
  return all.find((x) => x.device_code === d.replaced_by_device_code)?.resident_codes ?? [];
}

function inUse(d: DeviceItem): string {
  if (!d.in_use_since) return STUDY_EMPTY_CELL;
  if (d.active || !d.in_use_until) return studyInUseSince(d.in_use_since);
  return studyInUseRange(d.in_use_since, d.in_use_until, d.replaced_by_device_code);
}

export function DevicesSection({ devices, meta }: DevicesSectionProps) {
  const rows = buildDeviceRows(devices, meta);
  const allName = studyShowAllDevices(devices.length);
  const all = [...devices].sort((a, b) => naturalCompare(a.device_code, b.device_code));
  return (
    <section id="devices" className="panel pad stack" aria-labelledby="devices-heading">
      <h2 id="devices-heading" tabIndex={-1} className={styles.heading}>
        {STUDY_DEVICES_HEADING}
      </h2>
      {devices.length === 0 ? (
        <p className="small muted">{STUDY_DEVICES_EMPTY}</p>
      ) : (
        <>
          <ul className={styles.list}>
            {rows.map((r) => (
              <li key={r.key} className={styles.row} data-testid="device-row">
                <span className={r.online ? styles.online : styles.offline}>
                  {r.online ? STUDY_DEVICE_ONLINE : STUDY_DEVICE_NO_UPLOAD}
                </span>
                <span>
                  <b>{r.code}</b>
                  {r.rest}
                </span>
              </li>
            ))}
          </ul>
          <details className={styles.details}>
            <summary>{allName}</summary>
            {/* eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex -- scroll container (UX-243) */}
            <div className="scroll-x" tabIndex={0} role="region" aria-label={allName}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    {STUDY_DEVICE_COLUMNS.map((c) => (
                      <th key={c} scope="col">
                        {c}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {all.map((d) => (
                    <tr key={d.device_code} data-testid="device-table-row">
                      <th scope="row">{d.device_code}</th>
                      <td>{residentsOf(d, devices).join(", ") || STUDY_EMPTY_CELL}</td>
                      <td>{inUse(d)}</td>
                      <td>
                        {d.last_upload_at
                          ? formatDateTimeShort(d.last_upload_at, meta.facility_tz, meta.as_of)
                          : STUDY_EMPTY_CELL}
                      </td>
                      <td>{d.firmware_version ?? STUDY_EMPTY_CELL}</td>
                      <td>{studyDayCount(d.silent_days_last_30)}</td>
                      <td>{studyDayCount(d.device_gap_days_last_30)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        </>
      )}
    </section>
  );
}
