// req: UX-207, UX-210..UX-219, UX-227, UX-228, UX-229, FE-032, FE-034, FE-079, FEAT-074-AC-01..AC-08
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import AdminPage from "@/app/(protected)/admin/page";
import ProtectedLayout from "@/app/(protected)/layout";
import type { PipelineRun, PipelineRunList } from "@/lib/types";
import pipelineRuns from "@/tests/fixtures/ds07/pipeline-runs.json";
import { API, problem } from "@/tests/msw/handlers";
import { server } from "@/tests/msw/server";
import { nav, setLocation } from "@/tests/support/navigation";
import { renderSignedIn } from "@/tests/support/render";

const runs = pipelineRuns as PipelineRunList;
const baseRun = runs.items[0] as PipelineRun;
// "Now" for the nightly banner: Oct 31, 2026, 10:00 AM CT.
const NOW = new Date("2026-10-31T15:00:00Z");

function runsWith(items: PipelineRun[]) {
  server.use(
    http.get(`${API}/pipeline/runs`, () =>
      HttpResponse.json({ ...runs, items, total: items.length }),
    ),
  );
}

function renderAdmin(search = "", role: "admin" | "clinician" | "researcher" = "admin") {
  setLocation("/admin", search);
  return renderSignedIn(
    <ProtectedLayout>
      <AdminPage />
    </ProtectedLayout>,
    role,
  );
}

const tab = (name: string) => screen.getByRole("tab", { name });

