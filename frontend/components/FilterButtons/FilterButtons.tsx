// "Show" group of filter toggle buttons with API counts (TRD 11 UX-401..UX-404, TRD 04 FE-082).
import { useState } from "react";
import type { ResidentsResponse } from "@/lib/types";
import {
  LIST_FILTERS,
  LIST_FILTER_GROUP,
  filterButtonText,
  showingAnnouncement,
  type ListFilter,
} from "@/lib/wording";
import styles from "./FilterButtons.module.css";

export interface FilterButtonsProps {
  /** API `summary`; undefined while the list loads (counts show "—"). */
  summary: ResidentsResponse["summary"] | undefined;
  /** API `total` (the "All" count). */
  total: number | undefined;
  value: ListFilter;
  onChange(v: ListFilter): void;
}

export function FilterButtons({ summary, total, value, onChange }: FilterButtonsProps) {
  const [announcement, setAnnouncement] = useState("");
  const count = (f: ListFilter): number | null => {
    if (f === "all") return total ?? null;
    return summary ? summary[f] : null;
  };
  const shown = LIST_FILTERS.filter((f) => f !== "learning" || (summary?.learning ?? 0) > 0);
  return (
    <>
      <div className={styles.filters} role="group" aria-label={LIST_FILTER_GROUP}>
        {shown.map((f) => (
          <button
            key={f}
            type="button"
            className={styles.button}
            aria-pressed={value === f}
            onClick={() => {
              setAnnouncement(showingAnnouncement(f));
              if (f !== value) onChange(f);
            }}
          >
            {filterButtonText(f, count(f))}
          </button>
        ))}
      </div>
      <p className="visually-hidden" role="status" aria-live="polite" data-testid="filter-live">
        {announcement}
      </p>
    </>
  );
}
