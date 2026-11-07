// req: FE-022, FE-023, FE-054, FE-055, FE-056, FE-088, FE-145
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import ProtectedLayout from "@/app/(protected)/layout";
import { activeFor } from "@/components/AppHeader/AppHeader";
import ProtectedError from "@/app/(protected)/error";
import GlobalError from "@/app/global-error";
import NotFound from "@/app/not-found";
import { API, problem } from "@/tests/msw/handlers";
import { server } from "@/tests/msw/server";
import { nav, setLocation } from "@/tests/support/navigation";
import { renderSignedIn } from "@/tests/support/render";
import { render } from "@testing-library/react";

describe("protected layout", () => {
  it("renders the app bar, data bar and content once signed in", async () => {
    setLocation("/residents");
    renderSignedIn(
      <ProtectedLayout>
        <p>content</p>
      </ProtectedLayout>,
      "clinician",
    );
    expect(screen.getByRole("status")).toHaveTextContent("Loading EchoWell…");
    expect(await screen.findByText("content")).toBeVisible();
    expect(await screen.findByText("Edgewood, Assisted living")).toBeVisible();
    expect(await screen.findByTestId("data-bar")).toHaveTextContent(
      "Test data only (pipeline test data v0.1, Oct 1–30, 2026).",
    );
    expect(screen.getByRole("main")).toHaveAttribute("id", "main");
  });

  it("redirects to /login?next= without a token (FE-055)", async () => {
    window.history.pushState({}, "", "/residents/R09?x=1#y");
    renderSignedIn(
      <ProtectedLayout>
        <p>secret</p>
      </ProtectedLayout>,
      null,
    );
    await waitFor(() =>
      expect(nav.router.replace).toHaveBeenCalledWith(
        `/login?next=${encodeURIComponent("/residents/R09?x=1#y")}`,
      ),
    );
    expect(screen.queryByText("secret")).toBeNull();
  });

  it("signs out when /auth/me fails", async () => {
    server.use(http.get(`${API}/auth/me`, () => HttpResponse.error()));
    renderSignedIn(
      <ProtectedLayout>
        <p>secret</p>
      </ProtectedLayout>,
      null,
    );
    await waitFor(() => expect(nav.router.replace).toHaveBeenCalled());
  });

  it("goes to /login?reason=expired on a 401 (FE-056)", async () => {
    window.history.pushState({}, "", "/study");
    server.use(http.get(`${API}/config/ui`, () => problem(401, "UNAUTHORIZED", "x")));
    const { client } = renderSignedIn(
      <ProtectedLayout>
        <p>c</p>
      </ProtectedLayout>,
      "admin",
    );
    await waitFor(() =>
      expect(nav.router.replace).toHaveBeenCalledWith(
        `/login?reason=expired&next=${encodeURIComponent("/study")}`,
      ),
    );
    expect(client.getQueryCache().getAll()).toHaveLength(0);
  });

  it("goes to plain /login after Sign out, without a next redirect (FE-058)", async () => {
    window.history.pushState({}, "", "/residents");
    nav.router.replace.mockClear();
    server.use(http.post(`${API}/auth/logout`, () => new HttpResponse(null, { status: 204 })));
    renderSignedIn(
      <ProtectedLayout>
        <p>content</p>
      </ProtectedLayout>,
      "clinician",
    );
    await userEvent.click(await screen.findByRole("button", { name: "Sign out" }));
    await waitFor(() => expect(nav.router.replace).toHaveBeenCalledWith("/login"));
    expect(nav.router.replace).not.toHaveBeenCalledWith(expect.stringMatching(/^\/login\?next=/));
  });

  it("maps paths to the active link", () => {
    expect(activeFor("/residents/R09/log")).toBe("residents");
    expect(activeFor("/admissions")).toBe("admissions");
    expect(activeFor("/study")).toBe("study");
    expect(activeFor("/admin")).toBe("admin");
    expect(activeFor("/x")).toBeNull();
  });
});

describe("error and not-found pages (FE-145)", () => {
  it("renders without details and reloads", async () => {
    const reload = vi.fn();
    Object.defineProperty(window, "location", {
      value: { ...window.location, reload },
      writable: true,
    });
    render(<ProtectedError />);
    expect(
      screen.getByRole("heading", { name: "Something went wrong on this page." }),
    ).toBeVisible();
    await userEvent.click(screen.getByRole("button", { name: "Reload" }));
    expect(reload).toHaveBeenCalled();
    const html = GlobalError();
    expect(html.props.lang).toBe("en");
    render(<NotFound />);
    expect(screen.getByText("This page was not found.")).toBeVisible();
  });
});
