"""No audio in or out (TRD 13 TST-133; TRD 12 SEC-121; TRD 03 NFR-040; FEAT-039-FR-04,
FEAT-039-AC-04). The OpenAPI scan of FEAT-038 (`test_no_audio_or_identity_properties`) covers
the document; this module sends a WAV body to every route and checks nothing is stored."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from starlette.routing import Route

from backend.api.permissions import PERMISSIONS
from tests.integration.api.conftest import Principals
from tests.integration.world import World

pytestmark = pytest.mark.security

WAV = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x40\x1f\x00\x00"
TABLES = ("raw_sessions", "ingest_batches", "ingest_rejections", "staff_notes", "alert_reviews",
          "users", "pipeline_runs")  # fmt: skip


def _counts(scene: World) -> list[int]:
    return [
        int(scene.session.execute(text(f"SELECT count(*) FROM {t}")).scalar_one())  # noqa: S608
        for t in TABLES
    ]


def _credentials(principals: Principals, key: str) -> dict[str, str]:
    access = PERMISSIONS[key]
    if access.anonymous:
        return {}
    if access.roles:
        return principals.bearer("admin")
    return principals.api_key("ingest")


@pytest.mark.req("TST-133", "SEC-121", "NFR-040", "AGT-006", "FR-015", "FEAT-039-FR-04",
                 "FEAT-039-AC-04")  # fmt: skip
@pytest.mark.parametrize("media_type", ["audio/wav", "audio/mpeg", "Audio/WAV"])
def test_audio_is_refused_everywhere(
    api: TestClient, scene: World, principals: Principals, media_type: str
) -> None:
    before = _counts(scene)
    routes = [
        r for r in api.app.routes  # type: ignore[attr-defined]
        if isinstance(r, Route) and r.path.startswith("/api/v1/") and "/_test/" not in r.path
    ]  # fmt: skip
    called: list[Any] = []
    for route in routes:
        path = route.path.replace("{id}", str(uuid.uuid4())).replace("{resident_code}", "R01")
        for method in sorted(route.methods or ()):
            if method == "HEAD":
                continue
            key = f"{method} {route.path.removeprefix('/api/v1')}"
            if key not in PERMISSIONS:
                continue  # Swagger UI (test environments only)
            headers = {**_credentials(principals, key), "Content-Type": media_type}
            response = api.request(method, path, content=WAV, headers=headers)
            assert response.status_code in (415, 422), (key, response.status_code, response.text)
            assert response.json()["type"].endswith(("UNSUPPORTED_MEDIA_TYPE", "VALIDATION_ERROR"))
            called.append(key)
    assert set(called) >= {k for k in PERMISSIONS if "(text/csv)" not in k}
    assert _counts(scene) == before


@pytest.mark.req("TST-133", "FEAT-039-AC-04")
def test_audio_inside_a_multipart_upload_is_refused(
    api: TestClient, scene: World, principals: Principals
) -> None:
    before = _counts(scene)
    response = api.post("/api/v1/ingest", files={"file": ("voice.wav", WAV, "audio/wav")},
                        headers=principals.api_key("ingest"))  # fmt: skip
    assert response.status_code in (415, 422), response.text
    assert _counts(scene) == before
