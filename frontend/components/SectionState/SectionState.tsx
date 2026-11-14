// Uniform loading / empty / error rendering inside a panel (TRD 11 UX-200..UX-204, TRD 04 FE-140,
// FE-141). Use `stateFor()` to pick the copy from a query error (403 → no access, FE-035).
import { ApiError } from "@/services/api";
import { NO_ACCESS_INFO, TRY_AGAIN, errorText, loadingText, referenceText } from "@/lib/wording";
import styles from "./SectionState.module.css";

export interface SectionStateProps {
  state: "loading" | "empty" | "error";
  message: string;
  onRetry?: () => void;
  requestId?: string;
}

export function SectionState({ state, message, onRetry, requestId }: SectionStateProps) {
  if (state === "loading") {
    return (
      <p role="status" className={styles.state}>
        {message}
      </p>
    );
  }
  if (state === "empty") return <p className={styles.state}>{message}</p>;
  return (
    <div className={styles.error} role="alert">
      <p>{message}</p>
      {onRetry && (
        <button type="button" className="btn btn-secondary" onClick={onRetry}>
          {TRY_AGAIN}
        </button>
      )}
      {requestId && <p className={styles.ref}>{referenceText(requestId)}</p>}
    </div>
  );
}

/** Loading or error state for a query of the panel named `panel`; null once data is there. */
export function QueryState(props: {
  panel: string;
  isPending: boolean;
  error: unknown;
  refetch: () => unknown;
}) {
  if (props.error) {
    const e = props.error;
    if (e instanceof ApiError && e.status === 403) {
      return <SectionState state="empty" message={NO_ACCESS_INFO} />;
    }
    return (
      <SectionState
        state="error"
        message={errorText(props.panel)}
        onRetry={() => void props.refetch()}
        requestId={e instanceof ApiError ? (e.requestId ?? undefined) : undefined}
      />
    );
  }
  if (props.isPending) return <SectionState state="loading" message={loadingText(props.panel)} />;
  return null;
}
