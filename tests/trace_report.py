"""List Must requirements without a test or inspection entry (TRD 13 TST-013, TRD 03 NFR-111).

Usage: python tests/trace_report.py. Scans TRDs 02, 04, 05 and 07-12 for Must rows, then looks for
`@pytest.mark.req("<ID>")` / `req("<ID>", ...)` in tests/, `// req: <ID>` in frontend tests and
entries in docs/reports/traceability_inspections.md.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRDS = ("02", "04", "05", "07", "08", "09", "10", "11", "12")
ID = r"[A-Z]{2,4}-\d{3}"
MUST_ROW = re.compile(rf"^\|\s*({ID})\s*\|.*\|\s*Must\s*\|", re.MULTILINE)


def must_ids() -> set[str]:
    ids: set[str] = set()
    for prefix in TRDS:
        for path in (ROOT / "specs/TRD").glob(f"{prefix}_*.md"):
            ids |= set(MUST_ROW.findall(path.read_text(encoding="utf-8")))
    return ids


def referenced_ids() -> set[str]:
    found: set[str] = set()
    for path in (ROOT / "tests").rglob("test_*.py"):
        for call in re.findall(r"req\(([^)]*)\)", path.read_text(encoding="utf-8")):
            found |= set(re.findall(ID, call))
    frontend = ROOT / "frontend"
    for pattern in ("tests/**/*.ts*", "components/**/*.test.tsx"):
        for path in frontend.glob(pattern):
            for line in re.findall(r"//\s*req:(.*)", path.read_text(encoding="utf-8")):
                found |= set(re.findall(ID, line))
    inspections = ROOT / "docs/reports/traceability_inspections.md"
    if inspections.exists():
        found |= set(re.findall(ID, inspections.read_text(encoding="utf-8")))
    return found


def main() -> int:
    missing = sorted(must_ids() - referenced_ids())
    for requirement_id in missing:
        print(requirement_id)
    print(f"{len(missing)} Must requirement(s) without a test or inspection entry")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
