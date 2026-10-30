// Root layout (TRD 04 §4.2, FE-004, FE-172). Fonts are self-hosted at build time by next/font.
import type { Metadata } from "next";
import type { ReactNode } from "react";
import { IBM_Plex_Mono, IBM_Plex_Sans } from "next/font/google";
import { EnvironmentRibbon } from "@/components/EnvironmentRibbon/EnvironmentRibbon";
import { config } from "@/lib/config";

const plexSans = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "600"],
  variable: "--font-plex-sans",
});
const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400"],
  variable: "--font-plex-mono",
});

export const metadata: Metadata = {
  title: "EchoWell",
  other: { "echowell-build": config.gitSha },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={`${plexSans.variable} ${plexMono.variable}`}>
      <body className={plexSans.className}>
        <EnvironmentRibbon appEnv={config.appEnv} />
        {children}
      </body>
    </html>
  );
}
