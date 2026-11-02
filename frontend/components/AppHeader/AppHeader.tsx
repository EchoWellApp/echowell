"use client";
// App bar: brand, facility line, main navigation with the alarm count, user, Sign out
// (TRD 11 UX-010..UX-018, TRD 04 FE-023..FE-029, FE-036).
import Link from "next/link";
import { useAuth } from "@/lib/AuthProvider";
import { useOpenAlarmCount } from "@/lib/hooks";
import { canSeeStudyTeam, isAdmin } from "@/lib/roles";
import type { Meta } from "@/lib/types";
import { BRAND, NAV, facilityLine, residentListLinkName } from "@/lib/wording";
import { CountBadge } from "../CountBadge/CountBadge";
import styles from "./AppHeader.module.css";

export type ActivePage = "residents" | "admissions" | "study" | "admin" | null;

export interface AppHeaderProps {
  meta: Meta | undefined;
  active: ActivePage;
  variant?: "full" | "brand-only";
}

function NavLink(props: {
  href: string;
  active: boolean;
  label?: string;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={props.href}
      className={styles.link}
      aria-current={props.active ? "page" : undefined}
      aria-label={props.label}
    >
      {props.children}
    </Link>
  );
}

function FullNav({ active }: { active: ActivePage }) {
  const { user, signOut } = useAuth();
  const role = user?.role;
  const count = useOpenAlarmCount(!!user);
  const n = count.isSuccess ? count.data.total : 0;
  return (
    <>
      <nav aria-label={NAV.label} className={styles.nav}>
        <NavLink href="/residents" active={active === "residents"} label={residentListLinkName(n)}>
          {NAV.residents}
          <CountBadge count={n} label={`${n === 1 ? "1 alarm" : `${n} alarms`} not reviewed`} />
        </NavLink>
        <NavLink href="/admissions" active={active === "admissions"}>
          {NAV.admissions}
        </NavLink>
        {canSeeStudyTeam(role) && (
          <NavLink href="/study" active={active === "study"}>
            {NAV.study}
          </NavLink>
        )}
        {isAdmin(role) && (
          <NavLink href="/admin" active={active === "admin"}>
            {NAV.admin}
          </NavLink>
        )}
      </nav>
      <div className={styles.user}>
        {user && <span className={styles.name}>{user.displayName}</span>}
        <button type="button" className={styles.signOut} onClick={() => void signOut()}>
          {NAV.signOut}
        </button>
      </div>
    </>
  );
}

export function AppHeader({ meta, active, variant = "full" }: AppHeaderProps) {
  return (
    <header className={styles.appbar}>
      <span className={styles.brand}>{BRAND}</span>
      {variant === "full" && meta && <span className={styles.facility}>{facilityLine(meta)}</span>}
      {variant === "full" && <FullNav active={active} />}
    </header>
  );
}
