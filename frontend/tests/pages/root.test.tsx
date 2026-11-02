// req: FE-004, FE-021, FE-033, FE-172 (root layout) and the "/" redirect of TRD 04 §4.2
import type { ReactElement } from "react";

vi.mock("next/font/google", () => ({
  Source_Sans_3: () => ({ className: "source-sans", variable: "--font-source-sans-3" }),
}));

describe("root layout and home page", () => {
  it("renders html lang=en with the skip link first", async () => {
    const { default: RootLayout } = await import("@/app/layout");
    const html = RootLayout({ children: null }) as ReactElement<{
      lang: string;
      children: ReactElement<{ children: ReactElement<{ href: string }>[] }>;
    }>;
    expect(html.props.lang).toBe("en");
    const first = html.props.children.props.children[0];
    expect(first?.props.href).toBe("#main");
  });

  it("redirects / to /residents", async () => {
    const { redirect } = await import("next/navigation");
    const { default: HomePage } = await import("@/app/page");
    HomePage();
    expect(redirect).toHaveBeenCalledWith("/residents");
  });
});
