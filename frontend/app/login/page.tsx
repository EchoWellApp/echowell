"use client";
// Login screen (TRD 11 §4.9; brand-only AppHeader + DataBar, FE-023).
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect } from "react";
import { AppHeader } from "@/components/AppHeader/AppHeader";
import { DataBar } from "@/components/DataBar/DataBar";
import { LoginForm } from "@/components/LoginForm/LoginForm";
import { safeNext } from "@/lib/auth";
import { useAuth } from "@/lib/AuthProvider";
import { useDocumentTitle } from "@/lib/hooks";

function LoginContent() {
  const params = useSearchParams();
  const router = useRouter();
  const { status } = useAuth();
  const next = params.get("next");
  const reason = params.get("reason") === "expired" ? "expired" : null;
  useDocumentTitle("Sign in");
  useEffect(() => {
    if (status === "signed-in") router.replace(safeNext(next));
  }, [status, next, router]);
  return <LoginForm next={next} reason={reason} />;
}

export default function LoginPage() {
  return (
    <>
      <AppHeader meta={undefined} active={null} variant="brand-only" />
      <DataBar meta={undefined} />
      <main id="main">
        <Suspense fallback={null}>
          <LoginContent />
        </Suspense>
      </main>
    </>
  );
}
