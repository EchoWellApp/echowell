// Root layout (TRD 04 §4.2, FE-004, FE-033, FE-172). Source Sans 3 is self-hosted from app/fonts by
// next/font/local, so neither the build nor the browser calls a font service (FE-192).
import type { Metadata } from "next";
import type { ReactNode } from "react";
import localFont from "next/font/local";
import { EnvironmentRibbon } from "@/components/EnvironmentRibbon/EnvironmentRibbon";
import { config } from "@/lib/config";
import { NOSCRIPT_TEXT, SKIP_LINK } from "@/lib/wording";
import "@/styles/globals.css";
import { Providers } from "./providers";

// Source Sans 3 (SIL OFL 1.1, app/fonts/OFL.txt), latin variable font committed to the repository so the
// build never downloads fonts (Docker and CI builds failed on Google Fonts fetches; FE-192, UX-252).
const sourceSans = localFont({
  src: "./fonts/SourceSans3-latin-variable.woff2",
  weight: "400 700",
  variable: "--font-source-sans-3",
  display: "swap",
});

export const metadata: Metadata = {
  title: "EchoWell",
  other: { "echowell-build": config.gitSha },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={sourceSans.variable}>
      <body>
        <a href="#main" className="skip-link">
          {SKIP_LINK}
        </a>
        <noscript>
          <p className="noscript">{NOSCRIPT_TEXT}</p>
        </noscript>
        <EnvironmentRibbon appEnv={config.appEnv} />
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
