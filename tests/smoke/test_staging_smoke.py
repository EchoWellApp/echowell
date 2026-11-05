"""Staging smoke tests, run by `deploy-staging.yml` after every merge to `main` (TRD 15 DEP-080
(a)-(i); TRD 16 CIC-042; TRD 13 TST-134, TST-135, TST-152; FEAT-086-FR-05, FR-06, AC-05).

Staging holds exactly the `test_v0_1` seed at the fixed as-of 2026-10-30T15:00:00-05:00 (D-59,
D-71), so the expected figures are the answer-key values. Tests that log in carry the
`authenticated` marker (TST-006); the TLS check (j) is in `test_tls.py`.
Locally: SMOKE_ENV=staging SMOKE_API_BASE_URL=http://localhost:8000/api/v1 with the seed loaded.
"""

from __future__ import annotations

from collections.abc import Iterator

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

REFUSED_ORIGIN = "https://example.org"


@pytest.fixture(autouse=True)
def _staging_only(target: SmokeTarget) -> None:
    require_env(target, "staging")


@pytest.fixture(scope="session")
def auth(target: SmokeTarget, http: httpx.Client) -> Iterator[dict[str, str]]:
    """DEP-080 (c): one login per run as the seeded researcher (login is rate-limited 5/minute)."""
    if target.env != "staging":
        pytest.skip("TST-152: staging suite only")
    if not (target.user_email and target.user_password):
        pytest.fail("SMOKE_USER_EMAIL and SMOKE_USER_PASSWORD are required for staging (DEP-080)")
    response = http.post(
        f"{target.api_base_url}/auth/login",
        json={"email": target.user_email, "password": target.user_password},
    )
    assert response.status_code == 200, response.status_code
    token = response.json()["access_token"]
    yield {"Authorization": f"Bearer {token}"}
    http.post(f"{target.api_base_url}/auth/logout", headers={"Authorization": f"Bearer {token}"})


def _get(http: httpx.Client, target: SmokeTarget, path: str, auth: dict[str, str]) -> object:
    response = http.get(f"{target.api_base_url}{path}", headers=auth)
    assert response.status_code == 200, (path, response.status_code)
    return response.json()


@pytest.mark.req("DEP-080", "TST-152")
def test_a_health_ok_with_expected_version(target: SmokeTarget, http: httpx.Client) -> None:
    assert_health(http, target)


@pytest.mark.req("DEP-080", "TST-152")
def test_b_frontend_login_page(target: SmokeTarget, http: httpx.Client) -> None:
    require_frontend(target)
    assert_login_page(http, target)


@pytest.mark.authenticated
@pytest.mark.req("DEP-080", "TST-152")
def test_c_login_as_seeded_researcher(auth: dict[str, str]) -> None:
    assert auth["Authorization"].startswith("Bearer ")


@pytest.mark.authenticated
@pytest.mark.req("DEP-080", "D-114")
def test_d_resident_summary(target: SmokeTarget, http: httpx.Client, auth: dict[str, str]) -> None:
    body = _get(http, target, "/residents", auth)
    assert isinstance(body, dict)
    assert body["summary"] == {"changed": 2, "needs_attention": 2, "learning": 0, "usual": 6}
    assert body["total"] == 10


@pytest.mark.authenticated
@pytest.mark.req("DEP-080")
def test_e_r09_alarm_since_oct_21(
    target: SmokeTarget, http: httpx.Client, auth: dict[str, str]
) -> None:
    body = _get(http, target, "/residents/R09", auth)
    assert isinstance(body, dict)
    assert body["status"] == "alarm_on"
    assert body["alarm_since"] == "2026-10-21"


@pytest.mark.authenticated
@pytest.mark.req("DEP-080")
def test_f_open_alarms_and_data_alerts(
    target: SmokeTarget, http: httpx.Client, auth: dict[str, str]
) -> None:
    alerts = _get(http, target, "/alerts?status=open", auth)
    assert isinstance(alerts, dict)
    assert sorted(a["resident_code"] for a in alerts["items"]) == ["R09", "R10"]
    data_alerts = _get(http, target, "/data-alerts?status=open", auth)
    assert isinstance(data_alerts, dict)
    found = sorted(
        (a["kind"], a["resident_code"] or a["device_code"]) for a in data_alerts["items"]
    )
    assert found == [
        ("baseline_stalled", "R08"),
        ("device_silent", "D02"),
        ("high_set_aside", "R03"),
        ("possible_other_speaker", "R05"),
    ]
    silent = next(a for a in data_alerts["items"] if a["kind"] == "device_silent")
    assert "Oct 12" in silent["detail"]


@pytest.mark.authenticated
@pytest.mark.req("DEP-080")
def test_g_analytics_received_and_used(
    target: SmokeTarget, http: httpx.Client, auth: dict[str, str]
) -> None:
    body = _get(http, target, "/analytics", auth)
    assert isinstance(body, dict)
    kpis = body["kpis"]
    assert (kpis["checkins_received"]["count"], kpis["checkins_received"]["expected"]) == (281, 300)
    assert (kpis["used_for_scoring"]["count"], kpis["used_for_scoring"]["expected"]) == (267, 300)


@pytest.mark.req("DEP-080", "TST-134")
def test_h_cors_preflight(target: SmokeTarget, http: httpx.Client) -> None:
    require_frontend(target)
    url = f"{target.api_base_url}/residents"
    request_headers = {"Access-Control-Request-Method": "GET"}
    allowed = http.options(url, headers={**request_headers, "Origin": target.frontend_origin})
    assert allowed.headers.get("access-control-allow-origin") == target.frontend_origin
    refused = http.options(url, headers={**request_headers, "Origin": REFUSED_ORIGIN})
    assert "access-control-allow-origin" not in refused.headers


@pytest.mark.req("DEP-080", "TST-135", "SEC-062")
def test_i_api_hsts_and_https_redirect(target: SmokeTarget, http: httpx.Client) -> None:
    require_https(target.api_base_url)
    assert_hsts(http.get(f"{target.api_base_url}/health"))
    assert_redirects_to_https(http, f"{target.api_base_url}/health")


@pytest.mark.req("DEP-080", "TST-135", "SEC-062")
def test_i_frontend_hsts_and_https_redirect(target: SmokeTarget, http: httpx.Client) -> None:
    require_frontend(target)
    require_https(target.frontend_url)
    assert_hsts(assert_login_page(http, target))
    assert_redirects_to_https(http, f"{target.frontend_url}/login")
