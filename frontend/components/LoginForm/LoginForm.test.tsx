// req: FE-050, FE-052, FE-057, FE-066, UX-170..UX-176
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { getToken } from "@/lib/auth";
import { API, problem } from "@/tests/msw/handlers";
import { server } from "@/tests/msw/server";
import { nav } from "@/tests/support/navigation";
import { renderSignedIn } from "@/tests/support/render";
import { LoginForm } from "./LoginForm";

async function fill() {
  await userEvent.type(screen.getByLabelText("Email"), "clinician@example.com");
  await userEvent.type(screen.getByLabelText("Password"), "secret");
  await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
}

describe("LoginForm", () => {
  it("renders the fields with the right autocomplete", () => {
    renderSignedIn(<LoginForm next={null} reason="expired" />, null);
    expect(screen.getByRole("heading", { level: 1, name: "EchoWell" })).toBeVisible();
    expect(screen.getByText("Sign in to see voice check-ins")).toBeVisible();
    expect(screen.getByLabelText("Email")).toHaveAttribute("autocomplete", "username");
    expect(screen.getByLabelText("Password")).toHaveAttribute("type", "password");
    expect(screen.getByLabelText("Password")).toHaveAttribute("autocomplete", "current-password");
    expect(screen.getByText("Your session has ended. Please sign in again.")).toBeVisible();
    expect(screen.getByText("Accounts are created by the EchoWell admin.")).toBeVisible();
  });

  it("signs in and goes to a safe next path", async () => {
    renderSignedIn(<LoginForm next="/residents/R09" reason={null} />, null);
    await fill();
    await waitFor(() => expect(nav.router.replace).toHaveBeenCalledWith("/residents/R09"));
    expect(getToken()).not.toBeNull();
  });

  it("rejects an external next value", async () => {
    renderSignedIn(<LoginForm next="https://evil.example" reason={null} />, null);
    await fill();
    await waitFor(() => expect(nav.router.replace).toHaveBeenCalledWith("/residents"));
  });

  it("shows the wrong-credentials, rate-limit and network messages", async () => {
    server.use(http.post(`${API}/auth/login`, () => problem(401, "INVALID_CREDENTIALS", "x")));
    renderSignedIn(<LoginForm next={null} reason={null} />, null);
    await fill();
    expect(await screen.findByRole("alert")).toHaveTextContent("Email or password is incorrect.");
    server.use(http.post(`${API}/auth/login`, () => problem(429, "RATE_LIMITED", "x")));
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(
      await screen.findByText("Too many sign-in attempts. Wait one minute and try again."),
    ).toBeVisible();
    server.use(http.post(`${API}/auth/login`, () => HttpResponse.error()));
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByText(/Could not reach EchoWell/)).toBeVisible();
  });

  it("shows Signing in… while busy", async () => {
    let release: () => void = () => undefined;
    server.use(
      http.post(
        `${API}/auth/login`,
        () =>
          new Promise<Response>((r) => {
            release = () => r(problem(401, "X", "x"));
          }),
      ),
    );
    renderSignedIn(<LoginForm next={null} reason={null} />, null);
    await fill();
    expect(await screen.findByRole("button", { name: "Signing in…" })).toBeDisabled();
    release();
    expect(await screen.findByRole("button", { name: "Sign in" })).toBeEnabled();
  });
});
