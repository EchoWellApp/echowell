"use client";
// AuthGuard, AppHeader and DataBar around every protected route (TRD 04 FE-022, FE-023, FE-055).
import { usePathname, useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";
import { AppHeader, activeFor } from "@/components/AppHeader/AppHeader";
import { DataBar } from "@/components/DataBar/DataBar";
import { SectionState } from "@/components/SectionState/SectionState";
import { useAuth } from "@/lib/AuthProvider";
import { useUiConfig } from "@/lib/hooks";
import { loadingText } from "@/lib/wording";

function AuthGuard({ children }: { children: ReactNode }) {
  const { status, signedOutByUser } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (status === "signed-out" && !signedOutByUser) {
      const here = `${window.location.pathname}${window.location.search}${window.location.hash}`;
      router.replace(`/login?next=${encodeURIComponent(here)}`);
    }
  }, [status, signedOutByUser, router]);
  if (status !== "signed-in") {
    return (
      <main id="main">
        <SectionState state="loading" message={loadingText("EchoWell")} />
      </main>
    );
  }
  return <>{children}</>;
}

function Chrome({ children }: { children: ReactNode }) {
  const pathname = usePathname() ?? "";
  const ui = useUiConfig();
  return (
    <>
      <AppHeader meta={ui.data?.meta} active={activeFor(pathname)} />
      <DataBar meta={ui.data?.meta} />
      <main id="main" tabIndex={-1}>
        {children}
      </main>
    </>
  );
}

export default function ProtectedLayout({ children }: { children: ReactNode }) {
  return (
    <AuthGuard>
      <Chrome>{children}</Chrome>
    </AuthGuard>
  );
}
