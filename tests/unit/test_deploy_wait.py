"""Deploy wait helper of the deploy workflows (TRD 16 §4.4 steps 2-3, §4.5 step 5, §8;
FEAT-086-FR-02, FR-03)."""

from __future__ import annotations

import pytest

from tests.smoke import wait_for_deploy as w

pytestmark = pytest.mark.unit

SHA = "3f9c2ab0123456789abcdef0123456789abcdef0"


@pytest.mark.req("FEAT-086-FR-02")
def test_backend_version_reads_health() -> None:
    assert w.backend_version("https://x/api/v1/", lambda _: (200, f'{{"version":"{SHA}"}}')) == SHA
    assert w.backend_version("https://x/api/v1", lambda _: (503, "")) == "<http 503>"


@pytest.mark.req("FEAT-086-FR-03")
@pytest.mark.parametrize(
    "html",
    [
        f'<head><meta name="echowell-build" content="{SHA}"/></head>',
        f"<meta content='{SHA}' name='echowell-build'>",
    ],
)
def test_frontend_build_reads_meta(html: str) -> None:
    assert w.frontend_build("https://site", lambda _: (200, html)) == SHA


@pytest.mark.req("FEAT-086-FR-03")
def test_frontend_without_meta() -> None:
    assert w.frontend_build("https://site", lambda _: (200, "<html></html>")).startswith("<no")


@pytest.mark.req("FEAT-086-FR-02", "CIC-040")
def test_wait_times_out(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(w, "backend_version", lambda _url: "old")
    args = w.parse_args(["--sha", SHA, "--api-base-url", "https://x", "--timeout", "0"])
    assert w.wait(args, sleep=lambda _s: None) == 1


@pytest.mark.req("FEAT-086-FR-03")
def test_wait_accepts_previous_frontend_build(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(w, "frontend_build", lambda _url: "abc1234")
    args = w.parse_args(["--sha", SHA, "--frontend-url", "https://s", "--frontend-sha", "abc1234"])
    assert w.wait(args, sleep=lambda _s: None) == 0
