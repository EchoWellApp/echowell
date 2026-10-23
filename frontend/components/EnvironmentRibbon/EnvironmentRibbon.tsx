// Non-dismissable environment ribbon (TRD 04 FE-172, TRD 21 ENV-032).
import type { AppEnv } from "@/lib/config";
import styles from "./EnvironmentRibbon.module.css";

const LABELS: Record<AppEnv, string | null> = {
  local: "LOCAL",
  staging: "STAGING – synthetic data",
  production: null,
};

export function EnvironmentRibbon({ appEnv }: { appEnv: AppEnv }) {
  const label = LABELS[appEnv];
  if (!label) return null;
  return (
    <div className={styles.ribbon} role="note">
      {label}
    </div>
  );
}
