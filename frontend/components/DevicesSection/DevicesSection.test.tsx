// req: UX-050..UX-058, FE-102, UX-204
import { render, screen } from "@testing-library/react";
import type { DeviceItem, Meta } from "@/lib/types";
import devicesFixture from "@/tests/fixtures/ds07/devices.json";
import { DevicesSection, buildDeviceRows, mostCommonFirmware } from "./DevicesSection";

const meta = devicesFixture.meta as Meta;
const base = devicesFixture.items as DeviceItem[];
const dev = (code: string, patch: Partial<DeviceItem> = {}): DeviceItem => ({
  ...(base[0] as DeviceItem),
  device_code: code,
  resident_codes: [`R${code.slice(1)}`],
  ...patch,
});
const text = (r: { code: string; rest: string }) => `${r.code}${r.rest}`;

describe("buildDeviceRows", () => {
  it("renders the §4.13.4 rows for DS-07", () => {
    const rows = buildDeviceRows(base, meta);
    expect(rows.map((r) => [r.kind, r.online, text(r)])).toEqual([
      ["grouped", true, "D01, D04 to D06, D08 to D10: all uploaded Oct 30. Firmware fw-1.0.0."],
      [
        "shared",
        true,
        "D02 (shared by R02 and R03): last upload Oct 30, 2:55 PM CT. Silent all day Oct 12.",
      ],
      [
        "replacement",
        true,
        "D07B (R07): in use since Oct 13, replacing D07. Last upload Oct 30, 2:52 PM CT.",
      ],
    ]);
  });

  it("devices needing attention: no upload today, gap days, other firmware", () => {
    const rows = buildDeviceRows(
      [
        dev("D01"),
        dev("D02"),
        dev("D03"),
        dev("D11", { uploaded_on_as_of_date: false, last_upload_at: null }),
        dev("D05", {
          device_gap_days_last_30: ["2026-10-02", "2026-10-04", "2026-10-06", "2026-10-27"],
        }),
        dev("D04", { firmware_version: "fw-1.1.0" }),
        dev("D09", { active: false }),
      ],
      meta,
    );
    expect(rows.map((r) => [r.kind, r.online, text(r)])).toEqual([
      ["grouped", true, "D01 to D03: all uploaded Oct 30. Firmware fw-1.0.0."],
      ["attention", true, "D04 (R04): last upload Oct 30, 2:07 PM CT. Firmware fw-1.1.0."],
      [
        "attention",
        true,
        "D05 (R05): last upload Oct 30, 2:07 PM CT. Silent all day on 4 days (latest Oct 27).",
      ],
      ["attention", false, "D11 (R11): no upload yet."],
    ]);
  });

  it("groups by firmware; a replacement older than 30 days is grouped", () => {
    const rows = buildDeviceRows(
      [
        dev("D01"),
        dev("D02"),
        dev("D03", { firmware_version: "fw-2.0.0" }),
        dev("D06", { replaces_device_code: "D00", in_use_since: "2026-09-01" }),
      ],
      meta,
    );
    expect(rows.map(text)).toEqual([
      "D01, D02, D06: all uploaded Oct 30. Firmware fw-1.0.0.",
      "D03 (R03): last upload Oct 30, 2:07 PM CT. Firmware fw-2.0.0.",
    ]);
    expect(mostCommonFirmware([dev("D01"), dev("D02", { firmware_version: "fw-0.9" })])).toBe(
      "fw-0.9",
    );
    expect(mostCommonFirmware([])).toBeNull();
  });

  it("shared device with three residents and no upload today", () => {
    const rows = buildDeviceRows(
      [
        dev("D02", {
          shared: true,
          resident_codes: ["R01", "R02", "R03"],
          uploaded_on_as_of_date: false,
        }),
      ],
      { ...meta, as_of: null },
    );
    expect(rows[0]?.online).toBe(false);
    expect(text(rows[0]!)).toBe(
      "D02 (shared by R01, R02 and R03): last upload Oct 30, 2:07 PM CT.",
    );
  });
});

describe("DevicesSection", () => {
  it("shows the empty state", () => {
    render(<DevicesSection devices={[]} meta={meta} />);
    expect(screen.getByRole("heading", { name: "Devices" })).toBeVisible();
    expect(screen.getByText("No devices are registered yet.")).toBeVisible();
  });

  it("shows tags and the all-devices table cells for unusual devices", () => {
    const { container } = render(
      <DevicesSection
        devices={[
          dev("D11", {
            uploaded_on_as_of_date: false,
            last_upload_at: null,
            firmware_version: null,
            in_use_since: null,
          }),
          dev("D12", { active: false, resident_codes: [], in_use_until: "2026-10-05" }),
        ]}
        meta={meta}
      />,
    );
    expect(screen.getByText("○ No upload today")).toBeVisible();
    const cells = Array.from(container.querySelectorAll("tbody tr")).map((r) =>
      Array.from(r.children).map((c) => c.textContent),
    );
    expect(cells).toEqual([
      ["D11", "R11", "—", "—", "—", "0", "0"],
      ["D12", "—", "Oct 1–5", "Oct 30, 2:07 PM CT", "fw-1.0.0", "0", "0"],
    ]);
  });
});
