"""Performance suite fixtures and timing helpers (TRD 13 TST-120..TST-126, TST-190; TRD 16 CIC-035,
CIC-036; FEAT-079).

Commands:

- nightly (`e2e.yml` job `performance`, CIC-035): `pytest tests/performance -m performance`;
- every PR (`ci.yml` job `backend-test`, CIC-036, TST-126): `pytest tests/performance -m budget`
  (TST-120, TST-121 with 50 requests, TST-124).

The modules here are deselected from any other pytest run (for example a bare `pytest -q`) unless
the marker expression names `performance` or `budget` or a path under `tests/performance` is given,
so the normal suite never pays for DS-08. Deselection is not a skip (TST-153).

Each stack is a throwaway migrated PostgreSQL 16 database (`tests.support.system.database`: the
configured server when TEST_SUPERUSER_URL is set, else a `postgres:16-alpine` testcontainer) served
by the real app on a local uvicorn server in a background thread, so a 202 is timed when it is sent,
before the background pipeline run (API-123). Requests go through `httpx`; samples are
`time.perf_counter` wall-clock milliseconds; every latency test warms its endpoint before sampling
(NFR-001..NFR-004 "warm"). Credentials (an admin user and an `ingest:write` API key) are created per
stack with the operator CLI and never committed (CIC-026). DS-08 and every other dataset here are
synthetic and live only in these throwaway databases (TDV-007).

`build/performance.json` (artifact `performance-report`, TRD 16 §4.10), written at session end::

    {
      "generated_at": "2026-11-05T12:00:00+00:00",   # UTC
      "git_sha": "<HEAD>",
      "budgets": {
        "TST-121": {"title": "...", "statistic": "p95", "measured_ms": 84.1, "budget_ms": 1000,
                    "samples": 50, "passed": true},
        ...
      },
      "info": {"ds08_db_size_bytes": ..., "nfr152_projection_bytes": ...}
    }

`statistic` is `p95` (`statistics.quantiles(samples, n=100)[94]`), `max` or `elapsed` (one timed
operation); a budget whose wait timed out is recorded with the elapsed time and `passed: false`.
"""

from __future__ import annotations

import json
import os
import secrets
import socket
import statistics
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
import uvicorn
from fastapi import FastAPI

from backend.core.config import get_settings
from backend.core.rate_limit import limiter
from backend.main import create_app
from tests.conftest import make_settings
from tests.integration.db_support import ROOT, PgUrls, cli_environment
from tests.performance import make_load_dataset as ds
from tests.support.system import SEED_SECRETS, TEST_AS_OF, database, operator

API = "/api/v1"
REPORT = ROOT / "build" / "performance.json"
HERE = Path(__file__).resolve().parent
PERF_MARKS = ("performance", "budget")
BATCH_SIZE = 2500  # well under the 5,000-record and 5 MB batch limits (ING-007, API-031)


# --- selection ----------------------------------------------------------------------------------


def _asked_for(config: pytest.Config) -> bool:
    expression = config.getoption("markexpr") or ""
    if any(mark in expression for mark in PERF_MARKS):
        return True
    for arg in config.args:
        path = Path(arg.split("::", 1)[0]).resolve()
        if path == HERE or HERE in path.parents:
            return True
    return False


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if _asked_for(config):
        return
    dropped = [i for i in items if HERE in Path(str(i.path)).resolve().parents]
    if dropped:
        config.hook.pytest_deselected(items=dropped)
        items[:] = [i for i in items if i not in dropped]


# --- timing and the report ----------------------------------------------------------------------


def p95(samples: list[float]) -> float:
    """95th percentile of the samples (FEAT-079 implementation note)."""
    if len(samples) < 2:
        return samples[0]
    return statistics.quantiles(samples, n=100)[94]


@dataclass
class PerfReport:
    budgets: dict[str, dict[str, Any]] = field(default_factory=dict)
    info: dict[str, Any] = field(default_factory=dict)

    def record(
        self,
        budget_id: str,
        title: str,
        *,
        measured_ms: float,
        budget_ms: float,
        statistic: str = "p95",
        samples: int = 1,
        **extra: Any,
    ) -> bool:
        passed = measured_ms <= budget_ms
        self.budgets[budget_id] = {
            "title": title, "statistic": statistic, "measured_ms": round(measured_ms, 1),
            "budget_ms": budget_ms, "samples": samples, "passed": passed, **extra,
        }  # fmt: skip
        return passed

    def outcome(self, budget_id: str, title: str, *, passed: bool, **extra: Any) -> bool:
        """A pass/fail budget without a time limit (TST-190: every response 201 or 200)."""
        self.budgets[budget_id] = {"title": title, "statistic": "outcome", "passed": passed,
                                   **extra}  # fmt: skip
        return passed

    def check(self, budget_id: str) -> None:
        """Fail with the measured value and the budget (FEAT-079 error handling)."""
        entry = self.budgets[budget_id]
        assert entry["passed"], (
            f"{budget_id} {entry['title']}: {entry['statistic']} {entry['measured_ms']} ms "
            f"exceeds the budget of {entry['budget_ms']} ms ({entry['samples']} samples)"
        )

    def write(self, path: Path = REPORT) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        body = {
            "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "git_sha": _git_sha(),
            "budgets": dict(sorted(self.budgets.items())),
            "info": self.info,
        }
        path.write_text(json.dumps(body, indent=2) + "\n", encoding="utf-8")


