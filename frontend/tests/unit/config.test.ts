// req: FE-170, FE-171, ENV-030, AC-ENV-08
import { parsePublicConfig } from "@/lib/config";

describe("parsePublicConfig", () => {
  it("accepts a local http origin", () => {
    expect(parsePublicConfig({ apiBaseUrl: "http://localhost:8000", appEnv: "local" })).toEqual({
      apiBaseUrl: "http://localhost:8000",
      appEnv: "local",
      gitSha: "unknown",
    });
  });

  it.each([
    [undefined, "local", /is required/],
    ["localhost:8000", "local", /absolute http\(s\) URL/],
    ["ftp://api.example.org", "production", /absolute http\(s\) URL/],
    ["https://api.example.org/api/v1", "production", /origin only/],
    ["https://api.example.org/", "production", /origin only/],
    ["http://api.example.org", "staging", /https:\/\//],
    ["https://api.example.org", "demo", /NEXT_PUBLIC_APP_ENV/],
  ])("rejects %s with app env %s", (apiBaseUrl, appEnv, message) => {
    expect(() => parsePublicConfig({ apiBaseUrl, appEnv })).toThrow(message);
  });
});
