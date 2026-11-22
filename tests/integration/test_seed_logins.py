"""Seeded logins (TRD 13 TST-188; TRD 06 DB-056, DB-057; TRD 24 D-71; TRD 19 `LoginRequest`).

`python -m backend.cli seed test_v0_1` runs in-process against a throwaway database with the
CI-only SEED_* values of `tests/integration/conftest.py`; each seeded user then logs in through
`POST /api/v1/auth/login` on the real app. The three seeded addresses use the RFC 2606 domain
`example.com`, so they must pass the TRD 19 `format: email` check as written, with no validator
override for the e-mail field (DB-057; the reserved `.test` domain is not used).
"""

from __future__ import annotations

from typing import Any

import jsonschema
import pytest
import yaml
from fastapi.testclient import TestClient

from backend.cli import SEED_USERS
from backend.core.config import get_settings
from backend.main import create_app
from backend.schemas.users import LoginRequest
from tests.conftest import make_settings
from tests.contract.response_validation import document
from tests.integration.conftest import SEED_SECRETS, Cli
from tests.integration.db_support import ROOT

pytestmark = pytest.mark.integration

SEEDED = {
    "admin@example.com": ("admin", "SEED_ADMIN_PASSWORD"),
    "clinician@example.com": ("clinician", "SEED_CLINICIAN_PASSWORD"),
    "researcher@example.com": ("researcher", "SEED_RESEARCHER_PASSWORD"),
}
SKELETON = ROOT / "tests" / "fixtures" / "trd19_openapi_skeleton.yaml"


def _trd19_login_request() -> dict[str, Any]:
    spec: dict[str, Any] = yaml.safe_load(SKELETON.read_text(encoding="utf-8"))
    schema: dict[str, Any] = spec["components"]["schemas"]["LoginRequest"]
    return schema


@pytest.mark.req("TST-188", "DB-056", "DB-057", "D-71", "BR-16")
def test_seeded_users_log_in_with_their_role(cli: Cli) -> None:
    """TRD 13 TST-188: after `seed test_v0_1`, `POST /api/v1/auth/login` as each seeded user with
    its SEED_* password answers 200 with the matching `role`."""
    cli.env(**SEED_SECRETS, PIPELINE_AS_OF="2026-10-30T20:00:00+00:00")
    seeded = cli("seed", "test_v0_1")
    assert seeded.code == 0, seeded.err
    assert {email for email, *_ in SEED_USERS} == set(SEEDED)
    settings = make_settings(database_url=cli.urls.app, database_readonly_url=cli.urls.readonly,
                             facility_name="Demo Facility")  # fmt: skip
    app = create_app(settings)
    app.dependency_overrides[get_settings] = lambda: settings
    with TestClient(app, raise_server_exceptions=False) as client:
        for email, (role, secret) in SEEDED.items():
            credentials = {"email": email, "password": SEED_SECRETS[secret]}
            response = client.post("/api/v1/auth/login", json=credentials)
            assert response.status_code == 200, (email, response.text)
            body = response.json()
            assert body["token_type"] == "bearer"  # noqa: S105 - not a secret
            assert body["access_token"]
            assert (body["user"]["email"], body["user"]["role"]) == (email, role)
            assert body["user"]["active"] is True


@pytest.mark.req("TST-188", "DB-057", "D-71", "BR-16")
def test_seeded_emails_validate_against_login_request() -> None:
    """TRD 13 TST-188, TRD 06 DB-057: the seeded e-mail strings validate against the TRD 19
    `LoginRequest` schema (`format: email`, format checking on) and the backend `LoginRequest`
    model, whose e-mail field has no validator override."""
    trd19 = _trd19_login_request()
    assert trd19["properties"]["email"] == {"type": "string", "format": "email", "maxLength": 254}
    generated = document()["components"]["schemas"]["LoginRequest"]["properties"]["email"]
    assert generated["format"] == "email"
    validator = jsonschema.Draft202012Validator(
        trd19, format_checker=jsonschema.Draft202012Validator.FORMAT_CHECKER
    )
    # format checking is active: a string without "@" is rejected
    assert not validator.is_valid({"email": "not-an-email", "password": "x"})
    decorators = LoginRequest.__pydantic_decorators__
    targets = [d.info.fields for d in decorators.field_validators.values()]
    targets += [d.info.fields for d in decorators.validators.values()]
    assert [f for f in targets if "email" in f or "*" in f] == []
    assert decorators.model_validators == {}
    assert LoginRequest.model_fields["email"].annotation is str
    for email, (_, secret) in SEEDED.items():
        body = {"email": email, "password": SEED_SECRETS[secret]}
        errors = [e.message for e in validator.iter_errors(body)]
        assert errors == [], (email, errors)
        assert LoginRequest.model_validate(body).email == email
