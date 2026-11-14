"use client";
// Global error boundary (TRD 04 FE-145): no error details.
import "@/styles/globals.css";
import { RELOAD, SOMETHING_WRONG } from "@/lib/wording";

export default function GlobalError() {
  return (
    <html lang="en">
      <body>
        <main id="main">
          <section className="panel pad stack">
            <h1>{SOMETHING_WRONG}</h1>
            <div>
              <button type="button" className="btn" onClick={() => window.location.reload()}>
                {RELOAD}
              </button>
            </div>
          </section>
        </main>
      </body>
    </html>
  );
}
