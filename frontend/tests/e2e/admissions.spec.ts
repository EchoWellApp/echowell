// req: FE-189, E2E-13, UX-181, UX-264, FEAT-076-FR-04
// New admissions page with the DS-07 seed (TRD 11 §4.13.5).
import { test, expect } from "./fixtures";

test("E2E-13 / FE-189 experimental note and empty state", async ({ page, as }) => {
  await as("clinician");
  await page.goto("/admissions");
  await expect(page).toHaveTitle("New admissions – EchoWell");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("New admissions");
  await expect(
    page.getByText(
      "Future / experimental. Not in pipeline test v0.1: the test data has no admission group or facility range yet. Open question for Shaba and the PI.",
      { exact: true },
    ),
  ).toBeVisible();
  await expect(
    page.getByText("No new admissions. The pipeline test data v0.1 has no admission group.", {
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    page.getByText("Select a resident to see the comparison.", { exact: true }),
  ).toBeVisible();
  await expect(page.locator("main table tbody tr")).toHaveCount(0);
});
