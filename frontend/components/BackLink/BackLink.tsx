"use client";
// "← Resident list", keeping the list's last ?show= value (TRD 11 UX-060, TRD 04 FE-025).
import Link from "next/link";
import { useEffect, useState } from "react";
import { BACK_TO_LIST } from "@/lib/wording";
import styles from "./BackLink.module.css";

export const SHOW_KEY = "echowell.residentList.show";

export function rememberShow(value: string): void {
  try {
    window.sessionStorage.setItem(SHOW_KEY, value);
  } catch {
    // ignore (FE-025)
  }
}

export function lastShow(): string {
  try {
    return window.sessionStorage.getItem(SHOW_KEY) ?? "all";
  } catch {
    return "all";
  }
}

export interface BackLinkProps {
  href?: string;
}

export function BackLink({ href }: BackLinkProps) {
  const [target, setTarget] = useState(href ?? "/residents");
  useEffect(() => {
    if (href) return;
    const show = lastShow();
    setTarget(
      show && show !== "all" ? `/residents?show=${encodeURIComponent(show)}` : "/residents",
    );
  }, [href]);
  return (
    <Link href={target} className={styles.back}>
      {BACK_TO_LIST}
    </Link>
  );
}
