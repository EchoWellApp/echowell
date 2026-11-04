// A controllable stand-in for next/navigation in Vitest (pathname, search params, router calls).
import { vi } from "vitest";

export const nav = {
  pathname: "/residents",
  search: "",
  params: {} as Record<string, string>,
  router: {
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    refresh: vi.fn(),
    prefetch: vi.fn(),
    forward: vi.fn(),
  },
};

export function setLocation(pathname: string, search = "", params: Record<string, string> = {}) {
  nav.pathname = pathname;
  nav.search = search;
  nav.params = params;
}

export const navigationMock = {
  useRouter: () => nav.router,
  usePathname: () => nav.pathname,
  useSearchParams: () => new URLSearchParams(nav.search),
  useParams: () => nav.params,
  redirect: vi.fn(),
  notFound: vi.fn(() => {
    throw new Error("NEXT_NOT_FOUND");
  }),
};
