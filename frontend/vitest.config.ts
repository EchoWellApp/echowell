// Vitest configuration (TRD 04 FE-180, TRD 13 TST-003, TST-142).
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  resolve: { alias: { "@": fileURLToPath(new URL(".", import.meta.url)) } },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    include: ["tests/unit/**/*.test.ts", "tests/pages/**/*.test.tsx", "components/**/*.test.tsx"],
    env: { NEXT_PUBLIC_API_BASE_URL: "http://localhost:8000", NEXT_PUBLIC_APP_ENV: "local" },
    coverage: {
      enabled: true,
      provider: "v8",
      reporter: ["text", "lcov", "html"],
      include: ["app/**", "components/**", "lib/**", "services/**"],
      exclude: ["**/*.test.ts", "**/*.test.tsx", "tests/**", "lib/api-types.ts"],
      thresholds: { lines: 80 },
    },
  },
});
