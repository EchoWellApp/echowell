// Access-denied state (TRD 04 FE-034, FE-037; TRD 11 UX-350).
import { NO_ACCESS_PAGE } from "@/lib/wording";
import { BackLink } from "../BackLink/BackLink";

export function AccessDenied() {
  return (
    <section className="panel pad stack" aria-labelledby="denied-heading">
      <h1 id="denied-heading">{NO_ACCESS_PAGE}</h1>
      <BackLink href="/residents" />
    </section>
  );
}
