// req: FE-032, FE-087, FE-093, FE-097, FE-183, FE-184, UX-080, UX-082, UX-089, UX-092, UX-100..UX-108, UX-202, UX-225, UX-243, UX-262, AC-UX-04, AC-UX-05, FEAT-067-AC-04, FEAT-067-AC-05, FEAT-067-AC-06, FEAT-067-AC-07, TST-094
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse, delay } from "msw";
import VoiceTrendsPage from "@/app/(protected)/residents/[residentCode]/trends/page";
import r07Scores from "@/tests/fixtures/ds07/resident/R07-scores.json";
import { API, problem } from "@/tests/msw/handlers";
import { server } from "@/tests/msw/server";
import { setLocation } from "@/tests/support/navigation";
import { renderSignedIn } from "@/tests/support/render";

function open(code: string, role: "clinician" | "admin" | "researcher" = "clinician") {
  setLocation(`/residents/${code}/trends`, "", { residentCode: code });
  return renderSignedIn(<VoiceTrendsPage />, role);
}

const scoreRegion = () => screen.getByRole("region", { name: "Change score" });

describe("/residents/[residentCode]/trends", () => {
  it("renders R09 (AC-UX-04, TRD 11 §4.13.3)", async () => {
    const { container } = open("R09");
    expect(await screen.findByRole("img", { name: /^Change score for R09/ })).toHaveAccessibleName(
      "Change score for R09 from Oct 17 to Oct 30. Baseline Oct 1–16. Alarm line 5. Crossed the alarm line on Oct 21; now 26.8.",
    );
    expect(document.title).toBe("R09 · Voice trends – EchoWell");
    expect(screen.queryByRole("heading", { level: 1 })).toBeNull();
    expect(screen.getByRole("heading", { level: 2, name: "Change score" })).toBeInTheDocument();
    expect(
      screen.getByText(
        "Goes up when check-ins keep leaning away from R09’s usual. The alarm turns on at 5. Missed, set-aside and held-back check-ins leave it unchanged.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("Baseline Oct 1–16")).toBeInTheDocument();
    const bars = [...container.querySelectorAll("[data-testid='score-bar'] rect")];
    expect(bars.map((b) => b.getAttribute("fill"))).toEqual([
      ...Array(4).fill("var(--c-aside)"),
      ...Array(10).fill("var(--red)"),
    ]);
    expect(screen.getByTestId("alarm-line-label")).toHaveTextContent("Alarm line: 5");
    expect(screen.getByTestId("alarm-tick")).toHaveTextContent("Oct 21 · alarm");
    expect(screen.getByRole("region", { name: "Change score chart" })).toHaveAttribute(
      "tabindex",
      "0",
    );
    // table alternative
    await userEvent.click(screen.getByText("Show change score as a table"));
    const table = screen.getByRole("table", { name: /R09/ });
    expect(
      within(table)
        .getAllByRole("row")
        .slice(1)
        .map((r) => within(r).getAllByRole("cell")[1]?.textContent),
    ).toEqual([
      "3.2",
      "2.6",
      "1.8",
      "1.6",
      "5.4",
      "8.0",
      "8.3",
      "10.7",
      "12.4",
      "15.3",
      "16.7",
      "18.8",
      "23.1",
      "26.8",
    ]);
    // measurements
    expect(await screen.findAllByTestId("feature-card")).toHaveLength(7);
    expect(screen.getByTestId("other-measurements-card")).toHaveTextContent(
      "12 other measurements (pitch, jitter, MFCCs and others)Stored, not scored",
    );
    expect(
      screen.getByRole("img", {
        name: "Quieter (loudness): latest +2.2 compared with own baseline over 14 scored check-ins",
      }),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText("Device period")).toBeNull();
    expect(screen.queryByText(/Showing the current device period/)).toBeNull();
  });

  it("renders R08 forming: no bars, the forming text, Not scored yet ×7 (AC-UX-05)", async () => {
    const { container } = open("R08");
    expect(
      await screen.findByText(
        "No change score yet. Scoring starts after the baseline is complete (13 of 16 usable check-ins so far).",
      ),
    ).toBeInTheDocument();
    expect(container.querySelectorAll("[data-testid='score-bar']")).toHaveLength(0);
    expect(screen.queryByText("Show change score as a table")).toBeNull();
    expect(await screen.findAllByText("Not scored yet")).toHaveLength(7);
  });

  it("renders R07: device-period line, Oct 13–28 slot, 2 stubs, and loads epoch 1 (FEAT-067-AC-04, AC-07)", async () => {
    const epochs: (string | null)[] = [];
    server.use(
      http.get(`${API}/scores`, ({ request }) => {
        const epoch = new URL(request.url).searchParams.get("epoch");
        epochs.push(epoch);
        if (epoch === "1") {
          return HttpResponse.json({ ...r07Scores, items: [], total: 0, baseline_periods: [] });
        }
        return HttpResponse.json(r07Scores);
      }),
    );
    const { container } = open("R07");
    expect(
      await screen.findByText(
        "Showing the current device period since Oct 13. Earlier periods are not scored against this baseline.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText("Baseline Oct 13–28")).toBeInTheDocument();
    const stubs = container.querySelectorAll("[data-testid='score-bar'] rect[data-stub='true']");
    expect(stubs).toHaveLength(2);
    const select = screen.getByLabelText("Device period");
    expect(
      within(select)
        .getAllByRole("option")
        .map((o) => o.textContent),
    ).toEqual(["Period 1", "Period 2 (current)"]);
    expect(select).toHaveValue("2");
    await userEvent.selectOptions(select, "1");
    expect(
      await screen.findByText("No check-ins were scored in this device period."),
    ).toBeVisible();
    expect(container.querySelectorAll("[data-testid='score-bar']")).toHaveLength(0);
    expect(screen.queryByText(/Showing the current device period/)).toBeNull();
    expect(epochs).toContain("1");
    await userEvent.selectOptions(select, "2");
    expect(await screen.findByText("Baseline Oct 13–28")).toBeInTheDocument();
    expect(epochs[0]).toBeNull();
  });

  it("shows loading states for both panels", async () => {
    server.use(
      http.get(`${API}/scores`, async () => {
        await delay("infinite");
        return HttpResponse.json({});
      }),
      http.get(`${API}/residents/:code/features`, async () => {
        await delay("infinite");
        return HttpResponse.json({});
      }),
    );
    open("R09");
    expect(await screen.findByText("Loading the change score…")).toBeInTheDocument();
    expect(screen.getByText("Loading the voice measurements…")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { level: 2, name: "The 7 voice measurements behind the score" }),
    ).toBeInTheDocument();
  });

  it("shows an error only in the change score panel when scores fail, with retry (FE-087)", async () => {
    let fail = true;
    server.use(
      http.get(`${API}/scores`, () =>
        fail ? problem(500, "INTERNAL", "Internal error") : HttpResponse.json(r07Scores),
      ),
    );
    open("R07");
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(
      "Could not load the change score. Check your connection and try again.",
    );
    expect(alert).toHaveTextContent("Reference: req-test-0001");
    expect(await screen.findAllByTestId("feature-card")).toHaveLength(7);
    fail = false;
    await userEvent.click(within(alert).getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("Baseline Oct 13–28")).toBeInTheDocument();
  });

  it("shows an error only in the measurement panel when features fail", async () => {
    let fail = true;
    server.use(
      http.get(`${API}/residents/:code/features`, async ({ params }) => {
        if (fail) return problem(500, "INTERNAL", "Internal error");
        const f = await import("@/tests/fixtures/ds07/resident/R09-features.json");
        return HttpResponse.json({ ...f.default, resident_code: params.code });
      }),
    );
    open("R09");
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(
      "Could not load the voice measurements. Check your connection and try again.",
    );
    expect(await screen.findByRole("img", { name: /^Change score for R09/ })).toBeInTheDocument();
    fail = false;
    await userEvent.click(within(alert).getByRole("button", { name: "Try again" }));
    expect(await screen.findAllByTestId("feature-card")).toHaveLength(7);
  });

  it("retries the resident query from either panel when it fails", async () => {
    let fail = true;
    server.use(
      http.get(`${API}/residents/:code`, async ({ params }) => {
        if (fail) return problem(500, "INTERNAL", "Internal error");
        const r = await import("@/tests/fixtures/ds07/resident/R09.json");
        return HttpResponse.json({ ...r.default, resident_code: params.code });
      }),
    );
    open("R09");
    const alerts = await screen.findAllByRole("alert");
    expect(alerts).toHaveLength(2);
    fail = false;
    await userEvent.click(
      within(alerts[0] as HTMLElement).getByRole("button", { name: "Try again" }),
    );
    expect(await screen.findByRole("img", { name: /^Change score for R09/ })).toBeInTheDocument();
    expect(await screen.findAllByTestId("feature-card")).toHaveLength(7);
  });

  it("retries the resident query from the measurement panel", async () => {
    let fail = true;
    server.use(
      http.get(`${API}/residents/:code`, async () => {
        if (fail) return problem(500, "INTERNAL", "Internal error");
        const r = await import("@/tests/fixtures/ds07/resident/R09.json");
        return HttpResponse.json(r.default);
      }),
    );
    open("R09");
    const alerts = await screen.findAllByRole("alert");
    fail = false;
    await userEvent.click(
      within(alerts[1] as HTMLElement).getByRole("button", { name: "Try again" }),
    );
    expect(await screen.findAllByTestId("feature-card")).toHaveLength(7);
  });

  it("shows no-access text on 403", async () => {
    server.use(
      http.get(`${API}/scores`, () => problem(403, "FORBIDDEN", "Forbidden")),
      http.get(`${API}/residents/:code/features`, () => problem(403, "FORBIDDEN", "Forbidden")),
    );
    open("R09", "researcher");
    await waitFor(() =>
      expect(screen.getAllByText("You do not have access to this information.")).toHaveLength(2),
    );
  });

  it("shows the baseline slot without bars when the baseline is frozen but nothing is scored", async () => {
    server.use(
      http.get(`${API}/scores`, () => HttpResponse.json({ ...r07Scores, items: [], total: 0 })),
    );
    const { container } = open("R07");
    expect(await screen.findByText("Baseline Oct 13–28")).toBeInTheDocument();
    expect(container.querySelectorAll("[data-testid='score-bar']")).toHaveLength(0);
    expect(scoreRegion()).toBeInTheDocument();
  });
});
