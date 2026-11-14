"""Dependency-audit gate with time-boxed exceptions (TRD 16 CIC-019, CIC-072; TRD 24 D-105).

Reads the advisory IDs of the rows of `SECURITY_EXCEPTIONS.md` whose `Expires` date (YYYY-MM-DD) is
today or later, then runs the audit and fails on any finding that is not excepted:

    python scripts/ci/audit_gate.py pip -r backend/requirements.txt -r backend/requirements-dev.txt
    python scripts/ci/audit_gate.py npm --prefix frontend

An expired row no longer counts, so the gate turns red again on its expiry date.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TABLE = ROOT / "SECURITY_EXCEPTIONS.md"
ID = re.compile(r"\b(GHSA-[0-9a-z]{4}-[0-9a-z]{4}-[0-9a-z]{4}|PYSEC-\d{4}-\d+|CVE-\d{4}-\d+)\b")
DATE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
BLOCKING_NPM = {"high", "critical"}


def active_exceptions(today: dt.date | None = None) -> set[str]:
    today = today or dt.datetime.now(dt.UTC).date()
    ids: set[str] = set()
    for line in TABLE.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|") or line.startswith("|---"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 7 or cells[0] == "Advisory":
            continue
        expires = DATE.search(cells[6])
        if expires and dt.date.fromisoformat(expires.group(1)) >= today:
            ids.update(ID.findall(cells[0]))
    return ids


def pip_gate(args: list[str], allowed: set[str]) -> int:
    cmd = ["pip-audit", "--format", "json", *args]
    done = subprocess.run(cmd, capture_output=True, text=True, check=False)  # noqa: S603 - fixed tool
    data = json.loads(done.stdout or "{}")
    found = [
        (dep["name"], dep["version"], v["id"], [v["id"], *v.get("aliases", [])])
        for dep in data.get("dependencies", [])
        for v in dep.get("vulns", [])
    ]
    return report(found, allowed)


def npm_gate(args: list[str], allowed: set[str]) -> int:
    cmd = ["npm", "audit", "--omit=dev", "--json", *args]
    done = subprocess.run(cmd, capture_output=True, text=True, check=False)  # noqa: S603 - fixed tool
    data = json.loads(done.stdout or "{}")
    found = []
    for name, vuln in data.get("vulnerabilities", {}).items():
        for via in vuln.get("via", []):
            if isinstance(via, dict) and via.get("severity") in BLOCKING_NPM:
                ghsa = via.get("url", "").rsplit("/", 1)[-1]
                found.append((name, vuln.get("range", ""), ghsa, [ghsa]))
    return report(found, allowed)


def report(found: list[tuple[str, str, str, list[str]]], allowed: set[str]) -> int:
    blocking = [f for f in found if not set(f[3]) & allowed]
    for name, version, vid, _ in found:
        mark = "BLOCKING" if (name, version, vid, _) in blocking else "excepted"
        print(f"{mark:9} {name} {version} {vid}")
    print(
        f"{len(found)} advisories, {len(found) - len(blocking)} excepted, {len(blocking)} blocking"
    )
    return 1 if blocking else 0


def main(argv: list[str]) -> int:
    kind, rest = argv[0], argv[1:]
    allowed = active_exceptions()
    return pip_gate(rest, allowed) if kind == "pip" else npm_gate(rest, allowed)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
