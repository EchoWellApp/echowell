// Render helpers: a fresh QueryClient (no retries) and, optionally, a signed-in AuthProvider.
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, type RenderResult } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import type { ReactElement, ReactNode } from "react";
import { setToken, clearToken } from "@/lib/auth";
import { AuthProvider } from "@/lib/AuthProvider";
import type { Role } from "@/lib/types";
import meAdmin from "../fixtures/ds07/me-admin.json";
import { API, fakeJwt } from "../msw/handlers";
import { server } from "../msw/server";

export function testQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: Infinity }, mutations: { retry: false } },
  });
}

export function withQuery(ui: ReactElement, client: QueryClient = testQueryClient()): RenderResult {
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

const NAMES: Record<Role, string> = {
  admin: "Admin User",
  clinician: "Clinician User",
  researcher: "Researcher User",
};

/** Signs in as `role` (token + /auth/me) and renders inside the providers. */
export function renderSignedIn(
  ui: ReactElement,
  role: Role | null = "clinician",
  client: QueryClient = testQueryClient(),
): RenderResult & { client: QueryClient } {
  if (role) {
    setToken(fakeJwt());
    server.use(
      http.get(`${API}/auth/me`, () =>
        HttpResponse.json({ ...meAdmin, role, display_name: NAMES[role] }),
      ),
    );
  } else {
    clearToken();
  }
  const wrap = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>
      <AuthProvider>{children}</AuthProvider>
    </QueryClientProvider>
  );
  return Object.assign(render(ui, { wrapper: wrap }), { client });
}
