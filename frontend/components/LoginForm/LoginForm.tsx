"use client";
// Email, password, Sign in (TRD 11 UX-170..UX-176, TRD 04 FE-050..FE-057, FE-066, FE-079).
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { safeNext } from "@/lib/auth";
import { useAuth } from "@/lib/AuthProvider";
import { LOGIN } from "@/lib/wording";
import { ApiError } from "@/services/api";
import styles from "./LoginForm.module.css";

export interface LoginFormProps {
  next: string | null;
  reason: "expired" | null;
}

function messageFor(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 429) return LOGIN.tooMany;
    if (error.status === 0 || error.status >= 500) return LOGIN.network;
  }
  return LOGIN.wrong;
}

export function LoginForm({ next, reason }: LoginFormProps) {
  const { signIn } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await signIn(email, password);
      router.replace(safeNext(next));
    } catch (e) {
      setError(messageFor(e));
      setBusy(false);
    }
  }

  return (
    <section className={`panel ${styles.panel}`} aria-labelledby="login-heading">
      <h1 id="login-heading" className={styles.heading}>
        {LOGIN.heading}
      </h1>
      <p className="muted">{LOGIN.intro}</p>
      {reason === "expired" && !error && (
        <p className={styles.notice} role="status">
          {LOGIN.expired}
        </p>
      )}
      <form onSubmit={onSubmit} className={styles.form} noValidate>
        <label htmlFor="login-email">{LOGIN.email}</label>
        <input
          id="login-email"
          type="email"
          autoComplete="username"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <label htmlFor="login-password">{LOGIN.password}</label>
        <input
          id="login-password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <div role="alert" className={styles.error}>
          {error}
        </div>
        <button type="submit" className="btn" disabled={busy}>
          {busy ? LOGIN.submitting : LOGIN.submit}
        </button>
      </form>
      <p className="small muted">{LOGIN.accounts}</p>
    </section>
  );
}
