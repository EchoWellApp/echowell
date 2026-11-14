// MSW handlers serving the DS-07 fixtures (TRD 04 §4.14). Tests override single handlers with
// `server.use(...)` for error, empty and role cases.
import { http, HttpResponse } from "msw";
import admissions from "../fixtures/ds07/admissions.json";
import alertsOpen from "../fixtures/ds07/alerts-open.json";
import analytics from "../fixtures/ds07/analytics.json";
import configUi from "../fixtures/ds07/config-ui.json";
import dataAlertsOpen from "../fixtures/ds07/data-alerts-open.json";
import devices from "../fixtures/ds07/devices.json";
import meAdmin from "../fixtures/ds07/me-admin.json";
import pipelineRuns from "../fixtures/ds07/pipeline-runs.json";
import residents from "../fixtures/ds07/residents.json";
import users from "../fixtures/ds07/users.json";
import { resident as residentFixture } from "./residentFixtures";

const resident = (code: string, part: string) =>
  residentFixture(code, part) as Record<string, unknown> | undefined;

export const API = "http://localhost:8000/api/v1";

export function problem(status: number, code: string, title: string, extra: object = {}) {
  return HttpResponse.json(
    {
      type: `urn:echowell:error:${code}`,
      title,
      status,
      detail: title,
      request_id: "req-test-0001",
      errors: [],
      ...extra,
    },
    { status, headers: { "Content-Type": "application/problem+json" } },
  );
}

const notFound = () => problem(404, "RESIDENT_NOT_FOUND", "Resident not found");

export const handlers = [
  http.post(`${API}/auth/login`, () =>
    HttpResponse.json({
      access_token: fakeJwt(),
      token_type: "bearer",
      expires_in: 3600,
      user: meAdmin,
    }),
  ),
  http.post(`${API}/auth/logout`, () => new HttpResponse(null, { status: 204 })),
  http.get(`${API}/auth/me`, () => HttpResponse.json(meAdmin)),
  http.get(`${API}/config/ui`, () => HttpResponse.json(configUi)),
  http.get(`${API}/residents`, () => HttpResponse.json(residents)),
  http.get(`${API}/residents/:code`, ({ params }) => {
    const body = resident(String(params.code), "");
    return body ? HttpResponse.json(body) : notFound();
  }),
  http.get(`${API}/residents/:code/:part`, ({ params }) => {
    const body = resident(String(params.code), String(params.part));
    return body ? HttpResponse.json(body) : notFound();
  }),
  http.get(`${API}/scores`, ({ request }) => {
    const code = new URL(request.url).searchParams.get("resident_code") ?? "";
    const body = resident(code, "scores");
    return body ? HttpResponse.json(body) : notFound();
  }),
  http.get(`${API}/alerts`, ({ request }) => {
    const params = new URL(request.url).searchParams;
    const code = params.get("resident_code");
    if (code) return HttpResponse.json(resident(code, "alerts") ?? { items: [], total: 0 });
    return HttpResponse.json(alertsOpen);
  }),
  http.get(`${API}/alerts/:id/reviews`, ({ params }) => {
    for (const code of ["R09", "R10"]) {
      const alerts = resident(code, "alerts") as unknown as { items: { id: string }[] };
      if (alerts.items.some((a) => a.id === params.id))
        return HttpResponse.json(resident(code, "reviews"));
    }
    return HttpResponse.json({ items: [], total: 0, limit: 50, offset: 0 });
  }),
  http.get(`${API}/data-alerts`, () => HttpResponse.json(dataAlertsOpen)),
  http.get(`${API}/devices`, () => HttpResponse.json(devices)),
  http.get(`${API}/analytics`, () => HttpResponse.json(analytics)),
  http.get(`${API}/admissions`, () => HttpResponse.json(admissions)),
  http.get(`${API}/pipeline/runs`, () => HttpResponse.json(pipelineRuns)),
  http.get(`${API}/users`, () => HttpResponse.json(users)),
  http.get(`${API}/health`, () =>
    HttpResponse.json({
      status: "ok",
      database: "ok",
      version: "test",
      time: "2026-10-30T20:00:00Z",
    }),
  ),
];

/** An unsigned JWT whose `exp` is one hour from now (the frontend never verifies signatures). */
export function fakeJwt(expSeconds: number = Math.floor(Date.now() / 1000) + 3600): string {
  const b64 = (o: object) =>
    btoa(JSON.stringify(o)).replace(/=+$/, "").replace(/\+/g, "-").replace(/\//g, "_");
  return `${b64({ alg: "HS256", typ: "JWT" })}.${b64({ sub: "u", exp: expSeconds })}.sig`;
}
