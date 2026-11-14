"""TLS protocol check on both hosted origins (TRD 12 SEC-066, SEC-060; TRD 15 DEP-080 (j),
DEP-081 (g); FEAT-083, FEAT-086-FR-12).

TLS 1.1 must be refused by the server and TLS 1.2 accepted. The TLS 1.1 client lowers its own
OpenSSL security level so that a refusal can only come from the server; a client that cannot offer
TLS 1.1 at all makes the test fail rather than pass silently. Runs for staging and production;
skipped for plain-HTTP local targets (SEC-065).
"""

from __future__ import annotations

import socket
import ssl
from urllib.parse import urlsplit

import pytest

from tests.smoke.support import SmokeTarget, require_frontend, require_https

pytestmark = pytest.mark.smoke

TIMEOUT_S = 15.0


def _handshake(host: str, port: int, context: ssl.SSLContext) -> str | None:
    with (
        socket.create_connection((host, port), timeout=TIMEOUT_S) as raw,
        context.wrap_socket(raw, server_hostname=host) as tls,
    ):
        return tls.version()


def _tls11_context() -> ssl.SSLContext:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE  # only the protocol version is under test here
    context.minimum_version = ssl.TLSVersion.TLSv1_1
    context.maximum_version = ssl.TLSVersion.TLSv1_1
    context.set_ciphers("DEFAULT:@SECLEVEL=0")
    return context


def _tls12_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.maximum_version = ssl.TLSVersion.TLSv1_2
    return context


def assert_tls_policy(url: str) -> None:
    require_https(url)
    parts = urlsplit(url)
    host, port = parts.hostname or "", parts.port or 443
    try:
        version = _handshake(host, port, _tls11_context())
    except ssl.SSLError as exc:
        if "NO_PROTOCOLS_AVAILABLE" in str(exc).upper().replace(" ", "_"):
            pytest.fail(f"this client cannot offer TLS 1.1, so SEC-066 is not verified: {exc}")
    except (ConnectionResetError, ConnectionAbortedError, EOFError):
        pass  # the server closed the connection: refused
    else:
        pytest.fail(f"{host} accepted a TLS 1.1 handshake ({version})")
    assert _handshake(host, port, _tls12_context()) == "TLSv1.2"


@pytest.mark.req("SEC-066", "DEP-080", "DEP-081")
def test_tls_policy_api(target: SmokeTarget) -> None:
    assert_tls_policy(target.api_base_url)


@pytest.mark.req("SEC-066", "DEP-080", "DEP-081")
def test_tls_policy_frontend(target: SmokeTarget) -> None:
    require_frontend(target)
    assert_tls_policy(target.frontend_url)
