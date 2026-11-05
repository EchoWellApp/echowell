// req: FE-030, FE-032, FE-087, FE-140, FE-141, FE-186, UX-229, UX-262, UX-430, UX-431, UX-432, UX-433, §4.13.3 (Device sections), FEAT-070-AC-01, FEAT-070-AC-02, FEAT-070-AC-03, FEAT-070-AC-04
import { act, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import DevicePage from "@/app/(protected)/residents/[residentCode]/device/page";
import devices from "@/tests/fixtures/ds07/devices.json";
import r09 from "@/tests/fixtures/ds07/resident/R09.json";
import { API, problem } from "@/tests/msw/handlers";
import { server } from "@/tests/msw/server";
import { setLocation } from "@/tests/support/navigation";
import { renderSignedIn } from "@/tests/support/render";

function open(code: string) {
  setLocation(`/residents/${code}/device`, "", { residentCode: code });
  return renderSignedIn(<DevicePage />, "clinician");
}

function factsText() {
  return Array.from(document.querySelectorAll("dl > div")).map(
    (d) => `${d.querySelector("dd")!.textContent} / ${d.querySelector("dt")!.textContent}`,
  );
}

describe("Device section", () => {
  it("renders R03 (§4.13.3)", async () => {
    open("R03");
    expect(await screen.findByRole("heading", { level: 2, name: "Device D02" })).toBeVisible();
    expect(factsText()).toEqual([
      "● Online / Status",
      "Oct 30, 2:55 PM CT / Last upload",
      "fw-1.0.0 / Firmware",
      "Shared with R02 / Used by",
    ]);
    expect(screen.getByText("Oct 12")).toBeVisible();
    expect(screen.getByText("Silent all day. Affected R02 and R03.")).toBeVisible();
    expect(document.title).toBe("R03 · Device – EchoWell");
  });

  it("renders R07 (§4.13.3)", async () => {
    open("R07");
    expect(await screen.findByRole("heading", { name: "Device D07B" })).toBeVisible();
    expect(factsText()).toEqual([
      "● Online / Status",
      "Oct 30, 2:52 PM CT / Last upload",
      "fw-1.0.0 / Firmware",
      "This resident only / Used by",
    ]);
    expect(screen.getByText("Oct 13")).toBeVisible();
    expect(screen.getByText("Replaced D07 with D07B. Baseline restarted.")).toBeVisible();
  });

  it.each(["R01", "R02", "R04", "R05", "R06", "R08", "R09", "R10"])(
    "renders %s with its device and the caption",
    async (code) => {
      open(code);
      const heading = await screen.findByRole("heading", { level: 2, name: /^Device D/ });
      expect(heading).toBeVisible();
      expect(factsText()[0]).toBe("● Online / Status");
      if (code === "R02") {
        expect(screen.getByText("Silent all day. Affected R02 and R03.")).toBeVisible();
      } else {
        expect(screen.getByText("No problems in the last 30 days.")).toBeVisible();
      }
      expect(
        screen.getByText("Audio never leaves the device. Only voice measurements are uploaded."),
      ).toBeVisible();
      expect(screen.queryByRole("heading", { level: 1 })).toBeNull();
    },
  );

  it("shows ○ No upload today without changing anything else (UX-433)", async () => {
    server.use(
      http.get(`${API}/devices`, () =>
        HttpResponse.json({
          ...devices,
          items: devices.items.map((d) =>
            d.device_code === "D09" ? { ...d, uploaded_on_as_of_date: false } : d,
          ),
        }),
      ),
    );
    open("R09");
    expect(await screen.findByText("No upload today")).toBeVisible();
    expect(factsText()[0]).toBe("○ No upload today / Status");
  });

  it("shows loading, then an error with Try again and the reference", async () => {
    let fail = true;
    server.use(
      http.get(`${API}/devices`, () =>
        fail ? problem(500, "INTERNAL", "Boom") : HttpResponse.json(devices),
      ),
    );
    open("R09");
    expect(await screen.findByText("Loading the device…")).toBeInTheDocument();
    expect(
      await screen.findByText("Could not load the device. Check your connection and try again."),
    ).toBeVisible();
    expect(screen.getByText("Reference: req-test-0001")).toBeVisible();
    fail = false;
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByRole("heading", { name: "Device D09" })).toBeVisible();
  });

  it("shows the no-access text on a 403", async () => {
    server.use(http.get(`${API}/residents/R09/checkins`, () => problem(403, "FORBIDDEN", "No")));
    open("R09");
    expect(await screen.findByText("You do not have access to this information.")).toBeVisible();
  });

  it("says when no device is assigned", async () => {
    server.use(
      http.get(`${API}/residents/R09`, () =>
        HttpResponse.json({ ...r09, device: { ...r09.device, device_code: null } }),
      ),
    );
    open("R09");
    expect(await screen.findByText("No device is assigned to R09.")).toBeVisible();
  });

  it("renders nothing for an unknown resident (the layout shows not-found)", async () => {
    const { container } = open("R99");
    await waitFor(() => expect(container).toBeEmptyDOMElement());
  });

  it("makes no API call for an invalid resident code (FE-030)", async () => {
    const seen: string[] = [];
    const listener = ({ request }: { request: Request }) => seen.push(request.url);
    server.events.on("request:start", listener);
    const { container } = open("../R09");
    await act(async () => {
      await new Promise((r) => setTimeout(r, 50));
    });
    expect(container).toBeEmptyDOMElement();
    expect(seen.filter((u) => !u.endsWith("/auth/me"))).toEqual([]);
    server.events.removeListener("request:start", listener);
  });
});
