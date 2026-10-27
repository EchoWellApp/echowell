"""Static scans of the API document, the database model and the dependency files (TRD 23 DME-005,
DME-020; TRD 06 DB-035; TRD 12 SEC-121, SEC-122, SEC-128; TRD 22 TPS-080..TPS-086; FEAT-039-FR-07,
FEAT-039-FR-08, FEAT-039-AC-07)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from backend.models import Base, EvaluationGroundTruth
from tests.contract.response_validation import document

pytestmark = pytest.mark.security

ROOT = Path(__file__).resolve().parents[2]
SECRET_FIELDS = {"password_hash", "key_hash", "payload", "raw_body", "jwt_secret", "api_key"}
PERSONAL_COLUMN = re.compile(
    r"(^|_)(first|last|full|given|family|sur)?_?name$|dob|birth|phone|address|^email$|contact"
    r"|audio(?!_quality_flag)|recording|wav|ssn|mrn",
    re.IGNORECASE,
)
# Name-like columns that identify no resident: staff accounts, the facility, configuration.
ALLOWED_COLUMNS = {"users.email", "users.display_name", "facilities.name", "api_keys.name"}
FORBIDDEN_PACKAGES = (
    # TPS-080 LLM and generative AI
    "openai", "anthropic", "langchain", "llama", "google-generativeai", "google-genai", "cohere",
    "mistralai", "transformers", "huggingface",
    # TPS-081 web analytics and trackers
    "google-analytics", "react-ga", "@vercel/analytics", "mixpanel", "segment", "posthog",
    "amplitude", "hotjar", "@sentry",
    # TPS-082 voice and speech services
    "speechrecognition", "google-cloud-speech", "azure-cognitiveservices-speech", "deepgram",
    "assemblyai", "whisper", "vosk",
    # TPS-083 notification services
    "twilio", "sendgrid", "firebase", "pusher", "onesignal", "nodemailer", "web-push",
    # TPS-084 third-party auth
    "auth0", "next-auth", "@clerk", "okta", "supabase", "passport",
    # TPS-086 ML services
    "boto3", "sagemaker", "tensorflow", "torch", "scikit-learn", "sklearn", "xgboost",
)  # fmt: skip


def _schema_properties(node: Any, path: str = "") -> list[tuple[str, str]]:
    found = []
    if isinstance(node, dict):
        for name in node.get("properties", {}):
            found.append((path, name))
        for key, value in node.items():
            found += _schema_properties(value, f"{path}/{key}")
    elif isinstance(node, list):
        for value in node:
            found += _schema_properties(value, path)
    return found


@pytest.mark.req("DME-005", "SEC-122", "FEAT-039-FR-07", "FEAT-039-AC-07")
def test_no_secret_or_raw_fields_in_the_api() -> None:
    properties = _schema_properties(document())
    assert [p for p in properties if p[1] in SECRET_FIELDS] == []
    generic = {"id", "resident_code", "created_at"}
    truth = {c.name for c in EvaluationGroundTruth.__table__.columns} - generic
    assert "planted_change" in truth
    schemas = document()["components"]["schemas"]
    for name, schema in schemas.items():
        hits = truth & set(schema.get("properties", {}))
        assert not hits or name == "AlarmTimingRow", (name, hits)
    assert "AlarmTimingRow" in json.dumps(schemas["AnalyticsResponse"])


@pytest.mark.req("DME-020", "DB-035", "SEC-121", "FEAT-039-FR-07", "FEAT-039-AC-07")
def test_no_personal_or_audio_columns() -> None:
    columns = [f"{t.name}.{c.name}" for t in Base.metadata.sorted_tables for c in t.columns]
    personal = [c for c in columns if PERSONAL_COLUMN.search(c.split(".")[1])]
    assert sorted(set(personal) - ALLOWED_COLUMNS) == []
    audio = [c for c in columns if "audio" in c and not c.endswith(".audio_quality_flag")]
    assert audio == []


def _requirements() -> set[str]:
    names = set()
    for path in sorted((ROOT / "backend").glob("requirements*.txt")):
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.split("#")[0].strip()
            if line and not line.startswith("-"):
                names.add(re.split(r"[\[<>=!~; ]", line)[0].lower())
    return names


def _frontend_packages() -> set[str]:
    package = json.loads((ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))
    return {name.lower() for key in ("dependencies", "devDependencies")
            for name in package.get(key, {})}  # fmt: skip


def _forbidden(name: str) -> bool:
    return any(
        name == p or name.startswith((f"{p}-", f"{p}/", f"{p}.")) for p in FORBIDDEN_PACKAGES
    )


@pytest.mark.req("SEC-128", "TPS-080", "TPS-081", "TPS-082", "TPS-083", "TPS-084", "TPS-085",
                 "TPS-086", "AGT-004", "FEAT-039-FR-08", "FEAT-039-AC-07")  # fmt: skip
def test_no_forbidden_dependencies() -> None:
    backend, frontend = _requirements(), _frontend_packages()
    assert backend
    assert frontend
    assert sorted(n for n in backend | frontend if _forbidden(n)) == []


@pytest.mark.req("SEC-128", "FEAT-039-FR-08")
def test_the_scan_recognises_forbidden_names() -> None:
    assert all(_forbidden(n) for n in ("openai", "langchain-core", "@sentry/nextjs", "torch"))
    assert not any(_forbidden(n) for n in ("fastapi", "next", "pydantic", "sqlalchemy"))
