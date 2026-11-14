// req: FE-023, FE-032, UX-175, UX-229
import { screen, waitFor } from "@testing-library/react";
import LoginPage from "@/app/login/page";
import { nav, setLocation } from "@/tests/support/navigation";
import { renderSignedIn } from "@/tests/support/render";

describe("/login", () => {
  it("renders the brand-only header, the data bar and the form", async () => {
    setLocation("/login", "reason=expired&next=%2Fstudy");
    renderSignedIn(<LoginPage />, null);
    expect(await screen.findByRole("heading", { level: 1, name: "EchoWell" })).toBeVisible();
    expect(screen.getByTestId("data-bar")).toHaveTextContent(
      "No audio is stored or played anywhere in EchoWell.",
    );
    expect(screen.queryByRole("navigation")).toBeNull();
    expect(document.title).toBe("Sign in – EchoWell");
    expect(screen.getByText("Your session has ended. Please sign in again.")).toBeVisible();
  });

  it("sends a signed-in user on to next", async () => {
    setLocation("/login", "next=%2Fstudy");
    renderSignedIn(<LoginPage />, "researcher");
    await waitFor(() => expect(nav.router.replace).toHaveBeenCalledWith("/study"));
  });
});
