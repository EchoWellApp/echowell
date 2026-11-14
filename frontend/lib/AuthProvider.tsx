"use client";
// Auth context: user, role, signIn, signOut (TRD 04 FE-052..FE-058).
import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import * as api from "@/services/api";
import { clearToken, getExp, getToken, restoreToken, setToken } from "./auth";
import type { Role } from "./types";

export interface AuthUser {
  id: string;
  email: string;
  displayName: string;
  role: Role;
}

export interface AuthState {
  status: "loading" | "signed-in" | "signed-out";
  user: AuthUser | null;
  /** True after "Sign out", which navigates to /login itself (FE-058; no `next` redirect). */
  signedOutByUser?: boolean;
  signIn(email: string, password: string): Promise<void>;
  signOut(): Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth outside AuthProvider");
  return ctx;
}

function currentPath(): string {
  if (typeof window === "undefined") return "/residents";
  return `${window.location.pathname}${window.location.search}${window.location.hash}`;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const router = useRouter();
  const [status, setStatus] = useState<AuthState["status"]>("loading");
  const [user, setUser] = useState<AuthUser | null>(null);
  const [signedOutByUser, setSignedOutByUser] = useState(false);
  const expiryTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const reset = useCallback(() => {
    clearToken();
    if (expiryTimer.current) clearTimeout(expiryTimer.current);
    void queryClient.cancelQueries();
    queryClient.clear();
    setUser(null);
    setStatus("signed-out");
  }, [queryClient]);

  const expire = useCallback(() => {
    reset();
    router.replace(`/login?reason=expired&next=${encodeURIComponent(currentPath())}`);
  }, [reset, router]);

  const scheduleExpiry = useCallback(() => {
    if (expiryTimer.current) clearTimeout(expiryTimer.current);
    const exp = getExp();
    if (exp === null) return;
    const ms = Math.max(0, exp * 1000 - Date.now());
    expiryTimer.current = setTimeout(expire, Math.min(ms, 2_147_000_000));
  }, [expire]);

  const loadMe = useCallback(async () => {
    try {
      const me = await queryClient.fetchQuery({ queryKey: ["me"], queryFn: api.getMe });
      setUser({ id: me.id, email: me.email, displayName: me.display_name, role: me.role });
      setStatus("signed-in");
    } catch {
      reset();
    }
  }, [queryClient, reset]);

  useEffect(() => {
    api.setUnauthorizedHandler(expire);
    return () => api.setUnauthorizedHandler(null);
  }, [expire]);

  useEffect(() => {
    if (restoreToken() && getToken()) {
      scheduleExpiry();
      void loadMe();
    } else {
      setStatus("signed-out");
    }
    return () => {
      if (expiryTimer.current) clearTimeout(expiryTimer.current);
    };
  }, [loadMe, scheduleExpiry]);

  const signIn = useCallback(
    async (email: string, password: string) => {
      const token = await api.login(email, password);
      setToken(token.access_token);
      scheduleExpiry();
      const u = token.user;
      queryClient.setQueryData(["me"], u);
      setUser({ id: u.id, email: u.email, displayName: u.display_name, role: u.role });
      setSignedOutByUser(false);
      setStatus("signed-in");
    },
    [queryClient, scheduleExpiry],
  );

  const signOut = useCallback(async () => {
    await api.logout();
    setSignedOutByUser(true);
    reset();
    router.replace("/login");
  }, [reset, router]);

  const value = useMemo(
    () => ({ status, user, signedOutByUser, signIn, signOut }),
    [status, user, signedOutByUser, signIn, signOut],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
