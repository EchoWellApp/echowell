// req: UX-078, UX-200, FEAT-066-AC-02, FEAT-066-AC-04
import { render, screen } from "@testing-library/react";
import type { DeviceItem, DeviceList, ResidentDetail } from "@/lib/types";
import devicesJson from "@/tests/fixtures/ds07/devices.json";
import R03 from "@/tests/fixtures/ds07/resident/R03.json";
import R08 from "@/tests/fixtures/ds07/resident/R08.json";
import R09 from "@/tests/fixtures/ds07/resident/R09.json";
import { MoreDetailTiles } from "./MoreDetailTiles";

const as = (x: unknown) => x as ResidentDetail;
const devices = (devicesJson as unknown as DeviceList).items;
const dev = (code: string) => devices.find((d) => d.device_code === code) as DeviceItem;

const tiles = () =>
  screen.getAllByRole("link").map((a) => {
    const [k, v, go] = Array.from(a.children).map((c) => c.textContent);
    return `${k}|${v}|${go}|${a.getAttribute("href")}`;
  });

describe("MoreDetailTiles", () => {
  it("R09: change score, baseline, check-ins and device", () => {
    const r = as(R09);
    render(
      <MoreDetailTiles
        resident={r}
        latestTally={26.830255852459448}
        device={dev("D09")}
        meta={r.meta}
      />,
    );
    expect(screen.getByRole("heading", { level: 2 })).toHaveTextContent("More detail");
    expect(tiles()).toEqual([
      "Voice trends|Change score 26.8|Open|/residents/R09/trends",
      "Baseline|16 of 16 check-ins|Open|/residents/R09/baseline",
      "Check-ins, last 30 days|30 used, 0 missed|Open|/residents/R09/log",
      "Device|D09 online|Open|/residents/R09/device",
    ]);
  });

  it("R08 not scored yet, R03 no change, offline device and loading values", () => {
    const r08 = as(R08);
    const { rerender } = render(
      <MoreDetailTiles resident={r08} latestTally={null} device={dev("D08")} meta={r08.meta} />,
    );
    expect(tiles().map((t) => t.split("|")[1])).toEqual([
      "Not scored yet",
      "13 of 16 check-ins",
      "13 used, 12 missed",
      "D08 online",
    ]);
    rerender(
      <MoreDetailTiles
        resident={as(R03)}
        latestTally={0}
        device={{ ...dev("D02"), uploaded_on_as_of_date: false }}
        meta={r08.meta}
      />,
    );
    expect(tiles().map((t) => t.split("|")[1])).toEqual([
      "No change",
      "16 of 16 check-ins",
      "22 used, 1 missed",
      "D02 no upload today",
    ]);
    rerender(
      <MoreDetailTiles resident={as(R09)} latestTally={undefined} device={null} meta={r08.meta} />,
    );
    expect(tiles().map((t) => t.split("|")[1])).toEqual([
      "—",
      "16 of 16 check-ins",
      "30 used, 0 missed",
      "—",
    ]);
    rerender(
      <MoreDetailTiles resident={as(R09)} latestTally={null} device={null} meta={r08.meta} />,
    );
    expect(tiles()[0]).toContain("Change score 26.8");
  });
});
