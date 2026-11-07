// req: FE-092, UX-004
import { render } from "@testing-library/react";
import { statusLabel } from "@/lib/wording";
import { StatusPill } from "./StatusPill";

describe("StatusPill", () => {
  it.each([
    ["changed", "▲Changed", "▲ Changed"],
    ["needs_attention", "!Needs attention", "! Needs attention"],
    ["learning", "○Learning", "○ Learning"],
    ["usual", "●Usual", "● Usual"],
  ] as const)("%s pill has a hidden glyph and its label", (status, text, label) => {
    const { container } = render(<StatusPill status={status} size="lg" />);
    expect(container.textContent).toBe(text);
    expect(container.querySelector("[aria-hidden='true']")?.textContent).toBe(text[0]);
    expect(statusLabel(status)).toBe(label);
  });
});
