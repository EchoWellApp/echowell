// Global 404 (TRD 04 §4.2, FE-206).
import Link from "next/link";
import { BACK_TO_LIST, PAGE_NOT_FOUND } from "@/lib/wording";

export default function NotFound() {
  return (
    <main id="main">
      <section className="panel pad stack">
        <h1>{PAGE_NOT_FOUND}</h1>
        <Link href="/residents">{BACK_TO_LIST}</Link>
      </section>
    </main>
  );
}
