// `Cache-Control: private, no-store` on protected pages (TRD 04 FE-042); no CSP here (FE-060).
import { NextResponse, type NextRequest } from "next/server";

export function middleware(_request: NextRequest) {
  const response = NextResponse.next();
  response.headers.set("Cache-Control", "private, no-store");
  return response;
}

export const config = {
  matcher: ["/residents/:path*", "/admissions/:path*", "/study/:path*", "/admin/:path*", "/login"],
};