describe("/admin", () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(NOW);
    nav.router.replace.mockClear();
  });
  afterEach(() => vi.useRealTimers());

  it.each(["clinician", "researcher"] as const)(
    "denies %s with no admin API call (FE-034, UX-215)",
    async (role) => {
      const paths: string[] = [];
      const spy = ({ request }: { request: Request }) => {
        paths.push(new URL(request.url).pathname);
      };
      server.events.on("request:start", spy);
      renderAdmin("", role);
      expect(
        await screen.findByRole("heading", {
          level: 1,
          name: "You do not have access to this page.",
        }),
      ).toBeVisible();
      expect(screen.getByRole("link", { name: "← Resident list" })).toHaveAttribute(
        "href",
        "/residents",
      );
      await screen.findByText("Edgewood, Assisted living");
      server.events.removeListener("request:start", spy);
      expect(paths.filter((p) => /\/(users|pipeline|ingest|health)/.test(p))).toEqual([]);
      expect(screen.queryByRole("tablist")).toBeNull();
    },
  );

  it("shows the header, tabs, users, nightly banner and API status (AC-08, UX-216, UX-219)", async () => {
    renderAdmin();
    expect(await screen.findByRole("heading", { level: 1, name: "Admin" })).toBeVisible();
    expect(document.title).toBe("Admin – EchoWell");
    expect(await screen.findByRole("link", { name: "Admin" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByTestId("data-bar")).toBeVisible();
    expect(screen.getAllByRole("tab").map((t) => t.textContent)).toEqual([
      "Users",
      "Pipeline runs",
      "Upload data",
    ]);
    expect(tab("Users")).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tabpanel", { name: "Users" })).toBeVisible();
    expect(await screen.findByText("Nightly run missing for Oct 31")).toBeVisible();

    const table = await screen.findByRole("table");
    expect(
      within(table)
        .getAllByRole("columnheader")
        .map((h) => h.textContent),
    ).toEqual(["Email", "Display name", "Role", "Active", "Last sign-in", "Actions"]);
    const clin = screen.getByText("clinician@example.com").closest("tr") as HTMLElement;
    expect(within(clin).getByText("Never")).toBeVisible();
    expect(within(clin).getByText("Yes")).toBeVisible();
    expect(
      within(clin).getByRole("combobox", { name: "Role for clinician@example.com" }),
    ).toHaveValue("clinician");
    const adminRow = screen.getByText("admin@example.com").closest("tr") as HTMLElement;
    expect(within(adminRow).getByText("Nov 2, 4:40 PM CT")).toBeVisible();

    expect(await screen.findByText("API status: ok · version test")).toBeVisible();
    // UX-218: no master-data editing
    expect(screen.queryByRole("button", { name: /resident|device|api key/i })).toBeNull();
    expect(screen.queryByRole("link", { name: /device|api key/i })).toBeNull();
  });

  it("moves between tabs with the arrow keys and keeps ?tab= (UX-210)", async () => {
    renderAdmin();
    await screen.findByRole("tablist");
    tab("Users").focus();
    await userEvent.keyboard("{ArrowRight}");
    expect(tab("Pipeline runs")).toHaveAttribute("aria-selected", "true");
    expect(tab("Pipeline runs")).toHaveFocus();
    expect(nav.router.replace).toHaveBeenLastCalledWith("/admin?tab=runs", { scroll: false });
    await userEvent.keyboard("{End}");
    expect(tab("Upload data")).toHaveFocus();
    await userEvent.keyboard("{ArrowRight}");
    expect(tab("Users")).toHaveFocus();
    await userEvent.keyboard("{ArrowLeft}");
    expect(tab("Upload data")).toHaveAttribute("aria-selected", "true");
    await userEvent.keyboard("{Home}");
    expect(tab("Users")).toHaveAttribute("aria-selected", "true");
    expect(tab("Pipeline runs")).toHaveAttribute("tabindex", "-1");
    await userEvent.keyboard("a");
    expect(tab("Users")).toHaveAttribute("aria-selected", "true");
    await userEvent.click(tab("Upload data"));
    expect(nav.router.replace).toHaveBeenLastCalledWith("/admin?tab=upload", { scroll: false });
  });

  describe("Pipeline runs", () => {
    it("lists runs newest first and hides the nightly banner after a recent nightly run (AC-01)", async () => {
      const nightly: PipelineRun = {
        ...baseRun,
        id: "run-nightly",
        trigger: "nightly",
        started_at: "2026-10-31T07:00:00Z",
        finished_at: null,
        status: "succeeded",
        warnings: [{ code: "late_arrival", detail: null, resident_code: "R01", session_id: null }],
      };
      const older: PipelineRun = {
        ...baseRun,
        id: "run-old",
        started_at: "2026-10-29T07:00:00Z",
        counts: {},
      };
      runsWith([older, nightly]);
      renderAdmin("tab=runs");
      const region = await screen.findByRole("region", { name: "Pipeline runs table" });
      const rows = within(region).getAllByRole("row");
      expect(Array.from(rows[0]!.children).map((c) => c.textContent)).toEqual([
        "Started",
        "Finished",
        "Trigger",
        "Profile",
        "Status",
        "As of",
        "Counts",
        "Warnings",
      ]);
      expect(Array.from(rows[1]!.children).map((c) => c.textContent)).toEqual([
        "Oct 31, 2:00 AM CT",
        "—",
        "Nightly",
        "test_v0_1",
        "Succeeded",
        "Oct 30, 2026, 3:00 PM CT",
        "Arrivals 283 · Usable 267 · Scored 98 · Residents 10 · Alarms opened 2",
        "1",
      ]);
      expect(rows[2]).toHaveTextContent("Manual");
      expect(rows[2]).toHaveTextContent("—");
      expect(screen.queryByText(/Nightly run missing/)).toBeNull();
      expect(screen.queryByText(/latest pipeline run failed/)).toBeNull();
    });

    it("shows a banner when the latest run failed (LOG-112)", async () => {
      runsWith([{ ...baseRun, status: "failed", started_at: "2026-10-31T14:00:00Z" }]);
      renderAdmin("tab=runs");
      expect(
        await screen.findByText("The latest pipeline run failed (started Oct 31, 9:00 AM CT)."),
      ).toBeVisible();
    });

    it("starts a run with the environment profile and follows it (UX-212)", async () => {
      let body: unknown = null;
      server.use(
        http.post(`${API}/pipeline/run`, async ({ request }) => {
          body = await request.json();
          return HttpResponse.json({ pipeline_run_id: "new-run" }, { status: 202 });
        }),
        http.get(`${API}/pipeline/runs/:id`, () =>
          HttpResponse.json({ ...baseRun, id: "new-run", status: "succeeded" }),
        ),
      );
      renderAdmin("tab=runs");
      const select = await screen.findByRole("combobox", { name: "Profile" });
      await waitFor(() => expect(select).toBeEnabled());
      expect(
        within(select)
          .getAllByRole("option")
          .map((o) => o.textContent),
      ).toEqual(["test_v0_1"]);
      await userEvent.click(screen.getByRole("button", { name: "Run pipeline now" }));
      expect(await screen.findByText("Pipeline run succeeded.")).toBeVisible();
      expect(body).toEqual({ scope: "all", profile: "test_v0_1" });
    });

    it("shows a running run while it is polled", async () => {
      server.use(
        http.post(`${API}/pipeline/run`, () =>
          HttpResponse.json({ pipeline_run_id: "new-run" }, { status: 202 }),
        ),
        http.get(`${API}/pipeline/runs/:id`, () =>
          HttpResponse.json({ ...baseRun, id: "new-run", status: "running", finished_at: null }),
        ),
      );
      renderAdmin("tab=runs");
      const button = await screen.findByRole("button", { name: "Run pipeline now" });
      await waitFor(() => expect(button).toBeEnabled());
      await userEvent.click(button);
      expect(
        await screen.findByText(
          "Pipeline run started. Status: Running (refreshed every 5 seconds).",
        ),
      ).toBeVisible();
    });

    it.each([
      [
        409,
        "PIPELINE_RUN_IN_PROGRESS",
        "A pipeline run is already in progress. Try again when it has finished.",
      ],
      [422, "PROFILE_NOT_ALLOWED", "This profile is not allowed in this environment."],
      [500, "INTERNAL", "Could not start the pipeline run. Check your connection and try again."],
    ])("shows %s %s as a message", async (status, code, text) => {
      server.use(http.post(`${API}/pipeline/run`, () => problem(status, code, "x")));
      renderAdmin("tab=runs");
      const button = await screen.findByRole("button", { name: "Run pipeline now" });
      await waitFor(() => expect(button).toBeEnabled());
      await userEvent.click(button);
      expect(await screen.findByText(text)).toBeVisible();
    });

    it("shows the empty and error states", async () => {
      runsWith([]);
      const { unmount } = renderAdmin("tab=runs");
      expect(await screen.findByText("No pipeline runs yet.")).toBeVisible();
      unmount();
      server.use(http.get(`${API}/pipeline/runs`, () => problem(500, "INTERNAL", "x")));
      renderAdmin("tab=runs");
      expect(
        await screen.findByText(
          "Could not load pipeline runs. Check your connection and try again.",
        ),
      ).toBeVisible();
    });
  });

  describe("Users", () => {
    async function fillForm(email: string) {
      await userEvent.type(await screen.findByLabelText("Email"), email);
      await userEvent.type(screen.getByLabelText("Display name"), "New User");
      await userEvent.selectOptions(screen.getByLabelText("Role"), "researcher");
      await userEvent.type(screen.getByLabelText("Temporary password"), "a-long-temp-password");
    }

    it("adds a user and clears the form (UX-211, UX-228)", async () => {
      let body: unknown = null;
      server.use(
        http.post(`${API}/users`, async ({ request }) => {
          body = await request.json();
          return HttpResponse.json(
            {
              ...(body as object),
              id: "u-new",
              active: true,
              last_login_at: null,
              created_at: NOW.toISOString(),
            },
            { status: 201 },
          );
        }),
      );
      renderAdmin();
      expect(await screen.findByRole("heading", { level: 3, name: "Add user" })).toBeVisible();
      expect(
        within(screen.getByLabelText("Role"))
          .getAllByRole("option")
          .map((o) => o.textContent),
      ).toEqual(["Admin", "Clinician", "Researcher"]);
      await fillForm("new@example.com");
      await userEvent.click(screen.getByRole("button", { name: "Add user" }));
      expect(await screen.findByText("new@example.com was added.")).toBeVisible();
      expect(body).toEqual({
        email: "new@example.com",
        display_name: "New User",
        role: "researcher",
        password: "a-long-temp-password",
      });
      expect(screen.getByLabelText("Temporary password")).toHaveValue("");
    });

    it("shows a 409 under the Email field (AC-05, FE-079, UX-207, UX-227)", async () => {
      server.use(http.post(`${API}/users`, () => problem(409, "EMAIL_ALREADY_EXISTS", "x")));
      renderAdmin();
      await fillForm("clinician@example.com");
      await userEvent.click(screen.getByRole("button", { name: "Add user" }));
      const msg = await screen.findByText("A user with this email already exists.");
      const email = screen.getByLabelText("Email");
      expect(email).toHaveAttribute("aria-invalid", "true");
      expect(email).toHaveAttribute("aria-describedby", msg.id);
      expect(email).toHaveAccessibleDescription("A user with this email already exists.");
    });

    it("maps errors[] to fields and other errors above the button", async () => {
      server.use(
        http.post(`${API}/users`, () =>
          problem(422, "PASSWORD_POLICY_VIOLATION", "x", {
            errors: [
              { field: "body.password", code: "too_short", message: "Use at least 12 characters." },
            ],
          }),
        ),
      );
      renderAdmin();
      await fillForm("x@example.com");
      await userEvent.click(screen.getByRole("button", { name: "Add user" }));
      expect(await screen.findByText("Use at least 12 characters.")).toBeVisible();
      expect(screen.getByLabelText("Temporary password")).toHaveAccessibleDescription(
        "Use at least 12 characters.",
      );
      server.use(http.post(`${API}/users`, () => problem(500, "INTERNAL", "x")));
      await userEvent.click(screen.getByRole("button", { name: "Add user" }));
      expect(
        await screen.findByText("Could not save. Check your connection and try again."),
      ).toBeVisible();
    });

    it("requires every field before sending", async () => {
      renderAdmin();
      await userEvent.click(await screen.findByRole("button", { name: "Add user" }));
      expect(screen.getAllByText("This field is required.")).toHaveLength(3);
      expect(screen.getByLabelText("Email")).toHaveAccessibleDescription("This field is required.");
    });

    it("asks before deactivating and sends PATCH (AC-05)", async () => {
      const patches: unknown[] = [];
      server.use(
        http.patch(`${API}/users/:id`, async ({ request, params }) => {
          const patch = (await request.json()) as object;
          patches.push({ id: params.id, ...patch });
          return HttpResponse.json({
            id: params.id,
            email: "clinician@example.com",
            display_name: "Clinician",
            role: "clinician",
            active: false,
            last_login_at: null,
            created_at: NOW.toISOString(),
          });
        }),
      );
      renderAdmin();
      await userEvent.click(
        await screen.findByRole("button", { name: "Deactivate clinician@example.com" }),
      );
      const dialog = screen.getByRole("alertdialog");
      expect(dialog).toHaveTextContent(
        "Deactivate clinician@example.com? They will not be able to sign in.",
      );
      expect(within(dialog).getByRole("button", { name: "Cancel" })).toHaveFocus();
      await userEvent.click(within(dialog).getByRole("button", { name: "Cancel" }));
      expect(screen.queryByRole("alertdialog")).toBeNull();
      expect(patches).toEqual([]);
      await userEvent.click(
        screen.getByRole("button", { name: "Deactivate clinician@example.com" }),
      );
      await userEvent.click(
        within(screen.getByRole("alertdialog")).getByRole("button", { name: "Deactivate" }),
      );
      expect(await screen.findByText("clinician@example.com updated.")).toBeVisible();
      expect(patches).toEqual([{ id: "9cdbb2dc-0b12-4f24-a38c-818e4017f29f", active: false }]);
    });

    it("reactivates, changes a role and shows LAST_ADMIN", async () => {
      const users = (await import("@/tests/fixtures/ds07/users.json")).default;
      server.use(
        http.get(`${API}/users`, () =>
          HttpResponse.json({
            ...users,
            items: users.items.map((u) =>
              u.email === "researcher@example.com" ? { ...u, active: false } : u,
            ),
          }),
        ),
        http.patch(`${API}/users/:id`, async ({ request, params }) => {
          const patch = (await request.json()) as { role?: string };
          if (patch.role === "clinician") return problem(409, "LAST_ADMIN", "x");
          return HttpResponse.json({ ...users.items[2], id: params.id, ...patch });
        }),
      );
      renderAdmin();
      const researcher = (await screen.findByText("researcher@example.com")).closest(
        "tr",
      ) as HTMLElement;
      expect(within(researcher).getByText("No")).toBeVisible();
      await userEvent.click(
        within(researcher).getByRole("button", { name: "Reactivate researcher@example.com" }),
      );
      expect(await screen.findByText("researcher@example.com updated.")).toBeVisible();
      await userEvent.selectOptions(
        screen.getByRole("combobox", { name: "Role for admin@example.com" }),
        "clinician",
      );
      expect(await screen.findByText("At least one active admin must remain.")).toBeVisible();
    });

    it("shows the users loading and empty states", async () => {
      const users = (await import("@/tests/fixtures/ds07/users.json")).default;
      server.use(
        http.get(`${API}/users`, () => HttpResponse.json({ ...users, items: [], total: 0 })),
      );
      renderAdmin();
      expect(await screen.findByText("Loading users…")).toBeVisible();
      expect(await screen.findByText("No users yet.")).toBeVisible();
    });
  });

  describe("Upload data", () => {
    const csv = () => new File(["session_id\n"], "src05.csv", { type: "text/csv" });

    it("states the synthetic-data rule and requires a file (UX-214, AC-06)", async () => {
      renderAdmin("tab=upload");
      expect(
        await screen.findByText("Only synthetic or test data may be uploaded to this environment."),
      ).toBeVisible();
      const input = screen.getByLabelText("CSV file (pipeline input format v0.1)");
      expect(input).toHaveAttribute("accept", ".csv,text/csv");
      await userEvent.click(screen.getByRole("button", { name: "Upload" }));
      expect(input).toHaveAccessibleDescription("Choose a CSV file first.");
    });

    it("uploads and shows the batch result and rejections (UX-213, AC-03)", async () => {
      server.use(
        http.post(`${API}/ingest`, () =>
          HttpResponse.json(
            {
              ingest_batch_id: "b1",
              accepted: 283,
              rejected: 1,
              duplicates: 2,
              pipeline_run_id: null,
              source: "csv",
            },
            { status: 202 },
          ),
        ),
        http.get(`${API}/ingest/batches/:id`, () =>
          HttpResponse.json({
            id: "b1",
            accepted_count: 283,
            rejected_count: 1,
            duplicate_count: 2,
            filename: "src05.csv",
            pipeline_run_id: null,
            received_at: NOW.toISOString(),
            record_count: 284,
            source: "csv",
            uploaded_by: null,
            rejections: [
              {
                row_number: 7,
                session_id: null,
                received_at: NOW.toISOString(),
                errors: [
                  { field: "loudness_dbfs", code: "float_parsing", message: "Not a number." },
                  {
                    field: "resident_code",
                    code: "unknown_resident",
                    message: "Unknown resident.",
                  },
                ],
              },
            ],
          }),
        ),
      );
      renderAdmin("tab=upload");
      await userEvent.upload(
        await screen.findByLabelText("CSV file (pipeline input format v0.1)"),
        csv(),
      );
      await userEvent.click(screen.getByRole("button", { name: "Upload" }));
      expect(await screen.findByText("Accepted 283 · Rejected 1 · Duplicates 2")).toBeVisible();
      const table = await screen.findByRole("table", { name: "Rejected rows" });
      expect(
        within(table)
          .getAllByRole("row")
          .map((r) => Array.from(r.children).map((c) => c.textContent)),
      ).toEqual([
        ["Row", "Errors"],
        ["7", "Not a number.; Unknown resident."],
      ]);
    });

    it("shows a whole-file rejection (UX-217, AC-04)", async () => {
      server.use(
        http.post(`${API}/ingest`, () =>
          problem(422, "CSV_HEADER_MISMATCH", "CSV header does not match schema v0.1", {
            detail: "The CSV header does not match schema v0.1.",
            errors: [
              { field: "header", code: "missing_column", message: "Missing column loudness_dbfs." },
            ],
          }),
        ),
      );
      renderAdmin("tab=upload");
      await userEvent.upload(
        await screen.findByLabelText("CSV file (pipeline input format v0.1)"),
        csv(),
      );
      await userEvent.click(screen.getByRole("button", { name: "Upload" }));
      expect(
        await screen.findByText(
          "The file was not accepted: The CSV header does not match schema v0.1. Nothing was stored.",
        ),
      ).toBeVisible();
      expect(screen.getByText("Missing column loudness_dbfs.")).toBeVisible();
    });

    it("shows a network error with its reference", async () => {
      server.use(http.post(`${API}/ingest`, () => problem(500, "INTERNAL", "x")));
      renderAdmin("tab=upload");
      await userEvent.upload(
        await screen.findByLabelText("CSV file (pipeline input format v0.1)"),
        csv(),
      );
      await userEvent.click(screen.getByRole("button", { name: "Upload" }));
      expect(
        await screen.findByText("Could not upload the file. Check your connection and try again."),
      ).toBeVisible();
      expect(screen.getByText("Reference: req-test-0001")).toBeVisible();
    });
  });

  describe("API status (UX-216)", () => {
    it("reads degraded on 503", async () => {
      server.use(
        http.get(`${API}/health`, () =>
          HttpResponse.json(
            {
              status: "degraded",
              database: "unavailable",
              version: "1.2.3",
              time: NOW.toISOString(),
            },
            { status: 503 },
          ),
        ),
      );
      renderAdmin();
      expect(await screen.findByTestId("api-status")).toBeInTheDocument();
      await waitFor(() =>
        expect(screen.getByTestId("api-status").textContent).toMatch(
          /^API status: degraded \(database unavailable\)/,
        ),
      );
    });

    it("reads degraded with its version from a degraded body", async () => {
      server.use(
        http.get(`${API}/health`, () =>
          HttpResponse.json({
            status: "degraded",
            database: "unavailable",
            version: "1.2.3",
            time: NOW.toISOString(),
          }),
        ),
      );
      renderAdmin();
      expect(
        await screen.findByText("API status: degraded (database unavailable) · version 1.2.3"),
      ).toBeVisible();
    });

    it("reads unavailable when unreachable", async () => {
      server.use(http.get(`${API}/health`, () => HttpResponse.error()));
      renderAdmin();
      expect(await screen.findByText("API status: unavailable")).toBeVisible();
    });
  });
});
