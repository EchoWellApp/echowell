"""Production smoke tests, run by `deploy-production.yml` with `-m "smoke and not authenticated"`
(TRD 15 DEP-081 (a)-(f); TRD 16 CIC-051; TRD 13 TST-135, TST-152; FEAT-086-FR-08, FR-09, AC-05).

Unauthenticated and read-only: no login, no write, no smoke user (TST-152). None of these tests
carries the `authenticated` marker. The TLS check (g) is in `test_tls.py`.
"""

from __future__ import annotations

import httpx
import pytest

from tests.smoke.support import (
    SmokeTarget,
    assert_health,
    assert_hsts,
    assert_login_page,
    assert_redirects_to_https,
    require_env,
    require_frontend,
    require_https,
)

pytestmark = pytest.mark.smoke

PROBLEM_JSON = "application/problem+json"


@pytest.fixture(autouse=True)
def _production_only(target: SmokeTarget) -> None:
    require_env(target, "production")


@pytest.mark.req("DEP-081", "TST-152")
def test_a_health_ok_with_expected_version(target: SmokeTarget, http: httpx.Client) -> None:
    assert_health(http, target)


@pytest.mark.req("DEP-081", "TST-152")
def test_b_frontend_login_page_over_https(target: SmokeTarget, http: httpx.Client) -> None:
    require_frontend(target)
    require_https(target.frontend_url)
    assert_login_page(http, target)


@pytest.mark.req("DEP-081")
def test_c_residents_without_token_is_401_problem(target: SmokeTarget, http: httpx.Client) -> None:
    response = http.get(f"{target.api_base_url}/residents")
    assert response.status_code == 401
    assert response.headers.get("content-type", "").startswith(PROBLEM_JSON)
    body = response.json()
    assert body["status"] == 401
    assert body["type"]
    assert body["title"]


@pytest.mark.req("DEP-081")
def test_d_sessions_without_api_key_is_401(target: SmokeTarget, http: httpx.Client) -> None:
    # No X-API-Key: refused before any body is read, so nothing is written (read-only check).
    response = http.post(f"{target.api_base_url}/sessions", json={})
    assert response.status_code == 401


@pytest.mark.req("DEP-081", "TST-135", "SEC-062")
def test_e_hsts_and_https_redirect_on_api(target: SmokeTarget, http: httpx.Client) -> None:
    require_https(target.api_base_url)
    assert_hsts(http.get(f"{target.api_base_url}/health"))
    assert_redirects_to_https(http, f"{target.api_base_url}/health")


@pytest.mark.req("DEP-081", "TST-135", "SEC-062")
def test_e_hsts_and_https_redirect_on_frontend(target: SmokeTarget, http: httpx.Client) -> None:
    require_frontend(target)
    require_https(target.frontend_url)
    assert_hsts(assert_login_page(http, target))
    assert_redirects_to_https(http, f"{target.frontend_url}/login")


@pytest.mark.req("DEP-081", "TST-133")
def test_f_no_audio_route(target: SmokeTarget, http: httpx.Client) -> None:
    assert http.get(f"{target.api_base_url}/audio").status_code == 404