def _git_sha() -> str:
    try:
        done = subprocess.run(  # noqa: S603 - fixed arguments
            ["git", "rev-parse", "HEAD"],  # noqa: S607 - git from PATH
            cwd=ROOT, capture_output=True, text=True, check=False, timeout=10,
        )  # fmt: skip
    except OSError:
        return "unknown"
    return done.stdout.strip() or os.environ.get("GITHUB_SHA", "unknown")


@pytest.fixture(scope="session")
def perf_report() -> Iterator[PerfReport]:
    report = PerfReport()
    yield report
    if report.budgets or report.info:
        report.write()


# --- a live server and a small API client -------------------------------------------------------


class LiveServer:
    """The app on 127.0.0.1:<free port> in a uvicorn thread (lifespan on)."""

    def __init__(self, app: FastAPI) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(("127.0.0.1", 0))
        self.port = self.sock.getsockname()[1]
        config = uvicorn.Config(app, log_level="warning", access_log=False, lifespan="on")
        self.server = uvicorn.Server(config)
        self.thread = threading.Thread(
            target=self.server.run, kwargs={"sockets": [self.sock]}, daemon=True
        )

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    def __enter__(self) -> LiveServer:
        self.thread.start()
        deadline = time.monotonic() + 30
        while not self.server.started:
            if time.monotonic() > deadline or not self.thread.is_alive():
                raise RuntimeError("uvicorn did not start")
            time.sleep(0.05)
        return self

    def __exit__(self, *_: object) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=30)
        self.sock.close()


@dataclass
class Stack:
    urls: PgUrls
    client: httpx.Client
    admin_email: str
    admin_password: str
    api_key: str
    token: str = ""
    info: dict[str, Any] = field(default_factory=dict)

    def admin(self) -> dict[str, str]:
        if not self.token:
            response = self.client.post(f"{API}/auth/login", json={
                "email": self.admin_email, "password": self.admin_password})  # fmt: skip
            assert response.status_code == 200, f"login: {response.status_code} {response.text}"
            self.token = response.json()["access_token"]
        return {"Authorization": f"Bearer {self.token}"}

    def key(self) -> dict[str, str]:
        return {"X-API-Key": self.api_key}

    def timed(self, method: str, path: str, **kwargs: Any) -> tuple[httpx.Response, float]:
        started = time.perf_counter()
        response = self.client.request(method, f"{API}{path}", **kwargs)
        return response, (time.perf_counter() - started) * 1000

    def wait_run(self, run_id: str, timeout_s: float) -> tuple[dict[str, Any] | None, float]:
        """Poll `GET /pipeline/runs/{id}` until it leaves `running`; (run, elapsed ms).

        The run is None when the timeout passed first."""
        started = time.perf_counter()
        while True:
            response = self.client.get(f"{API}/pipeline/runs/{run_id}", headers=self.admin())
            assert response.status_code == 200, f"run {run_id}: {response.text}"
            run: dict[str, Any] = response.json()
            elapsed = (time.perf_counter() - started) * 1000
            if run["status"] != "running":
                return run, elapsed
            if elapsed > timeout_s * 1000:
                return None, elapsed
            time.sleep(0.1)

    def ingest(self, records: list[dict[str, Any]]) -> None:
        """Load records through `POST /ingest` (JSON batches) and wait for each batch's run."""
        for start in range(0, len(records), BATCH_SIZE):
            batch = records[start : start + BATCH_SIZE]
            limiter.reset()
            response = self.client.post(f"{API}/ingest", headers=self.admin(),
                                        json={"records": batch})  # fmt: skip
            assert response.status_code == 202, f"ingest: {response.status_code} {response.text}"
            run_id = response.json().get("pipeline_run_id")
            if run_id:
                run, _ = self.wait_run(run_id, timeout_s=600)
                assert run is not None, f"load run {run_id} still running after 600 s"
                assert run["status"] == "succeeded", f"load run: {run}"


