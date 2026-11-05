// "Data problems to follow up" (TRD 11 UX-306..UX-309, UX-331). Data-quality signals, not health
// alarms: never the "▲" glyph and never red. The row text is the backend `detail` (D-114).
import Link from "next/link";
import { naturalCompare } from "@/lib/deviceGroups";
import type { DataAlert, Meta } from "@/lib/types";
import {
  STUDY_PROBLEMS_EMPTY,
  STUDY_PROBLEMS_HEADING,
  STUDY_PROBLEM_ORDER,
  STUDY_TAG_STAFF,
  studyProblemTag,
} from "@/lib/wording";
import styles from "./DataProblemsList.module.css";

export interface DataProblemsListProps {
  alerts: DataAlert[];
  meta: Meta;
}

const codeOf = (a: DataAlert) => a.resident_code ?? a.device_code ?? "";

/** Kind order of §4.18.2, then resident or device code in natural order (UX-307). */
export function orderDataProblems(alerts: readonly DataAlert[]): DataAlert[] {
  const rank = (a: DataAlert) => {
    const i = STUDY_PROBLEM_ORDER.indexOf(a.kind);
    return i < 0 ? STUDY_PROBLEM_ORDER.length : i;
  };
  return [...alerts].sort((a, b) => rank(a) - rank(b) || naturalCompare(codeOf(a), codeOf(b)));
}

function CodeLink({ alert }: { alert: DataAlert }) {
  const text = `${codeOf(alert)}:`;
  if (alert.resident_code) {
    return (
      <Link href={`/residents/${alert.resident_code}/log`} aria-label={alert.title}>
        {text}
      </Link>
    );
  }
  if (alert.device_code) {
    // A plain anchor: same-document hash navigation fires `hashchange`, which focuses the
    // Devices heading (TRD 04 FE-026).
    return (
      <a href="/study#devices" aria-label={alert.title}>
        {text}
      </a>
    );
  }
  return <>{text}</>;
}

// `meta` is part of the inventory props (TRD 04 §4.8); the row text needs no formatting from it.
export function DataProblemsList({ alerts }: DataProblemsListProps) {
  const rows = orderDataProblems(alerts);
  return (
    <section className="panel pad stack" aria-labelledby="data-problems-heading">
      <h2 id="data-problems-heading">{STUDY_PROBLEMS_HEADING}</h2>
      {rows.length === 0 ? (
        <p className="small muted">{STUDY_PROBLEMS_EMPTY}</p>
      ) : (
        <ul className={styles.list}>
          {rows.map((a) => {
            const tag = studyProblemTag(a.kind);
            return (
              <li key={a.id} className={styles.row} data-testid="data-problem">
                <span className={tag === STUDY_TAG_STAFF ? styles.tagStaff : styles.tagTeam}>
                  {tag}
                </span>
                <span>
                  <b>
                    <CodeLink alert={a} />
                  </b>{" "}
                  {a.detail}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
