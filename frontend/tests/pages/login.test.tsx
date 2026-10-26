// req: FE-001, TRD 25 §4.6 Phase 3 (frontend renders /login)
import { render, screen } from "@testing-library/react";
import LoginPage from "@/app/login/page";

describe("/login", () => {
  it("renders the sign-in heading", () => {
    render(<LoginPage />);
    expect(screen.getByRole("heading", { level: 1, name: "Sign in to EchoWell" })).toBeVisible();
  });
});
