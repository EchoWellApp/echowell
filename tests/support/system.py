"""The full EchoWell system on a throwaway PostgreSQL 16 database, for tests (TRD 14 TDV-031, §4.9;
TRD 13 TST-048, TST-081; FEAT-058-FR-03, FEAT-060).

Shared test infrastructure (TRD 24 D-139): the validation harness (Tier B) and the DS-07 UI fixture
tests both build on it. `system()` starts from an empty migrated database, loads the roster with
`seed test_v0_1 --master-only` (the operator CLI) and serves the real app through a `TestClient`;
`TierB.ingest` uploads a CSV and waits for the batch's run, `run_at_as_of` runs the pipeline at the
test as-of and waits for `succeeded` (polling, never a fixed sleep). `ds07()` is the DS-07 fixture:
the full `seed test_v0_1` plus the DS-10 loader, with no clock override in the services.
"""

from __future__ import annotations

import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool

from backend.core.config import get_settings
from backend.main import create_app
from tests.conftest import make_settings
from tests.integration.db_support import (
    ROOT,
    PgUrls,
    cli_environment,
    provision,
    throwaway_database,
    urls_for_superuser,
    urls_from_environment,
)

API = "/api/v1"
AS_OF_PARAM = "2026-10-30T15:00:00-05:00"
TIMEOUT_S = 60.0
SEED_SECRETS = {  # test-only values (TRD 14 §4.9 users)
    "SEED_ADMIN_PASSWORD": "validation-only-admin-pw",
    "SEED_CLINICIAN_PASSWORD": "validation-only-clinician-pw",
    "SEED_RESEARCHER_PASSWORD": "validation-only-researcher-pw",
    "SEED_INGEST_API_KEY": "ewk_validation-only-ingest-key-00000000000000000",
}
LOADER = ROOT / "database" / "seeds" / "load_evaluation_ground_truth.py"
INPUT_CSV = ROOT / "tests" / "fixtures" / "pipeline_input" / "EchoWell_pipeline_test_input_v0_1.csv"
GROUND_TRUTH = ROOT / "tests" / "fixtures" / "answer_key" / "evaluation_ground_truth_v0_1.csv"
TEST_AS_OF = "2026-10-30T20:00:00+00:00"  # 2026-10-30 15:00 America/Chicago


class TierBError(AssertionError):
    pass


@contextmanager
def database() -> Iterator[PgUrls]:
    """A throwaway migrated database on the configured server, else a testcontainer."""
    urls = urls_from_environment()
    if urls is not None and urls.superuser is not None:
        with throwaway_database(urls) as fresh:
            yield fresh
        return
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("postgres:16-alpine", driver="psycopg") as container:
        superuser = container.get_connection_url()
        provision(superuser)
        with throwaway_database(urls_for_superuser(superuser)) as fresh:
            yield fresh


def operator(urls: PgUrls, *argv: str) -> None:
    """Run an operator command as a subprocess, as CI does (TRD 13 §8)."""
    done = subprocess.run(  # noqa: S603 - fixed interpreter and arguments
        [sys.executable, *argv], env=cli_environment(urls, **SEED_SECRETS), cwd=ROOT,
        capture_output=True, text=True, timeout=300, check=False,
    )  # fmt: skip
    if done.returncode != 0:
        raise TierBError(f"{' '.join(argv)} exited {done.returncode}: {done.stderr}")


def load_ground_truth(urls: PgUrls) -> None:
    operator(urls, str(LOADER), str(GROUND_TRUTH))


