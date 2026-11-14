"""Netlify configuration `/netlify.toml` and the CSP build guard `frontend/scripts/check-csp.mjs`
(TRD 15 §4.6 outline, DEP-050..DEP-054; TRD 12 §4.9, SEC-062, SEC-070, SEC-071; TRD 24 D-65, D-99;
FEAT-082)."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tomllib
from pathlib import Path
from typing import Any

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
NETLIFY = ROOT / "netlify.toml"
CHECK_CSP = ROOT / "frontend" / "scripts" / "check-csp.mjs"
TRD12 = ROOT / "specs" / "TRD" / "12_Security_and_Authentication_Spec.md"
TRD15 = ROOT / "specs" / "TRD" / "15_Deployment_and_DevOps_Spec.md"
STAGING_API = "https://echowell-api.onrender.com"
PRODUCTION_API = "https://echowell-backend-production.onrender.com"
NODE = shutil.which("node")


def config() -> dict[str, Any]:
    return tomllib.loads(NETLIFY.read_text())


def fenced_toml(path: Path, anchor: str) -> str:
    text = path.read_text()
    block = re.search(r"```toml\n(.*?)```", text[text.index(anchor) :], re.DOTALL)
    assert block is not None
    return block.group(1)


def trd12_excerpt() -> str:
    return fenced_toml(TRD12, "### 4.9 Browser security")


def csp_directives() -> dict[str, list[str]]:
    csp = config()["headers"][0]["values"]["Content-Security-Policy"]
    parts = [p.strip().split() for p in csp.split(";") if p.strip()]
    return {p[0]: p[1:] for p in parts}


@pytest.mark.req("DEP-053", "SEC-070", "FEAT-082-AC-01", "FEAT-082-FR-05")
def test_header_block_is_byte_identical_to_trd12_excerpt() -> None:
    excerpt = trd12_excerpt()
    text = NETLIFY.read_text()
    assert text.endswith(excerpt)
    assert text.count("[[headers]]") == 1
    headers = config()["headers"]
    assert headers == tomllib.loads(excerpt)["headers"]
    assert headers[0]["for"] == "/*"


@pytest.mark.req("DEP-050", "DEP-052", "FEAT-082-AC-04", "FEAT-082-FR-01", "FEAT-082-FR-04")
def test_build_settings_match_trd15_outline() -> None:
    outline = tomllib.loads(fenced_toml(TRD15, "`netlify.toml` outline"))
    actual = config()
    assert actual == outline
    assert {k: v for k, v in actual["build"].items() if k != "environment"} == {
        "base": "frontend",
        "command": "node scripts/check-csp.mjs && npm run build",
        "publish": ".next",
        "ignore": "git diff --quiet $CACHED_COMMIT_REF $COMMIT_REF -- . ../netlify.toml",
    }
    assert actual["build"]["environment"] == {"NODE_VERSION": "20", "NEXT_TELEMETRY_DISABLED": "1"}
    assert actual["plugins"] == [{"package": "@netlify/plugin-nextjs"}]


@pytest.mark.req("DEP-054", "D-99", "FEAT-082-AC-03", "FEAT-082-FR-03", "FEAT-082-FR-08")
def test_no_api_url_no_context_blocks_no_secrets() -> None:
    text = NETLIFY.read_text()
    assert "NEXT_PUBLIC_API_BASE_URL" not in text
    production_lines = [line for line in text.splitlines() if PRODUCTION_API.split("//")[1] in line]
    assert len(production_lines) == 1
    assert production_lines[0].strip().startswith("Content-Security-Policy")
    assert "context" not in config()
    assert "functions" not in config()
    assert "edge_functions" not in config()
    assert not re.search(r"://[^\s/\"']*:[^\s/\"']*@", text)
    assert "neon.tech" not in text


@pytest.mark.req("SEC-070", "FE-060", "TPS-051", "FEAT-082-FR-06")
def test_connect_src_is_exactly_self_and_the_two_render_origins() -> None:
    directives = csp_directives()
    assert directives["connect-src"] == ["'self'", STAGING_API, PRODUCTION_API]
    assert not any("*" in source for values in directives.values() for source in values)


@pytest.mark.req("SEC-071", "SEC-062", "FEAT-082-AC-05")
def test_permissions_policy_denies_microphone_and_camera_and_hsts_is_set() -> None:
    values = config()["headers"][0]["values"]
    policy = [p.strip() for p in values["Permissions-Policy"].split(",")]
    assert "camera=()" in policy
    assert "microphone=()" in policy
    assert values["Strict-Transport-Security"] == "max-age=31536000; includeSubDomains"


def run_check(api: str | None, *args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    assert NODE is not None
    env = {k: v for k, v in os.environ.items() if k != "NEXT_PUBLIC_API_BASE_URL"}
    if api is not None:
        env["NEXT_PUBLIC_API_BASE_URL"] = api
    return subprocess.run(  # noqa: S603 - fixed interpreter and script
        [NODE, str(CHECK_CSP.relative_to(cwd)) if cwd == ROOT else str(CHECK_CSP), *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )


needs_node = pytest.mark.skipif(NODE is None, reason="SEC-070: node is not installed")


@needs_node
@pytest.mark.req("SEC-070", "FEAT-082-AC-02")
def test_check_csp_accepts_listed_origins_from_any_directory() -> None:
    for api in (STAGING_API, PRODUCTION_API):
        assert run_check(api).returncode == 0
        assert run_check(api, cwd=ROOT / "frontend").returncode == 0


@needs_node
@pytest.mark.req("SEC-070", "D-65", "FEAT-082-AC-02")
@pytest.mark.parametrize(
    "api",
    [
        "https://example.org",
        None,
        "",
        f"{STAGING_API}/api/v1",
        f"{STAGING_API}/",
        "http://echowell-api.onrender.com",
        "not a url",
    ],
)
def test_check_csp_refuses_unlisted_or_malformed_origins(api: str | None) -> None:
    result = run_check(api)
    assert result.returncode != 0
    assert "check-csp:" in result.stderr


@needs_node
@pytest.mark.req("SEC-070", "FEAT-082-FR-06")
def test_check_csp_names_the_missing_origin_and_refuses_wildcards(tmp_path: Path) -> None:
    missing = run_check("https://example.org")
    assert "https://example.org" in missing.stderr
    wildcard = tmp_path / "netlify.toml"
    wildcard.write_text(NETLIFY.read_text().replace(STAGING_API, "https://*.onrender.com"))
    assert run_check(PRODUCTION_API, str(wildcard)).returncode != 0
    no_csp = tmp_path / "empty.toml"
    no_csp.write_text("[build]\n")
    assert run_check(STAGING_API, str(no_csp)).returncode != 0
