"""Helpers shared by the post-deploy smoke tests (TRD 15 DEP-080, DEP-081; TRD 13 TST-135;
FEAT-086). Fixtures live in `conftest.py`; configuration is described there."""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx
import pytest

SMOKE_ENVS = ("staging", "production")
TIMEOUT = httpx.Timeout(30.0)  # LOG-103: a response slower than 30 s is a failure
HSTS = "max-age=31536000; includeSubDomains"  # TRD 12 SEC-062


@dataclass(frozen=True)
class SmokeTarget:
    api_base_url: str
    frontend_url: str
    expected_sha: str
    env: str
    user_email: str
    user_password: str

    @property
    def api_is_https(self) -> bool:
        return urlsplit(self.api_base_url).scheme == "https"

    @property
    def frontend_is_https(self) -> bool:
        return urlsplit(self.frontend_url).scheme == "https"

    @property
    def frontend_origin(self) -> str:
        parts = urlsplit(self.frontend_url)
        return f"{parts.scheme}://{parts.netloc}"


def env_value(name: str) -> str:
    return os.environ.get(name, "").strip()


def require_env(target: SmokeTarget, env: str) -> None:
    if target.env != env:
        pytest.skip(f"TST-152: {env} suite; this run has SMOKE_ENV={target.env}")


def require_frontend(target: SmokeTarget) -> None:
    if not target.frontend_url:
        pytest.skip("DEP-080: SMOKE_FRONTEND_URL is not set (local run without a frontend)")


def require_https(url: str) -> None:
    if urlsplit(url).scheme != "https":
        pytest.skip("SEC-065: plain HTTP on localhost; HSTS, redirect and TLS need HTTPS (TST-135)")


def http_variant(url: str) -> str:
    parts = urlsplit(url)
    return f"http://{parts.netloc}{parts.path or '/'}"


def assert_hsts(response: httpx.Response) -> None:
    """TST-135, SEC-062: the HSTS header of TRD 12 §4.9 is present."""
    value = response.headers.get("strict-transport-security", "")
    assert value.replace(" ", "").lower().startswith(HSTS.replace(" ", "").lower()), value


def assert_redirects_to_https(http: httpx.Client, url: str) -> None:
    """TST-135: an `http://` request is redirected to the same host over `https://`."""
    response = http.get(http_variant(url))
    assert response.status_code in (301, 302, 307, 308), response.status_code
    location = response.headers.get("location", "")
    assert location.startswith(f"https://{urlsplit(url).netloc}"), location


def assert_health(http: httpx.Client, target: SmokeTarget) -> None:
    """DEP-080 (a) / DEP-081 (a): health 200, database ok, version = expected SHA."""
    response = http.get(f"{target.api_base_url}/health")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    if target.expected_sha:
        assert body["version"] == target.expected_sha
    else:
        assert body["version"], "health version is empty"


def assert_login_page(http: httpx.Client, target: SmokeTarget) -> httpx.Response:
    """DEP-080 (b) / DEP-081 (b): the frontend `/login` page returns 200."""
    response = http.get(f"{target.frontend_url}/login")
    assert response.status_code == 200, response.status_code
    assert "text/html" in response.headers.get("content-type", "")
    return response
