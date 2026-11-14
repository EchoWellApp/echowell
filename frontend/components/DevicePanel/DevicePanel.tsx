// Chart "Device" section: "Device <D>" facts, "History" and the audio caption (TRD 11
// UX-430..UX-433). Reports the upload state only; it never changes the resident's status (UX-433).
import { formatDateTimeShort, formatLocalDate, windowOf } from "@/lib/format";
import { naturalCompare } from "@/lib/deviceGroups";
import type { CheckinEvent, DeviceItem, Meta } from "@/lib/types";
import {
  DEVICE_CAPTION,
  DEVICE_FACT,
  DEVICE_HISTORY,
  DEVICE_NO_PROBLEMS,
  DEVICE_NO_UPLOAD,
  DEVICE_ONLINE,
  DEVICE_THIS_RESIDENT_ONLY,
  DEVICE_VALUE_MISSING,
  deviceFirmwareChanged,
  deviceHeading,
  deviceReplaced,
  deviceSharedWith,
  deviceSilentAllDay,
} from "@/lib/wording";
import styles from "./DevicePanel.module.css";

export interface DevicePanelProps {
  device: DeviceItem;
  residentCode: string;
  events: CheckinEvent[];
  meta: Meta;
}

export interface DeviceHistoryItem {
  date: string; // facility-local YYYY-MM-DD
  text: string;
  rank: number; // same-date order: restarts before silent days
}

/** Device events of the last 30 days, newest first (UX-431). */
export function deviceHistory(
  device: DeviceItem,
  events: CheckinEvent[],
  meta: Meta,
): DeviceHistoryItem[] {
  const from = meta.as_of ? windowOf(meta.as_of, meta.facility_tz).from : null;
  const inWindow = (d: string) => from === null || d >= from;
  const items: DeviceHistoryItem[] = [];
  for (const e of events) {
    if (e.event_type !== "baseline_restarted" || !inWindow(e.local_date)) continue;
    if (e.restart_cause === "device") {
      const oldCode = e.previous_device_code ?? e.from_value;
      if (oldCode) {
        items.push({
          date: e.local_date,
          text: deviceReplaced(oldCode, e.to_value ?? device.device_code),
          rank: 0,
        });
      }
    } else if (e.restart_cause === "firmware" && e.from_value && e.to_value) {
      items.push({
        date: e.local_date,
        text: deviceFirmwareChanged(e.from_value, e.to_value),
        rank: 1,
      });
    }
  }
  const affected = [...device.resident_codes].sort(naturalCompare);
  for (const day of new Set(device.device_gap_days_last_30)) {
    if (inWindow(day)) items.push({ date: day, text: deviceSilentAllDay(affected), rank: 2 });
  }
  return items.sort((a, b) => (a.date === b.date ? a.rank - b.rank : a.date < b.date ? 1 : -1));
}

export function DevicePanel({ device, residentCode, events, meta }: DevicePanelProps) {
  const tz = meta.facility_tz;
  const headingId = `device-heading-${device.device_code}`;
  const others = device.resident_codes.filter((c) => c !== residentCode).sort(naturalCompare);
  const state = device.uploaded_on_as_of_date ? DEVICE_ONLINE : DEVICE_NO_UPLOAD;
  const history = deviceHistory(device, events, meta);
  return (
    <section className="panel pad stack" aria-labelledby={headingId}>
      <h2 id={headingId}>{deviceHeading(device.device_code)}</h2>
      <dl className={styles.facts}>
        <div>
          <dt>{DEVICE_FACT.status}</dt>
          <dd className={device.uploaded_on_as_of_date ? styles.online : styles.offline}>
            <span aria-hidden="true">{state.glyph}</span> {state.text}
          </dd>
        </div>
        <div>
          <dt>{DEVICE_FACT.lastUpload}</dt>
          <dd>
            {device.last_upload_at
              ? formatDateTimeShort(device.last_upload_at, tz, meta.as_of)
              : DEVICE_VALUE_MISSING}
          </dd>
        </div>
        <div>
          <dt>{DEVICE_FACT.firmware}</dt>
          <dd>{device.firmware_version ?? DEVICE_VALUE_MISSING}</dd>
        </div>
        <div>
          <dt>{DEVICE_FACT.usedBy}</dt>
          <dd>{others.length > 0 ? deviceSharedWith(others) : DEVICE_THIS_RESIDENT_ONLY}</dd>
        </div>
      </dl>
      <h3 className={styles.history}>{DEVICE_HISTORY}</h3>
      {history.length > 0 ? (
        <ul className={styles.events}>
          {history.map((h) => (
            <li key={`${h.date}-${h.rank}-${h.text}`}>
              <span className={styles.date}>{formatLocalDate(h.date, meta.as_of, tz)}</span>
              <span>{h.text}</span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted">{DEVICE_NO_PROBLEMS}</p>
      )}
      <p className={styles.caption}>{DEVICE_CAPTION}</p>
    </section>
  );
}
