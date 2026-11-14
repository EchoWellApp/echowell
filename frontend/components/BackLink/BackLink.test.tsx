// req: FE-025, UX-060
import { render, screen } from "@testing-library/react";
import { BackLink, lastShow, rememberShow } from "./BackLink";

describe("BackLink", () => {
  it("keeps the last ?show= value", () => {
    rememberShow("changed");
    expect(lastShow()).toBe("changed");
    render(<BackLink />);
    expect(screen.getByRole("link", { name: "← Resident list" })).toHaveAttribute(
      "href",
      "/residents?show=changed",
    );
  });

  it("defaults to /residents and tolerates storage failures", () => {
    const spy = vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    expect(lastShow()).toBe("all");
    render(<BackLink />);
    expect(screen.getByRole("link")).toHaveAttribute("href", "/residents");
    spy.mockRestore();
    const set = vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("blocked");
    });
    expect(() => rememberShow("usual")).not.toThrow();
    set.mockRestore();
  });
});
