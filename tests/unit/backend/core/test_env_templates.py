"""Environment templates (TRD 21 §4.6, ENV-040, ENV-041; FEAT-006)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from backend.core.config import Settings, startup_violations
from tests.conftest import make_settings

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[4]
TRD21 = ROOT / "specs/TRD/21_Environment_Configuration_Spec.md"


def template_keys(name: str) -> set[str]:
    text = (ROOT / name).read_text()
    return set(re.findall(r"^#?\s*([A-Z][A-Z0-9_]+)=", text, flags=re.MULTILINE))


def trd21_block(filename: str) -> list[str]:
    """The dotenv code block that follows the "`<filename>` content:" line of TRD 21 §4.6."""
    text = TRD21.read_text()
    start = text.index(f"`{filename}` content:")
    block = text[start:].split("```dotenv\n", 1)[1].split("```", 1)[0]
    return block.splitlines()


@pytest.mark.req("ENV-040")
def test_env_040_every_settings_field_in_env_example() -> None:
    keys = template_keys(".env.example")
    missing = {f.upper() for f in Settings.model_fields} - keys
    assert missing == set()


@pytest.mark.req("ENV-040")
@pytest.mark.parametrize("filename", [".env.development.example", ".env.production.example"])
def test_env_040_templates_match_trd21(filename: str) -> None:
    actual = [line.rstrip() for line in (ROOT / filename).read_text().splitlines()]
    expected = [line.rstrip() for line in trd21_block(filename)]
    assert actual == expected


@pytest.mark.req("ENV-041", "AC-ENV-03")
def test_env_041_local_dev_jwt_refused_in_staging() -> None:
    settings = make_settings(
        app_env="staging",
        database_url="postgresql+psycopg://app:pw-x@db.example.org/echowell?sslmode=require",
        database_readonly_url="postgresql+psycopg://ro:pw-y@db.example.org/echowell?sslmode=require",
        jwt_secret="local-dev-only-0123456789abcdef0123456789abcdef",  # noqa: S106 - template value
        cors_origins="https://echowell-und-staging.netlify.app",
        facility_name="Edgewood",
    )
    assert ("JWT_SECRET", "template, placeholder or low-entropy value refused") in (
        startup_violations(settings)
    )
