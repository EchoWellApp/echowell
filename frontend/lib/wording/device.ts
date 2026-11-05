// Copy for the chart Device section (TRD 11 §4.5.8, UX-430..UX-433; TRD 04 FE-013).

export const DEVICE_SECTION = "Device";
export const DEVICE_PANEL_NAME = "the device";
export const deviceHeading = (code: string) => `Device ${code}`;

export const DEVICE_ONLINE = { glyph: "●", text: "Online" } as const;
export const DEVICE_NO_UPLOAD = { glyph: "○", text: "No upload today" } as const;
export const DEVICE_FACT = {
  status: "Status",
  lastUpload: "Last upload",
  firmware: "Firmware",
  usedBy: "Used by",
} as const;
export const DEVICE_VALUE_MISSING = "—";

/** "R02", "R02 and R03", "R01, R02 and R03". */
export function deviceJoinCodes(codes: readonly string[]): string {
  if (codes.length <= 1) return codes.join("");
  return `${codes.slice(0, -1).join(", ")} and ${codes[codes.length - 1]}`;
}

export const DEVICE_THIS_RESIDENT_ONLY = "This resident only";
export const deviceSharedWith = (codes: readonly string[]) =>
  `Shared with ${deviceJoinCodes(codes)}`;

export const DEVICE_HISTORY = "History";
export const deviceSilentAllDay = (codes: readonly string[]) =>
  `Silent all day. Affected ${deviceJoinCodes(codes)}.`;
export const deviceReplaced = (oldCode: string, newCode: string) =>
  `Replaced ${oldCode} with ${newCode}. Baseline restarted.`;
export const deviceFirmwareChanged = (from: string, to: string) =>
  `Firmware changed (${from} to ${to}). Baseline restarted.`;
export const DEVICE_NO_PROBLEMS = "No problems in the last 30 days.";
export const DEVICE_CAPTION =
  "Audio never leaves the device. Only voice measurements are uploaded.";
export const deviceNoneAssigned = (residentCode: string) =>
  `No device is assigned to ${residentCode}.`;
