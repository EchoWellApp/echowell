"""Alerts surface only through the authenticated API (TRD 02 FR-109; TRD 09 CUS-022;
FEAT-030-AC-07): no e-mail, SMS or push client in the dependencies or the backend code."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[3]
CLIENTS = re.compile(
    r"\b(smtplib|email\.mime|sendgrid|twilio|mailgun|postmark|pushover|firebase_admin|"
    r"apns|pyfcm|onesignal|boto3|botocore|vonage|plivo|slack_sdk)\b",
    re.IGNORECASE,
)


@pytest.mark.req("FR-109", "CUS-022", "AC-CUS-08", "FEAT-030-AC-07", "FEAT-030-FR-05")
def test_no_messaging_client() -> None:
    requirements = [ROOT / "backend" / "requirements.txt", ROOT / "requirements-dev.txt"]
    hits = [
        f"{path.relative_to(ROOT)}:{n}"
        for path in [*requirements, *sorted((ROOT / "backend").rglob("*.py"))]
        if path.exists()
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1)
        if CLIENTS.search(line) and not line.lstrip().startswith("#")
    ]
    assert hits == []
