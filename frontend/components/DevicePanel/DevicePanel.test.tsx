// req: UX-430, UX-431, UX-432, UX-433, UX-262, §4.13.3 (Device R03, R07, others), FEAT-070-AC-01, FEAT-070-AC-02, FEAT-070-AC-03, FEAT-070-AC-04
import { render, screen, within } from "@testing-library/react";
import type { CheckinEvent, DeviceItem, DeviceList, CheckinEventList } from "@/lib/types";
import devicesJson from "@/tests/fixtures/ds07/devices.json";
import r03Checkins from "@/tests/fixtures/ds07/resident/R03-checkins.json";
import r07Checkins from "@/tests/fixtures/ds07/resident/R07-checkins.json";
import r09Checkins from "@/tests/fixtures/ds07/resident/R09-checkins.json";
import { DevicePanel, deviceHistory } from "./DevicePanel";

const devices = devicesJson as DeviceList;
const meta = devices.meta;
const device = (code: string) => devices.items.find((d) => d.device_code === code)!;
const events = (list: unknown) => (list as CheckinEventList).items;

function facts() {
  const out: Record<string, string> = {};
  for (const div of Array.from(document.querySelector("dl")!.children)) {
    const dt = div.querySelector("dt")!.textContent!;
    out[dt] = div.querySelector("dd")!.textContent!;
  }
  return out;
}

describe("DevicePanel", () => {
  it("renders R03's shared device D02 (§4.13.3)", () => {
    render(
      <DevicePanel
        device={device("D02")}
        residentCode="R03"
        events={events(r03Checkins)}
        meta={meta}
      />,
    );
    expect(screen.getByRole("heading", { level: 2, name: "Device D02" })).toBeVisible();
    expect(facts()).toEqual({
      Status: "● Online",
      "Last upload": "Oct 30, 2:55 PM CT",
      Firmware: "fw-1.0.0",
      "Used by": "Shared with R02",
    });
    expect(screen.getByRole("heading", { level: 3, name: "History" })).toBeVisible();
    const rows = screen.getAllByRole("listitem");
    expect(rows.map((r) => r.textContent)).toEqual(["Oct 12Silent all day. Affected R02 and R03."]);
    expect(
      screen.getByText("Audio never leaves the device. Only voice measurements are uploaded."),
    ).toBeVisible();
  });

  it("renders R07's replacement device D07B (§4.13.3)", () => {
    render(
      <DevicePanel
        device={device("D07B")}
        residentCode="R07"
        events={events(r07Checkins)}
        meta={meta}
      />,
    );
    expect(screen.getByRole("heading", { name: "Device D07B" })).toBeVisible();
    expect(facts()).toEqual({
      Status: "● Online",
      "Last upload": "Oct 30, 2:52 PM CT",
      Firmware: "fw-1.0.0",
      "Used by": "This resident only",
    });
    const row = screen.getByRole("listitem");
    expect(within(row).getByText("Oct 13")).toBeVisible();
    expect(within(row).getByText("Replaced D07 with D07B. Baseline restarted.")).toBeVisible();
  });

  it("renders R09's device with no problems", () => {
    render(
      <DevicePanel
        device={device("D09")}
        residentCode="R09"
        events={events(r09Checkins)}
        meta={meta}
      />,
    );
    expect(screen.getByRole("heading", { name: "Device D09" })).toBeVisible();
    expect(facts().Status).toBe("● Online");
    expect(screen.getByText("No problems in the last 30 days.")).toBeVisible();
    expect(screen.queryByRole("list")).toBeNull();
    expect(
      screen.getByText("Audio never leaves the device. Only voice measurements are uploaded."),
    ).toBeVisible();
  });

  it('shows "○ No upload today" and dashes for missing values (UX-433)', () => {
    const silent: DeviceItem = {
      ...device("D09"),
      uploaded_on_as_of_date: false,
      last_upload_at: null,
      firmware_version: null,
    };
    render(<DevicePanel device={silent} residentCode="R09" events={[]} meta={meta} />);
    expect(facts()).toEqual({
      Status: "○ No upload today",
      "Last upload": "—",
      Firmware: "—",
      "Used by": "This resident only",
    });
    expect(
      screen.getByText("No upload today").closest("dd")!.querySelector("[aria-hidden]"),
    ).toHaveTextContent("○");
  });

  it("lists firmware changes and orders history newest first, outside-window events dropped", () => {
    const base: CheckinEvent = events(r07Checkins)[0]!;
    const evs: CheckinEvent[] = [
      {
        ...base,
        local_date: "2026-10-20",
        event_type: "baseline_restarted",
        restart_cause: "firmware",
        from_value: "fw-1.0.0",
        to_value: "fw-1.1.0",
      },
      {
        ...base,
        local_date: "2026-09-20",
        event_type: "baseline_restarted",
        restart_cause: "firmware",
        from_value: "fw-0.9.0",
        to_value: "fw-1.0.0",
      },
      {
        ...base,
        local_date: "2026-10-05",
        event_type: "baseline_restarted",
        restart_cause: "software",
      },
    ];
    const dev: DeviceItem = {
      ...device("D02"),
      resident_codes: ["R03", "R02", "R11"],
      device_gap_days_last_30: ["2026-10-12", "2026-10-20", "2026-09-01"],
    };
    expect(deviceHistory(dev, evs, meta).map((h) => [h.date, h.text])).toEqual([
      ["2026-10-20", "Firmware changed (fw-1.0.0 to fw-1.1.0). Baseline restarted."],
      ["2026-10-20", "Silent all day. Affected R02, R03 and R11."],
      ["2026-10-12", "Silent all day. Affected R02, R03 and R11."],
    ]);
    render(<DevicePanel device={dev} residentCode="R03" events={evs} meta={meta} />);
    expect(facts()["Used by"]).toBe("Shared with R02 and R11");
  });

  it("keeps every event when the as-of instant is unknown", () => {
    const dev: DeviceItem = { ...device("D02"), device_gap_days_last_30: ["2025-01-01"] };
    expect(deviceHistory(dev, [], { ...meta, as_of: null })).toHaveLength(1);
  });
});
