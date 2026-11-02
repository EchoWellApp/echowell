// req: FE-070, FE-071, FE-072, FE-073, FE-074, FE-056, FE-076, FE-080
import { http, HttpResponse } from "msw";
import { clearToken, getToken, setToken } from "@/lib/auth";
import { retryDelay, shouldRetry } from "@/lib/queryClient";
import * as api from "@/services/api";
import { API, fakeJwt, problem } from "../msw/handlers";
import { server } from "../msw/server";

describe("api client", () => {
  afterEach(() => {
    api.setUnauthorizedHandler(null);
    clearToken();
  });

  it("sends Accept, Bearer and X-Request-ID to ${base}/api/v1 (FE-070, FE-071)", async () => {
    const seen: Headers[] = [];
    let url = "";
    server.use(
      http.get(`${API}/residents`, ({ request }) => {
        seen.push(request.headers);
        url = request.url;
        return HttpResponse.json({ items: [] });
      }),
    );
    setToken(fakeJwt());
    await api.getResidents();
    expect(url).toBe(
      `${API}/residents?sort=alarm&cohort=longitudinal&include_withdrawn=false&limit=500&offset=0`,
    );
    expect(seen[0]?.get("Accept")).toBe("application/json");
    expect(seen[0]?.get("Authorization")).toMatch(/^Bearer /);
    expect(seen[0]?.get("X-Request-ID")).toMatch(/[0-9a-f-]{36}/);
  });

  it("parses problem+json into ApiError (FE-073)", async () => {
    server.use(
      http.get(`${API}/residents/:code`, () =>
        problem(422, "VALIDATION_ERROR", "Invalid", {
          errors: [{ field: "body", code: "too_long", message: "Too long" }],
        }),
      ),
    );
    const error = await api.getResident("R09").catch((e: unknown) => e);
    expect(error).toBeInstanceOf(api.ApiError);
    const e = error as api.ApiError;
    expect([e.status, e.code, e.title, e.requestId]).toEqual([
      422,
      "VALIDATION_ERROR",
      "Invalid",
      "req-test-0001",
    ]);
    expect(e.errors[0]?.field).toBe("body");
  });

  it("maps a non-JSON error to UNKNOWN", async () => {
    server.use(http.get(`${API}/devices`, () => new HttpResponse("boom", { status: 502 })));
    const e = (await api.getDevices().catch((x: unknown) => x)) as api.ApiError;
    expect([e.status, e.code]).toEqual([502, "UNKNOWN"]);
    expect(e.requestId).toBeTruthy();
  });

  it("maps a problem without a urn type to UNKNOWN", async () => {
    server.use(
      http.get(`${API}/devices`, () =>
        HttpResponse.json(
          { title: "x", type: "about:blank" },
          { status: 400, headers: { "Content-Type": "application/problem+json" } },
        ),
      ),
    );
    const e = (await api.getDevices().catch((x: unknown) => x)) as api.ApiError;
    expect(e.code).toBe("UNKNOWN");
  });

  it("maps network failures to status 0 (FE-074)", async () => {
    server.use(http.get(`${API}/analytics`, () => HttpResponse.error()));
    const e = (await api.getAnalytics().catch((x: unknown) => x)) as api.ApiError;
    expect([e.status, e.title]).toEqual([0, "Network error"]);
  });

  it("clears the token and calls the handler on 401 (FE-056)", async () => {
    const handler = vi.fn();
    api.setUnauthorizedHandler(handler);
    setToken(fakeJwt());
    server.use(http.get(`${API}/devices`, () => problem(401, "UNAUTHORIZED", "Unauthorized")));
    await api.getDevices().catch(() => undefined);
    expect(getToken()).toBeNull();
    expect(handler).toHaveBeenCalledOnce();
  });

  it("does not redirect on a failed login (no token yet)", async () => {
    const handler = vi.fn();
    api.setUnauthorizedHandler(handler);
    server.use(http.post(`${API}/auth/login`, () => problem(401, "INVALID_CREDENTIALS", "Wrong")));
    await api.login("a@example.com", "x").catch(() => undefined);
    expect(handler).not.toHaveBeenCalled();
  });

  it("ignores logout errors (FE-058)", async () => {
    server.use(http.post(`${API}/auth/logout`, () => HttpResponse.error()));
    await expect(api.logout()).resolves.toBeUndefined();
  });

  it("calls the remaining endpoints with their paths", async () => {
    const calls: string[] = [];
    server.use(
      http.all(`${API}/*`, ({ request }) => {
        const u = new URL(request.url);
        calls.push(`${request.method} ${u.pathname.replace("/api/v1", "")}${u.search}`);
        if (request.headers.get("Accept") === "text/csv")
          return new HttpResponse("a,b\n", { headers: { "Content-Type": "text/csv" } });
        return HttpResponse.json({});
      }),
    );
    setToken(fakeJwt());
    await api.getCheckins("R 1", { from: "2026-10-01" });
    await api.getFeatures("R09");
    await api.getScores({ residentCode: "R09", epoch: 2 });
    await api.getNotes("R09");
    await api.createNote("R09", { note_type: "observation", body: "x" });
    await api.getAlerts({ residentCode: "R09" });
    await api.getDataAlerts({ status: "open" });
    await api.getAlertReviews("a1");
    await api.createAlertReview("a1", { explanations: [], outcome: "no_concern" });
    await api.snoozeAlert("a1");
    await api.getAdmissions();
    await api.getAdmissionComparison("R11");
    await api.getReferenceRanges();
    expect(await (await api.downloadScoresCsv({ residentCode: "R09" })).text()).toBe("a,b\n");
    await api.downloadBaselinesCsv();
    await api.listPipelineRuns();
    await api.getPipelineRun("p1");
    await api.triggerPipelineRun({ scope: "all" });
    await api.uploadIngestCsv(new File(["x"], "x.csv", { type: "text/csv" }));
    await api.getIngestBatch("b1");
    await api.listUsers();
    await api.createUser({
      email: "n@example.com",
      display_name: "N",
      role: "clinician",
      password: "p",
    } as never);
    await api.updateUser("u1", { active: false });
    await api.getHealth();
    await api.getUiConfig();
    expect(calls).toContain("GET /residents/R%201/checkins?from=2026-10-01&limit=500&offset=0");
    expect(calls).toContain("GET /scores?resident_code=R09&epoch=2");
    expect(calls).toContain("POST /alerts/a1/snooze");
    expect(calls).toContain("GET /devices?limit=500&offset=0".replace("devices", "admissions"));
    expect(calls).toContain("PATCH /users/u1");
    expect(calls).toContain("POST /ingest");
  });
});

describe("query retries (FE-080)", () => {
  it("retries network and 5xx errors at most twice", () => {
    expect(shouldRetry(0, new api.ApiError({ status: 0, title: "x" }))).toBe(true);
    expect(shouldRetry(1, new api.ApiError({ status: 503, title: "x" }))).toBe(true);
    expect(shouldRetry(2, new api.ApiError({ status: 503, title: "x" }))).toBe(false);
    expect(shouldRetry(0, new api.ApiError({ status: 403, title: "x" }))).toBe(false);
    expect(shouldRetry(0, new Error("x"))).toBe(false);
    expect([retryDelay(0), retryDelay(1)]).toEqual([1000, 2000]);
  });
});
