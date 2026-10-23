// req: FE-004, FE-172 (root layout) and the "/" redirect of TRD 04 §4.2
import type { ReactElement } from "react";

vi.mock("next/font/google", () => ({
  IBM_Plex_Sans: () => ({ className: "plex-sans", variable: "--font-plex-sans" }),
  IBM_Plex_Mono: () => ({ className: "plex-mono", variable: "--font-plex-mono" }),
}));
vi.mock("next/navigation", () => ({ redirect: vi.fn() }));

describe("root layout and home page", () => {
  it("renders html lang=en with the ribbon for the configured environment", async () => {
    const { default: RootLayout } = await import("@/app/layout");
    const html = RootLayout({ children: null }) as ReactElement<{ lang: string }>;
    expect(html.props.lang).toBe("en");
  });

  it("redirects / to /residents", async () => {
    const { redirect } = await import("next/navigation");
    const { default: HomePage } = await import("@/app/page");
    HomePage();
    expect(redirect).toHaveBeenCalledWith("/residents");
  });
});
