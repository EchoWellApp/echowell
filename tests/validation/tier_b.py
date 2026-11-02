"""Tier B: the full system on PostgreSQL 16 (TRD 14 TDV-031, §4.4; TRD 13 TST-048, TST-081;
FEAT-058-FR-03).

From an empty migrated database: `seed test_v0_1 --master-only` (the operator CLI), admin login,
`POST /api/v1/ingest` with DS-01, wait for the batch's run, then `POST /api/v1/pipeline/run` at
the reference as-of and wait for `succeeded` (polling, never a fixed sleep). Results are read
back through the API (analytics, baselines, scores, data alerts, the run) and read-only SELECTs
(processed sessions, ledger, epochs, alerts, cusum state, raw rows).
"""

from __future__ import annotations

import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool

from analytics import COMPOSITE_KEYS
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
from tests.validation.answer_key import GROUND_TRUTH, INPUT_CSV
from tests.validation.outputs import (
    NO_RECORD,
    Outputs,
    alert_row,
    annotated_row,
    day_of,
    feature_label,
    offsets_of,
    outcome_row,
    params_of,
    record_values,
    score_row,
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

    def outputs(self) -> Outputs:
        return collect(self)


@contextmanager
def tier_b(*, ingest: bool = True) -> Iterator[TierB]:
    """Tier B on a fresh database; with `ingest`, DS-01 loaded and the as-of run succeeded."""
    with database() as urls:
        operator(urls, "-m", "backend.cli", "seed", "test_v0_1", "--master-only")
        settings = make_settings(database_url=urls.app, database_readonly_url=urls.readonly,
                                 facility_name="Edgewood")  # fmt: skip
        app = create_app(settings)
        app.dependency_overrides[get_settings] = lambda: settings
        with TestClient(app, raise_server_exceptions=False) as client:
            harness = TierB(urls, client)
            if ingest:
                harness.batch = harness.ingest(INPUT_CSV.read_bytes())
                harness.run_at_as_of()
            yield harness


# --- reading results back -----------------------------------------------------------------------


def collect(harness: TierB) -> Outputs:
    out = Outputs()
    snapshot = harness.select(  # the run DTO has no snapshot; the run row does (VC-G08)
        "SELECT config_snapshot FROM pipeline_runs WHERE id = :id", id=harness.run["id"]
    )[0][0]
    baseline_n = int(snapshot["baseline_n"])
    sessions = harness.select(
        "SELECT p.status, p.reason_text, p.local_date, p.local_time, p.is_morning, "
        "p.baseline_ordinal, p.in_baseline, p.adjusted_features, p.session_id, e.epoch_number, "
        "r.arrival_seq, r.payload, "
        "res.resident_code "
        "FROM processed_sessions p JOIN raw_sessions r ON r.id = p.raw_session_id "
        "JOIN residents res ON res.id = p.resident_id "
        "LEFT JOIN epochs e ON e.id = p.epoch_id ORDER BY r.arrival_seq")  # fmt: skip
    first_seq = min(s.arrival_seq for s in sessions)
    for s in sessions:
        key = (s.resident_code, day_of(s.local_date), s.arrival_seq - first_seq + 1)
        out.annotated[key] = annotated_row(
            local_time=f"{s.local_date.isoformat()} {s.local_time.strftime('%H:%M')}",
            status=s.status, reason=s.reason_text, morning=s.is_morning, epoch=s.epoch_number,
            ordinal=s.baseline_ordinal, in_baseline=s.in_baseline,
            record=record_values(payload_row(s.payload)), baseline_n=baseline_n,
        )  # fmt: skip
        if s.status != "duplicate":
            out.adjusted[(s.session_id,)] = {k: float(s.adjusted_features[k])
                                             for k in COMPOSITE_KEYS}  # fmt: skip
    ledger = harness.select(
        "SELECT res.resident_code, d.local_date, d.status, dev.device_code, d.reason "
        "FROM day_ledger d JOIN residents res ON res.id = d.resident_id "
        "LEFT JOIN devices dev ON dev.id = d.device_id")  # fmt: skip
    for d in ledger:
        out.ledger.append((d.resident_code, d.local_date, d.status, d.device_code, d.reason))
        if d.status != "checked_in":
            out.annotated[(d.resident_code, day_of(d.local_date), NO_RECORD)] = annotated_row(
                local_time=d.local_date.isoformat(), status=d.status, reason=d.reason,
                morning=None, epoch=None, ordinal=None, in_baseline=False,
                record=record_values(None, device=d.device_code), baseline_n=baseline_n,
            )  # fmt: skip
    out.ledger.sort()
    analytics = harness.get("/analytics", role="researcher")
    for row in analytics["status_counts"]:
        out.status_counts[(row["resident_code"],)] = {
            k: v for k, v in row.items() if k != "resident_code"}  # fmt: skip
    for row in analytics["resident_outcomes"]:
        out.outcomes[(row["resident_code"], row["epoch_number"])] = outcome_row(
            device=row["device_code"], usable=row["usable_in_epoch"],
            formed=row["baseline_formed"], frozen_after=row["baseline_frozen_after"],
            scored=row["scored_sessions"] or 0, first_alarm=row["first_alarm_session"],
        )  # fmt: skip
    for b in harness.items("/analytics/baselines"):
        out.baselines[(b["resident_code"], b["epoch_number"], feature_label(b["feature_key"]))] = {
            "device_id": b["device_code"], "n_sessions": b["n_sessions"],
            "first_session": b["first_session_id"],
            "baseline_frozen_after": b["frozen_after_session_id"], "median": b["median"],
            "mad": b["mad"], "robust_spread": b["robust_spread"],
            "floor_applied": b["floor_applied"],
        }  # fmt: skip
    for code in sorted({k[0] for k in out.status_counts}):
        for s in harness.items("/scores", resident_code=code):
            out.scores[(s["session_id"],)] = score_row(
                resident=s["resident_code"], epoch=s["epoch_number"],
                local=date.fromisoformat(s["local_date"]), morning=s["is_morning"], z=s["z"],
                composite_raw=s["composite_raw"], composite_z=s["composite_z"],
                tally=s["cusum_tally"], alarm=s["alarm_state"],
            )  # fmt: skip
    out.params = params_of(snapshot)
    out.morning_offsets = offsets_of(snapshot)
    for a in harness.select(
        "SELECT res.resident_code, e.epoch_number, a.session_id, a.triggered_at, a.local_date, "
        "a.cusum_value, a.status FROM alerts a JOIN epochs e ON e.id = a.epoch_id "
        "JOIN residents res ON res.id = a.resident_id"
    ):  # fmt: skip
        out.alerts.append(alert_row(
            resident=a.resident_code, epoch=a.epoch_number, session=a.session_id,
            triggered=a.triggered_at, local=a.local_date, value=a.cusum_value,
            status="closed" if a.status == "closed" else "open",
        ))  # fmt: skip
    out.alerts.sort(key=lambda a: (a["resident_id"], a["epoch"]))
    for c in harness.select(
        "SELECT res.resident_code, e.epoch_number, c.current_tally, c.alarm_on "
        "FROM cusum_state c JOIN epochs e ON e.id = c.epoch_id "
        "JOIN residents res ON res.id = c.resident_id"
    ):  # fmt: skip
        out.cusum[(c.resident_code, c.epoch_number)] = {
            "current_tally": c.current_tally, "alarm_on": c.alarm_on}  # fmt: skip
    out.data_alerts = sorted(
        (a["kind"], a["resident_code"] or a["device_code"] or "", a["title"], a["detail"])
        for a in harness.items("/data-alerts", status="open")
    )  # fmt: skip
    return out


def payload_row(payload: dict[str, Any]) -> dict[str, str]:
    """A stored payload as the CSV row it came from (values as received, TRD 14 VC-G11)."""
    row = {k: ("" if v is None else str(v)) for k, v in payload.items()}
    if "resident_code" in row and "resident_id" not in row:
        row["resident_id"] = row["resident_code"]
    return row


def as_of() -> datetime:
    return datetime(2026, 10, 30, 20, 0, tzinfo=UTC)
