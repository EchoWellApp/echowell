// Red count badge after a link (TRD 11 UX-018, UX-411); nothing for 0. The number is drawn by CSS
// (`::before { content: attr(data-count) }`) so that the visible link text stays inside the link's
// accessible name ("Resident list, 2 alarms not reviewed"; WCAG 2.5.3, axe label-content-name-mismatch).
import styles from "./CountBadge.module.css";

export interface CountBadgeProps {
  count: number;
  label: string; // accessible-name suffix, read with the link text
}

export function CountBadge({ count, label }: CountBadgeProps) {
  if (count <= 0) return null;
  return (
    <span className={styles.badge}>
      <span aria-hidden="true" className={styles.count} data-count={count} />
      <span className="visually-hidden">{`, ${label}`}</span>
    </span>
  );
}