@dataclass
class TierB:
    urls: PgUrls
    client: TestClient
    tokens: dict[str, str] = field(default_factory=dict)
    batch: dict[str, Any] = field(default_factory=dict)
    run: dict[str, Any] = field(default_factory=dict)

    def headers(self, role: str = "admin") -> dict[str, str]:
        if role not in self.tokens:
            email = f"{role}@example.com"
            password = SEED_SECRETS[f"SEED_{role.upper()}_PASSWORD"]
            response = self.client.post(f"{API}/auth/login",
                                        json={"email": email, "password": password})  # fmt: skip
            if response.status_code != 200:
                raise TierBError(f"login {role}: {response.status_code} {response.text}")
            self.tokens[role] = response.json()["access_token"]
        return {"Authorization": f"Bearer {self.tokens[role]}"}

    def get(self, path: str, role: str = "admin", **params: Any) -> Any:
        response = self.client.get(f"{API}{path}", params=params, headers=self.headers(role))
        if response.status_code != 200:
            raise TierBError(f"GET {path}: {response.status_code} {response.text}")
        return response.json()

    def items(self, path: str, role: str = "admin", **params: Any) -> list[dict[str, Any]]:
        """Every page of a list endpoint."""
        found: list[dict[str, Any]] = []
        while True:
            page = self.get(path, role, limit=500, offset=len(found), **params)
            found.extend(page["items"])
            if len(found) >= page["total"]:
                return found

    def wait(self, run_id: str) -> dict[str, Any]:
        """Poll `GET /pipeline/runs/{id}` until the run leaves `running` (TDV-031)."""
        deadline = time.monotonic() + TIMEOUT_S
        while True:
            run: dict[str, Any] = self.get(f"/pipeline/runs/{run_id}")
            if run["status"] != "running":
                return run
            if time.monotonic() > deadline:
                raise TierBError(f"run {run_id} still running after {TIMEOUT_S} s")
            time.sleep(0.2)

    def ingest(self, data: bytes, filename: str = INPUT_CSV.name) -> dict[str, Any]:
        response = self.client.post(f"{API}/ingest", headers=self.headers(),
                                    files={"file": (filename, data, "text/csv")})  # fmt: skip
        if response.status_code != 202:
            raise TierBError(f"POST /ingest: {response.status_code} {response.text}")
        batch: dict[str, Any] = response.json()
        if batch.get("pipeline_run_id"):
            self.wait(batch["pipeline_run_id"])
        return batch

    def run_at_as_of(self) -> dict[str, Any]:
        """The explicit-as-of run of TDV-031; fails unless it succeeds."""
        response = self.client.post(f"{API}/pipeline/run", headers=self.headers(),
                                    json={"scope": "all", "profile": "test_v0_1",
                                          "as_of": AS_OF_PARAM})  # fmt: skip
        if response.status_code != 202:
            raise TierBError(f"POST /pipeline/run: {response.status_code} {response.text}")
        run = self.wait(response.json()["pipeline_run_id"])
        if run["status"] != "succeeded":
            raise TierBError(f"run {run['id']} {run['status']}: {run.get('warnings')}")
        self.run = run
        return run

    def engine(self) -> Engine:
        return create_engine(self.urls.readonly, poolclass=NullPool)

    def select(self, sql: str, **params: Any) -> list[Any]:
        engine = self.engine()
        try:
            with engine.connect() as connection:
                return list(connection.execute(text(sql), params))
        finally:
            engine.dispose()


@contextmanager
def tier_b(*, ingest: bool = True) -> Iterator[TierB]:
    """Tier B on a fresh database; with `ingest`, DS-01 loaded and the as-of run succeeded.

    With `ingest`, PIPELINE_AS_OF is the test as-of, so the ingest-triggered run already
    evaluates 30 Oct (TRD 14 TDV-031, TRD 24 D-135). Without it the services follow the
    application clock, which tests may freeze (VC-R10-FRZ (c), TDV-061)."""
    with database() as urls:
        operator(urls, "-m", "backend.cli", "seed", "test_v0_1", "--master-only")
        settings = make_settings(database_url=urls.app, database_readonly_url=urls.readonly,
                                 facility_name="Edgewood",
                                 pipeline_as_of=TEST_AS_OF if ingest else "")  # fmt: skip
        app = create_app(settings)
        app.dependency_overrides[get_settings] = lambda: settings
        with TestClient(app, raise_server_exceptions=False) as client:
            harness = TierB(urls, client)
            if ingest:
                harness.batch = harness.ingest(INPUT_CSV.read_bytes())
                harness.run_at_as_of()
            yield harness


@contextmanager
def ds07() -> Iterator[TierB]:
    """DS-07 (TRD 14 §4.9, TDV-061): the full `seed test_v0_1` (roster, users, SRC-05 and the
    explicit-as-of run) plus the DS-10 loader, with no clock override in the running services."""
    with database() as urls:
        operator(urls, "-m", "backend.cli", "seed", "test_v0_1")
        load_ground_truth(urls)
        settings = make_settings(database_url=urls.app, database_readonly_url=urls.readonly,
                                 facility_name="Edgewood")  # fmt: skip
        app = create_app(settings)
        app.dependency_overrides[get_settings] = lambda: settings
        with TestClient(app, raise_server_exceptions=False) as client:
            harness = TierB(urls, client)
            harness.run = harness.items("/pipeline/runs")[0]
            yield harness