def cli(urls: PgUrls, *argv: str, stdin: str | None = None) -> str:
    """An operator command as a subprocess (TRD 15 §4.8); its stdout."""
    done = subprocess.run(  # noqa: S603 - fixed interpreter and arguments
        [sys.executable, "-m", "backend.cli", *argv], env=cli_environment(urls), cwd=ROOT,
        input=stdin, capture_output=True, text=True, timeout=300, check=False,
    )  # fmt: skip
    assert done.returncode == 0, f"{' '.join(argv)} exited {done.returncode}: {done.stderr}"
    return done.stdout


@contextmanager
def stack(
    roster: Path | None = None,
    *,
    seed_test_roster: bool = False,
    pipeline_as_of: str = "",
) -> Iterator[Stack]:
    """A fresh database with a roster, an admin and an API key, served on a live server."""
    with database() as urls:
        if seed_test_roster:  # roster R01-R10 and the seeded users and key (DB-056, DB-057)
            operator(urls, "-m", "backend.cli", "seed", "test_v0_1", "--master-only")
            email, password = "admin@example.com", SEED_SECRETS["SEED_ADMIN_PASSWORD"]
            api_key = SEED_SECRETS["SEED_INGEST_API_KEY"]
        else:
            email, password = "perf-admin@example.com", "perf-only-" + secrets.token_hex(12)
            cli(urls, "create-user", "--email", email, "--display-name", "Performance admin",
                "--role", "admin", "--password-stdin", stdin=password + "\n")  # fmt: skip
            api_key = cli(urls, "create-api-key", "--name", "performance").strip().splitlines()[-1]
        if roster is not None:
            cli(urls, "import-master-data", "--dir", str(roster))
        settings = make_settings(
            database_url=urls.app, database_readonly_url=urls.readonly,
            facility_name="Edgewood", pipeline_as_of=pipeline_as_of,
        )  # fmt: skip
        app = create_app(settings)
        app.dependency_overrides[get_settings] = lambda: settings
        with (
            LiveServer(app) as server,
            httpx.Client(base_url=server.base_url, timeout=600) as client,
        ):
            limiter.reset()
            yield Stack(urls, client, email, password, api_key)
        limiter.reset()


# --- the stacks ---------------------------------------------------------------------------------


@pytest.fixture(scope="session")
def ds08(tmp_path_factory: pytest.TempPathFactory) -> tuple[ds.Dataset, Path]:
    """DS-08 generated at test time into a temporary directory (TDV-008, never committed)."""
    out = tmp_path_factory.mktemp("ds08")
    data = ds.generate(ds.SEED)
    ds.write(data, out)
    return data, out


@pytest.fixture(scope="session")
def ds08_stack(ds08: tuple[ds.Dataset, Path]) -> Iterator[Stack]:
    """DS-08 loaded (roster import, then `POST /ingest` batches and their runs): 100 residents,
    10,800 records (TST-122, TST-123)."""
    data, out = ds08
    with stack(out) as s:
        started = time.perf_counter()
        s.ingest(data.records)
        s.info["load_s"] = round(time.perf_counter() - started, 1)
        yield s


HISTORY_DAYS = 380  # ANL-049: a resident with at most 400 records (119 + 50 + 200 used)
HISTORY_PRELOAD = 119  # TST-121: 120 days of history including the first timed record


@dataclass
class History:
    stack: Stack
    records: list[dict[str, Any]]
    next_index: int = HISTORY_PRELOAD

    def take(self, count: int) -> list[dict[str, Any]]:
        chunk = self.records[self.next_index : self.next_index + count]
        assert len(chunk) == count, "the history resident ran out of records"
        self.next_index += count
        return chunk


@pytest.fixture(scope="session")
def history(tmp_path_factory: pytest.TempPathFactory) -> Iterator[History]:
    """One resident H001 on device HD001 with 119 days of gap-free history preloaded; the timed
    `POST /sessions` requests use the following days (fresh session IDs, increasing timestamps)."""
    out = tmp_path_factory.mktemp("history")
    data = ds.generate(ds.SEED + 1, residents=1, days=HISTORY_DAYS, start=date(2025, 9, 1),
                       drop_fraction=0.0, noisy_fraction=0.0, prefix="H")  # fmt: skip
    ds.write(data, out)
    with stack(out) as s:
        s.ingest(data.records[:HISTORY_PRELOAD])
        yield History(s, data.records)


@pytest.fixture(scope="session")
def src05_stack() -> Iterator[Stack]:
    """The test_v0_1 roster with the seeded admin and key, at the test as-of (API-124)."""
    with stack(seed_test_roster=True, pipeline_as_of=TEST_AS_OF) as s:
        yield s
