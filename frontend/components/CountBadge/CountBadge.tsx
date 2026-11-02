// Red count badge after a link (TRD 11 UX-018, UX-411); nothing for 0.
import styles from "./CountBadge.module.css";

export interface CountBadgeProps {
  count: number;
  label: string; // accessible-name suffix, read with the link text
}

export function CountBadge({ count, label }: CountBadgeProps) {
  if (count <= 0) return null;
  return (
    <span className={styles.badge}>
      <span aria-hidden="true">{count}</span>
      <span className="visually-hidden">{`, ${label}`}</span>
    </span>
  );
}
