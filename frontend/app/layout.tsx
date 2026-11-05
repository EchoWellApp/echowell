// Root layout (TRD 04 §4.2, FE-004, FE-033, FE-172). Source Sans 3 is self-hosted at build time by
// next/font, so the browser never calls a font service (FE-192).
import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Source_Sans_3 } from "next/font/google";
import { EnvironmentRibbon } from "@/components/EnvironmentRibbon/EnvironmentRibbon";
import { config } from "@/lib/config";
import { NOSCRIPT_TEXT, SKIP_LINK } from "@/lib/wording";
import "@/styles/globals.css";
import { Providers } from "./providers";

const sourceSans = Source_Sans_3({
  subsets: ["latin"],
  weight: ["400", "600", "700"],
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
