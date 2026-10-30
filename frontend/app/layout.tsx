// Root layout (TRD 04 §4.2, FE-004, FE-172).
import type { Metadata } from "next";
import type { ReactNode } from "react";
import { EnvironmentRibbon } from "@/components/EnvironmentRibbon/EnvironmentRibbon";
import { config } from "@/lib/config";

export const metadata: Metadata = {
  title: "EchoWell",
  other: { "echowell-build": config.gitSha },
};

export default function RootLayout({ children, }
  : { children: ReactNode; }) {
    return (
      <body style={{ fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif', }} >
        <EnvironmentRibbon appEnv={config.appEnv} />
        {children}
        </body>
  );
}