"""Wait until a deployment serves the expected commit (TRD 16 §4.4 steps 2-3, §4.5 step 5, §8;
TRD 15 DEP-082; FEAT-086-FR-02, FR-03).

Polls every 15 s, for at most 15 minutes, in one loop for both targets:

* backend: `GET <api-base>/health` until JSON `version` equals `--sha`;
* frontend: `GET <frontend>/login` until `<meta name="echowell-build" content="…">` equals
  `--sha` or, when Netlify skipped the build because the commit changed nothing under
  `frontend/` or `netlify.toml`, the latest commit that did (`--frontend-sha`, from
  `git log -1 --format=%H -- frontend netlify.toml`).

Exit 0 when every target is ready, 1 on timeout. Prints one line per attempt with the observed
values only (no secrets are involved). Standard library only, so it runs before any install.

    python tests/smoke/wait_for_deploy.py --sha SHA --api-base-url URL \
        [--frontend-url URL --frontend-sha SHA] [--interval 15] [--timeout 900]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable

META = re.compile(
    r"<meta\b(?=[^>]*\bname=[\"']echowell-build[\"'])[^>]*\bcontent=[\"']([^\"']*)[\"']",
    re.IGNORECASE,
)
REQUEST_TIMEOUT_S = 30


def _fetch(url: str) -> tuple[int, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "echowell-deploy-check"})  # noqa: S310
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_S) as response:  # noqa: S310
            return response.status, response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, ""
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return 0, str(getattr(exc, "reason", exc))


def backend_version(api_base_url: str, fetch: Callable[[str], tuple[int, str]] = _fetch) -> str:
    status, body = fetch(f"{api_base_url.rstrip('/')}/health")
    if status != 200:
        return f"<http {status}>"
    try:
        return str(json.loads(body).get("version", ""))
    except ValueError:
        return "<invalid json>"


def frontend_build(frontend_url: str, fetch: Callable[[str], tuple[int, str]] = _fetch) -> str:
    status, body = fetch(f"{frontend_url.rstrip('/')}/login")
    if status != 200:
        return f"<http {status}>"
    match = META.search(body)
    return match.group(1) if match else "<no echowell-build meta>"


def wait(args: argparse.Namespace, sleep: Callable[[float], None] = time.sleep) -> int:
    deadline = time.monotonic() + args.timeout
    accepted_frontend = {args.sha, args.frontend_sha or args.sha}
    attempt = 0
    while True:
        attempt += 1
        ready, observed = True, []
        if args.api_base_url:
            version = backend_version(args.api_base_url)
            observed.append(f"backend version={version}")
            ready &= version == args.sha
        if args.frontend_url:
            build = frontend_build(args.frontend_url)
            observed.append(f"frontend build={build}")
            ready &= build in accepted_frontend
        print(f"attempt {attempt}: " + ", ".join(observed), flush=True)
        if ready:
            print(f"ready: expected {args.sha}", flush=True)
            return 0
        if time.monotonic() + args.interval > deadline:
            print(f"::error::not serving {args.sha} after {args.timeout} s", flush=True)
            return 1
        sleep(args.interval)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sha", required=True, help="commit the deployment must serve")
    parser.add_argument("--api-base-url", default="", help="API base including /api/v1")
    parser.add_argument("--frontend-url", default="", help="frontend origin")
    parser.add_argument(
        "--frontend-sha", default="", help="latest commit touching frontend/ or netlify.toml"
    )
    parser.add_argument("--interval", type=float, default=15.0)
    parser.add_argument("--timeout", type=float, default=900.0)
    args = parser.parse_args(argv)
    if not (args.api_base_url or args.frontend_url):
        parser.error("give --api-base-url, --frontend-url or both")
    return args


if __name__ == "__main__":
    sys.exit(wait(parse_args()))
