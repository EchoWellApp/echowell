"use client";
// Route-level error boundary (TRD 04 FE-145): no error details.
import { RELOAD, SOMETHING_WRONG } from "@/lib/wording";

export default function ProtectedError() {
  return (
    <section className="panel pad stack">
      <h1>{SOMETHING_WRONG}</h1>
      <div>
        <button type="button" className="btn" onClick={() => window.location.reload()}>
          {RELOAD}
        </button>
      </div>
    </section>
  );
}
