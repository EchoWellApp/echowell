// req: FE-023, FE-024, FE-027, FE-028, FE-029, FE-036, FE-058, UX-010..UX-018
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import configUi from "@/tests/fixtures/ds07/config-ui.json";
import { getToken } from "@/lib/auth";
import type { Meta } from "@/lib/types";
import { API } from "@/tests/msw/handlers";
import { server } from "@/tests/msw/server";
import { nav } from "@/tests/support/navigation";
import { renderSignedIn } from "@/tests/support/render";
import { AppHeader } from "./AppHeader";

const meta = configUi.meta as Meta;
const linkText = (a: HTMLElement) => (a.textContent ?? "").split(",")[0]?.replace(/\d+$/, "");

describe("AppHeader", () => {
  it("shows brand, facility line, nav with the alarm badge for a clinician", async () => {
    renderSignedIn(<AppHeader meta={meta} active="residents" />, "clinician");
    expect(await screen.findByText("Clinician User")).toBeVisible();
    expect(screen.getByText("EchoWell")).toBeVisible();
    expect(screen.getByText("Edgewood, Assisted living")).toBeVisible();
    const navEl = screen.getByRole("navigation", { name: "Main" });
    const list = await within(navEl).findByRole("link", {
      name: "Resident list, 2 alarms not reviewed",
    });
    expect(list).toHaveAttribute("aria-current", "page");
    expect(list).toHaveTextContent("Resident list");
    expect(list.querySelector("[data-count]")).toHaveAttribute("data-count", "2");
    expect(within(navEl).getAllByRole("link").map(linkText)).toEqual([
      "Resident list",
      "New admissions",
    ]);
    expect(screen.queryByText("Edge4Care")).toBeNull();
  });

  it("adds Study team for researchers and Admin for admins (FE-028)", async () => {
    renderSignedIn(<AppHeader meta={meta} active="study" />, "admin");
    const navEl = await screen.findByRole("navigation", { name: "Main" });
    await waitFor(() =>
      expect(within(navEl).getAllByRole("link").map(linkText)).toEqual([
        "Resident list",
        "New admissions",
        "Study team",
        "Admin",
      ]),
    );
    expect(within(navEl).getByRole("link", { name: "Study team" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });

  it("shows one alarm in the singular and no badge when the count fails (FE-036)", async () => {
    server.use(
      http.get(`${API}/alerts`, () =>
        HttpResponse.json({ items: [], total: 1, limit: 50, offset: 0 }),
      ),
    );
    const { unmount } = renderSignedIn(<AppHeader meta={meta} active={null} />, "researcher");
    expect(
      await screen.findByRole("link", { name: "Resident list, 1 alarm not reviewed" }),
    ).toBeVisible();
    unmount();
    server.use(http.get(`${API}/alerts`, () => HttpResponse.error()));
    renderSignedIn(<AppHeader meta={meta} active={null} />, "researcher");
    await screen.findByText("Researcher User");
    expect(screen.getByRole("link", { name: "Resident list" })).toBeVisible();
  });

  it("signs out best-effort and goes to /login (FE-058)", async () => {
    renderSignedIn(<AppHeader meta={meta} active="residents" />, "clinician");
    await userEvent.click(await screen.findByRole("button", { name: "Sign out" }));
    await waitFor(() => expect(nav.router.replace).toHaveBeenCalledWith("/login"));
    expect(getToken()).toBeNull();
  });

  it("renders the brand only on /login", () => {
    renderSignedIn(<AppHeader meta={undefined} active={null} variant="brand-only" />, null);
    expect(screen.getByText("EchoWell")).toBeVisible();
    expect(screen.queryByRole("navigation")).toBeNull();
  });
});
