"""Post-deploy smoke-test configuration (TRD 15 §4.11 DEP-080..DEP-082; TRD 16 §4.4 step 5, §4.5
step 6; TRD 21 §4.5; TRD 13 TST-134, TST-135, TST-152, TST-153; FEAT-086).

Targets come only from the environment:

| Variable | Meaning |
|---|---|
| SMOKE_API_BASE_URL | API base including `/api/v1` (`https://<backend-host>/api/v1`) |
| SMOKE_FRONTEND_URL | frontend origin (`https://<site>.netlify.app`; optional locally) |
| SMOKE_EXPECTED_SHA | commit the health `version` must equal (optional locally) |
| SMOKE_ENV | `staging` or `production` (selects the suite) |
| SMOKE_USER_EMAIL / SMOKE_USER_PASSWORD | staging only: the seeded researcher (TRD 16 §4.4) |

Without SMOKE_API_BASE_URL every smoke test is skipped, so a plain `pytest -q` stays offline.
Against plain `http://` (local Compose or uvicorn, SEC-065) the HTTPS-only checks (HSTS, the
http→https redirect and the TLS check) are skipped with a reason that names the requirement.
Production checks are unauthenticated and read-only (DEP-081); no smoke user exists there (TST-152).
"""

from __future__ import annotations

from collections.abc import Iterator

import httpx
import pytest

from tests.smoke.support import SMOKE_ENVS, TIMEOUT, SmokeTarget, env_value


@pytest.fixture(scope="session")
def target() -> SmokeTarget:
    api = env_value("SMOKE_API_BASE_URL").rstrip("/")
    if not api:
        pytest.skip("TST-152: SMOKE_API_BASE_URL is not set (smoke tests run after a deploy)")
    env = env_value("SMOKE_ENV")
    if env not in SMOKE_ENVS:
        raise pytest.UsageError("SMOKE_ENV must be staging or production (TRD 21 §4.5)")
    password = env_value("SMOKE_USER_PASSWORD")
    if env == "production" and (password or env_value("SMOKE_USER_EMAIL")):
        raise pytest.UsageError("SMOKE_USER_* is never set for production (TRD 21, TST-152)")
    return SmokeTarget(
        api_base_url=api,
        frontend_url=env_value("SMOKE_FRONTEND_URL").rstrip("/"),
        expected_sha=env_value("SMOKE_EXPECTED_SHA"),
        env=env,
        user_email=env_value("SMOKE_USER_EMAIL"),
        user_password=password,
    )


@pytest.fixture(scope="session")
def http() -> Iterator[httpx.Client]:
    with httpx.Client(timeout=TIMEOUT, follow_redirects=False) as client:
        yield client
