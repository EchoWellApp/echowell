import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeAll, vi } from "vitest";
import { clearToken } from "./lib/auth";
import { server } from "./tests/msw/server";

vi.mock("next/navigation", async () => {
  const nav = await import("./tests/support/navigation");
  return nav.navigationMock;
});

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  cleanup();
  clearToken();
  try {
    window.sessionStorage.clear();
  } catch {
    // ignore
  }
});
afterAll(() => server.close());
