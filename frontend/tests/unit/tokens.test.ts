// req: FE-160 (colours only from tokens), FE-164 (reduced motion), UX-250
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

function cssFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return cssFiles(path);
    return name.endsWith(".module.css") ? [path] : [];
  });
}

describe("design tokens", () => {
  it("no component stylesheet contains a hex colour literal", () => {
    const offenders = cssFiles(join(__dirname, "../../components")).filter((f) =>
      /#[0-9a-fA-F]{3,6}\b/.test(readFileSync(f, "utf8")),
    );
    expect(offenders).toEqual([]);
  });

  it("defines the light and dark schemes and reduced motion", () => {
    const tokens = readFileSync(join(__dirname, "../../styles/tokens.css"), "utf8");
    expect(tokens.toLowerCase()).toContain("--chrome: #1f3a52;");
    expect(tokens).toContain("@media (prefers-color-scheme: dark)");
    const globals = readFileSync(join(__dirname, "../../styles/globals.css"), "utf8");
    expect(globals).toContain("prefers-reduced-motion: reduce");
  });
});
